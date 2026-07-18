"""World model — game re86.  Multi-OBJECT version (levels 0,1,2).

MECHANICS (confirmed):
  * The board holds N rigid OBJECTS.  An object is a symmetric primitive: PLUS (4 orthogonal
    arms), X (4 diagonal arms), DIAMOND (hollow rhombus ring), HLINE / VLINE (2 arms).
    SEVERAL OBJECTS MAY SHARE ONE COLOUR (level 2: line + X + diamond, all colour 8).
  * Objects only TRANSLATE, 3 cells per action, and are clipped at the grid edge.  They never
    block one another; they simply overdraw in a fixed z-order (ascending entry centre (y,x)).
  * 3x3 boxes (border 4, centre = a colour) are static scenery.
  * The black pixel (0) marks the SELECTED object's centre.  ACTION5 cycles the selection in
    entry-centre (y,x) order.  1/2/3/4 = up/down/left/right.
  * An object's CENTRE cell may or may not belong to it (plus: yes; L1 X: no; diamond: no) —
    read it from the entry frame, or (if the mark hides it) require ORTHOGONAL continuity.
  * BAR = round(64*n/100) cells => 100-action budget per level.

GOAL: every box must be COVERED by some object OF THE BOX'S COLOUR.
"""
import numpy as np

BG, BORDER, MARK = 5, 4, 0
BAR_ROW, BAR_EMPTY, BAR_FILL = 63, 15, 1
STEP, BUDGET = 3, 100
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
_CACHE = {}


