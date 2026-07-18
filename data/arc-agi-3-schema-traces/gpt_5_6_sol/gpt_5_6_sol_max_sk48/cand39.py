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
            top_inner=a[y+1,x+1:x+5]
            bot_inner=a[y+4,x+1:x+5]
            parked=(np.all(top_inner==4) and np.all(bot_inner==4))
            active=(np.all(top_inner==0) and np.all(bot_inner==0))
            if (np.all(a[y, x:x+6] == 6) and
                a[y+1,x] == 6 and a[y+1,x+5] == 6 and
                a[y+4,x] == 6 and a[y+4,x+5] == 6 and
                np.all(a[y+5,x:x+6] == 6) and (active or parked)):
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
    # Treat each entry car glyph independently.  Repeated adjacent colors are
    # separate 4x4 components divided by their connector/border pixels.
    for c in colors:
        mask_all=(e==c)
        yygrid,xxgrid=np.indices(e.shape)
        mask_all &= ((xxgrid>=lx)&(xxgrid<=rx)&
                     (yygrid>=ty)&(yygrid<=by))
        seen=np.zeros(e.shape,dtype=bool)
        ys0,xs0=np.where(mask_all)
        for sy,sx in zip(ys0,xs0):
            sy=int(sy); sx=int(sx)
            if seen[sy,sx]:
                continue
            q=[(sx,sy)]; seen[sy,sx]=True; pts=[]
            while q:
                px,py=q.pop()
                pts.append((px,py))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=px+dx,py+dy
                    if (0<=nx<e.shape[1] and 0<=ny<e.shape[0] and
                        mask_all[ny,nx] and not seen[ny,nx]):
                        seen[ny,nx]=True
                        q.append((nx,ny))
            xx=[p[0] for p in pts]; yy=[p[1] for p in pts]
            xmin,xmax=min(xx),max(xx)
            ymin,ymax=min(yy),max(yy)
            absent=not np.any(a[ymin:ymax+1,xmin:xmax+1]==c)
            joined=(ymin>=y0 and ymax<=y0+5 and
                    xmax<=end and xmin>=x0)
            if absent or joined:
                cmask=(e[ymin:ymax+1,xmin:xmax+1]==c)
                view=b[ymin:ymax+1,xmin:xmax+1]
                view[cmask]=4
                erased[ymin:ymax+1,xmin:xmax+1] |= cmask

                # Some levels begin with cars already threaded on the engine's
                # horizontal cable. Their 1/2 boundary is dynamic too.
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

    # Internal cells painted with the exterior background are solid holes.
    # The engine itself lives outside the board, but no opaque rod/car pixel
    # inside the board may be carried vertically into such a cell.
    dst_base=base[ny:ny+6,x0:end+1]
    bg=int(np.array(ENTRY_GRID,dtype=int)[0,0])
    gx=np.arange(x0,end+1)
    inside=((gx>=lx)&(gx<=rx))[None,:]
    # Internal holes block vertical motion of both cars and the thin cable.
    if np.any(mask & inside & (dst_base==bg)):
        return a

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

def _goal_slots():
    # Each 4x4 car glyph in the lower illustration is an independent
    # progress slot.  Split by connected component rather than taking one
    # color-wide bounding box: later levels can repeat a color (8,9,8).
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    slots=[]
    h,w=e.shape
    for color in _target_colors():
        mask=(e==color)
        mask[:sep+1,:]=False
        seen=np.zeros(e.shape,dtype=bool)
        ys,xs=np.where(mask)
        for sy,sx in zip(ys,xs):
            sy=int(sy); sx=int(sx)
            if seen[sy,sx]:
                continue
            stack=[(sx,sy)]
            seen[sy,sx]=True
            pts=[]
            while stack:
                px,py=stack.pop()
                pts.append((px,py))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=px+dx,py+dy
                    if (0<=nx<w and 0<=ny<h and mask[ny,nx] and
                        not seen[ny,nx]):
                        seen[ny,nx]=True
                        stack.append((nx,ny))
            xx=[p[0] for p in pts]
            yy=[p[1] for p in pts]
            xmin,xmax=min(xx),max(xx)
            ymin,ymax=min(yy),max(yy)
            if xmax-xmin>=3 and ymax-ymin>=3:
                cx0=xmin+(xmax-xmin+1)//2-1
                cy0=ymin+(ymax-ymin+1)//2-1
                slots.append({"color":int(color), "x":xmin,
                              "cx0":cx0, "cy0":cy0})
    slots.sort(key=lambda q:q["x"])
    return slots

