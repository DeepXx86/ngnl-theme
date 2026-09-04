import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import design

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = {
    "thumbnail": ROOT / "reference" / "ngnl-thumbnail.webp",
    "board frame": ROOT / "reference" / "board-frame-avg.png",
    "late board": ROOT / "reference" / "board-frame-late.png",
    "close-up": ROOT / "reference" / "pieces-closeup.png",
}
CROPS = ROOT / "extracted-pieces" / "source-crops"
MASKS = ROOT / "extracted-pieces" / "masks"
PIECES = ROOT / "pieces"
MAP = ROOT / "extracted-pieces" / "extraction-map.json"

# grid: x0, y0, square width, square height, supersampling, padding
GRIDS = {
    "thumbnail": (102.0, 17.3, 219.8, 219.6, 5, 14),
    "board frame": (21.0, 27.0, 99.25, 98.0, 8, 8),
    "late board": (18.5, 8.5, 123.4, 123.5, 8, 12),
    # The close-up is already cropped to three squares, so its "grid" is the
    # square pitch measured across them; there is only one rank in it.
    "close-up": (4.0, -1.0, 342.0, 342.0, 4, 4),
}
# piece -> source, file, rank, polarity.  Light-green squares are used wherever
# possible: a piece on a blue square has about half the contrast and falls apart
# under thresholding.
INSTANCES = {
    "p": ("thumbnail", 1, 2, "light"),
    "n": ("thumbnail", 3, 0, "dark"),
    "b": ("close-up", 0, 0, "dark"),
    "q": ("thumbnail", 0, 0, "light"),
    "r": ("board frame", 7, 0, "dark"),
    "k": ("late board", 6, 0, "dark"),
}
SOURCE_NOTES = {
    "thumbnail": "1280x720 close-up of the board; thin features survive here",
    "board frame": ("114 identical frames (33.1-35.9 s) averaged at 1920x1080 "
                    "to cancel codec noise"),
    "late board": "later board shot, 123 px squares; the only frame with a legible king",
    "close-up": "three squares filling the frame; the sharpest bishop available",
}
SYMMETRIC = {"p", "b", "r", "q", "k"}
PIECE_NAMES = {"p": "pawn", "n": "knight", "b": "bishop",
               "r": "rook", "q": "queen", "k": "king"}
ORDER = "pnbrqk"

# Layout inside the 100x100 viewBox.
# The outline is painted OUTSIDE the silhouette: the body is stroked once at
# double width and then filled over, so the fill covers the inner half of the
# stroke.  A centred stroke eats OUTLINE units into every edge, which is enough
# to swallow a thin feature whole - the bishop's needle is only about 1.2 units
# wide, so an inner half of the same order erased it and left just the outline.
# TOP and SIDE leave room for the mitre overshoot at the sharp tips: a spike
# joined at a few degrees extends the outline by up to STROKE * miterlimit
# beyond the point itself, and the tips must not touch the viewBox edge.
BASELINE = 95.0
TOP = 9.0
SIDE = 8.0
OUTLINE = 1.8                 # visible band, entirely outside the shape
STROKE = OUTLINE * 2

# Sampled off the sources.  On screen the anime pieces are a slate blue, not
# black: the core of a dark piece measures #41689f and its glow rim #cfeef2,
# while a light piece is #f5f7fb with a pale lavender rim.  The fills below keep
# those hues but go a few steps deeper, because the frames are a bloomed CRT
# shot and the sampled values alone do not separate on every board theme.
THEME = {
    "w": {"fill": "#f3f7fb", "line": "#8fa6d6", "glow": "#dbe7ff", "label": "white"},
    "b": {"fill": "#33578f", "line": "#d2f0f7", "glow": "#8bd8f2", "label": "black"},
}


# --------------------------------------------------------------------------- #
# silhouette recovery
# --------------------------------------------------------------------------- #

def square(img, source, file_index, rank_index, pad=None, scale=None):
    """Sub-pixel crop of one board square, magnified."""
    x0, y0, sx, sy, default_scale, default_pad = GRIDS[source]
    pad = default_pad if pad is None else pad
    scale = default_scale if scale is None else scale
    left = x0 + file_index * sx - pad
    top = y0 + rank_index * sy - pad
    width = int(round(sx + 2 * pad)) * scale
    height = int(round(sy + 2 * pad)) * scale
    matrix = np.float32([[scale, 0, -left * scale], [0, scale, -top * scale]])
    return cv2.warpAffine(img, matrix, (width, height), flags=cv2.INTER_LANCZOS4)


