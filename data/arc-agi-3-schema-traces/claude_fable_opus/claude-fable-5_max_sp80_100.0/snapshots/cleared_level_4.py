# World model v8 — "pour into cups", cell-size parameterized, pieces as cell-sets
# CONFIRMED MECHANICS (levels 0-2):
#  - Pieces (8=unselected, 9=selected) move by CELL px with arrows (1=up,2=down,3=left,4=right);
#    blocked by non-bg and by orthogonal adjacency to cup(11) cells. Click (6) selects piece.
#  - CELL = spout width (4 in lvl0-2, 3 in lvl3).
#  - Budget row (all-14 at entry): drained(n)=round(64n/N); N per level {0:30,1:45,2:100};
#    n tracked in state, grid-calibrated. Drain side: right if water falls, left if rises (obs so far).
#  - POUR (5): all spouts stream at once. Column flows away from 4-tank; on obstacle: CELL-row layer
#    on incoming side spreading ≤1 CELL beyond run ends (blocked by obstacles in band, clipped at
#    board edge = pooling, no stray); each layer cell-block whose obstacle-row cells are bg continues.
#    Interior column reaching cup base -> fill. Floor(1)/budget/off-board -> stray.
#    SUCCESS = all cups filled AND zero strays -> level_up. Else FULL RESTORE (+drain) and the piece
#    first hit by a stream becomes selected.
#  - Piece C (lvl3) has a color-4 middle segment: semantics UNKNOWN, treated as solid for now.

BG = 12

def _budget_row(entry):
    for r in (0, 63):
        if all(v in (14, 0) for v in entry[r]):
            return r
    return 0

def _clusters_1d(xs):
    xs = sorted(set(xs))
    groups = []
    cur = [xs[0]]
    for a in xs[1:]:
        if a - cur[-1] <= 1:
            cur.append(a)
        else:
            groups.append((min(cur), max(cur))); cur = [a]
    groups.append((min(cur), max(cur)))
    return groups

def _dispensers(entry):
    """List of (sx0, sx1, start_y, dirn) — one per 6-spout; also returns tank(4) cells."""
    cells6 = [(y, x) for y, row in enumerate(entry) for x, v in enumerate(row) if v == 6]
    cells4 = [(y, x) for y, row in enumerate(entry) for x, v in enumerate(row) if v == 4]
    out = []
    tank_cells = set()
    if not cells6:
        return out, tank_cells
    for gx0, gx1 in _clusters_1d([c[1] for c in cells6]):
        y6 = [c[0] for c in cells6 if gx0 <= c[1] <= gx1]
        # tank 4-cells sharing this x-range and vertically adjacent to the 6-block
        t4 = [c for c in cells4 if gx0 <= c[1] <= gx1]
        # only those in a contiguous column run adjacent to the 6 block
        y6a, y6b = min(y6), max(y6)
        t4v = [c for c in t4 if c[0] == y6a - 1 or c[0] == y6b + 1]
        grow = set(t4v)
        changed = True
        allt4 = set(t4)
        while changed:
            changed = False
            for c in list(allt4 - grow):
                if any((c[0] + d, c[1]) in grow for d in (-1, 1)):
                    grow.add(c); changed = True
        if not grow:
            dirn = 1
        else:
            ty = [c[0] for c in grow]
            dirn = 1 if (y6a + y6b) > (min(ty) + max(ty)) else -1
        start = y6b + 1 if dirn == 1 else y6a - 1
        out.append((gx0, gx1, start, dirn))
        tank_cells |= grow
    return out, tank_cells

def _cell_size(entry):
    ds, _ = _dispensers(entry)
    if ds:
        return ds[0][1] - ds[0][0] + 1
    return 4

def _components(entry):
    """Pieces: connected components over {8,9,15,4} minus dispenser tank cells.
    kind = unselected color: 8 normal, 15 redirector (f)."""
    _, tank = _dispensers(entry)
    ok = lambda y, x: entry[y][x] in (8, 9, 15, 4) and (y, x) not in tank
    seen = [[False] * 64 for _ in range(64)]
    out = []
    for y in range(64):
        for x in range(64):
            if not seen[y][x] and ok(y, x):
                stack = [(y, x)]
                seen[y][x] = True
                cells = []
                while stack:
                    cy, cx = stack.pop()
                    cells.append((cy, cx))
                    for ny, nx in ((cy+1,cx),(cy-1,cx),(cy,cx+1),(cy,cx-1)):
                        if 0 <= ny < 64 and 0 <= nx < 64 and not seen[ny][nx] and ok(ny, nx):
                            seen[ny][nx] = True
                            stack.append((ny, nx))
                body = frozenset((cy, cx) for (cy, cx) in cells if entry[cy][cx] in (8, 9, 15))
                spec = frozenset((cy, cx) for (cy, cx) in cells if entry[cy][cx] == 4)
                kind = 15 if any(entry[cy][cx] == 15 for (cy, cx) in cells) else 8
                sel = any(entry[cy][cx] == 9 for (cy, cx) in cells)
                out.append({"body": body, "spec": spec, "sel": sel, "kind": kind})
    return out

