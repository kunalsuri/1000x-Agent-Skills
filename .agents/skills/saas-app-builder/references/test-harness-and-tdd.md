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
import React from 'react';
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
