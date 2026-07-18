"""General world model: mirror/reflection puzzle (levels 0-4+). STATEFUL predict().

MECHANIC:
- WALLS (color10): one or more mirror bars. A VERTICAL wall spans (most of) the height and moves
  horizontally (act3/act4); a HORIZONTAL wall spans the width and moves vertically (act1/act2).
  A wall is movable/selectable if HOLLOW (has center holes). Multiple walls can cross (L4 cross).
- TEMPLATES (color5, hollow): source pieces, move any direction (act1-4).
- Each template casts SOLID color-4 REFLECTIONS = its mirror image across every NON-EMPTY SUBSET of
  walls (1 wall -> 1 reflection; 2 perpendicular walls -> 3 reflections incl. the 180deg image).
  h-wall flips Y: y->2c-y ; v-wall flips X: x->2c-x. Reflections clipped to interior, skip floor/
  border and TARGET tile-centers (target shows through).
- TARGETS (color11 excl border col): reflections/templates cover their borders; tile-centers stay 11.
- SELECTION: movable = [hollow walls] + [templates]; act5 cycles; selected shows 0-centers, others 9.
- Counter: right border col fills top-down per effective action (color 5 for L0/L1 else 12).
- WIN/level-up when every target cell is covered by a reflection OR a template footprint.

STATE: {inited, offs:[per-template (dy,dx)], woffs:[per-wall offset], sel:int(movable idx), counter, fill}.
Lazy-init from the clean first grid of each level, then track deterministically (robust to crossings).
"""
import numpy as np
from collections import deque
import itertools

_LAST = [None, None]


_N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
_N8 = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))


def _comps(mask, conn8=False):
    H, W = mask.shape
    seen = np.zeros(mask.shape, bool)
    out = []
    nbrs = _N8 if conn8 else _N4
    ys, xs = np.where(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        q = deque([(sy, sx)]); seen[sy, sx] = True; cs = []
        while q:
            cy, cx = q.popleft(); cs.append((cy, cx))
            for dy, dx in nbrs:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx))
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


def _group(idxs):
    idxs = sorted(idxs); groups = []; cur = []
    for i in idxs:
        if cur and i - cur[-1] > 2:
            groups.append(cur); cur = []
        cur.append(i)
    if cur:
        groups.append(cur)
    return groups


