import numpy as np

_DIRS = {1:(0,-2), 2:(0,2), 3:(-2,0), 4:(2,0)}
_TRACK = (2, 6, 7, 8, 9, 11, 13)

def _entry():
    return np.array(ENTRY_GRID, dtype=int)

def _right_start():
    eg = _entry()
    # Two dashed black separator columns divide the yellow playfield from the
    # gray controls. They have by far the largest interior zero counts.
    z = np.sum(eg == 0, axis=0)
    m = int(z.max())
    sep = np.where(z >= max(2, int(m * 0.8)))[0]
    return int(sep.max()) + 1 if len(sep) else eg.shape[1]

def _play_rows():
    eg = _entry()
    rs = np.where(np.sum(eg == 5, axis=1) > 5)[0]
    return ((int(rs.min()), int(rs.max())+1) if len(rs) else (0, eg.shape[0]-1))

def init_state(entry_grid):
    # The first-ever action has no before-frame during replay, so ticks starts
    # unknown and is recovered from whether the observed grid is still ENTRY_GRID.
    return {"ticks": None, "under": [[2, 2], [2, 2]]}

def _clear_guides(a):
    y0, y1 = _play_rows()
    sub = a[y0:y1, _right_start():]
    sub[sub == 0] = 5

def _toggle8(a):
    """Toggle the left 8 arm: left of pivot <-> above pivot."""
    xxgrid = np.indices(a.shape)[1]
    cut = _right_start()
    ly, lx = np.where((a == 8) & (xxgrid < cut))
    # Ground the hinge center from ENTRY_GRID: the player may currently cover
    # part of the color-13 pivot, which must not shift the rotation center.
    eg = np.array(ENTRY_GRID, dtype=int)
    exgrid = np.indices(eg.shape)[1]
    py, px = np.where((eg == 13) & (exgrid < cut))
    if not len(lx) or not len(px):
        return
    cx, cy = float(px.mean()), float(py.mean())
    mx, my = float(lx.mean()), float(ly.mean())
    clockwise = abs(mx-cx) >= abs(my-cy)   # left -> above
    old = list(zip(ly.tolist(), lx.tolist()))
    new = []
    for yy, xx in old:
        dx, dy = xx-cx, yy-cy
        nx, ny = ((cx-dy, cy+dx) if clockwise else (cx+dy, cy-dx))
        new.append((int(round(ny)), int(round(nx))))
    for yy, xx in old:
        a[yy, xx] = 4
    for yy, xx in new:
        if 0 <= yy < a.shape[0] and 0 <= xx < cut:
            a[yy, xx] = 8

def _toggle6(a):
    """Toggle both color-7 arms around the static color-6 pivot."""
    cut = _right_start()
    xxgrid = np.indices(a.shape)[1]
    ly, lx = np.where((a == 7) & (xxgrid < cut))
    eg = _entry()
    exgrid = np.indices(eg.shape)[1]
    py, px = np.where((eg == 6) & (exgrid < cut))
    if not len(lx) or not len(px):
        return
    cx, cy = float(px.mean()), float(py.mean())
    horizontal = (int(lx.max()-lx.min()) >= int(ly.max()-ly.min()))
    old, new = list(zip(ly.tolist(), lx.tolist())), []
    for yy, xx in old:
        dx, dy = xx-cx, yy-cy
        nx, ny = ((cx-dy, cy+dx) if horizontal else (cx+dy, cy-dx))
        new.append((int(round(ny)), int(round(nx))))
    for yy, xx in old:
        a[yy, xx] = 4
    for yy, xx in new:
        if 0 <= yy < a.shape[0] and 0 <= xx < cut:
            a[yy, xx] = 7

def _nine_boxes():
    """Ground solid and checker 9-motif rectangles from ENTRY_GRID."""
    eg = _entry()
    cut = _right_start()
    pts = set((int(y), int(x)) for y, x in zip(*np.where(eg[:, :cut] == 9)))
    solid_boxes, singles = [], []
    while pts:
        seed = pts.pop()
        comp, stack = [seed], [seed]
        while stack:
            yy, xx = stack.pop()
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                q = (yy+dy, xx+dx)
                if q in pts:
                    pts.remove(q); stack.append(q); comp.append(q)
        if len(comp) > 1:
            ys, xs = zip(*comp)
            solid_boxes.append((min(ys), max(ys)+1, min(xs), max(xs)+1))
        else:
            singles.append(comp[0])
    # Checker cells are 4-disconnected but connect diagonally/within distance 2.
    rem, checker_boxes = set(singles), []
    while rem:
        seed = rem.pop()
        comp, stack = [seed], [seed]
        while stack:
            yy, xx = stack.pop()
            near = [q for q in rem if abs(q[0]-yy) <= 2 and abs(q[1]-xx) <= 2]
            for q in near:
                rem.remove(q); stack.append(q); comp.append(q)
        ys, xs = zip(*comp)
        checker_boxes.append((min(ys), max(ys)+1, min(xs), max(xs)+1))
    return sorted(solid_boxes + checker_boxes)

