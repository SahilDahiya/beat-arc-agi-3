"""World model (general, levels 0-5).

LATTICE: 3x3 px cells; the ORIGIN OFFSET is detected from the entry grid.
  cell(c,r) -> px x=ox+3c, y=oy+3r.

TOKENS: an arbitrary SET OF CELLS.
  * OUTLINE (colour 14): rectangular w x h box, DIGIT as a w x h px block at (+w,+h).
  * PATTERN (any other colour): redrawn from a stored pixel pattern.
  Each token has an IMMUTABLE INTRINSIC value v (= cells it flies when LAUNCHED).
  DISPLAYED digit = intrinsic - (1 if EVER selected else 0); the SELECTED token shows 0
  (so the selected token's v cannot be read off the screen -- it is pinned per level).

ACTIONS  1=U 2=D 3=L 4=R move the SELECTED token 1 cell; 6=click selects an OUTLINE token.
  BUMP: moving into another token does NOT move the pusher -- the bumped token LAUNCHES.
  LAUNCH: fly >= v (first PASSABLE landing, straight THROUGH walls), else as far as it can
          (k < v fallback).  A landing IGNORES occupancy: occupants are SHOVED along.
  A BLOCKED move still costs an action.

COUNTDOWN GAUGES (two-tone 12/13): the 13-region is the FUSE; it shrinks one unit per MOVE
  (clicks do NOT tick it) and WRAPS to full at 0.
  *** ON WRAP THE GAUGE FIRES: it LAUNCHES any token standing IMMEDIATELY ADJACENT on its
      MUZZLE side -- the side the 13-region sits on -- away from itself, by THAT TOKEN's v. ***
  Range is exactly 1 cell: aligned-but-distant tokens are untouched, and the non-muzzle
  sides are safe.  Firing is a BUMP delivered by the gauge, so it reuses the launch rule
  (overshoot, wall-piercing, shove) verbatim.
  A FULL gauge is uniform, so its axis/side cannot be read from pixels: fall back to the
  geometry (the muzzle faces the only PASSABLE side), then re-read it from the live grid as
  soon as the fuse burns down.

FRAMES: colour-4 outlines; GOAL = every frame's interior exactly covered by a token.
BAR (row 63): zeros = round(64*n/budget); the budget is PER-LEVEL.
"""

FLOOR, BG, WALL, FRAME = 1, 2, 15, 4
OUTLINE, SOLID = 14, 11
CD_A, CD_B = 12, 13                      # gauge body / FUSE colours
BAR_ROW, BAR_COLOR, BAR_SPENT = 63, 4, 0
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
NONBG = (FLOOR, BG, WALL, FRAME)
BUDGETS = {0: 100, 1: 128, 2: 100, 3: 128, 4: 100, 5: 150, 6: 200}
BUDGET_RANGE = list(range(90, 401))      # unknown levels: pruned against the bar each step
# L6 observed (n,zeros)=(1,0),(2,1),(3,1),(4,1) -> B in [171,256]; keep the range WIDE enough
# to contain it (a budget outside the range silently corrupts every bar prediction).
SOLID_VALUE_BY_LEVEL = {}
START_VALUE_BY_LEVEL = {4: 3, 6: 4}      # the selected token hides its digit -> pin from data
# (L6: V was fired UP by G2 from (15,14) and travelled 4, not 5 -> its intrinsic v is 4.)
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
    for pix in _pix_comps(entry, lambda v: v not in NONBG):
        ys = [p[0] for p in pix]
        xs = [p[1] for p in pix]
        return min(xs) % 3, min(ys) % 3
    return 0, 0


