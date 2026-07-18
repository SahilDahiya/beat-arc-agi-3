"""World model — 'rotated cipher word' game.

Mechanics (confirmed on level 0, generalised for level 1):
 - TOP region (bg 2): DICTIONARY. Each entry = [7x7 box, border = CLUE font colour] ==333==
   [box, border = ANSWER font colour, width 7/14/21...] i.e. one clue letter maps to a
   SEQUENCE of 1..3 answer letters. All glyphs are 5x5, ON = colour 5.
 - BOTTOM region (bg 3): the CLUE word (box bordered with the clue colour, read-only) above the
   ANSWER word (box bordered with the answer colour, editable, N slots).
 - Every glyph on screen is a ROTATED copy of an alphabet letter (identity = min over rotations).
 - A colour-0 bracket cursor selects one answer slot:
      1 = next letter in that font's WHEEL (cyclic, 7 letters), 2 = previous,
      3 = cursor left, 4 = cursor right.
   Slot s renders its wheel letter rotated by a fixed per-slot rotation, derived from the entry grid.
 - GOAL: the answer word = concatenation of the dictionary sequences of the clue letters
   (letter IDENTITIES; the rotation is handled by the slot's fixed rotation) -> level_up.
 - row 63: budget bar, floor(n_actions / 2) cells of colour 4 filling from the right.
"""
import numpy as np

# ---- alphabets: font colour -> the font's 7 letters in WHEEL (cycling) order -------------
W7 = [  # 7-font (colour 7), confirmed by cycling on level 0
    ((1,1,1,1,1),(0,1,0,0,1),(0,1,0,0,1),(0,1,1,1,1),(0,0,0,0,1)),
    ((0,0,1,0,0),(1,1,1,1,1),(1,0,1,0,1),(1,1,1,1,1),(0,0,1,0,0)),
    ((1,1,1,1,0),(1,0,0,1,1),(1,0,0,0,1),(1,1,0,0,1),(0,1,1,1,1)),
    ((0,0,1,0,0),(1,1,1,1,1),(1,0,0,0,1),(1,0,0,0,1),(1,1,1,1,1)),
    ((1,1,1,1,1),(1,0,0,0,1),(1,1,1,1,1),(0,1,0,1,0),(0,1,1,1,0)),
    ((0,0,1,1,1),(0,0,1,0,1),(1,1,1,1,1),(1,0,1,0,0),(1,1,1,0,0)),
    ((1,1,1,1,1),(1,0,1,0,1),(1,0,1,1,1),(1,0,0,0,1),(1,1,1,1,1)),
]
WB = [  # 11-font ('b') — letters AS DISPLAYED AT SLOT 0 (consistent orientation), in wheel order.
    # measured by cycling at slot 0: classes 6 -> 2 -> 5 -> 1 -> 0 -> [?] -> [?] -> wrap
    ((0,1,1,0,1),(1,1,0,0,0),(0,0,0,0,0),(1,1,0,0,0),(0,1,1,0,1)),
    ((1,0,1,1,1),(0,0,1,0,0),(1,0,1,1,1),(0,0,0,0,1),(1,0,1,1,1)),
    ((1,1,1,1,1),(1,0,0,0,1),(0,0,1,0,0),(1,0,0,0,1),(1,1,1,1,1)),
    ((0,1,0,1,0),(0,0,0,0,0),(1,1,1,1,1),(0,0,0,0,0),(0,1,0,1,0)),
    ((1,0,0,0,1),(1,0,0,0,0),(1,1,1,1,1),(0,0,0,0,1),(1,0,0,0,1)),
    ((1,0,0,1,1),(0,0,0,0,1),(1,0,0,0,1),(1,0,0,0,0),(1,1,0,0,1)),  # class 3 — ORIENTATION TBD
    ((1,1,1,1,1),(1,0,0,0,0),(1,0,1,0,1),(1,0,0,0,0),(1,0,1,0,1)),  # class 4 (observed at slot1, krot 0)
]
WHEELS = {7: W7, 11: WB}