def _toggle9(a):
    # Each motif independently alternates solid fill and the common checker
    # texture (9 on odd x+y, yellow background on even x+y). This also covers
    # unequal rectangle sizes in later levels.
    for y0,y1,x0,x1 in _nine_boxes():
        arr = a[y0:y1, x0:x1]
        solid = bool(np.all(arr == 9))
        if solid:
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    a[yy, xx] = 9 if (xx + yy) % 2 else 4
        else:
            a[y0:y1, x0:x1] = 9

def _activate8_switch(a, y0, y1, x0, x1):
    """Press the small mixed 2/8 floor switch and reveal its 8 control."""
    eg = _entry()
    cut = _right_start()

    # Flatten the connected entry-8 component touched by the player's 2x2
    # destination. This is the five-cell marking embedded in the red switch.
    seeds = [(int(y), int(x)) for y, x in zip(
        *np.where(eg[y0:y1+1, x0:x1+1] == 8))]
    seeds = [(y+y0, x+x0) for y, x in seeds]
    seen, stack = set(seeds), list(seeds)
    while stack:
        yy, xx = stack.pop()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            q = (yy+dy, xx+dx)
            if (0 <= q[0] < eg.shape[0] and 0 <= q[1] < cut
                    and eg[q] == 8 and q not in seen):
                seen.add(q); stack.append(q)
    for yy, xx in seen:
        a[yy, xx] = 2

    # The two entry controls are identical T templates with one empty slot
    # midway between them. Materialize an 8-colored copy in that slot.
    if not np.any(a[:, cut:] == 8):
        controls = []
        for color in range(16):
            if color in (0, 3, 4, 5, 8, 14):
                continue
            yy, xx0 = np.where(eg[:, cut:] == color)
            if len(xx0) >= 8:
                controls.append((int(yy.min()), color, yy, xx0 + cut))
        controls.sort(key=lambda z: z[0])
        if len(controls) >= 2:
            top, bottom = controls[0], controls[-1]
            target_y0 = (top[0] + bottom[0]) // 2
            dy = target_y0 - top[0]
            for yy, xx in zip(top[2], top[3]):
                ny = int(yy) + dy
                if 0 <= ny < a.shape[0]:
                    a[ny, int(xx)] = 8

def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    st = state or {}
    raw = st.get("ticks", None)
    if raw is None:
        old_ticks = 0 if np.array_equal(a, np.array(ENTRY_GRID, dtype=int)) else 1
    else:
        old_ticks = int(raw)
    under = np.array(st.get("under", [[2,2],[2,2]]), dtype=int)

    valid_control = False
    blocked_control = False
    control_cost = 2

    if (action == 6 and x is not None and y is not None
            and 0 <= y < a.shape[0] and 0 <= x < a.shape[1]):
        clicked = int(a[y, x])
        if x >= _right_start() and clicked in (6, 8, 9):
            # A moving platform cannot be actuated while the player occupies it.
            # Color-6 is the static pivot whose moving arms are color 7.
            moving_color = 7 if clicked == 6 else clicked
            if np.all(under == moving_color):
                blocked_control = True
            else:
                valid_control = True
                if clicked == 6:
                    _toggle6(a)
                elif clicked == 8:
                    _toggle8(a)
                else:
                    _toggle9(a)
                _clear_guides(a)

    reached_goal = False
    if action in _DIRS:
        ys, xs = np.where(a == 14)
        if len(xs):
            x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
            dx, dy = _DIRS[action]
            nx0, nx1, ny0, ny1 = x0+dx, x1+dx, y0+dy, y1+dy
            if 0 <= nx0 and nx1 < a.shape[1] and 0 <= ny0 and ny1 < a.shape[0]:
                dest = a[ny0:ny1+1, nx0:nx1+1].copy()
                floor_switch = (dest.shape == under.shape and np.any(dest == 8)
                                and np.any(dest == 2)
                                and np.all((dest == 2) | (dest == 8)))
                passable = (dest.shape == under.shape and np.all(dest == dest[0,0])
                            and int(dest[0,0]) in _TRACK)
                if passable or floor_switch:
                    a[y0:y1+1, x0:x1+1] = under
                    reached_goal = bool(np.all(dest == 11))
                    if floor_switch:
                        _activate8_switch(a, ny0, ny1, nx0, nx1)
                        under = np.full(dest.shape, 2, dtype=int)
                    else:
                        under = dest
                    a[ny0:ny1+1, nx0:nx1+1] = 14

    # The bottom meter groups increasingly many weighted ticks per cell:
    # level 0 uses pairs, level 1 triples, etc. Ordinary actions cost one
    # tick, transforming controls cost two, and occupied-platform failures 20.
    quantum = (int(CURRENT_LEVEL) + 2) if CURRENT_LEVEL is not None else 2
    cost = 20 if blocked_control else (2 if valid_control else 1)
    new_ticks = old_ticks + cost
    wanted = (new_ticks + quantum - 1) // quantum
    while int(np.sum(a[-1] == 3)) < wanted:
        z = np.where(a[-1] == 0)[0]
        if not len(z):
            break
        a[-1, int(z[0])] = 3

    info = {"level_up": reached_goal, "dead": False, "win": False}
    return a.tolist(), info, {"ticks": new_ticks, "under": under.tolist()}

def is_goal(state, grid):
    return False
