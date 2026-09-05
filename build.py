import base64
import io
import json
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent
PIECES = ROOT / "pieces"
CSS_OUT = ROOT / "ngnl-theme.css"
USERSCRIPT_OUT = ROOT / "ngnl-theme.user.js"
NAMES = ("wp", "wn", "wb", "wr", "wq", "wk", "bp", "bn", "bb", "br", "bq", "bk")
VERSION = "2.8.0"
TEXTURE = 256

BOARD_LIGHT = (142, 240, 200)
BOARD_DARK = (87, 134, 231)
BOARD_SQUARE = 64

TARGETS = (".piece.{name}", ".promotion-piece.{name}", ".vfx .element.{name}")
BOARD_TARGETS = ("wc-chess-board", "chess-board", ".board", ".fade-in-overlay")

BOARD_HOSTS = ('wc-chess-board, chess-board, .board, .fade-in-overlay, '
               '[class*="board"]')

BOARD_TEXTURE = (r'(chess-themes/boards/'
                 r'|assets-themes\.chess\.com/image/[^/"]+/\d+\.png)')

NL = "\n"


def piece_uri(name: str) -> str:
    texture = cairosvg.svg2png(
        bytestring=(PIECES / f"{name}.svg").read_bytes(),
        output_width=TEXTURE,
        output_height=TEXTURE,
    )
    return "data:image/png;base64," + base64.b64encode(texture).decode("ascii")