def init_state(entry):
    if entry is None:
        return {"pieces": [], "sel": 0, "n": 0}
    comps = _components(entry)
    sel = 0
    for i, p in enumerate(comps):
        if p["sel"]:
            sel = i
    return {"pieces": [(sorted(p["body"]), sorted(p["spec"]), p["kind"]) for p in comps],
            "sel": sel, "n": 0}

def _cups(entry, dirn):
    cells = [(y, x) for y, row in enumerate(entry) for x, v in enumerate(row) if v == 11]
    if not cells:
        return []
    cups = []
    for gx0, gx1 in _clusters_1d([c[1] for c in cells]):
        gys = [c[0] for c in cells if gx0 <= c[1] <= gx1]
        gy0, gy1 = min(gys), max(gys)
        open_row = gy0 if dirn == 1 else gy1
        icols = [x for x in range(gx0, gx1 + 1) if entry[open_row][x] != 11]
        if icols:
            cups.append({"bbox": (gy0, gy1, gx0, gx1), "ix0": min(icols), "ix1": max(icols)})
        else:
            # side-opening cup (opening faces left/right); interior = bg cells inside bbox
            cups.append({"bbox": (gy0, gy1, gx0, gx1), "ix0": -99, "ix1": -99})
    return cups

def _simulate_pour(grid, entry, fpieces=None):
    fpieces = [set(fp) for fp in (fpieces or [])]
    ds, _tank = _dispensers(entry)
    CELL = _cell_size(entry)
    dirn = ds[0][3]
    cups = _cups(entry, dirn)
    reached = set()
    strays = 0
    first_hit = None
    queue = [(sx0, sx1, sy) for (sx0, sx1, sy, _d) in ds]
    stream_starts = {(sx0, sx1): sy for (sx0, sx1, sy, _d) in ds}
    # piece-embedded 4-segments are mini-dispensers: emit a stream in gravity dir from the piece
    hole_seen = set()
    for yy in range(64):
        for xx in range(64):
            if grid[yy][xx] == 4 and (yy, xx) not in _tank and (yy, xx) not in hole_seen:
                # cluster this hole (contiguous 4s not in tank)
                stack = [(yy, xx)]
                hole_seen.add((yy, xx))
                cells = []
                while stack:
                    cy, cx = stack.pop()
                    cells.append((cy, cx))
                    for ny, nx in ((cy+1,cx),(cy-1,cx),(cy,cx+1),(cy,cx-1)):
                        if 0 <= ny < 64 and 0 <= nx < 64 and grid[ny][nx] == 4 \
                           and (ny, nx) not in _tank and (ny, nx) not in hole_seen:
                            hole_seen.add((ny, nx))
                            stack.append((ny, nx))
                hx0 = min(c[1] for c in cells); hx1 = max(c[1] for c in cells)
                hy0 = min(c[0] for c in cells); hy1 = max(c[0] for c in cells)
                # emission starts just past the piece body in flow dir: scan until bg
                ey = hy1 + 1 if dirn == 1 else hy0 - 1
                while 0 <= ey <= 63 and any(grid[ey][x] != BG for x in range(hx0, hx1 + 1)):
                    ey += dirn
                if 0 <= ey <= 63:
                    queue.append((hx0, hx1, ey))
    nstreams = len(queue)
    seen = set()
    it = 0
    while queue and it < 300:
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
        impact = set(grid[y][x] for x in range(cx0, cx1 + 1) if grid[y][x] != BG)
        if impact <= {1, 14, 0}:
            strays += 1
            continue
        if is_stream and impact & {8, 9, 4, 15}:
            y0s = stream_starts.get((cx0, cx1))
            if y0s is not None:
                d0 = abs(y - y0s)
                if first_hit is None or d0 < first_hit[0]:
                    first_hit = (d0, y, cx0)
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
        # f-redirector: column hitting a stem tip -> horizontal flow at stem rows
        hitcells = set((y, xx) for xx in range(cx0, cx1 + 1) if grid[y][xx] != BG)
        fp_hit = None
        for fp in fpieces:
            if hitcells and hitcells <= fp:
                fp_hit = fp
                break
        if fp_hit is not None:
            ys = sorted(set(cy for (cy, cx) in fp_hit))
            # stem = the CELL rows on the incoming side; bar = the other rows
            if dirn == -1:
                stem_rows = ys[-CELL:]
                bar_rows = ys[:-CELL]
            else:
                stem_rows = ys[:CELL]
                bar_rows = ys[CELL:]
            stem_cells = [(cy, cx) for (cy, cx) in fp_hit if cy in stem_rows]
            if bar_rows:  # any hit on the f-device (stem tip or bar) triggers the flow (bar-hit unverified)
                sxs = [cx for (cy, cx) in stem_cells]
                bxs = [cx for (cy, cx) in fp_hit if cy in bar_rows]
                sx0f, sx1f = min(sxs), max(sxs)
                bx0f, bx1f = min(bxs), max(bxs)
                # flow toward the bar's longer overhang
                left_over = sx0f - bx0f
                right_over = bx1f - sx1f
                step = -1 if left_over >= right_over else 1
                fx = (sx0f - 1) if step == -1 else (sx1f + 1)
                while 0 <= fx <= 63 and all(grid[r][fx] == BG for r in stem_rows):
                    fx += step
                if 0 <= fx <= 63:
                    hitcols = set(grid[r][fx] for r in stem_rows if grid[r][fx] != BG)
                    if hitcols & {11, 13}:
                        for i, cp in enumerate(cups):
                            gy0, gy1, gx0, gx1 = cp["bbox"]
                            if gx0 <= fx <= gx1 and any(gy0 <= r <= gy1 for r in stem_rows):
                                reached.add(i)
                                break
                    elif hitcols <= {1, 14, 0}:
                        strays += 1
                    # piece/other: pool, no effect
                else:
                    strays += 1
                continue
        xs_hit = [xx for xx in range(cx0, cx1 + 1) if grid[y][xx] != BG]
        ox0, ox1 = min(xs_hit), max(xs_hit)
        while ox0 - 1 >= 0 and grid[y][ox0 - 1] != BG:
            ox0 -= 1
        while ox1 + 1 <= 63 and grid[y][ox1 + 1] != BG:
            ox1 += 1
        if dirn == 1:
            band = [b for b in range(y - CELL, y) if 0 <= b <= 63]
        else:
            band = [b for b in range(y + 1, y + CELL + 1) if 0 <= b <= 63]
        def col_free(xx):
            return 0 <= xx <= 63 and all(grid[b][xx] == BG for b in band)
        # overflow blocks align to the obstacle run's ENDS (observed), spread along band
        # from the impact column outward, stopped by any non-bg band cell.
        ob0, ob1 = ox0 - CELL, ox0 - 1
        if ob0 >= 0 and all(col_free(xx) for xx in range(ob0, cx0)) \
           and all(grid[y][xx] == BG for xx in range(ob0, ob1 + 1)):
            queue.append((ob0, ob1, y))
        ob0, ob1 = ox1 + 1, ox1 + CELL
        if ob1 <= 63 and all(col_free(xx) for xx in range(cx1 + 1, ob1 + 1)) \
           and all(grid[y][xx] == BG for xx in range(ob0, ob1 + 1)):
            queue.append((ob0, ob1, y))
    return reached, strays, cups, first_hit

