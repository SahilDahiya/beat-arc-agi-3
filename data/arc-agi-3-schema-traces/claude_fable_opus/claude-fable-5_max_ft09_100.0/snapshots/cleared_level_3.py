# ARC3 world model — "match the glyph" click puzzle (levels 0-3)
# Layout: 3x3 panels of 6x6 tiles spaced 8px; panel center tile = GLYPH:
#   3x3 of 2x2-px cells, inks {0,2} + center color C. Panels may share tiles.
# PALETTE CYCLE: legend blocks at top-right (x60-63, 4 rows each from y=0)
#   list the level's tile colors IN ORDER. Click on a tile advances it to the
#   NEXT color in the cycle (wraps). 2-color levels = simple toggle.
#   lvl0: no legend -> fallback pair {glyph centers} U {tile colors}, base 9.
#   lvl1 [9,c], lvl2 [8,c], lvl3 [9,8,c] (direction 9->8->c->9 = GUESS).
# GLYPH MAP: 0-cell -> C (glyph center color); 2-cell -> D(C) = the color in
#   the ADJACENT legend slot (i+1, else i-1). 2-color levels: D = other color
#   (confirmed lvl0,1,2). lvl3 [9,8,c]: D(9)=D(c)=8 (consistent on shared tiles).
# Goal: ALL panels match their glyphs -> level_up.
# ENERGY BAR: row 63, c(12)->b(11) right-to-left; cumulative cells after n
#   actions = round(n*num/den); per-level _RATE. GUESS: bar empty = dead.

_GEO_CACHE = {}
# level -> (num,den): cumulative drained cells after n actions = round(n*num/den)
_RATE = {0: (2, 1), 1: (2, 1), 2: (2, 3)}
_RATE_DEFAULT = (2, 3)


def _find_glyphs(a):
    H, W = a.shape
    out = []
    for y in range(0, H - 6):
        for x in range(0, W - 5):
            blk = a[y:y + 6, x:x + 6]
            pat = []
            ok = True
            for r in range(3):
                row = []
                for c in range(3):
                    p = blk[2 * r:2 * r + 2, 2 * c:2 * c + 2]
                    v = int(p[0, 0])
                    if not (p == v).all():
                        ok = False
                        break
                    row.append(v)
                if not ok:
                    break
                pat.append(row)
            if not ok:
                continue
            C = pat[1][1]
            if C in (0, 2):
                continue
            flat = [v for row in pat for v in row]
            if any(v not in (0, 2, C) for v in flat):
                continue
            if not any(v in (0, 2) for v in flat):
                continue
            out.append((x, y, pat))
    return out


def _legend(entry, bg):
    cyc = []
    for y in (0, 4, 8, 12):
        blk = entry[y:y + 4, 60:64]
        v = int(blk[0, 0])
        if (blk == v).all() and v != bg and v not in (0, 2):
            cyc.append(v)
        else:
            break
    return cyc


def _geometry(entry):
    """From ENTRY grid: (panels, cycle). cycle = ordered tile colors."""
    key = entry.tobytes()
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
    vals, counts = np.unique(entry, return_counts=True)
    bg = int(vals[np.argmax(counts)])
    panels = []
    for (gx, gy, pat) in _find_glyphs(entry):
        C = pat[1][1]
        tiles = []
        ok = True
        for r in range(3):
            for c in range(3):
                if r == 1 and c == 1:
                    continue
                tx, ty = gx + (c - 1) * 8, gy + (r - 1) * 8
                if tx < 0 or ty < 0 or tx + 6 > entry.shape[1] or ty + 6 > entry.shape[0]:
                    ok = False
                    break
                blk = entry[ty:ty + 6, tx:tx + 6]
                v = int(blk[0, 0])
                if not (blk == v).all() or v == bg or v in (0, 2):
                    ok = False
                    break
                tiles.append((r, c, tx, ty))
            if not ok:
                break
        if ok and len(tiles) == 8:
            panels.append({'gx': gx, 'gy': gy, 'pat': pat, 'C': C, 'tiles': tiles})
    cycle = _legend(entry, bg)
    if len(cycle) < 2:
        pool = set()
        for p in panels:
            pool.add(p['C'])
            for (r, c, tx, ty) in p['tiles']:
                pool.add(int(entry[ty, tx]))
        if len(pool) == 1:
            pool.add(9)
        # base 9 first if present (lvl0 behaviour), rest in sorted order
        cycle = ([9] if 9 in pool else []) + sorted(v for v in pool if v != 9)
    geo = (panels, cycle)
    _GEO_CACHE[key] = geo
    return geo


def _dcolor(cycle, C):
    """Target color for 2-ink cells of a glyph with center C."""
    if C in cycle:
        i = cycle.index(C)
        return cycle[i + 1] if i + 1 < len(cycle) else cycle[i - 1]
    for u in cycle:
        if u != C:
            return u
    return C


def _all_match(a, panels, cycle):
    for p in panels:
        C = p['C']
        D = _dcolor(cycle, C)
        for (r, c, tx, ty) in p['tiles']:
            want = C if p['pat'][r][c] == 0 else D
            if a[ty, tx] != want:
                return False
    return True


def _cum_cells(n, num, den):
    return (2 * n * num + den) // (2 * den)  # round-half-up(n*num/den)


def init_state(entry_grid):
    return {'n': 0}


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    n0 = int(state.get('n', 0))
    a = np.array(grid)
    b = a.copy()
    panels, cycle = _geometry(np.array(ENTRY_GRID))
    if action == 0:
        return grid, info, {'n': 0}
    if action == 6 and x is not None and y is not None:
        hit = False
        for p in panels:
            for (r, c, tx, ty) in p['tiles']:
                if tx <= x < tx + 6 and ty <= y < ty + 6:
                    v = int(b[ty, tx])
                    if v in cycle:
                        nxt = cycle[(cycle.index(v) + 1) % len(cycle)]
                        b[ty:ty + 6, tx:tx + 6] = nxt
                    hit = True
                    break
            if hit:
                break
    n1 = n0 + 1
    num, den = _RATE.get(CURRENT_LEVEL, _RATE_DEFAULT)
    dcells = _cum_cells(n1, num, den) - _cum_cells(n0, num, den)
    if (b[63] == 12).any() or (b[63] == 11).any():
        for _ in range(dcells):
            idxs = np.where(b[63] == 12)[0]
            if len(idxs):
                b[63, idxs[-1]] = 11
        if not (b[63] == 12).any():
            info["dead"] = True  # GUESS: bar empty = out of moves
    if panels and _all_match(b, panels, cycle):
        info["level_up"] = True
    return b.tolist(), info, {'n': n1}


def is_goal(grid):
    a = np.array(grid)
    panels, cycle = _geometry(np.array(ENTRY_GRID))
    return bool(panels) and _all_match(a, panels, cycle)
