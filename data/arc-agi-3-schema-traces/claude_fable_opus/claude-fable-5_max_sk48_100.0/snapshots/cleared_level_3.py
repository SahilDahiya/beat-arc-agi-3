# sk48 world model — "crane & train" (generalized from L0, L1)
# Scene: panel (color 4) with vertical track (cols eng_c0+2/3, pattern 2,2,3,3,3,3);
# engine 6x6 box (border 6, interior 0, 2x2 hub) slides in 6-row slots; rope extends
# right from engine border col in 6-cell steps, twisted 1/2 texture, renders UNDER blocks.
# Blocks: 4x4, colors = goal-picture colors. Skewer-couple mechanic (all CONFIRMED L0):
#  - riding = row-aligned (r0==top+1) and c0 <= tip; rides all rope/engine moves.
#  - extend slides through fresh blocks; retract drags riders (clamp: >=2 gap between
#    blocks, c0 >= eng_c1+2); riders clamp before wall blocks (gap 2) on extend.
#  - vertical move: riders follow; non-riders overlapping rope destination rows
#    (r0==newtop+1, cols<=tip) get PUSHED by dy; chained pushes.
#  - tip passing a block's c0 hooks it (becomes riding).
# Goal picture (below divider row of 2s): engine + block sequence. LIVE tracker:
#  picture block k hollows (2x2 center=0) iff k-th riding car (by c0) matches color.
# LEVEL UP the moment cars == full picture sequence (confirmed L0: at final hook).
# Budget bar: divider row, rightmost k cells 2->3, k=(T-1)//3, T=actions since entry.

ROPE_TEX = [(1, 2), (2, 1), (1, 1)]


def init_state(entry_grid):
    return {'acts': 0, 'synced': False}


def grids_equal(a, b):
    if a is None or b is None:
        return False
    for r in range(len(a)):
        ra_, rb = a[r], b[r]
        for c in range(len(ra_)):
            if ra_[c] != rb[c]:
                return False
    return True


def is_block_color(v):
    return v not in (0, 1, 2, 3, 4, 5, 6)


_LAYOUT_CACHE = {}


def layout(eg):
    """Derive all level geometry from the entry grid (memoized)."""
    key = (tuple(eg[25]), tuple(eg[44]), tuple(eg[57]))
    if key in _LAYOUT_CACHE:
        return _LAYOUT_CACHE[key]
    ly = _layout(eg)
    _LAYOUT_CACHE[key] = ly
    return ly


def _layout(eg):
    n = len(eg)
    # divider: full-width row of 2s
    d = None
    for r in range(n):
        if all(v == 2 for v in eg[r]):
            d = r
            break
    # live engine box: 6s above divider
    sixes = [(r, c) for r in range(d) for c in range(64) if eg[r][c] == 6]
    etop = min(r for r, _ in sixes)
    ec0 = min(c for r, c in sixes if r == etop)
    ec1 = ec0 + 5
    # panel: color-4 bounding box above divider
    fours = [(r, c) for r in range(d) for c in range(64) if eg[r][c] == 4]
    pr0 = min(r for r, _ in fours); pr1 = max(r for r, _ in fours)
    pc0 = min(c for _, c in fours); pc1 = max(c for _, c in fours)
    # track
    tc0, tc1 = ec0 + 2, ec0 + 3
    trows = [r for r in range(d) if eg[r][tc0] in (2, 3)]
    tr0 = min(trows)
    # ---- goal picture: hubs (isolated 2x2 monochrome patches below divider) and
    # block runs; each run belongs to the nearest hub on its left.
    hubs = []  # (c, r, color)
    for r in range(d + 1, n - 1):
        for c in range(63):
            v = eg[r][c]
            if v in (0, 4) or v == 2 and False:
                continue
            if v == eg[r][c + 1] == eg[r + 1][c] == eg[r + 1][c + 1]:
                if (c == 0 or (eg[r][c - 1] != v and eg[r + 1][c - 1] != v)) \
                   and (c + 2 > 63 or (eg[r][c + 2] != v and eg[r + 1][c + 2] != v)) \
                   and (eg[r - 1][c] != v and eg[r - 1][c + 1] != v) \
                   and (r + 2 >= n or (eg[r + 2][c] != v and eg[r + 2][c + 1] != v)):
                    hubs.append((c, r, v))
    hub_r = min(r for _, r, _ in hubs)
    hubs = sorted([h for h in hubs if h[1] == hub_r])
    pic_brow = hub_r - 1  # picture blocks' top row
    groups = []  # (holder_color, [(block_color, pic_c0), ...])
    for i, (hc, hr, hv) in enumerate(hubs):
        limit = hubs[i + 1][0] if i + 1 < len(hubs) else 64
        seq = []
        c = hc + 2
        while c < limit:
            v = eg[pic_brow][c]
            if is_block_color(v):
                seq.append((v, c))
                c += 4
            else:
                c += 1
        groups.append((hv, seq))
    # ---- vertical chain-ropes (L2+): 2/3 cells above divider, excluding track
    # columns and the engine's entry row band; grouped into column-pairs, each a
    # FIXED rope: cols (cc0,cc0+1), rows rtop..rbot, texture VCHAIN_TEX[(r-rtop)%3],
    # anchored to a 2x2 colored anchor above (rows rtop-3..rtop-2).
    ccells = [(r, c) for r in range(d) for c in range(64)
              if eg[r][c] in (2, 3) and c not in (tc0, tc1)
              and not (etop <= r <= etop + 5)]
    ccols = sorted({c for _, c in ccells})
    vropes = []  # (rtop, rbot, cc0, anchor_color)
    for cc in ccols:
        if cc - 1 in ccols:
            continue  # right half of a pair
        rows = [r for r, c in ccells if c in (cc, cc + 1)]
        rtop, rbot = min(rows), max(rows)
        anc = eg[rtop - 3][cc]
        vropes.append((rtop, rbot, cc, anc))
    return {
        'div': d, 'etop0': etop, 'ec0': ec0, 'ec1': ec1,
        'pan': (pr0, pr1, pc0, pc1),
        'tc': (tc0, tc1), 'tr0': tr0, 'tr1': etop + 3,
        'top_min': tr0 - 2, 'top_max': etop,
        'l_max': pc1 - ec1 + 1,
        'blk_cmin': ec1 + 2, 'blk_cmax': pc1 - 4,
        'groups': groups, 'pic_hrows': (hub_r, hub_r + 1),
        'vropes': vropes,
    }


