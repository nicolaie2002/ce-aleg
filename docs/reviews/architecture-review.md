# Independent Production Architecture Review

> Historical snapshot for `7be9c7c` (17 July 2026). It is superseded by
> `docs/production-improvement-report.md`. Since this review, versioned release
> migrations, isolated factory tests, declarative route policies, full JS
> type-check inclusion, broader frontend coverage and typed runtime OpenAPI
> responses were implemented. Keep the findings below as review history, not as
> the current release verdict.

**Verdict: FAIL**  
**Scope:** current worktree at `HEAD 7be9c7c`, reviewed 2026-07-17  
**Focus:** Flask factory/Blueprint boundaries, Next.js architecture, API contracts,
data ownership, failure modes, maintainability, and the free-only deployment profile.

The current application has strong functional coverage and several sound production
controls, but it does not yet pass an architecture sign-off. The blockers below are
code-only changes and do not require a paid service.

## Blockers

### HIGH A-01: database schema changes run during every application import

**Evidence**

- `backend/app.py:7436` implements schema mutation inside the application module.
- `backend/app.py:7543` catches every DDL error, rolls back, logs a warning, and
  continues startup.
- `backend/app.py:17881` executes `db.create_all()`, column changes, indexes, data
  backfill, and admin mutation as an import-time side effect.
- There is no versioned migration directory or migration ledger in the repository.

**Impact:** a deploy can start serving requests after a partial or failed schema
change. Multiple process starts can race, rollback is not deterministic, and there
is no reliable downgrade or audit trail. `/health` can be green while normal routes
fail against an incompatible schema.

**Required fix:** introduce versioned Alembic/Flask-Migrate revisions, run them once
as a release step, fail the deployment on migration failure, and keep application
startup read-only with respect to schema. This is free and uses the existing DB.

### HIGH A-02: the factory and Blueprints are registration facades, not boundaries

**Evidence**

- `backend/app_factory.py:6` creates only a Flask shell; extensions, middleware,
  routes, providers, and startup work remain outside the factory.
- `backend/routes/auth.py:4` and the other domain route modules contain only an
  empty Blueprint object.
- `backend/routes/registry.py:33` assigns ownership by matching URL strings.
- `backend/routes/registry.py:70` sends every unmatched route to `system`.
- `backend/app.py:288` creates a global singleton; `backend/app.py:17878` registers
  all routes only after the 17k-line module has been evaluated.
- `backend/tests/conftest.py:16` imports and reuses that singleton instead of
  creating an isolated application per test.

Authorization and ownership are also maintained through manual endpoint-name sets
at `backend/app.py:4706`, `backend/app.py:4734`, `backend/app.py:4784`, and
`backend/app.py:4801`. A new sensitive handler is public unless its author remembers
to update the correct central set. The current middleware works, but this design is
fragile and defeats domain ownership, independent tests, and dependency inversion.

**Required fix:** move handlers into their real Blueprints, move business logic into
domain services, inject providers/repositories from a complete `create_app()`, and
attach authentication/authorization declaratively to routes or whole Blueprints.
Add a test that rejects unclassified mutating routes. No paid dependency is needed.

### HIGH A-03: frontend release gates omit most production JavaScript

**Evidence**

- `frontend/tsconfig.json:8` enables JavaScript, but `frontend/tsconfig.json:38`
  includes only `.ts` and `.tsx`; production `.js` pages are not type-checked.
- `frontend/jest.config.js:16` limits coverage to ten selected helpers/components;
  scanner, admin, alternatives, dashboard, billing, and missions pages are excluded.
- Critical pages are large client modules: `frontend/app/admin/page.js:1`,
  `frontend/app/barcode-scan/page.js:1`, `frontend/app/alternatives/page.js:1`, and
  `frontend/app/dashboard/page.js:1`.

`npm run typecheck` passes and Jest reports 95.83% statements, but those numbers do
not measure most production UI code. This creates false confidence around contract
changes and regressions in the highest-risk flows.

**Required fix:** enable `checkJs` and include `.js/.jsx` immediately, then migrate
critical contracts/pages incrementally to TypeScript. Expand Jest collection to
critical hooks/components and keep Playwright coverage for full user flows. All of
this is local tooling and free.

## Major Findings

### MEDIUM A-04: the OpenAPI contract is complete by path, not by schema

- Shared validation is a good start, but `backend/app.py:5439` maps only a subset of
  endpoints to reusable validators.
- `backend/app.py:7757` adds the remaining runtime routes dynamically, while
  `backend/app.py:7790` gives them generic responses without real payload schemas.
- Runtime inspection found 108 operations: 21 had request bodies, 37 had a typed
  success response, and 71 had only the generic `Successful response`.
