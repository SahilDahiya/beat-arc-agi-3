# ARC3 world model — "match the glyph" click puzzle (levels 0-5)
# BOARD: sparse lattice of 6x6 blocks spaced 8px. Block kinds:
#   TILE   = uniform non-bg color; click toggles it to next palette color.
#   GLYPH  = 3x3 of 2x2-px cells: inks {0,2,3} + center color C (C not ink).
#   BUTTON = base color B on corners+center, accent (6) on a SUBSET S of the
#            4 ortho cells (N=(0,1), W=(1,0), E=(1,2), S=(2,1)). Click toggles
#            its own base AND the blocks in directions S (tile toggle / button
#            base toggle; glyphs & empty unaffected; NO cascade (assumed)).
#            lvl4 "checkers" = buttons with S=all4; lvl5 = S={N}.
# LEGEND: vertical stack of 4x4 blocks from y=0 at some column = palette CYCLE.
#   Click advances tile/button-base to NEXT cycle color (wraps).
# GLYPH constraint on its 8 neighbors (+-8px):
#   ink 0 -> neighbor block (tile/button base) color == C
#   ink 2 -> neighbor block color != C (non-block: auto-ok)
#   ink 3 -> neighbor is not a block (structural, auto-ok)
# Goal: ALL glyph constraints satisfied -> level_up.
# ENERGY: row 63 c(12)->b(11) R->L; cum after n actions = round-half-EVEN(n*num/den)
#   _RATE per level; empty bar = dead (GUESS).

_GEO_CACHE = {}
_RATE = {0: (2, 1), 1: (2, 1), 2: (2, 3), 3: (2, 3), 4: (1, 2)}
_RATE_DEFAULT = (1, 2)

_DIRCELL = {(0, 1): (0, -8), (1, 0): (-8, 0), (1, 2): (8, 0), (2, 1): (0, 8)}


def _cell_pattern(a, tx, ty):
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


def _button_info(pat, bg):
    """(accent, dirs, accent_cells) if pat is a button, else None."""
    if pat is None:
        return None
    B = pat[1][1]
    if B in (0, 2, 3) or B == bg:
        return None
    for (r, c) in ((0, 0), (0, 2), (2, 0), (2, 2)):
        if pat[r][c] != B:
            return None
    accents = [(r, c) for (r, c) in _DIRCELL if pat[r][c] != B]
    if not accents:
        return None
    vals = {pat[r][c] for (r, c) in accents}
    if len(vals) != 1:
        return None
    A = vals.pop()
    if A in (0, 2, 3) or A == bg:
        return None
    return (A, [_DIRCELL[rc] for rc in accents], accents)


def _classify(entry, bg, tx, ty):
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
    bi = _button_info(pat, bg)
    if bi is not None:
        return ('button', bi)
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
            best = x0  # rightmost
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
    """(panels, cycle, tiles, buttons)
    buttons: {(tx,ty): (accent, [dirs], [accent_cells])}"""
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
    tiles = set()
    buttons = {}
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
                elif kind == 'button':
                    buttons[q] = extra
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
    geo = (panels, cycle, tiles, buttons)
    _GEO_CACHE[key] = geo
    return geo


def _all_match(a, panels):
    for p in panels:
        C = p['C']
        for (r, c, tx, ty, kind) in p['cons']:
            ink = p['pat'][r][c]
            if ink == 0:
                if kind not in ('tile', 'button') or a[ty, tx] != C:
                    return False
            elif ink == 2:
                if kind in ('tile', 'button') and a[ty, tx] == C:
                    return False
    return True


def _toggle_tile(b, tx, ty, cycle):
    v = int(b[ty, tx])
    if v in cycle:
        nxt = cycle[(cycle.index(v) + 1) % len(cycle)]
        b[ty:ty + 6, tx:tx + 6] = nxt


def _flip_button(b, tx, ty, accent_cells, cycle):
    base = int(b[ty, tx])  # corner (0,0) is always base
    if base not in cycle:
        return
    nb = cycle[(cycle.index(base) + 1) % len(cycle)]
    for r in range(3):
        for c in range(3):
            if (r, c) in accent_cells:
                continue
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
    panels, cycle, tiles, buttons = _geometry(np.array(ENTRY_GRID))
    if action == 0:
        return grid, info, {'n': 0}
    if action == 6 and x is not None and y is not None:
        hit = False
        for (tx, ty) in tiles:
            if tx <= x < tx + 6 and ty <= y < ty + 6:
                _toggle_tile(b, tx, ty, cycle)
                hit = True
                break
        if not hit:
            for (tx, ty), (acc, dirs, acells) in buttons.items():
                if tx <= x < tx + 6 and ty <= y < ty + 6:
                    _flip_button(b, tx, ty, acells, cycle)
                    for (dx, dy) in dirs:
                        q = (tx + dx, ty + dy)
                        if q in tiles:
                            _toggle_tile(b, q[0], q[1], cycle)
                        elif q in buttons:
                            _flip_button(b, q[0], q[1], buttons[q][2], cycle)
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
        if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5:
            info["win"] = True  # completing the last level (6 total) wins
    return b.tolist(), info, {'n': n1}


def is_goal(grid):
    a = np.array(grid)
    panels, cycle, tiles, buttons = _geometry(np.array(ENTRY_GRID))
    return bool(panels) and _all_match(a, panels)
