# dc22 world model (predict form, stateful)
# GENERAL MECHANICS (confirmed L0+L1):
# - e(14) = 2x2 SWIMMER. 1/2/3/4 = up/down/left/right by 2 cells.
#   May enter 2x2 dest iff all 4 cells are ONE color not in {0,3,4,5,14}.
#   On move: vacated cells := carried color; carried := dest color.
#   carried starts 2 (e begins inside a 2-container).
# - Entering a uniform-11 (b) destination => LEVEL UP (confirmed L0).
# - BUTTONS (click regions) toggle their color's slot PAIRS by swapping the
#   two slots' FILL-STATES (not cells!): full = all c; half = c iff (x+y) odd
#   else 4; empty = all 4. Confirmed by L1 flask-9: 4x4-full <-> 4x8-half.
#   If a slot's state is unrecognized (e inside / debris): treat as no-op pour.
# - First pour removes right-panel 0-outlines (L0 only; harmless otherwise).
# - Row63 clock: per-level time slope! cost units: normal action = 1, effective
#   pour = 2. bar cells = ceil(cum / den) where den = CURRENT_LEVEL + 2
#   (L0: /2, L1: /3 — both confirmed exactly; den for later levels is a guess).
#   First-call calibration: cum = den*(T-1)+1 if T>0 else 0 (run-start quirk).

DIRS = {1: (0, -2), 2: (0, 2), 3: (-2, 0), 4: (2, 0)}
# t208: e blocked by the 5-strip -> 5 IS a barrier (like right-panel bg).
BLOCKED = (0, 3, 4, 5, 14)

def _buttons():
    # list of ((x0,y0,x1,y1) inclusive region, color-key)
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return [((41, 16, 55, 22), 8), ((41, 33, 55, 39), 9)]
    if lvl == 1:
        return [((46, 20, 60, 24), 6), ((46, 38, 60, 42), 9),
                ((46, 29, 58, 33), 8)]  # flask-8 appears after item-box collected
    if lvl == 2:
        return [((45, 16, 57, 20), 8), ((45, 25, 57, 29), 9),
                ((45, 34, 57, 38), 6), ((45, 43, 57, 47), 15)]  # f-flask once collected
    if lvl == 3:
        return [((47, 17, 59, 21), 6), ((43, 25, 49, 31), 11),
                ((54, 26, 59, 31), "deploy")]  # right-panel 2-block button
    return []

def _slides():
    # flask key -> list of (colors, band(y0,h), dx): the contiguous run of any
    # color in colors within the band translates by dx per click.
    # L3 quirk: when track-1's run reaches x>=18 (docked at column), BOTH runs
    # recolor 1 -> c(12). (Observed t205; semantics guessed as 'docked'.)
    lvl = CURRENT_LEVEL
    if lvl == 3:
        return {11: [((1, 12), (28, 2), 2), ((1, 12), (38, 2), 2)]}
    return {}

def _slots():
    # color-key -> list of (material, (x,y,w,h), stateA, stateB): a click FLIPS
    # every slot between its two states (skip slots matching neither).
    F, H, E = "full", "half", "empty"
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return {
            8: [(8, (12, 30, 6, 4), F, E), (8, (18, 24, 4, 6), E, F)],
            9: [(9, (18, 20, 4, 4), F, H), (9, (8, 34, 4, 4), H, F)],
        }
    if lvl == 1:
        return {
            6: [(7, (8, 40, 8, 4), F, E), (7, (16, 32, 4, 8), E, F),
                (7, (20, 40, 8, 4), F, E), (7, (16, 44, 4, 8), E, F)],
            9: [(9, (8, 28, 4, 4), F, H), (9, (4, 32, 4, 8), H, F)],
            8: [(8, (12, 24, 8, 4), F, E), (8, (20, 16, 4, 8), E, F),
                (8, (24, 24, 8, 4), F, E), (8, (20, 28, 4, 8), E, F)],
        }
    if lvl == 2:
        return {
            9: [(9, (8, 24, 4, 4), F, H), (9, (4, 20, 4, 4), H, F),
                (9, (24, 16, 4, 4), H, F), (9, (12, 40, 4, 4), H, F)],
            8: [(8, (12, 24, 8, 4), F, E), (8, (20, 16, 4, 8), E, F),   # GUESS
                (8, (24, 24, 8, 4), F, E), (8, (20, 28, 4, 8), E, F)],  # d-rotation like L1
            15: [(15, (16, 32, 4, 8), H, F),
                 (15, (24, 32, 10, 4), H, F)],  # GUESS: flask-f flips half<->full
            6: [("cellswap", (6, 16, 2, 2), (12, 46, 2, 2))],  # PORTAL: cell-wise
            # content swap of the two 6/7 duals — e RIDES it (confirmed t175)!
        }
    if lvl == 3:
        return {
            6: [("cellswap", (4, 24, 2, 2), (18, 32, 2, 2))],  # portal duals
        }
    return {}

