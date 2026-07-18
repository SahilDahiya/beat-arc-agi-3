# v19: VERB THEORY: card PATTERN = the verb: {N,W,E,S}=size-toggle (always);
# {NW,N,C}=teleport to enterable card-color pad (no aim needed); {N,C,S}=dissolve via
# RAYCAST ahead (skip 2/4/13; fail on 5/9/10; wipe first structure's colors +13 globally).
# WORLD: s x s half-split 9|a HEAD (overlay; underlay restores on vacate: 11/b of entry, else red).
#   a1/a2/a3/a4 move U/D/L/R by s onto all-red target (facing := dir); all-'a'(10) target = DOCK
#   (level_up). Blocked+facing!=dir -> turn in place. Blocked+same-facing: nothing visible.
# CARDS: 10x10 3-framed boxes in ENTRY_GRID; marks = 2x2 blocks of a non-red color at
#   3x3 lattice (rel 1/4/7); each card = (pattern set, color).
# PANEL: 3x3 of 3x3px cells (0/2/14) framed by 3s. Click toggles: 2<->14, 0->14.
# CARD CLICK: re-seeds that card's pattern cells to 0, clears orientation, ARMS completion.
#   (pure no-op if already all-0)
# COMPLETION (marked cells == some card's pattern): panel clears to all-2, fee 1 (3 if teleport);
#   effect: if card-colored 4-corner pad (size s) with red interior -> TELEPORT head onto it;
#   elif such pad exists (not enterable) and ARMED -> DISSOLVE card-color + d(13) cells in field
#   (rows<47... use non-card area) to red; elif armed/not but no pad -> SHRINK s -> s/2 (top-left).
# COSTS: dark = 2*paid2 + 2*round(2M/3). paid2 += 1: CW/180 a1-a2 turns, blocked-move turns,
#   non-freebie clicks, completion (3 if teleport); M += 1 per move-attempt engaging non-bg;
#   at completion M bakes: paid2 += round(2M/3), M=0.
#   Click freebie: MARK (->14) whose cell lies on panel side (row/col of 3) of match-side;
#   match-side = 9-side if oriented else OPPOSITE of entry 9-side. Unmark always paid.

def _find_cards_raw(g):
    """All 10x10 3-framed cards: list of (x0, y0, pattern frozenset, color)."""
    cards = []
    for y0 in range(0, 55):
        for x0 in range(0, 55):
            if g[y0, x0] != 3:
                continue
            # frame check
            if not (np.all(g[y0, x0:x0+10] == 3) and np.all(g[y0+9, x0:x0+10] == 3)
                    and np.all(g[y0:y0+10, x0] == 3) and np.all(g[y0:y0+10, x0+9] == 3)):
                continue
            interior = g[y0+1:y0+9, x0+1:x0+9]
            vals = set(int(v) for v in np.unique(interior))
            if not vals <= {2, 6, 11, 14, 15, 13, 0, 4, 1, 7, 8, 12}:
                continue
            if 3 in vals or 5 in vals or 9 in vals or 10 in vals:
                continue
            colors = vals - {2}
            if len(colors) != 1:
                continue
            color = colors.pop()
            pattern = set()
            ok = True
            for r in range(3):
                for c in range(3):
                    block = g[y0+1+3*r:y0+3+3*r, x0+1+3*c:x0+3+3*c]
                    if np.all(block == color):
                        pattern.add((r, c))
                    elif not np.all(block == 2):
                        ok = False
            if ok and pattern:
                cards.append((x0, y0, frozenset(pattern), color))
    cards.sort(key=lambda t: (t[1], t[0]))
    return cards

_CARDS_CACHE = {}

def _cards():
    key = (CURRENT_LEVEL, int(np.array(ENTRY_GRID).sum()))
    if key not in _CARDS_CACHE:
        _CARDS_CACHE.clear()
        _CARDS_CACHE[key] = _find_cards_raw(np.array(ENTRY_GRID))
    return _CARDS_CACHE[key]

_CCW = {'L': 'D', 'D': 'R', 'R': 'U', 'U': 'L'}
_OPP = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}

def _turn_cost(old, new):
    if old == new or _CCW[old] == new:
        return 0
    return 2

def _find_head(g, base_bbox=None):
    for s in (4, 2):
        h = s // 2
        for y in range(0, 65 - s):
            for x in range(0, 65 - s):
                if base_bbox is not None:
                    bx0, by0, bx1, by1 = base_bbox
                    if not (x + s - 1 < bx0 or x > bx1 or y + s - 1 < by0 or y > by1):
                        continue
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