ON, BG_TOP, BG = 5, 2, 3


# ------------------------------------------------------------------ glyph helpers
def _g5(G, y, x):
    return tuple(tuple(1 if G[y + i][x + j] == ON else 0 for j in range(5)) for i in range(5))


def _rot(g, k):
    return tuple(map(tuple, np.rot90(np.array(g), k).tolist()))


def _canon(g):
    return min(_rot(g, k) for k in range(4))


def _wheel_index(g, wheel):
    c = _canon(g)
    for j, w in enumerate(wheel):
        if _canon(w) == c:
            return j
    return None


def _krots(g, wheel):
    """ALL rotations k that could render glyph g from its wheel letter (symmetric letters
    leave several possible) — kept as a candidate set and narrowed from later frames."""
    out = []
    for j, w in enumerate(wheel):
        for k in range(4):
            if _rot(w, k) == g and k not in out:
                out.append(k)
    return tuple(out) if out else (0, 1, 2, 3)


# ------------------------------------------------------------------ layout
def _hbox(E, y, x, colour):
    """if a box with this border colour starts at (y,x), return its (h,w)."""
    H, W = E.shape
    if x + 7 > W or y + 7 > H:
        return None
    if not ((E[y, x:x + 7] == colour).all() and (E[y:y + 7, x] == colour).all()):
        return None
    w = 7
    while x + w < W and E[y, x + w] == colour:
        w += 1
    if (E[y + 6, x:x + w] == colour).all() and (E[y:y + 7, x + w - 1] == colour).all():
        return (7, w)
    return None


def layout(E):
    E = np.array(E)
    H, W = E.shape
    rows3 = [y for y in range(H) if (E[y] == BG).sum() > W * 0.6]
    ymid = min(rows3) if rows3 else H // 2

    # dictionary bands in the top region: pairs of boxes (clue box, answer box)
    boxes = []
    seen = set()
    for y in range(ymid - 6):
        for x in range(W - 6):
            for c in range(16):
                if c in (ON, BG_TOP, BG, 0, 1):
                    continue
                hw = _hbox(E, y, x, c)
                if hw and not any(y == by and bx <= x < bx + bw for (by, bx, bw, bc) in boxes):
                    boxes.append((y, x, hw[1], c))
                    seen.add(c)
    boxes.sort()
    clue_c = boxes[0][3]
    ans_c = None
    for b in boxes:
        if b[3] != clue_c:
            ans_c = b[3]
            break
    pairs = []
    for (y, x, w, c) in boxes:
        if c != clue_c:
            continue
        rights = [b for b in boxes if b[0] == y and b[3] == ans_c and b[1] > x]
        if not rights:
            continue
        r = min(rights, key=lambda b: b[1])
        n = (r[2] - 2 + 2) // 7
        pairs.append((_g5(E, y + 1, x + 1),
                      [_g5(E, r[0] + 1, r[1] + 1 + 7 * s) for s in range(n)]))

    # bottom word boxes
    def bbox(colour):
        ys, xs = np.where(E[ymid:] == colour)
        return (int(ys.min()) + ymid, int(ys.max()) + ymid, int(xs.min()), int(xs.max()))
    bc = bbox(clue_c)
    ba = bbox(ans_c)
    nclue = (bc[3] - bc[2] + 1) // 7
    nans = (ba[3] - ba[2] + 1) // 7
    lay = {'clue_c': clue_c, 'ans_c': ans_c, 'pairs': pairs,
           'yc': bc[0] + 1, 'xc': bc[2] + 1, 'nclue': nclue,
           'ya': ba[0] + 1, 'xa': ba[2] + 1, 'nans': nans}
    lay['clue'] = [_g5(E, lay['yc'], lay['xc'] + 7 * s) for s in range(nclue)]
    lay['word'] = [_g5(E, lay['ya'], lay['xa'] + 7 * s) for s in range(nans)]
    return lay


