import numpy as np
from collections import deque

BG = 5
DOT = 13
BAR_EMPTY = 3
BAR_USED = 4

def _component(a, x, y):
    h, w = len(a), len(a[0])
    c = a[y][x]
    q = deque([(x, y)])
    seen = {(x, y)}
    while q:
        xx, yy = q.popleft()
        for nx, ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
            if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in seen and a[ny][nx] == c:
                seen.add((nx,ny)); q.append((nx,ny))
    return seen

def _control(x, y):
    """Return (track_colour, dx,dy) for a 3x3 seven-cell directional glyph."""
    a = ENTRY_GRID
    h, w = len(a), len(a[0])
    if not (0 <= x < w and 0 <= y < h):
        return None
    c = a[y][x]
    if c in (BG, DOT, 2, 3, 4):
        return None
    comp = _component(a, x, y)
    if len(comp) != 7:
        return None
    xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
    x0,x1,y0,y1 = min(xs),max(xs),min(ys),max(ys)
    if x1-x0 != 2 or y1-y0 != 2:
        return None
    cx,cy = x0+1,y0+1
    # The one open edge of the bracket-shaped glyph is opposite its direction.
    mids = {
        (-1,0):(x0,cy), (1,0):(x1,cy),
        (0,-1):(cx,y0), (0,1):(cx,y1)
    }
    missing = [d for d,p in mids.items() if p not in comp]
    if len(missing) != 1:
        return None
    mx,my = missing[0]
    return c, -mx, -my

def _target_centres(a):
    h,w = len(a),len(a[0])
    out=[]
    for y in range(1,h-1):
        for x in range(1,w-1):
            if a[y][x] == BG and all(a[y+dy][x+dx] == DOT for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))):
                out.append((x,y))
    return out

def _source_directions():
    """Read each track colour's direction from a 3-valued cap behind 2 body rows."""
    a=ENTRY_GRID
    h,w=len(a),len(a[0])
    out={}
    forbidden={BG,DOT,2,3,4}
    edges=[
        ([(0,i) for i in range(3)], (1,0)),
        ([(2,i) for i in range(3)], (-1,0)),
        ([(i,0) for i in range(3)], (0,1)),
        ([(i,2) for i in range(3)], (0,-1)),
    ]
    for y0 in range(h-2):
        for x0 in range(w-2):
            for edge,direction in edges:
                eset=set(edge)
                if not all(a[y0+yy][x0+xx] == 3 for xx,yy in edge):
                    continue
                vals=[a[y0+yy][x0+xx] for yy in range(3) for xx in range(3)
                      if (xx,yy) not in eset]
                colours=set(v for v in vals if v != DOT)
                if len(colours) == 1:
                    c=list(colours)[0]
                    if c not in forbidden and all(v in (c,DOT) for v in vals):
                        out.setdefault(c,direction)
    return out

def _source_segments():
    """Find each capped source segment as a 3x3 tile."""
    a=ENTRY_GRID
    h,w=len(a),len(a[0])
    out={}
    forbidden={BG,DOT,2,3,4}
    edges=[
        ([(0,i) for i in range(3)], (1,0)),
        ([(2,i) for i in range(3)], (-1,0)),
        ([(i,0) for i in range(3)], (0,1)),
        ([(i,2) for i in range(3)], (0,-1)),
    ]
    for y0 in range(h-2):
        for x0 in range(w-2):
            for edge,direction in edges:
                eset=set(edge)
                if not all(a[y0+yy][x0+xx] == 3 for xx,yy in edge):
                    continue
                vals=[a[y0+yy][x0+xx] for yy in range(3) for xx in range(3)
                      if (xx,yy) not in eset]
                colours=set(v for v in vals if v != DOT)
                if len(colours) == 1:
                    c=list(colours)[0]
                    if c not in forbidden and all(v in (c,DOT) for v in vals):
                        if c not in out:
                            out[c]={"x":x0,"y":y0,"dx":direction[0],"dy":direction[1]}
    return out

def _segment_links(segs):
    nxt={}
    prev={}
    for c,s in segs.items():
        tx=s["x"]+3*s["dx"]; ty=s["y"]+3*s["dy"]
        for d,t in segs.items():
            if d != c and t["x"] == tx and t["y"] == ty:
                nxt[c]=d; prev[d]=c
    return nxt,prev

