#!/usr/bin/env python3
"""
README & Documentation Scaffolder CLI.
Generates an ultra-modern, high-status, beautifully formatted README.md
complete with centered hero, badges, breathing room (<br/>), dividers (---),
comparison tables, Mermaid diagrams, and governance sections.
"""

import sys
import argparse
from pathlib import Path

def generate_readme_content(name: str, tagline: str, description: str, author: str, license_name: str) -> str:
    slug_name = name.lower().replace(" ", "-")
    return f"""<div align="center">

# 🧩 {name}

### *{tagline}*

<br/>

[![License: {license_name}](https://img.shields.io/badge/License-{license_name.replace(' ', '%20')}-f59e0b?style=for-the-badge)](./LICENSE)
[![Multi-Agent Ready](https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Antigravity%20%7C%20Cursor%20%7C%20Codex-6366f1?style=for-the-badge)](#-multi-agent-support)
[![Quality: Grade A](https://img.shields.io/badge/Quality-Grade%20A%2B-10b981?style=for-the-badge)](#-developer-tooling)

<br/>

[**⚡ Quickstart**](#-quickstart--usage) &nbsp;•&nbsp; [**💡 Overview**](#-what-is-{slug_name}) &nbsp;•&nbsp; [**⚖️ Comparison**](#️-architectural-comparison) &nbsp;•&nbsp; [**📁 Architecture**](#-repository-architecture) &nbsp;•&nbsp; [**📄 License**](./LICENSE)

<br/>

</div>

---

<br/>

### ⚡ Instant Install (1-Liner)

Install or run directly in **one command**:

<br/>

```bash
# 🚀 Instant execution via npx
npx {slug_name}
```

<br/>

---

<br/>

## 💡 What is {name}?

{description}

<br/>

- ❌ **Traditional Pitfall**: Monolithic prompts, lack of structure, high token consumption, and unverified workflows.
- ✨ **{name} Solution**: Modular, progressive disclosure, deterministic tool validation, and synchronized multi-agent directives.

<br/>

> [!IMPORTANT]
> **Core Architectural Philosophy**  
> Built for zero-overhead performance, rigorous verification, and deterministic execution across modern developer environments.

<br/>

```mermaid
flowchart TD
    subgraph Boot ["🚀 1. Initialization"]
        A["Load Lightweight Config<br/><b>(~100 tokens overhead)</b>"]
    end

    subgraph Process ["⚡ 2. Processing & Synthesis"]
        B["Execute Deterministic Tools<br/><b>& Semantic LLM Pass</b>"]
    end

    subgraph Output ["🎉 3. Verified Output"]
        C["Generate Clean Artifacts<br/><b>& Parity Checked Output</b>"]
    end

    Boot --> Process --> Output
```

<br/>

---

<br/>

## ⚖️ Architectural Comparison

<br/>

| Dimension | ❌ Traditional Approaches | 🌟 {name} Standard |
|---|---|---|
| **Context Overhead** | Heavy (unbounded token waste) | **Ultra-lightweight (progressive on-demand)** |
| **Verification & Quality** | Unverified static snippets | **Automated CI quality benchmarks & diagnostics** |
| **Cross-Platform Parity** | Fragmented & drift-prone | **Synchronized across Claude, Antigravity & Cursor** |

<br/>

---

<br/>

## ⚡ Quickstart & Usage

<br/>

### 1. Run Core Engine

<br/>

```bash
python run.py --target .
```

<br/>

```text
=================================================================
 [{name.upper()}] Execution Complete: 100% Passed
=================================================================
 [✓] Initialized environment
 [✓] Executed core pipeline
 [✓] Quality audit passed with Grade A+
=================================================================
```

<br/>

---

<br/>

## 🩺 Developer Tooling & Diagnostics

<br/>

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🩺 {name.upper()}: Health Score: 100 [GRADE A+ PRODUCTION READY]             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [✓] Configuration Valid             [✓] Link Integrity Verified            │
│  [✓] Spacing & Typography Clean      [✓] Multi-Agent Directives Synchronized│
└─────────────────────────────────────────────────────────────────────────────┘
```

<br/>

---

<br/>

## 📁 Repository Architecture

<br/>

```text
{slug_name}/
├── docs/             # Specification & technical documentation
├── scripts/          # Automation CLI tools & quality suites
├── tests/            # Test harness & benchmark test-cases
├── LICENSE           # {license_name} License
└── README.md         # Repository overview & quickstart
```

<br/>

---

<br/>

## 📜 Open-Source Governance & Citations

<br/>

- 🛡️ **[Security Policy](./SECURITY.md)**: Vulnerability disclosure guidelines and response timeline.
- 👥 **[Collaborator Guidelines](./COLLABORATORS.md)**: Contribution and maintainer guidelines.
- 📄 **[License](./LICENSE)**: Licensed under the **{license_name} License**.

<br/>

<div align="center">

**Created by {author} • Built with ❤️ for the Developer Community**

</div>
"""

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="Scaffold an ultra-modern README.md file.")
    parser.add_argument("--name", default="My Awesome Project", help="Project name.")
    parser.add_argument("--tagline", default="The Capability-Declared Toolchain for Modern Engineering", help="Punchy tagline.")
    parser.add_argument("--description", default="A high-performance, modular developer toolchain engineered for autonomous workflows.", help="Project description.")
    parser.add_argument("--author", default="Project Author", help="Author name.")
    parser.add_argument("--license", default="Apache 2.0", help="License name (e.g. Apache 2.0, MIT).")
    parser.add_argument("--output", default="README.md", help="Output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file if it exists.")
    args = parser.parse_args()

    out_path = Path(args.output).resolve()
    if out_path.exists() and not args.overwrite:
        print(f"[ERROR] Target file '{out_path}' already exists. Pass --overwrite to replace it.")
        sys.exit(1)

    content = generate_readme_content(
        name=args.name,
        tagline=args.tagline,
        description=args.description,
        author=args.author,
        license_name=args.license
    )

    out_path.write_text(content, encoding="utf-8")
    print(f"✨ [SUCCESS] Scaffolding complete! Created modern README at: {out_path}")

if __name__ == "__main__":
    main()
