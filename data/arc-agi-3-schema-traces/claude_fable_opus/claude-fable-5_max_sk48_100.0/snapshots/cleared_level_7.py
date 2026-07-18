# sk48 world model — "two cranes & trains" (generalized over L0-L5)
# HOLDERS: engine (6-box on vertical track, horizontal rope, hub 6) and optionally a
# top CRANE (colored box on horizontal track rows, vertical chain, colored hub).
# Clicking a hub ACTIVATES that holder (interior 0=active/4=inactive; rope values
# +1 when inactive: H-tex (1,2),(2,1),(1,1); V-tex (2,1),(1,2),(1,1); inactive=+1).
# Actions drive the ACTIVE holder: 1/2 = along its track (engine: up/down; crane:
# left/right), 3/4 = its rope retract/extend (engine: left/right; crane: up/down).
# Physics (mirror-symmetric between holders; all confirmed unless noted):
#  - riding: block straddles rope axis (engine: r0==top+1, c0<=tip; crane: c0==ccc0-1,
#    r0<=ktip). Riders follow rope and holder motion.
#  - extend: riders +6; tip-plow pushes free ahead-blocks to new_tip+2; push chains
#    (gap 6); jam at far margin (blk_cmax / blk_rmax) or behind immovables -> slid
#    under (hook). retract: mirror with near floor (ec1+2 / chain_r0+2).
#  - holder-track move: riders follow; non-riders straddling the rope DESTINATION
#    with pos<=tip get pushed; chain pushes; move BLOCKED if rope destination
#    overlaps a wall; blocks landing on walls cancel the move (guess).
#  - cross-hold: blocks riding the OTHER holder's rope are PINNED along this
#    holder's rope axis (chain-held horizontally / rope-held vertically); a rider
#    move that lands a block on another holder's column/row lattice snaps (L3).
#  - walls (5-rects in panel): cap rope extension; jam horizontal entry; block moves.
# Goal: picture groups (hub color -> holder). Holder CONTENTS (ordered along rope)
# must equal pictured sequence — pure order. Tracker hollows k-th slot iff k-th
# content matches, LIVE. Level up when ALL groups match exactly.
# Budget bar: divider row; rightmost k cells ->3, k=(T-1)//3; clicks don't tick.

H_TEX = [(1, 2), (2, 1), (1, 1)]   # horizontal rope, by (c-start)%3, +1 if inactive
V_TEX = [(2, 1), (1, 2), (1, 1)]   # vertical chain, by (r-start)%3, +1 if inactive


