---
name: saas-app-builder
version: 1.0.0
author: Kunal Suri <kunal.suri@cea.fr>
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
    ├── scaffold_saas.py                   # Deterministic monorepo scaffolder CLI
    └── audit_scaffold.py                  # Structural safety audit — see "Security & Auditability" below
```

Every command in this file is written assuming this skill is installed at
`skills/custom/saas-app-builder/` relative to wherever you run it from (that's
the layout in this skill's origin repo — see `attestation.json`'s
`provenance.origin_url`). If a platform installs it elsewhere (e.g. Claude
Code's `.claude/skills/saas-app-builder/`), substitute the actual path —
`python .claude/skills/saas-app-builder/scripts/scaffold_saas.py ...` instead
of `python skills/custom/saas-app-builder/scripts/scaffold_saas.py ...`, and
likewise for `audit_scaffold.py`. The commands are correct relative paths,
just anchored to one specific install location.

---

## 🔒 Security & Auditability

`scaffold_saas.py` is a large file, but ~90% of it is inert template *content* (JS/TS/CSS/JSON strings written verbatim to disk) — the executable *logic* is small: parse CLI args, build a `{path: content}` map, write each file under `--target-dir`. Before trusting any copy of this skill (including after any update to `scaffold_saas.py`), verify that structurally rather than by reading 2000+ lines:

```bash
python skills/custom/saas-app-builder/scripts/audit_scaffold.py skills/custom/saas-app-builder/scripts/scaffold_saas.py
```

It parses the file with Python's `ast` module (not a regex skim — a `subprocess.run(...)` can't hide from an AST walk the way it could from a quick read) and reports:
* every module the script imports, full stop — Python has no hidden-import mechanism, so this list is exhaustive by construction;
* any import of a networking, process-spawning, or dynamic-code-execution module (`socket`, `subprocess`, `urllib`, `requests`, etc.) — hard fail if present, since a file-writing CLI has no legitimate reason to import any of them;
* any call to `eval`/`exec`/`compile`/`__import__`/`os.system`/`os.popen`/file-deletion functions;
* base64/`atob`/`btoa`/`fromCharCode` obfuscation smells;
* every external URL in the file, for manual review — as of v1.3.0 there are 10, all inert strings inside generated-app *templates* (Google Fonts links, one Unsplash demo-avatar image, the SVG XML namespace URI, `ui.shadcn.com`'s `components.json` schema reference) that a browser fetches later when someone runs the *generated app* — not calls this script makes itself.

Exit code 0 = clean, 1 = something needs a human to look at it. Run it after every change to `scaffold_saas.py`, and re-run it yourself on any copy of this skill rather than trusting a prior attestation — `attestation.json` records the result of the last run, not a permanent guarantee about future edits.

---

## ⚡ 5-Phase Execution Workflow

```
[Phase 0: Requirements] ──> Confirm domain, app name, and target directory before touching disk
       │
[Phase 1: Scaffold]     ──> Run scaffold_saas.py, install deps, and verify the baseline is clean
       │
[Phase 2: Domain Plan]  ──> Define entities, Zod schemas, & storage in data/<domain>.json
       │
[Phase 3: TDD Feature]  ──> Write Vitest/Supertest tests, then implement controllers & UI slices
       │
[Phase 4: UI Polish]    ──> Integrate with Dashboard, apply Tailwind v4 tokens & Lucide icons
       │
