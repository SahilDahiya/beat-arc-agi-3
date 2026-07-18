# v20: VERB THEORY: card PATTERN = verb: {N,W,E,S}=size-toggle; {NW,N,C}=teleport to
# card-color pad (f-solid pad first, else nearest); {N,C,S}=dissolve: raycast ahead
# (skip {2,4,13}; fail {5,9,10}); hit structure flood-filled; WHIFF unless card color in
# its colors; else destroy the structure's cells + wipe its payload colors
# (colors - cardcolor) globally in the field (cards/panel excluded). NO cross-structure rider.
# WORLD: s x s half-split 9|a HEAD; walkable target = all {2,11,15} (pad-walk); all-10 = DOCK;
#   {2,14}-mix = E-PICKUP (consume block, refund m moves). Vacate restores ENTRY 11/15 else 2.
#   Blocked+facing!=dir -> turn in place (CCW free, CW/180 costs 1). Bump = free.
# RINGS render by head size: b outer 6x6 corners visible iff s==4; f-station 6x6 f-corners
#   visible iff s==2; 2x2 rings/inner corners/f-solid always (unless covered).
# CARDS/PANEL: 10x10 3-framed cards = (pattern,color); panel 3x3 cells toggle 2<->14, 0->14;
#   completion (marked==pattern) clears panel, fires verb.
# COSTS (L>=3): counter c; bar od = 2*floor(c/2), clamp [0,64]; od==64 -> DEATH.
#   c: level entry starts -2 (grace). +1 mark/unmark/move; +2 completion (any, incl whiff);
#   +3 successful teleport; 0: card-click, bump, CCW turn; +1 CW/180 blocked-turn.
#   E-pickup: c -= m (moves since last completion), pickup move free.
# L0-2 legacy costs kept: dark=2*paid2+2*round(2M/3), side-freebie clicks (old model).

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
    # c=0: L5 entry showed NO grace (move+mark -> od 2). L4's #146/#147 free opening
    # marks remain unexplained (2 tolerated backtest residuals; self-heal covers).
    pad4 = None
    try:
        geo = _pad_geo()
        for sx, sy in geo['pads4']:
            if g[sy-1, sx-1] == geo['color']:
                pad4 = (sx, sy)
    except Exception:
        pad4 = None
    return {"paid2": 0, "M": 0, "c": 0, "m": 0, "base_bbox": bbox, "oriented": False,
            "armed": False, "free_side": fs, "ccount": {}, "pad4_next": pad4}

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
    # restore scenery underlay (pad corners 11 / f-station 15) from ENTRY, else red
    e = np.array(ENTRY_GRID)
    for yy in range(y, y + s):
        for xx in range(x, x + s):
            g[yy, xx] = e[yy, xx] if e[yy, xx] in (11, 15) else 2

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

_RINGS_CACHE = {}

def _ring_cells():
    """Size-dependent ring corner cells, derived from ENTRY (head starts 4x4):
    - 'b4': outer 6x6 ring corners of 4x4 pad landings (visible iff head 4x4)
    - 'f':  6x6 f-ring corners around b-ringed f-solid stations (visible iff head 2x2)"""
    key = (CURRENT_LEVEL, int(np.array(ENTRY_GRID).sum()))
    if key in _RINGS_CACHE:
        return _RINGS_CACHE[key]
    e = np.array(ENTRY_GRID)
    f_ring = []
    b4 = []
    for y in range(1, 61):
        for x in range(1, 59):
            if np.all(e[y:y+2, x:x+2] == 15) and not _excluded(x, y, 2):
                if (e[y-1, x-1] == 11 and e[y-1, x+2] == 11
                        and e[y+2, x-1] == 11 and e[y+2, x+2] == 11):
                    for rx, ry in ((x-2, y-2), (x+3, y-2), (x-2, y+3), (x+3, y+3)):
                        if 0 <= rx < 62 and 0 <= ry < 64:
                            f_ring.append((rx, ry))
    for y in range(0, 58):
        for x in range(0, 56):
            if (e[y, x] == 11 and e[y, x+5] == 11 and e[y+5, x] == 11
                    and e[y+5, x+5] == 11 and not _excluded(x, y, 6)):
                inner = e[y+1:y+5, x+1:x+5]
                ok = True
                for yy in range(4):
                    for xx in range(4):
                        v = int(inner[yy, xx])
                        if v == 2 or v == 15:
                            continue
                        if v == 11 and yy in (0, 3) and xx in (0, 3):
                            continue
                        ok = False
                if ok:
                    b4.extend([(x, y), (x+5, y), (x, y+5), (x+5, y+5)])
    _RINGS_CACHE.clear()
    _RINGS_CACHE[key] = {'f': f_ring, 'b4': b4}
    return _RINGS_CACHE[key]

