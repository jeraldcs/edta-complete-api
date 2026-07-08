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
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 12, y + h - 20, title)
    c.setFillColor(PALETTE["muted"])
    c.setFont("Helvetica", 8.5)
    for index, line in enumerate(lines):
        c.drawString(x + 12, y + h - 36 - index * 13, line)


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
    c.setFont("Helvetica-Bold", 20)
    c.drawString(32, HEIGHT - 34, text)
    c.setFillColor(PALETTE["muted"])
    c.setFont("Helvetica", 9.5)
    c.drawString(32, HEIGHT - 50, subtitle)


def page_one(c):
    title(c, "EDTA Personalization API Architecture", "End-to-end runtime flow from browser context to ranked personalized content.")

    y_top = HEIGHT - 120
    box(c, 34, y_top, 150, 58, "Browser Demo", ["/demo, index.html"], "frontend")
    box(c, 34, y_top - 90, 150, 66, "static/app.js", ["Build visitor context", "scenario, events, channel"], "frontend")
    box(c, 238, y_top - 90, 150, 66, "POST /recommend", ["app/main.py", "route handler"], "api")
    box(c, 238, y_top - 188, 150, 66, "Pydantic Schema", ["app/models.py", "request and response"], "api")

    box(c, 444, y_top + 8, 188, 62, "RecommendationEngine", ["app/recommender.py"], "engine")
    box(c, 444, y_top - 86, 188, 62, "ContextGraph", ["keywords + context_text"], "engine")
    box(c, 444, y_top - 184, 188, 66, "Candidate Scoring", ["filter by channel", "score eligible candidates"], "engine")
    box(c, 444, y_top - 296, 86, 66, "EDS", ["intent, context", "business value"], "engine")
    box(c, 546, y_top - 296, 86, 66, "AI Modules", ["semantic, TAPL", "outcome, ranker"], "ai")
    box(c, 444, y_top - 398, 188, 64, "Ranked Recommendations", ["reason codes + explanation"], "engine")

    box(c, 682, y_top + 8, 118, 76, "OpenAI LLM", ["optional", "intent + explanation"], "llm")
    box(c, 682, y_top - 90, 118, 76, "Local AI Models", ["intent, journey", "joblib fallback"], "ai")
    box(c, 682, y_top - 188, 118, 62, "Catalog", ["app/catalog.py"], "data")

    box(c, 34, y_top - 398, 150, 64, "Personalized Page", ["hero, CTA, offer card"], "frontend")

    arrow(c, 109, y_top, 109, y_top - 24)
    arrow(c, 184, y_top - 57, 238, y_top - 57)
    arrow(c, 313, y_top - 90, 313, y_top - 122)
    arrow(c, 388, y_top - 155, 444, y_top + 38)
    arrow(c, 538, y_top + 8, 538, y_top - 24)
    arrow(c, 632, y_top + 39, 682, y_top + 39)
    arrow(c, 682, y_top - 52, 632, y_top - 52)
    arrow(c, 538, y_top - 86, 538, y_top - 118)
    arrow(c, 682, y_top - 157, 632, y_top - 151)
    arrow(c, 538, y_top - 184, 487, y_top - 230)
    arrow(c, 538, y_top - 184, 589, y_top - 230)
    arrow(c, 487, y_top - 296, 487, y_top - 334)
    arrow(c, 589, y_top - 296, 589, y_top - 334)
    arrow(c, 444, y_top - 366, 184, y_top - 366)

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(PALETTE["muted"])
    c.drawString(638, y_top + 52, "use_llm=true")
    c.drawString(636, y_top - 44, "fallback")


def page_two(c):
    title(c, "Layered Codebase View", "How folders and files map to responsibilities.")

    box(c, 58, 420, 166, 92, "Frontend Demo", ["static/index.html", "static/app.js", "static/styles.css"], "frontend")
    box(c, 306, 420, 166, 92, "API Layer", ["app/main.py", "/recommend", "/demo, /feedback"], "api")
    box(c, 554, 420, 166, 92, "Data Contracts", ["app/models.py", "CustomerContext", "RankedRecommendation"], "api")

    box(c, 306, 260, 166, 102, "Recommendation Core", ["app/recommender.py", "app/context_graph.py", "app/eds.py", "app/catalog.py"], "engine")

    box(c, 58, 82, 232, 118, "AI Modules", ["intent_model.py, journey_model.py", "tapl_model.py, channel_model.py", "semantic_similarity.py", "outcome_model.py, ranker_model.py"], "ai")
    box(c, 348, 82, 190, 118, "Optional LLM Layer", ["app/llm/llm_client.py", "OpenAI Responses API", "intent enrichment", "explanation generation"], "llm")
    box(c, 598, 82, 190, 118, "Data and Artifacts", ["data/*.csv", "models/*.joblib", "sample_requests/*.json", "scripts/train_all_models.py"], "data")

    arrow(c, 224, 466, 306, 466)
    arrow(c, 472, 466, 554, 466)
    arrow(c, 637, 420, 472, 340)
    arrow(c, 389, 260, 190, 200)
    arrow(c, 421, 260, 443, 200)
    arrow(c, 472, 310, 660, 200)
    arrow(c, 306, 310, 141, 420)

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(PALETTE["muted"])
    c.drawString(256, 478, "calls")
    c.drawString(502, 478, "validates")
    c.drawString(215, 238, "uses")
    c.drawString(446, 226, "optional")
    c.drawString(608, 242, "loads")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=landscape(letter))
    page_one(c)
    c.showPage()
    page_two(c)
    c.save()
    print(OUT.resolve())


if __name__ == "__main__":
    main()
