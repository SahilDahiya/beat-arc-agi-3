import numpy as np

# ---- Level 0 conveyor geometry (grounded from ENTRY_GRID layout) ----
# 20-cell closed loop, each cell a 4x4 block. Clockwise order from ROW A leftmost.
LOOP_CORNERS = [
    (19,12),(19,18),(19,24),(19,30),(19,36),(19,42),(19,48),  # ROW A left->right (0..6)
    (25,48),(31,48),(37,48),                                   # RIGHT col top->bot (7..9)
    (43,48),(43,42),(43,36),(43,30),(43,24),(43,18),(43,12),   # ROW B right->left (10..16)
    (37,12),(31,12),(25,12),                                   # LEFT col bot->top (17..19)
]
# Buttons (bboxes in ENTRY_GRID): LEFT shape color 8, RIGHT shape color e(14)
RIGHT_BOX = (29,36,56,61)   # y0,y1,x0,x1  -> rotate CLOCKWISE
LEFT_BOX  = (29,36, 2, 7)   # -> rotate COUNTER-CLOCKWISE (guess, unconfirmed)

def _in_box(box, x, y):
    if x is None or y is None:
        return False
    y0,y1,x0,x1 = box
    return y0 <= y <= y1 and x0 <= x <= x1

def _cell_color(grid, cy, cx):
    return grid[cy][cx]

def _set_cell(g, cy, cx, col):
    for dy in range(4):
        for dx in range(4):
            g[cy+dy][cx+dx] = col

def step(grid, action, x=None, y=None):
    H = len(grid); W = len(grid[0])
    g = [list(row) for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6:
        return g, info

    cols = [_cell_color(grid, cy, cx) for (cy, cx) in LOOP_CORNERS]
    n = len(cols)
    rotated = False
    if _in_box(RIGHT_BOX, x, y):
        newcols = [cols[(i-1) % n] for i in range(n)]  # clockwise
        rotated = True
    elif _in_box(LEFT_BOX, x, y):
        newcols = [cols[(i+1) % n] for i in range(n)]  # counter-clockwise
        rotated = True

    if rotated:
        for (cy, cx), col in zip(LOOP_CORNERS, newcols):
            _set_cell(g, cy, cx, col)
        # counter on col0: a move-budget bar of height H, BUDGET moves.
        # fill height = round(H * clicks / BUDGET). Invert current fill to get clicks.
        BUDGET = 13
        c = 0
        for yy in range(H):
            if grid[yy][0] == 5:
                c += 1
            else:
                break
        k = int(round(BUDGET * c / float(H)))   # clicks so far
        k2 = k + 1
        newc = int(round(H * k2 / float(BUDGET)))
        if newc > H:
            newc = H
        for yy in range(newc):
            g[yy][0] = 5
    return g, info

# Goal hypothesis: unique 'b'(11) tile aligned into bracketed slot = loop idx0
# (ROW A block#0, top-left pixel (19,12)). Bracket is drawn in color 11 (match hint).
def is_goal(grid):
    return grid[19][12] == 11
