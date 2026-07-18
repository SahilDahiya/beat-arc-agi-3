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
    for v in (0,1,2,3,4,6):
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

            # Some levels begin with cars already threaded on the engine's
            # horizontal cable.  Their 1/2 connector boundary is dynamic,
            # not board background, so erase it together with the car.
            px0=max(0,xmin-1); px1=min(e.shape[1]-1,xmax+1)
            py0=max(0,ymin-1); py1=min(e.shape[0]-1,ymax+1)
            left=e[ymin:ymax+1,px0]
            right=e[ymin:ymax+1,px1]
            prejoined=(np.any((left==1)|(left==2)) or
                       np.any((right==1)|(right==2)))
            if prejoined:
                p=e[py0:py1+1,px0:px1+1]
                pv=b[py0:py1+1,px0:px1+1]
                pv[(p==1)|(p==2)]=4

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
        lo,hi=int(visible.min()),int(visible.max())
        for yy in ys:
            # The tether is finite; aligned cars below its visible end do
            # not conceal an imaginary continuation.
            if lo<=int(yy)<=hi:
                b[yy,xx]=phase[int(yy)%3]
    return b

def _push_vertical_targets(a,out,x0,y0,ny,end,dy):
    # A horizontal rod moving vertically acts as a bar.  A contacted free
    # car is pushed one macro-row; if its destination is occupied by another
    # car, that car (and the rest of the column) is pushed recursively.
    # Cars already embedded in the source rod move with the rod separately.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(a)
    lx,ty,rx,by=_board_bounds(e)
    comps=[]
    yygrid=np.indices(a.shape)[0]
    for c in _target_colors():
        seen=np.zeros(a.shape,bool)
        ys0,xs0=np.where((a==c) & (yygrid<sep))
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
            in_source=(ymin>=y0 and ymax<=y0+5 and
                       xmin>=x0 and xmax<=end)
            comps.append({"c":c, "pts":pts, "set":set(pts),
                          "in_source":in_source,
                          "box":(xmin,ymin,xmax,ymax)})

    moving=set()
    for i,co in enumerate(comps):
        if co["in_source"]:
            continue
        pts=co["pts"]
        hit=(any(yy in (ny+2,ny+3) for xx,yy in pts) and
             any(x0+5<=xx<=end for xx,yy in pts))
        if hit:
            moving.add(i)

    # Closure under destination collisions gives a simultaneous chain push.
    changed=True
    while changed:
        changed=False
        destinations=set()
        for i in moving:
            destinations.update((xx,yy+dy) for xx,yy in comps[i]["pts"])
        for j,co in enumerate(comps):
            if j in moving or co["in_source"]:
                continue
            if destinations & co["set"]:
                moving.add(j)
                changed=True

    for i in moving:
        xmin,ymin,xmax,ymax=comps[i]["box"]
        if ymin+dy<ty or ymax+dy>by:
            return False

    # Clear every source before writing any destination, so adjacent cars do
    # not erase one another during the simultaneous push.  Build the base
    # after pretending the moving cars are absent; this reveals any concealed
    # 2/3 tether instead of replacing it with plain board color.
    abase=a.copy()
    for i in moving:
        for xx,yy in comps[i]["pts"]:
            abase[yy,xx]=4
    restore=_dynamic_base(abase,x0,y0,end)
    for i in moving:
        for xx,yy in comps[i]["pts"]:
            out[yy,xx]=restore[yy,xx]
    for i in moving:
        co=comps[i]
        for xx,yy in co["pts"]:
            out[yy+dy,xx]=co["c"]
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

    # In anchor levels a car is checked off while the next globally required
    # live car occupies its own finite tether.  Entering from below checks it;
    # carrying it back out below clears the check again. Cars before it on the
    # rod must already be checked, rejecting a wrong-order prefix [9,e,8].
    if _anchored_goal_mode():
        entry=np.array(ENTRY_GRID,dtype=int)
        specs=_anchor_specs()
        if dy<0:
            needed=_next_needed(a)
            active=_active_sequence(a)
            if needed is not None and needed in active:
                before=active[:active.index(needed)]
                clear=all(_goal_car_marked(a,c) for c in before)
                for spec in specs:
                    if needed not in spec["seq"] or not clear:
                        continue
                    ax0,ax1=spec["x0"],spec["x1"]
                    src_static=entry[y0:y0+6,ax0:ax1+1]
                    dst_static=entry[ny:ny+6,ax0:ax1+1]
                    src_tether=np.any((src_static==2)|(src_static==3))
                    dst_tether=np.any((dst_static==2)|(dst_static==3))
                    carried=np.any(a[y0:y0+6,ax0:ax1+1]==needed)
                    if carried and dst_tether and not src_tether:
                        _mark_goal_car(out,needed,force=True)
                        break
        elif dy>0:
            for spec in specs:
                ax0,ax1=spec["x0"],spec["x1"]
                src_static=entry[y0:y0+6,ax0:ax1+1]
                dst_static=entry[ny:ny+6,ax0:ax1+1]
                src_tether=np.any((src_static==2)|(src_static==3))
                dst_tether=np.any((dst_static==2)|(dst_static==3))
                if src_tether and not dst_tether:
                    for c in spec["seq"]:
                        if (_goal_car_marked(a,c) and
                            np.any(a[y0:y0+6,ax0:ax1+1]==c)):
                            _unmark_goal_car(out,c)
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

