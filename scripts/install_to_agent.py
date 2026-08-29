#!/usr/bin/env python3
"""
Install / Export Agent Skills to Claude Code, Google Antigravity, or Cursor.
"""

import sys
import os
import shutil
import argparse
from pathlib import Path

def get_target_path(target: str) -> Path:
    home = Path.home()
    if target == "antigravity":
        # Global Antigravity skills path
        return home / ".gemini" / "config" / "skills"
    elif target == "claude":
        # Claude Code global skills path
        return home / ".claude" / "skills"
    elif target == "cursor":
        # Current workspace cursor rules
        return Path.cwd() / ".cursor" / "rules"
    else:
        raise ValueError(f"Unknown target: {target}")

def install_skills(repo_root: Path, target: str, skill_name: str = None):
    target_dir = get_target_path(target)
    target_dir.mkdir(parents=True, exist_ok=True)

    skills_root = repo_root / "skills"
    installed_count = 0

    for cat_dir in sorted(skills_root.iterdir()):
        if not cat_dir.is_dir():
            continue
        for s_dir in sorted(cat_dir.iterdir()):
            if not s_dir.is_dir() or not (s_dir / "SKILL.md").exists():
                continue
            
            if skill_name and s_dir.name != skill_name:
                continue

            dest = target_dir / s_dir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(s_dir, dest)
            print(f"✅ Installed '{s_dir.name}' -> {dest}")
            installed_count += 1

    print(f"\n✨ Done! Installed {installed_count} skill(s) into '{target}' ({target_dir}).")

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Install 1000x Agent Skills to local agent platforms.")
    parser.add_argument("--target", choices=["antigravity", "claude", "cursor"], required=True, help="Target agent platform.")
    parser.add_argument("--skill", type=str, default=None, help="Name of specific skill to install (or omit for all).")
    parser.add_argument("--all", action="store_true", help="Install all available skills.")

    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    install_skills(repo_root, args.target, args.skill)

if __name__ == "__main__":
    main()
