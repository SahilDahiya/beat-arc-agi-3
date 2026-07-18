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

def _analyze_spring(cells):
    cells = set(cells); ys=[p[0] for p in cells]; xs=[p[1] for p in cells]
    x0,x1=min(xs),max(xs); cx=(x0+x1)//2; y0,y1=min(ys),max(ys)
    if (x1-x0) != 4: return None
    caprow=None
    for y in range(y0, y1+1):
        if set(x for (yy,x) in cells if yy==y) == {x0, x0+2, x0+4}: caprow=y
    if caprow is None: return None
    hd = 1 if (caprow+1, cx) in cells else -1
    hr = sorted(caprow+hd*k for k in range(5)); hy0,hy1 = hr[0],hr[-1]
    head_top = (hy0 == y0)
    handle = (y1-2, y1) if head_top else (y0, y0+2)
    htile = (_snap(handle[0], handle[1]), _snap(x0+1, x1-1))
    comp = set(); d = 6 if head_top else -6
    for (y,x) in cells:
        if hy0 <= y <= hy1: comp.add((y+d, x))
    nhy0, nhy1 = hy0+d, hy1+d; ht_y = htile[0]
    if head_top:
        for y in range(nhy1+1, ht_y): comp.add((y, cx))
    else:
        for y in range(ht_y+5, nhy0): comp.add((y, cx))
    return {'cells':cells, 'comp':comp, 'htile':htile}

def _springs(entry):
    out = []
    for c in _comps(entry, 8):
        sp = _analyze_spring(c)
        if sp is not None: out.append(sp)
    return out

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

def _base(entry, pat, start):
    b = entry.copy()
    for sp in _springs(entry):
        for (y,x) in sp['cells']: b[y,x] = 5
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
            'start':start, 'goal':goal, 'cur':[start], 'recordings':{}, 'k':0}

def _spring_cells(springs, occupied):
    s = set()
    for sp in springs:
        s |= (sp['comp'] if sp['htile'] in occupied else sp['cells'])
    return s

def _can_move(base, springs, pat, mover, ghosts, action):
    H, W = base.shape
    dy, dx = _DIRS[action]; ny, nx = mover[0]+dy, mover[1]+dx
    if ny<0 or nx<0 or ny+SIZE>H or nx+SIZE>W: return None
    occ = set(ghosts) | {(ny,nx)}
    sc = _spring_cells(springs, occ)
    gc = set()
    for gp in ghosts:
        for (di,dj) in pat: gc.add((gp[0]+di, gp[1]+dj))
    for (di,dj) in pat:
        cy, cx = ny+di, nx+dj
        if (cy,cx) in gc: continue
        if (cy,cx) in sc: return None
        if base[cy,cx] != 5: return None
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
          'k':state.get('k',0)}
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
        nm = _can_move(base, springs, pat, mover, gs, action)
        if nm is not None: new_mover = nm
        st['cur'].append(new_mover)
        cur_ghosts = gs
    elif action == 5:
        if len(st['cur']) > 1:  # moved since last toggle
            st['recordings'][st['legend']] = st['cur'][:]
            st['legend'] = (st['legend'] + 1) % st['n_states']
            new_mover = st['start']; st['cur'] = [st['start']]; st['k'] = 0
        cur_ghosts = ghosts_at(st['k'])
    else:
        cur_ghosts = ghosts_at(st['k'])

    # ---------- render ----------
    out = base.copy()
    occ = set(cur_ghosts) | {new_mover}
    all8 = set(); reveal_lists = []
    for sp in springs:
        comp = sp['htile'] in occ
        c8 = sp['comp'] if comp else sp['cells']
        all8 |= set(c8)
        if comp: reveal_lists.append(c8)
    for (cy,cx) in all8: out[cy,cx] = 8
    for c8 in reveal_lists:
        for (cy,cx) in c8:
            for (dy,dx) in _NEIGH8:
                ny,nx = cy+dy, cx+dx
                if 0<=ny<H and 0<=nx<W and base[ny,nx]==0 and (ny,nx) not in all8:
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
        info['win'] = True; info['level_up'] = True

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
