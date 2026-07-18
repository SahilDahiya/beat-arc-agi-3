import numpy as np

# ============================================================
# Room-hop maze model (ARC3), grid-grounded (robust to state re-init).
#
# Rendering: 64x64. Background=5. Bottom row(63)=HUD move counter (0s fill from the RIGHT).
# Content: NxN logical cells, each a 3x3 pixel block, at pixel origin (ox,oy).
#   wall cell   = 3x3 of 5
#   corridor    = 3x3 of 0 (if (x+y) even) or 2 (odd)   [decorative checkerboard]
#   goal cell   = 3x3 of 14
#   player cell = sprite [[9,9,9],[9,9,4],[9,9,9]] drawn on top of underlying corridor.
#
# Movement: ROOM-HOP. Rooms at even logical coords; door = the odd cell between two rooms.
#   dir: 1=up 2=down 3=left 4=right. A hop moves the player 2 cells (door+dest room) iff BOTH
#   the door cell and destination cell are walkable (block not all-5); else no move.
# Counter: += max(1, cells_moved)  (blocked=+1, hop=+2). Reaching goal => level_up.
#
# The player position and current counter are READ FROM THE INPUT GRID each call (not stored
# state) so replay/backtest can never desync. State carries only the static layout (+player,
# for BFS dedup).
# ============================================================

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}  # up,down,left,right
# local (row,col) position of the '4' sprite pixel = facing direction of last successful move
FACE = {1: (0, 1), 2: (2, 1), 3: (1, 0), 4: (1, 2)}    # up,down,left,right
# HUD counter increment: +1 per action, EXCEPT a hop LEAVING a cell whose BOTH logical coords
# are divisible by 4 (x%4==0 and y%4==0) costs +2. Blocked always +1.
# (empirical dHUD over 6 steps = 1,2,1,1,1,2 for moves U*,E,D,D,E,U from
#  (0,0),(0,0),(2,0),(2,2),(2,4),(4,4); +2 exactly when leaving (0,0) and (4,4).)


def _find_layout(a):
    H, W = a.shape
    mask = (a != 5)
    for r in range(H):
        row = a[r]
        if row[0] == 6 and np.all(row == 6):
            mask[r, :] = False  # exclude HUD row(s)
    ys, xs = np.where(mask)
    oy, ox = int(ys.min()), int(xs.min())
    n = (int(ys.max()) - oy + 1) // 3
    return n, ox, oy


def _blk(a, ox, oy, x, y):
    return a[oy + 3 * y:oy + 3 * y + 3, ox + 3 * x:ox + 3 * x + 3]


def _is_wall(a, ox, oy, n, x, y):
    if not (0 <= x < n and 0 <= y < n):
        return True
    return bool(np.all(_blk(a, ox, oy, x, y) == 5))


def _find_player(a, ox, oy, n):
    for y in range(n):
        for x in range(n):
            b = _blk(a, ox, oy, x, y)
            if np.any(b == 4) or np.any(b == 9):
                return (x, y)
    return None


def _find_goal(a, ox, oy, n):
    for y in range(n):
        for x in range(n):
            if np.all(_blk(a, ox, oy, x, y) == 14):
                return (x, y)
    return None


def init_state(entry):
    a = np.array(entry, dtype=int)
    n, ox, oy = _find_layout(a)
    p0 = _find_player(a, ox, oy, n)
    return {'n': n, 'ox': ox, 'oy': oy,
            'goal': _find_goal(a, ox, oy, n),
            'player': p0, 'start': p0}


def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    n, ox, oy = state['n'], state['ox'], state['oy']
    goal = state.get('goal') or _find_goal(a, ox, oy, n)
    pos = _find_player(a, ox, oy, n)
    ns = dict(state)
    if pos is None or action not in DIRS:
        return grid, {'level_up': False, 'win': False, 'dead': False}, ns
    px, py = pos
    dx, dy = DIRS[action]
    door = (px + dx, py + dy)
    dest = (px + 2 * dx, py + 2 * dy)
    npos = (px, py)
    hop = (not _is_wall(a, ox, oy, n, *door)) and (not _is_wall(a, ox, oy, n, *dest))
    if hop:
        npos = dest
    # HUD counter increment. TRUE RULE UNKNOWN (some moves cost +2, positional, not yet cracked).
    # Using +1 always: correct for the majority; a committed plan chains through +1 moves and halts
    # exactly at each +2 move, cleanly revealing that +2 source position as data. Movement+sprite
    # are exact, so only the HUD mismatches. Known +2 sources so far: (0,0),(4,4),(6,4).
    if hop:
        inc = 1
        face = FACE[action]
    else:
        inc = 1
        cur_block = _blk(a, ox, oy, px, py)
        f = np.argwhere(cur_block == 4)
        face = (int(f[0][0]), int(f[0][1])) if len(f) else (1, 2)
    cur = int(np.sum(a[63, :] == 0))
    counter = min(cur + inc, 64)
    out = a.copy()
    # erase old player cell -> underlying corridor color (rooms at even coords -> 0)
    oc = 0 if (px + py) % 2 == 0 else 2
    out[oy + 3 * py:oy + 3 * py + 3, ox + 3 * px:ox + 3 * px + 3] = oc
    # draw player sprite at new pos with '4' facing the move dir
    cx, cy = npos
    spr = np.full((3, 3), 9, dtype=int)
    spr[face[0], face[1]] = 4
    out[oy + 3 * cy:oy + 3 * cy + 3, ox + 3 * cx:ox + 3 * cx + 3] = spr
    # HUD
    out[63, :] = 6
    if counter > 0:
        out[63, 64 - counter:64] = 0
    ns['player'] = npos
    win = (goal is not None and npos == tuple(goal))
    info = {'level_up': bool(win), 'win': False, 'dead': False}
    return out.tolist(), info, ns


def is_goal(state, grid=None):
    if not isinstance(state, dict):
        return False
    p = state.get('player')
    return p is not None and p == state.get('goal')
