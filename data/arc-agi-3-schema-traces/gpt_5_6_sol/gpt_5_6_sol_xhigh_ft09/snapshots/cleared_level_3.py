import numpy as np

def _clues(entry):
    """Editable doubled 3x3 codes as (center-x, center-y, center-colour)."""
    a = np.array(entry)
    h, w = a.shape
    out = []
    for y in range(2, h-3):
        for x in range(2, w-3):
            v = int(a[y, x])
            if v in (0, 2, 4, 5) or not np.all(a[y:y+2, x:x+2] == v):
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
            # Colour 4 is the editable layout's spacer/background.  Level-0
            # demonstrations instead have colour 5 around their codes.
            if ok and (a[y, x-3] == 4 or a[y-3, x] == 4):
                out.append((x, y, v))
    return out

def _button_positions(entry):
    s = set()
    for cx, cy, center in _clues(entry):
        for br in (-1, 0, 1):
            for bc in (-1, 0, 1):
                if br != 0 or bc != 0:
                    s.add((cx - 2 + 8*bc, cy - 2 + 8*br))
    return s

def _palette(entry):
    a = np.array(entry)
    bg = int(a[0, 0])
    vals = []
    # Levels with an explicit palette show ordered 4x4 swatches down the
    # upper-right corner.
    for y in range(0, min(a.shape[0]-3, 16), 4):
        q = a[y:y+4, a.shape[1]-4:a.shape[1]]
        if np.all(q == q[0, 0]) and int(q[0, 0]) != bg:
            v = int(q[0, 0])
            if v not in vals:
                vals.append(v)
        else:
            break
    if len(vals) >= 2:
        return tuple(vals)

    # Level 0 has no swatches; infer its two colours from centers/buttons.
    pool = {center for cx, cy, center in _clues(entry)}
    for x0, y0 in _button_positions(entry):
        pool.add(int(a[y0, x0]))
    return tuple(sorted(pool))

def _ink2(center, palette, clues):
    # With two colours, 2 means the colour opposite this clue's center.
    if len(palette) == 2 and center in palette:
        return palette[1] if palette[0] == center else palette[0]
    # With three or more, the layouts reserve one palette colour that is
    # not used by any clue center as the common meaning of 2.
    centers = {c for x, y, c in clues}
    remaining = [p for p in palette if p not in centers]
    if len(remaining) == 1:
        return remaining[0]
    return None

def _solved(g):
    clues = _clues(ENTRY_GRID)
    palette = _palette(ENTRY_GRID)
    if not clues or len(palette) < 2:
        return False
    a = np.array(g)
    # Inner 0 denotes the code's center colour; inner 2 denotes either the
    # opposite colour (two-colour palette) or the shared non-center colour.
    for cx, cy, center in clues:
        other = _ink2(center, palette, clues)
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                if dx == 0 and dy == 0:
                    continue
                inner = int(a[cy+dy, cx+dx])
                want = center if inner == 0 else (other if inner == 2 else None)
                outer = int(a[cy+4*dy, cx+4*dx])
                if want is None or outer != want:
                    return False
    return True

def init_state(entry_grid):
    return {"presses": 0}

def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    st = dict(state or {})
    st.setdefault("presses", 0)
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return a.tolist(), info, st

    palette = _palette(ENTRY_GRID)
    buttons = _button_positions(ENTRY_GRID)
    for x0, y0 in buttons:
        if x0 <= x < x0+6 and y0 <= y < y0+6:
            v = int(a[y0, x0])
            if len(palette) >= 2 and v in palette:
                nv = palette[(palette.index(v) + 1) % len(palette)]
                a[y0:y0+6, x0:x0+6] = nv

                # The footer is a compressed press counter. Compact
                # layouts add two pixels per press. Wide layouts add two
                # pixels per three presses: cumulative floor((2*n+1)/3),
                # giving increments 1,0,1,1,0,1,...
                old_n = st["presses"]
                st["presses"] = old_n + 1
                if len(buttons) <= 16:
                    width = 2
                else:
                    before_fill = (2*old_n + 1)//3
                    after_fill = (2*st["presses"] + 1)//3
                    width = after_fill - before_fill
                if width:
                    cs = [i for i in range(a.shape[1]) if a[-1, i] == 12]
                    if len(cs) >= width:
                        a[-1, cs[-width:]] = 11
            info["level_up"] = _solved(a)
            if info["level_up"] and CURRENT_LEVEL == 5:
                info["level_up"] = False
                info["win"] = True
            return a.tolist(), info, st
    return a.tolist(), info, st

def is_goal(state, grid):
    return _solved(grid)
