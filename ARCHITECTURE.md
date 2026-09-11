# Governed Architecture — Reference Implementation

Open-source reference for a **governed recommendation pipeline**: context enrichment, trust-aware ranking, and stateful journey memory — not a single black-box model.

**Live demo:** https://edta-api.onrender.com/scenario-demo  
**Swagger:** `/docs` on any running instance

---

## Pipeline overview

Every recommend request moves through three phases:

1. **Enrich context** — Client → Profile → EML → TKGE → HAOE  
2. **Score, govern & rank** — EDS → TAPL → OSE → Rank → Response  
3. **Update state** — persist memory & journey for the next request  

![Governed Architecture reference implementation](static/governed_architecture.png)

Solid arrows are request flow; dashed lines are context inputs and state feedback.

---

## Layers

| Layer | Role |
|-------|------|
| **Profile** | Lookup facade at the API boundary (pluggable CRM/CDP adapter) |
| **EML** | Cross-session memory — trust, fatigue, preferences, history (SQLite) |
| **TKGE** | Journey graph — temporal session context merged from prior snapshots |
| **HAOE** | Inference routing — Rules → SLM → ML → optional LLM |
| **EDS** | Explainable relevance score with reason codes |
| **TAPL** | Trust governance — show / soften / delay / suppress (modifies rank) |
| **OSE** | Outcome view — conversion, revenue, trust, and risk simulation |
| **Rank** | Hybrid final ordering |

Policies are externalized in YAML: `config/eml_policies.yaml`, `config/tapl_policies.yaml`, `config/haoe_policies.yaml`.

---

## Code entry points

| Path | Purpose |
|------|---------|
| `app/services/recommendation_handlers.py` | Request handler — enrich, rank, persist |
| `app/recommender.py` | Per-candidate scoring loop |
| `app/experience_memory.py` | EML facade |
| `app/context_graph.py` | TKGE graph builder |
| `app/orchestration.py` | HAOE tier routing |
| `app/eds.py` | EDS scoring |
| `app/ai/tapl_model.py` | TAPL governance |
| `app/ai/outcome_model.py` | OSE simulation |

---

## API response contract

Inspectable fields on each recommendation response include `experience_memory`, `context_graph`, `inference.tier`, `eds_score`, `tapl.action`, `outcome_simulation`, `reason_codes`, and `request_id`.

---

## Security note

Never commit `.env`, API keys, or runtime databases (`data/edta.db`). Use `.env.example` as a template. Rotate any key that was ever stored outside your secret manager.
