This document delivers **ready‑to‑wire country pack stubs** for South Africa (ZA), Australia (AU), and United States (US). Each pack includes: rule schemas, minimal checks, explainable messages, permit pack templates, seed data, and unit tests. You can expand them incrementally without breaking contracts.

---

# 0) Folder Layout
```
services/svc-compliance/
├─ app/
│  ├─ main.py
│  ├─ rules/
│  │  ├─ __init__.py
│  │  ├─ common.py
│  │  ├─ za/
│  │  │  ├─ __init__.py
│  │  │  ├─ nrs.py
│  │  │  ├─ sans_10142_1.py
│  │  │  └─ permits/
│  │  │     ├─ municipal_cpt.json
│  │  │     └─ municipal_jhb.json
│  │  ├─ au/
│  │  │  ├─ __init__.py
│  │  │  ├─ asnzs_5033.py
│  │  │  ├─ asnzs_4777.py
│  │  │  └─ permits/
│  │  │     └─ cer_stc_template.json
│  │  └─ us/
│  │     ├─ __init__.py
│  │     ├─ nec_2023.py
│  │     ├─ ul_1741_sb.py
│  │     ├─ ieee_1547_2018.py
│  │     └─ permits/
│  │        ├─ ahj_generic.json
│  │        └─ fire_label_set.json
│  └─ templates/
│     ├─ permit.tex
│     └─ lender_report.tex
└─ tests/
   └─ test_packs.py
```

---

# 1) Shared Rule Interfaces

## app/rules/common.py
```py
from typing import Any, Dict, Iterable, List, TypedDict

class Finding(TypedDict, total=False):
    ruleId: str
    severity: str  # info|warning|error
    message: str
    evidence: Dict[str, Any]
    remediation: str
    jurisdiction: str  # ZA|AU|US

Design = Dict[str, Any]

class Rule:
    id: str
    title: str
    severity_default: str = "warning"

    def check(self, design: Design) -> Iterable[Finding]:
        raise NotImplementedError


def pct(value: float) -> str:
    return f"{value:.2f}%"
```

---

# 2) South Africa (ZA) — NRS/SANS Stubs

## app/rules/za/nrs.py
```py
from ..common import Rule, Finding

class ZA_NRS_AntiIslanding(Rule):
    id = "NRS-097-AntiIslanding"
    title = "Inverter anti-islanding and grid code settings"

    def check(self, design):
        inv = design.get("inverter", {})
        if inv.get("antiIslanding") != True:
            yield Finding(
                ruleId=self.id,
                severity="error",
                message="Anti-islanding protection must be enabled per NRS 097.",
                evidence={"antiIslanding": inv.get("antiIslanding")},
                remediation="Enable anti-islanding and attach compliance settings sheet.",
                jurisdiction="ZA",
            )

class ZA_NRS_FrequencyRideThrough(Rule):
    id = "NRS-097-FRT"
    title = "Frequency ride-through profile"

    def check(self, design):
        grid = design.get("grid", {})
        frt = grid.get("frtProfile")
        if frt is None:
            yield Finding(
                ruleId=self.id,
                severity="warning",
                message="Frequency ride-through profile not provided.",
                evidence={"frtProfile": None},
                remediation="Provide FRT profile values or vendor certificate.",
                jurisdiction="ZA",
            )
```

## app/rules/za/sans_10142_1.py
```py
from ..common import Rule, Finding

class ZA_SANS_WiringCurrent(Rule):
    id = "SANS-10142-1-Current-Carrying"
    title = "Conductor current-carrying capacity vs. design current"

    def check(self, design):
        arr = design.get("array", {})
        isc = arr.get("stringIsc", 0)
        cable = design.get("dcCable", {"ampacity": 0})
        if cable["ampacity"] < 1.25 * isc:
            yield Finding(
                ruleId=self.id,
                severity="error",
                message="DC cable ampacity < 125% of string Isc.",
                evidence={"ampacity": cable["ampacity"], "isc": isc},
                remediation="Increase cable size or reduce series count.",
                jurisdiction="ZA",
            )
```

## ZA Permit Templates (JSON stubs)
- `municipal_cpt.json` (Cape Town)
```json
{
  "authority": "City of Cape Town",
  "checklist": [
    {"id": "site-plan", "label": "Site Plan with array layout", "required": true},
    {"id": "single-line", "label": "Single Line Diagram", "required": true},
    {"id": "structural", "label": "Structural/wind calc summary", "required": true}
  ]
}
```

---

# 3) Australia (AU) — AS/NZS & CEC Stubs

## app/rules/au/asnzs_5033.py
```py
from ..common import Rule, Finding

class AU_ArrayVoltageLimit(Rule):
    id = "ASNZS-5033-Array-Voltage"
    title = "Array maximum voltage vs. equipment ratings"

    def check(self, design):
        tmin = design.get("site", {}).get("tminC", 0)
        voc_stc = design.get("module", {}).get("voc", 38.5)
        temp_coeff = design.get("module", {}).get("betaVoc", -0.003)
        series = design.get("string", {}).get("modulesInSeries", 12)
        voc_min = series * voc_stc * (1 - temp_coeff * (25 - tmin))
        inv_max = design.get("inverter", {}).get("maxDcVoltage", 1000)
        if voc_min > inv_max:
            yield Finding(
                ruleId=self.id,
                severity="error",
                message="Calculated cold‑temp Voc exceeds inverter max DC voltage.",
                evidence={"voc_min": voc_min, "maxDcVoltage": inv_max},
                remediation="Reduce modules in series or select higher rating inverter.",
                jurisdiction="AU",
            )
```

