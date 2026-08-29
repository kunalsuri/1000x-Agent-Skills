# ⚛️ TypeScript & React Testing Reference & Recipes

This guide documents deep patterns, DOM component assertions, mock service workers (MSW), and accessibility testing using **Vitest**, **React Testing Library (RTL)**, **user-event**, and **fast-check**.

---

## 1. Directory Structure & Vitest Configuration

Standard layout for TypeScript / React test suites:

```text
tests/
├── setup.ts                  # DOM polyfills, MSW server lifecycle, test cleanup
├── fixtures/
│   └── mock_users.ts         # Typed factories and mock state objects
├── smoke/
│   └── preflight_smoke.test.ts # Entrypoint & export integrity verification
├── unit/
│   └── formatters.test.ts    # Pure TypeScript helper & algorithm tests
├── components/
│   ├── Button.test.tsx       # React Testing Library interaction tests
│   └── UserCard.test.tsx
└── integration/
    └── api_client.test.ts    # Service boundary tests with Mock Service Worker
```

### `vitest.config.ts` Example:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
});
```

---

## 2. React Component Testing (RTL + `user-event`)

Test components from the user's perspective rather than internal state implementation details.

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { LoginForm } from '../../src/components/LoginForm';

describe('<LoginForm />', () => {
  it('submits valid credentials when clicked', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<LoginForm onSubmit={handleSubmit} />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'kunal@example.com');
    await user.type(passwordInput, 'Secret123!');
    await user.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    expect(handleSubmit).toHaveBeenCalledWith({
      email: 'kunal@example.com',
      password: 'Secret123!',
    });
  });

  it('displays validation error on empty submit', async () => {
    const user = userEvent.setup();
    render(<LoginForm onSubmit={vi.fn()} />);

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitBtn);

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });
});
```

---

## 3. Network Interception with Mock Service Worker (MSW)

Hermetically intercept network calls at the network level without mocking `fetch` manually.

```typescript
// tests/setup.ts
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { beforeAll, afterAll, afterEach } from 'vitest';

export const handlers = [
  http.get('https://api.example.com/user', () => {
    return HttpResponse.json({ id: '123', name: 'Alice' });
  }),
];

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## 4. Accessibility Testing (`axe-core` / `jest-axe`)

Ensure components satisfy WCAG accessibility standards.

```tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { Header } from '../../src/components/Header';

expect.extend(toHaveNoViolations);

it('should have zero accessibility violations', async () => {
  const { container } = render(<Header title="Dashboard" />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

---

## 5. Property-Based Testing in TypeScript (`fast-check`)

```typescript
import * as fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { parseJsonSafe } from '../../src/utils/json';

describe('Property tests for parseJsonSafe', () => {
  it('never throws regardless of arbitrary string input', () => {
    fc.assert(
      fc.property(fc.string(), (input) => {
        const result = parseJsonSafe(input);
        expect(result).toBeDefined();
      })
    );
  });
});
```
