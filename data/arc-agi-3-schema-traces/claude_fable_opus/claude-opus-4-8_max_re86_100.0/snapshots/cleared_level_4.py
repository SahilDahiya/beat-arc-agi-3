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
STEP = 3
# Action budget PER LEVEL (the bar shows round(64*n/BUDGET) filled cells).
# L0/L1 = 100 (verified exactly).  L2: n=1 -> 0 cells => BUDGET > 128; 200 is the working guess.
BUDGETS = {0: 100, 1: 100, 2: 200, 3: 200, 4: 250}
# L4: bar data (n=0..5 -> 0,0,1,1,1,1) pins the budget to [214,256]; 250 is the working guess.
# per-level draw order (indices into objs, sorted by entry (y,x)); first = bottom.
# L3: objs = [X(24,21), plus(54,36)]; the X is drawn ON TOP => [plus, X] = [1, 0]
ZORDER = {3: [1, 0], 4: [1, 2, 0]}   # L4: objs=[diamond,plus,X]; stack is plus < X < diamond
# true colour of boxes whose centre is HIDDEN by an object in the entry frame (per level)
BOXCOL = {4: {(57, 33): 8, (54, 42): 8}}   # centres hidden by the plus in the entry frame
# centre-fill of the ENTRY-SELECTED object (hidden under the mark at entry): {level: {objidx: True}}
CENTREFILL = {4: True}         # L4's entry-selected X has a FILLED centre (L1's X did not).
# NOTE: the entry-selected object's centre is hidden under the 0 mark, so whether it is a real
# cell CANNOT be read from the entry frame — it must be observed once the object is deselected.
DEFAULT_BUDGET = 200
# (recompile)
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
_CACHE = {}


def _budget(lev):
    try:
        return BUDGETS.get(int(lev), DEFAULT_BUDGET)
    except Exception:
        return DEFAULT_BUDGET


