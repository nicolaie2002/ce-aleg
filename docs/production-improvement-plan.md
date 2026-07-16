# Ce Aleg - Production Improvement Plan

**Generated:** July 16, 2026  
**Based on:** Parallel analysis of frontend, backend, testing, infrastructure, security/compliance, documentation

---

## Executive Summary

This plan addresses 15 improvement areas identified in the audit, organized into 7 implementation waves. Each wave has clear dependencies, file ownership to prevent conflicts, and validation gates.

**Current State:** Production-deployed (Vercel + Render + Supabase) with solid core functionality but gaps in observability, scalability, compliance, and developer experience.

**Target State:** Production-hardened system with distributed rate limiting/caching, full test coverage, OpenAPI docs, GDPR-compliant tooling, PWA support, and automated operations.

---

## Wave Dependency Graph

```
WAVE 1: FOUNDATION (Testing + Validation + OpenAPI + Error Boundaries + Sentry + a11y)
    │
    ├─► Test Infrastructure (Jest + pytest) ──► Required for all subsequent waves
    ├─► Input Validation (marshmallow) ──► Required for OpenAPI, Stripe, Admin
    ├─► OpenAPI Docs (flask-smorest) ──► Required for FE type generation
    ├─► Error Boundary + Sentry (FE + BE) ──► Required for production observability
    └─► eslint-plugin-jsx-a11y + basic fixes ──► Required for accessibility baseline
    │
    ▼
WAVE 2: INFRASTRUCTURE (Redis + Rate Limiting + Caching + Stripe Portal + Webhook Hardening)
    │
    ├─► Redis/Upstash provisioning ──► Prerequisite for rate limiting + caching
    ├─► Distributed Rate Limiting (flask-limiter) ──► Replaces in-memory defaultdict
    ├─► Distributed Caching (flask-caching) ──► Replaces in-memory dicts
    ├─► Stripe Billing Portal ──► Self-service subscription management
    ├─► Stripe Webhook Idempotency + Alerting ──► Prevents duplicate processing
    └─► Structured Logging (JSON) ──► Enables log aggregation
    │
    ▼
WAVE 3: USER EXPERIENCE (i18n + PWA + Analytics + AI Visual Assistant + Cookie Consent)
    │
    ├─► next-intl migration ──► Replaces custom LocaleProvider
    ├─► PWA (@neshca/pwa-next) ──► Offline support, installability
    ├─► PostHog Analytics ──► Replaces GA4/Meta/TikTok, feature flags
    ├─► AI Visual Assistant (feature-flagged, provider abstraction) ──► Future-ready
    └─► Granular Cookie Consent + Server logging ──► GDPR/ePrivacy compliance
    │
    ▼
WAVE 4: OPERATIONS (Backup + Catalog Monitoring + Alerting + Runbooks)
    │
    ├─► Automated Supabase Backup (GitHub Actions + pg_dump) ──► Disaster recovery
    ├─► Catalog Quality Checks + Admin Report ──► Data quality automation
    ├─► Configurable Alerting (Sentry/Slack/Email) ──► Proactive incident response
    └─► Operational Runbooks ──► Incident response procedures
    │
    ▼
WAVE 5: LEGAL/COMPLIANCE (GDPR Tooling + DPA Docs + Consent Records)
    │
    ├─► Data Export Endpoint (Art 20) ──► User data portability
    ├─► Data Access Endpoint (Art 15) ──► Right of access
    ├─► Restriction of Processing (Art 18) ──► Pause without delete
    ├─► Processor DPA Documentation ──► Legal compliance
    ├─► Consent Logging Server-side ──► Audit trail
    └─► Retention Policies + Cleanup Jobs ──► Data minimization
    │
    ▼
WAVE 6: CODE QUALITY (Refactoring + Type Safety + CI Hardening)
    │
    ├─► Flask App Factory + Blueprints ──► Maintainability
    ├─► Stripe Python 11→15 Migration ──► Security/support
    ├─► Frontend TypeScript Strict Mode ──► Type safety
    ├─► E2E Tests (Playwright) ──► Critical user flows
    └─► CI Gates (lint + test + build + a11y + secret scan)
    │
    ▼
WAVE 7: FINAL REVIEW (Security Review + Regression Testing + Documentation)
    │
    ├─► Code Review (3 subagents)
    ├─► Security Review
    ├─► Regression Testing
    ├─► Documentation Update
    └─► Production Readiness Sign-off
```

---

## Wave 1: Foundation (Week 1-2)

**Goal:** Establish test infrastructure, validation, docs, observability, accessibility baseline

### 1.1 Frontend Test Setup (Jest + React Testing Library)

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/jest.config.js` - New
- `frontend/jest.setup.js` - New
- `frontend/.github/workflows/test-frontend.yml` - New
- `frontend/package.json` - Add deps
- `frontend/tsconfig.json` - Add test types

**Dependencies to Add:**
```json
{
  "devDependencies": {
    "jest": "^29.7.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/user-event": "^14.5.0",
    "jest-environment-jsdom": "^29.7.0",
    "ts-jest": "^29.2.0",
    "@types/jest": "^29.5.0",
    "identity-obj-proxy": "^3.0.0"
  }
}
```

**Test Structure:**
```
frontend/
├── __tests__/
│   ├── components/
│   │   ├── AppHeader.test.tsx
│   │   ├── ProductImage.test.tsx
│   │   ├── CookieConsentBanner.test.tsx
│   │   └── LanguageSwitcher.test.tsx
│   ├── utils/
│   │   ├── apiResponse.test.ts
│   │   ├── profilePreferences.test.ts
│   │   └── passwordStrength.test.ts
│   └── integration/
│       └── scan-flow.test.tsx
```

**Validation Gate:** `npm test` passes, coverage > 60% on utils/components

---

### 1.2 Backend Test Setup (pytest)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/pytest.ini` - New
- `backend/conftest.py` - New (fixtures: app, client, db, user, auth_headers)
- `backend/tests/` - New directory
- `backend/requirements.txt` - Add test deps
- `.github/workflows/test-backend.yml` - New

**Dependencies to Add:**
```txt
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
pytest-flask>=1.3.0
factory-boy>=3.3.0
faker>=25.0.0
responses>=0.25.0
```

**Test Structure:**
```
backend/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_cart.py
│   ├── test_favorites.py
│   ├── test_history.py
│   ├── test_submissions.py
│   ├── test_billing.py
│   ├── test_gamification.py
│   ├── test_admin.py
│   ├── test_feedback.py
│   └── test_utils.py
```

**Validation Gate:** `pytest --cov=app --cov-report=term-missing` passes, coverage > 70%

---

### 1.3 Input Validation (marshmallow schemas)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/validation.py` - **NEW** (all request schemas)
- `backend/app.py` - Import and use schemas in endpoints
- `backend/requirements.txt` - Add `marshmallow>=3.20`

**Schema Coverage (80+ endpoints):**

| Category | Endpoints | Priority |
|----------|-----------|----------|
| Auth | register, login, verify-email, forgot-password, reset-password, delete-account | P0 |
| Products | search, analyze, barcode-lookup, seed, alternatives | P0 |
| Cart | add, update, delete, clear | P1 |
| Favorites | add, delete, clear | P1 |
| History | add, delete, clear | P1 |
| Submissions | add, ai-review, approve | P1 |
| Billing | checkout, portal, cecoin-checkout, cecoin-sync | P0 |
| Gamification | summary, claim, redeem, coin-packs | P1 |
| Family | profiles CRUD | P1 |
| Admin | all 18 endpoints | P1 |
| Feedback | alternative, product, contact | P1 |
| AI/Translate | extract, identify, translate | P2 |

**Example Schema:**
```python
# validation.py
from marshmallow import Schema, fields, validate, validates, ValidationError

class RegisterSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    age_confirmed = fields.Bool(required=True, validate=validate.Equal(True))
    terms_accepted = fields.Bool(required=True, validate=validate.Equal(True))
    invite_code = fields.Str(validate=validate.Length(max=30), missing=None)
    turnstile_token = fields.Str(missing=None)

class ProductSearchSchema(Schema):
    q = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    store = fields.Str(validate=validate.OneOf(["lidl", "kaufland", "carrefour", "mega", "profi", "penny", "local", "any"]), missing="any")
    user_id = fields.Int(missing=None)

# In app.py - apply via decorator
from functools import wraps
def validate_json(schema_class):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            schema = schema_class()
            try:
                data = schema.load(request.get_json() or {})
                request.validated_data = data
            except ValidationError as err:
                return jsonify({"error": "Invalid request", "details": err.messages}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

**Validation Gate:** All public endpoints return 400 with structured errors for invalid input

---

### 1.4 OpenAPI Documentation (flask-smorest)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/api_docs.py` - **NEW** (APISpec + flask-smorest setup)
- `backend/app.py` - Register blueprint, mount `/api/docs`, `/api/openapi.json`
- `backend/requirements.txt` - Add `flask-smorest>=0.44`, `apispec>=6.0`, `marshmallow>=3.20`

