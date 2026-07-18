# vc33 world model — v6 (valves + float + timer)
# SCENE (x acts like "height", gravity points to x=0):
#   row0 = timer bar. A 4-row rod (color 5, grip b) splits scene into TOP section
#   (rows 1..rod_top-1) and BOTTOM section (rows rod_bot+1..63).
#   Each section is green(3) for x < L (its "level"), black(0) beyond.
#   9-colored blocks = VALVE BUTTONS (fixed): one in top section, one in bottom section.
#   An arrow float (4s + b tail) rides the BOTTOM surface: cells at fixed offsets from L_bot.
# MECHANICS (observed #8):
#   click bottom valve: L_top += 4, L_bot -= 4; float follows. (effective click)
#   click top valve: PREDICTED reverse: L_top -= 4, L_bot += 4. (untested)
#   any other click: no world change.
# TIMER (row0): t = consumed cells (non-7). drain = (2 if t%5==1 else 1) + (1 if effective else 0).
#   (alternative not yet ruled out: effective clicks cost flat 2 — differs only when t%5==1.)
# Unknowns: level limits/clamping, what empties/fills do, goal condition, bar-empty consequence.

def _rod_rows(g):
    rows = [yy for yy in range(64) if any(v == 5 for v in g[yy])]
    if not rows:
        return None, None
    return min(rows), max(rows)

def _first0(row):
    for i, v in enumerate(row):
        if v == 0:
            return i
    return 64

def _arrow_offsets():
    # cells of color 4/11 in bottom section of ENTRY_GRID, as (dy_row, dx_from_Lbot, color)
    eg = ENTRY_GRID
    rt, rb = _rod_rows(eg)
    L0 = _first0(eg[63])
    out = []
    for yy in range(rb + 1, 64):
        for xx in range(64):
            if eg[yy][xx] in (4, 11):
                out.append((yy, xx - L0, eg[yy][xx]))
    return out

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return g, info
    eff = False
    rt, rb = _rod_rows(grid)
    if rt is not None and grid[y][x] == 9:
        top_rows = range(1, rt)
        bot_rows = range(rb + 1, 64)
        L_t = _first0(grid[1])
        L_b = _first0(grid[63])
        if y < rt:
            nLt, nLb = L_t - 4, L_b + 4   # top valve (untested prediction)
        else:
            nLt, nLb = L_t + 4, L_b - 4   # bottom valve (observed)
        eff = True
        # redraw top section
        for yy in top_rows:
            for xx in range(64):
                g[yy][xx] = 3 if xx < nLt else 0
        # redraw bottom section
        for yy in bot_rows:
            for xx in range(64):
                g[yy][xx] = 3 if xx < nLb else 0
        # re-stamp valve blocks (9s persist)
        for yy in range(1, 64):
            for xx in range(64):
                if ENTRY_GRID[yy][xx] == 9:
                    g[yy][xx] = 9
        # re-stamp float at new bottom level
        for (yy, dx, c) in _arrow_offsets():
            nx = nLb + dx
            if 0 <= nx < 64:
                g[yy][nx] = c
    # timer drain: total consumed after n clicks = (13n+4)//10  (~1.3/click, fits all 10 observed)
    # stateless: recover n from t, drain = total(n+1) - t. "effective+1" hypothesis DEAD (#9 cost 1).
    t = sum(1 for v in grid[0] if v != 7)
    n = (10 * t + 5) // 13
    cost = (13 * (n + 1) + 4) // 10 - t
    n = 0
    for i in range(63, -1, -1):
        if n >= cost:
            break
        if g[0][i] == 7:
            g[0][i] = 4
            n += 1
    return g, info