def init_state(entry_grid):
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
    fs = None
    if h is not None:
        fs = _OPP.get(h[3])
    return {"paid2": 0, "M": 0, "base_bbox": bbox, "oriented": False, "armed": False,
            "free_side": fs, "ccount": {}}

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

def _move_contrib(m):
    # L3+ observed: 1 unit (2 rows) per move; earlier levels: 2 rows per 3 moves (rounded)
    if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 3:
        return 2 * m
    return 2 * int(2 * m / 3.0 + 0.5)

def _dark_total(st):
    return 2 * st.get("paid2", 0) + _move_contrib(st.get("M", 0))

def _paint_bar(g, dark):
    dark = min(64, dark)
    for r in range(64):
        v = 0 if r < dark else 14
        g[r, 62] = v
        g[r, 63] = v

def _vacate(g, x, y, s):
    e = np.array(ENTRY_GRID)
    for yy in range(y, y + s):
        for xx in range(x, x + s):
            g[yy, xx] = 11 if e[yy, xx] == 11 else 2

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
    if len(xs) != 3 or len(ys) != 3:
        return {}
    return {(ys.index(cy), xs.index(cx)): (cx, cy) for cx, cy in cells}

def _excluded(px, py, s):
    """Square intersects a card or the panel area? (pads live in the field)"""
    for cx0, cy0, pattern, color in _cards():
        if px <= cx0 + 9 and px + s - 1 >= cx0 and py <= cy0 + 9 and py + s - 1 >= cy0:
            return True
    # panel zone: approximate from ENTRY buttons
    e = np.array(ENTRY_GRID)
    btns = _find_buttons(e)
    if btns:
        xs = [c[0] for c in btns.values()]
        ys = [c[1] for c in btns.values()]
        bx0, bx1 = min(xs) - 2, max(xs) + 4
        by0, by1 = min(ys) - 2, max(ys) + 4
        if px <= bx1 and px + s - 1 >= bx0 and py <= by1 and py + s - 1 >= by0:
            return True
    return False

def _find_pad(g, s, color):
    for py in range(0, 65 - s):
        for px in range(0, 65 - s):
            if (g[py, px] == color and g[py, px+s-1] == color
                    and g[py+s-1, px] == color and g[py+s-1, px+s-1] == color):
                if _excluded(px, py, s):
                    continue
                inner = g[py:py+s, px:px+s].copy()
                mask = np.ones((s, s), dtype=bool)
                mask[0, 0] = mask[0, s-1] = mask[s-1, 0] = mask[s-1, s-1] = False
                enterable = bool(np.all((inner == 2) | (~mask)))
                return px, py, enterable
    return None

def _aimed_at(head, px, py, ps):
    """Head aligned with pad span (perpendicular axis) and facing toward it."""
    hx, hy, s, facing = head
    if facing in ('L', 'R'):
        if not (py <= hy and hy + s <= py + ps):
            return False
        return (px + ps <= hx) if facing == 'L' else (px >= hx + s)
    else:
        if not (px <= hx and hx + s <= px + ps):
            return False
        return (py + ps <= hy) if facing == 'U' else (py >= hy + s)

def _head_touches(g, hx, hy, s, color):
    """Any STRUCTURE cell (not floor/bg/base) in the ring around the head footprint?
    (L2 dissolve fired while touching the yellow gate: any structure counts.)"""
    for yy in range(max(0, hy-1), min(64, hy+s+1)):
        for xx in range(max(0, hx-1), min(62, hx+s+1)):
            if hx <= xx < hx+s and hy <= yy < hy+s:
                continue
            if g[yy, xx] not in (2, 5, 9, 10):
                return True
    return False

def _color_struct_bbox(g, color):
    """Bbox (x, y, w, h) of card-colored cells in the field (outside cards/panel)."""
    pts = []
    for y in range(64):
        for x in range(62):
            if g[y, x] == color and not _excluded(x, y, 1):
                pts.append((x, y))
    if not pts:
        return None
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    return (x0, y0, x1 - x0 + 1, y1 - y0 + 1)

def _color_in_field(g, color):
    """Does the color appear anywhere outside cards/panel/bar columns?"""
    for y in range(64):
        for x in range(62):
            if g[y, x] == color and not _excluded(x, y, 1):
                return True
    return False

