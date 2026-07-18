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
BLOCKED = (0, 3, 4, 5, 14)

def _buttons():
    # list of ((x0,y0,x1,y1) inclusive region, color-key)
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return [((41, 16, 55, 22), 8), ((41, 33, 55, 39), 9)]
    if lvl == 1:
        return [((46, 20, 60, 24), 6), ((46, 38, 60, 42), 9),
                ((46, 29, 58, 33), 8)]  # flask-8 appears after item-box collected
        # NOTE: clicking flask-8 before it materializes: region is 5s; the game
        # may ignore it — model applies _pour only if slots exist; harmless.
    return []

def _slots():
    # color-key -> list of (material_color, slotA(x,y,w,h), slotB(x,y,w,h))
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return {
            8: [(8, (12, 30, 6, 4), (18, 24, 4, 6))],
            9: [(9, (18, 20, 4, 4), (8, 34, 4, 4))],
        }
    if lvl == 1:
        return {
            6: [(7, (8, 40, 8, 4), (16, 32, 4, 8)),
                (7, (20, 40, 8, 4), (16, 44, 4, 8))],
            9: [(9, (8, 28, 4, 4), (4, 32, 4, 8))],
            8: [(8, (12, 24, 8, 4), (20, 16, 4, 8)),   # GUESS: 8-runs rotate
                (8, (24, 24, 8, 4), (20, 28, 4, 8))],  # around d into the gap
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
    return []

def _divider_x():
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return 34
    return 40

def init_state(entry_grid):
    return {"cum": None, "carried": 2}

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
    for (x, y) in _cells(slot):
        if st == "full":
            g[y][x] = c
        elif st == "half":
            g[y][x] = c if (x + y) % 2 == 1 else 4
        else:
            g[y][x] = 4

def _pour(g, key):
    """Swap fill-states of each pair. Returns (changed, net_material_delta)."""
    slots = _slots()
    if key not in slots:
        return False, 0
    changed = False
    net = 0
    for c, a, b in slots[key]:
        sa, sb = _slot_state(g, a, c), _slot_state(g, b, c)
        if sa is None or sb is None or sa == sb:
            continue
        before = sum(1 for (xx, yy) in _cells(a) + _cells(b) if g[yy][xx] == c)
        _render(g, a, c, sb)
        _render(g, b, c, sa)
        after = sum(1 for (xx, yy) in _cells(a) + _cells(b) if g[yy][xx] == c)
        net += after - before
        changed = True
    return changed, net

def predict(state, grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}

    den = (CURRENT_LEVEL if CURRENT_LEVEL is not None else 0) + 2
    T0 = sum(1 for xx in range(64) if grid[63][xx] == 3)
    cum = state.get("cum")
    if cum is None or -(-cum // den) != T0:
        # (re)calibrate from the visible bar when desynced
        cum = 0 if T0 == 0 else den * (T0 - 1) + 1

    carried = state.get("carried", 2)
    if action in DIRS:
        p = _find_player(g)
        if p is not None:
            px, py = p
            dx, dy = DIRS[action]
            nx, ny = px + dx, py + dy
            if 0 <= nx <= 62 and 0 <= ny <= 62:
                vals = {g[ny][nx], g[ny][nx + 1], g[ny + 1][nx], g[ny + 1][nx + 1]}
                entered = False
                if len(vals) == 1:
                    v = vals.pop()
                    if v not in BLOCKED:
                        entered = True
                        newcarried = v
                        if v == 11:
                            info["level_up"] = True
                else:
                    # item-box collection: mixed {2, item} inside a known box
                    for bx, by, bw, bh, ic, fpx in _item_boxes():
                        inside = (bx <= nx and nx + 1 < bx + bw and
                                  by <= ny and ny + 1 < by + bh)
                        if inside and vals <= {2, ic} and any(
                                g[yy][xx] == ic for yy in range(by, by + bh)
                                for xx in range(bx, bx + bw)):
                            for yy in range(by, by + bh):
                                for xx in range(bx, bx + bw):
                                    if g[yy][xx] == ic:
                                        g[yy][xx] = 2
                            for (xx, yy) in fpx:
                                g[yy][xx] = ic
                            entered = True
                            newcarried = 2
                            break
                if entered:
                    for yy in (py, py + 1):
                        for xx in (px, px + 1):
                            g[yy][xx] = carried
                    for yy in (ny, ny + 1):
                        for xx in (nx, nx + 1):
                            g[yy][xx] = 14
                    carried = newcarried

    poured = False
    penalty = False
    net = 0
    if action == 6 and x is not None and y is not None:
        for (x0, y0, x1, y1), key in _buttons():
            if x0 <= x <= x1 and y0 <= y <= y1:
                if grid[y][x] != key:
                    break  # flask not present/clicked off its fill: plain click
                # clicking a flask while e occupies one of its slots:
                # NO swap + big time penalty (+20 units; pinned by t82-t84)
                occupied = False
                for c, a, b in _slots().get(key, []):
                    for (xx, yy) in _cells(a) + _cells(b):
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

    return g, info, {"cum": cum, "carried": carried}