def _cells_of(pix, ox, oy):
    return {((x - ox) // 3, (y - oy) // 3) for (y, x) in pix}


def _box(cells):
    cs = sorted(cells)
    c0 = min(c for c, r in cs)
    r0 = min(r for c, r in cs)
    c1 = max(c for c, r in cs)
    r1 = max(r for c, r in cs)
    return c0, r0, c1 - c0 + 1, r1 - r0 + 1


def parse_tokens(entry):
    """[(cells frozenset, colour, digit or None, pattern)] from a CLEAN grid."""
    ox, oy = _origin(entry)
    out = []
    for pix in _pix_comps(entry, lambda v: v not in NONBG):
        cols = {entry[y][x] for (y, x) in pix}
        cells = _cells_of(pix, ox, oy)
        c0, r0, w, h = _box(cells)
        if OUTLINE in cols:
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


# ---------------------------------------------------------------- gauges

def _gauge_read(d, W, H):
    """(axis, side, kmax, k) from a two-tone pixel map, or None when it is UNIFORM
    (a full/empty fuse is uniform in both axes, so it pins neither axis nor side)."""
    cols = set(d.values())
    if not cols <= {CD_A, CD_B} or len(cols) < 2:
        return None
    rows_u = all(len({d[(i, j)] for i in range(W)}) == 1 for j in range(H))
    cols_u = all(len({d[(i, j)] for j in range(H)}) == 1 for i in range(W))
    if rows_u:
        bs = [j for j in range(H) if d[(0, j)] == CD_B]
        if not bs:
            return None
        return ("row", "end" if bs[-1] == H - 1 else "start", H, len(bs))
    if cols_u:
        bs = [i for i in range(W) if d[(i, 0)] == CD_B]
        if not bs:
            return None
        return ("col", "end" if bs[-1] == W - 1 else "start", W, len(bs))
    return None


def _gauge_geom(entry, cells, ox, oy):
    """A FULL gauge is uniform -> read the muzzle off the LAYOUT: it faces the open side."""
    _c0, _r0, w, h = _box(cells)
    op = {}
    for name, (dc, dr) in (("U", (0, -1)), ("D", (0, 1)), ("L", (-1, 0)), ("R", (1, 0))):
        strip = [p for p in ((c + dc, r + dr) for (c, r) in cells) if p not in cells]
        op[name] = bool(strip) and all(_passable(entry, p, ox, oy) for p in strip)
    vert = int(op["U"]) + int(op["D"])
    horz = int(op["L"]) + int(op["R"])
    if vert == 1 and horz != 1:
        return ("row", "end" if op["D"] else "start", 3 * h)
    if horz == 1 and vert != 1:
        return ("col", "end" if op["R"] else "start", 3 * w)
    if vert == 1:
        return ("row", "end" if op["D"] else "start", 3 * h)
    if horz == 1:
        return ("col", "end" if op["R"] else "start", 3 * w)
    return ("row", "end", 3 * h)


def _cd_setup(entry, cells, pat, ox, oy):
    """(cd=(axis,side,kmax), k) for a two-tone token, else (None, None)."""
    if not pat or not set(pat.values()) <= {CD_A, CD_B}:
        return None, None
    _c0, _r0, w, h = _box(cells)
    info = _gauge_read(pat, 3 * w, 3 * h)
    if info:
        return (info[0], info[1], info[2]), info[3]
    cd = _gauge_geom(entry, cells, ox, oy)
    return cd, cd[2]                      # uniform => the fuse is FULL


def _fire_dir(cd):
    axis, side, _kmax = cd
    if axis == "row":
        return (0, 1) if side == "end" else (0, -1)
    return (1, 0) if side == "end" else (-1, 0)


# ---------------------------------------------------------------- rendering

def _draw(g, t, sel, ox, oy):
    cells = set(t["cells"])
    c0, r0, w, h = _box(cells)
    if t.get("pat"):
        cd = t.get("cd")
        if cd:                                    # gauge: paint the fuse from t["k"]
            axis, side, kmax = cd
            k = t.get("k") or kmax
            W, H = 3 * w, 3 * h
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
        _draw(g, t, i == sel, ox, oy)
    if sel is not None and 0 <= sel < len(toks):
        t = toks[sel]
        for (c, r) in t["cells"]:
            x0, y0 = ox + 3 * c, oy + 3 * r
            for (dc, dr) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                if any(occ.get((cc + dc, rr + dr), sel) != sel for (cc, rr) in t["cells"]):
                    if (c + dc, r + dr) in t["cells"]:
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
    frames = parse_frames(ENTRY_GRID)
    if not frames:
        return False
    toks = (state or {}).get("toks")
    if toks:
        have = {frozenset(tuple(c) for c in t["cells"]) for t in toks}
    else:
        have = {cells for (cells, _c, _d, _p) in parse_tokens(grid)}
    return all(f in have for f in frames)


def init_state(entry_grid):
    lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    Ns = [BUDGETS[lvl]] if lvl in BUDGETS else list(BUDGET_RANGE)
    ox, oy = _origin(entry_grid)
    toks, sel = [], None
    for i, (cells, col, digit, pat) in enumerate(parse_tokens(entry_grid)):
        used = False
        if digit == 0:
            sel = i
            v = START_VALUE_BY_LEVEL.get(lvl, DEFAULT_VALUE)
        elif digit is None:
            v = SOLID_VALUE_BY_LEVEL.get(lvl, DEFAULT_VALUE)
        else:
            v = digit
        cd, kk = _cd_setup(entry_grid, cells, pat, ox, oy)
        toks.append({"cells": sorted(cells), "col": col, "v": v, "u": used,
                     "pat": None if pat is None else sorted(pat.items()),
                     "cd": cd, "k": kk})
    return {"n": 0, "toks": toks, "sel": sel, "Ns": Ns}


def _launch(toks, i, dc, dr, entry, ox, oy, lim):
    """The one and only launch rule -- used by BUMPS and by GAUGE FIRE alike."""
    v = toks[i]["v"]
    land = None
    for k in range(v, lim):                      # fly AT LEAST v (overshoot past walls)
        cand = [(c + dc * k, r + dr * k) for (c, r) in toks[i]["cells"]]
        if all(_passable(entry, cell, ox, oy) for cell in cand):
            land = cand
            break
    if land is None:                             # ...else as FAR AS IT CAN (k < v)
        for k in range(v - 1, 0, -1):
            cand = [(c + dc * k, r + dr * k) for (c, r) in toks[i]["cells"]]
            if all(_passable(entry, cell, ox, oy) for cell in cand):
                land = cand
                break
    if land is None:
        return
    toks[i]["cells"] = land
    landset = set(land)
    for j, t in enumerate(toks):                 # SHOVE whoever sat in the landing
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


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {})
    entry = ENTRY_GRID
    ox, oy = _origin(entry)
    lim = len(grid[0]) + len(grid)

    Ns = list(st.get("Ns") or BUDGET_RANGE)
    b = _barcount(grid)
    if len(Ns) == 1:
        cand = max(0, st.get("n", 0))
        while _bar_for(cand, Ns[0]) < b:
            cand += 1
        if _bar_for(cand, Ns[0]) == b:
            st["n"] = cand
    else:
        pruned = [N for N in Ns if _bar_for(st.get("n", 0), N) == b]
        if pruned:
            Ns = pruned
    st["Ns"] = Ns

    toks = [dict(t, cells=[tuple(c) for c in t["cells"]]) for t in (st.get("toks") or [])]
    sel = st.get("sel")

    gcells = set()
    for c in range((len(grid[0]) - ox) // 3):
        for r in range((BAR_ROW - oy) // 3):
            x0, y0 = ox + 3 * c, oy + 3 * r
            if any(grid[y0 + j][x0 + i] not in NONBG for j in range(3) for i in range(3)):
                gcells.add((c, r))
    scells = set()
    for t in toks:
        scells |= set(t["cells"])
    if scells != gcells:                          # state lags the grid -> rebuild
        st2 = init_state(grid)
        toks = [dict(t, cells=[tuple(c) for c in t["cells"]]) for t in st2["toks"]]
        sel = st2["sel"]

    if not toks or sel is None:
        return [row[:] for row in grid], info, st

    # RE-READ every gauge off the LIVE grid: fuse level, and (once it is burning) the
    # axis/side that a full gauge could not reveal.
    for t in toks:
        if not t.get("cd"):
            continue
        c0, r0, w, h = _box(t["cells"])
        W, H = 3 * w, 3 * h
        d = {}
        for j in range(H):
            for i in range(W):
                d[(i, j)] = grid[oy + 3 * r0 + j][ox + 3 * c0 + i]
        live = _gauge_read(d, W, H)
        if live:
            t["cd"] = (live[0], live[1], live[2])
            t["k"] = live[3]
        else:
            t["k"] = t["cd"][2]                   # uniform => full fuse

    occ = {}
    for i, t in enumerate(toks):
        for cell in t["cells"]:
            occ[cell] = i

    def finish(n, tick=True):
        if tick:                                  # only MOVES burn the fuses
            fired = []
            for t in toks:
                if not t.get("cd"):
                    continue
                kmax = t["cd"][2]
                k = t.get("k") or kmax
                if k > 1:
                    t["k"] = k - 1
                else:
                    t["k"] = kmax
                    fired.append(t)
            for gg in fired:                      # FIRE: a bump delivered by the gauge
                dc, dr = _fire_dir(gg["cd"])
                gc = set(gg["cells"])
                beam = {(c + dc, r + dr) for (c, r) in gc} - gc
                for i, t in enumerate(toks):
                    if t is gg:
                        continue
                    if set(t["cells"]) & beam:
                        _launch(toks, i, dc, dr, entry, ox, oy, lim)
        g = _render(entry, toks, sel, n, Ns)
        st.update({"toks": [dict(t, cells=[tuple(c) for c in t["cells"]]) for t in toks],
                   "sel": sel, "n": n, "Ns": Ns})
        if is_goal(st, g):
            info["level_up"] = True
        return g, info, st

    if action == 6:
        if x is not None and y is not None:
            tgt = occ.get(((x - ox) // 3, (y - oy) // 3))
            if tgt is not None and tgt != sel and toks[tgt]["col"] == OUTLINE:
                sel = tgt
                toks[tgt]["u"] = True
        return finish(st["n"] + 1, tick=False)    # a click does NOT burn the fuses

    if action not in DIRS:
        return [row[:] for row in grid], info, st

    dc, dr = DIRS[action]
    me = toks[sel]
    dest = {(c + dc, r + dr) for (c, r) in me["cells"]}
    hit = {occ[cell] for cell in dest if cell in occ and occ[cell] != sel}

    if hit:                                       # BUMP: the pusher stays put
        for i in hit:
            _launch(toks, i, dc, dr, entry, ox, oy, lim)
        return finish(st["n"] + 1)

    if not all(_passable(entry, cell, ox, oy) for cell in dest):
        return finish(st["n"] + 1)                # a BLOCKED move still costs an action

    me["cells"] = [(c + dc, r + dr) for (c, r) in me["cells"]]
    return finish(st["n"] + 1)