def bg_color(r, c, ly):
    pr0, pr1, pc0, pc1 = ly['pan']
    if pr0 <= r <= pr1 and pc0 <= c <= pc1:
        return 4
    if c in ly['tc'] and ly['tr0'] <= r <= ly['tr1']:
        return 2 if (r - ly['tr0']) % 6 in (0, 1) else 3
    return 5


def find_engine_top(g, ly):
    c0 = ly['ec0']
    for r in range(ly['div']):
        if g[r][c0] == 6 and g[r][c0 + 1] == 6 and g[r][c0 + 2] == 6:
            return r
    return None


def rope_len(g, top, ly):
    r = top + 2
    ec1 = ly['ec1']
    last = ec1 - 1
    for c in range(ec1, 64):
        v = g[r][c]
        if v in (1, 2):
            last = c
        elif is_block_color(v):
            continue
        else:
            break
    return last - ec1 + 1


def find_blocks(g, ly):
    out = {}
    colors = {v for _, seq in ly['groups'] for v, _ in seq}
    for v in colors:
        cells = [(r, c) for r in range(ly['div']) for c in range(64) if g[r][c] == v]
        if cells:
            out[v] = (min(r for r, _ in cells), min(c for _, c in cells))
    return out


def cars_of(ly, top, L, blocks):
    tip = ly['ec1'] + L - 1
    return [v for v, (r0, c0) in sorted(blocks.items(), key=lambda kv: kv[1][1])
            if r0 == top + 1 and c0 <= tip]


def chain_slot_holder(ly, anc):
    """(rtop, cc0) of the chain belonging to anchor color anc."""
    for (rtop, rbot, cc0, a) in ly['vropes']:
        if a == anc:
            return rtop, cc0
    return None


def chain_occupants(ly, holder, blocks):
    """Blocks threaded on holder's chain, ordered top-down (anchor-outward)."""
    slot = None
    for (rtop, rbot, cc0, a) in ly['vropes']:
        if a == holder:
            slot = (rtop, rbot, cc0)
            break
    if slot is None:
        return []
    rtop, rbot, cc0 = slot
    occ = [(r0, v) for v, (r0, c0) in blocks.items()
           if c0 <= cc0 + 1 and c0 + 3 >= cc0 and r0 <= rbot and r0 + 3 >= rtop]
    return [v for _, v in sorted(occ)]


def holder_list(ly, top, L, blocks, holder):
    """Current ordered contents of a holder (engine rope or chain)."""
    if holder == 6:
        return cars_of(ly, top, L, blocks)
    return chain_occupants(ly, holder, blocks)


