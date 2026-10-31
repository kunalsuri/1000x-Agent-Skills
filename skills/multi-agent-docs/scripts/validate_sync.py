#!/usr/bin/env python3
"""
Comprehensive Sync & Equivalence Validator for multi-agent-docs.
Deterministically verifies that CLAUDE.md and AGENTS.md exist, contain
companion sync markers, maintain full command parity, structural section
symmetry, directory architecture equivalence, subfolder synchronization,
and textual Jaccard similarity metrics.
"""

import sys
import os
import re
import argparse
from pathlib import Path

def extract_commands(text: str) -> set:
    """Extracts inline code commands under command sections or command bullet items."""
    commands = set()
    in_command_section = False

    cmd_bullet_re = re.compile(
        r"^\s*[-*]\s*(?:\*\*)?(?:Build|Test|Lint|Run|Compile|Package|Clean|Format|Dev|Start)(?:\*\*)?:\s*(.+)$",
        re.IGNORECASE
    )
    cmd_header_re = re.compile(
        r"^##+\s+.*(?:command|build|test|script|run).*",
        re.IGNORECASE
    )
    any_header_re = re.compile(r"^##+\s+")

    for line in text.splitlines():
        stripped = line.strip()
        if any_header_re.match(stripped):
            in_command_section = bool(cmd_header_re.match(stripped))
            continue

        # If line explicitly matches a command bullet pattern
        bullet_match = cmd_bullet_re.match(stripped)
        if bullet_match:
            content_to_scan = bullet_match.group(1)
            matches = re.findall(r"`([^`]+)`", content_to_scan)
            for m in matches:
                m_clean = m.strip()
                if not m_clean.startswith("TODO"):
                    commands.add(m_clean)
        elif in_command_section:
            # Inside a dedicated command section, check bullet items with code spans
            if stripped.startswith(("-", "*", "1.", "2.", "3.", "4.")):
                matches = re.findall(r"`([^`]+)`", stripped)
                for m in matches:
                    m_clean = m.strip()
                    if not m_clean.startswith("TODO") and not m_clean.endswith((".md", ".json", ".yaml", ".yml", ".toml")):
                        commands.add(m_clean)
    return commands

def extract_arch_paths(text: str) -> set:
    """Extracts documented directory paths under architecture sections."""
    paths = set()
    in_arch = False
    arch_header_re = re.compile(r"^##+\s+.*(?:architecture|director).*", re.IGNORECASE)
    any_header_re = re.compile(r"^##+\s+")

    for line in text.splitlines():
        stripped = line.strip()
        if any_header_re.match(stripped):
            in_arch = bool(arch_header_re.match(stripped))
            continue
        if in_arch and stripped.startswith(("-", "*")):
            matches = re.findall(r"`([^`]+)`", stripped)
            for m in matches:
                if "/" in m or m.endswith(("/", "\\")):
                    paths.add(m.replace("\\", "/"))
    return paths

