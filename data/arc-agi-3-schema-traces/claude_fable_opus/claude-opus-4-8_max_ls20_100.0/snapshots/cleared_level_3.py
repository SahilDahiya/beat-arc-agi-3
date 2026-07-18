import numpy as np
import math

FLOOR = 3
VOID = 4          # the ONLY impassable colour
PANEL = 5         # pattern-panel background
BAR = 11
BLK = 12

BMAX = 200
# Each level has a move budget B; the bar shows floor(42*(B-used)/B). Only a move that ACTUALLY
# HAPPENS costs 1 (a refused/blocked move is a totally free no-op).
LEVEL_BUDGET = {0: 46, 1: 21, 2: 21, 3: 42}   # L3: 1 move drained 1px -> B>=42; 42 = conservative
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


def _comps(mask, diag=False):
    H, W = mask.shape
    seen = np.zeros((H, W), dtype=bool)
    out = []
    nbr = ([(1, 0), (-1, 0), (0, 1), (0, -1)] if not diag else
           [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)])
    for y in range(H):
        for x in range(W):
            if mask[y, x] and not seen[y, x]:
                c = np.zeros((H, W), dtype=bool)
                st = [(y, x)]
                c[y, x] = True
                while st:
                    a, b = st.pop()
                    for dy, dx in nbr:
                        ny, nx = a + dy, b + dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not c[ny, nx]:
                            c[ny, nx] = True
                            st.append((ny, nx))
                seen |= c
                out.append(c)
    return out


def _bbox(c):
    ys, xs = np.where(c)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _cellfree(floor, x0, y0, bw, bh):
    H, W = floor.shape
    return (0 <= x0 and x0 + bw <= W and 0 <= y0 and y0 + bh <= H
            and bool(floor[y0:y0 + bh, x0:x0 + bw].all()))


# ---------------------------------------------------------------- key panels
# A KEY is a (3x3 PATTERN, COLOUR) pair. The HUD panel shows the key you carry; the in-map panel
# is the lock. They must match in BOTH pattern and colour for the keyhole to open.

def _read(G, p):
    c = p['cell']
    vals = [[int(G[p['py'] + r * c, p['px'] + k * c]) for k in range(3)] for r in range(3)]
    pat = np.array([[1 if v != PANEL else 0 for v in row] for row in vals])
    on = [v for row in vals for v in row if v != PANEL]
    return pat, (on[0] if on else PANEL)


def _write(G, p, pat, colour):
    c = p['cell']
    for r in range(3):
        for k in range(3):
            G[p['py'] + r * c:p['py'] + (r + 1) * c,
              p['px'] + k * c:p['px'] + (k + 1) * c] = colour if pat[r, k] else PANEL


