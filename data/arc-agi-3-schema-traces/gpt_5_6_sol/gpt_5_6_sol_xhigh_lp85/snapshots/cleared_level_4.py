import numpy as np


def _components(a, excluded=(4,)):
    h, w = a.shape
    seen = set()
    out = []
    for y in range(h):
        for x in range(w):
            v = int(a[y, x])
            if v in excluded or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            cells = []
            while stack:
                xx, yy = stack.pop()
                cells.append((xx, yy))
                for nx, ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in seen and int(a[ny,nx]) == v:
                        seen.add((nx,ny)); stack.append((nx,ny))
            out.append((v, cells))
    return out


def _layout():
    a = np.array(ENTRY_GRID, dtype=int)
    comps = _components(a)
    tiles = []
    small = []
    large = []
    for v, cells in comps:
        xs = [p[0] for p in cells]; ys = [p[1] for p in cells]
        box = (min(xs), min(ys), max(xs), max(ys))
        bw, bh = box[2]-box[0]+1, box[3]-box[1]+1
        if len(cells) == 16 and bw == 4 and bh == 4:
            tiles.append((box[0], box[1], v))
        elif len(cells) == 4 and bw == 2 and bh == 2:
            small.append((box, v))
        elif len(cells) > 16 and bw > 1 and bh > 1:
            large.append((box, v, len(cells)))
    xs = sorted(set(x for x,y,v in tiles))
    ys = sorted(set(y for x,y,v in tiles))
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    pos = {(x,y):v for x,y,v in tiles}
    order = []
    for x in xs:
        if (x,ymin) in pos: order.append((x,ymin))
    for y in ys[1:]:
        if (xmax,y) in pos: order.append((xmax,y))
    for x in reversed(xs[:-1]):
        if (x,ymax) in pos: order.append((x,ymax))
    for y in reversed(ys[1:-1]):
        if (xmin,y) in pos: order.append((xmin,y))

    # The four small corner marks identify the target tile and their color
    # identifies the unique marker tile that must be rotated into it.
    best = None
    for tx, ty in order:
        near = [(b,v) for b,v in small
                if b[2] >= tx-3 and b[0] <= tx+6 and
                   b[3] >= ty-3 and b[1] <= ty+6]
        if best is None or len(near) > best[0]:
            best = (len(near), (tx,ty), near)
    target = best[1]
    marker = best[2][0][1] if best[2] else pos[target]

    # The two wide components outside the tile rectangle are arrow buttons.
    left = right = None
    for box,v,n in large:
        if box[3] < ymin or box[1] > ymax+3: continue
        if box[2] < xmin:
            left = box
        elif box[0] > xmax+3:
            right = box
    return order, target, marker, left, right


def _inside(box, x, y):
    return box is not None and x is not None and y is not None and box[0] <= x <= box[2] and box[1] <= y <= box[3]


def _layout1():
    a = np.array(ENTRY_GRID, dtype=int)
    comps = _components(a)
    tiles = []
    small = []
    arrows = []
    for v,cells in comps:
        xs=[p[0] for p in cells]; ys=[p[1] for p in cells]
        box=(min(xs),min(ys),max(xs),max(ys))
        bw=box[2]-box[0]+1; bh=box[3]-box[1]+1
        if len(cells)==4 and bw==2 and bh==2:
            tiles.append((box[0],box[1],v))
        elif len(cells)==1:
            small.append((box[0],box[1],v))
        elif v in (8,14) and len(cells)>4 and bw>1 and bh>1:
            arrows.append((box,v))
    xs=sorted(set(x for x,y,v in tiles)); ys=sorted(set(y for x,y,v in tiles))
    counts={x:sum(1 for xx,y,v in tiles if xx==x) for x in xs}
    cols=sorted(sorted(xs,key=lambda x:counts[x],reverse=True)[:2])
    xl,xr=cols; yt=min(ys); yb=max(ys)
    have={(x,y) for x,y,v in tiles}
    topxs=[x for x in xs if xl<=x<=xr and (x,yt) in have]
    ring=[]
    ring += [(x,yt) for x in topxs]
    ring += [(xr,y) for y in ys[1:-1] if (xr,y) in have]
    ring += [(x,yb) for x in reversed(topxs)]
    ring += [(xl,y) for y in reversed(ys[1:-1]) if (xl,y) in have]
    targets=[]
    for tx,ty,v in tiles:
        near=[(sx,sy,sv) for sx,sy,sv in small if tx-1<=sx<=tx+2 and ty-1<=sy<=ty+2]
        if len(near)>=4:
            targets.append((tx,ty))
    marker = small[0][2] if small else 11
    # Arrow pairs are indexed by their vertical row, top to bottom.
    arrows=sorted(arrows,key=lambda z:(z[0][1],z[0][0]))
    return tiles, ring, targets, marker, arrows


