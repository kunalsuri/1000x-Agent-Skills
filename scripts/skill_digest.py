#!/usr/bin/env python3
"""
Content digests for attested skills.

An attestation that is not bound to the content it attests is decoration:
`"attestation_status": "VERIFIED"` is a string anybody can type, and it keeps
saying VERIFIED no matter how the skill's files change afterwards.

This module binds the two together. Every skill's attestation carries a
`content_digest` over the exact bytes of every other file in the skill, so
editing a SKILL.md, a script, or a reference doc after attestation changes
the digest and fails the build. Re-attesting becomes a deliberate act with a
visible diff, rather than something that silently never happens.

The digest is a SHA-256 over a canonical manifest, one line per file:

    <posix relative path>  <sha256 of file bytes>\\n

Sorted by path, so it is stable across platforms and filesystem orderings.
`attestation.json` is excluded -- it is where the digest lives, so including
it would be self-referential.

Deliberately stdlib-only, so anyone can verify a skill they downloaded
without installing anything first:

    python scripts/skill_digest.py --check
    python scripts/skill_digest.py --update
    python scripts/skill_digest.py --print skills/custom/readme-designer
"""

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DIGEST_KEY = "content_digest"
DIGEST_PREFIX = "sha256:"
EXCLUDED_NAMES = {"attestation.json"}
EXCLUDED_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git",
    "node_modules", ".venv", "venv",
}


def iter_digest_files(skill_dir: Path) -> List[Path]:
    """Every file covered by the digest, in a deterministic order."""
    files = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(skill_dir).parts):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(skill_dir).as_posix())


def build_manifest(skill_dir: Path) -> str:
    """The canonical text the digest is taken over. Useful for diffing."""
    lines = []
    for path in iter_digest_files(skill_dir):
        rel = path.relative_to(skill_dir).as_posix()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{rel}  {file_hash}")
    return "\n".join(lines) + "\n"


def compute_skill_digest(skill_dir: Path) -> str:
    """Return the `sha256:<hex>` digest binding an attestation to its content."""
    manifest = build_manifest(skill_dir)
    return DIGEST_PREFIX + hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def read_recorded_digest(skill_dir: Path) -> Optional[str]:
    attestation = skill_dir / "attestation.json"
    if not attestation.exists():
        return None
    try:
        data = json.loads(attestation.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = data.get(DIGEST_KEY)
    return value if isinstance(value, str) else None


def verify_skill(skill_dir: Path) -> Tuple[bool, str]:
    """Return (ok, human-readable explanation)."""
    attestation = skill_dir / "attestation.json"
    if not attestation.exists():
        return False, "no attestation.json, so nothing binds this skill's content"

    recorded = read_recorded_digest(skill_dir)
    if recorded is None:
        return False, (
            f"attestation.json has no '{DIGEST_KEY}'. Run "
            f"`python scripts/skill_digest.py --update` to bind it to its content"
        )

    actual = compute_skill_digest(skill_dir)
    if recorded != actual:
        return False, (
            f"content has changed since attestation.\n"
            f"        recorded: {recorded}\n"
            f"        actual:   {actual}\n"
            f"        Re-review the diff, then re-attest with "
            f"`python scripts/skill_digest.py --update`"
        )
    return True, actual


def update_skill(skill_dir: Path) -> Tuple[bool, str]:
    """Write the current digest into attestation.json. Returns (changed, digest)."""
    attestation = skill_dir / "attestation.json"
    data = json.loads(attestation.read_text(encoding="utf-8"),
                      object_pairs_hook=collections.OrderedDict)
    digest = compute_skill_digest(skill_dir)
    changed = data.get(DIGEST_KEY) != digest
    if changed:
        data[DIGEST_KEY] = digest
        attestation.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed, digest


def discover_skills(repo_root: Path) -> List[Path]:
    found: List[Path] = []
    for base in (repo_root / "skills", repo_root / ".agents" / "skills"):
        if base.exists():
            found.extend(sorted(md.parent for md in base.rglob("SKILL.md")))
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or refresh skill content digests.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="Verify every recorded digest matches the content.")
    group.add_argument("--update", action="store_true",
                       help="Re-bind every attestation to its current content.")
    group.add_argument("--print", dest="print_dir", metavar="SKILL_DIR",
                       help="Print the digest manifest for one skill.")
    parser.add_argument("--target", default=None, help="Repository root (default: this repo).")
    args = parser.parse_args()

    repo_root = (Path(args.target).resolve() if args.target
                 else Path(__file__).resolve().parent.parent)

    if args.print_dir:
        skill_dir = Path(args.print_dir).resolve()
        if not (skill_dir / "SKILL.md").exists():
            raise SystemExit(f"[ERROR] Not a skill directory: {skill_dir}")
        sys.stdout.write(build_manifest(skill_dir))
        print(f"\ndigest: {compute_skill_digest(skill_dir)}")
        return

    skills = discover_skills(repo_root)
    if not skills:
        raise SystemExit("[ERROR] No skills found.")

    failures = 0
    for skill_dir in skills:
        rel = skill_dir.relative_to(repo_root).as_posix()
        if args.update:
            changed, digest = update_skill(skill_dir)
            print(f"{'[UPDATED]' if changed else '[CURRENT]'} {rel}  {digest}")
        else:
            ok, detail = verify_skill(skill_dir)
            print(f"{'[OK]  ' if ok else '[FAIL]'} {rel}  {detail}")
            failures += 0 if ok else 1

    if args.check:
        print(f"\n{len(skills)} skills checked, {failures} failed.")
        sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
