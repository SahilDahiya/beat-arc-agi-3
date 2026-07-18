import numpy as np
import collections

# ============================================================
# Room-hop maze model (ARC3). Non-square grids. Boxes tracked in STATE (a list) because color-12
# patrol boxes can OVERLAP (never merge) and the grid can't represent two boxes in one cell.
#
# Rendering: 64x64. bg=5. row63 = HUD move counter (0s fill from RIGHT). Content = nx*ny logical
#   cells (3x3 px each) at pixel origin (ox,oy). wall=all5; corridor=0 if (x+y)even else 2; goal=14;
#   player sprite = all 9 with one 4 pixel pointing at last-move dir; box = all(color) with one
#   marker pixel giving its facing.
# Movement: room-hop; hop moves player 2 cells iff BOTH door(+dir) and dest(+2dir) are walkable.
# BOX types (each has a marker facing pixel). Box tuple = [x,y,fx,fy,col,active]:
#   color 8  = STATIC. marker 15. Kill zone = room 2 cells in facing dir (hop INTO it = die). Hopping
#              onto the box's own cell (non-facing side) DESTROYS it.
#   color 12 = PATROL. marker 15. On each successful player HOP it advances 1 room in facing dir
#              (door+dest walkable); flips facing when it can't continue. Boxes overlap; die if a box
#              lands on the player, or player/box swap.
#   color 13 = DORMANT SENTRY. marker 15 (asleep) / 11 (active). While asleep it does NOT move; the
#              turn the player enters its facing LINE-OF-SIGHT (rooms straight ahead, walls block) it
#              ACTIVATES (marker 15->11) but does NOT move that turn; once active it PATROLS in its
#              facing dir every hop (same rules as color 12). Contact kills like a patrol.
# HUD increment per move = BASE_BY_LEVEL[level] (majority); occasional +-1 minority moves just halt.
# Boxes+player move in lockstep (box advances only on a hop) -> deterministic per hop-count.
# ============================================================

DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
FACE = {1: (0, 1), 2: (2, 1), 3: (1, 0), 4: (1, 2)}
FACE2DIR = {(1, 0): (-1, 0), (1, 2): (1, 0), (0, 1): (0, -1), (2, 1): (0, 1)}
DIR2FACE = {(-1, 0): (1, 0), (1, 0): (1, 2), (0, -1): (0, 1), (0, 1): (2, 1)}
BASE_BY_LEVEL = {0: 1, 1: 1, 2: 2, 3: 3, 4: 1, 5: 1, 6: 2, 7: 1}


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
            if vals <= {8, 15} and 8 in vals and 15 in vals:
                col, active, mk = 8, True, 15
            elif vals <= {12, 15} and 12 in vals and 15 in vals:
                col, active, mk = 12, True, 15
            elif vals <= {13, 15} and 13 in vals and 15 in vals:
                col, active, mk = 13, False, 15   # dormant sentry
            elif vals <= {13, 11} and 13 in vals and 11 in vals:
                col, active, mk = 13, True, 11    # active sentry
            else:
                continue
            f = np.argwhere(b == mk)
            fd = FACE2DIR.get((int(f[0][0]), int(f[0][1])), (0, 0))
            boxes.append([x, y, fd[0], fd[1], col, active])
    return boxes


def _corridor(x, y):
    return 0 if (x + y) % 2 == 0 else 2


def _patrol_step(base, ox, oy, nx, ny, bx, by, fx, fy):
    """color-12 PATROL hop: advance 1 room in facing dir, REVERSE when blocked."""
    fd = (fx, fy)
    if _bcan(base, ox, oy, nx, ny, bx, by, fd):
        nb = (bx + 2 * fd[0], by + 2 * fd[1]); nfd = fd
    else:
        nfd = (-fd[0], -fd[1])
        nb = (bx + 2 * nfd[0], by + 2 * nfd[1]) if _bcan(base, ox, oy, nx, ny, bx, by, nfd) else (bx, by)
    if not _bcan(base, ox, oy, nx, ny, nb[0], nb[1], nfd):
        nfd = (-nfd[0], -nfd[1])
    return nb, nfd