def _initial_lengths():
    a=ENTRY_GRID
    h,w=len(a),len(a[0])
    segs=_source_segments()
    nxt,_=_segment_links(segs)
    lengths={}
    for c,s in segs.items():
        if c in nxt:
            lengths[c]=2
            continue
        dx,dy=s["dx"],s["dy"]
        if dx == 1: cx,cy=s["x"],s["y"]+1
        elif dx == -1: cx,cy=s["x"]+2,s["y"]+1
        elif dy == 1: cx,cy=s["x"]+1,s["y"]
        else: cx,cy=s["x"]+1,s["y"]+2
        L=0
        while True:
            k=L+1
            bx,by=cx+dx*k,cy+dy*k
            cells=[(bx-dy*off,by+dx*off) for off in (-1,0,1)]
            if all(0 <= xx < w and 0 <= yy < h and a[yy][xx] in (c,DOT)
                   for xx,yy in cells):
                L += 1
            else:
                break
        lengths[c]=L
    return lengths

def _chain_layout(lengths):
    """Render articulated capped segments; growing one translates its suffix."""
    segs=_source_segments()
    nxt,prev=_segment_links(segs)
    roots=[c for c in segs if c not in prev]
    cells={}
    heads=[]
    for root in roots:
        c=root
        tile_x,tile_y=segs[c]["x"],segs[c]["y"]
        guard=0
        while True:
            s=segs[c]; dx,dy=s["dx"],s["dy"]
            if dx == 1: cx,cy=tile_x,tile_y+1
            elif dx == -1: cx,cy=tile_x+2,tile_y+1
            elif dy == 1: cx,cy=tile_x+1,tile_y
            else: cx,cy=tile_x+1,tile_y+2
            for off in (-1,0,1):
                cells[(cx-dy*off,cy+dx*off)]=3
            L=lengths.get(c,2)
            for k in range(1,L+1):
                bx,by=cx+dx*k,cy+dy*k
                for off in (-1,0,1):
                    cells[(bx-dy*off,by+dx*off)]=c
            if c not in nxt:
                hx,hy=cx+dx*(L-1),cy+dy*(L-1)
                cells[(hx,hy)]=DOT
                heads.append((hx,hy))
                break
            tile_x += dx*(L+1)
            tile_y += dy*(L+1)
            c=nxt[c]
            guard += 1
            if guard > 20:
                break
    return cells,heads

def _apply_lengths(grid, old_lengths, new_lengths):
    """Clear the old articulated object and draw the proposed new one."""
    g=[row[:] for row in grid]
    old_cells,initial_dynamic_heads=_chain_layout(old_lengths)
    init_cells,entry_heads=_chain_layout(_initial_lengths())
    static_d=set()
    for y,row in enumerate(ENTRY_GRID):
        for x,v in enumerate(row):
            if v == DOT and (x,y) not in entry_heads:
                static_d.add((x,y))
    for (x,y) in old_cells:
        if (x,y) not in static_d:
            g[y][x]=BG
    new_cells,new_heads=_chain_layout(new_lengths)
    # Fixed non-background scenery blocks a translated/extended chain.
    for (x,y),v in new_cells.items():
        if not (0 <= y < len(g) and 0 <= x < len(g[0])):
            return [row[:] for row in grid],False
        if (x,y) not in static_d and g[y][x] != BG:
            return [row[:] for row in grid],False
    for (x,y),v in new_cells.items():
        if (x,y) in static_d and v != DOT:
            continue
        g[y][x]=v
    return g,True

def _entry_head_count(palette):
    a=ENTRY_GRID
    h,w=len(a),len(a[0])
    nheads=0
    for y in range(h):
        for x in range(w):
            if a[y][x] == DOT:
                n=sum(0 <= x+ax < w and 0 <= y+ay < h and
                      a[y+ay][x+ax] in palette
                      for ax,ay in ((1,0),(-1,0),(0,1),(0,-1)))
                if n >= 2:
                    nheads += 1
    return nheads

