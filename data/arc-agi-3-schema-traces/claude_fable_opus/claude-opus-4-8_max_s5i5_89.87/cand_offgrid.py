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

# ------------------------- LEVEL 4 (linkage; predict w/ state) -------------------------
_L4_WALLS=set()
for (_y0,_y1,_x0,_x1) in [(9,17,15,17),(21,26,15,17),(36,38,36,38)]:
    for _r in range(_y0,_y1+1):
        for _c in range(_x0,_x1+1): _L4_WALLS.add((_r,_c))
_L4_CLICK={(27,57):('c',1),(21,57):('c',-1),(42,57):('e',1),(36,57):('e',-1),
           (12,57):('n',1),(6,57):('n',-1),(57,57):('a',1),(51,57):('a',-1)}
_L4_RING=[(24,37),(25,36),(25,38),(26,37)]  # a-diamond ring: FIXED & PASSABLE (9-bar goes around it)

def _is_l4(entry):
    try:
        return bool((entry==1).any()) and bool((entry==15).any())
    except Exception:
        return False

def _l4_bg(entry):
    bg=entry.copy()
    for (y0,y1,x0,x1) in [(6,8,9,11),(6,8,42,44),(9,11,9,11),(30,32,33,56),(30,47,30,32),(30,35,54,56),(24,26,21,45)]:
        for r in range(y0,y1+1):
            for c in range(x0,x1+1): bg[r,c]=5
    return bg

def _l4_rects(c,e,n,a):
    d={'lc':(7,8+3*c,9,11),'rc':(7,8+3*c,42,44),'e':(9+3*c,11+3*c,9,11+3*e),
       'b9':(30-3*e,32-3*e,33-3*n,56),'blue':(30-3*e,47-3*e,30-3*n,32-3*n),'eb':(33-3*e,35,54,56)}
    ar=38+3*a
    if ar>=22: d['abar']=(24,26,22,ar)   # a-bar (ring x36-38 PASSABLE, excluded)
    return d

def _l4_valid(c,e,n,a):
    if c<0 or e<0: return False
    items=list(_l4_rects(c,e,n,a).items())
    def ov(A,B): return not (A[1]<B[0] or B[1]<A[0] or A[3]<B[2] or B[3]<A[2])
    for k,(r0,r1,c0,c1) in items:
        if r0<0 or c0<0 or r1>63 or c1>63: return False
    for i in range(len(items)):
        for j in range(i+1,len(items)):
            if ov(items[i][1],items[j][1]): return False
    for k,rc in items:
        r0,r1,c0,c1=rc
        for (wr,wc) in _L4_WALLS:
            if r0<=wr<=r1 and c0<=wc<=c1: return False
    return True

def _l4_render(entry,c,e,n,a):
    G=_l4_bg(entry)
    for x in (9,10,11): G[6,x]=3
    for y in range(7,9+3*c):
        for x in (9,10,11):
            if 0<=y<64: G[y,x]=12
    for x in (42,43,44): G[6,x]=3
    for y in range(7,9+3*c):
        for x in (42,43,44):
            if 0<=y<64: G[y,x]=12
    et=9+3*c
    for r in range(et,et+3):
        if 0<=r<64:
            G[r,9]=3
            for x in range(10,12+3*e):
                if 0<=x<64: G[r,x]=14
    if 0<=et+1<64 and 0<=10+3*e<64: G[et+1,10+3*e]=13
    for r in range(30-3*e,33-3*e):
        if 0<=r<64:
            for x in range(33-3*n,56):
                if 0<=x<64: G[r,x]=9
            G[r,56]=3
    for r in range(30-3*e,48-3*e):
        if 0<=r<64:
            for x in range(30-3*n,33-3*n):
                if 0<=x<64: G[r,x]=1
    for (rr,cc3) in ((36,22),(37,21),(37,23),(38,22)): G[rr,cc3]=13   # hollow diamond ring (blue passes around it)
    for r in range(33-3*e,35):
        if 0<=r<64:
            for x in (54,55,56): G[r,x]=14
    for x in (54,55,56): G[35,x]=3
    # a-region: handle, a-bar (color10) x22..(38+3a), fixed ring d, a-ptr d(25,37+3a)
    for r in (24,25,26): G[r,21]=3
    ar=38+3*a
    for r in (24,25,26):
        for x in range(22,ar+1):
            if 0<=x<64: G[r,x]=10
    for (rr,cc2) in _L4_RING: G[rr,cc2]=13
    if 0<=37+3*a<64: G[25,37+3*a]=13
    return G

