import numpy as np

def _target_center(entry):
    a = np.array(entry)
    h, w = a.shape
    # Center of the small 3x3 code embedded in the large colour-4 answer panel.
    for y in range(1, h-2):
        for x in range(1, w-2):
            if np.all(a[y:y+2, x:x+2] == 8):
                if x >= 3 and y >= 3 and (a[y, x-3] == 4 or a[y-3, x] == 4):
                    return x, y
    return None

def _solved(g):
    c = _target_center(ENTRY_GRID)
    if c is None:
        return False
    cx, cy = c
    a = np.array(g)
    # Each little code cell says what the corresponding large surrounding
    # block must be: 0 -> 8, 2 -> 9.
    for dy in (-2, 0, 2):
        for dx in (-2, 0, 2):
            if dx == 0 and dy == 0:
                continue
            inner = int(a[cy+dy, cx+dx])
            want = 8 if inner == 0 else (9 if inner == 2 else None)
            outer = int(a[cy+4*dy, cx+4*dx])
            if want is None or outer != want:
                return False
    return True

def step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return a.tolist(), info
    c = _target_center(ENTRY_GRID)
    if c is None:
        return a.tolist(), info
    cx, cy = c

    # Only the eight large 6x6 answer blocks are buttons.  The central small
    # glyph is the fixed clue, so a click there has no effect.
    for br in (-1, 0, 1):
        for bc in (-1, 0, 1):
            if br == 0 and bc == 0:
                continue
            x0 = cx - 2 + 8*bc
            y0 = cy - 2 + 8*br
            if x0 <= x < x0+6 and y0 <= y < y0+6:
                v = int(a[y0, x0])
                if v in (8, 9):
                    a[y0:y0+6, x0:x0+6] = 17-v
                    # A successful button press spends one unit in the
                    # bottom status bar, rendered as a two-pixel c -> b pair
                    # filled from right to left.
                    cs = [i for i in range(a.shape[1]) if a[-1, i] == 12]
                    if len(cs) >= 2:
                        a[-1, cs[-2:]] = 11
                info["level_up"] = _solved(a)
                return a.tolist(), info
    return a.tolist(), info

def is_goal(grid):
    return _solved(grid)
