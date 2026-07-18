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

    # At the socket mouth the miniature touches the socket's same-colour
    # component, so connectivity no longer separates it. Recover the movable
    # half-and-half square by its motif and adjacent colour-2 track.
    best = None
    for side in (2, 4):
        for y in range(h-side+1):
            for x in range(w-side+1):
                tile = a[y:y+side, x:x+side]
                if not np.all((tile == 9) | (tile == 10)):
                    continue
                half = side // 2
                split_lr = (np.all(tile[:,:half] == tile[0,0])
                            and np.all(tile[:,half:] == tile[0,-1])
                            and tile[0,0] != tile[0,-1])
                split_tb = (np.all(tile[:half,:] == tile[0,0])
                            and np.all(tile[half:,:] == tile[-1,0])
                            and tile[0,0] != tile[-1,0])
                if not (split_lr or split_tb):
                    continue
                score = 0
                if y > 0:
                    score += int(np.sum(a[y-1, x:x+side] == 2))
                if y+side < h:
                    score += int(np.sum(a[y+side, x:x+side] == 2))
                if x > 0:
                    score += int(np.sum(a[y:y+side, x-1] == 2))
                if x+side < w:
                    score += int(np.sum(a[y:y+side, x+side] == 2))
                if score > 0 and (best is None or score > best[0]):
                    best = (score, y, y+side, x, x+side)
    return None if best is None else best[1:]

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

