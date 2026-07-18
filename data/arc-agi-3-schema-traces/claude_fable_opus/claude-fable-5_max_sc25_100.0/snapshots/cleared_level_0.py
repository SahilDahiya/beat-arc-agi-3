# v8: head = s x s half-split 9|a block in red(2); s in {4,2}; shrinks on recipe completion.
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
    return {"paid2": 0, "leftpx": 0}

def _dark_total(st):
    return 2 * st.get("paid2", 0) + 2 * int(st.get("leftpx", 0) / 3.0 + 0.5)

_CCW = {'L': 'D', 'D': 'R', 'R': 'U', 'U': 'L'}
_RECIPE = frozenset({(0, 1), (1, 0), (1, 2), (2, 1)})

def _turn_cost(old, new):
    if old == new or _CCW[old] == new:
        return 0
    return 2

def _ring_clear(g, x, y, s):
    x0, y0, x1, y1 = max(0, x-1), max(0, y-1), min(63, x+s), min(63, y+s)
    for yy in range(y0, y1+1):
        for xx in range(x0, x1+1):
            if x <= xx < x+s and y <= yy < y+s:
                continue
            if g[yy, xx] in (9, 10):
                return False
    return True

def _find_head(g):
    for s in (4, 2):
        h = s // 2
        for y in range(0, 65 - s):
            for x in range(0, 65 - s):
                w = g[y:y+s, x:x+s]
                if not np.all((w == 9) | (w == 10)):
                    continue
                f = None
                if np.all(w[:, :h] == 9) and np.all(w[:, h:] == 10):
                    f = 'L'
                elif np.all(w[:, h:] == 9) and np.all(w[:, :h] == 10):
                    f = 'R'
                elif np.all(w[:h, :] == 9) and np.all(w[h:, :] == 10):
                    f = 'U'
                elif np.all(w[h:, :] == 9) and np.all(w[:h, :] == 10):
                    f = 'D'
                if f and _ring_clear(g, x, y, s):
                    return x, y, s, f
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

def _click_button(g, x, y, head):
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
    if marked == _RECIPE:
        for bx, by in buttons.values():
            g[by:by+3, bx:bx+3] = 2
        if head is not None:
            hx, hy, s, facing = head
            if s >= 4:
                g[hy:hy+s, hx:hx+s] = 2
                ns = s // 2
                g[hy:hy+ns, hx:hx+ns] = _texture(facing, ns)
        return 1, True
    facing = head[3] if head else None
    return (0 if _CELL_DIR.get(hit) == facing else 1), False

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {"paid2": 0, "leftpx": 0})
    h = _find_head(g)
    if action == 6 and x is not None and y is not None:
        paid, completed = _click_button(g, x, y, h)
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
            if np.all(tgt == 2):
                g[hy:hy+s, hx:hx+s] = 2
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                moved = True
                if action == 3:
                    st["leftpx"] = st.get("leftpx", 0) + s
                elif action == 4:
                    pass  # right travel free (does NOT reduce leftpx - unverified)
                else:
                    st["paid2"] = st.get("paid2", 0) + s // 2  # vertical GUESS
        if not moved and facing != f:
            g[hy:hy+s, hx:hx+s] = _texture(f, s)
            if action in (1, 2):
                st["paid2"] = st.get("paid2", 0) + _turn_cost(facing, f) // 2
            else:
                st["paid2"] = st.get("paid2", 0) + 1  # blocked-move turn flat
    _paint_bar(g, _dark_total(st))
    return g.tolist(), info, st
