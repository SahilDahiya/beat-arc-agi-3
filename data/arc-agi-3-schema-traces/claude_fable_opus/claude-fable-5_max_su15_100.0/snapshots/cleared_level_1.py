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
    core = None
    for y in range(10, 61):
        for x in range(0, 62):
            if all(eg[y+dy][x+dx] == 3 for dy in range(3) for dx in range(3)):
                if y-1 >= 10 and eg[y-1][x+1] == 9 and eg[y+3][x+1] == 9:
                    core = (x+1, y+1)
    feats['core'] = core
    # destination: core center if marked, else center of the 9-disk bbox
    nine = [(x, y) for y in range(10, 63) for x in range(64) if eg[y][x] == 9]
    if core is not None:
        feats['dest'] = core
    elif nine:
        xs = [c[0] for c in nine]; ys = [c[1] for c in nine]
        feats['dest'] = ((min(xs)+max(xs))//2, (min(ys)+max(ys))//2)
    else:
        feats['dest'] = None
    # goal tier: the piece shown in the HUD slot (band rows 0-9, x>=17)
    hud = None
    for y in range(0, 10):
        for x in range(17, 64):
            t = COLOR_TIER.get(eg[y][x])
            if t is not None:
                hud = t
    feats['hud_tier'] = hud
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
    return eg[y][x]

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6:
        return g, info
    if y is None or y <= 9:
        return g, info
    # pay budget
    paid = 0
    for bx in range(63, -1, -1):
        if paid >= 2:
            break
        if g[63][bx] == 0:
            g[63][bx] = 5
            paid += 1
    if y == 63:
        return g, info  # untested; assume no piece interaction
    pieces = _find_pieces(g)
    feats = _entry_features()
    # attracted pieces per tier
    from collections import defaultdict
    att = defaultdict(list)
    for (t, ax, ay) in pieces:
        if (ax - x)**2 + (ay - y)**2 <= 81:
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
        if nt == feats['hud_tier'] and (x, y) == feats['dest']:
            info["level_up"] = True  # goal: HUD-tier piece anchored at destination
    return g, info

def is_goal(grid):
    feats = _entry_features()
    pieces = _find_pieces(grid)
    return any(t == feats['hud_tier'] and (ax, ay) == feats['dest']
               for (t, ax, ay) in pieces)