- Frontend errors still depend partly on Romanian message-string matching at
  `frontend/app/utils/apiResponse.js:27` and `frontend/app/utils/apiResponse.js:163`.

**Risk:** backend and frontend can drift while OpenAPI, tests, and typecheck remain
green. Make stable error codes universal, define request/response schemas for every
frontend-consumed route, and generate or validate a client from that contract.

### MEDIUM A-05: free-mode rate limiting is process-local and racy

- `render.yaml:5` and `render.yaml:8` deliberately use one free worker with four
  threads.
- `backend/app.py:121` stores fallback buckets in process memory.
- `backend/app.py:2605` uses Redis only when configured; `backend/app.py:2620`
  mutates the local deque without synchronization.

The one-worker choice limits cross-process drift, but cold starts erase limits and
four threads can interleave the check/append sequence. This is acceptable as
best-effort throttling, not as an abuse/security invariant. A free-safe improvement
is a PostgreSQL-backed atomic limiter for sensitive endpoints, while keeping local
caches for non-sensitive performance.

### MEDIUM A-06: critical Next.js pages combine UI, orchestration, and contracts

- `frontend/app/admin/page.js:158`, `frontend/app/barcode-scan/page.js:258`,
  `frontend/app/dashboard/page.js:98`, and
  `frontend/app/alternatives/page.js:2243` own large amounts of state, networking,
  transformation, and rendering in one client component.
- `frontend/app/components/AutomaticPageTranslation.js:179` mutates rendered DOM
  through a global `MutationObserver`; `frontend/app/layout.js:176` always renders
  the initial document as Romanian.

**Risk:** difficult isolation, repeated fetch/error patterns, broad rerenders, and
English output that can differ between initial HTML and hydrated DOM. Extract domain
hooks and view components, centralize the API client, and replace DOM translation
with keyed locale resources rendered directly by React.

### MEDIUM A-07: the new latency gate is a microbenchmark, not production evidence

- `scripts/benchmark-backend.py:20` disables external providers and uses in-memory
  SQLite.
- `scripts/benchmark-backend.py:98` measures a warm Flask test client in-process.
- `scripts/verify-project.ps1:38` labels the result representative backend p95.

The uncommitted change does not regress runtime behavior, but a 500 ms pass cannot
predict Render cold start, network, Supabase, or provider latency. Keep it as a
regression microbenchmark, rename it accordingly, and complement it with a low-rate
live smoke check that stays within free quotas.

## Strengths Verified

- Production config fails closed for missing Postgres and weak auth secrets at
  `backend/config.py:79` and `backend/config.py:85`.
- Stripe webhook signature and persistent event idempotency are implemented at
  `backend/app.py:9030` and `backend/app.py:9061`.
- Transaction/catalog locking uses database locks at `backend/app.py:2469` and
  `backend/app.py:2478`.
- External catalog and price providers have kill switches; paid vision remains off
  in the free profile at `render.yaml:115` and `render.yaml:123`.
- Same-origin API proxying is centralized at `frontend/next.config.mjs:100`, and
  protected-page checks are enforced at `frontend/proxy.js:51` with backend
  authorization still authoritative.
- Current read-only verification passed: backend `330/330`, frontend `55/55`,
  targeted config/contract/distributed-control tests `43/43`, and `tsc --noEmit`.
- Tracked backend coverage reports 73.01%; the 70% backend release threshold is met.

## Free-Only Assessment

**PASS with constraints:** the code does not require a new paid AI, cache,
observability, or backup product. OCR/local vision, optional integrations, Supabase,
GitHub Actions, and the single Render worker form a workable zero-new-subscription
profile.

**Residual operational limits:** free hosting has cold starts, quotas, no SLA, one
backend instance, and optional alerting. The backup remains a 30-day GitHub artifact
at `.github/workflows/backup.yml:50`, so a successful scheduled run and isolated
restore drill are still required. `docs/architecture.md:162` also correctly flags
Stripe transaction fees, domain renewal, and the need to verify Vercel Hobby terms;
these cannot be removed through architecture changes.

## Sign-Off Conditions

Architecture can move to **PASS** after all three HIGH findings are fixed and the
following evidence is attached:

1. versioned migration upgrade/rollback tested against a disposable Postgres DB;
2. a real factory test creating two isolated apps with different configs;
3. route-classification test proving every non-public route has explicit policy;
4. frontend typecheck/coverage includes critical production modules;
5. OpenAPI contract tests validate every frontend-consumed request and response;
6. complete local gates plus live smoke, backup, restore, Stripe, and email checks.

Until then, functional regression status is **PASS**, but independent production
architecture status is **FAIL**.
