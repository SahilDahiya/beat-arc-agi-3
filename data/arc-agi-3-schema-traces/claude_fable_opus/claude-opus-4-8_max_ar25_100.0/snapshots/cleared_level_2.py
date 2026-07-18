"""General world model: mirror/reflection puzzle (levels 0-2+). STATELESS step().

MECHANIC:
- Movable objects: a WALL (color10 mirror axis, movable only if HOLLOW=has center holes) plus one or
  more hollow TEMPLATES (color5, tile-center holes). Selection cycles via act5 over
  [wall(if hollow)] + templates(sorted by position); the SELECTED object shows color-0 centers,
  others color-9.
- Directional moves the SELECTED object 3px: act1 up / act2 down / act3 left / act4 right.
  A WALL moves only along its free axis: HORIZONTAL wall (spans width) moves vertically (act1/act2),
  VERTICAL wall (spans height) moves horizontally (act3/act4); the other two dirs are NO-OP.
- Each template casts a SOLID color-4 REFLECTION = mirror image across the wall center along the
  wall's normal axis (horizontal wall -> flip Y: (2c-y,x); vertical wall -> flip X: (y,2c-x)),
  clipped to the grid interior, skipping the floor(y=H-1)/border(x=W-1) and TARGET tile-centers.
- TARGETS: solid color11 (excl. border col). Reflection over a target covers its border (color4),
  target tile-centers stay color11.
- Counter: right border col x=W-1 fills top-down per EFFECTIVE action (color 5 in L0/L1, color 12 in L2).
- WIN/level-up when reflections fully cover all target cells (footprints subset).  [L2 win TBD]
"""
import numpy as np
from collections import deque

_LAST = [None, None]