_P_TOGGLE = frozenset({(0, 1), (1, 0), (1, 2), (2, 1)})   # plus {N,W,E,S}
_P_TELE = frozenset({(0, 0), (0, 1), (1, 1)})             # {NW,N,C}
_P_DISS = frozenset({(0, 1), (1, 1), (2, 1)})             # {N,C,S}

_PAD_GEO_CACHE = {}

def _pad_geo():
    """L5 pad geometry from ENTRY: 4x4 landings (top-lefts) derived from always-visible
    2x2 quads of the teleport-card color; station (super-landing holds f-solid) yields
    f-ring corners instead. Returns {'color', 'pads4': [(sx,sy)...], 'fring': [(x,y)...]}"""
    key = (CURRENT_LEVEL, int(np.array(ENTRY_GRID).sum()))
    if key in _PAD_GEO_CACHE:
        return _PAD_GEO_CACHE[key]
    e = np.array(ENTRY_GRID)
    color = 11
    for x0, y0, p, c in _cards():
        if p == _P_TELE:
            color = c
    pads4 = []
    fring = []
    for py2 in range(2, 58):
        for px2 in range(2, 58):
            if not (e[py2-1, px2-1] == color and e[py2-1, px2+2] == color
                    and e[py2+2, px2-1] == color and e[py2+2, px2+2] == color):
                continue
            if _excluded(px2-1, py2-1, 4):
                continue
            sx, sy = px2 - 1, py2 - 1
            w = e[sy:sy+4, sx:sx+4]
            if np.any(w == 15):
                for rx, ry in ((sx-1, sy-1), (sx+4, sy-1), (sx-1, sy+4), (sx+4, sy+4)):
                    if 0 <= rx < 62 and 0 <= ry < 64:
                        fring.append((rx, ry))
            elif np.all((w == 2) | (w == color) | (w == 9) | (w == 10)):
                pads4.append((sx, sy))
    _PAD_GEO_CACHE.clear()
    _PAD_GEO_CACHE[key] = {'color': color, 'pads4': pads4, 'fring': fring}
    return _PAD_GEO_CACHE[key]

def _find_pad(g, s, color, head=None):
    """Pad = 4 `color` cells at the corners of an (s+2)x(s+2) ring; landing = the s x s
    interior. Interior may hold f-solid(15) or `color` marks at its OWN corners
    (inner-ring render); anything else -> not enterable. Choice: f-solid first,
    then nearest to head, then scan order."""
    cands = []
    for py in range(1, 63 - s):
        for px in range(1, 63 - s):
            if not (g[py-1, px-1] == color and g[py-1, px+s] == color
                    and g[py+s, px-1] == color and g[py+s, px+s] == color):
                continue
            if _excluded(px-1, py-1, s+2):
                continue
            ok = True
            for yy in range(s):
                for xx in range(s):
                    v = int(g[py+yy, px+xx])
                    if v == 2 or v == 15:
                        continue
                    if v == color and yy in (0, s-1) and xx in (0, s-1):
                        continue
                    ok = False
            if ok:
                cands.append((px, py))
    if not cands:
        return None
    def rank(c):
        px, py = c
        hasf = bool(np.any(g[py:py+s, px:px+s] == 15))
        d = abs(px - head[0]) + abs(py - head[1]) if head is not None else 0
        return (0 if hasf else 1, d, py, px)
    cands.sort(key=rank)
    px, py = cands[0]
    return px, py, True

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

