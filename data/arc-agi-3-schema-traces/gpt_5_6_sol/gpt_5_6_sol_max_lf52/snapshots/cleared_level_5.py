# World model for the peg-jumping board game.
# numpy is preloaded by the ARC3 sandbox as np.

def _lock_cells(e):
    """Logical cells occupied by the small 4x4 colour-f/7 lock sprites."""
    e = np.asarray(e)
    out = []
    h,w = e.shape
    for y in range(h-3):
        for x in range(w-3):
            b = e[y:y+4,x:x+4]
            if (np.all(b[0] == 15) and np.all(b[3] == 15) and
                np.all(b[:,0] == 15) and np.all(b[:,3] == 15)):
                out.append((x,y+1))
    return out

def _tiles_from(e):
    """Return playable 4x4 tile top-lefts from a slider-free static view."""
    e = np.asarray(e)

    m = (e == 1) | (e == 8) | (e == 14)
    out = []
    h, w = e.shape
    for y in range(h - 3):
        for x in range(w - 3):
            if not np.all(m[y:y+4, x:x+4]):
                continue
            if x and m[y, x-1]:
                continue
            if y and m[y-1, x]:
                continue
            out.append((x, y))
    for p in _lock_cells(e):
        if p not in out:
            out.append(p)
    return out

def _tiles():
    return _tiles_from(np.asarray(ENTRY_GRID))

def _has_peg(g, p):
    x, y = p
    return bool(np.any(np.isin(g[y:y+4, x:x+4], [8,14])))

def _piece_block(colour, corner):
    b = np.full((4,4), int(colour), dtype=int)
    b[0,0] = b[0,3] = b[3,0] = b[3,3] = int(corner)
    return b

def _piece_colour(g, p):
    box = _slider_for_cell(g, p)
    if box is not None:
        bx,by = box
        b = g[by:by+6,bx:bx+6]
    else:
        x,y = p
        b = g[y:y+4,x:x+4]
    if np.any(b == 8):
        return 8
    if np.any(b == 14):
        return 14
    return None

def _selected(g, tiles):
    # A selected peg has a colour-3 ring around its 4x4 tile.
    h, w = g.shape
    for x, y in tiles:
        ya, yb = max(0, y-1), min(h, y+5)
        xa, xb = max(0, x-1), min(w, x+5)
        if np.any(g[ya:yb, xa:xb] == 3):
            return (x, y)
    # The loaded slider is itself a selectable logical cell.
    for bx, by in _slider_bboxes(g):
        if np.any(g[by:by+6, bx:bx+6] == 3):
            return (bx+1, by+1)
    return None

def _clear_guides(g, tiles):
    # Restore guide pixels while retaining the current set of pegs.
    for x, y in tiles:
        block = g[y:y+4, x:x+4]
        block[(block == 2) | (block == 3)] = 1
        # The 1-pixel selection ring is in the black lattice gap.
        if y > 0:
            g[y-1, x:x+4][g[y-1, x:x+4] == 3] = 0
        if y+4 < g.shape[0]:
            g[y+4, x:x+4][g[y+4, x:x+4] == 3] = 0
        if x > 0:
            g[y:y+4, x-1][g[y:y+4, x-1] == 3] = 0
        if x+4 < g.shape[1]:
            g[y:y+4, x+4][g[y:y+4, x+4] == 3] = 0
        # Four outer corners of the 6x6 ring.
        for xx, yy in ((x-1,y-1),(x+4,y-1),(x-1,y+4),(x+4,y+4)):
            if 0 <= yy < g.shape[0] and 0 <= xx < g.shape[1] and g[yy,xx] == 3:
                g[yy,xx] = 0
    # A destination guide on the slider is drawn in its inner c-coloured 4x4.
    for bx, by in _slider_bboxes(g):
        face = g[by:by+6, bx:bx+6]
        pc = 8 if np.any(face == 8) else (14 if np.any(face == 14) else None)
        # Rebuild the face to erase either a destination-2 motif or a
        # source-selection 3 surround.
        face[:] = np.array([[11,11,11,11,11,11],
                            [11,12,12,12,12,11],
                            [11,12,12,12,12,11],
                            [11,12,12,12,12,11],
                            [11,12,12,12,12,11],
                            [11,11,11,11,11,11]])
        if pc is not None:
            face[1:5,1:5] = _piece_block(pc, 12)

def _slider_cell(g):
    # Backward-compatible convenience for one-slider levels.
    cells = _slider_cells(g)
    return cells[0] if cells else None

def _cell_has_peg(g, p, regular_set):
    if p in set(_lock_slider_cells(g)):
        return True
    box = _slider_for_cell(g, p)
    if box is not None:
        bx, by = box
        return bool(np.any(np.isin(g[by:by+6, bx:bx+6], [8,14])))
    return p in regular_set and (_has_peg(g, p) or p in set(_lock_cells(g)))

def _moves(g, src, tile_set):
    cells = set(tile_set)
    cells.update(_slider_cells(g))
    cells.update(_lock_slider_cells(g))
    x, y = src
    ans = []
    for dx, dy in ((0,-6),(0,6),(-6,0),(6,0)):
        mid = (x+dx, y+dy)
        dst = (x+2*dx, y+2*dy)
        if (mid in cells and dst in cells and
            _cell_has_peg(g, mid, tile_set) and
            not _cell_has_peg(g, dst, tile_set)):
            ans.append((dst, mid))
    return ans

def _clicked_tile(x, y, tiles):
    if x is None or y is None:
        return None
    for p in tiles:
        tx, ty = p
        if tx <= x < tx+4 and ty <= y < ty+4:
            return p
    return None

def _tick(g):
    # Row zero is a layered action counter.  It fills left-to-right at the
    # current minimum colour, then begins the next colour layer rather than
    # imposing a 64-action limit.
    m = int(np.min(g[0]))
    z = np.where(g[0] == m)[0]
    if len(z) and m < 15:
        g[0, int(z[0])] = m + 1

def _peg_count(g, tiles):
    return sum(_has_peg(g, p) for p in tiles)

def _solved(g, tiles):
    # Peg phase is complete when each disconnected rectangular lattice has
    # been reduced to one peg.
    unseen = set(tiles)
    while unseen:
        seed = unseen.pop()
        comp = {seed}
        todo = [seed]
        while todo:
            px, py = todo.pop()
            for q in ((px+6,py),(px-6,py),(px,py+6),(px,py-6)):
                if q in unseen:
                    unseen.remove(q)
                    comp.add(q)
                    todo.append(q)
        if sum(_has_peg(g, p) for p in comp) != 1:
            return False
    return bool(tiles)

def _has_lock():
    e = np.asarray(ENTRY_GRID)
    return bool(np.any(e == 11) and np.any(e == 12))

def _slider_bboxes(g):
    # A slider face is always 6x6 and retains b-coloured (11) corners,
    # whether empty, carrying a peg, marked as a destination, or selected.
    out = []
    h, w = g.shape
    allowed = np.array([2,3,8,11,12,14])
    for by in range(h-5):
        for bx in range(w-5):
            if not (g[by,bx] == 11 and g[by,bx+5] == 11 and
                    g[by+5,bx] == 11 and g[by+5,bx+5] == 11):
                continue
            face = g[by:by+6, bx:bx+6]
            if (np.all(np.isin(face, allowed)) and
                    not np.any(face[1:5,1:5] == 11)):
                out.append((bx,by))
    return out

def _lock_slider_bboxes(g):
    """Movable b-framed f/7 lock faces (permanent jump supports)."""
    e = np.asarray(g)
    out = []
    h,w = e.shape
    allowed = np.array([0,5,7,11,15])
    for by in range(h-5):
        for bx in range(w-5):
            b = e[by:by+6,bx:bx+6]
            if (np.all(b[:,0] == 11) and np.all(b[:,5] == 11)
                    and np.all(b[5] == 11) and np.any(b == 15)
                    and np.all(np.isin(b,allowed))):
                out.append((bx,by))
    return out

def _lock_slider_cells(g):
    return [(bx+1,by+1) for bx,by in _lock_slider_bboxes(g)]

def _slider_bbox(g):
    boxes = _slider_bboxes(g)
    return boxes[0] if boxes else None

def _slider_cells(g):
    return [(bx+1,by+1) for bx,by in _slider_bboxes(g)]

def _slider_for_cell(g, p):
    for bx, by in _slider_bboxes(g):
        if p == (bx+1,by+1):
            return (bx,by)
    return None

def _rail_dirs(g, bx, by):
    h, w = g.shape
    ans = set()
    if 0 <= bx-2 < w and np.any(g[by+2:by+4, bx-2] == 5):
        ans.add("L")
    if 0 <= bx+8 < w and np.any(g[by+2:by+4, bx+8] == 5):
        ans.add("R")
    if 0 <= by-2 < h and np.any(g[by-2, max(0,bx+2):min(w,bx+4)] == 5):
        ans.add("U")
    if 0 <= by+8 < h and np.any(g[by+8, max(0,bx+2):min(w,bx+4)] == 5):
        ans.add("D")
    return ans

def _erase_slider(g, bx, by, dirs, underlay=None, tiles=None):
    # At a board dock the slider temporarily covered part of the board's
    # fixed rim.  Restore that rim from ENTRY_GRID, but keep every live tile
    # block (whose peg contents may differ from entry).
    dock_l = (bx-2 >= 0 and
              np.any(np.isin(g[by-1:by+8, bx-2], [1,2,8,14])))
    dock_r = (bx+7 < g.shape[1] and
              np.any(np.isin(g[by-1:by+8, bx+7], [1,2,8,14])))
    if dock_l or dock_r:
        old = g.copy()
        substrate = np.asarray(ENTRY_GRID) if underlay is None else np.asarray(underlay)
        g[by-1:by+8, bx-1:bx+8] = substrate[by-1:by+8, bx-1:bx+8]
        use_tiles = _tiles() if tiles is None else tiles
        for tx, ty in use_tiles:
            if tx < bx+8 and tx+4 > bx-1 and ty < by+8 and ty+4 > by-1:
                g[ty:ty+4, tx:tx+4] = old[ty:ty+4, tx:tx+4]
        return

    # Else clear its face, one-pixel outline and lower/right shadow, then
    # reveal the two-pixel-wide rail that passed underneath it.
    g[by-1:by+8, bx-1:bx+8] = 10
    if "L" in dirs:
        g[by+2:by+4, bx-1:bx+4] = 5
    if "R" in dirs:
        g[by+2:by+4, bx+2:bx+8] = 5
    if "U" in dirs:
        g[by-1:by+4, bx+2:bx+4] = 5
    if "D" in dirs:
        g[by+2:by+8, bx+2:bx+4] = 5

