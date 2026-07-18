"""World model — 'rotated cipher word' game.

ONE mechanism for every level seen so far:

  * TOP region (bg 2): a DICTIONARY.  Entries sit in bands; on a band the boxes pair up
    left->right ([box] ==333== [box]).  A box's BORDER COLOUR is its FONT; a box may hold several
    5x5 glyphs (width 7/14/21 = 1/2/3 letters), so an entry maps a SEQUENCE of letters to a
    SEQUENCE of letters.  Several font pairs may coexist and are CHAINED (level 3: a -> 7 -> b).
  * BOTTOM region (bg 3): the CLUE word (upper box) and the ANSWER word (lower box).
  * GOAL (all levels):  translate(clue word, dictionary) == answer word.

  * A colour-0 bracket cursor selects ONE editable glyph.  Which glyphs are editable depends on
    the level: the ANSWER WORD slots (levels 0-3) or the DICTIONARY glyphs (level 4).  The entry
    grid tells us which — whichever set the cursor starts on.
      1 = next letter in that glyph's FONT wheel, 2 = previous, 3/4 = cursor prev/next.
  * Every glyph is a ROTATED copy of an alphabet letter; identity = canonical form over the 4
    rotations.  Each editable position renders its letter with a FIXED, ARBITRARY rotation, kept
    as a candidate set ('kc') and narrowed from the live grid.
  * row 63 = budget bar: floor(n_actions / 2) cells of colour 4, filling from the right.
"""
import numpy as np

# ---- alphabets: font colour -> that font's 7 letters, in WHEEL (cycling) order --------------
# stored AS DISPLAYED AT THE SLOT WHERE THEY WERE MEASURED (a consistent orientation per font)
W7 = [
    ((1,1,1,1,1),(0,1,0,0,1),(0,1,0,0,1),(0,1,1,1,1),(0,0,0,0,1)),
    ((0,0,1,0,0),(1,1,1,1,1),(1,0,1,0,1),(1,1,1,1,1),(0,0,1,0,0)),
    ((1,1,1,1,0),(1,0,0,1,1),(1,0,0,0,1),(1,1,0,0,1),(0,1,1,1,1)),
    ((0,0,1,0,0),(1,1,1,1,1),(1,0,0,0,1),(1,0,0,0,1),(1,1,1,1,1)),
    ((1,1,1,1,1),(1,0,0,0,1),(1,1,1,1,1),(0,1,0,1,0),(0,1,1,1,0)),
    ((0,0,1,1,1),(0,0,1,0,1),(1,1,1,1,1),(1,0,1,0,0),(1,1,1,0,0)),
    ((1,1,1,1,1),(1,0,1,0,1),(1,0,1,1,1),(1,0,0,0,1),(1,1,1,1,1)),
]
WB = [
    ((0,1,1,0,1),(1,1,0,0,0),(0,0,0,0,0),(1,1,0,0,0),(0,1,1,0,1)),
    ((1,0,1,1,1),(0,0,1,0,0),(1,0,1,1,1),(0,0,0,0,1),(1,0,1,1,1)),
    ((1,1,1,1,1),(1,0,0,0,1),(0,0,1,0,0),(1,0,0,0,1),(1,1,1,1,1)),
    ((0,1,0,1,0),(0,0,0,0,0),(1,1,1,1,1),(0,0,0,0,0),(0,1,0,1,0)),
    ((1,0,0,0,1),(1,0,0,0,0),(1,1,1,1,1),(0,0,0,0,1),(1,0,0,0,1)),
    ((1,0,0,1,1),(0,0,0,0,1),(1,0,0,0,1),(1,0,0,0,0),(1,1,0,0,1)),
    ((1,1,1,1,1),(1,0,0,0,0),(1,0,1,0,1),(1,0,0,0,0),(1,0,1,0,1)),
]
WA = [
    ((1,0,0,0,1),(1,0,0,0,1),(1,1,0,1,1),(1,0,0,0,1),(1,1,1,1,1)),
    ((1,1,1,0,0),(0,0,1,0,0),(0,1,1,1,0),(0,0,1,0,0),(0,0,1,1,1)),
    ((0,0,0,0,1),(0,0,1,0,1),(1,1,1,1,1),(0,0,1,0,1),(0,0,0,0,1)),
    ((1,1,1,1,1),(0,1,0,0,1),(0,1,0,0,0),(0,1,0,0,1),(1,1,1,1,1)),
    ((1,0,0,0,1),(1,0,0,0,1),(1,1,1,0,1),(1,0,1,0,1),(1,0,1,1,1)),
    ((1,1,0,1,1),(0,1,0,1,0),(0,1,1,1,0),(0,1,0,1,0),(1,1,0,1,1)),
    ((0,1,1,1,0),(0,1,0,0,0),(1,1,1,1,1),(0,1,0,0,0),(0,1,1,1,0)),
]
WHEELS = {7: W7, 11: WB, 10: WA}

