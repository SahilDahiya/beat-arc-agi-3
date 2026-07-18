# World model for the peg-jumping board game.
# numpy is preloaded by the ARC3 sandbox as np.

def _tiles():
    """Return playable 4x4 tile top-lefts, derived from this level's entry board."""
    e = np.asarray(ENTRY_GRID)
    m = (e == 1) | (e == 14)
    out = []
    h, w = e.shape
    for y in range(h - 3):
        for x in range(w - 3):
            if not np.all(m[y:y+4, x:x+4]):
                continue
            if x and m[y, x-1]:
                continue
            if y and m[y-1, x]:
                continue
            out.append((x, y))
    return out

def _has_peg(g, p):
    x, y = p
    return bool(np.any(g[y:y+4, x:x+4] == 14))

def _selected(g, tiles):
    # A selected peg has a colour-3 ring around its 4x4 tile.
    h, w = g.shape
    for x, y in tiles:
        ya, yb = max(0, y-1), min(h, y+5)
        xa, xb = max(0, x-1), min(w, x+5)
        if np.any(g[ya:yb, xa:xb] == 3):
            return (x, y)
    return None

def _clear_guides(g, tiles):
    # Restore guide pixels while retaining the current set of pegs.
    for x, y in tiles:
        block = g[y:y+4, x:x+4]
        block[(block == 2) | (block == 3)] = 1
        # The 1-pixel selection ring is in the black lattice gap.
        if y > 0:
            g[y-1, x:x+4][g[y-1, x:x+4] == 3] = 0
        if y+4 < g.shape[0]:
            g[y+4, x:x+4][g[y+4, x:x+4] == 3] = 0
        if x > 0:
            g[y:y+4, x-1][g[y:y+4, x-1] == 3] = 0
        if x+4 < g.shape[1]:
            g[y:y+4, x+4][g[y:y+4, x+4] == 3] = 0
        # Four outer corners of the 6x6 ring.
        for xx, yy in ((x-1,y-1),(x+4,y-1),(x-1,y+4),(x+4,y+4)):
            if 0 <= yy < g.shape[0] and 0 <= xx < g.shape[1] and g[yy,xx] == 3:
                g[yy,xx] = 0

def _moves(g, src, tile_set):
    x, y = src
    ans = []
    for dx, dy in ((0,-6),(0,6),(-6,0),(6,0)):
        mid = (x+dx, y+dy)
        dst = (x+2*dx, y+2*dy)
        if mid in tile_set and dst in tile_set and _has_peg(g, mid) and not _has_peg(g, dst):
            ans.append((dst, mid))
    return ans

def _clicked_tile(x, y, tiles):
    if x is None or y is None:
        return None
    for p in tiles:
        tx, ty = p
        if tx <= x < tx+4 and ty <= y < ty+4:
            return p
    return None

def _tick(g):
    # Row zero is the visible move-use meter: one new cell per action.
    z = np.where(g[0] == 0)[0]
    if len(z):
        g[0, int(z[0])] = 1

def _peg_count(g, tiles):
    return sum(_has_peg(g, p) for p in tiles)

def step(grid, action, x=None, y=None):
    g = np.array(grid, dtype=int, copy=True)
    tiles = _tiles()
    tile_set = set(tiles)

    if action == 0:
        return np.array(ENTRY_GRID, dtype=int, copy=True).tolist(), {"level_up":False, "dead":False, "win":False}

    _tick(g)

    if action == 6:
        oldsel = _selected(g, tiles)
        clicked = _clicked_tile(x, y, tiles)

        # Work out a move before erasing its visual guides.
        chosen = None
        if oldsel is not None and clicked is not None:
            for dst, mid in _moves(g, oldsel, tile_set):
                if dst == clicked:
                    chosen = (dst, mid)
                    break

        _clear_guides(g, tiles)

        if chosen is not None:
            dst, mid = chosen
            sx, sy = oldsel
            mx, my = mid
            dx, dy = dst
            # Empty source and jumped tile.
            g[sy:sy+4, sx:sx+4] = 1
            g[my:my+4, mx:mx+4] = 1
            # Draw the standard disk in the landing tile.
            g[dy:dy+4, dx:dx+4] = np.array([[1,14,14,1],
                                             [14,14,14,14],
                                             [14,14,14,14],
                                             [1,14,14,1]])
        elif clicked is not None and _has_peg(g, clicked):
            opts = _moves(g, clicked, tile_set)
            if opts:
                sx, sy = clicked
                # six-by-six selection surround; peg pixels stay colour 14.
                g[sy-1:sy+5, sx-1:sx+5] = 3
                # The four outer corners are not part of the rounded ring.
                g[sy-1, sx-1] = 0
                g[sy-1, sx+4] = 0
                g[sy+4, sx-1] = 0
                g[sy+4, sx+4] = 0
                # The assignment above overwrote the peg; redraw it.
                g[sy:sy+4, sx:sx+4] = np.array([[3,14,14,3],
                                                 [14,14,14,14],
                                                 [14,14,14,14],
                                                 [3,14,14,3]])
                for (dst, mid) in opts:
                    dx, dy = dst
                    g[dy:dy+4, dx:dx+4] = np.array([[1,2,2,1],
                                                     [2,1,1,2],
                                                     [2,1,1,2],
                                                     [1,2,2,1]])

    n = _peg_count(g, tiles)
    level_up = (n == 1)
    win = bool(level_up and CURRENT_LEVEL is not None and CURRENT_LEVEL >= 9)
    return g.tolist(), {"level_up":bool(level_up), "dead":False, "win":win}

def is_goal(grid):
    g = np.asarray(grid)
    return _peg_count(g, _tiles()) == 1
