#!/usr/bin/env python3
"""
Verifier for third-party Agent Skill bundles.

This tool answers one question about a skill somebody else wrote:
*what can this thing do to me, and is any of it hidden?*

It is the outward-facing counterpart to scripts/audit_skill_safety.py. That
tool audits skills this repository authors, and can therefore assume the
files are laid out honestly. This one assumes the opposite: the bundle is
hostile until read, and the parts of it designed to escape review are the
parts that matter.

Three properties define the design, and each is a deliberate refusal:

  * It never fetches.  No URL is ever opened. You clone or unpack the skill
    yourself and point this at a directory. A verifier that reaches the
    network is a verifier that can exfiltrate what it reads.

  * It never writes.  The report goes to stdout; `--json > file` is how you
    keep a copy. Nothing on disk is modified, so running it can never be the
    step that installs the thing you were trying to check.

  * It never runs anything.  No import, no exec, no subprocess, no archive
    extraction. Every file is read as bytes and analysed structurally.

Those three refusals are also why the capability declaration in
attestation.json reads `network: none, process_execution: none,
dynamic_code_execution: none, filesystem: read-only` -- and why
scripts/audit_skill_safety.py can hold this file to them on every commit.

WHAT IT ACTUALLY CHECKS

  1. Every file in the bundle, not just SKILL.md and the scripts SKILL.md
     mentions. Published research bypassed eight scanners by shipping the
     payload in a file nothing references -- a test fixture that pytest
     imports automatically. Enumerating the whole tree, including
     __pycache__, is the cheapest defence against that entire class.

  2. Files that execute without anyone invoking them: conftest.py,
     sitecustomize.py, .pth files, setup.py, npm lifecycle scripts, git
     hooks, agent hook settings, and __init__.py that does more than declare.

  3. Content that cannot be reviewed at all: shipped bytecode, opaque
     binaries, nested archives, encoded blobs, oversize files.

  4. Content engineered to escape review: invisible and bidirectional
     Unicode, directive-bearing HTML comments, whitespace inflation, single
     lines long enough to run past where any reviewer or scanner looks.

  5. What the Python actually does, derived from the AST, compared against
     whatever the bundle claims in attestation.json when it carries one.

WHAT IT DOES NOT DO -- READ THIS PART

  A clean result means "none of the patterns below were found". It does not
  mean the skill is safe, and this tool will never print the word "safe".
  Every published skill scanner, including the ones maintained by NVIDIA,
  Snyk and Cisco, has been bypassed by researchers using ordinary
  obfuscation. There is no reason to believe this one is the exception.
  Static analysis cannot decide intent, and a skill whose behaviour is
  benign in its code can still be malicious in its prose.

  Use this to decide what to read, not to decide what to trust.

Deliberately stdlib-only and self-contained, so a copy of this skill lifted
out of this repository still runs, and so auditing a stranger's skill never
requires installing a stranger's package first.

Usage:
    python verify_skill_bundle.py ./downloaded-skill
    python verify_skill_bundle.py ./downloaded-skill --json > record.json
    python verify_skill_bundle.py ./downloaded-skill --expect-digest sha256:...
    python verify_skill_bundle.py ./downloaded-skill --show-info

Exit codes:
    0  no_known_findings  -- nothing matched; read it anyway
    1  needs_review       -- a human must look at the findings before installing
    2  do_not_install     -- at least one CRITICAL finding
    3  tool error         -- bad arguments or an unreadable target
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

TOOL_NAME = "verify_skill_bundle.py"
TOOL_VERSION = "1.0.0"
RECORD_SCHEMA_VERSION = "1.0.0"
RULESET_VERSION = "2026.08.31"

DISCLAIMER = (
    "This record lists patterns that were and were not found by a static "
    "scan. It is not a certification, a warranty, or a statement that the "
    "bundle is safe. Every published agent-skill scanner has been bypassed "
    "by researchers using ordinary obfuscation; assume this one can be too. "
    "Responsibility for installing the bundle remains with whoever installs it."
)

# ---------------------------------------------------------------------------
# Resource ceilings.
#
# A verifier that can be made to exhaust memory on a crafted input is a
# denial-of-service vector aimed at the person doing the reviewing. Every
# limit below is enforced, and hitting one is itself reported rather than
# silently truncating the analysis.
# ---------------------------------------------------------------------------

MAX_FILES = 5000            # bundle-wide file count before analysis is incomplete
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_READ_BYTES = 2 * 1024 * 1024   # per-file; larger files are reported, not read
MAX_LINE_CHARS = 5000       # a longer single line is an evasion signal
MAX_WHITESPACE_RUN = 2000   # consecutive whitespace chars
INFLATION_MIN_BYTES = 20000
INFLATION_RATIO = 0.5

# ---------------------------------------------------------------------------
# Capability model.
#
# Identical ladders to scripts/audit_skill_safety.py, duplicated on purpose:
# this file must keep working when copied out of the repository. A test
# (tests/unit/test_verifier_ruleset_parity.py) fails the build if this
# module's tables ever become weaker than the auditor's.
# ---------------------------------------------------------------------------

CAPABILITY_LADDERS: Dict[str, List[str]] = {
    "network": ["none", "outbound"],
    "process_execution": ["none", "subprocess"],
    "dynamic_code_execution": ["none", "eval"],
    "filesystem": ["read-only", "workspace-write", "workspace-delete", "unrestricted"],
}

DEFAULT_DECLARATION: Dict[str, str] = {
    "network": "none",
    "process_execution": "none",
    "dynamic_code_execution": "none",
    "filesystem": "read-only",
}

NETWORK_MODULES = {
    "socket", "ssl", "urllib", "http", "ftplib", "smtplib", "telnetlib",
    "requests", "httpx", "aiohttp", "xmlrpc", "poplib", "imaplib",
    "webbrowser", "asyncio", "websockets", "paramiko", "boto3", "urllib3",
}
PROCESS_MODULES = {"subprocess", "multiprocessing", "ctypes", "pty", "os2", "signal"}
DYNAMIC_MODULES = {"pickle", "marshal", "importlib", "imp", "runpy", "types", "code"}

DYNAMIC_BUILTINS = {"eval", "exec", "compile", "__import__"}

PROCESS_ATTRS = {
    "system", "popen", "spawnl", "spawnv", "spawnve", "spawnlp", "spawnvp",
    "execv", "execl", "execlp", "execvp", "execve", "fork", "forkpty",
    "posix_spawn", "posix_spawnp", "check_output", "check_call",
}
FS_DELETE_ATTRS = {"remove", "unlink", "rmtree", "rmdir", "removedirs"}
FS_WRITE_ATTRS = {
    "write_text", "write_bytes", "mkdir", "makedirs", "copytree", "copyfile",
    "copy", "copy2", "touch", "rename", "replace", "symlink_to", "chmod",
    "writelines", "chown", "move",
}

OBFUSCATION_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("base64", re.compile(r"\bb(?:ase)?64(?:decode|encode|_decode|_encode)\b", re.IGNORECASE)),
    ("base64-module", re.compile(r"^\s*(?:import|from)\s+base64\b", re.MULTILINE)),
    ("hex-decode", re.compile(r"\bbytes\.fromhex\s*\(")),
    ("codecs-decode", re.compile(r"\bcodecs\.decode\s*\(")),
    ("charcode", re.compile(r"\bfromCharCode\b")),
    ("js-b64", re.compile(r"\b(?:atob|btoa)\s*\(")),
    ("zlib-decompress", re.compile(r"\bzlib\.decompress\s*\(")),
    ("rot13", re.compile(r"['\"]rot[_-]?13['\"]", re.IGNORECASE)),
]

# ---------------------------------------------------------------------------
# Instruction-surface model.
#
# Characters invisible to a reviewer that still reach the model verbatim.
# ---------------------------------------------------------------------------

INVISIBLE_CHARS = {
    0x00AD: "SOFT HYPHEN",
    0x180E: "MONGOLIAN VOWEL SEPARATOR",
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    0x2060: "WORD JOINER",
    0x2061: "FUNCTION APPLICATION",
    0x2062: "INVISIBLE TIMES",
    0x2063: "INVISIBLE SEPARATOR",
    0x2064: "INVISIBLE PLUS",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE (BOM)",
}
BIDI_CHARS = {
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
}


def is_tag_char(cp: int) -> bool:
    """Unicode Tags block: renders as nothing, reaches the model intact."""
    return 0xE0000 <= cp <= 0xE007F


HIDDEN_DIRECTIVE_RE = re.compile(
    r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|the\s+|previous\s+|prior\s+|above\s+)*"
    r"(?:instruction|prompt|rule|direction|guideline|context)"
    r"|\byou\s+(?:must|should|will|shall)\b"
    r"|\b(?:system|developer)\s+prompt\b"
    r"|\bwithout\s+(?:telling|informing|notifying|asking)\b"
    r"|\bdo\s+not\s+(?:tell|mention|report|inform|reveal)\b"
    r"|\bsecretly\b"
    r"|\bdeveloper\s+mode\b",
    re.IGNORECASE,
)

PIPE_TO_SHELL_RE = re.compile(
    r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|k|da)?sh\b"
    r"|(?:iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:iex|invoke-expression)\b",
    re.IGNORECASE,
)

SENSITIVE_TOKEN_RE = re.compile(
    r"(?:^|[\s\"'`/(])\.env\b"
    r"|~/\.ssh|\.ssh/|id_rsa|id_ed25519|id_ecdsa"
    r"|\.aws/credentials|\.netrc|\.npmrc|\.pypirc|\.git-credentials"
    r"|credentials\.json|service_account\.json|\.kube/config"
    r"|\b(?:api[_\s-]?key|secret[_\s-]?key|access[_\s-]?token|auth[_\s-]?token|private[_\s-]?key|password)s?\b",
    re.IGNORECASE,
)
EXFIL_VERB_RE = re.compile(
    r"\bcurl\b|\bwget\b|\bnc\b|\bnetcat\b|\bscp\b|\bfetch\s*\("
    r"|\brequests\.(?:post|put|get)\b|\burlopen\b|\bXMLHttpRequest\b"
    r"|\bPOST\b|\bexfiltrat|\bupload\b|\bsend\s+(?:it\s+|them\s+|this\s+)?to\b"
    r"|https?://",
    re.IGNORECASE,
)
EXFIL_WINDOW = 2

B64_BLOB_RE = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")

# Shell constructs with no benign reading inside a skill bundle.
SHELL_DANGER_PATTERNS: List[Tuple[str, str, "re.Pattern[str]"]] = [
    ("reverse-shell", "CRITICAL", re.compile(r"/dev/tcp/|/dev/udp/|\bnc\b[^\n]*\s-e\s|\bncat\b[^\n]*--exec")),
    ("base64-decode-pipe", "HIGH", re.compile(r"\bbase64\b[^\n]*\s(?:-d|--decode)\b")),
    ("eval-command-substitution", "HIGH", re.compile(r"\beval\s+[\"']?\$\(")),
    ("recursive-force-delete", "HIGH", re.compile(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*[rR]")),
    ("history-tampering", "HIGH", re.compile(r"\bunset\s+HISTFILE\b|\bHISTFILE=\s*/dev/null|\bhistory\s+-c\b")),
    ("crontab-install", "HIGH", re.compile(r"\bcrontab\s+-|/etc/cron\.")),
    ("ld-preload", "HIGH", re.compile(r"\bLD_PRELOAD\b|\bDYLD_INSERT_LIBRARIES\b")),
    ("sudo-nopasswd", "HIGH", re.compile(r"\bNOPASSWD\b|/etc/sudoers")),
]

URL_RE = re.compile(r"\bhttps?://([A-Za-z0-9._~%-]+(?::\d+)?)(?:/[^\s\"'`<>)\]]*)?")

# ---------------------------------------------------------------------------
# File classification.
# ---------------------------------------------------------------------------

PROSE_SUFFIXES = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc", ".org"}
PYTHON_SUFFIXES = {".py", ".pyw"}
BYTECODE_SUFFIXES = {".pyc", ".pyo"}
SHELL_SUFFIXES = {
    ".sh", ".bash", ".zsh", ".fish", ".ksh", ".command", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".wsf",
}
OTHER_CODE_SUFFIXES = {
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".rb", ".pl", ".pm",
    ".php", ".lua", ".r", ".jl", ".go", ".rs", ".java", ".scala", ".swift",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cs", ".kt", ".groovy",
    ".applescript", ".osascript", ".awk",
}
NATIVE_SUFFIXES = {
    ".so", ".dylib", ".dll", ".exe", ".bin", ".o", ".a", ".wasm", ".msi",
    ".app", ".sys", ".ko", ".elf", ".pyd",
}
ARCHIVE_SUFFIXES = {
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz", ".xz", ".txz", ".7z",
    ".rar", ".whl", ".egg", ".jar", ".apk", ".dmg", ".iso", ".zst", ".lz4",
    ".cab", ".deb", ".rpm",
}
# Binary formats whose presence in a skill bundle is ordinary.
BENIGN_BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".mp3", ".wav", ".ogg", ".webm", ".mov",
}

CODE_CLASSES = {"python", "shell", "other-code", "bytecode", "native", "archive"}

CLASS_LABEL = {
    "shell": "shell script",
    "other-code": "non-Python source",
    "python": "Python source",
}

# Tool names a skill can request, grouped by what granting one actually costs.
# Skills are loaded by several agents and each names its tools differently, so
# a Claude-only table would miss the execution tool in an Antigravity skill --
# which is the single grant that matters most. Matching is on the whole name,
# case-insensitively, so `write_to_file` is not read as `Write`.
TOOL_GRANTS: Dict[str, Set[str]] = {
    "command execution": {
        "bash", "shell", "terminal", "run_command", "run_terminal_cmd",
        "execute_command", "run_in_terminal", "runcommand", "executebash",
        "computer", "process",
    },
    "file modification": {
        "write", "edit", "multiedit", "notebookedit", "str_replace_editor",
        "write_to_file", "replace_file_content", "create_file", "edit_file",
        "apply_patch", "delete_file", "writefile", "editfile",
    },
    "network access": {
        "webfetch", "websearch", "web_search", "read_url", "browser",
        "browser_navigate", "fetch", "search_web", "open_url",
    },
    "subagent delegation": {
        "task", "agent", "subagent", "dispatch_agent", "spawn_agent",
    },
}
# Granting these is what makes a hostile skill able to act rather than merely
# advise, so they carry the WARN; everything else is listed for information.
ESCALATING_GRANTS = {"command execution", "network access", "subagent delegation"}

# ---------------------------------------------------------------------------
# Files that execute without anyone invoking them.
#
# This is the class the documented scanner bypasses live in: nothing in
# SKILL.md points at them, so an intent-reading scanner never looks, but the
# runtime loads them anyway.
# ---------------------------------------------------------------------------

AUTORUN_BASENAMES: Dict[str, str] = {
    "conftest.py": (
        "pytest imports every conftest.py it finds, automatically, before any "
        "test runs. Nothing has to reference this file for its top-level code "
        "to execute on the machine of anyone who runs the test suite -- "
        "including CI, on every branch and every fork."
    ),
    "sitecustomize.py": (
        "Python imports sitecustomize at interpreter startup. Its top-level "
        "code runs before any program does."
    ),
    "usercustomize.py": (
        "Python imports usercustomize at interpreter startup when user site "
        "packages are enabled."
    ),
    "setup.py": (
        "pip executes setup.py during installation. Top-level code here runs "
        "with the privileges of whoever installs the package."
    ),
    ".envrc": (
        "direnv sources .envrc automatically on entering the directory."
    ),
    "__main__.py": (
        "Executed when the containing directory or package is run with "
        "`python -m` or `python <dir>`."
    ),
}

def is_convention_discovered_test(rel: str) -> bool:
    """
    True for a Python file pytest will collect without anyone naming it.

    These are never referenced by SKILL.md -- that is how test discovery
    works -- so "unreferenced" says nothing about them. What does say
    something is what their top-level code can do, because running the test
    suite executes it. The documented bypass put its payload in exactly such
    a file, so these are graded rather than excused.
    """
    if not rel.endswith(".py"):
        return False
    parts = rel.split("/")
    name = parts[-1]
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return any(part in ("tests", "test", "testing") for part in parts[:-1])


NPM_LIFECYCLE_KEYS = (
    "preinstall", "install", "postinstall", "prepare", "prepublish",
    "prepublishOnly", "prepack", "postpack",
)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "WARN": 2, "INFO": 3}
BLOCKING_SEVERITY = "CRITICAL"
REVIEW_SEVERITIES = {"HIGH", "WARN"}

VERDICT_DO_NOT_INSTALL = "do_not_install"
VERDICT_NEEDS_REVIEW = "needs_review"
VERDICT_CLEAN = "no_known_findings"

VERDICT_EXIT = {
    VERDICT_CLEAN: 0,
    VERDICT_NEEDS_REVIEW: 1,
    VERDICT_DO_NOT_INSTALL: 2,
}

EXIT_TOOL_ERROR = 3


class ToolError(Exception):
    """A problem with the invocation or the target, not with the bundle."""


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

def finding(check: str, severity: str, path: str, message: str,
            line: Optional[int] = None, snippet: Optional[str] = None,
            owasp: Optional[str] = None) -> Dict[str, Any]:
    """
    Build one finding.

    The fingerprint hashes the text that triggered the finding rather than
    its line number, so re-verifying a bundle whose lines have merely moved
    produces the same fingerprints, while edited content produces new ones.
    """
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"unknown severity: {severity!r}")
    basis = snippet if snippet is not None else message
    digest = hashlib.sha256(f"{check}|{path}|{basis.strip()}".encode("utf-8")).hexdigest()
    return {
        "check": check,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
        "owasp_ast": owasp,
        "fingerprint": digest[:16],
    }


# ---------------------------------------------------------------------------
# Bundle enumeration
#
# Symlinks are never followed, for two independent reasons: a symlinked
# directory can make the walk unbounded, and a symlink pointing outside the
# bundle makes the tool read -- and quote into its report -- a file the user
# never handed it.
# ---------------------------------------------------------------------------

class BundleFile:
    """One entry in the bundle, enumerated but not necessarily readable."""

    __slots__ = ("path", "rel", "size", "is_symlink", "link_target",
                 "escapes_root", "klass", "text", "sha256", "read_error",
                 "truncated")

    def __init__(self, path: Path, rel: str) -> None:
        self.path = path
        self.rel = rel
        self.size: int = 0
        self.is_symlink: bool = False
        self.link_target: Optional[str] = None
        self.escapes_root: bool = False
        self.klass: str = "unknown"
        self.text: Optional[str] = None
        self.sha256: Optional[str] = None
        self.read_error: Optional[str] = None
        self.truncated: bool = False


def _link_escapes(root: Path, link_path: Path) -> Tuple[bool, str]:
    """
    Decide whether a symlink points outside the bundle.

    `os.readlink` is used rather than `Path.resolve()` so the raw target is
    reported even when it does not exist; resolution is then done manually
    against the link's own directory.
    """
    try:
        raw = os.readlink(link_path)
    except OSError as exc:  # pragma: no cover - defensive
        return True, f"<unreadable link: {exc}>"
    target = Path(raw)
    if not target.is_absolute():
        target = link_path.parent / target
    try:
        resolved = Path(os.path.normpath(str(target)))
        root_resolved = Path(os.path.normpath(str(root)))
        resolved.relative_to(root_resolved)
        return False, raw
    except ValueError:
        return True, raw


def classify(rel: str, suffix: str, is_text: bool) -> str:
    """
    Assign one class per file. Suffix first, content second.

    Extension-based classification is not a security boundary -- a payload
    can be named `notes.txt` -- which is why the class only decides which
    scans run, never whether a file is scanned at all.
    """
    name = rel.rsplit("/", 1)[-1]
    if suffix in BYTECODE_SUFFIXES or "/__pycache__/" in f"/{rel}":
        return "bytecode"
    if suffix in PYTHON_SUFFIXES:
        return "python"
    if suffix in SHELL_SUFFIXES:
        return "shell"
    if suffix in OTHER_CODE_SUFFIXES:
        return "other-code"
    if suffix in ARCHIVE_SUFFIXES:
        return "archive"
    if suffix in NATIVE_SUFFIXES:
        return "native"
    if suffix in BENIGN_BINARY_SUFFIXES:
        return "media"
    if suffix in PROSE_SUFFIXES or name.upper().startswith(("README", "LICENSE", "NOTICE")):
        return "prose"
    if is_text:
        return "text-data"
    return "binary"


def _looks_binary(chunk: bytes) -> bool:
    """A NUL byte in the first block is the classic, cheap binary test."""
    return b"\x00" in chunk


def enumerate_bundle(root: Path) -> Tuple[List[BundleFile], List[Dict[str, Any]]]:
    """
    Walk the bundle, reading every file it can, and report what it could not.

    Returns (files, findings). The findings here are about the walk itself:
    truncation, symlinks, unreadable entries. Analysis findings come later.
    """
    files: List[BundleFile] = []
    findings: List[Dict[str, Any]] = []
    total_bytes = 0
    truncated = False

    stack: List[Path] = [root]
    seen_dirs: Set[Tuple[int, int]] = set()

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as scan:
                entries = sorted(scan, key=lambda e: e.name)
        except OSError as exc:
            rel = _rel(root, current)
            findings.append(finding(
                "EXT-UNREADABLE-DIR", "HIGH", rel or ".",
                f"Directory could not be listed ({exc}); its contents were not "
                f"examined, so this bundle has not been fully verified.",
                owasp="AST08",
            ))
            continue

        for entry in entries:
            entry_path = Path(entry.path)
            rel = _rel(root, entry_path)

            if entry.is_symlink():
                if len(files) >= MAX_FILES:
                    truncated = True
                    continue
                escapes, raw = _link_escapes(root, entry_path)
                item = BundleFile(entry_path, rel)
                item.is_symlink = True
                item.link_target = raw
                item.escapes_root = escapes
                item.klass = "symlink"
                files.append(item)
                continue

            if entry.is_dir(follow_symlinks=False):
                if entry.name == ".git":
                    # Object storage would exhaust the file ceiling and says
                    # nothing. The two things inside .git that execute are
                    # inspected directly instead.
                    findings.extend(inspect_git_dir(entry_path, f"{rel}/"))
                    continue
                try:
                    stat = entry.stat(follow_symlinks=False)
                    key = (stat.st_dev, stat.st_ino)
                except OSError:
                    key = None
                if key is not None:
                    if key in seen_dirs:
                        continue
                    seen_dirs.add(key)
                stack.append(entry_path)
                continue

            if not entry.is_file(follow_symlinks=False):
                if len(files) >= MAX_FILES:
                    truncated = True
                    continue
                item = BundleFile(entry_path, rel)
                item.klass = "special"
                files.append(item)
                continue

            if len(files) >= MAX_FILES:
                truncated = True
                continue

            item = BundleFile(entry_path, rel)
            try:
                item.size = entry.stat(follow_symlinks=False).st_size
            except OSError as exc:
                item.read_error = str(exc)
                item.klass = "unknown"
                files.append(item)
                continue

            total_bytes += item.size
            if total_bytes > MAX_TOTAL_BYTES:
                truncated = True
                continue

            _load_file(item)
            files.append(item)

    files.sort(key=lambda f: f.rel)

    if truncated:
        findings.append(finding(
            "EXT-BUNDLE-TRUNCATED", "CRITICAL", ".",
            f"The bundle exceeds this tool's analysis ceiling "
            f"({MAX_FILES} files / {MAX_TOTAL_BYTES // (1024 * 1024)} MiB) and "
            f"was only partially examined. A partial scan of an untrusted "
            f"bundle establishes nothing. Split it, or review it by hand.",
            owasp="AST08",
        ))

    return files, findings


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:  # pragma: no cover - defensive
        return path.as_posix()


def _load_file(item: BundleFile) -> None:
    """Read, hash, and classify one file, tolerating every failure mode."""
    suffix = item.path.suffix.lower()

    if item.size > MAX_READ_BYTES:
        item.truncated = True
        item.klass = classify(item.rel, suffix, is_text=False)
        try:
            digest = hashlib.sha256()
            with open(item.path, "rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            item.sha256 = digest.hexdigest()
        except OSError as exc:
            item.read_error = str(exc)
        return

    try:
        raw = item.path.read_bytes()
    except OSError as exc:
        item.read_error = str(exc)
        item.klass = classify(item.rel, suffix, is_text=False)
        return

    item.sha256 = hashlib.sha256(raw).hexdigest()

    is_text = False
    if not _looks_binary(raw[:8192]):
        try:
            item.text = raw.decode("utf-8")
            is_text = True
        except UnicodeDecodeError:
            item.text = None

    item.klass = classify(item.rel, suffix, is_text)


# ---------------------------------------------------------------------------
# Bundle digest
#
# The same construction scripts/skill_digest.py uses, with one deliberate
# difference: attestation.json is included. That file is excluded there
# because the digest is stored inside it. Here the bundle belongs to someone
# else, nothing is written back, and a changed attestation is exactly the
# kind of change re-verification must notice.
# ---------------------------------------------------------------------------

def build_manifest(files: Iterable[BundleFile]) -> str:
    """The canonical text the bundle digest is taken over."""
    lines = []
    for item in sorted(files, key=lambda f: f.rel):
        if item.klass == "symlink":
            marker = f"symlink:{item.link_target or ''}"
            lines.append(f"{item.rel}  {hashlib.sha256(marker.encode('utf-8')).hexdigest()}")
        elif item.sha256:
            lines.append(f"{item.rel}  {item.sha256}")
        else:
            lines.append(f"{item.rel}  unreadable")
    return "\n".join(lines) + "\n"


def compute_bundle_digest(files: Iterable[BundleFile]) -> str:
    return "sha256:" + hashlib.sha256(build_manifest(files).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Text surface
#
# Two tiers, because a heuristic tuned for prose produces noise when pointed
# at code, and a noisy scanner gets switched off.
#
#   objective  -- run on every text file. These match constructs that have no
#                 benign reading anywhere: invisible Unicode, bidi overrides,
#                 encoded blobs, pipe-to-shell, evasion-scale formatting.
#   prose      -- run only on files that reach the model as instructions.
#                 These are judgement calls ("this sentence tells the agent to
#                 read your keys"), and judgement calls about English do not
#                 survive contact with a secret-scanning script's regexes.
# ---------------------------------------------------------------------------

def decode_tag_characters(line: str) -> str:
    """
    Recover the text hidden in a Unicode Tags run.

    The Tags block mirrors printable ASCII at an offset, so a smuggled
    instruction can be read back exactly. Showing the reviewer the sentence
    that was hidden is worth far more than telling them a code point was
    present, and it removes the guesswork about whether a hit is meaningful.
    """
    out = []
    for ch in line:
        cp = ord(ch)
        if 0xE0020 <= cp <= 0xE007E:
            out.append(chr(cp - 0xE0000))
    return "".join(out)


def _scan_line_characters(line: str, idx: int, rel: str) -> List[Dict[str, Any]]:
    """
    Report one finding per line per category, not one per character.

    A smuggled sentence is one attack, and emitting a finding for each of its
    characters buries every other finding in the report under it. The reader
    has to get through this output; forty identical lines is a failure of the
    tool, not thoroughness.
    """
    out: List[Dict[str, Any]] = []

    tags = [ch for ch in line if is_tag_char(ord(ch))]
    if tags:
        hidden = decode_tag_characters(line)
        readable = f" It decodes to: {hidden!r}." if hidden else ""
        out.append(finding(
            "EXT-INVISIBLE-UNICODE", "CRITICAL", rel,
            f"{len(tags)} Unicode Tag characters at line {idx}. This block "
            f"renders as nothing at all and is the standard carrier for an "
            f"instruction smuggled past a human reviewer.{readable}",
            idx, f"tags:{hidden or len(tags)}", owasp="AST05",
        ))

    bidi = [ch for ch in line if ord(ch) in BIDI_CHARS]
    if bidi:
        names = sorted({BIDI_CHARS[ord(ch)] for ch in bidi})
        out.append(finding(
            "EXT-BIDI-CONTROL", "CRITICAL", rel,
            f"{len(bidi)} bidirectional control character(s) at line {idx} "
            f"({', '.join(names)}). Text can render in a different order than "
            f"it is parsed, so what you read is not what runs.",
            idx, f"bidi:{','.join(names)}", owasp="AST05",
        ))

    invisible = [ch for ch in line if ord(ch) in INVISIBLE_CHARS]
    if invisible:
        names = sorted({INVISIBLE_CHARS[ord(ch)] for ch in invisible})
        out.append(finding(
            "EXT-INVISIBLE-UNICODE", "HIGH", rel,
            f"{len(invisible)} invisible character(s) at line {idx} "
            f"({', '.join(names)}).",
            idx, f"invisible:{','.join(names)}", owasp="AST05",
        ))

    return out


def scan_text_objective(text: str, rel: str) -> List[Dict[str, Any]]:
    """Constructs with no legitimate use in any file of a skill bundle."""
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        out.extend(_scan_line_characters(line, idx, rel))

        if len(line) > MAX_LINE_CHARS:
            out.append(finding(
                "EXT-LONG-LINE", "HIGH", rel,
                f"Line {idx} is {len(line)} characters long. Content this far "
                f"along a single line is past where a reviewer scrolls and past "
                f"where several scanners stop reading -- a documented evasion.",
                idx, line[:200], owasp="AST08",
            ))

    for match in B64_BLOB_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        out.append(finding(
            "EXT-ENCODED-BLOB", "HIGH", rel,
            f"{len(match.group(0))}-character base64-like blob at line "
            f"{line_no}. Encoded content cannot be reviewed, which is the "
            f"point of encoding it.",
            line_no, match.group(0)[:120], owasp="AST01",
        ))

    for match in PIPE_TO_SHELL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        out.append(finding(
            "EXT-PIPE-TO-SHELL", "CRITICAL", rel,
            f"Download-and-execute one-liner at line {line_no}: "
            f"{match.group(0).strip()!r}. This runs code that was never "
            f"reviewed, from a server that can serve different code tomorrow.",
            line_no, match.group(0), owasp="AST02",
        ))

    out.extend(_scan_inflation(text, rel))
    return out


def _scan_inflation(text: str, rel: str) -> List[Dict[str, Any]]:
    """
    Detect padding used to push content past a scanner's context window.

    Two independent signals: one very long run of whitespace, or a large file
    that is mostly whitespace. Either shape is how a payload gets separated
    from the part of the file a truncating scanner reads.
    """
    out: List[Dict[str, Any]] = []

    longest = 0
    run = 0
    at = 0
    for index, ch in enumerate(text):
        if ch.isspace():
            run += 1
            if run > longest:
                longest = run
                at = index - run + 1
        else:
            run = 0
    if longest > MAX_WHITESPACE_RUN:
        line_no = text.count("\n", 0, at) + 1
        out.append(finding(
            "EXT-WHITESPACE-INFLATION", "HIGH", rel,
            f"An unbroken run of {longest} whitespace characters begins at line "
            f"{line_no}. Padding at this scale has no formatting purpose; it is "
            f"used to push what follows beyond a scanner's reading limit.",
            line_no, owasp="AST08",
        ))

    if len(text) >= INFLATION_MIN_BYTES:
        whitespace = sum(1 for ch in text if ch.isspace())
        ratio = whitespace / len(text)
        if ratio > INFLATION_RATIO:
            out.append(finding(
                "EXT-WHITESPACE-INFLATION", "HIGH", rel,
                f"File is {len(text)} characters and {ratio:.0%} whitespace. "
                f"A file this size that is mostly padding is shaped to exhaust "
                f"a reviewer or a scanner rather than to be read.",
                owasp="AST08",
            ))
    return out


def scan_text_prose(text: str, rel: str) -> List[Dict[str, Any]]:
    """
    Judgement-call checks, run only on files that become agent instructions.

    Everything here is a heuristic that reports something for a human to
    read, never a determination that the bundle is malicious.
    """
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()

    for match in re.finditer(r"<!--(.*?)-->", text, re.DOTALL):
        body = match.group(1)
        line_no = text.count("\n", 0, match.start()) + 1
        if HIDDEN_DIRECTIVE_RE.search(body):
            out.append(finding(
                "EXT-HIDDEN-DIRECTIVE", "CRITICAL", rel,
                f"HTML comment at line {line_no} contains instruction-shaped "
                f"language. It is invisible in rendered Markdown and fully "
                f"visible to the agent reading the raw file.",
                line_no, body[:200], owasp="AST05",
            ))
        else:
            out.append(finding(
                "EXT-HTML-COMMENT", "INFO", rel,
                f"HTML comment at line {line_no} (no directive language "
                f"detected). Listed because comments are invisible when "
                f"rendered and are worth eyeballing in a stranger's skill.",
                line_no, body[:200], owasp="AST05",
            ))

    for idx, line in enumerate(lines, start=1):
        if not SENSITIVE_TOKEN_RE.search(line):
            continue
        lo = max(0, idx - 1 - EXFIL_WINDOW)
        hi = min(len(lines), idx + EXFIL_WINDOW)
        verb = EXFIL_VERB_RE.search("\n".join(lines[lo:hi]))
        if verb:
            out.append(finding(
                "EXT-CREDENTIAL-EXFIL", "CRITICAL", rel,
                f"Line {idx} names a credential or secret artefact within "
                f"{EXFIL_WINDOW} lines of a way to move data off the machine "
                f"({verb.group(0).strip()!r}). Confirm this is documentation "
                f"and not an instruction the agent will follow.",
                idx, line, owasp="AST01",
            ))
    return out


def scan_shell_like(text: str, rel: str) -> List[Dict[str, Any]]:
    """
    Pattern scan for shell and shell-adjacent code.

    Pattern matching is a weaker instrument than the AST walk used on Python,
    and this function does not pretend otherwise -- every non-Python
    executable also earns an EXT-UNVERIFIABLE-CODE finding saying so.
    """
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()
    for label, severity, pattern in SHELL_DANGER_PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = lines[line_no - 1] if line_no <= len(lines) else ""
            out.append(finding(
                "EXT-SHELL-DANGER", severity, rel,
                f"Shell construct '{label}' at line {line_no}: "
                f"{match.group(0).strip()[:120]!r}.",
                line_no, line, owasp="AST01",
            ))
    return out


def scan_obfuscation(text: str, rel: str) -> List[Dict[str, Any]]:
    """Encoding helpers, wherever they appear."""
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()
    for label, pattern in OBFUSCATION_PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            snippet = lines[line_no - 1] if line_no <= len(lines) else match.group(0)
            out.append(finding(
                "EXT-OBFUSCATION", "HIGH", rel,
                f"Obfuscation smell '{label}' at line {line_no}. A skill has no "
                f"routine need to decode a payload at runtime, and encoded "
                f"content defeats the review you are trying to perform.",
                line_no, snippet, owasp="AST01",
            ))
    return out


def extract_destinations(text: str) -> Set[str]:
    """Every network host named anywhere in the bundle's text."""
    return {match.group(1).lower() for match in URL_RE.finditer(text)}