def _draw_slider(g, bx, by, dirs, loaded=False):
    # When the face docks immediately beside a peg board, that board supplies
    # the side edge: do not paint our right outline/shadow over its first tile.
    dock_r = (bx+7 < g.shape[1] and
              np.any(np.isin(g[by-1:by+8, bx+7], [1,2,8,14])))
    dock_l = (bx-2 >= 0 and
              np.any(np.isin(g[by-1:by+8, bx-2], [1,2,8,14])))
    # At a rail/board junction the fixed substrate already supplies the
    # upper-right cap and the first shadow pixel.  Preserve those two cells.
    side_cap = (bx+7 < g.shape[1] and g[by,bx+7] == 5)
    keep_top_cap = int(g[by-1,bx+6]) if side_cap else None
    keep_side_cap = int(g[by,bx+7]) if side_cap else None
    top_face_is_gap = bool(np.all(g[by-1,bx:bx+6] == 0))
    keep_top_face = (g[by-1,bx:bx+6].copy()
                     if (dock_r or dock_l) and top_face_is_gap else None)
    keep_r = g[by-1:by+8, bx+6:bx+8].copy() if dock_r else None
    keep_r_corner = int(g[by+6, bx+6]) if dock_r else None
    keep_r_bottom = int(g[by+7, bx+5]) if dock_r else None
    keep_l = g[by-1:by+7, bx-1].copy() if dock_l else None
    keep_bl = int(g[by+7, bx]) if dock_l else None
    pat = np.array([[11,11,11,11,11,11],
                    [11,12,12,12,12,11],
                    [11,12,12,12,12,11],
                    [11,12,12,12,12,11],
                    [11,12,12,12,12,11],
                    [11,11,11,11,11,11]])
    g[by-1, bx-1:bx+7] = 5
    g[by:by+6, bx-1] = 5
    g[by:by+6, bx:bx+6] = pat
    if loaded:
        pc = int(loaded) if int(loaded) in (8,14) else 14
        g[by+1:by+5, bx+1:bx+5] = _piece_block(pc, 12)
    g[by:by+6, bx+6] = 5
    g[by:by+6, bx+7] = 9
    g[by+6, bx-1:bx+7] = 5
    g[by+6, bx+7] = 9
    g[by+7, bx:bx+8] = 9
    # A connected rail cuts through the would-be right/bottom shadow.
    if "R" in dirs:
        g[by+2:by+4, bx+7] = 5
    if "D" in dirs:
        g[by+7, bx+2:bx+4] = 5
    if dock_r:
        g[by-1:by+6, bx+6:bx+8] = keep_r[:7]
        g[by+6, bx+7] = keep_r[7,1]
        g[by+7, bx+6:bx+8] = keep_r[8]
        g[by+6, bx+6] = keep_r_corner
        # A rail crossing under the dock cuts through the lower shadow;
        # otherwise the slider's shadow remains visible over background.
        if keep_r_bottom == 5:
            g[by+7, bx+5] = keep_r_bottom
    if dock_l:
        g[by-1:by+7, bx-1] = keep_l
        g[by+7, bx] = keep_bl
    if keep_top_face is not None:
        g[by-1,bx:bx+6] = keep_top_face
    if side_cap:
        g[by-1,bx+6] = keep_top_cap
        g[by,bx+7] = keep_side_cap

def _erase_slider_safe(g, bx, by, underlay, tiles):
    """Erase even a slider clipped by a screen edge."""
    old = g.copy()
    h,w = g.shape
    xa,xb = max(0,bx-1),min(w,bx+8)
    ya,yb = max(0,by-1),min(h,by+8)
    if xa < xb and ya < yb:
        g[ya:yb,xa:xb] = underlay[ya:yb,xa:xb]
        for tx,ty in tiles:
            if tx < xb and tx+4 > xa and ty < yb and ty+4 > ya:
                g[ty:ty+4,tx:tx+4] = old[ty:ty+4,tx:tx+4]

def _draw_slider_safe(g, bx, by, dirs, loaded=False):
    """Draw a slider whose 9x9 sprite may extend outside the viewport."""
    h,w = g.shape
    if bx >= 1 and by >= 1 and bx+7 < w and by+7 < h:
        _draw_slider(g,bx,by,dirs,loaded)
        return
    pad = 96
    z = np.full((h+2*pad,w+2*pad),10,dtype=int)
    z[pad:pad+h,pad:pad+w] = g
    _draw_slider(z,bx+pad,by+pad,dirs,loaded)
    g[:] = z[pad:pad+h,pad:pad+w]

def _draw_lock_slider_safe(g,bx,by,dirs):
    """Draw a movable lock carrier with the normal slider outline/shadow."""
    h,w = g.shape
    false_left_dock = (bx-2 >= 0 and bx-2 < w and by >= 1 and by+7 < h and
                       np.any(np.isin(g[by-1:by+8,bx-2],[1,2,8,14])) and
                       not np.any(np.isin(g[by:by+6,bx-2],[1,2,8,14])))
    false_right_dock = (bx+7 >= 0 and bx+7 < w and by >= 1 and by+7 < h and
                        np.any(np.isin(g[by-1:by+8,bx+7],[1,2,8,14])) and
                        not np.any(np.isin(g[by:by+6,bx+7],[1,2,8,14])))
    above_cell = (by >= 2 and
                  (np.any(np.isin(g[by-2,bx:bx+6],[1,2,8,14])) or
                   np.any(g[max(0,by-7):by-2,bx:bx+6] == 15)))
    below_cell = (by+7 < h and
                  (np.any(np.isin(g[by+7,bx:bx+6],[1,2,8,14])) or
                   np.any(g[by+7:min(h,by+13),bx:bx+6] == 15)))
    vertical_between = (bx >= 1 and bx+7 < w and above_cell and below_cell)
    keep_v_top = g[by-1,bx-1:bx+7].copy() if vertical_between else None
    keep_v_bottom = g[by+6:by+8,bx:bx+7].copy() if vertical_between else None
    # A carrier entering a board's rightmost cell displaces that board's
    # shadow one column outward.  Remember the interior separator before
    # the generic 9x9 slider outline overwrites it.
    right_dock = (bx >= 1 and bx+7 < w and by >= 1 and by+5 < h and
                  bool(np.all(g[by:by+5,bx-1] == 0)))
    left_before = (g[by:by+5,bx-1].copy() if right_dock else None)
    right_before = (g[by:by+5,bx+6:bx+8].copy() if right_dock else None)
    # Use the live slider-free substrate, not ENTRY_GRID: later camera stages
    # expose world coordinates whose screen locations do not correspond to the
    # entry frame.
    upper_left_before = (int(g[by-1,bx-1])
                         if by >= 1 and bx >= 1 and by-1 < g.shape[0]
                         and bx-1 < g.shape[1] else 10)
    between_boards = (right_dock and
                      bool(np.all((right_before == 0) | (right_before == 1))))
    _draw_slider_safe(g,bx,by,dirs,False)
    pat = np.array([[11,15,15,15,15,11],
                    [11,15,0,7,15,11],
                    [11,15,7,7,15,11],
                    [11,15,15,15,15,11],
                    [11,5,5,5,5,11],
                    [11,11,11,11,11,11]])
    h,w = g.shape
    xa,xb = max(0,bx),min(w,bx+6)
    ya,yb = max(0,by),min(h,by+6)
    if xa < xb and ya < yb:
        g[ya:yb,xa:xb] = pat[ya-by:yb-by,xa-bx:xb-bx]
    if between_boards:
        # At a bridge cell the two adjacent board interiors remain visible;
        # only the six-cell lock face occupies the connecting rail.
        g[by:by+5,bx-1] = left_before
        g[by:by+5,bx+6:bx+8] = right_before
    elif right_dock:
        g[by:by+5,bx-1] = left_before
        if bool(np.all(right_before == 10)):
            # At an exposed one-sided dock, push the carrier frame and shadow
            # outward beginning one row above the face.
            g[by-1:by+5,bx+6] = 5
            g[by:by+5,bx+7] = 9
        else:
            # Along a board's lower corner, its existing top frame remains;
            # extend the side frame below it and offset the shadow one row.
            g[by:by+5,bx+6] = 5
            g[by+1:by+5,bx+7] = 9
    # On a free-standing vertical rail segment the carrier instead keeps a
    # reinforced left frame from above its face through its penultimate row.
    elif ("U" in dirs or "D" in dirs) and 0 <= bx-1 < w:
        # Exposed rail keeps the cap above; beside a board-bottom junction
        # the separator above stays visible and the side starts at the face.
        start = by-1 if upper_left_before == 10 else by
        if start == by and by-1 >= 0:
            g[by-1,bx-1] = upper_left_before
        ya2,yb2 = max(0,start),min(h,by+5)
        if ya2 < yb2:
            g[ya2:yb2,bx-1] = 5
    if false_left_dock and 0 <= bx-1 < w:
        g[by:by+5,bx-1] = 5
    if false_right_dock and 0 <= bx+7 < w:
        g[by:by+5,bx+6] = 5
        edge = g[by:by+5,bx+7]
        edge[edge == 10] = 9
    if vertical_between:
        g[by-1,bx-1:bx+7] = keep_v_top
        g[by+6:by+8,bx:bx+7] = keep_v_bottom

def _draw_compact_slider_safe(g,bx,by,loaded=False,right_edge=False):
    """Third-stage slider: face plus left rail edge, without outer shadow."""
    h,w = g.shape
    pad = 96
    z = np.full((h+2*pad,w+2*pad),10,dtype=int)
    z[pad:pad+h,pad:pad+w] = g
    xx,yy = bx+pad,by+pad
    pat = np.array([[11,11,11,11,11,11],
                    [11,12,12,12,12,11],
                    [11,12,12,12,12,11],
                    [11,12,12,12,12,11],
                    [11,12,12,12,12,11],
                    [11,11,11,11,11,11]])
    z[yy:yy+6,xx:xx+6] = pat
    z[yy:yy+6,xx-1] = 5
    if right_edge:
        z[yy:yy+6,xx+6] = 5
        z[yy+4,xx+7] = 9
    if loaded:
        pc = int(loaded) if int(loaded) in (8,14) else 14
        z[yy+1:yy+5,xx+1:xx+5] = _piece_block(pc, 12)
    g[:] = z[pad:pad+h,pad:pad+w]

def _draw_level3_record(g,under,bx,by,loaded,cam,cam_y):
    sx,sy = bx-cam,by-cam_y
    if by == 71:
        _draw_compact_slider_safe(g,sx,sy,loaded,right_edge=(bx < 59))
        # At the left board junction the fixed board supplies a partial
        # outer frame around the otherwise compact rail face.
        if bx == 35:
            g[sy-1, sx+1:sx+5] = 5
            g[sy+6, sx+1:sx+5] = 5
            g[sy+7, sx+2:sx+5] = 9
        elif bx == 29:
            # At the final left dock, the neighbouring board replaces the
            # compact face's left rail edge and supplies one lower shadow.
            g[sy:sy+6, sx-1] = under[sy:sy+6, sx-1]
            g[sy+5, sx+7] = 9
    else:
        _draw_slider_safe(g,sx,sy,_rail_dirs(under,sx,sy),loaded)
        # A vertical dock immediately above an f/7 lock uses a complete
        # upper/side frame, while the lock itself remains visible beneath it.
        if (sy >= 1 and sx >= 1 and sy+7 < g.shape[0] and sx+7 < g.shape[1]
                and np.any(under[sy+6:sy+8,sx:sx+6] == 15)):
            g[sy-1,sx-1:sx+7] = 5
            g[sy:sy+5,sx-1] = 5
            g[sy:sy+5,sx+6] = 5
            g[sy:sy+5,sx+7] = 9
            g[sy+6:sy+8,sx-1:sx+8] = under[sy+6:sy+8,sx-1:sx+8]

