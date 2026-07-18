import numpy as np
from collections import deque

# ================= GAME MODEL =================
# A level is a set of rigid PIECES on a 20x20 block lattice (each block = 3x3 cells, offset (2,2)).
# Every piece has a body colour and some CONNECTORS (colour 8).
#  * Exactly ONE piece is SELECTED.  The selected piece's body renders as colour 0 (the
#    selection highlight) instead of its true colour.  CONFIRMED: clicking obj11 turned it 0
#    and turned the previously-selected piece back to its true colour 15.
#  * ACTION 6 (click) selects the piece under the clicked block.  Costs a move.
#  * ACTIONS 1-4 translate the SELECTED piece 1 block; ACTION 5 rotates it 90 deg CW,
#    anchored at its bounding-box TOP-LEFT.
#  * A move is blocked unless every overlap with another piece is CONNECTOR-on-CONNECTOR.
#    Two coincident connectors render as colour 3 ("bonded"). Bonds are NOT persistent —
#    move apart and they revert to 8.
#  * GOAL: every connector coincident at once  <=>  ZERO colour-8 cells remain.

S, OX, OY = 3, 2, 2
NBX = (64 - OX) // S     # 20
NBY = (64 - OY) // S     # 20

SEL_COLOR  = 0           # body colour of the SELECTED piece (highlight)
MARK_COLOR = 8           # unbonded connector
DOCK_COLOR = 3           # two connectors coincide
HIDDEN_TRUE = 15         # true colour of the initially-selected piece (hidden by the highlight
                         # in ENTRY_GRID; revealed as 15 when we clicked away from it)

BODY, MARK = 1, 2

HUD_Y, HUD_X0, HUD_N = 0, 16, 32
HUD_FULL, HUD_USED = 4, 0

DELTA = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
ROT, CLICK = 5, 6


