import numpy as np
from collections import deque

# ===================== General model: mover + SPRINGS + N-STATE ghosts =====================
# MOVER: 5x5 9-ring (center hole), moves PITCH=6/tile. 1=up 2=down 3=left 4=right. Hole-aware.
# SPRING (8): HANDLE-block(3-wide,no cap)+STEM+HEAD-block(5x5,858585 cap). COMPRESSED iff mover OR
#   any ghost occupies the HANDLE-TILE -> head shifts 6 toward handle; REVEAL halo (wall neighbours->5).
# action5 = teleport mover to START + ADVANCE legend state (cycle mod n_states), IF moved since last
#   toggle. LEGEND has n_states slots: slot<active = 2-ring (a recorded ghost), slot==active = 9-ring,
#   slot>active = 1-solid (unrecorded). Row5 indicator under the active slot.
# GHOSTS: each state s != active that has a recording spawns a ghost replaying recordings[s], synced to
#   current-state move count k (pos = rec[min(k,len-1)]); freezes at end; overlay; HOLDS springs.
# COUNTER: row63 fills from RIGHT with 1; = floor(n_actions/2). Resets on RESET.
# WIN: mover (tracked) lands on GOAL tile = (peg-2,peg-2); peg = isolated 9 (all-5 neighbours).

PITCH = 6; SIZE = 5
_NEIGH8 = ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))
_DIRS = {1:(-PITCH,0), 2:(PITCH,0), 3:(0,-PITCH), 4:(0,PITCH)}
_R9 = ((9,9,9),(9,0,9),(9,9,9)); _R2 = ((2,2,2),(2,0,2),(2,2,2)); _R1 = ((1,1,1),(1,1,1),(1,1,1))

def _comps(g, val):
    H, W = g.shape; seen = np.zeros((H, W), bool); out = []
    for y in range(H):
        for x in range(W):
            if g[y, x] == val and not seen[y, x]:
                q = deque([(y, x)]); seen[y, x] = True; cs = [(y, x)]
                while q:
                    cy, cx = q.popleft()
                    for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                        ny, nx = cy+dy, cx+dx
                        if 0<=ny<H and 0<=nx<W and g[ny,nx]==val and not seen[ny,nx]:
                            seen[ny,nx]=True; q.append((ny,nx)); cs.append((ny,nx))
                out.append(cs)
    return out

def _snap(lo, hi):
    for r in range(8, 60, 6):
        if r <= lo and r+4 >= hi: return r
    return None

