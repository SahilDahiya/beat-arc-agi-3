import numpy as np

# ============================================================
# Room-hop maze model (ARC3). Non-square grids. Boxes tracked in STATE (a list) because color-12
# patrol boxes can OVERLAP (never merge) and the grid can't represent two boxes in one cell.
#
# Rendering: 64x64. bg=5. row63 = HUD move counter (0s fill from RIGHT). Content = nx*ny logical
#   cells (3x3 px each) at pixel origin (ox,oy). wall=all5; corridor=0 if (x+y)even else 2; goal=14;
#   player sprite = all 9 with one 4 pixel pointing at last-move dir; box = all(color) with one 15
#   'f' pixel giving its facing.
# Movement: room-hop; hop moves player 2 cells iff BOTH door(+dir) and dest(+2dir) are walkable.
# BOX types (each has a 15 'f' facing pixel):
#   color 8  = STATIC. Kill zone = room 2 cells in facing dir (hop INTO it = die). Hopping onto the
#              box's own cell (non-facing side) DESTROYS it.
#   color 12 = PATROL. On each successful player HOP it advances 1 room in facing dir (door+dest must
#              be walkable); on arrival it FLIPS facing if it can't continue (patrols back). Boxes move
#              independently & may overlap. Die if a box lands on the player, or player/box swap.
# HUD increment per move = BASE_BY_LEVEL[level] (majority); occasional +-1 minority moves just halt.
# Boxes+player move in lockstep (box advances only on a hop) -> deterministic per hop-count.
# ============================================================

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
FACE = {1: (0, 1), 2: (2, 1), 3: (1, 0), 4: (1, 2)}
FACE2DIR = {(1, 0): (-1, 0), (1, 2): (1, 0), (0, 1): (0, -1), (2, 1): (0, 1)}
DIR2FACE = {(-1, 0): (1, 0), (1, 0): (1, 2), (0, -1): (0, 1), (0, 1): (2, 1)}
BASE_BY_LEVEL = {0: 1, 1: 1, 2: 2, 3: 3, 4: 1}


def _find_layout(a):
    H, W = a.shape
    mask = (a != 5)
    for r in range(H):
        if a[r, 0] == 6 and np.all(a[r] == 6):
            mask[r, :] = False
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


def _bcan(a, ox, oy, nx, ny, x, y, fd):
    return (not _is_wall(a, ox, oy, nx, ny, x + fd[0], y + fd[1])) and \
           (not _is_wall(a, ox, oy, nx, ny, x + 2 * fd[0], y + 2 * fd[1]))


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


def _find_boxes_list(a, ox, oy, nx, ny):
    boxes = []
    for y in range(ny):
        for x in range(nx):
            b = _blk(a, ox, oy, x, y)
            vals = set(b.flatten().tolist())
            if 15 not in vals:
                continue
            col = 8 if vals <= {8, 15} else (12 if vals <= {12, 15} else None)
            if col is None:
                continue
            f = np.argwhere(b == 15)
            fd = FACE2DIR.get((int(f[0][0]), int(f[0][1])), (0, 0))
            boxes.append([x, y, fd[0], fd[1], col])
    return boxes


def _corridor(x, y):
    return 0 if (x + y) % 2 == 0 else 2


def init_state(entry):
    a = np.array(entry, dtype=int)
    ox, oy, nx, ny = _find_layout(a)
    boxes = _find_boxes_list(a, ox, oy, nx, ny)
    goal = _find_goal(a, ox, oy, nx, ny)
    player = _find_player(a, ox, oy, nx, ny)
    base = a.copy()
    base[63, :] = 6
    for (bx, by, fx, fy, col) in boxes:
        base[oy + 3 * by:oy + 3 * by + 3, ox + 3 * bx:ox + 3 * bx + 3] = _corridor(bx, by)
    if player is not None:
        px, py = player
        base[oy + 3 * py:oy + 3 * py + 3, ox + 3 * px:ox + 3 * px + 3] = _corridor(px, py)
    return {'ox': ox, 'oy': oy, 'nx': nx, 'ny': ny, 'goal': goal, 'player': player,
            'boxes': [list(b) for b in boxes], 'base': base.tolist()}


