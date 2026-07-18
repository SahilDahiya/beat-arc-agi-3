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
                    elif not (np.all(q == 0) or np.all(q == 2) or np.all(q == 3)):
                        ok = False
            # Colour 4 is the editable layout's spacer/background.  Level-0
            # demonstrations instead have colour 5 around their codes.
            if ok and (a[y, x-3] == 4 or a[y-3, x] == 4):
                out.append((x, y, v))
    return out

def _primary_button_positions(entry):
    a = np.array(entry)
    s = set()
    for cx, cy, center in _clues(entry):
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                if dx == 0 and dy == 0:
                    continue
                # Inner 3 explicitly marks an absent direction.
                if int(a[cy+dy, cx+dx]) == 3:
                    continue
                x0, y0 = cx - 2 + 4*dx, cy - 2 + 4*dy
                q = a[y0:y0+6, x0:x0+6]
                # Only solid 6x6 tiles are buttons. Patterned e/6 tiles in
                # level 4 are fixed holes and therefore impose no constraint.
                if q.shape == (6, 6) and np.all(q == q[0, 0]) and int(q[0, 0]) not in (4, 5):
                    s.add((x0, y0))
    return s

def _secondary_clues(entry):
    # Level 4 contains a second clue alphabet: doubled e/6 checker codes
    # with an e center. Require both symbols so solid tiles are not mistaken
    # for codes.
    a = np.array(entry)
    h, w = a.shape
    out = []
    for y in range(2, h-3):
        for x in range(2, w-3):
            center = int(a[y, x])
            if center in (0, 2, 3, 4, 5, 6) or not np.all(a[y:y+2, x:x+2] == center):
                continue
            ok = True
            seen6 = False
            for dy in (-2, 0, 2):
                for dx in (-2, 0, 2):
                    q = a[y+dy:y+dy+2, x+dx:x+dx+2]
                    if not (np.all(q == center) or np.all(q == 6)):
                        ok = False
                    if (dx or dy) and np.all(q == 6):
                        seen6 = True
            if ok and seen6:
                out.append((x, y, center))
    return out

def _secondary_button_positions(entry):
    a = np.array(entry)
    s = set()
    for cx, cy, center in _secondary_clues(entry):
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                if dx == 0 and dy == 0:
                    continue
                x0, y0 = cx - 2 + 4*dx, cy - 2 + 4*dy
                q = a[y0:y0+6, x0:x0+6]
                if q.shape == (6, 6) and np.all(q == q[0, 0]) and int(q[0, 0]) not in (4, 5):
                    s.add((x0, y0))
    return s

def _fillable_positions(entry):
    # e/6 checker tiles are unfilled (transparent) cells. Their top-left
    # palette-colour pixel gives the current cycle phase; clicking fills the
    # whole 6x6 cell with the next palette colour.
    return {(cx-2, cy-2) for cx, cy, center in _secondary_clues(entry)}

def _button_positions(entry):
    return (_primary_button_positions(entry) |
            _secondary_button_positions(entry) |
            _fillable_positions(entry))

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
    buttons = _button_positions(ENTRY_GRID)
    secondary_buttons = _secondary_button_positions(ENTRY_GRID)

    # e/6 checker cells are transparent/unfilled buttons, not clue
    # alphabets. Ordinary clues constrain them exactly like solid neighbours.
    # All otherwise unconstrained buttons remain at the first palette colour.
    if _secondary_clues(ENTRY_GRID):
        base = palette[0]
        desired = {p: base for p in buttons}
        primary = _primary_button_positions(ENTRY_GRID)
        fillable = _fillable_positions(ENTRY_GRID)
        for cx, cy, center in clues:
            other = _ink2(center, palette, clues)
            for dy in (-2, 0, 2):
                for dx in (-2, 0, 2):
                    if dx == 0 and dy == 0:
                        continue
                    p = (cx - 2 + 4*dx, cy - 2 + 4*dy)
                    if p not in primary and p not in fillable:
                        continue
                    inner = int(a[cy+dy, cx+dx])
                    want = center if inner == 0 else (other if inner == 2 else None)
                    if want is not None:
                        desired[p] = want
        return all(int(a[y0, x0]) == want for (x0, y0), want in desired.items())

    for cx, cy, center in clues:
        other = _ink2(center, palette, clues)
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                if dx == 0 and dy == 0:
                    continue
                x0, y0 = cx - 2 + 4*dx, cy - 2 + 4*dy
                # Secondary checker-alphabet clues are the later layer and
                # override primary constraints wherever they overlap.
                if (x0, y0) not in buttons or (x0, y0) in secondary_buttons:
                    continue
                inner = int(a[cy+dy, cx+dx])
                want = center if inner == 0 else (other if inner == 2 else None)
                outer = int(a[y0, x0])
                if want is None or outer != want:
                    return False

    # Checker-alphabet clues form a later overriding layer. In this
    # alphabet the center symbol denotes the center colour and 6 denotes the
    # other palette colour.
    for cx, cy, center in _secondary_clues(ENTRY_GRID):
        other = _ink2(center, palette, [(cx, cy, center)])
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                if dx == 0 and dy == 0:
                    continue
                x0, y0 = cx - 2 + 4*dx, cy - 2 + 4*dy
                if (x0, y0) not in secondary_buttons:
                    continue
                inner = int(a[cy+dy, cx+dx])
                want = center if inner == center else (other if inner == 6 else None)
                if want is None or int(a[y0, x0]) != want:
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
                if (x0, y0) in _fillable_positions(ENTRY_GRID):
                    # A patterned cell is a masked multi-cell switch. Its own
                    # palette pixels cycle, and every 6 in its doubled 3x3
                    # icon cycles the corresponding neighbouring button.
                    targets = [(x0, y0)]
                    e = np.array(ENTRY_GRID)
                    cx, cy = x0 + 2, y0 + 2
                    for dy in (-2, 0, 2):
                        for dx in (-2, 0, 2):
                            if dx == 0 and dy == 0:
                                continue
                            p = (x0 + 4*dx, y0 + 4*dy)
                            if int(e[cy+dy, cx+dx]) == 6 and p in buttons:
                                targets.append(p)
                    for tx, ty in targets:
                        src = a[ty:ty+6, tx:tx+6].copy()
                        q = src.copy()
                        for i, pv in enumerate(palette):
                            q[src == pv] = palette[(i + 1) % len(palette)]
                        a[ty:ty+6, tx:tx+6] = q
                else:
                    nv = palette[(palette.index(v) + 1) % len(palette)]
                    a[y0:y0+6, x0:x0+6] = nv

                # The footer is a compressed press counter. Compact
                # layouts add two pixels per press. Wide layouts add two
                # pixels per three presses: cumulative floor((2*n+1)/3),
                # giving increments 1,0,1,1,0,1,...
                old_n = st["presses"]
                st["presses"] = old_n + 1
                if _fillable_positions(ENTRY_GRID):
                    # Masked-switch layouts use the slow counter cadence
                    # regardless of their number of switches.
                    width = 1 if st["presses"] % 4 in (2, 3) else 0
                elif len(buttons) <= 16:
                    width = 2
                elif len(buttons) <= 24:
                    before_fill = (2*old_n + 1)//3
                    after_fill = (2*st["presses"] + 1)//3
                    width = after_fill - before_fill
                else:
                    # Largest plain layouts render two counter pixels per
                    # four presses, adjacent: increments 0,1,1,0 repeating.
                    width = 1 if st["presses"] % 4 in (2, 3) else 0
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
