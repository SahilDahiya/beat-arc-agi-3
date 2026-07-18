# vc33 world model — v8 (general hydraulics, any orientation)
# CONFIRMED (L0, L1 cleared):
#  - Scene: sections (tanks) split by rods; green(3)=water on floor side, black(0)=air on sky side.
#  - Valves (9-blocks) sit at sky edge, each adjacent to a rod: press => its own section loses
#    `step` units of water across that rod; other side gains the same. step was 4 in L0/L1 (rod 4 thick).
#  - Floats (4-body + tail color 11/14/15) ride their section's surface at fixed offsets.
#  - Gates: tail-colored cells embedded in a rod. SINGLE-float levels: tail cols == gate cols => level_up.
# L2 NEW: vertical rods (whole scene rotated 90) -> handled by transposing; yellow(4) frame ->
#  interior box from non-{4,7} cells (rows>=1); rods 2 thick + 2x2 valves -> step = rod thickness (GUESS);
#  THREE floats/gates: what alignment does is UNKNOWN -> model predicts plain redraw, no flags
#  (deliberate: the real event will mispredict and teach us).
# TIMER row0 (original orientation): total consumed after n clicks = (13n+4)//10 (stateless inverse).
# Unknown: bar-empty consequence; cap behavior at box edges (model blocks presses beyond [lo,hi+1]).

TAILC = (11, 14, 15)

def _transpose(g):
    return [list(r) for r in zip(*g)]

def _is_vertical(eg):
    xs, ys = set(), set()
    for yy in range(64):
        for xx in range(64):
            if eg[yy][xx] == 5:
                xs.add(xx); ys.add(yy)
    if not xs:
        return False
    return len(ys) > len(xs)

_PCACHE = {}

def _parse(eg):
    key = (len(eg), sum(eg[1]) * 131071 + sum(eg[33]) * 8191 + sum(eg[62]),
           tuple(eg[30][::4]), tuple(eg[50][::4]))
    hit = _PCACHE.get(key)
    if hit is not None:
        return hit
    P = _parse_impl(eg)
    if len(_PCACHE) > 32:
        _PCACHE.clear()
    _PCACHE[key] = P
    return P