def block_satisfied(ly, top, L, blocks, holder, k, color):
    """Tracker rule (confirmed t#137): k-th occupant of the holder == color.
    Slot positions / skewering are irrelevant — pure order."""
    lst = holder_list(ly, top, L, blocks, holder)
    return k < len(lst) and lst[k] == color


def goal_satisfied(ly, top, L, blocks):
    for holder, seq in ly['groups']:
        if holder_list(ly, top, L, blocks, holder) != [v for v, _ in seq]:
            return False
    return True


def render(g, top, L, blocks, bar_k, ly, chain=None):
    pr0, pr1 = ly['pan'][0], ly['pan'][1]
    ec0, ec1 = ly['ec0'], ly['ec1']
    rlo = min(pr0, ly['top_min'])
    rhi = max(pr1, ly['top_max'] + 5)
    for r in range(rlo, rhi + 1):
        for c in range(64):
            g[r][c] = bg_color(r, c, ly)
    for r in range(top, top + 6):
        for c in range(ec0, ec1 + 1):
            border = r in (top, top + 5) or c in (ec0, ec1)
            g[r][c] = 6 if border else 0
    for r in (top + 2, top + 3):
        for c in (ec0 + 2, ec0 + 3):
            g[r][c] = 6
    # vertical chain-ropes (fixed cells; under horizontal rope and blocks)
    for (rtop, rbot, cc0, _anc) in ly['vropes']:
        for r in range(rtop, rbot + 1):
            a, b = VCHAIN_TEX[(r - rtop) % 3]
            g[r][cc0] = a
            g[r][cc0 + 1] = b
    for c in range(ec1, ec1 + L):
        a, b = ROPE_TEX[(c - ec1) % 3]
        g[top + 2][c] = a
        g[top + 3][c] = b
    for v, (r0, c0) in blocks.items():
        for r in range(r0, r0 + 4):
            for c in range(c0, c0 + 4):
                if 0 <= r < 64 and 0 <= c < 64:
                    g[r][c] = v
    d = ly['div']
    for c in range(64):
        g[d][c] = 3 if c >= 64 - bar_k else 2
    # live goal tracker: per picture group/slot
    h1, h2 = ly['pic_hrows']
    for holder, seq in ly['groups']:
        for k, (col, pcc) in enumerate(seq):
            match = block_satisfied(ly, top, L, blocks, holder, k, col)
            for r in (h1, h2):
                for c in (pcc + 1, pcc + 2):
                    g[r][c] = 0 if match else col
    return goal_satisfied(ly, top, L, blocks)


VCHAIN_TEX = [(3, 2), (2, 3), (2, 2)]


def chained_set(blocks, ly):
    """Blocks threaded on a vertical chain-rope: rows intersect [rtop,rbot] and
    cols overlap that chain's columns."""
    out = set()
    for (rtop, rbot, cc0, _anc) in ly['vropes']:
        for v, (r0, c0) in blocks.items():
            if r0 <= rbot and r0 + 3 >= rtop and c0 <= cc0 + 1 and c0 + 3 >= cc0:
                out.add(v)
    return out


