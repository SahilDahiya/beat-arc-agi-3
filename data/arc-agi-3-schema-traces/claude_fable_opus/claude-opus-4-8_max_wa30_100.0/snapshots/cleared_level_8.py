import numpy as np
from collections import deque

# NOTE: a carrying block BFSes to ANY reachable empty D cell. Tested and REJECTED by backtest:
# "commit to the NEAREST empty D and idle if unreachable" (709->681) and its block-distance variant
# (->675) -- both break levels 1-4. Block2's occasional stall on level 7 remains UNEXPLAINED; do not
# patch it with a special case that regresses earlier levels.
# WARNING: writing this file from run_python does NOT reinstall the live model -- only write_file /
# edit_file recompile and install it.
BG = 1         # (touch to force reinstall)
BODY = 14      # player E body
HEAD = 0       # E head (facing side); also E-carried box border color
B_INNER = 9    # box inner
B_NORMAL = 4   # box border normal
B_HL = 3       # box border when E faces it
B_EGRAB = 0    # box border when E carries it
B_BGRAB = 5    # box border when a CARRIER (color-12 block OR color-15 agent) carries it
BLOCK = 12     # color-12 turtle-block avatar
AGENT = 15     # color-15 ANTAGONIST: steals boxes and hauls them to its own color-2 goal
AGENT_HL = 11  # antagonist recoloured when E is FACING it (E can then kill it with action 5)

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


def _find_blocks(g):
    # ALL color-12 blocks as a list of top-left cell pixel coords (each block is a 4x4 cell).
    # NOTE: row 63 is the move-counter BAR, which is drawn OVER the bottom cell row -- a block in cell
    # row 15 is therefore visible only on rows 60..62. Match on the non-bar part so it is still found.
    g = np.asarray(g)
    H, W = g.shape
    res = []
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            y1 = min(cy + 4, 63)
            if y1 > cy and np.all(g[cy:y1, cx:cx + 4] == BLOCK):
                res.append((cx, cy))
    return res


def _find_agents(g):
    # EVERY color-15 antagonist. A faced agent is drawn as an 11 ring around a 15 inner, so a cell
    # containing ANY 15 is an agent. (Level 7 has two of them; earlier levels had one or none.)
    g = np.asarray(g)
    H, W = g.shape
    res = []
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            if np.any(g[cy:cy + 4, cx:cx + 4] == AGENT):
                res.append((cx, cy))
    return res


def _find_agent(g):
    a = _find_agents(g)
    return a[0] if a else None


_GOAL2_CACHE = {}


def _goal2_cells(entry):
    # The ANTAGONIST'S goal: cells whose static tile is SOLID colour-2 (all 16 px). Distinct from
    # (a) D cells, which are 2-interior but ringed with 9, and (b) level-2/3 STRIPE walls, whose
    # tile MIXES 2s with 1s. Solid-2 cells are PASSABLE FLOOR for E -- only the agent cares about them.
    if entry is None:
        return frozenset()
    return _regions(entry)[1]


_BAR = {                 # level -> (divisor D, off_init, mult): filled = (mult*n + off) // D
    0: (3, 2, 1),        # 1/3
    1: (1, 0, 1),        # 1/1
    2: (3, 1, 2),        # 2/3
    3: (3, 1, 2),        # 2/3
    4: (2, 0, 1),        # 1/2   (was defaulting to 1/1 -> mispredicted EVERY OTHER step)
    5: (7, 0, 6),        # 6/7   (ditto)
    6: (2, 1, 1),        # 1/2 with off=1: observed n=1->1, n=2->1, n=3->2
    7: (7, 3, 3),        # 3/7: bars 0,1,1,2,2,3,3,3 for n=1..8 (NOT 1/2 -- it skips at n=8).
                         # => budget ~149 actions, not 128.
    8: (1, 0, 1),        # ~1/1 with RARE irregular skips (bars 1,2,3,4,5,5,6,7,8,9,10,11,12).
                         # The self-correcting `off` absorbs each skip in one step and pushes the
                         # death point back correctly => effective budget ~68-72, not 64.
}