**Implementation:**
```python
# api_docs.py
from flask_smorest import Api
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

def init_api_docs(app):
    app.config.update({
        "API_TITLE": "Ce Aleg API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.1.0",
        "OPENAPI_URL_PREFIX": "/api/docs",
        "OPENAPI_SWAGGER_UI_PATH": "/",
        "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
        "OPENAPI_REDOC_PATH": "/redoc",
        "OPENAPI_REDOC_URL": "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    })
    
    spec = APISpec(
        title="Ce Aleg API",
        version="v1",
        openapi_version="3.1.0",
        plugins=[MarshmallowPlugin()],
    )
    
    api = Api(app, spec=spec)
    
    # Register blueprints with schemas
    from .validation import (
        RegisterSchema, LoginSchema, ProductSearchSchema,
        CartAddSchema, FavoriteAddSchema, SubmissionAddSchema,
        CheckoutSchema, CoinCheckoutSchema, MissionClaimSchema,
        FeedbackAlternativeSchema, FeedbackProductSchema
    )
    
    # Tag each endpoint with schema
    return api
```

**Frontend Type Generation (Wave 3 dependency):**
```bash
# Add to frontend package.json scripts
"generate:api": "openapi-typescript http://localhost:5001/api/openapi.json -o src/types/api.d.ts"
```

**Validation Gate:** `GET /api/openapi.json` returns valid OpenAPI 3.1 spec; Swagger UI loads at `/api/docs`

---

### 1.5 Global Error Boundary + Sentry (Frontend)

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/sentry.client.config.ts` - **NEW**
- `frontend/sentry.server.config.ts` - **NEW**
- `frontend/sentry.edge.config.ts` - **NEW**
- `frontend/instrumentation.ts` - **NEW** (Node instrumentation hook)
- `frontend/app/error.tsx` - **NEW** (Global error boundary)
- `frontend/app/global-error.tsx` - **NEW** (Root layout error)
- `frontend/app/layout.js` - Wrap with Sentry provider
- `frontend/package.json` - Add `@sentry/nextjs`
- `frontend/next.config.mjs` - Sentry webpack plugin
- `frontend/.env.example` - Add `NEXT_PUBLIC_SENTRY_DSN`

**Implementation:**
```typescript
// sentry.client.config.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
    Sentry.feedbackIntegration({
      colorScheme: 'dark',
      triggerLabel: 'Feedback',
    }),
  ],
  environment: process.env.NEXT_PUBLIC_VERCEL_ENV || 'development',
  release: process.env.NEXT_PUBLIC_APP_VERSION,
});
```

```tsx
// app/error.tsx
'use client';
import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0b0f14] text-white p-4">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Ceva nu a mers</h2>
        <p className="text-gray-300 mb-6">Ne cerem scuze. Eroarea a fost raportată automat.</p>
        <button
          onClick={() => reset()}
          className="px-6 py-3 bg-white text-black font-bold rounded-xl hover:bg-cyan-100"
        >
          Reîncearcă
        </button>
      </div>
    </div>
  );
}
```

**Validation Gate:** Error thrown in component → captured in Sentry, error.tsx renders, reset works

---

### 1.6 Sentry Backend Integration

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/sentry_init.py` - **NEW** (import before app)
- `backend/app.py` - Import sentry_init at top
- `backend/requirements.txt` - Add `sentry-sdk[flask]>=2.65`
- `backend/.env.example` - Add `SENTRY_DSN`

**Implementation:**
```python
# sentry_init.py
import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

def init_sentry():
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return
    
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FlaskIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get("APP_ENV", "development"),
        release=os.environ.get("RENDER_GIT_COMMIT", "local"),
        send_default_pii=False,
        before_send=filter_sensitive_data,
    )

def filter_sensitive_data(event, hint):
    # Remove PII from events
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if isinstance(data, dict):
            for key in ['password', 'password_hash', 'token', 'secret', 'email']:
                if key in data:
                    data[key] = '[REDACTED]'
    return event
```

```python
# app.py - TOP of file, before any other imports
from sentry_init import init_sentry
init_sentry()
```

**Validation Gate:** Backend error → captured in Sentry with transaction context

---

### 1.7 Accessibility - eslint-plugin-jsx-a11y + Basic Fixes

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/eslint.config.mjs` - Extend with jsx-a11y recommended
- `frontend/package.json` - Add `eslint-plugin-jsx-a11y` (already in next config, enable rules)
- `frontend/app/components/` - Fix violations in components

**ESLint Config:**
```javascript
// eslint.config.mjs
import jsxA11y from "eslint-plugin-jsx-a11y";

export default [
  // ... existing config
  ...jsxA11y.configs.recommended,
  {
    rules: {
      "jsx-a11y/anchor-is-valid": "error",
      "jsx-a11y/click-events-have-key-events": "error",
      "jsx-a11y/no-noninteractive-element-interactions": "error",
      "jsx-a11y/role-has-required-aria-props": "error",
      "jsx-a11y/aria-props": "error",
      "jsx-a11y/img-alt": ["error", { components: ["Image"], elements: ["img"] }],
      "jsx-a11y/no-autofocus": "warn",
      "jsx-a11y/tabindex-no-positive": "error",
    },
  },
];
```

**Priority Component Fixes:**

| Component | Issues to Fix |
|-----------|---------------|
| `CookieConsentBanner.js` | Add `role="dialog"`, `aria-modal="true"`, focus trap, `Escape` to close |
| `LanguageSwitcher.js` | Add `aria-label`, `aria-pressed` on buttons |
| `ConfirmModal.js` | Focus management, `aria-labelledby`, `Escape` close |
| `ProductImage.js` | Ensure `alt` from product name, not empty |
| `AppHeader.js` | Navigation landmarks, `aria-current` |
| `Scan page` | Camera permission rationale, loading `aria-live` |

**Validation Gate:** `npm run lint` passes with zero a11y errors; manual audit of key flows

---

## Wave 2: Infrastructure (Week 2-3)

**Goal:** Distributed rate limiting, caching, Stripe portal, webhook hardening, structured logging

### 2.1 Redis/Upstash Provisioning

**Owner:** Infrastructure Agent  
**Files to Create/Modify:**
- `render.yaml` - Add Redis service
- `backend/.env.example` - Add `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`
- `frontend/.env.example` - Add `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`

**render.yaml Addition:**
```yaml
services:
  - type: redis
    name: cealeg-redis
    plan: free
    maxmemoryPolicy: allkeys-lru
    ipAllowList: []  # Restrict to Render VPC
```

**Upstash Account Setup:**
1. Create account at upstash.com
2. Create Redis database (EU region)
3. Copy `UPSTASH_REDIS_URL` and `UPSTASH_REDIS_TOKEN`
4. Add to Render Environment Variables
5. Add to Vercel Environment Variables

---

### 2.2 Distributed Rate Limiting (flask-limiter)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/rate_limiter.py` - **NEW** (configuration)
- `backend/app.py` - Replace in-memory rate limiting
- `backend/requirements.txt` - Add `flask-limiter>=3.11`, `upstash-redis>=1.31`

**Implementation:**
```python
# rate_limiter.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from upstash_redis import Redis
import os

redis_client = Redis(
    url=os.environ["UPSTASH_REDIS_URL"],
    token=os.environ["UPSTASH_REDIS_TOKEN"],
)

def get_rate_limit_key():
    # User-ID based for authenticated, IP for anonymous
    from flask import request, g
    if hasattr(g, 'user') and g.user:
        return f"user:{g.user.id}"
    return get_remote_address()

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=f"redis://:{os.environ['UPSTASH_REDIS_TOKEN']}@{os.environ['UPSTASH_REDIS_URL'].replace('https://', '').replace('http://', '')}",
    default_limits=["300 per minute"],
    headers_enabled=True,  # X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After
)

# Per-endpoint limits (apply in app.py)
RATE_LIMITS = {
    "auth": "5 per 15 minutes",
    "barcode": "45 per minute",
    "translate": "120 per minute",
    "ai_off": "30 per minute",
    "contact": "20 per minute",
    "scan": "10 per minute",
    "search": "60 per minute",
}
```

**In app.py - Replace rate_limit() function:**
```python
# Remove RATE_LIMIT_BUCKETS and rate_limit() function
# Apply @limiter.limit() decorators on routes
```

**Validation Gate:** Multiple concurrent requests from same IP/user → proper 429 with headers; works across multiple gunicorn workers

---

### 2.3 Distributed Caching (flask-caching)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/cache.py` - **NEW** (cache configuration + helpers)
- `backend/app.py` - Replace all in-memory caches
- `backend/requirements.txt` - Add `flask-caching>=2.1`

