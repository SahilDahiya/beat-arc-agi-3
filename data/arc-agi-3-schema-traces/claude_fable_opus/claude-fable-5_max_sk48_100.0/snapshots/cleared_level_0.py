# sk48 world model — "crane & train" (Level 0)
# Panel rows12-41 cols17-46 (color 4). Track cols13-14 rows14-39 (2,2,3,3,3,3 from row14).
# Engine 6x6 box cols11-16, top in {12,18,24,30,36} (6-row slots). Rope at rows top+2,
# top+3 from col16, length L in {1,7,13,19,25,31}, twisted 1/2 texture, renders UNDER blocks.
# Blocks 4x4 (colors 8,9,e): entry wall slots cols42-45 at rows19-22 / 25-28 / 31-34.
# MECHANIC (skewer-couple, partially confirmed):
#   - a1/a2: engine up/down 6 (clamp top 12..36); riding blocks move vertically too.
#   - a3/a4: rope -6/+6 (clamp L 1..31). Riding block = row-aligned (r0==top+1) and
#     c0 <= tip. Riding blocks move with rope, clamped: left >= col18 (1 gap to engine),
#     >= 2 cells from neighbor block; right c0 <= 42 (wall slot).
#   - Fresh wall block doesn't move while rope slides through; once tip >= its c0 it rides.
#   - Budget bar row53: rightmost k cells '3', k = floor(rope_actions/3) [hyp A; alt: T-based].
# CONFIRMED by history: a1 up; a3 retract w/ drag (e rode 42-45 -> 36-39); a4 extend
#   (block stayed while rope passed through); rope-under-block render; bar flips at ra=3,6.
# UNTESTED: a2, extend-carry, vertical-carry, collision clamps, a6, a7, goal detection.
# GOAL (hyp): assemble train per bottom picture rows54-63: from engine: gap1, 8, gap2, e,
#   gap2, 9, tip -> i.e. 8 at cols18-21, e 24-27, 9 30-33, tip 34 (L=19), hook order 8,e,9.

TRACK_C0, TRACK_C1 = 13, 14
TRACK_R0, TRACK_R1 = 14, 39
PAN_R0, PAN_R1 = 12, 41
PAN_C0, PAN_C1 = 17, 46
ENG_C0, ENG_C1 = 11, 16
TOP_MIN, TOP_MAX = 12, 36
L_MIN, L_MAX = 1, 31
BLK_CMIN, BLK_CMAX = 18, 42   # block c0 clamps (left: engine gap; right: wall slot)

ROPE_TEX = [(1, 2), (2, 1), (1, 1)]
BLOCK_COLORS = (8, 9, 14)


def init_state(entry_grid):
    return {'acts': 0, 'ra': 0, 'synced': False}


def grids_equal(a, b):
    if a is None or b is None:
        return False
    for r in range(len(a)):
        ra_, rb = a[r], b[r]
        for c in range(len(ra_)):
            if ra_[c] != rb[c]:
                return False
    return True


def bg_color(r, c):
    if PAN_R0 <= r <= PAN_R1 and PAN_C0 <= c <= PAN_C1:
        return 4
    if c in (TRACK_C0, TRACK_C1) and TRACK_R0 <= r <= TRACK_R1:
        return 2 if (r - TRACK_R0) % 6 in (0, 1) else 3
    return 5


def find_engine_top(g):
    for r in range(64):
        if g[r][ENG_C0] == 6 and g[r][ENG_C0 + 1] == 6 and g[r][ENG_C0 + 2] == 6:
            return r
    return None


def rope_len(g, top):
    r = top + 2
    last = ENG_C1 - 1
    for c in range(ENG_C1, 64):
        v = g[r][c]
        if v in (1, 2):
            last = c
        elif v in BLOCK_COLORS:
            continue
        else:
            break
    return last - ENG_C1 + 1


def find_blocks(g):
    out = {}
    for v in BLOCK_COLORS:
        cells = [(r, c) for r in range(PAN_R0, PAN_R1 + 1) for c in range(64)
                 if g[r][c] == v]
        if cells:
            out[v] = (min(r for r, _ in cells), min(c for _, c in cells))
    return out


def pic_blocks(eg):
    """Goal-picture blocks (color, c0) left-to-right from entry grid row57 (cols>=26)."""
    out = []
    c = 26
    while c < 64:
        v = eg[57][c]
        if v in BLOCK_COLORS:
            out.append((v, c))
            c += 4
        else:
            c += 1
    return out


def render(g, top, L, blocks, bar_k):
    for r in range(PAN_R0, PAN_R1 + 1):
        for c in range(64):
            g[r][c] = bg_color(r, c)
    for r in range(top, top + 6):
        for c in range(ENG_C0, ENG_C1 + 1):
            border = r in (top, top + 5) or c in (ENG_C0, ENG_C1)
            g[r][c] = 6 if border else 0
    for r in (top + 2, top + 3):
        for c in (13, 14):
            g[r][c] = 6
    for c in range(ENG_C1, ENG_C1 + L):
        a, b = ROPE_TEX[(c - ENG_C1) % 3]
        g[top + 2][c] = a
        g[top + 3][c] = b
    for v, (r0, c0) in blocks.items():
        for r in range(r0, r0 + 4):
            for c in range(c0, c0 + 4):
                if 0 <= r < 64 and 0 <= c < 64:
                    g[r][c] = v
    for c in range(64):
        g[53][c] = 3 if c >= 64 - bar_k else 2
    return g


