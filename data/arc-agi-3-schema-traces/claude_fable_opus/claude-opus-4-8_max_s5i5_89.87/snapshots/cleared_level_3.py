# world_model_v5 — ARC3 game s5i5.
# Dispatch: if ENTRY_GRID contains color 15 (f) -> LEVEL-1 "chain-push" mechanic; else LEVEL-0 bars.
#
# LEVEL 0: two template bars (block-color rect + 13 pointer + '3' handle); control boxes grow/shrink
#   value by +-3 (vertical divider: left=-, right=+). Dock each pointer into its aligned diamond center
#   => win. Counter (row 63) irrelevant.
#
# LEVEL 1: four bars c(12),a(10),b(11),e(14) in a CHAIN c->a->b->e. Growing a bar (+3) extends it in its
#   growth dir and SHIFTS all downstream bars by 3 in that dir. Dirs: c=+x, a=-y(up), b=+x, e=+y(down).
#   Only e has a pointer (bottom-center). 4 boxes (color-2, vertical divider): box of color X, RIGHT
#   subcell = grow X +3, LEFT = shrink X -3 (min length 2). Pointer moves as a point: +x(b/c right),
#   -x(b/c left), -y(a right / e left), +y(a left / e right). Counter row63 +1 only on b/c GROW.
#   GOAL (hypothesis): pointer reaches the diamond center. WALL behavior of 'f' frame: UNTESTED
#   (this model does NOT block on walls yet — used to march & discover wall behavior).
import numpy as np
from collections import deque

def _grid_np(g): return np.array(g, dtype=int)

# ------------------------- shared helpers -------------------------
def _find_boxes(g):
    H, W = g.shape
    seen = np.zeros_like(g, bool); boxes = []
    for y in range(H):
        for x in range(W):
            if g[y,x]==2 and not seen[y,x]:
                q=deque([(y,x)]); seen[y,x]=1; cells=[(y,x)]
                while q:
                    cy,cx=q.popleft()
                    for dy in (-1,0,1):
                        for dx in (-1,0,1):
                            ny,nx=cy+dy,cx+dx
                            if 0<=ny<H and 0<=nx<W and not seen[ny,nx] and g[ny,nx]==2:
                                seen[ny,nx]=1; q.append((ny,nx)); cells.append((ny,nx))
                ys=[c[0] for c in cells]; xs=[c[1] for c in cells]
                boxes.append((min(ys),min(xs),max(ys),max(xs)))
    return boxes

# ------------------------- LEVEL 0 -------------------------
def _find_template(g, block_color):
    H, W = g.shape
    ptr = None
    for py, px in zip(*np.where(g == 13)):
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = py+dy, px+dx
            if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == block_color:
                ptr = (py, px); break
        if ptr: break
    if ptr is None: return None
    start = None
    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
        ny, nx = ptr[0]+dy, ptr[1]+dx
        if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == block_color:
            start = (ny, nx); break
    if start is None: return None
    seen = {start}; q = deque([start]); block = [start]
    while q:
        cy, cx = q.popleft()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ny, nx = cy+dy, cx+dx
                if 0 <= ny < H and 0 <= nx < W and (ny,nx) not in seen and g[ny,nx] == block_color:
                    seen.add((ny,nx)); q.append((ny,nx)); block.append((ny,nx))
    bys = [c[0] for c in block]; bxs = [c[1] for c in block]
    y0,y1,x0,x1 = min(bys),max(bys),min(bxs),max(bxs)
    if (x1-x0) >= (y1-y0):
        axis='h'; cross=list(range(y0,y1+1)); center=(y0+y1)//2
        left3 = any(x0-1>=0 and g[y,x0-1]==3 for y in cross)
        anchor = x0 if left3 else x1; grow = 1 if left3 else -1
    else:
        axis='v'; cross=list(range(x0,x1+1)); center=(x0+x1)//2
        top3 = any(y0-1>=0 and g[y0-1,x]==3 for x in cross)
        anchor = y0 if top3 else y1; grow = 1 if top3 else -1
    return dict(color=block_color, axis=axis, cross=cross, center=int(center),
                anchor=int(anchor), grow=int(grow))

def _measure(g, t):
    H, W = g.shape
    for py, px in zip(*np.where(g == 13)):
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = py+dy, px+dx
            if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == t['color']:
                coord = px if t['axis']=='h' else py
                return (coord - t['anchor']) * t['grow']
    return None

