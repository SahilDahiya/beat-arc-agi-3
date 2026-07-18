# World model for the peg-jumping board game.
# numpy is preloaded by the ARC3 sandbox as np.

def _tiles_from(e):
    """Return playable 4x4 tile top-lefts from a slider-free static view."""
    e = np.asarray(e)

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

def _tiles():
    return _tiles_from(np.asarray(ENTRY_GRID))

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
    # Backward-compatible convenience for one-slider levels.
    cells = _slider_cells(g)
    return cells[0] if cells else None

def _cell_has_peg(g, p, regular_set):
    box = _slider_for_cell(g, p)
    if box is not None:
        bx, by = box
        return bool(np.any(g[by:by+6, bx:bx+6] == 14))
    return p in regular_set and _has_peg(g, p)

def _moves(g, src, tile_set):
    cells = set(tile_set)
    cells.update(_slider_cells(g))
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

def _slider_bboxes(g):
    # A slider face is always 6x6 and retains b-coloured (11) corners,
    # whether empty, carrying a peg, marked as a destination, or selected.
    out = []
    h, w = g.shape
    allowed = np.array([2,3,11,12,14])
    for by in range(h-5):
        for bx in range(w-5):
            if not (g[by,bx] == 11 and g[by,bx+5] == 11 and
                    g[by+5,bx] == 11 and g[by+5,bx+5] == 11):
                continue
            if np.all(np.isin(g[by:by+6, bx:bx+6], allowed)):
                out.append((bx,by))
    return out

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
    if bx-2 >= 0 and np.any(g[by+2:by+4, bx-2] == 5):
        ans.add("L")
    if bx+8 < w and np.any(g[by+2:by+4, bx+8] == 5):
        ans.add("R")
    if by-2 >= 0 and np.any(g[by-2, bx+2:bx+4] == 5):
        ans.add("U")
    if by+8 < h and np.any(g[by+8, bx+2:bx+4] == 5):
        ans.add("D")
    return ans

def _erase_slider(g, bx, by, dirs, underlay=None, tiles=None):
    # At a board dock the slider temporarily covered part of the board's
    # fixed rim.  Restore that rim from ENTRY_GRID, but keep every live tile
    # block (whose peg contents may differ from entry).
    dock_l = (bx-2 >= 0 and
              np.any(np.isin(g[by-1:by+8, bx-2], [1,2,14])))
    dock_r = (bx+7 < g.shape[1] and
              np.any(np.isin(g[by-1:by+8, bx+7], [1,2,14])))
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
              np.any(np.isin(g[by-1:by+8, bx+7], [1,2,14])))
    dock_l = (bx-2 >= 0 and
              np.any(np.isin(g[by-1:by+8, bx-2], [1,2,14])))
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
        g[by+6, bx+6] = keep_r_corner
        # A rail crossing under the dock cuts through the lower shadow;
        # otherwise the slider's shadow remains visible over background.
        if keep_r_bottom == 5:
            g[by+7, bx+5] = keep_r_bottom
    if dock_l:
        g[by-1:by+7, bx-1] = keep_l
        g[by+7, bx] = keep_bl

def _move_sliders(g, action, underlay=None, tiles=None):
    boxes = _slider_bboxes(g)
    delta = {1:(0,-6), 2:(0,6), 3:(-6,0), 4:(6,0)}.get(action)
    if not boxes or delta is None:
        return
    original = g.copy()
    records = []
    base = g.copy()
    # All sliders receive the arrow simultaneously, so reveal all rails
    # before deciding/drawing any destination.
    for bx, by in boxes:
        loaded = bool(np.any(original[by:by+6, bx:bx+6] == 14))
        dirs = _rail_dirs(original, bx, by)
        records.append((bx,by,loaded))
        _erase_slider(base, bx, by, dirs, underlay, tiles)

    moves = []
    occupied = set()
    for bx, by, loaded in records:
        nx, ny = bx + delta[0], by + delta[1]
        valid = (nx >= 1 and ny >= 1 and nx+7 < g.shape[1] and ny+7 < g.shape[0])
        if valid:
            centre = base[ny+2:ny+4, nx+2:nx+4]
            valid = bool(np.all(centre == 5))
        if valid and (nx,ny) not in occupied:
            occupied.add((nx,ny))
            moves.append((nx,ny,loaded,True,bx,by))
        else:
            moves.append((bx,by,loaded,False,bx,by))

    g[:] = base
    for nx, ny, loaded, moved, ox, oy in moves:
        if moved:
            _draw_slider(g, nx, ny, _rail_dirs(base,nx,ny), loaded)
        else:
            # A blocked slider is visually unchanged.
            g[oy-1:oy+8, ox-1:ox+8] = original[oy-1:oy+8, ox-1:ox+8]

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

