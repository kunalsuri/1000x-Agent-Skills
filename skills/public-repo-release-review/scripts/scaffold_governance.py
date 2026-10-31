#!/usr/bin/env python3
"""
Scaffolding CLI for open-source repository governance and release compliance.
Generates:
- SECURITY.md (Vulnerability reporting policy)
- COLLABORATORS.md (Explicit collaboration policy: solo or community)
- CITATION.cff & CITATIONS.md (Academic and software citation metadata)
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- SUPPORT.md (Support guidelines)
- .github/ issue and pull request templates
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

SECURITY_TEMPLATE = """# 🛡️ Security Policy

## Supported Versions

We actively maintain and provide security updates for the current release stream:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

## Reporting a Vulnerability

We take the security and integrity of this project very seriously. If you discover a security vulnerability or sensitive information exposure, please **DO NOT** open a public issue.

### Private Reporting Channel
- **Contact**: [{EMAIL}](mailto:{EMAIL})
- **Subject Line**: `[SECURITY] Vulnerability Report - {REPO_NAME}`

### Responsible Disclosure Timeline
1. **Initial Acknowledgment**: Within **48 hours** of receiving your report.
2. **Assessment & Triage**: Within **7 days** with severity rating and remediation scope.
3. **Patch & Release**: Critical security fixes will be published in a coordinated minor/patch release.

Thank you for helping keep our software secure!
"""

COLLABORATORS_SOLO_TEMPLATE = """# 👥 Collaborator & Contribution Policy

## Project Status: Solo Maintainer / Closed Collaboration

This repository is actively developed, authored, and maintained exclusively by:

**{AUTHOR}** ([{EMAIL}](mailto:{EMAIL}))

---

### 🚫 Pull Requests & External Contributions
- **Current Status**: **External pull requests are currently NOT accepted.**
- **Rationale**: The project architecture, specifications, and core artifacts are undergoing focused stabilization. To ensure high conceptual integrity and compliance with strict verification standards, code additions are managed internally.
- Pull requests submitted by external accounts may be closed without review.

---

### 💬 Community Engagement & Bug Reports
While direct code modifications from external contributors are paused, community feedback and engagement are highly valued:

1. **🐛 Bug Reports**: If you discover a defect, bug, or regression, please file a detailed report via the [GitHub Issue Tracker](../../issues).
2. **💡 Feature Ideas & Discussion**: Use GitHub Issues or Discussions to propose new workflows, skills, or architecture enhancements.
3. **⭐ Star & Share**: Sharing and citing this project helps the ecosystem grow!

*This policy may be revisited in future major releases as community governance matures.*
"""

COLLABORATORS_OPEN_TEMPLATE = """# 👥 Contributing & Collaborator Guidelines

Thank you for your interest in contributing to **{REPO_NAME}**! We welcome community contributions, bug fixes, and improvements.

---

## 🚀 How to Contribute

1. **Check Existing Issues**: Before starting work, search existing issues and pull requests to avoid duplicated effort.
2. **Fork and Branch**: Create a feature branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Make Atomic Changes**: Keep your changes focused, testable, and documented.
4. **Run Verification & Tests**:
   Ensure all validation scripts and tests pass before submitting:
   ```bash
   python scripts/validate_skills.py
   ```
5. **Submit a Pull Request**: Open a PR with a clear title and detailed summary of changes.

---

## 📜 Code of Conduct
All contributors and maintainers are expected to adhere to our [Code of Conduct](./CODE_OF_CONDUCT.md).
"""

CITATION_CFF_TEMPLATE = """cff-version: 1.2.0
message: "If you use this software or agent skills in your research or tooling, please cite it as below."
authors:
  - family-names: "{AUTHOR_FAMILY}"
    given-names: "{AUTHOR_GIVEN}"
    email: "{EMAIL}"
    affiliation: "CEA List"
title: "{REPO_NAME}: The Capability-Declared, Attested & Evaluated Skills Suite for Autonomous AI Coding Agents"
version: 1.0.0
date-released: {RELEASE_DATE}
url: "https://github.com/kunalsuri/{REPO_NAME}"
license: "Apache-2.0"
keywords:
  - "agent-skills"
  - "autonomous-agents"
  - "claude-code"
  - "antigravity"
  - "ai-engineering"
  - "preflight-audit"
