from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas


OUT = Path(__file__).with_name("edta_architecture_diagram.pdf")
WIDTH, HEIGHT = landscape(letter)


PALETTE = {
    "text": colors.HexColor("#102118"),
    "muted": colors.HexColor("#5d6c63"),
    "line": colors.HexColor("#cfd9d1"),
    "frontend": colors.HexColor("#eaf6ef"),
    "frontend_stroke": colors.HexColor("#1f7a52"),
    "api": colors.HexColor("#edf7fb"),
    "api_stroke": colors.HexColor("#21759f"),
    "engine": colors.HexColor("#fff7e7"),
    "engine_stroke": colors.HexColor("#bd7b13"),
    "ai": colors.HexColor("#f4f0ff"),
    "ai_stroke": colors.HexColor("#6c55a3"),
    "llm": colors.HexColor("#fff0f0"),
    "llm_stroke": colors.HexColor("#b84a4a"),
    "empathy": colors.HexColor("#e8f4ea"),
    "empathy_stroke": colors.HexColor("#2d6a4f"),
    "data": colors.HexColor("#f3f5f3"),
    "data_stroke": colors.HexColor("#6b746c"),
    "arrow": colors.HexColor("#53645a"),
}


def box(c, x, y, w, h, title, lines, kind):
    fill = PALETTE[kind]
    stroke = PALETTE[f"{kind}_stroke"]
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, 7, fill=1, stroke=1)
    c.setFillColor(PALETTE["text"])
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x + 10, y + h - 18, title)
    c.setFillColor(PALETTE["muted"])
    c.setFont("Helvetica", 8)
    for index, line in enumerate(lines):
        c.drawString(x + 10, y + h - 32 - index * 12, line)


def arrow(c, x1, y1, x2, y2):
    c.setStrokeColor(PALETTE["arrow"])
    c.setFillColor(PALETTE["arrow"])
    c.setLineWidth(1.15)
    c.line(x1, y1, x2, y2)
    dx = x2 - x1
    dy = y2 - y1
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux = dx / length
    uy = dy / length
    size = 6
    left = (x2 - ux * size - uy * size * 0.55, y2 - uy * size + ux * size * 0.55)
    right = (x2 - ux * size + uy * size * 0.55, y2 - uy * size - ux * size * 0.55)
    c.line(x2, y2, left[0], left[1])
    c.line(x2, y2, right[0], right[1])


def title(c, text, subtitle):
    c.setFillColor(PALETTE["text"])
    c.setFont("Helvetica-Bold", 18)
    c.drawString(32, HEIGHT - 34, text)
    c.setFillColor(PALETTE["muted"])
    c.setFont("Helvetica", 9)
    c.drawString(32, HEIGHT - 50, subtitle)


