# Traditional Personalization vs EDTA

**Audience:** architects, product leaders, InfoQ reviewers, customer due diligence  
**Live demo:** [https://edta-api.onrender.com/scenario-demo](https://edta-api.onrender.com/scenario-demo)  
**Related:** `docs/EDTA_POSITIONING.md`, `docs/BENCHMARKS.md`, showcase Word doc section *Traditional vs EDTA*

---

## Practitioner framing

EDTA is a **demo and reference implementation** built from experience with traditional personalization architectures — rule engines, single-model rankers, and batch CRM campaigns — then extended with modern AI under explicit governance.

> EDTA does not replace traditional personalization — it completes it. Rules stay fast and auditable; ML stays for catalog fit; AI enters only where ambiguity demands it; and governance, memory, and explainability sit *inside* the decision path, not in a downstream dashboard.

---

## Three traditional patterns (fair baseline)

| Pattern | Typical stack | Strengths | Failure mode with modern AI / multi-channel |
|---------|---------------|-----------|-----------------------------------------------|
| **Rule-based personalization** | CMS + segments + if/then | Auditable, fast, cheap | Brittle at scale; no journey memory; weak NLP |
| **Monolithic ranker** | One ML model → score | Strong catalog match | Opaque; consent/fatigue often outside ranking |
| **LLM bolt-on** | Prompt → recommendation | Handles ambiguity | Unbounded cost/latency; weak audit; governance after the fact |

EDTA keeps what those systems did well and adds **HAOE tier routing**, **EML memory**, **TAPL trust policy in rank**, **OSE outcome simulation**, and **API-native explainability**.

---

## Comparison dimensions (what you can prove in the demo)

| Dimension | Traditional (typical) | EDTA | How to show it |
|-----------|----------------------|------|----------------|
| **Explainability** | Score only, or post-hoc SHAP | Rules fired, inference tier, TAPL action, EDS breakdown, explanation source | Open **Developer view** / architecture panels after Recommend |
| **Governance in rank** | Consent in CRM, not in ranker | TAPL `show` / `soften` / `delay` / `suppress` / `generic_fallback` | Demo chips: **No consent**, **High fatigue**, or **Compare vs traditional** |
| **Cross-session memory** | Stateless or batch segments | EML trust/fatigue before → after | Run related scenarios; watch trust/fatigue meters |
| **Journey context** | Last click / last segment | TKGE timeline + journey stage | Architecture panels + `GET /context-graph` |
| **Outcome before show** | Click-optimized rank | OSE conversion / revenue / trust risk | Benchmark table Outcome vs Semantic columns |
| **Cost control** | Fixed infra or unbounded LLM | HAOE Rules → SLM → ML → optional LLM | `python scripts/load_test_tiers.py` + `docs/BENCHMARKS.md` |
| **Latency tiers** | One path for all requests | Rules &lt;50 ms vs LLM seconds (local engine) | Label Render cold-start separately |
| **Vertical portability** | Rewrite engine per industry | Same pipeline; swap YAML + catalog | Travel vs healthcare scenarios in one API |
| **Testability** | Hard to regression-test black boxes | Pytest suite + 11-scenario travel matrix | `docs/TRAVEL_SCENARIO_SCORES.md` |

---

## Side-by-side narrative (5-minute demo script)

Use the live **Compare vs traditional** chips on `/scenario-demo`, or follow this script manually.

### Act 1 — Rules-era upsell

**Traditional expectation:** If text mentions SUV / booking → always push the upgrade.  
**EDTA demo:** Same structured loyalty SUV scenario still recommends a fit vehicle, but response includes TAPL action, EDS breakdown, empathy fit, and explanation — not only a candidate ID.

**Chip:** Rules-era upsell (`compare_rules`)

### Act 2 — Monolithic ranker

**Traditional expectation:** Highest similarity / click score wins, even if journey and constraints disagree.  
**EDTA demo:** Family vacation with cargo and kids → empathy constraints + OSE favor family-fit vehicles; Semantic score alone is not the final authority.

**Chip:** ML ranker era (`compare_ranker`)

### Act 3 — LLM bolt-on risk

**Traditional expectation:** Ambiguous one-liner → LLM picks an offer; cost and audit are opaque.  
**EDTA demo:** Ambiguous text still yields a ranked recommendation with **inference tier** visible; TAPL remains the governance layer; LLM is optional and budget-gated (demo often runs without LLM).

**Chip:** LLM bolt-on risk (`compare_llm`)

### Act 4 — EDTA governed baseline

**EDTA demo:** Loyalty family SUV with consent true — full stack: EML trust, TAPL `show`, empathy profile, outcome scores, architecture panels.

**Chip:** EDTA governed (`compare_edta`)  
**Also try:** No consent → TAPL `generic_fallback`; High fatigue → `delay` / soften.

---

## Architecture comparison table

| Pattern | Typical approach | EDTA difference |
|---------|------------------|-----------------|
| LLM-first personalization | One prompt → recommendation | LLM optional teacher; TAPL + rules own governance |
| Monolithic ranker | Single model score | EDS + TAPL + OSE + ranker — each auditable |
| Trust as logging | Trust score in analytics only | TAPL modifies rank and action |
| Hidden routing | Ad hoc if/else for model choice | HAOE with YAML policy + `InferenceResult` |
| Stateless API | Each request independent | EML + TKGE across sessions |
| Black-box explainability | SHAP post-hoc | Rules, reason codes, tier, TAPL reason in JSON |
| Vertical rewrite | New engine per industry | Same core; swap policies and catalogs |

---

## Evidence already in the repo

| Exhibit | Location | Claim style |
|---------|----------|-------------|
| 11-scenario travel matrix | `docs/TRAVEL_SCENARIO_SCORES.md` | Alignment proxy — not production A/B lift |
| Four-tier latency / cost | `docs/BENCHMARKS.md` | Local Docker for engine; Render labeled separately |
| Counterfactual A vs B | `POST /v1/compare-outcomes` | Outcome simulation before live A/B |
| Automated tests | `pytest` | Contract + security + scenario coverage |

---

## What not to claim

- No production conversion lift without partner A/B data.
- ML “accuracy” in this package is a **demo alignment proxy** (training CSV / scenario match), not Netflix-scale generalization.
- Separate **engine benchmarks** (local) from **hosted demo latency** (cold start on free tier).
- Prefer: *“better architecture for governed personalization”* over *“always better recommendations.”*

Traditional systems still win on **simplicity** for one channel and one segment. EDTA’s value appears when you need multi-channel consistency, consent/fatigue in rank, LLM cost control, and auditability.

---

## Audience-specific talking points

| Audience | Traditional pain | EDTA benefit |
|----------|------------------|--------------|
| Architect | Hidden routing, untestable LLM paths | HAOE + `inference_mode`, OpenAPI, tests |
| Product | Wrong offer at wrong journey stage | TKGE + empathy + OSE |
| Compliance | “Why did we show this?” unanswered | TAPL audit, reason codes, consent in rank |
| Ops / finance | LLM cost surprises | Rules/SLM for common paths; LLM budget-gated |
| Industry teams | Rebuild engine per vertical | Policy YAML + catalog swap |

---

## One-liner for slides and InfoQ

**EDTA does not replace traditional personalization — it completes it** with tiered AI, memory, outcome simulation, and trust-aware ranking inside the decision path.

---

## Demo UI reference

On [scenario-demo](https://edta-api.onrender.com/scenario-demo):

1. **Try scenario** — travel archetypes (existing).
2. **Try governance** — No consent / High fatigue (existing).
3. **Compare vs traditional** — Rules-era, ML ranker era, LLM bolt-on risk, EDTA governed (additive chips; same Recommend API).

Each comparison chip loads scenario text and runs the **same** `/recommend-from-scenario` path — no alternate ranking mode, no change to default demo behavior.