def _anchored_goal_mode():
    # Extra colours repeated as a button above a vertical play tether and
    # as a head in the lower diagram identify multi-output/anchor levels.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    above=set(int(v) for v in np.unique(e[:sep]))
    below=set(int(v) for v in np.unique(e[sep+1:]))
    extras=(above & below) - set(_target_colors()) - {0,1,2,3,4,5,6}
    return bool(extras)

def _anchor_specs():
    # Pair each lower goal car with the closest anchor head to its left, and
    # retain the matching play-tether x range for delivery detection.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    yy,xx=np.indices(e.shape)
    above=set(int(v) for v in np.unique(e[:sep]))
    below=set(int(v) for v in np.unique(e[sep+1:]))
    extras=sorted((above & below) - set(_target_colors()) -
                  {0,1,2,3,4,5,6})
    specs=[]
    for c in extras:
        py,px=np.where((e==c) & (yy<sep))
        gy,gx=np.where((e==c) & (yy>sep))
        if len(px) and len(gx):
            specs.append({"color":c, "x0":int(px.min()), "x1":int(px.max()),
                          "goal_x":int(gx.max()), "seq":[]})
    for c in _target_colors():
        ys,xs=np.where((e==c) & (yy>sep))
        if not len(xs):
            continue
        tx=int(xs.min())
        candidates=[s for s in specs if s["goal_x"]<tx]
        if candidates:
            s=max(candidates,key=lambda q:q["goal_x"])
            s["seq"].append((tx,c))
    for s in specs:
        s["seq"]=[c for _,c in sorted(s["seq"])]
    return specs

