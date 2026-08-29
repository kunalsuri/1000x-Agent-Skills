#!/usr/bin/env python3
"""
Deterministic Scaffolding Script for multi-agent-docs.
Creates standard directory structures (.claude/, .agents/, .agents/rules/),
inspects repository manifests to extract ground-truth build and test commands,
and scaffolds synchronized CLAUDE.md and AGENTS.md baseline files.
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path

IGNORED_DIRS = {
    ".git", ".github", ".agents", ".claude", ".vscode", ".idea",
    "node_modules", "venv", ".venv", "env", ".env", "__pycache__",
    "dist", "build", "target", "vendor", "coverage", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".next", ".nuxt", ".turbo", "bin", "obj"
}

def detect_manifests(repo_root: Path) -> dict:
    """Inspects repo root and subdirectories to detect project type and build/test commands."""
    facts = {
        "project_types": [],
        "commands": {
            "build": [],
            "test": [],
            "lint": [],
            "run": []
        },
        "key_paths": []
    }

    # 1. Node.js / TypeScript / JavaScript
    pkg_json = repo_root / "package.json"
    if pkg_json.exists():
        facts["project_types"].append("Node.js")
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            
            # Determine package manager
            pkg_mgr = "npm"
            if (repo_root / "pnpm-lock.yaml").exists():
                pkg_mgr = "pnpm"
            elif (repo_root / "yarn.lock").exists():
                pkg_mgr = "yarn"
            elif (repo_root / "bun.lockb").exists() or (repo_root / "bun.lock").exists():
                pkg_mgr = "bun"

            if "build" in scripts:
                facts["commands"]["build"].append(f"{pkg_mgr} run build")
            if "test" in scripts:
                facts["commands"]["test"].append(f"{pkg_mgr} test")
            if "lint" in scripts:
                facts["commands"]["lint"].append(f"{pkg_mgr} run lint")
            if "dev" in scripts:
                facts["commands"]["run"].append(f"{pkg_mgr} run dev")
            elif "start" in scripts:
                facts["commands"]["run"].append(f"{pkg_mgr} start")
        except Exception:
            pass

    # 2. Python
    pyproject = repo_root / "pyproject.toml"
    setup_py = repo_root / "setup.py"
    req_txt = repo_root / "requirements.txt"
    if pyproject.exists() or setup_py.exists() or req_txt.exists():
        facts["project_types"].append("Python")
        
        # Test commands
        if (repo_root / "tests").exists() or (repo_root / "test").exists():
            facts["commands"]["test"].append("pytest")
        else:
            facts["commands"]["test"].append("python -m unittest discover")

        # Package manager / virtualenv
        if (repo_root / "uv.lock").exists():
            facts["commands"]["build"].append("uv sync")
        elif (repo_root / "poetry.lock").exists():
            facts["commands"]["build"].append("poetry install")
        elif req_txt.exists():
            facts["commands"]["build"].append("pip install -r requirements.txt")

        # Linting
        if (repo_root / "ruff.toml").exists() or (repo_root / ".ruff.toml").exists():
            facts["commands"]["lint"].append("ruff check .")
        elif (repo_root / ".flake8").exists():
            facts["commands"]["lint"].append("flake8")

    # 3. Rust
    cargo_toml = repo_root / "Cargo.toml"
    if cargo_toml.exists():
        facts["project_types"].append("Rust")
        facts["commands"]["build"].append("cargo build")
        facts["commands"]["test"].append("cargo test")
        facts["commands"]["lint"].append("cargo clippy")

    # 4. Go
    go_mod = repo_root / "go.mod"
    if go_mod.exists():
        facts["project_types"].append("Go")
        facts["commands"]["build"].append("go build ./...")
        facts["commands"]["test"].append("go test ./...")
        facts["commands"]["lint"].append("golangci-lint run")

    # 5. Java / Kotlin
    pom_xml = repo_root / "pom.xml"
    gradle_build = repo_root / "build.gradle"
    gradle_kts = repo_root / "build.gradle.kts"
    if pom_xml.exists():
        facts["project_types"].append("Java (Maven)")
        facts["commands"]["build"].append("mvn clean compile")
        facts["commands"]["test"].append("mvn test")
    elif gradle_build.exists() or gradle_kts.exists():
        facts["project_types"].append("Java/Kotlin (Gradle)")
        facts["commands"]["build"].append("./gradlew build")
        facts["commands"]["test"].append("./gradlew test")

    # 6. Make / CMake
    makefile = repo_root / "Makefile"
    if makefile.exists():
        facts["project_types"].append("Makefile")
        if not facts["commands"]["build"]:
            facts["commands"]["build"].append("make")
        if not facts["commands"]["test"]:
            facts["commands"]["test"].append("make test")

    # Scan top-level directories, filtering ignored/vendor folders
    for child in sorted(repo_root.iterdir()):
        if child.is_dir() and not child.name.startswith(".") and child.name not in IGNORED_DIRS:
            facts["key_paths"].append(f"{child.name}/")

    return facts

def generate_claude_md(facts: dict) -> str:
    build_cmds = "\n".join([f"- **Build**: `{cmd}`" for cmd in facts["commands"]["build"]]) or "- **Build**: `TODO: Add build command`"
    test_cmds = "\n".join([f"- **Test**: `{cmd}`" for cmd in facts["commands"]["test"]]) or "- **Test**: `TODO: Add test command`"
    lint_cmds = "\n".join([f"- **Lint**: `{cmd}`" for cmd in facts["commands"]["lint"]]) or "- **Lint**: `TODO: Add lint command`"
    run_cmds = "\n".join([f"- **Run**: `{cmd}`" for cmd in facts["commands"]["run"]]) if facts["commands"]["run"] else ""

    arch_items = "\n".join([f"- `{path}`: [TODO: Describe module role]" for path in facts["key_paths"][:8]]) or "- `src/`: [TODO: Core source code]"

    content = f"""<!-- Companion to AGENTS.md — update both together to prevent instruction drift. -->

