# vc33 world model — v9 (hydraulics + doors + traveling floats)
# CONFIRMED MECHANICS (L0-L3):
#  - Scene splits into SECTIONS (tanks) by rods (color 5 bands); vertical scenes are transposed
#    so rods are horizontal; interior box = bbox of non-{4,7} cells (excludes timer + frame).
#  - Water: green(3) floor-side, black(0) sky-side; sky side = where 9-valves sit.
#  - Valve press: its section loses `step`=rod-thickness units across the adjacent rod (other gains);
#    blocked if either level would leave [lo, hi+1].
#  - Floats: 4-body + tail (color 11/14/15), ride their section's surface; located from CURRENT grid.
#  - Gates: tail-colored cells embedded in a rod. WIN (level_up): EVERY float aligned: tail cols ==
#    gate cols, color match, float's band ADJACENT to gate's rod (adjacency inferred L3; true L0-L2).
#  - DOORS (L3+): blue(1) segment in a rod. OPEN iff adjacent levels EQUAL (variant A; stateless).
#    Open render: segment -> cyan(12); black channel cells at band-rows rod_r0-2 & rod_r1+2,
#    T-cols [door_lo+2 .. door_hi-2]. Closed: segment -> 1, channel cells revert to water rule.
#    Clicking an OPEN door while a float (in an adjacent band) fits inside the door's col-span
#    teleports the float to the other adjacent band, CENTERED in that band, riding its surface.
#  - TIMER row0: level-specific totals after n clicks (state n, resync from bar when off):
#    L0/L1/L3: (13n+4)//10 ; L2: (6n+3)//7 ; unseen: n.
# Unknown: door variant (pure equality vs +submerged/fit); bar-empty consequence.

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
    r0 = c0 = 64; r1 = c1 = -1
    for yy in range(0, 64):
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
    doors = []
    for i, (a, b) in enumerate(rods):
        for col in TAILC:
            cols = sorted(set(xx for yy in range(a, b + 1) for xx in range(c0, c1 + 1)
                              if eg[yy][xx] == col))
            if cols:
                gates.append({"rod": i, "cols": tuple(cols), "color": col})
        dcols = sorted(set(xx for yy in range(a, b + 1) for xx in range(c0, c1 + 1)
                           if eg[yy][xx] in (1, 12)))
        if dcols:
            doors.append({"rod": i, "lo": dcols[0], "hi": dcols[-1],
                          "up": band_of(a - 1), "dn": band_of(b + 1)})
    rodset = set()
    for (a, b) in rods:
        for r in range(a, b + 1):
            rodset.add(r)
    # float SHAPES from entry: offsets relative to (min_row, band entry level)
    fcells = {}
    for yy in range(r0, r1 + 1):
        if yy in rodset:
            continue
        for xx in range(c0, c1 + 1):
            v = eg[yy][xx]
            if v in (4,) + TAILC:
                fcells.setdefault(band_of(yy), []).append((yy, xx, v))
    P0 = {"box": (r0, r1, c0, c1), "rods": rods, "bands": bands, "sky_left": sky_left}
    shapes = []
    for bi, cells in fcells.items():
        L0 = _level_band(eg, bands[bi], P0, eg)
        rmin = min(c[0] for c in cells)
        tcol = [v for (_, _, v) in cells if v in TAILC][0]
        offs = [(yy - rmin, xx - L0, v) for (yy, xx, v) in cells]
        h = max(o[0] for o in offs) + 1
        shapes.append({"tcolor": tcol, "offs": offs, "h": h})
    P = {"box": (r0, r1, c0, c1), "rods": rods, "bands": bands, "sky_left": sky_left,
         "valves": valves, "gates": gates, "doors": doors, "shapes": shapes}
    return P

def _clean_row(g, band, P, eg):
    (r0, r1, c0, c1) = P["box"]
    a, b = band
    for yy in range(a, b + 1):
        ok = True
        for xx in range(c0, c1 + 1):
            if g[yy][xx] not in (0, 3):
                ok = False; break
        if ok:
            return yy
    return a

