#!/usr/bin/env python3
"""Generate a printable assembly document (PDF) for a KiCad board.

The document has one page per component: every footprint with the same value
and footprint is one component, and its page shows the whole board with all of
its instances highlighted. Parts placed on earlier pages are shaded so the
pages also read as a running placement order. Footprints excluded from the BOM
(the mounting holes) get no page, nor do the parts named with --skip (by
default BT1, the AA holder, which is hand-soldered after reflow).

Pages are ordered by where each component's topmost instance sits on the
board: top to bottom, then left to right, except that components whose
reference prefix is named with --last (default: R, the resistors) come at the
end.

Usage:
    scripts/assembly_doc.py [PCB] [-o OUT.pdf] [--skip REF ...] [--last PREFIX ...]

Defaults to the back board and docs/assembly/assembly_guide.pdf.

Needs KiCad's pcbnew python module (the script re-runs itself under KiCad's
bundled python if the current one can't import it; set PCBNEW_PYTHON to
override) and rsvg-convert (librsvg; `brew install librsvg`) to build the PDF.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import pcbnew
except ImportError:
    # pcbnew only loads in the python KiCad was built against. -E ignores
    # PYTHONHOME/PYTHONPATH set by other toolchains.
    candidates = [
        os.environ.get("PCBNEW_PYTHON"),
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3",
        "/usr/bin/python3",
    ]
    for py in filter(None, candidates):
        if os.path.realpath(py) == os.path.realpath(sys.executable):
            continue
        if subprocess.run([py, "-E", "-c", "import pcbnew"],
                          capture_output=True).returncode == 0:
            os.execv(py, [py, "-E", os.path.abspath(__file__), *sys.argv[1:]])
    sys.exit("error: no python can import pcbnew; install KiCad 9+ or set PCBNEW_PYTHON")


# Page: US letter, landscape, in mm (SVG user units).
PAGE_W, PAGE_H = 279.4, 215.9
MARGIN = 12.0
HEADER_H = 34.0

COLORS = {
    "page": "#ffffff",
    "board": "#2f6b3a",
    "board_edge": "#1d3f23",
    "hole": "#ffffff",
    "pad": "#c9b27c",
    "silk": "#f4f4f0",
    "placed": "#6d7f73",
    "highlight": "#ff2d2d",
    "pin1": "#9cf59a",
    "label": "#ffffff",
    "text": "#1a1a1a",
    "muted": "#666666",
}

# Plain-English names shown next to each value: by value first, then by
# reference prefix.
NAMES_BY_VALUE = {
    "TPS613222ADBV": "Boost converter",
    "SW_SPDT": "Slide switch",
    "WHITE": "LED",
    "GREEN": "LED",
}
NAMES_BY_PREFIX = {
    "R": "Resistor",
    "C": "Capacitor",
    "L": "Inductor",
    "D": "Diode",
    "LED": "LED",
    "U": "Integrated circuit",
    "Q": "Transistor",
    "SW": "Switch",
    "J": "Connector",
    "BT": "Battery holder",
    "Y": "Crystal",
    "F": "Fuse",
}


def component_name(value, ref, footprint):
    if value in NAMES_BY_VALUE:
        return NAMES_BY_VALUE[value]
    if footprint.upper().startswith("LED"):
        return "LED"
    return NAMES_BY_PREFIX.get(ref_prefix(ref).upper(), "")


# Reference prefixes whose pin 1 matters (polarity / orientation).
POLARIZED_PREFIXES = ("D", "U", "Q", "BT", "J", "SW")

MAX_ERROR = pcbnew.FromMM(0.005)


def mm(v):
    return pcbnew.ToMM(v)


def natural_key(ref):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def uid(fp):
    return fp.m_Uuid.AsString()


def ref_prefix(ref):
    return re.match(r"[A-Za-z_]*", ref).group(0)


def poly_to_path(polyset):
    """SVG path data (mm) for a SHAPE_POLY_SET, outlines and holes."""
    parts = []

    def chain(line):
        pts = [line.CPoint(i) for i in range(line.PointCount())]
        if not pts:
            return
        parts.append("M" + " L".join(f"{mm(p.x):.3f},{mm(p.y):.3f}" for p in pts) + "Z")

    for i in range(polyset.OutlineCount()):
        chain(polyset.COutline(i))
        for h in range(polyset.HoleCount(i)):
            chain(polyset.CHole(i, h))
    return " ".join(parts)


def item_path(item, layer):
    polyset = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(polyset, layer, 0, MAX_ERROR, pcbnew.ERROR_INSIDE)
    return poly_to_path(polyset)


def pad_path(pad, layer):
    return poly_to_path(pad.GetEffectivePolygon(layer, pcbnew.ERROR_INSIDE))


def footprint_outline_path(fp, layer):
    """Courtyard of the footprint, or its bounding box if it has none."""
    court = fp.GetCourtyard(layer)
    if court.OutlineCount():
        return poly_to_path(court)
    bb = fp.GetBoundingBox(False)
    x, y, w, h = mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetWidth()), mm(bb.GetHeight())
    return f"M{x:.3f},{y:.3f} h{w:.3f} v{h:.3f} h{-w:.3f}Z"


def group_components(board, skip=(), last=()):
    groups = {}
    for fp in board.GetFootprints():
        if fp.IsExcludedFromBOM() or fp.IsBoardOnly() or fp.GetReference() in skip:
            continue
        if fp.GetFPID().GetLibNickname() == "MountingHole" or not fp.Pads():
            continue
        key = (fp.GetValue(), str(fp.GetFPID().GetLibItemName()), fp.GetLayer())
        groups.setdefault(key, []).append(fp)

    out = []
    for (value, footprint, layer), fps in groups.items():
        fps.sort(key=lambda f: natural_key(f.GetReference()))
        out.append({
            "value": value,
            "footprint": footprint,
            "layer": layer,
            "footprints": fps,
            "refs": [f.GetReference() for f in fps],
            "name": component_name(value, fps[0].GetReference(), footprint),
            # Reading-order position of the topmost (then leftmost) instance.
            "pos": min((f.GetPosition().y, f.GetPosition().x) for f in fps),
        })
    out.sort(key=lambda g: (ref_prefix(g["refs"][0]).upper() in last, g["pos"]))
    return out


def silkscreen_paths(board, silk):
    """SVG paths for everything printed on the given silkscreen layer: board
    graphics and text, and each footprint's graphics and visible text."""
    items = list(board.GetDrawings())
    for fp in board.GetFootprints():
        items.extend(fp.GraphicalItems())
        items.extend(f for f in fp.GetFields() if f.IsVisible())
    paths = []
    for item in items:
        if item.GetLayer() != silk:
            continue
        if isinstance(item, pcbnew.EDA_TEXT) and not item.IsVisible():
            continue
        if isinstance(item, (pcbnew.PCB_TEXT, pcbnew.PCB_FIELD)):
            # TransformShapeToPolygon gives text's bounding box; this gives glyphs.
            polyset = pcbnew.SHAPE_POLY_SET()
            item.TransformTextToPolySet(polyset, 0, MAX_ERROR, pcbnew.ERROR_INSIDE)
            d = poly_to_path(polyset)
        else:
            d = item_path(item, silk)
        if d:
            paths.append(f'<path d="{d}" fill="{COLORS["silk"]}" fill-rule="nonzero"/>')
    return paths