**Implementation:**
```python
# cache.py
from flask_caching import Cache
import os

cache = Cache(config={
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": f"redis://:{os.environ['UPSTASH_REDIS_TOKEN']}@{os.environ['UPSTASH_REDIS_URL'].replace('https://', '').replace('http://', '')}",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "cealeg:",
})

# Cache key namespacing
class CacheKeys:
    OFF_ALTERNATIVES = "off:alt:{category}"
    OFF_PRODUCT = "off:prod:{barcode}"
    PRODUCT_SEARCH = "search:{query}:{store}"
    OPEN_PRICES = "prices:{barcode}"
    LEADERBOARD = "leaderboard:{period}"
    CATALOG_STATS = "catalog:stats"
    RECOMMENDATION_FAMILY = "rec:family:{key}"
    RECOMMENDATION_TEXT = "rec:text:{key}"

# Helper functions with metrics
def get_cached(key, factory, ttl=None):
    """Get from cache or call factory, track hit/miss."""
    value = cache.get(key)
    if value is not None:
        record_cache_hit(key)
        return value
    record_cache_miss(key)
    value = factory()
    cache.set(key, value, timeout=ttl)
    return value

def invalidate_pattern(pattern):
    """Invalidate all keys matching pattern."""
    # Use SCAN + DELETE for production
    pass
```

**Migration Map (in-memory → Redis):**

| In-Memory Cache | New Redis Key | TTL |
|-----------------|---------------|-----|
| `OPEN_FOOD_FACTS_ALTERNATIVES_CACHE` | `off:alt:{category}` | 600s |
| `OPEN_FOOD_FACTS_PRODUCT_CACHE` | `off:prod:{barcode}` | 3600s |
| `PRODUCT_SEARCH_RESULT_CACHE` | `search:{query}:{store}` | 900s |
| `OPEN_PRICES_CACHE` | `prices:{barcode}` | 1800s |
| `AI_STATUS_CACHE` | `ai:status` | 30s |
| `LEADERBOARD_CACHE` | `leaderboard:{period}` | 60s |
| `PUBLIC_CATALOG_STATS_CACHE` | `catalog:stats` | 300s |
| `RECOMMENDATION_FAMILY_CACHE` | `rec:family:{hash}` | 3600s |
| `PRODUCT_RECOMMENDATION_TEXT_CACHE` | `rec:text:{hash}` | 3600s |

**Fallback:** If Redis unavailable, gracefully degrade to no-cache (factory called every time)

**Validation Gate:** Cache hit/miss metrics visible in logs; cache survives deploy/restart

---

### 2.4 Stripe Billing Portal

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/app.py` - Add `/billing/portal` endpoint
- `frontend/app/dashboard/page.js` - Add "Manage Subscription" button
- `frontend/app/billing/page.js` - **NEW** (billing management page)

**Backend Endpoint:**
```python
@app.route("/billing/portal", methods=["POST"])
@require_auth
def billing_portal():
    user = g.user
    subscription = Subscription.query.filter_by(user_id=user.id).first()
    
    if not subscription or not subscription.provider_customer_id:
        return jsonify({"error": "No active subscription"}), 400
    
    if not configure_stripe():
        return jsonify({"error": "Stripe not configured"}), 503
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=subscription.provider_customer_id,
            return_url=f"{FRONTEND_PUBLIC_URL}/dashboard",
        )
        return jsonify({"url": session.url})
    except stripe.error.StripeError as e:
        app.logger.error("Billing portal error: %s", e)
        return jsonify({"error": "Could not create portal session"}), 500
```

**Frontend Integration:**
```javascript
// dashboard/page.js - Add to wallet cards or billing section
async function openBillingPortal() {
  const res = await fetch(`${API_URL}/billing/portal`, { method: "POST" });
  const data = await res.json();
  if (data.url) window.location.href = data.url;
  else setError(data.error);
}
```

**Validation Gate:** User clicks "Manage Subscription" → redirected to Stripe Portal → can upgrade/downgrade/cancel → webhook syncs back

---

### 2.5 Stripe Webhook Idempotency + Alerting

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/models.py` - Add `StripeWebhookEvent` model
- `backend/app.py` - Webhook handler hardening
- `backend/requirements.txt` - Already has stripe

**New Model:**
```python
# models.py
class StripeWebhookEvent(db.Model):
    __tablename__ = "stripe_webhook_events"
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    payload_hash = db.Column(db.String(64), nullable=False)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
```

**Hardened Webhook Handler:**
```python
@app.route("/billing/stripe/webhook", methods=["POST"])
def stripe_webhook():
    import hashlib
    
    payload = request.get_data()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        return jsonify({"error": "Missing signature"}), 400
    
    # Idempotency check
    payload_hash = hashlib.sha256(payload).hexdigest()
    event_id = request.headers.get("stripe-event-id")  # From Stripe
    
    existing = StripeWebhookEvent.query.filter_by(event_id=event_id).first()
    if existing:
        return jsonify({"received": True, "duplicate": True})
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return jsonify({"error": "Invalid signature"}), 400
    
    # Record attempt
    webhook_record = StripeWebhookEvent(
        event_id=event.id,
        event_type=event.type,
        payload_hash=payload_hash,
    )
    db.session.add(webhook_record)
    
    try:
        # Handle event types...
        if event.type == "checkout.session.completed":
            handle_stripe_checkout_completed(event.data.object)
        elif event.type.startswith("customer.subscription."):
            sync_stripe_subscription_by_id(event.data.object.id)
        elif event.type.startswith("invoice."):
            handle_invoice_event(event.data.object)
        
        webhook_record.success = True
        db.session.commit()
        
    except Exception as e:
        webhook_record.error_message = str(e)
        db.session.commit()
        # Alert via Sentry
        sentry_sdk.capture_exception(e)
        return jsonify({"error": "Handler failed"}), 500
    
    return jsonify({"received": True})
```

**Validation Gate:** Duplicate webhook delivery → returns 200, no duplicate processing; failed handler → alerted in Sentry

---

### 2.6 Structured JSON Logging

**Owner:** Infrastructure Agent  
**Files to Create/Modify:**
- `backend/app.py` - Add logging configuration at startup
- `backend/.env.example` - Add `LOG_LEVEL`, `LOG_FORMAT`

**Implementation:**
```python
# app.py - After app = Flask(__name__)
import logging
import json
import sys
from pythonjsonlogger import jsonlogger

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        from flask import g, has_request_context
        if has_request_context() and hasattr(g, 'request_id'):
            record.request_id = g.request_id
        else:
            record.request_id = '-'
        return True

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
handler = logging.StreamHandler(sys.stdout)

if os.environ.get("LOG_FORMAT") == "json":
    handler.setFormatter(jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"levelname": "level", "name": "logger"},
    ))
else:
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] [%(request_id)s] %(message)s"
    ))

handler.addFilter(RequestIdFilter())
app.logger.handlers = [handler]
app.logger.setLevel(log_level)

# Reduce noise
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

**Add to requirements.txt:** `python-json-logger>=2.0`

**Validation Gate:** Logs in Render appear as JSON with `request_id`, `level`, `logger`, `message` fields

---

## Wave 3: User Experience (Week 3-4)

**Goal:** i18n migration, PWA, analytics, AI assistant, cookie consent

### 3.1 i18n Migration (next-intl)

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/messages/ro.json` - **NEW** (extracted from components)
- `frontend/messages/en.json` - **NEW**
- `frontend/i18n.ts` - **NEW** (config)
- `frontend/middleware.ts` - **NEW** (locale detection)
- `frontend/app/[locale]/layout.tsx` - **NEW** (locale wrapper)
- `frontend/app/[locale]/...` - Move all pages under locale
- `frontend/next.config.mjs` - Add `withNextIntl`
- `frontend/package.json` - Add `next-intl`, update scripts
- `frontend/components/LocaleProvider.js` - **REMOVE** (replace with next-intl)

**Extraction Process:**
```bash
# 1. Install
npm i next-intl@4.13.2

# 2. Extract all pick('ro', 'en') calls
# Run codemod or manual extraction - ~200 strings across 30+ files

# 3. Configure middleware
# middleware.ts
import createMiddleware from 'next-intl/middleware';
export default createMiddleware({ locales: ['ro', 'en'], defaultLocale: 'ro' });
export const config = { matcher: ['/((?!api|_next|.*\\..*).*)'] };
```

**Message Structure:**
```json
// messages/ro.json
{
  "home": {
    "hero": {
      "title": "Alege produsul mai bun direct la raft.",
      "subtitle": "Scanezi codul de bare, vezi dacă produsul merită cumpărat..."
    },
    "steps": [
      { "title": "Scanezi codul de bare", "detail": "..." }
    ]
  },
  "dashboard": {
    "welcome": "Salut, {name}",
    "actions": { "scan": "Scanează codul", ... }
  },
  "common": {
    "scan": "Scanează", "save": "Salvează", "cancel": "Anulează"
  }
}
```

