# 🚀 Production Readiness Checklist — Aegis Audit Swarm

Status legend: 🔴 blocker · 🟠 important · 🟢 nice-to-have · ✅ done

This is the work required to move Aegis from a working **MVP / pilot-grade** system
to something a security-conscious company can run in **production**. Items are
ordered by priority within each phase.

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