def _goal_slot_marked(a,slot):
    x,y=slot["cx0"],slot["cy0"]
    return bool(np.all(a[y:y+2,x:x+2]==0))

def _goal_car_marked(a,color):
    # For movement-order checks, a color is established once any one of its
    # slots is checked.  Slot multiplicity is handled by _next_needed and
    # _completed below.
    slots=[s for s in _goal_slots() if s["color"]==color]
    return bool(slots) and any(_goal_slot_marked(a,s) for s in slots)

def _next_needed(a):
    for slot in _goal_slots():
        if not _goal_slot_marked(a,slot):
            return slot["color"]
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
    # Repeated colors fill their independent slots from left to right.
    for slot in _goal_slots():
        if slot["color"]==color and not _goal_slot_marked(out,slot):
            x,y=slot["cx0"],slot["cy0"]
            out[y:y+2,x:x+2]=0
            return

def _unmark_goal_car(out, color):
    # Undo the most recently filled non-prefilled slot.  Entry-preset slots
    # (level 4's middle 9) are permanent requirements already satisfied.
    e=np.array(ENTRY_GRID,dtype=int)
    slots=[s for s in _goal_slots() if s["color"]==color]
    for slot in reversed(slots):
        x,y=slot["cx0"],slot["cy0"]
        entry_marked=bool(np.all(e[y:y+2,x:x+2]==0))
        if not entry_marked and _goal_slot_marked(out,slot):
            out[y:y+2,x:x+2]=e[y:y+2,x:x+2]
            return

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
        base=_dynamic_base(a,x0,y0,end)
        dest0=chain_end+STEP
        dest_base=base[y0:y0+6,dest0:dest0+STEP]
        # A non-car macro-cell is not necessarily empty: internal color-5
        # blocks are solid walls.  A pushed run needs a genuinely clear
        # board-background (4) cell beyond it.
        can_push=(not anchored and
                  chain_end+2*STEP-1<=rx and
                  not _tile_has_car(a,y0,dest0) and
                  dest_base.shape==(STEP,STEP) and
                  np.all(dest_base==4))
        if can_push:
            bstart=_car_block_start(a,x0,y0,end)
            start=nxt if bstart is None else bstart
            block=a[y0:y0+6,start:chain_end+STEP].copy()
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

    base=_dynamic_base(a,x0,y0,end)
    if not groups:
        dest_base=base[y0:y0+6,nxt:nxt+STEP]
        bg=int(np.array(ENTRY_GRID,dtype=int)[0,0])
        if (dest_base.shape==(STEP,STEP) and
            not np.any(dest_base==bg)):
            _put_pattern(out,x0,y0,nxt)
            return out
        return a

    moving=[]
    for group in groups:
        gs,ge=group[0],group[-1]+STEP-1
        dest0=ge+1
        dest_base=base[y0:y0+6,dest0:dest0+STEP]
        # A group is pinned while crossing/entering a tether, and any solid
        # internal obstacle blocks its leading cell exactly like a wall.
        anchored=(np.any(a[y0:y0+6,gs:ge+1]==3) or
                  np.any(a[y0:y0+6,dest0:dest0+STEP]==3))
        open_dest=(dest_base.shape==(STEP,STEP) and
                   np.all(dest_base==4))
        if not anchored and open_dest:
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
    if end<x0+11:
        return a
    base=_dynamic_base(a,x0,y0,end)
    out=a.copy()
    # Even the final compact car can be released: restore its plain border
    # and leave the colored 4x4 body raw in place.
    if end==x0+11 and _tile_has_car(a,y0,x0+6):
        tip=x0+6
        tile=a[y0:y0+STEP,tip:tip+STEP].copy()
        raw=base[y0:y0+STEP,tip:tip+STEP].copy()
        for c in _target_colors():
            raw[tile==c]=c
        out[y0:y0+STEP,tip:tip+STEP]=raw
        return out

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
            # On anchor-output levels a correctly checked car is banked by
            # releasing it raw on its tether; its goal hollow persists.  The
            # ordinary single-tether levels instead clear the check on release.
            if not _anchored_goal_mode():
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
    return [slot["color"] for slot in _goal_slots()]

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