def board_uri() -> str:
    size = BOARD_SQUARE * 8
    board = Image.new("RGB", (size, size), BOARD_LIGHT)
    dark = Image.new("RGB", (BOARD_SQUARE, BOARD_SQUARE), BOARD_DARK)
    for rank in range(8):
        for file in range(8):
            if (rank + file) % 2:
                board.paste(dark, (file * BOARD_SQUARE, rank * BOARD_SQUARE))
    buffer = io.BytesIO()
    board.save(buffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def piece_css(uris: dict[str, str], indent: str = "") -> list[str]:
    lines = [f"{indent}:root {{"]
    for name in NAMES:
        lines.append(f'{indent}  --ngnl-{name}: url("{uris[name]}");')
    lines.append("")
    for name in NAMES:
        lines.append(
            f"{indent}  --theme-piece-set-{name}: var(--ngnl-{name}) !important;"
        )
    lines += [f"{indent}}}", ""]
    for name in NAMES:
        selector = ", ".join(t.format(name=name) for t in TARGETS)
        lines += [
            f"{indent}{selector} {{",
            f"{indent}  background-image: var(--ngnl-{name}) !important;",
            f"{indent}  background-size: 100% 100% !important;",
            f"{indent}  background-repeat: no-repeat !important;",
            f"{indent}  background-position: center !important;",
            f"{indent}}}",
            "",
        ]
    return lines


def board_rule(indent: str = "") -> list[str]:
    return [
        f"{indent}{', '.join(BOARD_TARGETS)} {{",
        f"{indent}  background-image: var(--ngnl-board) !important;",
        f"{indent}  background-size: 100% 100% !important;",
        f"{indent}  background-repeat: no-repeat !important;",
        f"{indent}  background-position: center !important;",
        f"{indent}}}",
        "",
    ]


def board_css(uri: str, indent: str = "") -> list[str]:
    return [
        f"{indent}:root {{",
        f'{indent}  --ngnl-board: url("{uri}");',
        f"{indent}  --theme-board-style-image: var(--ngnl-board) !important;",
        f"{indent}}}",
        "",
    ] + board_rule(indent)


def build_css(uris: dict[str, str], board: str) -> str:
    lines = [
        "/* ==UserStyle==",
        "@name           NGNL Chess Pieces",
        "@namespace      github.com/ngnl-theme",
        f"@version        {VERSION}",
        "@description    Fan-made No Game No Life chess pieces for Chess.com.",
        "==/UserStyle== */",
        "",
        '@-moz-document domain("chess.com") {',
        "",
    ]
    lines += piece_css(uris, "  ")
    lines += board_css(board, "  ")
    lines.append("}")
    return NL.join(lines)


def build_userscript(uris: dict[str, str], board: str) -> str:
    board_rule_js = " +\n".join(
        "    " + json.dumps(line + "\n") for line in board_rule()
    )
    return NL.join([
        "// ==UserScript==",
        "// @name         NGNL Chess Pieces",
        "// @namespace    github.com/ngnl-theme",
        f"// @version      {VERSION}",
        "// @description  Fan-made No Game No Life piece set for Chess.com.",
        "// @match        https://www.chess.com/*",
        "// @match        https://chess.com/*",
        "// @run-at       document-start",
        "// @grant        none",
        "// ==/UserScript==",
        "",
        "(function () {",
        '  "use strict";',
        "",
        "  const NGNL_PIECES = true;",
        "  const NGNL_BOARD_COLORS = true;",
        "",
        "  const PIECE_CSS = " + json.dumps(NL.join(piece_css(uris))) + ";",
        "",
        "  const BOARD_URI = " + json.dumps(board) + ";",
        "",
        "  const BOARD_IMAGE = 'url(\"' + BOARD_URI + '\")';",
        "",
        "  const BOARD_CSS =",
        "    ':root {\\n  --ngnl-board: ' + BOARD_IMAGE + ';\\n' +",
        "    '  --theme-board-style-image: var(--ngnl-board) !important;\\n}\\n\\n' +",
        board_rule_js + ";",
        "",
        "  const CSS =",
        '    (NGNL_PIECES ? PIECE_CSS : "") +',
        '    (NGNL_BOARD_COLORS ? BOARD_CSS : "");',
        "",
        '  const STYLE_ID = "ngnl-piece-set";',
        "  const BOARD_HOSTS = " + json.dumps(BOARD_HOSTS) + ";",
        "  const BOARD_TEXTURE = new RegExp(" + json.dumps(BOARD_TEXTURE) + ");",
        "",
        "  function install() {",
        "    if (!CSS) return;",
        "    let style = document.getElementById(STYLE_ID);",
        "    if (!style) {",
        '      style = document.createElement("style");',
        "      style.id = STYLE_ID;",
        "    }",
        "    if (style.textContent !== CSS) {",
        "      style.textContent = CSS;",
        "    }",
        "    const parent = document.head || document.documentElement;",
        "    if (style.parentNode !== parent || parent.lastChild !== style) {",
        "      parent.appendChild(style);",
        "    }",
        "  }",
        "",
        "  function paintBoard(el) {",
        "    if (!el || !el.style) return false;",
        '    if (el.style.backgroundImage.indexOf("data:") !== -1) return false;',
        '    el.style.setProperty("background-image", BOARD_IMAGE, "important");',
        '    el.style.setProperty("background-size", "100% 100%", "important");',
        '    el.style.setProperty("background-repeat", "no-repeat", "important");',
        '    el.style.setProperty("background-position", "center", "important");',
        "    return true;",
        "  }",
        "",
        "  function paintBoards() {",
        "    if (!NGNL_BOARD_COLORS) return 0;",
        "    let count = 0;",
        "    try {",
        '      const piece = document.querySelector(".piece");',
        "      if (piece && piece.parentElement) {",
        "        if (paintBoard(piece.parentElement)) count += 1;",
        "      }",
        "      const nodes = document.querySelectorAll(BOARD_HOSTS);",
        "      for (let i = 0; i < nodes.length; i += 1) {",
        "        const el = nodes[i];",
        "        if (!el.style) continue;",
        '        if (el.style.backgroundImage.indexOf("data:") !== -1) continue;',
        "        const painted = window.getComputedStyle(el).backgroundImage;",
        '        if (!painted || painted === "none") continue;',
        "        if (!BOARD_TEXTURE.test(painted)) continue;",
        "        if (paintBoard(el)) count += 1;",
        "      }",
        "    } catch (error) {",
        "      return count;",
        "    }",
        "    return count;",
        "  }",
        "",
        "  function apply() {",
        "    install();",
        "    paintBoards();",
        "  }",
        "",
        "  apply();",
        "",
        "  let queued = false;",
        "  const observer = new MutationObserver(function () {",
        "    if (queued) return;",
        "    queued = true;",
        "    setTimeout(function () {",
        "      queued = false;",
        "      apply();",
        "    }, 0);",
        "  });",
        "  observer.observe(document.documentElement, {",
        "    childList: true,",
        "    subtree: true,",
        "  });",
        "",
        '  document.addEventListener("DOMContentLoaded", apply);',
        "  window.NGNL_THEME = {",
        f'    version: "{VERSION}",',
        "    pieces: NGNL_PIECES,",
        "    board: NGNL_BOARD_COLORS,",
        "    css: CSS,",
        "    reapply: apply,",
        "    paintBoards: paintBoards,",
        "    boardElement: function () {",
        '      const piece = document.querySelector(".piece");',
        "      return piece ? piece.parentElement : null;",
        "    },",
        "  };",
        '  console.info("[NGNL Theme] v' + VERSION
        + ' pieces=" + NGNL_PIECES + " board=" + NGNL_BOARD_COLORS);',
        "})();",
        "",
    ])


def main() -> None:
    uris = {name: piece_uri(name) for name in NAMES}
    board = board_uri()
    CSS_OUT.write_text(build_css(uris, board), encoding="utf-8")
    USERSCRIPT_OUT.write_text(build_userscript(uris, board), encoding="utf-8")
    print(CSS_OUT)
    print(USERSCRIPT_OUT)


if __name__ == "__main__":
    main()
