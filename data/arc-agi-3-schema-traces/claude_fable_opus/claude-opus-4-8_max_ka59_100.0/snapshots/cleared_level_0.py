"""World model. (v6: intrinsic vs displayed digit)

TOKENS: 3x3 'e'(14) outlines with a centre DIGIT.
  Each token has TWO quantities -- this distinction is the crux of the game:
    * INTRINSIC value (immutable)  -> the distance it flies when LAUNCHED.
    * DISPLAYED digit = intrinsic - (moves it has made itself), floor 0.  A wear counter.
  The SELECTED token displays 0 instead of its digit, so the starting token's value is not
  visible in the entry grid (level 0: it is 4, learned by clicking it away).

ACTIONS
  1-4 move the SELECTED token 1 cell (1=U 2=D 3=L 4=R) and decrement ITS displayed digit.
      Moving is still allowed at 0.
  Bumping another token does NOT move the selected one: the bumped token LAUNCHES exactly
      its INTRINSIC value in cells, straight THROUGH walls, and its digit is UNCHANGED.
      Confirmed: Y(intr 5) launched +5 twice -- once while displaying 5, once while
      displaying 4. So the launch uses the INTRINSIC, not the shown digit.
  6 (click) on a token SELECTS it (shows 0); the old one reveals its digit. Costs a move.
      => cross a wall by LAUNCHING a token over it, then CLICKING it to take control.

OTHER
  - CONTACT: while selected and orthogonally adjacent to a token, the selected token's 3
    edge pixels on the facing side render as 0.
  - 5x5 colour-4 outlines = FRAMES around one cell. is_goal: every frame covered by a token.
  - Bar (row 63): zeros = round(64*n/100); n = actions since level start / RESET.
"""

# NOTE: selection is tracked in state (a decayed 0-digit token looks identical to selected).
FLOOR, BG, WALL, BOX = 1, 2, 15, 14
BAR_ROW, BAR_COLOR, BAR_SPENT = 63, 4, 0
FRAME = 4
OX, OY = 9, 21
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
LEVEL_BUDGET = 100

# Intrinsic of the token that starts SELECTED (hidden behind its 0 in the entry grid).
START_VALUE_BY_LEVEL = {0: 5}


def _bar_for(n):
    return (2 * 64 * n + LEVEL_BUDGET) // (2 * LEVEL_BUDGET)


def _cell_px(c, r):
    return OX + 3 * c, OY + 3 * r


