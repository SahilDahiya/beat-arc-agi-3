"""World model — "centroid docking".  General; verified on levels 0-3.

OBJECTS
  * NODE = filled Manhattan diamond r<=2 (12 cells) of a BODY colour + a CENTRE DOT.
      - BODY colour = SELECTION: BLACK(0) = the single globally selected node, GREEN(3) = others.
      - CENTRE-DOT colour = the node's SYSTEM id.
  * Each SYSTEM has a CENTROID MARKER (octagon: Chebyshev<=2 minus 4 corners, DOT(6) at centre)
    drawn at the FLOOR-AVERAGE of that system's node centres.
      *** From L3 the octagon is a multi-coloured PIE CHART (a fixed per-system signature), e.g.
      {12,14,15}.  Earlier levels are the degenerate 1-colour case. ***
  * TARGET RINGS = static dashed rings (Manhattan==4 minus the 4 axis tips, 12 cells) each with
    its own colour signature.  A system docks in the ring whose COLOUR SET matches its octagon's.
    L3 has 8 rings for 3 systems => 5 DECOYS.  A docked ring renders BLACK.
  * SPOKES = colour-1 lines from each centroid OUTWARD to its own nodes (DDA; .5 ties round away
    from the start).
  * TERRAIN: land = the colour the nodes sit on (5); sea(2) / obstacle(10) are not placeable.
    NB colour 10 doubles as a ring-sector colour, so ring cells must be treated as objects.
  * Column x=0 is a PROGRESS BAR: cells = round(64*clicks/60)  => 60 clicks per level.
  * z-order: terrain < spokes < rings < nodes < octagons.

ACTIONS (only action 6, a click)
  * Click within Manhattan<=2 of a node centre => SELECT it.  Nothing moves.
  * Click elsewhere => the SELECTED node teleports there, IF everything the move redraws lands on
    land: its 13-cell body, its system's new 21-cell octagon, and its system's new spokes.
    (The node's straight travel path does NOT matter — nodes teleport.)
GOAL: every system's centroid docks on its matching ring => level_up.
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
RING = [(dx, dy) for dx in range(-4, 5) for dy in range(-4, 5)
        if abs(dx) + abs(dy) == 4 and dx != 0 and dy != 0]
TIPS = [(0, -4), (0, 4), (-4, 0), (4, 0)]
CLICK_BUDGET = 60


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


def _oct_centres(g, sig=None):
    """A DOT(6) is a real octagon centre only if its 20 ring-of-sector cells are signature colours.
    (L3's ring at (20,8) has six DOT-coloured cells — surrounded by LAND, so they're excluded.)"""
    H, W = g.shape
    out = []
    for y, x in np.argwhere(g == DOT):
        x, y = int(x), int(y)
        ok = True
        for dx, dy in OCT:
            X, Y = x + dx, y + dy
            if not (0 <= X < W and 0 <= Y < H):
                ok = False
                break
            c = int(g[Y][X])
            if (c in sig) if sig is not None else (c not in (2, 5)):
                continue
            ok = False
            break
        if ok:
            out.append((x, y))
    return out


def _find_nodes(g, sig=None):
    H, W = g.shape
    occ = np.zeros((H, W), bool)
    for ox, oy in _oct_centres(g, sig):                 # octagons draw OVER node bodies
        for dx, dy in OCT21:
            X, Y = ox + dx, oy + dy
            if 0 <= X < W and 0 <= Y < H:
                occ[Y][X] = True
    out = []
    for body in (SEL, UNSEL):
        m = (g == body)
        m[:, 0] = False
        cand = m | occ
        ok = np.ones((H, W), bool)
        cnt = np.zeros((H, W), int)
        for dx, dy in DIAM:
            ok &= _shift(cand, dx, dy)
            cnt += _shift(m, dx, dy).astype(int)
        ok &= (cnt >= 6)
        for y, x in zip(*np.where(ok)):
            s = int(g[y][x])
            if s == DOT:
                s = int(g[y][x + 1]) if x + 1 < W else int(g[y][x - 1])
            if s not in NON_SYS:
                out.append((int(x), int(y), body, s))
    return out


def _centroids(nodes):
    out = {}
    for s in sorted(set(n[3] for n in nodes)):
        pts = [(x, y) for x, y, b, ss in nodes if ss == s]
        out[s] = (sum(p[0] for p in pts) // len(pts), sum(p[1] for p in pts) // len(pts))
    return out


_CACHE = {}


def _layout(entry):
    g = np.asarray(entry, dtype=int)
    key = g.tobytes()
    if key in _CACHE:
        return _CACHE[key]
    H, W = g.shape

    octs = _oct_centres(g)                                     # bootstrap: non-terrain sectors
    sig = set()
    for ox, oy in octs:
        for dx, dy in OCT:
            sig.add(int(g[oy + dy][ox + dx]))
    nodes = _find_nodes(g, sig)
    cents = _centroids(nodes)

    oct_pat = {}                                               # per-system pie-chart signature
    for s, (cx, cy) in cents.items():
        oct_pat[s] = tuple((dx, dy, int(g[cy + dy][cx + dx])) for dx, dy in OCT)

    rings = []                                                 # (centre, 12-cell pattern)
    for y in range(4, H - 4):
        for x in range(4, W - 4):
            rc = [int(g[y + dy][x + dx]) for dx, dy in RING]
            tp = [int(g[y + dy][x + dx]) for dx, dy in TIPS]
            if any(c in (2, 5) for c in rc):
                continue
            if any(t not in (2, 5, 10) for t in tp):
                continue
            if all(c == 10 for c in rc):
                continue
            rings.append(((x, y), tuple((dx, dy, int(g[y + dy][x + dx])) for dx, dy in RING)))

    ring_of = {}                                               # system -> its matching ring centre
    for s in cents:
        cs = set(c for _, _, c in oct_pat[s])
        for (rc_, rp) in rings:
            if set(c for _, _, c in rp) == cs:
                ring_of[s] = rc_
                break

    obj = set()
    for x, y, b, s in nodes:
        for dx, dy in DIAM13:
            obj.add((x + dx, y + dy))
    for s, (cx, cy) in cents.items():
        for dx, dy in OCT21:
            obj.add((cx + dx, cy + dy))
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

    lay = dict(H=H, W=W, bg=bg, land=land, sig=frozenset(sig), rings=tuple(rings),
               ring_of=ring_of, oct_pat=oct_pat, used_col=used_col, bar_col=bar_col)
    _CACHE[key] = lay
    return lay


def _cells_ok(lay, cells):
    H, W, land = lay["H"], lay["W"], lay["land"]
    for X, Y in cells:
        if not (0 <= X < W and 0 <= Y < H) or not land[Y][X]:
            return False
    return True


def _move_ok(lay, nodes, i, x, y):
    if not _cells_ok(lay, [(x + dx, y + dy) for dx, dy in DIAM13]):
        return False
    s = nodes[i][3]
    new = list(nodes)
    new[i] = (x, y, nodes[i][2], s)
    pts = [(nx, ny) for nx, ny, b, ss in new if ss == s]
    cx = sum(p[0] for p in pts) // len(pts)
    cy = sum(p[1] for p in pts) // len(pts)
    if not _cells_ok(lay, [(cx + dx, cy + dy) for dx, dy in OCT21]):
        return False
    for p in pts:
        if not _cells_ok(lay, _seg((cx, cy), p)):
            return False
    return True


DOCK_R = 5   # a system docks when its centroid is within this Manhattan distance of its ring.
# Proof it is NOT exact-centre: L2 sys14 levelled up with centroid (55,48) vs ring (55,53) — dist 5
# — and with those node positions an exact match was arithmetically impossible.  Every non-docked
# state in all history is >=12 away, so the true radius is somewhere in [5,11]; 5 is the observed
# lower bound and is SAFE to plan against (any larger radius also docks).  Keep intermediate
# centroids >11 from their ring so the ambiguity can never bite.


def _at_ring(c, r):
    return c is not None and abs(c[0] - r[0]) + abs(c[1] - r[1]) <= DOCK_R


def _docked(lay, nodes):
    cents = _centroids(nodes)
    ro = lay["ring_of"]
    if not ro or len(ro) != len(cents):
        return False
    return all(_at_ring(cents.get(s), r) for s, r in ro.items())


def _render(lay, nodes, bar):
    H, W = lay["H"], lay["W"]
    g = lay["bg"].copy()
    cents = _centroids(nodes)
    for s, c in cents.items():                                       # 1. spokes
        for x, y, b, ss in nodes:
            if ss != s:
                continue
            for px, py in _seg(c, (x, y)):
                if 0 <= px < W and 0 <= py < H:
                    g[py][px] = LINE
    docked_rings = {r for s, r in lay["ring_of"].items() if _at_ring(cents.get(s), r)}
    for (rx, ry), rp in lay["rings"]:                                # 2. rings (BLACK if docked)
        for dx, dy, col in rp:
            X, Y = rx + dx, ry + dy
            if 0 <= X < W and 0 <= Y < H:
                g[Y][X] = SEL if (rx, ry) in docked_rings else col
    for x, y, b, s in nodes:                                         # 3. nodes
        for dx, dy in DIAM:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                g[y + dy][x + dx] = b
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = s
    for s, (cx, cy) in cents.items():                                # 4. octagons ON TOP
        for dx, dy, col in lay["oct_pat"].get(s, ()):
            X, Y = cx + dx, cy + dy
            if 0 <= X < W and 0 <= Y < H:
                g[Y][X] = col
        if 0 <= cx < W and 0 <= cy < H:
            g[cy][cx] = DOT
    for k in range(H):                                               # 5. progress bar
        g[k][0] = lay["used_col"] if k < bar else lay["bar_col"]
    return g


def step(grid, action, x=None, y=None):
    lay = _layout(ENTRY_GRID)
    g = np.asarray(grid, dtype=int)
    if action == 0:
        return (np.asarray(ENTRY_GRID, dtype=int).tolist(),
                {"level_up": False, "dead": False, "win": False})
    nodes = _find_nodes(g, lay["sig"])
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
            if sel and _move_ok(lay, nodes, sel[0], x, y):
                i = sel[0]
                nodes[i] = (x, y, SEL, nodes[i][3])
        clicks += 1

    out = _render(lay, nodes, _bar_cells(clicks))
    win_all = _docked(lay, nodes)
    last = (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5)
    return out.tolist(), {"level_up": bool(win_all and not last), "dead": False,
                          "win": bool(win_all and last)}


def is_goal(grid):
    if ENTRY_GRID is None or grid is None:
        return False
    lay = _layout(ENTRY_GRID)
    nodes = _find_nodes(np.asarray(grid, dtype=int), lay["sig"])
    return bool(nodes) and _docked(lay, nodes)