def _analyze_spring(cells, color):
    # HEAD(5-wide cross-section, maybe 858585 cap) + STEM(1-wide) + HANDLE(3-wide). Color 8 or 11, any
    # orientation. Head shifts 6 TOWARD the handle when the handle-tile is occupied.
    # color 8 = spring-back (compressed only while handle-tile occupied).
    # color 11 = RATCHET (once pushed, head stays; handle re-forms when the mover leaves).
    # Three renderings: 'cells'(original) / 'comp'(head moved, handle consumed by mover) /
    #                   'rest1'(head moved, handle re-formed) [ratchet, mover off handle].
    cells = set(cells); ys=[p[0] for p in cells]; xs=[p[1] for p in cells]
    y0,y1,x0,x1 = min(ys),max(ys),min(xs),max(xs)
    vertical = (y1-y0) >= (x1-x0)
    if vertical:
        p0, p1 = x0, x1; cperp = (x0+x1)//2; lo, hi = y0, y1
        headpos = [y for y in range(y0,y1+1) if (y,p0) in cells and (y,p1) in cells]
        axc = lambda p: p[0]
        mk = lambda a: (a, cperp)
        shift = lambda p, d: (p[0]+d, p[1])
    else:
        p0, p1 = y0, y1; cperp = (y0+y1)//2; lo, hi = x0, x1
        headpos = [x for x in range(x0,x1+1) if (p0,x) in cells and (p1,x) in cells]
        axc = lambda p: p[1]
        mk = lambda a: (cperp, a)
        shift = lambda p, d: (p[0], p[1]+d)
    if not headpos: return None
    h0, h1 = min(headpos), max(headpos)
    head_at_min = (h0 == lo)
    d = 6 if head_at_min else -6
    head_cells = set(p for p in cells if h0 <= axc(p) <= h1)
    shifted = set(shift(p, d) for p in head_cells)
    nh0, nh1 = h0+d, h1+d
    if head_at_min: ha0, ha1 = hi-2, hi      # handle at high end
    else:           ha0, ha1 = lo, lo+2      # handle at low end
    handle_cells = set(p for p in cells if ha0 <= axc(p) <= ha1)
    if vertical: ht = (_snap(ha0, ha1), _snap(p0+1, p1-1))
    else:        ht = (_snap(p0+1, p1-1), _snap(ha0, ha1))
    if ht[0] is None or ht[1] is None: return None
    ht_ax = ht[0] if vertical else ht[1]
    comp = set(shifted)
    if head_at_min:
        for a in range(nh1+1, ht_ax): comp.add(mk(a))
    else:
        for a in range(ht_ax+5, nh0): comp.add(mk(a))
    rest1 = set(shifted) | set(handle_cells)
    if head_at_min:
        for a in range(nh1+1, ha0): rest1.add(mk(a))
    else:
        for a in range(ha1+1, nh0): rest1.add(mk(a))
    a_on = set(head_cells)   # toggle state A (head at original) but mover ON handle (handle consumed)
    if head_at_min:
        for a in range(h1+1, ht_ax): a_on.add(mk(a))
    else:
        for a in range(ht_ax+5, h0): a_on.add(mk(a))
    return {'cells':cells, 'comp':comp, 'rest1':rest1, 'a_on':a_on, 'htile':ht, 'color':color}

def _springs(entry):
    out = []
    for color in (8, 11):
        for c in _comps(entry, color):
            sp = _analyze_spring(c, color)
            if sp is not None: out.append(sp)
    return out

def _sp_cells(sp, occ, toggle):
    # cells (8/11) this spring occupies. color 8 = spring-back; color 11 = persistent TOGGLE
    # (each entry into the handle-tile flips state 0<->1). on = mover/ghost currently on handle-tile.
    on = sp['htile'] in occ
    if sp['color'] == 11:
        if toggle.get(sp['htile'], 0) == 0:
            return sp['a_on'] if on else sp['cells']      # state A: head at original position
        return sp['comp'] if on else sp['rest1']          # state B: head shifted 6 toward handle
    return sp['comp'] if on else sp['cells']               # color 8: compressed only while held

def _ring_pattern(entry):
    for c in _comps(entry, 9):
        ys=[p[0] for p in c]; xs=[p[1] for p in c]
        if max(ys)-min(ys)==4 and max(xs)-min(xs)==4 and min(ys)>=7:
            y0,x0=min(ys),min(xs)
            return [(p[0]-y0, p[1]-x0) for p in c], (y0,x0)
    return [(i,j) for i in range(5) for j in range(5) if (i,j)!=(2,2)], (8,14)

def _find_mover(g):
    for c in _comps(g, 9):
        ys=[p[0] for p in c]; xs=[p[1] for p in c]
        if max(ys)-min(ys)==4 and max(xs)-min(xs)==4 and min(ys)>=7:
            return (min(ys), min(xs))
    return None

def _find_peg(g):
    H, W = g.shape
    for y in range(7, min(57, H-1)):
        for x in range(7, min(57, W-1)):
            if g[y, x] == 9 and all(g[y+dy, x+dx] == 5 for dy, dx in ((-1,0),(1,0),(0,-1),(0,1))):
                return (y, x)
    return None

def _has_legend(g):
    try:
        return (g[1,1] in (9,2) and g[2,2]==0 and g[1,3] in (9,2) and g[3,1] in (9,2))
    except Exception:
        return False

def _n_states(g):
    n = 0
    for sx in (1,5,9,13):
        try:
            if int(g[1,sx]) in (9,2,1): n += 1
        except Exception:
            break
    return max(2, n)

def _entry():
    try: return np.array(ENTRY_GRID)
    except Exception: return None

