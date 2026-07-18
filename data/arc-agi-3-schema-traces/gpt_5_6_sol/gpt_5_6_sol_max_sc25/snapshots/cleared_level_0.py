"""World model for ARC3 game sc25.

The upper small 4x4 colour-{9,10} component is a movable patterned marker on
colour-2 floor. Successful horizontal moves normally spend the next two rows
of the colour-14 edge meter. Crossing the central free edge (between the middle
slot and the slot immediately right of it) is free in either direction.
Rotating in place and blocked-left are free; a blocked action 4 at the right
endpoint still spends a band.

Confirmed:
* The first input after entry/RESET is a universal wake-up no-op. Thereafter
  action 1/2 set the two absolute vertical orientations. Establishing vertical
  from horizontal is free; flipping vertical polarity spends.
* action 3 moves it 4 cells left over colour 2 and sets ENTRY's marker pattern.
* action 4 moves it 4 cells right and sets the left-right flipped ENTRY pattern.
* clicking a large-board cell toggles it: inactive→14 normally costs a band.
  With marker size4 the observed middle-right cell is free; after shrink to
  size2 the observed top-middle cell is free. 14→ENTRY colour is free.
* when active cells exactly match the colour-15 stencil, they auto-paint with
  the stencil's base colour, the patterned marker shrinks 4→2, and a bonus
  meter band is spent. A second firing expands 2→4 shifted two cells left,
  so shrink/expand is a crawl cycle rather than a terminal.
"""

def _small_marker(a):
    h, w = a.shape
    mask = (a == 9) | (a == 10)
    seen = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = 1
            pts = []
            while stack:
                yy, xx = stack.pop()
                pts.append((yy, xx))
                for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny, nx = yy+dy, xx+dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = 1
                        stack.append((ny,nx))
            ys = [p[0] for p in pts]
            xs = [p[1] for p in pts]
            y0, y1, x0, x1 = min(ys), max(ys)+1, min(xs), max(xs)+1
            side = y1-y0
            if side == x1-x0 and side in (2, 4) and len(pts) == side*side:
                return y0, y1, x0, x1
    return None

def _entry_marker_pattern():
    e = np.array(ENTRY_GRID, dtype=int)
    box = _small_marker(e)
    if box is None:
        return None
    y0, y1, x0, x1 = box
    return e[y0:y1, x0:x1].copy()