# ---------------------------------------------------------------------------
# Python surface
#
# Capabilities are derived from the AST rather than from text search. A
# `subprocess.run(...)` call cannot hide from an AST walk the way it can hide
# from a skim of a 2000-line file, and unlike a regex the walk is not fooled
# by the word appearing inside a string or a comment.
# ---------------------------------------------------------------------------

# Modules that ship with the interpreter. Every other import comes from
# outside the bundle, and a static reader cannot see what it does: the AST has
# the name `requests_oauthlib`, not the socket inside it. Mirrors
# scripts/audit_skill_safety.py, which must never catch something this misses.
STDLIB_MODULES: Set[str] = set(getattr(sys, "stdlib_module_names", ()))


def bundle_module_names(rels: List[str]) -> Set[str]:
    """Module names a bundle can import from its own files.

    `from connections import x` beside connections.py is local source, which is
    itself in scope for this scan, not an unreviewable dependency.
    """
    names: Set[str] = set()
    for rel in rels:
        path = PurePosixPath(rel)
        if path.suffix == ".py":
            names.add(path.stem)
            if path.stem == "__init__" and path.parent.name:
                names.add(path.parent.name)
    return names


def is_unprovable_import(root: str, local_modules: Set[str]) -> bool:
    """True for an import whose capabilities cannot be derived from this source."""
    if root in NETWORK_MODULES or root in PROCESS_MODULES or root in DYNAMIC_MODULES:
        return False
    if root in STDLIB_MODULES or root in local_modules:
        return False
    return bool(STDLIB_MODULES)


