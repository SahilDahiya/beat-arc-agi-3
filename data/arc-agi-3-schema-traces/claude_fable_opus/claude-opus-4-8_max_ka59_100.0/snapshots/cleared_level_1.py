"""World model (general).

LATTICE: 3x3 px cells, origin (0,0). Cell (c,r) -> px x=3c..3c+2, y=3r..3r+2.

TOKENS: rectangular 'e'(14) outlines, w x h CELLS (level 1 has 1x1, 2x1, 1x2, 2x2).
  Rendered as a 3w x 3h px box; the digit is a w x h px block at offset (+w,+h).
  Each token has:
    * INTRINSIC value (immutable) = the distance in CELLS it flies when LAUNCHED.
    * DISPLAYED digit = intrinsic - (1 if it has EVER been selected else 0);
      the SELECTED token shows 0 instead.  MOVES DECAY NOTHING.

ACTIONS
  1-4 move the SELECTED token 1 cell (1=U 2=D 3=L 4=R).
  Bumping another token does NOT move the selected one: the bumped token LAUNCHES exactly
      its INTRINSIC value in cells, straight THROUGH walls.
  6 (click) on a token SELECTS it (shows 0); the old one reveals its digit.
  Every action costs one bar tick.

FRAMES: colour-4 rectangular outlines; the interior is a w x h cell region matching one
  token's shape.  GOAL: every frame's interior exactly covered by a token.
BAR (row 63): zeros = round(64*n/100), n = actions since level start / RESET.
"""

# Budget is per-level and inferred; see BUDGETS / BUDGET_RANGE.
FLOOR, BG, WALL, BOX, FRAME = 1, 2, 15, 14, 4
BAR_ROW, BAR_COLOR, BAR_SPENT = 63, 4, 0
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
# Action budget per LEVEL (bar = round(64*n/budget)). It DIFFERS per level, so unknown
# levels start with a feasible SET that is pruned from the observed bar each step.
BUDGETS = {0: 100}
BUDGET_RANGE = list(range(96, 145))     # prior: budgets seen so far are ~100 (L0), 103-128 (L1)
NONBG = (FLOOR, BG, WALL, FRAME)

# Intrinsic of the token that starts SELECTED (hidden behind its 0 in the entry grid).
START_VALUE_BY_LEVEL = {0: 5, 1: 5}


def _bar_for(n, budget):
    return (2 * 64 * n + budget) // (2 * budget)


def _bar_pick(n, Ns):
    """Predicted zeros: the majority vote over still-feasible budgets."""
    vals = [_bar_for(n, N) for N in Ns]
    return max(set(vals), key=vals.count)