def _marker_pattern_for_side(base, side):
    """Scale ENTRY's square marker motif down to the currently active side."""
    if base is None or side <= 0:
        return None
    if base.shape[0] == side:
        return base.copy()
    stride = max(1, base.shape[0] // side)
    return base[::stride, ::stride][:side, :side].copy()

def _large_green_board_box():
    """BBox of the largest connected colour-3 component in ENTRY_GRID."""
    e = np.array(ENTRY_GRID, dtype=int)
    h, w = e.shape
    mask = (e == 3)
    seen = np.zeros((h, w), dtype=np.uint8)
    best = None
    for y in range(h):
        for x in range(w):
            if not mask[y,x] or seen[y,x]:
                continue
            stack = [(y,x)]
            seen[y,x] = 1
            pts = []
            while stack:
                yy, xx = stack.pop()
                pts.append((yy,xx))
                for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny, nx = yy+dy, xx+dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = 1
                        stack.append((ny,nx))
            if best is None or len(pts) > best[0]:
                ys = [p[0] for p in pts]
                xs = [p[1] for p in pts]
                best = (len(pts), min(ys), max(ys)+1, min(xs), max(xs)+1)
    return None if best is None else best[1:]

def _clicked_board_cell(a, x, y):
    """Return interior cell bbox containing a click on the large green grid."""
    if x is None or y is None:
        return None
    box = _large_green_board_box()
    if box is None:
        return None
    yb0, yb1, xb0, xb1 = box
    x, y = int(x), int(y)
    if not (xb0 < x < xb1-1 and yb0 < y < yb1-1) or a[y,x] == 3:
        return None
    x0 = x
    while x0 > xb0 and a[y,x0-1] != 3:
        x0 -= 1
    x1 = x+1
    while x1 < xb1 and a[y,x1] != 3:
        x1 += 1
    y0 = y
    while y0 > yb0 and a[y0-1,x] != 3:
        y0 -= 1
    y1 = y+1
    while y1 < yb1 and a[y1,x] != 3:
        y1 += 1
    return y0, y1, x0, x1

def _board_cells():
    """Nine interior bboxes of the large green board, row-major."""
    e = np.array(ENTRY_GRID, dtype=int)
    box = _large_green_board_box()
    if box is None:
        return []
    yb0, yb1, xb0, xb1 = box
    cells = []
    seen = np.zeros(e.shape, dtype=np.uint8)
    for y in range(yb0+1, yb1-1):
        for x in range(xb0+1, xb1-1):
            if e[y,x] == 3 or seen[y,x]:
                continue
            stack = [(y,x)]
            seen[y,x] = 1
            pts = []
            while stack:
                yy, xx = stack.pop()
                pts.append((yy,xx))
                for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny, nx = yy+dy, xx+dx
                    if yb0 < ny < yb1-1 and xb0 < nx < xb1-1 and e[ny,nx] != 3 and not seen[ny,nx]:
                        seen[ny,nx] = 1
                        stack.append((ny,nx))
            ys = [p[0] for p in pts]
            xs = [p[1] for p in pts]
            cells.append((min(ys),max(ys)+1,min(xs),max(xs)+1))
    return sorted(cells, key=lambda b:(b[0],b[2]))

def _stencil_spec():
    """Return (logical selected positions, paint colour) from the small green stencil."""
    e = np.array(ENTRY_GRID, dtype=int)
    board = _large_green_board_box()
    # Find a non-board colour-3 component bbox containing colour 15.
    h,w = e.shape
    mask = (e == 3)
    seen = np.zeros((h,w), dtype=np.uint8)
    source = None
    for y in range(h):
        for x in range(w):
            if not mask[y,x] or seen[y,x]:
                continue
            stack=[(y,x)]; seen[y,x]=1; pts=[]
            while stack:
                yy,xx=stack.pop(); pts.append((yy,xx))
                for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<h and 0<=nx<w and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=1; stack.append((ny,nx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            b=(min(ys),max(ys)+1,min(xs),max(xs)+1)
            if board is not None and b == board:
                continue
            y0,y1,x0,x1=b
            if np.any(e[y0:y1,x0:x1] == 15):
                source=b
                break
    if source is None:
        return set(), 2
    y0,y1,x0,x1=source
    # Map each colour-15 component center into one of three logical rows/cols.
    sub=(e[y0:y1,x0:x1] == 15)
    ss=np.zeros(sub.shape,dtype=np.uint8)
    logical=set()
    for yy in range(sub.shape[0]):
        for xx in range(sub.shape[1]):
            if not sub[yy,xx] or ss[yy,xx]:
                continue
            stack=[(yy,xx)]; ss[yy,xx]=1; pts=[]
            while stack:
                py,px=stack.pop(); pts.append((py,px))
                for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny,nx=py+dy,px+dx
                    if 0<=ny<sub.shape[0] and 0<=nx<sub.shape[1] and sub[ny,nx] and not ss[ny,nx]:
                        ss[ny,nx]=1; stack.append((ny,nx))
            cy=sum(p[0] for p in pts)/len(pts)
            cx=sum(p[1] for p in pts)/len(pts)
            row=int(round((cy-1)*2/max(1,(y1-y0)-3)))
            col=int(round((cx-1)*2/max(1,(x1-x0)-3)))
            logical.add((max(0,min(2,row)),max(0,min(2,col))))
    vals=e[y0+1:y1-1,x0+1:x1-1].ravel().tolist()
    vals=[int(v) for v in vals if v not in (3,15)]
    paint=max(set(vals),key=lambda v:vals.count(v)) if vals else 2
    return logical, paint

def _spend_meter(a):
    e = np.array(ENTRY_GRID, dtype=int)
    cols = [x for x in range(e.shape[1]) if np.all(e[:,x] == 14)]
    if not cols:
        return
    for y in range(a.shape[0]-1):
        if all(a[y,x] == 14 and a[y+1,x] == 14 for x in cols):
            for x in cols:
                a[y:y+2, x] = 0
            return

def init_state(entry_grid):
    # The first input after level entry / RESET only wakes the controls.
    return {"effective": 0, "armed": False, "phase": 0}

def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    before = a.copy()
    box = _small_marker(a)
    base = _entry_marker_pattern()

    spend = False
    bonus_spend = False
    level_up = False
    armed = bool(state.get("armed", False))

    # Confirmed across two RESETs: the very first input is a visual no-op that
    # merely wakes/arms the controls, regardless of which direction is pressed.
    if not armed:
        info = {"level_up": False, "dead": False, "win": False}
        return a.tolist(), info, {"effective": int(state.get("effective", 0)), "armed": True, "phase": 0}

    # After wake-up, the ordinary directional movement charge alternates:
    # even-numbered inputs spend a band. Turning and endpoint cases can add a
    # charge independently; inert blocked-left/repeated inputs remain free.
    phase = int(state.get("phase", 0)) + 1

    if action in (1, 2) and box is not None and base is not None:
        y0, y1, x0, x1 = box
        motif = _marker_pattern_for_side(base, y1-y0)
        turns = -1 if action == 1 else 1
        target = np.rot90(motif, turns)
        old = a[y0:y1, x0:x1].copy()
        # Establishing a vertical orientation from a horizontal one is free;
        # flipping between the two vertical orientations spends a band.
        other_vertical = np.rot90(motif, -turns)
        changed = not np.array_equal(old, target)
        spend = changed and phase % 2 == 0
        a[y0:y1, x0:x1] = target

    elif action == 3 and box is not None and base is not None:
        y0, y1, x0, x1 = box
        width = x1-x0
        motif = _marker_pattern_for_side(base, width)
        orientation_changed = not np.array_equal(a[y0:y1, x0:x1], motif)
        nx0, nx1 = x0-width, x1-width
        if nx0 >= 0 and np.all(a[y0:y1, nx0:nx1] == 2):
            a[y0:y1, x0:x1] = 2
            a[y0:y1, nx0:nx1] = motif
            # Locate the middle of the entry board's five full-height slots.
            e = np.array(ENTRY_GRID, dtype=int)
            eb = _small_marker(e)
            center = None
            if eb is not None:
                ey0, ey1, ex0, ex1 = eb
                left = ex0
                while left-width >= 0 and np.all(e[ey0:ey1, left-width:left] == 2):
                    left -= width
                center = (left + ex0)//2
            # Ordinary directional charge alternates. Reorientation and the
            # wide track's far-left landing charge regardless of phase.
            entering_neck = width < base.shape[0] and x0 == left
            spend = (orientation_changed or phase % 2 == 0 or center is None
                     or nx0 == left or entering_neck)
        elif (width < base.shape[0] and nx0 >= 0
              and np.all(a[y0:y1, nx0:nx1] == 10)):
            # A correctly miniaturised marker at the neck mouth inserts into
            # the colour-10 socket chamber and completes the level.
            level_up = True

    elif action == 4 and box is not None and base is not None:
        y0, y1, x0, x1 = box
        width = x1-x0
        motif = _marker_pattern_for_side(base, width)
        orientation_changed = not np.array_equal(a[y0:y1, x0:x1], np.fliplr(motif))
        nx0, nx1 = x0+width, x1+width
        # Right presses spend by default, even when blocked at the endpoint.
        spend = True
        if nx1 <= a.shape[1] and np.all(a[y0:y1, nx0:nx1] == 2):
            a[y0:y1, x0:x1] = 2
            a[y0:y1, nx0:nx1] = np.fliplr(motif)
            e = np.array(ENTRY_GRID, dtype=int)
            eb = _small_marker(e)
            center = None
            if eb is not None:
                ey0, ey1, ex0, ex1 = eb
                left = ex0
                while left-width >= 0 and np.all(e[ey0:ey1, left-width:left] == 2):
                    left -= width
                center = (left + ex0)//2
            spend = orientation_changed or phase % 2 == 0

    elif action == 6:
        cell = _clicked_board_cell(a, x, y)
        if cell is not None:
            cy0, cy1, cx0, cx1 = cell
            if np.all(a[cy0:cy1, cx0:cx1] == 14):
                # Clicking an active cell deselects it, restoring ENTRY, for free.
                e = np.array(ENTRY_GRID, dtype=int)
                a[cy0:cy1, cx0:cx1] = e[cy0:cy1, cx0:cx1]
            else:
                a[cy0:cy1, cx0:cx1] = 14
                board = _large_green_board_box()
                free_cell = False
                if board is not None:
                    by0, by1, bx0, bx1 = board
                    cell_cx = (cx0+cx1-1)//2
                    cell_cy = (cy0+cy1-1)//2
                    mbox_now = _small_marker(a)
                    side_now = 0 if mbox_now is None else mbox_now[1]-mbox_now[0]
                    if mbox_now is not None:
                        my0, my1, mx0, mx1 = mbox_now
                        mid_x = (bx0+bx1-1)//2
                        mid_y = (by0+by1-1)//2
                        left_cell = (cell_cx == bx0+3 and cell_cy == mid_y)
                        right_cell = (cell_cx == bx1-4 and cell_cy == mid_y)

                        # A full-size marker makes its occupied horizontal
                        # endpoint free on the cardinal board: right at ENTRY,
                        # left at the wide track's far end.
                        eb = _small_marker(np.array(ENTRY_GRID, dtype=int))
                        left_end = None
                        right_end = None
                        if eb is not None:
                            ey0, ey1, ex0, ex1 = eb
                            right_end = ex0
                            left_end = ex0
                            while left_end-side_now >= 0 and np.all(
                                np.array(ENTRY_GRID, dtype=int)[ey0:ey1, left_end-side_now:left_end] == 2
                            ):
                                left_end -= side_now
                        if left_end is not None and mx0 <= left_end:
                            free_cell = left_cell
                        if right_end is not None and mx0 >= right_end:
                            free_cell = free_cell or right_cell

                        # At miniature size, its visible 9→10 orientation is
                        # another already-satisfied/free cardinal direction.
                        if side_now == 2:
                            tile_now = a[my0:my1, mx0:mx1]
                            top_cell = (cell_cx == mid_x and cell_cy == by0+3)
                            bottom_cell = (cell_cx == mid_x and cell_cy == by1-4)
                            if np.all(tile_now[0,:] == 9) and np.all(tile_now[1,:] == 10):
                                free_cell = free_cell or top_cell
                            elif np.all(tile_now[0,:] == 10) and np.all(tile_now[1,:] == 9):
                                free_cell = free_cell or bottom_cell
                            elif np.all(tile_now[:,0] == 9) and np.all(tile_now[:,1] == 10):
                                free_cell = free_cell or left_cell
                            elif np.all(tile_now[:,0] == 10) and np.all(tile_now[:,1] == 9):
                                free_cell = free_cell or right_cell
                spend = not free_cell

                # A complete active stencil fires automatically: paint those
                # logical cells, shrink the patterned marker by 2, and spend
                # one additional band.
                cells = _board_cells()
                active = set()
                for i, cb in enumerate(cells):
                    yy0, yy1, xx0, xx1 = cb
                    if np.all(a[yy0:yy1, xx0:xx1] == 14):
                        active.add((i//3, i%3))
                stencil, paint = _stencil_spec()
                if stencil and active == stencil:
                    for i, cb in enumerate(cells):
                        if (i//3, i%3) in active:
                            yy0, yy1, xx0, xx1 = cb
                            a[yy0:yy1, xx0:xx1] = paint
                    mbox = _small_marker(a)
                    if mbox is not None:
                        my0, my1, mx0, mx1 = mbox
                        side = my1-my0
                        tile = a[my0:my1, mx0:mx1].copy()
                        if side <= 2:
                            # Observed second firing: expand 2→4 and crawl two
                            # cells left, preserving the miniature's pattern.
                            big = np.repeat(np.repeat(tile, 2, axis=0), 2, axis=1)
                            ny0, nx0 = my0, mx0-side
                            a[my0:my1, mx0:mx1] = paint
                            a[ny0:ny0+big.shape[0], nx0:nx0+big.shape[1]] = big
                        else:
                            tiny = tile[::2, ::2]
                            a[my0:my1, mx0:mx1] = paint
                            a[my0:my0+tiny.shape[0], mx0:mx0+tiny.shape[1]] = tiny
                    # Resizing away from the wide track's left endpoint
                    # spends an extra band. At the left endpoint the resize is
                    # the intended neck transition and has no bonus charge.
                    bonus_spend = True
                    if mbox is not None:
                        e_now = np.array(ENTRY_GRID, dtype=int)
                        eb_now = _small_marker(e_now)
                        if eb_now is not None:
                            ey0, ey1, ex0, ex1 = eb_now
                            left_now = ex0
                            while left_now-side >= 0 and np.all(
                                e_now[ey0:ey1, left_now-side:left_now] == 2
                            ):
                                left_now -= side
                            if mx0 <= left_now:
                                bonus_spend = False

    effective = int(state.get("effective", 0))
    marker_changed = not np.array_equal(a, before)
    if marker_changed:
        effective += 1
    if spend:
        _spend_meter(a)
    if bonus_spend:
        _spend_meter(a)

    info = {"level_up": level_up, "dead": False, "win": False}
    return a.tolist(), info, {"effective": effective, "armed": armed, "phase": phase}