def _mark_goal_car(out, color, force=False):
    # The lower illustration is also the live progress display.  On anchor
    # levels it changes only on a verified tether delivery, hence force=True.
    if _anchored_goal_mode() and not force:
        return
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
    # Slide every untethered car group one cable cell right.  Cable gaps
    # can split the carried cars into several groups; they move
    # simultaneously, while any group crossing a 2/3 tether stays pinned.
    starts=list(range(x0+6,end-STEP+2,STEP))
    groups=[]
    cur=[]
    for s in starts:
        if _tile_has_car(a,y0,s):
            cur.append(s)
        elif cur:
            groups.append(cur); cur=[]
    if cur:
        groups.append(cur)

    if not groups:
        _put_pattern(out,x0,y0,nxt)
        return out

    base=_dynamic_base(a,x0,y0,end)
    moving=[]
    for group in groups:
        gs,ge=group[0],group[-1]+STEP-1
        # A group is pinned both while it crosses a tether and when its
        # leading car would enter a tether on this rightward slide.
        anchored=(np.any(a[y0:y0+6,gs:ge+1]==3) or
                  np.any(a[y0:y0+6,ge+1:ge+STEP+1]==3))
        if not anchored:
            moving.append((gs,ge,a[y0:y0+6,gs:ge+1].copy()))

    for gs,ge,block in moving:
        out[y0:y0+6,gs:ge+1]=base[y0:y0+6,gs:ge+1]
        for s in range(gs,ge+1,STEP):
            _put_pattern(out,x0,y0,s)
    for gs,ge,block in moving:
        out[y0:y0+6,gs+STEP:ge+STEP+1]=block

    tip_group=groups[-1]
    tgs,tge=tip_group[0],tip_group[-1]+STEP-1
    if (tge<end or np.any(a[y0:y0+6,tgs:tge+1]==3)):
        # Extension always lengthens the telescope.  When the last car is
        # separated from the old tip by a cable tail (or is pinned), no car
        # enters the new cell, so thread a plain cable cell there.
        _put_pattern(out,x0,y0,nxt)
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

    # With several cars crossing parallel tethers, the first anchored car
    # pins the right side of the strand.  Retraction slides only the mobile
    # car prefix left through the cable; the anchored suffix and tip stay.
    starts=list(range(x0+6,end-STEP+2,STEP))
    tether_starts=[s for s in starts
                   if (_tile_has_car(a,y0,s) and
                       np.any(a[y0:y0+6,s:s+STEP]==3))]
    if tether_starts:
        first_t=min(tether_starts)

        # A tether is a barrier, not merely a cut between one large prefix
        # and suffix.  Cable gaps split the mobile prefix into independent
        # car groups.  Each group may slide left only when the immediately
        # preceding cell is not itself a vertical tether.
        groups=[]
        cur=[]
        for s in starts:
            if s>=first_t:
                break
            if _tile_has_car(a,y0,s):
                cur.append(s)
            elif cur:
                groups.append(cur); cur=[]
        if cur:
            groups.append(cur)

        moving=[]
        for group in groups:
            gs,ge=group[0],group[-1]+STEP-1
            dest=gs-STEP
            if (gs>x0+6 and
                not np.any(a[y0:y0+6,dest:dest+STEP]==3) and
                not _tile_has_car(a,y0,dest)):
                moving.append((gs,ge,a[y0:y0+6,gs:ge+1].copy()))

        for gs,ge,block in moving:
            out[y0:y0+6,gs:ge+1]=base[y0:y0+6,gs:ge+1]
            for s in range(gs,ge+1,STEP):
                _put_pattern(out,x0,y0,s)
        for gs,ge,block in moving:
            out[y0:y0+6,gs-STEP:ge-STEP+1]=block

        # Retraction releases a tethered car at the far tip, independently
        # of whichever mobile prefix groups were able to slide.
        tip=end-STEP+1
        detached=False
        if np.any(a[y0:y0+6,tip:tip+STEP]==3):
            tile=a[y0:y0+6,tip:tip+STEP].copy()
            held=[c for c in _target_colors() if np.any(tile==c)]
            raw=base[y0:y0+6,tip:tip+STEP].copy()
            for c in held:
                raw[tile==c]=c
            out[y0:y0+6,tip:tip+STEP]=raw
            for c in held:
                _unmark_goal_car(out,c)
            detached=True

        # If the anchored car is followed only by threaded cable, the
        # telescope can still retract that tail one far cell at a time.
        if (not detached and
            not _tile_has_car(a,y0,tip)):
            out[y0:y0+6,tip:tip+STEP]=base[y0:y0+6,tip:tip+STEP]

        # The anchored part of the strand cannot be handled by the generic
        # contiguous-block pull below, even if nothing moved this turn.
        return out

    # Away from anchored cars, cable gaps split the train into independent
    # sliding groups.  Retraction is the exact leftward counterpart of
    # extension: every group with a free non-tether cell on its left moves
    # simultaneously, while the telescope loses its farthest cell.
    groups=[]
    cur=[]
    for s in starts:
        if _tile_has_car(a,y0,s):
            cur.append(s)
        elif cur:
            groups.append(cur); cur=[]
    if cur:
        groups.append(cur)

    if not groups:
        # Plain cable contraction.
        out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out

    moving=[]
    for group in groups:
        gs,ge=group[0],group[-1]+STEP-1
        dest=gs-STEP
        if (gs>x0+6 and
            not _tile_has_car(a,y0,dest) and
            not np.any(a[y0:y0+6,dest:dest+STEP]==3)):
            moving.append((gs,ge,a[y0:y0+6,gs:ge+1].copy()))

    if moving:
        for gs,ge,block in moving:
            out[y0:y0+6,gs:ge+1]=base[y0:y0+6,gs:ge+1]
            for s in range(gs,ge+1,STEP):
                _put_pattern(out,x0,y0,s)
        for gs,ge,block in moving:
            out[y0:y0+6,gs-STEP:ge-STEP+1]=block
        out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out

    # No car can slide, but a cable tail beyond the last car can still
    # telescope inward one cell.
    last_end=groups[-1][-1]+STEP-1
    if end>last_end:
        out[y0:y0+6,end-STEP+1:end+1]=base[y0:y0+6,end-STEP+1:end+1]
        return out

    # A fully compact multi-car train has no leftward room.  Retraction then
    # uncouples its far car in place, turning only that tip tile back into a
    # raw target while the shorter prefix remains attached.
    if (len(groups)==1 and len(groups[0])>=2 and
        groups[0][0]==x0+6 and last_end==end):
        tip=groups[0][-1]
        tile=a[y0:y0+6,tip:tip+STEP].copy()
        raw=base[y0:y0+6,tip:tip+STEP].copy()
        held=[c for c in _target_colors() if np.any(tile==c)]
        for c in held:
            raw[tile==c]=c
            _unmark_goal_car(out,c)
        out[y0:y0+6,tip:tip+STEP]=raw
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