def _f_cells(entry):
    return [(int(y),int(x)) for (y,x) in np.argwhere(np.array(entry) == 15)]

def _base(entry, pat, start):
    b = entry.copy()
    for sp in _springs(entry):
        for (y,x) in sp['cells']: b[y,x] = 5
    for (y,x) in _f_cells(entry): b[y,x] = 5   # color-15 'f' = passable OVERLAY over corridor
    for (di,dj) in pat: b[start[0]+di, start[1]+dj] = 5
    return b

def _render_legend(out, n_states, active):
    for i in range(n_states):
        sx = 1 + 4*i
        pat = _R2 if i < active else (_R9 if i == active else _R1)
        for r in range(3):
            for c in range(3):
                out[1+r, sx+c] = pat[r][c]
        for c in range(3):
            out[5, sx+c] = 9 if i == active else 0

def init_state(entry_grid):
    g = np.array(entry_grid)
    pat, start = _ring_pattern(g)
    m = _find_mover(g)
    if m is not None: start = m
    peg = _find_peg(g)
    goal = (peg[0]-2, peg[1]-2) if peg is not None else None
    return {'n_actions':0, 'legend':0, 'has_legend':_has_legend(g), 'n_states':_n_states(g),
            'start':start, 'goal':goal, 'cur':[start], 'recordings':{}, 'k':0,
            'toggle':[], 'occ11':[], 'eaten':[]}   # eaten: color-15 cells the mover erased (permanent)

def _spring_cells(springs, occupied, ratcheted):
    s = set()
    for sp in springs:
        s |= _sp_cells(sp, occupied, ratcheted)
    return s

