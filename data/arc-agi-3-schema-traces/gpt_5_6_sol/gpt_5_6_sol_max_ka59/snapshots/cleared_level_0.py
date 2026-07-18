# ARC3 ka59 world model
# numpy (np), ENTRY_GRID, and CURRENT_LEVEL are preloaded.

DIRS = {1:(0,-3), 2:(0,3), 3:(-3,0), 4:(3,0)}

def _glyph_center(a, value):
    h,w = a.shape
    for yy in range(1,h-1):
        for xx in range(1,w-1):
            if int(a[yy,xx]) != value:
                continue
            q = a[yy-1:yy+2, xx-1:xx+2]
            if q.shape != (3,3):
                continue
            ok = True
            for j in range(3):
                for i in range(3):
                    if i == 1 and j == 1:
                        continue
                    if int(q[j,i]) != 14:
                        ok = False
            if ok:
                return (xx,yy)
    return None

def _player_center(a):
    p = _glyph_center(a, 0)
    if p is not None:
        return p
    # On contact the center remains 0 and the entire contacting face is 0.
    h,w = a.shape
    for yy in range(1,h-1):
        for xx in range(1,w-1):
            q = a[yy-1:yy+2, xx-1:xx+2]
            vals = set(int(v) for v in q.ravel())
            if vals <= {0,14} and 0 in vals and 14 in vals:
                return (xx,yy)
    return None

def _base():
    # Static terrain is ENTRY_GRID with its two initial glyphs removed.
    b = np.array(ENTRY_GRID, dtype=int).copy()
    for val in (0,5):
        c = _glyph_center(b, val)
        if c is not None:
            b[c[1]-1:c[1]+2, c[0]-1:c[0]+2] = 1
    return b

def _restore_tile(a, cx, cy):
    b = _base()
    a[cy-1:cy+2, cx-1:cx+2] = b[cy-1:cy+2, cx-1:cx+2]

def _draw_glyph(a, cx, cy, center):
    a[cy-1:cy+2, cx-1:cx+2] = 14
    a[cy,cx] = center

def _mark_progress(a, side=1):
    xs = np.where(a[-1] == 4)[0]
    if len(xs):
        a[-1,int(xs[-1] if side > 0 else xs[0])] = 0

def _mark_bar(a, action, nx=None, ny=None):
    # The bottom strip records alternating walking/animation phases.  With
    # stride 3, ordinary actions add a cell whenever the selected glyph ends
    # on the opposite x-lattice phase from the entry player's starting phase.
    p0 = _glyph_center(np.array(ENTRY_GRID, dtype=int), 0)
    if nx is not None and p0 is not None and (nx - p0[0]) % 6 == 3:
        _mark_progress(a, 1)

def _mirror_across_separator(a, x):
    # The central color-15 vertical strip is a mirror/transfer barrier.
    mask = (np.array(ENTRY_GRID, dtype=int) == 15)
    counts = np.sum(mask, axis=0)
    cols = np.where(counts >= 3)[0]
    if len(cols):
        # use the contiguous strip containing the densest columns
        return int(cols[0] + cols[-1] - x)
    return x

def _goal_centers():
    e = np.array(ENTRY_GRID, dtype=int)
    out = []
    h,w = e.shape
    for y in range(h-4):
        for x in range(w-4):
            q = e[y:y+5,x:x+5]
            if (np.all(q[0,:] == 4) and np.all(q[4,:] == 4) and
                np.all(q[:,0] == 4) and np.all(q[:,4] == 4) and
                np.all(q[1:4,1:4] == 1)):
                out.append((x+2,y+2))
    return out

def _goals_filled(a):
    cs = _goal_centers()
    if not cs:
        return False
    for cx,cy in cs:
        q = a[cy-1:cy+2,cx-1:cx+2]
        if q.shape != (3,3) or int(q[1,1]) not in (0,4):
            return False
        z = q.copy(); z[1,1] = 14
        if not np.all(z == 14):
            return False
    return True

