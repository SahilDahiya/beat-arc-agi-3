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
    """Ground complete solid and checker rectangles of a toggle color.

    Irregular target markings inside mixed floor switches are deliberately
    excluded: a connected component counts as a solid motif only when it
    completely fills its bounding rectangle.
    """
    eg = _entry()
    cut = _right_start()
    pts = set((int(y), int(x)) for y, x in zip(*np.where(eg[:, :cut] == color)))
    singles, solids = [], []
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
        else:
            ys, xs = zip(*comp)
            box = (min(ys), max(ys)+1, min(xs), max(xs)+1)
            if len(comp) == (box[1]-box[0]) * (box[3]-box[2]):
                solids.append(box)
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
    return sorted(solids + boxes)

def _toggle_checker_color(a, color):
    for y0, y1, x0, x1 in _entry_checker_boxes(color):
        arr = a[y0:y1, x0:x1]
        if np.all(arr == color):
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    a[yy, xx] = color if (xx + yy) % 2 else 4
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
        # Level4's carriage panel fills the lower control slots.  Its missing
        # floor-switch control is therefore inserted in the open slot above
        # the stack, using the unique bottom color-6 T as the five-row
        # template.  Ground both the shape and placement from ENTRY_GRID.
        left = eg[:, :cut]
        if (target == 15 and np.any(left == 8) and not np.any(left == 13)):
            ty, tx = np.where(eg[:, cut:] == 6)
            colored = np.where(np.any(~np.isin(eg[:, cut:], (0, 3, 4, 5)), axis=1))[0]
            if len(ty) and len(colored):
                target_y0 = int(colored.min()) - 7
                dy = target_y0 - int(ty.min())
                for yy, xx in zip(ty, tx + cut):
                    ny = int(yy) + dy
                    if 0 <= ny < a.shape[0]:
                        a[ny, int(xx)] = target
                return
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

def _eight_buttons():
    """Four small 4x4 mover buttons shown above the rectangular 8 label."""
    eg = _entry()
    cut = _right_start()
    out = []
    for color in (9, 10):
        pts = set((int(y), int(x)) for y, x in zip(*np.where(eg[:, cut:] == color)))
        pts = {(y, x+cut) for y, x in pts}
        while pts:
            seed = pts.pop(); comp = [seed]; stack = [seed]
            while stack:
                yy, xx = stack.pop()
                for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    q = (yy+dy, xx+dx)
                    if q in pts:
                        pts.remove(q); stack.append(q); comp.append(q)
            ys, xs = zip(*comp)
            box = (min(ys), max(ys)+1, min(xs), max(xs)+1)
            if len(comp) == 16 and box[1]-box[0] == 4 and box[3]-box[2] == 4:
                out.append(box)
    return sorted(out, key=lambda z:z[2])


def _eight_button_index(x, y):
    for i, (y0,y1,x0,x1) in enumerate(_eight_buttons()):
        if x0 <= x < x1 and y0 <= y < y1:
            return i
    return None


def _eight_slider_base():
    """Infer the black/yellow floor hidden under level4's irregular 8 piece."""
    eg = _entry()
    cut = _right_start()
    I = np.indices(eg.shape)
    m8 = (eg == 8) & (I[1] < cut)
    if not np.any(m8) or np.any((eg == 13) & (I[1] < cut)):
        return eg
    yy, xx = np.where(m8)
    oy0, ox0 = int(yy.min()), int(xx.min())
    b = eg.copy()
    b[m8] = 4
    # The visible zero corridors and the 8 overlay form three rectilinear
    # bands.  Complete those bands underneath the entry sprite.
    near0 = ((eg == 0) & (I[1] < cut) & (I[0] < oy0+6)
             & (I[1] <= int(xx.max())+12))
    zy, zx = np.where(near0)
    if len(zx):
        zx1 = int(zx.max()) + 1
        b[oy0-10:oy0-6, ox0+1:zx1] = 0
        b[oy0-6:oy0+2, ox0+1:ox0+5] = 0
        b[oy0+2:oy0+6, ox0+1:zx1-1] = 0
    return b


