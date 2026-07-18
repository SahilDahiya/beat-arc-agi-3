# sk48 world model — "crane & train" (generalized over L0-L4)
# Scene: panel (4) with vertical track (cols ec0+2/3, pattern 2,2,3,3,3,3 from tr0);
# engine 6x6 box (border 6, interior 0, 2x2 hub) slides on 6-row lattice; rope from
# border col ec1, twisted 1/2 texture (period 3), renders UNDER blocks, OVER chains.
# Blocks 4x4 (colors from goal picture; DUPLICATE colors possible — blocks are a LIST).
# Mechanics (all confirmed via backtest):
#  - riding = r0==top+1 and c0<=tip. Riders follow rope/engine moves.
#  - extend: riders +6; tip PLOW pushes free ahead-blocks to new_tip+2; push chains
#    (gap 6); jam at blk_cmax / behind immovables — jammed blocks get slid under (hook).
#  - retract: riders -6 with floor blk_cmin, gap 6, pull-chain; jammed -> rope slides out.
#  - vertical: riders follow; non-riders straddling the rope DESTINATION rows with
#    c0<=tip are PUSHED dy (chain pushes via overlap); chained riders SNAP the move to
#    the chain slot lattice (next slot in direction; jam above top slot).
#  - chains (vertical ropes cols cc0/cc0+1, rows rtop..rbot, texture (3,2),(2,3),(2,2)):
#    blocks overlapping them at chain rows are threaded: pinned horizontally, slide
#    vertically, fall off past rbot. Horizontal moves INTO a chain column jam (wall).
#  - walls (5-rects inside panel): block rope extension at their rows, jam horizontal
#    block moves, CANCEL vertical moves that would overlap (guess).
# Goal: picture groups below divider (hub 2x2 -> holder: 6=engine rope, else anchor
# color = that chain). Holder contents (cars by c0 / chain occupants by r0) must equal
# the pictured color sequence — order only (t#137). Tracker hollows slot k iff k-th
# content == color, LIVE. Level up when ALL groups match exactly.
# Budget bar: divider row; rightmost k cells ->3, k=(T-1)//3; clicks don't count (t#84).

ROPE_TEX = [(1, 2), (2, 1), (1, 1)]
VCHAIN_TEX = [(3, 2), (2, 3), (2, 2)]


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
    key = (tuple(eg[25]), tuple(eg[44]), tuple(eg[57]))
    if key in _LAYOUT_CACHE:
        return _LAYOUT_CACHE[key]
    ly = _layout(eg)
    _LAYOUT_CACHE[key] = ly
    return ly


