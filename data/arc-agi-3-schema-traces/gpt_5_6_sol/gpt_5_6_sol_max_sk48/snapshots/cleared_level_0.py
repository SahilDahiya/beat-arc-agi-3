import numpy as np

# The puzzle is a telescoping train/rod on a 6-pixel macro-grid.
# 1/2 move it vertically; 4 extends the patterned coupling to the right.
STEP = 6

def _separator(a):
    # A full 2/3 status row separates play from the target illustration.
    for y in range(a.shape[0]):
        if np.sum((a[y] == 2) | (a[y] == 3)) >= a.shape[1] - 2:
            return y
    return a.shape[0]

def _engine(a):
    sep = _separator(a)
    # Locate the movable icon, excluding its duplicate below the separator.
    for y in range(max(0, sep-5)):
        for x in range(a.shape[1]-5):
            if (np.all(a[y, x:x+6] == 6) and
                a[y+1,x] == 6 and a[y+1,x+5] == 6 and
                np.all(a[y+1,x+1:x+5] == 0) and
                a[y+4,x] == 6 and a[y+4,x+5] == 6 and
                np.all(a[y+4,x+1:x+5] == 0) and
                np.all(a[y+5,x:x+6] == 6)):
                return x,y
    return None

def _board_bounds(e):
    a = np.array(e, dtype=int)
    sep = _separator(a)
    seen = np.zeros(a.shape, bool)
    best, bestn = None, -1
    # Largest connected 4-region above the separator is the board.
    for sy in range(sep):
        for sx in range(a.shape[1]):
            if a[sy,sx] != 4 or seen[sy,sx]:
                continue
            q=[(sx,sy)]; seen[sy,sx]=1; pts=[]
            for x,y in q:
                pts.append((x,y))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx,yy=x+dx,y+dy
                    if (0<=xx<a.shape[1] and 0<=yy<sep and
                        not seen[yy,xx] and a[yy,xx]==4):
                        seen[yy,xx]=1; q.append((xx,yy))
            if len(pts)>bestn:
                bestn=len(pts); best=pts
    if not best:
        return (0,0,a.shape[1]-1,sep-1)
    xs=[p[0] for p in best]; ys=[p[1] for p in best]
    return min(xs),min(ys),max(xs),max(ys)

def _clean_base():
    e=np.array(ENTRY_GRID, dtype=int)
    b=e.copy()
    loc=_engine(e)
    if loc is None:
        return b
    x0,y0=loc
    lx,ty,rx,by=_board_bounds(e)
    sep=_separator(e)
    bg=int(np.bincount(e[:sep].ravel(), minlength=16).argmax())
    rail=[]
    for x in range(max(0,lx-8),lx):
        if np.sum((e[:sep,x]==2)|(e[:sep,x]==3)) >= 6:
            rail.append(x)
    # Remove the initial engine and its one-cell coupling.
    for y in range(y0,y0+6):
        for x in range(x0,x0+12):
            if lx<=x<=rx and ty<=y<=by:
                b[y,x]=4
            else:
                b[y,x]=bg
                if x in rail and ty+2<=y<=by-2:
                    yy=y
                    while yy>=y0:
                        yy-=6
                    if 0<=yy<sep and e[yy,x] in (2,3):
                        b[y,x]=e[yy,x]
                    else:
                        b[y,x]=2 if ((y-ty)%6 in (2,3)) else 3
    return b

def _strand_end(a, x0, y0):
    # Active coupling is an uninterrupted run of connector values or car
    # colors. This must stop at exterior background (often color 5).
    active=set((1,2)) | _target_colors()
    x=x0+5
    while x+1<a.shape[1] and (int(a[y0+2,x+1]) in active or
                              int(a[y0+3,x+1]) in active):
        x += 1
    return x

def _target_colors():
    e=np.array(ENTRY_GRID,dtype=int)
    lx,ty,rx,by=_board_bounds(e)
    vals=set(int(v) for v in np.unique(e[ty:by+1,lx:rx+1]))
    vals.discard(4)
    vals.discard(1)
    vals.discard(2)
    return vals

