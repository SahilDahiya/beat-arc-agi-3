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
    N = {0: 32, 1: 32, 2: 48}.get(CURRENT_LEVEL, 48)
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
    pre_target = _glyph_target(g)
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
    _move_glyph(g, pre_target)
    if is_goal(g):
        info["level_up"] = True
    return g, info

def _glyph_center(g):
    cells = [(x, y) for y in range(10, 63) for x in range(64) if g[y][x] == 7]
    if not cells:
        return None, None
    n = len(cells)
    gx = int(sum(c[0] for c in cells) / n + 0.5)
    gy = int(sum(c[1] for c in cells) / n + 0.5)
    return (gx, gy), cells

def _glyph_target(g):
    """(tier, ax, ay) of the glyph's current target = nearest piece."""
    (c, cells) = _glyph_center(g)
    if c is None:
        return None
    pieces = _find_pieces(g)
    if not pieces:
        return None
    gx, gy = c
    return min(pieces, key=lambda p: (p[1]-gx)**2 + (p[2]-gy)**2)

# --- 7-glyph: autonomous walker; steps once per paid click ---
def _move_glyph(g, pre_target):
    """7-glyph chaser (post-click step):
    - DASH: if its pre-click target was consumed by the click, teleport to
      the MIRROR point through the target: new_center = 2*T - C (no clamp).
      [observed: C(42,29), T=a(36,29) merged -> C'=(30,29)]
    - else NORMAL: step (clamp(dx,+-4), clamp(dy,+-4)) toward nearest piece;
      if it lands exactly ON that anchor: piece EATEN (guess, untested)."""
    (c, cells) = _glyph_center(g)
    if c is None:
        return
    gx, gy = c
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
    else:
        if not pieces:
            return
        t, tx, ty = min(pieces, key=lambda p: (p[1]-gx)**2 + (p[2]-gy)**2)
        # eat thresholds measured to piece's NEAREST CELL (like pulls!);
        # step direction toward ANCHOR (that's what matched history)
        def cell_delta(cgx, cgy):
            pc = _cells(tx, ty, t)
            best = min(pc, key=lambda c: (c[0]-cgx)**2 + (c[1]-cgy)**2)
            return best[0] - cgx, best[1] - cgy
        cdx, cdy = cell_delta(gx, gy)
        dx, dy = tx - gx, ty - gy
        if abs(cdx) <= 4 and abs(cdy) <= 4:
            _eat(g, cells, (t, tx, ty), half_step=True)
            return
        mvx = max(-4, min(4, dx))
        mvy = max(-4, min(4, dy))
        pdx, pdy = cell_delta(gx + mvx, gy + mvy)
        if abs(pdx) <= 2 and abs(pdy) <= 2:
            # lands with a piece CELL within (2,2): full step, then eat
            new = [(x + mvx, y + mvy) for (x, y) in cells]
            if all(0 <= x <= 63 and 10 <= y <= 62 for (x, y) in new):
                for (x, y) in cells:
                    g[y][x] = _underlay(x, y)
                for (x, y) in new:
                    g[y][x] = 7
                cells = new
            _eat(g, cells, (t, tx, ty), half_step=False)
            return
        eaten = None
    if (mvx, mvy) == (0, 0):
        return
    new = [(x + mvx, y + mvy) for (x, y) in cells]
    if any(not (0 <= x <= 63 and 10 <= y <= 62) for (x, y) in new):
        return  # would exit play area: freeze (guess)
    for (x, y) in cells:
        g[y][x] = _underlay(x, y)
    if eaten is not None:
        et, ex, ey = eaten
        for (cx, cy) in _cells(ex, ey, et):
            if 0 <= cx <= 63 and 10 <= cy <= 62:
                g[cy][cx] = _underlay(cx, cy)
    for (x, y) in new:
        g[y][x] = 7

def _eat(g, cells, target, half_step):
    """Glyph eats a piece:
    - half_step=True (target already within (4,4) pre-step): glyph moves
      round_half_away((piece_cellcentroid - glyph_centroid)/2) then eats.
    - half_step=False: caller already moved the glyph; just eat.
    - piece removed; a piece one tier LOWER spawns at the piece's farthest
      cell from the glyph, +9 along the dominant approach axis (observed:
      6@(33,28) -> a@(42,27), glyph (30,29)->(31,28))
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
    if half_step:
        pcx = sum(c[0] for c in pc) / len(pc)
        pcy = sum(c[1] for c in pc) / len(pc)
        hx, hy = (pcx - cgx) / 2.0, (pcy - cgy) / 2.0
        import math
        mvx, mvy = int(math.floor(hx + 0.5)), int(math.floor(hy + 0.5))
        new = [(x + mvx, y + mvy) for (x, y) in cells]
        if all(0 <= x <= 63 and 10 <= y <= 62 for (x, y) in new):
            for (x, y) in cells:
                g[y][x] = _underlay(x, y)
            for (x, y) in new:
                g[y][x] = 7
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
