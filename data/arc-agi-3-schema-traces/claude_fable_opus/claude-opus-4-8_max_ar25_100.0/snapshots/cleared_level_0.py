"""World model for the ARC-AGI-3 mirror puzzle. STATELESS step() — reads piece position
from the passed grid each call (robust to backtest skipping transition #0).

LEVEL 0 mechanic (confirmed; render reproduces history exactly):
- Two mirror-locked rigid pieces move together (mirror axis = wall, x -> derived offsets):
    * RIGHT piece = "4-piece": solid L (color 4), arm-LEFT.
    * LEFT  piece = "template": hollow L (color 5 border + color 0 center holes), arm-RIGHT;
      it is the mirror image of the 4-piece and moves with template-shift = (oy, -ox).
- Directional actions shift by exactly 3px (one 3x3 tile):
    act1 UP (oy-=3); act2 DOWN (oy+=3); act3 RIGHT for 4-piece (ox+=3); act4 LEFT (ox-=3).
- Right border col x=W-1 = MOVE COUNTER: each directional move fills next cell top-down color 5.
- b-shape (fixed color-11 L) is a TARGET not a blocker: 4-piece slides onto it; overlap covers
  its border cells with 4 but each b-shape tile-CENTER (x%3==1 & y%3==1) stays color 11 (hollow).
- act5/6/7 observed/assumed no-op.

NOT YET CONFIRMED: win condition (hypothesis: 4-piece fully overlays b-shape) and blocking at
walls/edges. Not encoded until observed.
"""
import numpy as np

_LAST = [None, None]  # [E, analysis]  (avoid id(); use 'is' identity)


def _entry_analysis(E):
    if _LAST[0] is E and _LAST[1] is not None:
        return _LAST[1]
    H = len(E)
    W = len(E[0])
    piece4 = []
    tmpl = []
    bshape = []
    for y in range(H):
        for x in range(W):
            v = int(E[y][x])
            if v == 4:
                piece4.append((y, x))
            elif v == 0:
                tmpl.append((y, x, 0))
            elif v == 5 and x != W - 1 and y != H - 1:
                tmpl.append((y, x, 5))
            elif v == 11 and x != W - 1:
                bshape.append((y, x))
    fixed = np.array([[int(E[y][x]) for x in range(W)] for y in range(H)], dtype=np.int16)
    for (y, x) in piece4:
        fixed[y, x] = 9
    for (y, x, c) in tmpl:
        fixed[y, x] = 9
    bcenters = set((y, x) for (y, x) in bshape if x % 3 == 1 and y % 3 == 1)
    emin_y = min(y for y, x in piece4) if piece4 else 0
    emin_x = min(x for y, x in piece4) if piece4 else 0
    A = dict(H=H, W=W, piece4=piece4, tmpl=tmpl, fixed=fixed, bcenters=bcenters,
             emin_y=emin_y, emin_x=emin_x)
    _LAST[0] = E
    _LAST[1] = A
    return A


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    A = _entry_analysis(ENTRY_GRID)  # noqa: F821 (preloaded global)
    H, W = A["H"], A["W"]
    arr = np.asarray(grid, dtype=np.int16)
    ys, xs = np.where(arr == 4)
    if len(xs) == 0:
        return arr.copy(), info  # no movable piece found; no-op
    oy = int(ys.min()) - A["emin_y"]
    ox = int(xs.min()) - A["emin_x"]
    moves = int((arr[:, W - 1] == 5).sum())

    if action in (1, 2, 3, 4):
        if action == 1:
            oy -= 3
        elif action == 2:
            oy += 3
        elif action == 3:
            ox += 3
        elif action == 4:
            ox -= 3
        moves += 1
    # else (5/6/7): no-op -> render current offsets/moves unchanged

    out = A["fixed"].copy()
    if moves > 0:
        out[:min(moves, H), W - 1] = 5
    for (ty, tx, c) in A["tmpl"]:
        ny, nx = ty + oy, tx - ox
        if 0 <= ny < H and 0 <= nx < W:
            out[ny, nx] = c
    bc = A["bcenters"]
    for (py, px) in A["piece4"]:
        ny, nx = py + oy, px + ox
        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in bc:
            out[ny, nx] = 4
    return out, info