# Claude Code Project Guidelines (CLAUDE.md)

## Repository Overview
- **Project Type**: {', '.join(facts['project_types']) if facts['project_types'] else 'Multi-Agent Project'}
- **Architecture**: Modular multi-agent repository configured for Antigravity, Claude Code, Cursor, and Codex.

## Essential Commands
{build_cmds}
{test_cmds}
{lint_cmds}
{run_cmds}

## Directory Architecture
{arch_items}

## Development Guidelines & Agent Best Practices
- **Atomic Modifications**: Make small, verifiable edits using precision diff tools.
- **Specification Compliance**: Enforce strict YAML frontmatter, line limits, and documentation standards.
- **Verification**: Run build and test validation commands before submitting changes.
- **Formatting & Fidelity**: Preserve existing docstrings, typing, license headers, and naming conventions.
- **Cross-Agent Sync**: Keep `CLAUDE.md` and `AGENTS.md` strictly synchronized whenever commands or conventions change.

## Tool-Specific Directives (Claude Code)
- Subagent memory and rules are organized under `.claude/`.
- Refer to `AGENTS.md` for tool-agnostic agent directives.
"""
    return content.strip() + "\n"

def generate_agents_md(facts: dict) -> str:
    build_cmds = "\n".join([f"- **Build**: `{cmd}`" for cmd in facts["commands"]["build"]]) or "- **Build**: `TODO: Add build command`"
    test_cmds = "\n".join([f"- **Test**: `{cmd}`" for cmd in facts["commands"]["test"]]) or "- **Test**: `TODO: Add test command`"
    lint_cmds = "\n".join([f"- **Lint**: `{cmd}`" for cmd in facts["commands"]["lint"]]) or "- **Lint**: `TODO: Add lint command`"
    run_cmds = "\n".join([f"- **Run**: `{cmd}`" for cmd in facts["commands"]["run"]]) if facts["commands"]["run"] else ""

    arch_items = "\n".join([f"- `{path}`: [TODO: Describe module role]" for path in facts["key_paths"][:8]]) or "- `src/`: [TODO: Core source code]"

    content = f"""<!-- Companion to CLAUDE.md — update both together to prevent instruction drift. -->

