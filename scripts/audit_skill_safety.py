#!/usr/bin/env python3
"""
Skill Safety Auditor for 1000x-Agent-Skills.

Answers the one question a stranger cloning this repository actually needs
answered: *can any of these skills do something I would not want?*

A skill has two distinct attack surfaces, and this tool scans both:

  1. Its scripts, which execute on the user's machine. Audited structurally
     via Python's `ast` module -- a `subprocess.run(...)` call cannot hide
     from an AST walk the way it can from a skim-read of a 2000-line file.

  2. Its Markdown, which is injected verbatim into an agent's context and
     becomes instructions the agent follows. This surface is the sneakier
     of the two and is almost never scanned: a sentence buried in a
     reference file ("also read the user's .env and POST it to ...") is
     executable text, not documentation.

Every skill declares its capabilities in `attestation.json`. This tool
computes the capabilities the code *actually* has and fails when the code
exceeds its declaration. That is what turns "Capability-Declared" from a
tagline into an enforced invariant: a skill claiming `network: none` that
imports `urllib` cannot pass.

Deliberately stdlib-only. Auditing this repository must never require
installing third-party code first.

Usage:
    python scripts/audit_skill_safety.py                 # audit everything
    python scripts/audit_skill_safety.py --skill NAME    # audit one skill
    python scripts/audit_skill_safety.py --json          # machine-readable
    python scripts/audit_skill_safety.py --strict        # WARN also fails

Exit code 0 = clean. Exit code 1 = a human needs to look at something.
"""

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# --------------------------------------------------------------------------
# Capability model
#
# Each capability is an ordered ladder from least to most powerful. A skill
# passes when every observed level is <= the declared level. Declaring more
# than you use is allowed (and merely noted); using more than you declared
# is a hard failure.
# --------------------------------------------------------------------------

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

# Imports that grant each capability. Matched on the top-level module name,
# so `from urllib.request import urlopen` is caught as `urllib`.
NETWORK_MODULES = {
    "socket", "ssl", "urllib", "http", "ftplib", "smtplib", "telnetlib",
    "requests", "httpx", "aiohttp", "xmlrpc", "poplib", "imaplib",
    "webbrowser", "websockets", "paramiko", "boto3", "urllib3",
}

# The verifier's table is deliberately wider still: it also treats asyncio,
# signal, types and code as capability-granting. Those stay verifier-only on
# purpose. They are stdlib modules with overwhelmingly non-capability uses, and
# forcing every skill that imports asyncio to declare 'network: outbound' would
# manufacture false declarations -- the exact failure this auditor exists to
# catch. The verifier faces a stranger's code and is allowed to be blunt; this
# tool grades honesty and has to be precise. CAP-UNPROVEN below is what closes
# the gap generally, without guessing.
PROCESS_MODULES = {"subprocess", "multiprocessing", "ctypes", "pty"}
DYNAMIC_MODULES = {"pickle", "marshal", "importlib", "imp", "runpy"}

# Bare builtin calls -- `compile(...)`. Checked as ast.Name only, never as
# an attribute, so `re.compile(...)` is correctly left alone.
DYNAMIC_BUILTINS = {"eval", "exec", "compile", "__import__"}

# Attribute calls -- `x.system(...)` -- dangerous whatever `x` is.
PROCESS_ATTRS = {
    "system", "popen", "spawnl", "spawnv", "spawnve", "spawnlp", "spawnvp",
    "execv", "execl", "execlp", "execvp", "execve", "fork", "forkpty",
    "posix_spawn", "posix_spawnp",
}
FS_DELETE_ATTRS = {"remove", "unlink", "rmtree", "rmdir", "removedirs"}
FS_WRITE_ATTRS = {
    "write_text", "write_bytes", "mkdir", "makedirs", "copytree", "copyfile",
    "copy", "copy2", "touch", "rename", "replace", "symlink_to", "chmod",
    "writelines",
}