def predict(state, grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    st = dict(state)
    if not st.get('synced', True):
        if not grids_equal(grid, ENTRY_GRID):
            st['acts'] = st.get('acts', 0) + 1
        st['synced'] = True
    st['acts'] = st.get('acts', 0) + 1
    info = {'level_up': False, 'dead': False, 'win': False}

    top = find_engine_top(g)
    if top is None:
        return g, info, st
    L = rope_len(g, top)
    blocks = find_blocks(g)
    tip = ENG_C1 + L - 1

    riding = {v for v, (r0, c0) in blocks.items() if r0 == top + 1 and c0 <= tip}
    wall = {v: rc for v, rc in blocks.items() if v not in riding}

    if action in (1, 2):
        new_top = max(TOP_MIN, top - 6) if action == 1 else min(TOP_MAX, top + 6)
        if new_top != top:
            dy = new_top - top
            moved = set()
            for v in riding:
                r0, c0 = blocks[v]
                blocks[v] = (r0 + dy, c0)
                moved.add(v)
            # push rule (CONFIRMED t#13): non-riding block overlapping the rope's
            # destination rows (or a moved block) gets pushed by dy; chains.
            changed = True
            while changed:
                changed = False
                for w, (wr0, wc0) in list(blocks.items()):
                    if w in moved:
                        continue
                    hit = (wr0 <= new_top + 3 and wr0 + 3 >= new_top + 2
                           and wc0 <= tip and wc0 + 3 >= ENG_C1)
                    if not hit:
                        for m in moved:
                            mr0, mc0 = blocks[m]
                            if abs(wr0 - mr0) < 4 and abs(wc0 - mc0) < 4:
                                hit = True
                                break
                    if hit:
                        blocks[w] = (wr0 + dy, wc0)
                        moved.add(w)
                        changed = True
            top = new_top
            # dead-guard: pushing a block off the panel is UNVERIFIED — mark dead
            # so BFS avoids it (not a confirmed game rule).
            for v, (r0, c0) in blocks.items():
                if r0 < 13 or r0 > 37:
                    info['dead'] = True
    elif action in (3, 4):
        if action == 3:
            new_L = max(L_MIN, L - 6)
            delta = new_L - L  # <= 0
            # move riding blocks left, leftmost first, clamp vs engine/neighbors
            order = sorted(riding, key=lambda v: blocks[v][1])
            placed = []  # c0s already fixed this step (left neighbors)
            for v in order:
                r0, c0 = blocks[v]
                nc0 = c0 + delta
                nc0 = max(nc0, BLK_CMIN)
                for pc0 in placed:
                    nc0 = max(nc0, pc0 + 6)  # 4 wide + 2 gap
                blocks[v] = (r0, nc0)
                placed.append(nc0)
            L = new_L
        else:
            new_L = min(L_MAX, L + 6)
            delta = new_L - L  # >= 0
            # move riding blocks right, rightmost first, clamp vs wall slot/neighbors
            order = sorted(riding, key=lambda v: -blocks[v][1])
            placed = []
            for v in order:
                r0, c0 = blocks[v]
                nc0 = c0 + delta
                nc0 = min(nc0, BLK_CMAX)
                # clamp vs static blocks on same rows (wall blocks ahead)
                for w, (wr0, wc0) in wall.items():
                    if abs(r0 - wr0) < 4 and wc0 > c0:
                        nc0 = min(nc0, wc0 - 6)
                for pc0 in placed:
                    nc0 = min(nc0, pc0 - 6)
                blocks[v] = (r0, nc0)
                placed.append(nc0)
            L = new_L

    bar_k = max(0, (st['acts'] - 1) // 3)   # flips at T=4,7,10,13,...
    render(g, top, L, blocks, bar_k)

    # LIVE goal-picture tracker (confirmed t#34 vs pre-reset frames): picture block k
    # hollows its 2x2 center (rows58-59) iff the k-th riding car from the engine
    # (sorted by c0) has that color; otherwise solid.
    tip2 = ENG_C1 + L - 1
    cars = [v for v, (r0, c0) in sorted(blocks.items(), key=lambda kv: kv[1][1])
            if r0 == top + 1 and c0 <= tip2]
    for k, (col, pc0) in enumerate(pic_blocks(ENTRY_GRID)):
        match = k < len(cars) and cars[k] == col
        for r in (58, 59):
            for c in (pc0 + 1, pc0 + 2):
                g[r][c] = 0 if match else col
    return g, info, st


def is_goal(state, grid):
    """Target train per bottom picture: from engine border col16 -> gap, 8@18-21,
    e@24-27, 9@30-33, rope tip col34 (L=19), all riding at engine rope rows."""
    top = find_engine_top(grid)
    if top is None:
        return False
    if rope_len(grid, top) != 19:
        return False
    blocks = find_blocks(grid)
    want = {8: (top + 1, 18), 14: (top + 1, 24), 9: (top + 1, 30)}
    return all(blocks.get(v) == rc for v, rc in want.items())
