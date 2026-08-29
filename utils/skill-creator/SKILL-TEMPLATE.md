---
name: example-skill-name
version: 1.0.0
author: Your Name <your-email@example.com>
description: A clear, high-density summary of what this skill accomplishes. Use when encountering scenario X, handling task Y, or orchestrating workflow Z.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [run_command, view_file, write_to_file, replace_file_content, grep_search]
tags: [workflow, automation, quality]
license: Apache-2.0
---

# Example Skill Name

## Overview
Brief explanation of the capability this skill adds to the agent and why it is needed.

## Preconditions & Required Tools
- Verify that necessary tools (e.g., CLI, environment variables, dependencies) are available.
- Check workspace state before proceeding.

## Step-by-Step Procedure

### 1. Analysis Phase
- Gather required context and inspect target files.
- Formulate an explicit plan before making modifications.

### 2. Execution Phase
- Apply modifications systematically in small, verifiable steps.
- Preserve existing formatting and comments unless explicitly instructed otherwise.

### 3. Verification Phase
- Run automated tests or linting to verify the fix/feature.
- Document any side effects or notable changes.

## Output Artifacts & Deliverables
- List expected outputs (e.g., modified files, test reports, summary markdown).

## References & Deep Dive
If this skill requires extensive schemas or reference data, link to `references/` (e.g., `[API Guide](references/api-guide.md)`).
