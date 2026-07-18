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
BUDGETS = {0: 100, 1: 100, 2: 200, 3: 200, 4: 250, 5: 200, 6: 300}
# L6 budget = 300 (fits n=0..12 bar data exactly).
# L4: bar data (n=0..5 -> 0,0,1,1,1,1) pins the budget to [214,256]; 250 is the working guess.
# per-level draw order (indices into objs, sorted by entry (y,x)); first = bottom.
# L3: objs = [X(24,21), plus(54,36)]; the X is drawn ON TOP => [plus, X] = [1, 0]
ZORDER = {3: [1, 0], 4: [1, 2, 0], 5: [0, 1, 2], 6: [0, 2, 3, 1]}
# L6 objs=[0:1-obstacle, 1:a-plus, 2:c-ring, 3:7-plus]; draw order obstacle<ring<7-plus<a-plus.
# L5: objs=[plus(48,15), blob(31,31), ring(15,48)]; the b-ring draws ON TOP of the 9-plus.
# true colour of boxes whose centre is HIDDEN by an object in the entry frame (per level)
BOXCOL = {4: {(57, 33): 8, (54, 42): 8}}   # box centres hidden by an object in the entry frame
# centre-fill of the ENTRY-SELECTED object (hidden under the mark at entry): {level: {objidx: True}}
CENTREFILL = {4: True}         # L4's entry-selected X has a FILLED centre (L1's X did not).
# NOTE: the entry-selected object's centre is hidden under the 0 mark, so whether it is a real
# cell CANNOT be read from the entry frame — it must be observed once the object is deselected.
DEFAULT_BUDGET = 200
# L5: an object may DEFORM against an obstacle (a colour with no boxes): a BLOCKED move shrinks the
# blocked axis by 3 and grows the other by 3, conserving cell count (19x19 -> 22x16 -> 25x13, 72).
# The ring's centre follows its bbox, so pos[] is refreshed from the frame each step.
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


def _sring(c, r):
    x, y = c
    s = set()
    for k in range(-r, r + 1):
        s |= {(x + k, y - r), (x + k, y + r), (x - r, y + k), (x + r, y + k)}
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


def _asym_cross(cells, avail, W, H):
    """Detect ONE asymmetric plus/cross covering `cells`: a crossing (cx,cy) whose full row and
    column runs (arms may differ) explain every cell.  Arms are read from the max extent along the
    crossing row/col (robust to occlusion, which only removes interior cells).  Returns
    (cx, cy, [u,d,l,r]) or None.  Clipped arms (tip at a grid edge) are completed by symmetry."""
    from collections import Counter
    cx = Counter(p[0] for p in cells).most_common(1)[0][0]
    cy = Counter(p[1] for p in cells).most_common(1)[0][0]
    col_ys = [p[1] for p in cells if p[0] == cx]
    row_xs = [p[0] for p in cells if p[1] == cy]
    if len(col_ys) < 5 or len(row_xs) < 5:
        return None
    u, d = cy - min(col_ys), max(col_ys) - cy
    l, r = cx - min(row_xs), max(row_xs) - cx
    if min(col_ys) <= 0:         u = max(u, d)          # top-clipped -> symmetric
    if max(col_ys) >= H - 2:     d = max(u, d)          # bottom-clipped (bar row)
    if min(row_xs) <= 0:         l = max(l, r)
    if max(row_xs) >= W - 1:     r = max(l, r)
    cross = {(cx, y) for y in range(cy - u, cy + d + 1)} | {(x, cy) for x in range(cx - l, cx + r + 1)}
    ongrid = {p for p in cross if 0 <= p[0] < W and 0 <= p[1] < H - 1}
    # every observed cell must lie on the cross, and the cross's on-grid cells must be avail/cells
    if not (cells <= cross):
        return None
    if any(p not in avail and p not in cells for p in ongrid):
        return None
    if u < 3 or d < 3 or l < 3 or r < 3:
        return None
    return (cx, cy), [u, d, l, r]


