#!/usr/bin/env python3
"""
Re-sync the .agents/skills/ mirror from the canonical skills/ tree.

.agents/skills/ must be a byte-identical copy of every skills/<skill>/
directory (tests/unit/test_agents_mirror_parity.py enforces it). Until this
script existed, "re-sync" meant a hand-run cp -- easy to forget, and easy to
do with a tool that is not installed everywhere (rsync is absent from many
CI images and from Windows).

Default is a dry run that prints what would change. Pass --write to apply.
Exit codes: 0 = mirror already in sync (or synced with --write),
1 = drift found in dry-run mode, 2 = usage error.

Standard library only; writes and deletes only inside .agents/skills/.
"""

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / "skills"
MIRROR = REPO_ROOT / ".agents" / "skills"

# Never mirrored: OS and interpreter litter.
IGNORED = {".DS_Store", "__pycache__", "Thumbs.db"}


def canonical_skills(root: Path) -> list:
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def tree_differs(left: Path, right: Path) -> bool:
    if not right.exists():
        return True
    cmp = filecmp.dircmp(left, right, ignore=list(IGNORED))
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return True
    for name in cmp.common_files:
        if not filecmp.cmp(left / name, right / name, shallow=False):
            return True
    return any(tree_differs(left / d, right / d) for d in cmp.common_dirs)


def plan(canonical_root: Path, mirror_root: Path) -> tuple:
    """Return (to_copy, to_delete): skill dirs to refresh, mirror dirs to drop."""
    sources = canonical_skills(canonical_root)
    names = {p.name for p in sources}
    to_copy = [p for p in sources if tree_differs(p, mirror_root / p.name)]
    to_delete = []
    if mirror_root.exists():
        to_delete = sorted(p for p in mirror_root.iterdir()
                           if p.is_dir() and p.name not in names)
    return to_copy, to_delete


def apply(to_copy: list, to_delete: list, mirror_root: Path) -> None:
    mirror_root.mkdir(parents=True, exist_ok=True)
    for stale in to_delete:
        shutil.rmtree(stale)
    for src in to_copy:
        dest = mirror_root / src.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*IGNORED))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    parser.add_argument("--write", action="store_true",
                        help="apply the changes (default: dry run)")
    args = parser.parse_args(argv)

    to_copy, to_delete = plan(CANONICAL, MIRROR)
    for src in to_copy:
        print(f"[SYNC]   skills/{src.name} -> .agents/skills/{src.name}")
    for stale in to_delete:
        print(f"[DELETE] .agents/skills/{stale.name} (no canonical source)")
    if not to_copy and not to_delete:
        print("[OK] .agents/skills/ already mirrors skills/.")
        return 0
    if not args.write:
        print("Dry run. Re-run with --write to apply.")
        return 1
    apply(to_copy, to_delete, MIRROR)
    print("[DONE] mirror updated. Run `python scripts/skill_digest.py --check` next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
