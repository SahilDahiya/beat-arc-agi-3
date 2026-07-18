"""World model — "centroid docking".  General; verified on levels 0-4.

OBJECTS
  * NODE = filled Manhattan diamond r<=2 (12 cells) + a CENTRE DOT.
      BODY colour = SELECTION: BLACK(0) = the one selected node, GREEN(3) = all others.
  * Each SYSTEM has a CENTROID MARKER: an octagon (Chebyshev<=2 minus 4 corners, 21 cells) drawn
    at the FLOOR-AVERAGE of its nodes.  Its 21 cells are a multi-coloured PIE CHART (signature).
    Detected BY SHAPE (21 non-terrain cells, 4 terrain corners) — L4's octagons have NO DOT centre.
    Which nodes belong to which system: solve the partition so each octagon centre == the
    floor-average of its group (the node's centre-dot colour is NOT a system id on L4 — all 4).
  * PICKUPS (L4) = octagon-shaped static objects that are NOT at any centroid: half one colour,
    half BLACK.  Driving a system's centroid onto one fills that half of its pie chart.
    (L4 system octagons start ALL BLACK = empty.)
  * TARGET RINGS = static dashed rings (Manhattan==4 minus tips).  A system docks in the ring whose
    COLOUR SET matches its octagon's.  Extra rings are DECOYS.  A docked ring renders BLACK.
  * SPOKES = colour-1 lines from each centroid OUTWARD to its nodes (DDA; .5 ties round away).
  * TERRAIN: land = the colour nodes sit on (5).  Column x=0 = progress bar, round(64*clicks/60).
  * z-order: terrain < spokes < static objects (rings, pickups) < nodes < system octagons.
GOAL: every system docked (centroid within DOCK_R of its matching ring).
"""
import math
import numpy as np
from collections import deque

LINE, DOT, SEL, UNSEL = 1, 6, 0, 3
NON_SYS = (LINE, DOT, SEL, UNSEL)
DIAM = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if 0 < abs(dx) + abs(dy) <= 2]
DIAM13 = DIAM + [(0, 0)]
OCT = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)
       if not (abs(dx) == 2 and abs(dy) == 2) and (dx, dy) != (0, 0)]
OCT21 = OCT + [(0, 0)]
CORNERS = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
RING = [(dx, dy) for dx in range(-4, 5) for dy in range(-4, 5)
        if abs(dx) + abs(dy) == 4 and dx != 0 and dy != 0]
TIPS = [(0, -4), (0, 4), (-4, 0), (4, 0)]
CLICK_BUDGET = 60
DOCK_R = 5          # snap radius (observed 5 on L2; true value in [5,11])
TERRAIN = (2, 5, 10)   # land / sea / obstacle


def _bar_cells(k):
    return (128 * k + CLICK_BUDGET) // (2 * CLICK_BUDGET)


def _clicks_from_bar(b):
    for k in range(0, 4 * CLICK_BUDGET):
        if _bar_cells(k) == b:
            return k
    return b