def _top_active_sequence(a):
    loc=_current_top_frame(a)
    if loc is None:
        return []
    x0,y0=loc
    end=_top_strand_end(a,x0,y0)
    seq=[]
    for start in range(y0+STEP,end+1,STEP):
        for c in _target_colors():
            if np.any(a[start:start+STEP,x0:x0+STEP]==c):
                seq.append(c)
                break
    return seq


def _sync_ordinary_goals(out):
    # Dual-crane specifications are two independent live sequences. Switching
    # controllers recolours but does not erase the parked train.
    frames=_dual_controller_frames(out)
    slots=_goal_slots()
    if frames is not None:
        split=frames["top_goal"][0]
        left=[s for s in slots if s["x"]<split]
        top=[s for s in slots if s["x"]>split]
        groups=((left,_active_sequence(out)),
                (top,_top_active_sequence(out)))
        entry=np.array(ENTRY_GRID,dtype=int)
        for group,seq in groups:
            for i,slot in enumerate(group):
                x,y=slot["cx0"],slot["cy0"]
                if i<len(seq) and seq[i]==slot["color"]:
                    out[y:y+2,x:x+2]=0
                else:
                    out[y:y+2,x:x+2]=entry[y:y+2,x:x+2]
        return

    # Ordinary lower diagrams compare train positions independently.  A slot
    # is hollow exactly when the car at the same live-sequence index matches
    # its requested color.  This explains level 4's initially hollow middle
    # 9 despite mismatching 9s on both sides.
    if _anchored_goal_mode():
        return
    seq=_active_sequence(out)
    for i,slot in enumerate(slots):
        x,y=slot["cx0"],slot["cy0"]
        if i<len(seq) and seq[i]==slot["color"]:
            out[y:y+2,x:x+2]=0
        else:
            out[y:y+2,x:x+2]=slot["color"]

def _completed(a):
    # Completion fires once every independent lower-diagram slot is hollow.
    # Components matter when one color appears more than once.
    slots=_goal_slots()
    return bool(slots) and all(_goal_slot_marked(a,s) for s in slots)

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

def _empty_tether_exit(a, action):
    # Lowering an empty rod across the bottom edge of the finite output
    # tethers to fetch the last outstanding car is a free staging move:
    # it moves spatially but does not advance the fuse.
    if action!=2 or not _anchored_goal_mode() or _active_sequence(a):
        return False
    seq=_goal_sequence()
    # This deferred exit is the final-output staging transition: earlier
    # trips below the tethers redraw normally.
    if sum(1 for c in seq if _goal_car_marked(a,c)) != len(seq)-1:
        return False
    loc=_engine(a)
    if loc is None:
        return False
    _,ey=loc
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    bottoms=[]
    for s in _anchor_specs():
        for xx in range(s["x0"],s["x1"]+1):
            ys=np.where(((e[:sep,xx]==2)|(e[:sep,xx]==3)))[0]
            if len(ys):
                bottoms.append(int(ys.max()))
    return bool(bottoms) and ey<=max(bottoms)<ey+STEP


