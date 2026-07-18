import numpy as np

BG = 1
BODY = 14      # player body 'e'
HEAD = 0       # player head (facing side); ALSO grabbed-box border color
B_INNER = 9    # box inner
B_NORMAL = 4   # box border normal
B_HL = 3       # box border when E faces it (highlight)
B_GRAB = 0     # box border when grabbed/carried

CDIR = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}          # action -> cell delta
FACE_NAME = {1: 'up', 2: 'down', 3: 'left', 4: 'right'}
FACE_D = {'up': (0, -4), 'down': (0, 4), 'left': (-4, 0), 'right': (4, 0)}


def _entry():
    try:
        e = ENTRY_GRID
    except NameError:
        return None
    return np.array(e) if e is not None else None


def _cur_level():
    try:
        return CURRENT_LEVEL
    except NameError:
        return None


def _bar_filled(g):
    # HUD move counter on row 63: bg=7, fills with color 4 from the RIGHT.
    return int((np.asarray(g)[63] == 4).sum())


def init_state(entry_grid):
    # HUD move-counter bar = floor((step + off)/3). Rare one-time "skips" permanently drop off by 1
    # (observed off: 2 -> 1 -> 0). We can't predict a skip, but we self-correct off each step by
    # comparing our previous predicted filled (pf) to the real grid's filled -> exactly 1 mismatch
    # per skip, forward-exact otherwise. off starts 2 on level 0 (framework hides global step#0) else 1.
    lvl = _cur_level()
    seen = _bar_filled(entry_grid) if entry_grid is not None else 0
    return {'n': 0, 'off': 2 if lvl == 0 else 1, 'pf': seen}


def _d_region(entry):
    if entry is None:
        return None
    ys, xs = np.where(entry == 2)
    if len(xs) == 0:
        return None
    x0 = max(0, int(xs.min()) - 1); x1 = min(entry.shape[1] - 1, int(xs.max()) + 1)
    y0 = max(0, int(ys.min()) - 1); y1 = min(entry.shape[0] - 1, int(ys.max()) + 1)
    return (x0, y0, x1, y1)


