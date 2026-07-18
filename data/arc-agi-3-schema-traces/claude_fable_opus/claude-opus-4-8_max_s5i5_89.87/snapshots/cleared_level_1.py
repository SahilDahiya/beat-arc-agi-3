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

# ------------------------- dispatch -------------------------
def step(grid, action, x=None, y=None):
    try:
        entry = _grid_np(ENTRY_GRID)
        is_l1 = bool((entry == 15).any())
    except Exception:
        is_l1 = False
    if is_l1:
        return _step_l1(grid, action, x, y)
    return _step_l0(grid, action, x, y)

def is_goal(grid):
    g = _grid_np(grid)
    try:
        entry = _grid_np(ENTRY_GRID)
    except Exception:
        return False
    if not (entry == 15).any():
        return False
    dia = _l1_diamond(entry)
    if dia is None: return False
    H,W=g.shape
    for py,px in zip(*np.where(g==13)):
        if any(0<=px+dx<W and 0<=py+dy<H and g[py+dy][px+dx]==14 for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))):
            return (int(px),int(py))==(int(dia[0]),int(dia[1]))
    return False
