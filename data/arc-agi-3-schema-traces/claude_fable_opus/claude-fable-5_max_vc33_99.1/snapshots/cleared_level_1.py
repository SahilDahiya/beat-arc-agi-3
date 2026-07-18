# vc33 world model — v7 (general hydraulics)
# SCENE: x is "height". sky side = where 9-valves sit (L0: right/x63, L1: left/x0).
#   Rods (color-5 row bands) split rows into SECTIONS (water tanks).
#   Section water: green(3) on floor side of boundary L, black(0) on sky side.
#   Valves: 4x4 9-blocks at sky edge, each adjacent (row-wise) to a rod.
#     Press valve => ITS section loses 4 columns of water across that rod (other side gains 4).
#     (blocked in model if either new L out of [0,64])
#   Float: 4-body + tail (color 11 or 14) embedded at a section surface; rides that surface.
#   Gate: 11/14-colored column-pair embedded in a rod.
# WIN (= level_up): after a press, float tail columns == gate columns (color-matched).
#   Confirmed L0: gate b(11) at x38-39, win when L_bot=40 put tail exactly there.
# TIMER row0: total consumed after n clicks = (13n+4)//10; stateless inverse n=(10t+5)//13.
# Unknown: bar-empty consequence; real overflow/underflow behavior (model blocks at [0,64]).

def _parse(eg):
    rod_rows = [yy for yy in range(1, 64) if any(v == 5 for v in eg[yy])]
    rods = []
    for r in rod_rows:
        if rods and r == rods[-1][1] + 1:
            rods[-1][1] = r
        else:
            rods.append([r, r])
    bands = []
    prev = 1
    for (a, b) in rods:
        if a > prev:
            bands.append((prev, a - 1))
        prev = b + 1
    if prev <= 63:
        bands.append((prev, 63))
    nine = [(xx, yy) for yy in range(64) for xx in range(64) if eg[yy][xx] == 9]
    sky_left = any(xx < 32 for (xx, yy) in nine) if nine else False
    # valve components (assume rectangular blocks)
    comps = []
    seen = set()
    nset = set(nine)
    for cell in nine:
        if cell in seen:
            continue
        stack = [cell]
        comp = []
        seen.add(cell)
        while stack:
            (cx, cy) = stack.pop()
            comp.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (cx + dx, cy + dy)
                if nb in nset and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        xs = [c[0] for c in comp]; ys = [c[1] for c in comp]
        comps.append((min(xs), max(xs), min(ys), max(ys)))
    def band_of(row):
        for i, (a, b) in enumerate(bands):
            if a <= row <= b:
                return i
        return None
    valves = []
    for (x0, x1, y0, y1) in comps:
        src = band_of(y0)
        rod_i = None
        for i, (a, b) in enumerate(rods):
            if y1 + 1 == a or y0 - 1 == b:
                rod_i = i
                break
        if rod_i is None or src is None:
            continue
        a, b = rods[rod_i]
        other_row = b + 1 if y1 + 1 == a else a - 1
        dst = band_of(other_row)
        valves.append({"bbox": (x0, x1, y0, y1), "src": src, "dst": dst})
    gates = []
    for i, (a, b) in enumerate(rods):
        run = []
        for xx in range(64):
            if eg[a][xx] in (11, 14):
                run.append(xx)
        if run:
            gates.append({"rod": i, "cols": tuple(run), "color": eg[a][run[0]]})
    # float: 4s and 11/14 outside rod rods
    rodset = set()
    for (a, b) in rods:
        for r in range(a, b + 1):
            rodset.add(r)
    fcells = [(xx, yy) for yy in range(1, 64) for xx in range(64)
              if yy not in rodset and eg[yy][xx] in (4, 11, 14)]
    flt = None
    if fcells:
        fband = band_of(fcells[0][1])
        L0 = _level(eg, bands[fband], sky_left, eg)
        cells = [(yy, xx - L0, eg[yy][xx]) for (xx, yy) in fcells]
        tail_dx = sorted(dx for (_, dx, c) in cells if c in (11, 14))
        tcol = [c for (_, dx, c) in cells if c in (11, 14)][0]
        flt = {"band": fband, "cells": cells, "tail_dx": sorted(set(tail_dx)), "tcolor": tcol}
    return {"rods": rods, "bands": bands, "sky_left": sky_left,
            "valves": valves, "gates": gates, "float": flt}

def _clean_row(g, band, eg):
    a, b = band
    for yy in range(a, b + 1):
        if all(eg[yy][xx] in (0, 3) for xx in range(64)):
            return yy
    return a

def _level(g, band, sky_left, eg):
    yy = _clean_row(g, band, eg)
    row = g[yy]
    if sky_left:
        for xx in range(64):
            if row[xx] == 3:
                return xx
        return 64
    else:
        for xx in range(64):
            if row[xx] == 0:
                return xx
        return 64

def _aligned(P, levels):
    flt = P["float"]
    if flt is None or not P["gates"]:
        return False
    L = levels[flt["band"]]
    tail = tuple(sorted(L + dx for dx in flt["tail_dx"]))
    for gt in P["gates"]:
        if tail == gt["cols"] and gt["color"] == flt["tcolor"]:
            return True
    return False

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return g, info
    P = _parse(ENTRY_GRID)
    levels = [_level(grid, bd, P["sky_left"], ENTRY_GRID) for bd in P["bands"]]
    if grid[y][x] == 9:
        hit = None
        for v in P["valves"]:
            (x0, x1, y0, y1) = v["bbox"]
            if x0 <= x <= x1 and y0 <= y <= y1:
                hit = v
                break
        if hit is not None and hit["dst"] is not None:
            s, d = hit["src"], hit["dst"]
            sgn = 1 if P["sky_left"] else -1     # losing water moves L toward sky-opposite
            nLs = levels[s] + 4 * sgn
            nLd = levels[d] - 4 * sgn
            if 0 <= nLs <= 64 and 0 <= nLd <= 64:
                levels = list(levels)
                levels[s], levels[d] = nLs, nLd
                for bi in (s, d):
                    a, b = P["bands"][bi]
                    L = levels[bi]
                    for yy in range(a, b + 1):
                        for xx in range(64):
                            if P["sky_left"]:
                                g[yy][xx] = 3 if xx >= L else 0
                            else:
                                g[yy][xx] = 3 if xx < L else 0
                    # re-stamp valves in this band
                    for v2 in P["valves"]:
                        (vx0, vx1, vy0, vy1) = v2["bbox"]
                        if a <= vy0 <= b:
                            for yy in range(vy0, vy1 + 1):
                                for xx in range(vx0, vx1 + 1):
                                    g[yy][xx] = 9
                    flt = P["float"]
                    if flt is not None and flt["band"] == bi:
                        for (yy, dx, c) in flt["cells"]:
                            nx = L + dx
                            if 0 <= nx < 64:
                                g[yy][nx] = c
                if _aligned(P, levels):
                    info["level_up"] = True
                    if CURRENT_LEVEL == 6:
                        info["win"] = True
    # timer drain
    t = sum(1 for v in grid[0] if v != 7)
    n = (10 * t + 5) // 13
    cost = (13 * (n + 1) + 4) // 10 - t
    m = 0
    for i in range(63, -1, -1):
        if m >= cost:
            break
        if g[0][i] == 7:
            g[0][i] = 4
            m += 1
    return g, info

def is_goal(grid):
    P = _parse(ENTRY_GRID)
    levels = [_level(grid, bd, P["sky_left"], ENTRY_GRID) for bd in P["bands"]]
    return _aligned(P, levels)
