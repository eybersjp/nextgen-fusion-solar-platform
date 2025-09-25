Below is a complete, ready‑to‑commit repository boilerplate. Copy directly into a fresh private GitHub repo, or let Trae write these files via `/implement` using this canvas as the source of truth.

---

# 0) Repository Layout (monorepo)

```
solar-platform/
├─ README.md
├─ .gitignore
├─ .editorconfig
├─ package.json
├─ pnpm-workspace.yaml
├─ turbo.json
├─ docker-compose.yml
├─ Makefile
├─ .env.example
├─ /docs
│  ├─ constitution.yml
│  ├─ user_rules.yml
│  ├─ project_rules.yml
│  ├─ tasks.seed.md
│  └─ adr/0001-use-monorepo.md
├─ /schemas
│  ├─ project.json
│  ├─ design.json
│  ├─ compliance.json
│  ├─ finance.json
│  └─ lender_checklist.json
├─ /apps
│  ├─ web/               # React + Vite
│  └─ gateway/           # Node/TS BFF
├─ /services
│  ├─ svc-design/        # FastAPI
│  ├─ svc-compliance/    # FastAPI (country packs)
│  ├─ svc-finance/       # FastAPI
│  ├─ svc-ops/           # FastAPI
│  └─ svc-support/       # FastAPI (AI copilot)
├─ /plugins
│  ├─ battery-design/
│  │  ├─ manifest.json
│  │  └─ src/index.ts
│  └─ example-hello/
│     ├─ manifest.json
│     └─ src/index.ts
├─ /infra
│  ├─ terraform/
│  │  ├─ main.tf
│  │  ├─ variables.tf
│  │  └─ outputs.tf
│  └─ k8s/
│     ├─ namespace.yaml
│     ├─ gateway.yaml
│     └─ svc-design.yaml
├─ /.github
│  └─ workflows/
│     ├─ ci.yml
│     ├─ e2e.yml
│     └─ deploy.yml
└─ /tools
   ├─ scripts/
   │  ├─ db-wait.sh
   │  └─ gen-openapi.sh
   └─ specify/
      └─ playbooks.md
```

---

# 1) Top‑Level Files

