# ARC3 world model — "match the glyph" click puzzle (levels 0,1)
# Layout: 3x3 panels of 6x6 tiles spaced 8px; panel center tile = GLYPH:
#   3x3 of 2x2-px cells, colors subset of {0,2,C} where C = center cell color
#   (C=8 on lvl0, C=12 on lvl1), at least one cell in {0,2}.
# Tiles are uniform 6x6 in {9, C}. Panels may SHARE tiles (lvl1: stacked panels).
# CONFIRMED: ACTION6 click inside a tile toggles it 9 <-> C.
# CONFIRMED: bottom row (y=63) = energy bar, drains 2 cells c(12)->b(11) per
#   action, right to left. GUESS: empty bar = dead.
# Goal: every panel matches its glyph (0 -> C, 2 -> 9) -> level_up.
# PERF: glyph geometry detected once from ENTRY_GRID (module cache); step()
#   only reads tile colors from the live grid.

_GEO_CACHE = {}


def _find_glyphs(a):
    H, W = a.shape
    out = []
    for y in range(0, H - 6):  # exclude energy-bar row
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
    """Panels detected from the ENTRY grid: list of dicts with glyph pos, pattern,
    C (on-color) and the 8 tile origins."""
    key = entry.tobytes()
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
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
                if not (blk == v).all() or v not in (9, C):
                    ok = False
                    break
                tiles.append((r, c, tx, ty))
            if not ok:
                break
        if ok and len(tiles) == 8:
            panels.append({'gx': gx, 'gy': gy, 'pat': pat, 'C': C, 'tiles': tiles})
    _GEO_CACHE[key] = panels
    return panels


def _all_match(a, panels):
    for p in panels:
        C = p['C']
        for (r, c, tx, ty) in p['tiles']:
            want = C if p['pat'][r][c] == 0 else 9
            if a[ty, tx] != want:
                return False
    return True


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    a = np.array(grid)
    b = a.copy()
    panels = _geometry(np.array(ENTRY_GRID))
    if action == 6 and x is not None and y is not None:
        hit = False
        for p in panels:
            C = p['C']
            for (r, c, tx, ty) in p['tiles']:
                if tx <= x < tx + 6 and ty <= y < ty + 6:
                    v = int(b[ty, tx])
                    b[ty:ty + 6, tx:tx + 6] = C if v == 9 else 9
                    hit = True
                    break
            if hit:
                break
    # Energy bar: bottom row drains c(12)->b(11), 2 cells per action, R->L.
    if action != 0 and ((b[63] == 12).any() or (b[63] == 11).any()):
        for _ in range(2):
            idxs = np.where(b[63] == 12)[0]
            if len(idxs):
                b[63, idxs[-1]] = 11
        if not (b[63] == 12).any():
            info["dead"] = True  # GUESS: bar empty = out of moves
    if panels and _all_match(b, panels):
        info["level_up"] = True
    return b.tolist(), info


def is_goal(grid):
    a = np.array(grid)
    panels = _geometry(np.array(ENTRY_GRID))
    return bool(panels) and _all_match(a, panels)