**Migration Strategy:**
1. Create message files from existing strings
2. Add middleware + locale routing
3. Replace `useLocale().pick(ro, en)` with `useTranslations('namespace')`
4. Test all pages in both locales
5. Remove `LocaleProvider`, `useTranslatedText`, `TranslatedText`

**Validation Gate:** All pages render in RO/EN; locale switching works; no hardcoded strings remain

---

### 3.2 PWA Implementation (@neshca/pwa-next)

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/next.config.mjs` - Add `@neshca/pwa-next` plugin
- `frontend/public/offline.html` - **NEW** (offline fallback)
- `frontend/app/offline/page.tsx` - **NEW** (offline page)
- `frontend/app/manifest.ts` - Update for PWA
- `frontend/package.json` - Add `@neshca/pwa-next`, `workbox-window`

**Configuration:**
```javascript
// next.config.mjs
import withPWA from '@neshca/pwa-next';

export default withPWA({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    {
      urlPattern: /^https:\/\/images\.openfoodfacts\.org/,
      handler: 'CacheFirst',
      options: {
        cacheName: 'product-images',
        expiration: { maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 },
      },
    },
    {
      urlPattern: /^https:\/\/.*\.supabase\.co/,
      handler: 'NetworkFirst',
      options: { cacheName: 'supabase-api', networkTimeoutSeconds: 10 },
    },
    {
      urlPattern: /\/api\/backend/,
      handler: 'NetworkFirst',
      options: { cacheName: 'api-cache', networkTimeoutSeconds: 5 },
    },
  ],
  fallbacks: {
    document: '/offline',
  },
});
```

**Offline Page:**
```tsx
// app/offline/page.tsx
export default function OfflinePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0b0f14] text-white p-4">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-4">Ești offline</h1>
        <p className="text-gray-300 mb-6">
          Verifică conexiunea și reîncearcă. Istoricul și coșul sunt salvați local.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-white text-black font-bold rounded-xl hover:bg-cyan-100"
        >
          Reîncearcă
        </button>
      </div>
    </main>
  );
}
```

**Manifest:**
```typescript
// app/manifest.ts
export default function manifest() {
  return {
    name: 'Ce aleg?',
    short_name: 'Ce aleg?',
    description: 'Cumpărături mai inteligente - scanează, compară, alege',
    start_url: '/',
    display: 'standalone',
    background_color: '#020617',
    theme_color: '#14b8a6',
    orientation: 'portrait-primary',
    icons: [
      { src: '/icon.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
    ],
    categories: ['shopping', 'health', 'food'],
    screenshots: [],
  };
}
```

**Validation Gate:** Lighthouse PWA score > 90; offline page works; install prompt appears; cache strategies effective

---

### 3.3 PostHog Analytics Integration

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/lib/posthog.ts` - **NEW** (client config)
- `frontend/components/PostHogProvider.tsx` - **NEW** (wrapper)
- `frontend/app/layout.tsx` - Wrap with provider
- `frontend/components/Analytics.tsx` - Replace GA4/Meta/TikTok
- `frontend/utils/analytics.ts` - Update `trackEvent` to use PostHog
- `frontend/.env.example` - Add `NEXT_PUBLIC_POSTHOG_KEY`, `NEXT_PUBLIC_POSTHOG_HOST`
- `frontend/package.json` - Add `posthog-js`, `@posthog/plugin-react`
- `backend/app.py` - Add server-side PostHog tracking
- `backend/requirements.txt` - Add `posthog>=7.24`

**Implementation:**
```typescript
// lib/posthog.ts
import posthog from 'posthog-js';
import { PostHogProvider, usePostHog } from '@posthog/plugin-react';

export function PostHogProviderWrapper({ children }) {
  if (typeof window === 'undefined') return <>{children}</>;
  
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) return <>{children}</>; // Disabled if no key
  
  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://eu.i.posthog.com',
    capture_pageview: false,
    persistence: 'localStorage',
    loaded: (ph) => {
      // Identify user if logged in
      const user = localStorage.getItem('cealeg_user');
      if (user) {
        const { id, email, name } = JSON.parse(user);
        ph.identify(id, { email, name });
      }
    },
  });
  
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>;
}

// components/Analytics.tsx
'use client';
import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect } from 'react';
import { usePostHog } from '@posthog/plugin-react';

export function PostHogPageView() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const posthog = usePostHog();
  
  useEffect(() => {
    if (!posthog) return;
    const url = searchParams ? `${pathname}?${searchParams}` : pathname;
    posthog.capture('$pageview', { $current_url: url });
  }, [pathname, searchParams, posthog]);
  
  return null;
}

// utils/analytics.ts - Updated
export function trackEvent(event: string, properties?: Record<string, any>) {
  if (typeof window === 'undefined') return;
  
  // PostHog
  if (window.posthog) {
    window.posthog.capture(event, properties);
  }
  
  // Fallback to dataLayer for GA4 if still needed
  if (window.dataLayer) {
    window.dataLayer.push({ event, ...properties });
  }
}
```

**Backend Tracking:**
```python
# app.py - Add PostHog server-side
import posthog
posthog.api_key = os.environ.get("POSTHOG_API_KEY")
posthog.host = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")

def track_event(user_id, event, properties=None):
    if posthog.api_key:
        posthog.capture(user_id, event, properties or {})
```

**Validation Gate:** Events appear in PostHog dashboard; feature flags work; user identification works

---

### 3.4 AI Visual Assistant (Feature-Flagged, Provider Abstraction)

**Owner:** Frontend + Backend Agents  
**Files to Create/Modify:**
- `backend/ai_providers.py` - **NEW** (abstract base + implementations)
- `backend/app.py` - Add `/ai/identify-product-frame` endpoint with feature flag
- `frontend/app/live-assistant/page.js` - Connect to new endpoint
- `frontend/components/AIProvider.ts` - **NEW** (frontend abstraction)
- `frontend/.env.example` - Add `AI_VISION_ENABLED=false`, `AI_VISION_PROVIDER=mock`

**Backend Provider Abstraction:**
```python
# ai_providers.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class ProductIdentification:
    name: str
    brand: Optional[str]
    barcode: Optional[str]
    confidence: float
    category: Optional[str]
    ingredients: Optional[str]
    nutrition: dict

class AIVisionProvider(ABC):
    @abstractmethod
    def identify(self, image_bytes: bytes) -> ProductIdentification:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass

class MockProvider(AIVisionProvider):
    """Development/testing provider - returns mock data"""
    def identify(self, image_bytes: bytes) -> ProductIdentification:
        return ProductIdentification(
            name="Produs de test (Mock AI)",
            brand="Test Brand",
            barcode=None,
            confidence=0.95,
            category="Altele",
            ingredients="Apă, zahăr, aromă",
            nutrition={"calories": 100, "protein": 0, "sugar": 25, "fat": 0}
        )
    
    def is_available(self) -> bool:
        return True

class OpenAIProvider(AIVisionProvider):
    """GPT-4V / GPT-4o provider"""
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("AI_VISION_MODEL", "gpt-4o")
    
    def identify(self, image_bytes: bytes) -> ProductIdentification:
        import base64
        from openai import OpenAI
        
        client = OpenAI(api_key=self.api_key)
        b64 = base64.b64encode(image_bytes).decode()
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Identifică acest produs românesc. Returnează JSON: name, brand, barcode (dacă e vizibil), category, ingredients, nutrition (calories, protein, sugar, fat per 100g), confidence (0-1)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        # Parse and return ProductIdentification
        pass
    
    def is_available(self) -> bool:
        return bool(self.api_key)

# Factory
def get_ai_provider() -> AIVisionProvider:
    provider_name = os.environ.get("AI_VISION_PROVIDER", "mock").lower()
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "gemini":
        return GeminiProvider()  # TODO
    return MockProvider()
```

**Endpoint with Feature Flag:**
```python
# app.py
@app.route("/ai/identify-product-frame", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def ai_identify_product_frame():
    if not os.environ.get("AI_VISION_ENABLED", "false").lower() == "true":
        return jsonify({"error": "AI vision not enabled"}), 503
    
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    image = request.files['image']
    image_bytes = image.read()
    
    provider = get_ai_provider()
    if not provider.is_available():
        return jsonify({"error": "AI provider not configured"}), 503
    
    try:
        result = provider.identify(image_bytes)
        return jsonify({
            "name": result.name,
            "brand": result.brand,
            "barcode": result.barcode,
            "confidence": result.confidence,
            "category": result.category,
            "ingredients": result.ingredients,
            "nutrition": result.nutrition,
        })
    except Exception as e:
        app.logger.exception("AI identification failed")
        return jsonify({"error": "Identification failed"}), 500
```

**Frontend Integration:**
```typescript
// components/AIProvider.ts
export interface AIProvider {
  identify(image: Blob): Promise<ProductIdentification>;
  isAvailable(): boolean;
}

export class MockAIProvider implements AIProvider {
  async identify(image: Blob) {
    return { name: "Produs de test", brand: "Test", confidence: 0.9, ... };
  }
  isAvailable() { return true; }
}

export class OpenAIProvider implements AIProvider {
  async identify(image: Blob) {
    const formData = new FormData();
    formData.append('image', image);
    const res = await fetch('/api/backend/ai/identify-product-frame', {
      method: 'POST', body: formData
    });
    return res.json();
  }
  isAvailable() { 
    return process.env.NEXT_PUBLIC_AI_VISION_ENABLED === 'true';
  }
}

export function getAIProvider(): AIProvider {
  if (process.env.NEXT_PUBLIC_AI_VISION_ENABLED === 'true') {
    return new OpenAIProvider();
  }
  return new MockAIProvider();
}
```

**Validation Gate:** Feature flag OFF → endpoint returns 503; feature flag ON + mock provider → returns mock data; UI shows "În dezvoltare" banner when disabled

---

### 3.5 Granular Cookie Consent + Server Logging

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/app/components/CookieConsentBanner.tsx` - **REWRITE** (granular)
- `frontend/app/components/CookieManager.tsx` - **NEW** (manage consent UI)
- `backend/models.py` - Add `ConsentLog` model
- `backend/app.py` - Add `/consent/log` endpoint
- `frontend/app/privacy/page.tsx` - Link to cookie manager

**Consent Categories:**
```typescript
// Types
type ConsentCategory = 'necessary' | 'analytics' | 'marketing' | 'functional';

interface ConsentState {
  necessary: true; // Always true
  analytics: boolean;
  marketing: boolean;
  functional: boolean;
  version: string; // Increment when policy changes
  timestamp: string;
  ip?: string; // Server-side
}

// Default
const DEFAULT_CONSENT: ConsentState = {
  necessary: true,
  analytics: false,
  marketing: false,
  functional: false,
  version: '1.0',
  timestamp: new Date().toISOString(),
};
```

**Banner UI (Granular):**
```tsx
// CookieConsentBanner.tsx
'use client';
import { useState, useEffect } from 'react';
import { X, Check, Settings } from 'lucide-react';

const CATEGORIES = [
  { id: 'necessary', label: 'Neesentiale', desc: 'Funcționarea site-ului', required: true },
  { id: 'analytics', label: 'Analitică', desc: 'PostHog - înțelegem utilizarea' },
  { id: 'marketing', label: 'Marketing', desc: 'Meta/TikTok Pixel - reclame personalizate' },
  { id: 'functional', label: 'Funcționale', desc: 'Preferințe, setări personalizate' },
];

export function CookieConsentBanner() {
  const [open, setOpen] = useState(false);
  const [consent, setConsent] = useState<ConsentState>(DEFAULT_CONSENT);
  
  useEffect(() => {
    const saved = localStorage.getItem('cealeg_consent');
    if (saved) {
      const parsed = JSON.parse(saved);
      // Check version - re-prompt if policy changed
      if (parsed.version === CONSENT_VERSION) {
        setConsent(parsed);
        return;
      }
    }
    setOpen(true);
  }, []);
  
  const acceptAll = () => saveConsent({ ...consent, analytics: true, marketing: true, functional: true });
  const rejectAll = () => saveConsent({ ...consent, analytics: false, marketing: false, functional: false });
  const saveCustom = (cats: Partial<ConsentState>) => saveConsent({ ...consent, ...cats });
  
  const saveConsent = async (newConsent: ConsentState) => {
    const final = { ...newConsent, version: CONSENT_VERSION, timestamp: new Date().toISOString() };
    localStorage.setItem('cealeg_consent', JSON.stringify(final));
    setConsent(final);
    setOpen(false);
    
    // Server log (non-blocking)
    fetch('/api/backend/consent/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(final),
    }).catch(() => {});
    
    // Dispatch event for analytics initialization
    window.dispatchEvent(new CustomEvent('cealeg:consent-change', { detail: final }));
  };
  
  // Render...
}
```

**Backend Consent Log:**
```python
# models.py
class ConsentLog(db.Model):
    __tablename__ = "consent_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    session_id = db.Column(db.String(100), nullable=True, index=True)
    categories = db.Column(db.JSON, nullable=False)
    version = db.Column(db.String(20), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# app.py
@app.route("/consent/log", methods=["POST"])
def log_consent():
    data = request.get_json()
    if not data or 'categories' not in data:
        return jsonify({"error": "Invalid consent data"}), 400
    
    log = ConsentLog(
        user_id=g.user.id if hasattr(g, 'user') else None,
        session_id=request.headers.get('X-Session-ID'),
        categories=data['categories'],
        version=data.get('version', '1.0'),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True})
