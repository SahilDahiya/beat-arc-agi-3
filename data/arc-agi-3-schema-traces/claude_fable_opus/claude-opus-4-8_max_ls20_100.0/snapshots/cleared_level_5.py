import numpy as np
import math

FLOOR = 3
VOID = 4          # the ONLY impassable colour
PANEL = 5         # pattern-panel background
BAR = 11
BLK = 12

# The PATTERN glyph CYCLES the key's shape (it does NOT copy the lock — that was a coincidence on
# L3). Only the transitions actually OBSERVED are encoded; unknown inputs leave the pattern alone.
SETTER_CYCLE = {
    ((0, 1, 0), (1, 1, 0), (0, 1, 1)): ((1, 1, 1), (0, 0, 1), (1, 0, 1)),   # .#./##./.## -> ###/..#/#.#
    ((1, 1, 1), (0, 0, 1), (1, 0, 1)): ((1, 1, 0), (0, 1, 1), (1, 0, 1)),   # ###/..#/#.# -> ##./.##/#.#
    ((1, 1, 0), (0, 1, 1), (1, 0, 1)): ((0, 1, 0), (0, 1, 0), (1, 1, 1)),   # ##./.##/#.# -> .#./.#./###
    ((0, 1, 0), (0, 1, 0), (1, 1, 1)): ((1, 0, 1), (1, 0, 1), (1, 1, 1)),   # .#./.#./### -> #.#/#.#/###
    ((1, 0, 1), (1, 0, 1), (1, 1, 1)): ((0, 1, 1), (1, 0, 1), (0, 1, 0)),   # #.#/#.#/### -> .##/#.#/.#.
    ((0, 1, 1), (1, 0, 1), (0, 1, 0)): ((0, 1, 0), (1, 1, 0), (0, 1, 1)),   # .##/#.#/.#. -> .#./##./.##
}   # <-- CLOSES THE CYCLE: period 6 (A->B->C->D->E->F->A)

BMAX = 200
# Each level has a move budget B; the bar shows floor(bar0*(B-used)/B). Only a move that ACTUALLY
# HAPPENS costs 1 (a refused/blocked move is a totally free no-op).
LEVEL_BUDGET = {0: 46, 1: 21, 2: 21, 3: 42, 4: 21, 5: 42}   # L5: B>=42 (lower bound only; conservative)
_CACHE = {}