ON, BG_TOP, BG = 5, 2, 3   # glyph-on colour; top / bottom background (bar scale K is per level)
# NOTE: in dictionary mode the editable unit is a whole BOX. All glyphs in the box CYCLE TOGETHER,
# each keeping a fixed OFFSET from the box's base letter (level 4: offsets 0 -> identical letters;
# level 5: non-zero offsets) and its own fixed display rotation.


# ------------------------------------------------------------------ glyph helpers
def _g5(G, y, x):
    return tuple(tuple(1 if G[y + i][x + j] == ON else 0 for j in range(5)) for i in range(5))


def _rot(g, k):
    return tuple(map(tuple, np.rot90(np.array(g), k).tolist()))


def _canon(g):
    return min(_rot(g, k) for k in range(4))


def _widx(g, wheel):
    c = _canon(g)
    for j, w in enumerate(wheel):
        if _canon(w) == c:
            return j
    return None


def _krots(g, wheel):
    out = []
    for w in wheel:
        for k in range(4):
            if _rot(w, k) == g and k not in out:
                out.append(k)
    return tuple(out) if out else (0, 1, 2, 3)


def _hbox(E, y, x, colour):
    H, W = E.shape
    if x + 7 > W or y + 7 > H:
        return None
    if not ((E[y, x:x + 7] == colour).all() and (E[y:y + 7, x] == colour).all()):
        return None
    w = 7
    while x + w < W and E[y, x + w] == colour:
        w += 1
    if (E[y + 6, x:x + w] == colour).all() and (E[y:y + 7, x + w - 1] == colour).all():
        return w
    return None