```

**Validation Gate:** Banner shows granular toggles; consent logged to server; analytics only load after consent; "Manage Cookies" link in footer reopens banner

---

## Wave 4: Operations (Week 4-5)

**Goal:** Automated backup, catalog monitoring, alerting, runbooks

### 4.1 Automated Supabase Backup

**Owner:** Infrastructure Agent  
**Files to Create/Modify:**
- `.github/workflows/backup-supabase.yml` - **NEW** (nightly backup)
- `scripts/backup-supabase.sh` - **NEW** (backup script)
- `scripts/restore-supabase.sh` - **NEW** (restore script)
- `docs/supabase-backup.md` - Update with automation details
- `backend/.env.example` - Add backup config vars

**GitHub Actions Workflow:**
```yaml
# .github/workflows/backup-supabase.yml
name: Supabase Backup

on:
  schedule:
    - cron: '0 3 * * *'  # Daily 3 AM UTC
  workflow_dispatch:

env:
  SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
  BACKUP_BUCKET: ${{ secrets.BACKUP_BUCKET }}  # S3/GCS/Supabase Storage
  BACKUP_ENCRYPTION_KEY: ${{ secrets.BACKUP_ENCRYPTION_KEY }}
  RETENTION_DAYS: 30

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup PostgreSQL client
        run: sudo apt-get update && sudo apt-get install -y postgresql-client-16 pv
      
      - name: Dump database
        id: dump
        run: |
          TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
          FILE="cealeg-backup-${TIMESTAMP}.sql.gz"
          
          pg_dump "$SUPABASE_URL" \
            --no-owner --no-privileges --no-tablespaces \
            --format=custom --compress=6 \
            | pv | gzip > "$FILE"
          
          echo "file=$FILE" >> $GITHUB_OUTPUT
          echo "size=$(stat -c%s "$FILE")" >> $GITHUB_OUTPUT
      
      - name: Encrypt backup
        run: |
          openssl enc -aes-256-cbc -salt -in ${{ steps.dump.outputs.file }} \
            -out ${{ steps.dump.outputs.file }}.enc \
            -pass pass:"$BACKUP_ENCRYPTION_KEY"
      
      - name: Upload to storage
        run: |
          # Upload to S3, GCS, or Supabase Storage
          # Example for AWS S3:
          aws s3 cp ${{ steps.dump.outputs.file }}.enc s3://$BACKUP_BUCKET/backups/
      
      - name: Cleanup old backups
        run: |
          # Delete backups older than RETENTION_DAYS
          aws s3 ls s3://$BACKUP_BUCKET/backups/ | while read -r line; do
            # Parse date and delete if old
          done
      
      - name: Notify on failure
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"❌ Supabase backup failed"}' \
            $SLACK_WEBHOOK_URL
```

**Restore Script:**
```bash
# scripts/restore-supabase.sh
#!/bin/bash
set -euo pipefail

BACKUP_FILE="${1:?Usage: $0 <backup-file.sql.gz.enc>}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:?Set BACKUP_ENCRYPTION_KEY}"

echo "Decrypting..."
openssl enc -d -aes-256-cbc -in "$BACKUP_FILE" -pass pass:"$ENCRYPTION_KEY" | gunzip | pg_restore \
  --clean --if-exists --no-owner --no-privileges \
  --dbname="$DATABASE_URL"

echo "Restore complete. Run migrations if needed."
```

**Validation Gate:** Workflow runs successfully; backup file exists in storage; restore tested in staging

---

### 4.2 Catalog Quality Checks + Admin Report

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/catalog_quality.py` - **NEW** (quality checks)
- `backend/app.py` - Add `/admin/catalog/quality-report` endpoint
- `frontend/app/admin/page.js` - Add quality report section
- `backend/requirements.txt` - No new deps

