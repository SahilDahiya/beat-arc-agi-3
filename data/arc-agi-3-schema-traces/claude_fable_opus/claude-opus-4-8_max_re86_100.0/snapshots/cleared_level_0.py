"""World model — game re86.   STATELESS step(): everything is re-derived from the frame.

CONFIRMED (level 0, 18 transitions):
  * Objects = plus/cross shapes, 4 arms of FIXED length (cross 9: arms 13, cross b: arms 11).
  * 3x3 boxes (border 4, centre = a cross colour), 4 per colour, STATIC scenery.
  * The black pixel (0) marks the centre of the SELECTED cross.
  * ACTION 1/2/3/4 = move selected cross UP/DOWN/LEFT/RIGHT by 3 (whole cross translates).
      confirmed: 1=up, 4=right, 3=left.   ACTION5 = switch selected cross.
  * Arms are CLIPPED at the grid edge (b-cross up-arm ran off the top; the move was allowed).
  * RENDER: bg -> boxes -> crosses ON TOP (arms overwrite box borders), SELECTED cross drawn last
    (it overwrites the other cross) -> the 0 mark -> row-63 bar.
  * BAR (row 63) = k cells of colour 1, right-aligned:  k = round(64 * n / 100)   [= (64n+50)//100]
    i.e. a BUDGET BAR: 100 actions per level rendered on a 64-cell strip.  Every action counts the
    same (a switch is NOT special).  Fits all 18 transitions exactly; B=100 is the unique budget.
    ** => the level's action budget is ~100.  Watch it. **

GOAL: per colour, the 2 boxes sharing an x give target cx, the 2 sharing a y give target cy;
translate each cross so its centre = (cx,cy) — its 4 arms then cover its 4 boxes.
    level0: target(9)=(48,24) [reached], target(b)=(15,9)
"""
import numpy as np
from collections import Counter

BG = 5
BORDER = 4
BAR_ROW = 63
BAR_EMPTY = 15
BAR_FILL = 1
MARK = 0
STEP = 3
BUDGET = 100

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}   # dx,dy
_LAYOUT_CACHE = {}


def _bar_of(n):
    """bar cells after n actions = round(64*n/BUDGET)"""
    return (64 * n + BUDGET // 2) // BUDGET


# ---------------------------------------------------------------- static layout (ENTRY_GRID)
def _layout(entry):
    eg = np.asarray(entry)
    key = eg.astype(np.int8).tobytes()
    hit = _LAYOUT_CACHE.get(key)
    if hit is not None:
        return hit
    H, W = eg.shape
    boxes = []
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            c = int(eg[y, x])
            if c in (BG, BORDER, BAR_EMPTY):
                continue
            if all(int(eg[y + dy, x + dx]) == BORDER
                   for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)):
                boxes.append((x, y, c))
    boxcells = set()
    for (x, y, c) in boxes:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                boxcells.add((x + dx, y + dy))
    mark = None
    for y in range(H - 1):
        for x in range(W):
            if int(eg[y, x]) == MARK:
                mark = (x, y)
    arms, ecent = {}, {}
    for col in sorted(set(int(v) for v in np.unique(eg[:H - 1]))):
        if col in (BG, BORDER, BAR_EMPTY, MARK):
            continue
        pts = [(int(px), int(py)) for py, px in zip(*np.where(eg[:H - 1] == col))
               if (int(px), int(py)) not in boxcells]
        if len(pts) < 5:
            continue
        cx = Counter(p[0] for p in pts).most_common(1)[0][0]
        cy = Counter(p[1] for p in pts).most_common(1)[0][0]
        if mark is not None and abs(mark[0] - cx) + abs(mark[1] - cy) <= 1:
            cx, cy = mark
        col_ys = sorted(p[1] for p in pts if p[0] == cx)
        row_xs = sorted(p[0] for p in pts if p[1] == cy)
        arms[col] = (cy - col_ys[0], col_ys[-1] - cy, cx - row_xs[0], row_xs[-1] - cx)
        ecent[col] = (cx, cy)
    esel = None
    for col, c in ecent.items():
        if mark is not None and c == mark:
            esel = col
    targets = {}
    for col in arms:
        bs = [(x, y) for (x, y, c) in boxes if c == col]
        xs, ys = Counter(b[0] for b in bs), Counter(b[1] for b in bs)
        tx = [v for v, n in xs.items() if n >= 2]
        ty = [v for v, n in ys.items() if n >= 2]
        if tx and ty:
            targets[col] = (tx[0], ty[0])
    val = {'boxes': boxes, 'boxcells': boxcells, 'arms': arms, 'targets': targets,
           'ecent': ecent, 'esel': esel, 'H': H, 'W': W, 'cols': sorted(arms)}
    _LAYOUT_CACHE[key] = val
    return val


