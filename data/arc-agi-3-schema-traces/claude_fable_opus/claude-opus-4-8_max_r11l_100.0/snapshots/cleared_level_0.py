"""World model — "centroid docking" game.

ALL MECHANICS CONFIRMED on level 0:
  * Terrain: island (land) in a sea.  Column x=0 is a COUNTER BAR: every click (even a no-op)
    spends one cell from the TOP (black -> island colour).
  * NODE = filled Manhattan diamond r<=2 (12 cells) + WHITE(15) centre dot.
    ** COLOUR ENCODES SELECTION, NOT IDENTITY: the SELECTED node is drawn BLACK(0), every other
       node is drawn in the normal node colour (GREEN 3 on level 0). **
  * CENTROID MARKER = octagon (Chebyshev<=2 minus 4 corners, WHITE) + unique DOT(6) at its centre,
    drawn at the FLOOR-AVERAGE of the node centres.
  * SPOKES = colour-1 straight lines (DDA, round-half-up) from the centroid marker to each node.
  * TARGET RING = static WHITE dashed ring (Manhattan==4 minus the 4 axis tips; 4 disjoint arcs,
    so cluster by proximity, never by 8-connectivity).  It is exactly the octagon's halo.
  * CLICK on a node's body (Manhattan<=2 of its centre) => SELECT it (it turns black, the old one
    reverts to green).  Nothing moves.
  * CLICK anywhere else => the SELECTED node teleports there, but ONLY if its whole 13-cell diamond
    lands on LAND; otherwise nothing happens.
  * z-order: terrain < spokes < ring < octagon < nodes.
  * GOAL: the centroid marker docks on the ring centre -> level_up.

Stateless: node positions, which node is selected (= the black one) and the click count are all
read back out of the grid, so it can't desync (the backtest skips transition 0 without rolling
state forward — never rely on threaded state).
"""
import math
import numpy as np
from collections import deque

LINE, DOT, WHITE, BLACK = 1, 6, 15, 0
DIAM = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if 0 < abs(dx) + abs(dy) <= 2]
DIAM13 = DIAM + [(0, 0)]
OCT = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)
       if not (abs(dx) == 2 and abs(dy) == 2) and (dx, dy) != (0, 0)]


