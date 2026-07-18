# dc22 world model (predict form, stateful)
# CONFIRMED (level 0):
# - e(14) is a 2x2 SWIMMER. Actions 1/2/3/4 = up/down/left/right by 2.
#   It may enter a 2x2 destination iff all 4 cells are ONE color in
#   {2, 8, 9, 11, 13} (solid material). 4 (empty) blocks; MIXED blocks.
#   e CARRIES the color it displaced: on move, vacated cells restore carried
#   color, then carried := destination's color. (t30: left B leaving 2s;
#   t31: moved up through 9s leaving 9s.) carried starts 2 (inside container).
# - Click on a cup fill (right panel x>=34, color 8/9) = SWAP that color's two
#   slots cell-wise row-major (works on whatever the slots contain now):
#     slots8: strip (12,30,6x4) <-> gap (18,24,4x6)
#     slots9: tower (18,20,4x4) <-> checker (8,34,4x4)
#   First pour also turned right-panel 0-outlines -> 5 (one-time; encoded idempotent).
# - Other clicks: no-ops.
# - Row63 clock: halves h; +1 per action; +1 extra when a swap fires;
#   bar = ceil(h/2) 3s from left. First-call calibration h=2T-1 if T>0 else 0.
# GOAL HYPOTHESIS: tunnel e into container A and reach/merge with b(11) 2x2 at
# (24,20). Unknown what happens on entry — model predicts plain move, no flags.

DIRS = {1: (0, -2), 2: (0, 2), 3: (-2, 0), 4: (2, 0)}

SLOTS = {
    8: [(12, 30, 6, 4), (18, 24, 4, 6)],
    9: [(18, 20, 4, 4), (8, 34, 4, 4)],
}

ENTERABLE = (2, 8, 9, 11, 13)

def init_state(entry_grid):
    return {"h": None, "carried": 2}

def _find_player(g, color=14):
    for y in range(64):
        for x in range(64):
            if g[y][x] == color:
                return x, y
    return None

def _cells(slot):
    x0, y0, w, hh = slot
    return [(x0 + i % w, y0 + i // w) for i in range(w * hh)]

def _pour(g, c):
    if c not in SLOTS:
        return False
    a, b = SLOTS[c]
    changed = False
    for (xa, ya), (xb, yb) in zip(_cells(a), _cells(b)):
        va, vb = g[ya][xa], g[yb][xb]
        if va != vb:
            g[ya][xa], g[yb][xb] = vb, va
            changed = True
    return changed

def predict(state, grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}

    h = state.get("h")
    if h is None:
        T = sum(1 for xx in range(64) if grid[63][xx] == 3)
        h = 0 if T == 0 else 2 * T - 1

    carried = state.get("carried", 2)
    if action in DIRS:
        p = _find_player(g)
        if p is not None:
            px, py = p
            dx, dy = DIRS[action]
            nx, ny = px + dx, py + dy
            if 0 <= nx <= 62 and 0 <= ny <= 62:
                vals = {g[ny][nx], g[ny][nx + 1], g[ny + 1][nx], g[ny + 1][nx + 1]}
                if len(vals) == 1:
                    v = vals.pop()
                    if v in ENTERABLE:
                        for yy in (py, py + 1):
                            for xx in (px, px + 1):
                                g[yy][xx] = carried
                        for yy in (ny, ny + 1):
                            for xx in (nx, nx + 1):
                                g[yy][xx] = 14
                        carried = v

    poured = False
    if action == 6 and x is not None and y is not None:
        c = grid[y][x]
        if x >= 34 and c in (8, 9):
            poured = _pour(g, c)
            if poured:
                for yy in range(10, 54):
                    for xx in range(34, 64):
                        if g[yy][xx] == 0:
                            g[yy][xx] = 5

    h += 1
    if poured:
        h += 1
    ticks = -(-h // 2)
    for xx in range(64):
        if xx < ticks:
            g[63][xx] = 3
        elif g[63][xx] == 3:
            g[63][xx] = 0

    return g, info, {"h": h, "carried": carried}
