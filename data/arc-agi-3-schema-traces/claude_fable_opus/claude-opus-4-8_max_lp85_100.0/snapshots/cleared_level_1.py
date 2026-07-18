import numpy as np

# ============================================================
# LEVEL 0 : single 20-cell CLOCKWISE conveyor loop, each cell 4x4.
# ============================================================
L0_LOOP = [
    (19,12),(19,18),(19,24),(19,30),(19,36),(19,42),(19,48),  # ROW A L->R (0..6)
    (25,48),(31,48),(37,48),                                   # RIGHT col top->bot (7..9)
    (43,48),(43,42),(43,36),(43,30),(43,24),(43,18),(43,12),   # ROW B R->L (10..16)
    (37,12),(31,12),(25,12),                                   # LEFT col bot->top (17..19)
]
L0_RIGHT_BOX = (29,36,56,61)   # e-shape -> CW
L0_LEFT_BOX  = (29,36, 2, 7)   # 8-shape -> CCW
L0_BUDGET = 13

def _in_box(box, x, y):
    if x is None or y is None:
        return False
    y0,y1,x0,x1 = box
    return y0 <= y <= y1 and x0 <= x <= x1

def _set_cell(g, cy, cx, col, sz=4):
    for dy in range(sz):
        for dx in range(sz):
            g[cy+dy][cx+dx] = col

def _counter_advance(g, grid, H, budget):
    # col0 move-budget bar: fill height = round(H*clicks/budget). Invert then +1.
    c = 0
    for yy in range(H):
        if grid[yy][0] == 5:
            c += 1
        else:
            break
    k = int(round(budget * c / float(H)))
    newc = int(round(H * (k+1) / float(budget)))
    if newc > H:
        newc = H
    for yy in range(newc):
        g[yy][0] = 5

def _level0_step(grid, action, x, y):
    H = len(grid)
    g = [list(row) for row in grid]
    if action != 6:
        return g, False
    cols = [grid[cy][cx] for (cy, cx) in L0_LOOP]
    n = len(cols)
    if _in_box(L0_RIGHT_BOX, x, y):
        newcols = [cols[(i-1) % n] for i in range(n)]      # CW
    elif _in_box(L0_LEFT_BOX, x, y):
        newcols = [cols[(i+1) % n] for i in range(n)]      # CCW
    else:
        return g, False
    for (cy, cx), col in zip(L0_LOOP, newcols):
        _set_cell(g, cy, cx, col)
    _counter_advance(g, grid, H, L0_BUDGET)
    return g, True

def _level0_is_goal(grid):
    # unique b(11) tile aligned into bracketed slot idx0 (top-left pixel (19,12))
    return grid[19][12] == 11

# ============================================================
# LEVEL 1 : interlocking loops. RING(26) + CROSS3(10 @ r3) + CROSS6(10 @ r6).
# Lattice cell (r,c) -> 2x2 block top-left px (17+3r, 17+3c). Shared cells belong to
# multiple loops; rotate = cyclically shift a loop's cells' colors.
# ============================================================
L1_RING = (
    [(0,c) for c in range(2,7)] +          # top r0 c2..c6
    [(r,6) for r in range(1,10)] +         # right c6 r1..r9
    [(9,c) for c in range(5,1,-1)] +       # bottom r9 c5..c2
    [(r,2) for r in range(8,0,-1)]         # left c2 r8..r1
)                                          # 26 cells, clockwise from (0,2)
L1_CROSS3 = [(3,c) for c in range(10)]
L1_CROSS6 = [(6,c) for c in range(10)]
# buttons: (box, loop, direction). box=(y0,y1,x0,x1). d=+1 forward along loop order.
L1_BUTTONS = [
    ((16,19,38,40), 'RING',  +1),   # ring top-right e  -> CW confirmed
    ((16,19,19,21), 'RING',  -1),   # ring top-left  8  -> CCW
    ((25,28,47,49), 'C3',    +1),   # cross3 right e    (guess +1)
    ((25,28,13,15), 'C3',    -1),   # cross3 left 8
    ((34,37,47,49), 'C6',    +1),   # cross6 right e
    ((34,37,13,15), 'C6',    -1),   # cross6 left 8
]
L1_LOOPS = {'RING': L1_RING, 'C3': L1_CROSS3, 'C6': L1_CROSS6}
L1_BUDGET = 60   # confirmed: col0 fill = round(64*clicks/60)

def _cellval(grid, r, c):
    return grid[17+3*r][17+3*c]

def _level1_step(grid, action, x, y):
    H = len(grid)
    g = [list(row) for row in grid]
    if action != 6:
        return g, False
    loop_name = None; d = 0
    for box, ln, dd in L1_BUTTONS:
        if _in_box(box, x, y):
            loop_name = ln; d = dd; break
    if loop_name is None:
        return g, False
    order = L1_LOOPS[loop_name]
    n = len(order)
    cols = [grid[17+3*r][17+3*c] for (r, c) in order]
    newcols = [cols[(i-d) % n] for i in range(n)]
    for (r, c), col in zip(order, newcols):
        _set_cell(g, 17+3*r, 17+3*c, col, sz=2)
    _counter_advance(g, grid, H, L1_BUDGET)
    return g, True

def _level1_is_goal(grid):
    # both color-b brackets filled with b(11): cells (r3,c6)=(26,35) & (r6,c6)=(35,35)
    return grid[26][35] == 11 and grid[35][35] == 11

# ============================================================
# Dispatcher
# ============================================================
def step(grid, action, x=None, y=None):
    lvl = CURRENT_LEVEL
    info = {"level_up": False, "dead": False, "win": False}
    if lvl == 0:
        g, moved = _level0_step(grid, action, x, y)
        if moved and _level0_is_goal(g):
            info["level_up"] = True
        return g, info
    if lvl == 1:
        g, moved = _level1_step(grid, action, x, y)
        if moved and _level1_is_goal(g):
            info["level_up"] = True
        return g, info
    # ---- level 2+ : not yet modelled -> passthrough ----
    return [list(row) for row in grid], info

def is_goal(grid):
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return _level0_is_goal(grid)
    if lvl == 1:
        return _level1_is_goal(grid)
    return False
