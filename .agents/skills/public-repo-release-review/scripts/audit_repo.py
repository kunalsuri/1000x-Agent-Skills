#!/usr/bin/env python3
"""
public-repo-release-review: Pre-Flight Codebase & Governance Audit Tool.
Performs deterministic static analysis on a target repository before public GitHub release:
- Secret & Credential Leak Detection
- Open-Source Governance File Verification (SECURITY.md, COLLABORATORS.md, CITATION.cff, etc.)
- Markdown Link & Reference Integrity
- Codebase & Gitignore Hygiene
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Secret Regex Signatures
SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "Private Cryptographic Key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token (classic)"),
    (re.compile(r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"), "GitHub Fine-Grained Token"),
    (re.compile(r"sk-[a-zA-Z0-9]{32,}"), "OpenAI API Key signature"),
    (re.compile(r"sk-ant-[a-zA-Z0-9_\-]{32,}"), "Anthropic API Key signature"),
    (re.compile(r"(?i)(?:api_key|secret_key|auth_token)\s*=\s*['\"][a-zA-Z0-9_\-]{24,}['\"]"), "Hardcoded High-Entropy Secret"),
]

# Sensitive File Patterns
SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.secret",
    "id_rsa", "id_ecdsa", "id_ed25519",
    "credentials.json", "service_account.json", "auth.json"
}

# Essential Governance Files
GOVERNANCE_CHECKS = {
    "LICENSE": {
        "patterns": ["LICENSE", "LICENSE.md", "LICENSE.txt"],
        "required": True,
        "desc": "Open Source License (SPDX conformant)"
    },
    "README.md": {
        "patterns": ["README.md", "README"],
        "required": True,
        "desc": "Repository Readme & Architecture Overview"
    },
    "SECURITY.md": {
        "patterns": ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"],
        "required": True,
        "desc": "Security Policy & Responsible Disclosure"
    },
    "COLLABORATORS.md": {
        "patterns": ["COLLABORATORS.md", "CONTRIBUTING.md", "docs/COLLABORATORS.md", "docs/CONTRIBUTING.md"],
        "required": True,
        "desc": "Collaborator / Contribution Guidelines"
    },
    "CITATION.cff": {
        "patterns": ["CITATION.cff", "CITATIONS.md", "docs/CITATION.cff"],
        "required": True,
        "desc": "Software / Academic Citation Metadata"
    },
    "CODE_OF_CONDUCT.md": {
        "patterns": ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md", "docs/CODE_OF_CONDUCT.md"],
        "required": True,
        "desc": "Code of Conduct (Contributor Covenant)"
    },
    "SUPPORT.md": {
        "patterns": ["SUPPORT.md", ".github/SUPPORT.md", "docs/SUPPORT.md"],
        "required": False,
        "desc": "Support Guidelines & Help Resources"
    },
    ".gitignore": {
        "patterns": [".gitignore"],
        "required": True,
        "desc": "Git Ignore File"
    },
}

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache",
    ".venv", "venv", "env", "dist", "build", ".egg-info", ".idea", ".vscode"
}

TEMPLATE_DIRS = {
    "skill-creator", "templates"
}

def scan_secrets(target_dir: Path) -> List[Dict[str, Any]]:
    findings = []
    
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(target_dir).as_posix()
            
            # Check sensitive filename
            if file.lower() in SENSITIVE_FILENAMES or file.endswith(".pem") or file.endswith(".key"):
                findings.append({
                    "type": "sensitive_file",
                    "path": rel_path,
                    "severity": "HIGH",
                    "message": f"Sensitive file '{file}' found in workspace. Ensure it is gitignored and contains no real credentials."
                })

            # Check contents of text files < 2MB
            if file_path.stat().st_size > 2 * 1024 * 1024:
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    # Skip test-cases or sample docs that mention signatures as examples
                    if "AKIAIOSFODNN7EXAMPLE" in line or "sk-example" in line or "sk-ant-example" in line:
                        continue
                    for pattern, secret_type in SECRET_PATTERNS:
                        if pattern.search(line):
                            findings.append({
                                "type": "secret_leak",
                                "path": rel_path,
                                "line": line_idx,
                                "severity": "CRITICAL",
                                "message": f"Potential {secret_type} match on line {line_idx}."
                            })
            except Exception:
                pass
                
    return findings

def check_governance(target_dir: Path) -> Dict[str, Any]:
    status = {}
    for name, spec in GOVERNANCE_CHECKS.items():
        found = False
        matched_path = None
        for p in spec["patterns"]:
            candidate = target_dir / p
            if candidate.exists() and candidate.is_file():
                found = True
                matched_path = p
                break
        status[name] = {
            "found": found,
            "path": matched_path,
            "required": spec["required"],
            "desc": spec["desc"]
        }
    return status

def check_markdown_links(target_dir: Path) -> List[Dict[str, Any]]:
    broken_links = []
    link_pattern = re.compile(r'(?<!`)(?:(?<=\s)|(?<=^))\[([^\]]+)\]\(([^)]+)\)')
    
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if not file.endswith(".md"):
                continue
            md_path = Path(root) / file
            rel_md = md_path.relative_to(target_dir).as_posix()
            
            # Skip template files in skill-creator or templates dir
            if any(t_dir in rel_md.split("/") for t_dir in TEMPLATE_DIRS):
                continue
            
            try:
                content = md_path.read_text(encoding="utf-8", errors="ignore")
                in_code_block = False
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        continue
                    
                    # Search for markdown links outside code blocks
                    for match in link_pattern.finditer(line):
                        link_target = match.group(2).strip()
                        
                        # Skip external URLs, mailto, anchor fragments
                        if link_target.startswith(("http://", "https://", "mailto:", "#")):
                            continue
                        
                        # Handle file:/// URLs or relative paths
                        clean_target = link_target.split("#")[0]
                        if not clean_target:
                            continue
                            
                        if clean_target.startswith("file:///"):
                            resolved_path = Path(clean_target.replace("file:///", "").replace("file://", ""))
                        else:
                            resolved_path = (md_path.parent / clean_target).resolve()
                            
                        if not resolved_path.exists():
                            broken_links.append({
                                "source_file": rel_md,
                                "line": line_idx,
                                "target": link_target,
                                "message": f"Broken internal link to '{link_target}' in {rel_md}:{line_idx}"
                            })
            except Exception:
                pass
                
    return broken_links

def check_codebase_hygiene(target_dir: Path) -> List[Dict[str, Any]]:
    issues = []
    junk_files = {".ds_store", "thumbs.db", "desktop.ini"}
    
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(target_dir).as_posix()
            
            # Junk files check
            if file.lower() in junk_files:
                issues.append({
                    "path": rel_path,
                    "type": "os_junk",
                    "severity": "LOW",
                    "message": f"OS junk file '{file}' should be removed and gitignored."
                })
                
            # Large binary blobs check (>5MB)
            if file_path.stat().st_size > 5 * 1024 * 1024 and not file.endswith((".zip", ".tar.gz", ".onnx")):
                issues.append({
                    "path": rel_path,
                    "type": "large_file",
                    "severity": "WARN",
                    "message": f"Large file '{file}' ({file_path.stat().st_size / (1024*1024):.1f} MB). Consider Git LFS."
                })
                
    return issues

def print_colored_report(target: Path, secrets: list, gov: dict, broken_links: list, hygiene: list, json_mode: bool) -> int:
    missing_required_gov = [k for k, v in gov.items() if v["required"] and not v["found"]]
    missing_optional_gov = [k for k, v in gov.items() if not v["required"] and not v["found"]]
    
    critical_errors = len(secrets) + len(missing_required_gov) + len(broken_links)
    warnings = len(missing_optional_gov) + len(hygiene)
    
    # Calculate score
    score = 100
    score -= (len(secrets) * 25)
    score -= (len(missing_required_gov) * 15)
    score -= (len(broken_links) * 5)
    score -= (len(missing_optional_gov) * 5)
    score -= (len(hygiene) * 2)
    score = max(0, min(100, score))
    
    if score >= 98:
        grade = "A+ (99.999% Ready for Public Release)"
        grade_color = GREEN
    elif score >= 90:
        grade = "A (Public Release Candidate)"
        grade_color = GREEN
    elif score >= 80:
        grade = "B (Minor Governance/Hygiene Deficiencies)"
        grade_color = YELLOW
    else:
        grade = "FAIL (Critical Security or Missing Requirements)"
        grade_color = RED

    if json_mode:
        data = {
            "target": str(target),
            "health_grade": grade,
            "readiness_score": score,
            "secrets_detected": secrets,
            "governance_status": gov,
            "broken_links": broken_links,
            "hygiene_issues": hygiene,
            "status": "PASS" if critical_errors == 0 else "FAIL"
        }
        print(json.dumps(data, indent=2))
        return 0 if critical_errors == 0 else 1

    print("=" * 72)
    print(f" {BOLD}🔍 [PUBLIC REPO RELEASE REVIEW] Pre-Flight Codebase Audit{RESET}")
    print("=" * 72)
    print(f" Target Workspace : {CYAN}{target.resolve()}{RESET}")
    print(f" Readiness Score  : {grade_color}{score}/100{RESET} — {grade_color}{grade}{RESET}")
    print("-" * 72)

    # 1. Security & Secrets
    print(f"\n{BOLD}1. 🛡️ Secret & Credential Leak Scan{RESET}")
    if not secrets:
        print(f"  {GREEN}[PASS]{RESET} 0 secrets or sensitive credential files detected.")
    else:
        for s in secrets:
            sev_color = RED if s["severity"] == "CRITICAL" else YELLOW
            print(f"  {sev_color}[{s['severity']}]{RESET} {s['path']}: {s['message']}")

    # 2. Governance Files
    print(f"\n{BOLD}2. 📜 Open-Source Governance & Metadata{RESET}")
    for name, item in gov.items():
        if item["found"]:
            print(f"  {GREEN}[PASS]{RESET} {name:<18} -> Found at {CYAN}{item['path']}{RESET} ({item['desc']})")
        else:
            if item["required"]:
                print(f"  {RED}[FAIL]{RESET} {name:<18} -> {RED}MISSING{RESET} (Required: {item['desc']})")
            else:
                print(f"  {YELLOW}[WARN]{RESET} {name:<18} -> Optional (Recommended: {item['desc']})")

    # 3. Link Integrity
    print(f"\n{BOLD}3. 🔗 Markdown Link & Reference Integrity{RESET}")
    if not broken_links:
        print(f"  {GREEN}[PASS]{RESET} All internal relative Markdown links resolved successfully.")
    else:
        for b in broken_links:
            print(f"  {RED}[FAIL]{RESET} {b['source_file']}:{b['line']} -> {b['message']}")

    # 4. Codebase Hygiene
    print(f"\n{BOLD}4. 🧹 Codebase Hygiene & Artifacts{RESET}")
    if not hygiene:
        print(f"  {GREEN}[PASS]{RESET} Workspace is free from OS junk and unmanaged binary blobs.")
    else:
        for h in hygiene:
            print(f"  {YELLOW}[WARN]{RESET} {h['path']} -> {h['message']}")

    print("\n" + "=" * 72)
    if critical_errors == 0:
        print(f" {GREEN}{BOLD}✨ CERTIFICATION PASSED:{RESET} Repository meets 99.999% public release standards!")
    else:
        print(f" {RED}{BOLD}❌ CERTIFICATION BLOCKED:{RESET} Found {critical_errors} critical issue(s). Resolve before pushing to public GitHub.")
    print("=" * 72 + "\n")

    return 0 if critical_errors == 0 else 1

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Audit a codebase before publishing as a public GitHub repository.")
    parser.add_argument("--target", type=str, default=".", help="Target repository directory (default: current directory)")
    parser.add_argument("--strict", action="store_true", help="Exit with error if any warning is present.")
    parser.add_argument("--json", action="store_true", help="Output results in structured JSON format.")

    args = parser.parse_args()
    target_path = Path(args.target).resolve()

    if not target_path.exists() or not target_path.is_dir():
        print(f"{RED}[ERROR] Target directory does not exist: {target_path}{RESET}")
        sys.exit(1)

    secrets = scan_secrets(target_path)
    gov = check_governance(target_path)
    broken_links = check_markdown_links(target_path)
    hygiene = check_codebase_hygiene(target_path)

    exit_code = print_colored_report(target_path, secrets, gov, broken_links, hygiene, args.json)
    if args.strict and (len(hygiene) > 0 or not all(v["found"] for v in gov.values())):
        sys.exit(1)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
