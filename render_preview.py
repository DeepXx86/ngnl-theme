from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image


ROOT = Path(__file__).resolve().parent
PIECES = ROOT / "pieces"
OUT = ROOT / "preview" / "ngnl-piece-theme.png"
SIZE = 128
LIGHT = "#8ef0c8"
DARK = "#5786e7"


def render_piece(name: str) -> Image.Image:
    png = cairosvg.svg2png(
        url=str(PIECES / f"{name}.svg"),
        output_width=SIZE,
        output_height=SIZE,
    )
    return Image.open(BytesIO(png)).convert("RGBA")


def main() -> None:
    board = Image.new("RGB", (SIZE * 8, SIZE * 8))
    for rank in range(8):
        for file in range(8):
            color = LIGHT if (rank + file) % 2 == 0 else DARK
            tile = Image.new("RGB", (SIZE, SIZE), color)
            board.paste(tile, (file * SIZE, rank * SIZE))

    order = "rnbqkbnr"
    layout = {}
    for file, kind in enumerate(order):
        layout[(file, 0)] = f"b{kind}"
        layout[(file, 7)] = f"w{kind}"
        layout[(file, 1)] = "bp"
        layout[(file, 6)] = "wp"

    rendered = {name: render_piece(name) for name in set(layout.values())}
    for (file, rank), name in layout.items():
        piece = rendered[name]
        board.paste(piece, (file * SIZE, rank * SIZE), piece)

    OUT.parent.mkdir(exist_ok=True)
    board.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