# For PHASED BFS on hard levels: when set to (pattern_tuple_or_None, colour_or_None), is_goal()
# targets that HUD (key) state instead of the real insert goal. Only BFS reads is_goal, so this
# never affects the live game. None -> the real goal (block inserted in the lock with a matching key).
SUBGOAL = None
# For pure NAVIGATION BFS (used when SUBGOAL is None): (px_x, px_y) block-topleft target.
POS_GOAL = None


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

    # The BLOCK = the LARGEST solid component containing a BLK pixel. (Seeding at min(y),min(x) of
    # the BLK pixels can land on the PINWHEEL, which also contains colour 12/9.)
    solid = (E != VOID) & (E != FLOOR) & ~panelpx
    cands = [c for c in _comps(solid) if (E[c] == BLK).any()]
    blk = max(cands, key=lambda c: int(c.sum()))
    bx, by, bx1, by1 = _bbox(blk)
    bw, bh = bx1 - bx + 1, by1 - by + 1

    floor = _comp(E != VOID, (by, bx))           # walkable = anything not VOID, reachable
    block_sprite = E[by:by + bh, bx:bx + bw].copy()   # fixed sprite -> robust template matching

    locks = []
    hud = None
    for p in panels:
        x0, y0, x1, y1 = p['bbox']
        if floor[y0:y1 + 1, x0:x1 + 1].any():     # in the map -> a keyhole (there can be SEVERAL!)
            pat, col = _read(E, p)
            locks.append({'bbox': p['bbox'], 'pat': pat, 'col': col})
        else:
            hud = p                               # off-map -> the key you carry

    # --- glyph tiles on the walkable map (block excluded) ---
    gm = floor & ~np.isin(E, [FLOOR, PANEL]) & ~panelpx
    gm[by:by + bh, bx:bx + bw] = False
    rot = np.zeros((H, W), dtype=bool)      # 3x3 PLUS {0,1}, 5 cells: rotate key pattern 90 CW
    cyc = np.zeros((H, W), dtype=bool)      # 3x3 PINWHEEL, 9 cells: advance key COLOUR one step CW
    setp = np.zeros((H, W), dtype=bool)     # 3x3 {0}, 4 cells: CYCLE the key PATTERN shape
    refill = np.zeros((H, W), dtype=bool)   # 3x3 RING {11}, 8 cells: refill the bar, then consumed
    launch = {}                             # colour-1 EDGE LINE: cell -> slide direction
    wheel = []                              # the pinwheel's CW colour cycle
    glyph_list = []                         # (type, cell_x0, cell_y0) of each key-transform glyph
    unknown = []
    # 8-connectivity: the pattern-setter glyph is two diagonal pieces under 4-connectivity.
    for c in _comps(gm, diag=True):
        cols = set(int(v) for v in E[c])
        x0, y0, x1, y1 = _bbox(c)
        w, h, n = x1 - x0 + 1, y1 - y0 + 1, int(c.sum())
        if cols <= {0, 1} and (w, h, n) == (3, 3, 5):
            rot |= c
            glyph_list.append(('plus', x0 - 1, y0 - 1))     # coarse cell the 3x3 is centred in
        elif cols == {BAR} and (w, h, n) == (3, 3, 8):
            refill |= c
        elif (w, h, n) == (3, 3, 9):
            cyc |= c                        # pinwheel: 4 two-cell arms round a centre
            g = E[y0:y0 + 3, x0:x0 + 3]
            wheel = [int(g[0, 1]), int(g[1, 2]), int(g[2, 1]), int(g[1, 0])]   # N,E,S,W = CW order
            glyph_list.append(('pinwheel', x0 - 1, y0 - 1))
        elif cols == {0} and (w, h, n) == (3, 3, 4):
            setp |= c                       # CYCLES the key pattern shape (see SETTER_CYCLE)
            glyph_list.append(('setter', x0 - 1, y0 - 1))
        elif cols == {1} and w == 1 and h == bh and n == bh:
            # vertical line on a cell EDGE -> launches the block away from it, horizontally.
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

    # --- MOBILE key-glyphs: they PATROL one coarse cell per block MOVE, bouncing off the walls of
    # their row; their transform fires on CONVERGENCE (block & glyph END on the SAME cell), and the
    # block draws ON TOP (occlusion). Per-level mobility (confirmed): L4 = PLUS only; L5 = PLUS +
    # PINWHEEL + SETTER. On L0-L3 every glyph is STATIC (handled by the slide/cells loop instead).
    lvl = CURRENT_LEVEL if CURRENT_LEVEL is not None else -1

    def _is_mobile(t):
        if lvl < 4:
            return False
        return True if t == 'plus' else (lvl >= 5)

    mobiles = []
    for (t, cx0, cy0) in glyph_list:
        if not _is_mobile(t):
            continue
        sprite = E[cy0:cy0 + bh, cx0:cx0 + bw].copy()
        bg[cy0:cy0 + bh, cx0:cx0 + bw] = FLOOR      # drawn dynamically, not as backdrop
        # 2D PATROL: initial velocity is HORIZONTAL toward the FARTHER wall of the row segment
        # (tie -> left). Thereafter the glyph moves straight; when the cell ahead is a wall it turns,
        # preferring UP, then REVERSE, then DOWN, then the horizontals. Its START cell is a NEAR
        # BOUND: it reverses there rather than pass back through it (this is why L4's plus never
        # reaches -8 though it is free). Confirmed vs L4 plus (full traj) + L5 plus/pinwheel/setter.
        seg_lo = seg_hi = cx0
        while _cellfree(floor, seg_lo - bw, cy0, bw, bh):
            seg_lo -= bw
        while _cellfree(floor, seg_hi + bw, cy0, bw, bh):
            seg_hi += bw
        vx0 = 1 if (seg_hi - cx0) > (cx0 - seg_lo) else -1
        mobiles.append({'type': t, 'x0': cx0, 'y0': cy0, 'sprite': sprite, 'vx0': vx0})
        # remove from the static masks so the slide/cells loop does not double-apply the transform
        if t == 'plus':
            rot[cy0:cy0 + bh, cx0:cx0 + bw] = False
        elif t == 'pinwheel':
            cyc[cy0:cy0 + bh, cx0:cx0 + bw] = False
        elif t == 'setter':
            setp[cy0:cy0 + bh, cx0:cx0 + bw] = False

    res = dict(floor=floor, bg=bg, bw=bw, bh=bh, H=H, W=W, panelpx=panelpx, glyphpx=glyphpx,
               rot=rot, cyc=cyc, setp=setp, refill=refill, launch=launch, wheel=wheel,
               unknown=unknown, mobiles=mobiles, block_sprite=block_sprite, bx0=bx,
               barmask=barmask, barcols=barcols, bar0=len(barcols),
               locks=locks, hud=hud)
    _CACHE[ck] = res
    return res