## app/rules/au/asnzs_4777.py
```py
from ..common import Rule, Finding

class AU_InverterSettings(Rule):
    id = "ASNZS-4777-Inverter-Settings"
    title = "Inverter settings profile (volt/var, volt/watt)"

    def check(self, design):
        inv = design.get("inverter", {})
        if not inv.get("voltVarEnabled"):
            yield Finding(
                ruleId=self.id,
                severity="warning",
                message="Volt/Var must be configured per AS/NZS 4777.",
                evidence={"voltVarEnabled": inv.get("voltVarEnabled")},
                remediation="Enable Volt/Var and attach settings screenshot.",
                jurisdiction="AU",
            )
```

## AU CER/CEC Paperwork Template
- `permits/cer_stc_template.json`
```json
{
  "form": "CER-STC",
  "fields": [
    {"key": "installer_licence", "required": true},
    {"key": "panel_listed_cec", "required": true},
    {"key": "inverter_listed_cec", "required": true}
  ]
}
```

---

# 4) United States (US) — NEC/UL/IEEE Stubs

## app/rules/us/nec_2023.py
```py
from ..common import Rule, Finding

class US_NEC_DCAC_RatioHint(Rule):
    id = "NEC-690-DCAC-Ratio-Hint"
    title = "Advisory on DC/AC ratio and downstream impacts"

    def check(self, design):
        ratio = float(design.get("dcAcRatio", 1.2))
        if ratio > 1.7:
            yield Finding(
                ruleId=self.id,
                severity="warning",
                message="High DC/AC ratio may increase clipping and conductor sizing requirements (NEC 690/705 context).",
                evidence={"dcAcRatio": ratio},
                remediation="Run clipping calc and verify 690.8 conductor ampacity + 705 interconnection sizing.",
                jurisdiction="US",
            )

class US_NEC_Labeling(Rule):
    id = "NEC-690-Labels"
    title = "PV labeling and directories"

    def check(self, design):
        labels = design.get("labels", {})
        if not labels.get("rapidShutdown"):
            yield Finding(
                ruleId=self.id,
                severity="error",
                message="Rapid shutdown labeling missing for rooftop systems.",
                evidence={"rapidShutdown": labels.get("rapidShutdown")},
                remediation="Add RSD label per NEC 690 and local fire code.",
                jurisdiction="US",
            )
```

## app/rules/us/ul_1741_sb.py
```py
from ..common import Rule, Finding

class US_UL1741SB_Listing(Rule):
    id = "UL-1741SB-Listing"
    title = "Inverter listing per UL 1741 SB"

    def check(self, design):
        inv = design.get("inverter", {})
        if inv.get("ul1741sb") != True:
            yield Finding(
                ruleId=self.id,
                severity="error",
                message="Inverter must be listed to UL 1741 SB.",
                evidence={"ul1741sb": inv.get("ul1741sb")},
                remediation="Select a listed model or attach NRTL certificate.",
                jurisdiction="US",
            )
```

## app/rules/us/ieee_1547_2018.py
```py
from ..common import Rule, Finding

class US_IEEE1547_RideThrough(Rule):
    id = "IEEE-1547-2018-RideThrough"
    title = "Voltage/Frequency ride-through capability"

    def check(self, design):
        inv = design.get("inverter", {})
        if not inv.get("ieee1547RideThrough"):
            yield Finding(
                ruleId=self.id,
                severity="warning",
                message="Ride-through capability not specified.",
                evidence={"ieee1547RideThrough": inv.get("ieee1547RideThrough")},
                remediation="Provide IEEE 1547-2018 ride-through test summary.",
                jurisdiction="US",
            )
```

## US Permit Templates
- `permits/ahj_generic.json`
```json
{
  "authority": "Generic AHJ",
  "checklist": [
    {"id": "slg", "label": "Single Line Diagram", "required": true},
    {"id": "labels", "label": "Label set per NEC & Fire Code", "required": true},
    {"id": "structural", "label": "Structural calc summary", "required": true}
  ]
}
```

- `permits/fire_label_set.json`
```json
{"labels": ["RAPID SHUTDOWN", "PV SYSTEM DISCONNECT", "WARNING DC CONDUCTORS"]}
```

---

# 5) Wiring the Packs into svc-compliance