def render_board(board, side_layer, highlighted, placed, label_size):
    """SVG <g> content for the board in board coordinates (mm)."""
    front = side_layer == pcbnew.F_Cu
    copper = pcbnew.F_Cu if front else pcbnew.B_Cu
    silk = pcbnew.F_SilkS if front else pcbnew.B_SilkS
    court = pcbnew.F_CrtYd if front else pcbnew.B_CrtYd

    out = []
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    out.append(f'<path d="{poly_to_path(outline)}" fill="{COLORS["board"]}" '
               f'fill-rule="evenodd" stroke="{COLORS["board_edge"]}" stroke-width="0.4"/>')

    # Compare by UUID: SWIG hands out a new wrapper object on every call.
    hl_ids = {uid(f) for f in highlighted}
    placed_ids = {uid(f) for f in placed}

    # Parts placed on earlier pages.
    for fp in placed:
        if fp.GetLayer() != side_layer:
            continue
        out.append(f'<path d="{footprint_outline_path(fp, court)}" fill="{COLORS["placed"]}" '
                   f'fill-rule="nonzero" stroke="none"/>')

    # Pads for every footprint on this side.
    holes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(copper):
                color = COLORS["placed"] if uid(fp) in placed_ids else COLORS["pad"]
                if uid(fp) in hl_ids:
                    color = COLORS["highlight"]
                out.append(f'<path d="{pad_path(pad, copper)}" fill="{color}" fill-rule="evenodd"/>')
            if pad.HasHole():
                pos, drill = pad.GetPosition(), pad.GetDrillSize()
                holes.append((mm(pos.x), mm(pos.y), mm(min(drill.x, drill.y)) / 2))
    for x, y, r in holes:
        out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}" fill="{COLORS["hole"]}"/>')

    # Highlighted parts: courtyard outline, a ring so small parts stand out at
    # a glance, pin 1 marker, and the reference above the ring when the
    # silkscreen doesn't already print it.
    for fp in highlighted:
        bb = fp.GetBoundingBox(False)
        c = bb.GetCenter()
        cx, cy = mm(c.x), mm(c.y)
        size = max(mm(bb.GetWidth()), mm(bb.GetHeight()))
        small = size < 10
        out.append(f'<path d="{footprint_outline_path(fp, court)}" fill="none" '
                   f'stroke="{COLORS["highlight"]}" stroke-width="{label_size * (0.08 if small else 0.15):.3f}"/>')
        if small:
            ring_r = size / 2 + label_size * 0.5
            out.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{ring_r:.3f}" fill="none" '
                       f'stroke="{COLORS["highlight"]}" stroke-width="{label_size * 0.15:.3f}"/>')
            label_y = cy - ring_r - label_size * 0.25
        else:
            label_y = cy + label_size * 0.35
        if ref_prefix(fp.GetReference()).upper().startswith(POLARIZED_PREFIXES):
            for pad in fp.Pads():
                if pad.GetNumber() == "1" and pad.IsOnLayer(copper):
                    out.append(f'<path d="{pad_path(pad, copper)}" fill="{COLORS["pin1"]}" '
                               f'fill-rule="evenodd"/>')
        ref_field = fp.Reference()
        if ref_field.IsVisible() and ref_field.GetLayer() == silk:
            continue
        out.append(
            f'<text x="{cx:.3f}" y="{label_y:.3f}" font-size="{label_size:.2f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-weight="bold" text-anchor="middle" '
            f'fill="{COLORS["label"]}" stroke="{COLORS["text"]}" '
            f'stroke-width="{label_size * 0.18:.3f}" paint-order="stroke">'
            f'{html.escape(fp.GetReference())}</text>')
    # Silkscreen, as printed on the board. Drawn last so the highlight rings
    # never hide its text.
    out.extend(silkscreen_paths(board, silk))
    return "\n".join(out)


