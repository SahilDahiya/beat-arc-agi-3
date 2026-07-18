"""World model — game re86.  GENERIC rigid-shape version (explains levels 0 and 1).

MECHANICS (confirmed):
  * The board holds several RIGID SHAPES, one per colour.  Seen so far: PLUS (4 arms), X (4
    diagonal arms), DIAMOND outline.  A shape never rotates/scales — it only TRANSLATES.
  * 3x3 boxes (border 4, centre = a shape colour) are STATIC scenery.
  * The black pixel (0) marks the CENTRE of the SELECTED shape.
  * ACTION 1/2/3/4 = move the selected shape UP/DOWN/LEFT/RIGHT by 3 cells.  ACTION5 = switch
    the selected shape (cycles).
  * Shapes are CLIPPED at the grid edge (the move is still allowed).
  * RENDER: bg -> boxes -> shapes (non-selected first, SELECTED drawn last, so it overwrites the
    others) -> the 0 mark at the selected centre -> row-63 bar.
  * BAR = k right-aligned cells of colour 1, k = round(64*n/100): a 100-ACTION BUDGET per level
    drawn on a 64-cell strip.  Every action counts once.

GOAL: translate every shape so that its cells COVER ALL the box-centres of its own colour.
  (level 0: plus 9 -> (48,24), plus b -> (15,9).  level 1: plus 9 -> (27,48), X c -> (18,48),
   diamond d -> (21,12) or (18,9) — 3 boxes leave the diamond ambiguous; both cover all boxes.)
"""
import numpy as np
from collections import Counter

BG, BORDER, MARK = 5, 4, 0
BAR_ROW, BAR_EMPTY, BAR_FILL = 63, 15, 1
STEP, BUDGET = 3, 100
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
_CACHE = {}


