# su15 world model
# Mechanic (L0): a 3x3 white (f=15) block in the play area (rows 10..62, bg=5)
# teleports its CENTER to a clicked cell if Chebyshev distance from current
# center <= 6. Landing restores what was under the old position (static
# underlay from ENTRY_GRID; the 0-plus marker is consumed on first landing,
# revealing a trail dot at its center). Each play-area click (y>=10) costs 2
# budget cells (rightmost 0s of row 63 -> 5). Clicks in top band (y<=9) are
# free no-ops. Action 7: no-op.
# GOAL HYPOTHESIS: land block exactly on the 3x3 core of 3s inside the 9-disk.

def _find_block(g):
    # 3x3 block of 15s with top-left minimal; search play area rows 10..62
    for y in range(10, 61):
        for x in range(0, 62):
            if g[y][x] == 15 and g[y][x+1] == 15 and g[y][x+2] == 15 \
               and g[y+1][x] == 15 and g[y+2][x] == 15:
                return (x+1, y+1)  # center
    return None

def _entry_features():
    eg = ENTRY_GRID
    feats = {}
    # block at entry
    bc = _find_block(eg)
    feats['entry_block'] = bc
    # plus marker: 0-colored cells in play area (rows 10..62)
    plus = [(x, y) for y in range(10, 63) for x in range(64) if eg[y][x] == 0]
    feats['plus_cells'] = plus
    if plus:
        xs = sorted(set(x for x, y in plus))
        ys = sorted(set(y for x, y in plus))
        feats['plus_center'] = (xs[len(xs)//2], ys[len(ys)//2])
    else:
        feats['plus_center'] = None
    # ball core: 3x3 of 3s fully surrounded by 9s (inside disk)
    core = None
    for y in range(10, 61):
        for x in range(0, 62):
            if all(eg[y+dy][x+dx] == 3 for dy in range(3) for dx in range(3)):
                # check ring of 9s around (at least corners)
                if y-1 >= 0 and eg[y-1][x] == 9 and eg[y+3][x] == 9:
                    core = (x+1, y+1)
    feats['core'] = core
    return feats

def _underlay(x, y):
    """What lies beneath position (x,y) once the block/plus are gone."""
    eg = ENTRY_GRID
    f = _entry_features()
    bx, by = f['entry_block'] if f['entry_block'] else (-99, -99)
    if abs(x - bx) <= 1 and abs(y - by) <= 1:
        return 5  # under entry block: plain bg
    if (x, y) in f['plus_cells']:
        return 3 if (x, y) == f['plus_center'] else 5
    return eg[y][x]

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6:
        return g, info
    if y is not None and y <= 9:
        return g, info  # top band: free no-op
    # pay budget: two rightmost 0-cells of row 63
    paid = 0
    for bx in range(63, -1, -1):
        if paid >= 2:
            break
        if g[63][bx] == 0:
            g[63][bx] = 5
            paid += 1
    bc = _find_block(g)
    if bc is None:
        return g, info
    cx, cy = bc
    if max(abs(x - cx), abs(y - cy)) <= 6 and (x, y) != (cx, cy):
        # fits inside play area?
        if 1 <= x <= 62 and 11 <= y <= 61:
            # move: clear old, stamp new
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    g[cy+dy][cx+dx] = _underlay(cx+dx, cy+dy)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    g[y+dy][x+dx] = 15
            core = _entry_features()['core']
            if core is not None and (x, y) == core:
                info["level_up"] = True
    return g, info

def is_goal(grid):
    bc = _find_block(grid)
    core = _entry_features()['core']
    return bc is not None and core is not None and bc == core