**Quality Checks:**
```python
# catalog_quality.py
from dataclasses import dataclass
from typing import List
from sqlalchemy import func, or_
from models import Product, ProductSubmission, SearchEvent, UsageEvent
from database import db

@dataclass
class QualityIssue:
    severity: str  # critical, warning, info
    category: str
    message: str
    count: int
    sample_ids: List[int]

def run_quality_checks() -> List[QualityIssue]:
    issues = []
    
    # 1. Products without score
    no_score = db.session.query(func.count(Product.id)).filter(
        or_(Product.score.is_(None), Product.score == 0)
    ).scalar()
    if no_score > 0:
        sample = db.session.query(Product.id).filter(
            or_(Product.score.is_(None), Product.score == 0)
        ).limit(10).all()
        issues.append(QualityIssue(
            severity="warning",
            category="scoring",
            message=f"{no_score} products missing score",
            count=no_score,
            sample_ids=[s[0] for s in sample],
        ))
    
    # 2. Products without nutrition data
    no_nutrition = db.session.query(func.count(Product.id)).filter(
        or_(Product.calories.is_(None), Product.protein.is_(None),
            Product.sugar.is_(None), Product.fat.is_(None))
    ).scalar()
    if no_nutrition > 0:
        issues.append(QualityIssue("warning", "nutrition", ...))
    
    # 3. Products with "Altele" or generic category
    generic_cats = db.session.query(func.count(Product.id)).filter(
        Product.category.in_(["Altele", "Other", "General", "Categorie neconfirmată"])
    ).scalar()
    if generic_cats > 0:
        issues.append(QualityIssue("warning", "categorization", ...))
    
    # 4. Duplicate barcodes
    dup_barcodes = db.session.query(Product.barcode, func.count(Product.id)).filter(
        Product.barcode.isnot(None)
    ).group_by(Product.barcode).having(func.count(Product.id) > 1).all()
    if dup_barcodes:
        issues.append(QualityIssue("critical", "duplicates", ...))
    
    # 5. Stale products (not updated in 180 days) - needs updated_at column
    # 6. Search misses (top queries with 0 results)
    search_misses = db.session.query(SearchEvent.search_text, func.count(SearchEvent.id)).filter(
        SearchEvent.result_count == 0
    ).group_by(SearchEvent.search_text).order_by(func.count(SearchEvent.id).desc()).limit(20).all()
    if search_misses:
        issues.append(QualityIssue("info", "search_gaps", ...))
    
    # 7. Unresolved alternative reports
    alt_reports = db.session.query(func.count(UsageEvent.id)).filter(
        UsageEvent.event_type == "alternative_report",
        ~UsageEvent.metadata_json.like('%resolved%')
    ).scalar()
    if alt_reports > 0:
        issues.append(QualityIssue("warning", "alt_reports", ...))
    
    # 8. Pending submissions > 7 days
    from datetime import timedelta
    old_pending = db.session.query(func.count(ProductSubmission.id)).filter(
        ProductSubmission.status == "pending",
        ProductSubmission.created_at < datetime.utcnow() - timedelta(days=7)
    ).scalar()
    if old_pending > 0:
        issues.append(QualityIssue("info", "stale_submissions", ...))
    
    return issues

def generate_quality_report() -> dict:
    issues = run_quality_checks()
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "critical": sum(1 for i in issues if i.severity == "critical"),
            "warning": sum(1 for i in issues if i.severity == "warning"),
            "info": sum(1 for i in issues if i.severity == "info"),
        },
        "issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "message": i.message,
                "count": i.count,
                "sample_ids": i.sample_ids,
            }
            for i in issues
        ],
    }
```

**Admin Endpoint:**
```python
# app.py
@app.route("/admin/catalog/quality-report", methods=["GET"])
@require_admin
def catalog_quality_report():
    return jsonify(generate_quality_report())
```

**Validation Gate:** Report generates in < 5s; issues actionable; admin can drill into samples

---

### 4.3 Configurable Alerting

**Owner:** Infrastructure Agent  
**Files to Create/Modify:**
- `backend/alerts.py` - **NEW** (alert definitions + dispatch)
- `backend/app.py` - Integrate alert calls
- `backend/.env.example` - Add alert webhooks
- `render.yaml` - No changes (uses env vars)

**Alert System:**
```python
# alerts.py
import os
import requests
import sentry_sdk
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Alert:
    level: AlertLevel
    title: str
    message: str
    source: str
    metadata: dict = None

class AlertDispatcher:
    def __init__(self):
        self.slack_webhook = os.environ.get("ALERT_SLACK_WEBHOOK")
        self.discord_webhook = os.environ.get("ALERT_DISCORD_WEBHOOK")
        self.email_to = os.environ.get("ALERT_EMAIL_TO")
        self.pagerduty_key = os.environ.get("ALERT_PAGERDUTY_KEY")
    
    def send(self, alert: Alert):
        # Always send to Sentry
        sentry_sdk.capture_message(
            f"[{alert.level.value.upper()}] {alert.title}: {alert.message}",
            level=alert.level.value,
        )
        
        # Slack
        if self.slack_webhook:
            color = {"info": "good", "warning": "warning", "critical": "danger"}[alert.level.value]
            payload = {
                "attachions": [{
                    "color": color,
                    "title": f"[{alert.level.value.upper()}] {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Source", "value": alert.source, "short": True},
                        {"title": "Level", "value": alert.level.value, "short": True},
                    ],
                    "footer": "Ce Aleg Alerting",
                }]
            }
            requests.post(self.slack_webhook, json=payload, timeout=5)
        
        # Email (for critical)
        if alert.level == AlertLevel.CRITICAL and self.email_to:
            # Use existing send_transactional_email
            pass

dispatcher = AlertDispatcher()

# Convenience functions
def alert_warning(title, message, source, **meta):
    dispatcher.send(Alert(AlertLevel.WARNING, title, message, source, meta))

def alert_critical(title, message, source, **meta):
    dispatcher.send(Alert(AlertLevel.CRITICAL, title, message, source, meta))

# Usage in app.py
from alerts import alert_critical, alert_warning

# In stripe_webhook exception handler:
alert_critical("Stripe Webhook Failed", str(e), "billing", event_type=event.type)

# In catalog quality cron:
def run_quality_cron():
    report = generate_quality_report()
    if report["summary"]["critical"] > 0:
        alert_critical("Catalog Quality Critical Issues", 
            f"{report['summary']['critical']} critical issues found", "catalog")
```

**Validation Gate:** Test alert fires in Sentry/Slack; critical alerts page on-call

---

### 4.4 Operational Runbooks

**Owner:** Documentation Agent  
**Files to Create/Modify:**
- `docs/runbooks/` - **NEW** directory
- `docs/runbooks/incident-response.md` - **NEW**
- `docs/runbooks/database-restore.md` - **NEW**
- `docs/runbooks/stripe-webhook-failure.md` - **NEW**
- `docs/runbooks/catalog-quality-degraded.md` - **NEW**
- `docs/runbooks/rate-limit-exceeded.md` - **NEW**

**Runbook Template:**
```markdown
# Runbook: [Incident Type]

## Overview
- **Severity:** SEV-1/SEV-2/SEV-3
- **Owner:** [Team/Role]
- **Last Updated:** YYYY-MM-DD

## Symptoms
- [Observable indicators]

## Diagnosis
1. Check [dashboard/metric]
2. Run [query/command]
3. Verify [condition]

## Resolution
### Immediate Mitigation
- [Steps to reduce impact]

### Root Cause Fix
- [Steps to fix permanently]

## Verification
- [How to confirm fixed]

## Post-Incident
- [Retrospective, action items]

## References
- [Links to dashboards, docs, code]
```

---

## Wave 5: Legal/Compliance (Week 5-6)

**Goal:** GDPR tooling, DPA documentation, consent records, retention

### 5.1 Data Export Endpoint (Art 20)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/app.py` - Add `/api/user/export` endpoint
- `frontend/app/dashboard/page.js` - Add "Export My Data" button

**Implementation:**
```python
@app.route("/api/user/export", methods=["GET"])
@require_auth
def export_user_data():
    user = g.user
    
    # Collect all user data
    data = {
        "profile": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "email_verified": user.email_verified,
            "invite_code": user.invite_code,
            "bonus_unlimited_until": user.bonus_unlimited_until.isoformat() if user.bonus_unlimited_until else None,
            "bonus_scan_credits": user.bonus_scan_credits,
        },
        "subscriptions": [
            {
                "plan": s.plan,
                "status": s.status,
                "provider": s.provider,
                "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            }
            for s in user.subscription
        ] if user.subscription else [],
        "family_profiles": [
            {"id": p.id, "name": p.name, "color": p.color, "is_primary": p.is_primary}
            for p in user.family_profiles
        ],
        "scan_history": [
            {
                "product_name": h.product_name,
                "store": h.store,
                "category": h.category,
                "score": h.score,
                "price": h.price,
                "verdict": h.verdict,
                "scanned_at": h.scanned_at.isoformat(),
            }
            for h in user.scan_history
        ],
        "favorites": [
            {"product_name": f.product_name, "store": f.store, "created_at": f.created_at.isoformat()}
            for f in user.favorites
        ],
        "cart": [
            {"product_name": c.product_name, "store": c.store, "quantity": c.quantity, "bought": c.bought}
            for c in user.cart_items
        ],
        "submissions": [
            {"product_name": s.product_name, "store": s.store, "status": s.status, "created_at": s.created_at.isoformat()}
            for s in user.product_submissions
        ],
        "consent_logs": [
            {"categories": c.categories, "version": c.version, "created_at": c.created_at.isoformat()}
            for c in ConsentLog.query.filter_by(user_id=user.id).all()
        ],
    }
    
    from flask import Response
    import json
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="cealeg-export-{user.id}.json"'}
    )
```