def _block(G, M):
    """Locate the block by matching its fixed sprite. Robust to MOBILE glyphs (the pinwheel reuses
    colours 12/9 but never matches the full 5x5 sprite) and to the block sitting ON a glyph (it
    occludes it, so the block reads clean). Returns None when not visible (inserted in the lock)."""
    spr = M['block_sprite']
    bh, bw = spr.shape
    H, W = G.shape
    ys, xs = np.where(G == int(spr[0, 0]))
    for y, x in zip(ys.tolist(), xs.tolist()):
        if y + bh <= H and x + bw <= W and np.array_equal(G[y:y + bh, x:x + bw], spr):
            return int(x), int(y), bw, bh
    return None


DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}


def _free(M, x0, y0):
    bw, bh = M['bw'], M['bh']
    return (0 <= x0 and x0 + bw <= M['W'] and 0 <= y0 and y0 + bh <= M['H']
            and bool(M['floor'][y0:y0 + bh, x0:x0 + bw].all()))


def _which_lock(M, x0, y0, opened=()):
    """The (index, keyhole) the block would be FULLY inside at (x0,y0), or (None,None). A level can
    have SEVERAL keyholes; the block may only enter the one its key matches. An ALREADY-OPENED
    keyhole (index in `opened`) is now plain floor -> ignored."""
    bw, bh = M['bw'], M['bh']
    for i, lk in enumerate(M['locks']):
        if i in opened:
            continue
        lx0, ly0, lx1, ly1 = lk['bbox']
        if lx0 <= x0 and x0 + bw - 1 <= lx1 and ly0 <= y0 and y0 + bh - 1 <= ly1:
            return i, lk
    return None, None


def _matched(G, M, lk):
    """Key fits THIS keyhole only if BOTH the 3x3 pattern AND the colour agree."""
    if lk is None or M['hud'] is None:
        return False
    pat, colour = _read(G, M['hud'])
    return bool((pat == lk['pat']).all()) and colour == lk['col']


def _px(bar0, B, u):
    return int(math.floor(bar0 * (B - u) / B))


def _draw_bar(out, M, px):
    keep = set(M['barcols'][M['bar0'] - px:]) if px > 0 else set()
    for c in M['barcols']:
        rows = np.where(M['barmask'][:, c])[0]
        out[rows, c] = BAR if c in keep else FLOOR


def _setter_apply(pat):
    """SETTER advances the shape one step (A->B->...->F->A) and COMMUTES with rotation:
    setter(rot^k X) = rot^k next(X). (rot^k = k CW turns = np.rot90(.,-k), so the canonical is
    np.rot90(pat,k).)  Find the rotation that makes pat canonical, advance it, re-apply the rotation.
    Confirmed L5 #501: setter(rot(B)=#.#/..#/###) = rot(C)=#.#/.##/##.."""
    for k in range(4):
        base = np.rot90(pat, k)
        nxt = SETTER_CYCLE.get(tuple(tuple(int(v) for v in r) for r in base.tolist()))
        if nxt is not None:
            return np.rot90(np.array(nxt), -k)
    return pat


