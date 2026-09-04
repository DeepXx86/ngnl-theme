from io import BytesIO
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import extract_trace as pipeline

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "preview" / "extraction-comparison.png"

CELL = 180
GAP = 10
HEAD = 46
LABEL = 24
BACKDROP = (24, 31, 54)
STRIPE = (33, 43, 71)
TEXT = (226, 234, 248)
DIM = (150, 165, 196)


def font(size):
    for name in ("segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit(image, box=CELL):
    image = image.copy()
    image.thumbnail((box, box), Image.LANCZOS)
    tile = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    tile.paste(image, ((box - image.width) // 2, (box - image.height) // 2))
    return tile


def render(path_data, size):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           f'<path d="{path_data}" fill="#000"/></svg>')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    return np.array(Image.open(BytesIO(png)).split()[-1])


def overlay(mask, path_data):
    ys, xs = np.nonzero(mask)
    height = ys.max() - ys.min()
    drawn = (render(path_data, 700) > 128).astype(np.uint8)
    dy, dx = np.nonzero(drawn)
    scale = height / (dy.max() - dy.min())
    matrix = np.float32([
        [scale, 0, (xs.min() + xs.max()) / 2 - (dx.min() + dx.max()) / 2 * scale],
        [0, scale, ys.min() - dy.min() * scale],
    ])
    warped = cv2.warpAffine(drawn * 255, matrix, (mask.shape[1], mask.shape[0]))

    view = np.zeros((*mask.shape, 3), np.uint8)
    view[mask > 127] = (90, 96, 112)
    contours, _ = cv2.findContours(warped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(view, contours, -1, (255, 150, 40), max(2, height // 130))
    alpha = np.where(view.any(axis=2), 255, 0).astype(np.uint8)
    cut = np.dstack([view, alpha])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return Image.fromarray(cut)


def main():
    images = {}
    for name, path in pipeline.SOURCE_FILES.items():
        images[name] = cv2.imread(str(path))
        if images[name] is None:
            raise SystemExit(f"missing source: {path}")
    bodies, _ = pipeline.build(images)

    rows = ["Source square", "Recovered silhouette", "Rebuilt geometry",
            "Black piece", "White piece"]
    order = pipeline.ORDER
    width = GAP + len(order) * (CELL + GAP)
    height = HEAD + len(rows) * (LABEL + CELL + GAP)
    sheet = Image.new("RGB", (width, height), BACKDROP)
    draw = ImageDraw.Draw(sheet)

    head_font, row_font = font(18), font(13)
    for column, code in enumerate(order):
        x = GAP + column * (CELL + GAP)
        source = pipeline.INSTANCES[code][0]
        draw.text((x + 4, 6), pipeline.PIECE_NAMES[code].upper(), TEXT, head_font)
        draw.text((x + 4, 27), source, DIM, row_font)

    y = HEAD
    for index, title in enumerate(rows):
        draw.rectangle([0, y, width, y + LABEL + CELL + GAP - 1],
                       STRIPE if index % 2 else BACKDROP)
        draw.text((GAP + 2, y + 5), title, DIM, row_font)
        for column, code in enumerate(order):
            x = GAP + column * (CELL + GAP)
            top = y + LABEL
            if index == 0:
                source, file_index, rank_index, _ = pipeline.INSTANCES[code]
                crop = pipeline.square(images[source], source, file_index, rank_index,
                                       pad=3, scale=4)
                tile = fit(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).convert("RGBA"))
            elif index == 1:
                mask = pipeline.piece_mask(images, code)
                ys, xs = np.nonzero(mask)
                cut = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                rgba = np.zeros((*cut.shape, 4), np.uint8)
                rgba[..., :3] = 231
                rgba[..., 3] = cut
                tile = fit(Image.fromarray(rgba))
            elif index == 2:
                tile = fit(overlay(pipeline.piece_mask(images, code), bodies[code]))
            else:
                name = ("b" if index == 3 else "w") + code
                png = cairosvg.svg2png(url=str(ROOT / "pieces" / f"{name}.svg"),
                                       output_width=CELL, output_height=CELL)
                tile = Image.open(BytesIO(png)).convert("RGBA")
            sheet.paste(tile, (x, top), tile)
        y += LABEL + CELL + GAP

    OUT.parent.mkdir(exist_ok=True)
    sheet.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