def page_one(c):
    """Scenario demo runtime — latest code path."""
    title(
        c,
        "EDTA Scenario Demo Runtime (July 2026)",
        "Free-text scenario → empathy-aware ranking → auditable JSON + architecture panels",
    )

    y = HEIGHT - 108
    box(c, 28, y, 128, 52, "scenario-demo UI", ["static/scenario.html", "scenario_app.js"], "frontend")
    box(c, 28, y - 72, 128, 58, "demo_html.py", ["inline __EDTA_DEMO_CONFIG__", "cache-bust assets"], "frontend")
    box(c, 178, y - 72, 132, 58, "POST /recommend-from-scenario", ["app/main.py", "recommendation_handlers"], "api")
    box(c, 178, y - 152, 132, 58, "ScenarioNLPParser", ["app/scenario_nlp.py", "channel, intent, consent"], "api")
    box(c, 178, y - 232, 132, 58, "scenario_anonymous_id", ["per-profile EML/TKGE subject", "empathy/scenario_profiles"], "api")

    box(c, 338, y + 4, 148, 56, "ProfileLookupService", ["profile_service.py", "cust-789 JSON adapter"], "data")
    box(c, 338, y - 72, 148, 58, "Experience Memory (EML)", ["experience_memory.py", "eml_store.py — trust/fatigue"], "data")
    box(c, 338, y - 152, 148, 58, "ContextGraph (TKGE)", ["context_graph.py", "graph_store.py timeline"], "engine")
    box(c, 338, y - 232, 148, 58, "HAOE orchestrator", ["orchestration.py", "Rules → SLM → ML → LLM"], "ai")

    box(c, 514, y + 4, 148, 56, "EmpathyEngine", ["empathy/service.py", "hidden needs + TCO"], "empathy")
    box(c, 514, y - 72, 148, 58, "Scenario profiles", ["trained_scenarios.yaml", "11 travel archetypes"], "empathy")
    box(c, 514, y - 152, 148, 58, "Vehicle catalog", ["vehicle_candidates()", "constraint matcher"], "empathy")

    box(c, 690, y - 8, 118, 64, "RecommendationEngine", ["app/recommender.py", "rank loop"], "engine")
    box(c, 690, y - 92, 118, 56, "EDS + Semantic", ["eds.py, semantic_similarity"], "engine")
    box(c, 690, y - 168, 118, 56, "TAPL + OSE", ["tapl_model, outcome_model"], "ai")
    box(c, 690, y - 244, 118, 56, "Ranker + empathy boost", ["ranker_model.py", "ai vs final_hybrid"], "engine")

    box(c, 514, y - 320, 294, 52, "Response JSON", ["request_summary, empathy panels", "TKGE/EML/HAOE/OSE/TAPL cards"], "api")
    box(c, 28, y - 320, 280, 52, "GET /travel-scenario-benchmark", ["travel_benchmark.py — 11 scenario matrix"], "api")

    arrow(c, 92, y, 92, y - 14)
    arrow(c, 156, y - 43, 178, y - 43)
    arrow(c, 244, y - 72, 244, y - 94)
    arrow(c, 244, y - 152, 244, y - 174)
    arrow(c, 310, y - 201, 338, y - 123)
    arrow(c, 310, y - 201, 338, y - 43)
    arrow(c, 414, y - 152, 414, y - 174)
    arrow(c, 486, y - 201, 514, y - 43)
    arrow(c, 662, y - 43, 690, y - 43)
    arrow(c, 749, y - 92, 749, y - 112)
    arrow(c, 749, y - 168, 749, y - 188)
    arrow(c, 749, y - 244, 661, y - 294)
    arrow(c, 514, y - 232, 690, y - 212)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(PALETTE["muted"])
    c.drawString(318, y - 118, "enrich")
    c.drawString(468, y - 188, "graph + tier")
    c.drawString(620, y - 218, "merge candidates")


def page_two(c):
    """Layered codebase map — current repository layout."""
    title(c, "EDTA Codebase Layer Map", "How app/, config/, static/, and tests map to architecture responsibilities.")

    box(c, 40, 418, 155, 88, "Demo & static", ["static/scenario.html", "scenario_app.js, demo-shared.js", "app/demo_html.py"], "frontend")
    box(c, 230, 418, 155, 88, "API surface", ["app/main.py", "app/api/v1/router.py", "services/recommendation_handlers.py"], "api")
    box(c, 420, 418, 155, 88, "Contracts", ["app/models.py", "app/api/schemas.py", "CustomerContext, TAPL, OSE"], "api")
    box(c, 610, 418, 155, 88, "Container & config", ["app/container.py", "app/config.py", "config/*.yaml"], "data")

    box(c, 135, 268, 200, 96, "Recommendation core", ["recommender.py", "context_graph.py (TKGE)", "eds.py, catalog.py"], "engine")
    box(c, 375, 268, 200, 96, "Memory & audit", ["experience_memory.py, eml_store.py", "graph_store.py, tapl_audit.py", "rules_audit.py"], "data")
    box(c, 615, 268, 150, 96, "Orchestration", ["orchestration.py (HAOE)", "haoe_policy.py", "inference/explanation_router.py"], "ai")

    box(c, 40, 118, 175, 108, "AI modules", ["ai/intent_model.py", "journey_model, tapl_model", "outcome_model, ranker_model", "semantic_similarity, channel_model"], "ai")
    box(c, 245, 118, 175, 108, "Empathy (travel)", ["empathy/service.py", "hidden_needs, scenario_profiles", "constraint_matcher, tco_calculator", "trained_scenarios.py"], "empathy")
    box(c, 450, 118, 155, 108, "Optional LLM", ["llm/llm_client.py", "slm_client.py", "prompt_templates.py"], "llm")
    box(c, 635, 118, 130, 108, "Ops & tests", ["tests/ (149+)", "scripts/benchmark_*", "render.yaml"], "data")

    arrow(c, 195, 462, 230, 462)
    arrow(c, 385, 462, 420, 462)
    arrow(c, 575, 462, 610, 462)
    arrow(c, 687, 418, 515, 364)
    arrow(c, 305, 418, 235, 364)
    arrow(c, 475, 268, 235, 226)
    arrow(c, 335, 268, 420, 226)
    arrow(c, 575, 268, 690, 226)
    arrow(c, 215, 268, 332, 226)


