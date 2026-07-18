# su15 world model — general "magnet + merge-chain + glyph" engine
#
# PIECES (tiers): 1: 'a'=10 (1x1), 2: '6'=6 (2x2), 3: 'f'=15 (3x3), 4: 'b'=11 (4x4)
# A piece of size s anchored at (ax,ay) occupies ax+lo..ax+lo+s-1 where lo=-(s//2)
#   (1x1: cell; 2x2: click at bottom-right; 3x3: centered; 4x4: guess -2..+1)
# CLICK (x,y) with 10<=y<=62: costs 2 budget cells (rightmost 0s of row 63 -> 5).
#   All pieces whose anchor is within dist^2 <= 81 of the click are attracted:
#     - exactly 1 piece of a tier in range -> it moves, anchor=click
#     - >=2 pieces of same tier in range -> they vanish, ONE next-tier piece
#       appears anchored at click (merge). (3+ in range untested; assume all merge)
# Clicks with y<=9 (HUD band): free no-op. Action 7: no-op.
# Underlay: ENTRY_GRID minus pieces (->bg 5); L0 plus-marker (0-cells in play):
#   consumed by first landing: center reveals trail dot 3, arms -> bg.
# GOALS:
#   - if ENTRY_GRID has a 3x3 core of 3s inside the 9-disk (L0): tier-3 piece
#     anchored at core center -> level_up.
#   - else (L1): creating the tier-4 piece (b) -> level_up (HYPOTHESIS).

TIER_COLOR = {1: 10, 2: 6, 3: 15, 4: 11, 5: 12, 6: 8}
COLOR_TIER = {10: 1, 6: 2, 15: 3, 11: 4, 12: 5, 8: 6}

_PIECE_SIZE = {}  # (tier,ax,ay) -> actual size, for big odd-sized pieces