def init_state(entry_grid):
    # phase: ticking actions since last observed bar flip (-1 = level entry;
    # first flip comes after 4 ticks, later ones every 3). last_bar resyncs
    # from each REAL input grid, so anomalies self-heal after one mispredict.
    return {'acts': 0, 'synced': False, 'phase': -1, 'last_bar': 0}


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
    key = (tuple(eg[4]), tuple(eg[25]), tuple(eg[44]), tuple(eg[57]))
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
    prow = [r for r in range(d) if sum(1 for c in range(64) if eg[r][c] == 4) >= 16]
    pr0, pr1 = min(prow), max(prow)
    pcs = [c for r in prow for c in range(64) if eg[r][c] == 4]
    pc0, pc1 = min(pcs), max(pcs)
    tc0, tc1 = ec0 + 2, ec0 + 3
    trows = [r for r in range(d) if eg[r][tc0] in (2, 3)]
    tr0 = min(trows)
    tr1 = max(max(trows), etop + 3)
    # horizontal track rows (top crane)
    htrows = sorted(r for r in range(d)
                    if sum(1 for c in range(64)
                           if eg[r][c] in (2, 3) and c not in (tc0, tc1)) >= 6)
    crane = None
    if htrows:
        htr0 = htrows[0]
        hcols = [c for c in range(64) if eg[htr0][c] in (2, 3)]
        # crane box: non-track colored border on the track row band
        ccolor = None
        for c in range(64):
            v = eg[htr0 - 2][c]
            if v not in (4, 5) and not (tc0 <= c <= tc1):
                ccolor = v
                break
        cc0_entry = min(c for c in range(64) if eg[htr0 - 2][c] == ccolor)
        crane = {
            'color': ccolor, 'box_r0': htr0 - 2, 'htr': (htr0, htr0 + 1),
            'ht_c0': min(hcols), 'ht_c1': max(hcols),
            'c_min': min(hcols) - 2, 'c_max': max(hcols) - 3,
            'chain_r0': htr0 + 3,
            'kl_max': pr1 - (htr0 + 3) + 1,
            'blk_rmax': pr1 - 4,
        }
    # static vertical chains (anchor blobs, not crane chains)
    ccells = [(r, c) for r in range(d) for c in range(64)
              if eg[r][c] in (2, 3) and c not in (tc0, tc1)
              and not (etop <= r <= etop + 5) and r not in htrows]
    ccols = sorted({c for _, c in ccells})
    vropes = []
    for cc in ccols:
        if cc - 1 in ccols:
            continue
        rows = [r for r, c in ccells if c in (cc, cc + 1)]
        rtop, rbot = min(rows), max(rows)
        if crane and rtop == crane['chain_r0'] - 1 + 1:
            continue  # the crane's own chain — dynamic, not static
        anc = eg[rtop - 3][cc]
        vropes.append((rtop, rbot, cc, anc))
    # goal picture: hubs + block runs (+ rope texture cells for active-mirroring)
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
    # entry-active holder: engine iff its interior is 0 at entry
    entry_active = 6 if eg[etop + 1][ec0 + 1] == 0 else (crane['color'] if crane else 6)
    groups = []
    for i, (hc, hr, hv) in enumerate(hubs):
        c_lo = hc - 2
        limit = (hubs[i + 1][0] - 2) if i + 1 < len(hubs) else 64
        seq = []
        c = hc + 4
        while c < limit:
            v = eg[pic_brow][c]
            if is_block_color(v):
                seq.append((v, c))
                c += 4
            else:
                c += 1
        # picture cells owned by this group: box interior + rope-texture cells
        interior = []
        for r in range(hub_r - 1, hub_r + 3):
            for c in range(c_lo + 1, c_lo + 5):
                if not (hub_r <= r <= hub_r + 1 and hc <= c <= hc + 1):
                    interior.append((r, c))
        ropecells = []
        for r in (hub_r, hub_r + 1):
            for c in range(c_lo, limit):
                v = eg[r][c]
                if v in (1, 2, 3) and not (hc <= c <= hc + 1):
                    base = v - (0 if hv == entry_active else 1)
                    ropecells.append((r, c, base))
        groups.append((hv, seq, interior, ropecells))
    return {
        'div': d, 'etop0': etop, 'ec0': ec0, 'ec1': ec1,
        'pan': (pr0, pr1, pc0, pc1),
        'tc': (tc0, tc1), 'tr0': tr0, 'tr1': tr1,
        'top_min': tr0 - 2, 'top_max': tr1 - 3,
        'l_max': pc1 - ec1 + 1,
        'blk_cmin': ec1 + 2, 'blk_cmax': pc1 - 4,
        'groups': groups, 'pic_hrows': (hub_r, hub_r + 1),
        'vropes': vropes, 'walls': walls_of(eg, d, pr0, pr1, pc0, pc1),
        'crane': crane,
    }


def walls_of(eg, d, pr0, pr1, pc0, pc1):
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
    return walls


def bg_color(r, c, ly):
    pr0, pr1, pc0, pc1 = ly['pan']
    for (wr0, wr1, wc0, wc1) in ly['walls']:
        if wr0 <= r <= wr1 and wc0 <= c <= wc1:
            return 5
    if pr0 <= r <= pr1 and pc0 <= c <= pc1:
        return 4
    if c in ly['tc'] and ly['tr0'] <= r <= ly['tr1']:
        return 2 if (r - ly['tr0']) % 6 in (0, 1) else 3
    cr = ly['crane']
    if cr and cr['htr'][0] <= r <= cr['htr'][1] and cr['ht_c0'] <= c <= cr['ht_c1']:
        return 2 if (c - cr['ht_c0']) % 6 in (0, 1) else 3
    return 5


def find_engine_top(g, ly):
    c0 = ly['ec0']
    for r in range(ly['div']):
        if g[r][c0] == 6 and g[r][c0 + 1] == 6 and g[r][c0 + 2] == 6:
            return r
    return None


