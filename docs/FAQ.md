# EDTA — Top 10 FAQ

**Product:** Experience-Driven Targeting Architecture (EDTA)  
**Live demo:** https://edta-api.onrender.com/scenario-demo  
**Source:** https://github.com/jeraldcs/edta-complete-api  
**Audience:** architects, engineers, product, compliance reviewers, InfoQ / conference attendees

---

### 1. What is EDTA?

EDTA is an **open-source reference implementation** of enterprise personalization as a **governed decision pipeline** — not a single black-box model. It combines:

- **HAOE** — Hybrid AI Orchestration (Rules → SLM → ML → optional LLM)
- **TAPL** — Trust-Aware Personalization (show / soften / delay / suppress in ranking)
- **EML / TKGE** — Experience memory and temporal journey context
- **EDS / OSE** — Explainable relevance and outcome simulation
- **FastAPI** surface with API-native explainability and a live travel demo

The LLM enriches and explains; it does **not** own consent, compliance, fatigue, or final trust governance.

---

### 2. How is this different from a traditional recommender or an LLM chatbot?

| Traditional / LLM-first | EDTA |
|-------------------------|------|
| One model or one prompt → offer | Explicit tiers with cost budget and audit |
| Consent/fatigue in analytics only | TAPL **modifies** the final rank |
| Score or prose explanation only | Rules fired, tier, TAPL, EDS, OSE in JSON |
| Rebuild engine per industry | Same core; swap YAML policies + catalog |

Traditional systems stay valuable for simple, single-channel rules. EDTA completes them for multi-channel, AI-assisted, auditable personalization.

---

### 3. Is this production-ready or a demo?

It is a **reference architecture with a runnable demo** — hardened enough to deploy (auth, demo proxy, webhook SSRF checks, CI, metrics), but **not** a certified enterprise product or a Fortune 500 case study.

Use it to:

- Learn the architecture pattern  
- Integrate via `/v1` APIs  
- Adapt policies and catalogs to your vertical  

Do **not** claim production conversion lift or regulatory certification from the demo alone.

---

### 4. How does the live demo work?

1. Open `/scenario-demo` and pick a travel, governance, or “Compare vs traditional” chip (or type free text).  
2. **Recommend** calls `POST /recommend-from-scenario` (production browsers use `/demo-api/*` with server-side auth — no API key in the page).  
3. The response shows the top vehicle, TAPL action, EDS/outcome meters, empathy panels, and technical scoring signals.  
4. Architecture panels expose TKGE, EML, HAOE, and OSE from the same JSON.

Same recommend path for all chips — comparison chips only change the scenario text and UI narrative.

---

### 5. What do the scoring signals mean?

For the top recommendation:

| Signal | Meaning |
|--------|---------|
| **EDS** | Explainable relevance (intent, engagement, business value, journey, context − risk) |
| **Semantic similarity** | Text similarity of scenario vs candidate copy |
| **Channel fit** | Suitability of candidate type for the channel |
| **Expected outcome** | Simulated conversion / revenue / trust blend (OSE) |
| **Base / Pre-TAPL rank** | Hybrid rank after empathy/preference boosts |
| **Final rank** | After TAPL (e.g. delay ≈ ×0.55; no consent capped low) |

Hero “Match score” = **final rank score**. Details: Technical details → **3. Scoring Signals**.

---

### 6. How do I integrate EDTA with my application?

Prefer the versioned API:

```http
POST /v1/recommend
POST /v1/recommend-from-scenario
POST /v1/feedback
POST /v1/compare-outcomes
```

- Send `X-API-Key` when `EDTA_API_KEY` is set.  
- Pass structured `CustomerContext` from your CDP/BFF, or free-text for demos.  
- Persist `request_id`, TAPL action, inference tier, and EDS for support and audit.  
- Use `Idempotency-Key` on recommend/feedback for safe retries.  
- OpenAPI: https://edta-api.onrender.com/docs  

New apps should use `/v1`; root routes remain for the web demo.

---

### 7. Can this work for any industry?

**Yes at the engine layer; no as a one-size catalog.**

- Keep HAOE, TAPL, EML, TKGE, EDS, OSE.  
- Swap: candidate catalog, `config/rules/packs/`, TAPL YAML, training rows, optional empathy profiles.  
- Training corpus already spans car rental, hotel, restaurant, and healthcare (100 scenarios).  
- Hero demo vertical = **travel / car rental**; healthcare appears as **HCP education governance**, not clinical decision support.

---

### 8. How does EDTA help with GDPR / CCPA / HIPAA?

EDTA provides **technical controls that map to privacy principles** — consent-aware ranking, channel sensitivity, explainability, audit logs. It is **not** “GDPR/CCPA/HIPAA certified.”

Your organization still owns: privacy notices, DPAs/BAAs, retention/erasure runbooks, and legal review.  
See also: `docs/TRADITIONAL_VS_EDTA.md` and security notes in `docs/SECURITY.md`.

---

### 9. Why not just use an LLM for every recommendation?

LLMs are powerful for ambiguous language and explanations, but:

- Cost and latency spike if every request escalates  
- Governance (consent, fatigue, compliance) must not live only in a prompt  
- Auditability suffers when the “decision” is opaque prose  

HAOE keeps **Rules / SLM / ML** as the default path and uses the LLM as an **optional, budget-gated** teacher/explainer. Benchmarks: `docs/BENCHMARKS.md`.

---

### 10. Where should I start, and what’s next?

**Start**

1. Run the [live demo](https://edta-api.onrender.com/scenario-demo) — loyalty, No consent, High fatigue, Compare vs traditional.  
2. Clone the repo and run locally (`uvicorn` + `pytest`).  
3. Read `docs/EDTA_ARCHITECTURE_DOCUMENT.md` and `docs/TRADITIONAL_VS_EDTA.md`.  
4. Call `/v1/recommend` with a sample from `sample_requests/`.

**Roadmap themes**

- Stronger subject export/erasure APIs for privacy ops  
- PostgreSQL / multi-instance ops  
- Live enrichment APIs for travel empathy  
- Partner case study with real A/B metrics (when available)

**Conference / InfoQ materials**

- Article title: *Governed Personalization: Why Trust Must Change the Rank, Not Just the Log*  
- Talk title: *Why Did We Show This? Designing Auditable Recommendation Systems*  
- Technical title: *Beyond LLM-First Recommendations: A Four-Tier Architecture for Trust-Aware Ranking*  
- Pitch: `docs/INFOQ_EDITOR_PITCH.md`  
- Outline: `docs/INFOQ_ARTICLE_OUTLINE.md`  
- Slides: `docs/EDTA_INFOQ_PRESENTATION_latest.pptx`  
- Speaker notes: `docs/EDTA_INFOQ_PRESENTATION.md`

---

## Quick links

| Resource | URL / path |
|----------|------------|
| Live demo | https://edta-api.onrender.com/scenario-demo |
| GitHub | https://github.com/jeraldcs/edta-complete-api |
| Swagger | https://edta-api.onrender.com/docs |
| Architecture PDF | `docs/edta_architecture_diagrams_full.pdf` |
| Showcase Word | `docs/EDTA_COMPLETE_SHOWCASE_updated.docx` |
| Traditional vs EDTA | `docs/TRADITIONAL_VS_EDTA.md` |
| Public SLM hosting (Groq/Together) | `docs/SLM_PUBLIC_HOSTING.md` |
