# v13: head = s x s half-split 9|a overlay block; underlay restored on vacate.
# Card-A click: re-seed recipe 0s, clear orientation, ARM next completion (dissolve).
# Cost: dark = 2*paid2 + 2*round(2M/3); M = toward-base MOVES (any size) since completion.
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
    return {"paid2": 0, "M": 0, "base_bbox": bbox, "oriented": False}

def _dark_total(st):
    # paid2 = flat 2-row events; M = toward-base moves since last completion-bake
    return 2 * st.get("paid2", 0) + 2 * int(2 * st.get("M", 0) / 3.0 + 0.5)

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

def _mark_color():
    """Card A's mark color (the non-red color inside the recipe card at entry)."""
    e = np.array(ENTRY_GRID)
    region = e[51:59, 12:20]
    vals = [int(v) for v in np.unique(region) if v != 2]
    return vals[0] if len(vals) == 1 else None

def _find_pad(g, s):
    """Find an s x s square whose 4 corners are mark-colored -> (px, py, enterable)."""
    mc = _mark_color()
    if mc is None:
        return None
    for py in range(0, 65 - s):
        for px in range(0, 65 - s):
            if (g[py, px] == mc and g[py, px+s-1] == mc
                    and g[py+s-1, px] == mc and g[py+s-1, px+s-1] == mc):
                inner = g[py:py+s, px:px+s].copy()
                corners_ok = np.ones((s, s), dtype=bool)
                corners_ok[0, 0] = corners_ok[0, s-1] = corners_ok[s-1, 0] = corners_ok[s-1, s-1] = False
                enterable = bool(np.all((inner == 2) | (~corners_ok)))
                return px, py, enterable
    return None

def _click_button(g, x, y, head, st):
    """Returns (paid_flag, completed_flag). May mutate st['armed']."""
    oriented = st.get("oriented", False)
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
            if pad is not None and pad[2]:
                # TELEPORT: head jumps onto the enterable mark-cornered pad
                px, py = pad[0], pad[1]
                _vacate(g, hx, hy, s)
                g[py:py+s, px:px+s] = _texture(facing, s)
                fee = 3  # observed L1: +6 rows
            elif pad is not None and st.get("armed"):
                # ARMED completion: DISSOLVE mark-colored structures + d(13) cells in the
                # field (rows < 47) to red (observed L2 s68: box + bridge -> 2)
                mc = _mark_color()
                field = g[0:47, :]
                field[(field == mc) | (field == 13)] = 2
                st["armed"] = False
            elif pad is not None:
                pass  # pad exists but not enterable, unarmed: fizzle (L2 s38, s50), fee 1
            elif s >= 4:
                # no pad at all: shrink in place (L0 behavior)
                _vacate(g, hx, hy, s)
                ns = s // 2
                g[hy:hy+ns, hx:hx+ns] = _texture(facing, ns)
        return fee, True
    facing = head[3] if head else None
    # Freebie: clicked cell lies on the panel SIDE (row/col of 3) of the match-side.
    # match-side = current 9-side if oriented; else OPPOSITE of the ENTRY 9-side
    # (orientation cleared at level entry and by card-A re-arm). Fits all 20 clicks.
    _OPP = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}
    if oriented:
        match_side = facing
    else:
        eh = _find_head(np.array(ENTRY_GRID), None)
        match_side = _OPP.get(eh[3]) if eh else _OPP.get(facing)
    r, c = hit
    in_side = (match_side == 'U' and r == 0) or (match_side == 'D' and r == 2) \
        or (match_side == 'L' and c == 0) or (match_side == 'R' and c == 2)
    # freebie only when MARKING (result = e); unmarking always costs (s65)
    return (0 if (in_side and new == 14) else 1), False

def _card_bbox():
    """Card A's bbox from ENTRY_GRID (3-bordered box containing the mark color)."""
    return (11, 50, 20, 59)  # constant across L0-L2; derive smarter if it moves

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {"paid2": 0, "leftpx": 0})
    h = _find_head(g, st.get("base_bbox"))
    if action == 6 and x is not None and y is not None:
        cx0, cy0, cx1, cy1 = _card_bbox()
        if cx0 <= x <= cx1 and cy0 <= y <= cy1:
            # CARD A CLICK: re-seed recipe cells to 0 AND reset orientation (s62, s66).
            # Pure no-op (cells already 0) changes nothing at all (L0 s9).
            btns = _find_buttons(g)
            changed = False
            for rc in _recipe():
                if rc in btns:
                    bx, by = btns[rc]
                    if not np.all(g[by:by+3, bx:bx+3] == 0):
                        g[by:by+3, bx:bx+3] = 0
                        changed = True
            if changed:
                st["oriented"] = False
                st["armed"] = True  # re-arm charges the next completion (dissolve)
            _paint_bar(g, _dark_total(st))
            return g.tolist(), info, st
        paid, completed = _click_button(g, x, y, h, st)
        st["paid2"] = st.get("paid2", 0) + paid
        if completed:
            # travel contribution bakes into the base; move counter restarts
            st["paid2"] = st.get("paid2", 0) + int(2 * st.get("M", 0) / 3.0 + 0.5)
            st["M"] = 0
    if h is not None and action in (1, 2, 3, 4):
        hx, hy, s, facing = h
        dxy = {1: (0, -1, 'U'), 2: (0, 1, 'D'), 3: (-1, 0, 'L'), 4: (1, 0, 'R')}[action]
        dx, dy, f = dxy[0] * s, dxy[1] * s, dxy[2]
        nx, ny = hx + dx, hy + dy
        moved = False
        engaged = False  # attempted target contains any non-background cell
        if 0 <= nx <= 64 - s and 0 <= ny <= 64 - s:
            tgt = g[ny:ny+s, nx:nx+s]
            engaged = not np.all(tgt == 5)
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
        if moved:
            st["M"] = st.get("M", 0) + 1  # every real move counts (any direction)
        elif facing != f:
            g[hy:hy+s, hx:hx+s] = _texture(f, s)
            if action in (1, 2):
                st["paid2"] = st.get("paid2", 0) + _turn_cost(facing, f) // 2
            else:
                st["paid2"] = st.get("paid2", 0) + 1  # blocked-move turn flat
        elif engaged:
            st["M"] = st.get("M", 0) + 1  # bumping a structure counts; void doesn't
        if moved or facing != f:
            st["oriented"] = True
    _paint_bar(g, _dark_total(st))
    return g.tolist(), info, st
