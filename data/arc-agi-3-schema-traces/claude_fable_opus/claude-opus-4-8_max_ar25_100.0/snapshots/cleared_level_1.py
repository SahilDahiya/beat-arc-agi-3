"""General world model for the ARC-AGI-3 mirror/reflection puzzle (levels 0 & 1+).

UNIFIED MECHANIC:
- TEMPLATE = a hollow shape (color 5 border + tile-center holes). It is the SOURCE.
- WALL = the vertical mirror axis (color 10). Solid wall = fixed. Hollow wall (center holes) = movable.
- SOLID piece (color 4) = live horizontal REFLECTION of the template across the wall center
  (per cell: (y, 2*c - x)), drawn SOLID.
- TARGET (color 11 "b-shape", excl. right border col) = fixed; overlap of the solid reflection
  hollows the target's tile-CENTERS (x%3==1 & y%3==1 stay color 11).
- SELECTION: exactly one movable object (template or hollow wall) is SELECTED, marked by color-0
  tile-centers (non-selected movable objects show color-9 centers). act5 toggles selection
  (only if the wall is hollow / selectable).
- Directional actions move the SELECTED object by 3px:
    act1 up(dy-3) act2 down(dy+3) act3 left(dx-3) act4 right(dx+3).
    A hollow WALL can only move horizontally (act3/act4); act1/act2 on the wall = NO-OP.
- Right border col x=W-1 = MOVE COUNTER: each EFFECTIVE action fills the next cell top-down color 5.
  No-op actions (blocked / wall-vertical) do NOT advance the counter.
- WIN/level-up when the solid reflection fully overlays the target (footprints equal).

Stateless step(): reads template offset, wall offset, selection, counter from the passed grid;
shapes grounded from ENTRY_GRID. Tile grid aligned to multiples of 3.
"""
import numpy as np

_LAST = [None, None]