def _module_roots_with_lines(tree: ast.AST) -> Dict[str, int]:
    """Top-level module name -> the first line it is imported on."""
    roots: Dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.setdefault(alias.name.split(".")[0], node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module and not node.level:
                roots.setdefault(node.module.split(".")[0], node.lineno)
    return roots


def _module_roots(tree: ast.AST) -> Set[str]:
    roots: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and not node.level:
                roots.add(node.module.split(".")[0])
    return roots


def _open_is_writable(node: ast.Call) -> bool:
    """True when an `open(...)` call requests a write, append or create mode."""
    mode: Optional[str] = None
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        if isinstance(node.args[1].value, str):
            mode = node.args[1].value
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            if isinstance(keyword.value.value, str):
                mode = keyword.value.value
    return bool(mode) and any(ch in mode for ch in "wax+")


def observe_python(text: str, rel: str,
                   local_modules: Set[str] = frozenset(),
                   ) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """Return (observed capabilities, findings) for one Python source file."""
    observed = dict(DEFAULT_DECLARATION)
    out: List[Dict[str, Any]] = []

    try:
        tree = ast.parse(text, filename=rel)
    except (SyntaxError, ValueError, RecursionError) as exc:
        out.append(finding(
            "EXT-PY-UNPARSEABLE", "HIGH", rel,
            f"File has a .py extension but does not parse as Python ({exc}). "
            f"Its behaviour cannot be verified, and a file that defeats the "
            f"parser also defeats every tool that depends on one.",
            getattr(exc, "lineno", None), owasp="AST08",
        ))
        return observed, out

    def raise_to(cap: str, level: str) -> None:
        ladder = CAPABILITY_LADDERS[cap]
        if ladder.index(level) > ladder.index(observed[cap]):
            observed[cap] = level

    evidence: List[Dict[str, Any]] = []

    for root, lineno in sorted(_module_roots_with_lines(tree).items()):
        if root in NETWORK_MODULES:
            raise_to("network", "outbound")
            evidence.append(finding("EXT-CAPABILITY", "INFO", rel,
                                    f"imports '{root}' -> network: outbound"))
        if root in PROCESS_MODULES:
            raise_to("process_execution", "subprocess")
            evidence.append(finding("EXT-CAPABILITY", "INFO", rel,
                                    f"imports '{root}' -> process_execution: subprocess"))
        if root in DYNAMIC_MODULES:
            raise_to("dynamic_code_execution", "eval")
            evidence.append(finding("EXT-CAPABILITY", "INFO", rel,
                                    f"imports '{root}' -> dynamic_code_execution: eval"))
        if is_unprovable_import(root, local_modules):
            out.append(finding(
                "EXT-CAP-UNPROVEN", "HIGH", rel,
                f"imports '{root}', which is not in the standard library, not a "
                f"file in this bundle, and not a module this tool has capability "
                f"rules for. The capability summary above therefore does not "
                f"cover it: whatever '{root}' does when called, this skill does. "
                f"Installing the skill also installs that dependency, which "
                f"nothing here has read. Establish what it is before installing.",
                lineno, owasp="AST01",
            ))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            if node.func.id in DYNAMIC_BUILTINS:
                raise_to("dynamic_code_execution", "eval")
                evidence.append(finding(
                    "EXT-CAPABILITY", "INFO", rel,
                    f"calls builtin '{node.func.id}()' -> dynamic_code_execution: eval",
                    node.lineno))
            elif node.func.id == "open" and _open_is_writable(node):
                raise_to("filesystem", "workspace-write")
                evidence.append(finding(
                    "EXT-CAPABILITY", "INFO", rel,
                    "calls open() in a write mode -> filesystem: workspace-write",
                    node.lineno))
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in PROCESS_ATTRS:
                raise_to("process_execution", "subprocess")
                evidence.append(finding(
                    "EXT-CAPABILITY", "INFO", rel,
                    f"calls '.{attr}()' -> process_execution: subprocess", node.lineno))
            elif attr in FS_DELETE_ATTRS:
                raise_to("filesystem", "workspace-delete")
                evidence.append(finding(
                    "EXT-CAPABILITY", "INFO", rel,
                    f"calls '.{attr}()' -> filesystem: workspace-delete", node.lineno))
            elif attr in FS_WRITE_ATTRS:
                raise_to("filesystem", "workspace-write")
                evidence.append(finding(
                    "EXT-CAPABILITY", "INFO", rel,
                    f"calls '.{attr}()' -> filesystem: workspace-write", node.lineno))

    out.extend(evidence)
    return observed, out


def merge_observed(into: Dict[str, str], other: Dict[str, str]) -> None:
    for cap, ladder in CAPABILITY_LADDERS.items():
        if ladder.index(other[cap]) > ladder.index(into[cap]):
            into[cap] = other[cap]


def _init_is_declarative(text: str) -> Tuple[bool, Optional[int]]:
    """
    True when an __init__.py only declares things.

    An __init__.py runs on import. One containing only imports, a docstring
    and simple constant assignments has no side effects worth flagging; one
    containing a call at module level runs that call in every process that
    imports the package, which is a different thing entirely.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return False, None

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef, ast.Pass)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            # Both halves have to be inert. `os.environ["X"] = "1"` assigns a
            # constant, but its target mutates another module's state at
            # import time, which is a side effect however simple the value is.
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not all(isinstance(target, ast.Name) for target in targets):
                return False, getattr(node, "lineno", None)
            value = getattr(node, "value", None)
            if value is None or isinstance(value, (ast.Constant, ast.List,
                                                   ast.Tuple, ast.Set, ast.Dict,
                                                   ast.Name, ast.Attribute)):
                continue
        if isinstance(node, ast.If):
            test = node.test
            # `if TYPE_CHECKING:` and `if __name__ == "__main__":` are inert
            # at import time in the ways that matter here.
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                continue
        return False, getattr(node, "lineno", None)
    return True, None


# ---------------------------------------------------------------------------
# Files that run without being invoked
#
# The severity here is graded rather than fixed. A conftest.py is ordinary in
# any bundle that ships tests; a conftest.py that opens a socket is the
# documented attack. Flagging the first as CRITICAL would make the tool
# useless on well-tested skills, and a tool people mute protects nobody.
# ---------------------------------------------------------------------------

def _autorun_severity(observed: Dict[str, str], declarative: bool,
                      clean_severity: str = "WARN") -> Tuple[str, str]:
    """
    Grade an auto-executing Python file by what its code can actually do.

    `clean_severity` is what an inert file scores. Shipping tests is ordinary,
    so a clean test file is INFO; a conftest.py exists only to be imported and
    stays WARN. Neither judgement changes the escalation, which is the part
    that catches the attack.
    """
    powers = [cap for cap, level in observed.items()
              if CAPABILITY_LADDERS[cap].index(level) > 0]
    if powers:
        return "CRITICAL", (
            f"and its top-level code carries capabilities it never has to "
            f"declare to anyone: {', '.join(f'{c}={observed[c]}' for c in sorted(powers))}"
        )
    if not declarative:
        return "HIGH", "and it runs statements at import time, not just definitions"
    return clean_severity, "though it only declares imports and constants at import time"


def scan_autorun(item: BundleFile, observed: Dict[str, str]) -> List[Dict[str, Any]]:
    """Findings for files the runtime loads on its own initiative."""
    out: List[Dict[str, Any]] = []
    name = item.rel.rsplit("/", 1)[-1]
    text = item.text or ""

    if name in AUTORUN_BASENAMES and item.klass == "python":
        declarative, offending_line = _init_is_declarative(text)
        severity, qualifier = _autorun_severity(observed, declarative)
        out.append(finding(
            "EXT-AUTORUN", severity, item.rel,
            f"{AUTORUN_BASENAMES[name]} Nothing in SKILL.md needs to reference "
            f"this file for it to execute, {qualifier}.",
            offending_line, owasp="AST01",
        ))

    if (item.klass == "python" and name not in AUTORUN_BASENAMES
            and is_convention_discovered_test(item.rel)):
        declarative, offending_line = _init_is_declarative(text)
        severity, qualifier = _autorun_severity(observed, declarative,
                                                clean_severity="INFO")
        out.append(finding(
            "EXT-AUTORUN", severity, item.rel,
            f"pytest collects this file by naming convention, so its top-level "
            f"code runs for anyone who runs the test suite -- including CI, on "
            f"every branch and every fork -- without SKILL.md ever mentioning "
            f"it, {qualifier}.",
            offending_line, owasp="AST01",
        ))

    if name == "__init__.py" and item.klass == "python":
        declarative, offending_line = _init_is_declarative(text)
        if not declarative:
            severity, qualifier = _autorun_severity(observed, declarative)
            out.append(finding(
                "EXT-AUTORUN", severity, item.rel,
                f"__init__.py runs statements at import time rather than only "
                f"declaring names, so importing anything from this package "
                f"executes them -- {qualifier}.",
                offending_line, owasp="AST01",
            ))

    if item.rel.endswith(".pth"):
        executable = [i for i, line in enumerate(text.splitlines(), start=1)
                      if line.startswith(("import ", "import\t"))]
        if executable:
            out.append(finding(
                "EXT-AUTORUN", "CRITICAL", item.rel,
                f"A .pth file whose line {executable[0]} begins with 'import' is "
                f"executed by Python's site module at interpreter startup, "
                f"before any program runs. This is a persistence mechanism, not "
                f"a packaging convenience.",
                executable[0], owasp="AST01",
            ))
        else:
            out.append(finding(
                "EXT-AUTORUN", "WARN", item.rel,
                ".pth files are read by Python's site module at startup. This "
                "one contains no 'import' line, so it only extends sys.path.",
                owasp="AST01",
            ))

    if name == "package.json" and text:
        out.extend(_scan_npm_lifecycle(text, item.rel))

    if name in ("settings.json", "settings.local.json") and text:
        out.extend(_scan_agent_hooks(text, item.rel))

    return out


def _scan_npm_lifecycle(text: str, rel: str) -> List[Dict[str, Any]]:
    """npm runs these scripts during `npm install`, before anyone reads them."""
    out: List[Dict[str, Any]] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return out
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return out
    for key in NPM_LIFECYCLE_KEYS:
        command = scripts.get(key)
        if not isinstance(command, str):
            continue
        severity = "CRITICAL" if PIPE_TO_SHELL_RE.search(command) else "HIGH"
        out.append(finding(
            "EXT-AUTORUN", severity, rel,
            f"package.json defines the npm lifecycle script {key!r}: "
            f"{command[:200]!r}. npm executes it during installation, before "
            f"anybody has read the package.",
            snippet=command, owasp="AST01",
        ))
    return out


def _scan_agent_hooks(text: str, rel: str) -> List[Dict[str, Any]]:
    """
    Agent hook settings shipped inside a skill bundle.

    A hook is a command the agent runs on its own schedule -- on session
    start, before a tool call, after an edit. A skill that ships one is
    asking for code execution that no SKILL.md instruction has to mention
    and that no prompt-reading scanner will find.
    """
    if "/.claude/" not in f"/{rel}" and not rel.startswith(".claude/"):
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict) or "hooks" not in data:
        return []
    return [finding(
        "EXT-AGENT-HOOKS", "CRITICAL", rel,
        "This bundle ships agent hook settings. Hooks are commands the agent "
        "executes on its own events, independently of anything SKILL.md says, "
        "so installing this skill grants command execution that reading "
        "SKILL.md would never reveal.",
        snippet=json.dumps(data.get("hooks"), sort_keys=True)[:400], owasp="AST01",
    )]


def inspect_git_dir(git_dir: Path, rel_prefix: str) -> List[Dict[str, Any]]:
    """
    Inspect a .git directory without walking it.

    Object storage is uninteresting and would exhaust the file ceiling, but
    two things inside .git execute: an active hook, and a config key that
    names a command git will run.
    """
    out: List[Dict[str, Any]] = []

    hooks = git_dir / "hooks"
    if hooks.is_dir():
        try:
            names = sorted(entry.name for entry in os.scandir(hooks)
                           if entry.is_file(follow_symlinks=False))
        except OSError:
            names = []
        for name in names:
            if name.endswith(".sample"):
                continue
            out.append(finding(
                "EXT-GIT-HOOK", "CRITICAL", f"{rel_prefix}hooks/{name}",
                f"An active git hook is present. Git executes {name} on the "
                f"matching git operation, on the machine of anyone who uses "
                f"this working copy. Git does not transmit hooks on clone, so "
                f"a hook shipped inside a bundle was put there deliberately.",
                owasp="AST01",
            ))

    config = git_dir / "config"
    if config.is_file():
        try:
            text = config.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for key in ("fsmonitor", "sshCommand", "pager", "editor",
                    "askpass", "hooksPath"):
            match = re.search(rf"^\s*{key}\s*=\s*(.+)$", text,
                              re.IGNORECASE | re.MULTILINE)
            if match:
                out.append(finding(
                    "EXT-GIT-CONFIG-EXEC", "CRITICAL", f"{rel_prefix}config",
                    f"git config sets {key} = {match.group(1).strip()[:160]!r}. "
                    f"Git runs the value of this key as a command during "
                    f"ordinary git operations.",
                    snippet=match.group(0), owasp="AST01",
                ))
    return out


# ---------------------------------------------------------------------------
# Reference graph
#
# The headline check. Published research bypassed eight scanners by putting
# the payload in a file nothing points at, because every one of those
# scanners reads SKILL.md and follows what SKILL.md mentions. A file that
# nothing mentions, yet which the runtime will happily execute, is the shape
# of that entire attack class.
#
# The test is deliberately generous about what counts as a reference: a
# false "unreferenced" claim on an ordinary skill would teach the user to
# ignore this check, which costs more than the check is worth.
# ---------------------------------------------------------------------------

def is_referenced(candidate: BundleFile, files: List[BundleFile]) -> bool:
    """True when any other text file in the bundle mentions this one."""
    name = candidate.rel.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    import_re = re.compile(rf"(?:^|\s)(?:import|from)\s+[\w.]*\b{re.escape(stem)}\b")
    require_re = re.compile(rf"""(?:require|import)\s*\(?\s*['"][^'"]*{re.escape(stem)}""")

    for other in files:
        if other.rel == candidate.rel or not other.text:
            continue
        text = other.text
        if candidate.rel in text or name in text:
            return True
        if candidate.klass == "python" and import_re.search(text):
            return True
        if candidate.klass == "other-code" and require_re.search(text):
            return True
    return False


def scan_reference_graph(files: List[BundleFile]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in files:
        if item.klass not in CODE_CLASSES:
            continue
        name = item.rel.rsplit("/", 1)[-1]
        if (name in AUTORUN_BASENAMES or name == "__init__.py"
                or item.rel.endswith(".pth")
                or is_convention_discovered_test(item.rel)):
            # Already graded as autorun. Being unreferenced is how these files
            # are found at all, so reporting it too would be noise that teaches
            # the reader to skip the check that matters.
            continue
        if is_referenced(item, files):
            continue
        out.append(finding(
            "EXT-UNREFERENCED-EXECUTABLE", "HIGH", item.rel,
            f"This bundle contains executable code that no other file in the "
            f"bundle mentions by name. Reading SKILL.md would never lead a "
            f"reviewer here, which is precisely how payloads have been shipped "
            f"past scanners that only follow what SKILL.md points at. Establish "
            f"why it is here before installing.",
            owasp="AST01",
        ))
    return out


# ---------------------------------------------------------------------------
# Structure and metadata
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Read the top-level scalar keys of a SKILL.md frontmatter block.

    A minimal reader on purpose: no YAML library is available in a stdlib-only
    tool, and a partial parse is honest here because every value it returns is
    reported to a human rather than acted on. Anything it cannot parse is
    reported as unparseable rather than silently treated as absent.
    """
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return None, "no frontmatter block delimited by '---' at the top of the file"

    body = match.group(1)
    data: Dict[str, Any] = {}
    key: Optional[str] = None

    for raw_line in body.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        list_item = re.match(r"^\s+-\s+(.*)$", raw_line)
        if list_item and key:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(list_item.group(1).strip().strip("'\""))
            continue
        pair = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", raw_line)
        if pair:
            key = pair.group(1)
            value = pair.group(2).strip()
            if value in ("", "|", ">", "|-", ">-"):
                data[key] = [] if value == "" else ""
            else:
                data[key] = value.strip("'\"")
            continue
        if key and isinstance(data.get(key), str):
            data[key] = f"{data[key]} {raw_line.strip()}".strip()

    return data, None


def scan_metadata(skill_md: Optional[BundleFile], bundle_name: str) -> List[Dict[str, Any]]:
    """Checks on the frontmatter, which is what makes a skill load at all."""
    out: List[Dict[str, Any]] = []
    if skill_md is None or not skill_md.text:
        return out

    data, error = parse_frontmatter(skill_md.text)
    if error:
        out.append(finding(
            "EXT-METADATA-UNPARSEABLE", "HIGH", skill_md.rel,
            f"SKILL.md frontmatter could not be read: {error}. An agent that "
            f"parses it differently than a reviewer does is the gap this check "
            f"exists to close.",
            owasp="AST04",
        ))
        return out

    name = data.get("name")
    if isinstance(name, str) and name and name != bundle_name:
        out.append(finding(
            "EXT-METADATA-NAME-MISMATCH", "WARN", skill_md.rel,
            f"Frontmatter declares name {name!r} but the directory is "
            f"{bundle_name!r}. Installing under one name while presenting as "
            f"another is how a skill ends up shadowing one you trust.",
            owasp="AST04",
        ))

    description = data.get("description")
    if isinstance(description, str) and description:
        if HIDDEN_DIRECTIVE_RE.search(description):
            out.append(finding(
                "EXT-TRIGGER-ABUSE", "CRITICAL", skill_md.rel,
                "The frontmatter description contains instruction-shaped "
                "language. Descriptions are loaded into the agent's context "
                "for every skill, all the time, whether or not the skill is "
                "ever invoked -- it is the cheapest place in the system to "
                "put an instruction.",
                snippet=description[:300], owasp="AST04",
            ))
        if len(description) > 1024:
            out.append(finding(
                "EXT-METADATA-OVERSIZE", "WARN", skill_md.rel,
                f"Description is {len(description)} characters. Long "
                f"descriptions occupy context permanently and give more room "
                f"to hide an instruction in.",
                owasp="AST04",
            ))

    tools = data.get("allowed-tools") or data.get("allowed_tools")
    if tools:
        out.extend(_scan_tool_grants(tools, skill_md.rel))
    return out


def _normalise_tool(entry: str) -> str:
    """`Bash(git status:*)` and `  bash ` both reduce to `bash`."""
    return entry.strip().strip("'\"").split("(")[0].strip().lower()


def _scan_tool_grants(tools: Any, rel: str) -> List[Dict[str, Any]]:
    """
    Report what installing the skill actually grants it.

    Requesting tools is normal and is reported as INFO. The WARN is reserved
    for the grants that turn a skill from something that advises into
    something that acts, because a check that fires on every skill is a check
    people learn to scroll past.
    """
    out: List[Dict[str, Any]] = []
    entries = tools if isinstance(tools, list) else [
        part for part in re.split(r"[,\n]", str(tools).strip("[]")) if part.strip()
    ]
    names = [_normalise_tool(entry) for entry in entries if _normalise_tool(entry)]
    if not names:
        return out

    granted: Dict[str, List[str]] = {}
    wildcard = [name for name in names if name in ("*", "all", "any")]
    for name in names:
        for category, vocabulary in TOOL_GRANTS.items():
            if name in vocabulary:
                granted.setdefault(category, []).append(name)

    out.append(finding(
        "EXT-TOOL-GRANT", "INFO", rel,
        f"The skill requests {len(names)} tool(s): {', '.join(sorted(set(names)))}. "
        f"Installing it grants these for anything it decides to do.",
        snippet=", ".join(sorted(set(names))), owasp="AST03",
    ))

    if wildcard:
        out.append(finding(
            "EXT-OVER-PRIVILEGE", "HIGH", rel,
            "The skill requests every tool by wildcard. A wildcard grant means "
            "no reading of SKILL.md can tell you what the skill may do, because "
            "the answer is 'anything the agent can do'.",
            snippet=", ".join(sorted(set(names))), owasp="AST03",
        ))
        return out

    escalating = sorted(set(granted) & ESCALATING_GRANTS)
    if escalating:
        detail = "; ".join(
            f"{category} via {', '.join(sorted(set(granted[category])))}"
            for category in escalating
        )
        out.append(finding(
            "EXT-OVER-PRIVILEGE", "WARN", rel,
            f"Installing this skill grants it {detail}. That is what separates "
            f"a skill that can only give the agent bad advice from one that can "
            f"act on your machine. Confirm each is needed for what the skill "
            f"claims to be for.",
            snippet=detail, owasp="AST03",
        ))
    return out


def read_declaration(attestation: Optional[BundleFile]
                     ) -> Tuple[Optional[Dict[str, str]], List[Dict[str, Any]]]:
    """
    Read a capability declaration if the bundle carries one.

    Most third-party skills carry none, and that is reported as a fact about
    what cannot be checked rather than as a defect: an absent declaration is
    normal outside this repository, and treating it as a failure would make
    the verdict meaningless.
    """
    out: List[Dict[str, Any]] = []
    if attestation is None or not attestation.text:
        out.append(finding(
            "EXT-NO-DECLARATION", "INFO", "attestation.json",
            "The bundle declares no capabilities, so there is nothing to hold "
            "its code against. The capabilities reported below were derived "
            "from the code itself and are the only account you have of what "
            "this skill can do.",
            owasp="AST04",
        ))
        return None, out

    try:
        data = json.loads(attestation.text)
    except json.JSONDecodeError as exc:
        out.append(finding(
            "EXT-DECLARATION-MALFORMED", "WARN", attestation.rel,
            f"attestation.json is present but unreadable ({exc}), so its claims "
            f"cannot be checked against the code.",
            owasp="AST04",
        ))
        return None, out

    raw = data.get("capabilities") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        out.append(finding(
            "EXT-NO-DECLARATION", "INFO", attestation.rel,
            "attestation.json carries no 'capabilities' object, so the file "
            "attests to nothing this tool can verify.",
            owasp="AST04",
        ))
        return None, out

    declared = dict(DEFAULT_DECLARATION)
    for cap, ladder in CAPABILITY_LADDERS.items():
        value = raw.get(cap)
        if value is None:
            continue
        if value not in ladder:
            out.append(finding(
                "EXT-DECLARATION-INVALID", "WARN", attestation.rel,
                f"capabilities.{cap} is {value!r}, which is not one of {ladder}. "
                f"Treating it as the most restrictive value.",
                owasp="AST04",
            ))
            continue
        declared[cap] = value
    return declared, out


def compare_capabilities(observed: Dict[str, str], declared: Dict[str, str],
                         rel: str) -> List[Dict[str, Any]]:
    """A declaration the code exceeds is worse than no declaration at all."""
    out: List[Dict[str, Any]] = []
    for cap, ladder in CAPABILITY_LADDERS.items():
        if ladder.index(observed[cap]) > ladder.index(declared[cap]):
            out.append(finding(
                "EXT-CAP-UNDECLARED", "CRITICAL", rel,
                f"The bundle declares '{cap}' as {declared[cap]!r} but its code "
                f"actually has {observed[cap]!r}. A declaration that understates "
                f"the code is not a mistake you can safely assume was innocent: "
                f"it is the document you would have trusted instead of reading.",
                owasp="AST03",
            ))
    return out


# ---------------------------------------------------------------------------
# Per-file structural findings
# ---------------------------------------------------------------------------

def scan_file_class(item: BundleFile) -> List[Dict[str, Any]]:
    """Findings that follow from what a file *is*, before reading it."""
    out: List[Dict[str, Any]] = []

    if item.klass == "symlink":
        if item.escapes_root:
            out.append(finding(
                "EXT-SYMLINK-ESCAPE", "CRITICAL", item.rel,
                f"Symlink pointing outside the bundle, at {item.link_target!r}. "
                f"Whatever reads this bundle reads a file you did not download, "
                f"chosen by whoever wrote the link.",
                snippet=item.link_target, owasp="AST02",
            ))
        else:
            out.append(finding(
                "EXT-SYMLINK", "HIGH", item.rel,
                f"Symlink to {item.link_target!r}. Its target was not followed "
                f"or analysed, so the bytes reached through this path have not "
                f"been verified.",
                snippet=item.link_target, owasp="AST02",
            ))
        return out

    if item.klass == "special":
        out.append(finding(
            "EXT-SPECIAL-FILE", "HIGH", item.rel,
            "Not a regular file (socket, FIFO or device node). Nothing in a "
            "skill bundle has a reason to be one.",
            owasp="AST08",
        ))
        return out

    if item.read_error:
        out.append(finding(
            "EXT-UNREADABLE", "HIGH", item.rel,
            f"Could not be read ({item.read_error}), so it has not been "
            f"verified. An unread file in an untrusted bundle is an unverified "
            f"bundle.",
            owasp="AST08",
        ))
        return out

    if item.klass == "bytecode":
        out.append(finding(
            "EXT-BYTECODE", "CRITICAL", item.rel,
            "Compiled Python bytecode shipped inside the bundle. Python "
            "prefers a .pyc over the .py beside it when the .pyc looks current, "
            "so the code that runs need not be the code you read. Shipping "
            "bytecode is a documented way of getting a payload past a scanner "
            "that reads source.",
            owasp="AST01",
        ))
        return out

    if item.klass == "archive":
        out.append(finding(
            "EXT-NESTED-ARCHIVE", "HIGH", item.rel,
            "An archive inside the bundle. This tool does not extract archives "
            "-- extracting untrusted ones is its own risk -- so its contents "
            "are entirely unverified. Unpack it somewhere isolated and verify "
            "that directory separately.",
            owasp="AST08",
        ))
        return out

    if item.klass == "native":
        out.append(finding(
            "EXT-NATIVE-BINARY", "CRITICAL", item.rel,
            "A native executable or shared library. Nothing about its "
            "behaviour can be established by reading it, and a skill that "
            "needs one is asking for trust no static check can supply.",
            owasp="AST01",
        ))
        return out

    if item.klass == "binary":
        out.append(finding(
            "EXT-OPAQUE-BINARY", "HIGH", item.rel,
            "Not valid UTF-8 text and not a recognised media format, so its "
            "contents cannot be reviewed.",
            owasp="AST08",
        ))
        return out

    if item.truncated:
        out.append(finding(
            "EXT-OVERSIZE-FILE", "HIGH", item.rel,
            f"File is {item.size} bytes, above this tool's {MAX_READ_BYTES}-byte "
            f"read ceiling, and was hashed but not analysed. Files this large in "
            f"a skill bundle are worth explaining.",
            owasp="AST08",
        ))
        return out

    if item.text is None and item.klass in CODE_CLASSES:
        out.append(finding(
            "EXT-UNDECODABLE-CODE", "HIGH", item.rel,
            "Has an executable file extension but is not valid UTF-8, so it "
            "cannot be read as source.",
            owasp="AST08",
        ))
    elif item.text is None and item.klass in ("prose", "text-data"):
        out.append(finding(
            "EXT-UNDECODABLE-TEXT", "HIGH", item.rel,
            "An instruction or data file that is not valid UTF-8. Whatever an "
            "agent makes of these bytes, a reviewer cannot read them, so this "
            "file has not been checked.",
            owasp="AST08",
        ))

    return out


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def verdict_for(findings: List[Dict[str, Any]]) -> str:
    severities = {f["severity"] for f in findings}
    if BLOCKING_SEVERITY in severities:
        return VERDICT_DO_NOT_INSTALL
    if severities & REVIEW_SEVERITIES:
        return VERDICT_NEEDS_REVIEW
    return VERDICT_CLEAN


def verify_bundle(root: Path, expect_digest: Optional[str] = None,
                  now: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify one skill bundle and return a complete, serialisable record.

    Pure with respect to the filesystem: it reads, and returns. Nothing is
    written, fetched, extracted or executed.
    """
    if not root.exists():
        raise ToolError(f"Target does not exist: {root}")
    if not root.is_dir():
        raise ToolError(
            f"Target is not a directory: {root}. Unpack the skill first and "
            f"point this at the unpacked directory -- this tool does not "
            f"extract archives."
        )

    files, findings = enumerate_bundle(root)

    by_rel = {item.rel: item for item in files}
    skill_md = by_rel.get("SKILL.md")
    attestation = by_rel.get("attestation.json")

    if skill_md is None:
        findings.append(finding(
            "EXT-NO-SKILL-MD", "HIGH", ".",
            "No SKILL.md at the top of this directory. Either this is not a "
            "skill bundle, or the skill sits in a subdirectory -- point the "
            "tool at that subdirectory so the whole bundle is in scope.",
            owasp="AST04",
        ))

    observed = dict(DEFAULT_DECLARATION)
    destinations: Set[str] = set()
    counts: Dict[str, int] = {}
    local_modules = bundle_module_names([item.rel for item in files])

    for item in files:
        counts[item.klass] = counts.get(item.klass, 0) + 1
        findings.extend(scan_file_class(item))

        if item.text is None:
            continue

        findings.extend(scan_text_objective(item.text, item.rel))
        destinations |= extract_destinations(item.text)

        if item.klass in ("prose", "text-data") or item.rel == "SKILL.md":
            findings.extend(scan_text_prose(item.text, item.rel))

        file_observed = dict(DEFAULT_DECLARATION)
        if item.klass == "python":
            file_observed, py_findings = observe_python(
                item.text, item.rel, local_modules)
            findings.extend(py_findings)
            findings.extend(scan_obfuscation(item.text, item.rel))
            merge_observed(observed, file_observed)
        elif item.klass in ("shell", "other-code"):
            findings.extend(scan_shell_like(item.text, item.rel))
            findings.extend(scan_obfuscation(item.text, item.rel))
            findings.append(finding(
                "EXT-UNVERIFIABLE-CODE", "HIGH", item.rel,
                f"Executable {CLASS_LABEL.get(item.klass, item.klass)} that this tool "
                f"cannot analyse structurally. Only Python is parsed; "
                f"everything else gets a pattern scan, which is weaker. Read "
                f"this file yourself -- its capabilities are not represented in "
                f"the summary below.",
                owasp="AST08",
            ))

        findings.extend(scan_autorun(item, file_observed))

    findings.extend(scan_reference_graph(files))
    findings.extend(scan_metadata(skill_md, root.name))

    declared, decl_findings = read_declaration(attestation)
    findings.extend(decl_findings)
    if declared is not None:
        findings.extend(compare_capabilities(observed, declared, "attestation.json"))

    if destinations:
        findings.append(finding(
            "EXT-NETWORK-DESTINATION", "INFO", ".",
            f"Hosts named anywhere in this bundle: {', '.join(sorted(destinations))}. "
            f"Naming a host is not sending data to it, but if this skill ever "
            f"reaches the network, these are the addresses it was written near.",
            snippet=",".join(sorted(destinations)),
        ))

    digest = compute_bundle_digest(files)
    if expect_digest:
        expected = expect_digest.strip()
        if expected != digest:
            findings.append(finding(
                "EXT-DIGEST-MISMATCH", "CRITICAL", ".",
                f"The bundle does not match the digest it was verified at "
                f"before. Expected {expected}, found {digest}. Whatever was "
                f"reviewed is not what is on disk now; re-verify from scratch "
                f"and read the diff before installing.",
                owasp="AST02",
            ))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["path"],
                                 f["line"] or 0, f["check"]))

    return {
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION,
                 "ruleset_version": RULESET_VERSION},
        "verified_at": now or datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "bundle": {
            "name": root.name,
            "digest": digest,
            "file_count": len(files),
            "class_counts": dict(sorted(counts.items())),
        },
        "observed_capabilities": observed,
        "declared_capabilities": declared,
        "network_destinations": sorted(destinations),
        "findings": findings,
        "counts": {sev: sum(1 for f in findings if f["severity"] == sev)
                   for sev in SEVERITY_ORDER},
        "verdict": verdict_for(findings),
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

SEVERITY_LABEL = {
    "CRITICAL": "[CRIT]",
    "HIGH": "[HIGH]",
    "WARN": "[WARN]",
    "INFO": "[INFO]",
}

VERDICT_LINE = {
    VERDICT_DO_NOT_INSTALL: (
        "DO NOT INSTALL -- at least one finding has no benign explanation. "
        "Read every [CRIT] line above before going further."
    ),
    VERDICT_NEEDS_REVIEW: (
        "NEEDS REVIEW -- a human has to read the findings above and decide. "
        "This is the normal result for a stranger's skill; it is not an "
        "accusation."
    ),
    VERDICT_CLEAN: (
        "NO KNOWN FINDINGS -- nothing this tool looks for was present. That is "
        "not the same as safe, and this tool will not tell you a bundle is safe."
    ),
}


def _wrap(text: str, width: int, indent: str) -> List[str]:
    """Wrap without importing textwrap, keeping output identical everywhere."""
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) + len(indent) > width and current:
            lines.append(indent + current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(indent + current)
    return lines


def render_report(record: Dict[str, Any], show_info: bool) -> str:
    out: List[str] = []
    bundle = record["bundle"]

    out.append("=" * 78)
    out.append(" [THIRD-PARTY SKILL VERIFICATION] static scan of an untrusted bundle")
    out.append("=" * 78)
    out.append(f" bundle : {bundle['name']}")
    out.append(f" digest : {bundle['digest']}")
    out.append(f" files  : {bundle['file_count']} "
               f"({', '.join(f'{k}={v}' for k, v in bundle['class_counts'].items())})")
    out.append(f" ruleset: {record['tool']['ruleset_version']}  "
               f"verified_at: {record['verified_at']}")

    out.append("")
    out.append(" WHAT THIS SKILL'S CODE CAN DO (derived from the code, not its claims)")
    for cap in CAPABILITY_LADDERS:
        observed = record["observed_capabilities"][cap]
        declared = (record["declared_capabilities"] or {}).get(cap)
        suffix = "" if declared is None else f"   (declared: {declared})"
        marker = " <-- exceeds declaration" if (
            declared is not None
            and CAPABILITY_LADDERS[cap].index(observed) > CAPABILITY_LADDERS[cap].index(declared)
        ) else ""
        out.append(f"   {cap:<24} {observed}{suffix}{marker}")
    if record["declared_capabilities"] is None:
        out.append("   (the bundle declares nothing, so there is nothing to compare against)")
    out.append("   Note: only Python is analysed structurally. Any EXT-UNVERIFIABLE-CODE")
    out.append("   finding below names a file whose capabilities are NOT in this summary.")

    shown = [f for f in record["findings"]
             if show_info or f["severity"] != "INFO"]
    if shown:
        out.append("")
        out.append(" FINDINGS")
        for item in shown:
            location = f"{item['path']}:{item['line']}" if item["line"] else item["path"]
            tag = f" [{item['owasp_ast']}]" if item.get("owasp_ast") else ""
            out.append(f"   {SEVERITY_LABEL[item['severity']]} {item['check']}{tag}  {location}")
            out.extend(_wrap(item["message"], 78, "          "))
    else:
        out.append("")
        out.append(" FINDINGS: none at or above WARN.")

    counts = record["counts"]
    out.append("")
    out.append("-" * 78)
    out.append(f" CRITICAL: {counts['CRITICAL']}   HIGH: {counts['HIGH']}   "
               f"WARN: {counts['WARN']}   INFO: {counts['INFO']}")
    out.append("=" * 78)
    out.extend(_wrap(VERDICT_LINE[record["verdict"]], 78, " "))
    out.append("")
    out.extend(_wrap(DISCLAIMER, 78, " "))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

class _Parser(argparse.ArgumentParser):
    """Usage errors exit 3, so they can never be mistaken for a verdict."""

    def error(self, message: str) -> "None":  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise SystemExit(EXIT_TOOL_ERROR)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=TOOL_NAME,
        description=(
            "Statically verify a downloaded Agent Skill bundle. Reads only; "
            "never fetches, writes, extracts or executes anything."
        ),
    )
    parser.add_argument("target", help="Directory containing the unpacked skill.")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full verification record as JSON. "
                             "Redirect it to keep a dated receipt.")
    parser.add_argument("--expect-digest", default=None,
                        help="Fail if the bundle no longer matches this digest, "
                             "as printed by an earlier run.")
    parser.add_argument("--show-info", action="store_true",
                        help="Include INFO findings (capability evidence, "
                             "HTML comments, network destinations).")
    parser.add_argument("--now", default=None,
                        help="Fixed ISO-8601 timestamp for the record, so a "
                             "verification can be reproduced byte for byte.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover - platform dependent
            pass

    args = build_parser().parse_args(argv)

    try:
        record = verify_bundle(Path(args.target).expanduser(),
                               expect_digest=args.expect_digest, now=args.now)
    except ToolError as exc:
        sys.stderr.write(f"[ERROR] {exc}\n")
        return EXIT_TOOL_ERROR

    if args.json:
        print(json.dumps(record, indent=2, sort_keys=False))
    else:
        print(render_report(record, args.show_info))

    return VERDICT_EXIT[record["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
