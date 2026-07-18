import numpy as np

_DIRS = {1:(0,-2), 2:(0,2), 3:(-2,0), 4:(2,0)}
_TRACK = (2, 8, 9, 11, 13)

def init_state(entry_grid):
    # The first-ever action has no before-frame during replay, so ticks starts
    # unknown and is recovered from whether the observed grid is still ENTRY_GRID.
    return {"ticks": None, "under": [[2, 2], [2, 2]]}

def _clear_guides(a):
    sub = a[10:54, 34:]
    sub[sub == 0] = 5

def _toggle8(a):
    """Toggle the left 8 arm: left of pivot <-> above pivot."""
    xxgrid = np.indices(a.shape)[1]
    ly, lx = np.where((a == 8) & (xxgrid < 32))
    # Ground the hinge center from ENTRY_GRID: the player may currently cover
    # part of the color-13 pivot, which must not shift the rotation center.
    eg = np.array(ENTRY_GRID, dtype=int)
    exgrid = np.indices(eg.shape)[1]
    py, px = np.where((eg == 13) & (exgrid < 32))
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
        if 0 <= yy < a.shape[0] and 0 <= xx < 32:
            a[yy, xx] = 8

def _nine_boxes():
    """Ground the two 9-motif rectangles from their row clusters in ENTRY_GRID."""
    eg = np.array(ENTRY_GRID, dtype=int)
    xxgrid = np.indices(eg.shape)[1]
    ey, ex = np.where((eg == 9) & (xxgrid < 32))
    rows = sorted(set(ey.tolist()))
    clusters = []
    for rr in rows:
        if not clusters or rr > clusters[-1][-1] + 1:
            clusters.append([rr])
        else:
            clusters[-1].append(rr)
    boxes = []
    for rs in clusters:
        mask = np.isin(ey, rs)
        gx, gy = ex[mask], ey[mask]
        boxes.append((int(gy.min()), int(gy.max())+1,
                      int(gx.min()), int(gx.max())+1))
    return boxes

def _toggle9(a):
    boxes = _nine_boxes()
    if len(boxes) < 2:
        return
    y0,y1,x0,x1 = boxes[0]
    u0,u1,v0,v1 = boxes[1]
    p, q = a[y0:y1, x0:x1].copy(), a[u0:u1, v0:v1].copy()
    if p.shape == q.shape:
        a[y0:y1, x0:x1] = q
        a[u0:u1, v0:v1] = p

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

    if (action == 6 and x is not None and y is not None
            and 0 <= y < a.shape[0] and 0 <= x < a.shape[1]):
        clicked = int(a[y, x])
        if x >= 34 and clicked in (8, 9):
            # A moving platform cannot be actuated while the player occupies it.
            # The attempted action is blocked and incurs a large meter penalty.
            if np.all(under == clicked):
                blocked_control = True
            else:
                valid_control = True
                if clicked == 8:
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
                passable = (dest.shape == under.shape and np.all(dest == dest[0,0])
                            and int(dest[0,0]) in _TRACK)
                if passable:
                    a[y0:y1+1, x0:x1+1] = under
                    reached_goal = bool(np.all(dest == 11))
                    under = dest
                    a[ny0:ny1+1, nx0:nx1+1] = 14

    cost = 20 if blocked_control else (2 if valid_control else 1)
    new_ticks = old_ticks + cost
    wanted = (new_ticks + 1) // 2
    while int(np.sum(a[-1] == 3)) < wanted:
        z = np.where(a[-1] == 0)[0]
        if not len(z):
            break
        a[-1, int(z[0])] = 3

    info = {"level_up": reached_goal, "dead": False, "win": False}
    return a.tolist(), info, {"ticks": new_ticks, "under": under.tolist()}

def is_goal(state, grid):
    return False
