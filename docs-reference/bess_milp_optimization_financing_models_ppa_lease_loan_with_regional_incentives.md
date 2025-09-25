This document upgrades the prior stubs with:
1) **BESS MILP optimal dispatch** using OR‑Tools
2) **Sales finance models** for **PPA / Operating Lease / Loan (Amortizing)**
3) **Regional incentives** stubs for **ZA (Section 12B), AU (STCs/LGCs), US (ITC & MACRS)**
4) API contracts, tests, and gateway wiring

All code is drop‑in compatible with your existing monorepo layout.

---

# 0) Dependencies

### `services/svc-bess/pyproject.toml`
```toml
[project]
name = "svc-bess"
version = "0.2.0"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic>=2",
  "numpy",
  "ortools>=9.10"
]
```

### `services/svc-sales/pyproject.toml`
```toml
[project]
name = "svc-sales"
version = "0.2.0"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic>=2"
]
```

Update `docker-compose.yml` (already present for services) — no extra system libs required.

---

# 1) BESS MILP Optimal Dispatch (OR‑Tools)
**Path:** `services/svc-bess/app/main.py`

Replace the prior heuristic endpoint (or keep both under different paths). This model maximizes daily arbitrage revenue with power/energy limits, SOC bounds, and round‑trip efficiency.

```py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import numpy as np
from ortools.linear_solver import pywraplp

app = FastAPI(title="svc-bess")

class TariffPeriod(BaseModel):
    start: int
    end: int
    price: float

class DispatchRequest(BaseModel):
    load_kwh: List[float]  # 24h
    pv_kwh: List[float]    # 24h
    tariff: List[TariffPeriod]
    capacity_kwh: float
    power_kw: float
    roundtrip_eff: float = 0.92
    soc0: float = 0.5
    soc_min: float = 0.1
    soc_max: float = 0.9
    must_end_at_soc0: bool = True

@app.post("/optimize_milp")
async def optimize_milp(req: DispatchRequest):
    H = 24
    net = np.array(req.load_kwh) - np.array(req.pv_kwh)  # + means import needed
    price = np.zeros(H)
    for p in req.tariff:
        price[p.start:p.end+1] = p.price

    solver = pywraplp.Solver.CreateSolver('GLOP')  # LP sufficient for linear eff approximation
    if not solver:
        return {"error": "No solver available"}

    # Variables per hour
    ch = [solver.NumVar(0.0, req.power_kw, f"ch_{h}") for h in range(H)]
    dis = [solver.NumVar(0.0, req.power_kw, f"dis_{h}") for h in range(H)]
    soc = [solver.NumVar(req.soc_min*req.capacity_kwh, req.soc_max*req.capacity_kwh, f"soc_{h}") for h in range(H)]

    # SOC dynamics: soc[h] = soc[h-1] + eta*ch[h] - dis[h]
    eta = req.roundtrip_eff
    for h in range(H):
        if h == 0:
            solver.Add(soc[h] == req.soc0*req.capacity_kwh + eta*ch[h] - dis[h])
        else:
            solver.Add(soc[h] == soc[h-1] + eta*ch[h] - dis[h])

    # Optional terminal SOC constraint
    if req.must_end_at_soc0:
        solver.Add(soc[H-1] == req.soc0*req.capacity_kwh)

    # Objective: maximize arbitrage revenue (sell at dis*price, buy at ch*price)
    revenue = solver.Sum([dis[h]*price[h] - ch[h]*price[h] for h in range(H)])
    solver.Maximize(revenue)

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {"error": "No feasible solution"}

    soc_series = [soc[h].solution_value() for h in range(H)]
    ch_series = [ch[h].solution_value() for h in range(H)]
    dis_series = [dis[h].solution_value() for h in range(H)]
    rev = solver.Objective().Value()

    return {
        "soc": soc_series,
        "charge": ch_series,
        "discharge": dis_series,
        "revenue_day": rev,
        "prices": list(price),
        "net_load": list(net)
    }
```

> Note: This LP ignores simultaneous charge/discharge prevention; if desired, add binary vars with CBC or CP‑SAT. For most pricing cases, LP performs well.

### Gateway route
```ts
// apps/gateway/src/index.ts (append)
app.post('/api/bess/optimize_milp', async (req, reply) => {
  const res = await fetch('http://svc-bess:8000/optimize_milp', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(await req.body)
  })
  reply.send(await res.json())
})
```

### Basic test
```py
# services/svc-bess/app/tests/test_dispatch_milp.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_milp():
    payload = {
      "load_kwh": [30]*24,
      "pv_kwh": [10]*24,
      "tariff": [{"start":0,"end":7,"price":0.10},{"start":8,"end":17,"price":0.20},{"start":18,"end":23,"price":0.35}],
      "capacity_kwh": 100,
      "power_kw": 50,
      "roundtrip_eff": 0.92,
      "soc0": 0.5
    }
    r = client.post('/optimize_milp', json=payload)
    assert r.status_code == 200
    assert 'revenue_day' in r.json()
```

