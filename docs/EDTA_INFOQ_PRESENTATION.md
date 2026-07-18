# EDTA — InfoQ / Architecture Conference Deck

**Talk title:** Why Did We Show This? Designing Auditable Recommendation Systems  
**Article title (InfoQ):** Governed Personalization: Why Trust Must Change the Rank, Not Just the Log  
**Technical title:** Beyond LLM-First Recommendations: A Four-Tier Architecture for Trust-Aware Ranking  
**File:** `docs/EDTA_INFOQ_PRESENTATION_latest.pptx` — **20 slides**  
**Regenerate:** `python docs/generate_infoq_presentation.py`  
**Length:** ~25–30 minutes + Q&A  
**Speaker:** Jerald Selvaraj · jerald.cs@gmail.com

**Keep open during the talk**
- Live demo: https://edta-api.onrender.com/scenario-demo  
- FAQ: `docs/FAQ.md`  
- Traditional vs EDTA: `docs/TRADITIONAL_VS_EDTA.md`

---

## Slide map

| # | Slide | Section | Speak for |
|---|--------|---------|-----------|
| 1 | Title | Opening | 30s |
| 2 | Agenda | Overview | 45s |
| 3 | Part 01 — The Problem | Divider | 10s |
| 4 | Familiar failure story | Problem | 2 min |
| 5 | Anti-pattern + 6 gaps | Problem | 2 min |
| 6 | Part 02 — Architecture | Divider | 10s |
| 7 | What EDTA is | Architecture | 1.5 min |
| 8 | End-to-end flow | Architecture | 2 min |
| 9 | HAOE four tiers | Architecture | 2 min |
| 10 | EDS / OSE / TAPL | Architecture | 2.5 min |
| 11 | Part 03 — Benefits | Divider | 10s |
| 12 | Benefits at a glance | Benefits | 2 min |
| 13 | Benefit → capability map | Benefits | 2 min |
| 14 | Traditional vs EDTA | Benefits | 2 min |
| 15 | Multi-industry | Benefits | 1.5 min |
| 16 | Part 04 — Evidence & Use | Divider | 10s |
| 17 | Evidence & live demo | Evidence | 3–5 min (live) |
| 18 | How to integrate | How to use | 2 min |
| 19 | Lessons for architects | Takeaways | 1.5 min |
| 20 | Resources & Q&A | Close | — |

---

## Speaker notes (by section)

### Problem (slides 3–5)
- Lead with the family SUV airport story — not feature lists.
- Thesis: **Personalization is a governance problem, not only a ranking problem.**
- Call out the six gaps: opaque ranking, trust as metadata, LLM cost, single-channel, click-only, vertical rewrite.

### Architecture (slides 6–10)
- Define EDTA once; walk the 7-step flow left to right.
- Stress: TAPL is **inside** the rank loop.
- HAOE: Rules/SLM/ML default; LLM optional and budget-gated.
- Design rule: LLM enriches and explains — does not own consent/compliance.

### Benefits (slides 11–15)
- Three columns: Engineering / Business / Trust.
- Map each benefit to a concrete capability (slide 13).
- Traditional vs EDTA: “completes traditional — does not discard it.”
- Healthcare disclaimer: HCP education, not clinical DSS.

### Evidence & use (slides 16–20)
- Live demo path: loyalty → no consent → fatigue → compare chips → Scoring Signals.
- Honesty: alignment proxy, not production A/B lift.
- Integration: `/v1/recommend`, API key, persist `request_id` + TAPL + tier.
- Close on six architect lessons; leave resources on screen for Q&A.

---

## Suggested live demo sequence (slide 17)

1. Default loyalty family SUV  
2. **No consent** chip → `generic_fallback`  
3. **High fatigue** chip → `delay`  
4. Optional: **Compare vs traditional** → Rules-era or ML ranker  
5. Expand Technical details → **3. Scoring Signals**

---

## Tip for InfoQ / QCon audiences

Architects care more about **decision boundaries and contracts** than vehicle catalogs. Spend time on slides 5, 8, 10, and 13; keep travel as the concrete hero example, not the whole story.