def _parse_impl(eg):
    # eg is oriented so rods are horizontal (row bands)
    r0 = c0 = 64; r1 = c1 = -1
    for yy in range(1, 64):
        for xx in range(64):
            if eg[yy][xx] not in (4, 7):
                if yy < r0: r0 = yy
                if yy > r1: r1 = yy
                if xx < c0: c0 = xx
                if xx > c1: c1 = xx
    rodrows = [yy for yy in range(r0, r1 + 1)
               if any(eg[yy][xx] == 5 for xx in range(c0, c1 + 1))]
    rods = []
    for r in rodrows:
        if rods and r == rods[-1][1] + 1:
            rods[-1][1] = r
        else:
            rods.append([r, r])
    bands = []
    prev = r0
    for (a, b) in rods:
        if a > prev:
            bands.append((prev, a - 1))
        prev = b + 1
    if prev <= r1:
        bands.append((prev, r1))
    def band_of(row):
        for i, (a, b) in enumerate(bands):
            if a <= row <= b:
                return i
        return None
    nine = set()
    for yy in range(r0, r1 + 1):
        for xx in range(c0, c1 + 1):
            if eg[yy][xx] == 9:
                nine.add((xx, yy))
    sky_left = False
    if nine:
        mx = sum(p[0] for p in nine) / len(nine)
        sky_left = mx < (c0 + c1) / 2.0
    comps = []
    seen = set()
    for cell in sorted(nine):
        if cell in seen:
            continue
        stack = [cell]; seen.add(cell); comp = []
        while stack:
            (ax, ay) = stack.pop(); comp.append((ax, ay))
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nb = (ax+dx, ay+dy)
                if nb in nine and nb not in seen:
                    seen.add(nb); stack.append(nb)
        xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
        comps.append((min(xs), max(xs), min(ys), max(ys)))
    valves = []
    for (x0, x1, y0, y1) in comps:
        src = band_of(y0)
        rod_i = None
        for i, (a, b) in enumerate(rods):
            if y1 + 1 == a or y0 - 1 == b:
                rod_i = i; break
        if rod_i is None or src is None:
            continue
        a, b = rods[rod_i]
        other = b + 1 if y1 + 1 == a else a - 1
        valves.append({"bbox": (x0, x1, y0, y1), "src": src, "dst": band_of(other),
                       "step": b - a + 1})
    gates = []
    for i, (a, b) in enumerate(rods):
        for col in TAILC:
            cols = sorted(set(xx for yy in range(a, b + 1) for xx in range(c0, c1 + 1)
                              if eg[yy][xx] == col))
            if cols:
                gates.append({"rod": i, "cols": tuple(cols), "color": col})
    rodset = set()
    for (a, b) in rods:
        for r in range(a, b + 1):
            rodset.add(r)
    fcells = set()
    for yy in range(r0, r1 + 1):
        if yy in rodset:
            continue
        for xx in range(c0, c1 + 1):
            if eg[yy][xx] in (4,) + TAILC:
                fcells.add((xx, yy))
    floats = []
    seen = set()
    for cell in sorted(fcells):
        if cell in seen:
            continue
        stack = [cell]; seen.add(cell); comp = []
        while stack:
            (ax, ay) = stack.pop(); comp.append((ax, ay))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (ax + dx, ay + dy)
                    if nb in fcells and nb not in seen:
                        seen.add(nb); stack.append(nb)
        bi = band_of(comp[0][1])
        floats.append({"band": bi, "raw": comp})
    P = {"box": (r0, r1, c0, c1), "rods": rods, "bands": bands, "sky_left": sky_left,
         "valves": valves, "gates": gates, "floats": floats}
    levels = _levels(eg, P, eg)
    for f in floats:
        L = levels[f["band"]]
        f["cells"] = [(yy, xx - L, eg[yy][xx]) for (xx, yy) in f["raw"]]
        tl = [(xx - L, eg[yy][xx]) for (xx, yy) in f["raw"] if eg[yy][xx] in TAILC]
        f["tail_dx"] = sorted(set(d for (d, c) in tl))
        f["tcolor"] = tl[0][1] if tl else None
    return P

def _clean_row(g, band, P, eg):
    (r0, r1, c0, c1) = P["box"]
    a, b = band
    for yy in range(a, b + 1):
        ok = True
        for xx in range(c0, c1 + 1):
            if eg[yy][xx] not in (0, 3):
                ok = False; break
        if ok:
            return yy
    return a

def _levels(g, P, eg):
    (r0, r1, c0, c1) = P["box"]
    out = []
    for band in P["bands"]:
        yy = _clean_row(g, band, P, eg)
        row = g[yy]
        L = c1 + 1
        if P["sky_left"]:
            for xx in range(c0, c1 + 1):
                if row[xx] == 3:
                    L = xx; break
        else:
            for xx in range(c0, c1 + 1):
                if row[xx] == 0:
                    L = xx; break
        out.append(L)
    return out

def _aligned_floats(P, levels):
    out = []
    for f in P["floats"]:
        L = levels[f["band"]]
        tail = tuple(sorted(L + dx for dx in f["tail_dx"]))
        hit = any(tail == gt["cols"] and gt["color"] == f["tcolor"] for gt in P["gates"])
        out.append(hit)
    return out

