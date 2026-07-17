# InfoQ Editor Pitch — EDTA

Use this as the body of your submission email. InfoQ accepts article proposals via their [contribute](https://www.infoq.com/contribute/) page or by contacting editors directly.

---

**To:** InfoQ Editors (Articles — Architecture / AI / Software Design)  
**Subject:** Article proposal — Governed Personalization: Four-Tier Architecture for Explainable, Trust-Aware Recommendations  
**Author:** Jerald Selvaraj · jerald.cs@gmail.com

---

Dear InfoQ Editors,

I would like to propose an architecture article for InfoQ readers on **governed personalization** — treating recommendation systems as auditable decision pipelines rather than single black-box models.

## The problem

Enterprise teams are adopting LLMs for personalization faster than they are adopting **governance** for it. The result is often relevant but risky recommendations: opaque scores, uncontrolled token cost, and weak answers to *“why did we show this?”* when product, compliance, or trust teams ask.

Most stacks still look like:

```text
context → model → ranked recommendation
```

That pattern breaks down across web, mobile, chatbot, IoT, and partner channels — especially when consent, fatigue, compliance sensitivity, and explainability must influence the **final decision**, not just appear in analytics dashboards.

## The proposal

**Working title:**  
*Governed Personalization: A Four-Tier Architecture for Explainable, Trust-Aware Recommendations*

**Alternative title:**  
*Beyond LLM-First Recommendations: Cost-Aware, Auditable Personalization with Rules, SLM, ML, and Optional LLM*

I present **EDTA (Experience-Driven Targeting Architecture)** — an open-source reference implementation (FastAPI, Python) that decomposes personalization into explicit modules:

- **Hybrid AI Orchestration Engine (HAOE)** — Rules → SLM → ML → optional LLM, with cost budget and circuit breaker
- **Trust-Aware Personalization Layer (TAPL)** — show / soften / delay / suppress actions that **modify ranking**, not only logs
- **Experience Memory Layer (EML)** and **Temporal Knowledge Graph Engine (TKGE)** — trust, fatigue, and journey context across sessions
- **Experience DNA Score (EDS)** and **Outcome Simulation Engine (OSE)** — explainable relevance and expected business outcome
- **API-native explainability** — inference tier, rules fired, TAPL decision, score breakdown, and explanation source in every response

The LLM enriches and explains; it does **not** own consent, compliance, fatigue, or final trust governance.

## What readers will take away

1. **How to design multi-tier AI routing** for personalization without hiding tier selection inside ad hoc conditionals — including benchmark methodology for Rules, SLM, ML, and LLM in isolation.
2. **How to make trust governance first-class in ranking** — TAPL policies, fatigue, consent, and channel sensitivity as scored inputs with audit trails.
3. **How to structure explainability as an API contract** — so product, compliance, and engineering teams can answer *why* from the response payload, not from log archaeology.

## Evidence (reference implementation, not production case study)

This is an **implementation-oriented reference architecture**, not a Fortune 500 case study. I am explicit about that limit. What I provide:

| Asset | Link / detail |
|-------|----------------|
| **Live demo** | https://edta-api.onrender.com/scenario-demo |
| **Open source** | https://github.com/jeraldcs/edta-complete-api |
| **OpenAPI** | https://edta-api.onrender.com/docs |
| **Architecture diagrams** | 11-page PDF (`docs/edta_architecture_diagrams_full.pdf`) |
| **Automated tests** | 167 pytest tests, CI with model training and ML eval |
| **Four-tier benchmarks** | Reproducible scripts — latency, tier match rate, cost units, fallback rate |
| **Travel scenario matrix** | 11 trained road-trip scenarios — 100% top-rank alignment on demo training set (labeled as demo proxy, not production A/B lift) |

**Hero vertical for the article:** travel / car rental (high-intent, journey-driven). Healthcare HCP education appears as a **governance sidebar** (TAPL, audit, suppress on sensitive channels) with a required scope disclaimer — not clinical decision support.

## Article format

- **Length:** ~3,000 words (concise practitioner article, not documentation dump)
- **Tone:** Architecture guidance for software architects and senior engineers building personalization platforms
- **Includes:** 2–3 architecture diagrams, one annotated API walkthrough, one benchmark table, comparison vs. LLM-first and monolithic rankers, honest scope limits
- **Excludes:** Product marketing, unverified conversion claims, “Netflix-scale” generalization

## About the author

**Jerald Selvaraj** — architect and implementer of the EDTA reference stack. [Add 1–2 sentences: your current role, domain background, and why you built this — e.g. enterprise personalization, travel tech, healthcare education routing.]

## Supporting materials (available on request)

- Full publication package: `docs/EDTA_PUBLICATION_DOCUMENT.md`
- Detailed architecture document: `docs/EDTA_ARCHITECTURE_DOCUMENT.md`
- Benchmark methodology: `docs/BENCHMARKS.md`
- Article draft (extended): `docs/edta_llm_personalization_article_draft.md`

Thank you for considering this proposal. I am happy to adjust scope, length, or vertical emphasis to fit InfoQ’s editorial guidelines.

Best regards,  
**Jerald Selvaraj**  
jerald.cs@gmail.com  
GitHub: https://github.com/jeraldcs/edta-complete-api

---

## Submission checklist before sending

- [ ] Fill in author bio paragraph (role, affiliation, domain experience)
- [ ] Confirm live demo works (https://edta-api.onrender.com/scenario-demo)
- [ ] Attach or link architecture PDF (`docs/edta_architecture_diagrams_full.pdf`)
- [ ] Pick one hero vertical (travel recommended) and keep healthcare as sidebar only
- [ ] Submit via https://www.infoq.com/contribute/ or email editors