def _comps(grid, pred):
    H = min(len(grid), BAR_ROW)          # never scan the bar row
    W = len(grid[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or not pred(grid[y][x]):
                continue
            stack, cells = [(y, x)], []
            seen[y][x] = True
            while stack:
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and pred(grid[ny][nx]):
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            ys = [p[0] for p in cells]
            xs = [p[1] for p in cells]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def parse_tokens(grid):
    """[(c, r, w, h, digit)] from a CLEAN grid (no two tokens touching)."""
    out = []
    for x0, y0, x1, y1 in _comps(grid, lambda v: v not in NONBG):
        w, h = (x1 - x0 + 1) // 3, (y1 - y0 + 1) // 3
        if w < 1 or h < 1:
            continue
        out.append((x0 // 3, y0 // 3, w, h, grid[y0 + h][x0 + w]))
    return out


def parse_frames(entry):
    out = []
    for x0, y0, x1, y1 in _comps(entry, lambda v: v == FRAME):
        c0, r0 = (x0 + 1) // 3, (y0 + 1) // 3
        c1, r1 = (x1 - 1) // 3, (y1 - 1) // 3
        if c1 >= c0 and r1 >= r0:
            out.append((c0, r0, c1 - c0 + 1, r1 - r0 + 1))
    return out


def _occ(t):
    c, r, w, h = t["c"], t["r"], t["w"], t["h"]
    return {(c + i, r + j) for i in range(w) for j in range(h)}


def _passable(entry, cell):
    c, r = cell
    x0, y0 = 3 * c, 3 * r
    if c < 0 or r < 0 or x0 + 2 >= len(entry[0]) or y0 + 2 >= BAR_ROW:
        return False
    return all(entry[y0 + dy][x0 + dx] not in (BG, WALL)
               for dy in range(3) for dx in range(3))


def _background(entry):
    bg = [row[:] for row in entry]
    for (c, r, w, h, _d) in parse_tokens(entry):
        for j in range(3 * h):
            for i in range(3 * w):
                bg[3 * r + j][3 * c + i] = FLOOR
    for x in range(len(bg[0])):
        bg[BAR_ROW][x] = BAR_COLOR
    return bg


def _render(entry, toks, sel, n, Ns):
    g = _background(entry)
    occ = {}
    for i, t in enumerate(toks):
        for cell in _occ(t):
            occ[cell] = i
    for i, t in enumerate(toks):
        c, r, w, h = t["c"], t["r"], t["w"], t["h"]
        x0, y0 = 3 * c, 3 * r
        for j in range(3 * h):
            for k in range(3 * w):
                g[y0 + j][x0 + k] = BOX
        d = 0 if i == sel else t["v"] - (1 if t["u"] else 0)
        for j in range(h):
            for k in range(w):
                g[y0 + h + j][x0 + w + k] = d
    # CONTACT: if ANY token touches a SIDE of the selected token, that WHOLE side renders
    # as 0 (not just the touching cells).
    if sel is not None and 0 <= sel < len(toks):
        t = toks[sel]
        c, r, w, h = t["c"], t["r"], t["w"], t["h"]
        x0, y0, x1, y1 = 3 * c, 3 * r, 3 * (c + w) - 1, 3 * (r + h) - 1
        if any(occ.get((c + i, r - 1), sel) != sel for i in range(w)):
            for x in range(x0, x1 + 1):
                g[y0][x] = 0
        if any(occ.get((c + i, r + h), sel) != sel for i in range(w)):
            for x in range(x0, x1 + 1):
                g[y1][x] = 0
        if any(occ.get((c - 1, r + j), sel) != sel for j in range(h)):
            for y in range(y0, y1 + 1):
                g[y][x0] = 0
        if any(occ.get((c + w, r + j), sel) != sel for j in range(h)):
            for y in range(y0, y1 + 1):
                g[y][x1] = 0
    W = len(g[0])
    for i in range(min(_bar_pick(n, Ns), W)):
        g[BAR_ROW][W - 1 - i] = BAR_SPENT
    return g


def is_goal(grid):
    frames = parse_frames(ENTRY_GRID)
    if not frames:
        return False
    toks = parse_tokens(grid)
    have = {(c, r, w, h) for (c, r, w, h, _d) in toks}
    return all(f in have for f in frames)


def _barcount(grid):
    return sum(1 for v in grid[BAR_ROW] if v == BAR_SPENT)


def _resync_n(n, grid, budget):
    b = _barcount(grid)
    cand = max(0, n)
    while _bar_for(cand, budget) < b:
        cand += 1
    return cand if _bar_for(cand, budget) == b else n


def init_state(entry_grid):
    lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    sv = START_VALUE_BY_LEVEL.get(lvl, 5)
    Ns = [BUDGETS[lvl]] if lvl in BUDGETS else list(BUDGET_RANGE)
    toks, sel = [], None
    for i, (c, r, w, h, d) in enumerate(parse_tokens(entry_grid)):
        if d == 0:
            sel = i
            toks.append({"c": c, "r": r, "w": w, "h": h, "v": sv, "u": True})
        else:
            toks.append({"c": c, "r": r, "w": w, "h": h, "v": d, "u": False})
    return {"n": 0, "toks": toks, "sel": sel, "Ns": Ns}


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {})
    Ns = list(st.get("Ns") or BUDGET_RANGE)
    if len(Ns) == 1:
        st["n"] = _resync_n(st.get("n", 0), grid, Ns[0])
    else:                                   # prune budgets against the observed bar
        b = _barcount(grid)
        pruned = [N for N in Ns if _bar_for(st.get("n", 0), N) == b]
        if pruned:
            Ns = pruned
    st["Ns"] = Ns
    entry = ENTRY_GRID
    toks = [dict(t) for t in (st.get("toks") or [])]
    sel = st.get("sel")

    # RESYNC: if state disagrees with the grid (run_backtest skips the first-ever step),
    # rebuild from the grid. Only ever happens at a level start, before any click.
    # compare OCCUPIED CELLS (robust: two touching tokens merge under parse_tokens)
    grid_cells = set()
    for c in range(len(grid[0]) // 3):
        for r in range(BAR_ROW // 3):
            x0, y0 = 3 * c, 3 * r
            if any(grid[y0 + j][x0 + i] == BOX for j in range(3) for i in range(3)):
                grid_cells.add((c, r))
    state_cells = set()
    for t in toks:
        state_cells |= _occ(t)
    if state_cells != grid_cells:
        st2 = init_state(grid)
        toks, sel = st2["toks"], st2["sel"]

    if not toks or sel is None:
        return [row[:] for row in grid], info, st

    occ = {}
    for i, t in enumerate(toks):
        for cell in _occ(t):
            occ[cell] = i

    def finish(n):
        g = _render(entry, toks, sel, n, Ns)
        st.update({"toks": toks, "sel": sel, "n": n, "Ns": Ns})
        if is_goal(g):
            info["level_up"] = True
        return g, info, st

    if action == 6:
        tgt = occ.get((x // 3, y // 3)) if (x is not None and y is not None) else None
        if tgt is not None and tgt != sel:
            sel = tgt
            toks[tgt]["u"] = True
            return finish(st["n"] + 1)
        return [row[:] for row in grid], info, st

    if action not in DIRS:
        return [row[:] for row in grid], info, st

    dc, dr = DIRS[action]
    me = toks[sel]
    dest = {(c + dc, r + dr) for (c, r) in _occ(me)}
    hit = {occ[cell] for cell in dest if cell in occ and occ[cell] != sel}

    if hit:                                   # LAUNCH the bumped token(s)
        for i in hit:
            v = toks[i]["v"]
            toks[i]["c"] += dc * v
            toks[i]["r"] += dr * v
        return finish(st["n"] + 1)

    if not all(_passable(entry, cell) for cell in dest):
        return [row[:] for row in grid], info, st        # blocked

    me["c"] += dc
    me["r"] += dr
    return finish(st["n"] + 1)
