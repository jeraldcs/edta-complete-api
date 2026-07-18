"""
Generate a conference-quality InfoQ / architecture PowerPoint for EDTA.

Covers: problem → architecture → benefits → evidence → integration → takeaways.

Output:
    docs/EDTA_INFOQ_PRESENTATION.pptx

Usage:
    python docs/generate_infoq_presentation.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "EDTA_INFOQ_PRESENTATION.pptx"

# Brand (aligned with demo UI — not purple-gradient AI cliché)
NAVY = RGBColor(0x17, 0x32, 0x4D)
BLUE = RGBColor(0x2F, 0x6F, 0x9F)
TEAL = RGBColor(0x1F, 0x7A, 0x4D)
AMBER = RGBColor(0xB8, 0x86, 0x0B)
AMBER_DARK = RGBColor(0x7A, 0x4D, 0x00)
SLATE = RGBColor(0x34, 0x40, 0x54)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF4, 0xF8, 0xFB)
CARD = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x66, 0x70, 0x85)
LINE = RGBColor(0xD7, 0xE3, 0xEF)
SOFT_AMBER = RGBColor(0xFF, 0xFB, 0xF3)
SOFT_TEAL = RGBColor(0xF0, 0xF8, 0xF3)
SOFT_BLUE = RGBColor(0xED, 0xF4, 0xFB)

W = Inches(13.333)
H = Inches(7.5)


def _run(paragraph, text: str, size: int, color: RGBColor, bold: bool = False) -> None:
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = "Calibri"


def _rect(slide, left, top, width, height, fill: RGBColor, line: RGBColor | None = None):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
    return shape


def _round(slide, left, top, width, height, fill: RGBColor, line: RGBColor | None = None):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
    # Slight corner radius
    try:
        shape.adjustments[0] = 0.08
    except Exception:
        pass
    return shape


def _bg(slide, color: RGBColor = LIGHT) -> None:
    shape = _rect(slide, 0, 0, W, H, color)
    sp_tree = slide.shapes._spTree
    el = shape._element
    sp_tree.remove(el)
    sp_tree.insert(2, el)


def _accent(slide, color: RGBColor = BLUE) -> None:
    _rect(slide, 0, 0, Inches(0.14), H, color)


def _footer(slide, page: int, total: int, section: str = "") -> None:
    label = f"EDTA  ·  Governed Personalization"
    if section:
        label += f"  ·  {section}"
    label += f"  ·  {page}/{total}"
    box = slide.shapes.add_textbox(Inches(0.45), Inches(7.08), Inches(12.4), Inches(0.28))
    p = box.text_frame.paragraphs[0]
    _run(p, label, 10, MUTED)


def _title(slide, text: str, top=Inches(0.32)) -> None:
    box = slide.shapes.add_textbox(Inches(0.45), top, Inches(12.4), Inches(0.55))
    p = box.text_frame.paragraphs[0]
    _run(p, text, 28, NAVY, bold=True)


def _subtitle(slide, text: str, top=Inches(0.88)) -> None:
    box = slide.shapes.add_textbox(Inches(0.45), top, Inches(12.4), Inches(0.4))
    p = box.text_frame.paragraphs[0]
    _run(p, text, 14, MUTED)


def _textbox(slide, left, top, width, height, lines: list[tuple[str, int, RGBColor, bool]], *, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, (text, size, color, bold) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(4)
        _run(p, text, size, color, bold)
    return box


def section_divider(prs: Presentation, number: str, title: str, blurb: str, page: int, total: int, color: RGBColor) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(slide, 0, 0, W, H, NAVY)
    _rect(slide, 0, 0, Inches(0.2), H, color)
    _textbox(
        slide,
        Inches(0.8),
        Inches(2.2),
        Inches(11.5),
        Inches(2.5),
        [
            (f"PART {number}", 14, color, True),
            (title, 40, WHITE, True),
            (blurb, 18, RGBColor(0xC5, 0xD4, 0xE3), False),
        ],
    )
    _textbox(
        slide,
        Inches(0.8),
        Inches(6.9),
        Inches(11),
        Inches(0.3),
        [(f"{page}/{total}", 11, RGBColor(0x9E, 0xB8, 0xCF), False)],
    )


def title_slide(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(slide, 0, 0, W, H, NAVY)
    _rect(slide, 0, Inches(5.85), W, Inches(1.65), BLUE)

    _textbox(
        slide,
        Inches(0.7),
        Inches(1.35),
        Inches(12),
        Inches(0.4),
        [("INFOQ / ARCHITECTURE TALK", 12, RGBColor(0x9E, 0xB8, 0xCF), True)],
    )
    _textbox(
        slide,
        Inches(0.7),
        Inches(1.7),
        Inches(12),
        Inches(1.4),
        [("Why Did We Show This?", 36, WHITE, True)],
    )
    _textbox(
        slide,
        Inches(0.7),
        Inches(3.15),
        Inches(12),
        Inches(1.1),
        [
            ("Designing Auditable Recommendation Systems", 22, RGBColor(0xD7, 0xE3, 0xEF), False),
            (
                "Problem → Architecture → Benefits  ·  Trust must change the rank, not just the log",
                15,
                RGBColor(0x9E, 0xB8, 0xCF),
                False,
            ),
        ],
    )
    _textbox(
        slide,
        Inches(0.7),
        Inches(6.05),
        Inches(12),
        Inches(1.15),
        [
            ("Experience-Driven Targeting Architecture (EDTA)", 16, WHITE, True),
            ("Jerald Selvaraj  ·  jerald.cs@gmail.com  ·  Open-source reference implementation", 13, WHITE, False),
            ("Demo: edta-api.onrender.com/scenario-demo   ·   github.com/jeraldcs/edta-complete-api", 12, RGBColor(0xD7, 0xE3, 0xEF), False),
        ],
    )


def agenda_slide(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, BLUE)
    _title(slide, "Agenda")
    _subtitle(slide, "What we will cover in this talk")

    items = [
        ("01", "The Problem", "Why context → model → rank fails enterprises"),
        ("02", "Architecture", "HAOE, TAPL, EML, TKGE, EDS, OSE — how they fit"),
        ("03", "Benefits", "Engineering, business, compliance, and multi-industry value"),
        ("04", "Evidence & Demo", "Live travel scenarios, benchmarks, honest limits"),
        ("05", "How to Use", "Integrate the API, adapt policy, next steps"),
    ]
    for i, (num, head, desc) in enumerate(items):
        y = Inches(1.45 + i * 1.0)
        _round(slide, Inches(0.5), y, Inches(12.3), Inches(0.88), CARD, LINE)
        _textbox(slide, Inches(0.75), y + Inches(0.18), Inches(1.0), Inches(0.55), [(num, 22, BLUE, True)])
        _textbox(slide, Inches(1.9), y + Inches(0.12), Inches(10), Inches(0.35), [(head, 18, NAVY, True)])
        _textbox(slide, Inches(1.9), y + Inches(0.45), Inches(10), Inches(0.3), [(desc, 13, MUTED, False)])
    _footer(slide, page, total, "Overview")


def problem_story(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, AMBER_DARK)
    _title(slide, "A familiar failure story")
    _subtitle(slide, "Travel booking — high intent, wrong offer timing")

    _round(slide, Inches(0.5), Inches(1.45), Inches(7.6), Inches(5.1), SOFT_AMBER, RGBColor(0xE6, 0xD4, 0xA8))
    _textbox(
        slide,
        Inches(0.8),
        Inches(1.7),
        Inches(7.0),
        Inches(4.5),
        [
            ("Scenario", 12, AMBER_DARK, True),
            ("A family traveler searches for an airport SUV rental.", 16, SLATE, False),
            ("They move research → consideration → booking in one session.", 16, SLATE, False),
            ("", 10, SLATE, False),
            ("What goes wrong with a black-box ranker", 12, AMBER_DARK, True),
            ("• Right vehicle, wrong moment (already fatigued by banners)", 15, SLATE, False),
            ("• Right offer, wrong channel (SMS / push vs web)", 15, SLATE, False),
            ("• Personalization continues when consent is false", 15, SLATE, False),
            ("• No one can answer “why this offer?” from the API", 15, SLATE, False),
            ("• LLM path adds cost without governance guarantees", 15, SLATE, False),
        ],
    )

    _round(slide, Inches(8.4), Inches(1.45), Inches(4.4), Inches(5.1), NAVY)
    _textbox(
        slide,
        Inches(8.7),
        Inches(1.9),
        Inches(3.8),
        Inches(4.2),
        [
            ("Thesis", 12, AMBER, True),
            ("Personalization is a governance problem — not only a ranking problem.", 20, WHITE, True),
            ("", 12, WHITE, False),
            ("Relevance without trust, explainability, and cost control is enterprise risk.", 15, RGBColor(0xD7, 0xE3, 0xEF), False),
        ],
    )
    _footer(slide, page, total, "Problem")


def problem_anti_pattern(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, AMBER_DARK)
    _title(slide, "The anti-pattern enterprises still ship")
    _subtitle(slide, "A single model hides decisions that must be auditable")

    # Flow boxes
    boxes = [
        (0.5, "Customer\nContext"),
        (3.7, "One Model\n/ Prompt"),
        (6.9, "Ranked\nOffer"),
        (10.1, "Hope &\nDashboards"),
    ]
    for x, label in boxes:
        _round(slide, Inches(x), Inches(1.55), Inches(2.6), Inches(1.35), NAVY)
        box = slide.shapes.add_textbox(Inches(x), Inches(1.75), Inches(2.6), Inches(1.0))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        _run(p, label.replace("\n", " "), 16, WHITE, True)

    for x in (3.15, 6.35, 9.55):
        arrow = slide.shapes.add_textbox(Inches(x), Inches(1.95), Inches(0.5), Inches(0.5))
        p = arrow.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        _run(p, "→", 22, BLUE, True)

    gaps = [
        ("Opaque ranking", "Cannot answer why in incidents or reviews"),
        ("Trust as metadata", "Consent / fatigue logged, not enforced in rank"),
        ("LLM-first cost", "Unbounded latency, tokens, provider lock-in"),
        ("Single-channel thinking", "Web rules break on chatbot, SMS, IoT"),
        ("Click-only optimization", "No expected outcome / trust risk before show"),
        ("Vertical rewrite", "Each industry rebuilds the engine"),
    ]
    for i, (h, d) in enumerate(gaps):
        col = i % 3
        row = i // 3
        x = Inches(0.5 + col * 4.2)
        y = Inches(3.3 + row * 1.55)
        _round(slide, x, y, Inches(4.0), Inches(1.4), CARD, LINE)
        _textbox(slide, x + Inches(0.2), y + Inches(0.25), Inches(3.6), Inches(0.35), [(h, 15, AMBER_DARK, True)])
        _textbox(slide, x + Inches(0.2), y + Inches(0.65), Inches(3.6), Inches(0.55), [(d, 13, SLATE, False)])
    _footer(slide, page, total, "Problem")


def what_is_edta(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, BLUE)
    _title(slide, "What EDTA is")
    _subtitle(slide, "Experience-Driven Targeting Architecture — open reference implementation")

    _round(slide, Inches(0.5), Inches(1.4), Inches(12.3), Inches(1.35), SOFT_BLUE, LINE)
    _textbox(
        slide,
        Inches(0.75),
        Inches(1.6),
        Inches(11.8),
        Inches(1.0),
        [
            (
                "A governed decision pipeline for personalization: Rules, SLM, ML, and optional LLM under explicit orchestration — with trust policy inside ranking and explainability in every API response.",
                16,
                NAVY,
                False,
            )
        ],
    )

    layers = [
        ("HAOE", "Hybrid AI Orchestration", "Routes Rules → SLM → ML → LLM with cost budget"),
        ("TAPL", "Trust-Aware Layer", "show / soften / delay / suppress in the rank"),
        ("EML + TKGE", "Memory & Journey", "Trust, fatigue, preferences, timeline"),
        ("EDS + OSE", "Score & Outcome", "Explainable relevance + conversion sim"),
    ]
    for i, (code, name, desc) in enumerate(layers):
        x = Inches(0.5 + i * 3.2)
        _round(slide, x, Inches(3.1), Inches(3.0), Inches(3.3), CARD, LINE)
        _rect(slide, x, Inches(3.1), Inches(3.0), Inches(0.55), BLUE)
        _textbox(slide, x + Inches(0.15), Inches(3.2), Inches(2.7), Inches(0.4), [(code, 16, WHITE, True)], align=PP_ALIGN.CENTER)
        _textbox(slide, x + Inches(0.15), Inches(3.85), Inches(2.7), Inches(0.7), [(name, 14, NAVY, True)], align=PP_ALIGN.CENTER)
        _textbox(slide, x + Inches(0.2), Inches(4.6), Inches(2.6), Inches(1.5), [(desc, 13, SLATE, False)], align=PP_ALIGN.CENTER)

    _footer(slide, page, total, "Architecture")


def architecture_flow(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, BLUE)
    _title(slide, "End-to-end architecture flow")
    _subtitle(slide, "Every step is explicit, testable, and visible in the API")

    steps = [
        ("1", "Context", "NLP + profile\n+ consent"),
        ("2", "Memory", "EML trust &\nfatigue"),
        ("3", "Journey", "TKGE\ntimeline"),
        ("4", "Orchestrate", "HAOE tier\nselection"),
        ("5", "Score", "EDS + OSE\nper candidate"),
        ("6", "Govern", "TAPL action\nin rank"),
        ("7", "Respond", "Explain +\nlearn"),
    ]
    for i, (n, h, d) in enumerate(steps):
        x = Inches(0.35 + i * 1.85)
        _round(slide, x, Inches(1.55), Inches(1.7), Inches(2.55), CARD, LINE)
        circ = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, x + Inches(0.55), Inches(1.7), Inches(0.55), Inches(0.55))
        circ.fill.solid()
        circ.fill.fore_color.rgb = BLUE
        circ.line.fill.background()
        tb = slide.shapes.add_textbox(x + Inches(0.55), Inches(1.78), Inches(0.55), Inches(0.45))
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        _run(p, n, 14, WHITE, True)
        _textbox(slide, x + Inches(0.08), Inches(2.4), Inches(1.55), Inches(0.4), [(h, 13, NAVY, True)], align=PP_ALIGN.CENTER)
        box = slide.shapes.add_textbox(x + Inches(0.08), Inches(2.85), Inches(1.55), Inches(1.0))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        _run(p, d.replace("\n", " "), 11, MUTED, False)

    _round(slide, Inches(0.5), Inches(4.4), Inches(12.3), Inches(2.2), SOFT_BLUE, LINE)
    _textbox(
        slide,
        Inches(0.75),
        Inches(4.6),
        Inches(11.8),
        Inches(1.8),
        [
            ("Design rule", 12, BLUE, True),
            ("The LLM enriches and explains. It does not own consent, compliance, fatigue, or final trust governance.", 16, NAVY, True),
            ("Policy lives in YAML (TAPL, HAOE, industry rules). Ranking modules stay independently testable.", 14, SLATE, False),
            ("Implementation: FastAPI · Python · SQLite audit/memory · OpenAPI · 167 automated tests", 14, SLATE, False),
        ],
    )
    _footer(slide, page, total, "Architecture")


def haoe_slide(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, BLUE)
    _title(slide, "HAOE — four-tier inference routing")
    _subtitle(slide, "Hybrid AI Orchestration Engine: right model for the request, not LLM for everything")

    tiers = [
        ("Rules", "< 50 ms", "~0 cost", "Structured booking context, auditable intent/journey", BLUE),
        ("SLM", "< 100 ms", "Low", "Distilled patterns for repeated “family SUV airport” journeys", TEAL),
        ("ML", "< 300 ms", "Medium", "Catalog-aligned classifiers for intent, TAPL, outcome, rank", AMBER_DARK),
        ("LLM", "Seconds", "Highest", "Ambiguous chatbot text + explanations — optional & budget-gated", NAVY),
    ]
    for i, (name, lat, cost, desc, color) in enumerate(tiers):
        y = Inches(1.4 + i * 1.25)
        _round(slide, Inches(0.5), y, Inches(12.3), Inches(1.12), CARD, LINE)
        _rect(slide, Inches(0.5), y, Inches(0.18), Inches(1.12), color)
        _textbox(slide, Inches(0.9), y + Inches(0.18), Inches(1.8), Inches(0.35), [(name, 18, NAVY, True)])
        _textbox(slide, Inches(2.9), y + Inches(0.22), Inches(2.2), Inches(0.3), [(lat, 13, BLUE, True)])
        _textbox(slide, Inches(5.2), y + Inches(0.22), Inches(1.8), Inches(0.3), [(cost, 13, MUTED, True)])
        _textbox(slide, Inches(7.1), y + Inches(0.18), Inches(5.4), Inches(0.75), [(desc, 13, SLATE, False)])
    _footer(slide, page, total, "Architecture")


def tapl_eds_slide(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, TEAL)
    _title(slide, "Scoring + governance inside the loop")
    _subtitle(slide, "EDS explains relevance · OSE predicts outcome · TAPL changes the final rank")

    # Left EDS/OSE
    _round(slide, Inches(0.45), Inches(1.4), Inches(6.1), Inches(5.2), CARD, LINE)
    _rect(slide, Inches(0.45), Inches(1.4), Inches(6.1), Inches(0.55), BLUE)
    _textbox(slide, Inches(0.65), Inches(1.5), Inches(5.7), Inches(0.4), [("EDS + Outcome Simulation", 16, WHITE, True)])
    _textbox(
        slide,
        Inches(0.7),
        Inches(2.2),
        Inches(5.6),
        Inches(4.1),
        [
            ("Experience DNA Score (EDS)", 14, NAVY, True),
            ("Intent · engagement · business value · journey · context − risk", 13, SLATE, False),
            ("", 8, SLATE, False),
            ("Outcome Simulation (OSE)", 14, NAVY, True),
            ("Conversion probability · revenue impact · trust/fatigue risk", 13, SLATE, False),
            ("", 8, SLATE, False),
            ("Final hybrid rank blends", 14, NAVY, True),
            ("EDS + semantic + channel fit + trust + outcome", 13, SLATE, False),
            ("+ empathy / preference boosts (travel)", 13, SLATE, False),
            ("", 8, SLATE, False),
            ("All of this is returned in the recommendation JSON.", 13, MUTED, False),
        ],
    )

    # Right TAPL
    _round(slide, Inches(6.8), Inches(1.4), Inches(6.0), Inches(5.2), CARD, LINE)
    _rect(slide, Inches(6.8), Inches(1.4), Inches(6.0), Inches(0.55), TEAL)
    _textbox(slide, Inches(7.0), Inches(1.5), Inches(5.6), Inches(0.4), [("TAPL — Trust-Aware Policy", 16, WHITE, True)])

    actions = [
        ("show", "Normal personalized offer"),
        ("soften", "Tone down aggressive upsell"),
        ("delay", "Hold when fatigue is high (~×0.55 score)"),
        ("suppress", "Block sensitive channel/content"),
        ("generic_fallback", "No consent → non-personalized path"),
    ]
    y = Inches(2.2)
    for act, desc in actions:
        _textbox(slide, Inches(7.1), y, Inches(5.5), Inches(0.28), [(act, 14, TEAL, True)])
        _textbox(slide, Inches(7.1), y + Inches(0.28), Inches(5.5), Inches(0.28), [(desc, 12, SLATE, False)])
        y += Inches(0.58)
    _footer(slide, page, total, "Architecture")


def benefits_overview(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, TEAL)
    _title(slide, "Benefits at a glance")
    _subtitle(slide, "Why teams adopt a governed pipeline instead of another black-box model")

    cards = [
        ("Engineering", BLUE, [
            "Modular, testable layers (167 tests)",
            "Cost control via HAOE budgets",
            "Runs without OpenAI (LLM optional)",
            "Policy as YAML — no ranker rewrites",
            "OpenAPI + request_id correlation",
        ]),
        ("Business / Product", AMBER_DARK, [
            "Outcome-aware ranking (OSE)",
            "Fatigue-aware engagement",
            "Journey-fit upsell (TKGE + empathy)",
            "Compare offers before A/B tests",
            "Faster vertical experiments",
        ]),
        ("Trust / Compliance", TEAL, [
            "Consent enforced in ranking",
            "Channel sensitivity controls",
            "Auditable TAPL decisions",
            "Explainability in every response",
            "Clear healthcare scope boundaries",
        ]),
    ]
    for i, (title, color, items) in enumerate(cards):
        x = Inches(0.45 + i * 4.25)
        _round(slide, x, Inches(1.4), Inches(4.05), Inches(5.2), CARD, LINE)
        _rect(slide, x, Inches(1.4), Inches(4.05), Inches(0.65), color)
        _textbox(slide, x + Inches(0.2), Inches(1.52), Inches(3.65), Inches(0.45), [(title, 18, WHITE, True)], align=PP_ALIGN.CENTER)
        y = Inches(2.3)
        for item in items:
            _textbox(slide, x + Inches(0.25), y, Inches(3.55), Inches(0.55), [(f"•  {item}", 13, SLATE, False)])
            y += Inches(0.7)
    _footer(slide, page, total, "Benefits")


def benefits_deep(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, TEAL)
    _title(slide, "Benefit → capability mapping")
    _subtitle(slide, "Concrete mechanisms behind each claim")

    rows = [
        ("Answer “why this offer?”", "EDS breakdown, rules fired, TAPL reason, explanation_source"),
        ("Stop over-messaging", "EML fatigue + TAPL delay/soften"),
        ("Honor consent", "TAPL generic_fallback when personalization=false"),
        ("Control LLM spend", "HAOE tier routing, session cost budget, circuit breaker"),
        ("Improve offer fit", "Empathy constraints + OSE expected outcome"),
        ("Reuse across industries", "Same engine; swap catalog + YAML policy packs"),
        ("Ship with confidence", "CI, OpenAPI contracts, demo + benchmark scripts"),
    ]
    _round(slide, Inches(0.45), Inches(1.35), Inches(12.4), Inches(5.3), CARD, LINE)
    # header
    _rect(slide, Inches(0.45), Inches(1.35), Inches(12.4), Inches(0.5), NAVY)
    _textbox(slide, Inches(0.7), Inches(1.45), Inches(4.5), Inches(0.35), [("Benefit", 13, WHITE, True)])
    _textbox(slide, Inches(5.4), Inches(1.45), Inches(7.0), Inches(0.35), [("EDTA capability", 13, WHITE, True)])

    for i, (b, c) in enumerate(rows):
        y = Inches(1.95 + i * 0.62)
        bg = LIGHT if i % 2 == 0 else WHITE
        _rect(slide, Inches(0.45), y, Inches(12.4), Inches(0.62), bg)
        _textbox(slide, Inches(0.7), y + Inches(0.15), Inches(4.5), Inches(0.4), [(b, 13, NAVY, True)])
        _textbox(slide, Inches(5.4), y + Inches(0.15), Inches(7.1), Inches(0.4), [(c, 13, SLATE, False)])
    _footer(slide, page, total, "Benefits")


def traditional_vs(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, AMBER_DARK)
    _title(slide, "Traditional architectures vs EDTA")
    _subtitle(slide, "EDTA does not discard what worked — it completes it for AI-era governance")

    headers = ["Pattern", "What it does well", "Where it breaks", "EDTA upgrade"]
    widths = [2.4, 3.0, 3.2, 3.4]
    x0 = 0.45
    _rect(slide, Inches(x0), Inches(1.35), Inches(12.4), Inches(0.5), NAVY)
    x = x0
    for h, w in zip(headers, widths):
        _textbox(slide, Inches(x + 0.1), Inches(1.45), Inches(w - 0.1), Inches(0.35), [(h, 12, WHITE, True)])
        x += w

    data = [
        ("Rules engine", "Fast, auditable", "Brittle NLP / memory", "Keep rules as tier-1"),
        ("Monolithic ML", "Catalog match", "Opaque; no consent in rank", "EDS + TAPL + OSE"),
        ("LLM bolt-on", "Handles ambiguity", "Cost + weak audit", "Optional, budget-gated"),
        ("CRM segments", "Batch targeting", "Stateless live decisions", "EML + TKGE memory"),
    ]
    for i, row in enumerate(data):
        y = Inches(1.95 + i * 1.1)
        bg = SOFT_AMBER if i % 2 == 0 else CARD
        _rect(slide, Inches(x0), y, Inches(12.4), Inches(1.05), bg, LINE)
        x = x0
        for j, (cell, w) in enumerate(zip(row, widths)):
            color = TEAL if j == 3 else SLATE
            bold = j in (0, 3)
            _textbox(slide, Inches(x + 0.1), y + Inches(0.3), Inches(w - 0.15), Inches(0.5), [(cell, 13, color, bold)])
            x += w
    _footer(slide, page, total, "Benefits")


def multi_industry(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, TEAL)
    _title(slide, "Useful across industries")
    _subtitle(slide, "Same engine · different catalog, rules, and TAPL sensitivity")

    industries = [
        ("Travel / rental", "Empathy, TCO, journey upsell", "11 live scenarios"),
        ("Hospitality", "Room / booking assists", "Hotel rule pack"),
        ("Restaurant", "QR menu, mobile promos", "Channel fit"),
        ("Banking", "Offer + advisor content", "Compliance sensitivity"),
        ("Healthcare*", "HCP education routing", "Suppress on SMS/wearable"),
        ("Retail / IoT", "Upsell + micro-prompts", "Connected channels"),
    ]
    for i, (name, mech, note) in enumerate(industries):
        col = i % 3
        row = i // 3
        x = Inches(0.45 + col * 4.25)
        y = Inches(1.45 + row * 2.5)
        _round(slide, x, y, Inches(4.05), Inches(2.25), CARD, LINE)
        _textbox(slide, x + Inches(0.25), y + Inches(0.3), Inches(3.55), Inches(0.4), [(name, 16, NAVY, True)])
        _textbox(slide, x + Inches(0.25), y + Inches(0.85), Inches(3.55), Inches(0.5), [(mech, 13, SLATE, False)])
        _textbox(slide, x + Inches(0.25), y + Inches(1.5), Inches(3.55), Inches(0.4), [(note, 12, TEAL, True)])

    _textbox(
        slide,
        Inches(0.5),
        Inches(6.55),
        Inches(12),
        Inches(0.35),
        [("*Healthcare scope: approved HCP education / commercial routing — not clinical decision support.", 11, MUTED, False)],
    )
    _footer(slide, page, total, "Benefits")


def evidence_demo(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, BLUE)
    _title(slide, "Evidence & live demo")
    _subtitle(slide, "Reference implementation with reproducible artifacts — not marketing claims")

    left = [
        ("Live demo", "edta-api.onrender.com/scenario-demo"),
        ("Open source", "github.com/jeraldcs/edta-complete-api"),
        ("OpenAPI", "Swagger at /docs"),
        ("Tests", "167 pytest cases + CI"),
        ("Diagrams", "11-page architecture PDF"),
        ("FAQ / Deck", "docs/FAQ.md + this presentation"),
    ]
    _round(slide, Inches(0.45), Inches(1.4), Inches(6.2), Inches(5.2), CARD, LINE)
    _rect(slide, Inches(0.45), Inches(1.4), Inches(6.2), Inches(0.55), BLUE)
    _textbox(slide, Inches(0.65), Inches(1.5), Inches(5.8), Inches(0.4), [("What you can run today", 16, WHITE, True)])
    y = Inches(2.2)
    for h, d in left:
        _textbox(slide, Inches(0.75), y, Inches(5.6), Inches(0.3), [(h, 14, NAVY, True)])
        _textbox(slide, Inches(0.75), y + Inches(0.3), Inches(5.6), Inches(0.3), [(d, 12, SLATE, False)])
        y += Inches(0.7)

    _round(slide, Inches(6.9), Inches(1.4), Inches(5.9), Inches(5.2), SOFT_AMBER, RGBColor(0xE6, 0xD4, 0xA8))
    _textbox(
        slide,
        Inches(7.15),
        Inches(1.7),
        Inches(5.4),
        Inches(4.6),
        [
            ("Demo script (5 minutes)", 14, AMBER_DARK, True),
            ("1. Loyalty family SUV — full stack scores", 13, SLATE, False),
            ("2. No consent → TAPL generic_fallback", 13, SLATE, False),
            ("3. High fatigue → delay / soften", 13, SLATE, False),
            ("4. Compare vs traditional chips", 13, SLATE, False),
            ("5. Open Scoring Signals + architecture panels", 13, SLATE, False),
            ("", 10, SLATE, False),
            ("Honesty bounds", 14, AMBER_DARK, True),
            ("• Travel matrix = alignment proxy, not A/B lift", 13, SLATE, False),
            ("• Local Docker for latency; Render cold-start separate", 13, SLATE, False),
            ("• Reference architecture ≠ Fortune 500 case study", 13, SLATE, False),
        ],
    )
    _footer(slide, page, total, "Evidence")


def integrate_slide(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, BLUE)
    _title(slide, "How to integrate with any application")
    _subtitle(slide, "Versioned /v1 API — BFF, mobile, chatbot, partner, or event-driven")

    _round(slide, Inches(0.45), Inches(1.4), Inches(7.5), Inches(5.2), NAVY)
    _textbox(
        slide,
        Inches(0.75),
        Inches(1.7),
        Inches(7.0),
        Inches(4.6),
        [
            ("Core endpoints", 14, AMBER, True),
            ("POST /v1/recommend", 16, WHITE, True),
            ("POST /v1/recommend-from-scenario", 16, WHITE, True),
            ("POST /v1/feedback   ·   POST /v1/compare-outcomes", 15, RGBColor(0xD7, 0xE3, 0xEF), False),
            ("", 10, WHITE, False),
            ("Auth", 14, AMBER, True),
            ("X-API-Key when EDTA_API_KEY is set", 14, WHITE, False),
            ("Browser demo uses /demo-api proxy (no client key)", 14, RGBColor(0xD7, 0xE3, 0xEF), False),
            ("", 10, WHITE, False),
            ("Persist for audit / support", 14, AMBER, True),
            ("request_id · TAPL action · inference tier · EDS", 14, WHITE, False),
        ],
    )

    patterns = [
        ("Web / mobile", "BFF enriches CustomerContext from CDP"),
        ("Chatbot", "recommend-from-scenario + channel=chatbot"),
        ("Batch / CRM", "Async /v1/recommend/batch + job poll"),
        ("Events", "Webhooks (HTTPS, SSRF-validated)"),
        ("New industry", "Swap catalog + YAML; keep engine"),
    ]
    y = Inches(1.4)
    for h, d in patterns:
        _round(slide, Inches(8.2), y, Inches(4.6), Inches(0.95), CARD, LINE)
        _textbox(slide, Inches(8.4), y + Inches(0.15), Inches(4.2), Inches(0.3), [(h, 13, NAVY, True)])
        _textbox(slide, Inches(8.4), y + Inches(0.48), Inches(4.2), Inches(0.35), [(d, 12, SLATE, False)])
        y += Inches(1.05)
    _footer(slide, page, total, "How to use")


def lessons_slide(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide)
    _accent(slide, AMBER_DARK)
    _title(slide, "Lessons for architects")
    _subtitle(slide, "Takeaways you can apply even if you never deploy this exact repo")

    lessons = [
        ("01", "LLMs should not own governance", "Keep consent, fatigue, and compliance in policy code."),
        ("02", "Trust must change the rank", "Logging trust in analytics is not governance."),
        ("03", "Explainability is an API contract", "If it is not in the response, teams will dig logs."),
        ("04", "Tier routing must be explicit", "HAOE + YAML beats hidden if/else model selection."),
        ("05", "Benchmark honestly", "Isolate tiers; label demo proxies; separate cold-start."),
        ("06", "Complete traditional systems", "Rules and ML still matter — AI is not a full replacement."),
    ]
    for i, (n, h, d) in enumerate(lessons):
        col = i % 2
        row = i // 2
        x = Inches(0.45 + col * 6.4)
        y = Inches(1.4 + row * 1.75)
        _round(slide, x, y, Inches(6.15), Inches(1.55), CARD, LINE)
        _textbox(slide, x + Inches(0.25), y + Inches(0.25), Inches(1.0), Inches(0.4), [(n, 18, BLUE, True)])
        _textbox(slide, x + Inches(1.3), y + Inches(0.28), Inches(4.5), Inches(0.4), [(h, 15, NAVY, True)])
        _textbox(slide, x + Inches(1.3), y + Inches(0.8), Inches(4.5), Inches(0.5), [(d, 13, SLATE, False)])
    _footer(slide, page, total, "Takeaways")


def closing_slide(prs: Presentation, page: int, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _rect(slide, 0, 0, W, H, NAVY)
    _rect(slide, 0, 0, Inches(0.2), H, TEAL)

    _textbox(
        slide,
        Inches(0.7),
        Inches(1.3),
        Inches(12),
        Inches(1.2),
        [
            ("Why did we show this?", 28, WHITE, True),
            ("Because trust changed the rank — not only the log.", 22, RGBColor(0xD7, 0xE3, 0xEF), False),
        ],
    )

    links = [
        "Live demo   https://edta-api.onrender.com/scenario-demo",
        "GitHub      https://github.com/jeraldcs/edta-complete-api",
        "FAQ         docs/FAQ.md",
        "Compare     docs/TRADITIONAL_VS_EDTA.md",
        "Diagrams    docs/edta_architecture_diagrams_full.pdf",
        "Contact     jerald.cs@gmail.com",
    ]
    _textbox(
        slide,
        Inches(0.7),
        Inches(3.0),
        Inches(12),
        Inches(3.2),
        [(line, 16, RGBColor(0xD7, 0xE3, 0xEF), False) for line in links],
    )
    _textbox(
        slide,
        Inches(0.7),
        Inches(6.5),
        Inches(12),
        Inches(0.5),
        [("Questions?", 22, WHITE, True)],
    )
    _textbox(
        slide,
        Inches(11.5),
        Inches(7.05),
        Inches(1.5),
        Inches(0.3),
        [(f"{page}/{total}", 10, RGBColor(0x9E, 0xB8, 0xCF), False)],
        align=PP_ALIGN.RIGHT,
    )


def build() -> Path:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    total = 20

    title_slide(prs)
    agenda_slide(prs, 2, total)

    section_divider(prs, "01", "The Problem", "LLM adoption outpaced governance for personalization", 3, total, AMBER)
    problem_story(prs, 4, total)
    problem_anti_pattern(prs, 5, total)

    section_divider(prs, "02", "Architecture", "A governed decision pipeline — not a single model", 6, total, BLUE)
    what_is_edta(prs, 7, total)
    architecture_flow(prs, 8, total)
    haoe_slide(prs, 9, total)
    tapl_eds_slide(prs, 10, total)

    section_divider(prs, "03", "Benefits", "Engineering, business, trust — and multi-industry reuse", 11, total, TEAL)
    benefits_overview(prs, 12, total)
    benefits_deep(prs, 13, total)
    traditional_vs(prs, 14, total)
    multi_industry(prs, 15, total)

    section_divider(prs, "04", "Evidence & How to Use", "Demo, honest limits, integration, takeaways", 16, total, BLUE)
    evidence_demo(prs, 17, total)
    integrate_slide(prs, 18, total)
    lessons_slide(prs, 19, total)
    closing_slide(prs, 20, total)

    for candidate in (
        OUTPUT,
        ROOT / "EDTA_INFOQ_PRESENTATION_v2.pptx",
        ROOT / "EDTA_INFOQ_PRESENTATION_v3.pptx",
        ROOT / "EDTA_INFOQ_PRESENTATION_latest.pptx",
    ):
        try:
            prs.save(candidate)
            return candidate
        except PermissionError:
            continue
    raise PermissionError(
        "Could not write presentation — close PowerPoint and retry "
        f"(tried {OUTPUT.name}, _v2, _v3, _latest)."
    )


if __name__ == "__main__":
    path = build()
    print(path.resolve())