---

# 2) Sales Finance Models: PPA, Lease, Loan
**Path:** `services/svc-sales/app/finance.py`, augment `main.py`

## A) Finance Helpers
```py
# services/svc-sales/app/finance.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class Cashflow:
    year: int
    amount: float

# Level payment for amortizing loan
def loan_payment(principal: float, rate: float, years: int) -> float:
    r = rate
    n = years
    if r == 0: return principal / n
    return principal * (r * (1 + r)**n) / ((1 + r)**n - 1)

# PPA price path (escalator)
def ppa_price_series(p0: float, escalator: float, years: int) -> List[float]:
    return [p0 * ((1 + escalator)**y) for y in range(years)]

# Simple NPV
def npv(rate: float, cfs: List[Cashflow]) -> float:
    return sum(cf.amount / ((1 + rate) ** cf.year) for cf in cfs)
```

## B) Extend Service Endpoint
```py
# services/svc-sales/app/main.py (append)
from pydantic import BaseModel
from .finance import loan_payment, ppa_price_series, npv, Cashflow

class PPAModel(BaseModel):
    ppa_cents_per_kwh: float
    escalator_pct: float = 2.0

class LeaseModel(BaseModel):
    annual_rent_pct_of_capex: float  # e.g., 11% of CAPEX per year
    escalator_pct: float = 0.0

class LoanModel(BaseModel):
    rate: float  # e.g., 0.08
    years: int
    down_pct: float = 0.0

class FinanceOptions(BaseModel):
    type: str  # 'cash' | 'ppa' | 'lease' | 'loan'
    ppa: PPAModel | None = None
    lease: LeaseModel | None = None
    loan: LoanModel | None = None

class ProposalRequestFinance(ProposalRequest):
    finance: FinanceOptions

@app.post('/proposal/finance')
async def proposal_fin(req: ProposalRequestFinance):
    # reuse price calculation from /proposal
    w = req.pricing.system_kw * 1000
    capex = w * (req.pricing.module_cost_per_w + req.pricing.inverter_cost_per_w + req.pricing.bos_cost_per_w + req.pricing.labor_cost_per_w)
    overhead = capex * (req.pricing.overhead_pct/100)
    net_cost = (capex + overhead) - sum([i.get('value_per_w',0)*w for i in (req.pricing.incentives or [])])
    price = net_cost * (1 + req.pricing.margin_pct/100)

    annual_kwh = req.yield_kwh_per_kwp * req.pricing.system_kw
    # tariff savings is not used for PPA revenue to seller; instead, buyer pays PPA price

    years = req.years
    discount = 0.08

    if req.finance.type == 'cash':
        cfs = [Cashflow(0, -price)] + [Cashflow(y, annual_kwh * req.tariff.flat_rate * ((1 + req.escalation_pct/100) ** (y-1))) for y in range(1, years+1)]
        return {"mode": "cash", "price": price, "npv": npv(discount, cfs)}

    if req.finance.type == 'ppa' and req.finance.ppa:
        cents = req.finance.ppa.ppa_cents_per_kwh
        p0 = cents / 100.0
        series = ppa_price_series(p0, req.finance.ppa.escalator_pct/100, years)
        # Seller revenue
        rev = [annual_kwh * series[y-1] for y in range(1, years+1)]
        cfs = [Cashflow(0, -price)] + [Cashflow(y, rev[y-1]) for y in range(1, years+1)]
        return {"mode": "ppa", "ppa_series": series, "seller_npv": npv(discount, cfs)}

    if req.finance.type == 'lease' and req.finance.lease:
        rent0 = req.finance.lease.annual_rent_pct_of_capex/100 * price
        series = [rent0 * ((1 + req.finance.lease.escalator_pct/100) ** (y-1)) for y in range(1, years+1)]
        cfs = [Cashflow(0, -price)] + [Cashflow(y, s) for y, s in enumerate(series, start=1)]
        return {"mode": "lease", "lease_series": series, "lessor_npv": npv(discount, cfs)}

    if req.finance.type == 'loan' and req.finance.loan:
        down = price * (req.finance.loan.down_pct/100)
        principal = price - down
        pay = loan_payment(principal, req.finance.loan.rate, req.finance.loan.years)
        series = [pay for _ in range(req.finance.loan.years)]
        return {"mode": "loan", "down_payment": down, "annual_payment": pay, "schedule": series}

    return {"error": "Invalid finance option"}
```

### Test (short)
```py
# services/svc-sales/app/tests/test_finance_modes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def base_payload():
    return {
      "site": {"country":"US"}, "design": {},
      "pricing": {"system_kw": 100, "module_cost_per_w": 0.28, "inverter_cost_per_w": 0.09},
      "tariff": {"flat_rate": 0.18}, "yield_kwh_per_kwp": 1200,
      "finance": {"type": "ppa", "ppa": {"ppa_cents_per_kwh": 12, "escalator_pct": 2}}
    }

def test_ppa():
    r = client.post('/proposal/finance', json=base_payload())
    assert r.status_code == 200
    assert 'seller_npv' in r.json()
```

