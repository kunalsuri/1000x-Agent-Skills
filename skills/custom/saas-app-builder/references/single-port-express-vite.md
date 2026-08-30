# Single-Port Unified Serving Architecture (Port 3031)

## Why Single-Port Serving?

Traditional full-stack setups often run frontend on port 5173 and backend on port 3000, which introduces:
* CORS configuration issues.
* Authentication cookie/session domain mismatches.
* Complex environment-specific proxy rules.

The **SaaS App Builder** pattern unifies both frontend and backend on **Port 3031**:

```
Client Requests (http://localhost:3031)
              │
              ▼
   ┌───────────────────────┐
   │ Express Server (3031) │
   └──────────┬────────────┘
              │
      ┌───────┴────────┐
      ▼                ▼
 [/api/* routes]   [Static React SPA / index.html]
```

---

## Server Implementation Details

```ts
// server/server.ts
import express, { Request, Response } from 'express';
import path from 'path';
import fs from 'fs';

export const app = express();
const PORT = process.env.PORT || 3031;

app.use(express.json());

// 1. API Endpoints
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);

// 2. Static Client Fallback
// server.ts always runs from `server/` (via tsx, in both `npm run dev` and
// `npm start`) — it never actually runs from a compiled dist/server/ output.
// So `__dirname` is `<repo>/server`, and one `..` reaches the repo root,
// where the client build outputs to `dist/client`.
const clientDistPath = path.resolve(__dirname, '../dist/client');
if (fs.existsSync(clientDistPath)) {
  app.use(express.static(clientDistPath));
  app.get('*', (req: Request, res: Response) => {
    if (!req.path.startsWith('/api')) {
      res.sendFile(path.join(clientDistPath, 'index.html'));
    }
  });
}
```

**Common mistake**: using `../../dist/client` here (i.e. assuming `server.ts` runs from a compiled `dist/server/` location). It doesn't — `tsx` always executes the TypeScript source directly from `server/`. Getting this path wrong doesn't throw; `fs.existsSync` just returns `false` and the server silently falls back to its API-only dev-mode response, so *every* client route (`/`, `/dashboard`, `/login`, ...) 404s or returns the JSON fallback instead of the SPA — a symptom that's easy to misdiagnose as a build or routing problem. Always verify with a live check after `npm run build`: hit a client-only route directly (e.g. `curl -I http://localhost:3031/dashboard`) and confirm it returns the SPA's `index.html` (HTTP 200), not a 404 or the JSON dev-mode payload.

---

## Development vs. Production Workflows

* **Local Development**: Run `npm run dev` (`tsx watch server/server.ts`).
* **Client HMR (Optional)**: If ultra-fast hot module replacement is desired, run `npm run dev:client` which proxies `/api` calls directly to `http://localhost:3031`.
* **Production Build**: Run `npm run build && npm start`. Express serves the built bundle cleanly.