def _comps(mask):
    H, W = mask.shape
    seen = np.zeros(mask.shape, bool)
    out = []
    ys, xs = np.where(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        q = deque([(sy, sx)])
        seen[sy, sx] = True
        cs = []
        while q:
            cy, cx = q.popleft()
            cs.append((cy, cx))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        out.append(cs)
    return out


def _tiles(cells):
    return set((3 * (y // 3), 3 * (x // 3)) for y, x in cells)


def _full(ts):
    s = set()
    for tr, tc in ts:
        for a in range(3):
            for b in range(3):
                s.add((tr + a, tc + b))
    return s


def _analysis(E):
    if _LAST[0] is E and _LAST[1] is not None:
        return _LAST[1]
    E = np.asarray(E)
    H, W = E.shape
    notb = (np.arange(W)[None, :] != W - 1)
    notf = (np.arange(H)[:, None] != H - 1)
    tcomps = _comps((E == 5) & notb & notf)
    tcomps.sort(key=lambda c: (min(y for y, x in c), min(x for y, x in c)))
    templates = []
    for c in tcomps:
        ts = _tiles(c)
        templates.append(dict(full=_full(ts),
                              cent=set((tr + 1, tc + 1) for (tr, tc) in ts),
                              size=len(c),
                              anchor=(min(y for y, x in c), min(x for y, x in c))))
    wc = [(int(y), int(x)) for y, x in zip(*np.where(E == 10))]
    wys = [y for y, x in wc]
    wxs = [x for y, x in wc]
    horiz = (max(wxs) - min(wxs)) > (max(wys) - min(wys)) if wc else True
    # Wall is a solid bar: fill its whole tile bounding box (gaps in the entry are just
    # targets drawn OVER the wall, so the wall footprint is continuous).
    _wtr = [3 * (y // 3) for (y, x) in wc]
    _wtc = [3 * (x // 3) for (y, x) in wc]
    wts = set((tr, tc)
              for tr in range(min(_wtr), max(_wtr) + 1, 3)
              for tc in range(min(_wtc), max(_wtc) + 1, 3)) if wc else set()
    wfull = _full(wts)
    wcent = set((tr + 1, tc + 1) for (tr, tc) in wts)
    wborder = wfull - wcent
    wall_hollow = bool(wcent) and any(int(E[cy, cx]) != 10 for (cy, cx) in wcent)
    if horiz:
        wcenter = (min(wys) + max(wys)) // 2
        wanchor = min(wys)
    else:
        wcenter = (min(wxs) + max(wxs)) // 2
        wanchor = min(wxs)
    tg = set()
    for c in _comps((E == 11) & notb):
        tg |= set((int(y), int(x)) for y, x in c)
    tg_cent = set((y, x) for (y, x) in tg if x % 3 == 1 and y % 3 == 1)
    A = dict(H=H, W=W, templates=templates, horiz=horiz, wfull=wfull, wborder=wborder,
             wcent=wcent, wall_hollow=wall_hollow, wcenter=wcenter, wanchor=wanchor,
             tg=tg, tg_cent=tg_cent)
    _LAST[0] = E
    _LAST[1] = A
    return A


def _movable(A):
    lst = []
    if A["wall_hollow"]:
        lst.append("wall")
    lst += list(range(len(A["templates"])))
    return lst


def _read(g, A):
    H, W = A["H"], A["W"]
    notb = (np.arange(W)[None, :] != W - 1)
    notf = (np.arange(H)[:, None] != H - 1)
    offs = [(0, 0)] * len(A["templates"])
    used = [False] * len(A["templates"])
    for c in _comps((g == 5) & notb & notf):
        anch = (min(y for y, x in c), min(x for y, x in c))
        sz = len(c)
        for i, t in enumerate(A["templates"]):
            if not used[i] and t["size"] == sz:
                offs[i] = (anch[0] - t["anchor"][0], anch[1] - t["anchor"][1])
                used[i] = True
                break
    wl = np.where(g == 10)
    if A["horiz"]:
        wall_off = int(wl[0].min()) - A["wanchor"] if len(wl[0]) else 0
    else:
        wall_off = int(wl[1].min()) - A["wanchor"] if len(wl[1]) else 0
    sel = _selection(g, A, offs, wall_off)
    col = g[:H - 1, W - 1]
    filled = [int(v) for v in col if int(v) != 11]
    counter = len(filled)
    fill = filled[0] if filled else (12 if CURRENT_LEVEL == 2 else 5)  # noqa: F821
    return offs, wall_off, sel, counter, fill


def _selection(g, A, offs, wall_off):
    # Check TEMPLATES before the wall: a selected template drawn over the wall owns the
    # overlapping 0-center cells, so it must win attribution.
    H, W = A["H"], A["W"]
    mv = _movable(A)
    order = [m for m in mv if m != "wall"] + [m for m in mv if m == "wall"]
    for m in order:
        if m == "wall":
            for (cy, cx) in A["wcent"]:
                ny = cy + wall_off if A["horiz"] else cy
                nx = cx if A["horiz"] else cx + wall_off
                if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == 0:
                    return "wall"
        else:
            dy, dx = offs[m]
            for (cy, cx) in A["templates"][m]["cent"]:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == 0:
                    return m
    return mv[0] if mv else None


def _refl_cells(A, offs, wall_off):
    c = A["wcenter"] + wall_off
    cells = set()
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            ny, nx = y + dy, x + dx
            if A["horiz"]:
                cells.add((2 * c - ny, nx))
            else:
                cells.add((ny, 2 * c - nx))
    return cells


def _render(A, offs, wall_off, sel, counter, fill):
    # Layer order (bottom -> top): background, WALL, targets, reflections, templates, frame.
    H, W = A["H"], A["W"]
    g = np.full((H, W), 9, dtype=np.int16)
    # wall (bottom)
    for (y, x) in A["wborder"]:
        ny, nx = (y + wall_off, x) if A["horiz"] else (y, x + wall_off)
        if 0 <= ny < H - 1 and 0 <= nx < W - 1:
            g[ny, nx] = 10
    for (y, x) in A["wcent"]:
        ny, nx = (y + wall_off, x) if A["horiz"] else (y, x + wall_off)
        if 0 <= ny < H - 1 and 0 <= nx < W - 1:
            g[ny, nx] = 0 if sel == "wall" else (9 if A["wall_hollow"] else 10)
    # targets (over wall)
    for (y, x) in A["tg"]:
        g[y, x] = 11
    # reflections (over targets; skip target tile-centers so they show through)
    c = A["wcenter"] + wall_off
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            ny, nx = y + dy, x + dx
            ry, rx = (2 * c - ny, nx) if A["horiz"] else (ny, 2 * c - nx)
            if 0 <= ry < H - 1 and 0 <= rx < W - 1 and (ry, rx) not in A["tg_cent"]:
                g[ry, rx] = 4
    # templates (over reflections/wall); border covers, center hole is transparent
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                if (y, x) in t["cent"]:
                    g[ny, nx] = 11 if (ny, nx) in A["tg"] else (0 if sel == i else 9)
                else:
                    g[ny, nx] = 5
    # frame (border col, floor, counter) on top
    for y in range(H - 1):
        g[y, W - 1] = 11
    for x in range(W - 1):
        g[H - 1, x] = 5
    g[H - 1, W - 1] = 11
    for r in range(min(counter, H - 1)):
        g[r, W - 1] = fill
    return g


def _win(A, offs, wall_off):
    # Every target cell must be covered by a reflection OR a template footprint.
    if not A["tg"]:
        return False
    covered = _refl_cells(A, offs, wall_off)
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            covered.add((y + dy, x + dx))
    return A["tg"] <= covered


def init_state(entry_grid):
    # Lazy init: read the actual (clean) first grid on the first predict of the level.
    return {"inited": False}


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    A = _analysis(ENTRY_GRID)  # noqa: F821
    g = np.asarray(grid, dtype=np.int16)
    if not state or not state.get("inited"):
        offs, wall_off, sel, counter, fill = _read(g, A)
        st = {"inited": True, "offs": list(offs), "wall_off": wall_off,
              "sel": sel, "counter": counter, "fill": fill}
    else:
        st = {"inited": True, "offs": list(state["offs"]), "wall_off": state["wall_off"],
              "sel": state["sel"], "counter": state["counter"], "fill": state["fill"]}
    moved = False
    mv = _movable(A)
    sel = st["sel"]
    if action == 5:
        if len(mv) > 1:
            idx = mv.index(sel) if sel in mv else 0
            st["sel"] = mv[(idx + 1) % len(mv)]
            moved = True
    elif action in (1, 2, 3, 4):
        if sel == "wall":
            if A["horiz"]:
                if action == 1:
                    st["wall_off"] -= 3; moved = True
                elif action == 2:
                    st["wall_off"] += 3; moved = True
            else:
                if action == 3:
                    st["wall_off"] -= 3; moved = True
                elif action == 4:
                    st["wall_off"] += 3; moved = True
        else:
            dy, dx = st["offs"][sel]
            if action == 1:
                dy -= 3
            elif action == 2:
                dy += 3
            elif action == 3:
                dx -= 3
            elif action == 4:
                dx += 3
            st["offs"][sel] = (dy, dx)
            moved = True
    if moved:
        st["counter"] += 1
        if _win(A, st["offs"], st["wall_off"]):
            lvl = CURRENT_LEVEL  # noqa: F821
            if lvl is not None and lvl >= 7:
                info["win"] = True
            else:
                info["level_up"] = True
    g2 = _render(A, st["offs"], st["wall_off"], st["sel"], st["counter"], st["fill"])
    return g2, info, st


def is_goal(state, grid):
    A = _analysis(ENTRY_GRID)  # noqa: F821
    if state and state.get("inited"):
        return _win(A, state["offs"], state["wall_off"])
    g = np.asarray(grid, dtype=np.int16)
    offs, wall_off, sel, counter, fill = _read(g, A)
    return _win(A, offs, wall_off)