# ------------------------------------------------------------------ static layout
def layout(E):
    E = np.array(E)
    H, W = E.shape
    rows3 = [y for y in range(H) if (E[y] == BG).sum() > W * 0.6]
    ymid = min(rows3) if rows3 else H // 2

    boxes = []
    for y in range(ymid - 6):
        for x in range(W - 6):
            for c in range(16):
                if c in (ON, BG_TOP, BG, 0, 1):
                    continue
                w = _hbox(E, y, x, c)
                if w and not any(y == by and bx <= x < bx + bw for (by, bx, bw, bc) in boxes):
                    boxes.append((y, x, w, c))
    boxes.sort()
    bands = {}
    for b in boxes:
        bands.setdefault(b[0], []).append(b)

    entries = []          # (font_from, font_to, [left glyph positions], [right glyph positions])
    dict_boxes = []       # one entry per BOX (the editable unit in dictionary mode)
    for y in sorted(bands):
        row = sorted(bands[y], key=lambda b: b[1])
        for i in range(0, len(row) - 1, 2):
            (ly, lx, lw, lc) = row[i]
            (ry, rx, rw, rc) = row[i + 1]
            L = [(ly + 1, lx + 1 + 7 * s, lc, ly, ly + 6, 1) for s in range(lw // 7)]
            R = [(ry + 1, rx + 1 + 7 * s, rc, ry, ry + 6, 1) for s in range(rw // 7)]
            entries.append((lc, rc, L, R))
            # an editable dictionary BOX is one position: all its glyphs cycle together
            dict_boxes.append((ly + 1, lx + 1, lc, ly, ly + 6, lw // 7))
            dict_boxes.append((ry + 1, rx + 1, rc, ry, ry + 6, rw // 7))

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
    lay = {'entries': entries, 'clue_c': clue_c, 'ans_c': ans_c,
           'clue': [(cy0 + 1, cx0 + 1 + 7 * s) for s in range((cx1 - cx0 + 1) // 7)],
           'word': [(ay0 + 1, ax0 + 1 + 7 * s, ans_c, ay0, ay1, 1)
                    for s in range((ax1 - ax0 + 1) // 7)]}
    # the two candidate editable sets: the answer-word slots, or the dictionary boxes
    dict_boxes.sort(key=lambda p: (p[0], p[1]))
    lay['sets'] = {'word': lay['word'], 'dict': dict_boxes}
    return lay


def _cursor_cells(p):
    """bracket cells for editable position p = (gy, gx, colour, by0, by1, nglyphs);
    the bracket spans the whole box content (5 cells per glyph, pitch 7)."""
    (gy, gx, c, by0, by1, k) = p
    w = 7 * (k - 1) + 5
    cells = [(by0 - 3, gx + i) for i in range(w)] + [(by0 - 2, gx), (by0 - 2, gx + w - 1)] \
        + [(by1 + 2, gx), (by1 + 2, gx + w - 1)] + [(by1 + 3, gx + i) for i in range(w)]
    return cells


def _read_dict(grid, lay):
    out = []
    for (lc, rc, L, R) in lay['entries']:
        out.append((lc, rc,
                    [_canon(_g5(grid, p[0], p[1])) for p in L],
                    [_canon(_g5(grid, p[0], p[1])) for p in R]))
    return out


def _expand(seq, entries):
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


def _translate(grid, lay):
    """translate the clue word through the (current) dictionary chain; None if impossible"""
    dicts = {}
    for (lc, rc, L, R) in _read_dict(grid, lay):
        dicts.setdefault((lc, rc), []).append((L, R))
    prev, frontier = {lay['clue_c']: None}, [lay['clue_c']]
    while frontier and lay['ans_c'] not in prev:
        nxt = []
        for f in frontier:
            for (fc, tc) in dicts:
                if fc == f and tc not in prev:
                    prev[tc] = (f, (fc, tc))
                    nxt.append(tc)
        frontier = nxt
    if lay['ans_c'] not in prev:
        return None
    chain, cur = [], lay['ans_c']
    while prev[cur] is not None:
        f, key = prev[cur]
        chain.append(key)
        cur = f
    chain.reverse()
    seq = [_canon(_g5(grid, y, x)) for (y, x) in lay['clue']]
    for key in chain:
        seq = _expand(seq, dicts[key])
        if seq is None:
            return None
    return seq


def _answer(grid, lay):
    return [_canon(_g5(grid, p[0], p[1])) for p in lay['word']]


# ------------------------------------------------------------------ state
def init_state(entry_grid=None):
    eg = entry_grid if entry_grid is not None else ENTRY_GRID
    if eg is None:
        return {'np': 0}
    lay = layout(eg)
    E = np.array(eg)
    ys, xs = np.where(E == 0)
    cy, cx = int(ys.min()), int(xs.min())
    # which editable set does the cursor start on?
    best, bestd = None, None
    for name, ps in lay['sets'].items():
        for i, p in enumerate(ps):
            d = abs(p[1] - cx) + abs(p[3] - 3 - cy)
            if bestd is None or d < bestd:
                bestd, best = d, (name, i)
    mode, slot = best
    ps = lay['sets'][mode]
    st = {'lay_mode': mode, 'np': len(ps), 'slot': slot, 'n': 0,
          'pos': [tuple(p) for p in ps], 'lay': lay,
          'idx': [], 'kc': []}
    st['off'] = []
    for p in ps:
        wh = WHEELS.get(p[2], W7)
        base = _widx(_g5(eg, p[0], p[1]), wh)
        st['idx'].append(base)
        # each glyph inside the box has its OWN fixed display rotation ...
        st['kc'].append([_krots(_g5(eg, p[0], p[1] + 7 * b), wh) for b in range(p[5])])
        # ... and its own fixed OFFSET from the box's base letter: the whole box cycles together
        offs = []
        for b in range(p[5]):
            jb = _widx(_g5(eg, p[0], p[1] + 7 * b), wh)
            offs.append(0 if (jb is None or base is None) else (jb - base) % len(wh))
        st['off'].append(offs)
    st['e_idx'] = list(st['idx'])
    st['e_slot'] = slot
    # budget bar: one colour-4 cell per K actions.  K = 2 on levels 0-4; level 5's bar is slower
    # (no cell after 3 actions) -> its action budget is larger.
    lv = CURRENT_LEVEL
    st['K'] = 2 if (lv is None or lv < 5) else 4
    return st


def _read(grid, st):
    G = np.array(grid)
    ys, xs = np.where(G == 0)
    slot = st['slot']
    if len(xs):
        cx, cy = int(xs.min()), int(ys.min())
        bd = None
        for i, p in enumerate(st['pos']):
            d = abs(p[1] - cx) + abs(p[3] - 3 - cy)
            if bd is None or d < bd:
                bd, slot = d, i
    idx, kc = [], []
    for i, p in enumerate(st['pos']):
        wh = WHEELS.get(p[2], W7)
        j = _widx(_g5(grid, p[0], p[1]), wh)
        idx.append(j)
        rots = []
        for b in range(p[5]):
            g = _g5(grid, p[0], p[1] + 7 * b)
            jb = None if j is None else (j + st['off'][i][b]) % len(wh)
            live = [k for k in range(4) if jb is not None and _rot(wh[jb], k) == g]
            keep = [k for k in st['kc'][i][b] if k in live]
            rots.append(tuple(keep) if keep else (tuple(live) if live else st['kc'][i][b]))
        kc.append(rots)
    bar = int((G[len(grid) - 1] == 4).sum())
    return slot, idx, kc, bar


def predict(state, grid, action, x=None, y=None):
    st = dict(state)
    if not st.get('np'):
        return [list(r) for r in grid], {'level_up': False, 'dead': False, 'win': False}, st
    g = [list(r) for r in grid]
    H, W = len(g), len(g[0])
    info = {'level_up': False, 'dead': False, 'win': False}

    slot, idx, kc, bar = _read(grid, st)
    n = st['n']
    if n == 0 and (idx != st['e_idx'] or slot != st['e_slot']):
        n = 1                       # the framework skips the timeline's first transition
    K = st.get('K', 2)
    while n // K < bar:
        n += 1
    st['slot'], st['idx'], st['kc'] = slot, list(idx), [list(r) for r in kc]

    s = st['slot']
    p = st['pos'][s]
    wh = WHEELS.get(p[2], W7)
    if action in (1, 2):
        st['idx'][s] = (st['idx'][s] + (1 if action == 1 else -1)) % len(wh)
        for b in range(p[5]):
            jb = (st['idx'][s] + st['off'][s][b]) % len(wh)
            pat = _rot(wh[jb], min(st['kc'][s][b]))
            for i in range(5):
                for j in range(5):
                    g[p[0] + i][p[1] + 7 * b + j] = ON if pat[i][j] else p[2]
    elif action in (3, 4):
        ns = max(0, s - 1) if action == 3 else min(st['np'] - 1, s + 1)
        if ns != s:
            bg = BG if p[3] > 34 else BG_TOP
            for (cy, cx) in _cursor_cells(p):
                g[cy][cx] = bg
            q = st['pos'][ns]
            for (cy, cx) in _cursor_cells(q):
                g[cy][cx] = 0
            st['slot'] = ns

    n += 1
    st['n'] = n
    k = n // K
    for xx in range(W):
        g[H - 1][xx] = 4 if xx >= W - k else 1

    lay = st['lay']
    t = _translate(g, lay)
    if t is not None and t == _answer(g, lay):
        info['level_up'] = True
    return g, info, st


def is_goal(state, grid):
    if not state or not state.get('np'):
        return False
    lay = state['lay']
    t = _translate(grid, lay)
    return t is not None and t == _answer(grid, lay)
