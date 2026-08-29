# 🏛️ Test Pyramid & Hermetic Testing Strategy

This guide establishes universal testing principles, test level taxonomy, fixture isolation patterns, and anti-patterns to avoid.

---

## 1. The Pre-Flight Test Pyramid

```text
         ▲
        / \
       /E2E\        10% - Smoke & Critical Flows (Slow, broad)
      /-----\
     / Integ \      20% - Service contracts & API boundaries
    /---------\
   /   Unit    \    70% - Pure functions, logic, state transitions (Fast, hermetic)
  /-------------\
```

| Layer | Primary Focus | Execution Speed | Isolation Level |
|---|---|---|---|
| **Smoke / Pre-Flight** | Import graph, configuration sanity, dependency health | < 1 second | Isolated runtime |
| **Unit Tests** | Pure logic, algorithms, edge conditions, parsing | < 5 seconds | 100% Mocked / In-memory |
| **Component Tests** | UI render, event handling, accessible role queries | < 10 seconds | Virtual DOM (`jsdom`) |
| **Integration Tests** | Multi-module boundaries, DB migrations, API routes | < 30 seconds | In-memory DB / MSW |

---

## 2. The 5 Core Principles of Hermetic Testing

1. **Zero External Network Dependencies**: All outbound HTTP, database, and third-party API connections MUST be intercepted using mocks, stubs, or in-memory fixtures.
2. **Deterministic & Idempotent**: A test suite must produce the exact same outcome whether run 1 time or 1,000 times in parallel.
3. **No Cross-Test Leaks**: Reset environment variables, global state, singletons, and cache directories between every test (`autouse=True` or `afterEach`).
4. **Fast Feedback Loop**: The unit test suite should execute within seconds on standard hardware.
5. **Clear Error Diagnostics**: Assertions must provide meaningful diagnostic messages with actionable context.

---

## 3. Boundary & Negative Case Checklist

When authoring test suites for any function or component, systematically test:

- [ ] **Empty / Zero Cases**: `""`, `[]`, `{}`, `0`, `None`, `null`, `undefined`
- [ ] **Boundary Extremes**: Very large strings, negative numbers, floating point precision
- [ ] **Invalid Formats**: Malformed JSON, non-UTF8 strings, bad date formats
- [ ] **Error Handling**: Network timeout simulation, HTTP 400/401/403/500 responses
- [ ] **Race Conditions & Concurrency**: Fast double clicks, concurrent async requests

---

## 4. Testing Anti-Patterns to Avoid

- ❌ **Testing Implementation Details**: Don't assert private variable names or internal method call orders unless essential. Assert observable behavior and outputs.
- ❌ **Shared Mutable State**: Never share mutable database tables or global state across tests without explicit reset teardowns.
- ❌ **Sleep Delays in Async Tests**: Avoid `time.sleep()` or `setTimeout()` in tests. Use explicit async polling, `waitFor()`, or event-driven promises.
- ❌ **Unasserted Mocks**: Creating a mock without verifying either its call parameters or its return impact.
