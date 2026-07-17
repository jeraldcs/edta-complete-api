# InfoQ Article Outline (~3,000 words)

**Title:** Governed Personalization: A Four-Tier Architecture for Explainable, Trust-Aware Recommendations  
**Author:** Jerald Selvaraj  
**Target length:** 2,800–3,200 words (excluding code blocks and figure captions)  
**Hero vertical:** Travel / car rental  
**Secondary sidebar:** Healthcare HCP education (governance only)

Each section maps to existing repo documentation so you can copy, compress, and edit rather than write from scratch.

---

## Word budget summary

| Section | Words | Source docs |
|---------|------:|-------------|
| 1. Hook & problem | 350 | `EDTA_POSITIONING.md`, article draft §1 |
| 2. Why single-model fails | 250 | `EDTA_PUBLICATION_DOCUMENT.md` §3 |
| 3. Architecture overview | 400 | `EDTA_ARCHITECTURE_DOCUMENT.md` §4, diagrams PDF Fig 3 |
| 4. End-to-end walkthrough | 500 | Article draft §5, `recommendation_handlers.py` flow |
| 5. HAOE four-tier routing | 450 | `BENCHMARKS.md`, `EDTA_ARCHITECTURE_DOCUMENT.md` §8 |
| 6. Trust governance (TAPL + EML) | 400 | Publication doc §10, TAPL policies YAML |
| 7. Explainability in the API | 250 | Article draft, sample JSON from demo |
| 8. Travel vertical demo | 300 | `TRAVEL_SCENARIO_SCORES.md`, empathy section |
| 9. Comparison & alternatives | 250 | Publication doc §13 |
| 10. Lessons & limits | 200 | Publication doc §15–16 |
| 11. Conclusion & resources | 150 | GitHub, demo links |
| **Total** | **~3,100** | |

---

## Section 1 — Hook: LLM adoption outpaced governance (~350 words)

**Goal:** Grab architects who feel the pain of “we added GPT to personalization and now compliance is nervous.”

**Write:**
- Open with a concrete scenario: family traveler booking airport SUV rental; system pushes upgrade at wrong time/channel or after banner fatigue.
- State thesis in one sentence: *Personalization is a governance problem, not only a ranking problem.*
- Contrast LLM-first hype vs. enterprise needs (consent, fatigue, explainability, cost).
- Promise: a reference architecture readers can study, run, and adapt — not a product pitch.

**Pull from:**
- `docs/EDTA_POSITIONING.md` — “Recommended article angle (lead paragraph)”
- `docs/edta_llm_personalization_article_draft.md` — Abstract + §1

**Figure:** None (text hook only)

**Do not:** Lead with “car rental API” or feature list.

---

## Section 2 — Why `context → model → rank` fails (~250 words)

**Goal:** Frame the architectural problem InfoQ readers recognize.

**Write:**
- Show the anti-pattern diagram (one line).
- Table of gaps: opaque ranking, LLM cost, trust as metadata only, single-channel thinking, no outcome view, weak explainability.
- Transition: decompose into testable modules with explicit responsibilities.

**Pull from:**
- `docs/EDTA_PUBLICATION_DOCUMENT.md` — §3 Problem statement
- Article draft — §1 bullet questions (“Why was this selected?” etc.)

**Figure:** Optional small table (6 rows max)

---

## Section 3 — Architecture overview (~400 words)

**Goal:** Give the mental model before deep dives.

**Write:**
- Introduce EDTA acronym once; define layers briefly.
- Describe four runtime concerns: **input enrichment**, **memory/time**, **orchestration + inference**, **scoring + governance**, **output + learning**.
- Name core components: HAOE, TAPL, EML, TKGE, EDS, OSE, Empathy Engine (travel extension).
- One paragraph on FastAPI reference implementation + policy YAML externalization.

**Pull from:**
- `docs/EDTA_ARCHITECTURE_DOCUMENT.md` — §4 Architecture overview, acronym table §4.2
- `docs/edta_architecture_diagrams_full.pdf` — **Figure 3** (Logical layer stack)

**Figure (required):** Layer stack diagram — embed Figure 3 from PDF or export PNG.

**Code block:** None

---

## Section 4 — End-to-end walkthrough (~500 words)

**Goal:** Make the architecture tangible with one API path.

**Write:**
- Choose **`POST /recommend-from-scenario`** (matches live demo).
- Step through: scenario text → NLP parser → profile lookup → EML enrich → TKGE graph → HAOE tier → per-candidate scoring → response.
- Include **trimmed** request JSON (scenario_text, limit, flags) — ~15 lines max.
- Include **trimmed** response highlights — only: `inference.tier`, `tapl.action`, `eds_score.final_eds_score`, `explanation_source`, `context_graph` summary — ~20 lines max.
- Explain what each field answers for operators.