[Phase 5: Verify]       ──> Run 'npm run verify', build, smoke-test single-port serving, launch
```

---

### Phase 0: Requirements Gathering

Before running the scaffolder, resolve these three things — ask the user in a single round if any are missing, rather than iterating question-by-question:

1. **Domain** — a concrete noun phrase for what the app manages (e.g. "task/project tracker", "invoice tracker for freelancers"), not a category label. If the user's answer is itself vague (e.g. just "other" with no detail), ask one direct follow-up naming 2-3 concrete example domains — don't proceed on an unresolved domain.
2. **App name** — used for `--name` and `package.json`'s `"name"` field.
3. **Target directory** — where to scaffold. If it's the current repo root, confirm the directory is empty or has no conflicting files (`client/`, `server/`, `shared/`, `package.json`) before running the scaffolder — it will overwrite silently.

---

### Phase 1: Deterministic Monorepo Scaffolding

Run the deterministic CLI scaffolder to generate the complete foundation:

```bash
python skills/custom/saas-app-builder/scripts/scaffold_saas.py --name "<app-name>" --target-dir "<target-directory>" --port 3031
```

This immediately creates:
* **Frontend**: React 19, Vite 6, Tailwind CSS v4 (`@tailwindcss/vite`), shadcn UI primitives (`Button`, `Card`, `Input`, `Badge`, `ThemeToggle`), `AppLayout`, `Navbar`, `Sidebar`, `Landing`, `Login`, `Signup`, `Dashboard`, `TeamUsers`, `Settings` (profile name editing) — every `Sidebar` nav item ships with a matching route out of the box.
* **Backend**: Express single-port (`3031`) server with static bundle serving, JSON body parsing, CORS, auth middleware, `fileStorage.ts` helper, and account self-service (`GET`/`PATCH /api/auth/me`).
* **4-Harness Safety Net**: `vitest.config.ts`, `client/src/test/setup.ts`, initial component tests, API integration tests, and shared Zod schemas.

**Baseline check** — before writing any domain code, install, verify, build, and confirm the design tokens actually generated CSS:

```bash
npm install
npm run verify
npm run build
grep -c '\.bg-primary\b' dist/client/assets/*.css   # must be > 0
grep -c '\.bg-card\b' dist/client/assets/*.css      # must be > 0
```

`npm run verify` passing is necessary but **not sufficient** — `tsc` and `vitest` have no opinion on whether `bg-primary` produced a CSS rule or silently compiled to nothing. That exact silent failure (a missing `@theme` block in `index.css`) shipped in this skill through v1.2.0: every semantic color utility was inert, so every button/card/badge rendered with no color, no background, no border — the whole app looked flat and "not modern" despite `npm run verify` being green the entire time. The grep above is what would have caught it. See [`references/tailwind-v4-shadcn-tokens.md`](references/tailwind-v4-shadcn-tokens.md) for the full explanation and the correct `index.css`.

If any of this fails on the generated scaffold alone, the scaffolder itself has a bug — fix it in `scripts/scaffold_saas.py` (or the relevant reference doc) before proceeding, rather than patching around it in the generated app.

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
   * Stat/metric tiles: one flat `CardContent` (label + value left, a `size-10 rounded-full` tinted icon badge right) — not a `CardHeader`/`CardContent` split with a bare gray icon. See `references/tailwind-v4-shadcn-tokens.md` for the pattern and why.
   * Prefer canonical Tailwind classes over arbitrary values (`w-17` not `w-[68px]`) — most of what arbitrary values used to be needed for now has a real utility in v4's expanded scale.

---

### Phase 5: Verification & Live Launch

1. Execute the full verification harness:
   ```bash
   npm run verify
   ```
   * Step 1: `tsc --noEmit` validates TypeScript types across client and server.
   * Step 2: `vitest run` executes all frontend unit tests and Supertest API tests.
2. If any test or type error is detected, inspect the line number, fix the issue, and re-run.
3. **Production build + single-port smoke test** — `npm run verify` passing does not prove the built app actually serves correctly on port 3031; test-passing and route-serving are two different failure modes. Run:
   ```bash
   npm run build
   NODE_ENV=production npx tsx server/server.ts &
   curl -s -o /dev/null -w "%{http_code}" http://localhost:3031/api/health   # expect 200
   curl -s -o /dev/null -w "%{http_code}" http://localhost:3031/dashboard   # expect 200, the built index.html
   ```
   A client-only route returning 404 (or a JSON `"Development API mode active"` payload instead of HTML) means the server silently fell back to dev-API-only mode — almost always a wrong relative path to `dist/client` in `server/server.ts`. See [`references/single-port-express-vite.md`](references/single-port-express-vite.md) for the exact failure mode and fix. Stop the background server once confirmed.
4. **Nav/route parity check** — a passing build proves *a* route works, not that every link in `Sidebar.tsx` does. Read every `to:` value out of `navItems` and `curl` each one; every single one must return 200 with the SPA's HTML, never a 404 from the catch-all. If you added a new `Sidebar` entry for a domain feature (Phase 4), it needs a matching `<Route>` in `App.tsx` in the same change — a dead nav link that silently redirects to `/` is the single most common defect in this skill's output, and `npm run verify` cannot catch it (it's a routing-completeness gap, not a type or unit-test failure).
5. Also confirm the build didn't leave stray compiled `.js` files inside `server/` or `shared/` (a sign `server/tsconfig.json` is missing `outDir`/`rootDir`) — `git status` should show no new `.js` files alongside your `.ts` sources.
6. **Auth actually enforces, not just responds** — `npm run verify` passing proves the auth *tests* pass, not that a mistake outside their coverage (e.g. a new endpoint that skips `requireAuth`, or a `login()` rewrite that drops the `bcrypt.compare`) doesn't ship anyway. Live-check it, same server as step 3:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3031/api/auth/me -H "Authorization: Bearer not-a-real-token"        # expect 401
   curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:3031/api/auth/login -H "Content-Type: application/json" -d '{"email":"alex@example.com","password":"wrong"}'   # expect 401
   curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:3031/api/auth/login -H "Content-Type: application/json" -d '{"email":"alex@example.com","password":"password123"}'  # expect 200
   ```
   If you added a new `requireAuth`-protected route, also confirm it 401s with no `Authorization` header at all.
7. Update `docs/PROJECT_STATUS.md` and the root `README.md` with the custom domain features, API endpoints, local run instructions (`npm run dev`), and test commands (`npm test`, `npm run verify`).
8. Launch the application:
   ```bash
   npm run dev
   ```
   * Open `http://localhost:3031` for unified full-stack development.

---

## 🛡️ Best Practices Checklist

* ✅ **Maintain clear README instructions**: Ensure root `README.md` clearly guides the user on starting the server and running test suites.
* ✅ **Never bypass the test harness**: Always write or maintain tests for new domain features.
* ✅ **Keep single port serving**: Both API (`/api/*`) and React SPA run together on port `3031`. Prove it with a live route check (Phase 5, step 3), not just by reading the code.
* ✅ **Feature isolation**: Isolate domain logic inside `client/src/features/<domain>/` rather than cluttering shared folders.
* ✅ **CSS-First Tailwind v4**: Define theme tokens in `client/src/index.css` using `@layer base` and `@theme`.
* ✅ **Self-cleaning integration tests**: Backend CRUD tests run against the same `data/*.json` files as `npm run dev`. Create → assert → delete in the same test so repeated runs never accumulate garbage in the seed data. See [`references/test-harness-and-tdd.md`](references/test-harness-and-tdd.md).
* ✅ **Never re-enable `fileParallelism`**: `vitest.config.ts` sets `fileParallelism: false` because the JSON file storage has no locking — parallel test files can corrupt each other's reads/writes. Leave it off when adding domain test files.
* ✅ **Fix the scaffolder, not the symptom**: if a bug shows up in freshly-scaffolded (untouched) code — not code you wrote — fix `scripts/scaffold_saas.py` or the relevant `references/*.md` so the next scaffold is already correct, rather than only patching the generated app.
* ✅ **Nav/route parity, always**: `client/src/components/layout/Sidebar.tsx` and the `<Route>` list in `client/src/App.tsx` must be edited together. Never add a nav item without its route (or vice versa) — see Phase 5, step 4.
* ✅ **Account self-service is baseline, not a domain feature**: the scaffold ships `GET`/`PATCH /api/auth/me` and a working `Settings` page so a user can rename themselves out of the box. Don't remove or bypass this when wiring in domain features — extend it (e.g. avatar, password change) rather than replacing it.
* ✅ **Sanitize every user object before it leaves the server**: `password` must never appear in a JSON response. `listUsers`/`getUserById`/`getCurrentUser`/`updateCurrentUser` all destructure it out — copy that pattern for any new endpoint that returns a user record.
* ✅ **Passwords are hashed, and login actually checks them**: `register()` stores `await bcrypt.hash(password, 10)` (via `bcryptjs`), never the raw value, and `login()` calls `bcrypt.compare(password, user.password)` before issuing a session — copy this pattern for any new credential-based endpoint. Through v1.4.0 this skill's own scaffold got both of these wrong: `login()` only checked that a user with the given email existed and never looked at the submitted password at all, and `authMiddleware.ts`'s `requireAuth` treated *any* bearer token starting with the string `mock_jwt_token` as a valid session — even one nobody had ever issued — defaulting it to the admin demo user. Both were exploitable with nothing more than `curl` and were fixed in v1.5.0; see that entry in `attestation.json`. **Never reintroduce a token-prefix or other string-shape check as a substitute for an exact session/credential match.**
* ✅ **The frontend must actually call the auth endpoints it has**: `Login.tsx`/`Signup.tsx` call `POST /api/auth/login` / `POST /api/auth/register` via `apiRequest` and surface a rejected `ApiError` to the user — they must never fake success client-side (e.g. `setTimeout` + hardcoding a user/token). A backend auth fix is invisible, and easy to silently regress, if the UI that exercises it doesn't actually call it.
* ✅ **`@theme` is not optional**: every custom property in `client/src/index.css` that a component uses as `bg-*`/`text-*`/`border-*`/`rounded-*` must be registered in the `@theme inline` block. A bare `:root` declaration compiles clean and renders nothing — see Phase 1's baseline check and [`references/tailwind-v4-shadcn-tokens.md`](references/tailwind-v4-shadcn-tokens.md). This is the single highest-leverage thing to get right in this skill's output; get it wrong and the entire app looks flat and dated no matter how good the component markup is.
* ✅ **Sidebar collapse is two separate booleans**: `sidebarOpen` (desktop icon-rail collapse, toggle button lives in `Sidebar.tsx`) and `mobileNavOpen` (mobile drawer overlay, hamburger lives in `Navbar.tsx`). Never conflate them into one flag — see the reference doc's "Sidebar collapse" section.
* ✅ **Run `audit_scaffold.py` after editing `scaffold_saas.py`**: any new `import` in the generator itself should show up in its report and be either on the allowlist or justified. See "Security & Auditability" above.
