# World model v6 — "pour into cups" with STATEFUL piece tracking
# Pieces (movable deflectors) are persistent objects: color 9 = selected, 8 = unselected.
# Adjacent pieces can touch — connectivity can't identify them → track positions in state.
# CONFIRMED:
#  - Arrows 1=up 2=down 3=left 4=right move SELECTED piece 4px; blocked by any non-bg cells.
#  - Click (action 6) on a piece selects it (turns 9, all others 8). Click elsewhere: no change.
#  - Budget row (all-14 at entry): drained(n)=round(64n/N); lvl0 N=30 drains right, lvl1 N=43 drains left.
#  - Pour (5): stream from 6-spout away from 4-block; obstacle -> 4-row layer on incoming side,
#    spreads to 1 block beyond run ends (blocked by obstacles in layer band); free layer blocks
#    continue past obstacle row. Cup interior + base hit -> fill. Floor/off-board -> stray.
#    ALL cups filled in one pour -> level_up; otherwise FULL RESTORE (only drain persists).

BG = 12

def _budget_row(entry):
    for r in (0, 63):
        if all(v in (14, 0) for v in entry[r]):
            return r
    return 0

def _color_bbox(g, col):
    cells = [(y, x) for y, row in enumerate(g) for x, v in enumerate(row) if v == col]
    if not cells:
        return None
    ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
    return min(ys), max(ys), min(xs), max(xs)

def _components(entry):
    seen = [[False] * 64 for _ in range(64)]
    out = []
    for y in range(64):
        for x in range(64):
            if not seen[y][x] and entry[y][x] in (8, 9):
                stack = [(y, x)]
                seen[y][x] = True
                cells = []
                while stack:
                    cy, cx = stack.pop()
                    cells.append((cy, cx))
                    for ny, nx in ((cy+1,cx),(cy-1,cx),(cy,cx+1),(cy,cx-1)):
                        if 0 <= ny < 64 and 0 <= nx < 64 and not seen[ny][nx] and entry[ny][nx] in (8, 9):
                            seen[ny][nx] = True
                            stack.append((ny, nx))
                ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
                out.append({"y0": min(ys), "y1": max(ys), "x0": min(xs), "x1": max(xs),
                            "color": entry[cells[0][0]][cells[0][1]]})
    return out

def init_state(entry):
    if entry is None:
        return {"pieces": [], "sel": 0, "n": 0}
    pieces = _components(entry)
    sel = 0
    for i, p in enumerate(pieces):
        if p["color"] == 9:
            sel = i
    return {"pieces": [(p["y0"], p["y1"], p["x0"], p["x1"]) for p in pieces], "sel": sel, "n": 0}

def _dispensers(entry):
    """List of (sx0, sx1, start_y, dirn) — one per 6-spout (cluster 6-cells by x)."""
    cells6 = [(y, x) for y, row in enumerate(entry) for x, v in enumerate(row) if v == 6]
    cells4 = [(y, x) for y, row in enumerate(entry) for x, v in enumerate(row) if v == 4]
    if not cells6:
        return []
    xs = sorted(set(c[1] for c in cells6))
    groups = []
    cur = [xs[0]]
    for a in xs[1:]:
        if a - cur[-1] <= 1:
            cur.append(a)
        else:
            groups.append((min(cur), max(cur))); cur = [a]
    groups.append((min(cur), max(cur)))
    out = []
    for gx0, gx1 in groups:
        y6 = [c[0] for c in cells6 if gx0 <= c[1] <= gx1]
        y4 = [c[0] for c in cells4 if gx0 <= c[1] <= gx1]
        if not y4:
            dirn = 1
        else:
            dirn = 1 if (min(y6) + max(y6)) > (min(y4) + max(y4)) else -1
        start = max(y6) + 1 if dirn == 1 else min(y6) - 1
        out.append((gx0, gx1, start, dirn))
    return out

def _dispenser(entry):
    # legacy single-dispenser view (first one) — used for gravity/budget side
    ds = _dispensers(entry)
    return ds[0]

def _cups(entry, dirn):
    cells = [(y, x) for y, row in enumerate(entry) for x, v in enumerate(row) if v == 11]
    if not cells:
        return []
    xs = sorted(set(c[1] for c in cells))
    groups = []
    cur = [xs[0]]
    for a in xs[1:]:
        if a - cur[-1] <= 1:
            cur.append(a)
        else:
            groups.append((min(cur), max(cur))); cur = [a]
    groups.append((min(cur), max(cur)))
    cups = []
    for gx0, gx1 in groups:
        gys = [c[0] for c in cells if gx0 <= c[1] <= gx1]
        gy0, gy1 = min(gys), max(gys)
        open_row = gy0 if dirn == 1 else gy1
        icols = [x for x in range(gx0, gx1 + 1) if entry[open_row][x] != 11]
        cups.append({"bbox": (gy0, gy1, gx0, gx1), "ix0": min(icols), "ix1": max(icols)})
    return cups