def _dual_controller_frames(a):
    # Some later boards have two orthogonal engines: the ordinary 6-frame on
    # the left and a coloured 6-frame on the top rail.  Return their play and
    # lower-diagram frames, grounded entirely from the entry layout.
    e=np.array(ENTRY_GRID,dtype=int)
    sep=_separator(e)
    h,w=e.shape
    standard=[]
    for y in range(h-5):
        for x in range(w-5):
            if (np.all(e[y,x:x+6]==6) and np.all(e[y+5,x:x+6]==6) and
                    e[y+1,x]==6 and e[y+1,x+5]==6 and
                    e[y+4,x]==6 and e[y+4,x+5]==6):
                standard.append((x,y))
    above=set(int(v) for v in np.unique(e[:sep]))
    below=set(int(v) for v in np.unique(e[sep+1:]))
    extras=(above & below) - _target_colors() - {0,1,2,3,4,5,6}
    alternate=[]
    for c in extras:
        for y in range(h-5):
            for x in range(w-5):
                if (np.sum(e[y,x:x+6]==c)>=4 and
                        np.sum(e[y+5,x:x+6]==c)>=4 and
                        np.sum(e[y:y+6,x]==c)>=4 and
                        np.sum(e[y:y+6,x+5]==c)>=4 and
                        np.all(e[y+2:y+4,x+2:x+4]==c)):
                    alternate.append((x,y,c))
    sp=[q for q in standard if q[1]<sep]
    sg=[q for q in standard if q[1]>sep]
    ap=[q for q in alternate if q[1]<sep]
    ag=[q for q in alternate if q[1]>sep]
    if not (sp and sg and ap and ag):
        return None
    return {"left":sp[0],"left_goal":sg[0],
            "top":ap[0][:2],"top_goal":ag[0][:2],
            "color":ap[0][2]}


def _wire_map(out, region, mapping):
    y0,y1,x0,x1=region
    old=out[y0:y1,x0:x1].copy()
    view=out[y0:y1,x0:x1]
    for src,dst in mapping.items():
        view[old==src]=dst


def _controller_click(a, x, y):
    frames=_dual_controller_frames(a)
    if frames is None or x is None or y is None:
        return a.copy()
    left_loc=_engine(a)
    loc=_current_top_frame(a)
    if left_loc is None or loc is None:
        return a.copy()
    lx,ly=left_loc
    tx,ty=loc
    choose_top=(tx<=x<tx+STEP and ty<=y<ty+STEP)
    choose_left=(lx<=x<lx+STEP and ly<=y<ly+STEP)
    if not (choose_top or choose_left):
        return a.copy()
    # The active frame has zero-filled chambers; the inactive frame has
    # board-colour chambers. Clicking the already active controller is inert.
    top_active=bool(np.any(a[ty+1:ty+5,tx+1:tx+5]==0))
    want_top=choose_top
    if top_active==want_top:
        return a.copy()
    out=a.copy()

    # Locate the current horizontal strand, whose wire alphabet is 1/2 while
    # active and 2/3 while parked.
    active_pair={1,2} if not top_active else {2,3}
    hend=lx+5
    colors=_target_colors()
    while hend+1<a.shape[1] and (
            int(a[ly+2,hend+1]) in active_pair|colors or
            int(a[ly+3,hend+1]) in active_pair|colors):
        hend+=1

    # Locate the current vertical strand beneath the coloured top frame.
    top_pair={1,2} if top_active else {2,3}
    vend=ty+5
    while vend+1<_separator(a) and (
            int(a[vend+1,tx+2]) in top_pair|colors or
            int(a[vend+1,tx+3]) in top_pair|colors):
        vend+=1

    lgx,lgy=frames["left_goal"]
    tgx,tgy=frames["top_goal"]
    if want_top:
        left_map={0:4}; left_wire={1:2,2:3}
        top_map={4:0}; top_wire={2:1,3:2}
    else:
        left_map={4:0}; left_wire={2:1,3:2}
        top_map={0:4}; top_wire={1:2,2:3}

    _wire_map(out,(ly+1,ly+5,lx+1,lx+5),left_map)
    _wire_map(out,(ly,ly+STEP,lx+5,hend+1),left_wire)
    _wire_map(out,(ty+1,ty+5,tx+1,tx+5),top_map)
    _wire_map(out,(ty, vend+1, tx, tx+STEP),top_wire)

    # The lower specification mirrors which of its two output engines is live.
    _wire_map(out,(lgy+1,lgy+5,lgx+1,lgx+5),left_map)
    _wire_map(out,(lgy,lgy+STEP,lgx+5,tgx),left_wire)
    _wire_map(out,(tgy+1,tgy+5,tgx+1,tgx+5),top_map)
    _wire_map(out,(tgy,tgy+STEP,tgx+5,out.shape[1]),top_wire)
    return out