def _ray_target(g, head, color):
    """Raycast straight ahead. Skips {2,4,13}; fails on {5,9,10}. On hit: flood the
    struck structure; WHIFF (None) unless `color` (card color) is among its colors.
    Returns (cells, colors) of the structure."""
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
            seed = [(edge_x, yy) for yy in range(cy, cy+s)
                    if int(g[yy, edge_x]) not in (2, 4)]
        else:
            edge_y = cy if dy < 0 else cy + s - 1
            line = g[edge_y, cx:cx+s]
            seed = [(xx, edge_y) for xx in range(cx, cx+s)
                    if int(g[edge_y, xx]) not in (2, 4)]
        vals = set(int(v) for v in line)
        if vals <= {2, 4}:
            continue  # transparent: red floor + gates only (d/13 BLOCKS: L5 s291 whiff)
        if vals & {5, 9, 10}:
            return None
        seen = set(seed)
        stack = list(seed)
        colors = set()
        while stack:
            xx, yy = stack.pop()
            colors.add(int(g[yy, xx]))
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx2, ny2 = xx + ddx, yy + ddy
                if 0 <= nx2 < 62 and 0 <= ny2 < 64 and (nx2, ny2) not in seen:
                    if int(g[ny2, nx2]) not in (2, 4, 5, 9, 10):
                        seen.add((nx2, ny2))
                        stack.append((nx2, ny2))
        if color not in colors:
            return None  # wrong family -> whiff
        return seen, colors
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
        tele_success = False
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
                    # GROW: terrain-adaptive; prefer keep-bottom-right (hx-s,hy-s),
                    # else nearest all-red ns x ns square containing the old footprint
                    ns = s * 2
                    best = None
                    for gy in range(max(0, hy - s), min(64 - ns, hy) + 1):
                        for gx in range(max(0, hx - s), min(64 - ns, hx) + 1):
                            w = g[gy:gy+ns, gx:gx+ns]
                            m = np.ones((ns, ns), dtype=bool)
                            m[hy-gy:hy-gy+s, hx-gx:hx-gx+s] = False
                            if np.all((w == 2) | (w == 11) | (w == 15) | (~m)):
                                pri = (0 if (gx == hx - s and gy == hy - s) else 1,
                                       abs(gx - (hx - s)) + abs(gy - (hy - s)), gy, gx)
                                if best is None or pri < best[0]:
                                    best = (pri, gx, gy)
                    if best is not None:
                        _vacate(g, hx, hy, s)
                        gx, gy = best[1], best[2]
                        g[gy:gy+ns, gx:gx+ns] = _texture(facing, ns)
                fee = 1 + click_cost
            elif pattern == _P_TELE:
                # TELEPORT verb: jump onto the enterable pad of the card's color
                pad = _find_pad(g, s, color, (hx, hy))
                if pad is not None and pad[2]:
                    px, py = pad[0], pad[1]
                    _vacate(g, hx, hy, s)
                    g[py:py+s, px:px+s] = _texture(facing, s)
                    fee = 3
                    tele_success = True
                    if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5 and s == 4:
                        # L5: landing a 4x4 teleport ARMS the other 4x4 pad
                        others = [p for p in _pad_geo()['pads4'] if p != (px, py)]
                        if others:
                            st["pad4_next"] = others[0]
                else:
                    fee = 1 if CURRENT_LEVEL == 2 else 1 + click_cost
            elif pattern == _P_DISS:
                # DISSOLVE verb: destroy the aimed card-color structure; wipe its
                # payload colors (colors - cardcolor) globally in the field
                hitres = _ray_target(g, head, color)
                if hitres is not None:
                    cells, colors = hitres
                    payload = colors - {color}
                    for xx, yy in cells:
                        g[yy, xx] = 2
                    for yy in range(64):
                        for xx in range(62):
                            if int(g[yy, xx]) in payload and not _excluded(xx, yy, 1):
                                g[yy, xx] = 2
                    if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5 and cells:
                        # L5: destroyed structure drops a 2x2 E-PICKUP at its bbox top-left
                        bx0 = min(p[0] for p in cells)
                        by0 = min(p[1] for p in cells)
                        g[by0:by0+2, bx0:bx0+2] = 14
                    fee = 1
                else:
                    fee = 1 if CURRENT_LEVEL == 2 else 1 + click_cost
            else:
                fee = 1 + click_cost
        if st.get("legacy"):
            st["paid2"] = st.get("paid2", 0) + fee
            st["paid2"] = st.get("paid2", 0) + _move_contrib(st.get("M", 0)) // 2
            st["M"] = 0
        else:
            st["c"] = st.get("c", 0) + 2  # completion fee (tele ambiguous 2-3; 2 fits most)
            st["m"] = 0
        st["armed"] = False  # any completion consumes the arm (s84 wasted it; s93 proved)
        return info_level_up
    # click cost
    if st.get("legacy"):
        facing = head[3] if head else None
        match_side = facing if st.get("oriented", False) else st.get("free_side")
        r, c2 = hit
        in_side = (match_side == 'U' and r == 0) or (match_side == 'D' and r == 2) \
            or (match_side == 'L' and c2 == 0) or (match_side == 'R' and c2 == 2)
        if not (in_side and new == 14):
            st["paid2"] = st.get("paid2", 0) + 1
    else:
        st["c"] = st.get("c", 0) + 1
    return info_level_up