def _dynamic_base(a, x0, y0, end):
    # Static target cells already joined to the contiguous train must no
    # longer reappear when that train moves away.
    b=_clean_base()
    e=np.array(ENTRY_GRID,dtype=int)
    lx,ty,rx,by=_board_bounds(e)
    colors=_target_colors()
    for c in colors:
        ys,xs=np.where(e==c)
        keep=(xs>=lx)&(xs<=rx)&(ys>=ty)&(ys<=by)
        xs=xs[keep]; ys=ys[keep]
        if len(xs)==0:
            continue
        # Each level currently uses one component per color; connected
        # components can be split here later if a level repeats a color.
        xmin,xmax=int(xs.min()),int(xs.max())
        ymin,ymax=int(ys.min()),int(ys.max())
        absent=not np.any(a[ymin:ymax+1,xmin:xmax+1]==c)
        joined=(ymin>=y0 and ymax<=y0+5 and xmax<=end and xmin>=x0)
        if absent or joined:
            b[ymin:ymax+1,xmin:xmax+1][e[ymin:ymax+1,xmin:xmax+1]==c]=4
    return b

def _vertical(a, dy):
    loc=_engine(a)
    if loc is None:
        return a
    x0,y0=loc
    lx,ty,rx,by=_board_bounds(np.array(ENTRY_GRID,dtype=int))
    ny=y0+dy
    if ny<ty or ny+5>by:
        return a
    end=_strand_end(a,x0,y0)
    base=_dynamic_base(a,x0,y0,end)
    out=a.copy()
    # Opaque movable pixels: full engine, the two-line coupling, and any
    # colored cars embedded in the contiguous train.
    w=end-x0+1
    mask=np.zeros((6,w),bool)
    mask[:,:6]=True
    mask[2:4,5:]=True
    colors=_target_colors()
    if colors:
        reg=a[y0:y0+6,x0:end+1]
        for c in colors:
            mask |= (reg==c)
    src=a[y0:y0+6,x0:end+1].copy()
    old=out[y0:y0+6,x0:end+1]
    bb=base[y0:y0+6,x0:end+1]
    old[mask]=bb[mask]
    dst=out[ny:ny+6,x0:end+1]
    dst[mask]=src[mask]
    return out

def _mark_goal_car(out, color):
    # The lower illustration doubles as progress display: catching a car
    # hollows the central 2x2 pixels of that color's illustrated block.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    ys,xs=np.where((e==color) & (np.indices(e.shape)[0]>sep))
    if len(xs)==0:
        return
    # Goal cars are 4x4; their full entry-grid bounding box is enough.
    xmin,xmax=int(xs.min()),int(xs.max())
    ymin,ymax=int(ys.min()),int(ys.max())
    if xmax-xmin>=3 and ymax-ymin>=3:
        cx0=xmin+(xmax-xmin+1)//2-1
        cy0=ymin+(ymax-ymin+1)//2-1
        out[cy0:cy0+2,cx0:cx0+2]=0

def _tile_has_car(a,y0,start):
    colors=_target_colors()
    tile=a[y0:y0+6,start:start+STEP]
    return any(np.any(tile==c) for c in colors)

def _car_block_start(a,x0,y0,end):
    # Cars, when present, form one contiguous block at the rod tip.
    last=end-STEP+1
    if last<x0+6 or not _tile_has_car(a,y0,last):
        return None
    start=last
    while start-STEP>=x0+6 and _tile_has_car(a,y0,start-STEP):
        start-=STEP
    return start

def _put_pattern(out,x0,y0,start):
    for j,xx in enumerate(range(start,start+STEP)):
        phase=(xx-(x0+5))%3
        out[y0+2,xx]=(1,2,1)[phase]
        out[y0+3,xx]=(2,1,1)[phase]