def _current_top_frame(a):
    frames=_dual_controller_frames(a)
    if frames is None:
        return None
    c=frames["color"]
    sep=_separator(a)
    for y in range(max(0,sep-5)):
        for x in range(a.shape[1]-5):
            if (np.sum(a[y,x:x+6]==c)>=4 and
                    np.sum(a[y+5,x:x+6]==c)>=4 and
                    np.sum(a[y:y+6,x]==c)>=4 and
                    np.sum(a[y:y+6,x+5]==c)>=4 and
                    np.all(a[y+2:y+4,x+2:x+4]==c)):
                return x,y
    return None


def _top_controller_active(a):
    loc=_current_top_frame(a)
    if loc is None:
        return False
    x,y=loc
    return bool(np.any(a[y+1:y+5,x+1:x+5]==0))


def _top_strand_end(a,x0,y0):
    active={1,2}|_target_colors()
    y=y0+5
    while y+1<_separator(a) and (
            int(a[y+1,x0+2]) in active or
            int(a[y+1,x0+3]) in active):
        y+=1
    return y


def _put_vertical_pattern(out,x0,y0,start):
    # Counter-clockwise rotation of the horizontal 1/2 cable pattern.
    for yy in range(start,start+STEP):
        phase=(yy-(y0+5))%3
        out[yy,x0+2]=(2,1,1)[phase]
        out[yy,x0+3]=(1,2,1)[phase]


def _top_extend(a):
    loc=_current_top_frame(a)
    if loc is None:
        return a.copy()
    x0,y0=loc
    end=_top_strand_end(a,x0,y0)
    lx,ty,rx,by=_board_bounds(np.array(ENTRY_GRID,dtype=int))
    if end+STEP>by:
        return a.copy()
    nxt=end+1
    old=a[nxt:nxt+STEP,x0:x0+STEP].copy()
    # The embedded exterior-background cell is the same solid crossing that
    # blocks the horizontal crane.
    bg=int(np.array(ENTRY_GRID,dtype=int)[0,0])
    if old.shape!=(STEP,STEP) or np.any(old==bg):
        return a.copy()
    colors=_target_colors()
    caught=[c for c in colors if np.any(old==c)]
    out=a.copy()
    if caught:
        # Rotated counterpart of horizontal extension: a free target (and any
        # contiguous macro-stack below it) is pushed down while there is a
        # genuinely empty board cell beyond.  The cell it vacates becomes the
        # newly extended narrow cable.
        def has_car(start):
            tile=a[start:start+STEP,x0:x0+STEP]
            return any(np.any(tile==c) for c in colors)
        chain_end=nxt
        while chain_end+STEP<=by and has_car(chain_end+STEP):
            chain_end+=STEP
        dest0=chain_end+STEP
        dest_base=a[dest0:dest0+STEP,x0:x0+STEP]
        can_push=(dest0+STEP-1<=by and
                  dest_base.shape==(STEP,STEP) and
                  np.all(dest_base==4))
        if can_push:
            block=a[nxt:chain_end+STEP,x0:x0+STEP].copy()
            restore=old.copy()
            for c in colors:
                restore[restore==c]=4
            out[nxt:nxt+STEP,x0:x0+STEP]=restore
            _put_vertical_pattern(out,x0,y0,nxt)
            out[nxt+STEP:chain_end+2*STEP,x0:x0+STEP]=block
            return out

        # If the stack cannot move farther, the contacted car couples in place.
        _put_vertical_pattern(out,x0,y0,nxt)
        reg=out[nxt:nxt+STEP,x0:x0+STEP]
        for c in caught:
            reg[old==c]=c
        return out

    _put_vertical_pattern(out,x0,y0,nxt)
    return out


