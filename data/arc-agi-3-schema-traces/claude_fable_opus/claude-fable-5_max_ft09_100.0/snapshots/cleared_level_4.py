# ARC3 world model — "match the glyph" click puzzle (levels 0-4)
# BOARD: sparse lattice of 6x6 blocks spaced 8px. Block kinds:
#   TILE    = uniform non-bg color (clickable, cycles through palette)
#   GLYPH   = 3x3 of 2x2-px cells: inks {0,2,3} + center color C (C not ink)
#   CHECKER = 3x3 cells alternating two colors (decoration, not clickable)
# LEGEND: vertical stack of 4x4 blocks (rows 0-3,4-7,...) at some column:
#   the palette CYCLE in order. Click advances a tile to next cycle color.
#   lvl0: none -> fallback {tile colors}+{centers}, 9 first. lvl4: [14,15] @x54.
# GLYPH constraint on its 8 neighbors (offset ±8px):
#   ink 0 -> neighbor (tile or checker BASE) color == C
#   ink 2 -> neighbor (tile or checker BASE) color != C; non-blocks auto-ok
#   ink 3 -> neighbor is not a plain tile (structural, auto-true; e.g. empty/glyph)
# CHECKER = cross button (lvl4): click toggles its BASE color (accent 6 cells
#   unchanged) AND toggles the 4 ORTHO neighbor tiles/checkers (Lights-Out).
#   Checker counts as a tile with its base color for constraints.
# Goal: ALL glyph constraints satisfied -> level_up.
# ENERGY: row 63 drains c(12)->b(11) R->L; cumulative after n actions =
#   round(n*num/den); _RATE per level (lvl0 2/1, lvl1 2/1, lvl2 2/3, lvl3 2/3).
#   GUESS: bar empty = dead.

_GEO_CACHE = {}
# (num, den): cumulative drained cells after n actions = round-half-EVEN(n*num/den)
# lvl0/1: 2 per action; lvl2/3: 2/3; lvl4: 1/2 (ties -> even, verified n=1,3,5)
_RATE = {0: (2, 1), 1: (2, 1), 2: (2, 3), 3: (2, 3), 4: (1, 2)}
_RATE_DEFAULT = (1, 2)


def _cell_pattern(a, tx, ty):
    """3x3 cell colors if 6x6 block at (tx,ty) is 2x2-cell structured, else None."""
    H, W = a.shape
    if tx < 0 or ty < 0 or tx + 6 > W or ty + 6 > H:
        return None
    pat = []
    for r in range(3):
        row = []
        for c in range(3):
            p = a[ty + 2 * r:ty + 2 * r + 2, tx + 2 * c:tx + 2 * c + 2]
            v = int(p[0, 0])
            if not (p == v).all():
                return None
            row.append(v)
        pat.append(row)
    return pat


def _is_glyph_pat(pat):
    if pat is None:
        return False
    C = pat[1][1]
    if C in (0, 2, 3):
        return False
    flat = [v for row in pat for v in row]
    if any(v not in (0, 2, 3, C) for v in flat):
        return False
    return any(v in (0, 2) for v in flat)


def _classify(entry, bg, tx, ty):
    """('none'|'bg'|'tile'|'glyph'|'checker'|'other', extra)."""
    H, W = entry.shape
    if tx < 0 or ty < 0 or tx + 6 > W or ty + 6 > H:
        return ('none', None)
    blk = entry[ty:ty + 6, tx:tx + 6]
    v = int(blk[0, 0])
    if (blk == v).all():
        return ('bg', None) if v == bg else ('tile', v)
    pat = _cell_pattern(entry, tx, ty)
    if pat is None:
        return ('other', None)
    if _is_glyph_pat(pat):
        return ('glyph', pat)
    flat = [x for row in pat for x in row]
    A, B = pat[0][0], pat[0][1]
    if A != B and all(pat[r][c] == (A if (r + c) % 2 == 0 else B) for r in range(3) for c in range(3)):
        return ('checker', (A, B))
    return ('other', None)


def _find_glyphs(a, bg):
    H, W = a.shape
    out = []
    for y in range(0, H - 6):
        for x in range(0, W - 5):
            pat = _cell_pattern(a, x, y)
            if pat is None or not _is_glyph_pat(pat):
                continue
            flat = [v for row in pat for v in row]
            if bg in flat:
                continue
            out.append((x, y, pat))
    return out


def _legend(entry, bg):
    H, W = entry.shape
    best = None
    for x0 in range(0, W - 3):
        b1 = entry[0:4, x0:x0 + 4]
        b2 = entry[4:8, x0:x0 + 4]
        v1, v2 = int(b1[0, 0]), int(b2[0, 0])
        if (b1 == v1).all() and v1 != bg and (b2 == v2).all() and v2 != bg:
            best = x0  # keep rightmost
    if best is None:
        return []
    cyc = []
    for y in (0, 4, 8, 12):
        if y + 4 > H:
            break
        blk = entry[y:y + 4, best:best + 4]
        v = int(blk[0, 0])
        if (blk == v).all() and v != bg and v not in (0, 2, 3):
            cyc.append(v)
        else:
            break
    return cyc