def _observed_dark(g):
    n = 0
    while n < 64 and g[n, 62] == 0 and g[n, 63] == 0:
        n += 1
    return n

def _pred_od(c):
    return min(64, max(0, 2 * (c // 2)))

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    info = {"level_up": False, "dead": False, "win": False}
    st = dict(state or {"paid2": 0, "M": 0, "c": 0, "m": 0})
    legacy = CURRENT_LEVEL is None or CURRENT_LEVEL <= 3
    st["legacy"] = legacy
    # SELF-HEAL: re-anchor cost state to the observed bar (prevents drift)
    od = _observed_dark(g)
    if legacy:
        mc = _move_contrib(st.get("M", 0))
        st["paid2"] = max(0, (od - mc) // 2)
    else:
        c = st.get("c", 0)
        if _pred_od(c) != od:
            c = od
        st["c"] = c
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
        picked = False
        if 0 <= nx <= 64 - s and 0 <= ny <= 64 - s:
            tgt = g[ny:ny+s, nx:nx+s]
            engaged = not np.all(tgt == 5)
            if np.all(tgt == 10):
                _vacate(g, hx, hy, s)
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                info["level_up"] = True
                moved = True
            elif np.any(tgt == 14) and np.all((tgt == 2) | (tgt == 14)):
                # E-BLOCK = ENERGY PICKUP: move onto it; whole block consumed
                _vacate(g, hx, hy, s)
                x0s, y0s = max(0, nx - 3), max(0, ny - 3)
                sub = g[y0s:ny+s+3, x0s:min(62, nx+s+3)]
                sub[sub == 14] = 2
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                moved = True
                picked = True
            elif np.all((tgt == 2) | (tgt == 11) | (tgt == 15)):
                # walkable: red floor + pad ring corners (11) + f-solid (15)
                _vacate(g, hx, hy, s)
                g[ny:ny+s, nx:nx+s] = _texture(f, s)
                moved = True
        if legacy:
            if moved:
                if picked:
                    st["M"] = 0
                elif CURRENT_LEVEL == 3 and _head_touches(g, nx, ny, s, None):
                    pass  # L3: arrival adjacent to a structure = free
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
        else:
            if moved:
                if picked:
                    st["c"] = st.get("c", 0) - st.get("m", 0)
                    st["m"] = 0
                else:
                    st["c"] = st.get("c", 0) + 1
                    st["m"] = st.get("m", 0) + 1
            elif facing != f:
                g[hy:hy+s, hx:hx+s] = _texture(f, s)
                st["c"] = st.get("c", 0) + _turn_cost(facing, f) // 2
    # RENDER: size-dependent ring visibility
    hh = _find_head(g, st.get("base_bbox"))
    s_now = hh[2] if hh is not None else None
    def _covered(cx3, cy3):
        return hh is not None and hh[0] <= cx3 < hh[0]+hh[2] and hh[1] <= cy3 < hh[1]+hh[2]
    if CURRENT_LEVEL is None or CURRENT_LEVEL <= 4:
        rings = _ring_cells()
        for rx, ry in rings['f']:
            if not _covered(rx, ry):
                g[ry, rx] = 15 if s_now == 2 else 5
        for rx, ry in rings['b4']:
            if not _covered(rx, ry):
                g[ry, rx] = 11 if s_now == 4 else 5
    else:
        # L5+: 4x4 outer ring shows only on the ARMED pad while head is 4x4;
        # station f-ring shows while head is 2x2; hidden cells revert to ENTRY terrain
        geo = _pad_geo()
        e2 = np.array(ENTRY_GRID)
        armed = st.get("pad4_next")
        for sx, sy in geo['pads4']:
            show = (s_now == 4 and armed == (sx, sy))
            for cx3, cy3 in ((sx-1, sy-1), (sx+4, sy-1), (sx-1, sy+4), (sx+4, sy+4)):
                if 0 <= cx3 < 62 and 0 <= cy3 < 64 and not _covered(cx3, cy3):
                    g[cy3, cx3] = geo['color'] if show else (2 if e2[cy3, cx3] == 2 else 5)
        for cx3, cy3 in geo['fring']:
            if 0 <= cx3 < 62 and 0 <= cy3 < 64 and not _covered(cx3, cy3):
                g[cy3, cx3] = 15 if s_now == 2 else (2 if e2[cy3, cx3] == 2 else 5)
    dark = _dark_total(st) if legacy else _pred_od(st.get("c", 0))
    _paint_bar(g, dark)
    if dark >= 64:
        info["dead"] = True
    return g.tolist(), info, st