def _seg(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    n = max(abs(dx), abs(dy))
    if n == 0:
        return [p0]
    return [(math.floor(x0 + dx * i / n + 0.5), math.floor(y0 + dy * i / n + 0.5))
            for i in range(n + 1)]


def _shift(m, dx, dy):
    """mask of cells (x,y) whose neighbour (x+dx, y+dy) is set in m (out of bounds -> False)."""
    H, W = m.shape
    out = np.zeros((H, W), bool)
    ys0, ys1 = max(0, -dy), min(H, H - dy)
    xs0, xs1 = max(0, -dx), min(W, W - dx)
    if ys0 < ys1 and xs0 < xs1:
        out[ys0:ys1, xs0:xs1] = m[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    return out


def _diamond_centres(g, col):
    """centres whose full 12-cell diamond is `col` and whose centre cell is WHITE."""
    m = (g == col)
    m[:, 0] = False                       # column 0 is the counter bar, never a node
    ok = (g == WHITE)
    for dx, dy in DIAM:
        ok &= _shift(m, dx, dy)
    ys, xs = np.where(ok)
    return [(int(x), int(y)) for x, y in zip(xs, ys)]


_CACHE = {}


def _layout(entry):
    g = np.asarray(entry, dtype=int)
    key = g.tobytes()
    if key in _CACHE:
        return _CACHE[key]
    H, W = g.shape

    # node colours: BLACK (the selected one) + whatever other colours form node diamonds
    node_cols = [c for c in range(16) if c not in (LINE, DOT, WHITE) and len(_diamond_centres(g, c))]
    unsel = [c for c in node_cols if c != BLACK]
    unsel_col = unsel[0] if unsel else BLACK
    nodes = []
    for c in node_cols:
        for p in _diamond_centres(g, c):
            nodes.append((c, p))

    obj = set()
    dys, dxs = np.where(g == DOT)
    if len(dxs):
        cent = (int(dxs[0]), int(dys[0]))
        obj.add(cent)
        for dx, dy in OCT:
            obj.add((cent[0] + dx, cent[1] + dy))
    for c, (nx, ny) in nodes:
        for dx, dy in DIAM13:
            obj.add((nx + dx, ny + dy))
    for y in range(H):
        for x in range(1, W):
            if g[y][x] == LINE:
                obj.add((x, y))

    pts = [(int(x), int(y)) for y in range(H) for x in range(1, W)
           if g[y][x] == WHITE and (x, y) not in obj]
    groups = []
    for p in pts:                          # a ring is DASHED -> cluster by proximity
        hit = [i for i, gs in enumerate(groups)
               if any(max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 3 for q in gs)]
        merged = [p]
        for i in sorted(hit, reverse=True):
            merged += groups.pop(i)
        groups.append(merged)
    rings, ring_cells = [], []
    for cells in groups:
        rings.append((int(round(sum(c[0] for c in cells) / len(cells))),
                      int(round(sum(c[1] for c in cells) / len(cells)))))
        ring_cells += cells
        for c in cells:
            obj.add(c)

    bg = g.copy()                          # terrain = objects refilled from nearest terrain colour
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
    land_col = int(bg[nodes[0][1][1]][nodes[0][1][0]]) if nodes else used_col
    land = (bg == land_col)
    land[:, 0] = False

    lay = dict(H=H, W=W, bg=bg, land=land, rings=tuple(rings), ring_cells=tuple(ring_cells),
               unsel_col=unsel_col, n_nodes=len(nodes), used_col=used_col, bar_col=bar_col)
    _CACHE[key] = lay
    return lay


def _parse(g, lay):
    """-> (list of node centres, index of the selected one, clicks used)."""
    sel_pts = _diamond_centres(g, BLACK)
    oth_pts = _diamond_centres(g, lay["unsel_col"])
    nodes = sel_pts + oth_pts
    sel = 0 if sel_pts else -1
    clicks = int((g[:, 0] != lay["bar_col"]).sum())
    return nodes, sel, clicks


def _centroid(nodes):
    n = len(nodes)
    return (sum(p[0] for p in nodes) // n, sum(p[1] for p in nodes) // n)


def _placeable(lay, x, y):
    H, W, land = lay["H"], lay["W"], lay["land"]
    for dx, dy in DIAM13:
        X, Y = x + dx, y + dy
        if not (0 <= X < W and 0 <= Y < H) or not land[Y][X]:
            return False
    return True


def _render(lay, nodes, sel, clicks):
    H, W = lay["H"], lay["W"]
    g = lay["bg"].copy()
    cx, cy = _centroid(nodes)
    for p in nodes:                                        # 1. spokes
        for px, py in _seg((cx, cy), p):
            if 0 <= px < W and 0 <= py < H:
                g[py][px] = LINE
    for x, y in lay["ring_cells"]:                         # 2. target ring
        g[y][x] = WHITE
    for dx, dy in OCT:                                     # 3. centroid octagon
        if 0 <= cx + dx < W and 0 <= cy + dy < H:
            g[cy + dy][cx + dx] = WHITE
    if 0 <= cx < W and 0 <= cy < H:
        g[cy][cx] = DOT
    for i, (nx, ny) in enumerate(nodes):                   # 4. nodes: selected = BLACK
        col = BLACK if i == sel else lay["unsel_col"]
        for dx, dy in DIAM:
            if 0 <= nx + dx < W and 0 <= ny + dy < H:
                g[ny + dy][nx + dx] = col
        if 0 <= nx < W and 0 <= ny < H:
            g[ny][nx] = WHITE
    for k in range(H):                                     # 5. counter bar
        g[k][0] = lay["used_col"] if k < clicks else lay["bar_col"]
    return g


def step(grid, action, x=None, y=None):
    lay = _layout(ENTRY_GRID)
    g = np.asarray(grid, dtype=int)
    if action == 0:
        return (np.asarray(ENTRY_GRID, dtype=int).tolist(),
                {"level_up": False, "dead": False, "win": False})
    nodes, sel, clicks = _parse(g, lay)

    if action == 6 and x is not None and nodes:
        hit = None
        for i, p in enumerate(nodes):
            if abs(p[0] - x) + abs(p[1] - y) <= 2:         # clicked a node's body -> select it
                hit = i
                break
        if hit is not None:
            sel = hit
        elif sel >= 0 and _placeable(lay, x, y):           # else move the selected node
            nodes[sel] = (x, y)
        clicks += 1

    out = _render(lay, nodes, sel, clicks)
    docked = bool(lay["rings"]) and nodes and _centroid(nodes) in lay["rings"]
    last = (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5)
    return out.tolist(), {"level_up": bool(docked and not last), "dead": False,
                          "win": bool(docked and last)}


def is_goal(grid):
    if ENTRY_GRID is None or grid is None:
        return False
    lay = _layout(ENTRY_GRID)
    g = np.asarray(grid, dtype=int)
    dys, dxs = np.where(g == DOT)
    if len(dxs) == 0:
        return False
    return (int(dxs[0]), int(dys[0])) in lay["rings"]