def _bar_of(n):
    return (64 * n + BUDGET // 2) // BUDGET


# ---------------------------------------------------------------- primitives (centre excluded)
def _plus(c, r):
    x, y = c
    return {(x + k, y) for k in range(-r, r + 1) if k} | {(x, y + k) for k in range(-r, r + 1) if k}


def _xshape(c, r):
    x, y = c
    s = set()
    for k in range(1, r + 1):
        s |= {(x + k, y + k), (x - k, y - k), (x + k, y - k), (x - k, y + k)}
    return s


def _ring(c, r):
    x, y = c
    s = set()
    for k in range(0, r + 1):
        s |= {(x + k, y - (r - k)), (x + k, y + (r - k)), (x - k, y - (r - k)), (x - k, y + (r - k))}
    return s


def _hline(c, r):
    x, y = c
    return {(x + k, y) for k in range(-r, r + 1) if k}


def _vline(c, r):
    x, y = c
    return {(x, y + k) for k in range(-r, r + 1) if k}


def _grow(c, avail, gen, maxr):
    """largest r with gen(c,r) subset of avail (arms grow outward)"""
    best = 0
    for r in range(1, maxr + 1):
        if gen(c, r) <= avail:
            best = r
        else:
            break
    return best


def _decompose(cells, avail, maxr=26):
    """greedy exact cover of `cells` by maximal primitives (may use `avail` cells too)."""
    if not cells:
        return []
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    cands = []
    for cx in range(min(xs), max(xs) + 1):
        for cy in range(min(ys), max(ys) + 1):
            c = (cx, cy)
            r = _grow(c, avail, _plus, maxr)
            if r >= 3:
                cands.append(_plus(c, r) | {c} if False else (c, 'plus', r, _plus(c, r)))
            r = _grow(c, avail, _xshape, maxr)
            if r >= 3:
                cands.append((c, 'x', r, _xshape(c, r)))
            r = _grow(c, avail, _hline, maxr)
            if r >= 5:
                cands.append((c, 'h', r, _hline(c, r)))
            r = _grow(c, avail, _vline, maxr)
            if r >= 5:
                cands.append((c, 'v', r, _vline(c, r)))
            for r in range(3, maxr):          # diamond ring: cheap vertex pre-check
                if ((cx + r, cy) in avail and (cx - r, cy) in avail
                        and (cx, cy + r) in avail and (cx, cy - r) in avail):
                    ring = _ring(c, r)
                    if ring <= avail:
                        cands.append((c, 'd', r, ring))
    # a primitive also covers its own CENTRE when that cell belongs to the colour (plus-like)
    cov = []
    for (c, kind, r, pc) in cands:
        cc = set(pc)
        if c in cells:
            cc.add(c)
        cov.append((c, kind, r, pc, frozenset(cc)))
    chosen = []
    left = set(cells)
    while left:
        best = None
        for cand in cov:
            new = len(cand[4] & left)
            if new and (best is None or new > best[0]
                        or (new == best[0] and len(cand[4]) > len(best[1][4]))):
                best = (new, cand)
        if best is None:
            break
        chosen.append(best[1][:4])
        left -= best[1][4]
    return chosen


# ---------------------------------------------------------------- layout from ENTRY_GRID
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
    # cells a primitive may pass through (anything not background / box border)
    avail = {(x, y) for y in range(H - 1) for x in range(W)
             if int(eg[y, x]) not in (BG, BORDER, BAR_EMPTY)}
    objs = []
    for col in sorted(set(int(v) for v in np.unique(eg[:H - 1]))):
        if col in (BG, BORDER, BAR_EMPTY, MARK):
            continue
        cells = {(x, y) for y in range(H - 1) for x in range(W)
                 if int(eg[y, x]) == col and (x, y) not in bcent}
        if len(cells) < 8:
            continue
        for (c, kind, r, pc) in _decompose(cells, avail):
            full = set(pc)
            v = int(eg[c[1], c[0]])
            if mark is not None and c == mark:            # centre hidden by the mark
                filled = (((c[0] - 1, c[1]) in full and (c[0] + 1, c[1]) in full) or
                          ((c[0], c[1] - 1) in full and (c[0], c[1] + 1) in full))
            else:
                filled = (v == col)
            if filled:
                full.add(c)
            objs.append({'col': col, 'c0': c, 'kind': kind,
                         'off': frozenset((x - c[0], y - c[1]) for x, y in full)})
    objs.sort(key=lambda o: (o['c0'][1], o['c0'][0]))     # z-order AND switch order
    esel = 0
    for i, o in enumerate(objs):
        if mark is not None and o['c0'] == mark:
            esel = i
    val = {'boxes': boxes, 'bcent': bcent, 'objs': objs, 'esel': esel, 'H': H, 'W': W}
    _CACHE[key] = val
    return val


# ---------------------------------------------------------------- read / render / goal
def _locate(g, lay):
    """positions of every object + the selected index, straight from a frame (fallback path)."""
    H, W = lay['H'], lay['W']
    pos, sel = [], 0
    mark = None
    my, mx = np.where(g[:H - 1] == MARK)
    if len(mx):
        mark = (int(mx[0]), int(my[0]))
    for i, o in enumerate(lay['objs']):
        best, bestsc = o['c0'], -1
        for a in range(-21, 22):
            for b in range(-21, 22):
                c = (o['c0'][0] + STEP * a, o['c0'][1] + STEP * b)
                sc = 0
                for (ox, oy) in o['off']:
                    x, y = c[0] + ox, c[1] + oy
                    if 0 <= x < W and 0 <= y < H - 1 and int(g[y, x]) == o['col']:
                        sc += 1
                if mark is not None and c == mark:
                    sc += 2
                if sc > bestsc:
                    best, bestsc = c, sc
        pos.append(best)
    if mark is not None:
        for i, c in enumerate(pos):
            if c == mark:
                sel = i
    return pos, sel


def _render(pos, sel, lay, ncells):
    H, W = lay['H'], lay['W']
    g = np.full((H, W), BG, dtype=int)
    for (x, y, c) in lay['boxes']:
        g[y - 1:y + 2, x - 1:x + 2] = BORDER
        g[y, x] = c
    for i, o in enumerate(lay['objs']):
        cx, cy = pos[i]
        for (ox, oy) in o['off']:
            x, y = cx + ox, cy + oy
            if 0 <= x < W and 0 <= y < H - 1:
                g[y, x] = o['col']
    cx, cy = pos[sel]
    if 0 <= cx < W and 0 <= cy < H - 1:
        g[cy, cx] = MARK
    g[BAR_ROW, :] = BAR_EMPTY
    if ncells > 0:
        g[BAR_ROW, max(0, W - ncells):] = BAR_FILL
    return g


def _aligned(pos, lay):
    for (bx, by, bc) in lay['boxes']:
        ok = False
        for i, o in enumerate(lay['objs']):
            if o['col'] == bc and (bx - pos[i][0], by - pos[i][1]) in o['off']:
                ok = True
                break
        if not ok:
            return False
    return True


# ---------------------------------------------------------------- transition
def init_state(entry_grid):
    eg = entry_grid if entry_grid is not None else ENTRY_GRID
    if eg is None:
        return {'n': 0, 'pos': None, 'sel': 0}
    lay = _layout(eg)
    return {'n': 0, 'pos': [o['c0'] for o in lay['objs']], 'sel': lay['esel']}


def predict(state, grid, action, x=None, y=None):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    H, W = lay['H'], lay['W']
    st = state if isinstance(state, dict) else {}
    pos = list(st.get('pos') or [])
    sel = int(st.get('sel', lay['esel']))
    n = int(st.get('n', 0))

    # resync with the frame when the tracked state does not match it
    mark = None
    my, mx = np.where(g[:H - 1] == MARK)
    if len(mx):
        mark = (int(mx[0]), int(my[0]))
    if (len(pos) != len(lay['objs']) or mark is None or sel >= len(pos)
            or tuple(pos[sel]) != mark):
        pos, sel = _locate(g, lay)
    k = int(np.count_nonzero(g[BAR_ROW] != BAR_EMPTY))
    if _bar_of(n) != k:
        for v in range(0, 4 * BUDGET):
            if _bar_of(v) == k:
                n = v
                break

    pos = [tuple(p) for p in pos]
    if action in DIRS:
        dx, dy = DIRS[action]
        pos[sel] = (pos[sel][0] + dx * STEP, pos[sel][1] + dy * STEP)
    elif action == 5:
        sel = (sel + 1) % len(lay['objs'])
    n += 1

    ng = _render(pos, sel, lay, _bar_of(n))
    info = {'level_up': _aligned(pos, lay), 'dead': False, 'win': False}
    return ng.tolist(), info, {'n': n, 'pos': pos, 'sel': sel}


def is_goal(grid):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    pos, _ = _locate(g, lay)
    return _aligned(pos, lay)
