# World model for the peg-jumping board game.
# numpy is preloaded by the ARC3 sandbox as np.

def _tiles():
    """Return playable 4x4 tile top-lefts, derived from this level's entry board."""
    e = np.asarray(ENTRY_GRID)
    m = (e == 1) | (e == 14)
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
    return out

def _has_peg(g, p):
    x, y = p
    return bool(np.any(g[y:y+4, x:x+4] == 14))

def _selected(g, tiles):
    # A selected peg has a colour-3 ring around its 4x4 tile.
    h, w = g.shape
    for x, y in tiles:
        ya, yb = max(0, y-1), min(h, y+5)
        xa, xb = max(0, x-1), min(w, x+5)
        if np.any(g[ya:yb, xa:xb] == 3):
            return (x, y)
    # The loaded slider is itself a selectable logical cell.
    pos = _slider_bbox(g)
    if pos is not None:
        bx, by = pos
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
    pos = _slider_bbox(g)
    if pos is not None:
        bx, by = pos
        face = g[by:by+6, bx:bx+6]
        loaded = bool(np.any(face == 14))
        # Rebuild the face to erase either a destination-2 motif or a
        # source-selection 3 surround.
        face[:] = np.array([[11,11,11,11,11,11],
                            [11,12,12,12,12,11],
                            [11,12,12,12,12,11],
                            [11,12,12,12,12,11],
                            [11,12,12,12,12,11],
                            [11,11,11,11,11,11]])
        if loaded:
            face[1:5,1:5] = np.array([[12,14,14,12],
                                      [14,14,14,14],
                                      [14,14,14,14],
                                      [12,14,14,12]])

def _slider_cell(g):
    pos = _slider_bbox(g)
    if pos is None:
        return None
    bx, by = pos
    # Express the 6x6 face on the same coordinate lattice as a 4x4 board
    # tile: both then have centre (x+1.5,y+1.5).
    return (bx+1, by+1)

def _cell_has_peg(g, p, regular_set):
    sp = _slider_cell(g)
    if sp is not None and p == sp:
        bx, by = sp[0]-1, sp[1]-1
        return bool(np.any(g[by:by+6, bx:bx+6] == 14))
    return p in regular_set and _has_peg(g, p)

def _moves(g, src, tile_set):
    cells = set(tile_set)
    sp = _slider_cell(g)
    if sp is not None:
        cells.add(sp)
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
    # Row zero is the visible move-use meter: one new cell per action.
    z = np.where(g[0] == 0)[0]
    if len(z):
        g[0, int(z[0])] = 1

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

def _slider_bbox(g):
    yy, xx = np.where((g == 11) | (g == 12))
    if not len(xx):
        return None
    return (int(xx.min()), int(yy.min()))  # top-left of the 6x6 b/c face

def _rail_dirs(g, bx, by):
    h, w = g.shape
    ans = set()
    if bx-2 >= 0 and np.any(g[by+2:by+4, bx-2] == 5):
        ans.add("L")
    if bx+8 < w and np.any(g[by+2:by+4, bx+8] == 5):
        ans.add("R")
    if by-2 >= 0 and np.any(g[by-2, bx+2:bx+4] == 5):
        ans.add("U")
    if by+8 < h and np.any(g[by+8, bx+2:bx+4] == 5):
        ans.add("D")
    return ans

def _erase_slider(g, bx, by, dirs):
    # At a board dock the slider temporarily covered part of the board's
    # fixed rim.  Restore that rim from ENTRY_GRID, but keep every live tile
    # block (whose peg contents may differ from entry).
    dock_l = (bx-2 >= 0 and
              np.any(np.isin(g[by-1:by+8, bx-2], [1,2,14])))
    dock_r = (bx+7 < g.shape[1] and
              np.any(np.isin(g[by-1:by+8, bx+7], [1,2,14])))
    if dock_l or dock_r:
        old = g.copy()
        g[by-1:by+8, bx-1:bx+8] = np.asarray(ENTRY_GRID)[by-1:by+8, bx-1:bx+8]
        for tx, ty in _tiles():
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
              np.any(np.isin(g[by-1:by+8, bx+7], [1,2,14])))
    dock_l = (bx-2 >= 0 and
              np.any(np.isin(g[by-1:by+8, bx-2], [1,2,14])))
    keep_r = g[by-1:by+8, bx+6:bx+8].copy() if dock_r else None
    keep_l = g[by-1:by+7, bx-1].copy() if dock_l else None
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
        g[by+1:by+5, bx+1:bx+5] = np.array([[12,14,14,12],
                                             [14,14,14,14],
                                             [14,14,14,14],
                                             [12,14,14,12]])
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
    if dock_l:
        g[by-1:by+7, bx-1] = keep_l
        g[by+7, bx] = 5

def _move_slider(g, action):
    pos = _slider_bbox(g)
    if pos is None:
        return
    bx, by = pos
    loaded = bool(np.any(g[by:by+6, bx:bx+6] == 14))
    delta = {1:(0,-6), 2:(0,6), 3:(-6,0), 4:(6,0)}.get(action)
    if delta is None:
        return
    olddirs = _rail_dirs(g, bx, by)
    # Reveal the substrate first; adjacent 6-pixel moves overlap the old face.
    base = g.copy()
    _erase_slider(base, bx, by, olddirs)
    nx, ny = bx + delta[0], by + delta[1]
    if nx < 1 or ny < 1 or nx+7 >= g.shape[1] or ny+7 >= g.shape[0]:
        return
    # The slider stays on its two-pixel rail and docks BESIDE boards; it
    # cannot enter a playable board tile.
    centre = base[ny+2:ny+4, nx+2:nx+4]
    if not np.all(np.isin(centre, [5,11,12])):
        return
    newdirs = _rail_dirs(base, nx, ny)
    g[:] = base
    _draw_slider(g, nx, ny, newdirs, loaded)

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