def _level_band(g, band, P, eg):
    (r0, r1, c0, c1) = P["box"]
    yy = _clean_row(g, band, P, eg)
    row = g[yy]
    if P["sky_left"]:
        for xx in range(c0, c1 + 1):
            if row[xx] == 3:
                return xx
        return c1 + 1
    else:
        for xx in range(c0, c1 + 1):
            if row[xx] == 0:
                return xx
        return c1 + 1

def _levels(g, P, eg):
    return [_level_band(g, bd, P, eg) for bd in P["bands"]]

def _locate_floats(wg, P):
    # find each shape's current position from the grid: returns list of
    # {shape, band, rmin, L} (L = anchor: max tail col + 1)
    (r0, r1, c0, c1) = P["box"]
    rodset = set()
    for (a, b) in P["rods"]:
        for r in range(a, b + 1):
            rodset.add(r)
    out = []
    for sh in P["shapes"]:
        tc = sh["tcolor"]
        cells = [(yy, xx) for yy in range(r0, r1 + 1) if yy not in rodset
                 for xx in range(c0, c1 + 1) if wg[yy][xx] == tc]
        if not cells:
            out.append(None)
            continue
        rows = [c[0] for c in cells]
        cols = [c[1] for c in cells]
        rmin_tail = min(rows)
        # shape's tail min row offset:
        troffs = [o[0] for o in sh["offs"] if o[2] == tc]
        tdxs = [o[1] for o in sh["offs"] if o[2] == tc]
        rmin = rmin_tail - min(troffs)
        L = max(cols) - max(tdxs)
        bi = None
        for i, (a, b) in enumerate(P["bands"]):
            if a <= rmin <= b:
                bi = i; break
        out.append({"shape": sh, "band": bi, "rmin": rmin, "L": L})
    return out

def _stamp_float(wg, P, fl, rmin, L):
    (r0, r1, c0, c1) = P["box"]
    for (ro, dx, v) in fl["shape"]["offs"]:
        yy, xx = rmin + ro, L + dx
        if r0 <= yy <= r1 and c0 <= xx <= c1:
            wg[yy][xx] = v

def _water_val(P, levels, bi, xx):
    L = levels[bi]
    if P["sky_left"]:
        return 3 if xx >= L else 0
    return 3 if xx < L else 0

def _redraw_band(wg, weg, P, levels, bi):
    (r0, r1, c0, c1) = P["box"]
    a, b = P["bands"][bi]
    for yy in range(a, b + 1):
        for xx in range(c0, c1 + 1):
            wg[yy][xx] = _water_val(P, levels, bi, xx)
    for yy in range(a, b + 1):
        for xx in range(c0, c1 + 1):
            if weg[yy][xx] == 9:
                wg[yy][xx] = 9

def _door_pass(wg, weg, P, levels):
    # stateless: open iff adjacent levels equal; render doors + channels
    (r0, r1, c0, c1) = P["box"]
    for d in P["doors"]:
        a, b = P["rods"][d["rod"]]
        up, dn = d["up"], d["dn"]
        # open iff BOTH adjacent levels equal AND surface flush with door bottom (L == hi+1)
        # (rival hypothesis: equality + adjacent float fits — revisit if this mispredicts)
        open_ = (up is not None and dn is not None
                 and levels[up] == levels[dn] == d["hi"] + 1)
        col = 12 if open_ else 1
        for yy in range(a, b + 1):
            for xx in range(d["lo"], d["hi"] + 1):
                wg[yy][xx] = col
        ch_lo, ch_hi = d["lo"] + 2, d["hi"] - 2
        for (yy, bi) in ((a - 2, up), (b + 2, dn)):
            if bi is None or not (r0 <= yy <= r1):
                continue
            for xx in range(ch_lo, ch_hi + 1):
                wg[yy][xx] = 0 if open_ else _water_val(P, levels, bi, xx)
    return