def _move_eight_slider(a, dx, dy, under):
    """Translate the irregular left 8 piece four pixels inside its maze."""
    eg = _entry(); cut = _right_start(); I = np.indices(a.shape)
    entry_mask = (eg == 8) & (I[1] < cut)
    if not np.any(entry_mask) or np.any((eg == 13) & (I[1] < cut)):
        return under
    old = (a == 8) & (I[1] < cut)
    oy, ox = np.where(old)
    if not len(ox):
        return under
    base = _eight_slider_base()
    ey, ex = np.where(entry_mask)
    ny, nx = oy + dy, ox + dx
    # The irregular 8 is a carriage riding the black (color-0) U-shaped
    # rail, not a free collision sprite.  Infer its solid central 3x4 axle;
    # this stays invariant when the separate 8 actuator compresses the outer
    # silhouette.  A move is legal exactly when that axle remains on black.
    core = None
    for cy in range(int(oy.min()), int(oy.max())-2):
        for cx in range(int(ox.min()), int(ox.max())-1):
            if np.all(old[cy:cy+4, cx:cx+3]):
                core = (cy, cx)
                break
        if core is not None:
            break
    if core is None:
        return under

    # Closing at the top-right station couples the tall c-shaped load rigidly
    # to the carriage.  Its entry pose is anchored to the endpoint axle; from
    # then on both masks translate together around the U.  Reconstruct the
    # static floor beneath the load so crossed black/f/yellow cells reappear.
    entry_height = int(ey.max()-ey.min()+1)
    locked = int(oy.max()-oy.min()+1) < entry_height
    floor = base.copy()
    old_cy = old_cx = np.array([], dtype=int)
    if locked:
        cargo_entry = (eg == 12) & (I[1] < cut)
        floor[cargo_entry] = 4
        # The top U-rail continues beneath four cells at the load's left
        # edge.  They are hidden by c in ENTRY_GRID and are exposed only
        # after the coupled carriage has towed the load left twice.
        floor[int(ey.min())-10:int(ey.min())-6, int(ex.max())+11] = 0
        cey, cex = np.where(cargo_entry)
        anchor_core_y = int(ey.min()) - 10
        anchor_core_x = int(ex.min()) + 13
        off_y, off_x = core[0]-anchor_core_y, core[1]-anchor_core_x
        old_cy, old_cx = cey+off_y, cex+off_x

    ncy, ncx = core[0]+dy, core[1]+dx
    if (ncy < 0 or ncx < 0 or ncy+4 > a.shape[0] or ncx+3 > a.shape[1]
            or not np.all(floor[ncy:ncy+4, ncx:ncx+3] == 0)):
        return under
    for yy, xx in zip(oy, ox):
        a[int(yy), int(xx)] = floor[int(yy), int(xx)]
    for yy, xx in zip(old_cy, old_cx):
        a[int(yy), int(xx)] = floor[int(yy), int(xx)]
    if locked:
        for yy, xx in zip(old_cy+dy, old_cx+dx):
            a[int(yy), int(xx)] = 12
    for yy, xx in zip(ny, nx):
        a[int(yy), int(xx)] = 8
    return under


