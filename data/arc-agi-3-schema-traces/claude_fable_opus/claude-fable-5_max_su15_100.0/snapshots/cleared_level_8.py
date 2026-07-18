# su15 world model — magnet + merge-chain + glyph engine (v11)
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
    feats['eglyph_hud'] = any(eg[y][x] == 14 for y in range(0, 10)
                              for x in range(px, 64))
    feats['dglyph_hud'] = any(eg[y][x] == 13 for y in range(0, 10)
                              for x in range(px, 64))
    # leap mechanic is UNCONDITIONAL: #48 (L3) was a leap all along (d2=50);
    # no pre-L5 click ever landed within cell-d2<=64 otherwise (L4 min=100)
    feats['leaps_on'] = True
    return feats

def _underlay(x, y):
    eg = ENTRY_GRID
    f = _entry_features()
    for (t, ax, ay) in f['entry_pieces']:
        if (x, y) in _cells(ax, ay, t):
            return 5
    if (x, y) in f['plus_cells']:
        return 3 if (x, y) == f['plus_center'] else 5
    if eg[y][x] in (7, 13, 14):
        return 5  # glyphs are mobile, not decor
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
    N = {0: 32, 1: 32, 2: 48, 3: 48, 4: 32, 5: 32, 6: 32, 7: 48, 8: 48}.get(CURRENT_LEVEL, 32)
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
            nt = min(t + 1, 6)  # merge chain extends through tier 6
        col = TIER_COLOR[nt]
        for (cx, cy) in _cells(x, y, nt):
            if 0 <= cx <= 63 and 10 <= cy <= 62:
                g[cy][cx] = col
    # glyph interactions with the click, per color:
    # >=2 same-color glyphs in range -> MERGE to next tier at the click;
    # exactly 1 e/d-glyph in range -> PULL to the click (center=click);
    # exactly 1 7-glyph -> LEAP (handled in _move_glyph).
    merged_away = set()
    piece_cells_now = set()
    for p in _find_pieces(g):
        piece_cells_now |= set(_cells(p[1], p[2], p[0]))
    for color, nxt in ((7, 14), (14, 13), (13, None)):
        inrange = [i for i, (c0, gc, tg) in enumerate(pre_glyphs)
                   if c0 == color and gc and
                   min((cx-x)**2 + (cy-y)**2 for (cx, cy) in gc) <= 72]
        if len(inrange) >= 2 and nxt is not None:
            for i in inrange:
                merged_away.add(i)
                for (cx, cy) in pre_glyphs[i][1]:
                    if 10 <= cy <= 62 and g[cy][cx] == color:
                        g[cy][cx] = _underlay(cx, cy)
            shape = E_SHAPE if nxt == 14 else D_SHAPE
            for (dx2, dy2) in shape:
                cx, cy = x + dx2, y + dy2
                if 0 <= cx <= 63 and 10 <= cy <= 62 and \
                        (cx, cy) not in piece_cells_now:
                    g[cy][cx] = nxt
        elif len(inrange) == 1 and color in (14, 13):
            i = inrange[0]
            merged_away.add(i)
            for (cx, cy) in pre_glyphs[i][1]:
                if 10 <= cy <= 62 and g[cy][cx] == color:
                    g[cy][cx] = _underlay(cx, cy)
            shape = E_SHAPE if color == 14 else D_SHAPE
            for (dx2, dy2) in shape:
                cx, cy = x + dx2, y + dy2
                if 0 <= cx <= 63 and 10 <= cy <= 62 and \
                        (cx, cy) not in piece_cells_now:
                    g[cy][cx] = color
    for i, (gcolor, gcells, gtarget) in enumerate(pre_glyphs):
        if i in merged_away or not gcells:
            continue
        # e/d-glyphs chase like 7-glyphs when not pulled (obs #127), but
        # respond to in-range clicks by PULL (handled above), never leap
        # (leap gated on color==7 inside _move_glyph; click passed so the
        # moved-target persistence check works for e/d too — obs #145)
        _move_glyph(g, gcells, gtarget, x, y, gcolor)
    if is_goal(g):
        info["level_up"] = True
    return g, info

GLYPH_COLORS = (7, 14, 13)  # merge chain 7 -> e(14) -> d(13)
E_SHAPE = [(0, -2), (-1, -1), (1, -1), (-2, 0), (0, 0), (2, 0), (-1, 1), (1, 1)]
D_SHAPE = [(-2, -2), (0, -2), (2, -2), (-1, -1), (1, -1),
           (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1)]

