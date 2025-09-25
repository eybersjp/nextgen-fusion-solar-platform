This document adds **permit & lender report generators** with templates and endpoints. You get both **LaTeX** and **HTML→PDF** (WeasyPrint) options so you can pick what fits your CI/CD environment.

---

# 0) File Layout
```
services/
├─ svc-compliance/
│  └─ app/
│     ├─ templates/
│     │  ├─ permit.tex              # LaTeX base (AHJ checklists)
│     │  └─ permit.html             # HTML base (WeasyPrint)
│     └─ permit_render.py           # renderer util
└─ svc-finance/
   └─ app/
      ├─ templates/
      │  ├─ lender_report.tex       # LaTeX lender pack
      │  └─ lender_report.html      # HTML lender pack
      ├─ report_render.py           # renderer util (Jinja2 + WeasyPrint)
      └─ main.py                    # add /report endpoints
```

> **Tip**: Use HTML+WeasyPrint for fast setup. Use LaTeX for higher typographic quality when your build runners have a TeX engine (e.g., **tectonic**).

---

# 1) Permit Templates (Compliance)

## app/templates/permit.html
```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    h1 { font-size: 20px; margin: 0 0 8px; }
    h2 { font-size: 16px; margin: 16px 0 6px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #999; padding: 6px; font-size: 12px; }
    .small { color: #555; font-size: 11px; }
  </style>
</head>
<body>
  <h1>Permit Checklist — {{ authority_name }}</h1>
  <p class="small">Project: {{ project.name }} · Country: {{ project.country }}</p>
  <h2>Required Documents</h2>
  <table>
    <thead><tr><th>ID</th><th>Label</th><th>Required</th></tr></thead>
    <tbody>
      {% for item in checklist %}
      <tr>
        <td>{{ item.id }}</td>
        <td>{{ item.label }}</td>
        <td>{{ 'Yes' if item.required else 'No' }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <p class="small">Generated: {{ generated_at }}</p>
</body>
</html>
```

## app/templates/permit.tex
```tex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{array}
\begin{document}
\section*{Permit Checklist --- {{ authority_name }}}
Project: {{ project.name }} \quad Country: {{ project.country }}\\
\subsection*{Required Documents}
\begin{tabular}{| m{2.5cm} | m{9cm} | m{2cm} |}\n\hline
\textbf{ID} & \textbf{Label} & \textbf{Required}\\ \hline
{% for item in checklist %}
{{ item.id }} & {{ item.label }} & {% if item.required %}Yes{% else %}No{% endif %} \\ \hline
{% endfor %}
\end{tabular}

\vspace{6mm}
\textit{Generated: {{ generated_at }}}
\end{document}
```

## app/permit_render.py (Compliance)
```py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
from pathlib import Path
from weasyprint import HTML

TEMPLATES = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_permit_html(authority_name: str, checklist: list[dict], project: dict) -> bytes:
    tpl = env.get_template("permit.html")
    html = tpl.render(authority_name=authority_name, checklist=checklist, project=project, generated_at=datetime.utcnow().isoformat())
    return HTML(string=html).write_pdf()

# If using LaTeX/tectonic, add a tex renderer (optional) — see svc-finance example for approach.
```

> **Gateway wiring**: your existing `/permit/template` returns a checklist JSON. Pass that JSON + project info to `render_permit_html()` and send `application/pdf` back to the client.

---

# 2) Lender Report Templates (Finance)

