"""
Generate Governed Architecture diagram PNG for the public repository.

Outputs:
  - static/governed_architecture.png (tracked; used by ARCHITECTURE.md and the demo)
  - docs/edta_reference_implementation.png (optional local copy when docs/ exists)

Usage:
    python scripts/generate_governed_architecture_diagram.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT_STATIC = REPO / "static" / "governed_architecture.png"
OUT_DOCS_COPY = REPO / "docs" / "edta_reference_implementation.png"

NAVY = (15, 39, 64)
NAVY_MID = (27, 58, 92)
TEAL = (31, 111, 120)
TEAL_MID = (58, 138, 140)
BLUE = (43, 106, 158)
WHITE = (255, 255, 255)
LIGHT = (236, 244, 248)
BAND_A = (228, 238, 244)
BAND_B = (222, 236, 236)
LINE = (90, 120, 145)
LABEL = (60, 90, 115)
DB_FILL = (245, 248, 252)
EXT_FILL = (252, 246, 238)
EXT_LINE = (196, 120, 40)
API_FILL = (238, 244, 252)

# Arrow styles — color, width, dash pattern (0 = solid)
ARROW_FLOW = {"color": NAVY, "width": 4, "dash": 0, "gap": 0, "head": 12}
ARROW_API = {"color": (0, 92, 175), "width": 3, "dash": 0, "gap": 0, "head": 10}
ARROW_CONTEXT = {"color": (108, 78, 158), "width": 3, "dash": 8, "gap": 6, "head": 9}
ARROW_EXTERNAL = {"color": EXT_LINE, "width": 3, "dash": 12, "gap": 5, "head": 10}
ARROW_DB = {"color": (24, 108, 185), "width": 3, "dash": 6, "gap": 5, "head": 9}
ARROW_STATE = {"color": (0, 138, 118), "width": 3, "dash": 3, "gap": 7, "head": 9}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    candidates.extend(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _center_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    lines: list[str],
    fonts: list[ImageFont.ImageFont],
    fill: tuple[int, int, int],
    line_gap: int = 6,
) -> None:
    x0, y0, x1, y1 = box
    heights, widths = [], []
    for line, font in zip(lines, fonts):
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = y0 + (y1 - y0 - total_h) // 2
    for line, font, w, h in zip(lines, fonts, widths, heights):
        draw.text((x0 + (x1 - x0 - w) // 2, y), line, font=font, fill=fill)
        y += h + line_gap


def _left_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    lines: list[str],
    fonts: list[ImageFont.ImageFont],
    fill: tuple[int, int, int],
    line_gap: int = 5,
    pad_x: int = 12,
) -> None:
    x0, y0, x1, y1 = box
    heights = []
    for line, font in zip(lines, fonts):
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = y0 + (y1 - y0 - total_h) // 2
    for line, font, h in zip(lines, fonts, heights):
        draw.text((x0 + pad_x, y), line, font=font, fill=fill)
        y += h + line_gap


def _rounded_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
    radius: int = 16,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width if outline else 0)


def _arrow_head(
    draw: ImageDraw.ImageDraw,
    tip: tuple[int, int],
    direction: str,
    color: tuple[int, int, int],
    size: int,
) -> None:
    x, y = tip
    if direction == "right":
        draw.polygon([(x, y), (x - size, y - size // 2), (x - size, y + size // 2)], fill=color)
    elif direction == "left":
        draw.polygon([(x, y), (x + size, y - size // 2), (x + size, y + size // 2)], fill=color)
    elif direction == "down":
        draw.polygon([(x, y), (x - size // 2, y - size), (x + size // 2, y - size)], fill=color)
    else:
        draw.polygon([(x, y), (x - size // 2, y + size), (x + size // 2, y + size)], fill=color)


def _segment_direction(start: tuple[int, int], end: tuple[int, int]) -> str:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if abs(dx) >= abs(dy):
        return "right" if dx >= 0 else "left"
    return "down" if dy >= 0 else "up"


def _stroke_segment(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    style: dict,
) -> None:
    color = style["color"]
    width = style["width"]
    dash, gap = style["dash"], style["gap"]
    x0, y0 = start
    x1, y1 = end
    if dash == 0:
        draw.line([start, end], fill=color, width=width)
        return
    if y0 == y1:
        x, end_x = min(x0, x1), max(x0, x1)
        while x < end_x:
            draw.line([(x, y0), (min(x + dash, end_x), y0)], fill=color, width=width)
            x += dash + gap
    elif x0 == x1:
        y, end_y = min(y0, y1), max(y0, y1)
        while y < end_y:
            draw.line([(x0, y), (x0, min(y + dash, end_y))], fill=color, width=width)
            y += dash + gap
    else:
        draw.line([start, end], fill=color, width=width)


def _draw_path(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    style: dict,
    *,
    arrow_end: bool = True,
    arrow_start: bool = False,
) -> None:
    if len(points) < 2:
        return
    for start, end in zip(points[:-1], points[1:]):
        _stroke_segment(draw, start, end, style)
    head = style["head"]
    if arrow_end:
        _arrow_head(draw, points[-1], _segment_direction(points[-2], points[-1]), style["color"], head)
    if arrow_start:
        _arrow_head(draw, points[0], _segment_direction(points[1], points[0]), style["color"], head)


def _draw_connector(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    style: dict,
    *,
    arrow_end: bool = True,
) -> None:
    _draw_path(draw, [start, end], style, arrow_end=arrow_end)


def _legend_arrow(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    style: dict,
    label: str,
    font: ImageFont.ImageFont,
) -> None:
    _draw_connector(draw, (x, y + 6), (x + 46, y + 6), style)
    draw.text((x + 54, y), label, font=font, fill=style["color"])


def _label_on_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    center: tuple[int, int],
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = LABEL,
    pad: tuple[int, int] = (8, 4),
) -> None:
    cx, cy = center
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bg = (cx - tw // 2 - pad[0], cy - th // 2 - pad[1], cx + tw // 2 + pad[0], cy + th // 2 + pad[1])
    draw.rounded_rectangle(bg, radius=6, fill=WHITE, outline=(210, 220, 228), width=1)
    draw.text((cx - tw // 2, cy - th // 2 - 1), text, font=font, fill=fill)


def generate() -> list[Path]:
    W, H = 1480, 880
    img = Image.new("RGB", (W, H), LIGHT)
    draw = ImageDraw.Draw(img)

    title_font = _font(20, bold=True)
    band_font = _font(12, bold=True)
    acronym_font = _font(20, bold=True)
    phrase_font = _font(13)
    note_font = _font(11)
    small_font = _font(10)
    tag_font = _font(10, bold=True)

    draw.text((48, 24), "Governed Architecture", font=title_font, fill=NAVY)
    draw.text(
        (48, 52),
        "Reference implementation — recommendation path, API surface, persistence, and external calls",
        font=note_font,
        fill=LABEL,
    )

    # API entry strip (left, clear of main flow)
    api_box = (48, 82, 268, 168)
    _rounded_box(draw, api_box, API_FILL, outline=(180, 200, 220), radius=14)
    draw.text((60, 90), "API ENDPOINTS", font=tag_font, fill=BLUE)
    _left_text(
        draw,
        (48, 108, 268, 168),
        [
            "POST /v1/recommend",
            "POST /v1/recommend-from-scenario",
            "POST /v1/feedback  (state update)",
        ],
        [small_font, small_font, small_font],
        NAVY,
        line_gap=6,
        pad_x=14,
    )

    # External systems panel (right)
    ext_box = (1188, 82, 1432, 248)
    _rounded_box(draw, ext_box, EXT_FILL, outline=EXT_LINE, radius=14)
    draw.text((1200, 90), "EXTERNAL SYSTEMS", font=tag_font, fill=EXT_LINE)
    _left_text(
        draw,
        (1188, 108, 1432, 248),
        [
            "Profile adapter",
            "  (CRM / CDP / JSON file)",
            "SLM host (Groq / Together)",
            "  OpenAI-compatible API",
            "Optional LLM teacher",
            "  (frontier model, budgeted)",
        ],
        [small_font] * 6,
        NAVY,
        line_gap=4,
        pad_x=14,
    )

    # SQLite panel (right, below external — lower to avoid label overlap)
    db_box = (1188, 448, 1432, 598)
    _rounded_box(draw, db_box, DB_FILL, outline=(140, 165, 190), radius=14)
    draw.text((1200, 456), "SQLite  data/edta.db", font=tag_font, fill=BLUE)
    _left_text(
        draw,
        (1188, 476, 1432, 588),
        [
            "eml_subjects  ·  EML read/write",
            "tkge_snapshots  ·  TKGE read/write",
            "tapl_audit  ·  governance audit",
            "feedback_events  ·  outcome loop",
            "idempotency_keys  ·  API dedupe",
        ],
        [small_font] * 5,
        NAVY,
        line_gap=5,
        pad_x=14,
    )

    # Swim lanes — inset to leave room for side panels
    lane_x0, lane_x1 = 292, 1168
    band1 = (lane_x0, 82, lane_x1, 228)
    band2 = (lane_x0, 252, lane_x1, 398)
    _rounded_box(draw, band1, BAND_A, outline=(200, 215, 225), radius=18)
    _rounded_box(draw, band2, BAND_B, outline=(200, 220, 220), radius=18)
    draw.text((lane_x0 + 16, 90), "1  ENRICH CONTEXT", font=band_font, fill=TEAL)
    draw.text((lane_x0 + 16, 260), "2  SCORE, GOVERN & RANK", font=band_font, fill=TEAL)

    box_h = 88
    gap = 18
    y1 = 118
    y2 = 296

    def place(
        x: int,
        y: int,
        w: int,
        color: tuple[int, int, int],
        title: str,
        subtitle: str,
    ) -> tuple[int, int, int, int]:
        rect = (x, y, x + w, y + box_h)
        _rounded_box(draw, rect, color)
        _center_text(draw, rect, [title, subtitle], [acronym_font, phrase_font], WHITE)
        return rect

    # Row 1 — evenly spaced within lane
    row1_x = lane_x0 + 20
    row1_w = lane_x1 - lane_x0 - 40
    n1 = 5
    w1 = (row1_w - gap * (n1 - 1)) // n1
    x = row1_x
    client = place(x, y1, w1, NAVY_MID, "Client", "HTTP request")
    x += w1 + gap
    profile = place(x, y1, w1, NAVY_MID, "Profile", "lookup facade")
    x += w1 + gap
    eml = place(x, y1, w1, TEAL, "EML", "cross-session memory")
    x += w1 + gap
    tkge = place(x, y1, w1, TEAL, "TKGE", "journey graph")
    x += w1 + gap
    haoe = place(x, y1, w1, BLUE, "HAOE", "inference routing")

    # Row 2
    row2_x = lane_x0 + 20
    row2_w = lane_x1 - lane_x0 - 40
    n2 = 5
    w2 = (row2_w - gap * (n2 - 1)) // n2
    x = row2_x
    eds = place(x, y2, w2, TEAL_MID, "EDS", "explainable fit")
    x += w2 + gap
    tapl = place(x, y2, w2, TEAL_MID, "TAPL", "trust governance")
    x += w2 + gap
    ose = place(x, y2, w2, TEAL_MID, "OSE", "outcome view")
    x += w2 + gap
    rank = place(x, y2, w2, TEAL_MID, "Rank", "final ordering")
    x += w2 + gap
    response = place(x, y2, w2, NAVY, "Response", "ranked + audit")

    def mid(b: tuple[int, int, int, int]) -> tuple[int, int]:
        return (b[0] + b[2]) // 2, (b[1] + b[3]) // 2

    def mid_y(b: tuple[int, int, int, int]) -> int:
        return (b[1] + b[3]) // 2

    # Client ← API endpoints (blue solid)
    api_cx = (api_box[0] + api_box[2]) // 2
    client_cx, client_cy = mid(client)
    api_cy = (api_box[1] + api_box[3]) // 2
    _draw_path(
        draw,
        [(api_box[2], api_cy), (client[0] - 6, api_cy), (client[0], api_cy)],
        ARROW_API,
    )
    _label_on_line(draw, "ingress", ((api_box[2] + client[0]) // 2, api_cy - 16), small_font, ARROW_API["color"])

    # Row 1 flow (navy solid, thick)
    for left, right in [(client, profile), (profile, eml), (eml, tkge), (tkge, haoe)]:
        _draw_connector(draw, (left[2] + 4, mid_y(left)), (right[0] - 8, mid_y(right)), ARROW_FLOW)

    # HAOE → EDS (navy solid)
    hx, _ = mid(haoe)
    ex, _ = mid(eds)
    bridge_y = band2[1] - 6
    _draw_path(
        draw,
        [(hx, haoe[3]), (hx, bridge_y), (ex, bridge_y), (ex, eds[1] - 2)],
        ARROW_FLOW,
    )

    # Row 2 flow (navy solid, thick)
    for left, right in [(eds, tapl), (tapl, ose), (ose, rank), (rank, response)]:
        _draw_connector(draw, (left[2] + 4, mid_y(left)), (right[0] - 8, mid_y(right)), ARROW_FLOW)

    # Cross-band context hints (purple dashed)
    hint_y = 238
    eml_cx, _ = mid(eml)
    tapl_cx, _ = mid(tapl)
    tkge_cx, _ = mid(tkge)
    eds_cx, _ = mid(eds)
    _draw_path(draw, [(eml_cx, eml[3] + 4), (eml_cx, hint_y), (tapl_cx, hint_y), (tapl_cx, tapl[1] - 4)], ARROW_CONTEXT)
    _label_on_line(draw, "trust · fatigue", ((eml_cx + tapl_cx) // 2, hint_y - 18), small_font, ARROW_CONTEXT["color"])

    hint_y2 = hint_y + 22
    _draw_path(draw, [(tkge_cx, tkge[3] + 4), (tkge_cx, hint_y2), (eds_cx, hint_y2), (eds_cx, eds[1] - 4)], ARROW_CONTEXT)
    _label_on_line(draw, "intent · keywords", ((tkge_cx + eds_cx) // 2, hint_y2 - 18), small_font, ARROW_CONTEXT["color"])

    # Profile → external adapter (orange dashed)
    prof_cx, prof_cy = mid(profile)
    ext_prof_y = prof_cy - 36
    _draw_path(draw, [(profile[2], prof_cy), (ext_box[0] - 8, ext_prof_y), (ext_box[0], ext_prof_y)], ARROW_EXTERNAL)
    _label_on_line(draw, "adapter lookup", ((profile[2] + ext_box[0]) // 2, ext_prof_y - 18), small_font, ARROW_EXTERNAL["color"])

    # HAOE → SLM / LLM external (orange dashed)
    haoe_cx, haoe_cy = mid(haoe)
    ext_slm_y = 148
    _draw_path(draw, [(haoe[2], haoe_cy - 10), (ext_box[0] - 8, ext_slm_y), (ext_box[0], ext_slm_y)], ARROW_EXTERNAL)
    _label_on_line(draw, "SLM / LLM call", ((haoe[2] + ext_box[0]) // 2, ext_slm_y - 18), small_font, ARROW_EXTERNAL["color"])

    # DB calls — blue dashed via right gutter
    gutter_x = 1148
    db_eml_y = 432
    db_tkge_y = 468
    db_tapl_y = 504
    eml_cx, _ = mid(eml)
    tkge_cx, _ = mid(tkge)
    tapl_cx, _ = mid(tapl)
    for src_x, src_bottom, bus_y, label in (
        (eml_cx, eml[3], db_eml_y, "SELECT / INSERT eml_*"),
        (tkge_cx, tkge[3], db_tkge_y, "SELECT / INSERT tkge_snapshots"),
        (tapl_cx, tapl[3], db_tapl_y, "INSERT tapl_audit"),
    ):
        _draw_path(
            draw,
            [(src_x, src_bottom + 2), (src_x, bus_y), (gutter_x, bus_y), (db_box[0], bus_y)],
            ARROW_DB,
        )
        _label_on_line(draw, label, ((gutter_x + db_box[0]) // 2, bus_y - 18), small_font, ARROW_DB["color"])

    # Phase 3 — update state (green dotted)
    persist_y = 638
    draw.text((48, persist_y - 24), "3  UPDATE STATE", font=band_font, fill=TEAL)
    rx, _ = mid(response)
    eml_bottom_x, _ = mid(eml)
    tkge_bottom_x, _ = mid(tkge)
    _draw_path(
        draw,
        [
            (rx, response[3] + 8),
            (rx, persist_y),
            (eml_bottom_x, persist_y),
            (eml_bottom_x, eml[3] + 2),
        ],
        ARROW_STATE,
    )
    _draw_path(draw, [(rx, persist_y), (tkge_bottom_x, persist_y), (tkge_bottom_x, tkge[3] + 2)], ARROW_STATE)
    _label_on_line(draw, "persist memory & journey", ((rx + eml_bottom_x) // 2, persist_y + 20), small_font, ARROW_STATE["color"])

    # Feedback loop from API panel (blue dashed — API style variant)
    fb_y = persist_y + 62
    fb_style = {**ARROW_API, "dash": 6, "gap": 5}
    _draw_path(
        draw,
        [(api_cx, api_box[3]), (api_cx, fb_y), (eml_bottom_x, fb_y), (eml_bottom_x, eml[3] + 2)],
        fb_style,
    )
    _label_on_line(draw, "POST /v1/feedback → EML", ((api_cx + eml_bottom_x) // 2, fb_y + 18), small_font, ARROW_API["color"])

    # Visual legend — colored arrow samples
    legend_y = 768
    draw.text((48, legend_y - 22), "Arrow key", font=tag_font, fill=NAVY)
    _legend_arrow(draw, 48, legend_y, ARROW_FLOW, "Request flow (solid navy)", small_font)
    _legend_arrow(draw, 48, legend_y + 22, ARROW_API, "API ingress / feedback (solid blue)", small_font)
    _legend_arrow(draw, 48, legend_y + 44, ARROW_CONTEXT, "Context inputs (purple dash)", small_font)
    _legend_arrow(draw, 520, legend_y, ARROW_EXTERNAL, "External calls (orange dash)", small_font)
    _legend_arrow(draw, 520, legend_y + 22, ARROW_DB, "DB read/write (blue dash)", small_font)
    _legend_arrow(draw, 520, legend_y + 44, ARROW_STATE, "State update (green dot)", small_font)

    OUT_STATIC.parent.mkdir(parents=True, exist_ok=True)
    outputs = [OUT_STATIC]
    img.save(OUT_STATIC, "PNG", optimize=True)
    if OUT_DOCS_COPY.parent.is_dir():
        OUT_DOCS_COPY.parent.mkdir(parents=True, exist_ok=True)
        img.save(OUT_DOCS_COPY, "PNG", optimize=True)
        outputs.append(OUT_DOCS_COPY)
    return outputs


if __name__ == "__main__":
    for path in generate():
        print(f"Wrote {path}")