def _paint_piece(g, body, spec, col):
    for (yy, xx) in body:
        g[yy][xx] = col
    for (yy, xx) in spec:
        g[yy][xx] = 4

def _resync(st, grid, entry):
    """Ensure state piece cells match grid; refit by translation (polyomino cover) if drifted."""
    _, tank = _dispensers(entry)
    G = {}
    for yy in range(64):
        for xx in range(64):
            if grid[yy][xx] in (8, 9, 15, 4) and (yy, xx) not in tank:
                G[(yy, xx)] = grid[yy][xx]
    total = sum(len(b) + len(s) for (b, s, k) in st["pieces"])
    consistent = (total == len(G))
    if consistent:
        for i, (body, spec, kind) in enumerate(st["pieces"]):
            cols = set(G.get(c) for c in body)
            if not (cols <= {8, 9, 15} and len(cols) == 1):
                consistent = False
            if any(G.get(c) != 4 for c in spec):
                consistent = False
    if consistent:
        for i, (body, spec, kind) in enumerate(st["pieces"]):
            if body and G.get(tuple(body[0])) == 9:
                st["sel"] = i
        return st
    # exact cover by translated shapes
    shapes = []
    for (body, spec, kind) in st["pieces"]:
        cells = sorted(set(map(tuple, body)) | set(map(tuple, spec)))
        base = cells[0]
        rel = [(c[0] - base[0], c[1] - base[1]) for c in cells]
        brel = set((c[0] - base[0], c[1] - base[1]) for c in map(tuple, body))
        shapes.append((rel, brel))
    solutions = []
    def bt(uncov, placed, unplaced):
        if len(solutions) >= 12:
            return
        if not uncov:
            if not unplaced:
                solutions.append(dict(placed))
            return
        c0 = min(uncov)
        for i in list(unplaced):
            rel, brel = shapes[i]
            cells = [(c0[0] + r[0], c0[1] + r[1]) for r in rel]
            if all(c in uncov for c in cells):
                bcols = set(G[(c0[0] + r[0], c0[1] + r[1])] for r in rel if r in brel)
                scols = set(G[(c0[0] + r[0], c0[1] + r[1])] for r in rel if r not in brel)
                if bcols <= {8, 9, 15} and len(bcols) == 1 and scols <= {4}:
                    bt(uncov - set(cells), placed + [(i, c0)], unplaced - {i})
    bt(set(G.keys()), [], set(range(len(shapes))))
    if solutions:
        def disp(sol):
            t = 0
            for i, c0 in sol.items():
                old = min(sorted(set(map(tuple, st["pieces"][i][0])) | set(map(tuple, st["pieces"][i][1]))))
                t += abs(c0[0] - old[0]) + abs(c0[1] - old[1])
            return t
        best = min(solutions, key=disp)
        newp = []
        for i, (body, spec, kind) in enumerate(st["pieces"]):
            cells = sorted(set(map(tuple, body)) | set(map(tuple, spec)))
            base = cells[0]
            c0 = best[i]
            t = (c0[0] - base[0], c0[1] - base[1])
            nb = [(yy + t[0], xx + t[1]) for (yy, xx) in map(tuple, body)]
            nsp = [(yy + t[0], xx + t[1]) for (yy, xx) in map(tuple, spec)]
            newp.append((nb, nsp, kind))
            if nb and G.get(nb[0]) == 9:
                st["sel"] = i
        st["pieces"] = newp
    return st

