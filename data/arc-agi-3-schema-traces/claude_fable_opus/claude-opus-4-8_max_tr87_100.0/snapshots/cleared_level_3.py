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

# Dictionaries may CHAIN across fonts (level 3: clue 'a' -> '7' -> answer 'b').
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
WA = [  # 10-font ('a') — letters AS DISPLAYED AT SLOT 0, in wheel order (measured on level 2)
    ((1,0,0,0,1),(1,0,0,0,1),(1,1,0,1,1),(1,0,0,0,1),(1,1,1,1,1)),
    ((1,1,1,0,0),(0,0,1,0,0),(0,1,1,1,0),(0,0,1,0,0),(0,0,1,1,1)),
    ((0,0,0,0,1),(0,0,1,0,1),(1,1,1,1,1),(0,0,1,0,1),(0,0,0,0,1)),
    ((1,1,1,1,1),(0,1,0,0,1),(0,1,0,0,0),(0,1,0,0,1),(1,1,1,1,1)),
    ((1,0,0,0,1),(1,0,0,0,1),(1,1,1,0,1),(1,0,1,0,1),(1,0,1,1,1)),
    ((1,1,0,1,1),(0,1,0,1,0),(0,1,1,1,0),(0,1,0,1,0),(1,1,0,1,1)),
    ((0,1,1,1,0),(0,1,0,0,0),(1,1,1,1,1),(0,1,0,0,0),(0,1,1,1,0)),
]
WHEELS = {7: W7, 11: WB, 10: WA}

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

    # ---- dictionary boxes in the TOP region ----
    boxes = []
    for y in range(ymid - 6):
        for x in range(W - 6):
            for c in range(16):
                if c in (ON, BG_TOP, BG, 0, 1):
                    continue
                hw = _hbox(E, y, x, c)
                if hw and not any(y == by and bx <= x < bx + bw for (by, bx, bw, bc) in boxes):
                    boxes.append((y, x, hw[1], c))
    boxes.sort()
    bands = {}
    for b in boxes:
        bands.setdefault(b[0], []).append(b)
    dicts = {}
    for y in sorted(bands):
        row = sorted(bands[y], key=lambda b: b[1])
        for i in range(0, len(row) - 1, 2):
            (ly, lx, lw, lc) = row[i]
            (ry, rx, rw, rc) = row[i + 1]
            L = [_g5(E, ly + 1, lx + 1 + 7 * s) for s in range((lw - 2 + 2) // 7)]
            R = [_g5(E, ry + 1, rx + 1 + 7 * s) for s in range((rw - 2 + 2) // 7)]
            dicts.setdefault((lc, rc), []).append((L, R))

    # ---- the two word boxes in the BOTTOM region ----
    wb = []
    for c in range(16):
        if c in (ON, BG_TOP, BG, 0, 1):
            continue
        ys, xs = np.where(E[ymid:] == c)
        if len(ys):
            wb.append((int(ys.min()) + ymid, int(ys.max()) + ymid, int(xs.min()), int(xs.max()), c))
    wb.sort()
    (cy0, cy1, cx0, cx1, clue_c) = wb[0]
    (ay0, ay1, ax0, ax1, ans_c) = wb[1]
    lay = {'clue_c': clue_c, 'ans_c': ans_c, 'dicts': dicts,
           'yc': cy0 + 1, 'xc': cx0 + 1, 'nclue': (cx1 - cx0 + 1) // 7,
           'ya': ay0 + 1, 'xa': ax0 + 1, 'nans': (ax1 - ax0 + 1) // 7}
    lay['clue'] = [_g5(E, lay['yc'], lay['xc'] + 7 * s) for s in range(lay['nclue'])]
    lay['word'] = [_g5(E, lay['ya'], lay['xa'] + 7 * s) for s in range(lay['nans'])]
    return lay


def _expand(seq, entries):
    """segment `seq` (canonical letters) into dictionary entries and concatenate their outputs"""
    n = len(seq)
    best = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for (L, R) in entries:
            j = i + len(L)
            if j <= n and seq[i:j] == L and best[j] is None:
                best[j] = best[i] + R
    return best[n]


def _targets(lay, aw):
    """Translate the clue word into answer-font wheel indices, following a CHAIN of dictionaries
    (e.g. level 3: clue font 'a' -> font '7' -> answer font 'b').  Letters are matched by IDENTITY
    (canonical form over rotations); each dictionary entry maps a SEQUENCE to a SEQUENCE."""
    cdicts = {}
    for (fc, tc), ents in lay['dicts'].items():
        cdicts[(fc, tc)] = [([_canon(g) for g in L], [_canon(g) for g in R]) for (L, R) in ents]
    # shortest chain of fonts from the clue font to the answer font
    prev, frontier = {lay['clue_c']: None}, [lay['clue_c']]
    while frontier and lay['ans_c'] not in prev:
        nxt = []
        for f in frontier:
            for (fc, tc) in cdicts:
                if fc == f and tc not in prev:
                    prev[tc] = (f, (fc, tc))
                    nxt.append(tc)
        frontier = nxt
    if lay['ans_c'] not in prev:
        return None
    chain = []
    cur = lay['ans_c']
    while prev[cur] is not None:
        f, key = prev[cur]
        chain.append(key)
        cur = f
    chain.reverse()

    seq = [_canon(g) for g in lay['clue']]
    for key in chain:
        seq = _expand(seq, cdicts[key])
        if seq is None:
            return None
    out = []
    for c in seq:
        j = None
        for i, w in enumerate(aw):
            if _canon(w) == c:
                j = i
        out.append(j)
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