def _cell_of(x, y):
    if x is None or y is None or x < OX or y < OY:
        return None
    return ((x - OX) // 3, (y - OY) // 3)


def _cells(grid):
    H, W = len(grid), len(grid[0])
    c = 0
    while OX + 3 * c + 2 < W:
        r = 0
        while OY + 3 * r + 2 < H:
            yield c, r
            r += 1
        c += 1


def _tokens(grid):
    out = {}
    for c, r in _cells(grid):
        x0, y0 = _cell_px(c, r)
        border = [grid[y0 + dy][x0 + dx]
                  for dy in range(3) for dx in range(3) if (dx, dy) != (1, 1)]
        if sum(1 for v in border if v == BOX) >= 5:
            out[(c, r)] = grid[y0 + 1][x0 + 1]
    return out


def _selected(grid):
    for cell, d in _tokens(grid).items():
        if d == 0:
            return cell
    return None


def _passable(entry):
    ok = set()
    for c, r in _cells(entry):
        x0, y0 = _cell_px(c, r)
        block = [entry[y0 + dy][x0 + dx] for dy in range(3) for dx in range(3)]
        if all(v != BG and v != WALL for v in block):
            ok.add((c, r))
    return ok


def _frames(entry):
    H, W = len(entry), len(entry[0])
    out = set()
    for c, r in _cells(entry):
        x0, y0 = _cell_px(c, r)
        if x0 == 0 or y0 == 0 or x0 + 3 >= W or y0 + 3 >= H:
            continue
        ring = []
        for dx in range(-1, 4):
            ring.append(entry[y0 - 1][x0 + dx])
            ring.append(entry[y0 + 3][x0 + dx])
        for dy in range(3):
            ring.append(entry[y0 + dy][x0 - 1])
            ring.append(entry[y0 + dy][x0 + 3])
        if all(v == FRAME for v in ring):
            out.add((c, r))
    return out


def is_goal(grid):
    fr = _frames(ENTRY_GRID)
    return bool(fr) and fr <= set(_tokens(grid))


def _background(entry):
    bg = [row[:] for row in entry]
    for cell in _tokens(entry):
        x0, y0 = _cell_px(*cell)
        for dy in range(3):
            for dx in range(3):
                bg[y0 + dy][x0 + dx] = FLOOR
    for x in range(len(bg[0])):
        bg[BAR_ROW][x] = BAR_COLOR
    return bg


def _render(entry, sel, others, n):
    """others = {cell: displayed_digit}"""
    g = _background(entry)
    for cell, d in others.items():
        x0, y0 = _cell_px(*cell)
        for dy in range(3):
            for dx in range(3):
                g[y0 + dy][x0 + dx] = BOX
        g[y0 + 1][x0 + 1] = d
    x0, y0 = _cell_px(*sel)
    for dy in range(3):
        for dx in range(3):
            g[y0 + dy][x0 + dx] = BOX
    g[y0 + 1][x0 + 1] = 0
    for (bc, br) in others:
        dc, dr = bc - sel[0], br - sel[1]
        if (dc, dr) == (1, 0):
            for dy in range(3):
                g[y0 + dy][x0 + 2] = 0
        elif (dc, dr) == (-1, 0):
            for dy in range(3):
                g[y0 + dy][x0] = 0
        elif (dc, dr) == (0, 1):
            for dx in range(3):
                g[y0 + 2][x0 + dx] = 0
        elif (dc, dr) == (0, -1):
            for dx in range(3):
                g[y0][x0 + dx] = 0
    W = len(g[0])
    for i in range(min(_bar_for(n), W)):
        g[BAR_ROW][W - 1 - i] = BAR_SPENT
    return g


def _resync_n(n, grid):
    b = sum(1 for v in grid[BAR_ROW] if v == BAR_SPENT)
    cand = max(0, n)
    while _bar_for(cand) < b:
        cand += 1
    return cand if _bar_for(cand) == b else n


def init_state(entry_grid):
    lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    toks = _tokens(entry_grid)
    sel = _selected(entry_grid)
    sv = START_VALUE_BY_LEVEL.get(lvl)
    intr = {}
    for c, d in toks.items():
        intr[c] = (sv if sv is not None else d + 1) if c == sel else d
    return {"n": 0, "sel": sel, "intr": intr, "used": [sel] if sel else []}


def _sync(st, grid):
    """Selection is tracked in STATE, not read off the grid: a token whose digit has
    decayed to 0 renders exactly like the selected one, so the grid is ambiguous."""
    toks = _tokens(grid)
    sel = st.get("sel")
    if sel not in toks:                      # desync (e.g. a skipped step) -> rebuild
        sel = _selected(grid)
    return sel, toks


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {})
    st["n"] = _resync_n(st.get("n", 0), grid)
    entry = ENTRY_GRID

    intr = dict(st.get("intr") or {})
    used = set(st.get("used") or [])
    sel = st.get("sel")
    toks = _tokens(grid)
    if sel not in intr or set(intr) != set(toks):
        # desync (e.g. run_backtest skips the first-ever step) -> rebuild from the grid.
        lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
        sv = START_VALUE_BY_LEVEL.get(lvl)
        sel = _selected(grid)
        intr = {}
        for c, d in toks.items():
            intr[c] = ((sv if sv is not None else d + 1) if c == sel else d)
        used = {sel} if sel else set()
    if sel is None:
        return [row[:] for row in grid], info, st

    def out(sel, intr, used, n):
        others = {c: intr[c] - (1 if c in used else 0) for c in intr if c != sel}
        g = _render(entry, sel, others, n)
        st.update({"sel": sel, "intr": intr, "used": sorted(used), "n": n})
        if is_goal(g):
            info["level_up"] = True
        return g, info, st

    if action == 6:
        tgt = _cell_of(x, y)
        if tgt in intr and tgt != sel:
            return out(tgt, intr, used | {tgt}, st["n"] + 1)
        return [row[:] for row in grid], info, st

    if action not in DIRS:
        return [row[:] for row in grid], info, st

    dc, dr = DIRS[action]
    nxt = (sel[0] + dc, sel[1] + dr)

    if nxt in intr and nxt != sel:                       # LAUNCH: uses the INTRINSIC value
        v = intr[nxt]
        dest = (nxt[0] + dc * v, nxt[1] + dr * v)
        ni = {k: vv for k, vv in intr.items() if k != nxt}
        ni[dest] = v
        nu = {(dest if u == nxt else u) for u in used}
        return out(sel, ni, nu, st["n"] + 1)

    if nxt not in _passable(entry):
        return [row[:] for row in grid], info, st

    ni = {k: vv for k, vv in intr.items() if k != sel}
    ni[nxt] = intr[sel]
    nu = {(nxt if u == sel else u) for u in used}
    return out(nxt, ni, nu, st["n"] + 1)
