name: project_rules
version: 1.0
code:
lang_frontend: typescript
lang_services: python, typescript
framework_frontend: vite + react + tailwind
apis: REST + GraphQL (Hasura‑style patterns)
schema_migrations: alembic (py) + prisma (ts)
lint: eslint, ruff, black, prettier
test: vitest, pytest, pytest‑asyncio, playwright
security:
authn: OIDC (Auth0/Cognito), SSO/SAML for enterprise
authz: RBAC + row‑level security (Postgres RLS)
secrets: 12‑factor via env + GitHub OIDC to cloud
performance:
SLOs:
api_p95_latency_ms: 300
ui_tti_s: 2.5
availability: 99.9%
observability:
logs: JSON structured
tracing: OpenTelemetry
metrics: RED/USE standards
data:
pii: encrypted_at_rest
residency: selectable (US/EU/AU/ZA)
retention: 7y for finance artifacts
ai:
pattern: RAG + Toolformer style calls
guardrails:
- never hallucinate standards; cite source ids
- show uncertainty bands for P50/P90
release:
branches: trunk‑based with short‑lived PRs
versioning: semver + feature flags