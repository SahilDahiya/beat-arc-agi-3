# su15 world model v2 — general "magnet + merge-chain" engine
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

TIER_COLOR = {1: 10, 2: 6, 3: 15, 4: 11}
COLOR_TIER = {10: 1, 6: 2, 15: 3, 11: 4}

def _span(s):
    lo = -(s // 2)
    return lo, lo + s - 1

def _cells(ax, ay, s):
    lo, hi = _span(s)
    return [(ax+dx, ay+dy) for dy in range(lo, hi+1) for dx in range(lo, hi+1)]

def _find_pieces(g):
    """Return list of (tier, ax, ay). Scan play area rows 10..62."""
    pieces = []
    seen = set()
    for y in range(10, 63):
        for x in range(64):
            if (x, y) in seen:
                continue
            v = g[y][x]
            t = COLOR_TIER.get(v)
            if t is None:
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
                dests.append(((min(xs)+max(xs))//2, (min(ys)+max(ys))//2))
    dests.sort()
    feats['dests'] = dests
    # goal tiers: pieces shown in the HUD band (rows 0-9, x>=17), left-to-right
    hud = []
    seenh = set()
    for x in range(17, 64):
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
    return feats

def _underlay(x, y):
    eg = ENTRY_GRID
    f = _entry_features()
    for (t, ax, ay) in f['entry_pieces']:
        lo, hi = _span(t)
        if ax+lo <= x <= ax+hi and ay+lo <= y <= ay+hi:
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
    N = {0: 32, 1: 32, 2: 48, 3: 48, 4: 32}.get(CURRENT_LEVEL, 48)
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
        else:
            nt = t + 1  # merge
            if nt > 4:
                nt = 4  # cap (unknown)
        col = TIER_COLOR[nt]
        for (cx, cy) in _cells(x, y, nt):
            if 0 <= cx <= 63 and 10 <= cy <= 62:
                g[cy][cx] = col
    for (gcells, gtarget) in pre_glyphs:
        _move_glyph(g, gcells, gtarget)
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
def _move_glyph(g, cells, pre_target):
    """One glyph's post-click step (see notes; all thresholds cell-based)."""
    cells = [(x, y) for (x, y) in cells if g[y][x] == 7]
    if not cells:
        return
    gx, gy = _center_of(cells)
    pieces = _find_pieces(g)
    if pre_target is not None and pre_target not in pieces and any(
            abs(p[1] - pre_target[1]) <= 4 and abs(p[2] - pre_target[2]) <= 4
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
            # close: careful half-step toward the piece's cell centroid
            n = len(cells)
            cgx = sum(c[0] for c in cells) / n
            cgy = sum(c[1] for c in cells) / n
            pcx = sum(c[0] for c in pc) / len(pc)
            pcy = sum(c[1] for c in pc) / len(pc)
            import math as _m
            mvx = int(_m.floor((pcx - cgx) / 2.0 + 0.5))
            mvy = int(_m.floor((pcy - cgy) / 2.0 + 0.5))
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
        fx, fy = max(pc, key=lambda c: (c[0]-gx0)**2 + (c[1]-gy0)**2)
        ddx, ddy = tx - gx0, ty - gy0
        if abs(ddx) >= abs(ddy):
            sx, sy = (9 if ddx >= 0 else -9), 0
        else:
            sx, sy = 0, (9 if ddy >= 0 else -9)
        nt = t - 1
        lo, hi = _span(nt)
        # spawned piece's TOP-RIGHT cell sits at far_cell + 9*dir
        ex, ey = fx + sx - hi, fy + sy - lo
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
    """All destinations hold a goal-tier piece; multiset matches HUD pieces."""
    feats = _entry_features()
    if not feats['dests'] or not feats['hud_tiers']:
        return False
    pieces = {(ax, ay): t for (t, ax, ay) in _find_pieces(grid)}
    got = []
    for d in feats['dests']:
        if d not in pieces:
            return False
        got.append(pieces[d])
    return sorted(got) == sorted(feats['hud_tiers'])