def _card_hit(x, y):
    for cx0, cy0, pattern, color in _cards():
        if cx0 <= x < cx0 + 10 and cy0 <= y < cy0 + 10:
            return pattern, color
    return None

def _ray_target(g, head):
    """Raycast straight ahead of the head. Skips floor(2) and transparent {4,13}.
    Fails on bg/base {5,9,10}. Returns the first structure's wipe-colors, or None."""
    hx, hy, s, facing = head
    dx = -1 if facing == 'L' else 1 if facing == 'R' else 0
    dy = -1 if facing == 'U' else 1 if facing == 'D' else 0
    cx, cy = hx, hy
    for _ in range(64):
        cx += dx
        cy += dy
        if cx < 0 or cy < 0 or cx + s > 64 or cy + s > 64:
            return None
        if dx != 0:
            edge_x = cx if dx < 0 else cx + s - 1
            if edge_x >= 62:
                return None
            line = g[cy:cy+s, edge_x]
        else:
            edge_y = cy if dy < 0 else cy + s - 1
            line = g[edge_y, cx:cx+s]
        vals = set(int(v) for v in line)
        if vals <= {2}:
            continue
        if vals <= {2, 4, 13}:
            continue  # transparent scenery
        if vals & {5, 9, 10}:
            return None
        return (vals - {2, 4, 13}) | {13}
    return None

def _click(g, x, y, head, st):
    """Handle action 6. Mutates g and st. Returns True if grid changed."""
    info_level_up = False
    hit_card = _card_hit(x, y)
    if hit_card is not None:
        pattern, color = hit_card
        btns = _find_buttons(g)
        changed = False
        for rc in pattern:
            if rc in btns:
                bx, by = btns[rc]
                if not np.all(g[by:by+3, bx:bx+3] == 0):
                    g[by:by+3, bx:bx+3] = 0
                    changed = True
        if changed:
            st["oriented"] = False
            st["armed"] = True
        return info_level_up
    buttons = _find_buttons(g)
    hit = None
    for rc, (cx, cy) in buttons.items():
        if cx <= x < cx+3 and cy <= y < cy+3:
            hit = rc
            break
    if hit is None:
        return info_level_up
    cx, cy = buttons[hit]
    c = g[cy, cx]
    new = {2: 14, 14: 2, 0: 14}[c]
    g[cy:cy+3, cx:cx+3] = new
    marked = frozenset(rc for rc, (bx, by) in buttons.items() if g[by, bx] == 14)
    completed = None
    for cx0, cy0, pattern, color in _cards():
        if marked == pattern:
            completed = (pattern, color)
            break
    if completed is not None:
        pattern, color = completed
        for bx, by in buttons.values():
            g[by:by+3, bx:bx+3] = 2
        # completing-click's own cost (used by shrink fee)
        facing0 = head[3] if head else None
        ms = facing0 if st.get("oriented", False) else st.get("free_side")
        rr, cc = hit
        in_side0 = (ms == 'U' and rr == 0) or (ms == 'D' and rr == 2) \
            or (ms == 'L' and cc == 0) or (ms == 'R' and cc == 2)
        click_cost = 0 if in_side0 else 1
        fee = 1
        _P_TOGGLE = frozenset({(0, 1), (1, 0), (1, 2), (2, 1)})   # plus {N,W,E,S}
        _P_TELE = frozenset({(0, 0), (0, 1), (1, 1)})             # {NW,N,C}
        _P_DISS = frozenset({(0, 1), (1, 1), (2, 1)})             # {N,C,S}
        if head is not None:
            hx, hy, s, facing = head
            if pattern == _P_TOGGLE:
                # SIZE-TOGGLE verb: shrink (keep top-left quadrant) or grow (anchor BR)
                if s >= 4:
                    _vacate(g, hx, hy, s)
                    ns = s // 2
                    g[hy:hy+ns, hx:hx+ns] = _texture(facing, ns)
                    st["free_side"] = 'L' if facing in ('U', 'D') else 'U'
                else:
                    ns = s * 2
                    gx, gy = hx - s, hy - s
                    if 0 <= gx and 0 <= gy:
                        _vacate(g, hx, hy, s)
                        g[gy:gy+ns, gx:gx+ns] = _texture(facing, ns)
                fee = 1 + click_cost
            elif pattern == _P_TELE:
                # TELEPORT verb: jump onto the enterable pad of the card's color
                pad = _find_pad(g, s, color)
                if pad is not None and pad[2]:
                    px, py = pad[0], pad[1]
                    _vacate(g, hx, hy, s)
                    g[py:py+s, px:px+s] = _texture(facing, s)
                    fee = 3
                else:
                    fee = 1 if CURRENT_LEVEL == 2 else 1 + click_cost
            elif pattern == _P_DISS:
                # DISSOLVE verb: raycast ahead; wipe target colors (+13) globally
                colors = _ray_target(g, head)
                if colors is not None:
                    for yy in range(64):
                        for xx in range(62):
                            if int(g[yy, xx]) in colors and not _excluded(xx, yy, 1):
                                g[yy, xx] = 2
                    fee = 1
                else:
                    fee = 1 if CURRENT_LEVEL == 2 else 1 + click_cost
            else:
                fee = 1 + click_cost
        st["paid2"] = st.get("paid2", 0) + fee
        st["paid2"] = st.get("paid2", 0) + _move_contrib(st.get("M", 0)) // 2
        st["M"] = 0
        st["armed"] = False  # any completion consumes the arm (s84 wasted it; s93 proved)
        return info_level_up
    # click cost
    facing = head[3] if head else None
    match_side = facing if st.get("oriented", False) else st.get("free_side")
    r, c2 = hit
    in_side = (match_side == 'U' and r == 0) or (match_side == 'D' and r == 2) \
        or (match_side == 'L' and c2 == 0) or (match_side == 'R' and c2 == 2)
    if not (in_side and new == 14):
        st["paid2"] = st.get("paid2", 0) + 1
    return info_level_up