def extract(g, ly):
    """Dynamic state from grid: (top, L, cc0, KL, active, blocks)."""
    top = find_engine_top(g, ly)
    ec1 = ly['ec1']
    r = top + 2
    last = ec1 - 1
    for c in range(ec1, 64):
        v = g[r][c]
        if v in (1, 2, 3):
            last = c
        elif is_block_color(v):
            pass
        else:
            break
    L = last - ec1 + 1
    cr = ly['crane']
    cc0 = KL = None
    active = 6
    if cr:
        row = cr['box_r0']
        cc0 = min(c for c in range(64) if g[row][c] == cr['color'])
        cr0 = cr['chain_r0']
        ccc = cc0 + 2
        last_r = cr0 - 1
        for rr in range(cr0, ly['div']):
            v = g[rr][ccc]
            if v in (1, 2, 3):
                last_r = rr
            elif is_block_color(v):
                pass
            else:
                break
        KL = last_r - cr0 + 1
        if g[top + 1][ly['ec0'] + 1] != 0:
            active = cr['color']
    colors = {v for _, seq, _, _ in ly['groups'] for v, _ in seq}
    blocks = []
    covered = set()
    for r in range(ly['div']):
        for c in range(64):
            if (r, c) in covered or g[r][c] not in colors:
                continue
            blocks.append((g[r][c], r, c))
            for rr in range(r, r + 4):
                for cc_ in range(c, c + 4):
                    covered.add((rr, cc_))
    return top, L, cc0, KL, active, sorted(blocks)


def cars_of(ly, top, L, blocks):
    tip = ly['ec1'] + L - 1
    return [v for v, r0, c0 in sorted(blocks, key=lambda b: b[2])
            if r0 == top + 1 and c0 <= tip]


def crane_occupants(ly, cc0, KL, blocks):
    cr = ly['crane']
    ccc = cc0 + 2
    ktip = cr['chain_r0'] + KL - 1
    occ = [(r0, v) for v, r0, c0 in blocks if c0 == ccc - 1 and r0 <= ktip
           and r0 + 3 >= cr['chain_r0'] - 1]
    return [v for _, v in sorted(occ)]


def static_chain_occupants(ly, holder, blocks):
    for (rtop, rbot, cc, a) in ly['vropes']:
        if a == holder:
            occ = [(r0, v) for v, r0, c0 in blocks
                   if c0 <= cc + 1 and c0 + 3 >= cc and r0 <= rbot and r0 + 3 >= rtop]
            return [v for _, v in sorted(occ)]
    return []


def holder_list(ly, S, holder):
    top, L, cc0, KL, active, blocks = S
    if holder == 6:
        return cars_of(ly, top, L, blocks)
    cr = ly['crane']
    if cr and holder == cr['color']:
        return crane_occupants(ly, cc0, KL, blocks)
    return static_chain_occupants(ly, holder, blocks)


def goal_satisfied(ly, S):
    for grp in ly['groups']:
        holder, seq = grp[0], grp[1]
        if holder_list(ly, S, holder) != [v for v, _ in seq]:
            return False
    return True


def pinned_for_engine(ly, S):
    """Blocks held by vertical structures -> immovable horizontally."""
    top, L, cc0, KL, active, blocks = S
    out = set()
    for i, (v, r0, c0) in enumerate(blocks):
        for (rtop, rbot, cc, _anc) in ly['vropes']:
            if r0 <= rbot and r0 + 3 >= rtop and c0 <= cc + 1 and c0 + 3 >= cc:
                out.add(i)
        cr = ly['crane']
        if cr and cc0 is not None:
            ccc = cc0 + 2
            ktip = cr['chain_r0'] + KL - 1
            if c0 <= ccc + 1 and c0 + 3 >= ccc and r0 <= ktip and r0 + 3 >= cr['chain_r0'] - 1:
                out.add(i)
    return out


def overlaps_wall(ly, r0, c0):
    for (wr0, wr1, wc0, wc1) in ly['walls']:
        if r0 <= wr1 and r0 + 3 >= wr0 and c0 <= wc1 and c0 + 3 >= wc0:
            return True
    return False


