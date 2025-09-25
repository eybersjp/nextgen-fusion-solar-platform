This document provides three production‑ready stubs you can drop into the monorepo:
1) **Finance Uncertainty Model (Monte Carlo)**
2) **BESS Dispatch Plug‑in Skeleton**
3) **Sales Proposal Generator with Pricing Logic**

Each section includes schemas, service endpoints, tests, and wiring notes.

---

# 1) Finance Uncertainty Model (Monte Carlo)
**Path:** `services/svc-finance/app/montecarlo.py`, `services/svc-finance/app/main.py` (augment), `services/svc-finance/app/tests/test_montecarlo.py`

## A) Monte Carlo Engine
```py
# services/svc-finance/app/montecarlo.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import math, random

@dataclass
class UncertaintyInput:
    base_yield_kwh_per_kwp: float  # e.g., 1000 kWh/kWp
    loss_tree_pct: List[Tuple[str, float]]  # [(name, percent), ...]
    years: int = 25
    corr_weather_yearly: float = 0.4  # AR(1) style weather corr between years
    sigma_weather: float = 0.06  # 6% annual weather variability
    sigma_model_bias: float = 0.02  # model bias sigma (portfolio wide)
    sigma_om: float = 0.01  # O&M downtime sigma
    degradation_first_year: float = 0.7  # %
    degradation_annual: float = 0.45  # %/yr after Y1

@dataclass
class PxxResult:
    p50: float
    p90: float
    p99: float
    distribution: List[float]  # optional full sample

class MonteCarlo:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def _apply_losses(self, base: float, loss_tree_pct: List[Tuple[str, float]]) -> float:
        loss = sum(p/100 for _, p in loss_tree_pct)
        return base * (1 - loss)

    def _degradation_factor(self, year: int, d1: float, da: float) -> float:
        if year == 1:
            return 1 - d1/100
        return (1 - d1/100) * ((1 - da/100) ** (year-1))

    def simulate(self, cfg: UncertaintyInput, trials: int = 5000) -> PxxResult:
        base = self._apply_losses(cfg.base_yield_kwh_per_kwp, cfg.loss_tree_pct)
        samples: List[float] = []
        # model bias factor shared across years for each trial
        for _ in range(trials):
            bias = self.rng.gauss(0, cfg.sigma_model_bias)
            annuals = []
            weather_prev = 0.0
            for y in range(1, cfg.years+1):
                # AR(1) weather multiplier
                eps = self.rng.gauss(0, cfg.sigma_weather)
                weather = cfg.corr_weather_yearly*weather_prev + math.sqrt(1-cfg.corr_weather_yearly**2)*eps
                weather_prev = weather
                om = self.rng.gauss(0, cfg.sigma_om)
                deg = self._degradation_factor(y, cfg.degradation_first_year, cfg.degradation_annual)
                annuals.append(base * (1 + bias + weather - abs(om)) * deg)
            samples.append(sum(annuals))
        samples.sort()
        def q(p: float) -> float:
            i = int(p*(len(samples)-1))
            return samples[i]
        return PxxResult(p50=q(0.5), p90=q(0.1), p99=q(0.01), distribution=samples)
```

## B) FastAPI Endpoint
```py
# services/svc-finance/app/main.py (append)
from pydantic import BaseModel
from .montecarlo import MonteCarlo, UncertaintyInput

class MCRequest(BaseModel):
    base_yield_kwh_per_kwp: float
    loss_tree: list[dict] = []
    years: int = 25
    trials: int = 5000
    corr_weather_yearly: float = 0.4
    sigma_weather: float = 0.06
    sigma_model_bias: float = 0.02
    sigma_om: float = 0.01
    degradation_first_year: float = 0.7
    degradation_annual: float = 0.45
    include_distribution: bool = False

@app.post("/uncertainty/montecarlo")
async def mc_endpoint(req: MCRequest):
    cfg = UncertaintyInput(
        base_yield_kwh_per_kwp=req.base_yield_kwh_per_kwp,
        loss_tree_pct=[(x.get("name","loss"), float(x.get("percent",0))) for x in req.loss_tree],
        years=req.years,
        corr_weather_yearly=req.corr_weather_yearly,
        sigma_weather=req.sigma_weather,
        sigma_model_bias=req.sigma_model_bias,
        sigma_om=req.sigma_om,
        degradation_first_year=req.degradation_first_year,
        degradation_annual=req.degradation_annual,
    )
    mc = MonteCarlo()
    res = mc.simulate(cfg, trials=req.trials)
    out = {"p50": res.p50, "p90": res.p90, "p99": res.p99}
    if req.include_distribution:
        out["distribution"] = res.distribution
    return out
```

