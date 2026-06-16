# 🚀 Production Readiness Checklist — Aegis Audit Swarm

Status legend: 🔴 blocker · 🟠 important · 🟢 nice-to-have · ✅ done

This is the work required to move Aegis from a working **MVP / pilot-grade** system
to something a security-conscious company can run in **production**. Items are
ordered by priority within each phase.

---

## 🔐 Hardening shipped in this release ✅

Security & robustness work completed (see `backend/config.py` for all knobs):

- ✅ **Fail-fast config validation** — in `ENVIRONMENT=production` the gateway
  refuses to boot without `JWT_SECRET`, `ENCRYPTION_KEY`, `NOTARY_PRIVATE_KEY_PEM`,
  an explicit (non-`*`) `CORS_ORIGINS`, and `AUTO_MIGRATE=false`.
- ✅ **Real server-side logout** — JWTs carry a `jti`; logout records it in a
  `revoked_tokens` table and `authenticate` rejects revoked tokens. Hourly purge
  of expired entries.
- ✅ **Auth safety** — password strength rules (length + letters & digits) and
  per-account login brute-force lockout (`LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES`).
- ✅ **Distributed rate limiting** — Redis backend (`REDIS_URL`) with automatic
  in-process fallback, so multiple gateway workers/replicas share limits.
- ✅ **Request & LLM guards** — request body size cap, max prompt length, hard
  output-token cap, and provider call timeouts (SDK + asyncio backstop).
- ✅ **Security headers + HSTS** middleware on every response.
- ✅ **Audit data governance** — optional prompt/response encryption at rest
  (`ENCRYPT_AUDIT_CONTENT`) and retention purge (`AUDIT_RETENTION_DAYS`).
- ✅ **Telemetry without spam** — OpenTelemetry is opt-in via `OTEL_EXPORTER`
  (`none` default, `console`, or `otlp`); no more console span dumps.
- ✅ **Readiness probe** `/ready` (DB check) alongside `/health`; structured logs.
- ✅ **Alembic migrations** — linear chain (`0001_initial` → `0002_multitenant_auth`
  → `0003_account_recovery`); production runs `alembic upgrade head` on boot.
- ✅ **Production compose + TLS** — `docker-compose.prod.yml` adds Redis and an
  nginx TLS-terminating proxy (`deploy/nginx-tls.conf`).

### Phase 1 blockers — addressed (third pass) ✅

- ✅ **Signing-key lifecycle** — pluggable signer (`NOTARY_KEY_BACKEND`,
  KMS-ready), **key rotation** with a fingerprint **`key_id` recorded on every
  evidence-ledger and audit-log row**, and a verify registry of active + retired
  public keys (`NOTARY_VERIFY_KEYS`) so old evidence still verifies after
  rotation. Production still refuses to boot on an ephemeral key.
- ✅ **Durable, scalable event bus** — `bus.py` now uses **Redis Streams** with a
  consumer group when `REDIS_URL` is set (in-process fallback otherwise), so the
  gateway can run multiple replicas. Ledger append + the notary subscriber are
  **idempotent** (dedupe by tenant+request+event) against redelivery.
- ✅ **Persistent vector store** — pgvector backend (`VECTOR_BACKEND=pgvector`)
  with **real embeddings** (`embeddings.py`: OpenAI when configured, deterministic
  local feature-hashing fallback). Survives restarts; graceful fallback to
  in-memory if the extension/driver is unavailable.
- ✅ **Real security scanning (layered)** — regex pre-screen **+** a second-layer
  injection/jailbreak classifier (`SECURITY_LLM_SCAN` LLM mode, heuristic
  fallback) **+ output-side scanning** that redacts leaked secrets/PII/unsafe
  content from model responses (`SECURITY_SCAN_OUTPUTS`).

> Still open from Phase 1: true KMS/HSM signer wiring (extension point only),
> threat-feed signature ingestion, and ANN indexes/embedding-model tuning for
> pgvector at very large scale.

### Cost engine & budgets ✅