def _make_underlay(entry):
    u = np.array(entry, dtype=int, copy=True)
    original = u.copy()
    tiles = _tiles_from(original)
    for bx,by in _slider_bboxes(original):
        _erase_slider(u,bx,by,_rail_dirs(original,bx,by),None,tiles)
    u[0] = 0
    return u

def _world_underlay(entry_grid):
    """Known slider-free world canvas (the level-2 world is 88px wide)."""
    u = _make_underlay(entry_grid)
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
    return {"cam_x":0, "underlay":u.tolist(), "origin":u.tolist(),
            "world":world.tolist()}

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

def _sync_world(world, g, cam, under, tiles):
    """Write the live viewport back to the dynamic world without slider sprites."""
    base = g.copy()
    original = g.copy()
    for bx,by in _slider_bboxes(original):
        _erase_slider(base,bx,by,_rail_dirs(original,bx,by),under,tiles)
    base[0] = 0
    world[:,cam:cam+64] = base
    world[0] = 0
    return world

def predict(state, grid, action, x=None, y=None):
    if state is None:
        state = init_state(ENTRY_GRID)
    g = np.array(grid, dtype=int, copy=True)
    under = np.array(state.get("underlay", _make_underlay(ENTRY_GRID)), dtype=int)
    origin = state.get("origin", under.tolist())
    cam = int(state.get("cam_x",0))
    world = np.array(state.get("world", _world_underlay(ENTRY_GRID)), dtype=int)
    tiles = _tiles_from(under)
    tile_set = set(tiles)

    if action == 0:
        ns = init_state(ENTRY_GRID)
        return (np.array(ENTRY_GRID, dtype=int, copy=True).tolist(),
                {"level_up":False, "dead":False, "win":False}, ns)

    _tick(g)

    if action in (1,2,3,4):
        g, under, cam, panned, world = _camera_shift(g,action,state,tiles)
        if not panned:
            _move_sliders(g,action,under,tiles)
        tiles = _tiles_from(under)
        tile_set = set(tiles)

    # Clicking the large colour-f retry icon (including its hollow centre)
    # restarts the peg position while retaining the visible action meter.
    if action == 6 and np.any(g == 15) and x is not None and y is not None:
        fy, fx = np.where(g == 15)
        if int(fx.min())-1 <= x <= int(fx.max())+1 and int(fy.min())-1 <= y <= int(fy.max())+1:
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

        _clear_guides(g, tiles)

        if chosen is not None:
            dst, mid = chosen
            sx, sy = oldsel
            mx, my = mid
            dx, dy = dst
            # Empty source and jumped tile (the source may itself be the slider).
            for p in (oldsel, mid):
                px, py = p
                box = _slider_for_cell(g, p)
                if box is not None:
                    bx, by = box
                    g[by+1:by+5, bx+1:bx+5] = 12
                else:
                    g[py:py+4, px:px+4] = 1
            # Draw the disk in either a regular landing tile or a slider.
            box = _slider_for_cell(g, dst)
            if box is not None:
                bx, by = box
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
                source_box = _slider_for_cell(g, clicked)
                if source_box is not None:
                    bx, by = source_box
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

    world = _sync_world(world, g, cam, under, tiles)
    next_state = {"cam_x":cam, "underlay":under.tolist(), "origin":origin,
                  "world":world.tolist()}

    slider_pegs = sum(_cell_has_peg(g, sp, tile_set) for sp in _slider_cells(g))
    full_tiles = _tiles_from(_world_underlay(ENTRY_GRID))
    total_pegs = _peg_count(world, full_tiles) + slider_pegs
    if total_pegs == 1:
        level_up = True
    elif _solved(world, full_tiles) and _has_lock() and slider_pegs == 0:
        # More than one isolated survivor and no transport peg: dead-end UI.
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
    return (_peg_count(world, full_tiles) +
            sum(_cell_has_peg(g, sp, set(tiles))
                for sp in _slider_cells(g))) == 1