def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    ox, oy, nx, ny = state['ox'], state['oy'], state['nx'], state['ny']
    base = np.array(state['base'], dtype=int)
    goal = state.get('goal')
    pos = _find_player(a, ox, oy, nx, ny)
    boxes = [list(b) for b in state.get('boxes', [])]
    ns = dict(state)
    if pos is None or action not in DIRS:
        ns['player'] = pos
        return grid, {'level_up': False, 'win': False, 'dead': False}, ns
    px, py = pos
    dx, dy = DIRS[action]
    dest = (px + 2 * dx, py + 2 * dy)
    hop = _bcan(base, ox, oy, nx, ny, px, py, (dx, dy))
    npos = dest if hop else (px, py)
    if hop:
        face = FACE[action]
    else:
        f = np.argwhere(_blk(a, ox, oy, px, py) == 4)
        face = (int(f[0][0]), int(f[0][1])) if len(f) else (1, 2)

    dead = False
    # color-8 static: kill zone (die) / destroy-on-hop-onto
    destroy = set()
    for i, (bx, by, fx, fy, col) in enumerate(boxes):
        if col == 8:
            if hop and dest == (bx + 2 * fx, by + 2 * fy):
                dead = True
            if hop and dest == (bx, by):
                destroy.add(i)
    # move color-12 patrols (only on hop); build new box list + (old,new) pairs
    newboxes = []
    c12_pairs = []
    for i, (bx, by, fx, fy, col) in enumerate(boxes):
        if i in destroy:
            continue
        if col == 12 and hop:
            fd = (fx, fy)
            if _bcan(base, ox, oy, nx, ny, bx, by, fd):
                nb = (bx + 2 * fd[0], by + 2 * fd[1])
                nfd = fd
            else:
                nfd = (-fd[0], -fd[1])
                nb = (bx + 2 * nfd[0], by + 2 * nfd[1]) if _bcan(base, ox, oy, nx, ny, bx, by, nfd) else (bx, by)
            if not _bcan(base, ox, oy, nx, ny, nb[0], nb[1], nfd):
                nfd = (-nfd[0], -nfd[1])
            newboxes.append([nb[0], nb[1], nfd[0], nfd[1], 12])
            c12_pairs.append(((bx, by), nb))
        else:
            newboxes.append([bx, by, fx, fy, col])
            if col == 12:
                c12_pairs.append(((bx, by), (bx, by)))
    for (old, new) in c12_pairs:
        if new == npos:
            dead = True
        if npos == old and new == (px, py):
            dead = True  # swap

    # HUD
    cur = int(np.sum(a[63, :] == 0))
    try:
        _lvl = CURRENT_LEVEL
    except NameError:
        _lvl = None
    inc = BASE_BY_LEVEL.get(_lvl, max(1, _lvl)) if isinstance(_lvl, int) else 1
    counter = min(cur + inc, 64)

    out = base.copy()
    out[63, :] = 6
    if counter > 0:
        out[63, 64 - counter:64] = 0
    # overlapping boxes: the one whose FACING has highest priority (E>N>W>S) is drawn on top
    _prio = {(1, 0): 3, (0, -1): 2, (-1, 0): 1, (0, 1): 0}
    for (bx, by, fx, fy, col) in sorted(newboxes, key=lambda b: _prio.get((b[2], b[3]), 0)):
        blk = np.full((3, 3), col, dtype=int)
        fp = DIR2FACE.get((fx, fy))
        if fp is not None:
            blk[fp[0], fp[1]] = 15
        out[oy + 3 * by:oy + 3 * by + 3, ox + 3 * bx:ox + 3 * bx + 3] = blk
    cx, cy = npos
    spr = np.full((3, 3), 9, dtype=int)
    spr[face[0], face[1]] = 4
    out[oy + 3 * cy:oy + 3 * cy + 3, ox + 3 * cx:ox + 3 * cx + 3] = spr

    ns['player'] = npos
    ns['boxes'] = newboxes
    win = (goal is not None and npos == tuple(goal) and not dead)
    return out.tolist(), {'level_up': bool(win), 'win': False, 'dead': bool(dead)}, ns


def is_goal(state, grid=None):
    if not isinstance(state, dict):
        return False
    p = state.get('player')
    return p is not None and p == state.get('goal')
