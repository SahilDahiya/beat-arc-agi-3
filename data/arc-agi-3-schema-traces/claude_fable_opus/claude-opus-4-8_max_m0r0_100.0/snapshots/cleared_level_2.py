# World model — "you and your MIRROR CLONE" maze.
#
# CORE MECHANICS (levels 0-2)
#  1. Board = lattice of SxS blocks. Colour 5 = floor; the two room-background colours = wall.
#  2. TWO avatars, ONE key. B is the MIRROR of A about a vertical axis: bx_A + bx_B is invariant
#     while both move freely. VERTICAL moves are the SAME; HORIZONTAL moves are OPPOSITE.
#  3. A blocked avatar stays put while the other still moves => walls DESYNC the pair. Required.
#  4. GOAL: both avatars onto the SAME block. Needs bx_A == bx_B, NOT sum == MSUM.
#  5. BAR (the two all-floor border rows) = (5n+6)//12 = round(5n/12): pure HUD, counts actions
#     only. Refitted against ALL 21 bar observations across levels 0-2 (3/7 was slightly too fast
#     and only broke at high n: it said 18 at n=41 where the truth is 17).
#     EVERY action counts, including ACTION5 and ACTION6.
#  6. CHIRALITY IS A FIXED IDENTITY carried in state — never derived from left/right position.
#     The avatars cross; both are one colour so the swap is invisible in the grid.
#
# LEVEL 2: THE "DOORS" ARE PUSHABLE BLOCKS YOU PILOT (the reason ACTION5/6 exist)
#   ACTION6 = CLICK a door -> you TAKE CONTROL of it (colour 9 -> 11) and BOTH AVATARS FREEZE
#   (colour 10 -> 1). While a door is held, the direction keys move THAT DOOR, one block, in the
#   RAW direction (no mirroring — there is only one of it) and the avatars do not move at all.
#   CLICK = "SELECT WHAT YOU CONTROL", NOT a toggle: clicking the door you already hold is a
#   NO-OP. To get the avatars back you CLICK AN AVATAR. So doors are not locks: they are
#   obstacles you relocate.
#   => doors MOVE, so they must be located in the CURRENT grid every step. Looking them up at
#   their ENTRY blocks silently loses them the instant one is pushed.
#
# (older heading kept for context) LEVEL 2: DOORS + POLARITY
#  * "Doors" are 2x2 cores centred in a floor block. They BLOCK movement.
#  * ACTION5 is INERT (it only burns an action).
#  * ACTION6 = CLICK a door: that door toggles its colour (9 <-> 11) AND BOTH AVATARS toggle
#    theirs (10 <-> 1). Nothing else moves.
#  * So the AVATAR COLOUR IS NOT CONSTANT. Never look up avatars by the entry colour: find them
#    as the colour whose lattice blocks are completely FILLED (doors are only a 2x2 core).
#  * OPEN QUESTION (probing now): which (avatar colour, door colour) pairs are passable?
#    Known: avatar 10 could NOT pass door 9.

from collections import deque

FLOOR = 5
BUMP = 0

# BAR = (32n+37)//75  ~= round(64*n/150): a 64-px bar over a ~150-ACTION level budget.
# Fitted to EVERY transition of levels 0-2. Earlier 3/7 was very slightly too fast and only broke
# at n=41 (said 18, truth 17); (5n+6)//12 fitted the turn-boundary samples but failed 11 steps —
# a reminder to fit against EVERY action, not just the frames I happen to have lying around.

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}   # 1=UP 2=DOWN 3=LEFT 4=RIGHT (for A)

DOOR_IDLE, DOOR_HELD = 9, 11   # a door you are NOT / ARE piloting
AV_FROZEN = 1                  # avatars while some door is selected
DOOR_ALT = {9: 11, 11: 9}      # a click flips the clicked door
AV_ALT = {10: 1, 1: 10}        # ...and flips both avatars

_CACHE = {}


def _blobs(a, c, H, W):
    m = (a == c)
    seen = np.zeros_like(m)
    out = []
    for y0, x0 in zip(*np.where(m)):
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
                if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        out.append(cells)
    return out


def _square_side(cells):
    ys = [c[0] for c in cells]
    xs = [c[1] for c in cells]
    h = max(ys) - min(ys) + 1
    w = max(xs) - min(xs) + 1
    return h if (h == w and h * w == len(cells)) else 0


