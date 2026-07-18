import numpy as np

def _clues(entry):
    """Return editable-panel clue centers (x,y,alternate outer colour)."""
    a = np.array(entry)
    h, w = a.shape
    out = []
    for y in range(2, h-3):
        for x in range(2, w-3):
            v = int(a[y, x])
            if v in (0, 2, 4, 5, 9) or not np.all(a[y:y+2, x:x+2] == v):
                continue
            ok = True
            for dy in (-2, 0, 2):
                for dx in (-2, 0, 2):
                    q = a[y+dy:y+dy+2, x+dx:x+dx+2]
                    if dx == 0 and dy == 0:
                        if not np.all(q == v):
                            ok = False
                    elif not (np.all(q == 0) or np.all(q == 2)):
                        ok = False
            # Colour 4 is the answer-panel/background spacer.  Level-0
            # demonstrations use colour 5 here and are not editable.
            if ok and (a[y, x-3] == 4 or a[y-3, x] == 4):
                out.append((x, y, v))
    return out

def _buttons(entry):
    # Map each unique surrounding 6x6 block top-left to its alternate colour.
    d = {}
    for cx, cy, alt in _clues(entry):
        for br in (-1, 0, 1):
            for bc in (-1, 0, 1):
                if br == 0 and bc == 0:
                    continue
                d[(cx - 2 + 8*bc, cy - 2 + 8*br)] = alt
    return d

def _solved(g):
    clues = _clues(ENTRY_GRID)
    if not clues:
        return False
    a = np.array(g)
    # The little code says what each large surrounding block must be:
    # 2 -> colour 9; 0 -> the clue's central/alternate colour.
    for cx, cy, alt in clues:
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                if dx == 0 and dy == 0:
                    continue
                inner = int(a[cy+dy, cx+dx])
                want = alt if inner == 0 else (9 if inner == 2 else None)
                outer = int(a[cy+4*dy, cx+4*dx])
                if want is None or outer != want:
                    return False
    return True

def step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return a.tolist(), info

    for (x0, y0), alt in _buttons(ENTRY_GRID).items():
        if x0 <= x < x0+6 and y0 <= y < y0+6:
            v = int(a[y0, x0])
            if v in (9, alt):
                a[y0:y0+6, x0:x0+6] = alt if v == 9 else 9
                # Every successful button press advances the two-pixel
                # bottom status strip, right to left.
                cs = [i for i in range(a.shape[1]) if a[-1, i] == 12]
                if len(cs) >= 2:
                    a[-1, cs[-2:]] = 11
            info["level_up"] = _solved(a)
            # The sixth level's completion is the game win rather than an
            # ordinary level-up.
            if info["level_up"] and CURRENT_LEVEL == 5:
                info["level_up"] = False
                info["win"] = True
            return a.tolist(), info
    return a.tolist(), info

def is_goal(grid):
    return _solved(grid)
