import base64
import json
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parent
PIECES = ROOT / "pieces"
CSS_OUT = ROOT / "ngnl-theme.css"
USERSCRIPT_OUT = ROOT / "ngnl-theme.user.js"
NAMES = ("wp", "wn", "wb", "wr", "wq", "wk", "bp", "bn", "bb", "br", "bq", "bk")

TARGETS = (".piece.{name}", ".promotion-piece.{name}", ".vfx .element.{name}")


def data_uri(name: str) -> str:
    source = (PIECES / f"{name}.svg").read_bytes()
    texture = cairosvg.svg2png(
        bytestring=source,
        output_width=256,
        output_height=256,
    )
    encoded = base64.b64encode(texture).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def piece_rules(uris: dict[str, str], indent: str = "") -> list[str]:
    lines = []
    for name in NAMES:
        selector = ", ".join(t.format(name=name) for t in TARGETS)
        lines += [
            f"{indent}{selector} {{",
            f'{indent}  background-image: url("{uris[name]}") !important;',
            f"{indent}  background-size: 100% 100% !important;",
            f"{indent}  background-repeat: no-repeat !important;",
            f"{indent}  background-position: center !important;",
            f"{indent}}}",
            "",
        ]
    return lines


def variable_rule(uris: dict[str, str], indent: str = "") -> list[str]:
    lines = [f"{indent}:root {{"]
    for name in NAMES:
        lines.append(f'{indent}  --theme-piece-set-{name}: url("{uris[name]}") !important;')
    lines += [f"{indent}}}", ""]
    return lines


def build_css(uris: dict[str, str]) -> str:
    lines = [
        "/* ==UserStyle==",
        "@name           NGNL Chess Pieces",
        "@namespace      github.com/ngnl-theme",
        "@version        2.2.0",
        "@description    Fan-made No Game No Life chess pieces for Chess.com.",
        "==/UserStyle== */",
        "",
        '@-moz-document domain("chess.com") {',
        "",
        "  /* Board colours are deliberately untouched - they are your setting. */",
        "",
    ]
    lines += piece_rules(uris, "  ")
    lines.append("}")
    return "\n".join(lines)


def build_userscript(uris: dict[str, str]) -> str:
    entries = [f"  [{json.dumps(n)}, {json.dumps(uris[n])}]," for n in NAMES]
    return "\n".join([
        "// ==UserScript==",
        "// @name         NGNL Chess Pieces",
        "// @namespace    github.com/ngnl-theme",
        "// @version      2.2.0",
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
        "  const EMBEDDED_PNGS = new Map([",
        "    /* White */",
        *[f"  {e}" for e in entries[:6]],
        "    /* Black */",
        *[f"  {e}" for e in entries[6:]],
        "  ]);",
        "",
        "  function makeTextureUrl(dataUri) {",
        '    const encoded = dataUri.slice(dataUri.indexOf(",") + 1);',
        "    const binary = atob(encoded);",
        "    const bytes = new Uint8Array(binary.length);",
        "    for (let i = 0; i < binary.length; i += 1) {",
        "      bytes[i] = binary.charCodeAt(i);",
        "    }",
        '    return URL.createObjectURL(new Blob([bytes], { type: "image/png" }));',
        "  }",
        "",
        "  // PixiJS rejects long data: URLs as WebGL texture sources on the",
        "  // game board. Short blob: URLs decode as normal PNG images.",
        "  const PIECES = new Map(Array.from(EMBEDDED_PNGS, ([name, dataUri]) =>",
        "    [name, makeTextureUrl(dataUri)]",
        "  ));",
        "",
        "  // Chess.com paints the board with its own ID-scoped rules and no",
        "  // !important, so these win no matter what order the styles land in.",
        "  // The custom properties are set too, for the surfaces that read them.",
        "  const CSS = [",
        '    "html:root {",',
        "    ...Array.from(PIECES, ([name, url]) =>",
        '      `  --theme-piece-set-${name}: url("${url}") !important;`),',
        '    "}",',
        "    ...Array.from(PIECES, ([name, url]) => [",
        '      `.piece.${name}, .promotion-piece.${name}, .vfx .element.${name} {`,',
        '      `  background-image: url("${url}") !important;`,',
        '      "  background-size: 100% 100% !important;",',
        '      "  background-repeat: no-repeat !important;",',
        '      "  background-position: center !important;",',
        '      "}",',
        '    ].join("\\n")),',
        '  ].join("\\n");',
        "",
        '  const STYLE_ID = "ngnl-piece-set";',
        "",
        "  function install() {",
        "    let style = document.getElementById(STYLE_ID);",
        "    if (!style) {",
        '      style = document.createElement("style");',
        "      style.id = STYLE_ID;",
        "      style.textContent = CSS;",
        "    }",
        "    const parent = document.head || document.documentElement;",
        "    // Keep it last so it also wins on ties, not just on !important.",
        "    if (style.parentNode !== parent || parent.lastChild !== style) {",
        "      parent.appendChild(style);",
        "    }",
        "  }",
        "",
        "  install();",
        "",
        "  // Chess.com is a single-page app: it swaps boards in and out and",
        "  // injects fresh <style> blocks as you navigate. Re-assert on change,",
        "  // debounced to one pass per tick so this stays cheap.  setTimeout,",
        "  // not requestAnimationFrame: rAF is paused in a background tab, and",
        "  // the style has to be restored even when the tab is not being looked",
        "  // at.",
        "  let queued = false;",
        "  const observer = new MutationObserver(function () {",
        "    if (queued) return;",
        "    queued = true;",
        "    setTimeout(function () {",
        "      queued = false;",
        "      install();",
        "    }, 0);",
        "  });",
        "  observer.observe(document.documentElement, {",
        "    childList: true,",
        "    subtree: true,",
        "  });",
        "",
        '  document.addEventListener("DOMContentLoaded", install);',
        '  console.info("[NGNL Theme] v2.2.0: blob PNG textures installed");',
        "})();",
        "",
    ])


def main() -> None:
    uris = {name: data_uri(name) for name in NAMES}
    CSS_OUT.write_text(build_css(uris), encoding="utf-8")
    USERSCRIPT_OUT.write_text(build_userscript(uris), encoding="utf-8")
    print(CSS_OUT)
    print(USERSCRIPT_OUT)


if __name__ == "__main__":
    main()