def _layout(eg):
    n = len(eg)
    d = None
    for r in range(n):
        if all(v == 2 for v in eg[r]):
            d = r
            break
    sixes = [(r, c) for r in range(d) for c in range(64) if eg[r][c] == 6]
    etop = min(r for r, _ in sixes)
    ec0 = min(c for r, c in sixes if r == etop)
    ec1 = ec0 + 5
    fours = [(r, c) for r in range(d) for c in range(64) if eg[r][c] == 4]
    pr0 = min(r for r, _ in fours); pr1 = max(r for r, _ in fours)
    pc0 = min(c for _, c in fours); pc1 = max(c for _, c in fours)
    tc0, tc1 = ec0 + 2, ec0 + 3
    trows = [r for r in range(d) if eg[r][tc0] in (2, 3)]
    tr0 = min(trows)
    tr1 = max(max(trows), etop + 3)
    # goal picture: hubs + block runs
    hubs = []
    for r in range(d + 1, n - 1):
        for c in range(63):
            v = eg[r][c]
            if v in (0, 4):
                continue
            if v == eg[r][c + 1] == eg[r + 1][c] == eg[r + 1][c + 1]:
                if (c == 0 or (eg[r][c - 1] != v and eg[r + 1][c - 1] != v)) \
                   and (c + 2 > 63 or (eg[r][c + 2] != v and eg[r + 1][c + 2] != v)) \
                   and (eg[r - 1][c] != v and eg[r - 1][c + 1] != v) \
                   and (r + 2 >= n or (eg[r + 2][c] != v and eg[r + 2][c + 1] != v)):
                    hubs.append((c, r, v))
    hub_r = min(r for _, r, _ in hubs)
    hubs = sorted([h for h in hubs if h[1] == hub_r])
    pic_brow = hub_r - 1
    groups = []
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
    # vertical chain-ropes
    ccells = [(r, c) for r in range(d) for c in range(64)
              if eg[r][c] in (2, 3) and c not in (tc0, tc1)
              and not (etop <= r <= etop + 5)]
    ccols = sorted({c for _, c in ccells})
    vropes = []
    for cc in ccols:
        if cc - 1 in ccols:
            continue
        rows = [r for r, c in ccells if c in (cc, cc + 1)]
        rtop, rbot = min(rows), max(rows)
        anc = eg[rtop - 3][cc]
        vropes.append((rtop, rbot, cc, anc))
    # walls: 5-cells strictly inside the panel bbox -> bounding rectangles
    wcells = {(r, c) for r in range(pr0, pr1 + 1) for c in range(pc0, pc1 + 1)
              if eg[r][c] == 5}
    walls = []
    seen = set()
    for (r, c) in sorted(wcells):
        if (r, c) in seen:
            continue
        stack = [(r, c)]
        comp = []
        while stack:
            p = stack.pop()
            if p in seen or p not in wcells:
                continue
            seen.add(p)
            comp.append(p)
            pr_, pc_ = p
            stack += [(pr_ + 1, pc_), (pr_ - 1, pc_), (pr_, pc_ + 1), (pr_, pc_ - 1)]
        rs = [p[0] for p in comp]; cs = [p[1] for p in comp]
        walls.append((min(rs), max(rs), min(cs), max(cs)))
    return {
        'div': d, 'etop0': etop, 'ec0': ec0, 'ec1': ec1,
        'pan': (pr0, pr1, pc0, pc1),
        'tc': (tc0, tc1), 'tr0': tr0, 'tr1': tr1,
        'top_min': tr0 - 2, 'top_max': tr1 - 3,
        'l_max': pc1 - ec1 + 1,
        'blk_cmin': ec1 + 2, 'blk_cmax': pc1 - 4,
        'groups': groups, 'pic_hrows': (hub_r, hub_r + 1),
        'vropes': vropes, 'walls': walls,
    }


def bg_color(r, c, ly):
    pr0, pr1, pc0, pc1 = ly['pan']
    for (wr0, wr1, wc0, wc1) in ly['walls']:
        if wr0 <= r <= wr1 and wc0 <= c <= wc1:
            return 5
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
    """All 4x4 blocks above divider -> sorted list of (color, r0, c0)."""
    colors = {v for _, seq in ly['groups'] for v, _ in seq}
    out = []
    covered = set()
    for r in range(ly['div']):
        for c in range(64):
            if (r, c) in covered or g[r][c] not in colors:
                continue
            out.append((g[r][c], r, c))
            for rr in range(r, r + 4):
                for cc in range(c, c + 4):
                    covered.add((rr, cc))
    return sorted(out)


def cars_of(ly, top, L, blocks):
    tip = ly['ec1'] + L - 1
    return [v for v, r0, c0 in sorted(blocks, key=lambda b: b[2])
            if r0 == top + 1 and c0 <= tip]


def chain_occupants(ly, holder, blocks):
    slot = None
    for (rtop, rbot, cc0, a) in ly['vropes']:
        if a == holder:
            slot = (rtop, rbot, cc0)
            break
    if slot is None:
        return []
    rtop, rbot, cc0 = slot
    occ = [(r0, v) for v, r0, c0 in blocks
           if c0 <= cc0 + 1 and c0 + 3 >= cc0 and r0 <= rbot and r0 + 3 >= rtop]
    return [v for _, v in sorted(occ)]