def _extend(a):
    loc=_engine(a)
    if loc is None:
        return a
    x0,y0=loc
    lx,ty,rx,by=_board_bounds(np.array(ENTRY_GRID,dtype=int))
    end=_strand_end(a,x0,y0)
    if end+STEP>rx:
        return a
    nxt=end+1
    old=a[y0:y0+6,nxt:nxt+STEP].copy()
    colors=_target_colors()
    caught=[c for c in colors if np.any(old==c)]
    out=a.copy()
    if caught:
        # A target directly beyond the tip joins the existing car block.
        _put_pattern(out,x0,y0,nxt)
        reg=out[y0:y0+6,nxt:nxt+STEP]
        for c in caught:
            reg[old==c]=c
            _mark_goal_car(out,c)
        return out
    bstart=_car_block_start(a,x0,y0,end)
    if bstart is None:
        # No caught cars yet: telescope one plain cable cell.
        _put_pattern(out,x0,y0,nxt)
    else:
        # Extending a caught train pushes its whole contiguous car block
        # one cell right and inserts cable where that block began.
        block=a[y0:y0+6,bstart:end+1].copy()
        base=_dynamic_base(a,x0,y0,end)
        out[y0:y0+6,bstart:bstart+STEP]=base[y0:y0+6,bstart:bstart+STEP]
        _put_pattern(out,x0,y0,bstart)
        out[y0:y0+6,bstart+STEP:end+1+STEP]=block
    return out

def _retract(a):
    loc=_engine(a)
    if loc is None:
        return a
    x0,y0=loc
    end=_strand_end(a,x0,y0)
    if end<=x0+11:
        return a
    base=_dynamic_base(a,x0,y0,end)
    out=a.copy()
    bstart=_car_block_start(a,x0,y0,end)
    if bstart is None:
        # Plain cable contraction.
        out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out
    if bstart<=x0+6:
        return a
    # Pull the entire contiguous car block one cable cell left.
    block=a[y0:y0+6,bstart:end+1].copy()
    out[y0:y0+6,bstart-STEP:end+1]=base[y0:y0+6,bstart-STEP:end+1]
    out[y0:y0+6,bstart-STEP:end-STEP+1]=block
    return out

def _goal_sequence():
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    colors=_target_colors()
    items=[]
    for c in colors:
        ys,xs=np.where((e==c) & (np.indices(e.shape)[0]>sep))
        if len(xs):
            items.append((int(xs.min()),c))
    items.sort()
    return [c for _,c in items]

def _compact_sequence(a):
    loc=_engine(a)
    if loc is None:
        return None
    x0,y0=loc
    end=_strand_end(a,x0,y0)
    seq=[]
    for start in range(x0+6,end+1,STEP):
        found=None
        for c in _target_colors():
            if np.any(a[y0:y0+6,start:start+STEP]==c):
                found=c
                break
        if found is None:
            return None
        seq.append(found)
    return seq

def _completed(a):
    want=_goal_sequence()
    got=_compact_sequence(a)
    return bool(want) and got==want

def init_state(entry_grid):
    # The harness cannot replay the very first transition of the whole
    # run (it has no previous timeline frame). Level 0 therefore starts
    # its model rollout after one already-taken action; later levels do not.
    return {"turn": 1 if CURRENT_LEVEL == 0 else 0}

def predict(state, grid, action, x=None, y=None):
    a=np.array(grid,dtype=int)
    info={"level_up":False,"dead":False,"win":False}
    if action==1:
        out=_vertical(a,-STEP)
    elif action==2:
        out=_vertical(a,STEP)
    elif action==3:
        out=_retract(a)
    elif action==4:
        out=_extend(a)
    else:
        # Click/undo remain dormant until observed.
        out=a.copy()
    turn=int((state or {}).get("turn",0))+1
    # The 2/3 separator is a coarse move timer, not a rod/capture status:
    # one more right-to-left 3 appears on turns 4,7,10,...
    sep=_separator(out)
    n=max(0,(turn-1)//3)
    entry=np.array(ENTRY_GRID,dtype=int)
    esep=_separator(entry)
    if sep<out.shape[0] and esep<entry.shape[0]:
        out[sep,:]=entry[esep,:]
        if n:
            out[sep,max(0,out.shape[1]-n):]=3
    if _completed(out):
        info["level_up"]=True
    return out.tolist(),info,{"turn":turn}