def _step1(grid, x, y):
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    tiles,ring,targets,marker,arrows=_layout1()
    hit=None
    for box,v in arrows:
        if _inside(box,x,y): hit=(box,v); break
    if hit is None:
        return g,info
    box,v=hit
    # Right buttons rotate their track clockwise/right by one slot.
    top_y=min(b[0][1] for b in arrows)
    is_right = box[0] > 32
    moved=False
    if is_right and box[1] == top_y:
        track=ring
        moved=True
    elif is_right:
        row_y=box[1]+1
        track=sorted([(tx,ty) for tx,ty,tv in tiles if ty==row_y])
        moved=bool(track)
    else:
        track=[]  # left direction is not yet observed on this level
    if moved:
        old=[int(grid[py][px]) for px,py in track]
        for i,(px,py) in enumerate(track):
            val=old[(i-1)%len(track)]
            for yy in range(py,py+2):
                for xx in range(px,px+2): g[yy][xx]=val
        # Level-1 meter is rasterized at 9 pixels per 8 effective presses:
        # after seven single ticks the eighth press advances two cells.
        filled=sum(1 for row in grid if row[0]==5)
        ticks=2 if filled % 9 == 7 else 1
        for yy in range(len(g)):
            if g[yy][0]==14 and ticks>0:
                g[yy][0]=5; ticks-=1
    if targets and all(g[ty][tx]==marker for tx,ty in targets):
        info["level_up"]=True
    return g,info


def _layout2():
    a=np.array(ENTRY_GRID,dtype=int)
    comps=_components(a)
    tiles=[]; small=[]; buttons=[]
    for v,cells in comps:
        xs0=[p[0] for p in cells]; ys0=[p[1] for p in cells]
        box=(min(xs0),min(ys0),max(xs0),max(ys0))
        bw=box[2]-box[0]+1; bh=box[3]-box[1]+1
        if len(cells)==4 and bw==2 and bh==2:
            tiles.append((box[0],box[1],v))
        elif len(cells)==1 and v in (11,12):
            small.append((box[0],box[1],v))
        elif v in (8,14) and len(cells)>4 and bw>1 and bh>1:
            buttons.append((box,v))
    xs=sorted(set(x for x,y,v in tiles)); ys=sorted(set(y for x,y,v in tiles))
    # Two overlapping rounded-rectangle tracks, expressed by their lattice indices.
    def P(ix,iy): return (xs[ix],ys[iy])
    left=[P(2,0),P(3,0),P(4,0),P(5,1),P(6,2),P(6,3),P(6,4),P(5,5),
          P(4,6),P(3,6),P(2,6),P(1,5),P(0,4),P(0,3),P(0,2),P(1,1)]
    right=[P(6,0),P(7,0),P(8,0),P(9,1),P(10,2),P(10,3),P(10,4),P(9,5),
           P(8,6),P(7,6),P(6,6),P(5,5),P(4,4),P(4,3),P(4,2),P(5,1)]
    targets=[]
    for tx,ty,tv in tiles:
        near=[sv for sx,sy,sv in small if tx-1<=sx<=tx+2 and ty-1<=sy<=ty+2]
        if len(near)>=4: targets.append((tx,ty,near[0]))
    return tiles,[left,right],targets,buttons