def _move_level3_sliders(g, action, underlay, tiles, records,
                         cam=0, cam_y=0):
    """Move level 3's two world-coordinate sliders."""
    if not records:
        return g, records
    recs = [(int(r[0]),int(r[1]),bool(r[2])) for r in records]
    for bx,by,loaded in recs:
        _erase_slider_safe(g,bx-cam,by-cam_y,underlay,tiles)
    out = []
    for bx,by,loaded in recs:
        nx,ny = bx,by
        if by == 23:
            if action == 4 and bx in (47,53,59,65):
                nx += 6
            elif action == 3 and bx in (53,59,65,71):
                nx -= 6
        elif by == 47:
            if action == 4 and bx in (53,59,65,71):
                nx += 6
            elif action == 3 and bx in (59,65,71,77):
                nx -= 6
            elif action == 2 and bx == 53:
                ny += 6
        elif by == 53 and bx == 53:
            if action == 2:
                ny += 6
            elif action == 1:
                ny -= 6
        elif by == 59 and bx == 53:
            if action == 1:
                ny -= 6
        elif by == 71:
            if action == 4 and bx in (29,35,41,47,53):
                nx += 6
            elif action == 3 and bx in (35,41,47,53,59):
                nx -= 6
        out.append((nx,ny,loaded))
    for bx,by,loaded in out:
        _draw_level3_record(g,underlay,bx,by,loaded,cam,cam_y)
    return g, out

def _draw_normal_carrier_safe(g,bx,by,dirs,loaded,base):
    """Draw a normal carrier plus rail/board junction corrections."""
    false_left_dock = (bx-2 >= 0 and by >= 1 and by+7 < base.shape[0] and
        np.any(np.isin(base[by-1:by+8,bx-2],[1,2,8,14])) and
        not np.any(np.isin(base[by:by+6,bx-2],[1,2,8,14])))
    _draw_slider_safe(g,bx,by,dirs,loaded)
    if false_left_dock and ("U" in dirs or "D" in dirs):
        g[by-1:by+5,bx-1] = 5
    false_right_dock = (bx+7 >= 0 and bx+7 < g.shape[1] and
        by >= 1 and by+7 < base.shape[0] and
        np.any(np.isin(base[by-1:by+8,bx+7],[1,2,8,14])) and
        not np.any(np.isin(base[by:by+6,bx+7],[1,2,8,14])))
    one_sided_right = ((bx >= 1 and bx+7 < g.shape[1] and
        by >= 1 and by+5 < g.shape[0] and
        bool(np.all(base[by:by+5,bx-1] == 0)) and
        bool(np.all(base[by:by+5,bx+6:bx+8] == 10))) or
        false_right_dock)
    if one_sided_right:
        g[by-1:by+5,bx+6] = 5
        g[by:by+5,bx+7] = 9
    if ("U" in dirs or "D" in dirs) and by >= 1 and bx >= 1:
        corner = int(base[by-1,bx-1])
        if corner != 10:
            g[by-1,bx-1] = corner

def _move_level4_sliders(g,action,underlay,tiles,records,cam,full_under):
    """Move level-4 normal/lock carriers in fixed world coordinates."""
    delta = {1:(0,-6),2:(0,6),3:(-6,0),4:(6,0)}.get(action)
    if not records or delta is None:
        return g,records
    recs = [(int(r[0]),int(r[1]),bool(r[2]),bool(r[3])) for r in records]
    for bx,by,loaded,is_lock in recs:
        _erase_slider_safe(g,bx-cam,by,underlay,tiles)
    out=[]
    occupied=set()
    h,w=full_under.shape
    for bx,by,loaded,is_lock in recs:
        nx,ny=bx+delta[0],by+delta[1]
        valid=(nx>=1 and ny>=1 and nx+7<w and ny+7<h and
               bool(np.all(full_under[ny+2:ny+4,nx+2:nx+4]==5)))
        if valid and (nx,ny) not in occupied:
            bx,by=nx,ny
        occupied.add((bx,by))
        out.append((bx,by,loaded,is_lock))
    for bx,by,loaded,is_lock in out:
        sx=bx-cam
        dirs=_rail_dirs(underlay,sx,by)
        if is_lock:
            _draw_lock_slider_safe(g,sx,by,dirs)
        else:
            _draw_normal_carrier_safe(g,sx,by,dirs,loaded,underlay)
    return g,out

def _restore_level5_top_gap(g,base,sx,by):
    """A carrier below a fixed f/7 lock exposes the intervening gap row."""
    if by >= 6 and np.any(base[by-6:by,sx:sx+6] == 15):
        g[by-1,sx:sx+6] = base[by-1,sx:sx+6]


def _restore_level5_pair_seams(g,records,cam):
    """When two carrier faces touch, the left face border wins their seam."""
    recs=[(int(r[0]),int(r[1])) for r in records]
    for lx,ly in recs:
        if (lx+6,ly) in recs:
            sx=lx-int(cam)+5
            if 0 <= sx < g.shape[1]:
                g[max(0,ly):min(g.shape[0],ly+6),sx] = 11


def _move_level5_sliders(g,action,underlay,tiles,records,cam,full_under):
    """Move level-5's adjacent [ordinary, colour8] carrier train."""
    delta={1:(0,-6),2:(0,6),3:(-6,0),4:(6,0)}.get(action)
    if not records or delta is None:
        return g,records
    recs=[(int(r[0]),int(r[1]),int(r[2])) for r in records]
    for bx,by,colour in recs:
        _erase_slider_safe(g,bx-cam,by,underlay,tiles)
    out=[]
    occupied=set()
    h,w=full_under.shape
    for bx,by,colour in recs:
        nx,ny=bx+delta[0],by+delta[1]
        valid=(nx>=1 and ny>=1 and nx+7<w and ny+7<h and
               bool(np.all(full_under[ny+2:ny+4,nx+2:nx+4]==5)))
        if valid and (nx,ny) not in occupied:
            bx,by=nx,ny
        occupied.add((bx,by))
        out.append((bx,by,colour))
    base=g.copy()
    for bx,by,colour in out:
        sx=bx-cam
        dirs=_rail_dirs(underlay,sx,by)
        _draw_normal_carrier_safe(g,sx,by,dirs,colour,base)
        _restore_level5_top_gap(g,base,sx,by)
    _restore_level5_pair_seams(g,out,cam)
    # At the right junction the upper carrier's lower-left outline overlaps
    # the stationary lower carrier's upper-right corner; the lower face wins.
    for lx,ly,lc in out:
        for ux,uy,uc in out:
            if ux == lx+6 and uy == ly-6:
                sx=lx-cam
                g[ly,sx+5]=11
                g[ly+1,sx+6]=5
    return g,out

def _move_sliders(g, action, underlay=None, tiles=None):
    boxes = [(bx,by,False) for bx,by in _slider_bboxes(g)]
    boxes += [(bx,by,True) for bx,by in _lock_slider_bboxes(g)]
    delta = {1:(0,-6), 2:(0,6), 3:(-6,0), 4:(6,0)}.get(action)
    if not boxes or delta is None:
        return
    original = g.copy()
    records = []
    base = g.copy()
    # Every normal and lock-bearing rail carrier receives the arrow
    # simultaneously, so expose all substrates before testing destinations.
    for bx, by, is_lock in boxes:
        if is_lock:
            loaded = False
        else:
            face = original[by:by+6, bx:bx+6]
            loaded = (8 if np.any(face == 8) else
                      (14 if np.any(face == 14) else False))
        dirs = _rail_dirs(original, bx, by)
        records.append((bx,by,loaded,is_lock))
        if is_lock:
            # The reinforced carrier repeatedly overlaps fixed board rims;
            # restore its whole static 9x9 substrate, retaining live tiles.
            _erase_slider_safe(base,bx,by,underlay,tiles)
        else:
            # The slider-free underlay is the authoritative rail/board
            # substrate; preserving live tile blocks keeps peg dynamics.
            _erase_slider_safe(base,bx,by,underlay,tiles)

    moves = []
    occupied = set()
    for bx, by, loaded, is_lock in records:
        nx, ny = bx + delta[0], by + delta[1]
        valid = (nx >= 1 and ny >= 1 and
                 nx+7 < g.shape[1] and ny+7 < g.shape[0])
        if valid:
            centre = base[ny+2:ny+4, nx+2:nx+4]
            valid = bool(np.all(centre == 5))
        if valid and (nx,ny) not in occupied:
            occupied.add((nx,ny))
            moves.append((nx,ny,loaded,is_lock,True,bx,by))
        else:
            moves.append((bx,by,loaded,is_lock,False,bx,by))

    g[:] = base
    for nx, ny, loaded, is_lock, moved, ox, oy in moves:
        if moved:
            dirs = _rail_dirs(base,nx,ny)
            if is_lock:
                _draw_lock_slider_safe(g,nx,ny,dirs)
            else:
                _draw_normal_carrier_safe(g,nx,ny,dirs,loaded,base)
        else:
            # A blocked carrier is visually unchanged.
            g[oy-1:oy+8, ox-1:ox+8] = original[oy-1:oy+8, ox-1:ox+8]

def _retry_bounds(g):
    """Bounds of the large connected colour-f retry key, not small f locks."""
    ys, xs = np.where(g == 15)
    unseen = set((int(x), int(y)) for x, y in zip(xs, ys))
    while unseen:
        seed = unseen.pop()
        comp = [seed]
        todo = [seed]
        while todo:
            px, py = todo.pop()
            for q in ((px+1,py),(px-1,py),(px,py+1),(px,py-1)):
                if q in unseen:
                    unseen.remove(q)
                    comp.append(q)
                    todo.append(q)
        if len(comp) >= 40:
            xx = [p[0] for p in comp]
            yy = [p[1] for p in comp]
            return min(xx), min(yy), max(xx), max(yy)
    return None

def _enter_key_phase(g, tiles):
    # Completed pegs become blue activated markers.
    for x, y in tiles:
        b = g[y:y+4, x:x+4]
        b[b == 14] = 2

    # The key enters from the bottom edge.  This is the level's standard
    # upright key sprite (including its grey outline and shadow).
    rows = [
        "a55555555aa",
        "55ffffff55a",
        "5ffffffff59",
        "5ff5555ff59",
        "5ff5005ff59",
        "5ff5005ff59",
        "5ff5555ff59",
        "5ffffffff59",
        "55ffffff559",
        "a555ff55599",
        "aaa5ff5999a",
        "aaa5ff59aaa",
        "aaa5ff59aaa",
    ]
    x0 = 2
    y0 = g.shape[0] - len(rows)
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            g[y0+j, x0+i] = vals[c]

