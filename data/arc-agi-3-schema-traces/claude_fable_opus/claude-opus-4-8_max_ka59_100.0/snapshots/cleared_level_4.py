"""World model (general, levels 0-2).

LATTICE: 3x3 px cells. The ORIGIN OFFSET differs per level (L0/L1: 0,0 ; L2: 2,2) and is
  detected from the entry grid.  cell(c,r) -> px x=ox+3c, y=oy+3r.

TOKENS: an arbitrary SET OF CELLS. Two render styles seen:
  * OUTLINE (colour 14): a rectangular w x h box drawn as a 3w x 3h outline, with the
    DIGIT as a w x h px block at offset (+w,+h).
  * SOLID (colour 11): every cell filled; NO digit (e.g. the plus/cross shapes of level 2).
  Each token has an IMMUTABLE INTRINSIC value (= cells it flies when LAUNCHED); every
  token seen so far has intrinsic 5.
  DISPLAYED digit (outline tokens) = intrinsic - (1 if EVER selected else 0);
  the SELECTED token shows 0.  MOVES DECAY NOTHING.

ACTIONS
  1-4 move the SELECTED token 1 cell (1=U 2=D 3=L 4=R).
  Bumping another token does NOT move the selected one: the bumped token LAUNCHES exactly
      its INTRINSIC in cells, straight THROUGH walls.
  6 (click) a token SELECTS it.  Every action costs one bar tick.
CONTACT: if any token touches a SIDE of the selected token, that WHOLE side renders as 0.
FRAMES: colour-4 outlines; interior = a cell-set matching one token's SHAPE.
  GOAL: every frame's interior exactly covered by a token.
BAR (row 63): zeros = round(64*n/budget); the budget is PER-LEVEL (L0=100, L1 in 119..128)
  so unknown levels carry a feasible SET, pruned against the observed bar each step.
"""

# LAUNCH = fly >= v if possible (overshoot), else as far as it can (k<v); + SHOVE of occupants.
# NOTE: a BLOCKED move still costs an action (the bar ticks).
# Tokens may be OUTLINE (14, box+digit) or any other colour(s) redrawn from a pixel pattern.
# is_goal takes (state, grid): touching tokens merge under parse_tokens, so trust the state.
# Two-tone (12/13) tokens are COUNTDOWN gauges: the 13-region shrinks 1 unit per action and
# wraps to full at 0. *** WHEN IT EXPIRES THE TOKEN FIRES: it shoves whatever is below it. ***
# (Seen: at k=1 the next action threw the player from (9,13) down to (9,15).)  Avoid being
# under it when k hits 1; the timer tells you exactly when.
# The gauge AXIS must come from ENTRY_GRID: a FULL gauge is uniform in both axes.
FLOOR, BG, WALL, FRAME = 1, 2, 15, 4
OUTLINE, SOLID = 14, 11
BAR_ROW, BAR_COLOR, BAR_SPENT = 63, 4, 0
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
NONBG = (FLOOR, BG, WALL, FRAME)
BUDGETS = {0: 100, 1: 128, 2: 100, 3: 128}   # per-level action budget (pinned from history)
BUDGET_RANGE = list(range(96, 145))     # unknown levels: feasible set, pruned each step
# Every token seen so far (outline AND solid) has intrinsic 5. SOLID tokens show no digit
# and the SELECTED token hides its digit behind the 0, so both fall back to this.
SOLID_VALUE_BY_LEVEL = {}
START_VALUE_BY_LEVEL = {}
DEFAULT_VALUE = 5


def _bar_for(n, b):
    return (2 * 64 * n + b) // (2 * b)


def _bar_pick(n, Ns):
    vals = [_bar_for(n, N) for N in Ns]
    return max(set(vals), key=vals.count)


def _barcount(grid):
    return sum(1 for v in grid[BAR_ROW] if v == BAR_SPENT)


def _pix_comps(grid, pred):
    H, W = min(len(grid), BAR_ROW), len(grid[0])
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
            out.append(cells)
    return out