def _observed_dark(g):
    n = 0
    while n < 64 and g[n, 62] == 0 and g[n, 63] == 0:
        n += 1
    return n

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {"paid2": 0, "M": 0})
    # SELF-HEAL: re-anchor paid2 so formula matches the observed bar (prevents drift)
    od = _observed_dark(g)
    mc = _move_contrib(st.get("M", 0))
    st["paid2"] = max(0, (od - mc) // 2)
    h = _find_head(g, st.get("base_bbox"))
    if action == 6 and x is not None and y is not None:
        _click(g, x, y, h, st)
    if h is not None and action in (1, 2, 3, 4):
        hx, hy, s, facing = h
        dxy = {1: (0, -1, 'U'), 2: (0, 1, 'D'), 3: (-1, 0, 'L'), 4: (1, 0, 'R')}[action]
        dx, dy, f = dxy[0] * s, dxy[1] * s, dxy[2]
        nx, ny = hx + dx, hy + dy
        moved = False
        engaged = False
        if 0 <= nx <= 64 - s and 0 <= ny <= 64 - s:
            tgt = g[ny:ny+s, nx:nx+s]
            engaged = not np.all(tgt == 5)
            if np.all(tgt == 10):
                _vacate(g, hx, hy, s)
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                info["level_up"] = True
                moved = True
            elif np.all(tgt == 2):
                _vacate(g, hx, hy, s)
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                moved = True
            elif np.any(tgt == 14) and np.all((tgt == 2) | (tgt == 14)):
                # E-BLOCK = ENERGY PICKUP: normal move onto it; whole block consumed
                # (-> red) and bar refunds 2 rows (s138).
                _vacate(g, hx, hy, s)
                x0s, y0s = max(0, nx - 3), max(0, ny - 3)
                sub = g[y0s:ny+s+3, x0s:min(62, nx+s+3)]
                sub[sub == 14] = 2
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                st["M"] = 0  # pickup refunds ALL unbaked move costs (s138: 44->28 dark)
                st["_picked"] = True
                moved = True
        if moved:
            if st.pop("_picked", False):
                pass  # pickup move: M already zeroed, move itself free
            # L3+: arrival adjacent to a structure = free (s106). Earlier levels: always counts.
            elif (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 3) and _head_touches(g, nx, ny, s, None):
                pass
            else:
                st["M"] = st.get("M", 0) + 1
        elif facing != f:
            g[hy:hy+s, hx:hx+s] = _texture(f, s)
            if action in (1, 2):
                st["paid2"] = st.get("paid2", 0) + _turn_cost(facing, f) // 2
            else:
                st["paid2"] = st.get("paid2", 0) + 1
        elif engaged:
            st["M"] = st.get("M", 0) + 1
        if moved or facing != f:
            st["oriented"] = True
    _paint_bar(g, _dark_total(st))
    return g.tolist(), info, st