- ✅ **Usage-accurate cost** — captures the real billing dimensions from each
  provider's usage object: standard input, **cached input tokens** (priced at a
  lower rate, `CACHED_INPUT_RATIO` / per-model override), **reasoning tokens**,
  and output. Replaces the flat `input·price + output·price`.
- ✅ **Confidence flag** — every cost is marked **exact** (provider usage + known
  price) or **estimated** (unknown model price or tokenizer-estimated usage when
  a provider returns no usage), persisted as `audit_logs.cost_estimated`.
- ✅ **Structured spend** — `audit_logs.cost_usd` + token-breakdown columns make
  spend aggregation reliable instead of parsing a display string.
- ✅ **Per-tenant budgets** — `tenant_budgets` table with daily/monthly caps
  (`/cost/budget`), live spend rollups (`/cost/summary`), threshold alerts at
  `BUDGET_ALERT_FRACTION`, and **pre-request enforcement** (a call that would
  exceed the cap is blocked as `BUDGET_EXCEEDED`). Surfaced in the Cost & Billing
  dashboard tab.

### Account, session & supply-chain hardening (second pass) ✅

- ✅ **Account recovery** — email verification, password change (invalidates all
  sessions), and forgot/reset-password flows. Pluggable email sender
  (`SMTP_*`) with a console fallback for dev (`gateway/email.py`).
- ✅ **XSS/token hardening** — short-lived access tokens (`ACCESS_TOKEN_MINUTES`)
  + rotating, DB-backed, single-use refresh tokens (`gateway/refresh.py`);
  the frontend auto-refreshes on 401 (single-flight). Password change/reset
  revokes all refresh tokens.
- ✅ **Content-Security-Policy** + frame/referrer headers on the SPA (nginx),
  defense-in-depth against token theft via XSS.
- ✅ **Tamper-evident audit log** — every `audit_logs` row is hashed into a
  per-tenant chain and RSA-signed; `GET /audit/verify` recomputes hashes +
  signatures and reports the first break (`gateway/audit_integrity.py`).
- ✅ **Supply-chain CI** — GitHub Actions (`.github/workflows/ci.yml`) runs
  backend tests, frontend build, `pip-audit`, `npm audit`, Trivy
  vuln/secret/misconfig scan, and emits a CycloneDX SBOM. Dependabot
  (`.github/dependabot.yml`) keeps pip/npm/Docker/Actions deps current.

### Deploy (production)

```bash
cp .env.example .env          # fill in POSTGRES_PASSWORD, JWT_SECRET,
                              # ENCRYPTION_KEY, NOTARY_PRIVATE_KEY_PEM, CORS_ORIGINS
# generate secrets:
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET / ENCRYPTION_KEY
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048    # NOTARY_PRIVATE_KEY_PEM

# TLS certs into deploy/certs/ (fullchain.pem + privkey.pem) — certbot or org CA.

docker compose -f docker-compose.prod.yml up --build -d
```

Migrations run automatically on gateway boot. To manage schema manually:

```bash
cd backend && alembic upgrade head        # fresh DB
cd backend && alembic stamp head          # existing DB already built by dev sync
```

---

## Phase 0 — Already in place ✅
- ✅ End-to-end trust pipeline (scan → librarian → adversary → risk gate → notary → audit log)
- ✅ Env-driven config, no hardcoded secrets, SSL-required DB by default
- ✅ Auth refuses to boot "open" in production (`gateway/auth.py`)
- ✅ API-key + JWT auth, RBAC roles, multi-tenant header
- ✅ Hash-chained, RSA-signed evidence ledger + chain verification
- ✅ Rate limiting (sliding window)
- ✅ Alembic migrations, Docker + docker-compose, CI, passing unit suite
- ✅ Modern dashboard (light/dark, live charts)

---

## Phase 1 — Hard blockers (must fix before any real traffic) 🔴

