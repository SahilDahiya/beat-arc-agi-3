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


def _entry_component_size(y, x, color):
    eg = _entry()
    if not (0 <= y < eg.shape[0] and 0 <= x < eg.shape[1]
            and int(eg[y, x]) == int(color)):
        return 0
    seen, stack = {(int(y), int(x))}, [(int(y), int(x))]
    while stack:
        yy, xx = stack.pop()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            q = (yy+dy, xx+dx)
            if (0 <= q[0] < eg.shape[0] and 0 <= q[1] < eg.shape[1]
                    and int(eg[q]) == int(color) and q not in seen):
                seen.add(q); stack.append(q)
    return len(seen)


def _player_bbox(a):
    """Locate the movable 2x2 e sprite, ignoring right-panel e glyphs/arms."""
    cut = _right_start()
    for y in range(a.shape[0]-1):
        for x in range(min(a.shape[1]-1, max(0, cut-1))):
            if np.all(a[y:y+2, x:x+2] == 14):
                return (y, x)
    return None


def init_state(entry_grid):
    # The first-ever action has no before-frame during replay, so ticks starts
    # unknown and is recovered from whether the observed grid is still ENTRY_GRID.
    return {"ticks": None, "under": [[2, 2], [2, 2]], "red_phase": 0,
            "b_phase": 0}

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