def _geometry(entry):
    """(panels, cycle, tiles)
    panels: [{gx,gy,pat,C,cons:[(r,c,tx,ty,kind)]}]
    tiles:  {(tx,ty)} all clickable tile positions (flood over lattice)."""
    key = entry.tobytes()
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
    vals, counts = np.unique(entry, return_counts=True)
    bg = int(vals[np.argmax(counts)])
    glyphs = _find_glyphs(entry, bg)
    panels = []
    for (gx, gy, pat) in glyphs:
        C = pat[1][1]
        cons = []
        for r in range(3):
            for c in range(3):
                if r == 1 and c == 1:
                    continue
                tx, ty = gx + (c - 1) * 8, gy + (r - 1) * 8
                kind, _ = _classify(entry, bg, tx, ty)
                cons.append((r, c, tx, ty, kind))
        panels.append({'gx': gx, 'gy': gy, 'pat': pat, 'C': C, 'cons': cons})
    # flood-fill lattice from glyphs to find all board tiles + checkers
    tiles = set()
    checkers = {}  # (tx,ty) -> accent color
    seen = set()
    frontier = [(gx, gy) for (gx, gy, _p) in glyphs]
    seen.update(frontier)
    while frontier:
        nxt = []
        for (px, py) in frontier:
            for dx, dy in ((8, 0), (-8, 0), (0, 8), (0, -8)):
                q = (px + dx, py + dy)
                if q in seen:
                    continue
                seen.add(q)
                kind, extra = _classify(entry, bg, q[0], q[1])
                if kind == 'tile':
                    tiles.add(q)
                    nxt.append(q)
                elif kind == 'checker':
                    checkers[q] = extra[1]  # accent = cell (0,1)
                    nxt.append(q)
                elif kind in ('glyph', 'other'):
                    nxt.append(q)
        frontier = nxt
    cycle = _legend(entry, bg)
    if len(cycle) < 2:
        pool = set()
        for p in panels:
            pool.add(p['C'])
        for (tx, ty) in tiles:
            pool.add(int(entry[ty, tx]))
        if len(pool) == 1:
            pool.add(9)
        cycle = ([9] if 9 in pool else []) + sorted(v for v in pool if v != 9)
    geo = (panels, cycle, tiles, checkers)
    _GEO_CACHE[key] = geo
    return geo


def _all_match(a, panels):
    for p in panels:
        C = p['C']
        for (r, c, tx, ty, kind) in p['cons']:
            ink = p['pat'][r][c]
            if ink == 0:
                # tile or checker base must equal C
                if kind not in ('tile', 'checker') or a[ty, tx] != C:
                    return False
            elif ink == 2:
                # tile or checker base must differ from C
                if kind in ('tile', 'checker') and a[ty, tx] == C:
                    return False
            # ink 3 and center: structural, auto-ok
    return True


def _flip_checker(b, tx, ty, cycle):
    base = int(b[ty, tx])
    if base in cycle:
        nb = cycle[(cycle.index(base) + 1) % len(cycle)]
        for r in range(3):
            for c in range(3):
                if (r + c) % 2 == 0:
                    b[ty + 2 * r:ty + 2 * r + 2, tx + 2 * c:tx + 2 * c + 2] = nb


def _cum_cells(n, num, den):
    t = n * num
    q, r = divmod(t, den)
    if 2 * r < den:
        return q
    if 2 * r > den:
        return q + 1
    return q if q % 2 == 0 else q + 1  # round-half-even


def init_state(entry_grid):
    return {'n': 0}


def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    n0 = int(state.get('n', 0))
    a = np.array(grid)
    b = a.copy()
    panels, cycle, tiles, checkers = _geometry(np.array(ENTRY_GRID))
    if action == 0:
        return grid, info, {'n': 0}
    if action == 6 and x is not None and y is not None:
        hit = False
        for (tx, ty) in tiles:
            if tx <= x < tx + 6 and ty <= y < ty + 6:
                v = int(b[ty, tx])
                if v in cycle:
                    nxt = cycle[(cycle.index(v) + 1) % len(cycle)]
                    b[ty:ty + 6, tx:tx + 6] = nxt
                hit = True
                break
        if not hit:
            for (tx, ty) in checkers:
                if tx <= x < tx + 6 and ty <= y < ty + 6:
                    # cross button: flip self base + 4 ortho tiles/checkers
                    _flip_checker(b, tx, ty, cycle)
                    for dx, dy in ((8, 0), (-8, 0), (0, 8), (0, -8)):
                        q = (tx + dx, ty + dy)
                        if q in tiles:
                            v = int(b[q[1], q[0]])
                            if v in cycle:
                                nxt = cycle[(cycle.index(v) + 1) % len(cycle)]
                                b[q[1]:q[1] + 6, q[0]:q[0] + 6] = nxt
                        elif q in checkers:
                            _flip_checker(b, q[0], q[1], cycle)
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
    if panels and _all_match(b, panels):
        info["level_up"] = True
    return b.tolist(), info, {'n': n1}


def is_goal(grid):
    a = np.array(grid)
    panels, cycle, tiles, checkers = _geometry(np.array(ENTRY_GRID))
    return bool(panels) and _all_match(a, panels)
