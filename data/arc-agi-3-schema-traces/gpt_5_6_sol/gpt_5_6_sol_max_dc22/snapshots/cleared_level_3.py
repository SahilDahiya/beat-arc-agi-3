import numpy as np

_DIRS = {1:(0,-2), 2:(0,2), 3:(-2,0), 4:(2,0)}
_TRACK = (1, 2, 6, 7, 8, 9, 11, 12, 13, 15)

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
    return {"ticks": None, "under": [[2, 2], [2, 2]], "red_phase": 0}

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
    # Sparse 6/7 checker motifs are phase switches rather than a solid hinge.
    if len(px) < 8:
        m6 = (a == 6) & (xxgrid < cut)
        m7 = (a == 7) & (xxgrid < cut)
        a[m6] = 7
        a[m7] = 6
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

def _mixed67_sites():
    """Top-lefts of entry-grounded 2x2 checker platforms made of 6 and 7."""
    eg = _entry()
    cut = _right_start()
    out = []
    for y in range(eg.shape[0]-1):
        for x in range(max(0, cut-1)):
            z = eg[y:y+2, x:x+2]
            if np.all((z == 6) | (z == 7)) and np.any(z == 6) and np.any(z == 7):
                out.append((y, x))
    return out

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

def _entry_checker_boxes(color):
    """Rectangles whose ENTRY texture is a 4-disconnected color checker."""
    eg = _entry()
    cut = _right_start()
    pts = set((int(y), int(x)) for y, x in zip(*np.where(eg[:, :cut] == color)))
    singles = []
    while pts:
        seed = pts.pop()
        comp, stack = [seed], [seed]
        while stack:
            yy, xx = stack.pop()
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                q = (yy+dy, xx+dx)
                if q in pts:
                    pts.remove(q); stack.append(q); comp.append(q)
        if len(comp) == 1:
            singles.append(seed)
    rem, boxes = set(singles), []
    while rem:
        seed = rem.pop()
        comp, stack = [seed], [seed]
        while stack:
            yy, xx = stack.pop()
            near = [q for q in rem if abs(q[0]-yy) <= 2 and abs(q[1]-xx) <= 2]
            for q in near:
                rem.remove(q); stack.append(q); comp.append(q)
        ys, xs = zip(*comp)
        boxes.append((min(ys), max(ys)+1, min(xs), max(xs)+1))
    return sorted(boxes)

def _toggle_checker_color(a, color):
    eg = _entry()
    for y0, y1, x0, x1 in _entry_checker_boxes(color):
        arr = a[y0:y1, x0:x1]
        if np.all(arr == color):
            base = eg[y0:y1, x0:x1]
            a[y0:y1, x0:x1] = np.where(base == color, color, 4)
        else:
            a[y0:y1, x0:x1] = color

def _activate_floor_switch(a, target, y0, y1, x0, x1):
    """Flatten a mixed red/target switch and reveal its target-color control."""
    eg = _entry()
    cut = _right_start()

    # Flatten the connected entry-target marking touched by the destination.
    sy, sx = np.where(eg[y0:y1+1, x0:x1+1] == target)
    seeds = [(int(y)+y0, int(x)+x0) for y, x in zip(sy, sx)]
    seen, stack = set(seeds), list(seeds)
    while stack:
        yy, xx = stack.pop()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            q = (yy+dy, xx+dx)
            if (0 <= q[0] < eg.shape[0] and 0 <= q[1] < cut
                    and eg[q] == target and q not in seen):
                seen.add(q); stack.append(q)
    for yy, xx in seen:
        a[yy, xx] = 2

    # Copy an existing five-row T template into the missing control slot.
    # A two-control stack can have a single interior gap; a full consecutive
    # stack grows downward by one template-height-plus-gap (5+4 = 9 rows).
    if not np.any(a[:, cut:] == target):
        controls = []
        for color in range(16):
            if color in (0, 3, 4, 5, target, 14):
                continue
            yy, xx0 = np.where(eg[:, cut:] == color)
            if len(xx0) >= 8:
                controls.append((int(yy.min()), color, yy, xx0 + cut))
        controls.sort(key=lambda z: z[0])
        if len(controls) >= 2:
            top, bottom = controls[0], controls[-1]
            height = int(top[2].max() - top[2].min() + 1)
            spacing = height + 4
            if len(controls) == 2 and bottom[0] - top[0] >= 2 * spacing:
                target_y0 = top[0] + spacing
            else:
                target_y0 = bottom[0] + spacing
            dy = target_y0 - top[0]
            for yy, xx in zip(top[2], top[3]):
                ny = int(yy) + dy
                if 0 <= ny < a.shape[0]:
                    a[ny, int(xx)] = target