def step(grid, action, x=None, y=None):
    g = np.array(grid, dtype=int, copy=True)
    tiles = _tiles()
    tile_set = set(tiles)

    if action == 0:
        return np.array(ENTRY_GRID, dtype=int, copy=True).tolist(), {"level_up":False, "dead":False, "win":False}

    _tick(g)

    if action in (1,2,3,4):
        _move_slider(g, action)

    # Clicking the large colour-f retry icon (including its hollow centre)
    # restarts the peg position while retaining the visible action meter.
    if action == 6 and np.any(g == 15) and x is not None and y is not None:
        fy, fx = np.where(g == 15)
        if int(fx.min())-1 <= x <= int(fx.max())+1 and int(fy.min())-1 <= y <= int(fy.max())+1:
            meter = g[0].copy()
            g = np.array(ENTRY_GRID, dtype=int, copy=True)
            g[0] = meter
            return g.tolist(), {"level_up":False, "dead":False, "win":False}

    if action == 6:
        oldsel = _selected(g, tiles)
        clicked = _clicked_tile(x, y, tiles)
        sp = _slider_cell(g)
        if clicked is None and sp is not None and x is not None and y is not None:
            bx, by = sp[0]-1, sp[1]-1
            if bx <= x < bx+6 and by <= y < by+6:
                clicked = sp

        # Work out a move before erasing its visual guides.
        chosen = None
        if oldsel is not None and clicked is not None:
            for dst, mid in _moves(g, oldsel, tile_set):
                if dst == clicked:
                    chosen = (dst, mid)
                    break

        _clear_guides(g, tiles)

        if chosen is not None:
            dst, mid = chosen
            sx, sy = oldsel
            mx, my = mid
            dx, dy = dst
            # Empty source and jumped tile (the source may itself be the slider).
            for p in (oldsel, mid):
                px, py = p
                if sp is not None and p == sp:
                    bx, by = sp[0]-1, sp[1]-1
                    g[by+1:by+5, bx+1:bx+5] = 12
                else:
                    g[py:py+4, px:px+4] = 1
            # Draw the disk in either a regular landing tile or the slider.
            if sp is not None and dst == sp:
                bx, by = sp[0]-1, sp[1]-1
                g[by+1:by+5, bx+1:bx+5] = np.array([[12,14,14,12],
                                                     [14,14,14,14],
                                                     [14,14,14,14],
                                                     [12,14,14,12]])
            else:
                g[dy:dy+4, dx:dx+4] = np.array([[1,14,14,1],
                                                 [14,14,14,14],
                                                 [14,14,14,14],
                                                 [1,14,14,1]])
        elif clicked is not None and _cell_has_peg(g, clicked, tile_set):
            opts = _moves(g, clicked, tile_set)
            if opts:
                sx, sy = clicked
                if sp is not None and clicked == sp:
                    bx, by = sp[0]-1, sp[1]-1
                    # Same rounded 6x6 selection surround, but the slider's
                    # four b-coloured face corners remain b rather than black.
                    g[by:by+6, bx:bx+6] = 3
                    g[by, bx] = g[by, bx+5] = 11
                    g[by+5, bx] = g[by+5, bx+5] = 11
                    g[by+1:by+5, bx+1:bx+5] = np.array([[3,14,14,3],
                                                         [14,14,14,14],
                                                         [14,14,14,14],
                                                         [3,14,14,3]])
                else:
                    # six-by-six selection surround; peg pixels stay colour 14.
                    g[sy-1:sy+5, sx-1:sx+5] = 3
                    # The four outer corners are not part of the rounded ring.
                    g[sy-1, sx-1] = 0
                    g[sy-1, sx+4] = 0
                    g[sy+4, sx-1] = 0
                    g[sy+4, sx+4] = 0
                    # The assignment above overwrote the peg; redraw it.
                    g[sy:sy+4, sx:sx+4] = np.array([[3,14,14,3],
                                                     [14,14,14,14],
                                                     [14,14,14,14],
                                                     [3,14,14,3]])
                for (dst, mid) in opts:
                    dx, dy = dst
                    if sp is not None and dst == sp:
                        bx, by = sp[0]-1, sp[1]-1
                        g[by+1:by+5, bx+1:bx+5] = np.array([[12,2,2,12],
                                                             [2,12,12,2],
                                                             [2,12,12,2],
                                                             [12,2,2,12]])
                    else:
                        g[dy:dy+4, dx:dx+4] = np.array([[1,2,2,1],
                                                         [2,1,1,2],
                                                         [2,1,1,2],
                                                         [1,2,2,1]])

    sp = _slider_cell(g)
    slider_peg = bool(sp is not None and _cell_has_peg(g, sp, tile_set))
    total_pegs = _peg_count(g, tiles) + int(slider_peg)
    if total_pegs == 1:
        level_up = True
    elif _solved(g, tiles) and _has_lock() and not slider_peg:
        # More than one isolated survivor and no transport peg: dead-end UI.
        _enter_key_phase(g, tiles)
        level_up = False
    else:
        level_up = False
    win = bool(level_up and CURRENT_LEVEL is not None and CURRENT_LEVEL >= 9)
    return g.tolist(), {"level_up":bool(level_up), "dead":False, "win":win}

def is_goal(grid):
    g = np.asarray(grid)
    tiles = _tiles()
    ts = set(tiles)
    sp = _slider_cell(g)
    return _peg_count(g, tiles) + int(sp is not None and _cell_has_peg(g, sp, ts)) == 1