def _analyse(entry):
    key = tuple(tuple(r) for r in entry)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit

    a = np.array(entry, dtype=int)
    H, W = a.shape

    bg = frozenset(set(np.unique(a[1]).tolist()) | set(np.unique(a[H - 2]).tolist()))
    specials = set(np.unique(a).tolist()) - set(bg) - {FLOOR}

    best, tok, S = 0, None, 1
    sides = {}
    for c in sorted(specials):
        bs = _blobs(a, c, H, W)
        ss = [_square_side(b) for b in bs]
        side = min(ss) if ss and min(ss) > 0 else 0
        sides[c] = side
        if side > best:
            best, tok, S = side, c, side
    door_cols = set(c for c in specials if c != tok and sides.get(c, 0) >= 2)
    haz_cols = set(specials) - {tok} - door_cols

    tb = _blobs(a, tok, H, W)[0]
    py, px = min(c[0] for c in tb) % S, min(c[1] for c in tb) % S
    nby, nbx = (H - py) // S, (W - px) // S

    def cols_of(bx, by):
        return set(np.unique(a[py + S * by: py + S * by + S,
                              px + S * bx: px + S * bx + S]).tolist())

    wall = np.ones((nby, nbx), dtype=bool)
    haz = np.zeros((nby, nbx), dtype=bool)
    doors = []
    for by in range(nby):
        for bx in range(nbx):
            u = cols_of(bx, by)
            if u == {FLOOR} or u == {tok}:
                wall[by, bx] = False
            elif u & haz_cols:
                haz[by, bx] = True
                wall[by, bx] = False
            elif u & door_cols:
                wall[by, bx] = False        # floor UNDERNEATH; the door is a movable OBJECT
                doors.append((bx, by))

    ent = sorted((bx, by) for by in range(nby) for bx in range(nbx)
                 if (a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] == tok).all())
    msum = (ent[0][0] + ent[-1][0]) if len(ent) >= 2 else 0
    has_bar = bool((a[0] == FLOOR).all() and (a[H - 1] == FLOOR).all())

    res = (tok, S, py, px, nby, nbx, wall, len(ent), msum, has_bar, haz, ent,
           tuple(doors), bg, frozenset(door_cols))
    _CACHE[key] = res
    return res


def _avatars(a, S, py, px, nby, nbx, bg):
    """Find the avatars in the CURRENT grid. Their COLOUR CHANGES when a door is clicked, so we
    locate them structurally: the only colour whose lattice blocks are completely FILLED SxS
    (a door is merely a 2x2 core inside a floor block)."""
    for c in sorted(set(np.unique(a).tolist()) - set(bg) - {FLOOR}):
        ys, xs = np.where(a == c)
        blks = set()
        for y, x in zip(ys.tolist(), xs.tolist()):
            by, bx = (y - py) // S, (x - px) // S
            if 0 <= bx < nbx and 0 <= by < nby:
                blks.add((bx, by))
        if not blks:
            continue
        if all((a[py + S * b[1]: py + S * b[1] + S,
                  px + S * b[0]: px + S * b[0] + S] == c).all() for b in blks):
            return c, sorted(blks)
    return None, []


def _doors_now(a, S, py, px, nby, nbx, door_cols):
    """Doors MOVE (you pilot them), so they must be found in the CURRENT grid — looking them up
    at their ENTRY blocks silently loses them the moment one is pushed."""
    # COLOUR ROLES ARE PER-LEVEL: colour 11 is a room BACKGROUND on level 0, so never scan for
    # door colours on a level that has none.
    if not door_cols:
        return {}
    cols = set(door_cols)
    for c in list(cols):
        if c in DOOR_ALT:
            cols.add(DOOR_ALT[c])
    out = {}
    for c in sorted(cols):
        ys, xs = np.where(a == c)
        for y, x in zip(ys.tolist(), xs.tolist()):
            by, bx = (y - py) // S, (x - px) // S
            if 0 <= bx < nbx and 0 <= by < nby:
                out[(bx, by)] = int(c)
    return out


def init_state(entry_grid):
    try:
        lvl = CURRENT_LEVEL
    except NameError:
        lvl = None
    tok, S, py, px, nby, nbx, wall, n0, msum, has_bar, haz, ent, doors, bg, door_cols = _analyse(entry_grid)
    A = ent[0] if ent else (0, 0)
    B = ent[-1] if len(ent) > 1 else A
    return {"n": 1 if lvl == 0 else 0, "A": list(A), "B": list(B)}


