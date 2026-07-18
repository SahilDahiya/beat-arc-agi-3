"""World model — 'rotated cipher word' game.

Confirmed mechanics (level 0):
 - Top region: 6 dictionary pairs  [a-font glyph] ==333== [7-font glyph]  (5x5 glyphs, ON=colour 5).
 - Bottom: an a-font WORD (fixed clue) above a 7-font WORD (editable, 5 slots).
 - Every word letter is a ROTATED copy of a dictionary letter.
 - A cursor (colour-0 corner brackets) selects one slot of the 7-word:
      action 1 = next letter in the global 7-letter WHEEL, 2 = previous,
      action 3 = cursor left, 4 = cursor right.
 - Slot s renders the wheel letter rotated by a fixed per-slot rotation KROT[s]
   (derived from the entry grid).
 - GOAL: every slot shows the dict-7 partner of the a-letter above it  -> level up.
 - row 63 = budget bar: floor(n_actions / 2) cells of colour 4, filling from the right.

State is re-derived from the grid every step (robust to the framework skipping the
very first transition when rolling state forward).
"""
import numpy as np

# global 7-letter wheel of the 7-font alphabet (cyclic order; canonical = as slot 0 shows it)
WHEEL = [
    ((1,1,1,1,1),(0,1,0,0,1),(0,1,0,0,1),(0,1,1,1,1),(0,0,0,0,1)),  # 0
    ((0,0,1,0,0),(1,1,1,1,1),(1,0,1,0,1),(1,1,1,1,1),(0,0,1,0,0)),  # 1
    ((1,1,1,1,0),(1,0,0,1,1),(1,0,0,0,1),(1,1,0,0,1),(0,1,1,1,1)),  # 2
    ((0,0,1,0,0),(1,1,1,1,1),(1,0,0,0,1),(1,0,0,0,1),(1,1,1,1,1)),  # 3
    ((1,1,1,1,1),(1,0,0,0,1),(1,1,1,1,1),(0,1,0,1,0),(0,1,1,1,0)),  # 4
    ((0,0,1,1,1),(0,0,1,0,1),(1,1,1,1,1),(1,0,1,0,0),(1,1,1,0,0)),  # 5
    ((1,1,1,1,1),(1,0,1,0,1),(1,0,1,1,1),(1,0,0,0,1),(1,1,1,1,1)),  # 6
]

ON, CA, C7, BG = 5, 10, 7, 3
NW = len(WHEEL)


# ------------------------------------------------------------------ helpers
def _g5(G, y, x, on=ON):
    return tuple(tuple(1 if G[y + i][x + j] == on else 0 for j in range(5)) for i in range(5))


def _rot(g, k):
    return tuple(map(tuple, np.rot90(np.array(g), k).tolist()))


def _bbox(E, colour, y0, y1):
    ys, xs = np.where(np.array(E)[y0:y1] == colour)
    if len(ys) == 0:
        return None
    return (int(ys.min()) + y0, int(ys.max()) + y0, int(xs.min()), int(xs.max()))


