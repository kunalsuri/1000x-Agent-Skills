# Maintenance & Package Upgrades Guide

## Centralized Manifest

All package dependencies for scaffolded projects are defined in the `PACKAGE_MANIFEST` dictionary inside `skills/custom/saas-app-builder/scripts/scaffold_saas.py`.

```python
PACKAGE_MANIFEST = {
    "name": "my-saas-app",
    "version": "1.0.0",
    "dependencies": {
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "react-router-dom": "^7.1.0",
        "@tanstack/react-query": "^5.62.0",
        "zustand": "^5.0.2",
        "lucide-react": "^0.468.0",
        "clsx": "^2.1.1",
        "tailwind-merge": "^2.5.5",
        "class-variance-authority": "^0.7.1",
        "@radix-ui/react-slot": "^1.1.1",
        "zod": "^3.24.1",
        "express": "^4.21.2",
        "cors": "^2.8.5",
        "bcryptjs": "^2.4.3"
    },
    "devDependencies": {
        "@tailwindcss/vite": "^4.0.0",
        "tailwindcss": "^4.0.0",
        "vite": "^6.0.3",
        "@vitejs/plugin-react": "^4.3.4",
        "typescript": "^5.7.2",
        "tsx": "^4.19.2",
        "vitest": "^2.1.8",
        "@testing-library/react": "^16.1.0",
        "@testing-library/jest-dom": "^6.6.3",
        "supertest": "^7.0.0"
    }
}
```

---

## How to Upgrade to Newer Packages

1. **Update Pinned Versions**: Bump version strings in `PACKAGE_MANIFEST` within `scaffold_saas.py`.
2. **Add New shadcn Primitives**: Add the component source code to `scaffold_saas.py` under the template section (e.g. `CLIENT_DIALOG_TSX`, `CLIENT_TABLE_TSX`).
3. **Validate the generator itself**:
   ```bash
   python scripts/audit_scaffold.py scripts/scaffold_saas.py
   ```
   (There is no `scripts/validate_skills.py` in this skill — that was a stale reference. `audit_scaffold.py` is this skill's own validator; see "Security & Auditability" in `SKILL.md`.)
4. **Test Scaffolding**: Run scaffolding into a temporary folder and confirm clean generation:
   ```bash
   python scripts/scaffold_saas.py --name test-app --target-dir /tmp/test-app
   cd /tmp/test-app && npm install && npm run verify && npm run build
   grep -c '\.bg-primary\b' dist/client/assets/*.css   # must be > 0
   ```
   If you touched anything auth-related (`authController.ts`, `authMiddleware.ts`, `seedUsers.ts`, `DATA_USERS_JSON`), also re-run the live checks in `SKILL.md` Phase 5 step 3 plus a login round-trip (correct password succeeds, wrong password 401s) — `npm run verify` passing does not prove auth actually enforces anything; see the v1.5.0 entry in `attestation.json` for why that distinction mattered here before.
