---
name: preflight-test-engineer
version: 1.0.0
author: Kunal Suri <kunal@example.com>
description: Pre-flight codebase analysis, automated /tests/ suite scaffolding, and hermetic multi-stage verification for Python and TypeScript/React projects. Use when asked to test a codebase before running, scaffold a test suite into /tests/, verify test coverage, or execute pre-flight sanity checks.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [view_file, run_command, replace_file_content, write_to_file, grep_search]
tags: [testing, pytest, vitest, react-testing-library, preflight, tdd, quality-engineering]
license: Apache-2.0
---

# 🚀 Pre-Flight Test Engineer

The **Pre-Flight Test Engineer** skill deterministically inspects a target codebase, identifies missing test coverage across functions, classes, API routes, and React components, scaffolds an industrial-grade `/tests/` directory layout, and executes a 4-stage pre-flight verification sequence before application execution.

---

## 🏗️ Progressive Architecture & Directory Layout

```text
skills/custom/preflight-test-engineer/
├── SKILL.md                          # Core 5-phase testing workflow
├── attestation.json                  # Multi-agent verification attestation
├── evals/test-cases.json             # Trigger evaluation prompts
├── references/
│   ├── python-testing.md             # Pytest, asyncio, fixtures, hypothesis patterns
│   ├── typescript-react-testing.md   # Vitest, RTL, MSW, accessibility patterns
│   └── test-pyramid-and-mocking.md   # Hermetic fixtures & boundary case checklist
└── scripts/
    ├── analyze_codebase.py           # AST & stack inspector (Python + TS/JS/React)
    ├── scaffold_tests.py             # Deterministic /tests/ scaffolding engine
    └── run_preflight.py              # 4-stage pre-flight validation runner
```

---

## ⚡ 5-Phase Pre-Flight Execution Workflow

```
[Phase 1: Scan]       ──> Run analyze_codebase.py to detect stack & test gaps
       │
[Phase 2: Strategy]   ──> Map functions/components to Test Pyramid layers
       │
[Phase 3: Scaffold]   ──> Run scaffold_tests.py to generate /tests/ harness
       │
[Phase 4: Fortify]    ──> Add boundary, negative, and property-based assertions
       │
[Phase 5: Pre-Flight] ──> Run run_preflight.py (Syntax -> Discovery -> Fast Run)
```

---

### Phase 1: Codebase & Stack Inspection

Run the deterministic analyzer to inspect the project stack, existing test runners, and unmapped modules:

```bash
python <skill-dir>/scripts/analyze_codebase.py --target-dir .
```

*For JSON output for automated pipelines, add `--json`.*

#### Inspection Checklist:
1. **Language & Framework Detection**:
   - Python: FastAPI, Flask, Django, Click/Typer, Pydantic, Celery.
   - JS/TS: React, Next.js, Express, Fastify, Node.js.
2. **Runner & Config Audit**:
   - Check for `pytest.ini`, `pyproject.toml`, `vitest.config.ts`, `jest.config.js`.
3. **Module & Symbol Extraction**:
   - Functions, classes, async endpoints, React components, hooks.

---

### Phase 2: Test Architecture & Gap Mapping

Structure the test suite using the **Hermetic Test Pyramid**:

| Layer | Directory | Purpose | Isolation Strategy |
|---|---|---|---|
| **Smoke** | `tests/smoke/` | Import graph, configuration sanity, zero-side-effect startup | Isolated runtime |
| **Unit** | `tests/unit/` | Pure business logic, algorithms, state reducers | 100% Mocked / In-memory |
| **Components** | `tests/components/` | React DOM rendering, user events, accessibility roles | `jsdom` + `@testing-library/react` |
| **Integration** | `tests/integration/` | API route contracts, database transactions | In-memory SQLite / MSW handlers |
| **Fixtures** | `tests/fixtures/` | Typed mock data factories and payload generators | Hermetic factories |

---

### Phase 3: Scaffolding Standardized `/tests/` Suite

Execute the scaffolder script to create the full test harness:

```bash
# Preview proposed test files
python <skill-dir>/scripts/scaffold_tests.py --target-dir . --dry-run

# Generate the /tests/ structure and baseline test files
python <skill-dir>/scripts/scaffold_tests.py --target-dir .
```

#### Generated Assets:
- **Python**:
  - `tests/conftest.py` with `autouse` environment isolation fixture.
  - `pytest.ini` with standard markers (`unit`, `integration`, `smoke`, `slow`).
  - `tests/smoke/test_preflight_smoke.py` for pre-flight import checks.
  - `tests/fixtures/factories.py` for typed test payload generation.
  - Skeleton unit test files matching discovered modules (e.g. `tests/unit/test_<module>.py`).
- **TypeScript / React**:
  - `tests/setup.ts` with global mock resets and DOM cleanup.
  - `vitest.config.ts` configured for `jsdom` or `node`.
  - `tests/smoke/preflight_smoke.test.ts` for export sanity.
  - `tests/components/<Component>.test.tsx` for React components with RTL.
  - `tests/fixtures/factories.ts` for mock objects.

---

### Phase 4: Fortifying Assertions & Boundary Edge Cases

Enhance generated test templates with deep assertions according to the language reference:

1. **Python Projects**: Consult [python-testing.md](file:///skills/custom/preflight-test-engineer/references/python-testing.md)
   - Add `@pytest.mark.asyncio` for async endpoints.
   - Use `mocker.patch()` to intercept network calls.
   - Add `@given(st.text())` with **Hypothesis** for property-based fuzzing.
2. **TypeScript/React Projects**: Consult [typescript-react-testing.md](file:///skills/custom/preflight-test-engineer/references/typescript-react-testing.md)
   - Use `userEvent.setup()` and `screen.getByRole()` for RTL tests.
   - Add `toHaveNoViolations()` with `jest-axe` for accessibility contracts.
   - Intercept API calls using Mock Service Worker (MSW).
3. **Boundary Checklist**: Consult [test-pyramid-and-mocking.md](file:///skills/custom/preflight-test-engineer/references/test-pyramid-and-mocking.md)
   - Verify empty inputs (`""`, `[]`, `{}`, `None`/`null`), extreme numeric values, malformed JSON, and network timeouts.

---

### Phase 5: Pre-Flight Verification Pipeline

Execute the 4-stage pre-flight runner before launching the main application or deploying:

```bash
python <skill-dir>/scripts/run_preflight.py --target-dir .
```

#### Pipeline Stages:
1. **Stage 1 (Syntax & Compilation)**: Validates that all files compile and parse without syntax errors (`py_compile` / AST).
2. **Stage 2 (Test Discovery)**: Verifies test discovery and import graph (`pytest --collect-only` / `vitest --run`).
3. **Stage 3 (Hermetic Fast Run)**: Executes unit and smoke tests in sandbox isolation with strict timeouts.
4. **Stage 4 (Diagnostics)**: Generates a clear status scorecard and remediation action list.

```text
========================================================================
 🏁 [PRE-FLIGHT VERIFICATION SUMMARY]
========================================================================
 Target Directory : /path/to/project
 Total Duration   : 1.42s
 Overall Verdict  : 🟢 READY FOR LAUNCH (PASS)
------------------------------------------------------------------------
 Stage                               | Status     | Duration
------------------------------------------------------------------------
 Syntax & Compilation Integrity      | ✅ PASS    | 0.12s
 Test Discovery & Import Graph       | ✅ PASS    | 0.45s
 Hermetic Fast Test Execution        | ✅ PASS    | 0.85s
========================================================================
```