def _rotate_sparse_c_load(a):
    """Rotate the large c load in the final level's square docking arena."""
    eg = _entry()
    cut = _right_start()
    left_c = (eg[:, :cut] == 12)
    counts = np.sum(left_c, axis=1)
    if not len(counts) or int(counts.max()) < 12:
        return
    heavy = np.where(counts == counts.max())[0]
    if not len(heavy):
        return
    row = int(heavy[0])
    xs = np.where(left_c[row])[0]
    if not len(xs):
        return
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    size = x1 - x0
    if size < 12 or size % 2 or not np.any(eg[:, :cut] == 8):
        return
    broad = np.where(left_c[:, x0] & left_c[:, x1-1])[0]
    if not len(broad):
        return
    center_y = (int(broad.min()) + int(broad.max()) + 1) // 2
    y0, y1 = center_y - size // 2, center_y + size // 2
    if y0 < 0 or y1 > a.shape[0]:
        return

    floor = eg[y0:y1, x0:x1].copy()
    floor[floor == 12] = 4
    # The right lobe docks in a black horizontal rail hidden beneath c.
    rowmask = left_c[row, x0:x1]
    runs, start = [], None
    for i, on in enumerate(list(rowmask) + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append((start, i)); start = None
    if runs:
        rx0 = runs[-1][0]
        hy0, hy1 = int(broad.min())-y0, int(broad.max())+1-y0
        floor[hy0:hy1, rx0:] = 0

    sub = a[y0:y1, x0:x1]
    old = (sub == 12)
    new = np.rot90(old, 1)
    sub[old] = floor[old]
    sub[new] = 12


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
        # The final level couples this pulse to every grounded two-color 2x2
        # checker gear (b/c and 9/a included) and to a large rotating c load.
        extended = int(np.max(np.sum(eg[:, :cut] == 12, axis=1))) >= 12
        if extended:
            for yy in range(eg.shape[0]-1):
                for xx in range(max(0, cut-1)):
                    z = eg[yy:yy+2, xx:xx+2]
                    vals = np.unique(z)
                    if (len(vals) == 2 and z[0,0] == z[1,1]
                            and z[0,1] == z[1,0] and z[0,0] != z[0,1]):
                        p, q = int(z[0,0]), int(z[0,1])
                        arr = a[yy:yy+2, xx:xx+2].copy()
                        a[yy:yy+2, xx:xx+2] = np.where(
                            arr == p, q, np.where(arr == q, p, arr))
            _rotate_sparse_c_load(a)
        else:
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
        # In the final layout the mixed 2/8 floor switch reveals the intrinsic
        # horizontal color-8 actuator used on the preceding board: a 9x3 solid
        # bar.  Its open panel slot is grounded immediately above the existing
        # color-6 control, sharing that control's right edge.
        if (target == 8
                and int(np.max(np.sum(left == 12, axis=1))) >= 12):
            ty, tx = np.where(eg[:, cut:] == 6)
            if len(ty):
                center = (int(tx.min()) + int(tx.max())) // 2 + cut
                top = int(ty.min()) - 6
                a[top:top+3, center-4:center+5] = target
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


def _entry_composite_switch():
    """Ground the final board's four-colour, six-cell floor command.

    Its four markings form one tiny connected component inside a red pad.  The
    two red corner cells complete a 2x4 command strip; walking onto either
    2x2 half consumes the whole strip.
    """
    if CURRENT_LEVEL is None or int(CURRENT_LEVEL) < 5:
        return None
    eg = _entry()
    cut = _right_start()
    mask = ((eg[:, :cut] >= 6) & (eg[:, :cut] <= 15)
            & (eg[:, :cut] != 14))
    pts = set((int(y), int(x)) for y, x in zip(*np.where(mask)))
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
        colors = sorted(set(int(eg[p]) for p in comp))
        if (len(comp) == 6 and len(colors) == 4
                and y1-y0 == 2 and x1-x0 == 4
                and np.all(np.isin(eg[y0:y1, x0:x1],
                                   (2, 6, 7, 8, 9, 10, 11, 12, 13, 15)))):
            # Semantic order is left, up, right, down around the strip:
            # bottom-left, top-left, top-right, bottom-right.
            means = {}
            for c in colors:
                cy, cx = np.where(eg[y0:y1, x0:x1] == c)
                means[c] = (float(cy.mean()), float(cx.mean()))
            top = sorted(colors, key=lambda c: (means[c][0], means[c][1]))[:2]
            bottom = sorted(colors, key=lambda c: (-means[c][0], means[c][1]))[:2]
            top = sorted(top, key=lambda c: means[c][1])
            bottom = sorted(bottom, key=lambda c: means[c][1])
            return (y0, y1, x0, x1,
                    (bottom[0], top[0], top[1], bottom[1]))
    return None


def _composite_control_box():
    """Entry-grounded open slot used by the four-colour selector panel."""
    command = _entry_composite_switch()
    if command is None:
        return None
    eg = _entry()
    cut = _right_start()
    colored_y = np.where(np.any(~np.isin(eg[:, cut:], (0, 3, 4, 5)), axis=1))[0]
    if not len(colored_y):
        return None
    ty, tx = int(colored_y.max()) + 4, cut + 7
    return (ty, ty+4, tx, tx+4)


def _activate_composite_switch(a, command):
    """Flatten the command strip and materialise its four 2x2 selector keys."""
    y0, y1, x0, x1, colors = command
    a[y0:y1, x0:x1] = 2
    box = _composite_control_box()
    if box is None:
        return
    ty, ty1, tx, tx1 = box
    if ty < 0 or tx < 0 or ty1 > a.shape[0] or tx1 > a.shape[1]:
        return
    left, up, right, down = colors
    a[ty:ty+2, tx:tx+2] = left
    a[ty:ty+2, tx+2:tx+4] = up
    a[ty+2:ty+4, tx:tx+2] = right
    a[ty+2:ty+4, tx+2:tx+4] = down


def _composite_key_at(a, x, y):
    """Return the selected representative colour for a revealed quadrant."""
    box = _composite_control_box()
    command = _entry_composite_switch()
    if box is None or command is None:
        return None
    y0, y1, x0, x1 = box
    if not (x0 <= x < x1 and y0 <= y < y1):
        return None
    colors = command[4]
    index = (0 if y < y0+2 and x < x0+2 else
             1 if y < y0+2 else
             2 if x < x0+2 else 3)
    key = int(colors[index])
    return key if int(a[y, x]) == key else None


def _selector_partner(key):
    """Find the other colour of the isolated checker family selected by key."""
    # Color8's intrinsic partner is the d pivot used by every 8 hinge.  Its
    # checker is intentionally absent from ENTRY_GRID and is made on demand.
    if int(key) == 8:
        return 13
    eg = _entry()
    cut = _right_start()
    for yy in range(eg.shape[0]-1):
        for xx in range(max(0, cut-1)):
            z = eg[yy:yy+2, xx:xx+2]
            vals = np.unique(z)
            if (len(vals) == 2 and int(key) in vals
                    and z[0,0] == z[1,1] and z[0,1] == z[1,0]
                    and z[0,0] != z[0,1]):
                return int(vals[0] if int(vals[1]) == int(key) else vals[1])
    return None


def _set_selector_checker(a, key, under):
    """Recolour the left sparse 6/7 hub to the chosen checker family."""
    sites = _mixed67_sites()
    if not sites:
        # After its first recolouring, recover the hub from ENTRY_GRID.
        eg = _entry()
        sites = []
        for yy in range(eg.shape[0]-1):
            for xx in range(max(0, _right_start()-1)):
                z = eg[yy:yy+2, xx:xx+2]
                if (np.all((z == 6) | (z == 7))
                        and np.any(z == 6) and np.any(z == 7)):
                    sites.append((yy, xx))
    if not sites:
        return under
    sy, sx = min(sites, key=lambda p: p[1])
    partner = _selector_partner(key)
    if partner is None:
        return under
    pattern = np.array([[partner, key], [key, partner]], dtype=int)
    player = _player_bbox(a)
    if player == (sy, sx):
        under = pattern
    else:
        a[sy:sy+2, sx:sx+2] = pattern
    return under


def _micro_map_center():
    """Top-left of the final 9/a checker surrounded by four labelled tiles."""
    if CURRENT_LEVEL is None or int(CURRENT_LEVEL) < 5:
        return None
    eg = _entry()
    cut = _right_start()
    for yy in range(eg.shape[0]-1):
        for xx in range(max(0, cut-1)):
            z = eg[yy:yy+2, xx:xx+2]
            if (set(int(v) for v in np.unique(z)) == {9, 10}
                    and z[0,0] == z[1,1] and z[0,1] == z[1,0]):
                return (yy, xx)
    return None


def _micro_map_label_at(y, x):
    """Label of one of the four unusual [1,0;0,label] map tiles."""
    center = _micro_map_center()
    if center is None:
        return None
    cy, cx = center
    if (y-cy, x-cx) not in ((-2,0), (2,0), (0,-2), (0,2)):
        return None
    z = _entry()[y:y+2, x:x+2]
    vals = [int(v) for v in z.ravel() if int(v) not in (0, 1)]
    return vals[0] if len(vals) == 1 else None


def _activate_dpad_label(a, label):
    """Solidify the 4x4 right-panel arm containing a singleton map label."""
    eg = _entry()
    cut = _right_start()
    for yy in range(eg.shape[0]-3):
        for xx in range(cut, eg.shape[1]-3):
            z = eg[yy:yy+4, xx:xx+4]
            if (int(np.sum(z == label)) == 1
                    and np.all((z == 4) | (z == label))):
                a[yy:yy+4, xx:xx+4] = int(label)
                return


def _deactivate_dpad_label(a, label):
    """Restore a mini-map arm to its entry guide when e leaves that tile."""
    eg = _entry()
    cut = _right_start()
    for yy in range(eg.shape[0]-3):
        for xx in range(cut, eg.shape[1]-3):
            z = eg[yy:yy+4, xx:xx+4]
            if (int(np.sum(z == label)) == 1
                    and np.all((z == 4) | (z == label))):
                a[yy:yy+4, xx:xx+4] = z
                return


def _solid_dpad_arm(a, x, y, label):
    """Whether a click lies in the mini-map-activated solid 4x4 arm."""
    eg = _entry()
    cut = _right_start()
    for yy in range(eg.shape[0]-3):
        for xx in range(cut, eg.shape[1]-3):
            z = eg[yy:yy+4, xx:xx+4]
            if (int(np.sum(z == label)) == 1
                    and np.all((z == 4) | (z == label))
                    and xx <= x < xx+4 and yy <= y < yy+4):
                return bool(np.all(a[yy:yy+4, xx:xx+4] == label))
    return False


def _final_ring_box(a):
    """Locate the final board's hollow 8x8 color-8 maze ring."""
    cut = _right_start()
    for yy in range(a.shape[0]-7):
        for xx in range(max(0, cut-7)):
            z = a[yy:yy+8, xx:xx+8]
            border = np.zeros((8, 8), dtype=bool)
            border[0,:] = border[-1,:] = True
            border[:,0] = border[:,-1] = True
            if np.all(z[border] == 8) and int(np.sum(z == 8)) == 28:
                return (yy, xx)
    return None


def _move_final_ring(a, label):
    """Move the hollow ring one 4-cell maze step in the labelled direction."""
    box = _final_ring_box(a)
    entry_box = _final_ring_box(_entry())
    dirs = {12:(-4,0), 15:(0,-4), 14:(4,0), 10:(0,4)}
    if box is None or entry_box is None or int(label) not in dirs:
        return False
    y0, x0 = box
    dx, dy = dirs[int(label)]
    ny, nx = y0+dy, x0+dx
    if ny < 0 or nx < 0 or ny+8 > a.shape[0] or nx+8 > _right_start():
        return False

    # The ring straddles the maze; its central 4x4 aperture is the axle that
    # must remain over the black corridor.  ENTRY_GRID supplies the static
    # floor, including the black cells hidden by the ring at its start.
    base = _entry().copy()
    ey, ex = entry_box
    border = np.zeros((8, 8), dtype=bool)
    border[0,:] = border[-1,:] = True
    border[:,0] = border[:,-1] = True
    old_view = base[ey:ey+8, ex:ex+8]
    old_view[border] = 0
    if not np.all(base[ny+2:ny+6, nx+2:nx+6] == 0):
        return False

    cur = a[y0:y0+8, x0:x0+8]
    cur[border] = base[y0:y0+8, x0:x0+8][border]
    nxt = a[ny:ny+8, nx:nx+8]
    nxt[border] = 8
    return True


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
    player = _player_bbox(a)
    ey, ex = player if player is not None else (-99, -99)
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


def _final_bar_jobs():
    """Bottom slider bars, including platforms entering in their locked c phase."""
    eg = _entry(); cut = _right_start()
    raw = []
    # The final board's miniature staircase occupies the last ten play rows.
    for color in (1, 12):
        runs = []
        for yy in range(max(0, eg.shape[0]-10), eg.shape[0]-1):
            row = (eg[yy, :cut] == color)
            xx = 0
            while xx < cut:
                if not row[xx]:
                    xx += 1; continue
                x0 = xx
                while xx < cut and row[xx]:
                    xx += 1
                if xx-x0 >= 4:
                    runs.append((yy, x0, xx))
        used = set()
        for i, (yy, x0, x1) in enumerate(runs):
            if i in used: continue
            y1 = yy + 1
            for j, (zy, z0, z1) in enumerate(runs):
                if j not in used and zy == y1 and z0 == x0 and z1 == x1:
                    used.add(j); y1 += 1
            raw.append((yy, y1, x0, x1-x0, color))
    if not raw:
        return []
    # All rows are the same six-position conveyor.  Their staggered entry
    # x-coordinates encode staggered phases; an entry-c row is phase5/locked.
    origin = min(x0 if color == 1 else x0-10
                 for _, _, x0, _, color in raw)
    jobs = []
    for y0, y1, x0, width, color in raw:
        base_phase = ((x0-origin)//2) % 6 if color == 1 else 5
        jobs.append((y0, y1, origin, width, base_phase))
    return jobs


def _shift_one_bars(a, under, phase=None):
    """Shift entry-grounded horizontal color-1 platforms one tile right.

    The right-side b-shaped operator translates the bars without carrying e.
    On the final board several independently phased bars overlap into a stair:
    an entry-c bar is simply a slider already at its locked phase.
    """
    eg = _entry()
    cut = _right_start()

    jobs = _final_bar_jobs()
    if phase is not None and len(jobs) >= 4:
        player = _player_bbox(a)
        riding = bool(player is not None and np.all((under == 1) | (under == 12))
                      and any(y0 <= player[0] and player[0]+1 < y1
                              for y0, y1, _, _, _ in jobs))
        if riding:
            py, px = player
            a[py:py+2, px:px+2] = under
        # Erase every position any phase of each grounded platform can occupy,
        # then paint all jobs together so overlaps naturally form one bridge.
        for y0, y1, origin, width, _ in jobs:
            a[y0:y1, origin:origin+width+10] = 4
        for y0, y1, origin, width, base_phase in jobs:
            p = (base_phase + int(phase)) % 6
            xx = origin + 2*p if p < 5 else origin + 10
            a[y0:y1, xx:xx+width] = 12 if p == 5 else 1
        if riding:
            under = a[py:py+2, px:px+2].copy()
            a[py:py+2, px:px+2] = 14
        return under
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

    player = _player_bbox(a)
    player_y, player_x = player if player is not None else (-99, -99)
    for y0, y1, entry_x0, width in bands:
        ride1 = bool(player is not None and np.all(under == 1)
                     and y0 <= player_y and player_y+1 < y1)
        ride12 = bool(player is not None and np.all(under == 12)
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
            # Late boards share a one-tick latent offset. Their meter cell
            # widths double: L4=8 and L5=16.
            old_ticks = (-1
                         if (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 4)
                         else 0)
        else:
            old_ticks = 1
    else:
        old_ticks = int(raw)
    under = np.array(st.get("under", [[2,2],[2,2]]), dtype=int)
    red_phase = int(st.get("red_phase", 0))
    b_phase = int(st.get("b_phase", 0))

    valid_control = False
    blocked_control = False
    # The final conveyor's driven-row stall costs 19 ticks; a full
    # unsupported-platform interlock costs 20.  The one-tick distinction is
    # resolved by the final board's exact sixteen-tick meter intervals.
    final_bar_stall = False
    free_control = False
    control_cost = 2

    if (action == 6 and x is not None and y is not None
            and 0 <= y < a.shape[0] and 0 <= x < a.shape[1]):
        clicked = int(a[y, x])
        mover_button = _eight_button_index(x, y) if x >= _right_start() else None
        composite_key = _composite_key_at(a, x, y)
        # The final board's four singleton labels form a directional keypad,
        # not checker-toggle controls.  Until a direction is geometrically
        # available, pressing one is an ordinary-cost no-op.
        final_dpad = (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 5
                      and x >= _right_start() and clicked in (10, 12, 14, 15)
                      and int(np.sum(_entry()[:, _right_start():] == clicked)) == 1)
        # The large red shape sharing the final board's top map is decorative,
        # not the rail-front operator used on earlier boards.
        final_red_map = (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 5
                         and x >= _right_start() and clicked == 2)
        final_map_marker = (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 5
                            and x >= _right_start() and clicked == 11
                            and _entry_component_size(y, x, 11) < 8)
        if composite_key is not None:
            # The four keys choose which checker family occupies the left
            # sparse hub.  They retain the common off-diagonal representative.
            valid_control = True
            under = _set_selector_checker(a, composite_key, under)
        elif final_dpad:
            # A singleton legend is inert.  Entering its corresponding physical
            # mini-map tile first solidifies the whole arm; only that armed 4x4
            # button drives the hollow ring through its black maze.
            if _solid_dpad_arm(a, x, y, clicked):
                valid_control = True
                _move_final_ring(a, clicked)
            elif _player_bbox(a) == _micro_map_center():
                # Once the physical mini-map is occupied, an unarmed legend
                # click is ignored completely; movement into its tile arms it.
                free_control = True
        elif final_red_map or final_map_marker:
            # These map glyphs have no compatible mechanism on the playfield,
            # but a hit still consumes the ordinary two-tick control cost.
            valid_control = True
        elif mover_button is not None:
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
            elif (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 5
                  and _final_ring_box(a) != _final_ring_box(_entry())):
                # Once the hollow ring has left its entry dock, an inapplicable
                # shape-key press is ignored completely (including the meter).
                free_control = True
        elif (x >= _right_start() and clicked in (2, 6, 8, 9, 11, 15)
              and not (clicked == 8 and not np.any(_entry()[:, :_right_start()] == 13))):
            # A moving platform cannot be actuated while the player occupies it.
            # Color-6 is the static pivot whose moving arms are color 7.  Red and
            # the b-shaped translator are operators rather than their floor color.
            moving_color = 7 if clicked == 6 else (-1 if clicked in (2, 11) else clicked)
            final_jobs = _final_bar_jobs() if (CURRENT_LEVEL is not None
                                                  and int(CURRENT_LEVEL) >= 5) else []
            final_player = _player_bbox(a)
            # A b-slider can move beneath a stationary rider only when its
            # NEXT combined layout still covers all four occupied cells.  This
            # explains both the allowed top-row lock and the blocked bottom /
            # middle attempts without naming individual conveyor rows.
            b_unsupported = False
            on_b_bar = (clicked == 11 and final_player is not None
                        and np.all((under == 1) | (under == 12)))
            if on_b_bar:
                probe = a.copy()
                next_phase = ((b_phase + 1) % 6) if final_jobs else None
                probe_under = _shift_one_bars(probe, under.copy(), next_phase)
                b_unsupported = not np.all((probe_under == 1) | (probe_under == 12))
            final_bottom_stall = (b_unsupported and final_jobs
                                  and final_player[0] == max(q[0] for q in final_jobs))
            if b_unsupported or np.all(under == moving_color):
                blocked_control = True
                final_bar_stall = bool(final_bottom_stall)
            else:
                valid_control = True
                if clicked == 2:
                    n = _red_cycle_steps()
                    red_phase = (red_phase + 1) % (2*n)
                    stage = min(red_phase, 2*n-red_phase)
                    under = _red_operator(a, stage, under)
                elif clicked == 6:
                    # Sparse checker gears form a transport network.  The final
                    # selector can recolour the left 6/7 hub to another family;
                    # a rider then travels to the other currently matching
                    # checker (b/c, a/9, or the ordinary 6/7 mate).
                    sparse = int(np.sum(_entry()[:, :_right_start()] == 6)) < 8
                    checker = (under.shape == (2, 2)
                               and under[0,0] == under[1,1]
                               and under[0,1] == under[1,0]
                               and under[0,0] != under[0,1])
                    ride = bool(sparse and checker)
                    source, others, advance_family = None, [], False
                    if ride:
                        source = _player_bbox(a)
                        if source is not None:
                            a[source[0]:source[0]+2, source[1]:source[1]+2] = under
                            pair = set(int(v) for v in np.unique(under))
                            cut = _right_start()
                            for yy in range(a.shape[0]-1):
                                for xx in range(max(0, cut-1)):
                                    z = a[yy:yy+2, xx:xx+2]
                                    if ((yy, xx) != source
                                            and set(int(v) for v in np.unique(z)) == pair
                                            and z[0,0] == z[1,1]
                                            and z[0,1] == z[1,0]
                                            and z[0,0] != z[0,1]):
                                        others.append((yy, xx))
                            # d/8 is the selector's deliberately mate-less
                            # family.  Its pulse advances to the next intrinsic
                            # checker family, 9/a, copying that station's old
                            # floor into the hub while transporting to it.
                            if not others and pair == {8, 13}:
                                for yy in range(a.shape[0]-1):
                                    for xx in range(max(0, cut-1)):
                                        z = a[yy:yy+2, xx:xx+2]
                                        if (set(int(v) for v in np.unique(z)) == {9, 10}
                                                and z[0,0] == z[1,1]
                                                and z[0,1] == z[1,0]
                                                and z[0,0] != z[0,1]):
                                            others.append((yy, xx))
                                            advance_family = True
                                            break
                                    if others:
                                        break
                    _toggle6(a)
                    if ride and source is not None:
                        ty, tx = (others[0] if others else source)
                        under = a[ty:ty+2, tx:tx+2].copy()
                        if advance_family and (ty, tx) != source:
                            a[source[0]:source[0]+2,
                              source[1]:source[1]+2] = under
                        a[ty:ty+2, tx:tx+2] = 14
                elif clicked == 8:
                    _toggle8(a)
                elif clicked == 9:
                    _toggle9(a)
                elif clicked == 11:
                    b_phase = (b_phase + 1) % 6
                    under = _shift_one_bars(a, under, b_phase)
                else:
                    _toggle_checker_color(a, clicked)
                _clear_guides(a)

    reached_goal = False
    if action in _DIRS:
        player = _player_bbox(a)
        if player is not None:
            y0, x0 = player
            x1, y1 = x0 + 1, y0 + 1
            dx, dy = _DIRS[action]
            nx0, nx1, ny0, ny1 = x0+dx, x1+dx, y0+dy, y1+dy
            if 0 <= nx0 and nx1 < a.shape[1] and 0 <= ny0 and ny1 < a.shape[0]:
                dest = a[ny0:ny1+1, nx0:nx1+1].copy()
                nonred = np.unique(dest[dest != 2]) if dest.shape == under.shape else np.array([])
                floor_target = int(nonred[0]) if len(nonred) == 1 else None
                floor_switch = (floor_target is not None and np.any(dest == 2)
                                and np.any(dest == floor_target)
                                and np.all((dest == 2) | (dest == floor_target)))
                command = _entry_composite_switch()
                composite_switch = False
                if command is not None:
                    cy0, cy1, cx0, cx1 = command[:4]
                    overlaps = not (nx1 < cx0 or nx0 >= cx1
                                    or ny1 < cy0 or ny0 >= cy1)
                    live = np.any(a[cy0:cy1, cx0:cx1] != 2)
                    composite_switch = bool(overlaps and live)
                old_micro_label = _micro_map_label_at(y0, x0)
                micro_label = _micro_map_label_at(ny0, nx0)
                micro_center_pos = _micro_map_center()
                micro_center = (micro_center_pos is not None
                                and (ny0, nx0) == micro_center_pos)
                mixed67 = (dest.shape == under.shape and np.any(dest == 6)
                           and np.any(dest == 7)
                           and np.all((dest == 6) | (dest == 7)))
                # Track colors are traversable cellwise, not only as uniform
                # 2x2 tiles.  Sparse 6/7 first exposed this rule; the final
                # c/8 hub is the same composite-track case.
                passable = (dest.shape == under.shape
                            and np.all(np.isin(dest, _TRACK)))
                if (passable or floor_switch or composite_switch
                        or micro_label is not None or micro_center or mixed67):
                    a[y0:y1+1, x0:x1+1] = under
                    if old_micro_label is not None:
                        _deactivate_dpad_label(a, old_micro_label)
                    reached_goal = bool(np.all(dest == 11))
                    if floor_switch:
                        _activate_floor_switch(a, floor_target, ny0, ny1, nx0, nx1)
                        under = np.full(dest.shape, 2, dtype=int)
                    elif composite_switch:
                        _activate_composite_switch(a, command)
                        under = np.full(dest.shape, 2, dtype=int)
                    elif micro_label is not None:
                        _activate_dpad_label(a, micro_label)
                        under = dest
                    else:
                        under = dest
                    a[ny0:ny1+1, nx0:nx1+1] = 14

    # The bottom meter groups min(level+2, 3) weighted ticks per cell
    # (observed L0=2 and L1/L2=3). Ordinary actions cost one tick,
    # transforming controls cost two, and occupied-platform failures 20.
    quantum = ((2 ** (int(CURRENT_LEVEL)-1))
                if int(CURRENT_LEVEL) >= 4
                else min(int(CURRENT_LEVEL) + 2, 3)) if CURRENT_LEVEL is not None else 2
    cost = (0 if free_control else
            (19 if final_bar_stall else
             (20 if blocked_control else (2 if valid_control else 1))))
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
    return a.tolist(), info, {"ticks": new_ticks, "under": under.tolist(),
                            "red_phase": red_phase, "b_phase": b_phase}

def is_goal(state, grid):
    return bool(False)