def _targets(lay, aw):
    """expand the clue word through the dictionary -> answer wheel-index sequence.

    Clue letters are matched to dictionary letters by IDENTITY (canonical form over rotations),
    so the clue font needs no wheel of its own."""
    table = {}
    for (L, R) in lay['pairs']:
        table[_canon(L)] = [_wheel_index(g, aw) for g in R]
    out = []
    for g in lay['clue']:
        c = _canon(g)
        if c not in table:
            return None
        out.extend(table[c])
    return out


def init_state(entry_grid=None):
    eg = entry_grid if entry_grid is not None else globals().get('ENTRY_GRID')
    if eg is None:
        return {'ns': 0}
    lay = layout(eg)
    aw = WHEELS.get(lay['ans_c'])
    if aw is None:
        return {'ns': 0}
    st = {'x0': lay['xa'], 'y7': lay['ya'], 'ns': lay['nans'], 'ac': lay['ans_c'], 'n': 0,
          'kc': [_krots(lay['word'][s], aw) for s in range(lay['nans'])],
          'tgt': _targets(lay, aw)}
    st['e_idx'] = [_wheel_index(lay['word'][s], aw) for s in range(lay['nans'])]
    ys, xs = np.where(np.array(eg) == 0)
    st['e_slot'] = int(round((xs.min() - st['x0']) / 7.0)) if len(xs) else 0
    st['slot'] = st['e_slot']
    st['idx'] = list(st['e_idx'])
    return st


# ------------------------------------------------------------------ transition
def _read(grid, st, aw):
    G = np.array(grid)
    ys, xs = np.where(G == 0)
    slot = int(round((xs.min() - st['x0']) / 7.0)) if len(xs) else st['slot']
    idx = [_wheel_index(_g5(grid, st['y7'], st['x0'] + 7 * s), aw) for s in range(st['ns'])]
    bar = int((G[len(grid) - 1] == 4).sum())
    return slot, idx, bar, [(int(a), int(b)) for a, b in zip(ys, xs)]


def predict(state, grid, action, x=None, y=None):
    st = dict(state)
    if not st.get('ns'):
        return [list(r) for r in grid], {'level_up': False, 'dead': False, 'win': False}, st
    aw = WHEELS[st['ac']]
    st['idx'] = list(state['idx'])
    st['kc'] = [tuple(c) for c in state['kc']]
    g = [list(r) for r in grid]
    H, W = len(g), len(g[0])
    info = {'level_up': False, 'dead': False, 'win': False}

    slot, idx, bar, cells = _read(grid, st, aw)
    n = st['n']
    if n == 0 and (idx != st['e_idx'] or slot != st['e_slot']):
        n = 1                      # the framework skips the timeline's first transition
    while n // 2 < bar:
        n += 1
    st['slot'], st['idx'] = slot, idx

    # narrow each slot's rotation from what the live grid actually shows
    for s in range(st['ns']):
        disp = _g5(grid, st['y7'], st['x0'] + 7 * s)
        live = [k for k in range(4) if _rot(aw[idx[s]], k) == disp]
        inter = [k for k in st['kc'][s] if k in live]
        st['kc'][s] = tuple(inter) if inter else tuple(live)

    s = st['slot']
    if action in (1, 2):
        st['idx'][s] = (st['idx'][s] + (1 if action == 1 else -1)) % len(aw)
        pat = _rot(aw[st['idx'][s]], min(st['kc'][s]))
        y0, x0 = st['y7'], st['x0'] + 7 * s
        for i in range(5):
            for j in range(5):
                g[y0 + i][x0 + j] = ON if pat[i][j] else st['ac']
    elif action in (3, 4):
        ns = max(0, s - 1) if action == 3 else min(st['ns'] - 1, s + 1)
        dx = 7 * (ns - s)
        if dx:
            for (cy, cx) in cells:
                g[cy][cx] = BG
            for (cy, cx) in cells:
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