## README.md
```md
# Solar Platform (Trae + Spec‑Kit)

Spec‑driven, modular, AI‑enhanced solar platform. Built with Trae agents and GitHub Spec‑Kit to keep code aligned with requirements. Initial countries: South Africa, Australia, United States.

## Quickstart
```bash
pnpm i -w
cp .env.example .env
make dev   # starts DB, gateway, services, and web
```

Open: http://localhost:5173 (web), http://localhost:8080 (gateway)

## Spec‑Kit Flow
- `/constitution` → paste `docs/constitution.yml`
- `/specify` → paste High‑Level Product Spec (from canvas Section 5)
- `/plan` → paste Technical Implementation Plan (Section 6)
- `/tasks` → seed from `docs/tasks.seed.md`
- `/implement` → generate code under `/apps`, `/services`, `/plugins`

## Structure
- `apps/web`: React + Vite + Tailwind UI
- `apps/gateway`: API Gateway (Node/TS)
- `services/*`: Python FastAPI microservices
- `plugins/*`: add‑on modules (manifest‑driven)
- `schemas/*`: JSON Schemas (contracts)
- `infra/*`: Terraform + K8s manifests

## Commands
- `make dev` — local dev via Docker Compose
- `make test` — run unit tests (web + services)
- `make lint` — lint/format all
- `make typecheck` — TS typecheck + mypy

## Security & Compliance
- OIDC auth, RBAC + RLS in API layer (coming in M1)
- Data residency flags per env (US/EU/AU/ZA)
```

## .gitignore
```gitignore
# node
node_modules
pnpm-lock.yaml

# python
__pycache__
*.pyc
.venv

# env
.env
.env.*

# build
.dist
build
coverage

# editor
.vscode
.idea
```

## .editorconfig
```ini
root = true
[*]
charset = utf-8
end_of_line = lf
indent_size = 2
indent_style = space
insert_final_newline = true
trim_trailing_whitespace = true
```

## package.json (workspace root)
```json
{
  "name": "solar-platform",
  "private": true,
  "packageManager": "pnpm@9.6.0",
  "scripts": {
    "build": "turbo run build",
    "dev": "docker compose up --build",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "typecheck": "turbo run typecheck"
  },
  "devDependencies": {
    "turbo": "^2.1.0"
  }
}
```

## pnpm-workspace.yaml
```yaml
packages:
  - "apps/*"
  - "services/*"
  - "plugins/*"
```

## turbo.json
```json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**"] },
    "test": { "dependsOn": ["^build"] },
    "lint": {},
    "typecheck": {}
  }
}
```

## docker-compose.yml
```yaml
version: "3.9"
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: solar
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 20
  redis:
    image: redis:7
    ports: ["6379:6379"]
  gateway:
    build: ./apps/gateway
    env_file: .env
    ports: ["8080:8080"]
    depends_on: [db]
  svc-design:
    build: ./services/svc-design
    env_file: .env
    ports: ["8101:8000"]
    depends_on: [db]
  svc-compliance:
    build: ./services/svc-compliance
    env_file: .env
    ports: ["8102:8000"]
  svc-finance:
    build: ./services/svc-finance
    env_file: .env
    ports: ["8103:8000"]
  svc-support:
    build: ./services/svc-support
    env_file: .env
    ports: ["8104:8000"]
  web:
    build: ./apps/web
    env_file: .env
    ports: ["5173:5173"]
    depends_on: [gateway]
```

## Makefile
```make
.PHONY: dev test lint typecheck fmt

dev:
	docker compose up --build

down:
	docker compose down -v

test:
	pnpm -w test

lint:
	pnpm -w lint

fmt:
	pnpm -w lint --fix || true
	trufflehog --regex --entropy=False || true

typecheck:
	pnpm -w typecheck
```

## .env.example
```env
NODE_ENV=development
OIDC_ISSUER=https://your-issuer
OIDC_CLIENT_ID=xxx
OIDC_CLIENT_SECRET=xxx
DATABASE_URL=postgresql://postgres:postgres@db:5432/solar
REDIS_URL=redis://redis:6379
ALLOWED_ORIGINS=http://localhost:5173
```

---

# 2) Docs & Spec Files

## docs/constitution.yml
```yaml
name: constitution
purpose: Authoritative principles for spec‑driven dev.
principles:
  - Spec‑first; code follows specs
  - Single source of truth in repo; PR review required
  - Traceability: PR ↔ spec section
  - Safety: tests + approvals gate prod
  - Bankability outputs
  - Modularity via plug‑ins
  - Local compliance packs (ZA/AU/US)
```

## docs/user_rules.yml
```yaml
name: user_rules
preferences:
  tone: concise, professional
  ui_style: WCAG AA, multilingual (en, af, es, pt)
  currencies: [ZAR, AUD, USD]
  units_default: metric
product_principles:
  - bankability_by_default
  - explainable_ai
  - api_first_modular
```

## docs/project_rules.yml
```yaml
name: project_rules
code:
  frontend: typescript + react + vite + tailwind
  services: python (fastapi), typescript (gateway)
  schemas: json-schema versioned
security:
  authn: OIDC
  authz: RBAC + RLS
observability:
  tracing: opentelemetry
  logs: json
```

## docs/tasks.seed.md
```md
- Init monorepo and CI
- Implement auth skeleton in gateway
- Create design service MVP endpoints
- Add compliance country packs (ZA/AU/US)
- Permit generator MVP
- Finance P50/P90 endpoint
- Web shell (login, project list, design run)
```

## docs/adr/0001-use-monorepo.md
```md
# ADR-0001: Use Monorepo with pnpm workspaces
Decision: Keep apps, services, and plugins in one repo for atomic changes and shared tooling.
```

---

# 3) JSON Schemas (contracts)

## schemas/project.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "schemas/project.json",
  "type": "object",
  "required": ["id", "name", "country", "site"],
  "properties": {
    "id": {"type": "string", "format": "uuid"},
    "name": {"type": "string"},
    "country": {"enum": ["ZA", "AU", "US"]},
    "site": {"$ref": "#/definitions/site"},
    "design": {"$ref": "schemas/design.json"},
    "finance": {"$ref": "schemas/finance.json"}
  },
  "definitions": {
    "site": {
      "type": "object",
      "required": ["lat", "lng"],
      "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}, "elevation": {"type": "number"}}
    }
  }
}
```

## schemas/design.json (excerpt)
```json
{
  "$id": "schemas/design.json",
  "type": "object",
  "properties": {
    "dcAcRatio": {"type": "number"},
    "bifacial": {"type": "boolean"},
    "lossTree": {
      "type": "array",
      "items": {"type": "object", "properties": {"name": {"type": "string"}, "percent": {"type": "number"}}, "required": ["name", "percent"]}
    }
  }
}
```

## schemas/compliance.json (finding)
```json
{
  "$id": "schemas/compliance.json",
  "type": "object",
  "properties": {
    "ruleId": {"type": "string"},
    "severity": {"enum": ["info", "warning", "error"]},
    "message": {"type": "string"},
    "evidence": {"type": "object"},
    "remediation": {"type": "string"}
  },
  "required": ["ruleId", "severity", "message"]
}
```

## schemas/finance.json (P50/P90 input)
```json
{
  "$id": "schemas/finance.json",
  "type": "object",
  "properties": {
    "years": {"type": "integer", "minimum": 1, "maximum": 40},
    "weatherSource": {"type": "string"}
  }
}
```

## schemas/lender_checklist.json
```json
{"sections": [{"title": "Yield Methodology", "required": true}, {"title": "Assumptions Register", "required": true}]}
```

---

# 4) Apps

## apps/web/Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json pnpm-lock.yaml* .npmrc* ./
RUN corepack enable && pnpm i
COPY . .
EXPOSE 5173
CMD ["pnpm","dev","--","--host","0.0.0.0"]
```

## apps/web/package.json
```json
{
  "name": "web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.1",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "eslint": "^9.11.1",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vitest": "^2.1.1",
    "tailwindcss": "^3.4.10",
    "postcss": "^8.4.45",
    "autoprefixer": "^10.4.20"
  }
}
```

## apps/web/src/main.tsx
```tsx
import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'

function App() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold">Solar Platform</h1>
      <p className="text-slate-600">Spec‑driven, modular, AI‑enhanced.</p>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
```

## apps/web/index.html
```html
<!doctype html>
<html><head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Solar Platform</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body></html>
```

## apps/gateway/Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json pnpm-lock.yaml* .npmrc* ./
RUN corepack enable && pnpm i
COPY . .
EXPOSE 8080
CMD ["pnpm","start"]
```

## apps/gateway/package.json
```json
{
  "name": "gateway",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts",
    "build": "tsup src/index.ts --format esm,cjs --dts",
    "lint": "eslint .",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "fastify": "^4.28.1",
    "fastify-cors": "^8.5.0",
    "fastify-jwt": "^6.5.0",
    "zod": "^3.23.8",
    "undici": "^6.19.8"
  },
  "devDependencies": {
    "@types/node": "^22.5.5",
    "eslint": "^9.11.1",
    "tsup": "^8.3.0",
    "tsx": "^4.19.1",
    "typescript": "^5.6.2",
    "vitest": "^2.1.1"
  }
}
```

## apps/gateway/src/index.ts
```ts
import Fastify from 'fastify'
import cors from '@fastify/cors'

const app = Fastify({ logger: true })
await app.register(cors, { origin: process.env.ALLOWED_ORIGINS?.split(',') || true })

app.get('/api/health', async () => ({ ok: true }))

app.post('/api/compliance/check', async (req, reply) => {
  // proxy to svc-compliance in dev
  const res = await fetch('http://svc-compliance:8000/check', { method: 'POST', body: JSON.stringify(await req.body), headers: { 'content-type': 'application/json' }})
  reply.send(await res.json())
})

app.listen({ port: 8080, host: '0.0.0.0' })
```

---

# 5) Services (Python FastAPI)

## common service template (each service has similar files)
```
services/svc-*/
├─ Dockerfile
├─ pyproject.toml
├─ app/
│  ├─ main.py
│  ├─ routers/*.py
│  ├─ models/*.py
│  └─ deps.py
└─ tests/
```

## services/svc-compliance/Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install -r <(uv pip compile pyproject.toml --generate-hashes) || true
COPY app ./app
EXPOSE 8000
CMD ["python","-m","app.main"]
```

## services/svc-compliance/pyproject.toml
```toml
[project]
name = "svc-compliance"
version = "0.1.0"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic>=2",
]
```

## services/svc-compliance/app/main.py
```py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal, List, Dict, Any

app = FastAPI(title="svc-compliance")

class ComplianceFinding(BaseModel):
    ruleId: str
    severity: Literal["info","warning","error"]
    message: str
    evidence: Dict[str, Any] | None = None
    remediation: str | None = None

class CheckRequest(BaseModel):
    country: Literal["ZA","AU","US"]
    code: str
    projectId: str | None = None
    design: dict

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/check", response_model=List[ComplianceFinding])
async def check(req: CheckRequest):
    # Minimal placeholder rules — replace with real packs
    findings: List[ComplianceFinding] = []
    if req.country == "US" and req.code.startswith("NEC"):
        if req.design.get("dcAcRatio", 1.0) > 1.7:
            findings.append(ComplianceFinding(
                ruleId="NEC-690.8-DCAC",
                severity="warning",
                message="High DC/AC ratio; verify clipping and conductor sizing.",
                remediation="Reduce DC or upsize inverter; attach clipping calc."
            ))
    return findings
```

## services/svc-finance/app/main.py (excerpt)
```py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="svc-finance")

class PRequest(BaseModel):
    years: int = 25
    lossTree: list[dict] = []

@app.post("/p50p90")
async def p50p90(req: PRequest):
    base = 1000.0  # kWh/kWp dummy
    loss = sum([x.get("percent",0)/100 for x in req.lossTree])
    p50 = base * (1 - loss)
    p90 = p50 * 0.92
    p99 = p50 * 0.85
    return {"p50": p50, "p90": p90, "p99": p99}
```

---

# 6) Plugins

## plugins/example-hello/manifest.json
```json
{
  "id": "com.solar.example-hello",
  "name": "Example Hello",
  "version": "1.0.0",
  "capabilities": ["ui:panel"],
  "routes": [{"path": "/plugins/hello", "method": "GET"}],
  "permissions": {"scopes": ["project:read"]},
  "ui": {"panels": ["HelloPanel"], "i18n": ["en"]}
}
```

## plugins/example-hello/src/index.ts
```ts
export function register() {
  return {
    panels: [{ id: 'HelloPanel', name: 'Hello', render: () => 'Hello Plugin' }]
  }
}
```

## plugins/battery-design/manifest.json
```json
{
  "id": "com.solar.battery-design",
  "name": "Battery & Microgrid Designer",
  "version": "1.0.0",
  "capabilities": ["design:bess", "finance:dispatch", "compliance:ieee-1547"],
  "inputsSchema": "../../schemas/design.json",
  "outputsSchema": "./schemas/bess.output.schema.json",
  "routes": [{"path": "/plugins/bess/optimize", "method": "POST"}],
  "permissions": {"scopes": ["project:read", "boq:write"]},
  "ui": {"panels": ["BESSOptimizerPanel"], "i18n": ["en","af","es","pt"]}
}
```

---

# 7) CI/CD Workflows

## .github/workflows/ci.yml
```yaml
name: ci
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: pnpm i -w
      - run: pnpm -w lint
      - run: pnpm -w build
      - run: pnpm -w test
```

## .github/workflows/deploy.yml (stub)
```yaml
name: deploy
on:
  workflow_dispatch:
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure Cloud (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Deploy manifests
        run: |
          echo "apply k8s manifests here"
```

---

# 8) Infra (Terraform/K8s stubs)

## infra/terraform/main.tf (skeleton)
```hcl
terraform { required_version = ">= 1.5.0" }
provider "aws" { region = var.region }

# Define VPC, RDS (Postgres), EKS, S3 buckets as modules (omitted for brevity)
```

## infra/k8s/namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata: { name: solar }
```

## infra/k8s/gateway.yaml (stub)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: gateway, namespace: solar }
spec:
  replicas: 2
  selector: { matchLabels: { app: gateway } }
  template:
    metadata: { labels: { app: gateway } }
    spec:
      containers:
        - name: gateway
          image: ghcr.io/yourorg/gateway:latest
          ports: [{ containerPort: 8080 }]
```

---

# 9) Tools & Scripts

## tools/scripts/db-wait.sh
```bash
#!/usr/bin/env bash
set -e
until pg_isready -h db -p 5432 -U postgres; do echo "Waiting for db"; sleep 2; done
```

## tools/specify/playbooks.md
```md
### Initialize Spec‑Kit in this repo
/constitution (paste docs/constitution.yml)
/specify (paste High‑Level Product Spec from canvas)
/plan (paste Technical Implementation Plan)
/tasks (seed from docs/tasks.seed.md)
/implement
```

---

# 10) Getting Started (one page)

1. Clone repo → `pnpm i -w` → `cp .env.example .env`.
2. In Trae: open repo, create agents from canvas Appendix, load `.rules`.
3. Run Spec‑Kit commands from **tools/specify/playbooks.md**.
4. `make dev` to launch local stack.
5. Use `/implement` to flesh out services and plugins following schemas.
6. Commit, push, open PR → CI runs. Deploy with `deploy` workflow when ready.

---

**End of Boilerplate**