def _simulate_pour(grid, entry):
    ds = _dispensers(entry)
    dirn = ds[0][3]
    cups = _cups(entry, dirn)
    reached = set()
    strays = 0
    first_hit = None  # (y,x) of first impact of an initial stream, if piece
    queue = [(sx0, sx1, sy) for (sx0, sx1, sy, _d) in ds]
    nstreams = len(queue)
    seen = set()
    it = 0
    while queue and it < 200:
        it += 1
        cx0, cx1, y = queue.pop(0)
        if (cx0, cx1, y) in seen:
            continue
        seen.add((cx0, cx1, y))
        is_stream = (it <= nstreams)
        if cx0 < 0 or cx1 > 63:
            strays += 1
            continue
        while 0 <= y <= 63 and all(grid[y][x] == BG for x in range(cx0, cx1 + 1)):
            y += dirn
        if not (0 <= y <= 63):
            strays += 1
            continue
        if is_stream and first_hit is None and grid[y][cx0] in (8, 9):
            first_hit = (y, cx0)
        impact = set(grid[y][x] for x in range(cx0, cx1 + 1) if grid[y][x] != BG)
        if impact <= {1, 14, 0}:
            strays += 1
            continue
        incup = False
        for i, cp in enumerate(cups):
            if cx0 >= cp["ix0"] and cx1 <= cp["ix1"]:
                gy0, gy1, gx0, gx1 = cp["bbox"]
                if gy0 <= y <= gy1:
                    reached.add(i)
                    incup = True
                    break
        if incup:
            continue
        ox0 = cx0
        while ox0 - 1 >= 0 and grid[y][ox0 - 1] != BG:
            ox0 -= 1
        ox1 = cx1
        while ox1 + 1 <= 63 and grid[y][ox1 + 1] != BG:
            ox1 += 1
        if dirn == 1:
            band = [b for b in range(y - 4, y) if 0 <= b <= 63]
        else:
            band = [b for b in range(y + 1, y + 5) if 0 <= b <= 63]
        def block_free(bx0):
            bx1 = bx0 + 3
            if bx0 < 0 or bx1 > 63:
                return False
            return all(grid[b][x] == BG for b in band for x in range(bx0, bx1 + 1))
        blocks = []
        b = cx0
        while b >= ox0 - 4 and block_free(b):
            blocks.append(b); b -= 4
        b = cx0 + 4
        while b <= ox1 + 1 and block_free(b):
            blocks.append(b); b += 4
        for bx0 in blocks:
            if all(grid[y][x] == BG for x in range(bx0, bx0 + 4)):
                queue.append((bx0, bx0 + 3, y))
    return reached, strays, cups, first_hit

def _resync(st, grid):
    """Ensure state piece rects match the grid's 8/9 cells; refit if drifted."""
    cells = set()
    nines = set()
    for yy in range(64):
        for xx in range(64):
            if grid[yy][xx] in (8, 9):
                cells.add((yy, xx))
                if grid[yy][xx] == 9:
                    nines.add((yy, xx))
    total = 0
    ok = True
    for (y0, y1, x0, x1) in st["pieces"]:
        total += (y1 - y0 + 1) * (x1 - x0 + 1)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                if (yy, xx) not in cells:
                    ok = False
    if ok and total == len(cells):
        # also refresh sel from colors if unambiguous
        for i, (y0, y1, x0, x1) in enumerate(st["pieces"]):
            if (y0, x0) in nines:
                st["sel"] = i
        return st
    sizes = [(y1 - y0 + 1, x1 - x0 + 1) for (y0, y1, x0, x1) in st["pieces"]]
    solutions = []
    def corners(rem):
        return [(y, x) for (y, x) in rem if (y - 1, x) not in rem and (y, x - 1) not in rem]
    def bt(i, rem, placed):
        if len(solutions) >= 20:
            return
        if i == len(sizes):
            if not rem:
                solutions.append(list(placed))
            return
        h, w = sizes[i]
        for (yy, xx) in corners(rem):
            rect = [(a, b) for a in range(yy, yy + h) for b in range(xx, xx + w)]
            if all(c in rem for c in rect):
                bt(i + 1, rem - set(rect), placed + [(yy, yy + h - 1, xx, xx + w - 1)])
    bt(0, cells, [])
    if solutions:
        def disp(sol):
            return sum(abs(sol[i][0] - st["pieces"][i][0]) + abs(sol[i][2] - st["pieces"][i][2])
                       for i in range(len(sol)))
        best = min(solutions, key=disp)
        st["pieces"] = [tuple(r) for r in best]
        for i, (y0, y1, x0, x1) in enumerate(st["pieces"]):
            if (y0, x0) in nines:
                st["sel"] = i
    return st