def predict(state, grid, action, x=None, y=None):
    tok, S, py, px, nby, nbx, wall, n0, msum, has_bar, haz, ent, doors, bg, door_cols = _analyse(ENTRY_GRID)
    a = np.array(grid, dtype=int)
    H, W = a.shape

    acol, old = _avatars(a, S, py, px, nby, nbx, bg)
    if acol is None:
        acol, old = tok, []
    dcol = _doors_now(a, S, py, px, nby, nbx, door_cols)

    st = state or {}
    n = int(st.get("n", 0))
    sA = tuple(st.get("A", old[0] if old else (0, 0)))
    sB = tuple(st.get("B", old[-1] if old else (0, 0)))

    def dist(p, q):
        return abs(p[0] - q[0]) + abs(p[1] - q[1])
    if len(old) >= 2:
        p, q = old[0], old[1]
        posA, posB = (p, q) if dist(p, sA) + dist(q, sB) <= dist(q, sA) + dist(p, sB) else (q, p)
    elif old:
        posA = posB = old[0]
    else:
        posA, posB = sA, sB

    info = {"level_up": False, "dead": False, "win": False}
    n2 = n + 1

    def paint_bar(arr):
        if has_bar:
            cnt = min((32 * n2 + 37) // 75, W)
            arr[0, :] = FLOOR
            arr[H - 1, :] = FLOOR
            if cnt:
                arr[0, W - cnt:] = BUMP
                arr[H - 1, :cnt] = BUMP

    # ---- ACTION 6 = CLICK = "SELECT WHAT YOU CONTROL".  It is NOT a toggle:
    #   * click an IDLE door  -> you pilot it (9->11); every other door goes idle; avatars FREEZE.
    #   * click the HELD door -> it is already selected => NO-OP (confirmed: clicking the held
    #     door at (3,2) changed nothing at all, though it still burned an action).
    #   * click an AVATAR     -> the avatars wake (->10) and every door goes idle (->9).
    if action == 6:
        if x is not None and y is not None:
            bx, by = (int(x) - px) // S, (int(y) - py) // S
            tgt = (bx, by)
            def put(d, col):
                cy, cx = py + S * d[1] + S // 2 - 1, px + S * d[0] + S // 2 - 1
                a[cy:cy + 2, cx:cx + 2] = col
            def paint_av(col):
                for (abx, aby) in old:
                    a[py + S * aby: py + S * aby + S, px + S * abx: px + S * abx + S] = col
            if tgt in dcol:
                for d in dcol:
                    put(d, DOOR_HELD if d == tgt else DOOR_IDLE)
                paint_av(AV_FROZEN)
            elif tgt == posA or tgt == posB:
                for d in dcol:
                    put(d, DOOR_IDLE)
                paint_av(tok)
        paint_bar(a)
        return a.tolist(), info, {"n": n2, "A": list(posA), "B": list(posB)}

    # ---- ACTION 5 (and anything else non-directional): inert, but still burns an action.
    if action not in DIRS or not old:
        paint_bar(a)
        return a.tolist(), info, {"n": n2, "A": list(posA), "B": list(posB)}

    # ---- directional move.  WHO is under control?  A door showing the HELD colour, else the
    # avatars.  Confirmed level 2: while a door was held, action 4 moved THE DOOR one block right
    # (raw direction, no mirroring) and BOTH avatars stayed put.
    held = None
    for d, c in dcol.items():
        if c == DOOR_HELD:
            held = d
            break

    dx, dy = DIRS[action]

    if held is not None:
        nd = (held[0] + dx, held[1] + dy)
        ok = (0 <= nd[0] < nbx and 0 <= nd[1] < nby and not wall[nd[1], nd[0]]
              and nd not in dcol and nd != posA and nd != posB)
        newd = nd if ok else held
        cy, cx = py + S * held[1] + S // 2 - 1, px + S * held[0] + S // 2 - 1
        a[cy:cy + 2, cx:cx + 2] = FLOOR                      # lift it off the old block
        cy, cx = py + S * newd[1] + S // 2 - 1, px + S * newd[0] + S // 2 - 1
        a[cy:cy + 2, cx:cx + 2] = DOOR_HELD                  # set it down on the new one
        paint_bar(a)
        return a.tolist(), info, {"n": n2, "A": list(posA), "B": list(posB)}

    # nothing held -> the mirrored avatar pair moves; doors are solid obstacles
    new, died = [], False
    for i, (bx, by) in enumerate([posA, posB]):
        chir = 1 if i == 0 else -1
        nx, ny = bx + chir * dx, by + dy
        ok = (0 <= nx < nbx and 0 <= ny < nby and not wall[ny, nx] and (nx, ny) not in dcol)
        if ok:
            new.append((nx, ny))
            if haz[ny, nx]:
                died = True
        else:
            new.append((bx, by))
    for (bx, by) in [posA, posB]:
        a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] = FLOOR
    for (bx, by), c in dcol.items():
        if c is not None:
            cy, cx = py + S * by + S // 2 - 1, px + S * bx + S // 2 - 1
            a[cy:cy + 2, cx:cx + 2] = c
    for (bx, by) in new:
        a[py + S * by: py + S * by + S, px + S * bx: px + S * bx + S] = acol

    paint_bar(a)
    if died:
        info["dead"] = True
    elif n0 > 1 and len(set(new)) == 1:
        info["level_up"] = True
    return a.tolist(), info, {"n": n2, "A": list(new[0]), "B": list(new[1])}


def is_goal(state, grid):
    tok, S, py, px, nby, nbx, wall, n0, msum, has_bar, haz, ent, doors, bg, door_cols = _analyse(ENTRY_GRID)
    a = np.array(grid, dtype=int)
    _, blks = _avatars(a, S, py, px, nby, nbx, bg)
    return n0 > 1 and len(blks) == 1