def _bar_params(level):
    # The move-counter bar advances at a LEVEL-SPECIFIC rational rate with occasional irregular jumps.
    # `off` self-corrects each step (off += actual - predicted), so a jump costs ONE mispredict and then
    # re-syncs -- but the RATE must be right or every other step mispredicts and truncates committed plans.
    return _BAR.get(level, (2, 1, 1))  # unknown level: 1/2-with-offset prior, refined by _fit_bar()


def _fit_bar(obs, level):
    # Learn the bar rate ONLINE for a level we have no constant for. Fit the RAW law
    # filled = (mult*n + off0) // D directly to the (n, filled) pairs actually observed this level
    # -- NOT the self-correcting form, which absorbs any rate error and so cannot identify the rate.
    # Prefer the SLOWEST rate among equally-good fits: over-estimating the rate makes us predict a
    # bar advance that never happens, which mispredicts and truncates the committed plan.
    if level in _BAR or len(obs) < 3:
        return _bar_params(level)
    best = None
    for D in range(1, 13):
        for mult in range(1, D + 1):
            for off0 in range(0, D):
                err = sum(1 for (n, f) in obs if min(64, (mult * n + off0) // D) != f)
                key = (err, mult / D)
                if best is None or key < best[0]:
                    best = (key, D, off0, mult)
    return best[1], best[2], best[3]


def init_state(entry_grid):
    lvl = _cur_level()
    seen = _bar_filled(entry_grid) if entry_grid is not None else 0
    off0 = _bar_params(lvl)[1]
    return {'n': 0, 'off': off0, 'pf': seen, 'obs': [], 'disc': {}}


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
    covered = _covered_cells(e)
    for (cx, cy) in covered:
        col = [(cy2, e[cy2:cy2 + 4, cx:cx + 4]) for cy2 in range(0, H - 3, 4) if (cx, cy2) not in covered]
        tile = None
        # Prefer a pure-BG tile from this column (objects almost always sit on BG). Only when the whole
        # column is non-BG (e.g. level 2's full stripe column) fall back to the nearest uncovered tile.
        for cy2, t in col:
            if np.all(t == BG):
                tile = t
                break
        if tile is None and col:
            col.sort(key=lambda ct: abs(ct[0] - cy))
            tile = col[0][1]
        s[cy:cy + 4, cx:cx + 4] = tile if tile is not None else BG
    # The column heuristic cannot recover a DECORATED cell that was occluded at entry, so redraw the
    # two static regions procedurally from their recovered rectangles: each D rect = 1px ring of 9
    # around a fill of 2; each goal-2 cell = solid 2.
    dcells, goal2 = _regions(e)
    if dcells:
        xs = sorted(set(c[0] for c in dcells)); ys = sorted(set(c[1] for c in dcells))
        for (cx, cy) in dcells:
            s[cy:cy + 4, cx:cx + 4] = 2
        for (cx, cy) in dcells:
            for py in range(cy, cy + 4):
                for px in range(cx, cx + 4):
                    edge = ((px == cx and (cx - 4, cy) not in dcells) or
                            (px == cx + 3 and (cx + 4, cy) not in dcells) or
                            (py == cy and (cx, cy - 4) not in dcells) or
                            (py == cy + 3 and (cx, cy + 4) not in dcells))
                    if edge:
                        s[py, px] = 9
    for (cx, cy) in goal2:
        s[cy:cy + 4, cx:cx + 4] = 2
    return s


def _paint_bar(g, filled):
    for x in range(64):
        g[63][x] = 4 if x >= 64 - filled else 7


def _draw_box(ng, cx, cy, border):
    ng[cy:cy + 4, cx:cx + 4] = border
    ng[cy + 1:cy + 3, cx + 1:cx + 3] = B_INNER


def _render(shape, entry, boxes, e, face, blocks, filled, agents=(), disc=None):
    H, W = shape
    ng = _static_layer(entry) if entry is not None else np.full((H, W), BG, dtype=int)
    # DISCOVERED STATIC BACKGROUND: a cell occluded by an object in the ENTRY frame can never be
    # recovered from ENTRY alone (level 8 hides a solid-2 goal cell under a box). So we record each
    # cell's true tile the first time we see it UNCOVERED, and overlay that here.
    if disc:
        for (cx, cy), tile in disc.items():
            t = np.array(tile, dtype=int)
            ng[cy:cy + t.shape[0], cx:cx + t.shape[1]] = t
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
    for (bx, by) in blocks:
        ng[by:by + 4, bx:bx + 4] = BLOCK
    for (ax, ay) in agents:
        ng[ay:ay + 4, ax:ax + 4] = AGENT
        if (ax, ay) == faced:
            # E-faced agent is drawn like a faced box: a BORDER RING of 11 around a 15 inner 2x2
            # (NOT a solid block of 11).
            ng[ay:ay + 4, ax:ax + 4] = AGENT_HL
            ng[ay + 1:ay + 3, ax + 1:ax + 3] = AGENT
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
_DCELL_CACHE = {}
_REGION_CACHE = {}
_HARD_CACHE = {}


def _hard_walls(entry):
    # SOLID colour-5 walls only. A CARRIED BOX passes through a STRIPE wall (2s mixed with 1s -- this
    # is what makes wall-feeding work on levels 2/3/8) but is BLOCKED by a solid colour-5 wall, just
    # like E's body. Level 8 proves it: E could step to (9,8) but its carried box would have entered
    # the colour-5 wall at (9,7), and the whole move was refused.
    if entry is None:
        return frozenset()
    e = np.asarray(entry)
    key = e.tobytes()
    if key in _HARD_CACHE:
        return _HARD_CACHE[key]
    s = _static_layer(e)
    dcells, goal2 = _regions(e)
    H, W = s.shape
    hard = set()
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            if (cx, cy) in dcells or (cx, cy) in goal2:
                continue
            y1 = min(cy + 4, 63)
            b = s[cy:y1, cx:cx + 4]
            if b.size and np.all(b == 5):
                hard.add((cx, cy))
    r = frozenset(hard)
    _HARD_CACHE[key] = r
    return r


def _covered_cells(e):
    # Cells hidden by a MOVABLE object in the entry frame (their true background must be reconstructed).
    covered = set((b[0], b[1]) for b in _find_boxes(e))
    pe = _find_e(e)
    if pe is not None:
        covered.add(pe)
    for pb in _find_blocks(e):
        covered.add(pb)
    for pa in _find_agents(e):
        covered.add(pa)
    return covered


def _regions(entry):
    # Recover the two STATIC decorated regions as RECTANGLES, so that cells which happen to be hidden
    # by an object in the entry frame are still known (the old "copy a tile from the same column"
    # heuristic silently got these wrong: level 5 has a box parked ON a goal-2 cell at entry).
    #   D rect   -- a big ring of 9s with a 2 fill. Ignore 9s inside covered cells (a box's own 2x2
    #               inner is 9 too); the surviving 9s of a partly-occluded ring still connect, so the
    #               component's bbox recovers the full rect.
    #   GOAL2    -- the antagonist's solid-colour-2 rectangle; take the bbox of the visible solid-2
    #               cells so an occluded corner is included.
    # Returns (dcells, goal2cells) as frozensets of cell top-left pixel coords.
    e = np.asarray(entry)
    key = e.tobytes()
    if key in _REGION_CACHE:
        return _REGION_CACHE[key]
    H, W = e.shape
    covered = _covered_cells(e)

    nine = (e == 9)
    for (cx, cy) in covered:
        nine[cy:cy + 4, cx:cx + 4] = False  # a box's inner 9s are not D
    visited = np.zeros((H, W), dtype=bool)
    dcells = set()
    for sy in range(H):
        for sx in range(W):
            if not nine[sy, sx] or visited[sy, sx]:
                continue
            stack = [(sy, sx)]; visited[sy, sx] = True
            minx = maxx = sx; miny = maxy = sy
            while stack:
                y, x = stack.pop()
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and nine[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True; stack.append((ny, nx))
            if maxx - minx + 1 >= 4 and maxy - miny + 1 >= 4:  # a D ring (a box inner is only 2x2)
                cy = (miny // 4) * 4
                while cy + 4 <= maxy + 1:
                    cx = (minx // 4) * 4
                    while cx + 4 <= maxx + 1:
                        dcells.add((cx, cy)); cx += 4
                    cy += 4

    # Goal-2 regions: solid-colour-2 cells. There can be SEVERAL separate regions (level 7 has two),
    # so take the bbox of each CONNECTED COMPONENT -- a single global bbox would merge them into one
    # huge rectangle and swallow unrelated cells (including real walls).
    vis2 = set((cx, cy) for cy in range(0, H - 3, 4) for cx in range(0, W - 3, 4)
               if (cx, cy) not in covered and (cx, cy) not in dcells
               and np.all(e[cy:cy + 4, cx:cx + 4] == 2))
    goal2 = set()
    seen2 = set()
    for c0 in vis2:
        if c0 in seen2:
            continue
        stack = [c0]; seen2.add(c0); comp = []
        while stack:
            p = stack.pop(); comp.append(p)
            for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
                q = (p[0] + dx, p[1] + dy)
                if q in vis2 and q not in seen2:
                    seen2.add(q); stack.append(q)
        x0 = min(c[0] for c in comp); x1 = max(c[0] for c in comp)
        y0 = min(c[1] for c in comp); y1 = max(c[1] for c in comp)
        for cy in range(y0, y1 + 1, 4):      # bbox fills in cells occluded by a box at entry
            for cx in range(x0, x1 + 1, 4):
                if (cx, cy) not in dcells:
                    goal2.add((cx, cy))
    r = (frozenset(dcells), frozenset(goal2))
    _REGION_CACHE[key] = r
    return r


def _d_cells_all(entry):
    # ALL D cells (works for one big D box OR scattered/multi D regions): a cell is a D cell if its
    # center 2x2 is all 2 AND its 4x4 contains a 9 (the 9 border distinguishes a D interior from the
    # decorative STRIPE, whose 2122/1222 tile also has an all-2 center but no 9). Computed from ENTRY
    # (D cells are fixed by the level; once a box lands on one the rendered grid hides the 2).
    if entry is None:
        return frozenset()
    return _regions(entry)[0]


def _wall_cells(entry):
    # Impassable WALL cells: a static-background cell that is (a) a STRIPE cell (contains a 2 but NO 9,
    # so it's not a D cell) or (b) a solid COLOR-5 cell (level 3 uses color-5 lines/bars as walls too).
    # D cells are excluded. Both E's body and the blocks are blocked from ENTERING a wall, but a CARRIED
    # box passes over walls, and a box sitting on a wall cell is still grabbable from an adjacent cell.
    if entry is None:
        return frozenset()
    e = np.asarray(entry)
    key = e.tobytes()
    if key in _WALL_CACHE:
        return _WALL_CACHE[key]
    s = _static_layer(e)
    dcells = _d_cells_all(e)
    goal2 = _goal2_cells(e)
    H, W = s.shape
    walls = set()
    for cy in range(0, H - 3, 4):
        for cx in range(0, W - 3, 4):
            if (cx, cy) in dcells or (cx, cy) in goal2:
                continue  # D cells and the agent's solid-2 goal cells are PASSABLE floor
            # CELL ROW 15: the BAR is painted over row 63, so the full 4x4 tile is never uniform.
            # Read only the visible part (rows 60..62) or row-15 walls become invisible -- level 8's
            # maze has colour-5 walls there and the model happily routed carriers through them.
            y1 = min(cy + 4, 63)
            b = s[cy:y1, cx:cx + 4]
            if b.size == 0:
                continue
            if np.all(b == 5):
                walls.add((cx, cy))
            elif np.any(b == 2) and not np.any(b == 9):
                walls.add((cx, cy))  # STRIPE wall (2s mixed with 1s)
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
    # UNIFIED WIN (holds for every level 0-5): EVERY BOX sits on a D cell and NO box is being carried.
    # NOT "every D cell is covered": level 5 had 4 D cells but only 2 boxes, and it WON with two D
    # cells still empty. Where D has more cells than boxes (lvl1: 6 cells, 5 boxes) the block parks on
    # the remainder anyway, so this condition still fires exactly on the final release.
    g = np.array(grid)
    dcells = _d_cells_all(_entry())
    if not dcells:
        return False
    boxes = _find_boxes(g)
    if not boxes:
        return False
    if any(b[2] in ('egrab', 'bgrab') for b in boxes):
        return False  # a box is still being carried -> not settled
    return all((b[0], b[1]) in dcells for b in boxes)


def _move_e(g, action, boxes, ex, ey, face, W, H, blocks, agents=()):
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
        for blk in blocks:
            solid.add(blk)  # every color-12 block is solid for E and for a carried box
        for ag in agents:
            solid.add(ag)  # every antagonist's body blocks E too
        walls = _wall_cells(_entry())   # E's BODY is blocked by BOTH stripe and colour-5 walls
        hard = _hard_walls(_entry())    # a CARRIED BOX passes STRIPES but is blocked by colour-5
        ok = True
        for idx, (mx, my) in enumerate(moving):
            nx, ny = mx + ddx, my + ddy
            # CELL ROW 15 IS PLAYABLE: the bar only paints row 63 OVER it, so an object there is
            # simply rendered on rows 60..62. Bound is cy+4 <= 64, NOT cy+3 <= 62.
            if nx < 0 or ny < 0 or nx + 4 > W or ny + 3 > 62:
                ok = False; break
            if idx == 0 and (nx, ny) in walls:  # E body can NEVER enter a wall, even a box-vacated one
                ok = False; break
            if idx == 1 and (nx, ny) in hard:   # CARRIED BOX: passes STRIPES, blocked by colour-5
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


def _block_step(boxes, blocks, bi, dcells, W, H, epos, agents=()):
    # Auto-pathfinder via BFS. Neighbor expansion order LEFT, RIGHT, UP, DOWN (this exact order
    # reproduces ALL 93 recorded level-1 block moves; it is the pathfinder's tie-break among equal
    # shortest paths). Obstacles = E (epos) + normal/egrab boxes (not the carried one) + edges.
    #   - NOT carrying: BFS toward the nearest non-D normal box (chosen by Manhattan, tie-break
    #     y,x); GRAB it (border -> 5) on contact, staying put.
    #   - CARRYING: rigid-pair BFS (block+box move together) to the nearest block cell from which
    #     the carried box sits on an EMPTY D cell (D cell with no normal box); stop there and await
    #     the action-5 drop. E occupying a D cell makes that cell unreachable, so the block reroutes
    #     to another empty D cell -- this is what lets E steer which cell each box lands on.
    block = blocks[bi]
    bx, by = block
    carried = None
    for i, b in enumerate(boxes):
        if b[2] == 'bgrab' and abs(b[0] - bx) + abs(b[1] - by) == 4:
            carried = i  # THIS block's carried box = the bgrab box adjacent to it
            break
    obst = set()
    for i, b in enumerate(boxes):
        if i != carried and b[2] in ('normal', 'egrab', 'bgrab'):
            obst.add((b[0], b[1]))
    obst.add(epos)
    for j, ob in enumerate(blocks):
        if j != bi:
            obst.add(ob)  # other blocks are solid obstacles
    for ag in agents:
        obst.add(ag)  # antagonists are solid obstacles to the blocks too
    obst |= _wall_cells(_entry())  # striped/color-5 walls block the block too
    ORDER = [(-4, 0), (4, 0), (0, -4), (0, 4)]  # L, R, U, D

    def inb(c):
        # NOTE: blocks may LEAVE cell row 15 (lvl3/4 start a block there) but never ENTER it.
        # Allowing them in regresses lvl3/4 badly (648 vs 692) -- evidence, not elegance.
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
        # Pick the nearest box by ACTUAL PATH distance, not Manhattan: obstacles (e.g. boxes already
        # parked on D) can wall off a route so that a Manhattan-nearer box is really farther away.
        # (Level 7: block1 walked AWAY from the Manhattan-nearest box because row 2 was blocked.)
        dist = {block: 0}
        dq = deque([block])
        while dq:
            c = dq.popleft()
            for sx, sy in ORDER:
                nb = (c[0] + sx, c[1] + sy)
                if nb in dist or not inb(nb) or nb in obst:
                    continue
                dist[nb] = dist[c] + 1
                dq.append(nb)

        def _pd(c):
            best = None
            for sx, sy in ORDER:
                nb = (c[0] + sx, c[1] + sy)
                if nb in dist and (best is None or dist[nb] + 1 < best):
                    best = dist[nb] + 1
            return best if best is not None else 10 ** 6
        tgt = min(cand, key=lambda c: (_pd(c), c[1], c[0]))
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
        # A carrying block commits to the NEAREST EMPTY D CELL (Manhattan from the BOX, tie-break y,x)
        # and paths the rigid pair to the single cell Q from which the box lands there. If Q is
        # unreachable it IDLES -- it does NOT fall back to another D cell. (Level 7: block2 froze for
        # many ticks because its nearest empty D was (12,13), whose approach cell (12,12) was occupied
        # by an already-delivered box.)
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


def _agent_step(boxes, agent, blocks, goal2, W, H, epos, ecarry, others=()):
    # The color-15 ANTAGONIST. Same autonomous-carrier shape as the block, but it works AGAINST us:
    #   - target = nearest (Manhattan) NORMAL box that is NOT already parked on one of ITS goal cells
    #     (and not the one E is carrying). It happily steals a box off a D cell.
    #   - walk to it (BFS, L/R/U/D tie-break), then spend ONE tick GRABBING it (border -> 5).
    #   - carry it (offset LOCKED to the grab direction) until the BOX sits on a free goal-2 cell,
    #     then spend ONE tick DROPPING it (border -> normal).
    #   - no target -> idle.
    # Confirmed against every level-5 antagonist frame.
    ax, ay = agent
    carried = None
    for i, b in enumerate(boxes):
        if b[2] == 'bgrab' and abs(b[0] - ax) + abs(b[1] - ay) == 4:
            carried = i
            break
    obst = set()
    for i, b in enumerate(boxes):
        if i != carried and b[2] in ('normal', 'egrab', 'bgrab'):
            obst.add((b[0], b[1]))
    obst.add(epos)
    for blk in blocks:
        obst.add(blk)
    for o in others:
        obst.add(o)  # the other antagonists are solid too
    obst |= _wall_cells(_entry())
    ORDER = [(-4, 0), (4, 0), (0, -4), (0, 4)]

    def inb(c):
        return 0 <= c[0] and c[0] + 4 <= W and 0 <= c[1] and c[1] + 4 <= H  # cell row 15 IS playable

    def first_step(par, goal):
        cur = goal
        while par[cur] is not None and par[cur] != agent:
            cur = par[cur]
        return cur if par[cur] == agent else None

    if carried is None:
        cand = [(b[0], b[1]) for b in boxes
                if b[2] == 'normal' and (b[0], b[1]) not in goal2]
        if not cand:
            return agent
        # nearest by ACTUAL PATH distance, not Manhattan (see _block_step) -- obstacles can make a
        # Manhattan-nearer box genuinely farther away.
        adist = {agent: 0}
        adq = deque([agent])
        while adq:
            c0 = adq.popleft()
            for sx, sy in ORDER:
                nb = (c0[0] + sx, c0[1] + sy)
                if nb in adist or not inb(nb) or nb in obst:
                    continue
                adist[nb] = adist[c0] + 1
                adq.append(nb)

        def _apd(c):
            best = None
            for sx, sy in ORDER:
                nb = (c[0] + sx, c[1] + sy)
                if nb in adist and (best is None or adist[nb] + 1 < best):
                    best = adist[nb] + 1
            return best if best is not None else 10 ** 6
        tgt = min(cand, key=lambda c: (_apd(c), c[1], c[0]))
        if abs(tgt[0] - ax) + abs(tgt[1] - ay) == 4:  # adjacent -> GRAB (costs a tick, no move)
            for b in boxes:
                if (b[0], b[1]) == tgt and b[2] == 'normal':
                    b[2] = 'bgrab'
                    break
            return agent
        q = deque([agent]); par = {agent: None}; goal = None
        while q:
            c = q.popleft()
            for sx, sy in ORDER:
                nb = (c[0] + sx, c[1] + sy)
                if nb in par or not inb(nb):
                    continue
                if nb == tgt:
                    par[nb] = c; goal = nb; q.clear(); break
                if nb in obst:
                    continue
                par[nb] = c; q.append(nb)
            if goal is not None:
                break
        if goal is None:
            return agent
        step = first_step(par, goal)
        return step if (step is not None and step != tgt) else agent
    else:
        cb = boxes[carried]
        offset = (cb[0] - ax, cb[1] - ay)
        occ = set((b[0], b[1]) for i, b in enumerate(boxes) if i != carried and b[2] == 'normal')
        free = set(c for c in goal2 if c not in occ)
        if (cb[0], cb[1]) in free:
            cb[2] = 'normal'  # box is on a goal cell -> DROP it (one tick, no move)
            return agent
        q = deque([agent]); par = {agent: None}; goal = None
        while q:
            c = q.popleft()
            if (c[0] + offset[0], c[1] + offset[1]) in free:
                goal = c; break
            for sx, sy in ORDER:
                nb = (c[0] + sx, c[1] + sy); ncb = (nb[0] + offset[0], nb[1] + offset[1])
                if nb in par or not (inb(nb) and inb(ncb)):
                    continue
                if nb in obst or ncb in obst:
                    continue
                par[nb] = c; q.append(nb)
        if goal is None:
            return agent
        step = first_step(par, goal)
        if step is None or step == agent:
            return agent
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
    obs = list(state.get('obs', []))
    obs.append((n, cur))
    if len(obs) > 80:
        obs = obs[-80:]

    # --- learn the true static background of every cell that is currently UNCOVERED.
    disc = dict(state.get('disc', {}))
    _cov = set((b[0], b[1]) for b in _find_boxes(g))
    _pe = _find_e(g)
    if _pe is not None:
        _cov.add(_pe)
    for _c in _find_blocks(g):
        _cov.add(_c)
    for _c in _find_agents(g):
        _cov.add(_c)
    for cy0 in range(0, H - 3, 4):
        for cx0 in range(0, W - 3, 4):
            if (cx0, cy0) in _cov or (cx0, cy0) in disc:
                continue
            y1 = min(cy0 + 4, 63)  # never record the BAR row
            disc[(cx0, cy0)] = tuple(tuple(int(v) for v in row)
                                     for row in g[cy0:y1, cx0:cx0 + 4])

    lvl = _cur_level()
    e = _find_e(g)
    if e is None or action not in (1, 2, 3, 4, 5):
        return g.tolist(), {}, {'n': n, 'off': off, 'pf': cur, 'obs': obs, 'disc': disc}

    ex, ey = e
    face = _e_facing(g, ex, ey)
    boxes = _find_boxes(g)
    blocks = _find_blocks(g)
    dcells0 = _d_cells_all(_entry())
    agents = _find_agents(g)
    goal2 = set(_goal2_cells(_entry()))
    for (cx0, cy0), tile in disc.items():          # solid-2 cells revealed after a box moved off
        if (cx0, cy0) in dcells0:
            continue
        arr = np.array(tile)
        if arr.size and np.all(arr == 2):
            goal2.add((cx0, cy0))
    goal2 = frozenset(goal2)

    # --- ANTAGONIST KILL: action 5 while E is EMPTY-HANDED and FACING an agent removes THAT agent.
    # (If E is carrying, action 5 RELEASES the box instead -- so E can never kill mid-carry.)
    # The kill CONSUMES E's action but the world still TICKS: blocks keep moving and any OTHER agent
    # keeps acting. (Returning early here made the whole board freeze for one tick.)
    killed = False
    if action == 5 and agents:
        fdx, fdy = FACE_D[face]
        tgt = (ex + fdx, ey + fdy)
        if tgt in agents and not any(b[2] == 'egrab' for b in boxes):
            # A DYING AGENT DROPS ITS BOX. Without this the box stays flagged 'bgrab' forever with
            # no carrier -- an orphan that can never be delivered, so is_goal can never fire.
            # Only release a carried box that no BLOCK is holding (blocks use the same 'bgrab' flag).
            for b in boxes:
                if b[2] == 'bgrab' and abs(b[0] - tgt[0]) + abs(b[1] - tgt[1]) == 4:
                    if not any(abs(b[0] - bl[0]) + abs(b[1] - bl[1]) == 4 for bl in blocks):
                        b[2] = 'normal'
            agents = [a for a in agents if a != tgt]
            killed = True

    if action == 5:
        fdx, fdy = FACE_D[face]
        fcx, fcy = ex + fdx, ey + fdy
        # a block DROPS its carried box (border 5 -> normal) IF it's on a D cell (deposit) OR E is
        # facing it (handoff to E); otherwise it keeps carrying.
        bcarry_before = any(b[2] == 'bgrab' for b in boxes)  # any block carrying BEFORE the drop
        just_dropped = set()  # blocks that DELIVER on this action must NOT also step this tick
        for b in boxes:
            if b[2] == 'bgrab' and ((b[0], b[1]) in dcells0 or (b[0], b[1]) == (fcx, fcy)):
                b[2] = 'normal'
                for bi, bl in enumerate(blocks):
                    if abs(b[0] - bl[0]) + abs(b[1] - bl[1]) == 4:
                        just_dropped.add(bi)
        egrab_before = any(b[2] == 'egrab' for b in boxes)
        # (2) E toggle (grab the faced normal box / release E's own box). SKIPPED when this action was
        #     spent KILLING an agent -- E cannot also grab on the same tick.
        if not killed:
            ex, ey, face = _move_e(g, action, boxes, ex, ey, face, W, H, blocks, agents)
        egrab_after = any(b[2] == 'egrab' for b in boxes)
        # (3) blocks step iff a block is STILL carrying after the drop, OR none was carrying before and
        #     E's carry-state changed (E grabbed/released -> blocks re-target). A block that just
        #     DELIVERED (carrying before, not after) STAYS PUT on the drop action.
        # Blocks tick on EVERY action, including action 5 -- the only exception is a block that just
        # DELIVERED, which stays put on the drop tick. (The old "only step if a block is carrying or
        # E's carry-state changed" condition was a level-1 hack; it silently froze both blocks on
        # level 7 whenever E pressed 5 with nothing in front of it.)
        for bi in range(len(blocks)):
            if bi in just_dropped:
                continue
            blocks[bi] = _block_step(boxes, blocks, bi, dcells0, W, H, (ex, ey), agents)
    else:
        ex, ey, face = _move_e(g, action, boxes, ex, ey, face, W, H, blocks, agents)
        if action in CDIR:
            for bi in range(len(blocks)):
                blocks[bi] = _block_step(boxes, blocks, bi, dcells0, W, H, (ex, ey), agents)

    # every antagonist ticks ONCE per E action (whatever the action was)
    ecarry = any(b[2] == 'egrab' for b in boxes)
    for ai in range(len(agents)):
        others = [a for j, a in enumerate(agents) if j != ai]
        agents[ai] = _agent_step(boxes, agents[ai], blocks, goal2, W, H, (ex, ey), ecarry, others)

    n2 = n + 1
    D, _, mult = _fit_bar(obs, lvl)
    next_filled = min(64, (mult * n2 + off) // D)
    nstate = {'n': n2, 'off': off, 'pf': next_filled, 'obs': obs, 'disc': disc}

    ng = _render((H, W), _entry(), boxes, (ex, ey), face, blocks, next_filled, agents, disc)
    info = {}
    try:
        if is_goal(ng):
            info['level_up'] = True
    except Exception:
        pass
    if next_filled >= 64:
        info['dead'] = True  # the move-counter bar filling to 64 => GAME OVER (hard move limit)
    return ng.tolist(), info, nstate
