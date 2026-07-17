"""
Export all EDTA architecture Mermaid diagrams to a single PDF.

Source: docs/architecture_diagrams/*.mmd
Output: docs/edta_architecture_diagrams_full.pdf

Requires: Node.js (npx @mermaid-js/mermaid-cli), PyMuPDF (fitz)

Usage:
    python docs/generate_architecture_diagrams_pdf.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
DIAGRAMS_DIR = ROOT / "architecture_diagrams"
ASSETS_DIR = ROOT / "_architecture_pdf_assets"
OUTPUT_PDF = ROOT / "edta_architecture_diagrams_full.pdf"

PAGE_W = 792  # landscape letter width in points
PAGE_H = 612  # landscape letter height in points
MARGIN = 36
TITLE_H = 44

DIAGRAMS: list[tuple[str, str, Path]] = [
    ("1", "System Context — Clients, API, External Services", DIAGRAMS_DIR / "01_system_context.mmd"),
    ("2", "Application Container — Code Modules & ServiceContainer", DIAGRAMS_DIR / "02_application_container.mmd"),
    ("3", "Logical Layer Stack — EDTA Decision Pipeline", DIAGRAMS_DIR / "03_layer_stack.mmd"),
    ("4", "End-to-End Sequence — POST /v1/recommend", DIAGRAMS_DIR / "04_recommend_sequence.mmd"),
    ("5", "Scenario Demo Path — POST /recommend-from-scenario", DIAGRAMS_DIR / "05_scenario_demo_path.mmd"),
    ("6", "HAOE Four-Tier Inference Routing", DIAGRAMS_DIR / "06_haoe_routing.mmd"),
    ("7", "Per-Candidate Scoring — EDS, TAPL, OSE, Ranker", DIAGRAMS_DIR / "07_per_candidate_scoring.mmd"),
    ("8", "Data & Persistence — SQLite and File Artifacts", DIAGRAMS_DIR / "08_data_persistence.mmd"),
    ("9", "API Surface Map — Auth, Demo Proxy, Public Routes", DIAGRAMS_DIR / "09_api_surface.mmd"),
    ("10", "Cross-Cutting — Observability, Security, Events", DIAGRAMS_DIR / "10_cross_cutting.mmd"),
    ("11", "Deployment Topology — Render / Docker", DIAGRAMS_DIR / "11_deployment_topology.mmd"),
]


def _npx_command() -> list[str]:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("npx (Node.js) is required to render Mermaid diagrams.")
    return [npx]


def render_mermaid(mmd_path: Path, png_path: Path) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    config_path = DIAGRAMS_DIR / "mermaid-config.json"
    cmd = _npx_command() + [
        "-y",
        "@mermaid-js/mermaid-cli",
        "-i",
        str(mmd_path),
        "-o",
        str(png_path),
        "-b",
        "white",
        "--scale",
        "1.4",
        "-w",
        "1800",
    ]
    if config_path.exists():
        cmd.extend(["-c", str(config_path)])
    subprocess.run(cmd, check=True, cwd=ROOT, shell=False)


def compress_for_pdf(png_path: Path) -> Path:
    from PIL import Image

    jpeg_path = png_path.with_suffix(".jpg")
    image = Image.open(png_path)
    max_width = 1400
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)), Image.Resampling.LANCZOS)
    image.convert("RGB").save(jpeg_path, "JPEG", quality=88, optimize=True)
    return jpeg_path


def add_cover_page(doc: fitz.Document) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.insert_text(
        (MARGIN, 120),
        "EDTA Architecture Diagrams",
        fontsize=28,
        fontname="helv",
        color=(0.06, 0.13, 0.09),
    )
    page.insert_text(
        (MARGIN, 155),
        "Experience-Driven Targeting Architecture — Full Reference (v2.4)",
        fontsize=12,
        fontname="helv",
        color=(0.36, 0.42, 0.39),
    )
    lines = [
        "Generated from docs/architecture_diagrams/*.mmd",
        "Repository: github.com/jeraldcs/edta-complete-api",
        "Live demo: edta-api.onrender.com/scenario-demo",
        "",
        "Contents:",
    ]
    y = 200
    for number, title, _ in DIAGRAMS:
        page.insert_text((MARGIN, y), f"  {number}. {title}", fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))
        y += 18
    page.insert_text(
        (MARGIN, PAGE_H - MARGIN),
        "Regenerate: python docs/generate_architecture_diagrams_pdf.py",
        fontsize=8,
        fontname="helv",
        color=(0.45, 0.45, 0.45),
    )


def add_diagram_page(doc: fitz.Document, number: str, title: str, png_path: Path) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    header = f"Figure {number} — {title}"
    page.insert_text((MARGIN, MARGIN + 14), header, fontsize=11, fontname="hebo", color=(0.08, 0.12, 0.1))

    img_rect = fitz.Rect(
        MARGIN,
        MARGIN + TITLE_H,
        PAGE_W - MARGIN,
        PAGE_H - MARGIN,
    )
    page.insert_image(img_rect, filename=str(png_path), keep_proportion=True)


def main() -> int:
    try:
        _npx_command()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    png_paths: list[Path] = []
    jpeg_paths: list[Path] = []

    for number, title, mmd_path in DIAGRAMS:
        if not mmd_path.exists():
            print(f"Missing diagram source: {mmd_path}", file=sys.stderr)
            return 1
        png_path = ASSETS_DIR / f"diagram_{number}.png"
        print(f"Rendering {mmd_path.name} ...")
        render_mermaid(mmd_path, png_path)
        jpeg_paths.append(compress_for_pdf(png_path))
        png_paths.append(png_path)

    doc = fitz.open()
    add_cover_page(doc)
    for (number, title, _), jpeg_path in zip(DIAGRAMS, jpeg_paths, strict=True):
        add_diagram_page(doc, number, title, jpeg_path)

    doc.save(str(OUTPUT_PDF), garbage=4, deflate=True)
    doc.close()
    print(f"Wrote {OUTPUT_PDF.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