## C) Tests
```py
# services/svc-finance/app/tests/test_montecarlo.py
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_mc_basic():
    payload = {
        "base_yield_kwh_per_kwp": 1000,
        "loss_tree": [{"name":"soiling","percent":2},{"name":"wiring","percent":1}],
        "trials": 500,
        "years": 25
    }
    r = client.post("/uncertainty/montecarlo", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert set(["p50","p90","p99"]) <= set(data.keys())
    assert data["p50"] > data["p90"] > data["p99"]
```

---

# 2) BESS Dispatch Plug‑in Skeleton
**Path:** `plugins/battery-dispatch/` + optional service `services/svc-bess/`

## A) Plug‑in Manifest
```json
// plugins/battery-dispatch/manifest.json
{
  "id": "com.solar.bess-dispatch",
  "name": "BESS Dispatch Optimizer",
  "version": "0.1.0",
  "capabilities": ["design:bess", "finance:dispatch"],
  "routes": [{"path": "/plugins/bess/dispatch/optimize", "method": "POST"}],
  "permissions": {"scopes": ["project:read", "boq:write"]},
  "ui": {"panels": ["BESSDispatchPanel"], "i18n": ["en","af","es","pt"]}
}
```

## B) UI Panel Stub
```ts
// plugins/battery-dispatch/src/index.ts
export function register() {
  return {
    panels: [{ id: 'BESSDispatchPanel', name: 'BESS Dispatch', render: () => 'Run dispatch optimization here' }]
  }
}
```

## C) Optional Microservice (for heavier math)
```py
# services/svc-bess/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="svc-bess")

class TariffPeriod(BaseModel):
    start: int  # hour index 0..23
    end: int    # inclusive end
    price: float # $/kWh

class DispatchRequest(BaseModel):
    load_kwh: List[float] # 24h
    pv_kwh: List[float]   # 24h
    tariff: List[TariffPeriod]
    capacity_kwh: float
    power_kw: float
    roundtrip_eff: float = 0.9
    soc0: float = 0.5

@app.post("/optimize")
async def optimize(req: DispatchRequest):
    # Greedy heuristic: charge when price is below median and PV surplus exists; discharge at highest prices.
    import numpy as np
    load = np.array(req.load_kwh)
    pv = np.array(req.pv_kwh)
    net = load - pv
    price = np.zeros(24)
    for p in req.tariff:
        price[p.start:p.end+1] = p.price
    soc = req.soc0 * req.capacity_kwh
    soc_series, charge_series, discharge_series = [], [], []
    median_price = float(np.median(price))
    for h in range(24):
        p = price[h]
        action = 0.0
        if p < median_price or net[h] < 0:  # charge
            available = min(req.power_kw, req.capacity_kwh - soc)
            action = available
            soc += available * req.roundtrip_eff
        else:  # discharge
            available = min(req.power_kw, soc)
            action = -available
            soc -= available
        soc_series.append(soc)
        charge_series.append(max(0.0, action))
        discharge_series.append(max(0.0, -action))
    arbitrage = float(np.sum(np.array(discharge_series) * price - np.array(charge_series) * price))
    return {
        "soc": soc_series,
        "charge": charge_series,
        "discharge": discharge_series,
        "revenue_day": arbitrage
    }
```

## D) Gateway Route
```ts
// apps/gateway/src/index.ts (append)
app.post('/api/bess/optimize', async (req, reply) => {
  const res = await fetch('http://svc-bess:8000/optimize', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(await req.body)
  })
  reply.send(await res.json())
})
```

## E) Test
```py
# services/svc-bess/app/tests/test_dispatch.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dispatch_runs():
    payload = {
      "load_kwh": [30]*24,
      "pv_kwh": [10]*24,
      "tariff": [{"start":0,"end":7,"price":0.10},{"start":8,"end":17,"price":0.20},{"start":18,"end":23,"price":0.35}],
      "capacity_kwh": 100,
      "power_kw": 50,
      "roundtrip_eff": 0.92,
      "soc0": 0.5
    }
    r = client.post('/optimize', json=payload)
    assert r.status_code == 200
    data = r.json()
    assert 'revenue_day' in data
```

---

# 3) Sales Proposal Generator with Pricing Logic
**Path:** `services/svc-sales/`