def _top_retract(a):
    loc=_current_top_frame(a)
    if loc is None:
        return a.copy()
    x0,y0=loc
    end=_top_strand_end(a,x0,y0)
    if end<y0+STEP:
        return a.copy()
    out=a.copy()
    colors=_target_colors()

    def has_car(start):
        tile=a[start:start+STEP,x0:x0+STEP]
        return any(np.any(tile==c) for c in colors)

    starts=list(range(y0+STEP,end-STEP+2,STEP))
    groups=[]
    cur=[]
    for s in starts:
        if has_car(s):
            cur.append(s)
        elif cur:
            groups.append(cur); cur=[]
    if cur:
        groups.append(cur)

    if not groups:
        out[end-STEP+1:end+1,x0:x0+STEP]=4
        return out

    # Every untethered vertical car group with a free cable cell above it
    # slides one macro-row toward the top frame; the telescope simultaneously
    # loses its farthest cell.
    moving=[]
    for group in groups:
        gs,ge=group[0],group[-1]+STEP-1
        dest=gs-STEP
        if (gs>y0+STEP and not has_car(dest) and
                not np.any(a[dest:dest+STEP,x0:x0+STEP]==3)):
            moving.append((gs,ge,a[gs:ge+1,x0:x0+STEP].copy()))

    if moving:
        for gs,ge,block in moving:
            out[gs:ge+1,x0:x0+STEP]=4
            for s in range(gs,ge+1,STEP):
                _put_vertical_pattern(out,x0,y0,s)
        for gs,ge,block in moving:
            out[gs-STEP:ge-STEP+1,x0:x0+STEP]=block
        out[end-STEP+1:end+1,x0:x0+STEP]=4
        return out

    last_end=groups[-1][-1]+STEP-1
    if end>last_end:
        out[end-STEP+1:end+1,x0:x0+STEP]=4
        return out

    # At the frame, the final single car (or the far car of a compact stack)
    # is released raw in place, exactly like horizontal tip uncoupling.
    if (len(groups)==1 and groups[0][0]==y0+STEP):
        tip=groups[0][-1]
        if len(groups[0])==1 or len(groups[0])>=2:
            tile=a[tip:tip+STEP,x0:x0+STEP].copy()
            raw=np.full((STEP,STEP),4,dtype=int)
            for c in colors:
                raw[tile==c]=c
            out[tip:tip+STEP,x0:x0+STEP]=raw
            return out
    return a.copy()


def _top_clean_base():
    # Static scenery exposed when the movable top controller leaves its entry
    # position.  The top rail repeats every macro-cell; the entry frame hides
    # one period, so recover it from the visible period immediately to its
    # right.  Its initial parked tether hides one otherwise plain board cell.
    e=np.array(ENTRY_GRID,dtype=int)
    frames=_dual_controller_frames(e)
    if frames is None:
        return e
    tx,ty=frames["top"]
    base=e.copy()
    sx=tx+STEP if tx+2*STEP<=e.shape[1] else tx-STEP
    base[ty:ty+STEP,tx:tx+STEP]=e[ty:ty+STEP,sx:sx+STEP]
    sep=_separator(e)
    yy=ty+STEP
    while yy+STEP-1<sep and (
            int(e[yy,tx+2]) in {2,3} or int(e[yy,tx+3]) in {2,3}):
        base[yy:yy+STEP,tx:tx+STEP]=4
        yy+=STEP
    return base


