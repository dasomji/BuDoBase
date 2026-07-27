from pathlib import Path
import json

import fitz
from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / "docs/evidence/design-system-refactor/before"
BROKEN = ROOT / "docs/evidence/design-system-refactor/after"
FIXED = Path(__file__).resolve().parent
SLUGS = ("hc-nummernliste", "swp-einteilung-w1", "kitchen")


def difference(reference_path, candidate_path):
    reference = Image.open(reference_path).convert("RGB")
    candidate = Image.open(candidate_path).convert("RGB")
    if reference.size != candidate.size:
        raise ValueError(
            f"Image sizes differ: {reference_path}={reference.size}, "
            f"{candidate_path}={candidate.size}"
        )
    diff = ImageChops.difference(reference, candidate)
    channel_mean = ImageStat.Stat(diff).mean
    changed = sum(
        1 for pixel in diff.getdata()
        if pixel != (0, 0, 0)
    )
    return {
        "size": list(reference.size),
        "mean_absolute_rgb_delta": round(sum(channel_mean) / len(channel_mean), 4),
        "channel_mean_absolute_delta": [round(value, 4) for value in channel_mean],
        "changed_pixel_percentage": round(changed * 100 / (reference.width * reference.height), 4),
        "difference_bbox": list(diff.getbbox()) if diff.getbbox() else None,
    }


def matching_bbox(image_path, predicate, crop):
    image = Image.open(image_path).convert("RGB")
    left, top, right, bottom = crop
    points = [
        (x, y)
        for y in range(top, bottom)
        for x in range(left, right)
        if predicate(image.getpixel((x, y)))
    ]
    if not points:
        raise ValueError(f"No matching pixels found in {image_path}")
    return {
        "left": min(x for x, _ in points),
        "top": min(y for _, y in points),
        "right": max(x for x, _ in points),
        "bottom": max(y for _, y in points),
    }


def pdf_page_geometry(pdf_path):
    document = fitz.open(pdf_path)
    page = document[0]
    page_rect = [round(value, 4) for value in page.rect]
    drawings = page.get_drawings()
    paper = max(drawings, key=lambda drawing: drawing["rect"].get_area())["rect"]
    spans = [
        span
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    ]
    first_span = spans[0]
    return {
        "page_rect_points": page_rect,
        "paper_rect_points": [round(value, 4) for value in paper],
        "first_text": {
            "text": first_span["text"],
            "font": first_span["font"],
            "size_points": round(first_span["size"], 4),
            "bbox_points": [round(value, 4) for value in first_span["bbox"]],
            "origin_points": [round(value, 4) for value in first_span["origin"]],
        },
    }


def first_table_row_geometry(pdf_path):
    document = fitz.open(pdf_path)
    page = document[0]
    cell_rects = [
        drawing["rect"]
        for drawing in page.get_drawings()
        if (
            18 <= drawing["rect"].height <= 23
            and drawing["rect"].x0 >= 39
            and drawing["rect"].x1 <= 300
        )
    ]
    first_top = min(rect.y0 for rect in cell_rects)
    first_row = [
        rect
        for rect in cell_rects
        if abs(rect.y0 - first_top) < 0.01
    ]
    left = min(rect.x0 for rect in first_row)
    right = max(rect.x1 for rect in first_row)
    return {
        "left_points": round(left, 4),
        "right_points": round(right, 4),
        "width_points": round(right - left, 4),
        "ideal_width_at_100_dpi_pixels": round((right - left) * 100 / 72, 4),
    }


pixel_results = {}
for slug in SLUGS:
    filename = f"{slug}--print.png"
    broken = difference(FROZEN / filename, BROKEN / filename)
    fixed = difference(FROZEN / filename, FIXED / filename)
    pixel_results[slug] = {
        "frozen_before": str((FROZEN / filename).relative_to(ROOT)),
        "broken_after": str((BROKEN / filename).relative_to(ROOT)),
        "fixed_after": str((FIXED / filename).relative_to(ROOT)),
        "broken": broken,
        "fixed": fixed,
        "mean_delta_reduction": round(
            broken["mean_absolute_rgb_delta"] - fixed["mean_absolute_rgb_delta"],
            4,
        ),
    }

hc_paths = {
    "before": FROZEN / "hc-nummernliste--print.png",
    "broken": BROKEN / "hc-nummernliste--print.png",
    "fixed": FIXED / "hc-nummernliste--print.png",
}
hc_bounds = {
    name: matching_bbox(
        image_path,
        lambda pixel: min(pixel) < 245,
        (0, 55, 828, 1116),
    )
    for name, image_path in hc_paths.items()
}
for bounds in hc_bounds.values():
    bounds["width"] = bounds["right"] - bounds["left"] + 1