def _bfs_first(base, ox, oy, nx, ny, sx, sy, px, py):
    """First room-hop direction along the SHORTEST room-path from (sx,sy) to (px,py), or None.
    Explore order S,N,E,W (prefer vertical) -> matches observed sentry tie-breaks."""
    if (sx, sy) == (px, py):
        return None
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    q = collections.deque([(sx, sy)])
    parent = {(sx, sy): None}
    while q:
        cx, cy = q.popleft()
        if (cx, cy) == (px, py):
            break
        for d in dirs:
            if not _bcan(base, ox, oy, nx, ny, cx, cy, d):
                continue
            nxt = (cx + 2 * d[0], cy + 2 * d[1])
            if nxt in parent:
                continue
            parent[nxt] = (cx, cy)
            q.append(nxt)
    if (px, py) not in parent:
        return None
    cur = (px, py)
    while parent[cur] is not None and parent[cur] != (sx, sy):
        cur = parent[cur]
    return ((cur[0] - sx) // 2, (cur[1] - sy) // 2)


def _sentry_step(base, ox, oy, nx, ny, bx, by, px, py, fx, fy):
    """color-13 active SENTRY hop: PATHFINDING chase. Move one room along the shortest room-path
    to the player (px,py); facing = first-step dir along shortest path from the NEW cell to the
    player. Matches all observed active transitions (sentry follows the player around walls)."""
    d = _bfs_first(base, ox, oy, nx, ny, bx, by, px, py)
    nb = (bx + 2 * d[0], by + 2 * d[1]) if d is not None else (bx, by)
    d2 = _bfs_first(base, ox, oy, nx, ny, nb[0], nb[1], px, py)
    nfd = d2 if d2 is not None else (fx, fy)
    return nb, nfd


def _los(base, ox, oy, nx, ny, bx, by, fx, fy, target):
    """True if target room is straight ahead of the box in its facing dir (walls block)."""
    fd = (fx, fy)
    cx, cy = bx, by
    for _ in range(64):
        if not _bcan(base, ox, oy, nx, ny, cx, cy, fd):
            return False
        cx += 2 * fd[0]; cy += 2 * fd[1]
        if (cx, cy) == target:
            return True
    return False


def init_state(entry):
    a = np.array(entry, dtype=int)
    ox, oy, nx, ny = _find_layout(a)
    boxes = _find_boxes_list(a, ox, oy, nx, ny)
    goal = _find_goal(a, ox, oy, nx, ny)
    player = _find_player(a, ox, oy, nx, ny)
    base = a.copy()
    base[63, :] = 6
    for (bx, by, fx, fy, col, act) in boxes:
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
    for i, (bx, by, fx, fy, col, act) in enumerate(boxes):
        if col == 8:
            if hop and dest == (bx + 2 * fx, by + 2 * fy):
                dead = True
            if hop and dest == (bx, by):
                destroy.add(i)
    # move patrols / sentries (only on hop); build new box list + (old,new) contact pairs
    newboxes = []
    move_pairs = []
    for i, (bx, by, fx, fy, col, act) in enumerate(boxes):
        if i in destroy:
            continue
        if col == 12 and hop:
            nb, nfd = _patrol_step(base, ox, oy, nx, ny, bx, by, fx, fy)
            newboxes.append([nb[0], nb[1], nfd[0], nfd[1], 12, True])
            move_pairs.append(((bx, by), nb))
        elif col == 13 and hop and act:
            nb, nfd = _sentry_step(base, ox, oy, nx, ny, bx, by, px, py, fx, fy)
            newboxes.append([nb[0], nb[1], nfd[0], nfd[1], 13, True])
            move_pairs.append(((bx, by), nb))
        elif col == 13 and hop and (not act) and _los(base, ox, oy, nx, ny, bx, by, fx, fy, npos):
            newboxes.append([bx, by, fx, fy, 13, True])  # ACTIVATE this turn, no move yet
        else:
            newboxes.append([bx, by, fx, fy, col, act])
            if col in (12, 13) and act:
                move_pairs.append(((bx, by), (bx, by)))
    for (old, new) in move_pairs:
        if new == npos:
            dead = True
        if npos == old and new == (px, py):
            dead = True  # swap
    # (patrols/sentries pass THROUGH static boxes: they overlap, no destruction.)

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
    # overlapping boxes draw-on-top order: by FACING priority (W>E>N>S), ties broken by color-8 on top.
    _prio = {(-1, 0): 3, (1, 0): 2, (0, -1): 1, (0, 1): 0}
    for (bx, by, fx, fy, col, act) in sorted(newboxes, key=lambda b: (_prio.get((b[2], b[3]), 0), 1 if b[4] == 8 else 0)):
        blk = np.full((3, 3), col, dtype=int)
        fp = DIR2FACE.get((fx, fy))
        if fp is not None:
            blk[fp[0], fp[1]] = 11 if (col == 13 and act) else 15
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