def _top_shift(a, delta):
    # With the coloured controller selected, LEFT/RIGHT slides its whole
    # frame and empty vertical strand by one macro-column along the top rail.
    # Car-bearing lateral motion is left dormant until it is observed.
    loc=_current_top_frame(a)
    if loc is None:
        return a.copy()
    x0,y0=loc
    nx=x0+delta
    e=np.array(ENTRY_GRID,dtype=int)
    lx,ty,rx,by=_board_bounds(e)
    if nx<lx or nx+STEP-1>rx:
        return a.copy()
    end=_top_strand_end(a,x0,y0)
    strand=a[y0+STEP:end+1,x0:x0+STEP]
    if any(np.any(strand==c) for c in _target_colors()):
        return a.copy()
    # The narrow cable may slide only through ordinary board cells.
    dest=a[y0+STEP:end+1,nx+2:nx+4]
    if dest.shape[0] != strand.shape[0] or np.any(dest!=4):
        return a.copy()
    base=_top_clean_base()
    out=a.copy()
    frame=a[y0:y0+STEP,x0:x0+STEP].copy()
    wire=a[y0+STEP:end+1,x0+2:x0+4].copy()
    out[y0:y0+STEP,x0:x0+STEP]=base[y0:y0+STEP,x0:x0+STEP]
    out[y0+STEP:end+1,x0+2:x0+4]=base[y0+STEP:end+1,x0+2:x0+4]
    out[y0:y0+STEP,nx:nx+STEP]=frame
    out[y0+STEP:end+1,nx+2:nx+4]=wire
    return out


def _dual_relocation_retract_free(a, action):
    # On the dual-crane board, after the horizontal crane has pushed a raw
    # target one macro-cell away from the blocked crossing, its final empty
    # cable contraction (two cells back to the one-cell minimum) is free.
    if action!=3 or _dual_controller_frames(a) is None or _top_controller_active(a):
        return False
    loc=_engine(a)
    if loc is None:
        return False
    x0,y0=loc
    if _strand_end(a,x0,y0)!=x0+5+2*STEP or _active_sequence(a):
        return False
    e=np.array(ENTRY_GRID,dtype=int)
    lx,ty,rx,by=_board_bounds(e)
    colors=_target_colors()
    relocated=0
    current_row=False
    for yy in range(ty,by-STEP+2,STEP):
        for s in range(lx,rx-STEP+2,STEP):
            src=e[yy:yy+STEP,s:s+STEP]
            now=a[yy:yy+STEP,s:s+STEP]
            right=a[yy:yy+STEP,s+STEP:s+2*STEP]
            shifted=(right.shape==(STEP,STEP) and
                     any(np.any(src==c) for c in colors) and
                     not any(np.any(now==c) for c in colors) and
                     any(np.any(right==c) for c in colors))
            if shifted:
                relocated+=1
                if yy==y0:
                    current_row=True
    # Only the first successful cross-axis relocation earns the one-time fuse
    # credit; later rows contract normally.
    return current_row and relocated==1


def _post_obstacle_lift_redraw(a, action):
    # After a bar below an internal one-cell hole has recursively lifted cars
    # to the far side, contracting the empty bar from three cells to two is a
    # free fuse action (the later threshold proves it is not merely a redraw delay).
    if action != 3 or _anchored_goal_mode():
        return False
    loc=_engine(a)
    if loc is None:
        return False
    x0,y0=loc
    end=_strand_end(a,x0,y0)
    if end != x0+5+3*STEP or _active_sequence(a):
        return False
    e=np.array(ENTRY_GRID,dtype=int)
    lx,ty,rx,by=_board_bounds(e)
    bg=int(e[0,0])
    # Locate a full macro-cell of exterior background embedded in the board.
    holes=[]
    for yy in range(ty,by-STEP+2,STEP):
        for xx in range(lx,rx-STEP+2,STEP):
            if np.all(e[yy:yy+STEP,xx:xx+STEP]==bg):
                holes.append((xx,yy))
    if not holes:
        return False
    # The event is the row immediately below the hole, after at least one
    # collectible has been pushed above it.
    colors=_target_colors()
    for hx,hy in holes:
        if y0==hy+STEP and any(np.any(a[ty:hy, :]==c) for c in colors):
            return True
    return False