OBFUSCATION_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("base64", re.compile(r"\bb(?:ase)?64(?:decode|encode|_decode|_encode)\b", re.IGNORECASE)),
    ("base64-module", re.compile(r"^\s*(?:import|from)\s+base64\b", re.MULTILINE)),
    ("hex-decode", re.compile(r"\bbytes\.fromhex\s*\(")),
    ("codecs-decode", re.compile(r"\bcodecs\.decode\s*\(")),
    ("charcode", re.compile(r"\bfromCharCode\b")),
    ("js-b64", re.compile(r"\b(?:atob|btoa)\s*\(")),
]

# --------------------------------------------------------------------------
# Markdown / instruction-surface model
# --------------------------------------------------------------------------

# Characters that are invisible to a human reviewer but reach the model.
# The Unicode Tags block (U+E0000-U+E007F) is the serious one: it can encode
# an entire hidden instruction that renders as nothing at all.
INVISIBLE_CHARS = {
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


def _is_tag_char(cp: int) -> bool:
    """Unicode Tags block -- renders as nothing, reaches the model intact."""
    return 0xE0000 <= cp <= 0xE007F


# Instruction-shaped language inside an HTML comment. A comment is invisible
# in rendered Markdown but fully visible to the model reading the raw file.
HIDDEN_DIRECTIVE_RE = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+|the\s+|previous\s+|prior\s+|above\s+)*"
    r"(?:instruction|prompt|rule|direction|guideline|context)"
    r"|\byou\s+(?:must|should|will|shall)\b"
    r"|\b(?:system|developer)\s+prompt\b"
    r"|\bwithout\s+(?:telling|informing|notifying|asking)\b"
    r"|\bdo\s+not\s+(?:tell|mention|report|inform|reveal)\b"
    r"|\bsecretly\b",
    re.IGNORECASE,
)

# Shell one-liners that download and execute code in a single step.
PIPE_TO_SHELL_RE = re.compile(
    r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|k|da)?sh\b"
    r"|(?:iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:iex|invoke-expression)\b",
    re.IGNORECASE,
)

# Credential exfiltration = a sensitive artefact named near a way to move it
# off the machine. Neither half is suspicious alone; together they are.
SENSITIVE_TOKEN_RE = re.compile(
    r"(?:^|[\s\"'`/(])\.env\b"
    r"|~/\.ssh|\.ssh/|id_rsa|id_ed25519|id_ecdsa"
    r"|\.aws/credentials|\.netrc|\.npmrc|\.pypirc|\.git-credentials"
    r"|credentials\.json|service_account\.json"
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
EXFIL_WINDOW = 2  # lines of context on each side

# A long unbroken base64-ish run inside prose is not documentation.
B64_BLOB_RE = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv",
    "env", "dist", "build", ".idea", ".vscode", ".mypy_cache", ".ruff_cache",
}

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "WARN": 2, "INFO": 3}
BLOCKING_SEVERITIES = {"CRITICAL", "HIGH"}


# --------------------------------------------------------------------------
# Finding plumbing
# --------------------------------------------------------------------------