def _bar_of(n, lev=None):
    b = _budget(lev if lev is not None else CURRENT_LEVEL)
    return (64 * n + b // 2) // b
# (touched to force a recompile of the installed model)


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


def _ok(cells, avail, W, H):
    """every ON-GRID cell of the primitive must be available (off-grid cells are just clipped)"""
    for (x, y) in cells:
        if 0 <= x < W and 0 <= y < H - 1 and (x, y) not in avail:
            return False
    return True


def _grow(c, avail, gen, maxr, W=64, H=64):
    best = 0
    for r in range(1, maxr + 1):
        if _ok(gen(c, r), avail, W, H):
            best = r
        else:
            break
    return best


def _decompose(cells, avail, maxr=26, W=64, H=64):
    """greedy exact cover of `cells` by maximal primitives (may use `avail` cells too)."""
    if not cells:
        return []
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    cands = []
    for cx in range(min(xs), max(xs) + 1):
        for cy in range(min(ys), max(ys) + 1):
            c = (cx, cy)
            r = _grow(c, avail, _plus, maxr, W, H)
            if r >= 3:
                cands.append((c, 'plus', r, _plus(c, r)))
            r = _grow(c, avail, _xshape, maxr, W, H)
            if r >= 3:
                cands.append((c, 'x', r, _xshape(c, r)))
            r = _grow(c, avail, _hline, maxr, W, H)
            if r >= 5:
                cands.append((c, 'h', r, _hline(c, r)))
            r = _grow(c, avail, _vline, maxr, W, H)
            if r >= 5:
                cands.append((c, 'v', r, _vline(c, r)))
            for r in range(3, maxr):          # diamond ring
                ring = _ring(c, r)
                if _ok(ring, avail, W, H):
                    cands.append((c, 'd', r, ring))
    # a primitive also covers its own CENTRE when that cell belongs to the colour (plus-like)
    cov = []
    for (c, kind, r, pc) in cands:
        cc = {p for p in pc if 0 <= p[0] < W and 0 <= p[1] < H - 1}
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
    # BOXES: 3x3 with a BORDER(4) ring.  An object drawn over the box can hide part of the ring
    # AND its centre colour, so accept >=4 ring cells of BORDER as long as none of the ring is
    # background (the rest must be object colours).  A hidden centre is patched per level.
    boxes = []
    for y in range(1, H - 2):
        for x in range(1, W - 1):
            c = int(eg[y, x])
            if c in (BG, BORDER, BAR_EMPTY):
                continue
            nb = [int(eg[y + dy, x + dx]) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                  if (dy, dx) != (0, 0)]
            if nb.count(BORDER) >= 4 and all(v not in (BG, BAR_EMPTY) for v in nb):
                boxes.append((x, y, c))
    try:
        patch = BOXCOL.get(int(CURRENT_LEVEL), {})
    except Exception:
        patch = {}
    if patch:
        boxes = [(x, y, patch.get((x, y), c)) for (x, y, c) in boxes]
    bcent = {(x, y) for x, y, _ in boxes}
    # palettes: NxN block, uniform border ring, uniform interior of a different colour
    pals = []
    palcells = set()
    for y in range(H - 6):
        for x in range(W - 6):
            blk = eg[y:y + 6, x:x + 6]
            b = int(blk[0, 0])
            if b in (BG, BAR_EMPTY):
                continue
            ring_ok = (all(int(v) == b for v in blk[0, :]) and all(int(v) == b for v in blk[5, :])
                       and all(int(v) == b for v in blk[:, 0]) and all(int(v) == b for v in blk[:, 5]))
            if not ring_ok:
                continue
            inner = blk[1:5, 1:5]
            c0 = int(inner[0, 0])
            if c0 == b or c0 in (BG, BAR_EMPTY):
                continue
            if all(int(v) == c0 for v in inner.flatten()):
                pals.append({'x0': x + 1, 'x1': x + 4, 'y0': y + 1, 'y1': y + 4,
                             'col': c0, 'border': b, 'bx': x, 'by': y})
                for dy in range(6):
                    for dx in range(6):
                        palcells.add((x + dx, y + dy))
    mark = None
    for y in range(H - 1):
        for x in range(W):
            if int(eg[y, x]) == MARK:
                mark = (x, y)
    # cells a primitive may pass through (anything not background / box border)
    avail = {(x, y) for y in range(H - 1) for x in range(W)
             if int(eg[y, x]) not in (BG, BORDER, BAR_EMPTY) and (x, y) not in palcells}
    objs = []
    for col in sorted(set(int(v) for v in np.unique(eg[:H - 1]))):
        if col in (BG, BORDER, BAR_EMPTY, MARK):
            continue
        cells = {(x, y) for y in range(H - 1) for x in range(W)
                 if int(eg[y, x]) == col and (x, y) not in bcent and (x, y) not in palcells}
        if len(cells) < 8:
            continue
        for (c, kind, r, pc) in _decompose(cells, avail, 26, W, H):
            full = set(pc)
            # the centre belongs to the object's own SEGMENTS only when the shape runs
            # ORTHOGONALLY through it (plus / hline / vline).  X / diamond shapes do not.
            segc = (((c[0] - 1, c[1]) in full and (c[0] + 1, c[1]) in full) or
                    ((c[0], c[1] - 1) in full and (c[0], c[1] + 1) in full))
            if segc:
                full.add(c)
            # Such a shape MAY still carry a centre DOT.  The game DESTROYS that dot the first
            # time the object is selected (the 0 mark overwrites it and it is never redrawn).
            entry_sel = (mark is not None and c == mark)
            # If the object is ENTRY-SELECTED its centre is hidden under the 0 mark, so whether the
            # centre is a real cell is UNKNOWABLE from the entry frame (L1's X: hole; L4's X: filled).
            # Default to the orthogonal-continuity heuristic; allow a per-level override once seen.
            if entry_sel:
                try:
                    fill = CENTREFILL.get(int(CURRENT_LEVEL))
                except Exception:
                    fill = None
                if fill:
                    full.add(c)
            dot0 = (not segc) and (not entry_sel) and int(eg[c[1], c[0]]) == col
            objs.append({'col': col, 'c0': c, 'kind': kind, 'segc': segc, 'dot0': dot0,
                         'off': frozenset((x - c[0], y - c[1]) for x, y in full)})
    objs.sort(key=lambda o: (o['c0'][1], o['c0'][0]))     # SWITCH order: entry centre (y,x)
    # Z-ORDER is a DIFFERENT ordering: ascending entry centre X (later = on top).  Verified:
    # L0 9(x36) over b(x21); L1 c(27) < d(39) < 9(48); L2 X(18) < line(30) < diamond(45)
    # (in L2 the diamond hides the X's centre mark, while the X does NOT hide the line's).
    # Z-ORDER (draw order, later = on top) is the game's INTERNAL object order.  It is NOT a
    # function of position/colour/shape: L0-L2 happen to match ascending entry-x, but L3 reverses
    # it (the X overdraws the plus even though its entry x is smaller).  So: default to entry-x
    # and allow a per-level override learned from an observed overlap.
    zord = sorted(range(len(objs)), key=lambda i: (objs[i]['c0'][0], objs[i]['c0'][1]))
    try:
        ov = ZORDER.get(int(CURRENT_LEVEL))
    except Exception:
        ov = None
    if ov and len(ov) == len(objs):
        zord = list(ov)
    esel = 0
    for i, o in enumerate(objs):
        if mark is not None and o['c0'] == mark:
            esel = i
    val = {'boxes': boxes, 'bcent': bcent, 'objs': objs, 'esel': esel, 'z': zord,
           'pals': pals, 'palcells': palcells, 'H': H, 'W': W}
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


def _render(pos, sel, lay, ncells, dots=None, cols=None):
    H, W = lay['H'], lay['W']
    g = np.full((H, W), BG, dtype=int)
    for p in lay.get('pals', []):
        g[p['by']:p['by'] + 6, p['bx']:p['bx'] + 6] = p['border']
        g[p['y0']:p['y1'] + 1, p['x0']:p['x1'] + 1] = p['col']
    for (x, y, c) in lay['boxes']:
        g[y - 1:y + 2, x - 1:x + 2] = BORDER
        g[y, x] = c
    # objects in z-order; the 0 mark belongs to the SELECTED object's LAYER, so a later object
    # can overdraw it (seen in L2: the diamond's left vertex covers the X's centre mark).
    for i in lay['z']:
        o = lay['objs'][i]
        cx, cy = pos[i]
        col = o['col'] if cols is None else cols[i]
        for (ox, oy) in o['off']:
            x, y = cx + ox, cy + oy
            if 0 <= x < W and 0 <= y < H - 1:
                g[y, x] = col
        if dots is not None and i < len(dots) and dots[i] and 0 <= cx < W and 0 <= cy < H - 1:
            g[cy, cx] = col                             # surviving centre dot
        if i == sel and 0 <= cx < W and 0 <= cy < H - 1:
            g[cy, cx] = MARK
    g[BAR_ROW, :] = BAR_EMPTY
    if ncells > 0:
        g[BAR_ROW, max(0, W - ncells):] = BAR_FILL
    return g


def _aligned(pos, lay, cols=None):
    for (bx, by, bc) in lay['boxes']:
        ok = False
        for i, o in enumerate(lay['objs']):
            c = o['col'] if cols is None else cols[i]
            if c == bc and (bx - pos[i][0], by - pos[i][1]) in o['off']:
                ok = True
                break
        if not ok:
            return False
    return True


def _recolour(lay, obj, centre, col):
    """CONFIRMED: an object takes a palette's colour as soon as ANY of its CELLS touches ANY cell of
    that palette's whole 6x6 BLOCK (border ring included, not just the 4x4 interior).
      * L3 plus -> c when its up-arm tip hit (30,8)      [interior]
      * L3 X    -> 6 when its DR arm tip hit (33,54)     [BORDER ring] <- proves the block rule
    Colour persists after leaving; the last palette touched wins."""
    cx, cy = centre
    hits = []
    for p in lay.get('pals', []):
        for (ox, oy) in obj['off']:
            x, y = cx + ox, cy + oy
            if p['bx'] <= x <= p['bx'] + 5 and p['by'] <= y <= p['by'] + 5:
                hits.append(p['col'])
                break
    if not hits:
        return col
    # TIE-BREAK when several palette blocks are touched at once: the HIGHEST colour value wins.
    #   L3: X touched 6-block and e-block  -> became e (14 > 6)
    #   L4: X touched e-block and 9-block  -> became e (14 > 9)   [kills "last in row-major order"]
    return max(hits)


# ---------------------------------------------------------------- transition
def init_state(entry_grid):
    eg = entry_grid if entry_grid is not None else ENTRY_GRID
    if eg is None:
        return {'n': 0, 'pos': None, 'sel': 0}
    lay = _layout(eg)
    dots = [o['dot0'] for o in lay['objs']]
    if lay['esel'] < len(dots):
        dots[lay['esel']] = False                       # entry-selected object's dot is gone
    return {'n': 0, 'pos': [o['c0'] for o in lay['objs']], 'sel': lay['esel'], 'dots': dots,
            'cols': [o['col'] for o in lay['objs']]}


def predict(state, grid, action, x=None, y=None):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    H, W = lay['H'], lay['W']
    st = state if isinstance(state, dict) else {}
    pos = list(st.get('pos') or [])
    sel = int(st.get('sel', lay['esel']))
    n = int(st.get('n', 0))
    dots = list(st.get('dots') or [])
    if len(dots) != len(lay['objs']):
        dots = [o['dot0'] for o in lay['objs']]
        if lay['esel'] < len(dots):
            dots[lay['esel']] = False
    cols = list(st.get('cols') or [])
    if len(cols) != len(lay['objs']):
        cols = [o['col'] for o in lay['objs']]

    # resync with the frame when the tracked state does not match it
    mark = None
    my, mx = np.where(g[:H - 1] == MARK)
    if len(mx):
        mark = (int(mx[0]), int(my[0]))
    # trust the tracked state; only resync when it is absent/inconsistent with a VISIBLE mark
    # (the mark can legitimately be hidden by a higher-z object, so mark=None is not an error)
    if (len(pos) != len(lay['objs']) or sel >= len(pos)
            or (mark is not None and tuple(pos[sel]) != mark)):
        pos, sel = _locate(g, lay)
    # the harness never rolls state through transition #0 of the RUN -> recover n from the bar,
    # but ONLY in that case (never "resync" on a mis-guessed budget, which would corrupt n)
    k = int(np.count_nonzero(g[BAR_ROW] != BAR_EMPTY))
    if n == 0 and k > 0:
        for v in range(0, 4 * _budget(CURRENT_LEVEL)):
            if _bar_of(v) == k:
                n = v
                break

    pos = [tuple(p) for p in pos]
    if action in DIRS:
        dx, dy = DIRS[action]
        pos[sel] = (pos[sel][0] + dx * STEP, pos[sel][1] + dy * STEP)
        cols[sel] = _recolour(lay, lay['objs'][sel], pos[sel], cols[sel])   # palette repaint
    elif action == 5:
        sel = (sel + 1) % len(lay['objs'])
    if sel < len(dots):
        dots[sel] = False                               # selecting an object destroys its dot
    n += 1

    ng = _render(pos, sel, lay, _bar_of(n), dots, cols)
    info = {'level_up': _aligned(pos, lay, cols), 'dead': False, 'win': False}
    return ng.tolist(), info, {'n': n, 'pos': pos, 'sel': sel, 'dots': dots, 'cols': cols}


def is_goal(grid):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    pos, _ = _locate(g, lay)
    return _aligned(pos, lay)
