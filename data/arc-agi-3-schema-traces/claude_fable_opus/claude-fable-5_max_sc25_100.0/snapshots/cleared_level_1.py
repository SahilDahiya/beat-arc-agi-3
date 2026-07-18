# v10: head = s x s half-split 9|a overlay block; underlay restored on vacate (b's persist).
# Facing = 9-half side. Moves step by s pixels (swap with all-red target; facing := dir).
# TRUE COSTS (row-units, hidden total in state['spent']; bar displays 2*ceil(spent/2) dark rows):
#   a1/a2 turn: CCW=0, CW=2, 180=2 (CCW cycle L->D->R->U->L)
#   blocked-move turn (a3/a4): 2 flat (even CCW)
#   move LEFT: s/2 (4px->2, 2px->1); move RIGHT: 0; move U/D: UNKNOWN guess s/2
#   click matched NSEW (facing==cell dir): 0; other click: 2; completing click: 2
# a6 on button cell (3x3px, 3-bordered): toggle 2<->14, 0->14.
#   COMPLETION: 14-cells == recipe {N,W,E,S} -> panel all-2, head halves (top-left quadrant kept).
# Death at bar empty: unknown. First action after entry may be swallowed (replay skips 1st).

def init_state(entry_grid):
    # paid2: count of flat-cost events (2 dark rows each)
    # leftpx: leftward pixels traveled since last shrink (2 rows per 3 px, rounded)
    g = np.array(entry_grid)
    bbox = None
    h = _find_head(g, None)
    if h is not None:
        hx, hy, s, _ = h
        ys, xs = np.where((g == 9) | (g == 10))
        pts = [(x, y) for x, y in zip(xs, ys)
               if not (hx <= x < hx + s and hy <= y < hy + s)]
        if pts:
            bbox = (min(p[0] for p in pts), min(p[1] for p in pts),
                    max(p[0] for p in pts), max(p[1] for p in pts))
    return {"paid2": 0, "leftpx": 0, "base_bbox": bbox, "oriented": False}

def _dark_total(st):
    return 2 * st.get("paid2", 0) + 2 * int(st.get("leftpx", 0) / 3.0 + 0.5)

_CCW = {'L': 'D', 'D': 'R', 'R': 'U', 'U': 'L'}

def _recipe():
    """Recipe = positions of 0-cells in the button panel at level entry."""
    g = np.array(ENTRY_GRID)
    btns = _find_buttons(g)
    return frozenset(rc for rc, (bx, by) in btns.items() if g[by, bx] == 0)

def _turn_cost(old, new):
    if old == new or _CCW[old] == new:
        return 0
    return 2

def _find_head(g, base_bbox=None):
    """Find s x s half-split 9|a block NOT overlapping base_bbox; prefer larger s."""
    for s in (4, 2):
        h = s // 2
        for y in range(0, 65 - s):
            for x in range(0, 65 - s):
                if base_bbox is not None:
                    bx0, by0, bx1, by1 = base_bbox
                    if not (x + s - 1 < bx0 or x > bx1 or y + s - 1 < by0 or y > by1):
                        continue  # overlaps base structure
                w = g[y:y+s, x:x+s]
                if not np.all((w == 9) | (w == 10)):
                    continue
                if np.all(w[:, :h] == 9) and np.all(w[:, h:] == 10):
                    return x, y, s, 'L'
                if np.all(w[:, h:] == 9) and np.all(w[:, :h] == 10):
                    return x, y, s, 'R'
                if np.all(w[:h, :] == 9) and np.all(w[h:, :] == 10):
                    return x, y, s, 'U'
                if np.all(w[h:, :] == 9) and np.all(w[:h, :] == 10):
                    return x, y, s, 'D'
    return None

def _texture(facing, s):
    h = s // 2
    w = np.full((s, s), 10, dtype=int)
    if facing == 'L':
        w[:, :h] = 9
    elif facing == 'R':
        w[:, h:] = 9
    elif facing == 'U':
        w[:h, :] = 9
    else:
        w[h:, :] = 9
    return w

def _paint_bar(g, dark):
    dark = min(64, dark)
    for r in range(64):
        v = 0 if r < dark else 14
        g[r, 62] = v
        g[r, 63] = v

def _is_button(g, x0, y0):
    if x0 < 1 or y0 < 1 or x0 > 60 or y0 > 60:
        return False
    c = g[y0, x0]
    if c not in (0, 2, 14):
        return False
    if not np.all(g[y0:y0+3, x0:x0+3] == c):
        return False
    return (np.all(g[y0-1, x0:x0+3] == 3) and np.all(g[y0+3, x0:x0+3] == 3)
            and np.all(g[y0:y0+3, x0-1] == 3) and np.all(g[y0:y0+3, x0+3] == 3))

