# World model v3 — "pour into cups" game
# Confirmed:
#  - 9-bar (player) moves 4px: 1=up,2=down,3=left,4=right.
#  - Row0 budget bar: cumulative drained after n actions = floor(16n/7) (28-action budget).
#  - Action 5 = pour: stream (color 6) falls from dispenser column; if it reaches floor -> fail flash,
#    grid restored (net: only budget drain).
# Hypothesis: if stream hits the 9-bar, water runs along the bar and falls off both ends
#  (in the 4px columns just OUTSIDE the bar). If both falling columns land inside cup
#  interiors -> cups filled -> level_up.

def _bbox(grid, col):
    cells = [(yy, xx) for yy, row in enumerate(grid) for xx, v in enumerate(row) if v == col]
    if not cells:
        return None
    ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
    return min(ys), max(ys), min(xs), max(xs)

def _dispenser(entry):
    # 6-colored block in the top rows = spout; its x-range are the stream columns
    cells = [(yy, xx) for yy in range(0, 12) for xx in range(64) if entry[yy][xx] == 6]
    ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
    return min(xs), max(xs), max(ys) + 1  # x0, x1, stream starts below spout

def _cup_interiors(entry):
    # cups are color 11 U-shapes; interior = background column between the two legs
    # find connected-ish cup bboxes by scanning color 11 columns
    cells = [(yy, xx) for yy, row in enumerate(entry) for xx, v in enumerate(row) if v == 11]
    if not cells:
        return []
    # group by x-clusters
    xs = sorted(set(c[1] for c in cells))
    groups = []
    cur = [xs[0]]
    for a in xs[1:]:
        if a - cur[-1] <= 1:
            cur.append(a)
        else:
            groups.append(cur); cur = [a]
    groups.append(cur)
    outs = []
    for gxs in groups:
        gx0, gx1 = min(gxs), max(gxs)
        gys = [c[0] for c in cells if gx0 <= c[1] <= gx1]
        gy0, gy1 = min(gys), max(gys)
        # interior columns: x in [gx0,gx1] where top row of cup (gy0) is NOT 11
        icols = [x for x in range(gx0, gx1 + 1) if entry[gy0][x] != 11]
        if icols:
            outs.append((min(icols), max(icols), gy0))  # interior x-range, cup top y
    return outs

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}

    dy, dx = 0, 0
    if action == 1: dy = -4
    elif action == 2: dy = 4
    elif action == 3: dx = -4
    elif action == 4: dx = 4

    bb = _bbox(grid, 9)
    if bb and (dy or dx):
        y0, y1, x0, x1 = bb
        ny0, ny1, nx0, nx1 = y0 + dy, y1 + dy, x0 + dx, x1 + dx
        if 0 <= nx0 and nx1 <= 63 and 1 <= ny0 and ny1 <= 59:
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    g[yy][xx] = 12
            for yy in range(ny0, ny1 + 1):
                for xx in range(nx0, nx1 + 1):
                    g[yy][xx] = 9

    if action == 5 and bb:
        sx0, sx1, sy = _dispenser(ENTRY_GRID)
        y0, y1, x0, x1 = bb
        hit_bar = (x0 <= sx1 and x1 >= sx0) and y0 >= sy
        if hit_bar:
            # water falls off both ends just outside the bar: columns [x0-4,x0-1] and [x1+1,x1+4]
            falls = [(x0 - 4, x0 - 1), (x1 + 1, x1 + 4)]
            interiors = _cup_interiors(ENTRY_GRID)
            filled = set()
            for (fx0, fx1) in falls:
                for i, (ix0, ix1, iy) in enumerate(interiors):
                    if fx0 == ix0 and fx1 == ix1 and y1 < iy:
                        filled.add(i)
            if len(interiors) > 0 and len(filled) == len(interiors):
                info["level_up"] = True
        # failure: grid unchanged apart from budget drain

    # budget drain: cumulative drained after n actions = round(64n/30) (30-action budget)
    d = sum(1 for v in grid[0] if v == 0)
    n = int(15 * d / 32 + 0.5)
    nd = min(int(64 * (n + 1) / 30 + 0.5), 64)
    for i in range(64):
        g[0][i] = 0 if i >= 64 - nd else 14
    if nd >= 64:
        info["dead"] = True  # guess

    return g, info