def _red_rails():
    """Entry-grounded horizontal 5/12 rails controlled by the red operator."""
    eg = _entry()
    cut = _right_start()
    jobs = []
    for color in (5, 12):
        pts = set((int(y), int(x)) for y, x in zip(*np.where(eg[:, :cut] == color)))
        while pts:
            seed = pts.pop()
            comp, stack = [seed], [seed]
            while stack:
                yy, xx = stack.pop()
                for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    q = (yy+dy, xx+dx)
                    if q in pts:
                        pts.remove(q); stack.append(q); comp.append(q)
            ys, xs = zip(*comp)
            y0, y1, x0, x1 = min(ys), max(ys)+1, min(xs), max(xs)+1
            if x1-x0 >= 4 and x1-x0 > y1-y0:
                jobs.append((color, y0, y1, x0, x1))
    return jobs


def _red_cycle_steps():
    widths = [x1-x0 for _, _, _, x0, x1 in _red_rails()]
    return max(1, max(widths)//4) if widths else 1


def _red_operator(a, stage, under):
    """Render one stage of the complementary, ping-ponging rail fronts."""
    py, px = np.where(a == 14)
    ey = int(py.min()) if len(py) else -99
    ex = int(px.min()) if len(px) else -99
    for color, y0, y1, x0, x1 in _red_rails():
        n = _red_cycle_steps()
        if color == 5:
            if stage >= n:
                fill = np.full((y1-y0, x1-x0), 12, dtype=int)
            else:
                fill = np.full((y1-y0, x1-x0), 5, dtype=int)
                k = min(2*stage, (x1-x0)//2)
                if k:
                    fill[:, :k] = 1
                    fill[:, -k:] = 1
        else:
            if stage <= 0:
                fill = np.full((y1-y0, x1-x0), 12, dtype=int)
            else:
                fill = np.full((y1-y0, x1-x0), 5, dtype=int)
                k = min(2*(n-stage), (x1-x0)//2)
                if k:
                    fill[:, :k] = 1
                    fill[:, -k:] = 1
        riding = (y0 <= ey and ey+1 < y1 and x0 <= ex and ex+1 < x1)
        a[y0:y1, x0:x1] = fill
        if riding:
            under = fill[ey-y0:ey-y0+2, ex-x0:ex-x0+2].copy()
            a[ey:ey+2, ex:ex+2] = 14
    return under

def _shift_one_bars(a, under):
    """Shift entry-grounded horizontal color-1 platforms one tile right.

    The right-side b-shaped operator translates the two 1-bars without
    changing their shape.  If the player is riding one, translate it too.
    """
    eg = _entry()
    cut = _right_start()
    pts = set((int(y), int(x)) for y, x in zip(*np.where(eg[:, :cut] == 1)))
    bands = []
    while pts:
        seed = pts.pop()
        comp, stack = [seed], [seed]
        while stack:
            yy, xx = stack.pop()
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                q = (yy+dy, xx+dx)
                if q in pts:
                    pts.remove(q); stack.append(q); comp.append(q)
        ys, xs = zip(*comp)
        y0, y1 = min(ys), max(ys)+1
        x0, x1 = min(xs), max(xs)+1
        if x1-x0 > y1-y0:
            bands.append((y0, y1, x0, x1-x0))

    py, px = np.where(a == 14)
    player_y = int(py.min()) if len(py) else -99
    player_x = int(px.min()) if len(px) else -99
    for y0, y1, entry_x0, width in bands:
        ride1 = bool(len(px) and np.all(under == 1)
                     and y0 <= player_y and player_y+1 < y1)
        ride12 = bool(len(px) and np.all(under == 12)
                      and y0 <= player_y and player_y+1 < y1)
        xs = np.where(np.any(a[y0:y1, :cut] == 1, axis=0))[0]
        if ride1:
            xs = np.unique(np.concatenate((xs, np.arange(player_x, player_x+2))))

        if not len(xs):
            # The locked color12 endpoint wraps directly back to the entry
            # color1 location on the next pulse.
            cs = np.where(np.any(a[y0:y1, :cut] == 12, axis=0))[0]
            if ride12:
                cs = np.unique(np.concatenate((cs, np.arange(player_x, player_x+2))))
            if len(cs):
                x0 = int(cs.min())
                a[y0:y1, x0:x0+width] = 4
                a[y0:y1, entry_x0:entry_x0+width] = 1
                if ride12:
                    # Platforms slide beneath a stationary player; they do not
                    # carry it.  Its newly exposed hidden floor is whatever the
                    # reset platform leaves at the same coordinates.
                    under = a[player_y:player_y+2, player_x:player_x+2].copy()
                    a[player_y:player_y+2, player_x:player_x+2] = 14
            continue

        x0 = int(xs.min())
        # The platform retains its entry width even while e covers two cells.
        x1 = x0 + width
        nx0, nx1 = x0 + 2, x1 + 2
        if nx1 > cut:
            continue
        a[y0:y1, x0:x1] = 4
        # Five translations complete the bridge; its moving color1 state then
        # locks into the traversable color12 state at the destination.
        fill = 12 if nx0 - entry_x0 >= 10 else 1
        a[y0:y1, nx0:nx1] = fill
        if ride1:
            # As above, translation changes the floor under e but leaves its
            # screen position fixed; walking alongside the slider is manual.
            under = a[player_y:player_y+2, player_x:player_x+2].copy()
            a[player_y:player_y+2, player_x:player_x+2] = 14
    return under


def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    st = state or {}
    raw = st.get("ticks", None)
    if raw is None:
        old_ticks = 0 if np.array_equal(a, np.array(ENTRY_GRID, dtype=int)) else 1
    else:
        old_ticks = int(raw)
    under = np.array(st.get("under", [[2,2],[2,2]]), dtype=int)
    red_phase = int(st.get("red_phase", 0))

    valid_control = False
    blocked_control = False
    control_cost = 2

    if (action == 6 and x is not None and y is not None
            and 0 <= y < a.shape[0] and 0 <= x < a.shape[1]):
        clicked = int(a[y, x])
        if x >= _right_start() and clicked in (2, 6, 8, 9, 11, 15):
            # A moving platform cannot be actuated while the player occupies it.
            # Color-6 is the static pivot whose moving arms are color 7.  Red and
            # the b-shaped translator are operators rather than their floor color.
            moving_color = 7 if clicked == 6 else (-1 if clicked in (2, 11) else clicked)
            if np.all(under == moving_color):
                blocked_control = True
            else:
                valid_control = True
                if clicked == 2:
                    n = _red_cycle_steps()
                    red_phase = (red_phase + 1) % (2*n)
                    stage = min(red_phase, 2*n-red_phase)
                    under = _red_operator(a, stage, under)
                elif clicked == 6:
                    # Sparse paired 6/7 checker platforms exchange locations.
                    # If e rides one, restore its hidden pattern before swapping,
                    # then place e on the other platform with that result hidden.
                    sparse = int(np.sum(_entry()[:, :_right_start()] == 6)) < 8
                    ride = (sparse and np.any(under == 6) and np.any(under == 7)
                            and np.all((under == 6) | (under == 7)))
                    source = None
                    if ride:
                        ey, ex = np.where(a == 14)
                        if len(ex):
                            source = (int(ey.min()), int(ex.min()))
                            a[source[0]:source[0]+2, source[1]:source[1]+2] = under
                    _toggle6(a)
                    if ride and source is not None:
                        others = [p for p in _mixed67_sites() if p != source]
                        if others:
                            ty, tx = others[0]
                            under = a[ty:ty+2, tx:tx+2].copy()
                            a[ty:ty+2, tx:tx+2] = 14
                elif clicked == 8:
                    _toggle8(a)
                elif clicked == 9:
                    _toggle9(a)
                elif clicked == 11:
                    under = _shift_one_bars(a, under)
                else:
                    _toggle_checker_color(a, clicked)
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
                nonred = np.unique(dest[dest != 2]) if dest.shape == under.shape else np.array([])
                floor_target = int(nonred[0]) if len(nonred) == 1 else None
                floor_switch = (floor_target is not None and np.any(dest == 2)
                                and np.any(dest == floor_target)
                                and np.all((dest == 2) | (dest == floor_target)))
                mixed67 = (dest.shape == under.shape and np.any(dest == 6)
                           and np.any(dest == 7)
                           and np.all((dest == 6) | (dest == 7)))
                passable = (dest.shape == under.shape and np.all(dest == dest[0,0])
                            and int(dest[0,0]) in _TRACK)
                if passable or floor_switch or mixed67:
                    a[y0:y1+1, x0:x1+1] = under
                    reached_goal = bool(np.all(dest == 11))
                    if floor_switch:
                        _activate_floor_switch(a, floor_target, ny0, ny1, nx0, nx1)
                        under = np.full(dest.shape, 2, dtype=int)
                    else:
                        under = dest
                    a[ny0:ny1+1, nx0:nx1+1] = 14

    # The bottom meter groups min(level+2, 3) weighted ticks per cell
    # (observed L0=2 and L1/L2=3). Ordinary actions cost one tick,
    # transforming controls cost two, and occupied-platform failures 20.
    quantum = min(int(CURRENT_LEVEL) + 2, 3) if CURRENT_LEVEL is not None else 2
    cost = 20 if blocked_control else (2 if valid_control else 1)
    new_ticks = old_ticks + cost
    wanted = (new_ticks + quantum - 1) // quantum
    while int(np.sum(a[-1] == 3)) < wanted:
        z = np.where(a[-1] == 0)[0]
        if not len(z):
            break
        a[-1, int(z[0])] = 3

    info = {"level_up": reached_goal, "dead": False, "win": False}
    return a.tolist(), info, {"ticks": new_ticks, "under": under.tolist(), "red_phase": red_phase}

def is_goal(state, grid):
    return False
