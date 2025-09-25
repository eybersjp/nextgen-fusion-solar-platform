This document adds three major capabilities:
1) **Country‑specific tariff libraries** for ZA/AU/US with a normalized schema and seed examples
2) **Day‑ahead price forecast ingestion** service and contracts
3) **Demand‑charge optimization** (adds demand cost terms to the BESS MILP)

All pieces align with your monorepo and can be scaffolded via Trae `/implement` immediately.

---

# 0) New Services & Folders
```
services/
├─ svc-tariffs/            # tariff libraries + API
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ seed/
│  │  │  ├─ za.eskom.generic.json
│  │  │  ├─ au.generic.json
│  │  │  └─ us.generic.json
│  │  └─ tests/test_tariffs.py
└─ svc-forecasts/          # day-ahead price & irradiance adapters
   ├─ app/
   │  ├─ main.py
   │  ├─ providers/
   │  │  ├─ base.py
   │  │  └─ mock_day_ahead.py
   │  └─ tests/test_forecasts.py
```

Update `docker-compose.yml` to expose these services (ports 8107, 8108) and add gateway routes (see Section 4).

---

# 1) Tariff Library (svc-tariffs)

## app/models.py (schema)
```py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class TOUBlock(BaseModel):
    start: int  # 0-23
    end: int    # inclusive
    price: float  # price per kWh in local currency
    label: Optional[str] = None  # e.g., Peak/Off-peak

class DemandCharge(BaseModel):
    window_start: int  # hour index
    window_end: int
    price_per_kw: float  # monthly demand charge

class Tariff(BaseModel):
    id: str
    country: Literal['ZA','AU','US']
    currency: str  # 'ZAR','AUD','USD'
    timezone: str  # e.g., 'Africa/Johannesburg'
    utility: str
    sector: Literal['residential','commercial','industrial']
    tou: List[TOUBlock]
    demand: List[DemandCharge] = []
    notes: Optional[str] = None
```

## app/main.py
```py
from fastapi import FastAPI, HTTPException
from .models import Tariff
from pathlib import Path
import json

app = FastAPI(title='svc-tariffs')
BASE = Path(__file__).parent / 'seed'

def load_all():
    data = []
    for p in BASE.glob('*.json'):
        o = json.loads(p.read_text())
        data.append(Tariff(**o))
    return data

TARIFFS = load_all()

@app.get('/tariffs')
async def list_tariffs(country: str | None = None, sector: str | None = None):
    r = [t.model_dump() for t in TARIFFS if (not country or t.country==country) and (not sector or t.sector==sector)]
    return r

@app.get('/tariffs/{tariff_id}')
async def get_tariff(tariff_id: str):
    for t in TARIFFS:
        if t.id == tariff_id:
            return t
    raise HTTPException(404, 'Not found')
```

## Seed examples (illustrative placeholders — adjust with real data later)

### seed/za.eskom.generic.json
```json
{
  "id": "za-eskom-generic-ci",
  "country": "ZA",
  "currency": "ZAR",
  "timezone": "Africa/Johannesburg",
  "utility": "Eskom",
  "sector": "commercial",
  "tou": [
    {"start": 0, "end": 5, "price": 1.20, "label": "Off-Peak"},
    {"start": 6, "end": 17, "price": 2.10, "label": "Standard"},
    {"start": 18, "end": 21, "price": 3.40, "label": "Peak"},
    {"start": 22, "end": 23, "price": 2.10, "label": "Standard"}
  ],
  "demand": [ { "window_start": 6, "window_end": 21, "price_per_kw": 150.0 } ],
  "notes": "Illustrative values only."
}
```

### seed/au.generic.json
```json
{
  "id": "au-generic-ci",
  "country": "AU",
  "currency": "AUD",
  "timezone": "Australia/Sydney",
  "utility": "Generic AU Utility",
  "sector": "commercial",
  "tou": [
    {"start": 0, "end": 6, "price": 0.12, "label": "Off-Peak"},
    {"start": 7, "end": 17, "price": 0.22, "label": "Shoulder"},
    {"start": 18, "end": 21, "price": 0.35, "label": "Peak"},
    {"start": 22, "end": 23, "price": 0.22, "label": "Shoulder"}
  ],
  "demand": [ { "window_start": 12, "window_end": 21, "price_per_kw": 18.0 } ],
  "notes": "Illustrative values only."
}
```

### seed/us.generic.json
```json
{
  "id": "us-generic-ci",
  "country": "US",
  "currency": "USD",
  "timezone": "America/Los_Angeles",
  "utility": "Generic US Utility",
  "sector": "commercial",
  "tou": [
    {"start": 0, "end": 7, "price": 0.10, "label": "Off-Peak"},
    {"start": 8, "end": 16, "price": 0.20, "label": "On-Peak"},
    {"start": 17, "end": 21, "price": 0.32, "label": "Super-Peak"},
    {"start": 22, "end": 23, "price": 0.12, "label": "Off-Peak"}
  ],
  "demand": [ { "window_start": 8, "window_end": 21, "price_per_kw": 22.0 } ],
  "notes": "Illustrative values only."
}
```