def predict(state, grid, action, x=None, y=None):
    g = [list(row) for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    entry = ENTRY_GRID
    st = {"pieces": [(list(map(tuple, p[0])), list(map(tuple, p[1])), (p[2] if len(p) > 2 else 8))
                     for p in state.get("pieces", [])],
          "sel": state.get("sel", 0), "n": state.get("n", 0)}
    st = _resync(st, grid, entry)
    CELL = _cell_size(entry)

    # moves: step = CELL px in all four directions (CELL = spout width; confirmed lvl0-3)
    dy, dx = 0, 0
    if action == 1: dy = -CELL
    elif action == 2: dy = CELL
    elif action == 3: dx = -CELL
    elif action == 4: dx = CELL

    if (dy or dx) and st["pieces"]:
        i = st["sel"]
        body, spec, kind = st["pieces"][i]
        own = set(body) | set(spec)
        nbody = [(yy + dy, xx + dx) for (yy, xx) in body]
        nspec = [(yy + dy, xx + dx) for (yy, xx) in spec]
        ncells = nbody + nspec
        ok = all(0 <= yy <= 63 and 0 <= xx <= 63 for (yy, xx) in ncells)
        if ok:
            for (yy, xx) in ncells:
                v = grid[yy][xx]
                if v != BG and (yy, xx) not in own:
                    ok = False
        if ok:
            # no 8-neighbour adjacency (incl. diagonals) to cup (11) cells
            for (yy, xx) in ncells:
                for ay in (yy-1, yy, yy+1):
                    for ax in (xx-1, xx, xx+1):
                        if 0 <= ay <= 63 and 0 <= ax <= 63 and entry[ay][ax] == 11:
                            ok = False
        if ok:
            for (yy, xx) in own:
                g[yy][xx] = BG
            _paint_piece(g, nbody, nspec, 9)
            st["pieces"][i] = (nbody, nspec, kind)

    if action == 6 and x is not None and y is not None:
        hit = None
        for i, (body, spec, kind) in enumerate(st["pieces"]):
            if (y, x) in set(body) | set(spec):
                hit = i
        if hit is not None:
            st["sel"] = hit
            for i, (body, spec, kind) in enumerate(st["pieces"]):
                _paint_piece(g, body, spec, 9 if i == hit else kind)

    if action == 5:
        fpieces = [set(body) for (body, spec, kind) in st["pieces"] if kind == 15]
        reached, strays, cups, first_hit = _simulate_pour(grid, entry, fpieces)
        if cups and len(reached) == len(cups) and strays == 0:
            info["level_up"] = True
        elif first_hit is not None:
            _d0, fy, fx = first_hit
            for i, (body, spec, kind) in enumerate(st["pieces"]):
                if (fy, fx) in set(body) | set(spec):
                    st["sel"] = i
                    for j, (b2, s2, k2) in enumerate(st["pieces"]):
                        _paint_piece(g, b2, s2, 9 if j == i else k2)

    # budget drain: n tracked in state, calibrated vs grid when unambiguous
    br = _budget_row(entry)
    ds, _ = _dispensers(entry)
    dirn = ds[0][3] if ds else 1
    N = {0: 30, 1: 45, 2: 100, 3: 120, 4: 100}.get(CURRENT_LEVEL, 100)
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