def init_state(entry_grid):
    # The harness cannot replay the very first transition of the whole
    # run (it has no previous timeline frame). Level 0 therefore starts
    # its model rollout after one already-taken action; later levels do not.
    return {"turn": 1 if CURRENT_LEVEL == 0 else 0, "undo":[],
            "wall_pushes":0, "deferred_credit":False}

def predict(state, grid, action, x=None, y=None):
    a=np.array(grid,dtype=int)
    info={"level_up":False,"dead":False,"win":False}
    st=state or {}
    turn=int(st.get("turn",0))
    undo=list(st.get("undo",[]))
    wall_pushes=int(st.get("wall_pushes",0))
    # A deferred compact-tip redraw grants one credit to the immediately
    # following input.  Any action consumes it; if that action is simple,
    # its fuse increment is suppressed.
    deferred_credit=bool(st.get("deferred_credit",False))
    skip_deferred=deferred_credit
    deferred_credit=False
    # Undo/click and compact-tip uncoupling leave the rendered separator
    # unchanged even when hidden simple-action phase changes.
    wall_event=(action==4 and _wall_sorted_push(a))
    # The first completed-output wall arrival establishes an irreversible
    # hidden milestone. Repeating it after undo is free, though both arrivals
    # defer the timer redraw.
    free_special=(wall_event and wall_pushes>0)
    final_exit=_empty_tether_exit(a,action)
    post_lift_free=_post_obstacle_lift_redraw(a,action)
    relocation_free=_dual_relocation_retract_free(a,action)
    preserve_timer=(action in (6,7) or wall_event or post_lift_free or
                    relocation_free)
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
        # A top-crane LEFT shift must never be mistaken for uncoupling the
        # parked horizontal train merely because its inactive connectors use 3.
        if action==3 and not _top_controller_active(a):
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
                # Only a pop which leaves at least three live cars
                # defers the separator redraw.  Thus len4->len3 preserves it,
                # whereas len3->len2 is an ordinary immediately rendered move.
                compact=_compact_sequence(a)
                if compact is not None and len(compact)>=4:
                    preserve_timer=True
                    # On the first completed-output cycle the wall arrival
                    # counts, and its one deferred fuse credit is paid to the
                    # action immediately after the compact pop.  On repeats,
                    # the wall arrival itself was already the free action.
                    if wall_pushes==1:
                        deferred_credit=True
        top_active=_top_controller_active(a)
        if action==1:
            out=_top_retract(a) if top_active else _vertical(a,-STEP)
        elif action==2:
            out=_top_extend(a) if top_active else _vertical(a,STEP)
        elif action==3:
            out=_top_shift(a,-STEP) if top_active else _retract(a)
        elif action==4:
            out=_top_shift(a,STEP) if top_active else _extend(a)
        elif action==6:
            out=_controller_click(a,x,y)
        else:
            out=a.copy()
        if (action in (1,2,3,4) and not free_release and
                not free_special and not skip_deferred and not final_exit and
                not post_lift_free and not relocation_free):
            turn+=1
    _sync_ordinary_goals(out)
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
    complete=_completed(out)
    if complete:
        info["level_up"]=True
    elif n>=out.shape[1]:
        # The separator is also the move-budget fuse.  Filling its final
        # remaining 2 cell with 3 ends the attempt immediately.
        info["dead"]=True
    return out.tolist(),info,{"turn":turn,"undo":undo,
                                  "wall_pushes":wall_pushes,
                                  "deferred_credit":deferred_credit}


def is_goal(state, grid):
    return _completed(np.array(grid,dtype=int))