---

### 5.2 Data Access Endpoint (Art 15)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/app.py` - Add `/api/user/data` endpoint (structured view)

---

### 5.3 Restriction of Processing (Art 18)

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/models.py` - Add `processing_restricted` + `restricted_at` to User
- `backend/app.py` - Add `/api/user/restrict-processing` endpoint
- `frontend/app/dashboard/page.js` - Add toggle in settings

---

### 5.4 Processor DPA Documentation

**Owner:** Documentation Agent  
**Files to Create/Modify:**
- `docs/legal/dpa-register.md` - **NEW** (register of DPAs)
- `frontend/app/privacy/page.tsx` - Add processor table with DPA links

**DPA Register:**
```markdown
# Data Processing Agreement Register

| Processor | Purpose | Legal Basis | DPA Signed | DPA Location | SCCs | Location |
|-----------|---------|-------------|------------|--------------|------|----------|
| Supabase | Database, Storage, Auth | Art 6.1(b) | ☐ | [Link] | Yes (EU) | EU/US |
| Stripe | Payments, Subscriptions | Art 6.1(b) | ☐ | [Link] | Yes | EU/US |
| Brevo | Transactional Email | Art 6.1(b)/f | ☐ | [Link] | Yes | EU |
| Open Food Facts | Product Catalog | Art 6.1(f) | N/A (public) | N/A | N/A | France |
| PostHog | Analytics | Art 6.1(a) | ☐ | [Link] | Yes | EU |
| Render | Hosting (Backend) | Art 6.1(b) | ☐ | [Link] | Yes | EU/US |
| Vercel | Hosting (Frontend) | Art 6.1(b) | ☐ | [Link] | Yes | EU/US |
```

---

### 5.5 Consent Logging Server-side

**Completed in Wave 3.5** - `ConsentLog` model + `/consent/log` endpoint

---

### 5.6 Retention Policies + Cleanup Jobs

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/retention.py` - **NEW** (cleanup jobs)
- `backend/app.py` - Add cron endpoints for cleanup
- `render.yaml` - Add cron job service (or use pg_cron in Supabase)

**Retention Schedule:**
```python
# retention.py
from datetime import timedelta

RETENTION_POLICIES = {
    "usage_events": timedelta(days=730),      # 2 years
    "search_events": timedelta(days=365),     # 1 year
    "scan_history": None,                     # While account active
    "favorites": None,                        # While account active
    "cart_items": timedelta(days=90),         # 90 days after bought/abandoned
    "consent_logs": timedelta(days=1095),     # 3 years (legal)
    "stripe_webhook_events": timedelta(days=365), # 1 year
    "price_observations": timedelta(days=730), # 2 years
    "audit_logs": timedelta(days=2555),       # 7 years (fiscal)
}

def cleanup_expired_data():
    from models import UsageEvent, SearchEvent, CartItem, ConsentLog, StripeWebhookEvent
    from database import db
    from datetime import datetime
    
    cutoff_map = {
        UsageEvent: RETENTION_POLICIES["usage_events"],
        SearchEvent: RETENTION_POLICIES["search_events"],
        CartItem: RETENTION_POLICIES["cart_items"],
        ConsentLog: RETENTION_POLICIES["consent_logs"],
        StripeWebhookEvent: RETENTION_POLICIES["stripe_webhook_events"],
    }
    
    deleted_counts = {}
    for model, retention in cutoff_map.items():
        if retention is None:
            continue
        cutoff = datetime.utcnow() - retention
        count = db.session.query(model).filter(model.created_at < cutoff).delete(synchronize_session=False)
        deleted_counts[model.__tablename__] = count
    
    db.session.commit()
    return deleted_counts
```

---

## Wave 6: Code Quality (Week 6-8)

**Goal:** Refactoring, type safety, Stripe migration, CI hardening