def _origin(entry):
    """Lattice offset: token pixels sit at x,y = o + 3k."""
    for pix in _pix_comps(entry, lambda v: v not in NONBG):
        ys = [p[0] for p in pix]
        xs = [p[1] for p in pix]
        return min(xs) % 3, min(ys) % 3
    return 0, 0


def _cells_of(pix, ox, oy):
    return {((x - ox) // 3, (y - oy) // 3) for (y, x) in pix}


def parse_tokens(entry):
    """[(cells frozenset, colour, digit or None, pattern)] from a CLEAN grid.
    OUTLINE tokens (colour 14) render a box+digit; any other token (solid 11, or the
    two-tone 12/13 tokens of level 4) is redrawn from its stored PIXEL PATTERN."""
    ox, oy = _origin(entry)
    out = []
    for pix in _pix_comps(entry, lambda v: v not in NONBG):
        cols = {entry[y][x] for (y, x) in pix}
        cells = _cells_of(pix, ox, oy)
        cs = sorted(cells)
        c0 = min(c for c, r in cs)
        r0 = min(r for c, r in cs)
        if OUTLINE in cols:
            w = max(c for c, r in cs) - c0 + 1
            h = max(r for c, r in cs) - r0 + 1
            digit = entry[oy + 3 * r0 + h][ox + 3 * c0 + w]
            out.append((frozenset(cells), OUTLINE, digit, None))
        else:
            pat = {}
            for (c, r) in cells:
                for j in range(3):
                    for i in range(3):
                        pat[(3 * (c - c0) + i, 3 * (r - r0) + j)] = \
                            entry[oy + 3 * r + j][ox + 3 * c + i]
            out.append((frozenset(cells), sorted(cols)[0], None, pat))
    return out


def parse_frames(entry):
    """[cells frozenset] -- the interior of each colour-4 outline (any shape)."""
    ox, oy = _origin(entry)
    H, W = min(len(entry), BAR_ROW), len(entry[0])
    out = []
    tokpix = set()
    for pix in _pix_comps(entry, lambda v: v not in NONBG):
        tokpix |= set(pix)
    for pix in _pix_comps(entry, lambda v: v == FRAME):
        ys = [p[0] for p in pix]
        xs = [p[1] for p in pix]
        y0, y1 = min(ys) - 1, max(ys) + 1
        x0, x1 = min(xs) - 1, max(xs) + 1
        outline = set(pix) | tokpix
        outside, stack = set(), [(y0, x0)]
        while stack:
            cy, cx = stack.pop()
            if not (y0 <= cy <= y1 and x0 <= cx <= x1):
                continue
            if (cy, cx) in outside or (cy, cx) in outline:
                continue
            outside.add((cy, cx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                stack.append((cy + dy, cx + dx))
        inner = [(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
                 if (y, x) not in outside and (y, x) not in set(pix)
                 and (y, x) not in tokpix]
        if inner:
            out.append(frozenset(_cells_of(inner, ox, oy)))
    return out


def _passable(entry, cell, ox, oy):
    c, r = cell
    x0, y0 = ox + 3 * c, oy + 3 * r
    if x0 < 0 or y0 < 0 or x0 + 2 >= len(entry[0]) or y0 + 2 >= BAR_ROW:
        return False
    return all(entry[y0 + dy][x0 + dx] not in (BG, WALL)
               for dy in range(3) for dx in range(3))


def _background(entry):
    ox, oy = _origin(entry)
    bg = [row[:] for row in entry]
    for (cells, _col, _d, _p) in parse_tokens(entry):
        for (c, r) in cells:
            for j in range(3):
                for i in range(3):
                    bg[oy + 3 * r + j][ox + 3 * c + i] = FLOOR
    for x in range(len(bg[0])):
        bg[BAR_ROW][x] = BAR_COLOR
    return bg


CD_A, CD_B = 12, 13          # two-tone gauge colours (c / d)


def _cd_info(pat):
    """A two-tone token is a COUNTDOWN gauge: the CD_B region shrinks one unit per action
    and WRAPS to full at 0. Returns (axis, side, k0, kmax) or None."""
    if not pat:
        return None
    d = dict(pat)
    cols = set(d.values())
    if not cols <= {CD_A, CD_B} or len(cols) < 1:
        return None
    W = max(i for i, j in d) + 1
    H = max(j for i, j in d) + 1
    rows_uniform = all(len({d[(i, j)] for i in range(W)}) == 1 for j in range(H))
    cols_uniform = all(len({d[(i, j)] for j in range(H)}) == 1 for i in range(W))
    if rows_uniform:
        bs = [j for j in range(H) if d[(0, j)] == CD_B]
        if not bs:
            return None
        side = "end" if bs[-1] == H - 1 else "start"
        return ("row", side, len(bs), H)
    if cols_uniform:
        bs = [i for i in range(W) if d[(i, 0)] == CD_B]
        if not bs:
            return None
        side = "start" if bs[0] == 0 else "end"
        return ("col", side, len(bs), W)
    return None


def _draw(g, t, sel, ox, oy, n=0):
    cells = set(t["cells"])
    c0 = min(c for c, r in cells)
    r0 = min(r for c, r in cells)
    if t.get("pat"):
        info = t.get("cd")
        if info:                                # COUNTDOWN gauge (k stored in the token)
            axis, side, kmax = info
            k = t.get("k") or kmax
            W = 3 * (max(c for c, r in cells) - c0 + 1)
            H = 3 * (max(r for c, r in cells) - r0 + 1)
            for j in range(H):
                for i in range(W):
                    a = j if axis == "row" else i
                    N = H if axis == "row" else W
                    if side == "start":
                        val = CD_B if a < k else CD_A
                    else:
                        val = CD_B if a >= N - k else CD_A
                    g[oy + 3 * r0 + j][ox + 3 * c0 + i] = val
            return
        for (key, val) in t["pat"]:
            i, j = key
            g[oy + 3 * r0 + j][ox + 3 * c0 + i] = val
        return
    w = max(c for c, r in cells) - c0 + 1
    h = max(r for c, r in cells) - r0 + 1
    x0, y0 = ox + 3 * c0, oy + 3 * r0
    for j in range(3 * h):
        for i in range(3 * w):
            g[y0 + j][x0 + i] = OUTLINE
    d = 0 if sel else t["v"] - (1 if t["u"] else 0)
    for j in range(h):
        for i in range(w):
            g[y0 + h + j][x0 + w + i] = d


def _render(entry, toks, sel, n, Ns):
    ox, oy = _origin(entry)
    g = _background(entry)
    occ = {}
    for i, t in enumerate(toks):
        for cell in t["cells"]:
            occ[cell] = i
    for i, t in enumerate(toks):
        _draw(g, t, i == sel, ox, oy, n)
    if sel is not None and 0 <= sel < len(toks):
        t = toks[sel]
        for (c, r) in t["cells"]:
            x0, y0 = ox + 3 * c, oy + 3 * r
            for (dc, dr) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                # a side lights up if ANY cell of this token has a foreign neighbour there
                if any(occ.get((cc + dc, rr + dr), sel) != sel for (cc, rr) in t["cells"]):
                    if occ.get((c + dc, r + dr), sel) == sel and (c + dc, r + dr) in t["cells"]:
                        continue
                    for k in range(3):
                        if dr == -1:
                            g[y0][x0 + k] = 0
                        elif dr == 1:
                            g[y0 + 2][x0 + k] = 0
                        elif dc == -1:
                            g[y0 + k][x0] = 0
                        else:
                            g[y0 + k][x0 + 2] = 0
    W = len(g[0])
    for i in range(min(_bar_pick(n, Ns), W)):
        g[BAR_ROW][W - 1 - i] = BAR_SPENT
    return g


def is_goal(state, grid):
    """Check against the TRACKED tokens: two touching tokens merge under parse_tokens,
    so re-parsing the grid can miss a token that has just landed next to another."""
    frames = parse_frames(ENTRY_GRID)
    if not frames:
        return False
    toks = (state or {}).get("toks")
    if toks:
        have = {frozenset(tuple(c) for c in t["cells"]) for t in toks}
    else:
        have = {cells for (cells, _c, _d, _p) in parse_tokens(grid)}
    return all(f in have for f in frames)


def _entry_cd():
    """axis/side/kmax per token SHAPE, taken from ENTRY_GRID where the split is unambiguous
    (a FULL gauge is uniform in both axes, so the live grid cannot tell you the axis)."""
    out = {}
    for (cells, col, digit, pat) in parse_tokens(ENTRY_GRID):
        if not pat:
            continue
        info = _cd_info(pat)
        if not info:
            continue
        cs = sorted(cells)
        c0 = min(c for c, r in cs); r0 = min(r for c, r in cs)
        w = max(c for c, r in cs) - c0 + 1
        h = max(r for c, r in cs) - r0 + 1
        out[(w, h)] = info
    return out


def _k_from_pat(pat, info):
    axis, side, _k0, kmax = info
    d = dict(pat)
    W = max(i for i, j in d) + 1
    H = max(j for i, j in d) + 1
    if axis == "row":
        units = [j for j in range(H) if d[(0, j)] == CD_B]
    else:
        units = [i for i in range(W) if d[(i, 0)] == CD_B]
    return len(units) or kmax


def init_state(entry_grid):
    lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    Ns = [BUDGETS[lvl]] if lvl in BUDGETS else list(BUDGET_RANGE)
    toks, sel = [], None
    for i, (cells, col, digit, pat) in enumerate(parse_tokens(entry_grid)):
        used = (digit == 0)
        if digit == 0:
            sel = i
        if digit is None:
            v = SOLID_VALUE_BY_LEVEL.get(lvl, DEFAULT_VALUE)
        elif digit == 0:
            v = START_VALUE_BY_LEVEL.get(lvl, DEFAULT_VALUE)
        else:
            v = digit
        pat2 = None if pat is None else sorted(pat.items())
        cd = None; kk = None
        if pat:
            cs = sorted(cells)
            c0 = min(c for c, r in cs); r0 = min(r for c, r in cs)
            w = max(c for c, r in cs) - c0 + 1
            h = max(r for c, r in cs) - r0 + 1
            info = _entry_cd().get((w, h))
            if info:
                cd = (info[0], info[1], info[3])
                kk = _k_from_pat(pat, info)
        toks.append({"cells": sorted(cells), "col": col, "v": v, "u": used,
                     "pat": pat2, "cd": cd, "k": kk})
    return {"n": 0, "toks": toks, "sel": sel, "Ns": Ns}


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {})
    entry = ENTRY_GRID
    ox, oy = _origin(entry)

    Ns = list(st.get("Ns") or BUDGET_RANGE)
    if len(Ns) == 1:
        b = _barcount(grid)
        cand = max(0, st.get("n", 0))
        while _bar_for(cand, Ns[0]) < b:
            cand += 1
        if _bar_for(cand, Ns[0]) == b:
            st["n"] = cand
    else:
        b = _barcount(grid)
        pruned = [N for N in Ns if _bar_for(st.get("n", 0), N) == b]
        if pruned:
            Ns = pruned
    st["Ns"] = Ns

    toks = [dict(t, cells=[tuple(c) for c in t["cells"]]) for t in (st.get("toks") or [])]
    sel = st.get("sel")

    # RESYNC: run_backtest skips the first-ever step, so state can lag the grid. Compare
    # OCCUPIED CELLS (robust: touching tokens merge under parse_tokens) and rebuild if off.
    gcells = set()
    for c in range((len(grid[0]) - ox) // 3):
        for r in range((BAR_ROW - oy) // 3):
            x0, y0 = ox + 3 * c, oy + 3 * r
            if any(grid[y0 + j][x0 + i] not in NONBG for j in range(3) for i in range(3)):
                gcells.add((c, r))
    scells = set()
    for t in toks:
        scells |= set(t["cells"])
    if scells != gcells:
        st2 = init_state(grid)
        toks = [dict(t, cells=[tuple(c) for c in t["cells"]]) for t in st2["toks"]]
        sel = st2["sel"]

    if not toks or sel is None:
        return [row[:] for row in grid], info, st

    occ = {}
    for i, t in enumerate(toks):
        for cell in t["cells"]:
            occ[cell] = i

    def finish(n):
        for t in toks:                          # every action ticks the countdown gauges
            if t.get("cd") and t.get("k"):
                kmax = t["cd"][2]
                t["k"] = t["k"] - 1 if t["k"] > 1 else kmax
        g = _render(entry, toks, sel, n, Ns)
        st.update({"toks": [dict(t, cells=[tuple(c) for c in t["cells"]]) for t in toks],
                   "sel": sel, "n": n, "Ns": Ns})
        if is_goal(st, g):
            info["level_up"] = True
        return g, info, st

    if action == 6:
        # A click ALWAYS costs an action. It selects only an OUTLINE token:
        # SOLID (colour 11) tokens are NOT selectable -- proven on level 3 (clicking the
        # plus left the previously selected token still showing 0).
        if x is not None and y is not None:
            tgt = occ.get(((x - ox) // 3, (y - oy) // 3))
            if tgt is not None and tgt != sel and toks[tgt]["col"] != SOLID:
                sel = tgt
                toks[tgt]["u"] = True
        return finish(st["n"] + 1)

    if action not in DIRS:
        return [row[:] for row in grid], info, st

    dc, dr = DIRS[action]
    me = toks[sel]
    dest = {(c + dc, r + dr) for (c, r) in me["cells"]}
    hit = {occ[cell] for cell in dest if cell in occ and occ[cell] != sel}

    if hit:
        # LAUNCH: the bumped token flies EXACTLY v cells; if that landing is not PASSABLE it
        # keeps going to the first PASSABLE landing (overshoot; never less than v). Occupancy
        # does NOT affect the landing.
        # SHOVE: any other token sitting in the landing area is pushed along the launch
        # direction to the first free PASSABLE position (this can cross a wall!).
        lim = len(grid[0]) + len(grid)
        for i in hit:
            v = toks[i]["v"]
            land = None
            for k in range(v, lim):                 # prefer to fly AT LEAST v (overshoot)
                cand = [(c + dc * k, r + dr * k) for (c, r) in toks[i]["cells"]]
                if all(_passable(entry, cell, ox, oy) for cell in cand):
                    land = cand
                    break
            if land is None:                        # ...else go as FAR AS IT CAN (k < v)
                for k in range(v - 1, 0, -1):
                    cand = [(c + dc * k, r + dr * k) for (c, r) in toks[i]["cells"]]
                    if all(_passable(entry, cell, ox, oy) for cell in cand):
                        land = cand
                        break
            if land is None:
                continue
            toks[i]["cells"] = land
            landset = set(land)
            for j, t in enumerate(toks):
                if j == i or not (set(t["cells"]) & landset):
                    continue
                for d in range(1, lim):
                    cand = [(c + dc * d, r + dr * d) for (c, r) in t["cells"]]
                    blocked = set()
                    for q, u in enumerate(toks):
                        if q != j:
                            blocked |= set(u["cells"])
                    if all(_passable(entry, cell, ox, oy) for cell in cand) \
                            and not (set(cand) & blocked):
                        t["cells"] = cand
                        break
        return finish(st["n"] + 1)

    if not all(_passable(entry, cell, ox, oy) for cell in dest):
        return finish(st["n"] + 1)          # BLOCKED move still costs an action

    me["cells"] = [(c + dc, r + dr) for (c, r) in me["cells"]]
    return finish(st["n"] + 1)