def _seg(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    n = max(abs(dx), abs(dy))
    if n == 0:
        return [p0]
    out = []
    for i in range(n + 1):
        ox, oy = dx * i / n, dy * i / n
        rx = math.floor(ox + 0.5) if ox >= 0 else math.ceil(ox - 0.5)
        ry = math.floor(oy + 0.5) if oy >= 0 else math.ceil(oy - 0.5)
        out.append((x0 + rx, y0 + ry))
    return out


def _shift(m, dx, dy):
    H, W = m.shape
    out = np.zeros((H, W), bool)
    ys0, ys1 = max(0, -dy), min(H, H - dy)
    xs0, xs1 = max(0, -dx), min(W, W - dx)
    if ys0 < ys1 and xs0 < xs1:
        out[ys0:ys1, xs0:xs1] = m[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    return out


def _oct_centres(g):
    """Octagons BY SHAPE: all 21 cells non-terrain (terrain = land/sea/obstacle).
    A node's 21-cell neighbourhood always includes terrain at (+-2,+-1)/(+-1,+-2), so nodes never
    match.  No corner test — L0's octagon has SPOKE cells on its corners."""
    H, W = g.shape
    cands = []
    for y in range(2, H - 2):
        for x in range(2, W - 2):
            ok = True
            for dx, dy in OCT21:
                if int(g[y + dy][x + dx]) in TERRAIN:
                    ok = False
                    break
            if ok:
                cands.append((x, y))
    # A node overlapping an octagon makes a PHANTOM octagon shape beside the real one.  On L0-L3
    # the real octagon has a DOT(6) centre, so prefer dotted candidates and drop any shape that
    # merely shadows one.  L4's octagons have no DOT, so there all candidates stand.
    dotted = [c for c in cands if int(g[c[1]][c[0]]) == DOT]
    out = list(dotted)
    for c in cands:
        if c in dotted:
            continue
        if any(max(abs(c[0] - d[0]), abs(c[1] - d[1])) <= 2 for d in dotted):
            continue
        out.append(c)
    return sorted(out)


def _find_nodes(g, occ=None):
    H, W = g.shape
    if occ is None:
        occ = np.zeros((H, W), bool)
        for ox, oy in _oct_centres(g):
            for dx, dy in OCT21:
                occ[oy + dy][ox + dx] = True
    out = []
    for body in (SEL, UNSEL):
        m = (g == body)
        m[:, 0] = False
        cand = m | occ                       # a body cell may be hidden under an octagon...
        vis = m & (~occ)                     # ...but a REAL node has body cells OUTSIDE every octagon
        ok = np.ones((H, W), bool)
        cnt = np.zeros((H, W), int)
        for dx, dy in DIAM:
            ok &= _shift(cand, dx, dy)
            cnt += _shift(vis, dx, dy).astype(int)
        ok &= (cnt >= 6)                     # else an all-black octagon looks like a black node
        for y, x in zip(*np.where(ok)):
            s = int(g[y][x])
            if s in NON_SYS:
                continue
            out.append((int(x), int(y), body, s))
    return out


def _partition(nodes, octs):
    """Assign every node to an octagon so that each octagon == floor-average of its group."""
    n, k = len(nodes), len(octs)
    if n == 0 or k == 0:
        return None
    res = [None]

    def rec(i, groups):
        if res[0]:
            return
        if i == n:
            for j, (ox, oy) in enumerate(octs):
                gp = groups[j]
                if not gp:
                    return
                if (sum(nodes[t][0] for t in gp) // len(gp),
                        sum(nodes[t][1] for t in gp) // len(gp)) != (ox, oy):
                    return
            res[0] = [list(gp) for gp in groups]
            return
        for j in range(k):
            groups[j].append(i)
            rec(i + 1, groups)
            groups[j].pop()
            if res[0]:
                return
    rec(0, [[] for _ in range(k)])
    return res[0]


def _sysgroups(g):
    """-> (nodes, [(centroid, [node indices]), ...])  for the systems present in this grid."""
    octs = _oct_centres(g)
    nodes = _find_nodes(g)
    for k in range(len(octs), 0, -1):
        for sub in _combos(octs, k):
            part = _partition(nodes, list(sub))
            if part:
                return nodes, [(sub[j], part[j]) for j in range(k)]
    return nodes, []


def _combos(items, k):
    n = len(items)
    idx = list(range(k))
    while True:
        yield [items[i] for i in idx]
        i = k - 1
        while i >= 0 and idx[i] == i + n - k:
            i -= 1
        if i < 0:
            return
        idx[i] += 1
        for j in range(i + 1, k):
            idx[j] = idx[j - 1] + 1


_CACHE = {}


def _layout(entry):
    g = np.asarray(entry, dtype=int)
    key = g.tobytes()
    if key in _CACHE:
        return _CACHE[key]
    H, W = g.shape
    nodes, groups = _sysgroups(g)
    sys_centres = [c for c, _ in groups]
    all_octs = _oct_centres(g)
    pickups = [((ox, oy), tuple((dx, dy, int(g[oy + dy][ox + dx])) for dx, dy in OCT21))
               for ox, oy in all_octs if (ox, oy) not in sys_centres]

    rings = []
    for y in range(4, H - 4):
        for x in range(4, W - 4):
            rc = [int(g[y + dy][x + dx]) for dx, dy in RING]
            tp = [int(g[y + dy][x + dx]) for dx, dy in TIPS]
            if any(c in TERRAIN for c in rc):
                continue
            if any(t not in (2, 5, 10) for t in tp):
                continue
            if all(c == 10 for c in rc):
                continue
            rings.append(((x, y), tuple((dx, dy, int(g[y + dy][x + dx])) for dx, dy in RING)))

    obj = set()
    for x, y, b, s in nodes:
        for dx, dy in DIAM13:
            obj.add((x + dx, y + dy))
    for ox, oy in all_octs:
        for dx, dy in OCT21:
            obj.add((ox + dx, oy + dy))
    for (rx, ry), rp in rings:
        for dx, dy, c in rp:
            obj.add((rx + dx, ry + dy))
    for y in range(H):
        for x in range(1, W):
            if g[y][x] == LINE:
                obj.add((x, y))

    bg = g.copy()
    dist = np.full((H, W), -1, int)
    q = deque()
    for y in range(H):
        for x in range(W):
            if x == 0 or (x, y) in obj:
                bg[y][x] = -1
            else:
                dist[y][x] = 0
                q.append((x, y))
    while q:
        cx, cy = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < W and 0 <= ny < H and dist[ny][nx] < 0:
                dist[ny][nx] = dist[cy][cx] + 1
                bg[ny][nx] = bg[cy][cx]
                q.append((nx, ny))

    vals, cnts = np.unique(g, return_counts=True)
    used_col = int(vals[np.argmax(cnts)])
    bar_col = int(g[H - 1][0])
    land_col = int(bg[nodes[0][1]][nodes[0][0]]) if nodes else used_col
    land = (bg == land_col)
    land[:, 0] = False

    lay = dict(H=H, W=W, bg=bg, land=land, rings=tuple(rings), pickups=tuple(pickups),
               used_col=used_col, bar_col=bar_col)
    _CACHE[key] = lay
    return lay


def _cells_ok(lay, cells):
    H, W, land = lay["H"], lay["W"], lay["land"]
    for X, Y in cells:
        if not (0 <= X < W and 0 <= Y < H) or not land[Y][X]:
            return False
    return True


def _centroid(nodes, idxs):
    n = len(idxs)
    return (sum(nodes[i][0] for i in idxs) // n, sum(nodes[i][1] for i in idxs) // n)


def _move_ok(lay, nodes, groups, i, x, y):
    if not _cells_ok(lay, [(x + dx, y + dy) for dx, dy in DIAM13]):
        return False
    new = list(nodes)
    new[i] = (x, y, nodes[i][2], nodes[i][3])
    for c, idxs in groups:
        if i not in idxs:
            continue
        cx, cy = _centroid(new, idxs)
        if not _cells_ok(lay, [(cx + dx, cy + dy) for dx, dy in OCT21]):
            return False
        for j in idxs:
            if not _cells_ok(lay, _seg((cx, cy), (new[j][0], new[j][1]))):
                return False
    return True


def _pickups_in(g, sys_centres):
    """Pickups are the octagons in THIS grid that are not a system's centroid marker.
    They are CONSUMED on absorption (their cells revert to terrain), so they must be read from the
    live grid, never from the static entry layout."""
    out = []
    for ox, oy in _oct_centres(g):
        if (ox, oy) in sys_centres:
            continue
        out.append(((ox, oy), tuple((dx, dy, int(g[oy + dy][ox + dx])) for dx, dy in OCT21)))
    return out


def _absorb(pickups, pat, centre):
    """PICKUP ABSORPTION (L4): the pickup's COLOURED cells (its non-BLACK half) are permanently
    painted into the system octagon's pie chart, and the PICKUP IS CONSUMED (cells -> terrain).
    *** CAPTURE = the two octagons OVERLAP (Chebyshev distance of centres <= 4). ***
    Proved: absorbed at Chebyshev 4 (centroid (52,41), pickup (56,43)); NOT absorbed at Chebyshev 9
    (centroid (29,51), pickup (20,53)).  It is NOT exact-centre — an intermediate centroid can eat
    a pickup in passing, so plans must keep centroids Chebyshev>4 from pickups they don't want."""
    d = {(dx, dy): c for dx, dy, c in pat}
    eaten = set()
    for (px, py), pp in pickups:
        if max(abs(px - centre[0]), abs(py - centre[1])) <= 4:
            for dx, dy, c in pp:
                if c != SEL:
                    d[(dx, dy)] = c
            eaten.add((px, py))
    return tuple((dx, dy, d[(dx, dy)]) for dx, dy in OCT21), eaten


def _ring_for(lay, pat):
    """the ring whose colour set matches this octagon's pie chart (the centre cell — a DOT on
    L0-L3 — is NOT part of the signature)"""
    cs = set(c for dx, dy, c in pat if (dx, dy) != (0, 0))
    for (rc, rp) in lay["rings"]:
        if set(c for _, _, c in rp) == cs:
            return rc
    return None


def _docked_map(lay, cents_pats):
    out = {}
    for c, pat in cents_pats:
        r = _ring_for(lay, pat)
        out[c] = (r is not None and abs(c[0] - r[0]) + abs(c[1] - r[1]) <= DOCK_R, r)
    return out


def _render(lay, nodes, cents_pats, bar, pickups=()):
    H, W = lay["H"], lay["W"]
    g = lay["bg"].copy()
    for c, pat in cents_pats:                                    # 1. spokes
        for i in c[1]:
            for px, py in _seg(c[0], (nodes[i][0], nodes[i][1])):
                if 0 <= px < W and 0 <= py < H:
                    g[py][px] = LINE
    dm = _docked_map(lay, [(c[0], p) for c, p in cents_pats])
    docked_rings = {r for ok, r in dm.values() if ok and r}
    for (rx, ry), rp in lay["rings"]:                            # 2. rings
        for dx, dy, col in rp:
            X, Y = rx + dx, ry + dy
            if 0 <= X < W and 0 <= Y < H:
                g[Y][X] = SEL if (rx, ry) in docked_rings else col
    for (px_, py_), pp in pickups:                               # 3. surviving pickups
        for dx, dy, col in pp:
            X, Y = px_ + dx, py_ + dy
            if 0 <= X < W and 0 <= Y < H:
                g[Y][X] = col
    for x, y, b, s in nodes:                                     # 4. nodes
        for dx, dy in DIAM:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                g[y + dy][x + dx] = b
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = s
    for c, pat in cents_pats:                                    # 5. system octagons ON TOP
        cx, cy = c[0]
        for dx, dy, col in pat:
            X, Y = cx + dx, cy + dy
            if 0 <= X < W and 0 <= Y < H:
                g[Y][X] = col
    for k in range(H):
        g[k][0] = lay["used_col"] if k < bar else lay["bar_col"]
    return g


def step(grid, action, x=None, y=None):
    lay = _layout(ENTRY_GRID)
    g = np.asarray(grid, dtype=int)
    if action == 0:
        return (np.asarray(ENTRY_GRID, dtype=int).tolist(),
                {"level_up": False, "dead": False, "win": False})
    nodes, groups = _sysgroups(g)
    pats = {c: tuple((dx, dy, int(g[c[1] + dy][c[0] + dx])) for dx, dy in OCT21)
            for c, _ in groups}
    pickups = _pickups_in(g, {c for c, _ in groups})
    clicks = _clicks_from_bar(int((g[:, 0] != lay["bar_col"]).sum()))

    if action == 6 and x is not None and nodes:
        hit = None
        for i, (nx, ny, b, s) in enumerate(nodes):
            if abs(nx - x) + abs(ny - y) <= 2:
                hit = i
                break
        if hit is not None:
            nodes = [(nx, ny, SEL if i == hit else UNSEL, s)
                     for i, (nx, ny, b, s) in enumerate(nodes)]
        else:
            sel = [i for i, n in enumerate(nodes) if n[2] == SEL]
            if sel and _move_ok(lay, nodes, groups, sel[0], x, y):
                i = sel[0]
                nodes[i] = (x, y, SEL, nodes[i][3])
        clicks += 1

    new_cp = []
    eaten = set()
    for c, idxs in groups:
        nc = _centroid(nodes, idxs)
        pat, ate = _absorb(pickups, pats[c], nc)
        eaten |= ate
        new_cp.append((((nc), idxs), pat))
    left = [p for p in pickups if p[0] not in eaten]
    out = _render(lay, nodes, new_cp, _bar_cells(clicks), left)
    dm = _docked_map(lay, [(c[0], p) for c, p in new_cp])
    all_docked = bool(dm) and all(ok for ok, _ in dm.values())
    last = (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5)
    return out.tolist(), {"level_up": bool(all_docked and not last), "dead": False,
                          "win": bool(all_docked and last)}


def is_goal(grid):
    if ENTRY_GRID is None or grid is None:
        return False
    lay = _layout(ENTRY_GRID)
    g = np.asarray(grid, dtype=int)
    nodes, groups = _sysgroups(g)
    if not groups:
        return False
    cp = [((c, idxs), tuple((dx, dy, int(g[c[1] + dy][c[0] + dx])) for dx, dy in OCT21))
          for c, idxs in groups]
    dm = _docked_map(lay, [(c[0], p) for c, p in cp])
    return bool(dm) and all(ok for ok, _ in dm.values())
