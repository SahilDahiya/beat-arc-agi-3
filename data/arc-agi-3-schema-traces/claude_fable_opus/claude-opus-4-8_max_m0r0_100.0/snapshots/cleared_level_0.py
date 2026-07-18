# World model — "you and your MIRROR CLONE" maze.
#
# CONFIRMED MECHANICS
#  1. Board = lattice of SxS blocks. Colour 5 = floor; the two bg colours = wall.
#  2. Two avatars driven by ONE key, but avatar B is the MIRROR IMAGE of avatar A about a
#     vertical axis:  bx_A + bx_B = MSUM  (invariant while both move freely).
#     => VERTICAL moves are the SAME for both; HORIZONTAL moves are OPPOSITE.
#     (ACTION1=UP could never reveal this — a horizontal mirror leaves dy untouched.
#      ACTION4 exposed it: A stalled on a wall going RIGHT while B went LEFT.)
#  3. An avatar that would enter a wall / leave the board DOES NOT MOVE while the other still
#     does => walls DESYNCHRONISE the pair. That is the only way to break the mirror relation,
#     and it is REQUIRED (the "both-walkable" intersection maze is disconnected).
#  4. THE BAR (the two all-floor border rows; colour 0; row 0 fills right->left, row H-1
#     left->right, both showing the same count) = floor(n_actions / 2).  A MOVE-BUDGET bar:
#     one pixel per TWO actions, 64 px => a 128-action level budget.
#        n:   1  2  3  4
#        bar: 0  1  1  2      <- ticks only on even n
#     Ruled out: |dy| desync (f3 and f4 share desync (-1,+1) but show bar 1 vs 2), and any
#     bump counter (move 4 bumped NOBODY yet still ticked; move 3 bumped yet did NOT tick).
#     The bar is history-dependent, so it needs state — but see the note on init_state below.
#
# GOAL: both avatars onto the SAME block. Under a perfect mirror that can only happen ON the
# axis, so the merge square is the unique floor block of column bx=axis — dead centre of the
# top corridor, the one place the two rooms connect.
#
# Everything (lattice, walls, token colour, axis, bar) is derived from ENTRY_GRID.

from collections import deque

FLOOR = 5
BUMP = 0

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}   # 1=UP, 4=RIGHT confirmed; 2/3 assumed

_CACHE = {}


def _analyse(entry):
    key = tuple(tuple(r) for r in entry)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit

    a = np.array(entry, dtype=int)
    H, W = a.shape

    cols, cnts = np.unique(a, return_counts=True)
    tok = min([(int(c), int(n)) for c, n in zip(cols, cnts) if int(c) != FLOOR],
              key=lambda t: t[1])[0]

    mask = (a == tok)
    seen = np.zeros_like(mask)
    blobs = []
    for y0, x0 in zip(*np.where(mask)):
        y0, x0 = int(y0), int(x0)
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)])
        seen[y0, x0] = True
        cells = []
        while q:
            y, x = q.popleft()
            cells.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        blobs.append(cells)

    ys = [c[0] for c in blobs[0]]
    xs = [c[1] for c in blobs[0]]
    S = max(1, max(ys) - min(ys) + 1)
    py, px = min(ys) % S, min(xs) % S
    nby, nbx = (H - py) // S, (W - px) // S

    wall = np.ones((nby, nbx), dtype=bool)
    for by in range(nby):
        for bx in range(nbx):
            blk = a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S]
            u = set(np.unique(blk).tolist())
            if u == {FLOOR} or u == {tok}:
                wall[by, bx] = False

    ent = sorted((bx, by) for by in range(nby) for bx in range(nbx)
                 if (a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] == tok).all())
    msum = (ent[0][0] + ent[-1][0]) if len(ent) >= 2 else 0
    has_bar = bool((a[0] == FLOOR).all() and (a[H - 1] == FLOOR).all())

    res = (tok, S, py, px, nby, nbx, wall, len(ent), msum, has_bar)
    _CACHE[key] = res
    return res


def _tokens(a, tok, S, py, px, nby, nbx):
    return sorted((bx, by) for by in range(nby) for bx in range(nbx)
                  if (a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] == tok).all())


def init_state(entry_grid):
    # FRAMEWORK ARTEFACT: the run's very first transition is replayed WITHOUT advancing state
    # (tools.py:954 and agent.py:468 both `continue` before `state = next_state`). So on the
    # level that contains that step (level 0) our counters start exactly one action behind.
    # That skipped step was action 1 with BOTH avatars moving, so seeding n=1, bumps=0 reproduces
    # the framework's lagged state exactly.
    # CAVEAT: this seed is only right while level 0 has never been RESET. If you ever RESET
    # level 0, change the seed to n=0 (after a reset the rollout re-inits and no longer skips).
    try:
        lvl = CURRENT_LEVEL
    except NameError:
        lvl = None
    return {"n": 1 if lvl == 0 else 0, "bumps": 0}


def predict(state, grid, action, x=None, y=None):
    tok, S, py, px, nby, nbx, wall, n0, msum, has_bar = _analyse(ENTRY_GRID)
    a = np.array(grid, dtype=int)
    H, W = a.shape
    old = _tokens(a, tok, S, py, px, nby, nbx)

    st = state or {}
    n = int(st.get("n", 0))
    bumps = int(st.get("bumps", 0))

    info = {"level_up": False, "dead": False, "win": False}
    if action not in DIRS or not old:
        return grid, info, {"n": n, "bumps": bumps}   # ACTION5 / clicks: unprobed, no-op

    dx, dy = DIRS[action]
    new, blocked = [], 0
    for i, (bx, by) in enumerate(old):
        chir = 1 if i == 0 else -1                 # leftmost avatar un-mirrored, other mirrored
        nx, ny = bx + chir * dx, by + dy
        if 0 <= nx < nbx and 0 <= ny < nby and not wall[ny, nx]:
            new.append((nx, ny))
        else:
            new.append((bx, by))                   # blocked -> stay put, and it costs a BUMP
            blocked += 1

    n2, bumps2 = n + 1, bumps + blocked
    for (bx, by) in old:
        a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] = FLOOR
    for (bx, by) in new:
        a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] = tok

    # THE BAR = floor(3*(n+1)/7): a pure MOVE-BUDGET bar, 3 px per 7 actions.
    # Bumps do NOT affect it (every linear fit over (both-steps, bump-steps) collapsed to a
    # function of n alone). The rate is just UNDER 1/2, which is why floor(n/2) fitted n<=7 and
    # then drifted. Tick gaps run 2,2,3 repeating.
    if has_bar:
        cnt = min((3 * (n2 + 1)) // 7, W)
        for i in range(W):
            c = BUMP if i < cnt else FLOOR
            a[0, W - 1 - i] = c
            a[H - 1, i] = c

    if n0 > 1 and len(set(new)) == 1:
        info["level_up"] = True
    return a.tolist(), info, {"n": n2, "bumps": bumps2}


def is_goal(state, grid):
    tok, S, py, px, nby, nbx, wall, n0, msum, has_bar = _analyse(ENTRY_GRID)
    a = np.array(grid, dtype=int)
    return n0 > 1 and len(_tokens(a, tok, S, py, px, nby, nbx)) == 1