def silhouette(big, source, polarity):
    """Threshold one magnified square into a piece mask."""
    scale, pad = GRIDS[source][4], GRIDS[source][5]
    lightness = cv2.cvtColor(big, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float64)
    lightness = cv2.GaussianBlur(lightness, (0, 0), scale * 0.35)

    edge = pad * scale
    inner = lightness[edge:-edge, edge:-edge]
    band = max(3, int(0.04 * inner.shape[1]))
    ring = np.concatenate([
        inner[:band].ravel(), inner[-band:].ravel(),
        inner[:, :band].ravel(), inner[:, -band:].ravel(),
    ])
    background = np.median(ring)
    if polarity == "dark":
        piece = np.percentile(inner, 2)
        mask = lightness < background - (background - piece) * 0.45
    else:
        piece = np.percentile(inner, 98)
        mask = lightness > background + (piece - background) * 0.45

    mask = mask.astype(np.uint8) * 255
    keep = edge // 2
    mask[:keep] = 0
    mask[-keep:] = 0
    mask[:, :keep] = 0
    mask[:, -keep:] = 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count > 1:
        mask = ((labels == 1 + int(np.argmax(stats[1:, 4]))) * 255).astype(np.uint8)
    return mask


def piece_mask(images, code, symmetrise=True):
    source, file_index, rank_index, polarity = INSTANCES[code]
    mask = silhouette(square(images[source], source, file_index, rank_index),
                      source, polarity)
    if symmetrise and code in SYMMETRIC:
        ys, xs = np.nonzero(mask)
        centre = (xs.min() + xs.max()) / 2
        height, width = mask.shape
        shifted = cv2.warpAffine(mask, np.float32([[1, 0, width / 2 - centre], [0, 1, 0]]),
                                 (width, height), flags=cv2.INTER_LINEAR)
        soft = shifted.astype(np.float64) / 255.0
        mask = (((soft + soft[:, ::-1]) / 2) > 0.5).astype(np.uint8) * 255
    return fill_holes(mask)


def fill_holes(mask):
    flooded = mask.copy()
    height, width = mask.shape
    cv2.floodFill(flooded, np.zeros((height + 2, width + 2), np.uint8), (0, 0), 255)
    return cv2.bitwise_or(mask, (flooded == 0).astype(np.uint8) * 255)


def normalised(mask):
    """Outline points scaled so the piece is 1.0 tall and centred on x = 0."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea).astype(np.float32)
    ys, xs = np.nonzero(mask)
    height = float(ys.max() - ys.min())
    centre = (xs.min() + xs.max()) / 2.0
    points = contour.reshape(-1, 2).astype(np.float64)
    points[:, 0] = (points[:, 0] - centre) / height
    points[:, 1] = (points[:, 1] - ys.min()) / height
    return points


# --------------------------------------------------------------------------- #
# the knight: the one piece that stays a trace
# --------------------------------------------------------------------------- #

def knight_outline(mask, epsilon=0.0022, sharp_deg=46.0, round_frac=0.62):
    """Simplify the knight contour, rounding only the shallow turns."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea).astype(np.float32)
    simple = cv2.approxPolyDP(contour, epsilon * cv2.arcLength(contour, True), True)
    points = simple.reshape(-1, 2).astype(np.float64)

    ys, xs = np.nonzero(mask)
    height = float(ys.max() - ys.min())
    points[:, 0] = (points[:, 0] - (xs.min() + xs.max()) / 2.0) / height
    points[:, 1] = (points[:, 1] - ys.min()) / height

    # Sit the knight on the same flat base as the other five.
    on_base = points[:, 1] > 0.97
    points[on_base, 1] = points[on_base, 1].mean()

    count = len(points)
    radii = []
    for i in range(count):
        prev, here, nxt = points[i - 1], points[i], points[(i + 1) % count]
        into, out_of = here - prev, nxt - here
        len_in, len_out = float(np.hypot(*into)), float(np.hypot(*out_of))
        if len_in == 0 or len_out == 0:
            radii.append(0.0)
            continue
        cosine = float(np.clip(np.dot(into / len_in, out_of / len_out), -1.0, 1.0))
        turn = np.degrees(np.arccos(cosine))
        weight = 0.0 if turn >= sharp_deg else round_frac * (1.0 - turn / sharp_deg) ** 0.4
        radii.append(weight * min(len_in, len_out) * 0.5)
    return points, radii


def knight_path(points, radii, tf, digits=2):
    count = len(points)
    fmt = "{:." + str(digits) + "f}"
    view = [np.array(tf(x, y)) for x, y in points]
    scale = abs(tf(1.0, 0.0)[0] - tf(0.0, 0.0)[0])
    trims = [r * scale for r in radii]
    for i in range(count):
        j = (i + 1) % count
        span = float(np.hypot(*(view[j] - view[i]))) * 0.98
        if trims[i] + trims[j] > span > 0:
            shrink = span / (trims[i] + trims[j])
            trims[i] *= shrink
            trims[j] *= shrink

    def p(point):
        return fmt.format(point[0]) + " " + fmt.format(point[1])

    def toward(i, j, trim):
        step = view[j] - view[i]
        length = float(np.hypot(*step))
        return view[i] if length == 0 else view[i] + step / length * trim

    parts = []
    for i in range(count):
        arrive = toward(i, i - 1, trims[i])
        leave = toward(i, (i + 1) % count, trims[i])
        parts.append(("M" if i == 0 else "L") + p(arrive))
        if trims[i] > 1e-9:
            c1 = view[i] + (arrive - view[i]) * (1 - design.KAPPA)
            c2 = view[i] + (leave - view[i]) * (1 - design.KAPPA)
            parts.append("C" + p(c1) + " " + p(c2) + " " + p(leave))
    parts.append("Z")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="NGNL {label} {piece}" shape-rendering="geometricPrecision">
  <defs>
    <filter id="ngnl-glow" x="-25%" y="-25%" width="150%" height="150%">
      <feDropShadow dx="0" dy="0" stdDeviation="1.25" flood-color="{glow}" flood-opacity=".45"/>
    </filter>
  </defs>
  <g filter="url(#ngnl-glow)">
    <path d="{body}" fill="none" stroke="{line}" stroke-width="{stroke}" stroke-linejoin="miter" stroke-miterlimit="{miter}"/>
    <path d="{body}" fill="{fill}"/>{detail}
  </g>