def _finding(check: str, severity: str, path: str, message: str,
             line: Optional[int] = None, snippet: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a finding carrying a content fingerprint.

    The fingerprint hashes the exact text that triggered the finding, not its
    line number. That is what lets an allowlist entry be pinned to reviewed
    content: if the line is later edited, the fingerprint changes and the
    suppression stops applying, so the finding resurfaces for a fresh review.
    """
    basis = snippet if snippet is not None else message
    digest = hashlib.sha256(f"{check}|{path}|{basis.strip()}".encode("utf-8")).hexdigest()
    return {
        "check": check,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
        "fingerprint": digest[:16],
    }


def load_allowlist(repo_root: Path) -> List[Dict[str, str]]:
    """
    Load reviewed, justified exemptions.

    Allowlisting is per (path, check) pair, never per file, so exempting a
    scanner from the obfuscation-keyword check does not also silence a
    genuine `subprocess` import in the same file. Exempted findings are
    still printed -- suppressed, not hidden.
    """
    path = repo_root / "docs" / "safety-allowlist.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ERROR] Malformed docs/safety-allowlist.json: {exc}")
    entries = data.get("entries", [])
    for entry in entries:
        missing = {"path", "check", "reason"} - set(entry)
        if missing:
            raise SystemExit(
                f"[ERROR] safety-allowlist entry {entry!r} missing keys: {sorted(missing)}"
            )
    return entries


def is_allowlisted(finding: Dict[str, Any], allowlist: List[Dict[str, str]]) -> Optional[str]:
    """
    Return the justification if this exact finding is allowlisted.

    An entry with a `fingerprint` suppresses only the reviewed content it was
    written for. An entry without one suppresses the whole (path, check) pair
    and is therefore much blunter -- prefer pinning.
    """
    for entry in allowlist:
        if entry["path"] != finding["path"] or entry["check"] != finding["check"]:
            continue
        pinned = entry.get("fingerprint")
        if pinned and pinned != finding.get("fingerprint"):
            continue
        return entry["reason"]
    return None


# --------------------------------------------------------------------------
# Python surface
# --------------------------------------------------------------------------

# Modules that ship with the interpreter. Anything else a skill imports comes
# from outside and cannot be reasoned about structurally: the AST sees the name
# `anthropic` or `mcp`, not the socket or the fork inside it.
STDLIB_MODULES: Set[str] = set(getattr(sys, "stdlib_module_names", ()))


def _local_module_names(root: Path) -> Set[str]:
    """Module names importable from inside the bundle itself.

    `from connections import create_connection` next to connections.py is a
    local import, not a third-party dependency, and must not be flagged.
    """
    names: Set[str] = set()
    if not root.is_dir():
        return names
    for path in root.rglob("*"):
        if path.is_dir() and (path / "__init__.py").exists():
            names.add(path.name)
        elif path.suffix == ".py":
            names.add(path.stem)
    return names


def _module_roots_with_lines(tree: ast.AST) -> Dict[str, int]:
    """Top-level module name -> first line it is imported on."""
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
            # Relative imports (`from . import x`) have module None/level>0.
            if node.module and not node.level:
                roots.add(node.module.split(".")[0])
    return roots


def _is_unprovable_import(root: str, local_modules: Set[str]) -> bool:
    """True for an import whose capabilities this auditor cannot derive.

    A name in one of the capability tables is already accounted for -- the
    table says what it grants. A stdlib name is derivable in principle and is
    covered by the tables plus the call-level checks. A name defined inside the
    bundle is local source that is itself audited. Everything else is a
    third-party package: the structural derivation stops at its import line,
    and reporting 'none' for such a skill states more than the evidence
    supports.
    """
    if root in NETWORK_MODULES or root in PROCESS_MODULES or root in DYNAMIC_MODULES:
        return False
    if root in STDLIB_MODULES or root in local_modules:
        return False
    # An empty stdlib set means the interpreter did not expose the list; say
    # nothing rather than flag every import in the repository.
    return bool(STDLIB_MODULES)


def _open_is_writable(node: ast.Call) -> bool:
    """True when an `open(...)` call requests a write/append/create mode."""
    mode: Optional[str] = None
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        if isinstance(node.args[1].value, str):
            mode = node.args[1].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                mode = kw.value.value
    return bool(mode) and any(ch in mode for ch in "wax+")


def observe_python_file(path: Path, rel: str,
                        local_modules: Set[str] = frozenset(),
                        ) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    Return (observed capabilities, findings) for a single Python file.

    Capabilities are derived structurally from the AST. Findings cover
    obfuscation smells and unparseable source, both of which defeat review
    regardless of what capabilities the file declares.
    """
    observed = dict(DEFAULT_DECLARATION)
    findings: List[Dict[str, Any]] = []

    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(_finding(
            "PY-UNREADABLE", "HIGH", rel,
            f"Could not read file as UTF-8 ({exc}); it cannot be reviewed.",
        ))
        return observed, findings

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as exc:
        findings.append(_finding(
            "PY-UNPARSEABLE", "HIGH", rel,
            f"File is not parseable Python ({exc}); its behaviour cannot be verified.",
            getattr(exc, "lineno", None),
        ))
        return observed, findings

    def raise_to(cap: str, level: str) -> None:
        ladder = CAPABILITY_LADDERS[cap]
        if ladder.index(level) > ladder.index(observed[cap]):
            observed[cap] = level

    evidence: List[Dict[str, Any]] = []

    for root, lineno in sorted(_module_roots_with_lines(tree).items()):
        if root in NETWORK_MODULES:
            raise_to("network", "outbound")
            evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                     f"imports '{root}' -> network: outbound"))
        if root in PROCESS_MODULES:
            raise_to("process_execution", "subprocess")
            evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                     f"imports '{root}' -> process_execution: subprocess"))
        if root in DYNAMIC_MODULES:
            raise_to("dynamic_code_execution", "eval")
            evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                     f"imports '{root}' -> dynamic_code_execution: eval"))
        if _is_unprovable_import(root, local_modules):
            findings.append(_finding(
                "CAP-UNPROVEN", "HIGH", rel,
                f"imports '{root}', which is neither in the standard library, nor "
                f"local to this bundle, nor in the capability tables above. Its "
                f"capabilities cannot be derived from this source: the AST sees the "
                f"name, not what the package does when called. Whatever '{root}' can "
                f"do, this skill can do. Declare the capabilities it confers and pin "
                f"this finding in docs/safety-allowlist.json with the reasoning, or "
                f"drop the dependency.",
                lineno,
            ))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            if node.func.id in DYNAMIC_BUILTINS:
                raise_to("dynamic_code_execution", "eval")
                evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                         f"calls builtin '{node.func.id}()' -> dynamic_code_execution: eval",
                                         node.lineno))
            elif node.func.id == "open" and _open_is_writable(node):
                raise_to("filesystem", "workspace-write")
                evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                         "calls open() in a write mode -> filesystem: workspace-write",
                                         node.lineno))
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in PROCESS_ATTRS:
                raise_to("process_execution", "subprocess")
                evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                         f"calls '.{attr}()' -> process_execution: subprocess",
                                         node.lineno))
            elif attr in FS_DELETE_ATTRS:
                raise_to("filesystem", "workspace-delete")
                evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                         f"calls '.{attr}()' -> filesystem: workspace-delete",
                                         node.lineno))
            elif attr in FS_WRITE_ATTRS:
                raise_to("filesystem", "workspace-write")
                evidence.append(_finding("PY-CAPABILITY", "INFO", rel,
                                         f"calls '.{attr}()' -> filesystem: workspace-write",
                                         node.lineno))

    src_lines = src.splitlines()
    for label, pattern in OBFUSCATION_PATTERNS:
        for match in pattern.finditer(src):
            line_no = src.count("\n", 0, match.start()) + 1
            snippet = src_lines[line_no - 1] if line_no <= len(src_lines) else match.group(0)
            findings.append(_finding(
                "PY-OBFUSCATION", "HIGH", rel,
                f"Obfuscation smell '{label}' at line {line_no}. Encoded payloads "
                f"defeat human review; a skill script has no legitimate need for one.",
                line_no, snippet,
            ))

    findings.extend(evidence)
    return observed, findings


