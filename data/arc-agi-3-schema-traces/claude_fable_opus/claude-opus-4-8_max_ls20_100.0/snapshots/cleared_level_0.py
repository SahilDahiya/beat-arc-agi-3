import numpy as np

FLOOR = 3
VOID = 4          # the ONLY impassable colour
PANEL = 5
KEY = 9
BAR = 11
BLK = 12
ROT_COLORS = (0, 1)   # plus-shaped rotator tile

_CACHE = {}


def _comp(mask, seed):
    H, W = mask.shape
    out = np.zeros((H, W), dtype=bool)
    stack = [seed]
    out[seed] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not out[ny, nx] and mask[ny, nx]:
                out[ny, nx] = True
                stack.append((ny, nx))
    return out


def _find_block(G):
    ys, xs = np.where(G == BLK)
    if len(ys) == 0:
        return None
    m = _comp((G == BLK) | (G == KEY), (int(ys[0]), int(xs[0])))
    ys, xs = np.where(m)
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _panels(E, lo, hi):
    """3x3 pattern panels in rows [lo,hi]: a {PANEL,KEY} component that contains KEY cells.
    Returns list of dicts: bbox + pattern-grid origin/cell (bbox inset by 2)."""
    H, W = E.shape
    mask = (E == PANEL) | (E == KEY)
    mask[:lo, :] = False
    mask[hi + 1:, :] = False
    res, seen = [], np.zeros((H, W), dtype=bool)
    for y in range(H):
        for x in range(W):
            if mask[y, x] and not seen[y, x]:
                c = _comp(mask, (y, x))
                seen |= c
                if (E[c] == KEY).any():
                    ys, xs = np.where(c)
                    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
                    res.append(dict(bbox=(x0, y0, x1, y1), px=x0 + 2, py=y0 + 2,
                                    cell=(x1 - x0 - 3) // 3))
    return res


def _read_pat(G, p):
    c = p['cell']
    return np.array([[1 if G[p['py'] + r * c, p['px'] + k * c] == KEY else 0
                      for k in range(3)] for r in range(3)])


def _write_pat(G, p, pat):
    c = p['cell']
    for r in range(3):
        for k in range(3):
            G[p['py'] + r * c:p['py'] + (r + 1) * c,
              p['px'] + k * c:p['px'] + (k + 1) * c] = KEY if pat[r, k] else PANEL


def _get_map():
    E = np.array(ENTRY_GRID, dtype=np.int16)
    ck = E.tobytes()
    if ck in _CACHE:
        return _CACHE[ck]
    H, W = E.shape
    bx, by, bw, bh = _find_block(E)
    floor = _comp(E != VOID, (by, bx))            # walkable = anything not VOID, reachable
    maxy = int(np.where(floor.any(axis=1))[0].max())
    lock = _panels(E, 0, maxy)                    # pattern panel inside the map = LOCK / keyhole
    hud = _panels(E, maxy + 1, H - 1)             # pattern panel below the map = current KEY
    bg = E.copy()
    bg[by:by + bh, bx:bx + bw] = FLOOR
    res = dict(floor=floor, bg=bg, bw=bw, bh=bh, H=H, W=W,
               lock=lock[0] if lock else None, hud=hud[0] if hud else None)
    # the lock/target pattern is STATIC -> read it from ENTRY (the block may cover it later)
    res['lock_pat'] = _read_pat(E, res['lock']) if res['lock'] else None
    _CACHE[ck] = res
    return res


DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}


def _inserted(M, x0, y0, bw, bh):
    """Block sits fully inside the lock/keyhole panel."""
    L = M['lock']
    if L is None:
        return False
    lx0, ly0, lx1, ly1 = L['bbox']
    return lx0 <= x0 and x0 + bw - 1 <= lx1 and ly0 <= y0 and y0 + bh - 1 <= ly1


def _matched(G, M):
    """Current HUD key pattern equals the (static) lock pattern."""
    if M['lock_pat'] is None or M['hud'] is None:
        return False
    return bool((_read_pat(G, M['hud']) == M['lock_pat']).all())


def step(grid, action, x=None, y=None):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    out = G.copy()
    drain = True
    info = {"level_up": False, "dead": False, "win": False}

    blk = _find_block(G)
    if blk is not None and action in DIRS:
        x0, y0, bw, bh = blk
        dx, dy = DIRS[action]
        nx0, ny0 = x0 + dx * bw, y0 + dy * bh
        if (0 <= nx0 and nx0 + bw <= M['W'] and 0 <= ny0 and ny0 + bh <= M['H']
                and M['floor'][ny0:ny0 + bh, nx0:nx0 + bw].all()):
            hit_rot = bool(np.isin(M['bg'][ny0:ny0 + bh, nx0:nx0 + bw], ROT_COLORS).any())
            out[y0:y0 + bh, x0:x0 + bw] = M['bg'][y0:y0 + bh, x0:x0 + bw]
            out[ny0:ny0 + bh, nx0:nx0 + bw] = G[y0:y0 + bh, x0:x0 + bw]
            if hit_rot and M['hud'] is not None:
                _write_pat(out, M['hud'], np.rot90(_read_pat(G, M['hud']), -1))
                drain = False
            if _inserted(M, nx0, ny0, bw, bh) and _matched(out, M):
                info['level_up'] = True

    if drain:
        bar = (G == BAR)
        if bar.any():
            c = int(np.where(bar.any(axis=0))[0].min())
            out[np.where(bar[:, c])[0], c] = FLOOR

    return out.tolist(), info


def is_goal(grid):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    b = _find_block(G)
    if b is None:
        return False
    return _inserted(M, *b) and _matched(G, M)
