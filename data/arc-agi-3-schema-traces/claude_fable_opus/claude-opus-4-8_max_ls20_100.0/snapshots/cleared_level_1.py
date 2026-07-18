import numpy as np
import math

FLOOR = 3
VOID = 4          # the ONLY impassable colour
PANEL = 5
KEY = 9
BAR = 11
BLK = 12

# 3x3 glyphs centred in a coarse cell, walkable:
CW_COLORS = (0, 1)     # "plus" (.0./100/.1.) -> rotate the HUD key 90 deg CW. PERMANENT.
REFILL_COLOR = 11      # "ring" (bbb/b3b/bbb) -> refill the budget, then CONSUMED.

BMAX = 200
# Each level has a move budget B; the bar shows floor(42*(B-used)/B). B is a per-level constant,
# pinned exactly by brute-forcing it against the observed (used, px) pairs. Every action costs 1.
LEVEL_BUDGET = {0: 46, 1: 21}
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


def _comps(mask):
    H, W = mask.shape
    seen = np.zeros((H, W), dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if mask[y, x] and not seen[y, x]:
                c = _comp(mask, (y, x))
                seen |= c
                out.append(c)
    return out


def _find_block(G):
    ys, xs = np.where(G == BLK)
    if len(ys) == 0:
        return None
    m = _comp((G == BLK) | (G == KEY), (int(ys[0]), int(xs[0])))
    ys, xs = np.where(m)
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


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
    floor = _comp(E != VOID, (by, bx))          # walkable = not VOID, reachable from the block

    pm = ((E == PANEL) | (E == KEY))            # 3x3 pattern panels (block excluded)
    pm[by:by + bh, bx:bx + bw] = False
    lock = hud = None
    for c in _comps(pm):
        if not (E[c] == KEY).any():
            continue
        ys, xs = np.where(c)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        p = dict(bbox=(x0, y0, x1, y1), px=x0 + 2, py=y0 + 2, cell=(x1 - x0 - 3) // 3)
        if (c & floor).any():
            lock = p            # in the map -> the keyhole
        else:
            hud = p             # off-map -> the current-key display

    rot = np.zeros((H, W), dtype=bool)          # rotator tiles (permanent)
    for c in _comps(np.isin(E, CW_COLORS) & floor):
        rot |= c
    refill = (E == REFILL_COLOR) & floor        # ring tiles (one-shot)

    barcols = sorted(set(np.where((E == BAR) & ~floor)[1].tolist()))
    barmask = (E == BAR) & ~floor
    bg = E.copy()
    bg[by:by + bh, bx:bx + bw] = FLOOR
    res = dict(floor=floor, bg=bg, bw=bw, bh=bh, H=H, W=W, rot=rot, refill=refill,
               barmask=barmask, barcols=barcols, bar0=len(barcols), lock=lock, hud=hud,
               lock_pat=_read_pat(E, lock) if lock else None)
    _CACHE[ck] = res
    return res


DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}


def _inserted(M, x0, y0, bw, bh):
    if M['lock'] is None:
        return False
    lx0, ly0, lx1, ly1 = M['lock']['bbox']
    return lx0 <= x0 and x0 + bw - 1 <= lx1 and ly0 <= y0 and y0 + bh - 1 <= ly1


def _matched(G, M):
    if M['lock_pat'] is None or M['hud'] is None:
        return False
    return bool((_read_pat(G, M['hud']) == M['lock_pat']).all())


def _px(bar0, B, u):
    """Bar pixels shown for `u` used actions out of a budget of B."""
    return int(math.floor(bar0 * (B - u) / B))


def _draw_bar(out, M, px):
    """Bar drains from the LEFT: the rightmost `px` columns stay lit."""
    keep = set(M['barcols'][M['bar0'] - px:]) if px > 0 else set()
    for c in M['barcols']:
        rows = np.where(M['barmask'][:, c])[0]
        out[rows, c] = BAR if c in keep else FLOOR


def init_state(entry_grid):
    # `u` = actions used since the level started / since the last ring refill.
    # `cands` = move-budgets B still consistent with the bar seen so far.
    B = LEVEL_BUDGET.get(CURRENT_LEVEL)
    return {'u': 0, 'cands': (B,) if B else tuple(range(1, BMAX))}


def predict(state, grid, action, x=None, y=None):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    out = G.copy()
    info = {"level_up": False, "dead": False, "win": False}
    u = int(state.get('u', 0))
    cands = tuple(state.get('cands') or range(1, BMAX))

    # Narrow the budget from the bar we can actually see. EVERY action costs 1; the bar is just a
    # rounded display, which is why some moves *look* free (L0 u=12) — that was rounding, not a rule.
    # `u` also SELF-RESYNCS: the framework skips the run's first transition without advancing state
    # (tools.py:977), so a plain counter drifts. Trust the bar, not the counter.
    seen_px = int(np.unique(np.where(M['barmask'] & (G == BAR))[1]).size)
    for du in (0, 1, 2):
        nc = tuple(B for B in cands if B >= u + du and _px(M['bar0'], B, u + du) == seen_px)
        if nc:
            cands, u = nc, u + du
            break
    B = cands[0]

    refilled = False
    blk = _find_block(G)
    if blk is not None and action in DIRS:
        x0, y0, bw, bh = blk
        dx, dy = DIRS[action]
        nx0, ny0 = x0 + dx * bw, y0 + dy * bh
        if (0 <= nx0 and nx0 + bw <= M['W'] and 0 <= ny0 and ny0 + bh <= M['H']
                and M['floor'][ny0:ny0 + bh, nx0:nx0 + bw].all()):
            sl = (slice(ny0, ny0 + bh), slice(nx0, nx0 + bw))
            old = (slice(y0, y0 + bh), slice(x0, x0 + bw))
            hit = bool(M['rot'][sl].any())
            refilled = bool((G[sl] == BAR).any())     # a ring is alive only while its glyph shows
            out[old] = np.where(M['refill'][old], FLOOR, M['bg'][old])   # used rings stay gone
            out[sl] = G[old]
            if hit and M['hud'] is not None:
                _write_pat(out, M['hud'], np.rot90(_read_pat(G, M['hud']), -1))
            if _inserted(M, nx0, ny0, bw, bh) and _matched(out, M):
                info['level_up'] = True

    if u >= B:
        info['dead'] = True     # bar empty: this action is unaffordable (conservative)
    u2 = 0 if refilled else u + 1
    _draw_bar(out, M, max(0, _px(M['bar0'], B, min(u2, B))))
    return out.tolist(), info, {'u': u2, 'cands': cands}


def is_goal(grid):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    b = _find_block(G)
    if b is None:
        return False
    return _inserted(M, *b) and _matched(G, M)
