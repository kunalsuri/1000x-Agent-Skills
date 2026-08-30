# Test Suite Harness & Autonomous Agent TDD Loop

## 4-Harness Architecture Overview

The scaffolded SaaS monorepo includes a 4-layer verification harness:

1. **Vitest + React Testing Library**: Fast, in-memory component and hook testing.
2. **Supertest**: Direct HTTP endpoint testing against the Express server.
3. **TypeScript Typecheck (`tsc --noEmit`)**: Catches API contract and prop mismatches.
4. **Shared Zod Contracts**: Validates runtime payloads and synchronizes types.

---

## 🔁 The Autonomous Self-Correction Loop

When generating or modifying features:

```
[Write Feature Code] ──> Run 'npm run verify' ──> [Success] ──> Proceed
                               │
                          [Test Failure]
                               │
                     [Inspect Line & Trace]
                               │
                       [Apply Fix & Diff]
                               │
                      [Re-run 'npm run verify']
```

---

## Writing Backend API Tests (Supertest)

```ts
// server/__tests__/invoices.test.ts
import { describe, it, expect } from 'vitest';
import request from 'supertest';
import { app } from '../server.js';

describe('Invoices API', () => {
  it('GET /api/invoices returns list of items', async () => {
    const res = await request(app)
      .get('/api/invoices')
      .set('Authorization', 'Bearer mock_jwt_token_alex');

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.invoices)).toBe(true);
  });

  it('POST /api/invoices validates required fields', async () => {
    const res = await request(app)
      .post('/api/invoices')
      .set('Authorization', 'Bearer mock_jwt_token_alex')
      .send({});

    expect(res.status).toBe(400);
    expect(res.body.error).toBeDefined();
  });
});
```

---

## Writing React Component Tests (Vitest + RTL)

```tsx
// client/src/features/invoices/__tests__/InvoiceCard.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InvoiceCard } from '../components/InvoiceCard';

describe('InvoiceCard', () => {
  it('displays invoice amount and client name', () => {
    const mockInvoice = {
      id: 'inv_1',
      clientName: 'Acme Corp',
      amount: 1500,
      status: 'paid' as const,
    };

    render(<InvoiceCard invoice={mockInvoice} />);
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('$1,500')).toBeInTheDocument();
  });
});
```

---

## ⚠️ File-Backed Storage & Test Isolation

`readJsonFile` / `writeJsonFile` operate on plain `data/*.json` files with no locking. `vitest.config.ts` sets `fileParallelism: false` for exactly this reason — running test files in parallel lets one suite's write interleave with another suite's read of the same file (e.g. two domain test files both touching a shared `projects.json`), which surfaces as an intermittent `Unexpected end of JSON input` failure. Leave `fileParallelism: false` in place when adding new domain test files; do not re-enable it to "speed up" `npm test`.

Because tests run against the same `data/*.json` files as `npm run dev`, write **self-cleaning** integration tests for create/update/delete flows so repeated `npm test` runs don't leave garbage in the seed data:

```ts
it('creates, updates, and deletes an item', async () => {
  const createRes = await request(app).post('/api/invoices').set('Authorization', AUTH).send({ /* ... */ });
  const { id } = createRes.body.invoice;

  await request(app).patch(`/api/invoices/${id}`).set('Authorization', AUTH).send({ status: 'paid' });

  // Clean up — leaves data/invoices.json exactly as it started.
  await request(app).delete(`/api/invoices/${id}`).set('Authorization', AUTH);
});
```
