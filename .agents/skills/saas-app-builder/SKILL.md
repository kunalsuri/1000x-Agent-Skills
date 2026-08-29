---
name: saas-app-builder
version: 1.0.0
author: Kunal Suri <kunal@example.com>
description: Scaffolds and implements full-stack SaaS applications with React 19, Tailwind CSS v4, shadcn/ui primitives, Express port 3031, and a 4-harness test suite. Use when asked to create a SaaS app, scaffold a full-stack monorepo, build a feature-driven SaaS template, or create a modern web application with integrated tests.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [view_file, run_command, replace_file_content, write_to_file, grep_search]
tags: [saas, full-stack, react, vite, tailwindcss-v4, shadcn-ui, express, vitest, monorepo, tdd]
license: Apache-2.0
---

# 🚀 SaaS App Builder

The **SaaS App Builder** skill couples a **deterministic Python scaffolding engine** (instant, 0-token monorepo generation) with **agent intelligence** to build feature-driven SaaS applications. It incorporates **Tailwind CSS v4**, **shadcn/ui primitives**, **Express single-port 3031 serving**, and a **4-harness verification net** (Vitest, Supertest, TypeScript compile checks, and shared Zod contracts).

---

## 🏗️ Progressive Architecture & Directory Layout

```text
skills/custom/saas-app-builder/
├── SKILL.md                               # 5-Phase TDD & Feature Architecture Workflow
├── attestation.json                       # Multi-agent verification attestation
├── evals/test-cases.json                  # Intent and benchmark test cases
├── references/
│   ├── tailwind-v4-shadcn-tokens.md       # Tailwind v4 CSS-first tokens & Radix patterns
│   ├── test-harness-and-tdd.md            # Vitest + Supertest execution & self-correction loop
│   ├── single-port-express-vite.md        # Single-port 3031 serving architecture
│   └── updating-dependencies-and-templates.md # Maintenance & package upgrade guide
└── scripts/
    └── scaffold_saas.py                   # Deterministic monorepo scaffolder CLI
```

---

## ⚡ 5-Phase Execution Workflow

```
[Phase 1: Scaffold]    ──> Run scaffold_saas.py to create monorepo & test harness in < 1s
       │
[Phase 2: Domain Plan] ──> Define entities, Zod schemas, & storage in data/<domain>.json
       │
[Phase 3: TDD Feature] ──> Write Vitest/Supertest tests, then implement controllers & UI slices
       │
[Phase 4: UI Polish]   ──> Integrate with Dashboard, apply Tailwind v4 tokens & Lucide icons
       │
[Phase 5: Verify]      ──> Run 'npm run verify' (typecheck + test runner) & launch on port 3031
```

---

### Phase 1: Deterministic Monorepo Scaffolding

Run the deterministic CLI scaffolder to generate the complete foundation:

```bash
python skills/custom/saas-app-builder/scripts/scaffold_saas.py --name "<app-name>" --target-dir "<target-directory>" --port 3031
```

This immediately creates:
* **Frontend**: React 19, Vite 6, Tailwind CSS v4 (`@tailwindcss/vite`), shadcn UI primitives (`Button`, `Card`, `Input`, `Badge`, `ThemeToggle`), `AppLayout`, `Navbar`, `Sidebar`, `Landing`, `Login`, `Signup`, `Dashboard`.
* **Backend**: Express single-port (`3031`) server with static bundle serving, JSON body parsing, CORS, auth middleware, and `fileStorage.ts` helper.
* **4-Harness Safety Net**: `vitest.config.ts`, `client/src/test/setup.ts`, initial component tests, API integration tests, and shared Zod schemas.

---

### Phase 2: Domain Schema & Entity Design

1. Analyze the user's SaaS domain requirement (e.g. Prompt Management, Invoice Tracker, Micro-Course Hub).
2. Create a shared Zod contract in `shared/schemas/<domain>Schema.ts`:
   ```ts
   import { z } from 'zod';
   export const itemSchema = z.object({
     id: z.string(),
     title: z.string().min(2),
     status: z.enum(['active', 'draft', 'archived']),
     createdAt: z.string(),
   });
   export type Item = z.infer<typeof itemSchema>;
   ```
3. Initialize the seed storage file in `data/<domain>.json`.

---

### Phase 3: Test-Driven Feature Construction (TDD Loop)

Implement the domain in modular slices:

1. **Backend Integration Test**: Create `server/__tests__/<domain>.test.ts` testing CRUD endpoints with `supertest`.
2. **Backend Controller & Routes**:
   * Add `server/controllers/<domain>Controller.ts` using `readJsonFile` / `writeJsonFile` from `server/utils/fileStorage.ts`.
   * Add `server/routes/<domain>.ts` and mount in `server/server.ts` (`/api/<domain>`).
3. **Frontend Feature Slice**:
   * Create `client/src/features/<domain>/`:
     * `components/<Domain>List.tsx`, `<Domain>Form.tsx`, `<Domain>Card.tsx`
     * `hooks/use<Domain>.ts` (using `@tanstack/react-query`)
     * `index.ts` (public module exports)
4. **Frontend Component Test**: Create `client/src/features/<domain>/__tests__/<Domain>Card.test.tsx` verifying render and interactions with `@testing-library/react`.

---

### Phase 4: UI Polish & Dashboard Integration

1. Connect the new feature slice into `client/src/pages/Dashboard.tsx`.
2. Ensure UI adheres to **Tailwind CSS v4 tokens**:
   * Use semantic classes: `bg-card`, `text-card-foreground`, `border`, `text-primary`, `bg-primary/10`.
   * Add interactive states: `hover:bg-accent`, `transition-colors`, `shadow-sm`.
   * Add Lucide icons for visual clarity.
   * Support both Light and Dark modes seamlessly via CSS variables.

---

### Phase 5: Verification & Live Launch

1. Execute the full verification harness:
   ```bash
   npm run verify
   ```
   * Step 1: `tsc --noEmit` validates TypeScript types across client and server.
   * Step 2: `vitest run` executes all frontend unit tests and Supertest API tests.
2. If any test or type error is detected, inspect the line number, fix the issue, and re-run.
3. Update `docs/PROJECT_STATUS.md` and the root `README.md` with the custom domain features, API endpoints, local run instructions (`npm run dev`), and test commands (`npm test`, `npm run verify`).
4. Launch the application:
   ```bash
   npm run dev
   ```
   * Open `http://localhost:3031` for unified full-stack development.

---

## 🛡️ Best Practices Checklist

* ✅ **Maintain clear README instructions**: Ensure root `README.md` clearly guides the user on starting the server and running test suites.
* ✅ **Never bypass the test harness**: Always write or maintain tests for new domain features.
* ✅ **Keep single port serving**: Both API (`/api/*`) and React SPA run together on port `3031`.
* ✅ **Feature isolation**: Isolate domain logic inside `client/src/features/<domain>/` rather than cluttering shared folders.
* ✅ **CSS-First Tailwind v4**: Define theme tokens in `client/src/index.css` using `@layer base` and `@theme`.