def _bar_of(n):
    return (64 * n + BUDGET // 2) // BUDGET


def _centre_of(cells):
    """centre of a centrally-symmetric shape, from its long lines (cols/rows/diagonals)."""
    THR = 5
    xs = Counter(p[0] for p in cells); ys = Counter(p[1] for p in cells)
    ss = Counter(p[0] + p[1] for p in cells); ds = Counter(p[0] - p[1] for p in cells)
    L = lambda C: sorted(v for v, c in C.items() if c >= THR)
    lx, ly, ls, ld = L(xs), L(ys), L(ss), L(ds)
    if lx and ly:
        return ((lx[0] + lx[-1]) // 2, (ly[0] + ly[-1]) // 2)
    if ls and ld:
        s = (ls[0] + ls[-1]) // 2
        d = (ld[0] + ld[-1]) // 2
        return ((s + d) // 2, (s - d) // 2)
    if not cells:
        return (0, 0)
    return (int(round(sum(p[0] for p in cells) / len(cells))),
            int(round(sum(p[1] for p in cells) / len(cells))))


# ---------------------------------------------------------------- static layout (ENTRY_GRID)
def _layout(entry):
    eg = np.asarray(entry)
    key = eg.astype(np.int8).tobytes()
    hit = _CACHE.get(key)
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
    bcent = {(x, y) for x, y, _ in boxes}
    mark = None
    for y in range(H - 1):
        for x in range(W):
            if int(eg[y, x]) == MARK:
                mark = (x, y)
    shapes = {}
    for col in sorted(set(int(v) for v in np.unique(eg[:H - 1]))):
        if col in (BG, BORDER, BAR_EMPTY, MARK):
            continue
        pts = {(int(px), int(py)) for py, px in zip(*np.where(eg[:H - 1] == col))
               if (int(px), int(py)) not in bcent}
        if len(pts) < 5:
            continue
        c = _centre_of(pts)
        if mark is not None and abs(mark[0] - c[0]) + abs(mark[1] - c[1]) <= 1:
            c = mark
        full = pts | {(2 * c[0] - x, 2 * c[1] - y) for x, y in pts}   # complete occluded cells
        # Is the CENTRE itself a shape cell?  A plus's centre is filled; an X's and a diamond's
        # are a hole.  If the shape is not the entry-selected one, just read the entry frame;
        # otherwise (its centre is hidden under the 0 mark) fall back to: filled iff the shape
        # continues ORTHOGONALLY through the centre (true for a plus, false for an X/diamond).
        filled = None
        if not (mark is not None and c == mark):
            v = int(eg[c[1], c[0]])
            if v == col:
                filled = True
            elif v in (BG, BORDER):
                filled = False
        if filled is None:
            filled = (((c[0] - 1, c[1]) in full and (c[0] + 1, c[1]) in full) or
                      ((c[0], c[1] - 1) in full and (c[0], c[1] + 1) in full))
        if filled:
            full.add(c)
        shapes[col] = {'c0': c, 'off': frozenset((x - c[0], y - c[1]) for x, y in full)}
    esel = None
    for col, sh in shapes.items():
        if mark is not None and sh['c0'] == mark:
            esel = col
    targets = {}
    for col, sh in shapes.items():
        bs = [(x, y) for (x, y, c) in boxes if c == col]
        cx0, cy0 = sh['c0']
        good = [(cx0 + STEP * i, cy0 + STEP * j)
                for i in range(-21, 22) for j in range(-21, 22)
                if bs and all((bx - cx0 - STEP * i, by - cy0 - STEP * j) in sh['off'] for bx, by in bs)]
        targets[col] = set(good)
    # z-order: shapes are drawn in a FIXED order (later = on top), independent of selection.
    # level0: b(21,27) under 9(36,45); level1: c(27,18) under d(39,30) under 9(48,42)
    # => ascending by ENTRY centre (y, x).  ("selected on top" fitted L0 only by coincidence.)
    zorder = sorted(shapes, key=lambda c: (shapes[c]['c0'][1], shapes[c]['c0'][0]))
    val = {'boxes': boxes, 'bcent': bcent, 'shapes': shapes, 'targets': targets,
           'esel': esel, 'H': H, 'W': W, 'cols': sorted(shapes), 'z': zorder}
    _CACHE[key] = val
    return val


# ---------------------------------------------------------------- read the live frame
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
        pts = [(int(a), int(b)) for a, b in zip(xs, ys) if (int(a), int(b)) not in lay['bcent']]
        if not pts:
            continue
        centres[col] = _centre_of(pts)
    sel = None
    if mark is not None and centres:
        sel = min(centres, key=lambda c: abs(centres[c][0] - mark[0]) + abs(centres[c][1] - mark[1]))
        centres[sel] = mark
    return centres, sel


# ---------------------------------------------------------------- render / goal
def _render(centres, sel, lay, ncells):
    H, W = lay['H'], lay['W']
    g = np.full((H, W), BG, dtype=int)
    for (x, y, c) in lay['boxes']:
        g[y - 1:y + 2, x - 1:x + 2] = BORDER
        g[y, x] = c
    for col in [c for c in lay['z'] if c in centres]:
        cx, cy = centres[col]
        for (ox, oy) in lay['shapes'][col]['off']:
            x, y = cx + ox, cy + oy
            if 0 <= x < W and 0 <= y < H - 1:
                g[y, x] = col
    if sel is not None and sel in centres:
        cx, cy = centres[sel]
        if 0 <= cx < W and 0 <= cy < H - 1:
            g[cy, cx] = MARK
    g[BAR_ROW, :] = BAR_EMPTY
    if ncells > 0:
        g[BAR_ROW, max(0, W - ncells):] = BAR_FILL
    return g


def _aligned(centres, lay):
    for col in lay['cols']:
        if col not in centres or not lay['targets'].get(col):
            return False
        if tuple(centres[col]) not in lay['targets'][col]:
            return False
    return True


# ---------------------------------------------------------------- transition
def init_state(entry_grid):
    return {'n': 0}


def predict(state, grid, action, x=None, y=None):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    centres, sel = _read(g, lay)
    # action count: trust the threaded state when it matches the bar, else resync from the frame
    k = int(np.count_nonzero(g[BAR_ROW] != BAR_EMPTY))
    n = int(state.get('n', 0)) if isinstance(state, dict) else 0
    if _bar_of(n) != k:
        for v in range(0, 4 * BUDGET):
            if _bar_of(v) == k:
                n = v
                break

    if action in DIRS and sel is not None:
        dx, dy = DIRS[action]
        cx, cy = centres[sel]
        centres[sel] = (cx + dx * STEP, cy + dy * STEP)
    elif action == 5:
        cols = lay['cols']
        if cols:
            i = cols.index(sel) if sel in cols else -1
            sel = cols[(i + 1) % len(cols)]
    n += 1

    ng = _render(centres, sel, lay, _bar_of(n))
    info = {'level_up': _aligned(centres, lay), 'dead': False, 'win': False}
    return ng.tolist(), info, {'n': n}


def is_goal(grid):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    centres, _ = _read(g, lay)
    return _aligned(centres, lay)