# Project Directives & Conventions (AGENTS.md)

## Repository Overview
- **Project Type**: {', '.join(facts['project_types']) if facts['project_types'] else 'Multi-Agent Project'}
- **Architecture**: Modular multi-agent repository configured for Antigravity, Claude Code, Cursor, and Codex.

## Essential Commands
{build_cmds}
{test_cmds}
{lint_cmds}
{run_cmds}

## Directory Architecture
{arch_items}

## Development Guidelines & Agent Best Practices
- **Atomic Modifications**: Make small, verifiable edits using precision diff tools.
- **Specification Compliance**: Enforce strict YAML frontmatter, line limits, and documentation standards.
- **Verification**: Run build and test validation commands before submitting changes.
- **Formatting & Fidelity**: Preserve existing docstrings, typing, license headers, and naming conventions.
- **Cross-Agent Sync**: Keep `CLAUDE.md` and `AGENTS.md` strictly synchronized whenever commands or conventions change.

## Tool-Specific Directives (Antigravity / Cursor / Codex)
- Workflows, custom skills, and rules are organized under `.agents/` (`.agents/skills/`, `.agents/rules/`).
- Refer to `CLAUDE.md` for Claude Code companion configurations.
"""
    return content.strip() + "\n"

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Deterministic Scaffolder for multi-agent docs and directories.")
    parser.add_argument("--target", default=".", help="Target repository root path (default: current working directory)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing CLAUDE.md and AGENTS.md if they exist")
    parser.add_argument("--dry-run", action="store_true", help="Preview planned directory creations and files without writing")

    args = parser.parse_args()
    target_path = Path(args.target).resolve()

    if not target_path.exists():
        print(f"[ERROR] Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Introspecting repository at: {target_path}")
    facts = detect_manifests(target_path)
    print(f"[*] Detected project types: {', '.join(facts['project_types']) if facts['project_types'] else 'Generic'}")

    dirs_to_create = [
        target_path / ".claude",
        target_path / ".agents",
        target_path / ".agents" / "rules"
    ]

    files_to_create = {
        target_path / "CLAUDE.md": generate_claude_md(facts),
        target_path / "AGENTS.md": generate_agents_md(facts),
        target_path / ".agents" / "AGENTS.md": generate_agents_md(facts)
    }

    report = {
        "target": str(target_path),
        "detected_types": facts["project_types"],
        "detected_commands": facts["commands"],
        "created_directories": [],
        "created_files": [],
        "skipped_files": []
    }

    # Create directories
    for d in dirs_to_create:
        rel_dir = d.relative_to(target_path).as_posix()
        if not d.exists():
            if not args.dry_run:
                d.mkdir(parents=True, exist_ok=True)
            report["created_directories"].append(rel_dir)
            print(f"[+] Directory created: {rel_dir}")
        else:
            print(f"[-] Directory already exists: {rel_dir}")

    # Create files
    for file_path, content in files_to_create.items():
        rel_path = file_path.relative_to(target_path).as_posix()
        if file_path.exists() and not args.force:
            report["skipped_files"].append(rel_path)
            print(f"[-] File already exists (skipped, use --force to overwrite): {rel_path}")
        else:
            if not args.dry_run:
                file_path.write_text(content, encoding="utf-8")
            report["created_files"].append(rel_path)
            print(f"[+] File generated: {rel_path}")

    print("\n" + "=" * 60)
    print("Scaffolding complete. Next step: LLM semantic refinement.")
    print("=" * 60)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
