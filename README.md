# NGNL Chess Piece Theme

Fan-made *No Game No Life* SVG pieces for Chess.com.

## Install

- **Tampermonkey** (recommended): new script, paste `ngnl-theme.user.js`, save,
  refresh chess.com.
- **Stylus:** new style, paste `ngnl-theme.css`, save, refresh.

### Turning parts on and off

Two switches sit at the top of `ngnl-theme.user.js`. Set either to `false`, save,
refresh:

```js
const NGNL_PIECES = true;
const NGNL_BOARD_COLORS = true;
```

`NGNL_PIECES` is the 12 piece sprites. `NGNL_BOARD_COLORS` is the board itself,
in the anime's mint `#8ef0c8` and blue `#5786e7`. Turn the board off to keep your
own Chess.com board theme and only change the pieces. Both `false` injects
nothing at all.

The Stylus file has no switches - it is plain CSS. To drop the board colours
there, delete the rule block containing `--ngnl-board`.

To change the colours, edit `BOARD_LIGHT` and `BOARD_DARK` in `build.py` and
re-run it.


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

## Note

I did my best with this project! I’m not an artist, so I used code to create and recreate the images as accurately as I could.

I’ll keep improving and upgrading the theme in the future… probably later though, because I’m lazy 😭