def wrap(text, width):
    lines, line = [], ""
    for word in text.split(" "):
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        lines.append(line)
    return lines


def page_svg(board, title, step, total, group, placed):
    bb = board.GetBoardEdgesBoundingBox()
    bx, by, bw, bh = mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetWidth()), mm(bb.GetHeight())
    area_w = PAGE_W - 2 * MARGIN
    area_h = PAGE_H - 2 * MARGIN - HEADER_H
    scale = min(area_w / bw, area_h / bh)
    ox = MARGIN + (area_w - bw * scale) / 2 - bx * scale
    oy = MARGIN + HEADER_H + (area_h - bh * scale) / 2 - by * scale
    mirror = group["layer"] == pcbnew.B_Cu
    if mirror:
        # View the bottom from below: mirror left-right.
        transform = f"translate({ox + (2 * bx + bw) * scale:.3f},{oy:.3f}) scale({-scale:.5f},{scale:.5f})"
    else:
        transform = f"translate({ox:.3f},{oy:.3f}) scale({scale:.5f})"

    # Reference labels are ~3 mm tall on paper.
    label_size = 3.0 / scale
    board_svg = render_board(board, group["layer"], group["footprints"], placed, label_size)

    refs = group["refs"]

    t = []
    x0 = MARGIN
    t.append(f'<text x="{x0}" y="{MARGIN + 5}" font-size="4" fill="{COLORS["muted"]}">'
             f'{html.escape(title)} · Step {step} of {total}</text>')
    t.append(f'<text x="{x0}" y="{MARGIN + 15}" font-size="9" font-weight="bold" '
             f'fill="{COLORS["text"]}">{html.escape(group["value"])} '
             + (f'<tspan font-weight="normal">{html.escape(group["name"])}</tspan> ' if group["name"] else "") +
             f'<tspan font-size="6" font-weight="normal" fill="{COLORS["muted"]}">×{len(refs)}'
             f'{" · bottom side" if mirror else ""}</tspan></text>')
    y = MARGIN + 21
    for line in wrap(", ".join(refs), 120)[:2]:
        t.append(f'<text x="{x0}" y="{y:.1f}" font-size="4" fill="{COLORS["text"]}">'
                 f'{html.escape(line)}</text>')
        y += 5

    # Legend, top right.
    lx = PAGE_W - MARGIN - 52
    legend = [(COLORS["highlight"], "This step")]
    if any(ref_prefix(r).upper().startswith(POLARIZED_PREFIXES) for r in refs):
        pin1 = {"D": "Pin 1 (LED cathode)", "BT": "Pin 1 (+)"}.get(ref_prefix(refs[0]).upper(), "Pin 1")
        legend.append((COLORS["pin1"], pin1))
    if placed:
        legend.append((COLORS["placed"], "Placed in earlier steps"))
    for i, (color, label) in enumerate(legend):
        ly = MARGIN + 3 + i * 6
        t.append(f'<rect x="{lx}" y="{ly}" width="4" height="4" fill="{color}" stroke="#0003" stroke-width="0.2"/>')
        t.append(f'<text x="{lx + 6}" y="{ly + 3.3}" font-size="3.6" fill="{COLORS["text"]}">{html.escape(label)}</text>')

    t.append(f'<line x1="{MARGIN}" y1="{MARGIN + HEADER_H - 4}" x2="{PAGE_W - MARGIN}" '
             f'y2="{MARGIN + HEADER_H - 4}" stroke="#ccc" stroke-width="0.3"/>')

    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}mm" height="{PAGE_H}mm" '
        f'viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Helvetica, Arial, sans-serif">\n'
        f'<rect width="100%" height="100%" fill="{COLORS["page"]}"/>\n'
        + "\n".join(t)
        + f'\n<g transform="{transform}">\n{board_svg}\n</g>\n</svg>\n'
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pcb", nargs="?",
                    default=os.path.join(REPO_ROOT, "pcbs/nametag_back/nametag_back.kicad_pcb"))
    ap.add_argument("-o", "--output", default=os.path.join(REPO_ROOT, "docs/assembly/assembly_guide.pdf"))
    ap.add_argument("--skip", nargs="*", default=["BT1"], metavar="REF",
                    help="references to leave out (default: BT1, the AA holder)")
    ap.add_argument("--last", nargs="*", default=["R"], metavar="PREFIX",
                    help="reference prefixes whose pages go at the end (default: R)")
    ap.add_argument("--title", help="title shown on every page (default: board file name)")
    ap.add_argument("--keep-svg", metavar="DIR", help="also write each page's SVG into DIR")
    args = ap.parse_args()

    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        sys.exit("error: rsvg-convert not found; install librsvg (brew install librsvg)")

    board = pcbnew.LoadBoard(args.pcb)
    title = args.title or f"{os.path.splitext(os.path.basename(args.pcb))[0]} assembly"
    groups = group_components(board, set(args.skip), {p.upper() for p in args.last})
    if not groups:
        sys.exit("error: no components to document on this board")

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = args.keep_svg or tmp
        os.makedirs(out_dir, exist_ok=True)
        pages, placed = [], []
        for step, group in enumerate(groups, 1):
            svg = page_svg(board, title, step, len(groups), group, placed)
            path = os.path.join(out_dir, f"page_{step:02d}.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            pages.append(path)
            placed.extend(group["footprints"])
            print(f"Step {step:2d}: {group['value']} x{len(group['refs'])} ({', '.join(group['refs'])})")

        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        subprocess.run([rsvg, "-f", "pdf", "-o", args.output, *pages], check=True)
    print(f"Wrote {len(pages)} pages -> {os.path.relpath(args.output)}")


if __name__ == "__main__":
    main()
