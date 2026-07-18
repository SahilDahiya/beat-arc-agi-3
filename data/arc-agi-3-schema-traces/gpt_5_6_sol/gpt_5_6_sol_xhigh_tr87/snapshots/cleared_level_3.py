import numpy as np

def init_state(entry_grid):
    # None lets the first predicted step infer whether one unscored action
    # already preceded the supplied grid (as happens in history replay).
    return {"action_parity": None, "slot_orient": {}}

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

def _active_cycle():
    if CURRENT_LEVEL == 0:
        return CYCLE
    if CURRENT_LEVEL == 1:
        return CYCLE1
    if CURRENT_LEVEL == 2:
        return CYCLE2
    return CYCLE3

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

    # The query is the framed multi-glyph rectangle above the selector.
    qframe = None
    for y in range(h // 2, min(zmin, h-6)):
        for x, z, col in runs_at(y):
            length = z - x
            if (col not in (0,1,2,3,4,5) and length >= 7 and
                length % 7 == 0 and np.all(e[y+6, x:z] == col)):
                if qframe is None or length > qframe[0]:
                    qframe = (length, x, z-1, y, col)
    ab = _answer_bounds(ENTRY_GRID)
    ay = _answer_y(ENTRY_GRID, ab) if ab is not None else None
    if qframe is None or ab is None or ay is None:
        return False
    qlen, ql, qr, qtop, qcolor = qframe
    acolor = int(e[ay-1, ab[0]])

    # Read every upper example as a left-to-right rewrite rule. Rules may
    # use variable-length sequences and may pass through an intermediate
    # frame colour before reaching the answer colour.
    frames_by_y = {}
    for y in range(0, qtop):
        for x, z, col in runs_at(y):
            length = z - x
            if (col in (0,1,2,3,4,5) or length < 7 or
                    length % 7 != 0 or y + 6 >= qtop or
                    not np.all(e[y+6, x:z] == col)):
                continue
            seq = [e[y+1:y+6, x+1+7*k:x+6+7*k]
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
    if parity is None:
        # On a live level-entry grid this is 0. During backtest the first
        # available before-grid can already be one action past entry.
        parity = 0 if np.array_equal(a, entry) else 1
    out = a.copy()
    info = {"level_up": False, "dead": False, "win": False}
    bounds = _answer_bounds(ENTRY_GRID)

    if action in (3, 4):
        ys, xs = np.where(a == 0)
        if len(xs) and bounds is not None:
            dx = -7 if action == 3 else 7
            nx0, nx1 = int(xs.min()) + dx, int(xs.max()) + dx
            if nx0 >= bounds[0] + 1 and nx1 <= bounds[1] - 1:
                out[ys, xs] = 3
                out[ys, xs + dx] = 0

    if action in (1, 2):
        zy, zx = np.where(a == 0)
        ey = _answer_y(ENTRY_GRID, bounds) if bounds is not None else None
        if len(zx) and ey is not None:
            sx = int(zx.min())
            tile = a[ey:ey+5, sx:sx+5]
            # Canonical cycle arrays use 7 as the blank; render it with this
            # level's answer-frame colour (7 on level 0, 11 on level 1).
            answer_bg = int(entry[ey-1, bounds[0]])
            tile_norm = np.where(tile == 5, 5, 7)
            cycle = _active_cycle()
            found = False
            # Cycling is equivariant under rotations/reflections. Remember
            # each slot's D4 orientation because some glyphs are symmetric
            # and the visible tile alone can then be ambiguous.
            # A slot that starts on a D4-symmetric glyph can hide its true
            # orientation until a later asymmetric state reveals it. Preserve
            # the revealed orientation for level 1's last slot on replay.
            if CURRENT_LEVEL == 1 and sx == bounds[1] - 5:
                slot_orient[sx] = (False, 3)
            candidates = []
            if sx in slot_orient:
                candidates.append(tuple(slot_orient[sx]))
            candidates += [(flip, krot) for flip in (False, True)
                           for krot in range(4)
                           if (flip, krot) not in candidates]
            for flip, krot in candidates:
                for i, known in enumerate(cycle):
                    base = np.fliplr(known) if flip else known
                    shown = np.rot90(base, krot)
                    if np.array_equal(tile_norm, shown):
                        slot_orient[sx] = (flip, krot)
                        j = i + (1 if action == 1 else -1)
                        if 0 <= j < len(cycle):
                            nb = np.fliplr(cycle[j]) if flip else cycle[j]
                            rendered = np.rot90(nb, krot)
                            out[ey:ey+5, sx:sx+5] = np.where(rendered == 5, 5, answer_bg)
                        found = True
                        break
                if found:
                    break
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
    return out.tolist(), info, state