### 6.1 Flask App Factory + Blueprints

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/app/__init__.py` - **NEW** (factory)
- `backend/app/routes/` - **NEW** directory (blueprints)
- `backend/app.py` - **REFACTOR** to use factory
- `backend/config.py` - **NEW** (configuration classes)

**Structure:**
```
backend/
├── app/
│   ├── __init__.py          # create_app()
│   ├── config.py            # Config classes
│   ├── extensions.py        # db, limiter, cache, sentry
│   ├── models/              # Split models.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── products.py
│   │   ├── cart.py
│   │   ├── favorites.py
│   │   ├── history.py
│   │   ├── submissions.py
│   │   ├── billing.py
│   │   ├── gamification.py
│   │   ├── family.py
│   │   ├── admin.py
│   │   ├── feedback.py
│   │   ├── ai.py
│   │   └── system.py
│   ├── services/            # Business logic
│   ├── validation.py        # Schemas
│   ├── ai_providers.py
│   ├── alerts.py
│   ├── catalog_quality.py
│   └── retention.py
├── tests/
├── migrations/
├── config.py
├── requirements.txt
└── run.py                   # Entry point
```

---

### 6.2 Stripe Python 11→15 Migration

**Owner:** Backend Agent  
**Files to Create/Modify:**
- `backend/requirements.txt` - Update `stripe>=15,<16`
- `backend/app.py` - Fix all breaking changes
- `backend/tests/test_billing.py` - Update tests

**Key Breaking Changes:**
| Old (v11-13) | New (v15) |
|--------------|-----------|
| `stripe.Customer.create_source()` | Use `PaymentMethod.attach()` |
| `stripe.Subscription.create(plan=...)` | `stripe.Subscription.create(items=[{"price": ...}])` |
| `stripe.Webhook.construct_event(payload, sig, secret)` | Same but stricter |
| `stripe.Charge` | Use `PaymentIntent` |
| List methods return `ListObject` | Auto-paging iterators |

**Migration Steps:**
1. Upgrade in staging branch
2. Run full test suite
3. Test webhook with Stripe CLI
4. Test Checkout + Portal flows
5. Deploy to staging, verify
6. Deploy to production

---

### 6.3 Frontend TypeScript Strict Mode

**Owner:** Frontend Agent  
**Files to Create/Modify:**
- `frontend/tsconfig.json` - Enable strict mode
- Fix all type errors across codebase

---

### 6.4 E2E Tests (Playwright)

**Owner:** Testing Agent  
**Files to Create/Modify:**
- `frontend/playwright.config.ts` - **NEW**
- `frontend/tests/e2e/` - **NEW** directory
- `.github/workflows/test-e2e.yml` - **NEW**

**Critical Flows to Test:**
1. Register → Verify Email → Login
2. Scan Barcode → View Result → Add to Cart/Favorites
3. Search Product → View Alternatives
4. Subscribe Pro → Access Unlimited Scans
5. Invite Friend → Bonus Applied
6. Submit Product → Admin Approve → Bonus
7. Delete Account → Confirm via Email
8. Offline Mode → View History

---

### 6.5 CI Gates

**Owner:** Infrastructure Agent  
**Files to Create/Modify:**
- `.github/workflows/ci.yml` - Update with all gates

**Required Gates:**
```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Frontend lint
        run: cd frontend && npm ci && npm run lint
      - name: Backend lint (ruff)
        run: cd backend && pip install ruff && ruff check .
  
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npm test -- --coverage
  
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: POSTGRES_PASSWORD: postgres
        ports: 5432:5432
    steps:
      - uses: actions/checkout@v4
      - run: cd backend && pip install -r requirements.txt && pytest --cov=app --cov-fail-under=70
  
  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npx playwright install --with-deps && npm run test:e2e
  
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npm run test:a11y
  
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: trufflesecurity/trufflehog@main
        with: path: ., base: main, head: HEAD
  
  build-frontend:
    needs: [lint, test-frontend, a11y]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npm run build
  
  deploy-staging:
    needs: [build-frontend, test-backend, test-e2e, secret-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - Deploy to staging (Vercel Preview + Render)
```

---

## Wave 7: Final Review (Week 8-9)

**Goal:** Independent review, regression testing, documentation, sign-off

### 7.1 Code Review (3 Subagents)

**Reviewers:** Independent agents (read-only)

| Reviewer | Focus |
|----------|-------|
| Code Reviewer | Architecture, patterns, maintainability, DRY, SOLID |
| Security Reviewer | AuthZ/AuthN, input validation, secrets, dependencies, OWASP |
| Test/Regression Reviewer | Coverage, flakiness, critical paths, performance |

**Deliverable:** Review report with PASS/FAIL per area + blocking issues

---

### 7.2 Regression Testing

**Owner:** Testing Agent  
**Scope:** Full test suite + manual smoke test on staging

**Checklist:**
- [ ] All unit tests pass (FE + BE)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Lighthouse PWA > 90
- [ ] Lighthouse Accessibility > 95
- [ ] Lighthouse Performance > 70
- [ ] Bundle size < 500KB gzipped
- [ ] API response times < 500ms p95
- [ ] Stripe webhook idempotency verified
- [ ] Rate limiting works across workers
- [ ] Cache hit rate > 80% on search
- [ ] Backup restore tested
- [ ] GDPR export/access/restriction work

---

### 7.3 Documentation Update

**Owner:** Documentation Agent  
**Files to Update:**
- `README.md` - Update with new features
- `docs/go-live-checklist.md` - Add new items
- `docs/security-predeployment-audit.md` - Update
- `docs/project-handoff.md` - Update
- `docs/production-improvement-report.md` - **NEW** (final report)
- `docs/architecture.md` - **NEW** (system architecture)
- `docs/api.md` - Link to OpenAPI docs
- `docs/operations.md` - Runbooks index

---

### 7.4 Production Readiness Sign-off

**Criteria for Go-Live:**
- [ ] All Wave 1-6 validation gates passed
- [ ] All review blockers resolved
- [ ] Regression testing 100% pass
- [ ] No critical/security vulnerabilities
- [ ] Secrets scanned - none in code
- [ ] Staging deployed and verified
- [ ] Runbooks documented and accessible
- [ ] On-call rotation configured
- [ ] Legal review completed (DPA register, privacy policy)
- [ ] Stripe live keys configured
- [ ] Sentry alerts configured
- [ ] Backup verified in last 24h

---

## File Ownership Matrix (Conflict Prevention)

| File/Directory | Wave | Owner Agent | Notes |
|----------------|------|-------------|-------|
| `frontend/jest.config.js` | 1 | Frontend | |
| `frontend/__tests__/` | 1 | Frontend | |
| `backend/pytest.ini` | 1 | Backend | |
| `backend/tests/` | 1 | Backend | |
| `backend/validation.py` | 1 | Backend | |
| `backend/api_docs.py` | 1 | Backend | |
| `frontend/sentry.*.ts` | 1 | Frontend | |
| `frontend/app/error.tsx` | 1 | Frontend | |
| `backend/sentry_init.py` | 1 | Backend | |
| `frontend/eslint.config.mjs` | 1 | Frontend | |
| `frontend/app/components/*.js` | 1 | Frontend | A11y fixes |
| `render.yaml` | 2 | Infrastructure | Redis service |
| `backend/rate_limiter.py` | 2 | Backend | |
| `backend/cache.py` | 2 | Backend | |
| `backend/app.py` (rate limit/cache) | 2 | Backend | Coordinate with infra |
| `backend/models.py` (StripeWebhookEvent) | 2 | Backend | |
| `backend/app.py` (webhook, portal) | 2 | Backend | |
| `backend/app.py` (logging) | 2 | Infrastructure | |
| `frontend/messages/*.json` | 3 | Frontend | |
| `frontend/i18n.ts`, `middleware.ts` | 3 | Frontend | |
| `frontend/app/[locale]/` | 3 | Frontend | Move pages |
| `frontend/next.config.mjs` (PWA) | 3 | Frontend | |
| `frontend/public/offline.html` | 3 | Frontend | |
| `frontend/lib/posthog.ts` | 3 | Frontend | |
| `frontend/components/Analytics.tsx` | 3 | Frontend | |
| `backend/ai_providers.py` | 3 | Backend | |
| `backend/app.py` (AI endpoint) | 3 | Backend | |
| `frontend/components/AIProvider.ts` | 3 | Frontend | |
| `frontend/app/components/CookieConsentBanner.tsx` | 3 | Frontend | Rewrite |
| `backend/models.py` (ConsentLog) | 3 | Backend | |
| `backend/app.py` (consent log) | 3 | Backend | |
| `.github/workflows/backup-supabase.yml` | 4 | Infrastructure | |
| `scripts/backup-supabase.sh` | 4 | Infrastructure | |
| `scripts/restore-supabase.sh` | 4 | Infrastructure | |
| `backend/catalog_quality.py` | 4 | Backend | |
| `backend/alerts.py` | 4 | Infrastructure | |
| `docs/runbooks/` | 4 | Documentation | |
| `backend/app.py` (export/access/restrict) | 5 | Backend | |
| `docs/legal/dpa-register.md` | 5 | Documentation | |
| `backend/retention.py` | 5 | Backend | |
| `backend/app/` (factory) | 6 | Backend | Major refactor |
| `backend/requirements.txt` (stripe) | 6 | Backend | |
| `frontend/tsconfig.json` | 6 | Frontend | |
| `frontend/playwright.config.ts` | 6 | Testing | |
| `frontend/tests/e2e/` | 6 | Testing | |
| `.github/workflows/ci.yml` | 6 | Infrastructure | |

---

## External Services Requiring Accounts/Keys

| Service | Purpose | Required For | Status |
|---------|---------|--------------|--------|
| **Upstash Redis** | Rate limiting, caching | Wave 2 | Need account |
| **Sentry** | Error tracking, performance | Wave 1 | Need account |
| **PostHog** | Analytics, feature flags | Wave 3 | Need account |
| **Stripe** | Payments, Billing Portal | Wave 2 (live) | Has test, need live |
| **Brevo** | Transactional email | Existing | Has account |
| **Supabase** | Database, Storage | Existing | Has project |
| **Render** | Backend hosting | Existing | Has account |
| **Vercel** | Frontend hosting | Existing | Has account |
| **OpenAI** | AI Vision (optional) | Wave 3 (flagged) | Optional |
| **Slack/Discord** | Alerting | Wave 4 | Optional |
| **AWS S3 / GCS** | Backup storage | Wave 4 | Need bucket |

**Environment Variables to Add to Production:**
```bash
# Backend (Render)
SENTRY_DSN=
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=
LOG_LEVEL=INFO
LOG_FORMAT=json
ALERT_SLACK_WEBHOOK=
BACKUP_BUCKET=
BACKUP_ENCRYPTION_KEY=
AI_VISION_ENABLED=false
AI_VISION_PROVIDER=mock
OPENAI_API_KEY=
POSTHOG_API_KEY=
POSTHOG_HOST=https://eu.i.posthog.com

# Frontend (Vercel)
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com
NEXT_PUBLIC_APP_VERSION=
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=
NEXT_PUBLIC_AI_VISION_ENABLED=false
```

---

## Testing Commands Summary

```bash
# Frontend
cd frontend
npm ci
npm run lint              # ESLint + jsx-a11y
npm test                  # Jest + RTL
npm run test:a11y         # axe-core Playwright
npm run test:e2e          # Playwright E2E
npm run build             # Next.js build
npm run generate:api      # OpenAPI → TypeScript types

# Backend
cd backend
pip install -r requirements.txt
ruff check .              # Lint
pytest --cov=app --cov-report=term-missing --cov-fail-under=70
pytest tests/ -v          # Verbose

# Full CI Simulation
# Run all in sequence
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Stripe v15 migration breaks webhooks | High | Critical | Test extensively in staging with Stripe CLI; keep v13 branch as rollback |
| next-intl migration breaks locale routing | Medium | High | Incremental migration; feature flag old LocaleProvider |
| PWA breaks on iOS Safari | Medium | Medium | Test on real devices; use `@neshca/pwa-next` not `next-pwa` |
| Redis/Upstash free tier limits exceeded | Medium | Medium | Monitor usage; plan for paid tier; graceful degradation |
| GDPR export performance on large accounts | Low | Medium | Add pagination/streaming; test with 10k+ scans |
| Legal review delays launch | Medium | High | Start DPA collection early; use standard templates |
| Sentry/PostHog costs exceed budget | Low | Medium | Set quota alerts; sample rates configured |
| Catalog quality checks slow on 50k+ products | Low | Medium | Add indexes; run async; cache results |

---

## Final Deliverables Checklist

- [ ] `docs/production-improvement-report.md` - This final report
- [ ] All Wave 1-6 validation gates passed
- [ ] Review reports from 3 subagents
- [ ] Updated `README.md`, `docs/go-live-checklist.md`
- [ ] CI pipeline with all gates
- [ ] Staging environment verified
- [ ] Runbooks in `docs/runbooks/`
- [ ] DPA register in `docs/legal/dpa-register.md`
- [ ] No secrets in git history
- [ ] Production environment variables documented

---

**Plan Status:** READY FOR EXECUTION  
**Next Step:** Begin Wave 1 with parallel agent execution