def _predict_l4(state, grid, action, x, y):
    c=int(state.get('c',0)); e=int(state.get('e',0)); n=int(state.get('n',0)); a=int(state.get('a',0)); na=int(state.get('na',0))
    entry=_grid_np(ENTRY_GRID)
    info={'level_up':False,'dead':False,'win':False}
    na2=na+1
    if action==6 and (x,y) in _L4_CLICK:
        p,dl=_L4_CLICK[(x,y)]
        vals={'c':c,'e':e,'n':n,'a':a}; nv=vals[p]+dl
        if _l4_valid(*(nv if k==p else vals[k] for k in ('c','e','n','a'))):
            vals[p]=nv; c,e,n,a=vals['c'],vals['e'],vals['n'],vals['a']
    if c==9 and e==4 and a==0: info['win']=True   # WIN: BOTH diamonds docked - e-ptr@(37,22) AND a-ptr@(25,37)
    G=_l4_render(entry,c,e,n,a)
    G[63,:]=3
    cc=3*(na2//7)+(0,0,1,1,2,2,3)[na2%7]   # L4 counter: +3 per 7 clicks (2,2,3 gap pattern), exact vs history
    if cc>0: G[63,64-cc:]=4
    ns={'c':c,'e':e,'n':n,'a':a,'na':na2,'l4':True}
    return G.tolist(), info, ns

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

# ============ LEVEL 6: right arm b->e->9->c (base (13,49)) + 'a'(extend) + '8'(rotate). Dock c-ptr at (16,25). ============
_L6_PB=(13,49); _L6_P8=(7,13); _L6_PA=(7,34); _L6_DIA=(16,25)
_L6_RINGS=[(6,22),(7,21),(7,23),(8,22),(15,25),(16,24),(16,26),(17,25)]
_L6_ROT={(1,0):(0,1),(0,1):(-1,0),(-1,0):(0,-1),(0,-1):(1,0)}
_L6_CLICK={(17,52):('rot','b'),(39,52):('rot','9'),(17,59):('rot','e'),(60,59):('rot','8'),
           (17,50):('rot','b'),(39,50):('rot','9'),(17,57):('rot','e'),(60,57):('rot','8'),
           (16,51):('rot','b'),(38,51):('rot','9'),(16,58):('rot','e'),(59,58):('rot','8'),
           (18,51):('rot','b'),(40,51):('rot','9'),(18,58):('rot','e'),(61,58):('rot','8'),
           (10,51):('len','b',3),(4,51):('len','b',-3),(32,51):('len','9',3),(26,51):('len','9',-3),
           (10,58):('len','e',3),(4,58):('len','e',-3),(32,58):('len','c',3),(26,58):('len','c',-3),
           (60,51):('len','a',3),(54,51):('len','a',-3)}
def _is_l6(entry):
    try:
        return bool((entry==8).any() and (entry==11).any() and (entry==15).any() and (not (entry==1).any()) and entry[50,17]==11)
    except Exception:
        return False
def _l6_perp(d): return (0,1) if d[0]!=0 else (1,0)
def _l6_bc(P,d,L):
    pp=_l6_perp(d); out=[]
    for k in range(L):
        for s in(-1,0,1): out.append((P[0]+k*d[0]+s*pp[0],P[1]+k*d[1]+s*pp[1]))
    for s in(-1,0,1): out.append((P[0]-d[0]+s*pp[0],P[1]-d[1]+s*pp[1]))
    return out
def _l6_geom(st):
    db,Lb,de,Le,d9,L9,dc,Lc,La,d8,L8=st
    Tb=(_L6_PB[0]+(Lb-1)*db[0],_L6_PB[1]+(Lb-1)*db[1]); Pe=(Tb[0]+2*db[0],Tb[1]+2*db[1])
    Te=(Pe[0]+(Le-1)*de[0],Pe[1]+(Le-1)*de[1]); P9=(Te[0]+2*de[0],Te[1]+2*de[1])
    T9=(P9[0]+(L9-1)*d9[0],P9[1]+(L9-1)*d9[1]); Pc=(T9[0]+2*d9[0],T9[1]+2*d9[1])
    bars=[('b',_L6_PB,db,Lb,11),('e',Pe,de,Le,14),('9',P9,d9,L9,9),('c',Pc,dc,Lc,12),
          ('a',_L6_PA,(0,-1),La,10),('8',_L6_P8,d8,L8,8)]
    cptr=(Pc[0]+(Lc-2)*dc[0],Pc[1]+(Lc-2)*dc[1]); aptr=(_L6_PA[0],_L6_PA[1]-(La-2))
    return bars,cptr,aptr
def _l6_valid(st,walls,allow_off=True):
    db,Lb,de,Le,d9,L9,dc,Lc,La,d8,L8=st
    if min(Lb,Le,L9,Lc,La)<2 or max(Lb,Le,L9,Lc,La)>47: return False
    bars,cptr,aptr=_l6_geom(st)
    owner={}   # STRICT: no two bars overlap (reality blocks arm-internal overlaps too)
    for (nm,P,d,L,col) in bars:
        for (r,c) in _l6_bc(P,d,L):
            if not(0<=r<64 and 0<=c<64):
                if allow_off: continue   # off-grid allowed only for the +90 first-try
                return False
            if (r,c) in walls: return False
            if (r,c) in owner and owner[(r,c)]!=nm: return False
            owner[(r,c)]=nm
    return True
def _l6_render(entry,st,na,walls):
    G=np.full((64,64),5,dtype=entry.dtype)
    for (r,c) in walls: G[r,c]=15
    G[48:63]=entry[48:63]
    bars,cptr,aptr=_l6_geom(st)
    for (nm,P,d,L,col) in bars:
        pp=_l6_perp(d)
        for k in range(L):
            for s in(-1,0,1):
                r,c=P[0]+k*d[0]+s*pp[0],P[1]+k*d[1]+s*pp[1]
                if 0<=r<64 and 0<=c<64: G[r,c]=col
        for s in(-1,0,1):
            r,c=P[0]-d[0]+s*pp[0],P[1]-d[1]+s*pp[1]
            if 0<=r<64 and 0<=c<64: G[r,c]=3
    for (r,c) in _L6_RINGS: G[r,c]=13
    if 0<=aptr[0]<64 and 0<=aptr[1]<64: G[aptr[0],aptr[1]]=13
    if 0<=cptr[0]<64 and 0<=cptr[1]<64: G[cptr[0],cptr[1]]=13
    G[63]=3
    n6=na-1; cc=0; _p=1; _k=1   # counter (post-reset): +1 per 3 clicks; stall (gap 4) each time t4 reaches k with k%8==5
    while _p<=n6:
        cc=_k; _k+=1; _p += 4 if (_k%8==5) else 3
    if cc>0: G[63,64-cc:]=4
    return G
def _predict_l6(state,grid,action,x,y):
    entry=_grid_np(ENTRY_GRID)
    keys=['db','Lb','de','Le','d9','L9','dc','Lc','La','d8','L8']
    defs=[(-1,0),2,(0,1),5,(1,0),5,(0,-1),2,14,(1,0),14]
    st=[tuple(state[k]) if isinstance(state.get(k,defs[i]),(list,tuple)) else int(state.get(k,defs[i])) for i,k in enumerate(keys)]
    na=int(state.get('na',0)); info={'level_up':False,'dead':False,'win':False}
    na2=na+1
    walls=set((int(r),int(c)) for r,c in np.argwhere(entry==15))
    if action==6 and (x,y) in _L6_CLICK:
        act=_L6_CLICK[(x,y)]
        nst=list(st)
        idx={'b':0,'e':2,'9':4,'c':6,'a':8,'8':9}
        if act[0]=='rot':
            bar=act[1]
            chain={'b':['b','e','9','c'],'e':['e','9','c'],'9':['9','c'],'8':['8']}[bar]
            for turns in (1,2):   # rotate +90, else +180; NEVER +270. +90 allows off-grid; +180 requires on-grid
                nst=list(st)
                for _ in range(turns):
                    for cb in chain:
                        di=idx[cb]; nst[di]=_L6_ROT[tuple(nst[di])]
                if _l6_valid(nst,walls,allow_off=(turns==1)):
                    st=nst; break
        elif act[0]=='len':
            bar,dl=act[1],act[2]
            li={'b':1,'e':3,'9':5,'c':7,'a':8}[bar]
            nst=list(st); nst[li]=st[li]+dl
            if _l6_valid(nst,walls): st=nst
    bars,cptr,aptr=_l6_geom(st)
    if (cptr[0],cptr[1])==_L6_DIA and (aptr[0],aptr[1])==(7,22): info['win']=True; info['level_up']=True  # BOTH diamonds
    G=_l6_render(entry,st,na2,walls)
    ns={keys[i]:st[i] for i in range(len(keys))}; ns['na']=na2; ns['l6']=True
    return G.tolist(), info, ns

# ============ LEVEL 5: articulated robot arm (e->b->9); pointer docks hollow diamond (34,52) ============
_L5_PE=(16,40)              # base pivot (e-bar root), fixed
_L5_DIAMOND=(34,52)         # hollow diamond center = target
_L5_ROT={(1,0):(0,1),(0,1):(-1,0),(-1,0):(0,-1),(0,-1):(1,0)}  # down->right->up->left per down-click
_L5_CLICK={(12,49):('9','rot'),(31,49):('b','rot'),(50,49):('e','rot'),
           (16,57):('9','grow'),(8,57):('9','shrink'),
           (34,57):('b','grow'),(26,57):('b','shrink'),
           (52,57):('e','grow'),(44,57):('e','shrink')}
_L5_LIDX={'e':1,'b':3,'9':5}
def _is_l5(entry):
    try:
        return bool(entry[48,12]==9 and entry[48,50]==14 and entry[48,31]==11)
    except Exception:
        return False
def _l5_perp(d):
    return (0,1) if d[0]!=0 else (1,0)
def _l5_pivots(st):
    de,Le,db,Lb,d9,L9=st
    Pe=_L5_PE
    Te=(Pe[0]+(Le-1)*de[0],Pe[1]+(Le-1)*de[1]); Pb=(Te[0]+2*de[0],Te[1]+2*de[1])
    Tb=(Pb[0]+(Lb-1)*db[0],Pb[1]+(Lb-1)*db[1]); P9=(Tb[0]+2*db[0],Tb[1]+2*db[1])
    ptr=(P9[0]+(L9-2)*d9[0],P9[1]+(L9-2)*d9[1])
    return Pe,Pb,P9,ptr
def _l5_barcells(P,d,L):
    pp=_l5_perp(d); body=[]; hand=[]
    for k in range(L):
        for s in (-1,0,1): body.append((P[0]+k*d[0]+s*pp[0],P[1]+k*d[1]+s*pp[1]))
    for s in (-1,0,1): hand.append((P[0]-d[0]+s*pp[0],P[1]-d[1]+s*pp[1]))
    return body,hand
def _l5_valid(st,bg):
    de,Le,db,Lb,d9,L9=st
    if Le<2 or Lb<2 or L9<2: return False
    if Le>41 or Lb>41 or L9>41: return False   # search bound: solution uses <=38; keeps BFS focused
    Pe,Pb,P9,ptr=_l5_pivots(st)
    allc=[]
    for (P,d,L) in [(Pe,de,Le),(Pb,db,Lb),(P9,d9,L9)]:
        b,h=_l5_barcells(P,d,L); allc+=b+h
    allc.append(ptr)
    for (r,c) in allc:
        if not (0<=r<64 and 0<=c<64): return False
        if bg[r,c]==15: return False
    return True
def _l5_render(entry,st,na):
    G=entry.copy(); G[7:19,38:54]=5
    de,Le,db,Lb,d9,L9=st
    Pe,Pb,P9,ptr=_l5_pivots(st)
    for (P,d,L,col) in [(Pe,de,Le,14),(Pb,db,Lb,11),(P9,d9,L9,9)]:
        b,h=_l5_barcells(P,d,L)
        for (r,c) in b:
            if 0<=r<64 and 0<=c<64: G[r,c]=col
        for (r,c) in h:
            if 0<=r<64 and 0<=c<64: G[r,c]=3
    if 0<=ptr[0]<64 and 0<=ptr[1]<64: G[ptr[0],ptr[1]]=13
    G[63,:]=3
    cc=3*(na//7)+(0,0,1,1,2,2,3)[na%7]
    if cc>0: G[63,64-cc:]=4
    return G
def _predict_l5(state,grid,action,x,y):
    entry=_grid_np(ENTRY_GRID)
    de=tuple(state.get('de',(-1,0))); Le=int(state.get('Le',5))
    db=tuple(state.get('db',(0,1))); Lb=int(state.get('Lb',8))
    d9=tuple(state.get('d9',(1,0))); L9=int(state.get('L9',5))
    na=int(state.get('na',0))
    info={'level_up':False,'dead':False,'win':False}
    na2=na+1
    st=[de,Le,db,Lb,d9,L9]
    if action==6 and (x,y) in _L5_CLICK:
        bar,act=_L5_CLICK[(x,y)]
        nst=list(st)
        if act=='rot':
            nst[4]=_L5_ROT[d9]
            if bar in ('b','e'): nst[2]=_L5_ROT[db]
            if bar=='e': nst[0]=_L5_ROT[de]
        elif act=='grow':
            i=_L5_LIDX[bar]; nst[i]=st[i]+3
        elif act=='shrink':
            i=_L5_LIDX[bar]; nst[i]=st[i]-3
        bg=entry.copy(); bg[7:19,38:54]=5
        if _l5_valid(nst,bg): st=nst
    de,Le,db,Lb,d9,L9=st
    Pe,Pb,P9,ptr=_l5_pivots(st)
    if (ptr[0],ptr[1])==_L5_DIAMOND: info['win']=True
    G=_l5_render(entry,st,na2)
    ns={'de':tuple(de),'Le':Le,'db':tuple(db),'Lb':Lb,'d9':tuple(d9),'L9':L9,'na':na2,'l5':True}
    return G.tolist(), info, ns

def init_state(entry_grid=None):
    entry=None
    if entry_grid is not None:
        try: entry=_grid_np(entry_grid)
        except Exception: entry=None
    if entry is None:
        try: entry=_grid_np(ENTRY_GRID)
        except Exception: entry=None
    if entry is not None and _is_l4(entry):
        return {'c':0,'e':0,'n':0,'a':0,'na':0,'l4':True}
    if entry is not None and _is_l3(entry):
        return {'g':0,'bt':{o:_L3_OB[o]['home'] for o in _L3_IDS},'n':0,'l3':True}
    if entry is not None and _is_l5(entry):
        return {'de':(-1,0),'Le':5,'db':(0,1),'Lb':8,'d9':(1,0),'L9':5,'na':0,'l5':True}
    if entry is not None and _is_l6(entry):
        return {'db':(-1,0),'Lb':2,'de':(0,1),'Le':5,'d9':(1,0),'L9':5,'dc':(0,-1),'Lc':2,'La':14,'d8':(1,0),'L8':14,'na':0,'l6':True}
    return {}

def predict(state, grid, action, x=None, y=None):
    if state is None: state={}
    try:
        entry=_grid_np(ENTRY_GRID); l3=_is_l3(entry); l4=_is_l4(entry); l5=_is_l5(entry); l6=_is_l6(entry)
    except Exception:
        l3=False; l4=False; l5=False; l6=False
    if state.get('l6') or l6:
        return _predict_l6(state, grid, action, x, y)
    if state.get('l4') or l4:
        return _predict_l4(state, grid, action, x, y)
    if state.get('l3') or l3:
        return _predict_l3(state, grid, action, x, y)
    if state.get('l5') or l5:
        return _predict_l5(state, grid, action, x, y)
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
    if _is_l4(entry):
        return bool(g[37,22]==13 and g[25,37]==13)  # both diamonds docked
    if _is_l3(entry):
        return bool(g[10,31]==13 and g[9,31]==11)
    if _is_l5(entry):
        return bool(g[34,52]==13)
    if _is_l6(entry):
        return bool(g[16,25]==13 and g[7,22]==13)  # both diamonds: c-ptr@(16,25) AND a-ptr@(7,22)
    if not (entry == 15).any():
        return False
    dia = _l1_diamond(entry)
    if dia is None: return False
    H,W=g.shape
    for py,px in zip(*np.where(g==13)):
        if any(0<=px+dx<W and 0<=py+dy<H and g[py+dy][px+dx]==14 for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))):
            return (int(px),int(py))==(int(dia[0]),int(dia[1]))
    return False
