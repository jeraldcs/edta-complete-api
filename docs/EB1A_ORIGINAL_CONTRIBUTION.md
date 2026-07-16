# EB-1A Original Contribution Statement

**Field:** Artificial intelligence / enterprise software architecture / multi-channel personalization  
**Author:** Jerald Selvaraj  
**Reference implementation:** [edta-complete-api](https://github.com/jeraldcs/edta-complete-api)  
**Live demo:** [https://edta-api.onrender.com/scenario-demo](https://edta-api.onrender.com/scenario-demo)

---

## One-sentence contribution

I architected and implemented **EDTA (Experience-Driven Targeting Architecture)**, a **trust-aware, cost-orchestrated personalization framework** that separates **governed decision authority** (rules, compliance, fatigue, channel safety) from **inference capability** (distilled SLM, classical ML, optional LLM), with **auditable tier routing** and **explainable API contracts** suitable for regulated and journey-based industries.

---

## Problem addressed (industry significance)

Enterprise personalization systems increasingly default to **monolithic ML rankers** or **LLM-first** designs. Both approaches create operational and compliance risk:

- Decisions are **opaque** to product, legal, and clinical/commercial review teams.
- **Cost and latency** scale poorly when every request invokes a large language model.
- **Trust, consent, fatigue, and channel constraints** are often logged but not enforced in ranking.
- **Cross-channel** journeys (web, chatbot, email, connected car, wearable) lack a unified, auditable decision pipeline.

Industries such as **travel and car rental**, **hospitality**, and **healthcare commercial/education** need personalization that is **relevant** but also **governed, explainable, and cost-controlled**.

---

## Original contribution (what is new)

My contribution is not a single new ranking algorithm. It is an **original systems architecture** and **reference implementation** with the following distinct elements:

### 1. Four-tier public inference model with unified contract

I defined and implemented a **public four-tier model** — **Rules → SLM → ML → LLM** — exposed through a single `InferenceResult` contract. A **Hybrid AI Orchestration Engine (HAOE)** selects the cheapest reliable tier using policy YAML (cost units, latency estimates, circuit breaker, session budget). This makes tier choice **explicit, testable, and benchmarkable**, rather than hidden inside one model.

### 2. Trust-Aware Personalization Layer (TAPL) integrated into ranking

I designed **TAPL** as a first-class governance module (not post-hoc logging) that influences recommendation action (**show / soften / suppress / delay**) based on **consent, fatigue, compliance sensitivity, and channel constraints**, with SQLite audit trails. This addresses a gap in typical recommenders where “trust” is metadata rather than a ranking input.

### 3. Distilled teacher loop for cost-efficient repeat inference

I implemented a **self-distillation store** that captures high-confidence labels from SLM/LLM teachers and serves repeat scenarios via **pattern memory** without repeated token cost. This is integrated as the **SLM tier** (distilled memory + optional small-model endpoint + rules fallback), providing a practical path to reduce LLM spend on recurring journeys.

### 4. Memory-aware context architecture (EML + TKGE)

I integrated **Experience Memory Layer (EML)** and a **Temporal Knowledge Graph Engine (TKGE)** into the recommendation path so that trust, fatigue, preferences, and journey sequence influence scoring — not only the current request payload.

### 5. Explainability by API design

I specified API responses that return **EDS breakdowns, reason codes, rules fired, TAPL decisions, outcome simulation, inference tier, and explanation source** — enabling engineering, product, and compliance stakeholders to inspect decisions without model introspection tools.

### 6. Reproducible four-tier benchmark methodology

I authored scripts and documentation (`load_test_tiers.py`, `benchmark_metrics.py`, `docs/BENCHMARKS.md`) to compare tiers on **latency, tier routing fidelity, training-alignment proxy, fallback rate, and cost units** — supporting evidence-based architecture decisions.

---

## What is deliberately not claimed

- EDTA is **not** positioned as a replacement for large-scale production recommenders at Netflix/Amazon scale.
- ML models in the reference implementation are trained on a **demonstration corpus** (~100 cross-industry scenarios); production accuracy claims require partner data.
- EDTA **does not** provide clinical diagnosis or treatment recommendations; healthcare use cases are scoped to **approved HCP education and content routing** under policy control.

---

## Industry applicability (significance)

| Industry | How EDTA applies |
|----------|------------------|
| **Car rental / travel** | Journey-stage-aware upsell (SUV upgrade, early booking), airport/family context, chatbot and connected-car channels |
| **Hotel / hospitality** | Reservation assist, room offers, loyalty and fatigue-aware suppression |
| **Healthcare (commercial)** | HCP education routing, compliance-sensitive suppression, auditable rules + TAPL for approved content only |

The same engine generalizes via **YAML rule packs**, **TAPL policies**, and **catalog candidates** — demonstrating architectural portability across verticals.

---

## Evidence of implementation and recognition (current)

| Artifact | Description |
|----------|-------------|
| Open-source reference | Phased implementation (Phases 0–5), GitHub repository |
| Live deployment | Docker + Render production demo |
| Architecture article (draft) | InfoQ submission draft on trust-aware personalization |
| Benchmarks | Four-tier comparison with quality and latency metrics |
| Multi-channel demo | Scenario demo with TKGE, EML, HAOE, OSE panels |

**Recommended additional evidence for petition:** published InfoQ article, expert recommendation letters from enterprise architects, pilot letter of interest from a target industry, LLM-only vs EDTA comparison study.

---

## Suggested language for expert letters

Experts may describe the contribution as:

> *"An original enterprise personalization architecture that orchestrates rules, distilled memory, classical ML, and optional LLMs under explicit trust and cost governance — with auditable decision outputs suitable for multi-channel and compliance-sensitive deployments."*

---

## Distinction from prior art (summary)

| Typical approach | EDTA contribution |
|------------------|-------------------|
| Single ranker or LLM-first | Four explicit tiers with HAOE routing |
| Trust as logging only | TAPL enforced in ranking |
| Opaque score + item ID | Full explainability payload |
| LLM on every ambiguous request | Distilled SLM + budget/circuit breaker |
| Static profile only | EML + TKGE temporal memory |

---

*Document version: 1.0 — for EB-1A petition support and expert letter alignment. Not legal advice; consult immigration counsel for filing strategy.*
