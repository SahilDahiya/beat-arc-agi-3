import numpy as np

# ============================================================
# Room-hop maze model (ARC3), grid-grounded. Supports non-square grids.
#
# Rendering: 64x64. Background=5. Bottom row(63)=HUD move counter (0s fill from the RIGHT).
# Content: nx*ny logical cells, each a 3x3 pixel block, at pixel origin (ox,oy).
#   wall cell   = 3x3 of 5
#   corridor    = 3x3 of 0 (if (x+y) even) or 2 (odd)   [decorative checkerboard]
#   goal cell   = 3x3 of 14
#   player cell = sprite: all 9 with a single 4 pixel that POINTS toward last-move dir
#                 (up=(0,1) down=(2,1) left=(1,0) right=(1,2) local coords); blocked keeps facing.
#   special obj = e.g. color-8 block with a 15 pixel  [level 1+; mechanic TBD]
#
# Movement: ROOM-HOP. Rooms at even logical coords; door = odd cell between two rooms.
#   dir 1=up 2=down 3=left 4=right. Hop moves player 2 cells (door+dest) iff BOTH door and dest
#   are walkable (block not all-5); else no move.
# HUD: +1 per action. (SOME hops cost +2 - positional rule UNCRACKED; using +1-always so plans
#   chain +1 moves and halt exactly at each +2, revealing it. Movement+sprite are exact.)
# Reaching goal => level_up.
#
# Layout (ox,oy,nx,ny) derived from ENTRY_GRID (stable per level); player/goal/counter/walls read
# from the live grid each call (robust to state re-init).
# ============================================================

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
FACE = {1: (0, 1), 2: (2, 1), 3: (1, 0), 4: (1, 2)}
# HUD counter increment: normally +1, but +2 when the CURRENT counter (before the move) is one of
# these values. Discovered level 0: +2 at counter_before {1,6,10,15,20}; level 1 also +2 at 1.
# => appears COUNTER-based (level-independent), not positional. Extend as more levels confirm.
HUD_PLUS2 = {1, 6, 10, 15, 20, 25, 30, 35, 40, 45}  # confirmed {1,6,10,15,20}; rest = {1,6}∪mult-of-5 guess


def _find_layout(a):
    H, W = a.shape
    mask = (a != 5)
    for r in range(H):
        if a[r, 0] == 6 and np.all(a[r] == 6):
            mask[r, :] = False  # exclude HUD row(s)
    ys, xs = np.where(mask)
    oy, ox = int(ys.min()), int(xs.min())
    ny = (int(ys.max()) - oy + 1) // 3
    nx = (int(xs.max()) - ox + 1) // 3
    return ox, oy, nx, ny


def _layout(grid_arr):
    try:
        src = np.array(ENTRY_GRID, dtype=int)
    except NameError:
        src = grid_arr
    return _find_layout(src)


def _blk(a, ox, oy, x, y):
    return a[oy + 3 * y:oy + 3 * y + 3, ox + 3 * x:ox + 3 * x + 3]


def _is_wall(a, ox, oy, nx, ny, x, y):
    if not (0 <= x < nx and 0 <= y < ny):
        return True
    return bool(np.all(_blk(a, ox, oy, x, y) == 5))


def _find_player(a, ox, oy, nx, ny):
    for y in range(ny):
        for x in range(nx):
            if np.any(_blk(a, ox, oy, x, y) == 4):
                return (x, y)
    return None


def _find_goal(a, ox, oy, nx, ny):
    for y in range(ny):
        for x in range(nx):
            if np.all(_blk(a, ox, oy, x, y) == 14):
                return (x, y)
    return None


def init_state(entry):
    a = np.array(entry, dtype=int)
    ox, oy, nx, ny = _find_layout(a)
    return {'ox': ox, 'oy': oy, 'nx': nx, 'ny': ny,
            'goal': _find_goal(a, ox, oy, nx, ny),
            'player': _find_player(a, ox, oy, nx, ny)}


def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    ox, oy, nx, ny = _layout(a)
    goal = _find_goal(a, ox, oy, nx, ny)
    pos = _find_player(a, ox, oy, nx, ny)
    ns = dict(state)
    if pos is None or action not in DIRS:
        return grid, {'level_up': False, 'win': False, 'dead': False}, ns
    px, py = pos
    dx, dy = DIRS[action]
    door = (px + dx, py + dy)
    dest = (px + 2 * dx, py + 2 * dy)
    hop = (not _is_wall(a, ox, oy, nx, ny, *door)) and (not _is_wall(a, ox, oy, nx, ny, *dest))
    npos = dest if hop else (px, py)
    if hop:
        face = FACE[action]
    else:
        f = np.argwhere(_blk(a, ox, oy, px, py) == 4)
        face = (int(f[0][0]), int(f[0][1])) if len(f) else (1, 2)
    cur = int(np.sum(a[63, :] == 0))
    counter = min(cur + (2 if cur in HUD_PLUS2 else 1), 64)
    out = a.copy()
    oc = 0 if (px + py) % 2 == 0 else 2
    out[oy + 3 * py:oy + 3 * py + 3, ox + 3 * px:ox + 3 * px + 3] = oc
    cx, cy = npos
    spr = np.full((3, 3), 9, dtype=int)
    spr[face[0], face[1]] = 4
    out[oy + 3 * cy:oy + 3 * cy + 3, ox + 3 * cx:ox + 3 * cx + 3] = spr
    out[63, :] = 6
    if counter > 0:
        out[63, 64 - counter:64] = 0
    ns['player'] = npos
    win = (goal is not None and npos == tuple(goal))
    return out.tolist(), {'level_up': bool(win), 'win': False, 'dead': False}, ns


def is_goal(state, grid=None):
    if not isinstance(state, dict):
        return False
    p = state.get('player')
    return p is not None and p == state.get('goal')
