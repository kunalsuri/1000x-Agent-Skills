---
name: public-repo-release-review
version: 1.0.0
author: Kunal Suri <kunal.suri@cea.fr>
description: Review and audit a codebase before releasing or publishing it to public GitHub. Performs deep security checks, secret leak scanning, open-source governance verification (SECURITY.md, COLLABORATORS.md, CITATION.cff, LICENSE, CODE_OF_CONDUCT.md), link integrity checks, and codebase hygiene audits. Use when reviewing a codebase before public release, auditing repository security and governance, or preparing a repository for public GitHub launch.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [run_command, view_file, write_to_file, replace_file_content]
tags: [public-repo, release-review, security-audit, governance, secret-scan, preflight, citation]
license: Apache-2.0
---

# Public Repository Release Review & Pre-Flight Audit

## Purpose
Empowers the agent to act as an expert AI engineer, security auditor, and open-source release manager. Conducts a 99.999% rigorous audit before a repository is pushed or made public on GitHub, ensuring zero secret leaks, compliant governance files, intact link integrity, and pristine codebase hygiene.

---

## Procedural Workflow

```
┌─────────────────────────────────┐
│ 1. Deterministic Security Scan  │ ──> Scan secrets, .env files, high-entropy tokens, .gitignore
└─────────────────────────────────┘
                │
┌─────────────────────────────────┐
│ 2. Governance & Policy Audit    │ ──> Verify SECURITY.md, COLLABORATORS.md, CITATION.cff, etc.
└─────────────────────────────────┘
                │
┌─────────────────────────────────┐
│ 3. Link Integrity & Hygiene     │ ──> Verify relative markdown links, phantom files, dead code
└─────────────────────────────────┘
                │
┌─────────────────────────────────┐
│ 4. Scorecard & Auto-Remediation │ ──> Generate final release audit scorecard & scaffold missing files
└─────────────────────────────────┘
```

---

### Phase 1: Automated Deterministic Audit

Execute the built-in audit script using `run_command`:

```bash
python <skill_path>/scripts/audit_repo.py --target .
```

The script automatically verifies:
1. **Secret & Credential Leaks**: Scans for AWS tokens, private keys, GitHub tokens, OpenAI/Gemini/Anthropic API keys, high-entropy secrets, and unignored `.env*` files.
2. **Governance Metadata Compliance**: Checks for `SECURITY.md`, `COLLABORATORS.md` / `CONTRIBUTING.md`, `CITATION.cff`, `CITATIONS.md`, `LICENSE`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, and `.github/` templates.
3. **Link & Reference Integrity**: Scans every Markdown file (`*.md`) to verify all relative hyperlinks point to physical files.
4. **Codebase Hygiene**: Checks for OS junk (`.DS_Store`, `Thumbs.db`), untracked large binary blobs (>5MB), and unignored build artifacts.

---

### Phase 2: Missing Governance Scaffolding

If governance files are missing or incomplete, run the built-in scaffolding CLI:

```bash
# For solo-maintainer / closed-collaborator repositories:
python <skill_path>/scripts/scaffold_governance.py --target . --collaborators-mode solo --author "Author Name" --email "author@domain.com"

# For open-collaboration community repositories:
python <skill_path>/scripts/scaffold_governance.py --target . --collaborators-mode open --author "Author Name" --email "author@domain.com"
```

The scaffolding script generates:
- `SECURITY.md`: Vulnerability disclosure policy with reporting email and SLA.
- `COLLABORATORS.md`: Explicit collaborator guidelines (clearly declaring solo-maintainer or community contributor policy).
- `CITATION.cff` & `CITATIONS.md`: Standard academic and software citation formats (APA, BibTeX, IEEE).
- `CODE_OF_CONDUCT.md`: Contributor Covenant v2.1 guidelines.
- `SUPPORT.md`: Support channels, discussions, and troubleshooting pointers.
- `.github/`: Issue templates (`bug_report.yml`, `feature_request.yml`) and pull request template (`PULL_REQUEST_TEMPLATE.md`).

---

### Phase 3: Semantic Review & Codebase Polish

As an expert AI engineer, conduct a manual semantic pass on critical areas:

1. **Readme Completeness**:
   - Verify clear one-liner explanation, architecture diagram, installation/quickstart steps, and badges.
   - Verify all documented commands execute without syntax or environment errors.
2. **License Validity**:
   - Verify `LICENSE` matches the SPDX identifier and frontmatter licenses across skills.
3. **Collaboration Boundary**:
   - If the repository does not accept external pull requests, ensure `COLLABORATORS.md` explicitly states this upfront to avoid contributor confusion.
4. **Attestation & Specs**:
   - For skill repositories, ensure every skill directory has `attestation.json` and `evals/test-cases.json`.

---

### Phase 4: Final Release Certification

Re-run the audit suite to certify 100% compliance:

```bash
python <skill_path>/scripts/audit_repo.py --target . --strict
```

Ensure the terminal reports:
- `[PASS] 0 Security Leaks Detected`
- `[PASS] Governance Files: 100% Present`
- `[PASS] Markdown Links: 100% Resolved`
- `[PASS] Codebase Hygiene: Clean`
