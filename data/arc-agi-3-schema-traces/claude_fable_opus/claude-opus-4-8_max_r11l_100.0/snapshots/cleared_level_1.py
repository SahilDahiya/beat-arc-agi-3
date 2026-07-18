"""World model — "centroid docking" game.  General over levels; verified on levels 0 and 1.

OBJECTS
  * NODE = filled Manhattan diamond r<=2 (12 cells) of a BODY colour + a CENTRE DOT.
      - BODY colour encodes SELECTION, not identity:  BLACK(0) = the (single, global) SELECTED
        node;  GREEN(3) = every other node.
      - The CENTRE DOT colour is the node's SYSTEM id (15 on level 0; 12 and 15 on level 1).
  * Each SYSTEM s has:  its nodes, one CENTROID MARKER, one TARGET RING (all in colour s).
      - CENTROID MARKER = octagon (Chebyshev<=2 minus 4 corners) in colour s with the DOT(6) at
        its centre, drawn at the FLOOR-AVERAGE of that system's node centres.
      - TARGET RING = static dashed ring in colour s: cells at Manhattan==4 minus the 4 axis tips
        (12 cells, 4 disjoint arcs -> cluster by PROXIMITY, never 8-connectivity).
  * SPOKES = colour-1 lines (DDA, round-half-up) from each centroid marker to each of its nodes.
  * TERRAIN: land (the colour the nodes sit on, 5) vs everything else (sea 2, and colour 10 on
    level 1) — nodes may ONLY be placed on land.
  * Column x=0 = a per-level 64-cell COUNTER BAR; EVERY click spends one cell from the top.
  * z-order: terrain < spokes < rings < octagons < nodes.

ACTIONS (only action 6, a click)
  * Click within Manhattan<=2 of a node's centre  => SELECT that node (it turns black, the old one
    turns green).  Nothing moves.
  * Click anywhere else => the SELECTED node teleports there, but ONLY if its whole 13-cell diamond
    lands on land.  Otherwise nothing happens.  Either way the bar ticks.

GOAL: EVERY system's centroid marker docks on its own ring centre => level_up.

Stateless by design: positions, selection (= the black node) and the click count are all read back
out of the grid (the backtest skips transition 0 without rolling state forward, so never rely on
threaded state).
"""
import math
import numpy as np
from collections import deque

LINE, DOT, SEL, UNSEL = 1, 6, 0, 3
NON_SYS = (LINE, DOT, SEL, UNSEL)          # colours that can never be a system id
DIAM = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if 0 < abs(dx) + abs(dy) <= 2]
DIAM13 = DIAM + [(0, 0)]
OCT = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)
       if not (abs(dx) == 2 and abs(dy) == 2) and (dx, dy) != (0, 0)]
RING = [(dx, dy) for dx in range(-4, 5) for dy in range(-4, 5)
        if abs(dx) + abs(dy) == 4 and dx != 0 and dy != 0]


def _seg(p0, p1):
    """Spoke rasterisation.  ALWAYS call with p0 = the CENTROID (lines are drawn outward from it):
    cell i = start + round(offset) where offset = delta*i/n and .5 TIES ROUND AWAY FROM THE START
    (i.e. the offset is rounded half away from zero).  Verified on L0 (x-tie 19.5 -> 20, up) and
    L1 (y-tie 13.5 -> 13, down)."""
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


def _octagon_mask(g):
    """Cells covered by a centroid octagon.  Octagons are drawn LAST (over node bodies), so a
    node's diamond can be partly hidden by one — the parser must allow for that."""
    H, W = g.shape
    occ = np.zeros((H, W), bool)
    for oy, ox in zip(*np.where(g == DOT)):
        for dx, dy in OCT + [(0, 0)]:
            X, Y = int(ox) + dx, int(oy) + dy
            if 0 <= X < W and 0 <= Y < H:
                occ[Y][X] = True
    return occ