**Pull from:**
- `docs/EDTA_ARCHITECTURE_DOCUMENT.md` — §5.2 Scenario demo path
- `docs/edta_llm_personalization_article_draft.md` — §4–5 implementation flow
- Live demo: run one scenario and paste real JSON (cust-789 loyalty SUV)

**Figure:** **Figure 5** from diagrams PDF (scenario demo path) OR sequence diagram Figure 4

**Callout box:** “Try it: https://edta-api.onrender.com/scenario-demo”

---

## Section 5 — HAOE: four-tier inference routing (~450 words)

**Goal:** This is the **technical differentiator** — spend real depth here.

**Write:**
- Explain tiers in plain language:
  - **Rules** — YAML packs, deterministic, auditable, lowest cost
  - **SLM** — distilled pattern memory + optional local endpoint; explanation routing
  - **ML** — sklearn intent/journey/TAPL/outcome/ranker models
  - **LLM** — optional teacher; budget-gated; circuit breaker
- When HAOE escalates vs. stays local (parser confidence, ambiguity, fatigue/consent signals).
- **`inference_mode` force-routing** for benchmarks vs. `auto` for production-style behavior.
- Benchmark table (local Docker — **not** Render cold start):

| Tier | p95 latency (target) | Cost units | Tier match | Notes |
|------|---------------------:|-----------:|-----------:|-------|
| Rules | < 50 ms | ~0 | 100% | Deterministic |
| SLM | < 100 ms | Low | ≥ 80% | Distilled memory |
| ML | < 300 ms | Medium | ≥ 80% | sklearn |
| LLM | 3–8 s | Highest | n/a | Requires API key |

- Label clearly: *demo benchmarks on reference training data; not production SLOs.*

**Pull from:**
- `docs/BENCHMARKS.md` — full methodology
- `docs/EDTA_ARCHITECTURE_DOCUMENT.md` — §8 Four-tier inference
- `docs/edta_architecture_diagrams_full.pdf` — **Figure 6** (HAOE routing)

**Figure (required):** HAOE routing diagram

---

## Section 6 — Trust governance: TAPL + EML (~400 words)

**Goal:** Show governance is in the **ranking path**, not a dashboard afterthought.

**Write:**
- EML: trust score, fatigue, preferences, outcome history — per `customer_id` / `anonymous_id`.
- TAPL actions and **ranking effect**:

| Action | Effect |
|--------|--------|
| show | Full hybrid score |
| soften | × 0.85 |
| delay | × 0.55 |
| suppress / generic_fallback | Cap at 0.15 |

- YAML policy examples (2 bullets): no consent → generic_fallback; fatigue threshold → delay.
- Before/after example: same candidate with fatigue 0.1 vs. 0.8 — TAPL action change.
- SQLite audit trail mention (one sentence).

**Pull from:**
- `docs/EDTA_PUBLICATION_DOCUMENT.md` — §10 TAPL
- `docs/EDTA_ARCHITECTURE_DOCUMENT.md` — §6.4 EML, §6.6 TAPL
- `config/tapl_policies.yaml` — one policy snippet (5–10 lines)

**Figure:** Optional EML before/after from demo UI screenshot

**Sidebar (healthcare, ~80 words):** HCP obesity education scenario; TAPL suppress on SMS/wearable; **not clinical DSS** — cite disclaimer from `EDTA_POSITIONING.md` §B.

---

## Section 7 — Explainability in the API contract (~250 words)

**Goal:** Give architects a checklist they can reuse.

**Write:**
- List fields every serious personalization API should expose:
  - `inference.tier`, `rules_fired[]`, `tapl.action`, `eds_score` breakdown, `outcome_simulation`, `explanation` + `explanation_source`
- Explanation router order: local template → SLM → LLM escalation.
- Why Problem+JSON errors + `request_id` matter for ops (one sentence).

**Pull from:**
- Article draft — Key takeaways (explainability bullet)
- `docs/EDTA_PUBLICATION_DOCUMENT.md` — §13 differentiation table (explainability row)

**Code block:** One `reason_codes` array example from a real response

---

## Section 8 — Travel vertical: empathy engine (~300 words)

**Goal:** Prove vertical extension without rewriting the core.

**Write:**
- Hidden needs extraction (elderly passenger, toddler family, mountain travel).
- Constraint matcher + TCO calculator + trained scenario profiles (11 scenarios).
- Benchmark result: 11/11 top-rank vehicle match on demo training set — **label as alignment proxy**.
- Link benchmark table to live demo “click row to try scenario.”