def _known_right_strip(new_cam):
    # Static world columns 64..71 revealed by level 2's first camera pan.
    if CURRENT_LEVEL == 2 and new_cam == 8:
        rows = [
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","55555555","50000000",
            "50111100","50111100","50111100","50111100","50000000",
            "00000000","00111100","00111100","00111100","00111100",
            "00000000","50000000","50111100","50111100","50111100",
            "50111100","50000000","50000000","50111100","50111100",
            "50111100","50111100","50000000","50000000","50111100",
            "50111100","50111100","50111100","50000000","50000000",
            "50111100","50111100","50111100","50111100","50000000",
            "50000000","501ee100","50eeee00","50eeee00","501ee100",
            "50000000","50000000","50111100","50111100","50111100",
            "50111100","50000000","50000000","50111100","50111100",
            "50111100","50111100","50000000","55555555","a9999999",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa"
        ]
        vals = {c:int(c,16) for c in "0123456789abcdef"}
        z = np.zeros((64,8), dtype=int)
        for y,row in enumerate(rows, start=1):
            z[y] = [vals[c] for c in row]
        return z
    if CURRENT_LEVEL == 2 and new_cam == 16:
        rows = [
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","555555aa","0000059a",
            "1111059a","1111059a","1111059a","1111059a","0000059a",
            "0000059a","1111059a","1111059a","1111059a","1111059a",
            "00000555","00000000","1ee1001e","eeee00ee","eeee00ee",
            "1ee1001e","00000000","00000555","11110599","1111059a",
            "1111059a","1111059a","00000555","00000000","1ee1001e",
            "eeee00ee","eeee00ee","1ee1001e","00000000","00000555",
            "11110599","1111059a","1111059a","1111059a","00000555",
            "00000000","11110011","11110011","11110011","11110011",
            "00000000","00000555","1ee10599","eeee059a","eeee059a",
            "1ee1059a","0000059a","0000059a","1111059a","1111059a",
            "1111059a","1111059a","0000059a","5555559a","9999999a",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa"
        ]
        vals = {c:int(c,16) for c in "0123456789abcdef"}
        z = np.zeros((64,8), dtype=int)
        for y,row in enumerate(rows, start=1):
            z[y] = [vals[c] for c in row]
        return z
    if CURRENT_LEVEL == 2 and new_cam == 24:
        rows = [
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa",
            "55555555","00000000","e1001111","ee001111","ee001111",
            "e1001111","00000000","55555555","99999999","aaaaaaaa",
            "aaaaaaaa","aaaaaaaa","55555555","00000000","e1001111",
            "ee001111","ee001111","e1001111","00000000","55555555",
            "99999999","aaaaaaaa","aaaaaaaa","aaaaaaaa","5555aaaa",
            "00059aaa","11059aaa","11059aaa","11059aaa","11059aaa",
            "00059aaa","55559aaa","99999aaa","aaaaaaaa","aaaaaaaa",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa","aaaaaaaa",
            "aaaaaaaa","aaaaaaaa","aaaaaaaa"
        ]
        vals = {c:int(c,16) for c in "0123456789abcdef"}
        z = np.zeros((64,8), dtype=int)
        for y,row in enumerate(rows, start=1):
            z[y] = [vals[c] for c in row]
        return z
    return None

def _known_level3_right():
    """Level-3 static world columns 64..93 revealed by its first stage snap."""
    if CURRENT_LEVEL != 3:
        return None
    rows = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaa555555555555555555",
        "aaaaaaaaaaaa500000000000000000","aaaaaaaaaaaa501ee1001111001111",
        "55555555555550eeee001111001111","55555555555550eeee001111001111",
        "aaaaaaaaaaaa501ee1001111001111","aaaaaaaaaaaa500000000000000000",
        "aaaaaaaaaaaa50000000ffff000000","aaaaaaaaaaaa50111100f07f001111",
        "aaaaaaaaaaaa50111100f77f001111","aaaaaaaaaaaa50111100ffff001111",
        "aaaaaaaaaaaa501111005555001111","aaaaaaaaaaaa500000000000000000",
        "aaaaaaaaaaaa500000000000000000","aaaaaaaaaaaa501111001111001111",
        "aaaaaaaaaaaa501111001111001111","aaaaaaaaaaaa501111001111001111",
        "aaaaaaaaaaaa501111001111001111","aaaaaaaaaaaa500000000000000000",
        "aaaaaaaaaaaa50000000ffff000000","aaaaaaaaaaaa50111100f07f001111",
        "aaaaaaaaaaaa50111100f77f001111","aaaaaaaaaaaa50111100ffff001111",
        "aaaaaaaaaaaa501111005555001111","aaaaaaaaaaaa500000000000000000",
        "aaaaaaaaaaaa555555500000000000","aaaaaaaaaaaaa99999501111001111",
        "555555555555555555501111001111","555555555555555555501111001111",
        "aaaaaaaaaaaaaaaaaa501111001111","aaaaaaaaaaaaaaaaaa500000000000",
        "aaaaaaaaaaaaaaaaaa555555555555","aaaaaaaaaaaaaaaaaaa99999999999",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((64,30),dtype=int)
    for y,row in enumerate(rows,start=1):
        z[y] = [vals[c] for c in row]
    return z

def _known_level3_more():
    """Level-3 static world columns 94..117, revealed by camera follow."""
    if CURRENT_LEVEL != 3:
        return None
    z = np.full((64,24),10,dtype=int)
    left = {
        22:"555555", 23:"000000",
        24:"001111", 25:"001111", 26:"001111", 27:"001111",
        28:"000000", 29:"000000",
        30:"001111", 31:"001111", 32:"001111", 33:"001111",
        34:"000000", 35:"000000",
        36:"001111", 37:"001111", 38:"001111", 39:"001111",
        40:"000000", 41:"000000",
        42:"001111", 43:"001111", 44:"001111", 45:"001111",
        46:"000000", 47:"00ffff", 48:"00f07f", 49:"00f77f",
        50:"00ffff", 51:"005555", 52:"000000", 53:"555555",
        54:"999999"
    }
    right = {
        22:"555555", 23:"000000",
        24:"001ee1", 25:"00eeee", 26:"00eeee", 27:"001ee1",
        28:"000000", 29:"00ffff", 30:"00f07f", 31:"00f77f",
        32:"00ffff", 33:"005555", 34:"000000", 35:"000000",
        36:"001111", 37:"001111", 38:"001111", 39:"001111",
        40:"000000", 41:"00ffff", 42:"00f07f", 43:"00f77f",
        44:"00ffff", 45:"005555", 46:"000000", 47:"000000",
        48:"001111", 49:"001111", 50:"001111", 51:"001111",
        52:"000000", 53:"555555", 54:"999999"
    }
    far = {
        22:"555555", 23:"000000",
        24:"001111", 25:"001111", 26:"001111", 27:"001111",
        28:"000000", 29:"000000",
        30:"001111", 31:"001111", 32:"001111", 33:"001111",
        34:"000000", 35:"000000",
        36:"001111", 37:"001111", 38:"001111", 39:"001111",
        40:"000000", 41:"000000",
        42:"001111", 43:"001111", 44:"001111", 45:"001111",
        46:"000000", 47:"000000",
        48:"001111", 49:"001111", 50:"001111", 51:"001111",
        52:"000000", 53:"555555", 54:"999999"
    }
    edge = {22:"55aaaa", 53:"559aaa", 54:"999aaa"}
    for y in range(23,53):
        edge[y] = "059aaa"
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    for y,row in left.items():
        z[y,:6] = [vals[c] for c in row]
    for y,row in right.items():
        z[y,6:12] = [vals[c] for c in row]
    for y,row in far.items():
        z[y,12:18] = [vals[c] for c in row]
    for y,row in edge.items():
        z[y,18:24] = [vals[c] for c in row]
    return z