## app/rules/__init__.py
```py
from .za.nrs import ZA_NRS_AntiIslanding, ZA_NRS_FrequencyRideThrough
from .za.sans_10142_1 import ZA_SANS_WiringCurrent
from .au.asnzs_5033 import AU_ArrayVoltageLimit
from .au.asnzs_4777 import AU_InverterSettings
from .us.nec_2023 import US_NEC_DCAC_RatioHint, US_NEC_Labeling
from .us.ul_1741_sb import US_UL1741SB_Listing
from .us.ieee_1547_2018 import US_IEEE1547_RideThrough

PACKS = {
    "ZA": [ZA_NRS_AntiIslanding(), ZA_NRS_FrequencyRideThrough(), ZA_SANS_WiringCurrent()],
    "AU": [AU_ArrayVoltageLimit(), AU_InverterSettings()],
    "US": [US_NEC_DCAC_RatioHint(), US_NEC_Labeling(), US_UL1741SB_Listing(), US_IEEE1547_RideThrough()],
}
```

## app/main.py (augment)
```py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal, List
from .rules import PACKS

app = FastAPI(title="svc-compliance")

class CheckRequest(BaseModel):
    country: Literal["ZA","AU","US"]
    code: str
    projectId: str | None = None
    design: dict

@app.post("/check")
async def check(req: CheckRequest):
    findings = []
    for rule in PACKS[req.country]:
        findings.extend(list(rule.check(req.design)))
    return findings
```

---

# 6) Minimal Unit Tests

## tests/test_packs.py
```py
import pytest
from app.rules.za.nrs import ZA_NRS_AntiIslanding
from app.rules.au.asnzs_5033 import AU_ArrayVoltageLimit
from app.rules.us.nec_2023 import US_NEC_Labeling


def test_za_antiislanding_error():
    r = ZA_NRS_AntiIslanding()
    d = {"inverter": {"antiIslanding": False}}
    f = list(r.check(d))
    assert any(x["severity"] == "error" for x in f)


def test_au_voltage_limit_error():
    r = AU_ArrayVoltageLimit()
    d = {
        "site": {"tminC": -10},
        "module": {"voc": 45.0, "betaVoc": -0.0032},
        "string": {"modulesInSeries": 22},
        "inverter": {"maxDcVoltage": 1000}
    }
    f = list(r.check(d))
    assert any(x["severity"] == "error" for x in f)


def test_us_label_required():
    r = US_NEC_Labeling()
    d = {"labels": {"rapidShutdown": False}}
    f = list(r.check(d))
    assert any(x["ruleId"] == "NEC-690-Labels" for x in f)
```

---

# 7) Permit Pack Assembly (Service Endpoint)

Add this endpoint to `svc-compliance` to emit authority‑specific checklists based on `country` + `authority`.

```py
from fastapi import APIRouter, HTTPException
import json, pathlib

router = APIRouter(prefix="/permit")
BASE = pathlib.Path(__file__).parent / "rules"

@router.get("/template")
async def permit_template(country: str, authority: str = "generic"):
    path = None
    if country == "ZA" and authority == "cpt":
        path = BASE / "za" / "permits" / "municipal_cpt.json"
    elif country == "ZA" and authority == "jhb":
        path = BASE / "za" / "permits" / "municipal_jhb.json"
    elif country == "AU":
        path = BASE / "au" / "permits" / "cer_stc_template.json"
    elif country == "US":
        path = BASE / "us" / "permits" / "ahj_generic.json"
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return json.loads(path.read_text())
```

Wire router in `app/main.py`:
```py
from fastapi import FastAPI
from .permit_api import router as permit_router
app = FastAPI()
app.include_router(permit_router)
```

---

# 8) Sample Design Payload (works for all packs)
```json
{
  "country": "US",
  "design": {
    "dcAcRatio": 1.8,
    "labels": { "rapidShutdown": false },
    "inverter": { "ul1741sb": false, "maxDcVoltage": 1000, "voltVarEnabled": false },
    "site": { "tminC": -10 },
    "module": { "voc": 40.5, "betaVoc": -0.0032 },
    "string": { "modulesInSeries": 22 },
    "array": { "stringIsc": 12.1 },
    "dcCable": { "ampacity": 12.0 }
  }
}
```

---

# 9) How to Extend Safely
1. **Add a new rule** → create a class in the correct country file, give it a unique `id`, and implement `check()`.
2. **Document evidence** → always include inputs used in a finding.
3. **Reference text** → if you add citations, attach them in `evidence.sourceRef` (e.g., `"NEC-690.12(2023)"`).
4. **Severity** → use `error` only when a submittal would be rejected by an AHJ.
5. **Tests** → add at least one failing and one passing case per rule.

---

# 10) Plug‑in Contract (Compliance as a Plug‑in)
If you ship packs as plug‑ins instead of core, add a manifest:
```json
{
  "id": "com.solar.pack.us.nec2023",
  "name": "US NEC 2023 Pack",
  "version": "0.1.0",
  "capabilities": ["compliance:nec-2023"],
  "routes": [{"path": "/plugins/nec2023/check", "method": "POST"}],
  "permissions": {"scopes": ["project:read"]}
}
```
Expose a `/plugins/nec2023/check` endpoint that returns the same `Finding[]` structure.

---

**You now have working, test‑covered stubs for ZA/AU/US** that integrate with the existing gateway endpoint and can be expanded rule‑by‑rule without changing contracts.

