# Verification record

Verified on 30 September 2026.

| Check | Result |
| --- | --- |
| Python API, policy, security, idempotency and concurrency tests | 34 passed |
| Frontend production build | Passed (Vite) |
| Python dependency consistency | Passed (`pip check`) |
| Compose YAML structure | Parsed and checked; not equivalent to running Docker |
| Browser initial load | Passed; customer interface rendered, no page errors |
| Complete browser flows and recording | Passed: approval, denial, escalation, history, support review, audit, policy navigation, mobile layout and injection escalation; no page errors |
| Docker build and Compose smoke | Passed in GitHub Actions: containers built, became healthy, and the proxied API completed approve/deny/escalate/manual-review flows |
| Real OpenAI request | Not executed: user API key required. HTTP adapter tested against mocked provider responses. |

The suite covers approvals, final-sale and expired-order denial, already-refunded orders, the $500 boundary, future dates, duplicate and concurrent submissions, customer isolation, role checks, support review, hard-rule enforcement, invalid/expired tokens, input bounds, login rate limiting, injection patterns, negated claims, invalid model output, live-provider failure, and restart recovery.

Known test warning: Starlette reports that its httpx-based TestClient compatibility is deprecated in favor of httpx2. Tests still pass; this does not affect the runtime API.

CI evidence: [successful verification run](https://github.com/Yemsquare/worknoon/actions/runs/36700181925), code commit `12ff1e2b63ce39ddff6c75e2b62de03ae1c2c2d0`. Later documentation/recording updates do not change runtime application code.

## Honest completion boundaries

Demo-mode success does not prove live-provider availability. Container startup and API flows were verified on the CI runner. Before submitting, run locally and verify one genuine `mode: live` request using your own API key, and review the walkthrough so you can explain the implementation yourself.