def _known_level3_lower():
    """Level-3 world rows 64..93, columns 39..102, revealed by lower-stage snap."""
    if CURRENT_LEVEL != 3:
        return None
    rows = [
        "000000005555555555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "550ffff00000000ffff000000000000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "950f07f00111100f07f001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a50f77f00111100f77f001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a50ffff00111100ffff001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a505555001111005555001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a500000000000000000000000000000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a5555555555555555555bbbbbb00000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aa999999999999999995bccccb01111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "55555555555555555555bccccb01111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "55555555555555555555bccccb01111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaa5bccccb01111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a5555555555555555555bbbbbb00000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a50ffff000000000000000000000000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a50f07f001111001111001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a50f77f001111001111001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a50ffff001111001111001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "a505555001111001111001111001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "5500000000000000000000000000000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "0000000055555555555555555555555559aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "1001111059999999999999999999999999aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "e001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "e001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "1001111059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "0000000059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "5555555559aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "9999999999aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((30,64),dtype=int)
    for y,row in enumerate(rows):
        z[y] = [vals[c] for c in row]
    return z

def _known_level3_lower_left2():
    """Level-3 lower world rows 64..93, columns 21..26."""
    if CURRENT_LEVEL != 3:
        return None
    rows = [
        "a55555","a50000","a50111","a50111","a50111","a50111",
        "a50000","a50000","a50111","a50111","a50111","a50111",
        "a50000","a50000","a50111","a50111","a50111","a50111",
        "a50000","a55555","aa9999","aaaaaa","aaaaaa","aaaaaa",
        "aaaaaa","aaaaaa","aaaaaa","aaaaaa","aaaaaa","aaaaaa"
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((30,6),dtype=int)
    for y,row in enumerate(rows):
        z[y] = [vals[c] for c in row]
    return z

def _known_level3_lower_left():
    """Level-3 lower world rows 64..93, columns 27..38."""
    if CURRENT_LEVEL != 3:
        return None
    left = [
        "550000","000fff","100f07","100f77","100fff","100555",
        "000000","005555","105999","105555","105555","1059aa",
        "005555","000fff","100f07","100f77","100fff","100555",
        "000000","550000","950111","a50111","a50111","a50111",
        "a50000","a55555","aa9999","aaaaaa","aaaaaa","aaaaaa"
    ]
    right = [
        "000000","f05555","f05999","f059aa","f059aa","5059aa",
        "0059aa","5559aa","9999aa","555555","555555","aaaaaa",
        "555aaa","f059aa","f059aa","f059aa","f059aa","5059aa",
        "005555","000000","1001ee","100eee","100eee","1001ee",
        "000000","555555","999999","aaaaaa","aaaaaa","aaaaaa"
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((30,12),dtype=int)
    for y,(a,b) in enumerate(zip(left,right)):
        z[y] = [vals[c] for c in a+b]
    return z

def _known_level3_third_floor():
    """Slider-free substrate around the third-stage slider's first dock."""
    if CURRENT_LEVEL != 3:
        return None
    rows = [
        "0000000000","5555555000","9999995011","5555555011",
        "5555555011","aaaaaa5011","5555555000","0000000000",
        "0011110011","0011110011"
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((10,10),dtype=int)
    for y,row in enumerate(rows):
        z[y] = [vals[c] for c in row]
    return z

def _known_level3_third_floor2():
    """Slider-free substrate around the third slider's second dock."""
    if CURRENT_LEVEL != 3:
        return None
    rows = [
        "0000000000","5555555555","9999999999","5555555555",
        "5555555555","aaaaaaaaaa","5555555555","0000000000",
        "0011110011","0011110011"
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((10,10),dtype=int)
    for y,row in enumerate(rows):
        z[y] = [vals[c] for c in row]
    return z

def _apply_level3_dynamic_floor(canvas, records):
    """Reveal rail substrate only after the compact third slider reaches it."""
    if CURRENT_LEVEL != 3 or not records or len(records) < 3:
        return canvas
    bx, by = int(records[2][0]), int(records[2][1])
    if by == 71 and bx <= 53:
        floor = _known_level3_third_floor2()
        if floor is not None:
            canvas[70:80,52:62] = floor
    return canvas

def _known_level4_right():
    """Level-4 world columns 64..81 revealed by the carrier-loading snap."""
    if CURRENT_LEVEL != 4:
        return None
    rows = [
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaa555555",
        "aaaaaaaaaaaa500000",
        "aaaaaaaaaaaa501111",
        "55555aaaaaaa501111",
        "55555aaaaaaa501111",
        "aaa55aaaaaaa501111",
        "aaa55a555555500000",
        "aaa55a500000000000",
        "aaa55a501ee1001111",
        "aaa55550eeee001111",
        "aaa55550eeee001111",
        "aaaaaa501ee1001111",
        "aaaaaa500000000000",
        "aaaaaa555555500000",
        "aaaaaaa99999501111",
        "aaaaaaaaaaaa501111",
        "aaaaaaaaaaaa501111",
        "aaaaaaaaaaaa501111",
        "aaaaaaaaaaaa500000",
        "aaaaaaaaaaaa555555",
        "aaaaaaaaaaaaa99999",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaa",
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((64,18),dtype=int)
    for y,row in enumerate(rows,start=1):
        z[y] = [vals[c] for c in row]
    return z

def _known_level4_more1():
    """Level-4 world columns 82..87 revealed by first loaded-carrier follow."""
    if CURRENT_LEVEL != 4:
        return None
    rows = [
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaa555",
        "aaa555",
        "aaa55a",
        "55a55a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "05955a",
        "55955a",
        "99955a",
        "aaa555",
        "aaa555",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((64,6),dtype=int)
    for y,row in enumerate(rows,start=1):
        z[y] = [vals[c] for c in row]
    return z

def _known_level4_more2():
    """Level-4 world columns 88..93 revealed by second loaded-carrier follow."""
    if CURRENT_LEVEL != 4:
        return None
    rows = [
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "555555",
        "500000",
        "501111",
        "501111",
        "501111",
        "501111",
        "500000",
        "555555",
        "a99999",
        "555555",
        "555555",
        "aaaaaa",
        "555555",
        "500000",
        "501111",
        "501111",
        "501111",
        "501111",
        "500000",
        "500000",
        "501111",
        "501111",
        "501111",
        "501111",
        "500000",
        "500000",
        "501111",
        "501111",
        "501111",
        "501111",
        "500000",
        "555555",
        "a99999",
        "555555",
        "555555",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "555555",
        "500000",
        "501111",
        "501111",
        "501111",
        "501111",
        "500000",
        "555555",
        "a99999",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((64,6),dtype=int)
    for y,row in enumerate(rows,start=1):
        z[y] = [vals[c] for c in row]
    return z

def _known_level4_more3():
    """Level-4 world columns 94..99 revealed by third loaded-carrier follow."""
    if CURRENT_LEVEL != 4:
        return None
    rows = [
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
        "555555",
        "000000",
        "001111",
        "001111",
        "001111",
        "001111",
        "000000",
        "555555",
        "999999",
        "555555",
        "555555",
        "aaaaaa",
        "555555",
        "000000",
        "001111",
        "001111",
        "001111",
        "001111",
        "000000",
        "00ffff",
        "00f07f",
        "00f77f",
        "00ffff",
        "005555",
        "000000",
        "000000",
        "001111",
        "001111",
        "001111",
        "001111",
        "000000",
        "555555",
        "999999",
        "555555",
        "555555",
        "aaaaaa",
        "555555",
        "500000",
        "501111",
        "501111",
        "501111",
        "501111",
        "500000",
        "50ffff",
        "50f07f",
        "50f77f",
        "50ffff",
        "505555",
        "500000",
        "000000",
        "001111",
        "001111",
        "001111",
        "001111",
        "000000",
        "555555",
        "999999",
        "aaaaaa",
        "aaaaaa",
        "aaaaaa",
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((64,6),dtype=int)
    for y,row in enumerate(rows,start=1):
        z[y] = [vals[c] for c in row]
    return z

def _known_level4_more4():
    """Level-4 world columns 100..132 revealed by the second-stage snap."""
    if CURRENT_LEVEL != 4:
        return None
    rows = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "55555555555555555555555555aaaaaaa",
        "00ffff000000000000000000059aaaaaa",
        "00f07f001111001111001ee1059aaaaaa",
        "00f77f00111100111100eeee059aaaaaa",
        "00ffff00111100111100eeee059aaaaaa",
        "005555001111001111001ee1059aaaaaa",
        "000000000000000000000000059aaaaaa",
        "555555555555555555555555559aaaaaa",
        "999999999999999999999999999aaaaaa",
        "55555555555555555555555555555aaaa",
        "55555555555555555555555555555aaaa",
        "aaaaaaaaa55aaaaaaaaaaaaaaaa55aaaa",
        "55555555a55a55555555aaaa55555555a",
        "00000005955a500000059aaa5bffffb59",
        "00111105955a501111059aaa5bf07fb59",
        "00111105955a501111059aaa5bf77fb59",
        "00111105955a501111059aaa5bffffb59",
        "00111105955a501111059aaa5b5555b59",
        "00000005955a5000000555555bbbbbb59",
        "00000005955a500000000000055555559",
        "00111105955a501111001111059559999",
        "00111105955a50111100111105955aaaa",
        "00111105955a50111100111105955aaaa",
        "00111105955a50111100111105955aaaa",
        "00000005955a50000000000005955aaaa",
        "00ffff05955a50000000000005955aaaa",
        "00f07f05955a501ee100111105955aaaa",
        "00f77f05955a50eeee00111105955aaaa",
        "00ffff05955a50eeee00111105955aaaa",
        "00555505955a501ee100111105955aaaa",
        "00000005955a50000000000005955aaaa",
        "55555555955a55555555555555955aaaa",
        "99999999955aa9999999999999955aaaa",
        "55555555555555555555555555555aaaa",
        "55555555555555555555555555555aaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "55aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "059aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "05555555aaaaaaaaaaaaaaaaaaaaaaaaa",
        "000000059aaaaaaaaaaaaaaaaaaaaaaaa",
        "001ee1059aaaaaaaaaaaaaaaaaaaaaaaa",
        "00eeee059aaaaaaaaaaaaaaaaaaaaaaaa",
        "00eeee059aaaaaaaaaaaaaaaaaaaaaaaa",
        "001ee1059aaaaaaaaaaaaaaaaaaaaaaaa",
        "000000059aaaaaaaaaaaaaaaaaaaaaaaa",
        "555555559aaaaaaaaaaaaaaaaaaaaaaaa",
        "999999999aaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.zeros((64,33),dtype=int)
    for y,row in enumerate(rows,start=1):
        z[y] = [vals[c] for c in row]
    # Remove the newly revealed movable lock carrier (world bbox125,17)
    # from the authoritative substrate.  It sits on a vertical rail; the
    # four exceptional cells belong to the neighbouring board junction.
    z[16:25,24:33] = 10
    z[16:25,27:29] = 5
    z[22,24] = 5
    z[23,24] = 0
    z[24,24] = 0
    z[24,25] = 5
    # Cells exposed when that carrier moves up onto the top rail.
    z[22,25] = 5
    z[23,25] = 5
    z[23,26] = 9
    z[24,26] = 9
    return z

def _known_level5_more():
    """World columns 138..169 revealed by level 5's second camera snap."""
    rows = [
        "555555555555555555aaaa55555555aa",
        "0000000000000000059aaa500000059a",
        "1111001111001111059aaa501111059a",
        "111100111100111105555a501111059a",
        "111100111100111105555a501111059a",
        "111100111100111105955a501111059a",
        "000000000000000005955a500000059a",
        "555550ffff05555555955a500000059a",
        "999950f07f05999999955a501ee1059a",
        "aaaa50f77f059aaaaaa55a50eeee059a",
        "aaaa50ffff059aaaaaa55a50eeee059a",
        "aaaa505555059aaaaaa55a501ee1059a",
        "555550000005555555a55a500000059a",
        "00000bbbbbb0000005955a500000059a",
        "11110bccccb0111105955a501111059a",
        "11110bccccb0111105955a501111059a",
        "11110bccccb0111105955a501111059a",
        "11110bccccb0111105955a501111059a",
        "00000bbbbbb0000005955a500000059a",
        "000005555555555555955a555555559a",
        "1ee105955999999999955aa99999999a",
        "eeee05955aaaaaaaaaa55aaaaaaaaaaa",
        "eeee05955aaaaaaaaaa55aaaaaaaaaaa",
        "1ee105955aaaaaaaaaa55aaaaaaaaaaa",
        "000005955aaaaaaaaaa55aaaaaaaaaaa",
        "000005955aaaaaaaaaa55aaaaaaaaaaa",
        "111105955aaaaaaaaaa55aaaaaaaaaaa",
        "111105955555555555555aaaaaaaaaaa",
        "111105955555555555555aaaaaaaaaaa",
        "1111059aaaaaaaaaaaaaaaaaaaaaaaaa",
        "0000059aaaaaaaaaaaaaaaaaaaaaaaaa",
        "5555559aaaaaaaaaaaaaaaaaaaaaaaaa",
        "9999999aaaaaaaaaaaaaaaaaaaaaaaaa",
    ]
    vals = {c:int(c,16) for c in "0123456789abcdef"}
    z = np.full((64,32),10,dtype=int)
    z[0] = 0
    for y,row in enumerate(rows,start=16):
        z[y] = [vals[c] for c in row]
    return z


def _make_underlay(entry):
    u = np.array(entry, dtype=int, copy=True)
    original = u.copy()
    tiles = _tiles_from(original)
    for bx,by in _slider_bboxes(original):
        _erase_slider(u,bx,by,_rail_dirs(original,bx,by),None,tiles)
    for bx,by in _lock_slider_bboxes(original):
        _erase_slider(u,bx,by,_rail_dirs(original,bx,by),None,tiles)
    if CURRENT_LEVEL == 5:
        # The level starts with two edge-adjacent faces on one continuous
        # horizontal rail.  Erasing either face independently can restore
        # pixels of its neighbour from ENTRY_GRID, so expose their shared
        # slider-free substrate as a unit.
        u[40:49,47:64] = 10
        # Moving the train exposes the board's displaced right frame/shadow.
        u[40:49,47] = 5
        u[40:49,48] = 9
        u[43:45,47:64] = 5
    u[0] = 0
    return u

def _world_underlay(entry_grid):
    """Known slider-free world canvas (the level-2 world is 88px wide)."""
    u = _make_underlay(entry_grid)
    if CURRENT_LEVEL == 5:
        # The first snap reveals a horizontal rail through x89; the first
        # six-pixel follow step also exposes the left rim of the next board.
        w = np.full((64,170),10,dtype=int)
        w[:,:64] = u
        w[43:45,64:90] = 5
        w[10,88:96] = 5
        w[11,88] = 5
        w[11,89:96] = 0
        w[12:16,88] = 5
        w[12:16,89] = 0
        w[12:16,90:94] = 1
        w[12:16,94:96] = 0
        w[16:18,88] = 5
        w[16:18,89:96] = 0
        w[18:22,88] = 5
        w[18:22,89] = 0
        w[18:22,90:94] = 1
        w[18:22,94:96] = 0
        w[22,88] = 5
        w[22,89:96] = 0
        w[23,88] = 5
        w[23,89] = 0
        w[23,90:94] = 15
        w[23,94:96] = 0
        w[24,88] = 5
        w[24,89] = 0
        w[24,90:94] = [15,0,7,15]
        w[24,94:96] = 0
        w[25,88] = 5
        w[25,89] = 0
        w[25,90:94] = [15,7,7,15]
        w[25,94:96] = 0
        w[26,88] = 5
        w[26,89] = 0
        w[26,90:94] = 15
        w[26,94:96] = 0
        w[27,88] = 5
        w[27,89] = 0
        w[27,90:94] = 5
        w[27,94:96] = 0
        w[28,88] = 5
        w[28,89:96] = 0
        w[29,88:96] = 5
        w[30,89] = 9
        w[30,90] = 9
        w[30,91:93] = 5
        w[30,93:96] = 9
        w[31:43,91:93] = 5
        w[10,96:102] = 5
        w[11,96:102] = 0
        w[12:16,96:100] = 1
        w[12:16,100:102] = 0
        w[16:18,96:102] = 0
        w[18,96:102] = [1,14,14,1,0,0]
        w[19:21,96:102] = [14,14,14,14,0,0]
        w[21,96:102] = [1,14,14,1,0,0]
        w[22:24,96:102] = 0
        w[24:28,96:100] = 1
        w[24:28,100:102] = 0
        w[28,96:102] = 0
        w[29,96:102] = 5
        w[30,96:102] = 9
        w[10,102:108] = 5
        w[11,102:108] = 0
        w[12:16,102:106] = 1
        w[12:16,106:108] = 0
        w[16:18,102:108] = 0
        w[18:22,102:106] = 1
        w[18:22,106:108] = 0
        w[22:24,102:108] = 0
        w[24:28,102:106] = 1
        w[24:28,106:108] = 0
        w[28,102:108] = 0
        w[29,102:108] = 5
        w[30,102:108] = 9
        w[10,108:114] = 5
        w[11,108:113] = 0
        w[11,113] = 5
        w[12:16,108:112] = 1
        w[12:16,112] = 0
        w[12:16,113] = 5
        w[16,108:113] = 0
        w[16,113] = 5
        w[17,108:114] = 0
        w[18:22,108:112] = 1
        w[18:22,112:114] = 0
        w[22,108:114] = 0
        w[23,108:112] = 15
        w[23,112] = 0
        w[23,113] = 5
        w[24,108:114] = [15,0,7,15,0,5]
        w[25,108:114] = [15,7,7,15,0,5]
        w[26,108:114] = [15,15,15,15,0,5]
        w[27,108:112] = 5
        w[27,112] = 0
        w[27,113] = 5
        w[28,108:113] = 0
        w[28,113] = 5
        w[29,108:114] = 5
        w[30,108:114] = [9,5,5,9,9,9]
        w[31:43,109:111] = 5
        w[43:45,64:111] = 5
        w[11:16,114] = 9
        w[16,114:120] = 5
        w[17,114:120] = 0
        w[18:22,114:118] = 1
        w[18:22,118:120] = 0
        w[22,114:120] = 0
        w[23,114:120] = 5
        w[24,114:120] = 9
        w[25:31,114] = 9
        w[16,120:126] = 5
        w[17,120:126] = 0
        w[18:22,120:124] = 1
        w[18:22,124:126] = 0
        w[22,120:126] = 0
        w[23,120:126] = 5
        w[24,120:126] = 9
        w[40,124:126] = 5
        w[41:59,124] = 5
        w[41:59,125] = 0
        w[59,124:126] = 5
        w[60,125] = 9
        w[16,126:132] = 5
        w[17,126:132] = 0
        w[18:22,126:130] = 1
        w[18:22,130:132] = 0
        w[22,126:132] = 0
        w[23,126:132] = 5
        w[24,126:132] = 9
        w[40,126:132] = 5
        w[41,126:132] = 0
        w[42:46,126:130] = 1
        w[42:46,130:132] = 0
        w[46,126:132] = 0
        w[47,126:131] = 0
        w[47,131] = 5
        w[48,126:132] = [1,14,14,1,0,5]
        w[49:51,126:132] = [14,14,14,14,0,5]
        w[51,126:132] = [1,14,14,1,0,5]
        w[52:54,126:131] = 0
        w[52:54,131] = 5
        w[54:58,126:130] = 1
        w[54:58,130] = 0
        w[54:58,131] = 5
        w[58,126:131] = 0
        w[58,131] = 5
        w[59,126:132] = 5
        w[60,126:132] = 9
        w[16,132:138] = 5
        w[17,132:138] = 0
        w[18:22,132:136] = 1
        w[18:22,136:138] = 0
        w[22,132:138] = 0
        w[23,132:138] = 5
        w[24,132:138] = 9
        w[28,136:138] = 5
        w[29:40,136] = 5
        w[29:40,137] = 0
        w[40,132:137] = 5
        w[40,137] = 0
        w[41,132:138] = 0
        w[42:46,132:136] = 1
        w[42:46,136:138] = 0
        w[46,132:138] = 0
        w[47,132:138] = 5
        w[48,132:138] = 9
        w[49:61,132] = 9
        more5=_known_level5_more()
        w[:,138:170] = more5
        # The newly revealed b/c face at world bbox(143,29) is a third
        # movable carrier, not static scenery.  Its central substrate is the
        # same vertical rail as bbox107, but here the carrier is docked between
        # two board cells: retain the right board edge and both lower junction
        # pixels that the generic dock renderer preserves.
        w[29:38,143:152] = w[29:38,107:116]
        w[29:38,149:152] = more5[29:38,11:14]
        # When the carrier leaves cell144,30 it exposes a framed vertical
        # junction rather than the plain two-pixel spine used at cell108.
        w[29,143:149] = 5
        w[30,143:149] = [5,9,5,5,9,5]
        w[31:34,143:149] = [5,9,5,5,10,5]
        w[34:36,143:149] = [5,9,5,5,10,5]
        w[36,143:149] = [5,9,5,5,10,10]
        w[37,143:145] = more5[37,5:7]
        w[0] = 0
        return w
    l4 = _known_level4_right()
    if l4 is not None:
        more4 = _known_level4_more1()
        more42 = _known_level4_more2()
        more43 = _known_level4_more3()
        more44 = _known_level4_more4()
        width = (82 + (0 if more4 is None else more4.shape[1]) +
                 (0 if more42 is None else more42.shape[1]) +
                 (0 if more43 is None else more43.shape[1]) +
                 (0 if more44 is None else more44.shape[1]))
        w = np.full((64,width),10,dtype=int)
        w[:64,:64] = u
        w[:64,64:82] = l4
        pos = 82
        if more4 is not None:
            w[:64,pos:pos+more4.shape[1]] = more4
            pos += more4.shape[1]
        if more42 is not None:
            w[:64,pos:pos+more42.shape[1]] = more42
            pos += more42.shape[1]
        if more43 is not None:
            w[:64,pos:pos+more43.shape[1]] = more43
            pos += more43.shape[1]
        if more44 is not None:
            w[:64,pos:pos+more44.shape[1]] = more44
        w[0] = 0
        return w
    l3 = _known_level3_right()
    if l3 is not None:
        more = _known_level3_more()
        width = 94 + (0 if more is None else more.shape[1])
        lower = _known_level3_lower()
        lower_left = _known_level3_lower_left()
        lower_left2 = _known_level3_lower_left2()
        # The third-stage camera can follow six pixels below the first
        # mapped lower board; the newly exposed world rows 94..99 are blank.
        height = max(106, 64 + (0 if lower is None else lower.shape[0]))
        w = np.full((height,width),10,dtype=int)
        w[:64,:64] = u
        w[:64,64:94] = l3
        if more is not None:
            w[:64,94:width] = more
        if lower is not None:
            w[64:64+lower.shape[0],39:103] = lower
        if lower_left is not None:
            w[64:64+lower_left.shape[0],27:39] = lower_left
        if lower_left2 is not None:
            w[64:64+lower_left2.shape[0],21:27] = lower_left2
        third_floor = _known_level3_third_floor()
        if third_floor is not None:
            w[70:80,58:68] = third_floor
        w[0] = 0
        return w
    strips = []
    cam = 8
    while True:
        s = _known_right_strip(cam)
        if s is None:
            break
        strips.append((cam + 56, s))
        cam += 8
    if not strips:
        return u
    width = max(64, max(x + 8 for x, _ in strips))
    w = np.full((u.shape[0], width), 10, dtype=int)
    w[:, :64] = u
    for x, s in strips:
        w[:, x:x+8] = s
    w[0] = 0
    return w

def init_state(entry_grid):
    u = _make_underlay(entry_grid)
    world = _world_underlay(entry_grid)
    out = {"cam_x":0, "cam_y":0, "underlay":u.tolist(),
           "origin":u.tolist(), "world":world.tolist()}
    if CURRENT_LEVEL == 3:
        boxes = _slider_bboxes(np.asarray(entry_grid))
        if boxes:
            bx,by = boxes[0]
            loaded = bool(np.any(np.asarray(entry_grid)[by:by+6,bx:bx+6] == 14))
            # The paired lower slider starts four 6px steps down/right,
            # entirely outside the 64px viewport.
            out["l3_sliders"] = [(bx,by,loaded),(bx+24,by+24,False)]
    return out

def _camera_shift(g, action, state, tiles):
    """Pan the 88px world, preserving dynamic cells that leave the viewport."""
    cam = int(state.get("cam_x",0))
    under = np.array(state.get("underlay", _make_underlay(ENTRY_GRID)), dtype=int)
    world = np.array(state.get("world", _world_underlay(ENTRY_GRID)), dtype=int)
    can_right = action == 4 and _known_right_strip(cam + 8) is not None
    can_left = action == 3 and cam > 0
    if not (can_right or can_left):
        return g, under, cam, False, world
    new_cam = cam + (8 if can_right else -8)

    original = g.copy()
    base = original.copy()
    records = []
    for bx,by in _slider_bboxes(original):
        loaded = bool(np.any(original[by:by+6,bx:bx+6] == 14))
        records.append((bx + cam, by, loaded))
        _erase_slider(base,bx,by,_rail_dirs(original,bx,by),under,tiles)

    # Save the live slider-free window, then render the destination window.
    world[:,cam:cam+64] = base
    world[0] = 0
    full_under = _world_underlay(ENTRY_GRID)
    nu = full_under[:,new_cam:new_cam+64].copy()
    ng = world[:,new_cam:new_cam+64].copy()
    ng[0] = original[0]
    nu[0] = 0

    delta = 6 if action == 4 else -6
    for wx,by,loaded in records:
        tx = wx + delta
        valid = (tx >= 1 and tx+7 < world.shape[1] and
                 bool(np.all(world[by+2:by+4, tx+2:tx+4] == 5)))
        if valid:
            wx = tx
        nx = wx - new_cam
        _draw_slider(ng,nx,by,_rail_dirs(nu,nx,by),loaded)
    return ng, nu, new_cam, True, world

def _sync_world(world, g, cam, under, tiles, extra_sliders=None, cam_y=0):
    """Write the live viewport back to the dynamic world without slider sprites."""
    base = g.copy()
    original = g.copy()
    boxes = list(_slider_bboxes(original))
    for eb in _lock_slider_bboxes(original):
        if eb not in boxes:
            boxes.append(eb)
    if extra_sliders is not None:
        for rec in extra_sliders:
            eb = (int(rec[0]),int(rec[1]))
            if eb not in boxes:
                boxes.append(eb)
    for bx,by in boxes:
        _erase_slider_safe(base,bx,by,under,tiles)
    base[0] = 0
    world[cam_y:cam_y+64,cam:cam+64] = base
    world[0] = 0
    return world

def predict(state, grid, action, x=None, y=None):
    if state is None:
        state = init_state(ENTRY_GRID)
    g = np.array(grid, dtype=int, copy=True)
    under = np.array(state.get("underlay", _make_underlay(ENTRY_GRID)), dtype=int)
    origin = state.get("origin", under.tolist())
    cam = int(state.get("cam_x",0))
    cam_y = int(state.get("cam_y",0))
    world = np.array(state.get("world", _world_underlay(ENTRY_GRID)), dtype=int)
    l3_sliders = state.get("l3_sliders")
    l4_sliders = state.get("l4_sliders")
    l5_sliders = state.get("l5_sliders")
    tiles = _tiles_from(under)
    tile_set = set(tiles)

    if action == 0:
        ns = init_state(ENTRY_GRID)
        return (np.array(ENTRY_GRID, dtype=int, copy=True).tolist(),
                {"level_up":False, "dead":False, "win":False}, ns)

    _tick(g)

    if action in (1,2,3,4):
        if CURRENT_LEVEL == 3 and l3_sliders is not None:
            ui_meter = g[0].copy()
            old_cam = cam
            old_cam_y = cam_y
            old_records = [tuple(r) for r in l3_sliders]
            g, l3_sliders = _move_level3_sliders(
                g,action,under,tiles,l3_sliders,cam,cam_y)
            moved = any(tuple(a) != tuple(b)
                        for a,b in zip(old_records,l3_sliders))
            moved_loaded = any(
                (int(a[0]) != int(b[0]) or int(a[1]) != int(b[1]))
                and (bool(a[2]) or bool(b[2]))
                for a,b in zip(old_records,l3_sliders))
            # Once a later stage is entered, the camera follows each
            # slider step by six pixels on either axis, leaving the moving
            # sprites fixed on screen.
            delta_cam = (6 if action == 4 else
                         -6 if action == 3 else 0)
            delta_cam_y = (6 if action == 2 else
                           -6 if action == 1 else 0)
            new_cam = cam + delta_cam
            new_cam_y = cam_y + delta_cam_y
            min_cam = 30 if cam_y == 0 else 15
            min_cam_y = 0 if cam_y == 0 else 30
            if (moved_loaded and (delta_cam != 0 or delta_cam_y != 0) and
                    cam >= min_cam and new_cam >= min_cam and
                    new_cam + 64 <= world.shape[1] and
                    new_cam_y >= min_cam_y and
                    new_cam_y + 64 <= world.shape[0]):
                meter = ui_meter.copy()
                old_screen = [(r[0]-old_cam,r[1]-old_cam_y,r[2])
                              for r in l3_sliders]
                world = _sync_world(world,g,old_cam,under,tiles,
                                    old_screen,old_cam_y)
                cam = new_cam
                cam_y = new_cam_y
                full_under = _world_underlay(ENTRY_GRID)
                full_under = _apply_level3_dynamic_floor(full_under, l3_sliders)
                world = _apply_level3_dynamic_floor(world, l3_sliders)
                under = full_under[cam_y:cam_y+64,cam:cam+64].copy()
                g = world[cam_y:cam_y+64,cam:cam+64].copy()
                g[0] = meter
                under[0] = 0
                for bx,by,loaded in l3_sliders:
                    _draw_level3_record(g,under,bx,by,loaded,cam,cam_y)
            g[0] = ui_meter
        elif CURRENT_LEVEL == 5 and l5_sliders is not None:
            ui_meter=g[0].copy()
            old_cam=cam
            old_records=[tuple(r) for r in l5_sliders]
            full_under=_world_underlay(ENTRY_GRID)
            g,l5_sliders=_move_level5_sliders(
                g,action,under,tiles,l5_sliders,cam,full_under)
            moved_loaded=any(
                int(b[2]) in (8,14) and
                (int(a[0]) != int(b[0]) or int(a[1]) != int(b[1]))
                for a,b in zip(old_records,l5_sliders))
            delta_cam=(6 if action == 4 else -6 if action == 3 else 0)
            new_cam=cam+delta_cam
            # The first travelling stage tracks a loaded carrier, but the
            # second reveal is a terminal camera snap at x106: its full far
            # board stays fixed while carriers circulate inside that view.
            if (moved_loaded and cam < 106 and delta_cam != 0 and
                    new_cam >= 20 and new_cam+64 <= world.shape[1]):
                screen=[(r[0]-old_cam,r[1],r[2]) for r in l5_sliders]
                world=_sync_world(world,g,old_cam,under,tiles,screen)
                cam=new_cam
                under=full_under[:,cam:cam+64].copy()
                g=world[:,cam:cam+64].copy()
                under[0]=0
                base=g.copy()
                for bx,by,colour in l5_sliders:
                    sx=int(bx)-cam
                    dirs=_rail_dirs(under,sx,int(by))
                    _draw_normal_carrier_safe(
                        g,sx,int(by),dirs,int(colour),under)
                    _restore_level5_top_gap(g,base,sx,int(by))
                _restore_level5_pair_seams(g,l5_sliders,cam)
            g[0]=ui_meter
        elif CURRENT_LEVEL == 4 and l4_sliders is not None:
            ui_meter = g[0].copy()
            old_cam = cam
            old_records = [tuple(r) for r in l4_sliders]
            full_under = _world_underlay(ENTRY_GRID)
            g,l4_sliders = _move_level4_sliders(
                g,action,under,tiles,l4_sliders,cam,full_under)
            moved_loaded = any(
                not bool(b[3]) and bool(b[2]) and
                (int(a[0]) != int(b[0]) or int(a[1]) != int(b[1]))
                for a,b in zip(old_records,l4_sliders))
            delta_cam = 6 if action == 4 else -6 if action == 3 else 0
            new_cam = cam + delta_cam
            if (moved_loaded and delta_cam != 0 and new_cam >= 18 and
                    new_cam + 64 <= world.shape[1]):
                screen = [(r[0]-old_cam,r[1],r[2]) for r in l4_sliders]
                world = _sync_world(world,g,old_cam,under,tiles,screen)
                cam = new_cam
                under = full_under[:,cam:cam+64].copy()
                g = world[:,cam:cam+64].copy()
                under[0] = 0
                for bx,by,loaded,is_lock in l4_sliders:
                    sx = int(bx)-cam
                    dirs = _rail_dirs(under,sx,int(by))
                    if is_lock:
                        _draw_lock_slider_safe(g,sx,int(by),dirs)
                    else:
                        _draw_normal_carrier_safe(
                            g,sx,int(by),dirs,bool(loaded),under)
            g[0] = ui_meter
        else:
            g, under, cam, panned, world = _camera_shift(g,action,state,tiles)
            if not panned:
                _move_sliders(g,action,under,tiles)
        tiles = _tiles_from(under)
        tile_set = set(tiles)

    # Clicking the large colour-f retry icon (including its hollow centre)
    # restarts the peg position while retaining the visible action meter.
    retry = _retry_bounds(g)
    if action == 6 and retry is not None and x is not None and y is not None:
        x0,y0,x1,y1 = retry
        if x0-1 <= x <= x1+1 and y0-1 <= y <= y1+1:
            meter = g[0].copy()
            g = np.array(ENTRY_GRID, dtype=int, copy=True)
            g[0] = meter
            return g.tolist(), {"level_up":False, "dead":False, "win":False}, init_state(ENTRY_GRID)

    if action == 6:
        oldsel = _selected(g, tiles)
        clicked = _clicked_tile(x, y, tiles)
        if clicked is None and x is not None and y is not None:
            for bx, by in _slider_bboxes(g):
                if bx <= x < bx+6 and by <= y < by+6:
                    clicked = (bx+1,by+1)
                    break

        # Work out a move before erasing its visual guides.
        chosen = None
        if oldsel is not None and clicked is not None:
            for dst, mid in _moves(g, oldsel, tile_set):
                if dst == clicked:
                    chosen = (dst, mid)
                    break

        piece_colour = (_piece_colour(g, oldsel)
                        if chosen is not None and oldsel is not None else None)
        support_colour = (_piece_colour(g, chosen[1])
                          if chosen is not None else None)
        _clear_guides(g, tiles)

        if chosen is not None:
            dst, mid = chosen
            sx, sy = oldsel
            mx, my = mid
            dx, dy = dst
            # Ordinary disks consume the jumped disk.  The colour-8
            # mover is a non-capturing jumper: it relocates but leaves the
            # intervening support untouched.
            cleared = ((oldsel,) if 8 in (piece_colour, support_colour)
                       else (oldsel, mid))
            for p in cleared:
                px, py = p
                box = _slider_for_cell(g, p)
                if box is not None:
                    bx, by = box
                    g[by+1:by+5, bx+1:bx+5] = 12
                elif p in set(_lock_cells(g)):
                    # A lock is a permanent jump support: unlike a peg it is
                    # not consumed when a disk leaps over it.
                    pass
                else:
                    g[py:py+4, px:px+4] = 1
            # Draw the same coloured piece in either a regular landing
            # tile or a slider.  Ordinary disks are colour 14; level 5 also
            # contains a colour-8 jumper whose identity is preserved.
            pc = 14 if piece_colour is None else piece_colour
            box = _slider_for_cell(g, dst)
            if box is not None:
                bx, by = box
                g[by+1:by+5, bx+1:bx+5] = _piece_block(pc, 12)
            else:
                g[dy:dy+4, dx:dx+4] = _piece_block(pc, 1)
        elif clicked is not None and _has_peg(g,clicked):
            opts = _moves(g, clicked, tile_set)
            if opts:
                sx, sy = clicked
                pc = _piece_colour(g, clicked)
                if pc is None:
                    pc = 14
                source_box = _slider_for_cell(g, clicked)
                if source_box is not None:
                    bx, by = source_box
                    # Same rounded 6x6 selection surround, but the slider's
                    # four b-coloured face corners remain b rather than black.
                    g[by:by+6, bx:bx+6] = 3
                    g[by, bx] = g[by, bx+5] = 11
                    g[by+5, bx] = g[by+5, bx+5] = 11
                    g[by+1:by+5, bx+1:bx+5] = _piece_block(pc, 3)
                else:
                    # six-by-six selection surround; peg pixels stay colour 14.
                    g[sy-1:sy+5, sx-1:sx+5] = 3
                    # The four outer corners are not part of the rounded ring.
                    g[sy-1, sx-1] = 0
                    g[sy-1, sx+4] = 0
                    g[sy+4, sx-1] = 0
                    g[sy+4, sx+4] = 0
                    # The assignment above overwrote the piece; redraw it.
                    g[sy:sy+4, sx:sx+4] = _piece_block(pc, 3)
                for (dst, mid) in opts:
                    dx, dy = dst
                    dest_box = _slider_for_cell(g, dst)
                    if dest_box is not None:
                        bx, by = dest_box
                        g[by+1:by+5, bx+1:bx+5] = np.array([[12,2,2,12],
                                                             [2,12,12,2],
                                                             [2,12,12,2],
                                                             [12,2,2,12]])
                    else:
                        g[dy:dy+4, dx:dx+4] = np.array([[1,2,2,1],
                                                         [2,1,1,2],
                                                         [2,1,1,2],
                                                         [1,2,2,1]])

    # Keep carried-peg state for level-3 sliders even when they later
    # travel wholly outside the viewport.
    if l3_sliders is not None:
        refreshed = []
        for bx,by,loaded in l3_sliders:
            sx,sy = int(bx)-cam,int(by)-cam_y
            xa,xb = max(0,sx),min(g.shape[1],sx+6)
            ya,yb = max(0,sy),min(g.shape[0],sy+6)
            if xa < xb and ya < yb and np.any(
                    np.isin(g[ya:yb,xa:xb],[11,12,14])):
                loaded = bool(np.any(g[ya:yb,xa:xb] == 14))
            refreshed.append((int(bx),int(by),bool(loaded)))
        l3_sliders = refreshed

    if l4_sliders is not None:
        refreshed=[]
        for bx,by,loaded,is_lock in l4_sliders:
            if not is_lock:
                sx=int(bx)-cam
                xa,xb=max(0,sx),min(g.shape[1],sx+6)
                ya,yb=max(0,int(by)),min(g.shape[0],int(by)+6)
                if xa < xb and ya < yb and np.any(
                        np.isin(g[ya:yb,xa:xb],[11,12,14])):
                    loaded=bool(np.any(g[ya:yb,xa:xb]==14))
            refreshed.append((int(bx),int(by),bool(loaded),bool(is_lock)))
        l4_sliders=refreshed

    if l5_sliders is not None:
        refreshed=[]
        for bx,by,colour in l5_sliders:
            sx=int(bx)-cam
            xa,xb=max(0,sx),min(g.shape[1],sx+6)
            ya,yb=max(0,int(by)),min(g.shape[0],int(by)+6)
            if xa < xb and ya < yb:
                face=g[ya:yb,xa:xb]
                if np.any(face == 8):
                    colour=8
                elif np.any(face == 14):
                    colour=14
                elif np.any(np.isin(face,[11,12])):
                    colour=0
            refreshed.append((int(bx),int(by),int(colour)))
        l5_sliders=refreshed

    screen_sliders = ([(r[0]-cam,r[1]-cam_y,r[2]) for r in l3_sliders]
                      if l3_sliders is not None else
                      [(r[0]-cam,r[1],r[2]) for r in l4_sliders]
                      if l4_sliders is not None else
                      [(r[0]-cam,r[1],r[2]) for r in l5_sliders]
                      if l5_sliders is not None else None)
    world = _sync_world(world, g, cam, under, tiles, screen_sliders, cam_y)

    # Loading the first member of level 5's paired carrier snaps the
    # viewport twenty pixels right.  Both adjacent faces keep world
    # coordinates; the newly exposed strip is a continuation of their rail.
    if CURRENT_LEVEL == 5 and cam == 0 and l5_sliders is None:
        records=[]
        for bx,by in _slider_bboxes(g):
            face=g[by:by+6,bx:bx+6]
            colour=(8 if np.any(face == 8) else
                    14 if np.any(face == 14) else 0)
            records.append((int(bx),int(by),int(colour)))
        if any(r[2] == 14 for r in records):
            meter=g[0].copy()
            old_screen=g.copy()
            l5_sliders=records
            cam=20
            full_under=_world_underlay(ENTRY_GRID)
            under=full_under[:,cam:cam+64].copy()
            g=np.concatenate((old_screen[:,cam:64],
                              full_under[:,64:84]),axis=1)
            g[0]=meter
            under[0]=0
            tiles=_tiles_from(under)
            tile_set=set(tiles)

    # Delivering the first far-row e disk across the colour-8 bridge opens
    # level 5's second stage.  The camera snaps to world x106 and reveals a
    # third empty carrier below the next fixed lock.
    if (CURRENT_LEVEL == 5 and cam == 62 and l5_sliders is not None and
            _piece_colour(g,(52,18)) == 14 and
            _piece_colour(g,(46,18)) == 8):
        meter=g[0].copy()
        l5_sliders=list(l5_sliders)
        if not any(int(r[0]) == 143 and int(r[1]) == 29
                   for r in l5_sliders):
            l5_sliders.append((143,29,0))
        full_under=_world_underlay(ENTRY_GRID)
        if world.shape[1] < full_under.shape[1]:
            expanded=full_under.copy()
            expanded[:world.shape[0],:world.shape[1]]=world
            world=expanded
        cam=106
        under=full_under[:,cam:cam+64].copy()
        g=world[:,cam:cam+64].copy()
        under[0]=0
        base=g.copy()
        for bx,by,colour in l5_sliders:
            sx=int(bx)-cam
            dirs=_rail_dirs(under,sx,int(by))
            _draw_normal_carrier_safe(g,sx,int(by),dirs,int(colour),under)
            _restore_level5_top_gap(g,base,sx,int(by))
        _restore_level5_pair_seams(g,l5_sliders,cam)
        g[0]=meter
        tiles=_tiles_from(under)
        tile_set=set(tiles)

    # Loading the upper level-3 slider advances the viewport to the next
    # 30-pixel-wide stage while both sliders keep their world coordinates.
    if (CURRENT_LEVEL == 3 and cam == 0 and l3_sliders is not None
            and bool(l3_sliders[0][2])):
        meter = g[0].copy()
        cam = 30
        full_under = _world_underlay(ENTRY_GRID)
        under = full_under[cam_y:cam_y+64,cam:cam+64].copy()
        g = world[cam_y:cam_y+64,cam:cam+64].copy()
        g[0] = meter
        under[0] = 0
        for bx,by,loaded in l3_sliders:
            _draw_level3_record(g,under,bx,by,loaded,cam,cam_y)
        tiles = _tiles_from(under)
        tile_set = set(tiles)

    # Loading the lower slider advances to the vertically offset third stage.
    if (CURRENT_LEVEL == 3 and cam_y == 0 and l3_sliders is not None
            and bool(l3_sliders[1][2])):
        meter = g[0].copy()
        cam,cam_y = 39,30
        if len(l3_sliders) == 2:
            l3_sliders = list(l3_sliders) + [(59,71,False)]
        full_under = _world_underlay(ENTRY_GRID)
        under = full_under[cam_y:cam_y+64,cam:cam+64].copy()
        g = world[cam_y:cam_y+64,cam:cam+64].copy()
        under[0] = 0
        for bx,by,loaded in l3_sliders:
            _draw_level3_record(g,under,bx,by,loaded,cam,cam_y)
        g[0] = meter
        tiles = _tiles_from(under)
        tile_set = set(tiles)

    # Level 4 likewise continues beyond the apparent one-disk state.  Loading
    # its normal carrier reveals world columns 64..81 and snaps 18px right;
    # the normal and lock-bearing carriers retain world coordinates.
    if CURRENT_LEVEL == 4 and cam == 0 and l4_sliders is None:
        normals = []
        for bx,by in _slider_bboxes(g):
            loaded = bool(np.any(g[by:by+6,bx:bx+6] == 14))
            normals.append((bx,by,loaded,False))
        if any(r[2] for r in normals):
            locks = [(bx,by,False,True) for bx,by in _lock_slider_bboxes(g)]
            l4_sliders = normals + locks
            meter = g[0].copy()
            cam = 18
            full_under = _world_underlay(ENTRY_GRID)
            under = full_under[:,cam:cam+64].copy()
            g = world[:,cam:cam+64].copy()
            under[0] = 0
            g[0] = meter
            for bx,by,loaded,is_lock in l4_sliders:
                sx = int(bx)-cam
                dirs = _rail_dirs(under,sx,int(by))
                if is_lock:
                    _draw_lock_slider_safe(g,sx,int(by),dirs)
                else:
                    _draw_slider_safe(g,sx,int(by),dirs,bool(loaded))
            tiles = _tiles_from(under)
            tile_set = set(tiles)

    # Completing level 4's first far-board transfer reveals a still larger
    # overlapping stage.  The landed disk remains at world cell (78,24);
    # the camera jumps to x=69 and a new movable lock carrier appears on the
    # far-right vertical rail.
    if (CURRENT_LEVEL == 4 and cam == 36 and l4_sliders is not None
            and not any(bool(r[2]) for r in l4_sliders if not bool(r[3]))
            and _has_peg(g,(42,24))):
        meter = g[0].copy()
        l4_sliders = list(l4_sliders)
        if not any(bool(r[3]) and int(r[0]) == 125 and int(r[1]) == 17
                   for r in l4_sliders):
            l4_sliders.append((125,17,False,True))
        cam = 69
        full_under = _world_underlay(ENTRY_GRID)
        under = full_under[:,cam:cam+64].copy()
        g = world[:,cam:cam+64].copy()
        under[0] = 0
        g[0] = meter
        for bx,by,loaded,is_lock in l4_sliders:
            sx = int(bx)-cam
            dirs = _rail_dirs(under,sx,int(by))
            if is_lock:
                _draw_lock_slider_safe(g,sx,int(by),dirs)
            else:
                _draw_normal_carrier_safe(
                    g,sx,int(by),dirs,bool(loaded),under)
        tiles = _tiles_from(under)
        tile_set = set(tiles)

    next_state = {"cam_x":cam, "cam_y":cam_y,
                  "underlay":under.tolist(), "origin":origin,
                  "world":world.tolist()}
    if l3_sliders is not None:
        next_state["l3_sliders"] = [tuple(r) for r in l3_sliders]
    if l4_sliders is not None:
        next_state["l4_sliders"] = [tuple(r) for r in l4_sliders]
    if l5_sliders is not None:
        next_state["l5_sliders"] = [tuple(r) for r in l5_sliders]

    if l3_sliders is not None:
        slider_pegs = sum(bool(r[2]) for r in l3_sliders)
    elif l4_sliders is not None:
        slider_pegs = sum(bool(r[2]) for r in l4_sliders if not bool(r[3]))
    else:
        slider_pegs = sum(_cell_has_peg(g,sp,tile_set)
                          for sp in _slider_cells(g))
    full_tiles = _tiles_from(_world_underlay(ENTRY_GRID))
    if CURRENT_LEVEL == 5:
        # Colour8 is a reusable, indestructible bridge tool rather than a
        # goal peg.  Completion counts only ordinary e disks, including any
        # one currently carried by a rail face.
        total_pegs = sum(bool(np.any(world[py:py+4,px:px+4] == 14))
                         for px,py in full_tiles)
        if l5_sliders is not None:
            total_pegs += sum(int(r[2]) == 14 for r in l5_sliders)
    else:
        total_pegs = _peg_count(world, full_tiles) + slider_pegs
    if total_pegs == 1:
        level_up = True
    elif (_solved(world, full_tiles) and _has_lock() and slider_pegs == 0
          and not _lock_slider_bboxes(g)):
        # More than one isolated survivor and no movable carrier: dead-end UI.
        _enter_key_phase(g, tiles)
        level_up = False
    else:
        level_up = False
    win = bool(level_up and CURRENT_LEVEL is not None and CURRENT_LEVEL >= 9)
    return g.tolist(), {"level_up":bool(level_up), "dead":False, "win":win}, next_state

def is_goal(state, grid):
    g = np.asarray(grid)
    if state is None:
        state = init_state(ENTRY_GRID)
    under = np.asarray(state.get("underlay", _make_underlay(ENTRY_GRID)))
    world = np.asarray(state.get("world", _world_underlay(ENTRY_GRID)))
    tiles = _tiles_from(under)
    full_tiles = _tiles_from(_world_underlay(ENTRY_GRID))
    l3 = state.get("l3_sliders")
    l4 = state.get("l4_sliders")
    l5 = state.get("l5_sliders")
    if CURRENT_LEVEL == 5:
        ordinary = sum(bool(np.any(world[py:py+4,px:px+4] == 14))
                       for px,py in full_tiles)
        if l5 is not None:
            ordinary += sum(int(r[2]) == 14 for r in l5)
        return ordinary == 1
    carried = (sum(bool(r[2]) for r in l3) if l3 is not None else
               sum(bool(r[2]) for r in l4 if not bool(r[3])) if l4 is not None else
               sum(_cell_has_peg(g,sp,set(tiles)) for sp in _slider_cells(g)))
    return _peg_count(world, full_tiles) + carried == 1
