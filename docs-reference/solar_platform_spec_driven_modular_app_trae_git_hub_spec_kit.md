# Master Document Index

This canvas contains a complete, spec‑driven document set to build the modular, AI‑enhanced solar platform using **Trae AI** and **GitHub Spec‑Kit**. It’s organized into distinct entities. Use the “Find” feature to jump to a section.

**Entities**
1. [Beginner Handbook (Step‑by‑Step, Zero‑to‑Ship)](#1-beginner-handbook-step-by-step-zero-to-ship)
2. [User Rules (Agent Behavior Preferences)](#2-user-rules-agent-behavior-preferences)
3. [Project Rules (Engineering Guardrails)](#3-project-rules-engineering-guardrails)
4. [Spec‑Kit Constitution (Authoritative Principles)](#4-spec-kit-constitution-authoritative-principles)
5. [High‑Level Product Specification (What & Why)](#5-high-level-product-specification-what--why)
6. [Technical Implementation Plan (How)](#6-technical-implementation-plan-how)
7. [Execution Tasks & Milestones (Auto‑generated with /tasks)](#7-execution-tasks--milestones-auto-generated-with-tasks)
8. [Architecture & Modular Plug‑in System](#8-architecture--modular-plug-in-system)
9. [Domain Models & Data Schemas](#9-domain-models--data-schemas)
10. [Service & API Specifications](#10-service--api-specifications)
11. [Country Code Packs (SA, AU, US)](#11-country-code-packs-sa-au-us)
12. [AI Copilot & Tech‑Support Bot Specifications](#12-ai-copilot--tech-support-bot-specifications)
13. [Data Sources & Integrations](#13-data-sources--integrations)
14. [Security, Privacy, and Compliance](#14-security-privacy-and-compliance)
15. [DevOps, CI/CD, and Environments](#15-devops-cicd-and-environments)
16. [Quality Assurance & Testing Strategy](#16-quality-assurance--testing-strategy)
17. [Observability & SRE](#17-observability--sre)
18. [Bankability Outputs & Lender Package Spec](#18-bankability-outputs--lender-package-spec)
19. [Marketplace & Monetization](#19-marketplace--monetization)
20. [Governance & Change Management](#20-governance--change-management)
21. [Appendix: Trae Agent Setups, .rules, and Command Playbooks](#21-appendix-trae-agent-setups-rules-and-command-playbooks)
22. [Glossary](#22-glossary)

> **Note**: These specs are implementation‑ready and align with Spec‑Kit’s `/constitution → /specify → /plan → /tasks → /implement` workflow. You can paste any section into your agent, or run the commands from the Handbook.

---

# 1) Beginner Handbook (Step‑by‑Step, Zero‑to‑Ship)

**Goal**: Get from nothing to a running, modular solar platform with Trae + Spec‑Kit — without further assistance.

## A. Prerequisites
- Git ≥ 2.39
- Node.js ≥ 20 & pnpm ≥ 9 (frontend)
- Python ≥ 3.11 (data/CLI/micro‑services tooling)
- Docker Desktop (containers) & Docker Compose v2
- A GitHub account (private repo recommended)
- Trae IDE (latest) installed on your machine

> Optional: Cloud accounts (AWS/Azure/GCP) and a Postgres instance (local via Docker is fine).

## B. Create & Initialize the Project (Spec‑Kit)
1. **Create a new empty GitHub repo**: `solar-platform` (private).
2. **Clone locally**: `git clone <your_repo_url>`.
3. **Install Spec‑Kit’s CLI (Specify)** using the **uv** tool:
   ```bash
   # persistent installation
   uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
   # or one‑time execution
   uvx --from git+https://github.com/github/spec-kit.git specify init solar-platform
   ```
4. **Bootstrap the project using Specify**:
   ```bash
   cd solar-platform
   specify init --here
   specify check   # verifies agent tooling availability
   ```
5. Commit the scaffold: `git add -A && git commit -m "chore: init spec-kit scaffold"`.

## C. Open in Trae & Configure Agents
1. Open the repo folder in **Trae IDE**.
2. Create/select the **@Builder** agent, then create **custom agents** from the Appendix templates:
   - **@SpecOverseer** (enforces rules/specs)
   - **@SolarEngineer** (domain expert for PV/BESS)
   - **@ComplianceBot** (SA/AU/US code packs)
   - **@SupportCopilot** (tech support & AR workflows)
3. Add `.rules` files from Appendix to the repo root and to each module (they’re inherited by Trae and your agents).
4. (Optional) Attach MCP/Tools for web/GIS/diagramming if you use them.

## D. Authoritative Grounding — Create Constitution & Specs
1. In the agent chat (Trae), run:
   - `/constitution` → Paste the **Spec‑Kit Constitution** section.
   - `/specify` → Paste the **High‑Level Product Specification**.
   - `/plan` → Paste the **Technical Implementation Plan**.
   - `/tasks` → Generate tasks → copy them into `docs/tasks.md`.
   - `/implement` → Let the agent generate code following the plan.

## E. Run Locally
```bash
# One‑command developer environment
make dev   # or: docker compose up --build
# Frontend at http://localhost:5173 (Vite)
# API gateway at http://localhost:8080
# Postgres at localhost:5432 (dockerized)
```

## F. Validate & Commit
- Run unit tests: `pnpm test` (frontend), `pytest` (services)
- Lint/format: `pnpm lint:fix`, `ruff --fix`, `black .`
- Commit: `git commit -m "feat: initial modules + services" && git push`

## G. Deploy to a Sandbox
- Provision **staging** infra (IaC templates provided): `infra/terraform`.
- Set secrets in GitHub Actions → run `deploy-staging` workflow.

## H. How to Iterate
- Modify specs (not code) → re‑`/plan` → `
/tasks` → `/implement`.
- Use **@SpecOverseer** to ensure diffs comply with **User Rules** & **Project Rules**.

> You are now set. The rest of this canvas is your authoritative source of truth for the build.

---

# 2) User Rules (Agent Behavior Preferences)

**Purpose**: Personal, product, and UX preferences that must drive every AI decision.

```yaml
name: user_rules
version: 1.0
owner:
  org: Solar Super‑Platform, Inc.
  contact: you@example.com
preferences:
  tone: concise, professional, explainable
  docs: write first; code follows docs
  ui_style: clean, accessible (WCAG AA), international (EN/AFR/ES/PT)
  currencies: ZAR, AUD, USD (auto‑convert)
  units: metric by default; imperial optional in US contexts
  legal_disclaimer: "Compliance outputs are guidance, not legal advice."
product_principles:
  - bankability_by_default
  - global_compliance_packs
  - explainable_ai
  - offline_capable_field_apps
  - api_first_modular
risk_tolerance:
  production_changes_require: 2 approvals + green CI
  ai_autonomy_limit: "No schema or data‑lossing migrations without human approval"
non_goals:
  - on‑prem support in v1 (VPC is ok)
  - building a custom 3D engine
```

---

# 3) Project Rules (Engineering Guardrails)

```yaml
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
```

---

# 4) Spec‑Kit Constitution (Authoritative Principles)

> Paste this into `/constitution`.

```yaml
name: constitution
purpose: Establish non‑negotiable principles for Spec‑Driven Development.
principles:
  - Spec‑first: all work originates from specs; code never precedes specs.
  - Single source of truth: specs live in repo; changes require PR & review.
  - Traceability: every PR links to spec section + task id.
  - Safety: production changes gated by tests and approvals.
  - Bankability: outputs meet lender‑grade standards (see Section 18).
  - Modularity: all features are plug‑ins with stable contracts.
  - Local compliance: country packs enforce regional rules (SA/AU/US v1).
commands_alignment:
  - /specify must not prescribe stack choices.
  - /plan must map to tech choices and module boundaries.
  - /tasks must be small, parallelizable, and testable.
  - /implement must not edit specs; only generate code/tests.
```

---

# 5) High‑Level Product Specification (What & Why)

> Paste this into `/specify`.

**Vision**: One cloud platform that takes a solar project from **prospecting → engineering → permitting → procurement → construction → commissioning → operations → financing**. Bankable outputs, global compliance, and radical ease‑of‑use. Initial focus countries: **South Africa, Australia, United States**.

## Target Users
- Solar EPCs, engineering firms, solar designers/engineers, and installers.
- Secondary: lenders, insurers, O&M providers.

## Core Use Cases
1. **Prospecting & Site Intelligence**: global GIS, tariff/incentive lookup, feasibility scoring with P50/P90.
2. **Design & Engineering**: AI‑assisted layout, stringing, loss tree, BoM, code compliance checks.
3. **Permitting & Compliance**: localized permit packs (SA/AU/US v1).
4. **Financing & Bankability**: lender data room, risk scoring, P50/P90/P99.
5. **Procurement & Construction**: RFQ/RFP, AR‑guided install, QA/QC, commissioning wizard.
6. **Operations & Asset Mgmt**: monitoring, anomaly detection, CMMS, settlement.
7. **Sales & Marketing**: AI proposal generator, lead scoring, dynamic pricing/margins.
8. **Technical Support**: AI copilot (text/voice/vision) with photo/video diagnostics.

## Platform Requirements
- Modular **plug‑in** model with marketplace.
- Internationalization (units, currencies, languages).
- Accessibility (WCAG AA) and low‑bandwidth field mode.
- APIs for ecosystem partners; data export/import to PVsyst/HelioScope where applicable.

## Non‑Goals (v1)
- On‑prem bare‑metal deployments; multi‑cloud is acceptable.

---

# 6) Technical Implementation Plan (How)

> Paste this into `/plan`.

## Tech Stack
- **Frontend**: React + Vite + TypeScript + Tailwind; shadcn/ui components; MapLibre for maps.
- **Backend**: Python FastAPI services (analysis, compliance, finance); Node/TS for gateway.
- **Data**: Postgres + PostGIS; Redis for cache/queues; MinIO/S3 for object storage.
- **AI**: Provider‑agnostic LLM client; RAG over standards/Manuals; vector DB (pgvector or Qdrant).
- **Infra**: Docker Compose (dev), Terraform + Kubernetes (staging/prod).
- **Auth**: OIDC (Auth0/Cognito) + RBAC with Postgres RLS.

## Service Boundaries
- `svc-design`: layouts, shading, loss models.
- `svc-compliance`: code checks (country packs).
- `svc-finance`: P50/P90, IRR/LCOE, lender packs.
- `svc-procure`: RFQ/RFP, vendors, pricing.
- `svc-ops`: telemetry ingestion, anomaly detection, CMMS.
- `svc-support`: AI troubleshooting (text/voice/vision).
- `api-gateway`: BFF for frontend + auth, rate‑limit, audit logging.

## Data Flow
- Frontend → API Gateway → services.
- AI services call RAG/Tools; persist artifacts (reports, permit sets) to object storage.

## Contracts
- All services expose OpenAPI schemas and publish JSON Schema for inputs/outputs.
- Plug‑ins register capabilities via manifest (see Section 8).

## Environments
- `dev`, `staging`, `prod` with separate DBs & buckets; feature flags for dark‑launches.

---

# 7) Execution Tasks & Milestones (Auto‑generated with /tasks)

> Use this as seed text for `/tasks` to produce a detailed backlog.

**Milestone M0 — Foundations (2–3 weeks)**
- Init repo with Spec‑Kit, Constitution, Rules, CI scaffolding
- Auth skeleton (OIDC), RBAC stubs, Postgres + PostGIS
- UI shell, navigation, locale/units switcher, map base

**Milestone M1 — Core Design & Compliance (4–6 weeks)**
- `svc-design`: roof/ground layout MVP, BoM generator, loss tree
- `svc-compliance`: packs for **ZA (NRS/SANS)**, **AU (CEC/AS/NZS)**, **US (NEC/UL/IEEE)**
- Permit pack generator MVP (country templates)

**Milestone M2 — Finance & Sales (4–6 weeks)**
- `svc-finance`: yield uncertainty, P50/P90/P99, IRR/LCOE
- Proposal generator + dynamic pricing/margins

**Milestone M3 — Field & Ops (6–8 weeks)**
- AR install checklist, commissioning wizard
- Ops ingestion + anomaly detection + CMMS

**Milestone M4 — Marketplace (4–6 weeks)**
- Plug‑in registry, vendor onboarding, rev share

---

# 8) Architecture & Modular Plug‑in System

## Plug‑in Philosophy
- Everything non‑core is a plug‑in with a **stable contract**.
- Hot‑swappable, versioned, and permission‑scoped.

## Plug‑in Manifest (example)
```json
{
  "id": "com.solar.battery-design",
  "name": "Battery & Microgrid Designer",
  "version": "1.0.0",
  "capabilities": ["design:bess", "finance:dispatch", "compliance:ieee-1547"],
  "inputsSchema": "schemas/bess.input.schema.json",
  "outputsSchema": "schemas/bess.output.schema.json",
  "routes": [{"path": "/plugins/bess/optimize", "method": "POST"}],
  "permissions": {"scopes": ["project:read", "boq:write"]},
  "ui": {"panels": ["BESSOptimizerPanel"], "i18n": ["en", "af", "es", "pt"]}
}
```

## Registration & Lifecycle
- Plug‑ins register with `svc-registry` (part of gateway).
- On enable: migrate any plugin tables; publish OpenAPI; add UI panel lazily.
- On disable: revoke scopes; no hard deletes; archive data.

## Extension Points
- **Design**: layouts, loss models, shading engines
- **Compliance**: new jurisdictions, AHJ templates
- **Finance**: incentive models, lenders/insurers
- **Field**: checklists, AR overlays, device drivers
- **Ops**: anomaly rules, ticket workflows

---

# 9) Domain Models & Data Schemas

> Excerpts; full JSON Schemas are part of `/schemas`.

### Project
```json
{
  "$id": "schemas/project.json",
  "type": "object",
  "required": ["id", "name", "country", "site", "owner"],
  "properties": {
    "id": {"type": "string", "format": "uuid"},
    "name": {"type": "string"},
    "country": {"enum": ["ZA", "AU", "US"]},
    "site": {"$ref": "#/definitions/site"},
    "tariff": {"type": "string"},
    "incentives": {"type": "array", "items": {"type": "string"}},
    "design": {"$ref": "schemas/design.json"},
    "compliance": {"$ref": "schemas/compliance.json"},
    "finance": {"$ref": "schemas/finance.json"}
  },
  "definitions": {
    "site": {
      "type": "object",
      "properties": {
        "lat": {"type": "number"},
        "lng": {"type": "number"},
        "elevation": {"type": "number"}
      },
      "required": ["lat", "lng"]
    }
  }
}
```

### Design (loss tree excerpt)
```json
{
  "lossTree": [
    {"name": "Soiling", "percent": 2.0},
    {"name": "Mismatch", "percent": 1.0},
    {"name": "Wiring", "percent": 0.7},
    {"name": "Temperature", "percent": 6.0}
  ],
  "dcAcRatio": 1.25,
  "bifacial": true
}
```

### Compliance Finding
```json
{
  "ruleId": "NEC-690.7(A)-2023",
  "severity": "error",
  "message": "Max system voltage exceeds permitted value for module temp",
  "evidence": {"calculation": "V_oc_temp", "inputs": {"T_min": -10}},
  "remediation": "Reduce strings in series or select different module"
}
```

---

# 10) Service & API Specifications

### API Gateway (BFF)
- Auth: OIDC bearer + project‑scoped JWT claims
- Rate limiting: token bucket per org/user
- Endpoints (sample):
  - `GET /api/projects/:id`
  - `POST /api/design/optimize`
  - `POST /api/compliance/check`
  - `POST /api/finance/p50p90`
  - `POST /api/permit/generate`
  - `POST /api/plugins/:id/execute`

### Compliance API (country pack)
```http
POST /api/compliance/check
Content-Type: application/json
{
  "country": "US",
  "code": "NEC-2023",
  "projectId": "...",
  "design": { /* design schema */ }
}
```
**Response**: array of `ComplianceFinding` with `severity` and `remediation`.

### Finance API (P50/P90)
```http
POST /api/finance/p50p90
{
  "site": {"lat": -33.92, "lng": 18.42},
  "design": {"dcAcRatio": 1.25, "lossTree": [...]},
  "weatherSource": "best_available",
  "years": 25
}
```

---

# 11) Country Code Packs (SA, AU, US)

> Enforcement is implemented as **rule engines** with explainable checks and references.

## South Africa (ZA) — examples
- **NRS** series (e.g., NRS 097 for grid‑interconnection LV/MV)
- **SANS** 10142‑1 (wiring code) — PV chapter
- Municipal permit templates (Cape Town, Johannesburg, Tshwane)

Checks (illustrative):
- Inverter anti‑islanding settings & grid codes match utility requirements.
- Labeling/signage per municipal templates.
- Structural wind uplift calc references local map zones.

## Australia (AU)
- **CEC** design/installation guidelines
- **AS/NZS 5033** (PV arrays), **AS/NZS 4777** (inverters), **AS/NZS 3000** (Wiring Rules)
- STC/LGC paperwork automation templates

## United States (US)
- **NEC 2023 (NFPA 70)** PV articles (690/705/706)
- **UL 1741 SB**, **IEEE 1547‑2018**, local AHJ fire codes
- AHJ‑specific permit packages

> These references are used to **name rules** and produce **explainable findings**. Always display a disclaimer that outputs are guidance, not legal advice.

---

# 12) AI Copilot & Tech‑Support Bot Specifications

## Architecture
- **RAG** over code/standards/manuals, with source citations
- **Tools**: file system, shell, web fetch, image analysis (for field photos)
- **Modes**: Design Copilot, Compliance Assistant, Support Copilot (field)

## Support Copilot (Field)
- Inputs: photo/video, error codes, device model
- Outputs: stepwise remediation, safety call‑outs, parts list
- AR checklist JSON for mobile app

## Design Copilot
- Commands: “Optimize DC/AC”, “Run shade sweep”, “Generate BoM”, “Explain violation X”

## Guardrails
- Never autocorrect designs without showing diffs.
- Always show uncertainty & cite authoritative source IDs in explanations.

---

# 13) Data Sources & Integrations

- **GIS**: satellite/DEM/parcel layers; PostGIS tiling; MapLibre in UI
- **Tariffs & Incentives**: country libraries with versioned records
- **Interconnection**: utility capacity maps where available
- **OEM Portals**: telemetry ingestion via SunSpec/MODBUS/IEC‑61850 adapters
- **Document Generation**: LaTeX/Weasy templates for permits and lender packs

---

# 14) Security, Privacy, and Compliance

- SOC 2 Type II & ISO 27001 roadmap
- Data encryption: AES‑256 at rest, TLS 1.2+ in transit
- Audit logging for all privileged actions
- Data residency controls (US/EU/AU/ZA)
- Privacy by design; minimization; retention schedules

---

# 15) DevOps, CI/CD, and Environments

- **GitHub Actions** workflows:
  - `ci.yml`: lint, type‑check, build, unit tests
  - `e2e.yml`: Playwright tests on PR
  - `deploy.yml`: staging/prod to Kubernetes via OIDC
- **IaC**: Terraform modules for DB, buckets, CDN, cluster
- **Secrets**: stored in cloud secret manager, injected at runtime

---

# 16) Quality Assurance & Testing Strategy

- Unit tests ≥ 80% critical modules
- Contract tests for every service & plugin
- Golden files for permit/lender reports
- Synthetic monitoring for critical user journeys

---

# 17) Observability & SRE

- OpenTelemetry traces across gateway & services
- RED metrics per service; SLO error budgets and alerting
- Runbooks for common incidents (DB failover, queue backlog)

---

# 18) Bankability Outputs & Lender Package Spec

**Artifacts**
- Energy yield report with **P50/P90/P99** and uncertainty methods
- Assumptions register with versioning & audit trail
- Degradation/soiling methodologies
- Contracts & warranties index
- Export bundles: ZIP with PDF + machine‑readable JSON

**Checklist JSON (sample)**
```json
{
  "sections": [
    {"title": "Yield Methodology", "required": true},
    {"title": "Assumptions Register", "required": true},
    {"title": "BoM & Warranties", "required": true}
  ]
}
```

---

# 19) Marketplace & Monetization

- Take‑rates: financing, insurance, PE stamping, procurement
- Plug‑in revenue share for third‑party modules
- Usage‑based pricing for compute (sim minutes, lidar credits)

---

# 20) Governance & Change Management

- Spec changes via PR with **ADR (Architecture Decision Record)**
- Versioned country packs; deprecations with migration notes
- Monthly release trains; hotfix lanes

---

# 21) Appendix: Trae Agent Setups, .rules, and Command Playbooks

## A. Trae Agent Directory
- **@SpecOverseer** — blocks non‑compliant diffs
- **@SolarEngineer** — domain RAG + design reasoning
- **@ComplianceBot** — runs country pack rule checks
- **@SupportCopilot** — photo/video troubleshooting
- **@Builder** — default implementer (kept but supervised)

## B. Example `.rules` (root)
```json
{
  "identity": {
    "name": "SpecOverseer",
    "role": "Ensure absolute alignment with specs and rules"
  },
  "context": {
    "include": ["README.md", "docs/", "schemas/", "/Spec‑Kit Constitution/", "/Project Rules/", "/User Rules/"]
  },
  "policies": [
    "Never modify files in /docs without a linked spec change",
    "Reject code that reduces type safety or test coverage",
    "Require citations for compliance conclusions"
  ],
  "limits": {
    "max_changes_per_pr": 50,
    "blocked_paths": ["/migrations/drop_*", "/secrets"]
  }
}
```

## C. Country Pack `.rules` overlays
- `rules.za.json`, `rules.au.json`, `rules.us.json` loaded when the project country matches, injecting jurisdiction‑specific behaviors and vocabulary.

## D. Command Playbooks (copy/paste)

**Initialize rules & constitution**
```
/constitution (paste Section 4)
/specify (paste Section 5)
/plan (paste Section 6)
/tasks — generate backlog from plan
```

**Implement a plug‑in**
```
/specify Add a Battery & Microgrid Designer plug‑in with dispatch optimization and IEEE‑1547 checks.
/plan Create svc-bess service with endpoints; UI panel "BESSOptimizerPanel"; manifest as in Section 8.
/tasks
/implement
```

**Add a country pack**
```
/specify Add compliance checks for AU with AS/NZS 5033 & 4777 and CEC templates.
/plan Extend svc-compliance rules; add templates; update permit generator.
/tasks
/implement
```

---

# 22) Glossary
- **AHJ**: Authority Having Jurisdiction (local permitting authority)
- **BoM/BoQ**: Bill of Materials/Quantities
- **CMMS**: Computerized Maintenance Management System
- **LCOE/IRR**: Levelized Cost of Energy / Internal Rate of Return
- **P50/P90/P99**: Probabilistic yield scenarios
- **RAG**: Retrieval‑Augmented Generation
- **RBAC/RLS**: Role‑based access control / Row‑level security

---

**End of Document**