def predict(state, grid, action, x=None, y=None):
    g = [list(row) for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    entry = ENTRY_GRID
    st = {"pieces": [tuple(p) for p in state.get("pieces", [])], "sel": state.get("sel", 0),
          "n": state.get("n", 0)}
    st = _resync(st, grid)

    dy, dx = 0, 0
    if action == 1: dy = -4
    elif action == 2: dy = 4
    elif action == 3: dx = -4
    elif action == 4: dx = 4

    if (dy or dx) and st["pieces"]:
        i = st["sel"]
        y0, y1, x0, x1 = st["pieces"][i]
        ny0, ny1, nx0, nx1 = y0 + dy, y1 + dy, x0 + dx, x1 + dx
        if 0 <= nx0 and nx1 <= 63 and 0 <= ny0 and ny1 <= 63:
            ok = True
            for yy in range(ny0, ny1 + 1):
                for xx in range(nx0, nx1 + 1):
                    v = grid[yy][xx]
                    if v != BG and not (y0 <= yy <= y1 and x0 <= xx <= x1):
                        ok = False
            # pieces may not move orthogonally adjacent to cup (11) cells
            if ok:
                for yy in range(ny0, ny1 + 1):
                    for xx in (nx0 - 1, nx1 + 1):
                        if 0 <= xx <= 63 and entry[yy][xx] == 11:
                            ok = False
                for xx in range(nx0, nx1 + 1):
                    for yy in (ny0 - 1, ny1 + 1):
                        if 0 <= yy <= 63 and entry[yy][xx] == 11:
                            ok = False
            if ok:
                col = 9
                for yy in range(y0, y1 + 1):
                    for xx in range(x0, x1 + 1):
                        g[yy][xx] = BG
                for yy in range(ny0, ny1 + 1):
                    for xx in range(nx0, nx1 + 1):
                        g[yy][xx] = col
                st["pieces"][i] = (ny0, ny1, nx0, nx1)

    if action == 6 and x is not None and y is not None:
        hit = None
        for i, (y0, y1, x0, x1) in enumerate(st["pieces"]):
            if y0 <= y <= y1 and x0 <= x <= x1:
                hit = i
        if hit is not None:
            st["sel"] = hit
            for i, (y0, y1, x0, x1) in enumerate(st["pieces"]):
                col = 9 if i == hit else 8
                for yy in range(y0, y1 + 1):
                    for xx in range(x0, x1 + 1):
                        g[yy][xx] = col

    if action == 5:
        reached, strays, cups, first_hit = _simulate_pour(grid, entry)
        if cups and len(reached) == len(cups) and strays == 0:
            # success requires ALL cups filled AND no water touching floor/off-board
            info["level_up"] = True
        elif first_hit is not None:
            # failed pour: the piece first hit by the stream becomes selected
            fy, fx = first_hit
            for i, (y0, y1, x0, x1) in enumerate(st["pieces"]):
                if y0 <= fy <= y1 and x0 <= fx <= x1:
                    st["sel"] = i
                    for j, (a0, a1, b0, b1) in enumerate(st["pieces"]):
                        col = 9 if j == i else 8
                        for yy in range(a0, a1 + 1):
                            for xx in range(b0, b1 + 1):
                                g[yy][xx] = col

    # budget drain: n tracked in state, calibrated vs grid when unambiguous
    br = _budget_row(entry)
    _, _, _, dirn = _dispenser(entry)
    N = {0: 30, 1: 45, 2: 100}.get(CURRENT_LEVEL, 100)
    d = sum(1 for v in grid[br] if v == 0)
    n = st.get("n", 0)
    cands = [m for m in range(0, N + 3) if min(int(64 * m / N + 0.5), 64) == d]
    if cands and n not in cands:
        n = min(cands, key=lambda m: abs(m - n))
    st["n"] = n + 1
    nd = min(int(64 * (n + 1) / N + 0.5), 64)
    for i in range(64):
        drained = (i >= 64 - nd) if dirn == 1 else (i < nd)
        g[br][i] = 0 if drained else 14
    if nd >= 64:
        info["dead"] = True

    return g, info, st