def _core(wg, weg, cx, cy, P):
    # returns (changed?, levels_after) ; edits wg in place
    (r0, r1, c0, c1) = P["box"]
    levels = _levels(wg, P, weg)
    if wg[cy][cx] != 9:
        return False, levels
    hit = None
    for v in P["valves"]:
        (x0, x1, y0, y1) = v["bbox"]
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            hit = v; break
    if hit is None or hit["dst"] is None:
        return False, levels
    s, d, st = hit["src"], hit["dst"], hit["step"]
    sgn = 1 if P["sky_left"] else -1
    nLs = levels[s] + st * sgn
    nLd = levels[d] - st * sgn
    lo, hi = c0, c1 + 1
    if not (lo <= nLs <= hi and lo <= nLd <= hi):
        return False, levels
    levels = list(levels)
    levels[s], levels[d] = nLs, nLd
    for bi in (s, d):
        a, b = P["bands"][bi]
        L = levels[bi]
        for yy in range(a, b + 1):
            for xx in range(c0, c1 + 1):
                if P["sky_left"]:
                    wg[yy][xx] = 3 if xx >= L else 0
                else:
                    wg[yy][xx] = 3 if xx < L else 0
        for v2 in P["valves"]:
            (vx0, vx1, vy0, vy1) = v2["bbox"]
            if a <= vy0 <= b:
                for yy in range(vy0, vy1 + 1):
                    for xx in range(vx0, vx1 + 1):
                        wg[yy][xx] = 9
        for f in P["floats"]:
            if f["band"] == bi:
                for (yy, dx, c) in f["cells"]:
                    nx = L + dx
                    if c0 <= nx <= c1:
                        wg[yy][nx] = c
    return True, levels

def _bar_total(level, n):
    # per-level drain schedule: total consumed after n clicks (empirical)
    if level in (0, 1):
        return (13 * n + 4) // 10
    if level == 2:
        return (6 * n + 3) // 7   # refit x2: totals 1,2,3,3,4,5,6,7,8,9,9 (zeros at n=4,11)
    return n  # default guess for unseen levels: 1/click

def init_state(entry_grid):
    return {"n": 0}

def predict(state, grid, action, x=None, y=None):
    ns = dict(state)
    g, info = _step_impl(grid, action, x, y, ns)
    return g, info, ns

def _step_impl(grid, action, x, y, ns):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return g, info
    vert = _is_vertical(ENTRY_GRID)
    if vert:
        wg = _transpose(g); weg = _transpose(ENTRY_GRID); cx, cy = y, x
    else:
        wg = g; weg = ENTRY_GRID; cx, cy = x, y
    P = _parse(weg)
    changed, levels = _core(wg, weg, cx, cy, P)
    if vert:
        g = _transpose(wg)
    else:
        g = wg
    # WIN = ALL floats aligned with their color-matched gates SIMULTANEOUSLY
    # (confirmed: single f-float alignment in L2 triggered nothing; L0/L1 single-float wins consistent)
    if changed and P["floats"] and all(_aligned_floats(P, levels)):
        info["level_up"] = True
        if CURRENT_LEVEL == 6:
            info["win"] = True
    # timer drain on original row 0 — LEVEL-DEPENDENT schedule, click-indexed (state n),
    # resynced from the visible bar when they disagree (covers the skipped #0 quirk).
    lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    t = sum(1 for v in grid[0] if v != 7)
    n = ns.get("n", 0)
    if _bar_total(lvl, n) != t:
        m = 0
        while m < 200 and _bar_total(lvl, m) != t:
            m += 1
        n = m if m < 200 else n
    cost = _bar_total(lvl, n + 1) - t
    ns["n"] = n + 1
    m = 0
    for i in range(63, -1, -1):
        if m >= cost:
            break
        if g[0][i] == 7:
            g[0][i] = 4
            m += 1
    return g, info

def is_goal(grid):
    vert = _is_vertical(ENTRY_GRID)
    wg = _transpose(grid) if vert else [row[:] for row in grid]
    weg = _transpose(ENTRY_GRID) if vert else ENTRY_GRID
    P = _parse(weg)
    if not P["floats"]:
        return False
    levels = _levels(wg, P, weg)
    return all(_aligned_floats(P, levels))