def _mkwall(kind, xmin, xmax, ymin, ymax, E):
    trs = range(3 * (ymin // 3), 3 * (ymax // 3) + 1, 3)
    tcs = range(3 * (xmin // 3), 3 * (xmax // 3) + 1, 3)
    tiles = set((tr, tc) for tr in trs for tc in tcs)
    full = _full(tiles)
    cent = set((tr + 1, tc + 1) for (tr, tc) in tiles)
    border = full - cent
    hollow = bool(cent) and any(int(E[cy, cx]) != 10 for (cy, cx) in cent)
    center = (ymin + ymax) // 2 if kind == "h" else (xmin + xmax) // 2
    return dict(kind=kind, center=center, full=full, cent=cent, border=border, hollow=hollow)


def _analysis(E):
    if _LAST[0] is E and _LAST[1] is not None:
        return _LAST[1]
    E = np.asarray(E)
    H, W = E.shape
    notb = (np.arange(W)[None, :] != W - 1)
    notf = (np.arange(H)[:, None] != H - 1)
    # templates
    # templates: 8-connected (pieces touch diagonally, e.g. L5's upper piece)
    tcomps = _comps((E == 5) & notb & notf, conn8=True)
    # selection cycle order by size: DESC with a single wall, ASC with 2+ walls (observed L2/L3 vs L5).
    _c10 = (E == 10)
    _nwalls = (len(_group([x for x in range(W) if _c10[:, x].sum() > 0.4 * H]))
               + len(_group([y for y in range(H) if _c10[y, :].sum() > 0.4 * W])))
    _sgn = 1 if _nwalls >= 2 else -1
    tcomps.sort(key=lambda c: (_sgn * len(c), min(y for y, x in c), min(x for y, x in c)))
    templates = []
    for c in tcomps:
        ts = _tiles(c)
        templates.append(dict(full=_full(ts),
                              cent=set((tr + 1, tc + 1) for (tr, tc) in ts),
                              size=len(c),
                              anchor=(min(y for y, x in c), min(x for y, x in c))))
    # walls: vertical (full-height cols) and horizontal (full-width rows)
    c10 = (E == 10)
    colcount = c10.sum(axis=0)
    rowcount = c10.sum(axis=1)
    walls = []
    # horizontal walls first, then vertical (matches the observed act5 selection cycle order)
    for band in _group([y for y in range(H) if rowcount[y] > 0.4 * W]):
        xs = [x for x in range(W) if any(c10[y, x] for y in band)]
        walls.append(_mkwall("h", min(xs), max(xs), min(band), max(band), E))
    for band in _group([x for x in range(W) if colcount[x] > 0.4 * H]):
        ys = [y for y in range(H) if any(c10[y, x] for x in band)]
        walls.append(_mkwall("v", min(band), max(band), min(ys), max(ys), E))
    # targets
    tg = set()
    for c in _comps((E == 11) & notb):
        tg |= set((int(y), int(x)) for y, x in c)
    tg_cent = set((y, x) for (y, x) in tg if x % 3 == 1 and y % 3 == 1)
    # movable list: hollow walls (in order) then templates
    movable = [("wall", i) for i, w in enumerate(walls) if w["hollow"]]
    movable += [("tmpl", i) for i in range(len(templates))]
    A = dict(H=H, W=W, templates=templates, walls=walls, movable=movable, tg=tg, tg_cent=tg_cent)
    _LAST[0] = E; _LAST[1] = A
    return A


def _wall_cell(w, off, y, x):
    return (y + off, x) if w["kind"] == "h" else (y, x + off)


def _sel_wall_centers(A, sel, woffs):
    kind, i = A["movable"][sel]
    if kind != "wall":
        return set()
    w = A["walls"][i]
    return set(_wall_cell(w, woffs[i], cy, cx) for (cy, cx) in w["cent"])


def _reflect(y, x, subset, A, woffs):
    for wi in subset:
        w = A["walls"][wi]; c = w["center"] + woffs[wi]
        if w["kind"] == "h":
            y = 2 * c - y
        else:
            x = 2 * c - x
    return y, x


def _all_refl(A, offs, woffs):
    """All reflection cells (full footprints) of every template across every non-empty wall subset."""
    cells = set()
    nW = len(A["walls"])
    subsets = []
    for r in range(1, nW + 1):
        subsets += list(itertools.combinations(range(nW), r))
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            ay, ax = y + dy, x + dx
            for s in subsets:
                cells.add(_reflect(ay, ax, s, A, woffs))
    return cells


def _win(A, offs, woffs):
    if not A["tg"]:
        return False
    covered = _all_refl(A, offs, woffs)
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            covered.add((y + dy, x + dx))
    return A["tg"] <= covered


def _render(A, offs, woffs, sel, counter, fill):
    H, W = A["H"], A["W"]
    g = np.full((H, W), 9, dtype=np.int16)
    # walls (bottom): borders, then non-selected centers, then the SELECTED wall's 0-centers last
    # (so at wall crossings the selected wall's marker takes precedence).
    for wi, w in enumerate(A["walls"]):
        off = woffs[wi]
        for (y, x) in w["border"]:
            ny, nx = _wall_cell(w, off, y, x)
            if 0 <= ny < H - 1 and 0 <= nx < W - 1:
                g[ny, nx] = 10
    for wi, w in enumerate(A["walls"]):
        if A["movable"][sel] == ("wall", wi):
            continue
        off = woffs[wi]
        for (y, x) in w["cent"]:
            ny, nx = _wall_cell(w, off, y, x)
            if 0 <= ny < H - 1 and 0 <= nx < W - 1:
                g[ny, nx] = 9 if w["hollow"] else 10
    # targets over walls
    for (y, x) in A["tg"]:
        g[y, x] = 11
    # reflections over targets (skip target-centers)
    nW = len(A["walls"])
    subsets = []
    for r in range(1, nW + 1):
        subsets += list(itertools.combinations(range(nW), r))
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        for (y, x) in t["full"]:
            ay, ax = y + dy, x + dx
            for s in subsets:
                ry, rx = _reflect(ay, ax, s, A, woffs)
                if 0 <= ry < H - 1 and 0 <= rx < W - 1 and (ry, rx) not in A["tg_cent"]:
                    g[ry, rx] = 4
    # SELECTED wall's 0-centers over reflections (but under targets)
    _sk, _si = A["movable"][sel]
    if _sk == "wall":
        w = A["walls"][_si]; off = woffs[_si]
        for (y, x) in w["cent"]:
            ny, nx = _wall_cell(w, off, y, x)
            if 0 <= ny < H - 1 and 0 <= nx < W - 1 and (ny, nx) not in A["tg"]:
                g[ny, nx] = 0
    # templates over everything
    selwc = _sel_wall_centers(A, sel, woffs)
    for i, t in enumerate(A["templates"]):
        dy, dx = offs[i]
        tsel = (A["movable"][sel] == ("tmpl", i))
        for (y, x) in t["full"]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                if (y, x) in t["cent"]:
                    if (ny, nx) in A["tg"]:
                        g[ny, nx] = 11
                    elif tsel or (ny, nx) in selwc:
                        g[ny, nx] = 0
                    else:
                        g[ny, nx] = 9
                else:
                    g[ny, nx] = 5
    # frame
    for y in range(H - 1):
        g[y, W - 1] = 11
    for x in range(W - 1):
        g[H - 1, x] = 5
    g[H - 1, W - 1] = 11
    for r in range(min(counter, H - 1)):
        g[r, W - 1] = fill
    return g


def _read_init(g, A):
    H, W = A["H"], A["W"]
    # template offsets: match current color5 comps to entry templates by size
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
    # wall offsets: current band position minus entry center (one band per orientation assumed)
    woffs = [0] * len(A["walls"])
    c10 = (g == 10)
    for i, w in enumerate(A["walls"]):
        if w["kind"] == "v":
            cols = [x for x in range(W) if c10[:, x].sum() > 0.4 * H]
            if cols:
                woffs[i] = (min(cols) + max(cols)) // 2 - w["center"]
        else:
            rows = [y for y in range(H) if c10[y, :].sum() > 0.4 * W]
            if rows:
                woffs[i] = (min(rows) + max(rows)) // 2 - w["center"]
    # selection: the movable object with the MOST 0-centers (others may share only crossing cells)
    sel = 0
    best = -1
    for idx, (kind, i) in enumerate(A["movable"]):
        if kind == "wall":
            w = A["walls"][i]
            cells = [_wall_cell(w, woffs[i], cy, cx) for (cy, cx) in w["cent"]]
        else:
            dy, dx = offs[i]
            cells = [(cy + dy, cx + dx) for (cy, cx) in A["templates"][i]["cent"]]
        cnt = sum(1 for (cy, cx) in cells if 0 <= cy < H and 0 <= cx < W and g[cy, cx] == 0)
        if cnt > best:
            best = cnt
            sel = idx
    col = g[:H - 1, W - 1]
    filled = [int(v) for v in col if int(v) != 11]
    counter = len(filled)
    fill = filled[0] if filled else (5 if CURRENT_LEVEL in (0, 1) else 12)  # noqa: F821
    return offs, woffs, sel, counter, fill


def init_state(entry_grid):
    return {"inited": False}


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    A = _analysis(ENTRY_GRID)  # noqa: F821
    g = np.asarray(grid, dtype=np.int16)
    if not state or not state.get("inited"):
        offs, woffs, sel, counter, fill = _read_init(g, A)
        st = {"inited": True, "offs": list(offs), "woffs": list(woffs),
              "sel": sel, "counter": counter, "fill": fill}
    else:
        st = {"inited": True, "offs": list(state["offs"]), "woffs": list(state["woffs"]),
              "sel": state["sel"], "counter": state["counter"], "fill": state["fill"]}
    moved = False
    mv = A["movable"]
    sel = st["sel"]
    if action == 5:
        if len(mv) > 1:
            st["sel"] = (sel + 1) % len(mv)
            moved = True
    elif action in (1, 2, 3, 4):
        kind, i = mv[sel]
        if kind == "wall":
            w = A["walls"][i]
            if w["kind"] == "h":
                if action == 1:
                    st["woffs"][i] -= 3; moved = True
                elif action == 2:
                    st["woffs"][i] += 3; moved = True
            else:
                if action == 3:
                    st["woffs"][i] -= 3; moved = True
                elif action == 4:
                    st["woffs"][i] += 3; moved = True
        else:
            dy, dx = st["offs"][i]
            if action == 1:
                dy -= 3
            elif action == 2:
                dy += 3
            elif action == 3:
                dx -= 3
            elif action == 4:
                dx += 3
            st["offs"][i] = (dy, dx)
            moved = True
    if moved:
        st["counter"] += 1
        if _win(A, st["offs"], st["woffs"]):
            lvl = CURRENT_LEVEL  # noqa: F821
            if lvl is not None and lvl >= 7:
                info["win"] = True
            else:
                info["level_up"] = True
    g2 = _render(A, st["offs"], st["woffs"], st["sel"], st["counter"], st["fill"])
    return g2, info, st


def is_goal(state, grid):
    A = _analysis(ENTRY_GRID)  # noqa: F821
    if state and state.get("inited"):
        return _win(A, state["offs"], state["woffs"])
    g = np.asarray(grid, dtype=np.int16)
    offs, woffs, sel, counter, fill = _read_init(g, A)
    return _win(A, offs, woffs)