def _glyphs(g, color=7):
    """Connected components of glyph-colored cells, sorted by top-left."""
    seen = set()
    comps = []
    for y in range(10, 63):
        for x in range(64):
            if g[y][x] == color and (x, y) not in seen:
                stack = [(x, y)]; comp = []
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in seen or not (0 <= cx <= 63 and 10 <= cy <= 62) \
                       or g[cy][cx] != color:
                        continue
                    seen.add((cx, cy)); comp.append((cx, cy))
                    stack += [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1),
                              (cx+1, cy+1), (cx-1, cy-1), (cx+1, cy-1), (cx-1, cy+1)]
                comps.append(sorted(comp, key=lambda c: (c[1], c[0])))
    # D-glyphs (13): the shape has gaps; partially-hidden ones FRAGMENT.
    # Re-unify: fit D_SHAPE over ALL cells of this color at once.
    if color == 13 and comps:
        allc = set()
        for comp in comps:
            allc |= set(comp)
        for (ax, ay) in sorted(allc):
            for (sx, sy) in D_SHAPE:
                cx, cy = ax - sx, ay - sy
                full = set((cx + dx, cy + dy) for (dx, dy) in D_SHAPE)
                if allc <= full:
                    return [sorted(full, key=lambda c: (c[1], c[0]))]
        return [sorted(allc, key=lambda c: (c[1], c[0]))]
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
    """List of (color, cells, target) per glyph; target=nearest piece."""
    pieces = _find_pieces(g)
    out = []
    for color in (7, 14, 13):
        for cells in _glyphs(g, color):
            if not pieces:
                out.append((color, cells, None))
                continue
            gx, gy = _center_of(cells)
            out.append((color, cells, min(pieces,
                        key=lambda p: (p[1]-gx)**2 + (p[2]-gy)**2)))
    return out

