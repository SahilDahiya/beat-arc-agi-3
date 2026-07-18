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
    # Exterior/background is anchored by the top-left screen pixel;
    # on large boards color 4 can be the global mode, so mode is unsafe.
    bg=int(e[0,0])
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
    sep=_separator(e)
    # A target color occurs both in the play board and in the ordered
    # illustration below the separator.  This excludes level-specific
    # rails/anchors (for example a 2/3 vertical tether) without assuming
    # that every non-background play color is collectible.
    board=set(int(v) for v in np.unique(e[ty:by+1,lx:rx+1]))
    goal=set(int(v) for v in np.unique(e[sep+1:]))
    vals=board & goal
    for v in (0,1,2,4,6):
        vals.discard(v)
    return vals

def _dynamic_base(a, x0, y0, end):
    # Static target cells already joined to the contiguous train must no
    # longer reappear when that train moves away.
    b=_clean_base()
    e=np.array(ENTRY_GRID,dtype=int)
    lx,ty,rx,by=_board_bounds(e)
    colors=_target_colors()
    erased=np.zeros(e.shape,bool)
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
            mask=(e[ymin:ymax+1,xmin:xmax+1]==c)
            view=b[ymin:ymax+1,xmin:xmax+1]
            view[mask]=4
            erased[ymin:ymax+1,xmin:xmax+1] |= mask

    # Hanging cars can conceal a periodic two-column 2/3 tether.  Infer
    # each concealed column's three-row phase from the visible portions
    # immediately between cars, and reveal it when a car slides away.
    sep=_separator(e)
    for xx in range(e.shape[1]):
        ys=np.where(erased[:,xx])[0]
        if len(ys)==0:
            continue
        visible=np.where(((e[:sep,xx]==2)|(e[:sep,xx]==3)))[0]
        if not np.any(e[visible,xx]==3):
            continue
        phase={}
        for r in range(3):
            vr=visible[visible%3==r]
            if len(vr):
                vals=e[vr,xx]
                phase[r]=3 if np.sum(vals==3)>np.sum(vals==2) else 2
            else:
                phase[r]=2
        for yy in ys:
            b[yy,xx]=phase[int(yy)%3]
    return b

def _push_vertical_targets(a,out,x0,y0,ny,end,dy):
    # A horizontal rod moving vertically acts as a bar: any free colored
    # block intersected by its two scanlines is pushed one macro-row in
    # the same direction. Colored blocks already in the source rod move
    # with the rod instead and are excluded here.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(a)
    lx,ty,rx,by=_board_bounds(e)
    for c in _target_colors():
        seen=np.zeros(a.shape,bool)
        ys0,xs0=np.where((a==c) & (np.indices(a.shape)[0]<sep))
        for sx,sy in zip(xs0,ys0):
            if seen[sy,sx]:
                continue
            q=[(int(sx),int(sy))]; seen[sy,sx]=True; pts=[]
            for xx,yy in q:
                pts.append((xx,yy))
                for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xxx,yyy=xx+ddx,yy+ddy
                    if (0<=xxx<a.shape[1] and 0<=yyy<sep and
                        not seen[yyy,xxx] and a[yyy,xxx]==c):
                        seen[yyy,xxx]=True; q.append((xxx,yyy))
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
            in_source=(ymin>=y0 and ymax<=y0+5 and xmin>=x0 and xmax<=end)
            hit=(any(yy in (ny+2,ny+3) for yy in ys) and
                 any(x0+5<=xx<=end for xx in xs))
            if in_source or not hit:
                continue
            if ymin+dy<ty or ymax+dy>by:
                return False
            for xx,yy in pts:
                out[yy,xx]=4
            for xx,yy in pts:
                out[yy+dy,xx]=c
    return True

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
    if not _push_vertical_targets(a,out,x0,y0,ny,end,dy):
        return a
    dst=out[ny:ny+6,x0:end+1]
    dst[mask]=src[mask]
    return out

def _goal_car_marked(a,color):
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    yy,xx=np.indices(e.shape)
    ys,xs=np.where((e==color) & (yy>sep))
    if len(xs)==0:
        return False
    xmin,xmax=int(xs.min()),int(xs.max())
    ymin,ymax=int(ys.min()),int(ys.max())
    cx0=xmin+(xmax-xmin+1)//2-1
    cy0=ymin+(ymax-ymin+1)//2-1
    return bool(np.all(a[cy0:cy0+2,cx0:cx0+2]==0))

def _next_needed(a):
    for c in _goal_sequence():
        if not _goal_car_marked(a,c):
            return c
    return None

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

def _unmark_goal_car(out, color):
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    yy,xx=np.indices(e.shape)
    ys,xs=np.where((e==color) & (yy>sep))
    if len(xs)==0:
        return
    xmin,xmax=int(xs.min()),int(xs.max())
    ymin,ymax=int(ys.min()),int(ys.max())
    if xmax-xmin>=3 and ymax-ymin>=3:
        cx0=xmin+(xmax-xmin+1)//2-1
        cy0=ymin+(ymax-ymin+1)//2-1
        out[cy0:cy0+2,cx0:cx0+2]=e[cy0:cy0+2,cx0:cx0+2]

def _tile_has_car(a,y0,start):
    # Any colored block physically incorporated into the rod moves with
    # its contiguous tip block, even if its goal-order checkbox is unset.
    tile=a[y0:y0+6,start:start+STEP]
    return any(np.any(tile==c) for c in _target_colors())