def _find_e(g):
    ys, xs = np.where(g == BODY)
    if len(xs) == 0:
        return None
    return (int(xs.min()) // 4) * 4, (int(ys.min()) // 4) * 4


def _e_facing(g, ex, ey):
    b = g[ey:ey + 4, ex:ex + 4]
    if np.all(b[0, :] == HEAD): return 'up'
    if np.all(b[3, :] == HEAD): return 'down'
    if np.all(b[:, 0] == HEAD): return 'left'
    if np.all(b[:, 3] == HEAD): return 'right'
    return 'up'


def _box_type(g, cx, cy):
    H, W = g.shape
    if cx < 0 or cy < 0 or cx + 4 > W or cy + 4 > H:
        return None
    b = g[cy:cy + 4, cx:cx + 4]
    if not np.all(b[1:3, 1:3] == B_INNER):
        return None
    ring = np.concatenate([b[0, :], b[3, :], b[1:3, 0], b[1:3, 3]])
    vals = set(int(v) for v in ring)
    if vals == {B_GRAB}:
        return 'grab'
    if vals <= {B_NORMAL, B_HL}:
        return 'normal'
    return None


def _find_boxes(g):
    H, W = g.shape
    boxes = []
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            t = _box_type(g, cx, cy)
            if t is not None:
                boxes.append([cx, cy, t])
    return boxes


def _paint_bar(g, filled):
    for x in range(64):
        g[63][x] = 4 if x >= 64 - filled else 7


def _render(shape, entry, dreg, boxes, e, face, filled):
    H, W = shape
    ng = np.full((H, W), BG, dtype=int)
    if dreg is not None and entry is not None:
        x0, y0, x1, y1 = dreg
        ng[y0:y1 + 1, x0:x1 + 1] = entry[y0:y1 + 1, x0:x1 + 1]
    ex, ey = e
    fdx, fdy = FACE_D[face]
    faced = (ex + fdx, ey + fdy)
    for (cx, cy, t) in boxes:
        if t == 'grab':
            border = B_GRAB
        else:
            border = B_HL if (cx, cy) == faced else B_NORMAL
        ng[cy:cy + 4, cx:cx + 4] = border
        ng[cy + 1:cy + 3, cx + 1:cx + 3] = B_INNER
    ng[ey:ey + 4, ex:ex + 4] = BODY
    if face == 'up':
        ng[ey, ex:ex + 4] = HEAD
    elif face == 'down':
        ng[ey + 3, ex:ex + 4] = HEAD
    elif face == 'left':
        ng[ey:ey + 4, ex] = HEAD
    elif face == 'right':
        ng[ey:ey + 4, ex + 3] = HEAD
    _paint_bar(ng, filled)
    return ng


def _d_cells(dreg):
    if dreg is None:
        return set()
    x0, y0, x1, y1 = dreg
    cells = set()
    cy = y0
    while cy + 4 <= y1 + 1:
        cx = x0
        while cx + 4 <= x1 + 1:
            cells.add((cx, cy))
            cx += 4
        cy += 4
    return cells


def is_goal(grid):
    # HYPOTHESIS (unconfirmed): level clears when all small boxes are placed (released) on D's cells.
    g = np.array(grid)
    dreg = _d_region(_entry())
    dcells = _d_cells(dreg)
    if not dcells:
        return False
    boxes = _find_boxes(g)
    positions = set((b[0], b[1]) for b in boxes)
    return positions == dcells and all(b[2] != 'grab' for b in boxes)


def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    H, W = g.shape
    entry = _entry()
    dreg = _d_region(entry)

    # ---- offset-tracking bar phase ----
    cur = _bar_filled(g)
    n = state.get('n', 0)
    off = state.get('off', 2)
    pf = state.get('pf', cur)
    off += (cur - pf)  # self-correct offset from observed-vs-predicted (absorbs one-time skips)

    e = _find_e(g)
    if e is None or action not in (1, 2, 3, 4, 5):
        return g.tolist(), {}, {'n': n, 'off': off, 'pf': cur}

    ex, ey = e
    face = _e_facing(g, ex, ey)
    boxes = _find_boxes(g)
    carried = None
    for i, b in enumerate(boxes):
        if b[2] == 'grab':
            carried = i
            break

    if action in CDIR:
        dcx, dcy = CDIR[action]
        ddx, ddy = dcx * 4, dcy * 4
        moving = [(ex, ey)]
        if carried is not None:
            moving.append((boxes[carried][0], boxes[carried][1]))
        cur_cells = set(moving)
        obst = set((b[0], b[1]) for i, b in enumerate(boxes) if i != carried)
        ok = True
        for (mx, my) in moving:
            nx, ny = mx + ddx, my + ddy
            if nx < 0 or ny < 0 or nx + 4 > W or ny + 3 > 62:
                ok = False; break
            if (nx, ny) in cur_cells:
                continue
            if (nx, ny) in obst:
                ok = False; break
        if ok:
            ex, ey = ex + ddx, ey + ddy
            if carried is not None:
                boxes[carried][0] += ddx; boxes[carried][1] += ddy
            else:
                face = FACE_NAME[action]
    else:  # action == 5: toggle faced box (grab <-> release)
        fdx, fdy = FACE_D[face]
        fcx, fcy = ex + fdx, ey + fdy
        if carried is not None:
            boxes[carried][2] = 'normal'
        else:
            for b in boxes:
                if (b[0], b[1]) == (fcx, fcy) and b[2] == 'normal':
                    b[2] = 'grab'
                    break

    # advance bar: every action increments the step counter; filled = floor((n+off)/3)
    n2 = n + 1
    next_filled = min(64, (n2 + off) // 3)
    nstate = {'n': n2, 'off': off, 'pf': next_filled}

    ng = _render((H, W), entry, dreg, boxes, (ex, ey), face, next_filled)
    return ng.tolist(), {}, nstate