def _draw(g, t, v):
    old = _measure(g, t)
    if old is not None:
        for k in range(old+2):
            p = t['anchor'] + t['grow']*k
            for c in t['cross']:
                if t['axis']=='h': g[c, p] = 5
                else: g[p, c] = 5
    for k in range(v+2):
        p = t['anchor'] + t['grow']*k
        for c in t['cross']:
            val = t['color']
            if k == v and c == t['center']: val = 13
            if t['axis']=='h': g[c, p] = val
            else: g[p, c] = val

def _build_controls_l0(g):
    controls=[]
    for (y0,x0,y1,x1) in _find_boxes(g):
        interior = g[y0+1:y1, x0+1:x1]
        col=None
        for cc in (14,11):
            if (interior==cc).any(): col=cc; break
        if col is None: continue
        d3 = np.argwhere(interior==3)
        if len(d3)==0: continue
        cols3=set(d3[:,1].tolist()); rows3=set(d3[:,0].tolist())
        vertical = len(cols3)<=1 and len(rows3)>1
        controls.append(dict(col=col, box=(int(y0),int(x0),int(y1),int(x1)),
                             vertical=bool(vertical), cx=(x0+x1)//2, cy=(y0+y1)//2))
    return controls

def _is_triangular(k):
    if k <= 0: return False
    s = 8*k+1; r = int(s**0.5)
    return r*r==s or (r+1)*(r+1)==s

def _step_l0(grid, action, x, y):
    g = _grid_np(grid).copy()
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None: return g, info
    entry = _grid_np(ENTRY_GRID)
    tpl={}
    for cc in (14,11):
        t=_find_template(entry, cc)
        if t is not None: tpl[cc]=t
    ctrl=_build_controls_l0(entry)
    if not ctrl: return g, info
    chosen=None
    for c in ctrl:
        y0,x0,y1,x1=c['box']
        if y0<=y<=y1 and x0<=x<=x1: chosen=c; break
    if chosen is None: return g, info
    t = tpl.get(chosen['col'])
    if t is None: return g, info
    v0 = _measure(g, t)
    if v0 is None: return g, info
    delta = (-3 if x < chosen['cx'] else 3) if chosen['vertical'] else (-3 if y < chosen['cy'] else 3)
    v1 = max(0, v0 + delta)
    _draw(g, t, v1)
    lit = int((g[63]==4).sum())
    lit += 1
    if lit % 9 in (2, 7): lit += 1
    lit = min(lit, g.shape[1])
    g[63,:] = 3
    if lit>0: g[63, g.shape[1]-lit:] = 4
    return g, info

# ------------------------- LEVEL 1 -------------------------
# Base constants derived from ENTRY (state0): all bars minimum length 2.
#  c: color12, left x=10, rows y39-41, grows +x.   handle x9 y39-41.
#  a: color10, base x12 (3 wide), bottom y40, grows -y. handle y41.
#  b: color11, base x13, top y36 (3 tall), grows +x.    handle x=left-1.
#  e: color14, base x15 (3 wide), top y37, grows +y.    handle y=top-1.  pointer bottom-center.
# Positions vs lengths (b,c,a,e):  a_x=12+(c-2); b_x=13+(c-2), b_top=36-(a-2);
#  e_x=15+(b-2)+(c-2), e_top=37-(a-2); pointer=(e_x+1, e_top+e-2).
_L1_BOXES = {12:(3,15), 10:(18,30), 11:(33,45), 14:(48,60)}  # color -> (x0,x1)
_L1_CH = {12:'c', 10:'a', 11:'b', 14:'e'}

def _l1_measure(g):
    def ext(cols):
        pts=[(x,y) for y in range(0,53) for x in range(0,64) if g[y][x] in cols]
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        return xs,ys
    xs,ys=ext({12}); c_len=(max(xs)-min(xs)+1) if xs else 2
    xs,ys=ext({10}); a_len=(max(ys)-min(ys)+1) if ys else 2
    xs,ys=ext({11}); b_len=(max(xs)-min(xs)+1) if xs else 2
    xs,ys=ext({14}); e_len=(max(ys)-min(ys)+1) if ys else 2
    return {'b':b_len,'c':c_len,'a':a_len,'e':e_len}

def _l1_diamond(entry):
    # the 13-plus not adjacent to a bar color -> center
    H,W=entry.shape
    dcells=[(x,y) for y in range(H) for x in range(W) if entry[y][x]==13 and not any(
        0<=x+dx<W and 0<=y+dy<H and entry[y+dy][x+dx] in (10,11,12,14)
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)))]
    if not dcells: return None
    xs=[c[0] for c in dcells]; ys=[c[1] for c in dcells]
    return ((min(xs)+max(xs))//2, (min(ys)+max(ys))//2)

def _l1_cells(L):
    # Compute all cells occupied by the 4 bars + their '3' handles + the pointer, for lengths L.
    b_len,c_len,a_len,e_len=L['b'],L['c'],L['a'],L['e']
    cells={}
    for dx in range(c_len):
        for yy in range(39,42): cells[(10+dx,yy)]=12
    for yy in range(39,42): cells[(9,yy)]=3
    a_x=12+(c_len-2)
    for dx in range(3):
        for dy in range(a_len): cells[(a_x+dx,40-dy)]=10
    for dx in range(3): cells[(a_x+dx,41)]=3
    b_x=13+(c_len-2); b_yt=36-(a_len-2)
    for dx in range(b_len):
        for dy in range(3): cells[(b_x+dx,b_yt+dy)]=11
    for dy in range(3): cells[(b_x-1,b_yt+dy)]=3
    e_x=15+(b_len-2)+(c_len-2); e_yt=37-(a_len-2)
    for dx in range(3):
        for dy in range(e_len): cells[(e_x+dx,e_yt+dy)]=14
    for dx in range(3): cells[(e_x+dx,e_yt-1)]=3
    cells[(e_x+1, e_yt+e_len-2)] = 13   # pointer
    return cells

def _l1_render(g, L, entry):
    dia = _l1_diamond(entry)
    diaset=set()
    if dia is not None:
        cx,cy=dia
        diaset={(cx,cy-1),(cx-1,cy),(cx+1,cy),(cx,cy+1)}
    # erase old bars/handles/pointer in rows y<53 (preserve diamond, f(15), boxes)
    for y in range(0,53):
        for x in range(64):
            if (x,y) in diaset: continue
            v=g[y][x]
            if v in (10,11,12,13,14,3): g[y][x]=5
    for (x,y),val in _l1_cells(L).items():
        if 0<=x<64 and 0<=y<64: g[y][x]=val
    return g

def _l1_click_to_bar(cx, cy):
    for col,(x0,x1) in _L1_BOXES.items():
        if x0<=cx<=x1 and 54<=cy<=60:
            return _L1_CH[col], (3 if cx>(x0+x1)//2 else -3)
    return None, 0

def _step_l1(grid, action, x, y):
    # Bars/pointer/walls modelled exactly. COUNTER (row 63) left UNCHANGED (adversarial & cosmetic).
    # Consequence: up/down moves (a/e) match & run in bulk; right moves (b/c) stop at counter increments.
    g = _grid_np(grid).copy()
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None: return g, info
    entry = _grid_np(ENTRY_GRID)
    bar, delta = _l1_click_to_bar(x, y)
    if bar is None: return g, info
    L = _l1_measure(g)
    L2 = dict(L); L2[bar] = max(2, L[bar] + delta)
    if L2[bar] == L[bar]:
        return g, info  # clamped no-op
    # WALL BLOCK: any new bar cell overlapping an 'f'(15) wall or off the playfield (y0..52) => full no-op.
    ys, xs = np.where(entry == 15)
    fcells = set(zip(xs.tolist(), ys.tolist()))
    for (cx, cy) in _l1_cells(L2):
        if cx < 0 or cx > 63 or cy < 0 or cy > 52 or (cx, cy) in fcells:
            return g, info  # wall-blocked no-op
    g = _l1_render(g, L2, entry)   # row 63 COUNTER left UNCHANGED (adversarial/cosmetic; grind through it)
    return g, info

# ------------------------- LEVEL 2 (minimal: a-bar & 7-bar independent growth; obstacles/chain NOT modelled
#   yet — used to probe where bars hit obstacles). a-bar color10 anchor x7 grows +x, 3-tall y27-29, ptr row y28.
#   7-bar color7 anchor y4 grows +y (down), 3-wide x48-50, ptr col x49. bar = [value cells][ptr][1 far cell].
def _l2_measure(g, color, axis, anchor, line):
    # find pointer (13 adjacent to `color`), return value = signed distance along axis from anchor.
    H, W = g.shape
    for py, px in zip(*np.where(g == 13)):
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = py+dy, px+dx
            if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == color:
                coord = px if axis == 'h' else py
                return coord - anchor
    return None

def _l2_draw(g, color, axis, anchor, cross, v):
    old = _l2_measure(g, color, axis, anchor, cross[len(cross)//2])
    if old is not None:
        for k in range(old + 2):
            p = anchor + k
            for c in cross:
                if axis == 'h': g[c, p] = 5
                else: g[p, c] = 5
    for k in range(v + 2):
        p = anchor + k
        for c in cross:
            val = color
            if k == v and c == cross[len(cross)//2]: val = 13
            if axis == 'h': g[c, p] = val
            else: g[p, c] = val

def _step_l2(grid, action, x, y):
    g = _grid_np(grid).copy()
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None: return g, info
    # box-a (x26-38 y45-51) -> a-bar; box-7 (x26-38 y54-60) -> 7-bar. RIGHT subcell (x>32)=grow, else shrink.
    if 26 <= x <= 38 and 45 <= y <= 51:
        color, axis, anchor, cross = 10, 'h', 7, [27, 28, 29]
    elif 26 <= x <= 38 and 54 <= y <= 60:
        color, axis, anchor, cross = 7, 'v', 4, [48, 49, 50]
    else:
        return g, info  # other L2 boxes not modelled yet
    delta = 3 if x > 32 else -3
    v0 = _l2_measure(g, color, axis, anchor, cross[1])
    if v0 is None: return g, info
    v1 = max(0, v0 + delta)
    if v1 == v0: return g, info
    _l2_draw(g, color, axis, anchor, cross, v1)   # counter (row 63) left unmodeled/unchanged (adversarial)
    return g, info

# ------------------------- LEVEL 3 (pointer-dock; predict() w/ state for counter) -------------------------
_L3_OB = {
 'O_9': dict(anchor=52, d=-1, body=(51,52,53), ah=53, handle=17, home=12, bc=9),
 'O_e': dict(anchor=10, d=+1, body=(9,10,11),  ah=9,  handle=20, home=15, bc=14),
 'O_8': dict(anchor=46, d=-1, body=(45,46,47), ah=47, handle=23, home=18, bc=8),
 'O_c': dict(anchor=19, d=+1, body=(18,19,20), ah=18, handle=53, home=24, bc=12),
}
_L3_IDS = ['O_9','O_e','O_8','O_c']
_L3_BOXR = [(45,51,3,15),(45,51,48,60),(54,60,3,15),(51,57,24,37),(54,60,48,60)]
_L3_DIAMOND = [(9,31),(10,30),(10,32),(11,31)]
_L3_CLICK = {(33,54):('grow',None),(27,54):('shrink',None),
 (12,57):('up','O_c'),(6,57):('down','O_c'),(12,48):('up','O_e'),(6,48):('down','O_e'),
 (57,57):('up','O_8'),(51,57):('down','O_8'),(57,48):('up','O_9'),(51,48):('down','O_9')}
_L3_BOXES_BLOCK = False   # HYPOTHESIS: obstacles grow OVER the control boxes. If reality blocks, model diverges at O_c vs box-9.
_L3_BOXSET = set()
for (_y0,_y1,_x0,_x1) in _L3_BOXR:
    for _r in range(_y0,_y1+1):
        for _c in range(_x0,_x1+1): _L3_BOXSET.add((_r,_c))

def _is_l3(entry):
    try:
        return (bool((entry==8).any()) and bool((entry==9).any()) and bool((entry==12).any())
                and bool((entry==14).any()) and not bool((entry==1).any()) and not bool((entry==15).any()))
    except Exception:
        return False

def _l3_bg(entry):
    bg = np.full((64,64),5,dtype=int)
    for (r,c) in _L3_BOXSET: bg[r,c]=int(entry[r,c])
    for (r,c) in _L3_DIAMOND: bg[r,c]=13
    return bg

def _l3_xr(oid,w):
    o=_L3_OB[oid]
    return (o['anchor'],o['anchor']+w-1) if o['d']==1 else (o['anchor']-w+1,o['anchor'])

def _l3_counter(n):
    # adversarial move-counter (row63), DETERMINISTIC in n (stays at n=2,5,7,10,13,16,19,21,24,27,30...).
    tab=[0,1,1,2,3,3,4,4,5,6,6,7,8,8,9,10,10,11,12,12,13,13,14,15,15,16,17,17,18,19,19]
    if n<len(tab): return tab[n]
    return tab[-1] + (2*(n-30))//3

def _l3_render(entry, g, bt, n):
    G=_l3_bg(entry); w=2+3*g; ptop=42-3*g
    for r in range(ptop,44):
        if 0<=r<64:
            for c in (30,31,32): G[r,c]=11
    if 0<=43-3*g<64: G[43-3*g,31]=13
    for c in (30,31,32): G[44,c]=3
    for oid in _L3_IDS:
        o=_L3_OB[oid]; t=bt[oid]; xl,xr=_l3_xr(oid,w)
        for r in range(t,t+3):
            if 0<=r<64:
                for c in range(max(0,xl),min(64,xr+1)): G[r,c]=11
                if 0<=o['ah']<64: G[r,o['ah']]=3
        for r in range(t+3,o['handle']):
            if 0<=r<64:
                for c in o['body']: G[r,c]=o['bc']
        if 0<=o['handle']<64:
            for c in o['body']: G[o['handle'],c]=3
    G[63,:]=3
    cc=_l3_counter(n)
    if cc>0: G[63,64-cc:]=4
    return G

def _l3_occ(g, bt):
    cells={}
    def put(r,c,who):
        if not (0<=r<64 and 0<=c<64): return True
        if _L3_BOXES_BLOCK and (r,c) in _L3_BOXSET: return True
        if (r,c) in cells and cells[(r,c)]!=who: return True
        cells[(r,c)]=who; return False
    w=2+3*g; ptop=42-3*g
    for r in range(ptop,44):
        for c in (30,31,32):
            if put(r,c,'ptr'): return False
    for oid in _L3_IDS:
        o=_L3_OB[oid]; t=bt[oid]; xl,xr=_l3_xr(oid,w)
        for r in range(t,t+3):
            for c in range(xl,xr+1):
                if put(r,c,oid): return False
        for r in range(t+3,o['handle']):
            for c in o['body']:
                if put(r,c,oid): return False
    for (r,c) in _L3_DIAMOND:
        if (r,c) in cells and not (cells.get((r,c))=='ptr' and g==11): return False
    return True

def _predict_l3(state, grid, action, x, y):
    homes={o:_L3_OB[o]['home'] for o in _L3_IDS}
    g=int(state.get('g',0)); bt=dict(state.get('bt',homes)); n=int(state.get('n',0))
    entry=_grid_np(ENTRY_GRID)
    info={'level_up':False,'dead':False,'win':False}
    nn=n+1
    if action==6 and (x,y) in _L3_CLICK:
        kind,oid=_L3_CLICK[(x,y)]
        if kind=='grow':
            if g<11 and _l3_occ(g+1,bt):
                g+=1
                if g==11: info['win']=True
        elif kind=='shrink':
            if g>0: g-=1
        else:
            nb=dict(bt); nb[oid]=bt[oid]+(-3 if kind=='up' else 3); o=_L3_OB[oid]
            if nb[oid]>=0 and nb[oid]+2<o['handle'] and _l3_occ(g,nb):
                bt=nb
    ns={'g':g,'bt':bt,'n':nn,'l3':True}
    return _l3_render(entry,g,bt,nn).tolist(), info, ns

# ------------------------- dispatch -------------------------
def _step_012(grid, action, x=None, y=None):
    try:
        entry = _grid_np(ENTRY_GRID)
        is_l2 = bool((entry == 1).any())   # only L2 entry has color 1 (blue)
        is_l1 = bool((entry == 15).any())
    except Exception:
        is_l2 = is_l1 = False
    if is_l2:
        return _step_l2(grid, action, x, y)
    if is_l1:
        return _step_l1(grid, action, x, y)
    return _step_l0(grid, action, x, y)

def init_state(entry_grid=None):
    entry=None
    if entry_grid is not None:
        try: entry=_grid_np(entry_grid)
        except Exception: entry=None
    if entry is None:
        try: entry=_grid_np(ENTRY_GRID)
        except Exception: entry=None
    if entry is not None and _is_l3(entry):
        return {'g':0,'bt':{o:_L3_OB[o]['home'] for o in _L3_IDS},'n':0,'l3':True}
    return {}

def predict(state, grid, action, x=None, y=None):
    if state is None: state={}
    try:
        entry=_grid_np(ENTRY_GRID); l3=_is_l3(entry)
    except Exception:
        l3=False
    if state.get('l3') or l3:
        return _predict_l3(state, grid, action, x, y)
    g,info=_step_012(grid,action,x,y)
    return (g.tolist() if hasattr(g,'tolist') else g), info, state

def is_goal(state, grid=None):
    if grid is None:  # called as is_goal(grid)
        grid=state
    g=_grid_np(grid)
    try:
        entry=_grid_np(ENTRY_GRID)
    except Exception:
        return False
    if _is_l3(entry):
        return bool(g[10,31]==13 and g[9,31]==11)
    if not (entry == 15).any():
        return False
    dia = _l1_diamond(entry)
    if dia is None: return False
    H,W=g.shape
    for py,px in zip(*np.where(g==13)):
        if any(0<=px+dx<W and 0<=py+dy<H and g[py+dy][px+dx]==14 for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))):
            return (int(px),int(py))==(int(dia[0]),int(dia[1]))
    return False