def _find_nodes(g):
    """-> [(x, y, body, system)] for every node diamond, tolerating octagon occlusion."""
    H, W = g.shape
    occ = _octagon_mask(g)
    out = []
    for body in (SEL, UNSEL):
        m = (g == body)
        m[:, 0] = False                     # column 0 is the counter bar
        cand = m | occ                      # a body cell may be hidden under an octagon
        ok = np.ones((H, W), bool)
        cnt = np.zeros((H, W), int)
        for dx, dy in DIAM:
            ok &= _shift(cand, dx, dy)
            cnt += _shift(m, dx, dy).astype(int)
        ok &= (cnt >= 6)                    # enough real body cells => not a phantom in an octagon
        for y, x in zip(*np.where(ok)):
            s = int(g[y][x])
            if s == DOT:                    # node centre sits exactly on an octagon centre
                s = int(g[y][x + 1]) if x + 1 < W else int(g[y][x - 1])
            if s not in NON_SYS:
                out.append((int(x), int(y), body, s))
    return out


_CACHE = {}


def _layout(entry):
    g = np.asarray(entry, dtype=int)
    key = g.tobytes()
    if key in _CACHE:
        return _CACHE[key]
    H, W = g.shape
    nodes = _find_nodes(g)
    systems = sorted(set(n[3] for n in nodes))

    obj = set()
    for x, y, b, s in nodes:
        for dx, dy in DIAM13:
            obj.add((x + dx, y + dy))
    for s in systems:                        # the centroid octagon of each system
        pts = [(x, y) for x, y, b, ss in nodes if ss == s]
        cx = sum(p[0] for p in pts) // len(pts)
        cy = sum(p[1] for p in pts) // len(pts)
        obj.add((cx, cy))
        for dx, dy in OCT:
            obj.add((cx + dx, cy + dy))
    for y in range(H):
        for x in range(1, W):
            if g[y][x] == LINE:
                obj.add((x, y))

    rings, ring_cells = {}, []               # leftover system-coloured cells = the dashed rings
    for s in systems:
        pts = [(int(x), int(y)) for y, x in zip(*np.where(g == s)) if x > 0 and (int(x), int(y)) not in obj]
        groups = []
        for p in pts:
            hit = [i for i, gs in enumerate(groups)
                   if any(max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 3 for q in gs)]
            merged = [p]
            for i in sorted(hit, reverse=True):
                merged += groups.pop(i)
            groups.append(merged)
        for cells in groups:
            rings[s] = (int(round(sum(c[0] for c in cells) / len(cells))),
                        int(round(sum(c[1] for c in cells) / len(cells))))
            ring_cells += [(c[0], c[1], s) for c in cells]
            for c in cells:
                obj.add(c)

    bg = g.copy()                            # terrain: inpaint objects from the nearest terrain
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

    lay = dict(H=H, W=W, bg=bg, land=land, rings=rings, ring_cells=tuple(ring_cells),
               systems=tuple(systems), used_col=used_col, bar_col=bar_col)
    _CACHE[key] = lay
    return lay