def abstract_step(ly, S, action, x=None, y=None):
    """S = (top, L, cc0, KL, active, blocks-list). Returns (S', dead, counts)."""
    top, L, cc0, KL, active, blocks = S
    blocks = list(blocks)
    dead = False
    cr = ly['crane']

    if action == 6:
        if x is not None:
            if (top + 2 <= y <= top + 3 and ly['ec0'] + 2 <= x <= ly['ec0'] + 3):
                active = 6
            elif cr and cc0 is not None and \
                    (cr['htr'][0] <= y <= cr['htr'][1] and cc0 + 2 <= x <= cc0 + 3):
                active = cr['color']
        return (top, L, cc0, KL, active, blocks), dead, False

    if active == 6:
        tip = ly['ec1'] + L - 1
        pinned = pinned_for_engine(ly, S)
        riding = {i for i, (v, r0, c0) in enumerate(blocks)
                  if r0 == top + 1 and c0 <= tip}
        if action in (1, 2):
            new_top = (max(ly['top_min'], top - 6) if action == 1
                       else min(ly['top_max'], top + 6))
            if new_top != top and any(i in pinned for i in riding):
                anchors = [rt for (rt, rb, cc, a) in ly['vropes']]
                if cr:
                    anchors.append(cr['chain_r0'] - 1 + 1)
                rt = anchors[0]
                smod = (rt + 2) % 6
                cur = top + 1
                if action == 1:
                    step_ = (cur - smod) % 6 or 6
                    target = cur - step_
                else:
                    step_ = (smod - cur) % 6 or 6
                    target = cur + step_
                if target < rt + 2:
                    new_top = top
                else:
                    new_top = max(ly['top_min'], min(ly['top_max'], target - 1))
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
            cap = ly['ec1'] + ly['l_max'] - 1
            for (wr0, wr1, wc0, wc1) in ly['walls']:
                if top + 2 <= wr1 and top + 3 >= wr0 and wc0 > ly['ec1']:
                    cap = min(cap, wc0 - 1)
            if action == 3:
                new_L = max(1, L - 6)
            else:
                new_L = min(ly['l_max'], L + 6)
                new_L = min(new_L, cap - ly['ec1'] + 1)
                new_L = max(new_L, L)
            delta = new_L - L
            if delta:
                order = sorted([i for i, (v, r0, c0) in enumerate(blocks)
                                if r0 == top + 1], key=lambda i: blocks[i][2])
                vs = [blocks[i][0] for i in order]
                cs = [blocks[i][2] for i in order]
                jam = set()
                for k_ in range(len(order)):
                    t = cs[k_] + (6 if delta > 0 else -6)
                    for (rtop, rbot, cc, _anc) in ly['vropes']:
                        if top + 1 <= rbot and top + 4 >= rtop \
                           and t <= cc + 1 and t + 3 >= cc:
                            jam.add(order[k_])
                    if cr and cc0 is not None:
                        ccc = cc0 + 2
                        ktip = cr['chain_r0'] + KL - 1
                        if top + 1 <= ktip and top + 4 >= cr['chain_r0'] - 1 \
                           and t <= ccc + 1 and t + 3 >= ccc:
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
                    cap2 = ly['blk_cmax']
                    for k_ in range(len(n) - 1, -1, -1):
                        if order[k_] in pinned_h:
                            n[k_] = cs[k_]
                        else:
                            n[k_] = min(n[k_], cap2)
                        cap2 = n[k_] - 6
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
    else:
        # CRANE ACTIVE — mirrored physics (rows<->cols)
        ccc = cc0 + 2
        ktip = cr['chain_r0'] + KL - 1
        # blocks riding MY rope are pinned vertically (mirror of chain-hold)
        my_tip = ly['ec1'] + L - 1
        pinned = {i for i, (v, r0, c0) in enumerate(blocks)
                  if r0 == top + 1 and c0 <= my_tip}
        riding = {i for i, (v, r0, c0) in enumerate(blocks)
                  if c0 == ccc - 1 and r0 <= ktip}
        if action in (3, 4):
            # crane slides along its horizontal track (3=left, 4=right; global dirs)
            new_c = (max(cr['c_min'], cc0 - 6) if action == 3
                     else min(cr['c_max'], cc0 + 6))
            if new_c != cc0 and any(i in pinned for i in riding):
                # snap riders to my-rope block lattice? both lattices align (=12+6k);
                # treat as normal move (no snap needed on shared lattice)
                pass
            if new_c != cc0:
                # chain dest vs walls: blocked
                nccc = new_c + 2
                for (wr0, wr1, wc0, wc1) in ly['walls']:
                    if wc0 <= nccc + 1 and wc1 >= nccc \
                       and wr0 <= ktip and wr1 >= cr['chain_r0']:
                        new_c = cc0
                        break
            if new_c != cc0:
                dc = new_c - cc0
                nb = list(blocks)
                moved = set()
                for i in riding:
                    # my rope does NOT pin horizontally — riders slide along it
                    v, r0, c0 = nb[i]
                    nb[i] = (v, r0, c0 + dc)
                    moved.add(i)
                changed = True
                while changed:
                    changed = False
                    for j, (v, r0, c0) in enumerate(nb):
                        if j in moved:
                            continue
                        nccc = new_c + 2
                        hit = (c0 <= nccc + 1 and c0 + 3 >= nccc
                               and r0 <= ktip and r0 + 3 >= cr['chain_r0'] - 1)
                        if not hit:
                            for m in moved:
                                mv, mr0, mc0 = nb[m]
                                if abs(r0 - mr0) < 4 and abs(c0 - mc0) < 4:
                                    hit = True
                                    break
                        if hit and j not in pinned:
                            nb[j] = (v, r0, c0 + dc)
                            moved.add(j)
                            changed = True
                ok = True
                for i in moved:
                    v, r0, c0 = nb[i]
                    if overlaps_wall(ly, r0, c0):
                        ok = False
                    if c0 < ly['pan'][2] + 1 or c0 + 3 > ly['pan'][3] - 1:
                        dead = True
                if ok:
                    blocks = nb
                    cc0 = new_c
        elif action in (1, 2):
            # crane chain: 1=retract (up), 2=extend (down); global dirs
            cap = cr['chain_r0'] + cr['kl_max'] - 1
            for (wr0, wr1, wc0, wc1) in ly['walls']:
                if wc0 <= ccc + 1 and wc1 >= ccc and wr0 > cr['chain_r0']:
                    cap = min(cap, wr0 - 1)
            if action == 1:
                new_K = max(1, KL - 6)
            else:
                new_K = min(cr['kl_max'], KL + 6)
                new_K = min(new_K, cap - cr['chain_r0'] + 1)
                new_K = max(new_K, KL)
            delta = new_K - KL
            if delta:
                order = sorted([i for i, (v, r0, c0) in enumerate(blocks)
                                if c0 == ccc - 1], key=lambda i: blocks[i][1])
                rs = [blocks[i][1] for i in order]
                jam = set()
                for k_ in range(len(order)):
                    t = rs[k_] + (6 if delta > 0 else -6)
                    if overlaps_wall(ly, t, ccc - 1):
                        jam.add(order[k_])
                    # my rope band is a horizontal barrier (confirmed t#232):
                    # a block cannot be moved vertically onto/through it
                    if t == top + 1 and blocks[order[k_]][2] <= my_tip:
                        jam.add(order[k_])
                pinned_v = pinned | jam
                n = [rs[k_] + (delta if (order[k_] in riding
                                         and order[k_] not in pinned_v) else 0)
                     for k_ in range(len(order))]
                if delta > 0:
                    new_tip = cr['chain_r0'] + new_K - 1
                    for k_ in range(len(n)):
                        if order[k_] in pinned_v:
                            n[k_] = rs[k_]
                            continue
                        if rs[k_] > ktip:
                            n[k_] = max(n[k_], new_tip + 2)
                        if k_ > 0:
                            n[k_] = max(n[k_], n[k_ - 1] + 6)
                    cap2 = cr['blk_rmax']
                    for k_ in range(len(n) - 1, -1, -1):
                        if order[k_] in pinned_v:
                            n[k_] = rs[k_]
                        else:
                            n[k_] = min(n[k_], cap2)
                        cap2 = n[k_] - 6
                else:
                    for k_ in range(len(n) - 1, -1, -1):
                        if order[k_] in pinned_v:
                            n[k_] = rs[k_]
                            continue
                        if k_ < len(n) - 1:
                            n[k_] = min(n[k_], n[k_ + 1] - 6)
                    floor = cr['chain_r0'] + 2
                    for k_ in range(len(n)):
                        if order[k_] in pinned_v:
                            n[k_] = rs[k_]
                        else:
                            n[k_] = max(n[k_], floor)
                        floor = n[k_] + 6
                for k_, i in enumerate(order):
                    v, r0, c0 = blocks[i]
                    blocks[i] = (v, n[k_], c0)
            KL = new_K
    return (top, L, cc0, KL, active, blocks), dead, True