def compute_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Computes word-level Jaccard similarity between two text documents."""
    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)

def validate_sync(target_path: Path, min_similarity: float = 0.70) -> dict:
    errors = []
    warnings = []

    claude_md = target_path / "CLAUDE.md"
    agents_md = target_path / "AGENTS.md"
    claude_dir = target_path / ".claude"
    agents_dir = target_path / ".agents"
    agents_sub_md = target_path / ".agents" / "AGENTS.md"

    # 1. Check file existence
    if not claude_md.exists():
        errors.append("Missing CLAUDE.md at repository root.")
    if not agents_md.exists():
        errors.append("Missing AGENTS.md at repository root.")

    # 2. Check directory existence
    if not claude_dir.exists():
        warnings.append("Missing .claude/ directory scaffolding.")
    if not agents_dir.exists():
        warnings.append("Missing .agents/ directory scaffolding.")

    if not claude_md.exists() or not agents_md.exists():
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
            "synced_commands": [],
            "synced_paths": [],
            "similarity": 0.0
        }

    claude_text = claude_md.read_text(encoding="utf-8")
    agents_text = agents_md.read_text(encoding="utf-8")

    # 3. Check companion comments
    if "Companion to AGENTS.md" not in claude_text:
        warnings.append("CLAUDE.md is missing companion reference: '<!-- Companion to AGENTS.md ... -->'")
    if "Companion to CLAUDE.md" not in agents_text:
        warnings.append("AGENTS.md is missing companion reference: '<!-- Companion to CLAUDE.md ... -->'")

    # 4. Check command parity
    claude_cmds = extract_commands(claude_text)
    agents_cmds = extract_commands(agents_text)

    claude_only_cmds = claude_cmds - agents_cmds
    agents_only_cmds = agents_cmds - claude_cmds

    if claude_only_cmds:
        errors.append(f"Commands in CLAUDE.md but missing from AGENTS.md: {', '.join(sorted(claude_only_cmds))}")
    if agents_only_cmds:
        errors.append(f"Commands in AGENTS.md but missing from CLAUDE.md: {', '.join(sorted(agents_only_cmds))}")

    # 5. Check Architecture directory paths parity
    claude_paths = extract_arch_paths(claude_text)
    agents_paths = extract_arch_paths(agents_text)

    paths_in_claude_only = claude_paths - agents_paths
    paths_in_agents_only = agents_paths - claude_paths

    if paths_in_claude_only:
        warnings.append(f"Directory paths in CLAUDE.md but missing in AGENTS.md: {', '.join(sorted(paths_in_claude_only))}")
    if paths_in_agents_only:
        warnings.append(f"Directory paths in AGENTS.md but missing in CLAUDE.md: {', '.join(sorted(paths_in_agents_only))}")

    # 6. Check .agents/AGENTS.md synchronization
    if agents_sub_md.exists():
        sub_text = agents_sub_md.read_text(encoding="utf-8")
        if sub_text.strip() != agents_text.strip():
            warnings.append(".agents/AGENTS.md differs from root AGENTS.md. Keep them synchronized.")

    # 7. Check placeholder presence
    if "TODO:" in claude_text or "TODO:" in agents_text:
        warnings.append("Unresolved 'TODO:' placeholders found. LLM semantic refinement recommended.")

    # 8. Compute Jaccard Textual Similarity
    similarity = compute_jaccard_similarity(claude_text, agents_text)
    if similarity < min_similarity:
        warnings.append(
            f"Low textual Jaccard similarity ({similarity * 100:.1f}% < {min_similarity * 100:.1f}%). "
            "Files may have drifted significantly."
        )

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "synced_commands": sorted(list(claude_cmds.intersection(agents_cmds))),
        "synced_paths": sorted(list(claude_paths.intersection(agents_paths))),
        "similarity": similarity
    }

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Validate synchronization between CLAUDE.md and AGENTS.md.")
    parser.add_argument("--target", default=".", help="Target repository root path (default: current working directory)")
    parser.add_argument("--min-similarity", type=float, default=0.70, help="Minimum Jaccard similarity threshold for warning (default: 0.70)")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    print(f"[*] Validating multi-agent docs synchronization at: {target_path}")

    res = validate_sync(target_path, min_similarity=args.min_similarity)
    print("=" * 60)
    print(f"Sync Validation Status: [{res['status']}]")
    print("=" * 60)

    if res.get("synced_commands"):
        print(f"[+] Verified in-sync commands: {', '.join(res['synced_commands'])}")
    if res.get("synced_paths"):
        print(f"[+] Verified in-sync architecture paths: {', '.join(res['synced_paths'])}")
    
    sim_pct = res.get("similarity", 0.0) * 100
    sim_status = "PASS" if res.get("similarity", 0.0) >= args.min_similarity else "WARN"
    print(f"[+] Textual Jaccard Similarity: {sim_pct:.1f}% [{sim_status} (Threshold: >= {args.min_similarity * 100:.1f}%)]")

    for warn in res["warnings"]:
        print(f"[!] Warning: {warn}")

    for err in res["errors"]:
        print(f"[x] Error: {err}")

    if res["status"] == "FAIL":
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