def _active_sequence(a):
    # Read colored cars along the live telescope while ignoring leading
    # cable cells.  Anchor/tether levels use their two lower diagrams as one
    # concatenated output specification; sorting is complete when the live
    # train has that full color order, even if it is displaced toward a wall.
    loc=_engine(a)
    if loc is None:
        return []
    x0,y0=loc
    end=_strand_end(a,x0,y0)
    seq=[]
    for start in range(x0+6,end+1,STEP):
        for c in _target_colors():
            if np.any(a[y0:y0+6,start:start+STEP]==c):
                seq.append(c)
                break
    return seq

def _completed(a):
    # Completion fires immediately when the final required car is caught.
    # Ordinary levels record this by hollowing every goal car.  Anchor/tether
    # levels instead keep static diagrams and validate the sorted live train.
    if _anchored_goal_mode():
        colors=_goal_sequence()
        return bool(colors) and all(_goal_car_marked(a,c) for c in colors)
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

def _wall_sorted_push(a):
    if not _anchored_goal_mode():
        return False
    # When the last raw car of the complete ordered output is pushed into
    # the board's rightmost macro-cell, the spatial action advances hidden
    # phase but defers redrawing the separator until the following action.
    loc=_engine(a)
    if loc is None:
        return False
    x0,y0=loc
    lx,ty,rx,by=_board_bounds(np.array(ENTRY_GRID,dtype=int))
    end=_strand_end(a,x0,y0)
    if end+STEP>rx:
        return False
    nxt=end+1
    old=a[y0:y0+STEP,nxt:nxt+STEP]
    caught=[c for c in _target_colors() if np.any(old==c)]
    if not caught:
        return False
    chain_end=nxt
    while chain_end+STEP<=rx and _tile_has_car(a,y0,chain_end+STEP):
        chain_end+=STEP
    anchored=bool(np.any(old==3))
    can_push=(not anchored and chain_end+2*STEP-1<=rx and
              not _tile_has_car(a,y0,chain_end+STEP))
    if not can_push or chain_end+2*STEP-1!=rx:
        return False
    seq=_active_sequence(a)
    for s in range(nxt,chain_end+1,STEP):
        for c in _target_colors():
            if np.any(a[y0:y0+STEP,s:s+STEP]==c):
                seq.append(c)
                break
    return seq==_goal_sequence()