def holder_list(ly, top, L, blocks, holder):
    if holder == 6:
        return cars_of(ly, top, L, blocks)
    return chain_occupants(ly, holder, blocks)


def block_satisfied(ly, top, L, blocks, holder, k, color):
    lst = holder_list(ly, top, L, blocks, holder)
    return k < len(lst) and lst[k] == color


def goal_satisfied(ly, top, L, blocks):
    for holder, seq in ly['groups']:
        if holder_list(ly, top, L, blocks, holder) != [v for v, _ in seq]:
            return False
    return True


def chained_idx(blocks, ly):
    out = set()
    for (rtop, rbot, cc0, _anc) in ly['vropes']:
        for i, (v, r0, c0) in enumerate(blocks):
            if r0 <= rbot and r0 + 3 >= rtop and c0 <= cc0 + 1 and c0 + 3 >= cc0:
                out.add(i)
    return out


def overlaps_wall(ly, r0, c0):
    for (wr0, wr1, wc0, wc1) in ly['walls']:
        if r0 <= wr1 and r0 + 3 >= wr0 and c0 <= wc1 and c0 + 3 >= wc0:
            return True
    return False


def rope_cap(ly, top):
    """Max tip col given walls at the rope's rows."""
    cap = ly['ec1'] + ly['l_max'] - 1
    for (wr0, wr1, wc0, wc1) in ly['walls']:
        if top + 2 <= wr1 and top + 3 >= wr0 and wc0 > ly['ec1']:
            cap = min(cap, wc0 - 1)
    return cap