def _find_panels(E):
    """A panel = a PANEL-coloured component whose bbox is a square of side 3*cell+4; the 3x3
    pattern sits in the bbox inset by 2. Pattern colour varies per panel, so never test == 9."""
    out = []
    for c in _comps(E == PANEL):
        x0, y0, x1, y1 = _bbox(c)
        w = x1 - x0 + 1
        if w != y1 - y0 + 1 or w < 7 or (w - 4) % 3:
            continue
        p = dict(bbox=(x0, y0, x1, y1), px=x0 + 2, py=y0 + 2, cell=(w - 4) // 3)
        pat, colour = _read(E, p)
        if pat.any():
            out.append(p)
    return out


def _get_map():
    E = np.array(ENTRY_GRID, dtype=np.int16)
    ck = E.tobytes()
    if ck in _CACHE:
        return _CACHE[ck]
    H, W = E.shape

    panels = _find_panels(E)
    panelpx = np.zeros((H, W), dtype=bool)
    for p in panels:
        x0, y0, x1, y1 = p['bbox']
        panelpx[y0:y1 + 1, x0:x1 + 1] = True

    # The BLOCK = the LARGEST solid component containing a BLK pixel. It cannot just be seeded at
    # min(y),min(x) of the BLK pixels: the PINWHEEL glyph also contains colour 12 (and 9), so that
    # seed can land on empty floor and collapse the block to 1x1 (this silently broke L3).
    solid = (E != VOID) & (E != FLOOR) & ~panelpx
    cands = [c for c in _comps(solid) if (E[c] == BLK).any()]
    blk = max(cands, key=lambda c: int(c.sum()))
    bx, by, bx1, by1 = _bbox(blk)
    bw, bh = bx1 - bx + 1, by1 - by + 1

    floor = _comp(E != VOID, (by, bx))           # walkable = anything not VOID, reachable

    lock = hud = None
    for p in panels:
        x0, y0, x1, y1 = p['bbox']
        if floor[y0:y1 + 1, x0:x1 + 1].any():
            lock = p                              # in the map -> the keyhole
        else:
            hud = p                               # off-map -> the key you carry

    # --- glyph tiles on the walkable map (block excluded) ---
    gm = floor & ~np.isin(E, [FLOOR, PANEL]) & ~panelpx
    gm[by:by + bh, bx:bx + bw] = False
    rot = np.zeros((H, W), dtype=bool)      # 3x3 PLUS {0,1}, 5 cells: rotate key pattern 90 CW
    cyc = np.zeros((H, W), dtype=bool)      # 3x3 PINWHEEL, 9 cells: advance key COLOUR one step CW
    setp = np.zeros((H, W), dtype=bool)     # 3x3 {0}, 4 cells: SET the key PATTERN to the lock's
    refill = np.zeros((H, W), dtype=bool)   # 3x3 RING {11}, 8 cells: refill the bar, then consumed
    launch = {}                             # colour-1 EDGE LINE: cell -> slide direction
    wheel = []                              # the pinwheel's CW colour cycle
    unknown = []
    # 8-connectivity: the pattern-setter glyph is two diagonal pieces under 4-connectivity.
    for c in _comps(gm, diag=True):
        cols = set(int(v) for v in E[c])
        x0, y0, x1, y1 = _bbox(c)
        w, h, n = x1 - x0 + 1, y1 - y0 + 1, int(c.sum())
        if cols <= {0, 1} and (w, h, n) == (3, 3, 5):
            rot |= c
        elif cols == {BAR} and (w, h, n) == (3, 3, 8):
            refill |= c
        elif (w, h, n) == (3, 3, 9):
            cyc |= c                        # pinwheel: 4 two-cell arms round a centre
            g = E[y0:y0 + 3, x0:x0 + 3]
            wheel = [int(g[0, 1]), int(g[1, 2]), int(g[2, 1]), int(g[1, 0])]   # N,E,S,W = CW order
        elif cols == {0} and (w, h, n) == (3, 3, 4):
            setp |= c                       # L3: SETS the key pattern to the lock's pattern
        elif cols == {1} and w == 1 and h == bh and n == bh:
            # vertical line on a cell EDGE -> launches the block away from it, horizontally.
            # (May be an INTERNAL edge: then BOTH neighbours get a launcher, each firing outward.)
            if _cellfree(floor, x0 + 1, y0, bw, bh):
                launch[(x0 + 1, y0)] = (1, 0)
            if _cellfree(floor, x0 - bw, y0, bw, bh):
                launch[(x0 - bw, y0)] = (-1, 0)
        elif cols == {1} and h == 1 and w == bw and n == bw:
            if _cellfree(floor, x0, y0 + 1, bw, bh):
                launch[(x0, y0 + 1)] = (0, 1)
            if _cellfree(floor, x0, y0 - bh, bw, bh):
                launch[(x0, y0 - bh)] = (0, -1)
        else:
            unknown.append((x0, y0, x1, y1, tuple(sorted(cols)), n))

    glyphpx = gm.copy()                     # every glyph pixel (pinwheel reuses BLK/KEY colours)

    barmask = (E == BAR) & ~floor
    barcols = sorted(set(np.where(barmask)[1].tolist()))
    bg = E.copy()
    bg[by:by + bh, bx:bx + bw] = FLOOR
    lock_pat, lock_col = _read(E, lock) if lock else (None, None)
    res = dict(floor=floor, bg=bg, bw=bw, bh=bh, H=H, W=W, panelpx=panelpx, glyphpx=glyphpx,
               rot=rot, cyc=cyc, setp=setp, refill=refill, launch=launch, wheel=wheel,
               unknown=unknown,
               barmask=barmask, barcols=barcols, bar0=len(barcols),
               lock=lock, hud=hud, lock_pat=lock_pat, lock_col=lock_col)
    _CACHE[ck] = res
    return res


def _block(G, M):
    """Locate the block. Glyph pixels must be excluded: the pinwheel also uses colours 12/9."""
    ok = (G == BLK) & ~M['panelpx'] & ~M['glyphpx']
    ys, xs = np.where(ok)
    if len(ys) == 0:
        return None
    m = _comp((G != VOID) & (G != FLOOR) & ~M['panelpx'] & ~M['glyphpx'],
              (int(ys[0]), int(xs[0])))
    x0, y0, _x1, _y1 = _bbox(m)
    return x0, y0, M['bw'], M['bh']


DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}


def _free(M, x0, y0):
    bw, bh = M['bw'], M['bh']
    return (0 <= x0 and x0 + bw <= M['W'] and 0 <= y0 and y0 + bh <= M['H']
            and bool(M['floor'][y0:y0 + bh, x0:x0 + bw].all()))


def _inserted(M, x0, y0):
    if M['lock'] is None:
        return False
    lx0, ly0, lx1, ly1 = M['lock']['bbox']
    return lx0 <= x0 and x0 + M['bw'] - 1 <= lx1 and ly0 <= y0 and y0 + M['bh'] - 1 <= ly1


