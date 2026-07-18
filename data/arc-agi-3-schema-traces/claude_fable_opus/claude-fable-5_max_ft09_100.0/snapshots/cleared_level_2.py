# ARC3 world model — "match the glyph" click puzzle (levels 0,1,2)
# Layout: 3x3 panels of 6x6 tiles spaced 8px; panel center tile = GLYPH:
#   3x3 of 2x2-px cells, colors subset of {0,2,C}, C = center cell color,
#   at least one cell in {0,2}. Panels may SHARE tiles (overlapping panels).
# PALETTE PAIR: 2 tile colors = {glyph centers} | {entry tile colors}
#   (legend top-right). lvl0 {8,9}, lvl1 {9,12}, lvl2 {8,12}.
# CONFIRMED: click toggles a tile between the pair colors.
# GLYPH MAP: 0-cell -> C; 2-cell -> other pair color. Goal: all panels match.
# ENERGY BAR: row 63, c(12) -> b(11) right-to-left. Cumulative cells after n
#   actions = ceil(n * num/den), per-level rate: lvl0 2/1, lvl1 2/1, lvl2 1/2.
#   (needs action counter -> predict/state contract). GUESS: bar empty = dead.

_GEO_CACHE = {}
# level -> (num,den): cumulative drained cells after n actions = round(n*num/den)
# (round half up; observed lvl0 2/1, lvl1 2/1, lvl2 2/3 -> seq 1,1,2,3,3,4,...)
_RATE = {0: (2, 1), 1: (2, 1), 2: (2, 3)}


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


def _geometry(entry):
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
    pair = set()
    for p in panels:
        pair.add(p['C'])
        for (r, c, tx, ty) in p['tiles']:
            pair.add(int(entry[ty, tx]))
    if len(pair) == 1:
        pair.add(9)
    geo = (panels, pair)
    _GEO_CACHE[key] = geo
    return geo


def _other(pair, v):
    for u in pair:
        if u != v:
            return u
    return v


def _all_match(a, panels, pair):
    for p in panels:
        C = p['C']
        oth = _other(pair, C)
        for (r, c, tx, ty) in p['tiles']:
            want = C if p['pat'][r][c] == 0 else oth
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
    panels, pair = _geometry(np.array(ENTRY_GRID))
    if action == 0:
        return grid, info, {'n': 0}
    if action == 6 and x is not None and y is not None:
        hit = False
        for p in panels:
            for (r, c, tx, ty) in p['tiles']:
                if tx <= x < tx + 6 and ty <= y < ty + 6:
                    v = int(b[ty, tx])
                    b[ty:ty + 6, tx:tx + 6] = _other(pair, v)
                    hit = True
                    break
            if hit:
                break
    n1 = n0 + 1
    num, den = _RATE.get(CURRENT_LEVEL, (2, 3))
    dcells = _cum_cells(n1, num, den) - _cum_cells(n0, num, den)
    if (b[63] == 12).any() or (b[63] == 11).any():
        for _ in range(dcells):
            idxs = np.where(b[63] == 12)[0]
            if len(idxs):
                b[63, idxs[-1]] = 11
        if not (b[63] == 12).any():
            info["dead"] = True  # GUESS: bar empty = out of moves
    if panels and _all_match(b, panels, pair):
        info["level_up"] = True
    return b.tolist(), info, {'n': n1}


def is_goal(grid):
    a = np.array(grid)
    panels, pair = _geometry(np.array(ENTRY_GRID))
    return bool(panels) and _all_match(a, panels, pair)