def _item_boxes():
    # (x,y,w,h, item_color, flask_pixels) — e may enter mixed {2,item} cells
    # inside the box; on entry all item cells in the box -> 2, flask appears.
    lvl = CURRENT_LEVEL
    if lvl == 1:
        px = [(xx, yy) for yy in (29, 30, 31) for xx in range(49, 56)] + \
             [(xx, yy) for yy in (32, 33) for xx in range(46, 59)]
        return [(16, 52, 4, 4, 8, px)]
    if lvl == 2:
        px = [(xx, yy) for yy in (43, 44, 45) for xx in range(48, 55)] + \
             [(xx, yy) for yy in (46, 47) for xx in range(45, 58)]
        return [(16, 40, 4, 4, 15, px)]  # flask-f box; 6/7-mix boxes NOT encoded yet
    return []

def _divider_x():
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return 34
    return 40  # levels 1 and 2: dashes at x38-39, right panel x>=40

def init_state(entry_grid):
    return {"cum": None, "carried": 2, "tdir": 1}

def _find_player(g, color=14):
    for y in range(64):
        for x in range(64):
            if g[y][x] == color:
                return x, y
    return None

def _cells(slot):
    x0, y0, w, hh = slot
    return [(x0 + i % w, y0 + i // w) for i in range(w * hh)]

def _slot_state(g, slot, c):
    if isinstance(c, tuple) and c[0] == "dual":
        c1, c2 = c[1], c[2]
        isA = all(g[y][x] == (c1 if (x + y) % 2 == 0 else c2) for (x, y) in _cells(slot))
        isB = all(g[y][x] == (c2 if (x + y) % 2 == 0 else c1) for (x, y) in _cells(slot))
        return "A" if isA else ("B" if isB else None)
    full = empty = half = True
    for (x, y) in _cells(slot):
        v = g[y][x]
        if v != c:
            full = False
        if v != 4:
            empty = False
        if v != (c if (x + y) % 2 == 1 else 4):
            half = False
    if full:
        return "full"
    if empty:
        return "empty"
    if half:
        return "half"
    return None

def _render(g, slot, c, st):
    if isinstance(c, tuple) and c[0] == "dual":
        c1, c2 = c[1], c[2]
        for (x, y) in _cells(slot):
            even = (x + y) % 2 == 0
            g[y][x] = (c1 if even else c2) if st == "A" else (c2 if even else c1)
        return
    for (x, y) in _cells(slot):
        if st == "full":
            g[y][x] = c
        elif st == "half":
            g[y][x] = c if (x + y) % 2 == 1 else 4
        else:
            g[y][x] = 4

RECOLORED_E = [None]  # set when a recolor covered e's cells (carried update)

def _pour(g, key):
    """Flip each slot between its two states. Returns (changed, net_delta)."""
    RECOLORED_E[0] = None
    changed_any = False
    slides = _slides().get(key, [])
    if slides:
        runs = []
        any_blocked = False
        for colors, (y0, hh), dx in slides:
            cells = [(x, y) for y in range(y0, y0 + hh) for x in range(64)
                     if g[y][x] in colors]
            if not cells:
                continue
            cur = g[cells[0][1]][cells[0][0]]
            # run = full span including e-holes; e-holes stay at absolute pos
            x_lo = min(x for x, y in cells)
            x_hi = max(x for x, y in cells)
            exs = [x for y in range(y0, y0 + hh) for x in range(64) if g[y][x] == 14]
            if exs and min(exs) <= x_hi + 1 and max(exs) >= x_lo - 1:
                x_lo = min(x_lo, min(exs))
                x_hi = max(x_hi, max(exs))
            span = [(x, y) for y in range(y0, y0 + hh) for x in range(x_lo, x_hi + 1)]
            ok = all(0 <= x + dx < 64 and
                     (g[y][x + dx] in colors or g[y][x + dx] == 4 or g[y][x + dx] == 14)
                     for (x, y) in span)
            runs.append((span, cur, y0, dx, ok))
            if not ok:
                any_blocked = True
        if runs:
            if any_blocked:
                # any blocked run -> whole system RESETS to entry pos, color 1
                starts = {28: 8, 38: 4}
                for cells, cur, y0, dx, ok in runs:
                    for (x, y) in cells:
                        g[y][x] = 4
                    for yy in range(y0, y0 + 2):
                        for xx in range(starts.get(y0, 4), starts.get(y0, 4) + 6):
                            g[yy][xx] = 1
                changed_any = True
            else:
                newruns = []
                for span, cur, y0, dx, ok in runs:
                    for (x, y) in span:
                        if g[y][x] != 14:
                            g[y][x] = 4
                    moved = [(x + dx, y) for (x, y) in span]
                    for (x, y) in moved:
                        if g[y][x] != 14:
                            g[y][x] = cur
                    newruns.append((moved, y0))
                    changed_any = True
                t1 = [m for m, y0 in newruns if y0 == 28]
                if t1 and min(x for (x, y) in t1[0]) >= 18:
                    for m, y0 in newruns:
                        for (x, y) in m:
                            if g[y][x] != 14:
                                g[y][x] = 12
                            else:
                                RECOLORED_E[0] = 12  # e embedded in recolored run
    slots = _slots()
    if key not in slots:
        return changed_any, 0
    changed = changed_any
    net = 0
    for entry in slots[key]:
        if entry[0] == "cellswap":
            _, a, b = entry
            for (xa, ya), (xb, yb) in zip(_cells(a), _cells(b)):
                va, vb = g[ya][xa], g[yb][xb]
                if va != vb:
                    g[ya][xa], g[yb][xb] = vb, va
                    changed = True
            continue
        c, slot, sa, sb = entry
        st = _slot_state(g, slot, c)
        if st == sa:
            new = sb
        elif st == sb:
            new = sa
        else:
            continue
        before = sum(1 for (xx, yy) in _cells(slot) if g[yy][xx] == c)
        _render(g, slot, c, new)
        after = sum(1 for (xx, yy) in _cells(slot) if g[yy][xx] == c)
        net += after - before
        changed = True
    return changed, net

def predict(state, grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}

    lvl0 = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    den = {0: 2, 1: 3, 2: 3}.get(lvl0, 3)  # L2 den=3 confirmed by t145-146
    T0 = sum(1 for xx in range(64) if grid[63][xx] == 3)
    cum = state.get("cum")
    if cum is None or -(-cum // den) != T0:
        # (re)calibrate from the visible bar when desynced
        cum = 0 if T0 == 0 else den * (T0 - 1) + 1

    carried = state.get("carried", 2)
    tdir = state.get("tdir", 1)
    if not isinstance(carried, (list, tuple)):
        carried = ((carried, carried), (carried, carried))
    carried = tuple(tuple(r) for r in carried)
    if action in DIRS:
        p = _find_player(g)
        if p is not None:
            px, py = p
            dx, dy = DIRS[action]
            nx, ny = px + dx, py + dy
            if 0 <= nx <= 62 and 0 <= ny <= 62:
                dest = [[g[ny][nx], g[ny][nx + 1]], [g[ny + 1][nx], g[ny + 1][nx + 1]]]
                vals = {dest[0][0], dest[0][1], dest[1][0], dest[1][1]}
                # movement rule: allowed iff NO cell is empty/background/border
                if not (vals & set(BLOCKED)):
                    # item-box: entering a flask-picture box consumes the item
                    # and materializes the flask button on the right panel
                    for bx, by, bw, bh, ic, fpx in _item_boxes():
                        inside = (bx <= nx and nx + 1 < bx + bw and
                                  by <= ny and ny + 1 < by + bh)
                        if inside and ic in vals and any(
                                g[yy][xx] == ic for yy in range(by, by + bh)
                                for xx in range(bx, bx + bw)):
                            for yy in range(by, by + bh):
                                for xx in range(bx, bx + bw):
                                    if g[yy][xx] == ic:
                                        g[yy][xx] = 2
                            for (xx, yy) in fpx:
                                g[yy][xx] = ic
                            dest = [[2, 2], [2, 2]]  # consumed under e
                            break
                    for i, yy in enumerate((py, py + 1)):
                        for j, xx in enumerate((px, px + 1)):
                            g[yy][xx] = carried[i][j]
                    for yy in (ny, ny + 1):
                        for xx in (nx, nx + 1):
                            g[yy][xx] = 14
                    carried = tuple(tuple(r) for r in dest)
                    if vals == {11}:
                        info["level_up"] = True

    poured = False
    penalty = False
    net = 0
    if action == 6 and x is not None and y is not None:
        for (x0, y0, x1, y1), key in _buttons():
            if x0 <= x <= x1 and y0 <= y <= y1:
                if key == "deploy":
                    # L3 transfer PENDULUM: 8 cells of 1s shift between c-rail
                    # (y40-41,x16-31) and tube (y20-21,x8-23) each click; the
                    # direction reverses at the ends (tdir in state).
                    # wt = tube end-cart width (0..8); wc = 8-wt.
                    # width 8 renders FUSED as solid c(12); partial renders 1.
                    wt = 0
                    while wt < 8 and g[20][8 + wt] in (1, 12):
                        wt += 1
                    nwt = wt + 2 * tdir
                    if nwt > 8:
                        nwt, tdir = 6, -1
                    elif nwt < 0:
                        nwt, tdir = 2, 1
                    nwc = 8 - nwt
                    tc = 12 if nwt >= 8 else 1
                    cc = 12 if nwc >= 8 else 1
                    for yy in (20, 21):
                        for xx in range(8, 24):
                            if g[yy][xx] != 14:
                                g[yy][xx] = tc if (xx < 8 + nwt or xx >= 24 - nwt) else 5
                    for yy in (40, 41):
                        for xx in range(16, 32):
                            if g[yy][xx] != 14:
                                g[yy][xx] = cc if (xx < 16 + nwc or xx >= 32 - nwc) else 5
                    poured = True
                    break
                if grid[y][x] != key:
                    break  # flask not present/clicked off its fill: plain click
                # clicking a flask while e occupies one of its slots:
                # NO swap + big time penalty (+20 units; pinned by t82-t84)
                occupied = False
                for entry in _slots().get(key, []):
                    if entry[0] == "cellswap":
                        continue  # cellswap pairs carry e along — no penalty
                    c, slot, sa, sb = entry
                    for (xx, yy) in _cells(slot):
                        if g[yy][xx] == 14:
                            occupied = True
                if occupied:
                    penalty = True
                else:
                    poured, net = _pour(g, key)
                break
        if poured:
            dv = _divider_x()
            for yy in range(63):
                for xx in range(dv, 64):
                    if g[yy][xx] == 0:
                        g[yy][xx] = 5

    if RECOLORED_E[0] is not None:
        c2 = RECOLORED_E[0]
        carried = ((c2, c2), (c2, c2))
        RECOLORED_E[0] = None
    if penalty:
        cum += 20
    else:
        cum += 2 if poured else 1
    ticks = -(-cum // den)
    for xx in range(64):
        if xx < ticks:
            g[63][xx] = 3
        elif g[63][xx] == 3:
            g[63][xx] = 0

    return g, info, {"cum": cum, "carried": carried, "tdir": tdir}