## Simple tests
```py
# services/svc-tariffs/app/tests/test_tariffs.py
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_list():
    r = client.get('/tariffs?country=ZA')
    assert r.status_code == 200
    assert any(t['country']=='ZA' for t in r.json())
```

---

# 2) Day‑Ahead Forecast Ingestion (svc-forecasts)

The service provides a normalized API for **day‑ahead price** and **irradiance** forecasts. Providers are pluggable via adapters; start with a mock provider and swap for real ones later.

## app/providers/base.py
```py
from typing import List, Protocol

class PricePoint(dict):
    # keys: ts (ISO), price (float), currency (str)
    pass

class IrrPoint(dict):
    # keys: ts (ISO), ghi (W/m2), tempC (float)
    pass

class PriceProvider(Protocol):
    def day_ahead(self, zone: str) -> List[PricePoint]: ...

class IrrProvider(Protocol):
    def day_ahead(self, lat: float, lng: float) -> List[IrrPoint]: ...
```

## app/providers/mock_day_ahead.py
```py
from datetime import datetime, timedelta, timezone
import random
from .base import PricePoint, IrrPoint

def _hours(start, n=24):
    return [(start + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0) for i in range(n)]

def price_series(zone: str, currency: str='USD'):
    now = datetime.now(timezone.utc)
    base = 0.20
    out = []
    for i, ts in enumerate(_hours(now)):
        p = base + 0.1*abs((i-18)/18)  # peak in evening
        out.append(PricePoint(ts=ts.isoformat(), price=round(p, 4), currency=currency))
    return out

def irr_series(lat: float, lng: float):
    now = datetime.now(timezone.utc)
    out = []
    for i, ts in enumerate(_hours(now)):
        ghi = max(0, 900 * (1 - abs(i-12)/12))
        temp = 25 + 8 * (1 - abs(i-15)/15)
        out.append(IrrPoint(ts=ts.isoformat(), ghi=round(ghi, 1), tempC=round(temp, 1)))
    return out
```

## app/main.py
```py
from fastapi import FastAPI
from .providers import mock_day_ahead as provider

app = FastAPI(title='svc-forecasts')

@app.get('/price/dayahead')
async def price_dayahead(zone: str = 'default', currency: str = 'USD'):
    return provider.price_series(zone, currency)

@app.get('/irradiance/dayahead')
async def irr_dayahead(lat: float, lng: float):
    return provider.irr_series(lat, lng)
```

## tests
```py
# services/svc-forecasts/app/tests/test_forecasts.py
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_price():
    r = client.get('/price/dayahead?zone=us-ca&currency=USD')
    assert r.status_code == 200
    assert len(r.json()) == 24
```

---

# 3) Demand‑Charge Optimization (extend BESS MILP)

Add a new endpoint that **minimizes energy cost + demand charge** using a linear formulation. We introduce a variable `peak_kw` and enforce `grid_import[h] ≤ peak_kw` over the demand window.

**Path:** `services/svc-bess/app/main.py`