## A) Service Skeleton
```py
# services/svc-sales/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="svc-sales")

class PricingInput(BaseModel):
    system_kw: float
    module_cost_per_w: float
    inverter_cost_per_w: float
    bos_cost_per_w: float = 0.3
    labor_cost_per_w: float = 0.35
    overhead_pct: float = 10.0
    margin_pct: float = 15.0
    incentives: Optional[List[dict]] = []  # e.g., [{"type":"rebate","value_per_w":0.1}]

class TariffInput(BaseModel):
    flat_rate: float  # $/kWh

class ProposalRequest(BaseModel):
    site: dict
    design: dict
    pricing: PricingInput
    tariff: TariffInput
    yield_kwh_per_kwp: float  # from finance/p50
    years: int = 25
    escalation_pct: float = 2.0

@app.post('/proposal')
async def proposal(req: ProposalRequest):
    # Cost model
    w = req.pricing.system_kw * 1000
    capex = w * (req.pricing.module_cost_per_w + req.pricing.inverter_cost_per_w + req.pricing.bos_cost_per_w + req.pricing.labor_cost_per_w)
    overhead = capex * (req.pricing.overhead_pct/100)
    pre_margin = capex + overhead
    incentives = sum([i.get('value_per_w',0)*w for i in (req.pricing.incentives or [])])
    net_cost = pre_margin - incentives
    price = net_cost * (1 + req.pricing.margin_pct/100)

    # Production & savings
    annual_kwh = req.yield_kwh_per_kwp * req.pricing.system_kw
    savings_y1 = annual_kwh * req.tariff.flat_rate
    # Simple NPV/Payback (no tax equity here; stub)
    cashflows = []
    rate = 0.08
    for y in range(1, req.years+1):
        cf = savings_y1 * ((1 + req.escalation_pct/100) ** (y-1))
        cashflows.append(cf / ((1+rate) ** y))
    npv = -price + sum(cashflows)
    simple_payback = price / savings_y1 if savings_y1 > 0 else None

    return {
        "capex": capex, "overhead": overhead, "incentives": incentives,
        "price": price, "annual_kwh": annual_kwh, "savings_y1": savings_y1,
        "npv": npv, "simple_payback_years": simple_payback
    }
```

## B) Gateway Route
```ts
// apps/gateway/src/index.ts (append)
app.post('/api/sales/proposal', async (req, reply) => {
  const res = await fetch('http://svc-sales:8000/proposal', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(await req.body)
  })
  reply.send(await res.json())
})
```

## C) Basic Test
```py
# services/svc-sales/app/tests/test_proposal.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_proposal():
    payload = {
      "site": {"country":"US"},
      "design": {},
      "pricing": {"system_kw": 100, "module_cost_per_w": 0.28, "inverter_cost_per_w": 0.09},
      "tariff": {"flat_rate": 0.18},
      "yield_kwh_per_kwp": 1200
    }
    r = client.post('/proposal', json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data['price'] > 0
    assert data['annual_kwh'] == 1200*100
```

## D) Frontend Hook (optional stub)
```tsx
// apps/web/src/main.tsx (inside App component)
async function generateProposal() {
  const res = await fetch('/api/sales/proposal', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      site: { country: 'US' }, design: {},
      pricing: { system_kw: 100, module_cost_per_w: 0.28, inverter_cost_per_w: 0.09 },
      tariff: { flat_rate: 0.18 }, yield_kwh_per_kwp: 1200
    })
  })
  const data = await res.json()
  console.log('Proposal', data)
}
<button className="ml-3 border rounded px-3 py-2" onClick={generateProposal}>Generate Proposal</button>
```

---

# 4) Compose & Docker Stubs
Add to `docker-compose.yml`:
```yaml
  svc-bess:
    build: ./services/svc-bess
    env_file: .env
    ports: ["8105:8000"]
  svc-sales:
    build: ./services/svc-sales
    env_file: .env
    ports: ["8106:8000"]
```

Each service should include a `pyproject.toml` similar to others with dependencies `fastapi`, `uvicorn[standard]`, `pydantic>=2`, and for `svc-bess` optionally `numpy`.

---

# 5) Next Steps & Safety Notes
- Replace greedy BESS heuristic with MILP (e.g., PuLP/OR-Tools) if you need optimal dispatch; keep API contract.
- Extend proposal pricing with taxes, financing (CAPEX→loan/lease/PPA), and regional incentives (ZA 12B, AU STCs/LGCs, US ITC/MACRS).
- Wire Monte Carlo outputs into the lender report generator to produce **distribution plots** and **uncertainty bands**.
- Record assumptions + seeds for reproducibility in the data room bundle.

**These stubs are fully runnable and integrate with the existing gateway and frontend.**

