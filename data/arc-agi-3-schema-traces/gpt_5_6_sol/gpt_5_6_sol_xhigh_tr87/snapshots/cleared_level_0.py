import numpy as np

def init_state(entry_grid):
    # None lets the first predicted step infer whether one unscored action
    # already preceded the supplied grid (as happens in history replay).
    return {"action_parity": None, "slot_orient": {}}

def _answer_bounds(entry):
    a = np.array(entry)
    h, w = a.shape
    best = None
    # The editable answer is the widest horizontal run of 7 in the lower half.
    for y in range(h // 2, h):
        x = 0
        while x < w:
            if a[y, x] != 7:
                x += 1
                continue
            z = x
            while z < w and a[y, z] == 7:
                z += 1
            if best is None or z - x > best[0]:
                best = (z - x, x, z - 1, y)
            x = z
    return None if best is None else (best[1], best[2])

def _answer_y(entry, bounds):
    a = np.array(entry)
    for y in range(a.shape[0] // 2, a.shape[0]):
        if np.all(a[y, bounds[0]:bounds[1]+1] == 7):
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
    """Match each lower query glyph to a top source (up to D4), then
    require the corresponding top output class in the answer slot."""
    e = np.array(ENTRY_GRID)
    g = np.array(grid)
    h, w = e.shape
    src_boxes, out_boxes = [], []
    for color, dest in ((10, src_boxes), (7, out_boxes)):
        for yy in range(0, h // 2 - 6):
            for xx in range(0, w - 6):
                if ((xx == 0 or e[yy, xx-1] != color) and
                    (xx + 7 == w or e[yy, xx+7] != color) and
                    np.all(e[yy, xx:xx+7] == color) and
                    np.all(e[yy+6, xx:xx+7] == color)):
                    dest.append((xx, yy))
    pairs = []
    for sx, sy in src_boxes:
        choices = [(ox, oy) for ox, oy in out_boxes if oy == sy and ox > sx]
        if choices:
            ox, oy = min(choices, key=lambda p: p[0])
            pairs.append((e[sy+1:sy+6, sx+1:sx+6],
                          e[oy+1:oy+6, ox+1:ox+6]))
    # Widest lower-half aqua run is the query frame.
    best = None
    for yy in range(h // 2, h):
        xx = 0
        while xx < w:
            if e[yy, xx] != 10:
                xx += 1; continue
            zz = xx
            while zz < w and e[yy, zz] == 10:
                zz += 1
            if best is None or zz-xx > best[0]:
                best = (zz-xx, xx, zz-1, yy)
            xx = zz
    ab = _answer_bounds(ENTRY_GRID)
    ay = _answer_y(ENTRY_GRID, ab) if ab is not None else None
    if not pairs or best is None or ab is None or ay is None:
        return False
    _, ql, qr, qtop = best
    starts = list(range(ql+1, qr-3, 7))
    if not starts:
        return False
    for xq in starts:
        query = e[qtop+1:qtop+6, xq:xq+5]
        answer = g[ay:ay+5, ab[0]+1+(xq-(ql+1)):ab[0]+1+(xq-(ql+1))+5]
        matched = False
        for source, target in pairs:
            if _d4_equal(source, query):
                if not _d4_equal(target, answer):
                    return False
                matched = True
                break
        if not matched:
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
            found = False
            # Cycling is equivariant under rotations/reflections. Remember
            # each slot's D4 orientation because some glyphs are symmetric
            # and the visible tile alone can then be ambiguous.
            candidates = []
            if sx in slot_orient:
                candidates.append(tuple(slot_orient[sx]))
            candidates += [(flip, krot) for flip in (False, True)
                           for krot in range(4)
                           if (flip, krot) not in candidates]
            for flip, krot in candidates:
                for i, known in enumerate(CYCLE):
                    base = np.fliplr(known) if flip else known
                    shown = np.rot90(base, krot)
                    if np.array_equal(tile, shown):
                        slot_orient[sx] = (flip, krot)
                        j = i + (1 if action == 1 else -1)
                        if 0 <= j < len(CYCLE):
                            nb = np.fliplr(CYCLE[j]) if flip else CYCLE[j]
                            out[ey:ey+5, sx:sx+5] = np.rot90(nb, krot)
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