```py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import numpy as np
from ortools.linear_solver import pywraplp

app = FastAPI(title='svc-bess')

class DemandCfg(BaseModel):
    window_start: int
    window_end: int
    price_per_kw: float

class CostRequest(BaseModel):
    load_kwh: List[float]
    pv_kwh: List[float]
    price_per_kwh: List[float]  # 24h vector from tariff or forecast
    demand: DemandCfg | None = None
    capacity_kwh: float
    power_kw: float
    roundtrip_eff: float = 0.92
    soc0: float = 0.5
    soc_min: float = 0.1
    soc_max: float = 0.9

@app.post('/optimize_cost_dc')
async def optimize_cost_dc(req: CostRequest):
    H = 24
    price = np.array(req.price_per_kwh)
    solver = pywraplp.Solver.CreateSolver('GLOP')
    ch = [solver.NumVar(0.0, req.power_kw, f'ch_{h}') for h in range(H)]
    dis = [solver.NumVar(0.0, req.power_kw, f'dis_{h}') for h in range(H)]
    soc = [solver.NumVar(req.soc_min*req.capacity_kwh, req.soc_max*req.capacity_kwh, f'soc_{h}') for h in range(H)]
    grid = [solver.NumVar(-1e6, 1e6, f'grid_{h}') for h in range(H)]  # import (+) or export (-)

    eta = req.roundtrip_eff
    net = np.array(req.load_kwh) - np.array(req.pv_kwh)
    for h in range(H):
        # balance: grid = net + ch - dis
        solver.Add(grid[h] == net[h] + ch[h] - dis[h])
        # soc dynamics
        if h == 0:
            solver.Add(soc[h] == req.soc0*req.capacity_kwh + eta*ch[h] - dis[h])
        else:
            solver.Add(soc[h] == soc[h-1] + eta*ch[h] - dis[h])

    # Demand charge variable
    dc_cost = 0
    if req.demand:
        peak = solver.NumVar(0.0, req.power_kw + max(net.max(), 0), 'peak_kw')
        for h in range(req.demand.window_start, req.demand.window_end+1):
            # import only contributes; ensure peak >= import portion
            imp = solver.NumVar(0.0, 1e6, f'imp_{h}')
            # imp >= grid[h] and imp >= 0
            solver.Add(imp >= grid[h])
            solver.Add(imp >= 0)
            solver.Add(peak >= imp)
        dc_cost = peak * req.demand.price_per_kw

    energy_cost = solver.Sum([price[h] * grid[h] for h in range(H)])
    solver.Minimize(energy_cost + dc_cost)

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"error": "No feasible solution"}

    return {
        'charge': [ch[h].solution_value() for h in range(H)],
        'discharge': [dis[h].solution_value() for h in range(H)],
        'soc': [soc[h].solution_value() for h in range(H)],
        'grid_import_kwh': [max(0.0, grid[h].solution_value()) for h in range(H)],
        'grid_export_kwh': [max(0.0, -grid[h].solution_value()) for h in range(H)],
        'objective_cost': solver.Objective().Value()
    }
```

> **Tip:** Use forecast prices from `svc-forecasts` or library prices from `svc-tariffs` to create the `price_per_kwh` vector.

---

# 4) Gateway Wiring

## apps/gateway/src/index.ts (append)
```ts
// Tariffs
app.get('/api/tariffs', async (req, reply) => {
  const qs = new URLSearchParams((req.query as any) || {}).toString()
  const res = await fetch(`http://svc-tariffs:8000/tariffs?${qs}`)
  reply.send(await res.json())
})

// Forecasts
app.get('/api/forecasts/price/dayahead', async (req, reply) => {
  const qs = new URLSearchParams((req.query as any) || {}).toString()
  const res = await fetch(`http://svc-forecasts:8000/price/dayahead?${qs}`)
  reply.send(await res.json())
})

// BESS demand-charge optimization
app.post('/api/bess/optimize_cost_dc', async (req, reply) => {
  const res = await fetch('http://svc-bess:8000/optimize_cost_dc', { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(await req.body) })
  reply.send(await res.json())
})
```

---

# 5) Frontend Examples

```tsx
// Build a price vector from library tariff
async function priceFromTariff(tariffId: string) {
  const t = await fetch(`/api/tariffs/${tariffId}`).then(r=>r.json())
  const v = Array(24).fill(0)
  for (const b of t.tou) { for (let h=b.start; h<=b.end; h++) v[h] = b.price }
  return v
}

async function runCostWithDemandCharge() {
  const price = await priceFromTariff('za-eskom-generic-ci')
  const payload = {
    load_kwh: Array(24).fill(30),
    pv_kwh: Array(24).fill(10),
    price_per_kwh: price,
    demand: { window_start: 6, window_end: 21, price_per_kw: 150 },
    capacity_kwh: 100, power_kw: 50, roundtrip_eff: 0.92, soc0: 0.5
  }
  const r = await fetch('/api/bess/optimize_cost_dc', { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(payload) })
  console.log(await r.json())
}
```

---

# 6) Compose & CI

## docker-compose.yml additions
```yaml
  svc-tariffs:
    build: ./services/svc-tariffs
    env_file: .env
    ports: ["8107:8000"]
  svc-forecasts:
    build: ./services/svc-forecasts
    env_file: .env
    ports: ["8108:8000"]
```

## Minimal pyproject.toml
```toml
# services/svc-tariffs/pyproject.toml
[project]
name = "svc-tariffs"
version = "0.1.0"
dependencies = ["fastapi","uvicorn[standard]","pydantic>=2"]

# services/svc-forecasts/pyproject.toml
[project]
name = "svc-forecasts"
version = "0.1.0"
dependencies = ["fastapi","uvicorn[standard]"]
```

Add tests to CI (the existing `ci.yml` will discover them if you keep the same structure).

---

# 7) Next Steps
- Replace mock forecast provider with real market APIs where available.
- Expand tariff seeds with authoritative datasets; version tariffs with `effective_from` dates.
- Extend BESS model to include **export tariffs/credits**, **demand ratchets**, **critical peak pricing**, and **grid limits**.
- Persist tariff & forecast selections with project records and surface in lender packages.

**This completes tariff libraries, forecast ingestion, and demand‑charge optimization.**