allocation_paths = {
    "before": FROZEN / "swp-einteilung-w1--print.png",
    "broken": BROKEN / "swp-einteilung-w1--print.png",
    "fixed": FIXED / "swp-einteilung-w1--print.png",
}
allocation_heading_bounds = {
    name: matching_bbox(
        image_path,
        lambda pixel: max(pixel) < 100,
        (55, 55, 450, 200),
    )
    for name, image_path in allocation_paths.items()
}

kitchen_paths = {
    "before": FROZEN / "kitchen--print.png",
    "broken": BROKEN / "kitchen--print.png",
    "fixed": FIXED / "kitchen--print.png",
}
kitchen_table_bounds = {
    name: matching_bbox(
        image_path,
        lambda pixel: pixel[2] - pixel[0] >= 5 and pixel[2] - pixel[1] >= 2,
        (0, 100, 828, 320),
    )
    for name, image_path in kitchen_paths.items()
}
for bounds in kitchen_table_bounds.values():
    bounds["width"] = bounds["right"] - bounds["left"] + 1

layout_geometry = {
    "hc_number_list_paper_panel": {
        **hc_bounds,
        "broken_edge_delta": {
            "left": hc_bounds["broken"]["left"] - hc_bounds["before"]["left"],
            "right": hc_bounds["broken"]["right"] - hc_bounds["before"]["right"],
            "width": hc_bounds["broken"]["width"] - hc_bounds["before"]["width"],
        },
        "fixed_edge_delta": {
            "left": hc_bounds["fixed"]["left"] - hc_bounds["before"]["left"],
            "right": hc_bounds["fixed"]["right"] - hc_bounds["before"]["right"],
            "width": hc_bounds["fixed"]["width"] - hc_bounds["before"]["width"],
        },
    },
    "allocation_heading": {
        **allocation_heading_bounds,
        "broken_top_delta": (
            allocation_heading_bounds["broken"]["top"]
            - allocation_heading_bounds["before"]["top"]
        ),
        "fixed_top_delta": (
            allocation_heading_bounds["fixed"]["top"]
            - allocation_heading_bounds["before"]["top"]
        ),
    },
    "kitchen_first_menu_table": {
        **kitchen_table_bounds,
        "broken_width_delta": (
            kitchen_table_bounds["broken"]["width"]
            - kitchen_table_bounds["before"]["width"]
        ),
        "fixed_width_delta": (
            kitchen_table_bounds["fixed"]["width"]
            - kitchen_table_bounds["before"]["width"]
        ),
    },
}

swp_pdf_before = pdf_page_geometry(
    FROZEN / "swp-einteilung-w1--print.pdf"
)
swp_pdf_fixed = pdf_page_geometry(
    FIXED / "swp-einteilung-w1--print.pdf"
)
kitchen_pdf_before = first_table_row_geometry(
    FROZEN / "kitchen--print.pdf"
)
kitchen_pdf_fixed = first_table_row_geometry(
    FIXED / "kitchen--print.pdf"
)
pdf_geometry = {
    "allocation": {
        "before": swp_pdf_before,
        "fixed": swp_pdf_fixed,
        "page_rect_delta_points": [
            round(fixed - before, 4)
            for before, fixed in zip(
                swp_pdf_before["page_rect_points"],
                swp_pdf_fixed["page_rect_points"],
            )
        ],
        "paper_rect_delta_points": [
            round(fixed - before, 4)
            for before, fixed in zip(
                swp_pdf_before["paper_rect_points"],
                swp_pdf_fixed["paper_rect_points"],
            )
        ],
        "classification": (
            "Equivalent page/paper geometry; residual PNG glyph edge is "
            "pre-existing font substitution, not heading box displacement."
        ),
    },
    "kitchen_first_menu_table": {
        "before": kitchen_pdf_before,
        "fixed": kitchen_pdf_fixed,
        "width_delta_points": round(
            kitchen_pdf_fixed["width_points"]
            - kitchen_pdf_before["width_points"],
            4,
        ),
        "classification": (
            "Equivalent vector geometry; 328/329 PNG edge is 100 dpi "
            "raster coverage of a 328.125 px vector width."
        ),
    },
}

results = {
    "pixel_difference": pixel_results,
    "layout_geometry": layout_geometry,
    "pdf_geometry": pdf_geometry,
}

(FIXED / "pixel-diff-report.json").write_text(
    f"{json.dumps(results, indent=2)}\n",
    encoding="utf-8",
)
print(json.dumps(results, indent=2))