def init_state(entry_grid):
    B = LEVEL_BUDGET.get(CURRENT_LEVEL)
    M = _get_map()
    mob = tuple((m['x0'], m['y0'], m['vx0'], 0) for m in M['mobiles'])
    return {'u': 0, 'cands': (B,) if B else tuple(range(1, BMAX)), 'mob': mob, 'opened': ()}


def predict(state, grid, action, x=None, y=None):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    out = G.copy()
    info = {"level_up": False, "dead": False, "win": False}
    u = int(state.get('u', 0))
    cands = tuple(state.get('cands') or range(1, BMAX))
    mob = list(state.get('mob') or ())
    if len(mob) != len(M['mobiles']):
        mob = [(m['x0'], m['y0'], m['vx0'], 0) for m in M['mobiles']]
    opened = tuple(state.get('opened') or ())      # keyholes already opened (their panels -> floor)
    bg_eff = M['bg']
    if opened:
        bg_eff = M['bg'].copy()
        for i in opened:
            lx0, ly0, lx1, ly1 = M['locks'][i]['bbox']
            bg_eff[ly0:ly1 + 1, lx0:lx1 + 1] = FLOOR

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

    moved = refilled = bumped = False
    blk = _block(G, M)
    if blk is not None and action in DIRS:
        x0, y0, bw, bh = blk
        dx, dy = DIRS[action]
        nx0, ny0 = x0 + dx * bw, y0 + dy * bh
        # Two DIFFERENT kinds of "blocked":
        #  * into a WALL  -> the action still happens: the bar DRAINS, block+glyphs stay put.
        #  * into a SHUT KEYHOLE (key doesn't fit) -> the action is REFUSED entirely, for FREE.
        _i_dest, lk_dest = _which_lock(M, nx0, ny0, opened)
        shut = lk_dest is not None and not _matched(G, M, lk_dest)
        if not _free(M, nx0, ny0) and not shut:
            bumped = True
        if _free(M, nx0, ny0) and not shut:
            moved = True
            # a LAUNCHER on the entered cell fires the block onward until blocked (still ONE action)
            cells = [(nx0, ny0)]
            d = M['launch'].get((nx0, ny0))
            for _ in range(64):
                if d is None:
                    break
                tx, ty = cells[-1][0] + d[0] * bw, cells[-1][1] + d[1] * bh
                if not _free(M, tx, ty) or _which_lock(M, tx, ty, opened)[1] is not None:
                    break        # a slide never enters the keyhole: you must step in deliberately
                cells.append((tx, ty))
            fx, fy = cells[-1]
            old = (slice(y0, y0 + bh), slice(x0, x0 + bw))
            out[old] = np.where(M['refill'][old], FLOOR, bg_eff[old])   # spent rings/opened gates stay floor
            pat, colour = _read(G, M['hud']) if M['hud'] else (None, None)
            # STATIC glyphs the block slides over (mobile ones are removed from these masks).
            for (cx, cy) in cells:
                csl = (slice(cy, cy + bh), slice(cx, cx + bw))
                if M['rot'][csl].any() and pat is not None:
                    pat = np.rot90(pat, -1)                     # static plus: pattern 90 deg CW
                if M['cyc'][csl].any() and colour in M['wheel']:
                    w = M['wheel']
                    colour = w[(w.index(colour) + 1) % len(w)]  # static pinwheel: colour one CW
                if M['setp'][csl].any() and pat is not None:
                    pat = _setter_apply(pat)                     # static setter: cycle the SHAPE
                if (G[csl] == BAR).any():                       # live ring: refill, then consume
                    refilled = True
                    out[csl] = np.where(M['refill'][csl], FLOOR, out[csl])

            # --- MOBILE glyphs: move each one step (bounce), draw UNDER the block, and apply its
            # transform on CONVERGENCE (glyph ends on the block's final cell). ---
            newmob = []
            for i, m in enumerate(M['mobiles']):
                gx, gy, vx, vy = mob[i]
                v0x = m['vx0']
                mir = 2 * M['bx0'] - m['x0']    # reflection of start across the block's start column
                if mir != m['x0']:
                    # HORIZONTAL BOUNCE patrol [start, mirror]: reverse at START (heading -v0), at
                    # the MIRROR (heading +v0), or at a WALL; the glyph never leaves its row.
                    nxx = gx + vx * bw
                    if ((gx == m['x0'] and vx == -v0x) or (gx == mir and vx == v0x)
                            or not _cellfree(M['floor'], nxx, gy, bw, bh)):
                        vx = -vx
                        nxx = gx + vx * bw
                    nyy = gy
                else:
                    # glyph sits ON the block-start column -> 2D CW WALL-FOLLOW (rotate 90 CW when
                    # the cell ahead is blocked). (screen-coords CW: (vx,vy)->(-vy,vx))
                    nxx, nyy = gx + vx * bw, gy + vy * bh
                    if not _cellfree(M['floor'], nxx, nyy, bw, bh):
                        for _ in range(3):
                            vx, vy = -vy, vx
                            nxx, nyy = gx + vx * bw, gy + vy * bh
                            if _cellfree(M['floor'], nxx, nyy, bw, bh):
                                break
                out[gy:gy + bh, gx:gx + bw] = bg_eff[gy:gy + bh, gx:gx + bw]   # erase old
                out[nyy:nyy + bh, nxx:nxx + bw] = m['sprite']                    # draw new (under block)
                gx, gy = nxx, nyy
                newmob.append((gx, gy, vx, vy))
                if (gx, gy) == (fx, fy):                        # CONVERGENCE -> this glyph fires
                    if m['type'] == 'plus' and pat is not None:
                        pat = np.rot90(pat, -1)
                    elif m['type'] == 'setter' and pat is not None:
                        pat = _setter_apply(pat)
                    elif m['type'] == 'pinwheel' and colour in M['wheel']:
                        w = M['wheel']
                        colour = w[(w.index(colour) + 1) % len(w)]
            mob = newmob

            # Entering a keyhole with a MATCHING key CONSUMES its panel (-> floor): a GATE opens.
            # level_up ONLY when the LAST remaining keyhole is opened (all consumed).
            i_final, lk_final = _which_lock(M, fx, fy, opened)
            if lk_final is not None:                        # shut already ensured the key matches
                lx0, ly0, lx1, ly1 = lk_final['bbox']
                out[ly0:ly1 + 1, lx0:lx1 + 1] = FLOOR       # consume the keyhole panel
                opened = tuple(sorted(set(opened) | {i_final}))
                if len(opened) == len(M['locks']):
                    info['level_up'] = True
            # the block is drawn ON TOP of any glyph/floor it stands on (occlusion)
            out[fy:fy + bh, fx:fx + bw] = G[old]
            if M['hud'] is not None:
                _write(out, M['hud'], pat, colour)

    if (moved or bumped) and u >= B:
        info['dead'] = True
    if moved:
        u2 = 0 if refilled else u + 1
    elif bumped:
        u2 = u + 1              # bumping a wall costs a move
    else:
        u2 = u                  # keyhole refused the key: totally free no-op
    _draw_bar(out, M, max(0, _px(M['bar0'], B, min(u2, B))))
    return out.tolist(), info, {'u': u2, 'cands': cands, 'mob': tuple(mob), 'opened': opened}


def is_goal(grid):
    G = np.array(grid, dtype=np.int16)
    M = _get_map()
    okhud = True
    if SUBGOAL is not None:                        # phased BFS: aim for a HUD (key) sub-state
        if M['hud'] is None:
            return False
        pat, colour = _read(G, M['hud'])
        wp, wc = SUBGOAL
        okhud = ((wp is None or tuple(tuple(int(v) for v in r) for r in pat.tolist()) == wp)
                 and (wc is None or colour == wc))
    if POS_GOAL is not None:                        # navigation waypoint (+ preserve key if SUBGOAL set)
        b = _block(G, M)
        return okhud and b is not None and (b[0], b[1]) == tuple(POS_GOAL)
    if SUBGOAL is not None:
        return okhud
    if not M['locks']:
        return False
    for lk in M['locks']:                         # level complete iff EVERY keyhole is opened
        x0, y0, x1, y1 = lk['bbox']               # (its panel consumed -> no PANEL pixels remain)
        if (G[y0:y1 + 1, x0:x1 + 1] == PANEL).any():
            return False
    return True