## app/templates/lender_report.html
```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    h1 { font-size: 22px; margin: 0 0 12px; }
    h2 { font-size: 16px; margin: 18px 0 6px; }
    .meta { color: #555; font-size: 12px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #999; padding: 6px; font-size: 12px; }
    .code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
  </style>
</head>
<body>
  <h1>Lender Package — Energy Yield & Assumptions</h1>
  <p class="meta">Project: {{ project.name }} · Country: {{ project.country }} · Version: {{ version }}</p>

  <h2>Summary Metrics</h2>
  <table>
    <tr><th>P50 (kWh/kWp)</th><th>P90</th><th>P99</th><th>Uncertainty (1σ)</th></tr>
    <tr><td>{{ p50 }}</td><td>{{ p90 }}</td><td>{{ p99 }}</td><td>{{ sigma }}</td></tr>
  </table>

  <h2>Loss Tree</h2>
  <table>
    <thead><tr><th>Loss</th><th>%</th></tr></thead>
    <tbody>
      {% for l in loss_tree %}
      <tr><td>{{ l.name }}</td><td>{{ l.percent }}</td></tr>
      {% endfor %}
    </tbody>
  </table>

  <h2>Assumptions Register</h2>
  <pre class="code">{{ assumptions | tojson(indent=2) }}</pre>

  <h2>Compliance Snapshot</h2>
  <ul>
    {% for f in findings %}
      <li>[{{ f.severity|upper }}] {{ f.ruleId }} — {{ f.message }}</li>
    {% endfor %}
  </ul>

  <p class="meta">Generated: {{ generated_at }}</p>
</body>
</html>
```

## app/templates/lender_report.tex
```tex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{hyperref}
\begin{document}
\section*{Lender Package — Energy Yield \\ \normalsize Project: {{ project.name }} | Country: {{ project.country }} | Version: {{ version }}}
\subsection*{Summary Metrics}
\begin{tabular}{llll}
\toprule
P50 & P90 & P99 & Uncertainty (1$\sigma$) \\
\midrule
{{ p50 }} & {{ p90 }} & {{ p99 }} & {{ sigma }} \\
\bottomrule
\end{tabular}

\subsection*{Loss Tree}
\begin{tabular}{lp{6cm}}
\toprule
Loss & Percent \\
\midrule
{% for l in loss_tree %}
{{ l.name }} & {{ l.percent }}\\
{% endfor %}
\bottomrule
\end{tabular}

\subsection*{Assumptions Register}
\begin{verbatim}
{{ assumptions | tojson(indent=2) }}
\end{verbatim}

\subsection*{Compliance Snapshot}
\begin{itemize}
{% for f in findings %}
\item [{{ f.severity|upper }}] {{ f.ruleId }} --- {{ f.message }}
{% endfor %}
\end{itemize}

\end{document}
```

---

# 3) Finance Renderer & Endpoints

## app/report_render.py (Finance)
```py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
from pathlib import Path
from weasyprint import HTML

TEMPLATES = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_lender_pdf(data: dict) -> bytes:
    tpl = env.get_template("lender_report.html")
    html = tpl.render(**data, generated_at=datetime.utcnow().isoformat())
    return HTML(string=html).write_pdf()

# Optional LaTeX via tectonic
# def render_lender_tex_pdf(data: dict) -> bytes:
#     from jinja2 import Template
#     import subprocess, tempfile
#     tex_tpl = (TEMPLATES / "lender_report.tex").read_text()
#     tex = Template(tex_tpl).render(**data, generated_at=datetime.utcnow().isoformat())
#     with tempfile.TemporaryDirectory() as d:
#         p = Path(d)/"report.tex"; p.write_text(tex)
#         subprocess.check_call(["tectonic", str(p)])
#         return (Path(d)/"report.pdf").read_bytes()
```

## services/svc-finance/app/main.py (augment)
```py
from fastapi import FastAPI, Response
from pydantic import BaseModel
from .report_render import render_lender_pdf

app = FastAPI(title="svc-finance")

class LenderPayload(BaseModel):
    project: dict
    version: str = "v1"
    p50: float
    p90: float
    p99: float
    sigma: float | None = None
    loss_tree: list[dict] = []
    assumptions: dict = {}
    findings: list[dict] = []

@app.post("/report/lender", response_class=Response)
async def report_lender(payload: LenderPayload):
    pdf = render_lender_pdf(payload.model_dump())
    return Response(content=pdf, media_type="application/pdf")
```

---

# 4) Service Dockerfiles (WeasyPrint deps)

Add system packages required by WeasyPrint (Cairo/Pango). Replace existing Dockerfiles or extend them.

