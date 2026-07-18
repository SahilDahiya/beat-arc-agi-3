# v3: PEG SOLITAIRE model.
# Board: 4x4 blocks separated by 2px gaps, parsed from ENTRY_GRID (cells 1/14).
# Block kinds: empty (all 1), peg (diamond of 14, corners 1), selected peg (corners 3 +
#   green ring around 6x6), target (red 2 hollow diamond = legal jump landing).
# Click on peg -> select it (clears old selection/targets), show targets = landings of
#   legal jumps (over adjacent peg into empty block 2 away).
# Click on target with selection -> jump: source+jumped peg removed, landing gets peg.
# Click elsewhere/empty -> (guess) clears selection+targets.
# Every action appends 1 at leftmost 0 of row 0 (move counter).
# Guess: reducing to 1 peg => level_up.

E = 14

def _find_blocks(entry):
    H = len(entry); W = len(entry[0])
    pos = []
    for y in range(H):
        for x in range(W):
            if entry[y][x] in (1, E):
                left = x > 0 and entry[y][x-1] in (1, E)
                up = y > 0 and entry[y-1][x] in (1, E)
                if not left and not up:
                    pos.append((x, y))
    return pos

def _classify(g, x0, y0):
    cells = [g[y0+dy][x0+dx] for dy in range(4) for dx in range(4)]
    if E in cells:
        return ('peg', g[y0][x0] == 3)
    if 2 in cells:
        return ('target', False)
    return ('empty', False)

def _draw(g, x0, y0, kind, sel=False):
    if kind == 'empty':
        pat = [[1,1,1,1],[1,1,1,1],[1,1,1,1],[1,1,1,1]]
    elif kind == 'peg':
        c = 3 if sel else 1
        pat = [[c,E,E,c],[E,E,E,E],[E,E,E,E],[c,E,E,c]]
    else:  # target
        pat = [[1,2,2,1],[2,1,1,2],[2,1,1,2],[1,2,2,1]]
    for dy in range(4):
        for dx in range(4):
            g[y0+dy][x0+dx] = pat[dy][dx]

def _ring(g, x0, y0, on):
    v = 3 if on else 0
    for dx in range(4):
        g[y0-1][x0+dx] = v
        g[y0+4][x0+dx] = v
    for dy in range(4):
        g[y0+dy][x0-1] = v
        g[y0+dy][x0+4] = v

def _clear_sel(g, state):
    for b, (k, s) in state.items():
        if k == 'peg' and s:
            _draw(g, b[0], b[1], 'peg', sel=False)
            _ring(g, b[0], b[1], False)
        elif k == 'target':
            _draw(g, b[0], b[1], 'empty')

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    for i, v in enumerate(g[0]):
        if v == 0:
            g[0][i] = 1
            break
    if action != 6:
        return g, info
    blocks = _find_blocks(ENTRY_GRID)
    bset = set(blocks)
    state = {b: _classify(g, b[0], b[1]) for b in blocks}
    clicked = None
    for (bx, by) in blocks:
        if bx <= x <= bx + 3 and by <= y <= by + 3:
            clicked = (bx, by)
            break
    if clicked is None:
        return g, info
    kind, sel = state[clicked]
    selected = [b for b, (k, s) in state.items() if k == 'peg' and s]
    if kind == 'peg':
        _clear_sel(g, state)
        _draw(g, clicked[0], clicked[1], 'peg', sel=True)
        _ring(g, clicked[0], clicked[1], True)
        for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
            mid = (clicked[0] + dx, clicked[1] + dy)
            land = (clicked[0] + 2 * dx, clicked[1] + 2 * dy)
            if mid in bset and land in bset:
                if state[mid][0] == 'peg' and state[land][0] in ('empty', 'target'):
                    _draw(g, land[0], land[1], 'target')
        return g, info
    if kind == 'target' and selected:
        s = selected[0]
        mid = ((s[0] + clicked[0]) // 2, (s[1] + clicked[1]) // 2)
        for b, (k, ss) in state.items():
            if k == 'target':
                _draw(g, b[0], b[1], 'empty')
        _draw(g, s[0], s[1], 'empty')
        _ring(g, s[0], s[1], False)
        _draw(g, mid[0], mid[1], 'empty')
        _draw(g, clicked[0], clicked[1], 'peg')
        n = 0
        for b in blocks:
            if _classify(g, b[0], b[1])[0] == 'peg':
                n += 1
        if n == 1:
            info["level_up"] = True
        return g, info
    _clear_sel(g, state)
    return g, info

def is_goal(grid):
    n = 0
    for (x0, y0) in _find_blocks(ENTRY_GRID):
        cells = [grid[y0+dy][x0+dx] for dy in range(4) for dx in range(4)]
        if E in cells:
            n += 1
    return n == 1