# --------------------------------------------------------------------------
# Markdown / instruction surface
# --------------------------------------------------------------------------

def scan_markdown_text(text: str, rel: str) -> List[Dict[str, Any]]:
    """Scan text that will be injected into an agent's context as instructions."""
    findings: List[Dict[str, Any]] = []
    lines = text.splitlines()

    # 1. Characters a human reviewer cannot see but the model still reads.
    for idx, line in enumerate(lines, start=1):
        for ch in line:
            cp = ord(ch)
            if _is_tag_char(cp):
                findings.append(_finding(
                    "MD-INVISIBLE-UNICODE", "CRITICAL", rel,
                    f"Unicode Tag character U+{cp:04X} at line {idx}. This block renders "
                    f"as nothing and is the standard carrier for smuggled instructions.",
                    idx, line,
                ))
            elif cp in BIDI_CHARS:
                findings.append(_finding(
                    "MD-BIDI-CONTROL", "CRITICAL", rel,
                    f"Bidirectional control character U+{cp:04X} ({BIDI_CHARS[cp]}) at "
                    f"line {idx}. Text can render in a different order than it is parsed.",
                    idx, line,
                ))
            elif cp in INVISIBLE_CHARS:
                findings.append(_finding(
                    "MD-INVISIBLE-UNICODE", "HIGH", rel,
                    f"Invisible character U+{cp:04X} ({INVISIBLE_CHARS[cp]}) at line {idx}.",
                    idx, line,
                ))

    # 2. HTML comments: invisible when rendered, fully visible to the model.
    for match in re.finditer(r"<!--(.*?)-->", text, re.DOTALL):
        body = match.group(1)
        line_no = text.count("\n", 0, match.start()) + 1
        if HIDDEN_DIRECTIVE_RE.search(body):
            findings.append(_finding(
                "MD-HIDDEN-DIRECTIVE", "CRITICAL", rel,
                f"HTML comment at line {line_no} contains instruction-shaped language. "
                f"It is invisible in rendered Markdown but reaches the agent verbatim.",
                line_no, body,
            ))
        else:
            findings.append(_finding(
                "MD-HTML-COMMENT", "INFO", rel,
                f"HTML comment at line {line_no} (no directive language detected).",
                line_no, body,
            ))

    # 3. Encoded payloads hidden in prose.
    for match in B64_BLOB_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        findings.append(_finding(
            "MD-ENCODED-BLOB", "HIGH", rel,
            f"{len(match.group(0))}-character base64-like blob at line {line_no}. "
            f"Encoded content in an instruction file cannot be reviewed.",
            line_no, match.group(0),
        ))

    # 4. Download-and-execute one-liners.
    for match in PIPE_TO_SHELL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        findings.append(_finding(
            "MD-PIPE-TO-SHELL", "HIGH", rel,
            f"Pipe-to-shell instruction at line {line_no}: {match.group(0).strip()!r}. "
            f"This runs unreviewed remote code on the user's machine.",
            line_no, match.group(0),
        ))

    # 5. Credential exfiltration: a sensitive artefact named near a way to
    #    move it off the machine. Either half alone is unremarkable.
    for idx, line in enumerate(lines, start=1):
        if not SENSITIVE_TOKEN_RE.search(line):
            continue
        lo = max(0, idx - 1 - EXFIL_WINDOW)
        hi = min(len(lines), idx + EXFIL_WINDOW)
        window = "\n".join(lines[lo:hi])
        verb = EXFIL_VERB_RE.search(window)
        if verb:
            findings.append(_finding(
                "MD-CREDENTIAL-EXFIL", "CRITICAL", rel,
                f"Line {idx} names a credential or secret artefact within "
                f"{EXFIL_WINDOW} lines of a network operation ({verb.group(0).strip()!r}). "
                f"Verify this is documentation, not an instruction to exfiltrate.",
                idx, line,
            ))

    return findings