# --- 7-glyph: autonomous walker; steps once per paid click ---
def _move_glyph(g, cells, pre_target, clkx=None, clky=None, color=7):
    """One glyph's post-click step (see notes; all thresholds cell-based)."""
    pcs = set()
    for p in _find_pieces(g):
        pcs |= set(_cells(p[1], p[2], p[0]))
    cells = [(x, y) for (x, y) in cells
             if not (10 <= y <= 62) or g[y][x] == color or (x, y) in pcs]
    if not any(10 <= y <= 62 and g[y][x] == color for (x, y) in cells):
        return
    gx, gy = _center_of(cells)
    pieces = _find_pieces(g)
    # LEAP: a click within cell-d^2<=64 of the glyph makes it POUNCE toward
    # the click along the DOMINANT axis, length round(20 - |click-center|)
    # (obs: (+1,+9.1)->(0,+11); (0,+8.1)->(0,+12); (+8,0)->(+12,0))
    # ONLY when the HUD band shows the glyph icon (glyph is interactive
    # this level — L3/L4 clicks near glyphs did NOT leap).
    if clkx is not None and color == 7 and _entry_features().get('leaps_on') and \
            min((cx-clkx)**2 + (cy-clky)**2 for (cx, cy) in cells) <= 72:
        # LEAP v2: glyph's CENTER CELL lands 4 BEYOND the click along the
        # dominant axis; move length capped at 12. No eat on leap landing.
        # (5/5 exact: A 47=cap, B 58, C 34, c1 46, c2 35)
        n = len(cells)
        fgx = sum(c[0] for c in cells) / n
        fgy = sum(c[1] for c in cells) / n
        ddx, ddy = clkx - fgx, clky - fgy
        # pounce: 12 along dominant axis; +/-8 along minor axis when the
        # minor offset exceeds ~4.5 (obs #77 (+12,-8), #118 (-8,-12));
        # else 0 (10 leaps fit)
        def minor(v):
            return (8 if v >= 0 else -8) if abs(v) > 4.5 else 0
        if abs(ddx) >= abs(ddy):
            mvx, mvy = (12 if ddx >= 0 else -12), minor(ddy)
        else:
            mvx, mvy = minor(ddx), (12 if ddy >= 0 else -12)
        # leap CLAMPS at walls: body cells must stay within x0..63, y10..63
        # (row 63 allowed — body overhangs the budget row, clipped visually;
        # confirmed: down-leap stopped at center y=62, L5 up-leap at y=12)
        while (mvx, mvy) != (0, 0):
            new = [(cx + mvx, cy + mvy) for (cx, cy) in cells]
            if all(0 <= cx <= 63 and 10 <= cy <= 63 for (cx, cy) in new):
                break
            mvx -= (1 if mvx > 0 else -1 if mvx < 0 else 0)
            mvy -= (1 if mvy > 0 else -1 if mvy < 0 else 0)
        if (mvx, mvy) != (0, 0):
            new = [(cx + mvx, cy + mvy) for (cx, cy) in cells]
            for (cx, cy) in cells:
                if 10 <= cy <= 62 and g[cy][cx] == 7:
                    g[cy][cx] = _underlay(cx, cy)
            piece_cells = set()
            for p in _find_pieces(g):  # POST-click piece positions
                piece_cells |= set(_cells(p[1], p[2], p[0]))
            for (cx, cy) in new:
                if 10 <= cy <= 62 and (cx, cy) not in piece_cells:
                    g[cy][cx] = 7
        return
    # (the old "mirror dash on consumed target" rule is DEAD: #48 was a LEAP.
    # Consumed/moved targets simply retarget to the nearest piece and step.)
    # NOTE: transition #77 (L4) remains a KNOWN-UNEXPLAINED outlier: glyph
    # moved (+12,-8) after its target merged 8-away; no tried rule fits.
    if True:
        if not pieces:
            return
        if pre_target is not None and pre_target not in pieces and \
                clkx is not None and (pre_target[0], clkx, clky) in pieces and \
                (clkx - gx)**2 + (clky - gy)**2 <= 400:
            # target MOVED by this click's pull AND still within ~20:
            # keep chasing it (obs #144: d followed pulled f over nearer c;
            # obs #128: target moved 32 away -> retargeted nearest)
            t, tx, ty = pre_target[0], clkx, clky
        else:
            # nearest piece; ties break toward LARGER x (obs #105)
            t, tx, ty = min(pieces,
                            key=lambda p: ((p[1]-gx)**2 + (p[2]-gy)**2, -p[1], -p[2]))
        pc = _cells(tx, ty, t)
        # NOTE: #107 shows retarget steps may aim at the nearest CELL
        # ((-3,-4) vs anchor's (-4,-4)) but #79/#96 retargets matched
        # ANCHOR; unresolved ±1 — documented outlier family. Anchor used.
        bcx, bcy = min(pc, key=lambda c: (c[0]-gx)**2 + (c[1]-gy)**2)
        cdx, cdy = bcx - gx, bcy - gy
        dx, dy = tx - gx, ty - gy
        SPD = 8 if color == 13 else 4  # d-glyphs chase at clamp-8 (obs #144)
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
            if color == 13:
                # d-glyph = DOUBLED 7-glyph: step = 2*clamp4(round(delta/2))
                # with Python banker's rounding on halves.
                # Fits 4/4: dy +7->+8, +5->+4, -6->-6, 0->0 (#144/145/150/151)
                mvx = 2 * max(-4, min(4, round(dx / 2.0)))
                mvy = 2 * max(-4, min(4, round(dy / 2.0)))
            else:
                mvx = max(-SPD, min(SPD, dx))
                mvy = max(-SPD, min(SPD, dy))
        eaten = None
    # chase step stops at FIRST body-contact along the way (obs #110:
    # stopped at (0,-3) of a (0,-4) step when contact began)
    if (mvx, mvy) != (0, 0):
        m = max(abs(mvx), abs(mvy))
        allp = set()
        for p in pieces:
            allp |= set(_cells(p[1], p[2], p[0]))
        chosen = (mvx, mvy)
        for k in range(1, m + 1):
            ox = int(round(k * mvx / float(m)))
            oy = int(round(k * mvy / float(m)))
            body_k = set((x + ox, y + oy) for (x, y) in cells)
            if body_k & allp:
                chosen = (ox, oy)
                break
        mvx, mvy = chosen
    new = cells
    if (mvx, mvy) != (0, 0):
        cand = [(x + mvx, y + mvy) for (x, y) in cells]
        if all(0 <= x <= 63 and 10 <= y <= 63 for (x, y) in cand):
            new = cand
            for (x, y) in cells:
                if 10 <= y <= 62:
                    g[y][x] = _underlay(x, y)
            for (x, y) in new:
                if 10 <= y <= 62:
                    g[y][x] = color
    # EAT rule: glyph body cell OVERLAPS a piece cell -> that piece is eaten
    # (check against the pre-move piece list: the drawn glyph may cover cells)
    body = set(new)
    pre_body = set(cells)
    ate = False
    for p in pieces:
        pc0 = set(_cells(p[1], p[2], p[0]))
        if body & pc0:
            _eat(g, new, p, pre_overlap=bool(pre_body & pc0))
            ate = True
    if ate:
        # redraw body cells freed by the eaten piece's removal
        pcs2 = set()
        for p in _find_pieces(g):
            pcs2 |= set(_cells(p[1], p[2], p[0]))
        for (cx, cy) in new:
            if 10 <= cy <= 62 and (cx, cy) not in pcs2 and g[cy][cx] != color:
                g[cy][cx] = color