def abstract_step(ly, top, L, blocks, action, chain=None):
    """blocks: list of (color, r0, c0). Returns (top, L, blocks, dead)."""
    dead = False
    blocks = list(blocks)
    tip = ly['ec1'] + L - 1
    pinned = chained_idx(blocks, ly)
    riding = {i for i, (v, r0, c0) in enumerate(blocks)
              if r0 == top + 1 and c0 <= tip}

    if action in (1, 2):
        new_top = (max(ly['top_min'], top - 6) if action == 1
                   else min(ly['top_max'], top + 6))
        if new_top != top and any(i in pinned for i in riding):
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
                new_top = top
            else:
                new_top = max(ly['top_min'], min(ly['top_max'], target - 1))
        # rope-vs-wall: vertical move is BLOCKED if the rope's destination rows
        # would overlap a wall (confirmed t#159: whole move canceled, bar ticks)
        if new_top != top:
            for (wr0, wr1, wc0, wc1) in ly['walls']:
                if new_top + 2 <= wr1 and new_top + 3 >= wr0 \
                   and wc0 <= tip and wc1 >= ly['ec1']:
                    new_top = top
                    break
        if new_top != top:
            dy = new_top - top
            nb = list(blocks)
            moved = set()
            for i in riding:
                v, r0, c0 = nb[i]
                nb[i] = (v, r0 + dy, c0)
                moved.add(i)
            changed = True
            while changed:
                changed = False
                for j, (v, r0, c0) in enumerate(nb):
                    if j in moved:
                        continue
                    hit = (r0 <= new_top + 3 and r0 + 3 >= new_top + 2
                           and c0 <= tip and c0 + 3 >= ly['ec1'])
                    if not hit:
                        for m in moved:
                            mv, mr0, mc0 = nb[m]
                            if abs(r0 - mr0) < 4 and abs(c0 - mc0) < 4:
                                hit = True
                                break
                    if hit:
                        nb[j] = (v, r0 + dy, c0)
                        moved.add(j)
                        changed = True
            # wall check: any moved block overlapping a wall cancels the move (guess)
            ok = True
            for i in moved:
                v, r0, c0 = nb[i]
                if overlaps_wall(ly, r0, c0):
                    ok = False
            if ok:
                blocks = nb
                top = new_top
                for v, r0, c0 in blocks:
                    if r0 < ly['pan'][0] + 1 or r0 + 3 > ly['pan'][1] - 1:
                        dead = True
    elif action in (3, 4):
        cap_tip = rope_cap(ly, top)
        if action == 3:
            new_L = max(1, L - 6)
        else:
            new_L = min(ly['l_max'], L + 6)
            new_L = min(new_L, cap_tip - ly['ec1'] + 1)
            new_L = max(new_L, L)
        delta = new_L - L
        if delta:
            order = sorted([i for i, (v, r0, c0) in enumerate(blocks)
                            if r0 == top + 1], key=lambda i: blocks[i][2])
            vs = [blocks[i][0] for i in order]
            cs = [blocks[i][2] for i in order]
            # jams: chain columns and walls act as horizontal barriers
            jam = set()
            for k_ in range(len(order)):
                t = cs[k_] + (6 if delta > 0 else -6)
                for (rtop, rbot, cc0, _anc) in ly['vropes']:
                    if top + 1 <= rbot and top + 4 >= rtop \
                       and t <= cc0 + 1 and t + 3 >= cc0:
                        jam.add(order[k_])
                if overlaps_wall(ly, top + 1, t):
                    jam.add(order[k_])
            pinned_h = pinned | jam
            n = [cs[k_] + (delta if (order[k_] in riding
                                     and order[k_] not in pinned_h) else 0)
                 for k_ in range(len(order))]
            if delta > 0:
                new_tip = ly['ec1'] + new_L - 1
                for k_ in range(len(n)):
                    if order[k_] in pinned_h:
                        n[k_] = cs[k_]
                        continue
                    if cs[k_] > tip:
                        n[k_] = max(n[k_], new_tip + 2)
                    if k_ > 0:
                        n[k_] = max(n[k_], n[k_ - 1] + 6)
                cap = ly['blk_cmax']
                for k_ in range(len(n) - 1, -1, -1):
                    if order[k_] in pinned_h:
                        n[k_] = cs[k_]
                    else:
                        n[k_] = min(n[k_], cap)
                    cap = n[k_] - 6
            else:
                for k_ in range(len(n) - 1, -1, -1):
                    if order[k_] in pinned_h:
                        n[k_] = cs[k_]
                        continue
                    if k_ < len(n) - 1:
                        n[k_] = min(n[k_], n[k_ + 1] - 6)
                floor = ly['blk_cmin']
                for k_ in range(len(n)):
                    if order[k_] in pinned_h:
                        n[k_] = cs[k_]
                    else:
                        n[k_] = max(n[k_], floor)
                    floor = n[k_] + 6
            for k_, i in enumerate(order):
                v, r0, c0 = blocks[i]
                blocks[i] = (v, r0, n[k_])
        L = new_L
    return top, L, blocks, dead


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
    for (rtop, rbot, cc0, _anc) in ly['vropes']:
        for r in range(rtop, rbot + 1):
            a, b = VCHAIN_TEX[(r - rtop) % 3]
            g[r][cc0] = a
            g[r][cc0 + 1] = b
    for c in range(ec1, ec1 + L):
        a, b = ROPE_TEX[(c - ec1) % 3]
        g[top + 2][c] = a
        g[top + 3][c] = b
    for v, r0, c0 in blocks:
        for r in range(r0, r0 + 4):
            for c in range(c0, c0 + 4):
                if 0 <= r < 64 and 0 <= c < 64:
                    g[r][c] = v
    d = ly['div']
    for c in range(64):
        g[d][c] = 3 if c >= 64 - bar_k else 2
    h1, h2 = ly['pic_hrows']
    for holder, seq in ly['groups']:
        for k, (col, pcc) in enumerate(seq):
            match = block_satisfied(ly, top, L, blocks, holder, k, col)
            for r in (h1, h2):
                for c in (pcc + 1, pcc + 2):
                    g[r][c] = 0 if match else col
    return goal_satisfied(ly, top, L, blocks)


def predict(state, grid, action, x=None, y=None):
    ly = layout(ENTRY_GRID)
    g = [row[:] for row in grid]
    st = dict(state)
    info = {'level_up': False, 'dead': False, 'win': False}
    if action == 6:
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