def _aligned_all(P, floats, levels):
    if not P["shapes"]:
        return False
    for fl in floats:
        if fl is None:
            return False
        sh = fl["shape"]
        tdxs = sorted(set(o[1] for o in sh["offs"] if o[2] == sh["tcolor"]))
        tail = tuple(sorted(fl["L"] + dx for dx in tdxs))
        ok = False
        for gt in P["gates"]:
            if gt["color"] != sh["tcolor"] or tail != gt["cols"]:
                continue
            ra, rb = P["rods"][gt["rod"]]
            fa, fb = P["bands"][fl["band"]]
            if fb == ra - 1 or fa == rb + 1:
                ok = True; break
        if not ok:
            return False
    return True

def _bar_total(level, n):
    # empirical per-level schedules; refit via brute force over (a*n+b)//c on ALL clicks when broken
    if level in (0, 1, 3):
        return (14 * n + 6) // 11   # fits all 32 observed clicks of L0+L1+L3
    if level == 2:
        return (6 * n + 3) // 7     # fits all 22 observed clicks
    return n

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
    (r0, r1, c0, c1) = P["box"]
    levels = _levels(wg, P, weg)
    floats = _locate_floats(wg, P)
    changed = False
    cv = wg[cy][cx]
    if cv == 9:
        hit = None
        for v in P["valves"]:
            (x0, x1, y0, y1) = v["bbox"]
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                hit = v; break
        if hit is not None and hit["dst"] is not None:
            s, d, st = hit["src"], hit["dst"], hit["step"]
            sgn = 1 if P["sky_left"] else -1
            nLs = levels[s] + st * sgn
            nLd = levels[d] - st * sgn
            lo, hi = c0, c1 + 1
            if lo <= nLs <= hi and lo <= nLd <= hi:
                levels = list(levels)
                levels[s], levels[d] = nLs, nLd
                changed = True
                for bi in (s, d):
                    _redraw_band(wg, weg, P, levels, bi)
                    for fl in floats:
                        if fl is not None and fl["band"] == bi:
                            fl["L"] = levels[bi]
                            _stamp_float(wg, P, fl, fl["rmin"], fl["L"])
    elif cv == 12:
        # click on an OPEN door: teleport a fitting float across
        for d in P["doors"]:
            a, b = P["rods"][d["rod"]]
            if not (a <= cy <= b and d["lo"] <= cx <= d["hi"]):
                continue
            up, dn = d["up"], d["dn"]
            if up is None or dn is None or not (levels[up] == levels[dn] == d["hi"] + 1):
                break
            for fl in floats:
                if fl is None or fl["band"] not in (up, dn):
                    continue
                occ_lo = fl["L"] + min(o[1] for o in fl["shape"]["offs"])
                occ_hi = fl["L"] + max(o[1] for o in fl["shape"]["offs"])
                if occ_lo < d["lo"] or occ_hi > d["hi"]:
                    continue
                src = fl["band"]
                dst = dn if src == up else up
                # erase from src (water rule)
                for (ro, dx, v) in fl["shape"]["offs"]:
                    yy, xx = fl["rmin"] + ro, fl["L"] + dx
                    if r0 <= yy <= r1 and c0 <= xx <= c1:
                        wg[yy][xx] = _water_val(P, levels, src, xx)
                da, db = P["bands"][dst]
                fl["band"] = dst
                fl["rmin"] = (da + db + 1 - fl["shape"]["h"]) // 2
                fl["L"] = levels[dst]
                _stamp_float(wg, P, fl, fl["rmin"], fl["L"])
                changed = True
                break
            break
    _door_pass(wg, weg, P, levels)
    if changed and _aligned_all(P, floats, levels):
        info["level_up"] = True
        if CURRENT_LEVEL == 6:
            info["win"] = True
    if vert:
        g = _transpose(wg)
    # timer
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
    levels = _levels(wg, P, weg)
    floats = _locate_floats(wg, P)
    return _aligned_all(P, floats, levels)