def _hud_used(m, B):
    return min((64 * m + B) // (2 * B), HUD_N)


def _budget_guess():
    try:
        lv = CURRENT_LEVEL
    except NameError:
        lv = 0
    return 75 + 25 * int(lv or 0)


def _hud_read(g):
    return int(np.sum(g[HUD_Y, HUD_X0:HUD_X0 + HUD_N] != HUD_FULL))


def _narrow(lo, hi, m, u):
    if m <= 0:
        return lo, hi
    lo = max(lo, 64 * m // (2 * u + 1) + 1)
    if u >= 1:
        hi = min(hi, 64 * m // (2 * u - 1))
    return lo, hi


def _blocks(grid):
    g = np.array(grid, dtype=int)
    return g, g[OY:OY + NBY * S:S, OX:OX + NBX * S:S].copy()


def _bg_of(B):
    v, c = np.unique(B, return_counts=True)
    return int(v[np.argmax(c)])


def _components(B, bg):
    seen = np.zeros(B.shape, dtype=bool)
    out = []
    for y in range(NBY):
        for x in range(NBX):
            if B[y, x] != bg and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                cells = []
                while q:
                    cy, cx = q.popleft()
                    cells.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < NBY and 0 <= nx < NBX and B[ny, nx] != bg and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                out.append(cells)
    return out


_CACHE = {}


def _entry_info():
    try:
        eg = ENTRY_GRID
    except NameError:
        return None
    if eg is None:
        return None
    g = np.asarray(eg, dtype=int)
    ck = g.tobytes()
    if ck in _CACHE:
        return _CACHE[ck]

    _, B = _blocks(g)
    bg = _bg_of(B)
    pieces, sel0 = [], 0
    comps = sorted(_components(B, bg), key=lambda c: min(c))
    for idx, comp in enumerate(comps):
        cols = {int(B[y, x]) for (y, x) in comp} - {MARK_COLOR, DOCK_COLOR}
        col = cols.pop() if cols else HIDDEN_TRUE
        if col == SEL_COLOR:                      # rendered as the highlight at entry
            sel0 = idx
            col = HIDDEN_TRUE                     # its real colour is hidden; it is 15
        ys = [y for y, _ in comp]
        xs = [x for _, x in comp]
        y0, x0 = min(ys), min(xs)
        pat = np.zeros((max(ys) - y0 + 1, max(xs) - x0 + 1), dtype=int)
        for (y, x) in comp:
            pat[y - y0, x - x0] = MARK if B[y, x] == MARK_COLOR else BODY
        pieces.append({"col": col, "oris": [np.rot90(pat, k=-k) for k in range(4)]})

    info = {"bg": bg, "pieces": pieces, "sel0": sel0}
    _CACHE[ck] = info
    return info


def _cells_of(p_ori, r0, c0):
    return {(r0 + i, c0 + j): int(p_ori[i, j])
            for i in range(p_ori.shape[0]) for j in range(p_ori.shape[1]) if p_ori[i, j]}


def _find_piece(B, info, i, selected):
    """Locate piece i by its BODY cells (connectors are shared/ambiguous, bodies never are)."""
    col = SEL_COLOR if selected else info["pieces"][i]["col"]
    obs = [(y, x) for y in range(NBY) for x in range(NBX) if B[y, x] == col]
    if not obs:
        return None
    oy = min(y for y, _ in obs)
    ox = min(x for _, x in obs)
    norm = frozenset((y - oy, x - ox) for (y, x) in obs)
    for k, p in enumerate(info["pieces"][i]["oris"]):
        z = [(a, b) for a in range(p.shape[0]) for b in range(p.shape[1]) if p[a, b] == BODY]
        zy = min(a for a, _ in z)
        zx = min(b for _, b in z)
        if len(z) == len(obs) and frozenset((a - zy, b - zx) for (a, b) in z) == norm:
            return {"k": k, "r0": oy - zy, "c0": ox - zx,
                    "cells": _cells_of(p, oy - zy, ox - zx)}
    return None


def _canvas(info, poses, sel):
    bg = info["bg"]
    cv = np.full((NBY, NBX), bg, dtype=int)
    marks = {}
    for i, p in enumerate(poses):
        for c, kind in p["cells"].items():
            if kind == BODY:
                cv[c] = SEL_COLOR if i == sel else info["pieces"][i]["col"]
            else:
                marks[c] = marks.get(c, 0) + 1
    for c, n in marks.items():
        cv[c] = DOCK_COLOR if n >= 2 else MARK_COLOR
    return cv


def _render(g, cv, m, B):
    out = g.copy()
    out[OY:OY + NBY * S, OX:OX + NBX * S] = np.kron(cv, np.ones((S, S), dtype=int))
    used = _hud_used(m, B)
    for i in range(HUD_N):
        out[HUD_Y, HUD_X0 + i] = HUD_USED if i < used else HUD_FULL
    return out


def init_state(entry_grid):
    info = _entry_info()
    return {"m": 0, "lo": 1, "hi": 10 ** 9, "sel": info["sel0"] if info else 0}


def _recover_moves(state, g):
    m = int(state.get("m", 0))
    if m == 0:
        try:
            eg = ENTRY_GRID
        except NameError:
            eg = None
        if eg is not None and not np.array_equal(g, np.asarray(eg, dtype=int)):
            m = 1
    return m


def predict(state, grid, action, x=None, y=None):
    g, B = _blocks(grid)
    info = _entry_info()
    m = _recover_moves(state, g)
    nm = m + 1
    lo, hi = _narrow(int(state.get("lo", 1)), int(state.get("hi", 10 ** 9)), m, _hud_read(g))
    sel = int(state.get("sel", info["sel0"] if info else 0))
    flags = {"level_up": False, "dead": False, "win": False}
    ns = {"m": nm, "lo": lo, "hi": hi, "sel": sel}
    if info is None:
        return g.tolist(), flags, ns

    bud = min(max(_budget_guess(), lo), hi)
    n = len(info["pieces"])
    poses = [_find_piece(B, info, i, i == sel) for i in range(n)]
    if any(p is None for p in poses):
        return g.tolist(), flags, ns

    if action == CLICK and x is not None and y is not None:
        by, bx = (int(y) - OY) // S, (int(x) - OX) // S
        hit = None
        for i, p in enumerate(poses):                    # prefer a body cell
            if p["cells"].get((by, bx)) == BODY:
                hit = i
                break
        if hit is None:
            for i, p in enumerate(poses):
                if (by, bx) in p["cells"]:
                    hit = i
                    break
        if hit is not None:
            sel = hit
    elif action in DELTA or action == ROT:
        cur = poses[sel]["cells"]
        if action in DELTA:
            dy, dx = DELTA[action]
            cand = {(a + dy, b + dx): k for (a, b), k in cur.items()}
        else:
            p = info["pieces"][sel]["oris"][(poses[sel]["k"] + 1) % 4]
            cand = _cells_of(p, poses[sel]["r0"], poses[sel]["c0"])   # bbox TOP-LEFT anchored
        others = {}
        for i, p in enumerate(poses):
            if i != sel:
                for c, k in p["cells"].items():
                    others[c] = max(others.get(c, 0), k)
        ok = True
        for c, k in cand.items():
            if not (0 <= c[0] < NBY and 0 <= c[1] < NBX):
                ok = False
                break
            if c in others and not (k == MARK and others[c] == MARK):
                ok = False                                # only connector-on-connector allowed
                break
        if ok:
            nk = poses[sel]["k"] if action in DELTA else (poses[sel]["k"] + 1) % 4
            r0, c0 = min(c[0] for c in cand), min(c[1] for c in cand)
            poses[sel] = {"k": nk, "r0": poses[sel]["r0"], "c0": poses[sel]["c0"], "cells": cand}
            if action in DELTA:
                poses[sel]["r0"] += DELTA[action][0]
                poses[sel]["c0"] += DELTA[action][1]

    ns["sel"] = sel
    cv = _canvas(info, poses, sel)
    if not np.any(cv == MARK_COLOR):
        flags["level_up"] = True
    return _render(g, cv, nm, bud).tolist(), flags, ns


def is_goal(state, grid):
    _, B = _blocks(grid)
    return not np.any(B == MARK_COLOR)