**Pull from:**
- `docs/TRAVEL_SCENARIO_SCORES.md`
- `docs/EDTA_PUBLICATION_DOCUMENT.md` — §8 Empathy engine
- `docs/EDTA_ARCHITECTURE_DOCUMENT.md` — §7

**Figure:** Screenshot of travel benchmark table from `/scenario-demo` OR condensed markdown table (5 rows max in article)

**Do not:** Claim production conversion lift.

---

## Section 9 — Comparison with alternative approaches (~250 words)

**Goal:** Preempt “how is this different from X?” reviewer questions.

**Write comparison table:**

| Approach | Limitation | EDTA pattern |
|----------|------------|--------------|
| LLM-first recommender | Cost, opacity, provider lock-in | Optional LLM tier; rules/ML default |
| Monolithic ranker | Single opaque score | EDS + TAPL + OSE + ranker modules |
| Rules-only CDP | No ML/LLM enrichment path | HAOE escalation ladder |
| Feature store + batch ML | Stateless scoring | EML + TKGE session memory |
| RAG personalization | Retrieval ≠ governance | TAPL modifies rank; audit in API |

**Pull from:**
- `docs/EDTA_PUBLICATION_DOCUMENT.md` — §13 Why EDTA is different

---

## Section 10 — Lessons learned & honest limits (~200 words)

**Goal:** InfoQ trusts authors who know what they don’t claim.

**Write — lessons (pick 4):**
1. LLMs should not own governance.
2. Explainability belongs in the API contract.
3. Per-scenario memory isolation matters for demos and tests.
4. ML saturation requires heuristic blend for meaningful benchmark spread.

**Write — limits (required):**
- Reference implementation; synthetic/demo training data
- No production A/B outcomes cited
- Healthcare: education routing only
- Hosted demo includes Render cold-start overhead

**Pull from:**
- `docs/EDTA_PUBLICATION_DOCUMENT.md` — §15–16

---

## Section 11 — Conclusion & resources (~150 words)

**Goal:** Clear next steps for readers.

**Write:**
- Restate thesis in one sentence.
- Links:
  - Demo: https://edta-api.onrender.com/scenario-demo
  - GitHub: https://github.com/jeraldcs/edta-complete-api
  - Benchmarks: `python scripts/load_test_tiers.py`
- Invite feedback and issues on GitHub.

---

## Figures to include (max 4 in article)

| # | Diagram | Source |
|---|---------|--------|
| 1 | Logical layer stack | `edta_architecture_diagrams_full.pdf` Fig 3 |
| 2 | HAOE four-tier routing | Fig 6 |
| 3 | Scenario demo path OR recommend sequence | Fig 5 or Fig 4 |
| 4 | Optional: API surface / deployment | Fig 9 or Fig 11 |

Export PNGs: `python docs/generate_architecture_diagrams_pdf.py` (assets in `docs/_architecture_pdf_assets/`).

---

## Writing process (recommended order)

1. Draft Sections 1–2 (problem) — 1 hour  
2. Insert Figure 3 + Section 3 — 45 min  
3. Run demo; capture real JSON for Section 4 — 1 hour  
4. Sections 5–6 (HAOE + TAPL) — 2 hours  
5. Sections 7–8 (API + travel) — 1 hour  
6. Sections 9–11 (comparison, limits, close) — 45 min  
7. Cut to 3,000 words; move extras to GitHub README — 1 hour  
8. Editorial pass: remove internal doc references (`docs/...` paths → reader-facing links)

---

## Mapping: outline section → repo files

| Outline § | Primary source files |
|-----------|---------------------|
| 1–2 | `docs/EDTA_POSITIONING.md`, `docs/edta_llm_personalization_article_draft.md` |
| 3 | `docs/EDTA_ARCHITECTURE_DOCUMENT.md`, `docs/edta_architecture_diagrams_full.pdf` |
| 4 | `app/services/recommendation_handlers.py`, `app/scenario_nlp.py`, live demo JSON |
| 5 | `app/orchestration.py`, `docs/BENCHMARKS.md`, `config/haoe_policies.yaml` |
| 6 | `app/ai/tapl_model.py`, `config/tapl_policies.yaml`, `app/experience_memory.py` |
| 7 | `app/inference/explanation_router.py`, OpenAPI `/v1/recommend` schema |
| 8 | `app/empathy/service.py`, `docs/TRAVEL_SCENARIO_SCORES.md` |
| 9–11 | `docs/EDTA_PUBLICATION_DOCUMENT.md` §13–16 |

---

## After InfoQ acceptance (optional follow-ups)

- **QCon talk** — same narrative + live demo (15–20 min architecture track)
- **InfoQ podcast** — 30-min interview on governed personalization
- **GitHub release tag** — pin commit referenced in published article
- **Add `CITATION.cff`** — for academic/industry citations