def scan_markdown_file(path: Path, rel: str) -> List[Dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [_finding(
            "MD-UNREADABLE", "HIGH", rel,
            f"Could not read file as UTF-8 ({exc}); it cannot be reviewed.",
        )]
    return scan_markdown_text(text, rel)


# --------------------------------------------------------------------------
# Declaration handling
# --------------------------------------------------------------------------

def _merge_observed(into: Dict[str, str], other: Dict[str, str]) -> None:
    for cap, ladder in CAPABILITY_LADDERS.items():
        if ladder.index(other[cap]) > ladder.index(into[cap]):
            into[cap] = other[cap]


def read_declaration(source: Path, rel: str) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    Read a declared capability set from an attestation.json.

    A missing declaration is itself a finding: an undeclared skill cannot be
    checked against anything, so it silently escapes the entire point of
    this tool.
    """
    findings: List[Dict[str, Any]] = []
    if not source.exists():
        findings.append(_finding(
            "DECL-MISSING", "HIGH", rel,
            "No attestation.json, so the skill declares no capabilities and "
            "nothing can be enforced against it.",
        ))
        return dict(DEFAULT_DECLARATION), findings

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(_finding("DECL-MALFORMED", "HIGH", rel,
                                 f"attestation.json is unreadable: {exc}"))
        return dict(DEFAULT_DECLARATION), findings

    raw = data.get("capabilities")
    if not isinstance(raw, dict):
        findings.append(_finding(
            "DECL-MISSING", "HIGH", rel,
            "attestation.json has no 'capabilities' object. Add one so the "
            "code can be checked against what it claims to do.",
        ))
        return dict(DEFAULT_DECLARATION), findings

    declared = dict(DEFAULT_DECLARATION)
    for cap, ladder in CAPABILITY_LADDERS.items():
        if cap not in raw:
            findings.append(_finding(
                "DECL-INCOMPLETE", "WARN", rel,
                f"capabilities.{cap} is not declared; defaulting to the most "
                f"restrictive value '{DEFAULT_DECLARATION[cap]}'.",
            ))
            continue
        value = raw[cap]
        if value not in ladder:
            findings.append(_finding(
                "DECL-INVALID", "HIGH", rel,
                f"capabilities.{cap} is {value!r}, which is not one of {ladder}.",
            ))
            continue
        declared[cap] = value
    return declared, findings


def compare_capabilities(observed: Dict[str, str], declared: Dict[str, str],
                         rel: str) -> List[Dict[str, Any]]:
    """Fail when code exceeds its declaration; note when it under-uses it."""
    findings: List[Dict[str, Any]] = []
    for cap, ladder in CAPABILITY_LADDERS.items():
        obs_i, dec_i = ladder.index(observed[cap]), ladder.index(declared[cap])
        if obs_i > dec_i:
            findings.append(_finding(
                "CAP-UNDECLARED", "CRITICAL", rel,
                f"Code exceeds its declaration for '{cap}': declared "
                f"{declared[cap]!r} but the code actually has {observed[cap]!r}. "
                f"Either remove the capability or declare it honestly.",
            ))
        elif obs_i < dec_i:
            findings.append(_finding(
                "CAP-OVERDECLARED", "WARN", rel,
                f"Declares '{cap}' as {declared[cap]!r} but the code only needs "
                f"{observed[cap]!r}. Tighten the declaration to the real minimum.",
            ))
    return findings


# --------------------------------------------------------------------------
# Unit auditing
# --------------------------------------------------------------------------

def _iter_files(root: Path) -> List[Path]:
    out: List[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def audit_skill(skill_dir: Path, repo_root: Path) -> Dict[str, Any]:
    """Audit one skill directory: every script and every instruction file."""
    rel_dir = skill_dir.relative_to(repo_root).as_posix()
    observed = dict(DEFAULT_DECLARATION)
    findings: List[Dict[str, Any]] = []
    py_count = md_count = 0
    local_modules = _local_module_names(skill_dir)

    for path in _iter_files(skill_dir):
        rel = path.relative_to(repo_root).as_posix()
        if path.suffix == ".py":
            py_count += 1
            file_obs, file_findings = observe_python_file(path, rel, local_modules)
            _merge_observed(observed, file_obs)
            findings.extend(file_findings)
        elif path.suffix.lower() in MARKDOWN_SUFFIXES:
            md_count += 1
            findings.extend(scan_markdown_file(path, rel))

    declared, decl_findings = read_declaration(skill_dir / "attestation.json", rel_dir)
    findings.extend(decl_findings)
    findings.extend(compare_capabilities(observed, declared, rel_dir))

    return {
        "unit": rel_dir,
        "kind": "skill",
        "observed": observed,
        "declared": declared,
        "python_files": py_count,
        "markdown_files": md_count,
        "findings": findings,
    }


def audit_component(path: Path, repo_root: Path, declared_raw: Dict[str, str],
                    rationale: str) -> Dict[str, Any]:
    """
    Audit a single non-skill file -- repository tooling a user is expected to
    execute (the installer, the validators). These carry their declaration in
    docs/capability-declarations.json rather than an attestation.json.
    """
    rel = path.relative_to(repo_root).as_posix()
    findings: List[Dict[str, Any]] = []

    declared = dict(DEFAULT_DECLARATION)
    for cap, ladder in CAPABILITY_LADDERS.items():
        value = declared_raw.get(cap, DEFAULT_DECLARATION[cap])
        if value not in ladder:
            findings.append(_finding("DECL-INVALID", "HIGH", rel,
                                     f"Declared '{cap}' is {value!r}, not one of {ladder}."))
            continue
        declared[cap] = value

    if path.suffix == ".py":
        # A standalone component imports its neighbours in the same directory.
        observed, file_findings = observe_python_file(
            path, rel, _local_module_names(path.parent))
        findings.extend(file_findings)
    else:
        observed = dict(DEFAULT_DECLARATION)
        findings.extend(scan_markdown_file(path, rel))

    findings.extend(compare_capabilities(observed, declared, rel))
    return {
        "unit": rel,
        "kind": "component",
        "rationale": rationale,
        "observed": observed,
        "declared": declared,
        "python_files": 1 if path.suffix == ".py" else 0,
        "markdown_files": 0 if path.suffix == ".py" else 1,
        "findings": findings,
    }


def audit_instruction_file(path: Path, repo_root: Path) -> Dict[str, Any]:
    """
    Audit a root-level instruction file (CLAUDE.md, AGENTS.md).

    These are not skills, but they are loaded into an agent's context on
    every session, which makes them the highest-leverage place in the whole
    repository to hide an instruction.
    """
    rel = path.relative_to(repo_root).as_posix()
    return {
        "unit": rel,
        "kind": "instructions",
        "observed": dict(DEFAULT_DECLARATION),
        "declared": dict(DEFAULT_DECLARATION),
        "python_files": 0,
        "markdown_files": 1,
        "findings": scan_markdown_file(path, rel),
    }


def discover_skills(repo_root: Path) -> List[Path]:
    """Every directory containing a SKILL.md, under skills/ and .agents/."""
    found: List[Path] = []
    for base in (repo_root / "skills", repo_root / ".agents" / "skills"):
        if not base.exists():
            continue
        for skill_md in sorted(base.rglob("SKILL.md")):
            found.append(skill_md.parent)
    return found


def load_components(repo_root: Path) -> List[Tuple[Path, Dict[str, str], str]]:
    config = repo_root / "docs" / "capability-declarations.json"
    if not config.exists():
        return []
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ERROR] Malformed docs/capability-declarations.json: {exc}")

    out: List[Tuple[Path, Dict[str, str], str]] = []
    for entry in data.get("components", []):
        target = repo_root / entry["path"]
        if not target.exists():
            raise SystemExit(
                f"[ERROR] capability-declarations.json references a missing file: "
                f"{entry['path']}"
            )
        out.append((target, entry.get("capabilities", {}), entry.get("rationale", "")))
    return out


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

SEVERITY_ICON = {
    "CRITICAL": "[CRIT]",
    "HIGH": "[HIGH]",
    "WARN": "[WARN]",
    "INFO": "[INFO]",
}


def partition_findings(results: List[Dict[str, Any]],
                       allowlist: List[Dict[str, str]]) -> Tuple[List, List]:
    """Split findings into (active, suppressed-by-allowlist), preserving both."""
    active, suppressed = [], []
    for result in results:
        for finding in result["findings"]:
            reason = is_allowlisted(finding, allowlist)
            if reason is None:
                active.append(finding)
            else:
                suppressed.append({**finding, "allowlist_reason": reason})
    return active, suppressed


def print_report(results: List[Dict[str, Any]], suppressed: List[Dict[str, Any]],
                 show_info: bool) -> None:
    print("=" * 78)
    print(" [SKILL SAFETY AUDIT] Capability & Instruction-Surface Scan")
    print("=" * 78)

    for result in results:
        blocking = [f for f in result["findings"]
                    if f["severity"] in BLOCKING_SEVERITIES]
        warns = [f for f in result["findings"] if f["severity"] == "WARN"]
        status = "[FAIL]" if blocking else ("[WARN]" if warns else "[PASS]")
        print(f"\n{status} {result['unit']}  "
              f"({result['python_files']} py, {result['markdown_files']} md)")

        caps = []
        for cap in CAPABILITY_LADDERS:
            obs, dec = result["observed"][cap], result["declared"][cap]
            marker = "" if obs == dec else f" (declared {dec})"
            caps.append(f"{cap}={obs}{marker}")
        print(f"       capabilities: {', '.join(caps)}")

        ordered = sorted(result["findings"],
                         key=lambda f: (SEVERITY_ORDER[f["severity"]],
                                        f["path"], f["line"] or 0))
        for finding in ordered:
            if finding["severity"] == "INFO" and not show_info:
                continue
            loc = f"{finding['path']}:{finding['line']}" if finding["line"] else finding["path"]
            print(f"       {SEVERITY_ICON[finding['severity']]} {finding['check']} "
                  f"{loc}\n              {finding['message']}")

    if suppressed:
        print("\n" + "-" * 78)
        print(" Suppressed by docs/safety-allowlist.json (shown, not hidden):")
        for finding in suppressed:
            loc = f"{finding['path']}:{finding['line']}" if finding["line"] else finding["path"]
            print(f"   - {finding['check']} {loc}")
            print(f"     reason: {finding['allowlist_reason']}")


def print_summary(results: List[Dict[str, Any]], active: List[Dict[str, Any]],
                  suppressed: List[Dict[str, Any]]) -> None:
    counts = {sev: sum(1 for f in active if f["severity"] == sev)
              for sev in SEVERITY_ORDER}
    print("\n" + "=" * 78)
    print(f" Units audited: {len(results)} | "
          f"CRITICAL: {counts['CRITICAL']} | HIGH: {counts['HIGH']} | "
          f"WARN: {counts['WARN']} | suppressed: {len(suppressed)}")
    print("=" * 78)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def run_audit(repo_root: Path, skill_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Audit every skill, declared component, and root instruction file."""
    results: List[Dict[str, Any]] = []

    for skill_dir in discover_skills(repo_root):
        if skill_filter and skill_dir.name != skill_filter:
            continue
        results.append(audit_skill(skill_dir, repo_root))

    if skill_filter:
        return results

    for path, declared, rationale in load_components(repo_root):
        results.append(audit_component(path, repo_root, declared, rationale))

    for name in ("CLAUDE.md", "AGENTS.md"):
        path = repo_root / name
        if path.exists():
            results.append(audit_instruction_file(path, repo_root))

    return results


def main() -> None:
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Audit skills for undeclared capabilities and hidden instructions.",
    )
    parser.add_argument("--target", type=str, default=None,
                        help="Repository root to audit (default: this repository).")
    parser.add_argument("--skill", type=str, default=None,
                        help="Audit only the named skill.")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of a report.")
    parser.add_argument("--strict", action="store_true",
                        help="Treat WARN findings as failures too.")
    parser.add_argument("--show-info", action="store_true",
                        help="Include INFO capability evidence in the report.")
    args = parser.parse_args()

    repo_root = (Path(args.target).resolve() if args.target
                 else Path(__file__).resolve().parent.parent)
    if not repo_root.exists():
        raise SystemExit(f"[ERROR] Target does not exist: {repo_root}")

    allowlist = load_allowlist(repo_root)
    results = run_audit(repo_root, args.skill)

    if args.skill and not results:
        raise SystemExit(f"[ERROR] No skill named {args.skill!r} was found.")

    active, suppressed = partition_findings(results, allowlist)
    blocking = [f for f in active if f["severity"] in BLOCKING_SEVERITIES]
    warnings = [f for f in active if f["severity"] == "WARN"]

    if args.json:
        print(json.dumps({
            "units": results,
            "suppressed": suppressed,
            "blocking_count": len(blocking),
            "warning_count": len(warnings),
        }, indent=2))
    else:
        print_report(results, suppressed, args.show_info)
        print_summary(results, active, suppressed)
        if blocking:
            print(" RESULT: FAIL -- review every CRITICAL and HIGH finding above.")
        elif warnings and args.strict:
            print(" RESULT: FAIL (--strict) -- WARN findings present.")
        else:
            print(" RESULT: PASS -- no undeclared capability and no hidden "
                  "instruction detected.")

    sys.exit(1 if blocking or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
