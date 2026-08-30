#!/usr/bin/env python3
"""
Install / export agent skills to Claude Code, Google Antigravity, or Cursor.

This is the only tool in the repository that writes outside it, into agent
skill directories under the user's home. It therefore does three things
before touching anything:

  1. Previews by default. A bare invocation shows exactly what would be
     created, replaced, or left alone, and writes nothing. You opt in to
     the write with --apply.
  2. Prints each skill's declared capabilities and content digest, so the
     decision to install is made with the skill's blast radius on screen
     rather than after the fact.
  3. Refuses to install a skill that fails scripts/audit_skill_safety.py.
     An installer that will happily place code it just found to be unsafe
     into ~/.claude/skills is not much of a safeguard. Override with
     --skip-safety-audit only if you have reviewed the findings yourself.

Usage:
    python scripts/install_to_agent.py --target claude --all
    python scripts/install_to_agent.py --target claude --all --apply
    python scripts/install_to_agent.py --target cursor --skill readme-designer --apply
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_skill_safety import (  # noqa: E402
    BLOCKING_SEVERITIES, CAPABILITY_LADDERS, audit_skill, is_allowlisted, load_allowlist,
)
from skill_digest import verify_skill as verify_skill_digest  # noqa: E402

TARGETS = {
    "antigravity": ("Google Antigravity", lambda: Path.home() / ".gemini" / "config" / "skills"),
    "claude": ("Claude Code", lambda: Path.home() / ".claude" / "skills"),
    "cursor": ("Cursor (current workspace)", lambda: Path.cwd() / ".cursor" / "rules"),
}


def get_target_path(target: str) -> Path:
    if target not in TARGETS:
        raise ValueError(f"Unknown target: {target}")
    return TARGETS[target][1]()


def discover_installable(repo_root: Path) -> List[Path]:
    """Canonical skills only. The .agents/ mirror is a copy, never a source."""
    skills_root = repo_root / "skills"
    if not skills_root.exists():
        return []
    return sorted(
        (skill_md.parent for skill_md in skills_root.rglob("SKILL.md")),
        key=lambda p: p.name,
    )


def assess(skill_dir: Path, repo_root: Path, allowlist) -> Dict[str, object]:
    """Collect everything a user needs in order to consent to this install."""
    result = audit_skill(skill_dir, repo_root)
    blocking = [
        f for f in result["findings"]
        if f["severity"] in BLOCKING_SEVERITIES and is_allowlisted(f, allowlist) is None
    ]
    digest_ok, digest_detail = verify_skill_digest(skill_dir)
    return {
        "name": skill_dir.name,
        "source": skill_dir,
        "capabilities": result["declared"],
        "blocking": blocking,
        "digest_ok": digest_ok,
        "digest": digest_detail,
    }


def is_replaceable_skill_dir(dest: Path, target_dir: Path) -> Tuple[bool, str]:
    """
    Decide whether `dest` may be deleted and replaced.

    Guarded deliberately: this function stands between a typo and an
    rmtree in the user's home directory. A path is replaceable only if it
    sits directly inside the resolved target directory, is a real directory
    rather than a symlink, and actually looks like a skill.
    """
    # Checked before resolving: resolve() follows the link, which would both
    # hide that a link was involved and, for a link pointing at a sibling
    # inside the target directory, make the containment check below pass.
    if dest.is_symlink():
        return False, "destination is a symlink; refusing to follow it"

    try:
        resolved_dest = dest.resolve()
        resolved_target = target_dir.resolve()
    except OSError as exc:
        return False, f"path could not be resolved ({exc})"

    if resolved_dest.parent != resolved_target:
        return False, "destination is not directly inside the target directory"
    if not resolved_dest.is_dir():
        return False, "destination exists but is not a directory"
    if not (resolved_dest / "SKILL.md").exists():
        return False, "destination has no SKILL.md, so it is not a skill this tool installed"
    return True, "existing skill directory"


def format_capabilities(caps: Dict[str, str]) -> str:
    return ", ".join(f"{key}={caps[key]}" for key in CAPABILITY_LADDERS)


def main() -> None:
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Install 1000x Agent Skills to local agent platforms.",
        epilog="Previews by default; pass --apply to write.",
    )
    parser.add_argument("--target", choices=sorted(TARGETS), required=True,
                        help="Target agent platform.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--skill", type=str, help="Install one named skill.")
    selection.add_argument("--all", action="store_true", help="Install every skill.")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write. Without this, nothing is modified.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Explicitly preview (the default; kept for clarity in scripts).")
    parser.add_argument("--skip-safety-audit", action="store_true",
                        help="Install even if the safety audit fails. Review the findings first.")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply are mutually exclusive.")

    repo_root = Path(__file__).resolve().parent.parent
    target_dir = get_target_path(args.target)
    allowlist = load_allowlist(repo_root)

    candidates = discover_installable(repo_root)
    if args.skill:
        candidates = [s for s in candidates if s.name == args.skill]
        if not candidates:
            raise SystemExit(f"[ERROR] No skill named {args.skill!r} under skills/.")
    if not candidates:
        raise SystemExit("[ERROR] No installable skills found under skills/.")

    mode = "APPLY" if args.apply else "PREVIEW"
    print("=" * 78)
    print(f" Install to {TARGETS[args.target][0]}  [{mode}]")
    print(f" Destination: {target_dir}")
    print("=" * 78)

    plan, refused = [], []
    for skill_dir in candidates:
        info = assess(skill_dir, repo_root, allowlist)
        dest = target_dir / skill_dir.name

        action, note = "create", ""
        if dest.exists():
            replaceable, why = is_replaceable_skill_dir(dest, target_dir)
            action, note = ("replace", why) if replaceable else ("refuse", why)

        blocked = bool(info["blocking"]) and not args.skip_safety_audit
        if blocked or action == "refuse":
            refused.append((info, dest, action, note))
        else:
            plan.append((info, dest, action, note))

        print(f"\n  {skill_dir.name}")
        print(f"    capabilities: {format_capabilities(info['capabilities'])}")
        print(f"    digest:       {info['digest'] if info['digest_ok'] else 'MISMATCH -- ' + str(info['digest'])}")
        print(f"    safety audit: {'FAIL (' + str(len(info['blocking'])) + ' blocking)' if info['blocking'] else 'pass'}")
        if action == "refuse":
            print(f"    -> REFUSED: {note}")
        elif blocked:
            print("    -> REFUSED: safety audit failed. Run "
                  "`python scripts/audit_skill_safety.py` for detail.")
        else:
            print(f"    -> would {action}{' (' + note + ')' if note else ''}: {dest}")
        if not info["digest_ok"]:
            print("    !! content digest does not match its attestation; "
                  "the files have changed since they were attested.")

    print("\n" + "-" * 78)
    if not args.apply:
        print(f" PREVIEW ONLY -- nothing was written. {len(plan)} skill(s) ready, "
              f"{len(refused)} refused.")
        print(" Re-run with --apply to install.")
        sys.exit(1 if refused else 0)

    installed = 0
    for info, dest, action, _ in plan:
        if action == "replace":
            shutil.rmtree(dest)
        shutil.copytree(info["source"], dest)
        print(f" [OK] {action}d {info['name']} -> {dest}")
        installed += 1

    print(f"\n Installed {installed} skill(s) into {target_dir}.")
    if refused:
        print(f" {len(refused)} skill(s) refused; see the report above.")
    sys.exit(1 if refused else 0)


if __name__ == "__main__":
    main()