def _step2(grid,x,y,presses=0):
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    tiles,cycles,targets,buttons=_layout2()
    hit=None
    for box,v in buttons:
        if _inside(box,x,y): hit=(box,v); break
    if hit is None: return g,info
    box,v=hit
    # Button pairs are beneath their corresponding left/right track.
    ci=0 if (box[0]+box[2])//2 < 31 else 1
    if v==14:  # e-colored/right button: clockwise
        track=cycles[ci]
        old=[int(grid[py][px]) for px,py in track]
        for i,(px,py) in enumerate(track):
            val=old[(i-1)%len(track)]
            for yy in range(py,py+2):
                for xx in range(px,px+2): g[yy][xx]=val
        # Level 2 meter is the nearest-integer rasterization of 4/5 pixel per press.
        old_fill=(4*presses + 2)//5
        new_fill=(4*(presses+1) + 2)//5
        ticks=new_fill-old_fill
        for yy in range(len(g)):
            if g[yy][0]==14 and ticks>0:
                g[yy][0]=5; ticks-=1
    # 8-colored/counterclockwise direction remains unneeded and unobserved.
    if targets and all(g[ty][tx]==col for tx,ty,col in targets):
        info["level_up"]=True
    return g,info


def _layout3(base_grid=None):
    a=np.array(ENTRY_GRID if base_grid is None else base_grid,dtype=int)
    comps=_components(a)
    tiles=[]; small=[]; buttons=[]
    for v,cells in comps:
        xx=[p[0] for p in cells]; yy=[p[1] for p in cells]
        box=(min(xx),min(yy),max(xx),max(yy)); bw=box[2]-box[0]+1; bh=box[3]-box[1]+1
        if len(cells)==4 and bw==2 and bh==2:
            tiles.append((box[0],box[1],v))
        elif len(cells)==1 and v in (11,12):
            small.append((box[0],box[1],v))
        elif v in (8,14) and len(cells)==10 and bw>1 and bh>1:
            buttons.append((box,v))
    xs=sorted(set(x for x,y,v in tiles)); ys=sorted(set(y for x,y,v in tiles))
    # Four horizontal five-tile arms make one 20-cycle.
    rowys=sorted(y for y in ys if sum(1 for x,yy,v in tiles if yy==y)==10)
    rowxs=sorted(x for x in xs if any(yy in rowys and xx==x for xx,yy,v in tiles))
    horizontal=[(x,y) for y in rowys for x in rowxs]
    # The analogous four vertical arms form the other 20-cycle.
    colxs=sorted(x for x in xs if sum(1 for xx,y,v in tiles if xx==x)==10)
    colys=sorted(y for y in ys if any(xx in colxs and yy==y for xx,yy,v in tiles))
    vertical=[(x,y) for x in colxs for y in colys]
    targets=[]
    for tx,ty,tv in tiles:
        near=[sv for sx,sy,sv in small if tx-1<=sx<=tx+2 and ty-1<=sy<=ty+2]
        if len(near)>=4 and all(c==near[0] for c in near):
            targets.append((tx,ty,near[0]))
    return tiles,horizontal,vertical,targets,buttons