"""

CITATIONS_MD_TEMPLATE = r"""# 📑 Citation & Attribution

If you utilize **{REPO_NAME}** in academic publications, technical reports, benchmarks, or commercial AI agent tooling, please use the following citation formats:

---

### 📄 BibTeX
```bibtex
@software{suri2026agent_skills,
  author       = {{AUTHOR}},
  title        = {{{{REPO_NAME}: The Capability-Declared, Attested \& Evaluated Skills Suite for Autonomous AI Coding Agents}},
  month        = aug,
  year         = {YEAR},
  publisher    = {GitHub},
  journal      = {GitHub repository},
  howpublished = {\url{https://github.com/kunalsuri/{REPO_NAME}}}
}
```

---

### 📚 APA Format
> {AUTHOR}. ({YEAR}). *{REPO_NAME}: The Capability-Declared, Attested & Evaluated Skills Suite for Autonomous AI Coding Agents* (Version 1.0.0). GitHub. https://github.com/kunalsuri/{REPO_NAME}

---

### 📚 IEEE Format
> {AUTHOR}, "{REPO_NAME}: The Capability-Declared, Attested & Evaluated Skills Suite for Autonomous AI Coding Agents," GitHub repository, {YEAR}. [Online]. Available: https://github.com/kunalsuri/{REPO_NAME}
"""

CODE_OF_CONDUCT_TEMPLATE = """# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, caste, color, religion, or sexual
identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment for our
community include:

* Demonstrating empathy and kindness toward other people
* Being respectful of differing opinions, viewpoints, and experiences
* Giving and gracefully accepting constructive feedback
* Accepting responsibility and apologizing to those affected by our mistakes,
  and learning from the experience
* Focusing on what is best not just for us as individuals, but for the
  overall community

Examples of unacceptable behavior include:

* The use of sexualized language or imagery, and sexual attention or advances of
  any kind
* Trolling, insulting or derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or email
  address, without their explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of
acceptable behavior and will take appropriate and fair corrective action in
response to any behavior that they deem inappropriate, threatening, offensive,
or harmful.

## Scope

This Code of Conduct applies within all community spaces, and also applies when
an individual is officially representing the community in public spaces.

## Enforcement & Reporting

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the project team at [{EMAIL}](mailto:{EMAIL}). All complaints will be
reviewed and investigated promptly and fairly.
"""

SUPPORT_MD_TEMPLATE = """# 💬 Support & Community Guidelines

Thank you for using **{REPO_NAME}**! Here are the best ways to get help, report issues, and stay updated.

---

## 🔍 Frequently Asked Questions & Documentation
Before opening a new issue, please consult:
1. **[README.md](./README.md)**: Architecture, installation, and quickstart commands.
2. **[docs/](./docs/)**: Specification schemas, attestation rules, and authoring guidelines.

---

## 🐛 Bug Reports & Questions
- **Found a Bug?** Submit an issue via the [Bug Report Form](../../issues/new?template=bug_report.yml).
- **Need a New Skill or Feature?** Submit a [Feature Request](../../issues/new?template=feature_request.yml).
- **Private Security Vulnerability?** Refer to [SECURITY.md](./SECURITY.md).
"""

BUG_REPORT_YML = """name: 🐛 Bug Report
description: Report a reproducible bug or issue in a skill or CLI tool.
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: Thank you for reporting a bug! Please fill out the form below.
  - type: input
    id: skill_name
    attributes:
      label: Skill or Component Name
      placeholder: "e.g., multi-agent-docs, public-repo-release-review, validate_skills.py"
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: What happened?
      description: A clear description of the bug.
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      placeholder: "1. Run command ...\\n2. Inspect output ..."
    validations:
      required: true
  - type: input
    id: environment
    attributes:
      label: Agent / OS Environment
      placeholder: "Claude Code / Antigravity / Windows / Linux"