def _centroids(nodes):
    out = {}
    for s in sorted(set(n[3] for n in nodes)):
        pts = [(x, y) for x, y, b, ss in nodes if ss == s]
        out[s] = (sum(p[0] for p in pts) // len(pts), sum(p[1] for p in pts) // len(pts))
    return out


def _cells_ok(lay, cells):
    H, W, land = lay["H"], lay["W"], lay["land"]
    for X, Y in cells:
        if not (0 <= X < W and 0 <= Y < H) or not land[Y][X]:
            return False
    return True


def _placeable(lay, x, y):
    return _cells_ok(lay, [(x + dx, y + dy) for dx, dy in DIAM13])


def _move_ok(lay, nodes, i, x, y):
    """A move is legal only if EVERYTHING the move redraws lands on land:
       (a) the node's own 13-cell diamond,
       (b) its system's resulting CENTROID OCTAGON (21 cells),
       (c) its system's resulting SPOKES.
    (Confirmed: click (45,6) on L0 broke (a); click (37,31) on L1 broke (b) and (c) while (a) held.)
    A 4th candidate — the node's straight TRAVEL PATH — is still untested; (41,26) discriminates."""
    if not _placeable(lay, x, y):
        return False
    s = nodes[i][3]
    new = list(nodes)
    new[i] = (x, y, nodes[i][2], s)
    pts = [(nx, ny) for nx, ny, b, ss in new if ss == s]
    cx = sum(p[0] for p in pts) // len(pts)
    cy = sum(p[1] for p in pts) // len(pts)
    if not _cells_ok(lay, [(cx + dx, cy + dy) for dx, dy in OCT + [(0, 0)]]):
        return False
    for p in pts:
        if not _cells_ok(lay, _seg((cx, cy), p)):
            return False
    return True


def _render(lay, nodes, clicks):
    H, W = lay["H"], lay["W"]
    g = lay["bg"].copy()
    cents = _centroids(nodes)
    for s, c in cents.items():                                   # 1. spokes
        for x, y, b, ss in nodes:
            if ss != s:
                continue
            for px, py in _seg(c, (x, y)):
                if 0 <= px < W and 0 <= py < H:
                    g[py][px] = LINE
    for x, y, s in lay["ring_cells"]:                            # 2. target rings
        # a ring whose centroid has DOCKED renders BLACK(0) — the "locked in" indicator
        g[y][x] = SEL if cents.get(s) == lay["rings"].get(s) else s
    for x, y, b, s in nodes:                                     # 3. nodes
        for dx, dy in DIAM:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                g[y + dy][x + dx] = b
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = s
    for s, (cx, cy) in cents.items():                            # 4. centroid octagons ON TOP
        for dx, dy in OCT:                                       #    (proved: octagon at (41,33)
            if 0 <= cx + dx < W and 0 <= cy + dy < H:            #     overdrew the node at (41,31))
                g[cy + dy][cx + dx] = s
        if 0 <= cx < W and 0 <= cy < H:
            g[cy][cx] = DOT
    for k in range(H):                                           # 5. counter bar
        g[k][0] = lay["used_col"] if k < clicks else lay["bar_col"]
    return g


def _docked(lay, nodes):
    cents = _centroids(nodes)
    rings = lay["rings"]
    if not rings or len(rings) != len(cents):
        return False
    return all(cents.get(s) == r for s, r in rings.items())


def init_state(entry_grid):
    # only state we need: how many systems were docked BEFORE the PREVIOUS click (see predict).
    return {"prev_docked": 0}


def predict(state, grid, action, x=None, y=None):
    lay = _layout(ENTRY_GRID)
    g = np.asarray(grid, dtype=int)
    if action == 0:
        return (np.asarray(ENTRY_GRID, dtype=int).tolist(),
                {"level_up": False, "dead": False, "win": False}, {"prev_docked": 0})
    nodes = _find_nodes(g)
    clicks = int((g[:, 0] != lay["bar_col"]).sum())
    # BAR COST: 1 per click, PLUS 1 per docking — but the docking's +1 is charged ONE CLICK LATE.
    #   increment = 1 + (docked_now - docked_at_the_previous_click)
    # Fits every row of L1: clicks 1-7 cost 1; click 8 (right after sys12 docked) cost 2; click 9
    # cost 1 again.  ("Upkeep per docked system" was REFUTED — click 9 would have cost 2.)
    docked_before = sum(1 for s, c in _centroids(nodes).items() if c == lay["rings"].get(s))
    prev_docked = int(state.get("prev_docked", 0)) if isinstance(state, dict) else 0
    nxt = {"prev_docked": docked_before}

    if action == 6 and x is not None and nodes:
        hit = None
        for i, (nx, ny, b, s) in enumerate(nodes):
            if abs(nx - x) + abs(ny - y) <= 2:                   # clicked a node => select it
                hit = i
                break
        if hit is not None:
            nodes = [(nx, ny, SEL if i == hit else UNSEL, s)
                     for i, (nx, ny, b, s) in enumerate(nodes)]
        else:
            sel = [i for i, n in enumerate(nodes) if n[2] == SEL]
            if sel and _move_ok(lay, nodes, sel[0], x, y):       # else move the selected node
                i = sel[0]
                nodes[i] = (x, y, SEL, nodes[i][3])
        clicks += 1 + max(0, docked_before - prev_docked)

    out = _render(lay, nodes, clicks)
    win_all = _docked(lay, nodes)
    last = (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5)
    return (out.tolist(), {"level_up": bool(win_all and not last), "dead": False,
                           "win": bool(win_all and last)}, nxt)


def is_goal(grid):
    if ENTRY_GRID is None or grid is None:
        return False
    lay = _layout(ENTRY_GRID)
    nodes = _find_nodes(np.asarray(grid, dtype=int))
    return bool(nodes) and _docked(lay, nodes)