def _step3(grid,x,y,presses=0,vpresses=0):
    g=[row[:] for row in grid]; info={"level_up":False,"dead":False,"win":False}
    tiles,htrack,vtrack,targets,buttons=_layout3(grid)
    hit=None
    for box,v in buttons:
        if _inside(box,x,y): hit=(box,v); break
    if hit is None:return g,info
    box,v=hit; bw=box[2]-box[0]+1; bh=box[3]-box[1]+1
    track=[]; delta=0
    if v==14 and bh>bw:  # right/e side arrow: horizontal marker motion +1
        track=htrack; delta=1
    elif v==14 and bw>bh: # top/e arrow: vertical marker motion -1
        track=vtrack; delta=-1
    if track:
        old=[int(grid[py][px]) for px,py in track]
        for i,(px,py) in enumerate(track):
            val=old[(i-delta)%len(track)]
            for yy in range(py,py+2):
                for xx in range(px,px+2):g[yy][xx]=val
        # Level-3 raster is the sum of operation-counter breakpoints: vertical
        # fills at V1,V2,V3 and every sixth V; horizontal at multiples of 5 and 7.
        hpresses=presses-vpresses
        if delta==-1:
            old_fill=min(vpresses,3) + vpresses//6
            new_fill=min(vpresses+1,3) + (vpresses+1)//6
            ticks=new_fill-old_fill
        else:
            ticks=((hpresses+1)//5 + (hpresses+1)//7) - (hpresses//5 + hpresses//7)
        for yy in range(len(g)):
            if g[yy][0]==14 and ticks>0:
                g[yy][0]=5; ticks-=1
    if targets and all(g[ty][tx]==c for tx,ty,c in targets): info["level_up"]=True
    return g,info


def _layout4(base_grid=None):
    a=np.array(ENTRY_GRID if base_grid is None else base_grid,dtype=int)
    comps=_components(a)
    tiles=[]; corners=[]; buttons=[]
    for v,cells in comps:
        xx=[p[0] for p in cells]; yy=[p[1] for p in cells]
        box=(min(xx),min(yy),max(xx),max(yy)); bw=box[2]-box[0]+1; bh=box[3]-box[1]+1
        if len(cells)==16 and bw==4 and bh==4: tiles.append((box[0],box[1],v))
        elif len(cells)==4 and bw==2 and bh==2 and v==11: corners.append((box[0],box[1],v))
        elif v in (8,14) and len(cells)==40 and bw>1 and bh>1: buttons.append((box,v))
    xs=sorted(set(x for x,y,v in tiles)); ys=sorted(set(y for x,y,v in tiles))
    have={(x,y) for x,y,v in tiles}
    top=[(x,ys[0]) for x in xs if (x,ys[0]) in have]
    x0,x1,x2=xs[:3]; y=ys
    snake=[(x0,y[0]),(x0,y[1]),(x0,y[2]),(x1,y[2]),(x2,y[2]),
           (x2,y[3]),(x2,y[4]),(x1,y[4]),(x0,y[4]),(x0,y[5]),
           (x0,y[6]),(x1,y[6]),(x2,y[6]),(x2,y[7]),
           (x2,y[8]),(x1,y[8]),(x0,y[8])]
    targets=[]
    for tx,ty,tv in tiles:
        near=[c for sx,sy,c in corners if tx-2<=sx<=tx+5 and ty-2<=sy<=ty+5]
        if len(near)>=4 and all(c==near[0] for c in near): targets.append((tx,ty,near[0]))
    return tiles,top,snake,targets,buttons


def _step4(grid,x,y,presses=0):
    g=[row[:] for row in grid];info={"level_up":False,"dead":False,"win":False}
    tiles,top,snake,targets,buttons=_layout4(grid)
    hit=None
    for box,v in buttons:
        if _inside(box,x,y):hit=(box,v);break
    if hit is None:return g,info
    box,v=hit; operations=[]
    top_y=min(b[0][1] for b in buttons)
    if v==14 and box[1]==top_y:
        operations=[(top,1)]
    elif v==14:
        # Lower right/e couples the mechanisms: top row forward first,
        # then the 17-slot snake backward using the intermediate grid.
        operations=[(top,1),(snake,-1)]
    for track,delta in operations:
        old=[int(g[py][px]) for px,py in track]
        for i,(px,py) in enumerate(track):
            val=old[(i-delta)%len(track)]
            for yy in range(py,py+4):
                for xx in range(px,px+4):g[yy][xx]=val
    if operations:
        # Level-4 raster is nearest-integer 4/5 pixel per effective press.
        old_fill=(4*presses+2)//5
        new_fill=(4*(presses+1)+2)//5
        ticks=new_fill-old_fill
        for yy in range(len(g)):
            if g[yy][0]==14 and ticks>0:
                g[yy][0]=5; ticks-=1
    if targets and all(g[ty][tx]==c for tx,ty,c in targets):info["level_up"]=True
    return g,info


def _goal(grid):
    order, target, marker, left, right = _layout()
    x,y = target
    return int(grid[y][x]) == marker


def _core(grid, action, x=None, y=None, presses=0, vpresses=0):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6:
        return g, info
    if CURRENT_LEVEL == 1:
        return _step1(grid, x, y)
    if CURRENT_LEVEL == 2:
        return _step2(grid, x, y, presses)
    # Terminal transitions may already expose the next level number/ENTRY_GRID;
    # recognize the level-3 cross board directly from its board origin as well.
    if CURRENT_LEVEL == 3 or (len(grid)>3 and len(grid[0])>3 and grid[3][3]==4):
        return _step3(grid, x, y, presses, vpresses)
    if CURRENT_LEVEL == 4:
        return _step4(grid, x, y, presses)
    order, target, marker, left, right = _layout()
    direction = 0
    if _inside(left, x, y): direction = -1   # each position receives next clockwise tile
    if _inside(right, x, y): direction = 1
    if direction == 0:
        return g, info

    old = [int(grid[py][px]) for px,py in order]
    n = len(order)
    for i,(px,py) in enumerate(order):
        val = old[(i - direction) % n]
        for yy in range(py,py+4):
            for xx in range(px,px+4):
                g[yy][xx] = val

    # Each effective arrow press consumes one five-pixel unit of the left meter.
    used = 0
    for yy in range(len(g)):
        if g[yy][0] == 14 and used < 5:
            g[yy][0] = 5
            used += 1

    if _goal(g):
        if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 7:
            info["win"] = True
        else:
            info["level_up"] = True
    return g, info


def init_state(entry_grid):
    return {"presses": 0, "vpresses": 0}


def predict(state, grid, action, x=None, y=None):
    presses=int((state or {}).get("presses",0))
    vpresses=int((state or {}).get("vpresses",0))
    g,info=_core(grid,action,x,y,presses,vpresses)
    changed=any(g[y][x] != grid[y][x] for y in range(len(g)) for x in range(len(g[0])))
    is_vertical=False
    if CURRENT_LEVEL==3 and action==6 and changed:
        tiles,h,v,targets,buttons=_layout3(grid)
        for box,col in buttons:
            if _inside(box,x,y) and col==14 and (box[2]-box[0])>(box[3]-box[1]):
                is_vertical=True
    ns={"presses": presses + (1 if action==6 and changed else 0),
        "vpresses": vpresses + (1 if is_vertical else 0)}
    return g,info,ns


def is_goal(grid):
    if CURRENT_LEVEL == 1:
        tiles,ring,targets,marker,arrows=_layout1()
        return bool(targets) and all(grid[y][x]==marker for x,y in targets)
    if CURRENT_LEVEL == 2:
        tiles,cycles,targets,buttons=_layout2()
        return bool(targets) and all(grid[y][x]==c for x,y,c in targets)
    if CURRENT_LEVEL == 3:
        tiles,h,v,targets,buttons=_layout3(grid)
        return bool(targets) and all(grid[y][x]==c for x,y,c in targets)
    if CURRENT_LEVEL == 4:
        tiles,top,snake,targets,buttons=_layout4(grid)
        return bool(targets) and all(grid[y][x]==c for x,y,c in targets)
    return _goal(grid)