def abstract_step(ly, top, L, blocks, action, chain=None):
    """Pure transition on abstract state. blocks: {color:(r0,c0)} (MUTATED copy ok).
    Returns (top, L, blocks, dead)."""
    dead = False
    tip = ly['ec1'] + L - 1
    pinned = chained_set(blocks, ly)      # chain-held: no HORIZONTAL motion
    riding = {v for v, (r0, c0) in blocks.items()
              if r0 == top + 1 and c0 <= tip}   # chained blocks DO ride vertically

    if action in (1, 2):
        new_top = (max(ly['top_min'], top - 6) if action == 1
                   else min(ly['top_max'], top + 6))
        # chain-slot SNAP (confirmed t#123): if any rider is chained, the move
        # lands riders on the chain slot lattice (r0 = rtop+2 mod 6), i.e. the
        # next slot in the motion direction; blocked above the top slot.
        if new_top != top and any(v in pinned for v in riding):
            rtop = ly['vropes'][0][0]
            smod = (rtop + 2) % 6
            cur = top + 1
            if action == 1:
                step_ = (cur - smod) % 6 or 6
                target = cur - step_
            else:
                step_ = (smod - cur) % 6 or 6
                target = cur + step_
            if target < rtop + 2:
                new_top = top      # jam at top slot (guess)
            else:
                new_top = max(ly['top_min'], min(ly['top_max'], target - 1))
        if new_top != top:
            dy = new_top - top
            moved = set()
            for v in riding:
                r0, c0 = blocks[v]
                blocks[v] = (r0 + dy, c0)
                moved.add(v)
            changed = True
            while changed:
                changed = False
                for w, (wr0, wc0) in list(blocks.items()):
                    if w in moved:
                        continue
                    hit = (wr0 <= new_top + 3 and wr0 + 3 >= new_top + 2
                           and wc0 <= tip and wc0 + 3 >= ly['ec1'])
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
            # dead-guard: pushing a block outside panel margins is UNVERIFIED — avoid
            for v, (r0, c0) in blocks.items():
                if r0 < ly['pan'][0] + 1 or r0 + 3 > ly['pan'][1] - 1:
                    dead = True
    elif action in (3, 4):
        # horizontal motion with PUSH CHAIN + JAM (confirmed t#54: rider pushes
        # parked block ahead; L0 wall case = jam at blk_cmax, pusher stops gap-2)
        new_L = (max(1, L - 6) if action == 3 else min(ly['l_max'], L + 6))
        delta = new_L - L
        if delta:
            row = sorted((c0, v) for v, (r0, c0) in blocks.items() if r0 == top + 1)
            vs = [v for _, v in row]
            cs = [c0 for c0, _ in row]
            # chain-wall jam (confirmed t#131): a horizontal ±6 that would land a
            # block overlapping a chain column (at rows intersecting the chain)
            # is blocked — the block acts pinned for this step.
            jam = set()
            for (rtop, rbot, cc0, _anc) in ly['vropes']:
                if top + 1 <= rbot and top + 4 >= rtop:
                    for i, v in enumerate(vs):
                        t = cs[i] + (6 if delta > 0 else -6)
                        if t <= cc0 + 1 and t + 3 >= cc0:
                            jam.add(v)
            pinned = pinned | jam
            n = [cs[i] + (delta if (vs[i] in riding and vs[i] not in pinned) else 0)
                 for i in range(len(vs))]
            if delta > 0:
                new_tip = ly['ec1'] + new_L - 1
                for i in range(len(n)):
                    if vs[i] in pinned:
                        n[i] = cs[i]          # immovable; stops push propagation
                        continue
                    if cs[i] > tip:
                        # tip PLOW (confirmed t#93): advancing tip pushes free
                        # blocks ahead, keeping them 2 beyond the new tip
                        n[i] = max(n[i], new_tip + 2)
                    if i > 0:
                        n[i] = max(n[i], n[i - 1] + 6)
                cap = ly['blk_cmax']
                for i in range(len(n) - 1, -1, -1):
                    if vs[i] in pinned:
                        n[i] = cs[i]          # chain-held: immovable
                    else:
                        n[i] = min(n[i], cap)
                    cap = n[i] - 6
            else:
                for i in range(len(n) - 1, -1, -1):
                    if vs[i] in pinned:
                        n[i] = cs[i]          # immovable; stops pull propagation
                        continue
                    if i < len(n) - 1:
                        n[i] = min(n[i], n[i + 1] - 6)
                floor = ly['blk_cmin']
                for i in range(len(n)):
                    if vs[i] in pinned:
                        n[i] = cs[i]
                    else:
                        n[i] = max(n[i], floor)
                    floor = n[i] + 6
            for i, v in enumerate(vs):
                blocks[v] = (top + 1, n[i])
        L = new_L
    return top, L, blocks, dead


def predict(state, grid, action, x=None, y=None):
    ly = layout(ENTRY_GRID)
    g = [row[:] for row in grid]
    st = dict(state)
    info = {'level_up': False, 'dead': False, 'win': False}
    if action == 6:
        # CONFIRMED t#84: click = complete no-op (no grid change, no budget tick)
        return g, info, st
    if not st.get('synced', True):
        if not grids_equal(grid, ENTRY_GRID):
            st['acts'] = st.get('acts', 0) + 1
        st['synced'] = True
    st['acts'] = st.get('acts', 0) + 1

    top = find_engine_top(g, ly)
    if top is None:
        return g, info, st
    L = rope_len(g, top, ly)
    blocks = find_blocks(g, ly)

    top, L, blocks, dead = abstract_step(ly, top, L, blocks, action)
    info['dead'] = dead

    bar_k = max(0, (st['acts'] - 1) // 3)
    if render(g, top, L, blocks, bar_k, ly):
        info['level_up'] = True
    return g, info, st


def is_goal(state, grid):
    ly = layout(ENTRY_GRID)
    top = find_engine_top(grid, ly)
    if top is None:
        return False
    L = rope_len(grid, top, ly)
    blocks = find_blocks(grid, ly)
    return goal_satisfied(ly, top, L, blocks)