def _can_move(base, springs, pat, mover, ghosts, ratcheted, action):
    H, W = base.shape
    dy, dx = _DIRS[action]; ny, nx = mover[0]+dy, mover[1]+dx
    if ny<0 or nx<0 or ny+SIZE>H or nx+SIZE>W: return None
    occ = set(ghosts) | {(ny,nx)}
    sc = _spring_cells(springs, occ, ratcheted)
    gc = set()
    for gp in ghosts:
        for (di,dj) in pat: gc.add((gp[0]+di, gp[1]+dj))
    for (di,dj) in pat:
        cy, cx = ny+di, nx+dj
        if (cy,cx) in gc: continue
        if (cy,cx) in sc: return None
        if base[cy,cx] != 5: return None   # 'f' already cleared to 5 in base
    return (ny, nx)

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid); info = {"level_up":False, "dead":False, "win":False}
    entry = _entry()
    if entry is None: entry = g
    recs = {}
    for k0, v in state.get('recordings', {}).items():
        recs[int(k0)] = [tuple(p) for p in v]
    st = {'n_actions':state.get('n_actions',0),
          'legend':state.get('legend',0),
          'has_legend':state.get('has_legend',_has_legend(g)),
          'n_states':state.get('n_states',_n_states(np.array(entry))),
          'start':tuple(state.get('start',(8,14))),
          'goal':state.get('goal',None),
          'cur':[tuple(p) for p in state.get('cur',[])],
          'recordings':recs,
          'k':state.get('k',0),
          'toggle':{tuple(h):s for h,s in state.get('toggle',[])},
          'occ11':set(tuple(p) for p in state.get('occ11',[])),
          'eaten':set(tuple(p) for p in state.get('eaten',[]))}
    if not st['cur']: st['cur'] = [st['start']]
    if st['goal'] is None:
        pg = _find_peg(np.array(entry)); st['goal'] = (pg[0]-2, pg[1]-2) if pg is not None else None
    else:
        st['goal'] = tuple(st['goal'])
    st['n_actions'] += 1

    pat, _ = _ring_pattern(entry)
    springs = _springs(entry)
    base = _base(entry, pat, st['start'])
    H, W = g.shape
    mover = _find_mover(g)
    if mover is None: mover = st['cur'][-1]

    def ghosts_at(k):
        return [st['recordings'][s][min(k, len(st['recordings'][s])-1)]
                for s in st['recordings'] if s != st['legend']]

    new_mover = mover
    if action in _DIRS:
        st['k'] += 1
        gs = ghosts_at(st['k'])
        nm = _can_move(base, springs, pat, mover, gs, st['toggle'], action)
        if nm is not None: new_mover = nm
        st['cur'].append(new_mover)
        cur_ghosts = gs
    elif action == 5:
        if len(st['cur']) > 1:  # moved since last toggle
            st['recordings'][st['legend']] = st['cur'][:]
            st['legend'] = (st['legend'] + 1) % st['n_states']
            new_mover = st['start']; st['cur'] = [st['start']]; st['k'] = 0
            st['toggle'] = {}; st['occ11'] = set()   # teleport RESETS color-11 toggles to A (original)
        cur_ghosts = ghosts_at(st['k'])
    else:
        cur_ghosts = ghosts_at(st['k'])

    # color-11 TOGGLE: flip on the rising edge of handle-tile occupancy (mover/ghost enters it)
    occ = set(cur_ghosts) | {new_mover}
    occ11_now = set()
    for sp in springs:
        if sp['color'] == 11 and sp['htile'] in occ:
            occ11_now.add(sp['htile'])
            if sp['htile'] not in st['occ11']:
                st['toggle'][sp['htile']] = 1 - st['toggle'].get(sp['htile'], 0)
    st['occ11'] = occ11_now

    # ---------- render ----------
    out = base.copy()
    # color-15 'f' overlay: 'f' cells show 15 EXCEPT where the mover/ghost footprint covers them
    # (the mover walks THROUGH 'f' as passable terrain; 'f' reverts when the mover leaves)
    foot = set()
    for (di,dj) in [(i,j) for i in range(SIZE) for j in range(SIZE)]:
        foot.add((new_mover[0]+di, new_mover[1]+dj))
        for gp in cur_ghosts: foot.add((gp[0]+di, gp[1]+dj))
    for (cy,cx) in _f_cells(entry):
        if (cy,cx) not in foot: out[cy,cx] = 15
    all_cells = set(); reveal_lists = []
    for sp in springs:
        cells = _sp_cells(sp, occ, st['toggle'])
        for (cy,cx) in cells: out[cy,cx] = sp['color']
        all_cells |= set(cells)
        if cells is not sp['cells']: reveal_lists.append(cells)
    for cells in reveal_lists:
        for (cy,cx) in cells:
            for (dy,dx) in _NEIGH8:
                ny,nx = cy+dy, cx+dx
                if 0<=ny<H and 0<=nx<W and base[ny,nx]==0 and (ny,nx) not in all_cells:
                    out[ny,nx] = 5
    for gp in cur_ghosts:
        for (di,dj) in pat:
            yy,xx = gp[0]+di, gp[1]+dj
            if 0<=yy<H and 0<=xx<W: out[yy,xx] = 2
    for (di,dj) in pat:
        yy,xx = new_mover[0]+di, new_mover[1]+dj
        if 0<=yy<H and 0<=xx<W: out[yy,xx] = 9

    if st['has_legend']:
        _render_legend(out, st['n_states'], st['legend'])
        cnt = st['n_actions'] // 2
        for k in range(cnt):
            if W-1-k >= 0: out[H-1, W-1-k] = 1

    if st['goal'] is not None and tuple(new_mover) == st['goal']:
        info['level_up'] = True   # clearing a level; 'win' only on the final level
        try:
            info['win'] = (CURRENT_LEVEL == 6)
        except Exception:
            info['win'] = False

    st['toggle'] = [[list(h), s] for h, s in st['toggle'].items()]  # picklable
    st['occ11'] = [list(p) for p in st['occ11']]
    st['eaten'] = [list(p) for p in st['eaten']]
    return out.tolist(), info, st

def is_goal(state, grid):
    if isinstance(state, dict):
        goal = state.get('goal'); cur = state.get('cur')
        if goal is not None and cur:
            return tuple(cur[-1]) == tuple(goal)
        if goal is not None:
            m = _find_mover(np.array(grid))
            return m is not None and tuple(m) == tuple(goal)
    return False