# ---------------------------------------------------------------- dynamic read (current frame)
def _read(g, lay):
    H, W = lay['H'], lay['W']
    body = g[:H - 1]
    mark = None
    my, mx = np.where(body == MARK)
    if len(mx):
        mark = (int(mx[0]), int(my[0]))
    centres = {}
    for col in lay['cols']:
        ys, xs = np.where(body == col)
        if len(xs) == 0:
            continue
        centres[col] = (int(np.bincount(xs).argmax()), int(np.bincount(ys).argmax()))
    sel = None
    if mark is not None and centres:
        sel = min(centres, key=lambda c: abs(centres[c][0] - mark[0]) + abs(centres[c][1] - mark[1]))
        centres[sel] = mark
    return centres, sel


def _nactions(g, lay, centres, sel):
    """n from the frame: the bar pins n to <=2 consecutive values; parity(n) = parity(#moves)
    ^ parity(#switches), where #moves parity = parity(total displacement/3) and (2 crosses)
    #switches parity = 1 iff the selection differs from the entry selection."""
    k = int(np.count_nonzero(np.asarray(g[BAR_ROW]) != BAR_EMPTY))
    disp = sum(abs(centres[c][0] - lay['ecent'][c][0]) + abs(centres[c][1] - lay['ecent'][c][1])
               for c in centres if c in lay['ecent'])
    par = (disp // STEP) % 2
    if len(lay['cols']) == 2 and sel is not None and lay['esel'] is not None and sel != lay['esel']:
        par ^= 1
    cands = [n for n in range(0, 4 * BUDGET) if _bar_of(n) == k]
    for n in cands:
        if n % 2 == par:
            return n
    return cands[0] if cands else 0


# ---------------------------------------------------------------- rendering
def _render(centres, sel, lay, ncells):
    H, W = lay['H'], lay['W']
    g = np.full((H, W), BG, dtype=int)
    for (x, y, c) in lay['boxes']:                          # boxes ...
        g[y - 1:y + 2, x - 1:x + 2] = BORDER
        g[y, x] = c
    order = [c for c in centres if c != sel] + ([sel] if sel in centres else [])
    for col in order:                                       # ... crosses on top, selected last
        cx, cy = centres[col]
        up, dn, lf, rt = lay['arms'][col]
        if 0 <= cx < W:
            y0, y1 = max(0, cy - up), min(H - 2, cy + dn)
            if y0 <= y1:
                g[y0:y1 + 1, cx] = col
        if 0 <= cy < H - 1:
            x0, x1 = max(0, cx - lf), min(W - 1, cx + rt)
            if x0 <= x1:
                g[cy, x0:x1 + 1] = col
    if sel is not None and sel in centres:
        cx, cy = centres[sel]
        if 0 <= cx < W and 0 <= cy < H - 1:
            g[cy, cx] = MARK
    g[BAR_ROW, :] = BAR_EMPTY
    if ncells > 0:
        g[BAR_ROW, max(0, W - ncells):] = BAR_FILL
    return g


def _aligned(centres, lay):
    t = lay['targets']
    if not t or len(t) < len(lay['cols']):
        return False
    return all(col in centres and tuple(centres[col]) == tuple(t[col]) for col in lay['cols'])


# ---------------------------------------------------------------- transition
def step(grid, action, x=None, y=None):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    centres, sel = _read(g, lay)
    n = _nactions(g, lay, centres, sel)

    if action in DIRS and sel is not None:
        dx, dy = DIRS[action]
        cx, cy = centres[sel]
        centres[sel] = (cx + dx * STEP, cy + dy * STEP)
    elif action == 5:
        cols = lay['cols']
        if cols:
            i = cols.index(sel) if sel in cols else -1
            sel = cols[(i + 1) % len(cols)]

    ng = _render(centres, sel, lay, _bar_of(n + 1))
    info = {'level_up': _aligned(centres, lay), 'dead': False, 'win': False}
    return ng.tolist(), info


def is_goal(grid):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    centres, _ = _read(g, lay)
    return _aligned(centres, lay)