### 1.1 Persistent / managed signing key
- 🔴 Enforce `NOTARY_PRIVATE_KEY_PEM` (or KMS/HSM ref) in production — refuse to boot with an ephemeral key.
- 🔴 Support KMS/HSM-backed signing (AWS KMS, GCP KMS, or PKCS#11) instead of an in-process PEM.
- 🔴 Key rotation strategy + record the signing key ID / cert in each ledger entry so old signatures stay verifiable.

### 1.2 Real security scanning (replace regex-only)
- 🔴 Add an ML/LLM-based prompt-injection & jailbreak classifier alongside regex.
- 🟠 Integrate a maintained threat signature feed; make patterns hot-reloadable.
- 🟠 Add output-side scanning (data exfiltration / unsafe completions), not just input.

### 1.3 Durable, scalable event bus
- 🔴 Replace in-process `bus.py` with Redis Streams / Kafka / NATS so the gateway can run multiple replicas.
- 🔴 Make ledger writes + bus publish transactional/idempotent (no lost or double events).

### 1.4 Persistent vector store for RAG
- 🔴 Implement `pgvector` (and/or Pinecone) backends — `memory` resets on restart and won't scale.
- 🟠 Real embeddings for control matching instead of keyword heuristics.

---

## Phase 2 — Enterprise hardening 🟠

### 2.1 Scale & reliability
- 🟠 Stateless gateway behind a load balancer; verify horizontal scaling.
- 🟠 DB connection pooling tuning + read replicas for audit queries.
- 🟠 Backpressure / circuit breakers on upstream model calls; timeouts + retries.
- 🟠 Graceful shutdown, health/readiness/liveness probes (k8s).

### 2.2 Secrets & data
- 🟠 Secrets manager (Vault / AWS Secrets Manager) — stop relying on `.env` in prod.
- 🟠 Audit-log retention + archival policy; encryption at rest; PII handling/DLP policy.
- 🟠 Backup & disaster recovery for DB + ledger; tested restore.

### 2.3 Identity & access
- 🟠 SSO / OIDC for the dashboard (not just API keys); session management.
- 🟠 Finer-grained RBAC + per-tenant isolation guarantees; tenant data partitioning.
- 🟠 Per-tenant / per-key rate limits (distributed, Redis-backed — current limiter is per-instance).

### 2.4 Arbitrary upstream support
- 🟠 Configurable `upstream_url` so Aegis can govern any company API/agent endpoint, not only the 3 LLM providers.
- 🟢 Pluggable adapter interface for custom upstreams + response transforms.

---

## Phase 3 — Observability & operations 🟠

- 🟠 Wire OpenTelemetry to a real backend (Tempo/Jaeger/Datadog); add metrics (Prometheus) + dashboards (Grafana).
- 🟠 Structured logging with request correlation IDs; log shipping.
- 🟠 Alerting beyond webhook: PagerDuty/Opsgenie, SLO-based alerts.
- 🟠 Admin runbooks: key rotation, incident response, ledger verification procedure.

---

## Phase 4 — Validation, compliance & trust 🟠

- 🟠 Validate risk scoring + adversary battery against real attack datasets; tune thresholds, publish precision/recall.
- 🟠 Independent security audit / penetration test of the gateway itself.
- 🟠 Verify control library mappings (NIST AI RMF / ISO 27001 / EU AI Act) with a compliance expert.
- 🟠 Load/performance benchmarks with published latency & throughput numbers.
- 🟢 SOC 2 / ISO 27001 readiness for the product itself.

---

## Phase 5 — Quality & delivery 🟢

- 🟠 Integration + E2E test coverage (currently unit-only); coverage gates in CI.
- 🟠 Contract tests for each LLM provider + upstream adapter.
- 🟢 API versioning + OpenAPI client SDKs for customer agents.
- 🟢 Staging environment + blue/green or canary deploys.
- 🟢 Customer-facing docs: integration guide, SDK snippets, threat model.

---

## Suggested order of attack
1. **1.1 signing key** → makes evidence actually trustworthy across restarts.
2. **1.3 durable bus** + **1.4 vector store** → unlocks horizontal scale.
3. **1.2 real security scanning** → makes the core security claim credible.
4. **Phase 2** hardening → makes it safe to operate.
5. **Phase 4** validation → makes the "Trust Score" defensible to a regulator/customer.