def _tiles(cells):
    return set((3 * (y // 3), 3 * (x // 3)) for (y, x) in cells)


def _full(tiles):
    s = set()
    for (tr, tc) in tiles:
        for dy in range(3):
            for dx in range(3):
                s.add((tr + dy, tc + dx))
    return s


def _analysis(E):
    if _LAST[0] is E and _LAST[1] is not None:
        return _LAST[1]
    H = len(E)
    W = len(E[0])
    def v(y, x):
        return int(E[y][x])
    c5 = [(y, x) for y in range(H) for x in range(W) if v(y, x) == 5 and x != W - 1 and y != H - 1]
    c10 = [(y, x) for y in range(H) for x in range(W) if v(y, x) == 10]
    c11 = [(y, x) for y in range(H) for x in range(W) if v(y, x) == 11 and x != W - 1]
    templ_tiles = _tiles(c5)
    wall_tiles = _tiles(c10)
    templ_full = _full(templ_tiles)
    templ_cent = set((tr + 1, tc + 1) for (tr, tc) in templ_tiles)
    templ_border = templ_full - templ_cent
    wall_full = _full(wall_tiles)
    wall_cent = set((tr + 1, tc + 1) for (tr, tc) in wall_tiles)
    wall_border = wall_full - wall_cent
    wall_hollow = bool(wall_cent) and any(v(cy, cx) != 10 for (cy, cx) in wall_cent)
    wxs = [x for (y, x) in c10]
    wall_xmin = min(wxs) if wxs else 0
    wall_center = (min(wxs) + max(wxs)) // 2 if wxs else 0
    ty = [y for (y, x) in templ_border]
    tx = [x for (y, x) in templ_border]
    templ_ymin = min(ty) if ty else 0
    templ_xmin = min(tx) if tx else 0
    bset = set(c11)
    bcent = set((y, x) for (y, x) in bset if x % 3 == 1 and y % 3 == 1)
    A = dict(H=H, W=W, templ_full=templ_full, templ_cent=templ_cent, templ_border=templ_border,
             wall_border=wall_border, wall_cent=wall_cent, wall_hollow=wall_hollow,
             wall_xmin=wall_xmin, wall_center=wall_center, templ_ymin=templ_ymin,
             templ_xmin=templ_xmin, bset=bset, bcent=bcent)
    _LAST[0] = E
    _LAST[1] = A
    return A


def _read(arr, A):
    H, W = A["H"], A["W"]
    wxs = np.where(arr == 10)[1]
    dwall = int(wxs.min()) - A["wall_xmin"] if len(wxs) else 0
    ys, xs = np.where(arr == 5)
    m = (xs != W - 1) & (ys != H - 1)
    ys, xs = ys[m], xs[m]
    if len(xs):
        dty = int(ys.min()) - A["templ_ymin"]
        dtx = int(xs.min()) - A["templ_xmin"]
    else:
        dty = dtx = 0
    zy, zx = np.where(arr == 0)
    sel = "template"
    if len(zx) and len(wxs):
        wmin, wmax = int(wxs.min()), int(wxs.max())
        if any(wmin <= int(x) <= wmax for x in zx):
            sel = "wall"
    counter = int((arr[:, W - 1] == 5).sum())
    return dty, dtx, dwall, sel, counter


def _overlay(A, dty, dtx, dwall):
    if not A["bset"]:
        return False
    c = A["wall_center"] + dwall
    refl = set((y + dty, 2 * c - (x + dtx)) for (y, x) in A["templ_full"])
    return refl == A["bset"]


def _render(A, dty, dtx, dwall, sel, counter):
    H, W = A["H"], A["W"]
    g = np.full((H, W), 9, dtype=np.int16)
    for (y, x) in A["bset"]:
        g[y, x] = 11
    for y in range(H - 1):
        g[y, W - 1] = 11
    for x in range(W - 1):
        g[H - 1, x] = 5
    g[H - 1, W - 1] = 11
    for r in range(min(counter, H - 1)):
        g[r, W - 1] = 5
    c = A["wall_center"] + dwall
    for (y, x) in A["wall_border"]:
        nx = x + dwall
        if 0 <= nx < W:
            g[y, nx] = 10
    for (y, x) in A["wall_cent"]:
        nx = x + dwall
        if 0 <= nx < W:
            g[y, nx] = (0 if sel == "wall" else 9) if A["wall_hollow"] else 10
    for (y, x) in A["templ_border"]:
        ny, nx = y + dty, x + dtx
        if 0 <= ny < H and 0 <= nx < W:
            g[ny, nx] = 5
    for (y, x) in A["templ_cent"]:
        ny, nx = y + dty, x + dtx
        if 0 <= ny < H and 0 <= nx < W:
            g[ny, nx] = 0 if sel == "template" else 9
    for (y, x) in A["templ_full"]:
        ny, nx = y + dty, x + dtx
        ry, rx = ny, 2 * c - nx
        if 0 <= ry < H and 0 <= rx < W and (ry, rx) not in A["bcent"]:
            g[ry, rx] = 4
    return g


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    A = _analysis(ENTRY_GRID)  # noqa: F821
    arr = np.asarray(grid, dtype=np.int16)
    dty, dtx, dwall, sel, counter = _read(arr, A)
    moved = False
    if action == 5:
        if A["wall_hollow"]:
            sel = "template" if sel == "wall" else "wall"
            moved = True
    elif action in (1, 2, 3, 4):
        if sel == "wall":
            if action == 3:
                dwall -= 3
                moved = True
            elif action == 4:
                dwall += 3
                moved = True
            # act1/act2 on wall -> no-op (full-height wall can't move vertically)
        else:
            if action == 1:
                dty -= 3
            elif action == 2:
                dty += 3
            elif action == 3:
                dtx -= 3
            elif action == 4:
                dtx += 3
            moved = True
    if moved:
        counter += 1
        if _overlay(A, dty, dtx, dwall):
            lvl = CURRENT_LEVEL  # noqa: F821
            if lvl is not None and lvl >= 7:
                info["win"] = True
            else:
                info["level_up"] = True
    g = _render(A, dty, dtx, dwall, sel, counter)
    return g, info


def is_goal(grid):
    A = _analysis(ENTRY_GRID)  # noqa: F821
    arr = np.asarray(grid, dtype=np.int16)
    dty, dtx, dwall, sel, counter = _read(arr, A)
    return _overlay(A, dty, dtx, dwall)