---

# 3) Regional Incentives (ZA/AU/US)
**Path:** `services/svc-sales/app/incentives.py` and integrate with `/proposal` & `/proposal/finance`.

These are **simplified calculation stubs** to be replaced with authoritative tables later. Keep the API contracts stable.

```py
# services/svc-sales/app/incentives.py
from __future__ import annotations

def za_section_12b_deduction(capex: float, year: int) -> float:
    """Section 12B accelerated depreciation (illustrative): 100% in year 1 for PV.
    Return tax shield in currency for the given year, assuming corporate tax 27%.
    """
    corp_tax = 0.27
    if year == 1:
        return capex * corp_tax
    return 0.0


def au_stc_rebate(system_kw: float, stc_price_aud: float = 35.0, deeming_years: int = 10) -> float:
    """Simplified STC estimate: STCs ~ system_kW * deeming_years * zone_factor.
    Use zone_factor=1.0 placeholder.
    """
    zone_factor = 1.0
    stcs = system_kw * deeming_years * zone_factor
    return stcs * stc_price_aud


def au_lgc_revenue(annual_mwh: float, lgc_price_aud: float = 40.0) -> float:
    return annual_mwh * lgc_price_aud


def us_itc_credit(capex: float, itc_pct: float = 30.0) -> float:
    return capex * (itc_pct/100)


def us_macrs_tax_shield(capex_net_itc: float, year: int) -> float:
    """5‑year MACRS schedule stub (not bonus): [20, 32, 19.2, 11.52, 11.52, 5.76]% * 21% tax.
    """
    rates = [0.20, 0.32, 0.192, 0.1152, 0.1152, 0.0576]
    corp_tax = 0.21
    if 1 <= year <= 6:
        return capex_net_itc * rates[year-1] * corp_tax
    return 0.0
```

## Integrate incentives into `/proposal` price calc
```py
# services/svc-sales/app/main.py (inside /proposal and /proposal/finance before price)
from .incentives import za_section_12b_deduction, au_stc_rebate, us_itc_credit

# ... after computing capex + overhead
country = (req.site or {}).get('country', 'US')
rebate = 0.0
if country == 'AU':
    rebate += au_stc_rebate(req.pricing.system_kw)
elif country == 'US':
    rebate += us_itc_credit(capex + overhead)
# ZA 12B is a tax shield, not an upfront rebate, so keep it in cashflows if modeling taxes.

net_cost = (capex + overhead) - rebate - sum([i.get('value_per_w',0)*w for i in (req.pricing.incentives or [])])
price = net_cost * (1 + req.pricing.margin_pct/100)
```

> For **ZA Section 12B** and **US MACRS**, integrate into cashflow tax shields under `/proposal/finance` when you extend tax modeling. The stubs above show how to compute the single‑year shields.

---

# 4) Frontend Buttons (optional)
```tsx
// apps/web/src/main.tsx (within App)
<button className="mt-2 border rounded px-3 py-2" onClick={async () => {
  const r = await fetch('/api/bess/optimize_milp', { method: 'POST', headers: {'content-type':'application/json'}, body: JSON.stringify({
    load_kwh: Array(24).fill(30), pv_kwh: Array(24).fill(10),
    tariff: [{start:0,end:7,price:0.1},{start:8,end:17,price:0.2},{start:18,end:23,price:0.35}],
    capacity_kwh: 100, power_kw: 50, roundtrip_eff: 0.92, soc0: 0.5 }) });
  console.log(await r.json())
}}>Optimal BESS Dispatch</button>

<button className="mt-2 ml-2 border rounded px-3 py-2" onClick={async () => {
  const payload = {
    site: { country: 'AU' }, design: {},
    pricing: { system_kw: 100, module_cost_per_w: 0.28, inverter_cost_per_w: 0.09 },
    tariff: { flat_rate: 0.22 }, yield_kwh_per_kwp: 1400,
    finance: { type: 'ppa', ppa: { ppa_cents_per_kwh: 12, escalator_pct: 2 } }
  }
  const r = await fetch('/api/sales/proposal/finance', { method: 'POST', headers: {'content-type':'application/json'}, body: JSON.stringify(payload) })
  console.log(await r.json())
}}>Finance Proposal (PPA)</button>
```

---

# 5) Notes & Extensions
- Add binary variables to prevent simultaneous charge/discharge and enable demand‑charge management; switch solver to **CBC/CP‑SAT**.
- Model calendar‑time horizons (8760h) by chunking into day‑sized MILPs; stitch SOC terminal constraints between days.
- Replace incentive stubs with authoritative data sources; add currency conversion.
- Feed **Monte Carlo** annual yield distributions into revenue/cashflow models to produce **P50/P90** NPVs.

**This completes the optimal dispatch and finance modes with regional incentives, ready for Trae `/implement` and local run.**

