import numpy as np

def init_state(entry_grid):
    # None lets the first predicted step infer whether one unscored action
    # already preceded the supplied grid (as happens in history replay).
    return {"action_parity": None, "slot_orient": {}, "slot_index": {}}

def _answer_bounds(entry):
    a = np.array(entry)
    h, w = a.shape
    zy, zx = np.where(a == 0)
    selector_x = int(zx.min()) if len(zx) else None
    best = None
    # The answer frame is the lower rectangle whose first five-cell slot is
    # aligned with the black selector brackets. Its frame colour varies.
    for y in range(h // 2, h):
        x = 0
        while x < w:
            col = int(a[y, x])
            z = x + 1
            while z < w and a[y, z] == col:
                z += 1
            length = z - x
            if (col not in (0,1,2,3,4,5) and length >= 7 and
                selector_x is not None and x + 1 == selector_x and
                y + 6 < h and np.all(a[y+6, x:z] == col)):
                if best is None or length > best[0]:
                    best = (length, x, z-1)
            x = z
    return None if best is None else (best[1], best[2])

def _answer_y(entry, bounds):
    a = np.array(entry)
    if bounds is None:
        return None
    x0, x1 = bounds
    zy, zx = np.where(a == 0)
    zmin = int(zy.min()) if len(zy) else a.shape[0] // 2
    zmax = int(zy.max()) if len(zy) else a.shape[0]
    for y in range(a.shape[0] // 2, a.shape[0]-6):
        col = int(a[y, x0])
        if (y > zmin and y + 6 < zmax and
            col not in (0,1,2,3,4,5) and
            np.all(a[y, x0:x1+1] == col) and
            np.all(a[y+6, x0:x1+1] == col)):
            return y + 1
    return None

def _frame_rects(arr):
    """Return genuine framed sequence rectangles as (y,x,length,color)."""
    a = np.array(arr)
    h, w = a.shape
    found = []
    for y in range(h-6):
        x = 0
        while x < w:
            col = int(a[y, x])
            z = x + 1
            while z < w and a[y, z] == col:
                z += 1
            length = z - x
            if (col not in (0,1,2,3,4,5) and length >= 7 and
                    length % 7 == 0 and
                    np.all(a[y+6, x:z] == col) and
                    np.all(a[y:y+7, x] == col) and
                    np.all(a[y:y+7, z-1] == col)):
                found.append((y, x, length, col))
            x = z
    return found

def _editable_slots(entry):
    """Ordered editable tile interiors for either normal or reversed layout."""
    a = np.array(entry)
    bounds = _answer_bounds(entry)
    if bounds is not None:
        ay = _answer_y(entry, bounds)
        if ay is not None:
            return [(bounds[0] + 1 + 7*k, ay)
                    for k in range((bounds[1]-bounds[0]+1)//7)]
    frames = _frame_rects(a)
    lower = sorted([f for f in frames if f[0] >= a.shape[0]//2])
    if len(lower) < 2:
        return []
    qtop = lower[-2][0]
    # In the reversed level-4 layout, the selector treats each complete
    # framed sequence as one editable group (a two-glyph frame gets one wide
    # bracket and both glyphs cycle together), rather than selecting glyphs
    # inside that frame independently.
    return [(x + 1, y + 1)
            for y, x, length, col in sorted([f for f in frames if f[0] < qtop])]

# Consecutive states discovered in the cyclic glyph alphabet.
# ACTION1 advances through this list and ACTION2 reverses.
CYCLE = [
    np.array([[5,5,5,7,7],
              [5,7,5,5,5],
              [5,7,5,7,5],
              [5,7,5,5,5],
              [5,5,5,7,7]]),       # non-example alphabet class
    np.array([[5,5,5,7,7],
              [5,7,5,7,7],
              [5,5,5,5,5],
              [7,7,5,7,5],
              [7,7,5,5,5]]),       # O11 class
    np.array([[5,5,5,5,5],
              [5,7,5,7,5],
              [5,5,5,7,5],
              [5,7,7,7,5],
              [5,5,5,5,5]]),       # O20 class
    np.array([[5,5,5,5,5],
              [5,7,7,5,7],
              [5,7,7,5,7],
              [5,5,5,5,7],
              [5,7,7,7,7]]),       # O10 class
    np.array([[7,5,5,5,7],
              [7,5,7,5,7],
              [5,5,5,5,5],
              [7,5,7,5,7],
              [7,5,5,5,7]]),       # O21 class
    np.array([[7,5,5,5,5],
              [5,5,7,7,5],
              [5,7,7,7,5],
              [5,7,7,5,5],
              [5,5,5,5,7]]),       # O00 class
    np.array([[7,5,5,5,5],
              [7,5,7,7,5],
              [5,5,7,7,5],
              [7,5,7,7,5],
              [7,5,5,5,5]])        # O01 class
]

# Each level uses its own randomly drawn glyph alphabet; level 1 edges are
# learned independently while the transition mechanism is shared.
CYCLE1 = [
    np.array([[5,5,5,5,5],
              [5,7,7,7,7],
              [5,7,5,7,5],
              [5,7,7,7,7],
              [5,7,5,7,5]]),       # U target class
    np.array([[7,5,5,7,5],
              [5,5,7,7,7],
              [7,7,7,7,7],
              [5,5,7,7,7],
              [7,5,5,7,5]]),
    np.array([[5,7,5,5,5],
              [7,7,5,7,7],
              [5,7,5,5,5],
              [7,7,7,7,5],
              [5,7,5,5,5]]),
    np.array([[5,5,5,5,5],
              [5,7,7,7,5],
              [7,7,5,7,7],
              [5,7,7,7,5],
              [5,5,5,5,5]]),
    np.array([[7,5,7,5,7],
              [7,7,7,7,7],
              [5,5,5,5,5],
              [7,7,7,7,7],
              [7,5,7,5,7]]),
    np.array([[5,7,7,7,5],
              [5,7,7,7,7],
              [5,5,5,5,5],
              [7,7,7,7,5],
              [5,7,7,7,5]]),
    np.array([[5,7,7,5,5],
              [7,7,7,7,5],
              [5,7,7,7,5],
              [5,7,7,7,7],
              [5,5,7,7,5]])        # V target class
]

CYCLE2 = [
    np.array([[5,7,7,7,5],
              [5,7,7,7,5],
              [5,5,7,5,5],
              [5,7,7,7,5],
              [5,5,5,5,5]]),       # F
    np.array([[5,5,5,7,7],
              [7,7,5,7,7],
              [7,5,5,5,7],
              [7,7,5,7,7],
              [7,7,5,5,5]]),
    np.array([[7,7,7,7,5],
              [7,7,5,7,5],
              [5,5,5,5,5],
              [7,7,5,7,5],
              [7,7,7,7,5]]),       # E target class
    np.array([[5,5,5,5,5],
              [7,5,7,7,5],
              [7,5,7,7,7],
              [7,5,7,7,5],
              [5,5,5,5,5]]),       # C target class
    np.array([[5,7,7,7,5],
              [5,7,7,7,5],
              [5,5,5,7,5],
              [5,7,5,7,5],
              [5,7,5,5,5]]),       # B target class
    np.array([[5,5,7,5,5],
              [7,5,7,5,7],
              [7,5,5,5,7],
              [7,5,7,5,7],
              [5,5,7,5,5]]),       # D target class
    np.array([[7,5,5,5,7],
              [7,5,7,7,7],
              [5,5,5,5,5],
              [7,5,7,7,7],
              [7,5,5,5,7]])        # A target class
]

CYCLE3 = [
    np.array([[5,7,5,5,5],
              [7,7,5,7,7],
              [5,7,5,5,5],
              [7,7,7,7,5],
              [5,7,5,5,5]]),       # B4 class
    np.array([[5,5,5,5,5],
              [5,7,7,7,5],
              [7,7,5,7,7],
              [5,7,7,7,5],
              [5,5,5,5,5]]),       # B5 class
    np.array([[7,5,7,5,7],
              [7,7,7,7,7],
              [5,5,5,5,5],
              [7,7,7,7,7],
              [7,5,7,5,7]]),       # extra class X
    np.array([[5,7,7,7,5],
              [5,7,7,7,7],
              [5,5,5,5,5],
              [7,7,7,7,5],
              [5,7,7,7,5]]),       # B2 target class
    np.array([[5,7,7,5,5],
              [7,7,7,7,5],
              [5,7,7,7,5],
              [5,7,7,7,7],
              [5,5,7,7,5]]),       # B3 target class
    np.array([[5,5,5,5,5],
              [5,7,7,7,7],
              [5,7,5,7,5],
              [5,7,7,7,7],
              [5,7,5,7,5]]),       # B1 target class
    np.array([[7,5,5,7,5],
              [5,5,7,7,7],
              [7,7,7,7,7],
              [5,5,7,7,7],
              [7,5,5,7,5]])        # B0 target class
]

CYCLE4 = [
    np.array([[5,5,5,5,5],
              [7,5,7,7,5],
              [7,5,7,7,5],
              [7,5,5,5,5],
              [7,7,7,7,5]]),       # P0 class
    np.array([[7,7,5,7,7],
              [5,5,5,5,5],
              [5,7,5,7,5],
              [5,5,5,5,5],
              [7,7,5,7,7]]),       # extra class X
    np.array([[5,5,5,5,7],
              [5,7,7,5,5],
              [5,7,7,7,5],
              [5,5,7,7,5],
              [7,5,5,5,5]]),       # extra class Y
    np.array([[7,7,5,7,7],
              [5,5,5,5,5],
              [5,7,7,7,5],
              [5,7,7,7,5],
              [5,5,5,5,5]]),       # P1/P2 target class
    np.array([[5,5,5,5,5],
              [5,7,7,7,5],
              [5,5,5,5,5],
              [7,5,7,5,7],
              [7,5,5,5,7]]),       # extra class Z
    np.array([[7,7,5,5,5],
              [7,7,5,7,5],
              [5,5,5,5,5],
              [5,7,5,7,7],
              [5,5,5,7,7]]),       # second P0-oriented state
    np.array([[5,5,5,5,5],
              [5,7,5,7,5],
              [5,7,5,5,5],
              [5,7,7,7,5],
              [5,5,5,5,5]]),       # P4 target class
    np.array([[5,5,5,5,5],
              [7,5,7,7,5],
              [7,5,7,7,5],
              [7,5,5,5,5],
              [7,7,7,7,5]])        # P3 target class
]

CYCLE4A = [
    np.array([[5,5,5,7,7],
              [7,7,5,7,7],
              [7,5,5,5,7],
              [7,7,5,7,7],
              [7,7,5,5,5]]),       # A0 transient class
    np.array([[7,7,7,7,5],
              [7,7,5,7,5],
              [5,5,5,5,5],
              [7,7,5,7,5],
              [7,7,7,7,5]]),       # A1 class
    np.array([[5,5,5,5,5],
              [7,5,7,7,5],
              [7,5,7,7,7],
              [7,5,7,7,5],
              [5,5,5,5,5]]),       # extra orange class X
    np.array([[5,7,7,7,5],
              [5,7,7,7,5],
              [5,5,5,7,5],
              [5,7,5,7,5],
              [5,7,5,5,5]]),       # extra orange class Y
    np.array([[5,5,7,5,5],
              [7,5,7,5,7],
              [7,5,5,5,7],
              [7,5,7,5,7],
              [5,5,7,5,5]]),       # second A0-oriented state
    np.array([[7,5,5,5,7],
              [7,5,7,7,7],
              [5,5,5,5,5],
              [7,5,7,7,7],
              [7,5,5,5,7]]),       # A2/A3 target class
    np.array([[5,7,7,7,5],
              [5,7,7,7,5],
              [5,5,7,5,5],
              [5,7,7,7,5],
              [5,5,5,5,5]]),       # A4 target class
    np.array([[5,5,5,7,7],
              [7,7,5,7,7],
              [7,5,5,5,7],
              [7,7,5,7,7],
              [7,7,5,5,5]])        # recurrent A0 target class
]

def _active_cycle(frame_color=None):
    if CURRENT_LEVEL == 0:
        return CYCLE
    if CURRENT_LEVEL == 1:
        return CYCLE1
    if CURRENT_LEVEL == 2:
        return CYCLE2
    if CURRENT_LEVEL == 3:
        return CYCLE3
    if CURRENT_LEVEL == 4 and frame_color == 10:
        return CYCLE4A
    return CYCLE4

def _d4_equal(a, b):
    aa = (np.array(a) == 5)
    bb = (np.array(b) == 5)
    for flip in (False, True):
        base = np.fliplr(aa) if flip else aa
        for krot in range(4):
            if np.array_equal(np.rot90(base, krot), bb):
                return True
    return False

def _lookup_goal(grid):
    """Decode the top lookup table and concatenate variable-length outputs."""
    e = np.array(ENTRY_GRID)
    g = np.array(grid)
    h, w = e.shape
    zy, zx = np.where(e == 0)
    zmin = int(zy.min()) if len(zy) else h

    def runs_at(y):
        runs = []
        x = 0
        while x < w:
            col = int(e[y, x])
            z = x + 1
            while z < w and e[y, z] == col:
                z += 1
            runs.append((x, z, col))
            x = z
        return runs

    # Normally the selector brackets the lower answer. In the reversed
    # layout it brackets editable upper rules, while the bottom two frames
    # are a fixed query/answer pair.
    ab = _answer_bounds(ENTRY_GRID)
    reversed_mode = (ab is None)
    qframe = None
    ay = None
    if not reversed_mode:
        for y in range(h // 2, min(zmin, h-6)):
            for x, z, col in runs_at(y):
                length = z - x
                if (col not in (0,1,2,3,4,5) and length >= 7 and
                    length % 7 == 0 and np.all(e[y+6, x:z] == col)):
                    if qframe is None or length > qframe[0]:
                        qframe = (length, x, z-1, y, col)
        ay = _answer_y(ENTRY_GRID, ab)
    else:
        lower = sorted([f for f in _frame_rects(e) if f[0] >= h//2])
        if len(lower) >= 2:
            qy, qx, qlen0, qcol = lower[-2]
            ay0, ax, alen, acol = lower[-1]
            qframe = (qlen0, qx, qx+qlen0-1, qy, qcol)
            ab = (ax, ax+alen-1)
            ay = ay0 + 1
    if qframe is None or ab is None or ay is None:
        return False
    qlen, ql, qr, qtop, qcolor = qframe
    acolor = int(e[ay-1, ab[0]])

    # Read every upper example as a left-to-right rewrite rule. Rules may
    # use variable-length sequences and may pass through an intermediate
    # frame colour before reaching the answer colour.
    frames_by_y = {}
    rule_arr = g if reversed_mode else e
    for y, x, length, col in _frame_rects(e):
        if y >= qtop:
            continue
        seq = [rule_arr[y+1:y+6, x+1+7*k:x+6+7*k]
               for k in range(length // 7)]
        frames_by_y.setdefault(y, []).append((x, col, seq))
    rules = []
    for y in sorted(frames_by_y):
        row = sorted(frames_by_y[y], key=lambda p: p[0])
        for i in range(0, len(row)-1, 2):
            sx, scol, source_seq = row[i]
            ox, ocol, output_seq = row[i+1]
            rules.append((scol, source_seq, ocol, output_seq))

    query_seq = [e[qtop+1:qtop+6, ql+1+7*k:ql+6+7*k]
                 for k in range(qlen // 7)]

    def rewrite(seq, color, seen):
        if color == acolor:
            return list(seq)
        if color in seen:
            return None
        destinations = []
        for scol, source_seq, ocol, output_seq in rules:
            if scol == color and ocol not in destinations:
                destinations.append(ocol)
        for dest in destinations:
            stage_rules = [(src, out) for scol, src, ocol, out in rules
                           if scol == color and ocol == dest]
            memo = {}
            def tokenize(pos):
                if pos == len(seq):
                    return []
                if pos in memo:
                    return memo[pos]
                for source_seq, output_seq in stage_rules:
                    nsrc = len(source_seq)
                    if (pos + nsrc <= len(seq) and
                            all(_d4_equal(source_seq[j], seq[pos+j])
                                for j in range(nsrc))):
                        tail = tokenize(pos + nsrc)
                        if tail is not None:
                            memo[pos] = list(output_seq) + tail
                            return memo[pos]
                memo[pos] = None
                return None
            next_seq = tokenize(0)
            if next_seq is not None:
                result = rewrite(next_seq, dest, tuple(seen) + (color,))
                if result is not None:
                    return result
        return None

    targets = rewrite(query_seq, qcolor, ())
    if targets is None:
        return False

    nanswer = (ab[1] - ab[0] + 1) // 7
    if len(targets) != nanswer:
        return False
    for k, target in enumerate(targets):
        xa = ab[0] + 1 + 7*k
        if not _d4_equal(target, g[ay:ay+5, xa:xa+5]):
            return False
    return True

def is_goal(state, grid):
    return _lookup_goal(grid)

def predict(state, grid, action, x=None, y=None):
    state = dict(state or {})
    a = np.array(grid, dtype=int)
    entry = np.array(ENTRY_GRID)
    parity = state.get("action_parity", None)
    slot_orient = dict(state.get("slot_orient", {}))
    slot_index = dict(state.get("slot_index", {}))
    if parity is None:
        # On a live level-entry grid this is 0. During backtest the first
        # available before-grid can already be one action past entry.
        parity = 0 if np.array_equal(a, entry) else 1
    out = a.copy()
    info = {"level_up": False, "dead": False, "win": False}
    bounds = _answer_bounds(ENTRY_GRID)
    slots = _editable_slots(ENTRY_GRID)
    zy, zx = np.where(a == 0)
    selected = None
    if len(zx):
        minx, miny, maxy = int(zx.min()), int(zy.min()), int(zy.max())
        for i, (sx0, sy0) in enumerate(slots):
            if sx0 == minx and miny < sy0 + 2 < maxy:
                selected = i
                break

    if action in (3, 4) and selected is not None:
        ni = selected + (-1 if action == 3 else 1)
        if 0 <= ni < len(slots):
            sx, sy = slots[selected]
            nx, ny = slots[ni]
            background = 2 if sy < a.shape[0]//2 else 3
            out[a == 0] = background
            # Level 4 selects a whole framed sequence.  Its bracket spans
            # the complete interior width (5 for one glyph, 12 for two).
            bw = 5
            if CURRENT_LEVEL == 4:
                frame_col = int(entry[ny-1, nx-1])
                rz = nx - 1
                while rz < entry.shape[1] and entry[ny-1, rz] == frame_col:
                    rz += 1
                bw = rz - (nx - 1) - 2
            out[ny-4, nx:nx+bw] = 0
            out[ny-3, nx] = 0
            out[ny-3, nx+bw-1] = 0
            out[ny+7, nx] = 0
            out[ny+7, nx+bw-1] = 0
            out[ny+8, nx:nx+bw] = 0

    if action in (1, 2) and selected is not None:
        sx, ey = slots[selected]
        # Normally a selector addresses one glyph.  In level 4 it addresses
        # the entire framed sequence, so advance every glyph in that frame.
        ntiles = 1
        if CURRENT_LEVEL == 4:
            frame_col = int(entry[ey-1, sx-1])
            rz = sx - 1
            while rz < entry.shape[1] and entry[ey-1, rz] == frame_col:
                rz += 1
            ntiles = (rz - (sx - 1)) // 7
        for kk in range(ntiles):
            tx = sx + 7*kk
            tile = a[ey:ey+5, tx:tx+5]
            # Canonical cycle arrays use 7 as the blank; render it with the
            # selected tile's own frame colour.
            answer_bg = int(entry[ey-1, tx-1])
            tile_norm = np.where(tile == 5, 5, 7)
            cycle = _active_cycle(answer_bg)
            # Cycling is equivariant under rotations/reflections. Remember
            # each glyph's D4 orientation independently inside a group.
            slot_key = (tx, ey)
            if (CURRENT_LEVEL == 1 and bounds is not None and
                    tx == bounds[1] - 5):
                slot_orient[slot_key] = (False, 3)
            matched = None
            if (CURRENT_LEVEL == 4 and slot_key in slot_index and
                    slot_key in slot_orient):
                i = int(slot_index[slot_key])
                flip, krot = tuple(slot_orient[slot_key])
                matched = (i, flip, krot)
            else:
                candidates = []
                if slot_key in slot_orient:
                    candidates.append(tuple(slot_orient[slot_key]))
                rots = (0, 1, 2, 3)
                # Repeated glyphs in a multi-glyph level-4 frame can look
                # identical while carrying opposite D4 orientations.  The
                # later glyph is drawn in the reverse rotational phase.
                if (CURRENT_LEVEL == 4 and
                        ((ntiles > 1 and kk % 2 == 1) or selected == 5)):
                    rots = (0, 3, 2, 1)
                candidates += [(flip, krot) for flip in (False, True)
                               for krot in rots
                               if (flip, krot) not in candidates]
                if CURRENT_LEVEL == 4:
                    # Prefer the earliest semantic index before choosing
                    # among D4-equivalent renderings.  Index 0 and the final
                    # recurrent state can be visually identical.
                    for i, known in enumerate(cycle):
                        for flip, krot in candidates:
                            base = np.fliplr(known) if flip else known
                            shown = np.rot90(base, krot)
                            if np.array_equal(tile_norm, shown):
                                matched = (i, flip, krot)
                                break
                        if matched is not None:
                            break
                else:
                    for flip, krot in candidates:
                        for i, known in enumerate(cycle):
                            base = np.fliplr(known) if flip else known
                            shown = np.rot90(base, krot)
                            if np.array_equal(tile_norm, shown):
                                matched = (i, flip, krot)
                                break
                        if matched is not None:
                            break
            if matched is not None:
                i, flip, krot = matched
                slot_orient[slot_key] = (flip, krot)
                if CURRENT_LEVEL == 4:
                    # A transient entry glyph at index 0 is followed by a
                    # recurrent cycle over indices 1..last.
                    if len(cycle) == 1:
                        j = 0
                    elif action == 1:
                        j = 1 if i == len(cycle) - 1 else i + 1
                    else:
                        j = len(cycle) - 1 if i == 1 else max(i - 1, 0)
                elif action == 1:
                    j = min(i + 1, len(cycle) - 1)
                else:
                    j = max(i - 1, 0)
                if CURRENT_LEVEL == 4:
                    slot_index[slot_key] = j
                nb = np.fliplr(cycle[j]) if flip else cycle[j]
                rendered = np.rot90(nb, krot)
                out[ey:ey+5, tx:tx+5] = np.where(
                    rendered == 5, 5, answer_bg)
    # The red bottom meter advances whenever an odd-numbered prior action
    # is followed by the next action (i.e. after every pair of actions).
    meter_rows = []
    for yy in range(a.shape[0]):
        if np.sum(entry[yy] == 1) >= 10:
            meter_rows.append(yy)
    if meter_rows and parity == 1:
        yy = meter_rows[-1]
        loc = np.where(entry[yy] == 1)[0]
        remaining = [int(xx) for xx in loc if a[yy, xx] == 1]
        if remaining:
            out[yy, remaining[-1]] = 4

    if _lookup_goal(out):
        if CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 5:
            info["win"] = True
        else:
            info["level_up"] = True
    state["action_parity"] = 1 - int(parity)
    state["slot_orient"] = slot_orient
    state["slot_index"] = slot_index
    return out.tolist(), info, state
