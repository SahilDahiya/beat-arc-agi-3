# world_model_v5 — ARC3 game s5i5.
# LEVEL 0 mechanic (confirmed, backtest-green on 5 transitions):
#  - Two "template bars", each a rectangle of a block-color with a single 13 "pointer",
#    attached to a color-3 handle. Bar value = distance of pointer from the anchored (handle) edge.
#    t14: horizontal, anchored left (x28), grows +x, pointer on center row. entry value 3.
#    t11: vertical,   anchored top  (y28), grows +y, pointer on center col. entry value 6.
#    Layout along axis: [value block-cells][pointer 13][1 far block-cell]; length = value+2.
#  - Two control boxes (color-2 border). Box containing color-14 shapes controls t14;
#    color-11 box controls t11. Box with a VERTICAL color-3 divider: click left half = value-3,
#    right half = value+3. HORIZONTAL divider: click top half = -3, bottom half = +3. Clamp >=0.
#  - Move counter: bottom row (y63) all color 3; rightmost `lit` cells are color 4.
#    Each click: lit += 1, plus +1 extra if the edited bar's value was 0 BEFORE the click.
#  - Non-control clicks / non-6 actions: assumed no-op (unverified).
#  GOAL: still unknown (diamonds d1/d2 aligned with the bars are the leading target hypothesis).
#        is_goal intentionally undefined until confirmed.
import numpy as np
from collections import deque

def _grid_np(g): return np.array(g, dtype=int)

def _find_template(g, block_color):
    H, W = g.shape
    ptr = None
    for py, px in zip(*np.where(g == 13)):
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = py+dy, px+dx
            if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == block_color:
                ptr = (py, px); break
        if ptr: break
    if ptr is None:
        return None
    start = None
    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
        ny, nx = ptr[0]+dy, ptr[1]+dx
        if 0 <= ny < H and 0 <= nx < W and g[ny, nx] == block_color:
            start = (ny, nx); break
    if start is None:
        return None
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

def _build_controls(g):
    controls=[]
    for (y0,x0,y1,x1) in _find_boxes(g):
        interior = g[y0+1:y1, x0+1:x1]
        col=None
        for cc in (14,11):
            if (interior==cc).any(): col=cc; break
        if col is None: continue
        d3 = np.argwhere(interior==3)
        if len(d3)==0: continue
        rows3=set(d3[:,0].tolist()); cols3=set(d3[:,1].tolist())
        vertical = len(cols3)<=1 and len(rows3)>1
        controls.append(dict(col=col, box=(int(y0),int(x0),int(y1),int(x1)),
                             vertical=bool(vertical), cx=(x0+x1)//2, cy=(y0+y1)//2))
    return controls

def _setup():
    try:
        entry = _grid_np(ENTRY_GRID)
    except Exception:
        return None, None
    tpl={}
    for cc in (14,11):
        t=_find_template(entry, cc)
        if t is not None: tpl[cc]=t
    ctrl=_build_controls(entry)
    return tpl, ctrl

def _is_triangular(k):
    # k is a triangular number (1,3,6,10,15,...) iff 8k+1 is a perfect square. (k=0 excluded)
    if k <= 0:
        return False
    s = 8 * k + 1
    r = int(s ** 0.5)
    return r * r == s or (r + 1) * (r + 1) == s

def step(grid, action, x=None, y=None):
    g = _grid_np(grid).copy()
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return g, info
    tpl, ctrl = _setup()
    if not ctrl:
        return g, info
    chosen=None
    for c in ctrl:
        y0,x0,y1,x1=c['box']
        if y0<=y<=y1 and x0<=x<=x1: chosen=c; break
    if chosen is None:
        return g, info                # non-control click: assumed no-op
    t = tpl.get(chosen['col'])
    if t is None:
        return g, info
    v0 = _measure(g, t)
    if v0 is None:
        return g, info
    if chosen['vertical']:
        delta = -3 if x < chosen['cx'] else 3
    else:
        delta = -3 if y < chosen['cy'] else 3
    v1 = max(0, v0 + delta)
    _draw(g, t, v1)
    # Move counter (color-4 fill of bottom row from the right): every control click advances
    # the counter by 1, BUT the counter SKIPS any value == 2 or 7 (mod 9) — so landing on a
    # skipped value costs an extra +1. Uniform over increase/decrease and over both bars.
    lit = int((g[63]==4).sum())
    lit += 1
    if lit % 9 in (2, 7):
        lit += 1
    lit = min(lit, g.shape[1])
    g[63,:] = 3
    if lit>0:
        g[63, g.shape[1]-lit:] = 4
    return g, info