def _span(s):
    lo = -(s // 2)
    return lo, lo + s - 1

def _cells(ax, ay, s):
    # s is a TIER; big tiers may have a recorded actual size
    s = _PIECE_SIZE.get((s, ax, ay), s if s <= 4 else {5: 5, 6: 6}.get(s, s))
    lo, hi = _span(s)
    return [(ax+dx, ay+dy) for dy in range(lo, hi+1) for dx in range(lo, hi+1)]

def _find_pieces(g):
    """Return list of (tier, ax, ay). Scan play area rows 10..62.
    Tiers 1-4: size==tier squares. Tiers 5-6 (c=12, 8=8): detected as solid
    square components of ANY size (observed: the L5 '8' boulder is 7x7);
    anchor=component center; span derived from actual size via _PIECE_SIZE."""
    pieces = []
    seen = set()
    # big pieces (colors 12, 8): connected components
    for color, tier in ((12, 5), (8, 6)):
        comp_seen = set()
        for y in range(10, 63):
            for x in range(64):
                if g[y][x] == color and (x, y) not in comp_seen:
                    stack = [(x, y)]; comp = []
                    while stack:
                        cx, cy = stack.pop()
                        if (cx, cy) in comp_seen or not (0 <= cx <= 63 and 10 <= cy <= 62) \
                           or g[cy][cx] != color:
                            continue
                        comp_seen.add((cx, cy)); comp.append((cx, cy))
                        stack += [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
                    xs = [c[0] for c in comp]; ys = [c[1] for c in comp]
                    w = max(xs)-min(xs)+1; h = max(ys)-min(ys)+1
                    if w == h and len(comp) == w*h:
                        ax, ay = (min(xs)+max(xs))//2, (min(ys)+max(ys))//2
                        pieces.append((tier, ax, ay))
                        _PIECE_SIZE[(tier, ax, ay)] = w
                        seen |= set(comp)
    for y in range(10, 63):
        for x in range(64):
            if (x, y) in seen:
                continue
            v = g[y][x]
            t = COLOR_TIER.get(v)
            if t is None or t >= 5:
                continue
            s = t  # size == tier number (1,2,3,4)
            # (x,y) is top-left of the square if all cells match and this is
            # the first (scan order) cell
            ok = True
            for dy in range(s):
                for dx in range(s):
                    xx, yy = x+dx, y+dy
                    if xx > 63 or yy > 62 or g[yy][xx] != v:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                for dy in range(s):
                    for dx in range(s):
                        seen.add((x+dx, y+dy))
                lo, hi = _span(s)
                pieces.append((t, x - lo, y - lo))  # anchor = topleft - lo
    return pieces

def _entry_features():
    eg = ENTRY_GRID
    feats = {}
    feats['entry_pieces'] = _find_pieces(eg)
    plus = [(x, y) for y in range(10, 63) for x in range(64) if eg[y][x] == 0]
    feats['plus_cells'] = set(plus)
    if plus:
        xs = sorted(set(x for x, y in plus))
        ys = sorted(set(y for x, y in plus))
        feats['plus_center'] = (xs[len(xs)//2], ys[len(ys)//2])
    else:
        feats['plus_center'] = None
    # destinations: centers of connected 9-disk components (sorted by x)
    seen = set()
    dests = []
    for y in range(10, 63):
        for x in range(64):
            if eg[y][x] == 9 and (x, y) not in seen:
                stack = [(x, y)]; comp = []
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in seen or not (0 <= cx <= 63 and 10 <= cy <= 62) \
                       or eg[cy][cx] != 9:
                        continue
                    seen.add((cx, cy)); comp.append((cx, cy))
                    stack += [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
                xs = [c[0] for c in comp]; ys = [c[1] for c in comp]
                dests.append(((min(xs)+max(xs))//2, (min(ys)+max(ys))//2,
                              min(xs), max(xs), min(ys), max(ys)))
    dests.sort()
    feats['dest_boxes'] = [(d[2], d[3], d[4], d[5]) for d in dests]
    feats['dests'] = [(d[0], d[1]) for d in dests]
    # goal tiers: pieces shown in the HUD band, RIGHT of the palette box
    # (palette box = leading 5-bg region of row 0; L5 box is wider than L0-4)
    px = 16
    for x in range(64):
        if eg[0][x] == 4:
            px = x
            break
    hud = []
    seenh = set()
    for x in range(px, 64):
        for y in range(0, 10):
            v = eg[y][x]
            t = COLOR_TIER.get(v)
            if t is not None and (x, y) not in seenh:
                # mark the whole square
                for dy in range(t):
                    for dx in range(t):
                        seenh.add((x+dx, y+dy))
                hud.append(t)
    feats['hud_tiers'] = hud
    feats['glyph_hud'] = any(eg[y][x] == 7 for y in range(0, 10)
                             for x in range(px, 64))
    return feats

def _underlay(x, y):
    eg = ENTRY_GRID
    f = _entry_features()
    for (t, ax, ay) in f['entry_pieces']:
        if (x, y) in _cells(ax, ay, t):
            return 5
    if (x, y) in f['plus_cells']:
        return 3 if (x, y) == f['plus_center'] else 5
    if eg[y][x] == 7:
        return 5  # glyph is mobile, not decor
    return eg[y][x]

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6:
        return g, info
    if y is None or y <= 9:
        return g, info
    # budget bar row 63 = click-progress bar: after k clicks, floor(k*64/N)
    # cells are consumed (rightmost first), N = level's click allowance.
    # Observed: L0=32, L1=32, L2=48.
    N = {0: 32, 1: 32, 2: 48, 3: 48, 4: 32, 5: 32}.get(CURRENT_LEVEL, 48)
    C = sum(1 for v in g[63] if v == 5)
    k = (C * N + 63) // 64  # ceil(C*N/64): clicks taken so far
    newC = ((k + 1) * 64) // N
    for bx in range(63, -1, -1):
        if C >= newC:
            break
        if g[63][bx] == 0:
            g[63][bx] = 5
            C += 1
    if y == 63:
        return g, info  # untested; assume no piece interaction
    # glyph pre-click target (nearest piece) — for the dash rule
    pre_glyphs = _glyph_target(g)  # [(cells, target)] per glyph, pre-click
    pieces = _find_pieces(g)
    feats = _entry_features()
    # attracted pieces per tier
    from collections import defaultdict
    att = defaultdict(list)
    for (t, ax, ay) in pieces:
        # pulled iff ANY cell of the piece is within R=8 (d^2<=64) of click
        if min((cx - x)**2 + (cy - y)**2 for (cx, cy) in _cells(ax, ay, t)) <= 64:
            att[t].append((ax, ay))
    for t, lst in sorted(att.items()):
        if len(lst) == 0:
            continue
        # clear all attracted pieces of this tier
        for (ax, ay) in lst:
            for (cx, cy) in _cells(ax, ay, t):
                if 0 <= cx <= 63 and 10 <= cy <= 62:
                    g[cy][cx] = _underlay(cx, cy)
        if len(lst) == 1:
            nt = t  # move
            if t >= 5:  # preserve actual size of big pieces through moves
                old = lst[0]
                if (t, old[0], old[1]) in _PIECE_SIZE:
                    _PIECE_SIZE[(nt, x, y)] = _PIECE_SIZE[(t, old[0], old[1])]
        else:
            nt = t + 1  # merge
            if nt > 4 and t < 5:
                nt = 4  # cap (unknown)
        col = TIER_COLOR[nt]
        for (cx, cy) in _cells(x, y, nt):
            if 0 <= cx <= 63 and 10 <= cy <= 62:
                g[cy][cx] = col
    for (gcells, gtarget) in pre_glyphs:
        _move_glyph(g, gcells, gtarget, x, y)
    if is_goal(g):
        info["level_up"] = True
    return g, info

def _glyphs(g):
    """Connected components of 7-cells (each an independent glyph), sorted by
    top-left cell for deterministic processing order."""
    seen = set()
    comps = []
    for y in range(10, 63):
        for x in range(64):
            if g[y][x] == 7 and (x, y) not in seen:
                stack = [(x, y)]; comp = []
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in seen or not (0 <= cx <= 63 and 10 <= cy <= 62) \
                       or g[cy][cx] != 7:
                        continue
                    seen.add((cx, cy)); comp.append((cx, cy))
                    stack += [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1),
                              (cx+1, cy+1), (cx-1, cy-1), (cx+1, cy-1), (cx-1, cy+1)]
                comps.append(sorted(comp, key=lambda c: (c[1], c[0])))
    # canonicalize: a glyph partially hidden under a piece shows <8 cells;
    # fit the known hollow-diamond shape and return the FULL 8 cells
    SHAPE = [(0, -2), (-1, -1), (1, -1), (-2, 0), (2, 0), (-1, 1), (0, 1), (1, 1)]
    fixed = []
    for comp in comps:
        if len(comp) == 8:
            fixed.append(comp)
            continue
        cs = set(comp)
        done = False
        for (ax, ay) in comp:
            for (sx, sy) in SHAPE:
                cx, cy = ax - sx, ay - sy
                full = [(cx + dx, cy + dy) for (dx, dy) in SHAPE]
                if cs <= set(full):
                    fixed.append(sorted(full, key=lambda c: (c[1], c[0])))
                    done = True
                    break
            if done:
                break
        if not done:
            fixed.append(comp)
    comps = fixed
    comps.sort(key=lambda cs: cs[0][1] * 64 + cs[0][0])
    return comps

def _center_of(cells):
    n = len(cells)
    gx = int(sum(c[0] for c in cells) / n + 0.5)
    gy = int(sum(c[1] for c in cells) / n + 0.5)
    return gx, gy

def _glyph_target(g):
    """List of (cells, target) for each glyph; target=(tier,ax,ay) nearest piece."""
    pieces = _find_pieces(g)
    out = []
    for cells in _glyphs(g):
        if not pieces:
            out.append((cells, None))
            continue
        gx, gy = _center_of(cells)
        out.append((cells, min(pieces,
                    key=lambda p: (p[1]-gx)**2 + (p[2]-gy)**2)))
    return out

# --- 7-glyph: autonomous walker; steps once per paid click ---
def _move_glyph(g, cells, pre_target, clkx=None, clky=None):
    """One glyph's post-click step (see notes; all thresholds cell-based)."""
    cells = [(x, y) for (x, y) in cells if g[y][x] == 7]
    if not cells:
        return
    gx, gy = _center_of(cells)
    pieces = _find_pieces(g)
    # LEAP: a click within cell-d^2<=64 of the glyph makes it POUNCE toward
    # the click along the DOMINANT axis, length round(20 - |click-center|)
    # (obs: (+1,+9.1)->(0,+11); (0,+8.1)->(0,+12); (+8,0)->(+12,0))
    # ONLY when the HUD band shows the glyph icon (glyph is interactive
    # this level — L3/L4 clicks near glyphs did NOT leap).
    if clkx is not None and _entry_features().get('glyph_hud') and \
            min((cx-clkx)**2 + (cy-clky)**2 for (cx, cy) in cells) <= 64:
        # LEAP v2: glyph's CENTER CELL lands 4 BEYOND the click along the
        # dominant axis; move length capped at 12. No eat on leap landing.
        # (5/5 exact: A 47=cap, B 58, C 34, c1 46, c2 35)
        n = len(cells)
        fgx = sum(c[0] for c in cells) / n
        fgy = sum(c[1] for c in cells) / n
        ddx, ddy = clkx - fgx, clky - fgy
        # constant 12-cell pounce along the dominant axis (5/5 ground truth)
        if abs(ddx) >= abs(ddy):
            mvx, mvy = (12 if ddx >= 0 else -12), 0
        else:
            mvx, mvy = 0, (12 if ddy >= 0 else -12)
        new = [(cx + mvx, cy + mvy) for (cx, cy) in cells]
        if (mvx, mvy) != (0, 0) and \
                all(0 <= cx <= 63 and 10 <= cy <= 62 for (cx, cy) in new):
            for (cx, cy) in cells:
                if g[cy][cx] == 7:
                    g[cy][cx] = _underlay(cx, cy)
            piece_cells = set()
            for p in _find_pieces(g):  # POST-click piece positions
                piece_cells |= set(_cells(p[1], p[2], p[0]))
            for (cx, cy) in new:
                if (cx, cy) not in piece_cells:
                    g[cy][cx] = 7
        return
    if pre_target is not None and pre_target not in pieces and any(
            abs(p[1] - pre_target[1]) <= 3 and abs(p[2] - pre_target[2]) <= 3
            for p in pieces):
        # target consumed AND its successor spawned within (4,4) of its old
        # spot: glyph lunges THROUGH the old spot to the mirror point
        # (obs #48: product (33,28) near (36,29) -> dash; #61: product
        # (30,34) far -> normal step instead)
        tx, ty = pre_target[1], pre_target[2]
        mvx, mvy = 2*(tx - gx), 2*(ty - gy)
        eaten = None
    # NOTE: transition #77 (L4) is a KNOWN-UNEXPLAINED outlier: target
    # consumed, successor (product) 8 away at ~53deg off-axis -> glyph moved
    # (+12,-8), fitting no tried rule. Plans must avoid consumed-target
    # events unless successor is >=12 away AND <=25deg off the chase axis
    # (that regime is 4x confirmed as a plain normal step).
    else:
        if not pieces:
            return
        t, tx, ty = min(pieces, key=lambda p: (p[1]-gx)**2 + (p[2]-gy)**2)
        pc = _cells(tx, ty, t)
        bcx, bcy = min(pc, key=lambda c: (c[0]-gx)**2 + (c[1]-gy)**2)
        cdx, cdy = bcx - gx, bcy - gy
        dx, dy = tx - gx, ty - gy
        if abs(cdx) <= 4 and abs(cdy) <= 4:
            # close: UNIT creep toward prey cell-centroid (sign per axis,
            # |d|<0.5 -> 0). Fits all 4 close-approaches incl. overlap-eats.
            n = len(cells)
            cgx = sum(c[0] for c in cells) / n
            cgy = sum(c[1] for c in cells) / n
            pcx = sum(c[0] for c in pc) / len(pc)
            pcy = sum(c[1] for c in pc) / len(pc)
            def usign(v):
                return 0 if abs(v) < 0.5 else (1 if v > 0 else -1)
            mvx = usign(pcx - cgx)
            mvy = usign(pcy - cgy)
        else:
            mvx = max(-4, min(4, dx))
            mvy = max(-4, min(4, dy))
        eaten = None
    new = cells
    if (mvx, mvy) != (0, 0):
        cand = [(x + mvx, y + mvy) for (x, y) in cells]
        if all(0 <= x <= 63 and 10 <= y <= 62 for (x, y) in cand):
            new = cand
            for (x, y) in cells:
                g[y][x] = _underlay(x, y)
            for (x, y) in new:
                g[y][x] = 7
    # EAT rule: glyph body cell OVERLAPS a piece cell -> that piece is eaten
    # (check against the pre-move piece list: the drawn glyph may cover cells)
    body = set(new)
    for p in pieces:
        if body & set(_cells(p[1], p[2], p[0])):
            _eat(g, new, p)

def _eat(g, cells, target):
    """Glyph (already moved; body=cells) eats an overlapped piece:
    - piece removed; a piece one tier LOWER spawns at the piece's farthest
      cell from the glyph, +9 along the dominant approach axis (observed:
      6@(33,28) -> a@(42,27); f@(23,39) -> 6@(13,39))
    - if remaining units < required units: 9-disks and HUD pieces recolor to 2."""
    t, tx, ty = target
    n = len(cells)
    cgx = sum(c[0] for c in cells) / n
    cgy = sum(c[1] for c in cells) / n
    pc = _cells(tx, ty, t)
    # remove piece (never erase glyph cells drawn over it)
    for (cx, cy) in pc:
        if 0 <= cx <= 63 and 10 <= cy <= 62 and g[cy][cx] != 7:
            g[cy][cx] = _underlay(cx, cy)
    # eject downgraded piece
    gx0, gy0 = int(cgx + 0.5), int(cgy + 0.5)
    if t > 1:
        nt = t - 1
        ns = nt if nt <= 4 else {5: 5, 6: 6}[nt]
        xs = [c[0] for c in pc]; ys = [c[1] for c in pc]
        ddx, ddy = tx - gx0, ty - gy0
        # eject: along-axis leading edge = far edge +/-9 (2/3 obs; #91 was
        # closer — glyph overlapped when eating, unexplained); cross-axis
        # aligned to eaten piece's TOP/LEFT edge (3/3 obs)
        # TRAILING edge of the spawn at far_edge +/- 9 (3/4 obs; overlap-eat
        # wobble -1 documented on #90)
        if abs(ddx) >= abs(ddy):
            if ddx >= 0:
                x0 = max(xs) + 9              # obs #49
            else:
                x0 = min(xs) - 9 - (ns - 1)   # obs #65
            y0 = min(ys)
        else:
            if ddy >= 0:
                y0 = max(ys) + 9 - (ns - 1)   # obs #94 (#90 wobble -1)
            else:
                y0 = min(ys) - 9
            x0 = min(xs)
        # anchor from top-left (x0,y0)
        lo, hi = _span(ns)
        ex, ey = x0 - lo, y0 - lo
        if nt >= 5:
            _PIECE_SIZE[(nt, ex, ey)] = ns
        col = TIER_COLOR[nt]
        for (cx, cy) in _cells(ex, ey, nt):
            if 0 <= cx <= 63 and 10 <= cy <= 62:
                g[cy][cx] = col
    # failure recolor: units short of requirement
    feats = _entry_features()
    units = sum(2 ** (p[0] - 1) for p in _find_pieces(g))
    need = sum(2 ** (ht - 1) for ht in feats['hud_tiers'])
    if units < need:
        for y in range(10, 63):
            for x in range(64):
                if g[y][x] == 9:
                    g[y][x] = 2
        for y in range(0, 10):
            for x in range(17, 64):
                if g[y][x] in TIER_COLOR.values():
                    g[y][x] = 2

def is_goal(grid):
    """WIN when each destination disk's BBOX is OVERLAPPED by a distinct
    required item: HUD tier pieces, plus a glyph if the HUD shows the glyph
    icon (confirmed L4: b overlapping disk edge won; L0 core=ring interior)."""
    feats = _entry_features()
    boxes = feats['dest_boxes']
    items = list(feats['hud_tiers'])
    if feats.get('glyph_hud'):
        items.append('glyph')
    if not boxes or not items or len(items) != len(boxes):
        return False
    pieces = _find_pieces(grid)
    glyphs = _glyphs(grid)
    def overlaps(cellset, box):
        x0, x1, y0, y1 = box
        return any(x0 <= cx <= x1 and y0 <= cy <= y1 for (cx, cy) in cellset)
    # try all assignments of items to boxes (small: <=2-3 boxes)
    import itertools as _it
    for perm in _it.permutations(range(len(boxes))):
        used_p = set(); used_g = set()
        ok = True
        for item, bi in zip(items, perm):
            box = boxes[bi]
            found = False
            if item == 'glyph':
                for i, gc in enumerate(glyphs):
                    if i not in used_g and overlaps(gc, box):
                        used_g.add(i); found = True; break
            else:
                for i, (t, ax, ay) in enumerate(pieces):
                    if i not in used_p and t == item and \
                       overlaps(_cells(ax, ay, t), box):
                        used_p.add(i); found = True; break
            if not found:
                ok = False
                break
        if ok:
            return True
    return False