</svg>
"""
DETAIL = '\n    <path d="{d}" fill="{line}"/>'


def half_width(code, knight):
    if code == "n":
        return max(abs(knight[0][:, 0].min()), abs(knight[0][:, 0].max()))
    xs = [abs(seg[1]) for seg in design.HALVES[code]]
    return max(xs)


def build(images, report=False):
    knight = knight_outline(piece_mask(images, "n"))

    # One shared unit keeps the pieces in the proportions the anime gives them.
    unit = min((BASELINE - TOP) / max(design.HEIGHT.values()),
               (50.0 - SIDE) / max(half_width(c, knight) * design.HEIGHT[c]
                                   for c in ORDER))

    bodies, details = {}, {}
    for code in ORDER:
        scale = unit * design.HEIGHT[code]
        base = BASELINE - scale

        def tf(x, y, scale=scale, base=base):
            return (50.0 + x * scale, base + y * scale)

        if code == "n":
            bodies[code] = knight_path(knight[0], knight[1], tf)
            details[code] = design.eye_path(tf)
        else:
            bodies[code] = design.path_data(code, tf)
            details[code] = design.cross_path(code, tf) if code in design.CROSS else None

        if report:
            print(f"{PIECE_NAMES[code]:7s} source={design.SOURCE_OF[code]:12s} "
                  f"height={design.HEIGHT[code]:.3f} sq  "
                  f"half-width={half_width(code, knight):.3f} h  "
                  f"drawn={scale:.1f} units")
    return bodies, details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true",
                        help="print the measurements each piece was built from")
    args = parser.parse_args()

    images = {}
    for name, path in SOURCE_FILES.items():
        images[name] = cv2.imread(str(path))
        if images[name] is None:
            raise SystemExit(f"missing source: {path}")
    for folder in (CROPS, MASKS, PIECES):
        folder.mkdir(parents=True, exist_ok=True)

    for code in ORDER:
        source, file_index, rank_index, _ = INSTANCES[code]
        cv2.imwrite(str(MASKS / f"{PIECE_NAMES[code]}.png"), piece_mask(images, code))
        cv2.imwrite(str(CROPS / f"{PIECE_NAMES[code]}.png"),
                    square(images[source], source, file_index, rank_index, pad=3, scale=4))

    bodies, details = build(images, report=args.report)
    for code in ORDER:
        for side, theme in THEME.items():
            svg = SVG.format(
                label=theme["label"], piece=PIECE_NAMES[code],
                body=bodies[code], fill=theme["fill"], line=theme["line"],
                glow=theme["glow"], stroke=STROKE,
                miter=12 if code == "b" else 3,
                detail=DETAIL.format(d=details[code], line=theme["line"])
                if details[code] else "",
            )
            (PIECES / f"{side}{code}.svg").write_text(svg, encoding="utf-8")

    MAP.write_text(json.dumps({
        "sources": {
            name: {
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "note": SOURCE_NOTES[name],
                "grid": dict(zip(("x0", "y0", "square_width", "square_height",
                                  "supersampling", "pad"), GRIDS[name])),
            }
            for name, path in SOURCE_FILES.items()
        },
        "instances": {PIECE_NAMES[c]: dict(zip(("source", "file", "rank", "polarity"),
                                               INSTANCES[c])) for c in ORDER},
        "symmetrised": sorted(PIECE_NAMES[c] for c in SYMMETRIC),
        "height_in_squares": {PIECE_NAMES[c]: design.HEIGHT[c] for c in ORDER},
        "reconstruction": {PIECE_NAMES[c]: ("smoothed trace" if c == "n"
                                            else "geometry, see design.py") for c in ORDER},
        "detail_marks": {
            "bishop": "latin cross, hole y 0.315-0.616, bar at y 0.404; long needle to y 0.188",
            "queen": "latin cross, hole y 0.460-0.684, bar at y 0.572",
            "king": "latin cross, part of the silhouette: arms y 0.072-0.138 out to x 0.121",
            "knight": "eye, centre (-0.190, 0.305), radii 0.024 x 0.039, tilted 25 degrees",
        },
    }, indent=2), encoding="utf-8")

    print(f"wrote 12 svgs to {PIECES}")


if __name__ == "__main__":
    main()