def page_three(c):
    """HAOE four-tier + empathy pipeline."""
    title(c, "HAOE Four-Tier Inference + Empathy Pipeline", "Governed AI routing and travel vertical extension.")

    tiers = [
        ("Rules", "YAML packs + EDS + TKGE", "rules_engine.py"),
        ("SLM", "distilled memory + slm_client", "distilled_slm_provider.py"),
        ("ML", "sklearn intent/journey/TAPL/ranker", "inference/ml_service.py"),
        ("LLM", "optional teacher — budget gated", "llm/llm_client.py"),
    ]
    x0, tw, th, gap = 36, 168, 72, 22
    y_t = HEIGHT - 130
    for i, (name, desc, path) in enumerate(tiers):
        x = x0 + i * (tw + gap)
        kind = "llm" if name == "LLM" else "ai" if name == "ML" else "engine" if name == "Rules" else "api"
        box(c, x, y_t, tw, th, name, [desc, path], kind)
        if i < len(tiers) - 1:
            arrow(c, x + tw, y_t + th // 2, x + tw + gap, y_t + th // 2)

    box(c, 36, y_t - 100, 320, 58, "InferenceResult contract", ["tier, confidence, rules_fired, cost_units", "app/inference/contracts.py"], "api")
    arrow(c, 196, y_t, 196, y_t - 42)

    box(c, 380, y_t - 100, 385, 58, "RecommendationEngine consumes tier", ["intent/journey enrichment", "explanation_router — SLM first"], "engine")

    y_e = y_t - 220
    box(c, 36, y_e, 118, 64, "Scenario text", ["free-text input"], "frontend")
    box(c, 170, y_e, 118, 64, "Hidden needs", ["hidden_needs.yaml", "word-boundary rules"], "empathy")
    box(c, 304, y_e, 118, 64, "Profile match", ["scenario_profiles.yaml", "11 trained profiles"], "empathy")
    box(c, 438, y_e, 118, 64, "Route + TCO", ["route_planner, tco_calculator"], "empathy")
    box(c, 572, y_e, 118, 64, "Constraints", ["AWD, ISOFIX, EV range", "constraint_matcher.py"], "empathy")
    box(c, 706, y_e, 60, 64, "Vehicle", ["empathy vehicle", "+ pitch"], "empathy")

    for x1, x2 in [(154, 170), (288, 304), (422, 438), (556, 572), (690, 706)]:
        arrow(c, x1, y_e + 32, x2, y_e + 32)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(PALETTE["muted"])
    c.drawString(36, y_e - 18, "Empathy output merges into business_context → empathy boost in recommender.py")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=landscape(letter))
    page_one(c)
    c.showPage()
    page_two(c)
    c.showPage()
    page_three(c)
    c.save()
    print(OUT.resolve())


if __name__ == "__main__":
    main()