def _car_block_start(a,x0,y0,end):
    # Return a contiguous car block only when it is at the active tip.
    last=end-STEP+1
    if last<x0+6 or not _tile_has_car(a,y0,last):
        return None
    start=last
    while start-STEP>=x0+6 and _tile_has_car(a,y0,start-STEP):
        start-=STEP
    return start

def _car_block_bounds(a,x0,y0,end):
    # A tether can let cable continue beyond a car.  Find the first
    # contiguous incorporated car block anywhere along the active strand.
    starts=list(range(x0+6,end-STEP+2,STEP))
    first=None
    last=None
    for start in starts:
        if _tile_has_car(a,y0,start):
            if first is None:
                first=start
            last=start
        elif first is not None:
            break
    if first is None:
        return None
    return first,last+STEP-1

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
        # A free target is pushed, rather than coupled, whenever the whole
        # contiguous train/target run still has an empty cell on its right.
        # The free target keeps its plain 4 border while moving; it is only
        # coupled on a later extension once something blocks that push.
        chain_end=nxt
        while chain_end+STEP<=rx and _tile_has_car(a,y0,chain_end+STEP):
            chain_end+=STEP
        # A 2/3 tether crossing the target cell anchors it to the vertical
        # rail.  Anchored cars couple in place even with empty space right.
        anchored=bool(np.any(old==3))
        can_push=(not anchored and
                  chain_end+2*STEP-1<=rx and
                  not _tile_has_car(a,y0,chain_end+STEP))
        if can_push:
            bstart=_car_block_start(a,x0,y0,end)
            start=nxt if bstart is None else bstart
            block=a[y0:y0+6,start:chain_end+STEP].copy()
            base=_dynamic_base(a,x0,y0,end)
            restore=base[y0:y0+6,start:start+STEP].copy()
            # With no previously caught car, clean the original static
            # target out of the cell that becomes new cable.
            for c in colors:
                restore[restore==c]=4
            out[y0:y0+6,start:start+STEP]=restore
            _put_pattern(out,x0,y0,start)
            out[y0:y0+6,start+STEP:chain_end+2*STEP]=block
            return out

        # The target run cannot move: couple its first cell in place.
        _put_pattern(out,x0,y0,nxt)
        reg=out[y0:y0+6,nxt:nxt+STEP]
        needed=_next_needed(a)
        prior=[]
        for pc in colors:
            if np.any(a[y0:y0+6,x0+6:end+1]==pc):
                prior.append(pc)
        clear_path=all(_goal_car_marked(a,pc) for pc in prior)
        for c in caught:
            reg[old==c]=c
            # Rod can pass through wrong cars, but a needed car only
            # latches when every earlier colored cell in the rod is
            # already part of the checked train.
            if c==needed and clear_path:
                _mark_goal_car(out,c)
        return out
    bstart=_car_block_start(a,x0,y0,end)
    if bstart is None:
        # No caught cars yet: telescope one plain cable cell.
        _put_pattern(out,x0,y0,nxt)
    elif np.any(a[y0:y0+6,bstart:end+1]==3):
        # A car still crossing a vertical tether cannot be shifted right.
        # Extension threads more cable through and beyond it instead.
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
    bounds=_car_block_bounds(a,x0,y0,end)
    if bounds is None:
        # Plain cable contraction.
        out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out

    bstart,bend=bounds
    last=bend-STEP+1
    # A car still crossing a vertical tether cannot be pulled left.
    # If it is at the strand tip, retraction simply uncouples it in place.
    if bend==end and np.any(a[y0:y0+6,last:last+STEP]==3):
        tile=a[y0:y0+6,last:last+STEP].copy()
        tethered=[c for c in _target_colors() if np.any(tile==c)]
        raw=base[y0:y0+6,last:last+STEP].copy()
        for c in tethered:
            raw[tile==c]=c
        out[y0:y0+6,last:last+STEP]=raw
        # The lower hollow is a live coupling indicator on tethered cars;
        # detaching restores it rather than banking permanent progress.
        for c in tethered:
            _unmark_goal_car(out,c)
        return out

    if bstart>x0+6:
        # Pull the incorporated block one cable cell toward the engine.
        # Usually the block is the tip and the strand shrinks.  A tether
        # can, however, leave cable beyond the extracted car; in that case
        # the tail stays put and the vacated car cell becomes plain cable.
        block=a[y0:y0+6,bstart:bend+1].copy()
        out[y0:y0+6,bstart-STEP:bend+1]=base[y0:y0+6,bstart-STEP:bend+1]
        out[y0:y0+6,bstart-STEP:bend-STEP+1]=block
        if bend<end:
            _put_pattern(out,x0,y0,bend-STEP+1)
            # Retraction still shortens the whole telescope: the vacated
            # car cell becomes cable while the farthest tail cell vanishes.
            out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out

    # A compact car block cannot move farther left.  Retract any cable
    # tail that was threaded beyond a tethered car, one far cell at a time.
    if end>bend:
        out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out
    return a

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
    # Completion fires immediately when the final required car is caught;
    # the lower illustration records this by hollowing every car's center.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    any_car=False
    for c in _target_colors():
        ys,xs=np.where((e==c) & (np.indices(e.shape)[0]>sep))
        if len(xs)==0:
            continue
        any_car=True
        xmin,xmax=int(xs.min()),int(xs.max())
        ymin,ymax=int(ys.min()),int(ys.max())
        cx0=xmin+(xmax-xmin+1)//2-1
        cy0=ymin+(ymax-ymin+1)//2-1
        if not np.all(a[cy0:cy0+2,cx0:cx0+2]==0):
            return False
    return any_car

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
    turn=int((state or {}).get("turn",0))
    if action in (1,2,3,4):
        turn+=1
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