def _matched(G, M):
    """Key fits the lock only if BOTH the 3x3 pattern AND the colour agree. (L2: pattern matched
    but the key was colour 12 vs a colour-9 lock -> the keyhole refused entry, for free.)"""
    if M['lock_pat'] is None or M['hud'] is None:
        return False
    pat, colour = _read(G, M['hud'])
    return bool((pat == M['lock_pat']).all()) and colour == M['lock_col']


def _px(bar0, B, u):
    return int(math.floor(bar0 * (B - u) / B))


def _draw_bar(out, M, px):
    keep = set(M['barcols'][M['bar0'] - px:]) if px > 0 else set()
    for c in M['barcols']:
        rows = np.where(M['barmask'][:, c])[0]
        out[rows, c] = BAR if c in keep else FLOOR


def init_state(entry_grid):
    B = LEVEL_BUDGET.get(CURRENT_LEVEL)
    return {'u': 0, 'cands': (B,) if B else tuple(range(1, BMAX))}


def predict(state, grid, action, x=None, y=None):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    out = G.copy()
    info = {"level_up": False, "dead": False, "win": False}
    u = int(state.get('u', 0))
    cands = tuple(state.get('cands') or range(1, BMAX))

    seen_px = int(np.unique(np.where(M['barmask'] & (G == BAR))[1]).size)
    for pool in (cands, tuple(range(1, BMAX))):
        hit = False
        for du in (0, 1, 2):     # `u` self-resyncs (the framework skips the run's 1st transition)
            nc = tuple(b for b in pool if b >= u + du and _px(M['bar0'], b, u + du) == seen_px)
            if nc:
                cands, u, hit = nc, u + du, True
                break
        if hit:
            break
    B = cands[0]

    moved = refilled = False
    blk = _block(G, M)
    if blk is not None and action in DIRS:
        x0, y0, bw, bh = blk
        dx, dy = DIRS[action]
        nx0, ny0 = x0 + dx * bw, y0 + dy * bh
        # the keyhole refuses entry unless the key fits (pattern AND colour)
        shut = _inserted(M, nx0, ny0) and not _matched(G, M)
        if _free(M, nx0, ny0) and not shut:
            moved = True
            # a LAUNCHER on the entered cell fires the block onward until blocked (still ONE action)
            cells = [(nx0, ny0)]
            d = M['launch'].get((nx0, ny0))
            for _ in range(64):
                if d is None:
                    break
                tx, ty = cells[-1][0] + d[0] * bw, cells[-1][1] + d[1] * bh
                if not _free(M, tx, ty) or _inserted(M, tx, ty):
                    break        # a slide never enters the keyhole: you must step in deliberately
                cells.append((tx, ty))
                # NOTE: a slide keeps its ORIGINAL direction — launchers it passes OVER do not
                # redirect it. (L3 proves this: with re-triggering, the pocket holding the
                # pinwheel and the pattern glyph is unreachable and the level is unsolvable.)
            fx, fy = cells[-1]
            old = (slice(y0, y0 + bh), slice(x0, x0 + bw))
            out[old] = np.where(M['refill'][old], FLOOR, M['bg'][old])   # spent rings stay gone
            pat, colour = _read(G, M['hud']) if M['hud'] else (None, None)
            for (cx, cy) in cells:
                csl = (slice(cy, cy + bh), slice(cx, cx + bw))
                if M['rot'][csl].any() and pat is not None:
                    pat = np.rot90(pat, -1)                     # plus: pattern 90 deg CW
                if M['cyc'][csl].any() and colour in M['wheel']:
                    w = M['wheel']
                    colour = w[(w.index(colour) + 1) % 4]       # pinwheel: colour one step CW
                if M['setp'][csl].any() and M['lock_pat'] is not None:
                    pat = M['lock_pat'].copy()                  # setter: pattern := the lock's
                if (G[csl] == BAR).any():                       # live ring: refill, then consume
                    refilled = True
                    out[csl] = np.where(M['refill'][csl], FLOOR, out[csl])
            out[fy:fy + bh, fx:fx + bw] = G[old]
            if M['hud'] is not None:
                _write(out, M['hud'], pat, colour)
            if _inserted(M, fx, fy) and _matched(out, M):
                info['level_up'] = True

    if moved and u >= B:
        info['dead'] = True
    u2 = u if not moved else (0 if refilled else u + 1)   # refused move = FREE no-op
    _draw_bar(out, M, max(0, _px(M['bar0'], B, min(u2, B))))
    return out.tolist(), info, {'u': u2, 'cands': cands}


def is_goal(grid):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    b = _block(G, M)
    return b is not None and _inserted(M, b[0], b[1]) and _matched(G, M)
