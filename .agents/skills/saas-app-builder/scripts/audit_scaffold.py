#!/usr/bin/env python3
"""
Auditability tool for scaffold_saas.py.

scaffold_saas.py is one large file, but the vast majority of it is inert
template *content* (strings that get written verbatim to disk) rather than
executable *logic*. This script answers the one question that actually
matters for trusting it: does the Python code that runs have any capability
to make a network call, spawn a process, execute dynamic code, or delete
files outside the directory you told it to write to?

It does this structurally, via Python's `ast` module, not by trusting
comments or a manual read — a `subprocess.run(...)` call can't hide from
this the way it could from a skim-read of a 2000-line file.

Usage:
    python audit_scaffold.py [path/to/scaffold_saas.py]

Exit code 0 = clean. Exit code 1 = something needs a human to look at it.
Prints a report either way; run it after every change to scaffold_saas.py,
and re-run it yourself on any copy of this skill before trusting it.

Note: running this against itself (or any other file that legitimately
implements pattern/import detection) will report false positives — its own
source necessarily contains the detection keywords ("base64",
"fromCharCode", ...) and calls `re.compile(...)`, which trip the very
patterns it's built to flag. That's expected self-reference, not a bug;
this tool is meant to audit generator scripts like scaffold_saas.py, which
have no legitimate reason to contain any of those.
"""

import argparse
import ast
import re
import sys
from pathlib import Path

# Stdlib modules a deterministic "write some files to a directory" CLI
# script has a legitimate reason to import. Anything not on this list is
# flagged for review, not necessarily bad — just worth a human's eyes.
ALLOWED_IMPORTS = {
    "argparse", "json", "pathlib", "sys", "os",
    "re", "typing", "dataclasses", "textwrap", "string", "datetime",
}

# Imports that grant network, process-execution, or dynamic-code-execution
# capability. Presence of any of these is a hard fail — a scaffolder that
# only writes files to disk has no legitimate reason to import them.
DISALLOWED_IMPORTS = {
    "socket", "subprocess", "urllib", "urllib.request", "requests",
    "http", "http.client", "ftplib", "smtplib", "telnetlib",
    "multiprocessing", "ctypes", "pickle", "marshal", "importlib",
    "webbrowser", "shutil",
}

# Python builtins for dynamic code execution. Checked only as a *bare* call
# (`compile(...)`) — not as `node.func.attr`, because that would also match
# unrelated methods that happen to share the name, like `re.compile(...)`.
BUILTIN_DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__"}

# Attribute calls (`x.name(...)`) dangerous regardless of which object `x`
# is — these names are uncommon enough elsewhere that the false-positive
# risk is low, unlike the builtins above.
ATTR_DANGEROUS_CALLS = {
    "system", "popen", "spawnl", "spawnv", "fork", "execv", "execl",
    "remove", "unlink", "rmtree",
}

OBFUSCATION_PATTERNS = [
    re.compile(r"base64", re.IGNORECASE),
    re.compile(r"\batob\("),
    re.compile(r"\bbtoa\("),
    re.compile(r"fromCharCode"),
]

URL_PATTERN = re.compile(r"https?://[^\s\"'`)]+")


def audit(path: Path) -> int:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))

    imports: set[str] = set()
    # module name -> the local name(s) it actually binds, so "unused"
    # detection works for `from pathlib import Path` (binds `Path`, not
    # `pathlib`) as well as plain `import os` (binds `os`).
    bound_names: dict[str, set[str]] = {}
    dangerous_calls: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                imports.add(mod)
                bound_names.setdefault(mod, set()).add(alias.asname or mod)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[0]
            imports.add(mod)
            for alias in node.names:
                bound_names.setdefault(mod, set()).add(alias.asname or alias.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BUILTIN_DANGEROUS_CALLS:
                dangerous_calls.append((node.lineno, node.func.id))
            elif isinstance(node.func, ast.Attribute) and node.func.attr in ATTR_DANGEROUS_CALLS:
                dangerous_calls.append((node.lineno, node.func.attr))

    unexpected_imports = imports - ALLOWED_IMPORTS
    disallowed_hit = imports & DISALLOWED_IMPORTS
    obfuscation_hits = [
        (i + 1, pat.pattern)
        for i, line in enumerate(src.splitlines())
        for pat in OBFUSCATION_PATTERNS
        if pat.search(line)
    ]
    urls = sorted(set(URL_PATTERN.findall(src)))

    ok = not disallowed_hit and not dangerous_calls and not obfuscation_hits

    print(f"Auditing {path}\n")

    used_names = _used_names(tree)
    print("Imports found (this is the COMPLETE list of modules the script can use):")
    for m in sorted(imports):
        names = bound_names.get(m, {m})
        flag = " (unused import)" if not (names & used_names) else ""
        print(f"  - {m}{flag}")
    if unexpected_imports:
        print(f"\n  ⚠ Not on the allowlist, review these: {sorted(unexpected_imports)}")

    print("\nDisallowed (network / process / dynamic-import) modules:",
          sorted(disallowed_hit) or "NONE")

    print("Dangerous calls (eval/exec/subprocess-equivalents/file deletion):",
          dangerous_calls or "NONE")

    print("Obfuscation smells (base64/atob/btoa/fromCharCode):",
          obfuscation_hits or "NONE")

    print(f"\nExternal URLs referenced ({len(urls)}) — these live inside generated")
    print("app *templates* (fetched later by a browser running the generated app,")
    print("not by this script) unless shown otherwise above:")
    for u in urls:
        print(f"  - {u}")

    print("\n" + ("PASS — no network/exec/subprocess capability found." if ok
                   else "FAIL — see flagged items above."))
    return 0 if ok else 1


def _used_names(tree: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def main() -> None:
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        default=str(Path(__file__).with_name("scaffold_saas.py")),
        help="Path to scaffold_saas.py (default: the copy next to this script).",
    )
    args = parser.parse_args()
    sys.exit(audit(Path(args.target)))


if __name__ == "__main__":
    main()
