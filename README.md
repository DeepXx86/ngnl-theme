# NGNL Chess Piece Theme

Fan-made *No Game No Life* SVG pieces for Chess.com.

## Install

The Tampermonkey file contains 12 PNG textures rendered from the SVG pieces.

- **Tampermonkey** (recommended): new script, paste `ngnl-theme.user.js`, save,
  refresh chess.com.
- **Stylus:** works only on older DOM boards. Do not enable it together with
  Tampermonkey on the WebGL game board.

Neither touches the board colours. Your own board theme stays exactly as you set
it.

## Why it used to flash and revert

Chess.com uses a WebGL canvas on game boards and injects its own `<style>` at
runtime containing rules like

```css
#board-play-computer .piece.wp,
#board-play-computer .promotion-piece.wp,
#board-play-computer .vfx .element.wp { background-image: url(...theme.png) }
```

with the theme's PNG hard-coded and an ID in the selector. A style that only
overrides the custom properties therefore wins the first paint - which is the
second of NGNL pieces you saw - and loses the moment that block is injected.

The fix is to match the same three element shapes with `!important`. Chess.com
declares those rules *without* `!important`, so ours wins regardless of
specificity or injection order. The custom properties are still set as well,
because other surfaces on the site do read them.

The old script also applied its rules through `*:not(svg)`, which redeclared
twelve custom properties on every element in the document. That is expensive and
is the likely reason the board theme itself reset. It now writes to `:root` and
to the piece selectors only.

Because chess.com is a single-page app, a `MutationObserver` re-appends the
style if it is ever removed, debounced to one pass per tick. It uses
`setTimeout` rather than `requestAnimationFrame` so it still runs when the tab
is in the background.

Verified against a live board: all 12 pieces override, the style survives both a
newly injected chess.com rule and outright removal of the style element, and the
board colours are unchanged.

## Rebuild

```bash
python extract_trace.py
python render_trace.py
python render_preview.py
python build.py
```

To change a shape, edit the coordinates in `design.py` and re-run — they are all
named and commented. Colours live in `THEME` at the top of
`extract_trace.py`. Requires `opencv-python`, `numpy`, `pillow` and
`cairosvg`.

Reference video: <https://www.youtube.com/watch?v=vZKn-tQ6c0E>

This fan-made set is intended for personal use. The *No Game No Life* name and
source artwork belong to their respective rights holders.