def _entry_goal_direction():
    """Cardinal direction from ENTRY marker toward the other 9/10 socket."""
    e = np.array(ENTRY_GRID, dtype=int)
    mb = _small_marker(e)
    if mb is None:
        return (-1, 0)
    my0, my1, mx0, mx1 = mb
    # The colour-9 half is the marker's leading face. Reading the motif is
    # robust even when marker and socket are diagonally offset (level 3).
    tile = e[my0:my1, mx0:mx1]
    scores = {
        (-1,0): int(np.sum(tile[:,0] == 9)),
        (1,0): int(np.sum(tile[:,-1] == 9)),
        (0,-1): int(np.sum(tile[0,:] == 9)),
        (0,1): int(np.sum(tile[-1,:] == 9)),
    }
    best_score = max(scores.values())
    best_dirs = [d for d,v in scores.items() if v == best_score]
    if len(best_dirs) == 1:
        return best_dirs[0]
    mask = (e == 9) | (e == 10)
    seen = np.zeros(e.shape, dtype=np.uint8)
    sockets = []
    for y in range(e.shape[0]):
        for x in range(e.shape[1]):
            if not mask[y,x] or seen[y,x]:
                continue
            stack=[(y,x)]; seen[y,x]=1; pts=[]
            while stack:
                yy,xx=stack.pop(); pts.append((yy,xx))
                for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny,nx=yy+dy,xx+dx
                    if (0 <= ny < e.shape[0] and 0 <= nx < e.shape[1]
                            and mask[ny,nx] and not seen[ny,nx]):
                        seen[ny,nx]=1; stack.append((ny,nx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            b=(min(ys),max(ys)+1,min(xs),max(xs)+1)
            if b != mb:
                sockets.append((len(pts), b))
    if not sockets:
        return (-1, 0)
    _, (sy0,sy1,sx0,sx1) = max(sockets, key=lambda z:z[0])
    dx = (sx0+sx1) - (mx0+mx1)
    dy = (sy0+sy1) - (my0+my1)
    if abs(dx) >= abs(dy):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)

def _direction_pattern(base, side, action):
    """Rotate ENTRY motif from its goal-facing direction to action direction."""
    motif = _marker_pattern_for_side(base, side)
    wanted = {1:(0,-1), 2:(0,1), 3:(-1,0), 4:(1,0)}[action]
    vec = _entry_goal_direction()
    for k in range(4):
        if vec == wanted:
            return np.rot90(motif, k)
        # np.rot90(+1) turns a screen vector counter-clockwise.
        vec = (vec[1], -vec[0])
    return motif

def _full_goal_endpoint():
    """Top-left of the last full-size red landing toward ENTRY's socket."""
    e = np.array(ENTRY_GRID, dtype=int)
    mb = _small_marker(e)
    if mb is None:
        return None
    y0,y1,x0,x1 = mb
    side = y1-y0
    dx,dy = _entry_goal_direction()
    while True:
        ny0,ny1 = y0+dy*side, y1+dy*side
        nx0,nx1 = x0+dx*side, x1+dx*side
        if (ny0 < 0 or nx0 < 0 or ny1 > e.shape[0] or nx1 > e.shape[1]
                or not np.all(e[ny0:ny1,nx0:nx1] == 2)):
            return y0,x0
        y0,y1,x0,x1 = ny0,ny1,nx0,nx1

def _leaving_goal_endpoint(y0, x0, action):
    end = _full_goal_endpoint()
    if end is None or (y0,x0) != end:
        return False
    gx,gy = _entry_goal_direction()
    ax,ay = {1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
    return (ax,ay) == (-gx,-gy)

def _portal_target(symbol, side):
    """Find a nested-corner portal whose inner square accepts the marker."""
    if symbol is None:
        return None
    e = np.array(ENTRY_GRID, dtype=int)
    for y in range(1, e.shape[0]-side):
        for x in range(1, e.shape[1]-side):
            inner = ((y,x),(y,x+side-1),(y+side-1,x),(y+side-1,x+side-1))
            outer = ((y-1,x-1),(y-1,x+side),(y+side,x-1),(y+side,x+side))
            if all(e[yy,xx] == symbol for yy,xx in inner+outer):
                return y,x
    return None

def _unlock_frame(symbol):
    """Return (bbox, payload colour) for a square symbol frame."""
    if symbol is None:
        return None
    e = np.array(ENTRY_GRID, dtype=int)
    for side in (4, 6, 8):
        for y in range(e.shape[0]-side+1):
            for x in range(e.shape[1]-side+1):
                tile = e[y:y+side, x:x+side]
                border = np.zeros((side,side), dtype=bool)
                border[0,:]=border[-1,:]=True
                border[:,0]=border[:,-1]=True
                if not np.all(tile[border] == symbol):
                    continue
                inner = tile[1:-1,1:-1]
                vals = set(int(v) for v in inner.ravel())
                if len(vals) == 1:
                    value = list(vals)[0]
                    if value not in (symbol, 2, 3, 5, 14):
                        return (y, y+side, x, x+side), value
    return None

def _unlock_color(symbol):
    frame = _unlock_frame(symbol)
    return None if frame is None else frame[1]

def _underlay(y0, y1, x0, x1, cleared_colors=(), cleared_boxes=()):
    """Static terrain under a marker, including persistent command-cleared tiles."""
    e = np.array(ENTRY_GRID, dtype=int)
    out = e[y0:y1, x0:x1].copy()
    mb = _small_marker(e)
    if mb is not None:
        my0,my1,mx0,mx1 = mb
        oy0,oy1 = max(y0,my0), min(y1,my1)
        ox0,ox1 = max(x0,mx0), min(x1,mx1)
        if oy0 < oy1 and ox0 < ox1:
            out[oy0-y0:oy1-y0, ox0-x0:ox1-x0] = 2
    for colour in cleared_colors:
        out[out == int(colour)] = 2
    for by0,by1,bx0,bx1 in cleared_boxes:
        oy0,oy1 = max(y0,by0), min(y1,by1)
        ox0,ox1 = max(x0,bx0), min(x1,bx1)
        if oy0 < oy1 and ox0 < ox1:
            out[oy0-y0:oy1-y0, ox0-x0:ox1-x0] = 2
    return out

def _mini_landing_waiver(a, y0, y1, x0, x1, action):
    """Whether a miniature lands at a free staging mouth.

    Miniature translations normally cost.  A landing is supplied/free when it
    stages immediately before a non-floor target (socket/key), or immediately
    before the wide lane narrows to a side-sized corridor.
    """
    side = y1-y0
    dx,dy = {1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
    fy0,fy1 = y0+dy*side, y1+dy*side
    fx0,fx1 = x0+dx*side, x1+dx*side
    if fy0 < 0 or fx0 < 0 or fy1 > a.shape[0] or fx1 > a.shape[1]:
        return True
    forward = a[fy0:fy1,fx0:fx1]
    if np.all(forward == 10):
        # In battery/resource layouts the final staging landing remains paid;
        # the battery replaces the older socket-mouth waiver.
        return not _has_arena_energy_pickup()
    if not np.all(forward == 2):
        return False

    def perpendicular_open(by0,by1,bx0,bx1):
        score = 0
        if dx:
            if by0-side >= 0:
                score += int(np.all(a[by0-side:by0,bx0:bx1] == 2))
            if by1+side <= a.shape[0]:
                score += int(np.all(a[by1:by1+side,bx0:bx1] == 2))
        else:
            if bx0-side >= 0:
                score += int(np.all(a[by0:by1,bx0-side:bx0] == 2))
            if bx1+side <= a.shape[1]:
                score += int(np.all(a[by0:by1,bx1:bx1+side] == 2))
        return score

    here_open = perpendicular_open(y0,y1,x0,x1)
    forward_open = perpendicular_open(fy0,fy1,fx0,fx1)
    # The next landing must be a true side-wide corridor (no perpendicular
    # neighbouring block), not merely a somewhat narrower part of a wide room.
    return forward_open == 0 and here_open > forward_open

def _partial_key_approach_waiver(a, y0, y1, x0, x1, action):
    """A partially dialled framed-key command supplies its approach staging pad.

    The pad is one full-marker stride (two miniature strides) before the
    matching frame.  This is visible only while a proper nonempty subset of
    that key's stencil remains selected on the large board.
    """
    cells = _board_cells()
    if not cells:
        return False
    active = set()
    for i, (cy0,cy1,cx0,cx1) in enumerate(cells):
        if np.all(a[cy0:cy1,cx0:cx1] == 14):
            active.add((i//3, i%3))
    if not active:
        return False
    side = y1-y0
    for stencil, _, symbol in _stencil_specs():
        frame_info = _unlock_frame(symbol)
        if frame_info is None or not (active < stencil):
            continue
        (fy0,fy1,fx0,fx1), _ = frame_info
        overlap_y = max(y0,fy0) < min(y1,fy1)
        overlap_x = max(x0,fx0) < min(x1,fx1)
        if action == 3 and overlap_y and x0 == fx1 + 2*side:
            return True
        if action == 4 and overlap_y and x1 == fx0 - 2*side:
            return True
        if action == 1 and overlap_x and y0 == fy1 + 2*side:
            return True
        if action == 2 and overlap_x and y1 == fy0 - 2*side:
            return True
    return False

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
    symbol = None
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
            interior = e[y0+1:y1-1, x0+1:x1-1].ravel().tolist()
            vals = [int(v) for v in interior if v != 3]
            uniq = set(vals)
            if len(uniq) >= 2:
                counts = {v: vals.count(v) for v in uniq}
                paint0 = max(uniq, key=lambda v: counts[v])
                rare = [v for v in uniq if v != paint0]
                symbol = min(rare, key=lambda v: counts[v])
                source=b
                break
    if source is None or symbol is None:
        return set(), 2, None
    y0,y1,x0,x1=source
    # Map each rare-symbol component center into one of three logical rows/cols.
    sub=(e[y0:y1,x0:x1] == symbol)
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
    vals=[int(v) for v in vals if v not in (3,symbol)]
    paint=max(set(vals),key=lambda v:vals.count(v)) if vals else 2
    return logical, paint, symbol

def _stencil_specs():
    """Return every small green source stencil, in screen order.

    Later levels combine several previously learned commands.  Each separate
    non-board colour-3 component is its own 3x3 logical stencil; selecting the
    large board pattern fires whichever one matches exactly.
    """
    e = np.array(ENTRY_GRID, dtype=int)
    board = _large_green_board_box()
    h, w = e.shape
    mask = (e == 3)
    seen = np.zeros((h, w), dtype=np.uint8)
    specs = []
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
                    if (0 <= ny < h and 0 <= nx < w and mask[ny,nx]
                            and not seen[ny,nx]):
                        seen[ny,nx] = 1
                        stack.append((ny,nx))
            ys = [p[0] for p in pts]
            xs = [p[1] for p in pts]
            b = (min(ys), max(ys)+1, min(xs), max(xs)+1)
            if board is not None and b == board:
                continue
            y0, y1, x0, x1 = b
            vals = [int(v) for v in
                    e[y0+1:y1-1, x0+1:x1-1].ravel().tolist()
                    if int(v) != 3]
            uniq = set(vals)
            if len(uniq) < 2:
                continue
            counts = {v: vals.count(v) for v in uniq}
            paint = max(uniq, key=lambda v: counts[v])
            rare = [v for v in uniq if v != paint]
            symbol = min(rare, key=lambda v: counts[v])

            sub = (e[y0:y1, x0:x1] == symbol)
            ss = np.zeros(sub.shape, dtype=np.uint8)
            logical = set()
            for yy in range(sub.shape[0]):
                for xx in range(sub.shape[1]):
                    if not sub[yy,xx] or ss[yy,xx]:
                        continue
                    todo = [(yy,xx)]
                    ss[yy,xx] = 1
                    comp = []
                    while todo:
                        py,px = todo.pop()
                        comp.append((py,px))
                        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                            ny,nx = py+dy,px+dx
                            if (0 <= ny < sub.shape[0] and 0 <= nx < sub.shape[1]
                                    and sub[ny,nx] and not ss[ny,nx]):
                                ss[ny,nx] = 1
                                todo.append((ny,nx))
                    cy = sum(p[0] for p in comp) / len(comp)
                    cx = sum(p[1] for p in comp) / len(comp)
                    row = int(round((cy-1)*2/max(1,(y1-y0)-3)))
                    col = int(round((cx-1)*2/max(1,(x1-x0)-3)))
                    logical.add((max(0,min(2,row)), max(0,min(2,col))))
            specs.append((logical, paint, symbol))
    return specs

def _spend_meter(a):
    """Consume one two-row meter band; report whether one was available."""
    e = np.array(ENTRY_GRID, dtype=int)
    cols = [x for x in range(e.shape[1]) if np.all(e[:,x] == 14)]
    if not cols:
        return True
    for y in range(a.shape[0]-1):
        if all(a[y,x] == 14 and a[y+1,x] == 14 for x in cols):
            for x in cols:
                a[y:y+2, x] = 0
            return True
    return False

def _refill_meter(a, bands=8):
    """Restore the most recently depleted meter bands."""
    e = np.array(ENTRY_GRID, dtype=int)
    cols = [x for x in range(e.shape[1]) if np.all(e[:,x] == 14)]
    if not cols:
        return
    left = int(bands)
    for y in range(a.shape[0]-2, -1, -2):
        if left <= 0:
            break
        if all(a[y,x] == 0 and a[y+1,x] == 0 for x in cols):
            for x in cols:
                a[y:y+2,x] = 14
            left -= 1

def _has_arena_energy_pickup():
    """Whether ENTRY contains colour-14 away from the right-edge meter."""
    e = np.array(ENTRY_GRID, dtype=int)
    return bool(e.shape[1] > 2 and np.any(e[:, :-2] == 14))


def _collect_energy_pickup(a, y0, y1, x0, x1):
    """Consume a small colour-14 arena pickup touched by a miniature.

    The pickup is a connected 2x2 object, distinct from the right-edge meter
    and the large command board.  It restores eight two-row meter bands.
    """
    seeds = [(yy,xx) for yy in range(y0,y1) for xx in range(x0,x1)
             if a[yy,xx] == 14]
    if not seeds:
        return None
    seen = set(seeds)
    todo = list(seeds)
    while todo:
        yy,xx = todo.pop()
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny,nx = yy+dy,xx+dx
            if (0 <= ny < a.shape[0] and 0 <= nx < a.shape[1]
                    and a[ny,nx] == 14 and (ny,nx) not in seen):
                seen.add((ny,nx)); todo.append((ny,nx))
    if len(seen) > 16 or any(xx >= a.shape[1]-2 for yy,xx in seen):
        return None
    ys = [p[0] for p in seen]; xs = [p[1] for p in seen]
    bbox = (min(ys), max(ys)+1, min(xs), max(xs)+1)
    # The battery halves the depletion accumulated before contact.
    # Contact itself remains an ordinary paid miniature translation, so refill
    # ceil(used/2) now and let the caller spend that contact band afterward.
    e = np.array(ENTRY_GRID, dtype=int)
    cols = [x for x in range(e.shape[1]) if np.all(e[:,x] == 14)]
    used = 0
    if cols:
        for by in range(0, a.shape[0]-1, 2):
            if all(a[by,x] == 0 and a[by+1,x] == 0 for x in cols):
                used += 1
    for yy,xx in seen:
        a[yy,xx] = 2
    _refill_meter(a, (used + 1) // 2)
    return bbox

def init_state(entry_grid):
    # The first input after level entry / RESET only wakes the controls.
    return {"effective": 0, "armed": bool(CURRENT_LEVEL is not None and CURRENT_LEVEL > 0), "phase": 0, "unlocked": None, "cleared_colors": [], "cleared_boxes": [], "fresh_resize": False, "powered": 0, "key_approach_used": False, "remote_key": False}

def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    before = a.copy()
    box = _small_marker(a)
    base = _entry_marker_pattern()

    spend = False
    bonus_spend = 0
    level_up = False
    armed = bool(state.get("armed", False))
    # Some framed-key commands change collision state without recolouring the lock.
    unlocked = state.get("unlocked", None)
    cleared_colors = list(state.get("cleared_colors", []))
    cleared_boxes = list(state.get("cleared_boxes", []))
    fresh_resize = bool(state.get("fresh_resize", False))
    # Nonzero value is the reverse direction eligible for the
    # battery's carried return step.
    powered = int(state.get("powered", 0))
    key_approach_used = bool(state.get("key_approach_used", False))
    remote_key = bool(state.get("remote_key", False))

    # Confirmed across two RESETs: the very first input is a visual no-op that
    # merely wakes/arms the controls, regardless of which direction is pressed.
    if not armed:
        info = {"level_up": False, "dead": False, "win": False}
        return a.tolist(), info, {"effective": int(state.get("effective", 0)), "armed": True, "phase": 0, "unlocked": unlocked, "cleared_colors": cleared_colors, "cleared_boxes": cleared_boxes, "fresh_resize": fresh_resize, "powered": powered, "key_approach_used": key_approach_used, "remote_key": remote_key}

    # After wake-up, the ordinary directional movement charge alternates:
    # even-numbered inputs spend a band. Turning and endpoint cases can add a
    # charge independently; inert blocked-left/repeated inputs remain free.
    # The movement half-cycle advances on directional inputs and on actual
    # board interactions.  A click elsewhere on the screen is inert and does
    # not perturb that cycle.
    phase = int(state.get("phase", 0))
    if (action in (1,2,3,4)
            or (action == 6 and (_clicked_board_cell(a, x, y) is not None
                                 or int(state.get("effective", 0)) > 0))):
        phase += 1
    if action in (1,2,3,4):
        fresh_resize = False

    if action in (1, 2) and box is not None and base is not None:
        y0, y1, x0, x1 = box
        side = y1-y0
        target = _direction_pattern(base, side, action)
        old = a[y0:y1, x0:x1].copy()
        changed = not np.array_equal(old, target)
        step_y = -side if action == 1 else side
        ny0, ny1 = y0+step_y, y1+step_y
        if (ny0 >= 0 and ny1 <= a.shape[0]
                and np.all(a[ny0:ny1, x0:x1] == 2)):
            a[y0:y1, x0:x1] = _underlay(y0, y1, x0, x1, cleared_colors, cleared_boxes)
            a[ny0:ny1, x0:x1] = target
            # Moving/turning and landing at the end of the full-size lane can
            # charge independently of the alternating ordinary phase.
            fy0, fy1 = ny0+step_y, ny1+step_y
            next_clear = (fy0 >= 0 and fy1 <= a.shape[0]
                          and np.all(before[fy0:fy1, x0:x1] == 2))
            goal_end_here = _full_goal_endpoint()
            next_is_socket = (fy0 >= 0 and fy1 <= a.shape[0]
                              and np.all(before[fy0:fy1, x0:x1] == 10))
            endpoint = (side == base.shape[0]
                        and ((goal_end_here is not None and (ny0,x0) == goal_end_here)
                             or next_is_socket))
            lx0, lx1 = x0-side, x0
            rx0, rx1 = x1, x1+side
            left_clear = (lx0 >= 0 and np.all(before[y0:y1,lx0:lx1] == 2))
            right_clear = (rx1 <= a.shape[1] and np.all(before[y0:y1,rx0:rx1] == 2))
            corner_turn = (changed and side == base.shape[0]
                           and left_clear != right_clear)
            if side < base.shape[0]:
                # The battery's carried waiver is only for reversing along
                # the collection axis; a perpendicular departure discards it.
                if powered and action != powered:
                    powered = 0
                waiver = _mini_landing_waiver(
                    before, ny0, ny1, x0, x1, action)
                partial_key = _partial_key_approach_waiver(
                    before, ny0, ny1, x0, x1, action)
                if partial_key and not key_approach_used:
                    spend = False
                    key_approach_used = True
                elif powered and not changed:
                    spend = False
                    powered = False
                else:
                    # A staging-mouth waiver removes the miniature terrain
                    # surcharge, but the ordinary even half-cycle still costs.
                    spend = (phase % 2 == 0 or not waiver)
            else:
                spend = (phase % 2 == 0 or endpoint or corner_turn
                         or _leaving_goal_endpoint(y0, x0, action))
            # If a corner surcharge lands on the otherwise-free half-cycle,
            # it substitutes for (rather than advances) that half-cycle.
            if corner_turn and phase % 2 == 1:
                phase -= 1
        elif (ny0 >= 0 and ny1 <= a.shape[0]
              and np.all(a[ny0:ny1, x0:x1] == 10)):
            level_up = True
        else:
            # A blocked direction still turns the marker in place.
            spend = changed and phase % 2 == 0
            # A fired framed command does not recolour or open its payload.
            # Pushing the already-facing marker against that payload costs;
            # the preparatory turn toward it is free.
            if (unlocked is not None and ny0 >= 0 and ny1 <= a.shape[0]
                    and np.any(a[ny0:ny1, x0:x1] == unlocked)):
                spend = not changed
            a[y0:y1, x0:x1] = target

    elif action == 3 and box is not None and base is not None:
        y0, y1, x0, x1 = box
        width = x1-x0
        motif = _direction_pattern(base, width, 3)
        orientation_changed = not np.array_equal(a[y0:y1, x0:x1], motif)
        nx0, nx1 = x0-width, x1-width
        if nx0 >= 0 and np.all(a[y0:y1, nx0:nx1] == 2):
            a[y0:y1, x0:x1] = _underlay(y0, y1, x0, x1, cleared_colors, cleared_boxes)
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
            bx0, bx1 = x1, x1+width
            back_clear = (bx1 <= a.shape[1]
                          and np.all(before[y0:y1, bx0:bx1] == 2))
            leaving_gate = (width == base.shape[0] and not back_clear
                            and bx1 <= a.shape[1]
                            and np.any(before[y0:y1, bx0:bx1] == 4))
            nnx0, nnx1 = nx0-width, nx1-width
            next_is_socket = (nnx0 >= 0
                              and np.all(before[y0:y1,nnx0:nnx1] == 10))
            if width < base.shape[0]:
                if powered and powered != 3:
                    powered = 0
                waiver = _mini_landing_waiver(
                    before, y0, y1, nx0, nx1, 3)
                partial_key = _partial_key_approach_waiver(
                    before, y0, y1, nx0, nx1, 3)
                if partial_key and not key_approach_used:
                    spend = False
                    key_approach_used = True
                elif powered and not orientation_changed:
                    spend = False
                    powered = False
                else:
                    spend = (phase % 2 == 0 or not waiver)
            else:
                # Turning a full marker from a vertical facing into horizontal
                # spends even on the otherwise-free half-cycle.
                spend = (phase % 2 == 0
                         or (orientation_changed and _has_arena_energy_pickup())
                         or center is None or nx0 == left
                         or entering_neck or leaving_gate
                         or _leaving_goal_endpoint(y0, x0, 3))
        elif (nx0 >= 0 and np.all(a[y0:y1, nx0:nx1] == 10)):
            # A correctly miniaturised marker at the neck mouth inserts into
            # the colour-10 socket chamber and completes the level.
            level_up = True

    elif action == 4 and box is not None and base is not None:
        y0, y1, x0, x1 = box
        width = x1-x0
        motif = _direction_pattern(base, width, 4)
        orientation_changed = not np.array_equal(a[y0:y1, x0:x1], motif)
        nx0, nx1 = x0+width, x1+width
        # A miniature can absorb a small arena energy pickup even when only
        # part of its destination overlaps the pickup.
        pickup_box = None
        if (width < base.shape[0] and nx1 <= a.shape[1]
                and np.any(a[y0:y1,nx0:nx1] == 14)
                and np.all((a[y0:y1,nx0:nx1] == 2)
                           | (a[y0:y1,nx0:nx1] == 14))):
            pickup_box = _collect_energy_pickup(a, y0, y1, nx0, nx1)
            if pickup_box is not None:
                if pickup_box not in cleared_boxes:
                    cleared_boxes.append(pickup_box)
                # The pickup also carries one free straight miniature
                # translation.  A necessary turn away from the pickup does
                # not consume that carried step.
                powered = 3
        # Right presses spend by default, even when blocked at the endpoint.
        spend = True
        if nx1 <= a.shape[1] and np.all(a[y0:y1, nx0:nx1] == 2):
            a[y0:y1, x0:x1] = _underlay(y0, y1, x0, x1, cleared_colors, cleared_boxes)
            a[y0:y1, nx0:nx1] = motif
            e = np.array(ENTRY_GRID, dtype=int)
            eb = _small_marker(e)
            center = None
            if eb is not None:
                ey0, ey1, ex0, ex1 = eb
                left = ex0
                while left-width >= 0 and np.all(e[ey0:ey1, left-width:left] == 2):
                    left -= width
                center = (left + ex0)//2
            fx0, fx1 = nx1, nx1+width
            next_clear = (fx1 <= a.shape[1]
                          and np.all(before[y0:y1, fx0:fx1] == 2))
            endpoint = width == base.shape[0] and not next_clear
            next_is_socket = (fx1 <= a.shape[1]
                              and np.all(before[y0:y1,fx0:fx1] == 10))
            if width < base.shape[0]:
                if powered and powered != 4 and pickup_box is None:
                    powered = 0
                waiver = _mini_landing_waiver(
                    before, y0, y1, nx0, nx1, 4)
                partial_key = _partial_key_approach_waiver(
                    before, y0, y1, nx0, nx1, 4)
                if partial_key and not key_approach_used:
                    spend = False
                    key_approach_used = True
                elif (powered and pickup_box is None
                        and not orientation_changed):
                    spend = False
                    powered = False
                else:
                    spend = (phase % 2 == 0 or not waiver)
            else:
                spend = (phase % 2 == 0
                         or (orientation_changed and _has_arena_energy_pickup())
                         or endpoint or _leaving_goal_endpoint(y0, x0, 4))
            # Pickup contact remains a normal paid translation;
            # its dynamic half-refill was already rendered above.
        elif (nx1 <= a.shape[1]
              and np.all(a[y0:y1, nx0:nx1] == 10)):
            # Either marker size completes when inserted into the uniform
            # colour-10 socket chamber.
            level_up = True
            spend = False

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
                # Each newly dialled partial key supplies one approach-stage
                # waiver; revisiting the same pad without changing the dial
                # does not recharge it.
                key_approach_used = False
                board = _large_green_board_box()
                # A resize supplies exactly the immediately following board
                # activation, provided the marker has not moved meanwhile.
                free_cell = fresh_resize
                fresh_resize = False
                horizontal_gate = False
                mouth_station = False
                command_station = False
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
                        top_cell = (cell_cx == mid_x and cell_cy == by0+3)
                        bottom_cell = (cell_cx == mid_x and cell_cy == by1-4)
                        action_cell = {1:top_cell, 2:bottom_cell,
                                       3:left_cell, 4:right_cell}

                        # The cardinal pointing outward from the occupied end
                        # of the lane is already satisfied/free.
                        eb = _small_marker(np.array(ENTRY_GRID, dtype=int))
                        goal_end = _full_goal_endpoint()
                        gx,gy = _entry_goal_direction()
                        goal_action = {(0,-1):1,(0,1):2,(-1,0):3,(1,0):4}[(gx,gy)]
                        away_action = {1:2,2:1,3:4,4:3}[goal_action]
                        # Confirmed endpoint waiver is a horizontal-lane rule;
                        # the vertical level's top cardinal still charges.
                        if gx != 0:
                            if eb is not None:
                                ey0,ey1,ex0,ex1 = eb
                                if my0 == ey0 and mx0 == ex0:
                                    free_cell = free_cell or action_cell[away_action]
                            if goal_end is not None:
                                gy0,gx0 = goal_end
                                progressed = ((mx0-gx0)*gx + (my0-gy0)*gy) >= 0
                                if progressed:
                                    free_cell = free_cell or action_cell[goal_action]

                        # At the entrance of a horizontal colour-4
                        # narrowing gate, the leading/top command segment is
                        # supplied by the gate and is free.
                        if (base is not None and side_now == base.shape[0]
                                and mx1+side_now <= a.shape[1]
                                and np.array_equal(a[my0:my1,mx0:mx1],
                                                   _direction_pattern(base, side_now, 4))):
                            gate = a[my0:my1, mx1:mx1+side_now]
                            if np.any(gate == 4) and np.any(gate == 2):
                                horizontal_gate = True
                                free_cell = free_cell or top_cell

                        # A framed command station is either the learned
                        # colour-4 gate or a miniature directly facing its
                        # matching key frame.
                        key_symbols = [spec[2] for spec in _stencil_specs()]
                        for sym in key_symbols:
                            frame_info = _unlock_frame(sym)
                            if frame_info is None:
                                continue
                            (fy0,fy1,fx0,fx1), _ = frame_info
                            facing = None
                            if (mx0 == fx1
                                    and max(my0,fy0) < min(my1,fy1)):
                                facing = 3
                            elif (mx1 == fx0
                                    and max(my0,fy0) < min(my1,fy1)):
                                facing = 4
                            elif (my0 == fy1
                                    and max(mx0,fx0) < min(mx1,fx1)):
                                facing = 1
                            elif (my1 == fy0
                                    and max(mx0,fx0) < min(mx1,fx1)):
                                facing = 2
                            if (facing is not None and base is not None
                                    and np.array_equal(
                                        a[my0:my1,mx0:mx1],
                                        _direction_pattern(base,side_now,facing))):
                                command_station = True
                        # A miniature poised at a wide-to-side-wide
                        # narrowing, facing into that corridor, is also a remote
                        # command station.  Like the colour-4 gate it supplies
                        # the leading/top command segment.
                        if base is not None and side_now < base.shape[0]:
                            for face in (1, 2, 3, 4):
                                if (np.array_equal(
                                        a[my0:my1,mx0:mx1],
                                        _direction_pattern(base, side_now, face))
                                        and _mini_landing_waiver(
                                            a, my0, my1, mx0, mx1, face)):
                                    mouth_station = True
                                    break
                        if mouth_station:
                            free_cell = free_cell or top_cell
                        command_station = (command_station or horizontal_gate
                                           or mouth_station)
                        if not command_station:
                            # Preserve that at least one segment of the current
                            # dial was banked away from its eventual station.
                            # Non-key resize firings clear this flag below.
                            remote_key = True

                        # Away from a station the framed key supplies the
                        # central logical segment for free.
                        if (any(_unlock_color(sym) is not None
                                for sym in key_symbols)
                                and not command_station
                                and cell_cx == mid_x and cell_cy == mid_y):
                            free_cell = True
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
                matching = [spec for spec in _stencil_specs()
                            if spec[0] and active == spec[0]]
                stencil, paint, symbol = (matching[0] if matching
                                          else (set(), 2, None))
                if stencil:
                    remote_at_fire = remote_key
                    resize_succeeded = False
                    for i, cb in enumerate(cells):
                        if (i//3, i%3) in active:
                            yy0, yy1, xx0, xx1 = cb
                            a[yy0:yy1, xx0:xx1] = paint
                    mbox = _small_marker(a)
                    portal = None
                    unlock = _unlock_color(symbol)
                    if mbox is not None:
                        my0, my1, mx0, mx1 = mbox
                        side = my1-my0
                        tile = a[my0:my1, mx0:mx1].copy()
                        portal = _portal_target(symbol, side)
                        if portal is not None:
                            # A rare-symbol nested-corner portal teleports the
                            # marker into its inner square, preserving facing.
                            py,px = portal
                            a[my0:my1, mx0:mx1] = paint
                            a[py:py+side, px:px+side] = tile
                        elif unlock is not None:
                            frame_info = _unlock_frame(symbol)
                            if command_station and frame_info is not None:
                                # At the matching colour-4 command station, consume
                                # the framed key and clear every payload-colour lock.
                                (fy0,fy1,fx0,fx1), payload = frame_info
                                a[a == payload] = paint
                                a[fy0:fy1,fx0:fx1] = paint
                                if payload not in cleared_colors:
                                    cleared_colors.append(payload)
                                fb = (fy0,fy1,fx0,fx1)
                                if fb not in cleared_boxes:
                                    cleared_boxes.append(fb)
                                unlocked = None
                            else:
                                # Away from its station the command is consumed
                                # without changing the rendered key or lock.
                                unlocked = unlock
                        elif side <= 2:
                            # Resize portal absent: expand toward the socket,
                            # but only when the complete enlarged footprint is
                            # floor.  An obstructed command still paints the
                            # board and consumes its meter charge, while the
                            # miniature itself remains intact.
                            big = np.repeat(np.repeat(tile, 2, axis=0), 2, axis=1)
                            gx,gy = _entry_goal_direction()
                            ny0, nx0 = my0+gy*side, mx0+gx*side
                            ny1, nx1 = ny0+big.shape[0], nx0+big.shape[1]
                            terrain = a.copy()
                            terrain[my0:my1,mx0:mx1] = _underlay(
                                my0, my1, mx0, mx1,
                                cleared_colors, cleared_boxes)
                            if (0 <= ny0 and 0 <= nx0
                                    and ny1 <= a.shape[0] and nx1 <= a.shape[1]
                                    and np.all(terrain[ny0:ny1,nx0:nx1] == 2)):
                                a[my0:my1, mx0:mx1] = paint
                                a[ny0:ny1, nx0:nx1] = big
                                resize_succeeded = True
                        else:
                            tiny = tile[::2, ::2]
                            a[my0:my1, mx0:mx1] = paint
                            a[my0:my0+tiny.shape[0], mx0:mx0+tiny.shape[1]] = tiny
                            resize_succeeded = True
                    if (portal is None and unlock is None and mbox is not None
                            and resize_succeeded):
                        # The free follow-up activation is supplied only by a
                        # resize performed on the ENTRY marker pad.  Resizing
                        # at an arbitrary travel waypoint does not grant it.
                        eb0 = _small_marker(np.array(ENTRY_GRID, dtype=int))
                        fresh_resize = (eb0 is not None
                                        and (my0, mx0) == (eb0[0], eb0[2]))
                    if portal is not None:
                        bonus_spend = 2
                    elif unlock is not None:
                        # Banking any segment away from the final station
                        # incurs one transfer band when the key fires.
                        # A narrowing-mouth station transmits the
                        # key remotely, so firing has one transmission band even
                        # when every segment was dialled there.
                        bonus_spend = 1 if (not command_station or remote_at_fire
                                            or mouth_station) else 0
                    else:
                        # Resize away from the goal-side full endpoint costs
                        # an extra band; at that endpoint it is waived.
                        bonus_spend = 1
                        goal_end_now = _full_goal_endpoint()
                        if (mbox is not None and goal_end_now is not None
                                and (my0,mx0) == goal_end_now):
                            bonus_spend = 0
                    remote_key = False

    effective = int(state.get("effective", 0))
    marker_changed = not np.array_equal(a, before)
    if marker_changed:
        effective += 1
    dead = False
    charges = int(bool(spend)) + int(bonus_spend)
    for _ in range(charges):
        if not _spend_meter(a):
            dead = True
            break

    info = {"level_up": level_up, "dead": dead, "win": False}
    return a.tolist(), info, {"effective": effective, "armed": armed, "phase": phase, "unlocked": unlocked, "cleared_colors": cleared_colors, "cleared_boxes": cleared_boxes, "fresh_resize": fresh_resize, "powered": powered, "key_approach_used": key_approach_used, "remote_key": remote_key}
