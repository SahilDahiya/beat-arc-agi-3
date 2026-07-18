import numpy as np
from collections import deque

BG = 1
BODY = 14      # player E body
HEAD = 0       # E head (facing side); also E-carried box border color
B_INNER = 9    # box inner
B_NORMAL = 4   # box border normal
B_HL = 3       # box border when E faces it
B_EGRAB = 0    # box border when E carries it
B_BGRAB = 5    # box border when the color-12 block carries it
BLOCK = 12     # color-12 turtle-block avatar

CDIR = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
FACE_NAME = {1: 'up', 2: 'down', 3: 'left', 4: 'right'}
FACE_D = {'up': (0, -4), 'down': (0, 4), 'left': (-4, 0), 'right': (4, 0)}


def _entry():
    try:
        e = ENTRY_GRID
    except NameError:
        return None
    return np.array(e) if e is not None else None


def _cur_level():
    try:
        return CURRENT_LEVEL
    except NameError:
        return None


def _bar_filled(g):
    return int((np.asarray(g)[63] == 4).sum())


def _find_block(g):
    ys, xs = np.where(g == BLOCK)
    if len(xs) == 0:
        return None
    return (int(xs.min()) // 4) * 4, (int(ys.min()) // 4) * 4


def _bar_params(level):
    # (divisor, off_init). filled = floor((moves + off) / divisor); off self-corrects skips each step.
    # off_init compensates the framework hiding the GLOBAL first action (only affects level 0's opening).
    # divisor = moves-per-pixel, level-specific (lvl0: 3, lvl1: 1). Unknown levels default to 1 (re-observe & self-correct).
    # (divisor, off_init, mult): fill = floor((mult*n + off) / divisor). off self-corrects skips.
    if level == 0:
        return 3, 2, 1
    if level == 2:
        return 3, 1, 2  # lvl2: fill~floor((2n+1)/3) (rate 2/3, irregular skips); off self-corrects
    return 1, 0, 1  # lvl1: +1/move with occasional skips (self-corrected). Bar hits 64 => death.


def init_state(entry_grid):
    lvl = _cur_level()
    seen = _bar_filled(entry_grid) if entry_grid is not None else 0
    off0 = _bar_params(lvl)[1]
    return {'n': 0, 'off': off0, 'pf': seen}


def _find_e(g):
    ys, xs = np.where(g == BODY)
    if len(xs) == 0:
        return None
    return (int(xs.min()) // 4) * 4, (int(ys.min()) // 4) * 4


def _e_facing(g, ex, ey):
    b = g[ey:ey + 4, ex:ex + 4]
    if np.all(b[0, :] == HEAD): return 'up'
    if np.all(b[3, :] == HEAD): return 'down'
    if np.all(b[:, 0] == HEAD): return 'left'
    if np.all(b[:, 3] == HEAD): return 'right'
    return 'up'


def _box_type(g, cx, cy):
    H, W = g.shape
    if cx < 0 or cy < 0 or cx + 4 > W or cy + 4 > H:
        return None
    b = g[cy:cy + 4, cx:cx + 4]
    if not np.all(b[1:3, 1:3] == B_INNER):
        return None
    ring = set(int(v) for v in np.concatenate([b[0, :], b[3, :], b[1:3, 0], b[1:3, 3]]))
    if ring == {B_EGRAB}:
        return 'egrab'
    if ring == {B_BGRAB}:
        return 'bgrab'
    if ring <= {B_NORMAL, B_HL}:
        return 'normal'
    return None


def _find_boxes(g):
    H, W = g.shape
    boxes = []
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            t = _box_type(g, cx, cy)
            if t is not None:
                boxes.append([cx, cy, t])
    return boxes


def _static_layer(entry):
    # Background = entry with the MOVABLE objects (boxes, E, block) removed. Their background is not
    # always plain BG: level 2 has a vertical decorative STRIPE column, and boxes sit ON it. Restore
    # each removed cell's true background by copying the 4x4 tile from a CLEAN (uncovered) cell in the
    # SAME COLUMN (backgrounds are column-uniform: BG, or the repeating stripe tile, or D pattern).
    e = np.array(entry)
    s = e.copy()
    H, W = e.shape
    covered = set((b[0], b[1]) for b in _find_boxes(e))
    pe = _find_e(e)
    if pe is not None:
        covered.add(pe)
    pb = _find_block(e)
    if pb is not None:
        covered.add(pb)
    for (cx, cy) in covered:
        tile = None
        for cy2 in range(0, H - 3, 4):
            if (cx, cy2) not in covered:
                tile = e[cy2:cy2 + 4, cx:cx + 4]
                break
        s[cy:cy + 4, cx:cx + 4] = tile if tile is not None else BG
    return s


def _paint_bar(g, filled):
    for x in range(64):
        g[63][x] = 4 if x >= 64 - filled else 7


def _draw_box(ng, cx, cy, border):
    ng[cy:cy + 4, cx:cx + 4] = border
    ng[cy + 1:cy + 3, cx + 1:cx + 3] = B_INNER


def _render(shape, entry, boxes, e, face, block, filled):
    H, W = shape
    ng = _static_layer(entry) if entry is not None else np.full((H, W), BG, dtype=int)
    ex, ey = e
    fdx, fdy = FACE_D[face]
    faced = (ex + fdx, ey + fdy)
    for (cx, cy, t) in boxes:
        if t == 'egrab':
            border = B_EGRAB
        elif (cx, cy) == faced:
            border = B_HL  # E-facing highlight overrides block-carry(5)/normal(4)
        elif t == 'bgrab':
            border = B_BGRAB
        else:
            border = B_NORMAL
        _draw_box(ng, cx, cy, border)
    if block is not None:
        bx, by = block
        ng[by:by + 4, bx:bx + 4] = BLOCK
    ng[ey:ey + 4, ex:ex + 4] = BODY
    if face == 'up':
        ng[ey, ex:ex + 4] = HEAD
    elif face == 'down':
        ng[ey + 3, ex:ex + 4] = HEAD
    elif face == 'left':
        ng[ey:ey + 4, ex] = HEAD
    elif face == 'right':
        ng[ey:ey + 4, ex + 3] = HEAD
    _paint_bar(ng, filled)
    return ng


def _d_region(entry):
    # D is the big box: a large rectangular RING of border-9. Detect it as the bbox of the LARGEST
    # connected component of 9s. (Old code used 2s min/max, but level 2 has a decorative STRIPE of
    # 2s elsewhere -> mis-detected D. Box inners are tiny 2x2 9-components, so D's border ring wins.)
    if entry is None:
        return None
    e = np.asarray(entry)
    nine = (e == 9)
    if not nine.any():
        return None
    H, W = e.shape
    visited = np.zeros((H, W), dtype=bool)
    best = None
    best_size = 0
    for sy in range(H):
        for sx in range(W):
            if nine[sy, sx] and not visited[sy, sx]:
                stack = [(sy, sx)]
                visited[sy, sx] = True
                minx = maxx = sx
                miny = maxy = sy
                size = 0
                while stack:
                    y, x = stack.pop()
                    size += 1
                    if x < minx: minx = x
                    if x > maxx: maxx = x
                    if y < miny: miny = y
                    if y > maxy: maxy = y
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and nine[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
                if size > best_size:
                    best_size = size
                    best = (minx, miny, maxx, maxy)
    return best


def _d_cells(dreg):
    if dreg is None:
        return set()
    x0, y0, x1, y1 = dreg
    cells = set()
    cy = y0
    while cy + 4 <= y1 + 1:
        cx = x0
        while cx + 4 <= x1 + 1:
            cells.add((cx, cy))
            cx += 4
        cy += 4
    return cells


_WALL_CACHE = {}


def _wall_cells(entry):
    # Impassable WALL cells (level 2's striped column): cells whose STATIC background contains a 2
    # but are OUTSIDE the D box. Both E and the block are blocked from ENTERING them (a target box
    # sitting on a wall cell is still grabbable from an adjacent non-wall cell). Empty on lvl0/1.
    if entry is None:
        return frozenset()
    e = np.asarray(entry)
    key = e.tobytes()
    if key in _WALL_CACHE:
        return _WALL_CACHE[key]
    s = _static_layer(e)
    dreg = _d_region(e)
    H, W = s.shape
    walls = set()
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            if np.any(s[cy:cy + 4, cx:cx + 4] == 2):
                if dreg is not None and dreg[0] <= cx <= dreg[2] and dreg[1] <= cy <= dreg[3]:
                    continue
                walls.add((cx, cy))
    r = frozenset(walls)
    _WALL_CACHE[key] = r
    return r


def is_goal(grid):
    # WIN = the big box D is FULLY COVERED: every D interior cell (value 2) is hidden by a
    # box OR by the color-12 block. D has more cells than boxes (lvl1: 6 cells, 5 boxes),
    # so the BLOCK must cover the last cell (it can't leave after its final delivery).
    # Detect via: no value-2 cell remains inside D's bounding box in the rendered grid.
    # Level 0: 3 boxes fill 3 D cells (no block) -> same "no 2s left" condition.
    # Covered = only RELEASED (normal, border 4/3) boxes or the block (12) count. A cell that is
    # empty (2), under an E-carried box (egrab border 0) or block-carried box (bgrab border 5),
    # or under E's body (14) does NOT count -> win fires only after the final RELEASE (action 5).
    g = np.array(grid)
    dreg = _d_region(_entry())
    if dreg is None:
        return False
    x0, y0, x1, y1 = dreg
    sub = g[y0:y1 + 1, x0:x1 + 1]
    return not bool(np.any(np.isin(sub, [2, B_EGRAB, B_BGRAB, BODY])))


def _move_e(g, action, boxes, ex, ey, face, W, H, block):
    carried = None
    for i, b in enumerate(boxes):
        if b[2] == 'egrab':
            carried = i
            break
    if action in CDIR:
        dcx, dcy = CDIR[action]
        ddx, ddy = dcx * 4, dcy * 4
        moving = [(ex, ey)]
        if carried is not None:
            moving.append((boxes[carried][0], boxes[carried][1]))
        cur = set(moving)
        solid = set((b[0], b[1]) for i, b in enumerate(boxes) if i != carried)
        if block is not None:
            solid.add(block)  # the color-12 block is solid for E and for a carried box
        walls = _wall_cells(_entry())  # striped column blocks E's BODY; a CARRIED box passes OVER it
        ok = True
        for idx, (mx, my) in enumerate(moving):
            nx, ny = mx + ddx, my + ddy
            if nx < 0 or ny < 0 or nx + 4 > W or ny + 3 > 62:
                ok = False; break
            if idx == 0 and (nx, ny) in walls:  # E body can NEVER enter a wall, even a box-vacated one
                ok = False; break
            if (nx, ny) in cur:
                continue
            if (nx, ny) in solid:
                ok = False; break
        if ok:
            ex, ey = ex + ddx, ey + ddy
            if carried is not None:
                boxes[carried][0] += ddx; boxes[carried][1] += ddy
        if carried is None:
            face = FACE_NAME[action]  # E turns to the action dir even when blocked (not carrying)
    else:  # action 5: toggle faced box
        fdx, fdy = FACE_D[face]
        fcx, fcy = ex + fdx, ey + fdy
        if carried is not None:
            boxes[carried][2] = 'normal'
        else:
            for b in boxes:
                if (b[0], b[1]) == (fcx, fcy) and b[2] == 'normal':
                    b[2] = 'egrab'
                    break
    return ex, ey, face


def _block_step(boxes, block, dcells, W, H, epos):
    # Auto-pathfinder via BFS. Neighbor expansion order LEFT, RIGHT, UP, DOWN (this exact order
    # reproduces ALL 93 recorded level-1 block moves; it is the pathfinder's tie-break among equal
    # shortest paths). Obstacles = E (epos) + normal/egrab boxes (not the carried one) + edges.
    #   - NOT carrying: BFS toward the nearest non-D normal box (chosen by Manhattan, tie-break
    #     y,x); GRAB it (border -> 5) on contact, staying put.
    #   - CARRYING: rigid-pair BFS (block+box move together) to the nearest block cell from which
    #     the carried box sits on an EMPTY D cell (D cell with no normal box); stop there and await
    #     the action-5 drop. E occupying a D cell makes that cell unreachable, so the block reroutes
    #     to another empty D cell -- this is what lets E steer which cell each box lands on.
    bx, by = block
    carried = None
    for i, b in enumerate(boxes):
        if b[2] == 'bgrab':
            carried = i
            break
    obst = set()
    for i, b in enumerate(boxes):
        if i != carried and b[2] in ('normal', 'egrab'):
            obst.add((b[0], b[1]))
    obst.add(epos)
    obst |= _wall_cells(_entry())  # striped column blocks the block too
    ORDER = [(-4, 0), (4, 0), (0, -4), (0, 4)]  # L, R, U, D

    def inb(c):
        return 0 <= c[0] and c[0] + 4 <= W and 0 <= c[1] and c[1] + 3 <= 62

    def first_step(par, goal):
        cur = goal
        while par[cur] is not None and par[cur] != block:
            cur = par[cur]
        return cur if par[cur] == block else None

    if carried is None:
        cand = [(b[0], b[1]) for b in boxes if b[2] == 'normal' and (b[0], b[1]) not in dcells]
        if not cand:
            return block
        tgt = min(cand, key=lambda c: (abs(c[0] - bx) + abs(c[1] - by), c[1], c[0]))
        q = deque([block]); par = {block: None}; goal = None
        while q:
            b = q.popleft()
            for sx, sy in ORDER:
                nb = (b[0] + sx, b[1] + sy)
                if nb in par:
                    continue
                if not inb(nb):
                    continue
                if nb == tgt:
                    par[nb] = b; goal = nb; q.clear(); break
                if nb in obst:
                    continue
                par[nb] = b; q.append(nb)
            if goal is not None:
                break
        if goal is None:
            return block
        step = first_step(par, goal)
        if step == tgt:
            for b in boxes:
                if (b[0], b[1]) == tgt and b[2] == 'normal':
                    b[2] = 'bgrab'
                    break
            return block
        return step if step is not None else block
    else:
        cb = boxes[carried]
        offset = (cb[0] - bx, cb[1] - by)
        occ = set((b[0], b[1]) for b in boxes if b[2] == 'normal')
        empty = set(c for c in dcells if c not in occ)
        if (cb[0], cb[1]) in empty:
            cb[2] = 'normal'  # AUTO-DELIVER: once the carried box is on an empty D cell, the block
            return block      # DROPS it (bgrab->normal) on the next step -- no action-5 required.
        q = deque([block]); par = {block: None}; goal = None
        while q:
            b = q.popleft()
            boxc = (b[0] + offset[0], b[1] + offset[1])
            if boxc in empty:
                goal = b; break
            for sx, sy in ORDER:
                nb = (b[0] + sx, b[1] + sy); ncb = (nb[0] + offset[0], nb[1] + offset[1])
                if nb in par:
                    continue
                if not (inb(nb) and inb(ncb)):
                    continue
                if nb in obst or ncb in obst:
                    continue
                par[nb] = b; q.append(nb)
        if goal is None:
            return block
        step = first_step(par, goal)
        if step is None or step == block:
            return block
        cb[0] = step[0] + offset[0]; cb[1] = step[1] + offset[1]
        return step


def predict(state, grid, action, x=None, y=None):
    g = np.array(grid)
    H, W = g.shape
    cur = _bar_filled(g)
    n = state.get('n', 0)
    off = state.get('off', 2)
    pf = state.get('pf', cur)
    off += (cur - pf)

    e = _find_e(g)
    if e is None or action not in (1, 2, 3, 4, 5):
        return g.tolist(), {}, {'n': n, 'off': off, 'pf': cur}

    ex, ey = e
    face = _e_facing(g, ex, ey)
    boxes = _find_boxes(g)
    block = _find_block(g)

    if action == 5:
        dcells0 = _d_cells(_d_region(_entry()))
        fdx, fdy = FACE_D[face]
        fcx, fcy = ex + fdx, ey + fdy
        # block DROPS its carried box (border 5 -> normal) ONLY IF it's on a D cell (deposit)
        # OR E is facing it (so E can then steal it); otherwise the block keeps carrying.
        bcarry_before = any(b[2] == 'bgrab' for b in boxes)  # block carrying BEFORE the drop
        for b in boxes:
            if b[2] == 'bgrab' and ((b[0], b[1]) in dcells0 or (b[0], b[1]) == (fcx, fcy)):
                b[2] = 'normal'
        egrab_before = any(b[2] == 'egrab' for b in boxes)
        # (2) E toggle (grab the faced normal box / release E's own box)
        ex, ey, face = _move_e(g, action, boxes, ex, ey, face, W, H, block)
        egrab_after = any(b[2] == 'egrab' for b in boxes)
        # (3) block steps iff it is STILL carrying after the drop, OR it was NOT carrying before and
        #     E's carry-state changed this action (E grabbed/released a box -> block re-targets).
        #     A block that just DELIVERED (carrying before, not after) STAYS PUT on the drop action,
        #     even if E simultaneously grabbed another box (validated on all 7 action-5 frames).
        still_carrying = any(b[2] == 'bgrab' for b in boxes)
        if block is not None and (still_carrying or ((not bcarry_before) and egrab_after != egrab_before)):
            block = _block_step(boxes, block, dcells0, W, H, (ex, ey))
    else:
        ex, ey, face = _move_e(g, action, boxes, ex, ey, face, W, H, block)
        if block is not None and action in CDIR:
            block = _block_step(boxes, block, _d_cells(_d_region(_entry())), W, H, (ex, ey))

    n2 = n + 1
    D, _, mult = _bar_params(_cur_level())
    next_filled = min(64, (mult * n2 + off) // D)
    nstate = {'n': n2, 'off': off, 'pf': next_filled}

    ng = _render((H, W), _entry(), boxes, (ex, ey), face, block, next_filled)
    info = {}
    try:
        if is_goal(ng):
            info['level_up'] = True
    except Exception:
        pass
    if next_filled >= 64:
        info['dead'] = True  # the move-counter bar filling to 64 => GAME OVER (hard move limit)
    return ng.tolist(), info, nstate