def init_state(entry_grid):
    # The harness cannot replay the very first transition of the whole
    # run (it has no previous timeline frame). Level 0 therefore starts
    # its model rollout after one already-taken action; later levels do not.
    return {"turn": 1 if CURRENT_LEVEL == 0 else 0, "undo":[],
            "wall_pushes":0}

def predict(state, grid, action, x=None, y=None):
    a=np.array(grid,dtype=int)
    info={"level_up":False,"dead":False,"win":False}
    st=state or {}
    turn=int(st.get("turn",0))
    undo=list(st.get("undo",[]))
    wall_pushes=int(st.get("wall_pushes",0))
    # Undo/click and compact-tip uncoupling leave the rendered separator
    # unchanged even when hidden simple-action phase changes.
    wall_event=(action==4 and _wall_sorted_push(a))
    # The first completed-output wall arrival establishes an irreversible
    # hidden milestone. Repeating it after undo is free, though both arrivals
    # defer the timer redraw.
    free_special=(wall_event and wall_pushes>0)
    preserve_timer=(action in (6,7) or wall_event)
    if wall_event:
        wall_pushes+=1

    if action==7:
        # ACTION7 is a true one-step undo: restore both the rendered frame
        # and the simple-action timer, and pop so repeated undo walks back.
        if undo:
            prev,_old_turn=undo[-1]
            out=np.array(prev,dtype=int)
            undo=undo[:-1]
        else:
            out=a.copy()
    else:
        # Every ordinary action is an undo checkpoint, including inert
        # clicks; RESET is reinitialized by the framework.
        undo.append((a.tolist(),turn))
        # Uncoupling a tip exactly at the lower endpoint of a finite
        # vertical tether is a free release; unlike ordinary simple actions
        # it does not advance the separator timer.
        free_release=False
        if action==3:
            loc=_engine(a)
            if loc is not None:
                ex,ey=loc
                ee=_strand_end(a,ex,ey)
                tip=ee-STEP+1
                tile=a[ey:ey+STEP,tip:tip+STEP]
                below=a[ey+STEP:ey+2*STEP,tip:tip+STEP]
                free_release=(_tile_has_car(a,ey,tip) and
                              np.any(tile==3) and
                              below.size>0 and not np.any(below==3) and
                              not any(np.any(below==c)
                                      for c in _target_colors()))
                # Popping the far car off a fully compact multi-car train
                # advances the hidden action phase, but (like undo/click)
                # does not redraw the separator until a later ordinary move.
                compact=_compact_sequence(a)
                if compact is not None and len(compact)>=3:
                    preserve_timer=True
        if action==1:
            out=_vertical(a,-STEP)
        elif action==2:
            out=_vertical(a,STEP)
        elif action==3:
            out=_retract(a)
        elif action==4:
            out=_extend(a)
        else:
            out=a.copy()
        if action in (1,2,3,4) and not free_release and not free_special:
            turn+=1
    # The 2/3 separator is a coarse move timer, not a rod/capture status:
    # one more right-to-left 3 appears on turns 4,7,10,...
    sep=_separator(out)
    n=max(0,(turn-1)//3)
    entry=np.array(ENTRY_GRID,dtype=int)
    esep=_separator(entry)
    if sep<out.shape[0] and esep<entry.shape[0]:
        if preserve_timer:
            asep=_separator(a)
            if asep<a.shape[0]:
                out[sep,:]=a[asep,:]
        else:
            out[sep,:]=entry[esep,:]
            if n:
                out[sep,max(0,out.shape[1]-n):]=3
    if _completed(out):
        info["level_up"]=True
    return out.tolist(),info,{"turn":turn,"undo":undo,
                                  "wall_pushes":wall_pushes}


def is_goal(state, grid):
    return _completed(np.array(grid,dtype=int))