def _eat(g, cells, target, pre_overlap=False):
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
                x0 = min(xs) - 10             # obs #65 (far spawn edge min-10)
            y0 = min(ys)
        else:
            if ddy >= 0:
                y0 = max(ys) + 9 - (ns - 1)   # obs #94
            else:
                y0 = min(ys) - 10             # obs #104
            x0 = min(xs)
        # spawn rect CLAMPS to stay in-bounds (obs #140: bottom row 63 -> 62)
        x0 = max(0, min(x0, 64 - ns))
        y0 = max(10, min(y0, 63 - ns))
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
        px = 16
        for x in range(64):
            if ENTRY_GRID[0][x] == 4:
                px = x
                break
        for y in range(0, 10):
            for x in range(px, 64):
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
    if feats.get('eglyph_hud'):
        items.append('eglyph')
    if feats.get('dglyph_hud'):
        items.append('dglyph')
    if not boxes or not items or len(items) > len(boxes):
        return False
    pieces = _find_pieces(grid)
    glyphs = _glyphs(grid)
    dglyphs = _glyphs(grid, 13)
    def overlaps(cellset, box):
        x0, x1, y0, y1 = box
        return any(x0 <= cx <= x1 and y0 <= cy <= y1 for (cx, cy) in cellset)
    # try all assignments of items to boxes (small: <=2-3 boxes)
    import itertools as _it
    eglyphs = []
    seen_e = set()
    for y in range(10, 63):
        for x in range(64):
            if grid[y][x] == 14 and (x, y) not in seen_e:
                stack = [(x, y)]; comp = []
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in seen_e or not (0 <= cx <= 63 and 10 <= cy <= 62) \
                       or grid[cy][cx] != 14:
                        continue
                    seen_e.add((cx, cy)); comp.append((cx, cy))
                    stack += [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1),
                              (cx+1, cy+1), (cx-1, cy-1), (cx+1, cy-1), (cx-1, cy+1)]
                eglyphs.append(comp)
    for perm in _it.permutations(range(len(boxes)), len(items)):
        used_p = set(); used_g = set()
        ok = True
        for item, bi in zip(items, perm):
            box = boxes[bi]
            found = False
            if item == 'eglyph':
                for i, gc in enumerate(eglyphs):
                    n = len(gc)
                    cx = int(sum(c[0] for c in gc)/n + 0.5)
                    cy = int(sum(c[1] for c in gc)/n + 0.5)
                    x0, x1, y0, y1 = box
                    if x0 <= cx <= x1 and y0 <= cy <= y1:
                        found = True; break
                if not found:
                    ok = False
                if not ok:
                    break
                continue
            if item in ('glyph', 'dglyph'):
                # glyph delivery requires its CENTER inside the disk box
                # (L5: body-overlap did NOT win; center-in did)
                pool = glyphs if item == 'glyph' else dglyphs
                for i, gc in enumerate(pool):
                    cx, cy = _center_of(gc)
                    x0, x1, y0, y1 = box
                    if (item, i) not in used_g and x0 <= cx <= x1 and y0 <= cy <= y1:
                        used_g.add((item, i)); found = True; break
            else:
                # piece delivery: ANCHOR inside the disk bbox (all 6 wins
                # had anchor-in; L6 overlap-without-anchor did NOT win)
                for i, (t, ax, ay) in enumerate(pieces):
                    x0, x1, y0, y1 = box
                    if i not in used_p and t == item and \
                       x0 <= ax <= x1 and y0 <= ay <= y1:
                        used_p.add(i); found = True; break
            if not found:
                ok = False
                break
        if ok:
            return True
    return False