def _move_track(g, colour, dx, dy):
    """Advance a matching head, or the sole shared head, in this colour's direction."""
    h,w=len(g),len(g[0])
    palette=set(_source_directions())
    candidates=[]
    for y in range(h):
        for x in range(w):
            if g[y][x] != DOT:
                continue
            counts={}
            for ax,ay in ((1,0),(-1,0),(0,1),(0,-1)):
                if 0 <= x+ax < w and 0 <= y+ay < h:
                    v=g[y+ay][x+ax]
                    if v in palette:
                        counts[v]=counts.get(v,0)+1
            n=sum(counts.values())
            if n >= 2:
                candidates.append((x,y,counts.get(colour,0),n,counts))
    matching=[z for z in candidates if z[2] >= 2]
    if matching:
        x,y,_,_,counts=max(matching,key=lambda z:(z[2],z[3]))
    elif _entry_head_count(palette) == 1 and candidates:
        x,y,_,_,counts=max(candidates,key=lambda z:z[3])
    else:
        return False
    prev=max(counts,key=counts.get)
    # Do not allow a new 3x3 head tile through fixed obstacles.
    for k in range(1,5):
        bx,by=x+dx*k,y+dy*k
        for off in (-1,0,1):
            xx,yy=bx-dy*off,by+dx*off
            if not (0 <= xx < w and 0 <= yy < h):
                return False
            if g[yy][xx] not in palette and g[yy][xx] not in (BG,DOT):
                return False
    g[y][x]=prev
    for k in range(1,5):
        bx,by=x+dx*k,y+dy*k
        for off in (-1,0,1):
            xx,yy=bx-dy*off,by+dx*off
            if g[yy][xx] != DOT:
                g[yy][xx]=colour
    nx,ny=x+3*dx,y+3*dy
    g[ny][nx]=DOT
    return True

def _rounded_ratio(n, width, total):
    q=n*width
    base=q//total
    rem=q%total
    if 2*rem > total or (2*rem == total and base%2 == 1):
        base += 1
    return base

def _render_budget(g, turn, level):
    width=len(g[0])
    # Confirmed L0=50. L1 observations 0,1,1 pixels on turns 1..3;
    # its apparent level budget is 150 (three times L0).
    total=50 if level == 0 else 150
    wanted=_rounded_ratio(turn,width,total)
    for xx in range(width):
        if g[-1][xx] in (BAR_EMPTY,BAR_USED):
            g[-1][xx]=BAR_USED if xx >= width-wanted else BAR_EMPTY

def _all_targets_reached(g):
    centres=_target_centres(ENTRY_GRID)
    if not centres:
        return False
    return all(g[y][x] == DOT for x,y in centres)

def init_state(entry_grid):
    return {"turn":0,"level":CURRENT_LEVEL,"lengths":_initial_lengths()}

def predict(state, grid, action, x=None, y=None):
    level=state.get("level",CURRENT_LEVEL)
    base_lengths=state.get("lengths",_initial_lengths())
    lengths=dict(base_lengths)
    if action == 0:
        ns={"turn":0,"level":level,"lengths":_initial_lengths()}
        return [row[:] for row in ENTRY_GRID], {"level_up":False,"dead":False,"win":False}, ns
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    turn=state.get("turn",0)
    valid=False
    if action == 6:
        ctl=_control(x,y)
        if ctl is not None:
            colour,button_dx,button_dy=ctl
            if colour in lengths:
                delta=3 if (button_dx > 0 or button_dy > 0) else -3
                proposed=dict(lengths)
                proposed[colour]=max(2,lengths[colour]+delta)
                if proposed[colour] != lengths[colour]:
                    candidate,valid=_apply_lengths(grid,lengths,proposed)
                    if valid:
                        g=candidate
                        lengths=proposed
        if level == 0:
            # First ever transition is skipped in replay; recover L0 turn from bar.
            used=sum(v == BAR_USED for v in grid[-1])
            turn=int(used * 50.0 / len(grid[0]) + 0.5) + 1
        else:
            turn += 1
        _render_budget(g,turn,level)
    if valid and _all_targets_reached(g):
        info["level_up"]=True
    ns={"turn":turn,"level":level,"lengths":lengths}
    return g,info,ns

def is_goal(grid):
    return _all_targets_reached(grid)