def _find_buttons(g):
    cells = []
    for y0 in range(1, 61):
        for x0 in range(1, 61):
            if _is_button(g, x0, y0):
                if not any(bx <= x0 < bx+3 and by <= y0 < by+3 for bx, by in cells):
                    cells.append((x0, y0))
    xs = sorted({cx for cx, cy in cells})
    ys = sorted({cy for cx, cy in cells})
    return {(ys.index(cy), xs.index(cx)): (cx, cy) for cx, cy in cells}

_CELL_DIR = {(0, 1): 'U', (1, 0): 'L', (1, 2): 'R', (2, 1): 'D'}

def _vacate(g, x, y, s):
    """Head leaves (x,y,s): restore underlay = 11 where ENTRY_GRID had b(11), else red 2."""
    e = np.array(ENTRY_GRID)
    for yy in range(y, y + s):
        for xx in range(x, x + s):
            g[yy, xx] = 11 if e[yy, xx] == 11 else 2

def _find_pad(g, s):
    """Find an s x s square whose 4 corners are b(11) cells -> teleport pad top-left."""
    for py in range(0, 65 - s):
        for px in range(0, 65 - s):
            if (g[py, px] == 11 and g[py, px+s-1] == 11
                    and g[py+s-1, px] == 11 and g[py+s-1, px+s-1] == 11):
                return px, py
    return None

def _click_button(g, x, y, head, oriented=True):
    """Returns (paid_flag, completed_flag)."""
    buttons = _find_buttons(g)
    if len(buttons) != 9:
        return 0, False
    hit = None
    for rc, (cx, cy) in buttons.items():
        if cx <= x < cx+3 and cy <= y < cy+3:
            hit = rc
            break
    if hit is None:
        return 0, False
    cx, cy = buttons[hit]
    c = g[cy, cx]
    new = {2: 14, 14: 2, 0: 14}[c]
    g[cy:cy+3, cx:cx+3] = new
    marked = {rc for rc, (bx, by) in buttons.items() if g[by, bx] == 14}
    if marked == _recipe():
        for bx, by in buttons.values():
            g[by:by+3, bx:bx+3] = 2
        fee = 1
        if head is not None:
            hx, hy, s, facing = head
            pad = _find_pad(g, s)
            if pad is not None:
                # TELEPORT: head jumps onto the b-cornered pad (corners consumed)
                px, py = pad
                _vacate(g, hx, hy, s)
                g[py:py+s, px:px+s] = _texture(facing, s)
                fee = 3  # observed L1: +6 rows
            elif s >= 4:
                # no pad: shrink in place (L0 behavior)
                _vacate(g, hx, hy, s)
                ns = s // 2
                g[hy:hy+ns, hx:hx+ns] = _texture(facing, ns)
        return fee, True
    facing = head[3] if head else None
    return (0 if (_CELL_DIR.get(hit) == facing and oriented) else 1), False

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {"paid2": 0, "leftpx": 0})
    h = _find_head(g, st.get("base_bbox"))
    if action == 6 and x is not None and y is not None:
        paid, completed = _click_button(g, x, y, h, st.get("oriented", False))
        st["paid2"] = st.get("paid2", 0) + paid
        if completed:
            # travel contribution bakes into the base; accumulator restarts
            st["paid2"] = st.get("paid2", 0) + int(st.get("leftpx", 0) / 3.0 + 0.5)
            st["leftpx"] = 0
    if h is not None and action in (1, 2, 3, 4):
        hx, hy, s, facing = h
        dxy = {1: (0, -1, 'U'), 2: (0, 1, 'D'), 3: (-1, 0, 'L'), 4: (1, 0, 'R')}[action]
        dx, dy, f = dxy[0] * s, dxy[1] * s, dxy[2]
        nx, ny = hx + dx, hy + dy
        moved = False
        if 0 <= nx <= 64 - s and 0 <= ny <= 64 - s:
            tgt = g[ny:ny+s, nx:nx+s]
            if np.all(tgt == 10):
                # DOCKING: moving into the base interior ('a' cells) completes the level
                _vacate(g, hx, hy, s)
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                info["level_up"] = True
                moved = True
            elif np.all(tgt == 2):
                _vacate(g, hx, hy, s)
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                moved = True
                # moves TOWARD the base cost 2 rows per 3 px; away = free (L0: left paid, right free)
                bb = st.get("base_bbox")
                toward = action == 3  # fallback: L0 behavior
                if bb is not None:
                    bcx, bcy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
                    hcx, hcy = hx + s / 2.0, hy + s / 2.0
                    toward = (bcx - hcx) * dx + (bcy - hcy) * dy > 0
                if toward:
                    st["leftpx"] = st.get("leftpx", 0) + s
        if not moved and facing != f:
            g[hy:hy+s, hx:hx+s] = _texture(f, s)
            if action in (1, 2):
                st["paid2"] = st.get("paid2", 0) + _turn_cost(facing, f) // 2
            else:
                st["paid2"] = st.get("paid2", 0) + 1  # blocked-move turn flat
        if moved or facing != f:
            st["oriented"] = True
    _paint_bar(g, _dark_total(st))
    return g.tolist(), info, st