def layout(E):
    """Static layout of the level, from its entry grid."""
    E = np.array(E)
    H, W = E.shape
    rows3 = [y for y in range(H) if (E[y] == BG).sum() > W * 0.6]
    ymid = min(rows3) if rows3 else H // 2

    b7 = _bbox(E, C7, ymid, H)
    ba = _bbox(E, CA, ymid, H)
    lay = {'y7': b7[0] + 1, 'ya': ba[0] + 1, 'x0': b7[2] + 1,
           'n': (b7[3] - b7[2] + 1) // 7}
    top = E[:ymid]
    pairs = []
    for y in range(top.shape[0] - 6):
        for x in range(W - 6):
            if (top[y, x:x + 7] == CA).all() and (top[y + 6, x:x + 7] == CA).all() \
               and (top[y:y + 7, x] == CA).all() and (top[y:y + 7, x + 6] == CA).all():
                for x2 in range(x + 7, W - 6):
                    if (top[y, x2:x2 + 7] == C7).all() and (top[y + 6, x2:x2 + 7] == C7).all() \
                       and (top[y:y + 7, x2] == C7).all() and (top[y:y + 7, x2 + 6] == C7).all():
                        pairs.append((_g5(top, y + 1, x + 1), _g5(top, y + 1, x2 + 1)))
                        break
    lay['pairs'] = pairs
    lay['wordA'] = [_g5(E, lay['ya'], lay['x0'] + 7 * s) for s in range(lay['n'])]
    lay['word7'] = [_g5(E, lay['y7'], lay['x0'] + 7 * s) for s in range(lay['n'])]
    # per-slot display rotation, from the entry glyphs
    krot = []
    for s in range(lay['n']):
        g = lay['word7'][s]
        k_found = 0
        for k in range(4):
            if any(_rot(c, k) == g for c in WHEEL):
                k_found = k
                break
        krot.append(k_found)
    lay['krot'] = krot
    return lay


def _idx_of(g, k):
    """wheel index of a displayed glyph g at a slot with rotation k."""
    for j, c in enumerate(WHEEL):
        if _rot(c, k) == g:
            return j
    return None


def _read(grid, st):
    """derive (cursor slot, letter indices, bar count) from the live grid."""
    G = np.array(grid)
    ys, xs = np.where(G == 0)
    slot = int(round((xs.min() - st['x0']) / 7.0)) if len(xs) else st['slot']
    idx = [_idx_of(_g5(grid, st['y7'], st['x0'] + 7 * s), st['krot'][s]) for s in range(st['ns'])]
    bar = int((G[len(grid) - 1] == 4).sum())
    return slot, idx, bar, [(int(a), int(b)) for a, b in zip(ys, xs)]


def _targets(lay):
    """target wheel index per slot = dict-7 partner of the (rotated) a-letter above it."""
    tg = []
    for s in range(lay['n']):
        wa = np.array(lay['wordA'][s])
        acc = set()
        for (A, B) in lay['pairs']:
            for k in range(4):
                for f in (0, 1):
                    X, Y = np.rot90(np.array(A), k), np.rot90(np.array(B), k)
                    if f:
                        X, Y = np.fliplr(X), np.fliplr(Y)
                    if (X == wa).all():
                        acc.add(tuple(map(tuple, Y.tolist())))
        hit = None
        for j, c in enumerate(WHEEL):
            for k in range(4):
                for f in (0, 1):
                    Y = np.rot90(np.array(c), k)
                    if f:
                        Y = np.fliplr(Y)
                    if tuple(map(tuple, Y.tolist())) in acc:
                        hit = j
        tg.append(hit)
    return tg


def init_state(entry_grid=None):
    eg = entry_grid if entry_grid is not None else globals().get('ENTRY_GRID')
    if eg is None:
        return {'ns': 0}
    lay = layout(eg)
    st = {'x0': lay['x0'], 'y7': lay['y7'], 'ns': lay['n'], 'krot': lay['krot'],
          'tgt': _targets(lay), 'n': 0}
    st['e_idx'] = [_idx_of(lay['word7'][s], lay['krot'][s]) for s in range(lay['n'])]
    ys, xs = np.where(np.array(eg) == 0)
    st['e_slot'] = int(round((xs.min() - lay['x0']) / 7.0)) if len(xs) else 0
    st['slot'] = st['e_slot']
    st['idx'] = list(st['e_idx'])
    return st


# ------------------------------------------------------------------ transition
def predict(state, grid, action, x=None, y=None):
    st = dict(state)
    if not st.get('ns'):
        return [list(r) for r in grid], {'level_up': False, 'dead': False, 'win': False}, st
    st['idx'] = list(state['idx'])
    g = [list(r) for r in grid]
    H, W = len(g), len(g[0])
    info = {'level_up': False, 'dead': False, 'win': False}

    # --- re-derive live state from the grid (self-correcting) ---
    slot, idx, bar, cur_cells = _read(grid, st)
    n = st['n']
    if n == 0 and (idx != st['e_idx'] or slot != st['e_slot']):
        n = 1                      # an action happened that our state never saw
    while n // 2 < bar:
        n += 1
    st['slot'], st['idx'] = slot, idx

    s = st['slot']
    if action in (1, 2):
        st['idx'][s] = (st['idx'][s] + (1 if action == 1 else -1)) % NW
        pat = _rot(WHEEL[st['idx'][s]], st['krot'][s])
        y0, x0 = st['y7'], st['x0'] + 7 * s
        for i in range(5):
            for j in range(5):
                g[y0 + i][x0 + j] = ON if pat[i][j] else C7
    elif action in (3, 4):
        ns = max(0, s - 1) if action == 3 else min(st['ns'] - 1, s + 1)
        dx = 7 * (ns - s)
        if dx:
            for (cy, cx) in cur_cells:
                g[cy][cx] = BG
            for (cy, cx) in cur_cells:
                g[cy][cx + dx] = 0
        st['slot'] = ns

    n += 1
    st['n'] = n
    k = n // 2
    for xx in range(W):
        g[H - 1][xx] = 4 if xx >= W - k else 1

    if st['idx'] == st['tgt']:
        info['level_up'] = True
    return g, info, st


def is_goal(state, grid):
    if not state or not state.get('ns'):
        return False
    return state['idx'] == state['tgt']