def render(g, S, bar_k, ly):
    top, L, cc0, KL, active, blocks = S
    cr = ly['crane']
    rlo = 2 if cr else min(ly['pan'][0], ly['top_min'])
    rhi = max(ly['pan'][1], ly['top_max'] + 5)
    for r in range(rlo, rhi + 1):
        for c in range(64):
            g[r][c] = bg_color(r, c, ly)
    ec0, ec1 = ly['ec0'], ly['ec1']
    eact = active == 6
    for r in range(top, top + 6):
        for c in range(ec0, ec1 + 1):
            border = r in (top, top + 5) or c in (ec0, ec1)
            g[r][c] = 6 if border else (0 if eact else 4)
    for r in (top + 2, top + 3):
        for c in (ec0 + 2, ec0 + 3):
            g[r][c] = 6
    for (rtop, rbot, cc, _anc) in ly['vropes']:
        for r in range(rtop, rbot + 1):
            a, b = V_TEX[(r - rtop) % 3]
            g[r][cc] = a + 1
            g[r][cc + 1] = b + 1
    if cr and cc0 is not None:
        cact = not eact
        col = cr['color']
        b0 = cr['box_r0']
        for r in range(b0, b0 + 6):
            for c in range(cc0, cc0 + 6):
                border = r in (b0, b0 + 5) or c in (cc0, cc0 + 5)
                g[r][c] = col if border else (0 if cact else 4)
        for r in cr['htr']:
            for c in (cc0 + 2, cc0 + 3):
                g[r][c] = col
        off = 0 if cact else 1
        for r in range(cr['chain_r0'], cr['chain_r0'] + KL):
            a, b = V_TEX[(r - cr['chain_r0']) % 3]
            g[r][cc0 + 2] = a + off
            g[r][cc0 + 3] = b + off
    off = 0 if eact else 1
    for c in range(ec1, ec1 + L):
        a, b = H_TEX[(c - ec1) % 3]
        g[top + 2][c] = a + off
        g[top + 3][c] = b + off
    for v, r0, c0 in blocks:
        for r in range(r0, r0 + 4):
            for c in range(c0, c0 + 4):
                if 0 <= r < 64 and 0 <= c < 64:
                    g[r][c] = v
    d = ly['div']
    for c in range(64):
        g[d][c] = 3 if c >= 64 - bar_k else 2
    for grp in ly['groups']:
        holder, seq, interior, ropecells = grp
        togglable = holder == 6 or (cr and holder == cr['color'])
        if togglable:
            hact = holder == active
            for (r, c) in interior:
                g[r][c] = 0 if hact else 4
            for (r, c, base) in ropecells:
                g[r][c] = base + (0 if hact else 1)
        lst = holder_list(ly, S, holder)
        for k, (colr, pcc) in enumerate(seq):
            match = k < len(lst) and lst[k] == colr
            h1, h2 = ly['pic_hrows']
            for r in (h1, h2):
                for c in (pcc + 1, pcc + 2):
                    g[r][c] = 0 if match else colr
    return goal_satisfied(ly, S)


def predict(state, grid, action, x=None, y=None):
    ly = layout(ENTRY_GRID)
    g = [row[:] for row in grid]
    st = dict(state)
    info = {'level_up': False, 'dead': False, 'win': False}
    S = extract(g, ly)
    S2, dead, counts = abstract_step(ly, S, action, x, y)
    if action not in (6, 7):  # clicks AND a7 are free (no budget tick; t#192)
        if not st.get('synced', True):
            if not grids_equal(grid, ENTRY_GRID):
                st['acts'] = st.get('acts', 0) + 1
            st['synced'] = True
        st['acts'] = st.get('acts', 0) + 1
    # budget bar: T/196 of the level budget, rendered in 64ths (bar=floor(T*16/49);
    # fits ALL flips incl. the gap-4 every 16 flips — t#244/#294 explained)
    bar_k = (st.get('acts', 0) * 16) // 49
    info['dead'] = dead
    if render(g, S2, bar_k, ly):
        info['level_up'] = True
    return g, info, st


def is_goal(state, grid):
    ly = layout(ENTRY_GRID)
    return goal_satisfied(ly, extract(grid, ly))