def _set_finish(info):
    if CURRENT_LEVEL == 6:
        info["win"] = True
    else:
        info["level_up"] = True

def is_goal(grid):
    return _goals_filled(np.array(grid, dtype=int))

def step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    info = {"level_up":False, "dead":False, "win":False}

    # Clicking a rendered passive glyph selects it: its center becomes 0,
    # while the previously active glyph becomes a color-4 passive glyph.
    if action == 6:
        p = _player_center(a)
        chosen = None
        if x is not None and y is not None:
            for yy in range(max(1,y-1), min(a.shape[0]-1,y+2)):
                for xx in range(max(1,x-1), min(a.shape[1]-1,x+2)):
                    if int(a[yy,xx]) in (4,5):
                        q = a[yy-1:yy+2,xx-1:xx+2]
                        if q.shape == (3,3):
                            ring = q.copy()
                            ring[1,1] = 14
                            if np.all(ring == 14):
                                chosen = (xx,yy)
        if p is not None and chosen is not None and chosen != p:
            chosen_value = int(a[chosen[1],chosen[0]])
            a[p[1],p[0]] = 4
            a[chosen[1],chosen[0]] = 0
            # Selecting the initial color-5 token consumes/records it;
            # ordinary switching between color-4 parked tokens does not.
            if chosen_value == 5:
                _mark_progress(a, 1)
        if _goals_filled(a):
            _set_finish(info)
        return a.tolist(), info

    if action not in DIRS:
        return a.tolist(), info

    p = _player_center(a)
    t = _glyph_center(a, 5)
    if p is None:
        return a.tolist(), info
    dx,dy = DIRS[action]
    nx,ny = p[0]+dx,p[1]+dy

    # Driving into the 5-glyph transfers that glyph through the central
    # mirror.  The player stays on its side and its contact face closes.
    if t is not None and (nx,ny) == t:
        _restore_tile(a, t[0], t[1])
        _draw_glyph(a, p[0], p[1], 0)
        tx = _mirror_across_separator(a, t[0])
        _draw_glyph(a, tx, t[1], 5)
        _mark_progress(a, 1)
        return a.tolist(), info

    h,w = a.shape
    if nx-1 < 0 or ny-1 < 0 or nx+1 >= w or ny+1 >= h:
        return a.tolist(), info
    # Color-4 frames are traversable paint/goal outlines: the glyph
    # overwrites (and thereby erases) any color-4 pixels it crosses.
    destvals = a[ny-1:ny+2, nx-1:nx+2]
    if not np.all((destvals == 1) | (destvals == 4)):
        return a.tolist(), info

    _restore_tile(a, p[0], p[1])
    _draw_glyph(a, nx, ny, 0)

    # A move ending flush against a non-floor object displays a black
    # contacting face.  Such a contact setup is not yet a completed impulse.
    contact = False
    if dx > 0 and nx+2 < w and np.any((a[ny-1:ny+2, nx+2] != 1) & (a[ny-1:ny+2, nx+2] != 4)):
        a[ny-1:ny+2, nx+1] = 0; contact = True
    elif dx < 0 and nx-2 >= 0 and np.any((a[ny-1:ny+2, nx-2] != 1) & (a[ny-1:ny+2, nx-2] != 4)):
        a[ny-1:ny+2, nx-1] = 0; contact = True
    elif dy > 0 and ny+2 < h and np.any((a[ny+2, nx-1:nx+2] != 1) & (a[ny+2, nx-1:nx+2] != 4)):
        a[ny+1, nx-1:nx+2] = 0; contact = True
    elif dy < 0 and ny-2 >= 0 and np.any((a[ny-2, nx-1:nx+2] != 1) & (a[ny-2, nx-1:nx+2] != 4)):
        a[ny-1, nx-1:nx+2] = 0; contact = True
    if not contact:
        _mark_bar(a, action, nx, ny)
    if _goals_filled(a):
        _set_finish(info)
    return a.tolist(), info