def _contract_eight_carriage(a):
    """Close the outer 8 silhouette by one pixel at its c-side endpoint."""
    eg = _entry(); cut = _right_start(); I = np.indices(a.shape)
    entry_mask = (eg == 8) & (I[1] < cut)
    if not np.any(entry_mask) or np.any((eg == 13) & (I[1] < cut)):
        return False
    old = (a == 8) & (I[1] < cut)
    oy, ox = np.where(old)
    if not len(ox):
        return False
    base = _eight_slider_base()
    # The actuator engages only where the carriage touches the tall c lock.
    adjacent_c = False
    for yy, xx in zip(oy, ox):
        for ddy, ddx in ((1,0),(-1,0),(0,1),(0,-1)):
            qy, qx = int(yy+ddy), int(xx+ddx)
            if (0 <= qy < a.shape[0] and 0 <= qx < cut
                    and int(eg[qy, qx]) == 12):
                adjacent_c = True
                break
        if adjacent_c:
            break
    y0, y1 = int(oy.min()), int(oy.max())
    ey = np.where(entry_mask)[0]
    entry_height = int(ey.max()-ey.min()+1)
    # The c lock accepts exactly one closure; the already-compressed six-row
    # key is terminal, so later actuator presses are ordinary no-ops.
    if not adjacent_c or y1-y0+1 != entry_height:
        return False
    new = set()
    for yy, xx in zip(oy, ox):
        yy, xx = int(yy), int(xx)
        if yy <= y0+1:
            yy += 1
        elif yy >= y1-1:
            yy -= 1
        new.add((yy, xx))
    for yy, xx in zip(oy, ox):
        a[int(yy), int(xx)] = base[int(yy), int(xx)]
    for yy, xx in new:
        a[yy, xx] = 8
    return new != set((int(yy), int(xx)) for yy, xx in zip(oy, ox))


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
        if np.array_equal(a, np.array(ENTRY_GRID, dtype=int)):
            # Level4 uses eight-tick cells with a latent -1 offset.  The
            # entry is blank; after the first action at least one cell is shown,
            # and later thresholds follow weighted costs 10,18,26...
            old_ticks = -1 if (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 4) else 0
        else:
            old_ticks = 1
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
        mover_button = _eight_button_index(x, y) if x >= _right_start() else None
        if mover_button is not None:
            # Four ordinary-cost directional inputs, ordered left/up/right/down,
            # translate the irregular 8 sprite by one four-pixel maze tile.
            dirs = {0:(-4,0), 1:(0,-4), 2:(4,0), 3:(0,4)}
            if mover_button in dirs:
                # The universal occupied-platform interlock also applies to
                # the closed carriage's coupled c load: a directional input
                # is blocked while e stands on either moving body.
                if np.all(under == 8) or np.all(under == 12):
                    blocked_control = True
                else:
                    dx8, dy8 = dirs[mover_button]
                    under = _move_eight_slider(a, dx8, dy8, under)
        elif (x >= _right_start() and clicked == 8
              and np.any(_entry()[:, :_right_start()] == 8)
              and not np.any(_entry()[:, :_right_start()] == 13)):
            # Level4's separate 8 T closes the carriage only when it is
            # docked against the tall c-side endpoint.
            if _contract_eight_carriage(a):
                # Like the four direction keys, this shape key costs one
                # ordinary tick rather than the two-tick map-control cost.
                _clear_guides(a)
        elif (x >= _right_start() and clicked in (2, 6, 8, 9, 11, 15)
              and not (clicked == 8 and not np.any(_entry()[:, :_right_start()] == 13))):
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
    quantum = (8 if int(CURRENT_LEVEL) >= 4 else min(int(CURRENT_LEVEL) + 2, 3)) if CURRENT_LEVEL is not None else 2
    cost = 20 if blocked_control else (2 if valid_control else 1)
    new_ticks = old_ticks + cost
    wanted = (new_ticks + quantum - 1) // quantum
    if CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 4:
        wanted = max(1, wanted)
    while int(np.sum(a[-1] == 3)) < wanted:
        z = np.where(a[-1] == 0)[0]
        if not len(z):
            break
        a[-1, int(z[0])] = 3

    info = {"level_up": reached_goal, "dead": False, "win": False}
    return a.tolist(), info, {"ticks": new_ticks, "under": under.tolist(), "red_phase": red_phase}

def is_goal(state, grid):
    return False