def _decompose(cells, avail, maxr=26, W=64, H=64):
    """greedy exact cover of `cells` by maximal primitives (may use `avail` cells too)."""
    if not cells:
        return []
    ac = _asym_cross(cells, avail, W, H)                # one asymmetric cross explains it all?
    if ac is not None and (max(ac[1]) != min(ac[1])):   # only when genuinely asymmetric
        (cx, cy), arms = ac
        u, d, l, r = arms
        cc = {(cx, y) for y in range(cy - u, cy + d + 1)} | {(x, cy) for x in range(cx - l, cx + r + 1)}
        return [((cx, cy), 'plus', max(arms), frozenset(cc))]
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
            for r in range(3, maxr):          # SQUARE (Chebyshev) ring
                ring = _sring(c, r)
                if _ok(ring, avail, W, H):
                    cands.append((c, 's', r, ring))
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
    if left:
        # BLOB fallback: whatever no primitive explains stays ONE rigid object.
        xs = [p[0] for p in left]
        ys = [p[1] for p in left]
        c = ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)
        chosen.append((c, 'blob', 0, frozenset(left)))
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
    # palettes: SxS block (S=5 or 6), uniform border ring, uniform interior of another colour
    pals = []
    palcells = set()
    for S in (6, 5):
        for y in range(H - S):
            for x in range(W - S):
                if any((x + dx, y + dy) in palcells for dx in (0, S - 1) for dy in (0, S - 1)):
                    continue
                blk = eg[y:y + S, x:x + S]
                b = int(blk[0, 0])
                if b in (BG, BAR_EMPTY):
                    continue
                ring_ok = (all(int(v) == b for v in blk[0, :]) and all(int(v) == b for v in blk[S - 1, :])
                           and all(int(v) == b for v in blk[:, 0]) and all(int(v) == b for v in blk[:, S - 1]))
                if not ring_ok:
                    continue
                inner = blk[1:S - 1, 1:S - 1]
                c0 = int(inner[0, 0])
                if c0 == b or c0 in (BG, BAR_EMPTY):
                    continue
                if all(int(v) == c0 for v in inner.flatten()):
                    pals.append({'x0': x + 1, 'x1': x + S - 2, 'y0': y + 1, 'y1': y + S - 2,
                                 'col': c0, 'border': b, 'bx': x, 'by': y, 'sz': S})
                    for dy in range(S):
                        for dx in range(S):
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
            arms_udlr = None
            if kind == 'plus':
                offs = {(x - c[0], y - c[1]) for x, y in full}
                u = max([-oy for (ox, oy) in offs if ox == 0 and oy < 0] or [0])
                d = max([oy for (ox, oy) in offs if ox == 0 and oy > 0] or [0])
                lft = max([-ox for (ox, oy) in offs if oy == 0 and ox < 0] or [0])
                rgt = max([ox for (ox, oy) in offs if oy == 0 and ox > 0] or [0])
                arms_udlr = [u, d, lft, rgt]
            objs.append({'col': col, 'c0': c, 'kind': kind, 'segc': segc, 'dot0': dot0,
                         'arms_udlr': arms_udlr,
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
        _s = p.get('sz', 6)
        g[p['by']:p['by'] + _s, p['bx']:p['bx'] + _s] = p['border']
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


def _next_sel(sel, lay):
    """ACTION5 -> next SELECTABLE object, skipping the obstacle (a wall can't be
    selected/moved).  Cycles by object index."""
    obs = _obstacle(lay)
    oi = lay['objs'].index(obs) if obs is not None else -1
    n = len(lay['objs'])
    for step in range(1, n + 1):
        cand = (sel + step) % n
        if cand != oi:
            return cand
    return sel


def _obstacle(lay):
    """The obstacle is a WALL objects deform against (L5/L6's colour-1 anti-diamond).  It is a
    'blob' (an UNRECOGNISED primitive) whose colour has no boxes and is not a palette colour —
    movable objects are always recognised primitives (plus/x/diamond/ring/line), never blobs."""
    bcols = {c for (_, _, c) in lay['boxes']}
    pcols = {p['col'] for p in lay.get('pals', [])}
    for o in lay['objs']:
        if o['kind'] == 'blob' and o['col'] not in bcols and o['col'] not in pcols:
            return o
    return None


def _ringbox(g, col, lay):
    """live bounding box of a ring-ish object of colour col, straight from the frame"""
    pts = [(int(x), int(y)) for y, x in np.argwhere(np.asarray(g)[:lay['H'] - 1] == col)
           if (int(x), int(y)) not in lay['bcent']]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [min(xs), max(xs), min(ys), max(ys)]


def _rect_ring(bb):
    x0, x1, y0, y1 = bb
    s = set()
    for x in range(x0, x1 + 1):
        s.add((x, y0)); s.add((x, y1))
    for y in range(y0, y1 + 1):
        s.add((x0, y)); s.add((x1, y))
    return s


def _deform(bb, action, obs_cells, grow_side):
    """BLOCKED move: blocked axis -3 (blocked edge fixed), other axis +3 (cells conserved).
    UNBLOCKED: plain +/-3 translate.  Returns (new_bb, new_grow_side)."""
    x0, x1, y0, y1 = bb
    dx, dy = DIRS[action]
    lead = _rect_ring([x0 + dx * STEP, x1 + dx * STEP, y0 + dy * STEP, y1 + dy * STEP])
    if not (lead & obs_cells):
        return [x0 + dx * STEP, x1 + dx * STEP, y0 + dy * STEP, y1 + dy * STEP], grow_side
    if dy:                                   # vertical move blocked -> height -3, width +3
        if dy < 0:
            y1 -= STEP
        else:
            y0 += STEP
        if grow_side:
            x1 += STEP
        else:
            x0 -= STEP
    else:                                    # horizontal move blocked -> width -3, height +3
        if dx < 0:
            x1 -= STEP
        else:
            x0 += STEP
        if grow_side:
            y1 += STEP
        else:
            y0 -= STEP
    return [x0, x1, y0, y1], (not grow_side)


def _plus_cells(cx, cy, arms):
    u, d, l, r = arms
    s = {(cx, cy)}
    for k in range(1, u + 1): s.add((cx, cy - k))
    for k in range(1, d + 1): s.add((cx, cy + k))
    for k in range(1, l + 1): s.add((cx - k, cy))
    for k in range(1, r + 1): s.add((cx + k, cy))
    return s


def _plus_deform(cx, cy, arms, action, obs_cells):
    """A plus = a vertical bar V (x=cx, y in [cy-u,cy+d]) + a horizontal bar H (y=cy, x in
    [cx-l,cx+r]).  A move translates EACH bar by 3, unless that bar's translated cells would enter
    the obstacle -> that bar stays.  The crossing = (V.x, H.y); arms follow.  Cells are conserved.
    The mark cursor advances iff the bar PARALLEL to the move is free.
    Returns (new_crossing, new_arms, cursor_moved)."""
    u, d, l, r = arms
    mdx, mdy = DIRS[action][0] * STEP, DIRS[action][1] * STEP
    vy0, vy1 = cy - u, cy + d                       # vertical bar y-extent (x = cx)
    hx0, hx1 = cx - l, cx + r                       # horizontal bar x-extent (y = cy)
    v_hit = any((cx + mdx, y + mdy) in obs_cells for y in range(vy0, vy1 + 1))
    h_hit = any((x + mdx, cy + mdy) in obs_cells for x in range(hx0, hx1 + 1))
    vshx, vshy = (0, 0) if v_hit else (mdx, mdy)    # V shift
    hshx, hshy = (0, 0) if h_hit else (mdx, mdy)    # H shift
    nvx = cx + vshx
    nvy0, nvy1 = vy0 + vshy, vy1 + vshy
    nhy = cy + hshy
    nhx0, nhx1 = hx0 + hshx, hx1 + hshx
    ncx, ncy = nvx, nhy                             # crossing = (V.x, H.y)
    narms = [ncy - nvy0, nvy1 - ncy, ncx - nhx0, nhx1 - ncx]
    if mdx != 0:      cursor_moved = not h_hit      # horizontal move gated by H (the parallel bar)
    else:             cursor_moved = not v_hit      # vertical move gated by V (the parallel bar)
    return (ncx, ncy), narms, cursor_moved


def _recolour_cells(lay, cells, col):
    """an object takes a palette's colour as soon as ANY of its CELLS touches ANY cell of that
    palette's whole SxS BLOCK (border ring included).  Ties -> highest colour value wins."""
    hits = []
    for p in lay.get('pals', []):
        _s = p.get('sz', 6) - 1
        for (x, y) in cells:
            if p['bx'] <= x <= p['bx'] + _s and p['by'] <= y <= p['by'] + _s:
                hits.append(p['col'])
                break
    return max(hits) if hits else col


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
            _s = p.get('sz', 6) - 1
            if p['bx'] <= x <= p['bx'] + _s and p['by'] <= y <= p['by'] + _s:
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
    # parms/pcur are PER-OBJECT dicts (a level may hold several deformable pluses, e.g. L6).
    parms = {i: list(o['arms_udlr']) for i, o in enumerate(lay['objs'])
             if o['kind'] == 'plus' and o.get('arms_udlr')}
    pcur = {i: list(o['c0']) for i, o in enumerate(lay['objs'])
            if o['kind'] == 'plus' and o.get('arms_udlr')}
    return {'n': 0, 'pos': [o['c0'] for o in lay['objs']], 'sel': lay['esel'], 'dots': dots,
            'cols': [o['col'] for o in lay['objs']], 'parms': parms, 'pcur': pcur}


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
    obs0 = _obstacle(lay)
    if obs0 is not None:
        # L5: refresh the ring's centre from its live bbox (it may have deformed/translated).
        for i, o in enumerate(lay['objs']):
            if o['kind'] == 's':
                lb = _ringbox(g, o['col'], lay)
                if lb:
                    pos[i] = ((lb[0] + lb[1]) // 2, (lb[2] + lb[3]) // 2)
        # each object's MARK cell: pcur for the plus, bbox centre for the ring, pos otherwise.
        _pc = st.get('pcur') or {}
        def _markpos(i):
            o = lay['objs'][i]
            if o['kind'] == 'plus' and i in _pc:
                return tuple(_pc[i])
            if o['kind'] == 's' and st.get('bb'):
                b = st['bb']
                return ((b[0] + b[1] + 1) // 2, (b[2] + b[3] + 1) // 2)
            return tuple(pos[i])
        # keep the tracked sel if its mark already matches; only re-pick when it doesn't.
        if mark is not None and _markpos(sel) != mark:
            best, bd = sel, None
            for i in range(len(pos)):
                mp = _markpos(i)
                d = abs(mp[0] - mark[0]) + abs(mp[1] - mark[1])
                if bd is None or d < bd:
                    best, bd = i, d
            sel = best
    elif (len(pos) != len(lay['objs']) or sel >= len(pos)
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

    obs = _obstacle(lay)
    bb = st.get('bb')
    gs = bool(st.get('gs', False))
    # bb is threaded PURELY in state (never re-read from the frame): a ring can be occluded by
    # other objects on lower z, which would corrupt a frame-derived bbox.  Initialise from the
    # ring's entry layout shape the first time we need it.
    if obs is not None and bb is None:
        for _o in lay['objs']:
            if _o['kind'] == 's':
                _xs = [_o['c0'][0] + ox for (ox, oy) in _o['off']]
                _ys = [_o['c0'][1] + oy for (ox, oy) in _o['off']]
                bb = [min(_xs), max(_xs), min(_ys), max(_ys)]
                break
    parms = dict(st.get('parms') or {})
    pcur = dict(st.get('pcur') or {})
    if obs is not None:
        _oxs = [obs['c0'][0] + ox for (ox, oy) in obs['off']]
        _oys = [obs['c0'][1] + oy for (ox, oy) in obs['off']]
        obb = (min(_oxs), max(_oxs), min(_oys), max(_oys))     # solid bbox of the obstacle (wall)
        ocells = {(x, y) for x in range(obb[0], obb[1] + 1) for y in range(obb[2], obb[3] + 1)}
        pos = [tuple(p) for p in pos]
        selo = lay['objs'][sel]
        if action in DIRS and selo['kind'] == 's':               # deformable RING (bb threaded)
            bb, gs = _deform(bb, action, ocells, gs)
            cols[sel] = _recolour_cells(lay, _rect_ring(bb), cols[sel])
        elif action in DIRS and selo['kind'] == 'plus':          # deformable PLUS (per-object parms)
            pa = parms.get(sel) or list(selo['arms_udlr'])
            (ncx, ncy), pa, cmoved = _plus_deform(pos[sel][0], pos[sel][1], pa, action, ocells)
            pos[sel] = (ncx, ncy)
            parms[sel] = pa
            cols[sel] = _recolour_cells(lay, _plus_cells(ncx, ncy, pa), cols[sel])
            pc = pcur.get(sel) or list(selo['c0'])
            if cmoved:
                dxc, dyc = DIRS[action]
                pc = [pc[0] + dxc * STEP, pc[1] + dyc * STEP]
            pcur[sel] = pc
        elif action in DIRS:
            dx, dy = DIRS[action]
            pos[sel] = (pos[sel][0] + dx * STEP, pos[sel][1] + dy * STEP)
            cols[sel] = _recolour(lay, selo, pos[sel], cols[sel])
        elif action == 5:
            sel = _next_sel(sel, lay)
        if sel < len(dots):
            dots[sel] = False
        n += 1
        ng = _render_deform(pos, sel, lay, _bar_of(n), dots, cols, bb, parms, pcur)
        info = {'level_up': _aligned_deform(pos, lay, cols, bb, parms), 'dead': False, 'win': False}
        return ng.tolist(), info, {'n': n, 'pos': pos, 'sel': sel, 'dots': dots, 'cols': cols,
                                   'bb': bb, 'gs': gs, 'parms': parms, 'pcur': pcur}

    pos = [tuple(p) for p in pos]
    if action in DIRS:
        dx, dy = DIRS[action]
        pos[sel] = (pos[sel][0] + dx * STEP, pos[sel][1] + dy * STEP)
        cols[sel] = _recolour(lay, lay['objs'][sel], pos[sel], cols[sel])   # palette repaint
    elif action == 5:
        sel = _next_sel(sel, lay)
    if sel < len(dots):
        dots[sel] = False                               # selecting an object destroys its dot
    n += 1
    ng = _render(pos, sel, lay, _bar_of(n), dots, cols)
    info = {'level_up': _aligned(pos, lay, cols), 'dead': False, 'win': False}
    return ng.tolist(), info, {'n': n, 'pos': pos, 'sel': sel, 'dots': dots, 'cols': cols}


def _render_deform(pos, sel, lay, ncells, dots, cols, bb, parms, pcur=None):
    H, W = lay['H'], lay['W']
    g = np.full((H, W), BG, dtype=int)
    for p in lay.get('pals', []):
        _s = p.get('sz', 6)
        g[p['by']:p['by'] + _s, p['bx']:p['bx'] + _s] = p['border']
        g[p['y0']:p['y1'] + 1, p['x0']:p['x1'] + 1] = p['col']
    for (x, y, c) in lay['boxes']:
        g[y - 1:y + 2, x - 1:x + 2] = BORDER
        g[y, x] = c
    for i in lay['z']:
        o = lay['objs'][i]
        col = cols[i]
        cx, cy = pos[i]
        if o['kind'] == 's' and bb:
            cells = _rect_ring(bb)
            mk = ((bb[0] + bb[1] + 1) // 2, (bb[2] + bb[3] + 1) // 2)
        elif o['kind'] == 'plus' and parms and i in parms:
            cells = _plus_cells(cx, cy, parms[i])
            mk = tuple(pcur[i]) if (pcur and i in pcur) else (cx, cy)
        else:
            cells = {(cx + ox, cy + oy) for (ox, oy) in o['off']}
            mk = (cx, cy)
        for (x, y) in cells:
            if 0 <= x < W and 0 <= y < H - 1:
                g[y, x] = col
        if i == sel and 0 <= mk[0] < W and 0 <= mk[1] < H - 1:
            g[mk[1], mk[0]] = MARK
    g[BAR_ROW, :] = BAR_EMPTY
    if ncells > 0:
        g[BAR_ROW, max(0, W - ncells):] = BAR_FILL
    return g


def _aligned_deform(pos, lay, cols, bb, parms):
    for (bx, by, bc) in lay['boxes']:
        ok = False
        for i, o in enumerate(lay['objs']):
            if cols[i] != bc:
                continue
            if o['kind'] == 's' and bb:
                if (bx, by) in _rect_ring(bb):
                    ok = True
            elif o['kind'] == 'plus' and parms and i in parms:
                if (bx, by) in _plus_cells(pos[i][0], pos[i][1], parms[i]):
                    ok = True
            elif (bx - pos[i][0], by - pos[i][1]) in o['off']:
                ok = True
            if ok:
                break
        if not ok:
            return False
    return True


def _render_with_ring(pos, sel, lay, ncells, dots, cols, bb, obs):
    H, W = lay['H'], lay['W']
    g = np.full((H, W), BG, dtype=int)
    for (x, y, c) in lay['boxes']:
        g[y - 1:y + 2, x - 1:x + 2] = BORDER
        g[y, x] = c
    for i in lay['z']:
        o = lay['objs'][i]
        col = cols[i]
        if o['kind'] == 's' and bb:
            cells = _rect_ring(bb)
        else:
            cx, cy = pos[i]
            cells = {(cx + ox, cy + oy) for (ox, oy) in o['off']}
        for (x, y) in cells:
            if 0 <= x < W and 0 <= y < H - 1:
                g[y, x] = col
        if i == sel:
            if o['kind'] == 's' and bb:
                mx, my = (bb[0] + bb[1] + 1) // 2, (bb[2] + bb[3] + 1) // 2
            else:
                mx, my = pos[i]
            if 0 <= mx < W and 0 <= my < H - 1:
                g[my, mx] = MARK
    g[BAR_ROW, :] = BAR_EMPTY
    if ncells > 0:
        g[BAR_ROW, max(0, W - ncells):] = BAR_FILL
    return g


def _aligned_ring(pos, lay, cols, bb):
    for (bx, by, bc) in lay['boxes']:
        ok = False
        for i, o in enumerate(lay['objs']):
            if cols[i] != bc:
                continue
            if o['kind'] == 's' and bb:
                if (bx, by) in _rect_ring(bb):
                    ok = True
            elif (bx - pos[i][0], by - pos[i][1]) in o['off']:
                ok = True
            if ok:
                break
        if not ok:
            return False
    return True


def is_goal(grid):
    g = np.asarray(grid)
    lay = _layout(ENTRY_GRID if ENTRY_GRID is not None else g)
    pos, _ = _locate(g, lay)
    return _aligned(pos, lay)