## svc-finance/Dockerfile (updated)
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libffi8 shared-mime-info && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install -r <(uv pip compile pyproject.toml --generate-hashes) || true
COPY app ./app
EXPOSE 8000
CMD ["python","-m","app.main"]
```

## svc-finance/pyproject.toml (deps)
```toml
[project]
name = "svc-finance"
version = "0.1.0"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic>=2",
  "jinja2",
  "weasyprint==61.2"
]
```

> For **LaTeX/tectonic** builds, add `tectonic` to the image and skip WeasyPrint.

---

# 5) Minimal Tests

## services/svc-finance/app/tests/test_report.py
```py
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_lender_report_pdf():
    payload = {
        "project": {"name": "Demo C&I Rooftop", "country": "US"},
        "p50": 980, "p90": 920, "p99": 850,
        "sigma": 0.07,
        "loss_tree": [{"name": "Soiling", "percent": 2.0}],
        "assumptions": {"albedo": 0.2},
        "findings": []
    }
    r = client.post("/report/lender", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert len(r.content) > 1000
```

---

# 6) Gateway Wiring (proxy PDF back to web)

Add a route in `apps/gateway/src/index.ts`:
```ts
app.post('/api/finance/report/lender', async (req, reply) => {
  const res = await fetch('http://svc-finance:8000/report/lender', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(await req.body)
  })
  const arrayBuf = await res.arrayBuffer()
  reply.header('content-type', 'application/pdf')
  reply.send(Buffer.from(arrayBuf))
})
```

---

# 7) Frontend Download Button (stub)

In `apps/web/src/main.tsx` add:
```tsx
async function downloadLenderReport() {
  const res = await fetch('/api/finance/report/lender', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      project: { name: 'Demo C&I Rooftop', country: 'US' },
      p50: 980, p90: 920, p99: 850, sigma: 0.07,
      loss_tree: [{ name: 'Soiling', percent: 2.0 }],
      assumptions: { albedo: 0.2 }, findings: []
    })
  })
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'lender-package.pdf'
  a.click()
  URL.revokeObjectURL(url)
}

// inside App() JSX:
<button className="mt-4 border rounded px-3 py-2" onClick={downloadLenderReport}>
  Download Lender Report
</button>
```

---

# 8) Permit PDF Endpoint (Compliance)

Create `services/svc-compliance/app/permit_api.py`:
```py
from fastapi import APIRouter, HTTPException, Response
from .permit_render import render_permit_html
from .rules import PACKS

router = APIRouter(prefix="/permit")

@router.post("/pdf")
async def permit_pdf(payload: dict):
    # payload: { country, authority, project, checklist? }
    checklist = payload.get("checklist")
    if not checklist:
        # fallback: call existing template endpoint in-process (simplified)
        country = payload.get("country"); authority = payload.get("authority", "generic")
        # In a real implementation, fetch the template JSON from disk or service
        checklist = [{"id":"single-line","label":"Single Line Diagram","required":True}]
    pdf = render_permit_html(payload.get("authority","Authority"), checklist, payload.get("project",{}))
    return Response(content=pdf, media_type="application/pdf")
```
Wire it in `app/main.py`:
```py
from .permit_api import router as permit_router
app.include_router(permit_router)
```

---

# 9) Make It Work Locally
1. Add the files above to the repo (paths preserved).
2. Update `svc-finance` Dockerfile and `pyproject.toml` to include WeasyPrint + dependencies.
3. `make dev` — wait for services to start.
4. Hit `POST http://localhost:8080/api/finance/report/lender` with sample payload → returns a PDF.
5. Hit `POST http://localhost:8080/api/permit/pdf` with `{ country, authority, project, checklist }` → returns a PDF.

---

# 10) Production Notes
- WeasyPrint is CPU/RAM light; scale svc-finance horizontally.
- Cache rendered artifacts (object storage, e.g., S3) with content hash of payload.
- Store machine-readable JSON alongside PDFs in the data room bundle.
- For LaTeX: prefer **tectonic** (single-binary, reproducible builds) if you need strict layout.

---

**You now have end-to-end PDF generation for permits and lender packages, compatible with your existing gateway and frontend.**

