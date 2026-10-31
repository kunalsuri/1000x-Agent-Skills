#!/usr/bin/env python3
"""
Report (and optionally apply) updates for every version pin in this repository.

Pins checked:
  - requirements-dev.txt        name==X.Y.Z          -> latest on PyPI
  - .github/workflows/*.yml     uses: owner/repo@vN   -> latest major release tag
  - .github/workflows/*.yml     SKILLS_REF_SHA: <sha> -> agentskills/agentskills main
  - .github/workflows/*.yml     CLAUDE_CODE_VERSION   -> @anthropic-ai/claude-code on npm

Dependabot covers the first two kinds; the last two are pins Dependabot cannot
see, which is why this script exists. It also gives one command that brings a
working copy fully up to date instead of merging a stream of bot PRs.

Default is a dry run that prints a table. Pass --write to rewrite the pins in
place, then run the full test suite before committing.

Every value fetched from a registry is checked against a strict pattern before
it is compared or written: a registry response is untrusted input, and these
files are executed by CI.

Exit codes: 0 = everything current (or updated with --write),
            1 = updates available (dry run),
            2 = a registry could not be reached or returned something invalid,
            3 = usage error.

Standard library only. Network: outbound HTTPS GETs to pypi.org,
api.github.com and registry.npmjs.org. Filesystem: writes only with --write,
and only to requirements-dev.txt and .github/workflows/*.yml.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

# Fetch timeout in seconds: long enough for a slow registry, short enough that
# a hung connection fails the weekly job instead of eating its time budget.
TIMEOUT_SECONDS = 20

SEMVER = re.compile(r"^\d+(\.\d+){1,3}$")
MAJOR_TAG = re.compile(r"^v(\d+)(\.\d+){0,2}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
PKG_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s#]+)\s*$")
USES = re.compile(r"(uses:\s*)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(v\d+)\b")
ENV_PIN = re.compile(r"^(\s*)(SKILLS_REF_SHA|CLAUDE_CODE_VERSION):\s*(\S+)\s*$", re.M)


class FetchError(Exception):
    """A registry was unreachable or returned something that failed validation."""


def http_json(url: str) -> object:
    headers = {"Accept": "application/json", "User-Agent": "1000x-agent-skills-check-updates"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # network, HTTP and JSON errors all mean "no answer"
        raise FetchError(f"{url}: {exc}") from exc


def _checked(value: object, pattern: re.Pattern, what: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise FetchError(f"{what}: registry returned an unexpected value {value!r}")
    return value


def latest_pypi(name: str, fetch: Callable = http_json) -> str:
    data = fetch(f"https://pypi.org/pypi/{name}/json")
    return _checked(data.get("info", {}).get("version"), SEMVER, f"PyPI {name}")


def latest_action_major(repo: str, fetch: Callable = http_json) -> str:
    data = fetch(f"https://api.github.com/repos/{repo}/releases/latest")
    tag = _checked(data.get("tag_name"), MAJOR_TAG, f"GitHub {repo}")
    return "v" + MAJOR_TAG.match(tag).group(1)


def latest_skills_ref_sha(fetch: Callable = http_json) -> str:
    data = fetch("https://api.github.com/repos/agentskills/agentskills/commits/main")
    return _checked(data.get("sha"), SHA, "agentskills/agentskills main")


def latest_claude_code(fetch: Callable = http_json) -> str:
    data = fetch("https://registry.npmjs.org/@anthropic-ai/claude-code/latest")
    return _checked(data.get("version"), SEMVER, "npm @anthropic-ai/claude-code")


def collect_pins(root: Path) -> List[Dict[str, str]]:
    """Every pin in the repository, de-duplicated by (kind, name)."""
    pins: Dict[tuple, Dict[str, str]] = {}
    req = root / "requirements-dev.txt"
    if req.exists():
        for line in req.read_text(encoding="utf-8").splitlines():
            m = PKG_PIN.match(line.strip())
            if m:
                pins[("pip", m.group(1))] = {"kind": "pip", "name": m.group(1), "current": m.group(2)}
    wf_dir = root / ".github" / "workflows"
    for wf in sorted(wf_dir.glob("*.yml")) if wf_dir.exists() else []:
        text = wf.read_text(encoding="utf-8")
        for m in USES.finditer(text):
            pins.setdefault(("action", m.group(2)),
                            {"kind": "action", "name": m.group(2), "current": m.group(3)})
        for m in ENV_PIN.finditer(text):
            pins.setdefault(("env", m.group(2)),
                            {"kind": "env", "name": m.group(2), "current": m.group(3)})
    return list(pins.values())


def resolve_latest(pin: Dict[str, str], fetch: Callable = http_json) -> str:
    if pin["kind"] == "pip":
        return latest_pypi(pin["name"], fetch)
    if pin["kind"] == "action":
        return latest_action_major(pin["name"], fetch)
    if pin["name"] == "SKILLS_REF_SHA":
        return latest_skills_ref_sha(fetch)
    return latest_claude_code(fetch)


def _version_key(v: str):
    return tuple(int(p) for p in re.findall(r"\d+", v))


def is_newer(latest: str, current: str, kind: str, name: str) -> bool:
    if kind == "env" and name == "SKILLS_REF_SHA":
        return latest != current  # commits have no order we can compare offline
    return _version_key(latest) > _version_key(current)


def apply_updates(root: Path, updates: List[Dict[str, str]]) -> List[Path]:
    """Rewrite each outdated pin in place. Returns the files changed."""
    changed = []
    targets = [root / "requirements-dev.txt"] + sorted((root / ".github" / "workflows").glob("*.yml"))
    for path in targets:
        if not path.exists():
            continue
        text = original = path.read_text(encoding="utf-8")
        for u in updates:
            if u["kind"] == "pip":
                text = re.sub(rf"(?m)^({re.escape(u['name'])}==){re.escape(u['current'])}\s*$",
                              lambda m: m.group(1) + u["latest"], text)
            elif u["kind"] == "action":
                text = re.sub(rf"(uses:\s*{re.escape(u['name'])}@){re.escape(u['current'])}\b",
                              lambda m: m.group(1) + u["latest"], text)
            else:
                text = re.sub(rf"(?m)^(\s*{u['name']}:\s*){re.escape(u['current'])}\s*$",
                              lambda m: m.group(1) + u["latest"], text)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


def check(root: Path, fetch: Callable = http_json) -> Dict[str, list]:
    report = {"current": [], "outdated": [], "errors": []}
    for pin in collect_pins(root):
        try:
            latest = resolve_latest(pin, fetch)
        except FetchError as exc:
            report["errors"].append({**pin, "error": str(exc)})
            continue
        row = {**pin, "latest": latest}
        bucket = "outdated" if is_newer(latest, pin["current"], pin["kind"], pin["name"]) else "current"
        report[bucket].append(row)
    return report


def print_table(report: Dict[str, list]) -> None:
    rows = [(r, "UPDATE") for r in report["outdated"]] + [(r, "ok") for r in report["current"]]
    for r, status in sorted(rows, key=lambda x: (x[0]["kind"], x[0]["name"])):
        print(f"[{status:6}] {r['kind']:6} {r['name']:28} {r['current'][:12]:>14} -> {r['latest'][:12]}")
    for e in report["errors"]:
        print(f"[ERROR ] {e['kind']:6} {e['name']:28} {e['error']}", file=sys.stderr)


def main(argv: Optional[List[str]] = None, fetch: Callable = http_json, root: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(description="Check (and with --write, apply) updates to every version pin.")
    parser.add_argument("--write", action="store_true", help="rewrite outdated pins in place")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 3

    report = check(root, fetch)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_table(report)

    if report["errors"]:
        return 2
    if not report["outdated"]:
        if not args.json:
            print("All pins are current.")
        return 0
    if not args.write:
        if not args.json:
            print(f"{len(report['outdated'])} update(s) available. Re-run with --write, then run the tests.")
        return 1
    for path in apply_updates(root, report["outdated"]):
        print(f"[WROTE] {path.relative_to(root)}")
    print("Pins updated. Run `python -m pytest` and the CI checks before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