"""

FEATURE_REQUEST_YML = """name: 💡 Feature / Skill Request
description: Propose a new agent skill, tool, or repository improvement.
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: Have an idea for a high-impact agent skill or improvement? Let us know!
  - type: input
    id: title
    attributes:
      label: Skill / Feature Title
      placeholder: "e.g., git-rebase-conflict-resolver"
    validations:
      required: true
  - type: textarea
    id: problem
    attributes:
      label: Problem Statement / Agent Failure Mode
      description: What repetitive task or agent failure mode does this solve?
    validations:
      required: true
  - type: textarea
    id: proposed_workflow
    attributes:
      label: Proposed Capability & Workflow
      description: How should the skill execute?
    validations:
      required: true
"""

PR_TEMPLATE_MD = """## 📋 Description of Changes
<!-- Brief summary of what this pull request changes or adds -->

## 🧩 Modified / Added Components
- [ ] New Skill (`skills/<category>/<skill-name>/`)
- [ ] Specification Compliance (`SKILL.md` frontmatter + <500 lines)
- [ ] Attestation (`attestation.json`)
- [ ] Evaluation Test Cases (`evals/test-cases.json`)
- [ ] Governance Documentation

## 🧪 Verification & Testing
- [ ] Ran `python scripts/validate_skills.py` (0 errors, 0 warnings)
- [ ] Tested on target agent platform (Claude Code / Antigravity / Cursor)
"""

def scaffold(target_dir: Path, collaborators_mode: str, author: str, email: str, repo_name: str):
    now = datetime.now()
    year = str(now.year)
    release_date = now.strftime("%Y-%m-%d")
    author_parts = author.split(" ", 1)
    author_given = author_parts[0] if author_parts else "Kunal"
    author_family = author_parts[1] if len(author_parts) > 1 else "Suri"

    context = {
        "AUTHOR": author,
        "AUTHOR_GIVEN": author_given,
        "AUTHOR_FAMILY": author_family,
        "EMAIL": email,
        "REPO_NAME": repo_name,
        "YEAR": year,
        "RELEASE_DATE": release_date
    }

    def format_tmpl(text: str) -> str:
        res = text
        for k, v in context.items():
            res = res.replace("{" + k + "}", v)
        return res

    files_to_write = {
        "SECURITY.md": format_tmpl(SECURITY_TEMPLATE),
        "COLLABORATORS.md": format_tmpl(COLLABORATORS_SOLO_TEMPLATE if collaborators_mode == "solo" else COLLABORATORS_OPEN_TEMPLATE),
        "CITATION.cff": format_tmpl(CITATION_CFF_TEMPLATE),
        "CITATIONS.md": format_tmpl(CITATIONS_MD_TEMPLATE),
        "CODE_OF_CONDUCT.md": format_tmpl(CODE_OF_CONDUCT_TEMPLATE),
        "SUPPORT.md": format_tmpl(SUPPORT_MD_TEMPLATE),
        ".github/ISSUE_TEMPLATE/bug_report.yml": BUG_REPORT_YML,
        ".github/ISSUE_TEMPLATE/feature_request.yml": FEATURE_REQUEST_YML,
        ".github/PULL_REQUEST_TEMPLATE.md": PR_TEMPLATE_MD,
    }

    created = 0
    for rel_path, content in files_to_write.items():
        file_path = target_dir / rel_path
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.strip() + "\n", encoding="utf-8")
            print(f"  [CREATED] {rel_path}")
            created += 1
        else:
            print(f"  [EXISTS]  {rel_path} (skipped)")

    print(f"\n Scaffolding complete! Created {created} file(s).")

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Scaffold public repository governance files.")
    parser.add_argument("--target", type=str, default=".", help="Target repository directory")
    parser.add_argument("--collaborators-mode", choices=["solo", "open"], default="solo", help="Collaborator policy (solo or open)")
    parser.add_argument("--author", type=str, default="Kunal Suri", help="Author / Maintainer name")
    parser.add_argument("--email", type=str, default="kunal.suri@cea.fr", help="Contact email")
    parser.add_argument("--repo-name", type=str, default="1000x-Agent-Skills", help="Repository name")

    args = parser.parse_args()
    target_path = Path(args.target).resolve()
    scaffold(target_path, args.collaborators_mode, args.author, args.email, args.repo_name)

if __name__ == "__main__":
    main()
