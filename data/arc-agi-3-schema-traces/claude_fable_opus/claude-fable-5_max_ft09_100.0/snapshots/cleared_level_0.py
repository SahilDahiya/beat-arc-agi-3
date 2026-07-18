# ARC3 world model — "match the glyph" click puzzle (seen level 0)
# Layout: 3x3 panels of 6x6 tiles (colors 8/9), tile origins spaced 8px.
# Panel center tile = glyph: 3x3 of 2x2-px cells, colors {0,2}, center cell 8.
# Rule (from solved example panels): glyph 0 -> tile 8, glyph 2 -> tile 9.
# Hypothesis: ACTION6 click inside a non-center tile toggles 8<->9.
# Goal: every panel matches its glyph -> level_up.

def _find_glyphs(a):
    H, W = a.shape
    out = []
    for y in range(0, H - 5):
        for x in range(0, W - 5):
            if a[y + 2, x + 2] != 8:  # cheap prefilter: center cell is 8
                continue
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
            if pat[1][1] != 8:
                continue
            flat = [v for row in pat for v in row]
            if any(v not in (0, 2, 8) for v in flat):
                continue
            if all(v == 8 for v in flat):
                continue  # uniform 8 tile is not a glyph
            out.append((x, y, pat))
    return out


def _panels(a):
    panels = []
    for (gx, gy, pat) in _find_glyphs(a):
        tiles = []
        ok = True
        for r in range(3):
            for c in range(3):
                if r == 1 and c == 1:
                    continue
                tx, ty = gx + (c - 1) * 8, gy + (r - 1) * 8
                if tx < 0 or ty < 0 or tx + 6 > a.shape[1] or ty + 6 > a.shape[0]:
                    ok = False
                    break
                blk = a[ty:ty + 6, tx:tx + 6]
                v = int(blk[0, 0])
                if not (blk == v).all() or v not in (8, 9):
                    ok = False
                    break
                tiles.append((r, c, tx, ty, v))
            if not ok:
                break
        if ok and len(tiles) == 8:
            panels.append({'gx': gx, 'gy': gy, 'pat': pat, 'tiles': tiles})
    return panels


def _matches(p):
    for (r, c, tx, ty, v) in p['tiles']:
        want = 8 if p['pat'][r][c] == 0 else 9
        if v != want:
            return False
    return True


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    a = np.array(grid)
    b = a.copy()
    if action == 6 and x is not None and y is not None:
        panels = _panels(a)
        hit = False
        for p in panels:
            for (r, c, tx, ty, v) in p['tiles']:
                if tx <= x < tx + 6 and ty <= y < ty + 6:
                    b[ty:ty + 6, tx:tx + 6] = 8 if v == 9 else 9
                    hit = True
                    break
            if hit:
                break
    # Energy bar (confirmed lvl0): bottom row drains c(12)->b(11), 2 cells per
    # action, right to left. Applies to every game action.
    if action != 0 and ((b[63] == 12).any() or (b[63] == 11).any()):
        for _ in range(2):
            idxs = np.where(b[63] == 12)[0]
            if len(idxs):
                b[63, idxs[-1]] = 11
        if not (b[63] == 12).any():
            info["dead"] = True  # GUESS: bar empty = out of moves = game over
    new_panels = _panels(b)
    if new_panels and all(_matches(q) for q in new_panels):
        info["level_up"] = True
    return b.tolist(), info


def is_goal(grid):
    a = np.array(grid)
    panels = _panels(a)
    return bool(panels) and all(_matches(q) for q in panels)
