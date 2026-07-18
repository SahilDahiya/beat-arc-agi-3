import numpy as np

_DIR={1:(0,-4),2:(0,4),3:(-4,0),4:(4,0)}

def init_state(entry_grid):
    return {"turn":None,"comp_active":False,"comp_post":False,"phase_power":False}

def _box(g):
    ys,xs=np.where(g==14)
    if len(xs)==0:return None
    x0,x1=int(xs.min()),int(xs.max())+1
    y0,y1=int(ys.min()),int(ys.max())+1
    if x1-x0==3:
        if x0>0 and np.all(g[y0:y1,x0-1]==0):x0-=1
        else:x1+=1
    if y1-y0==3:
        if y0>0 and np.all(g[y0-1,x0:x1]==0):y0-=1
        else:y1+=1
    return x0,y0,x0+4,y0+4

def _facing(g,b):
    if b is None:return None
    x0,y0,_,_=b
    if np.all(g[y0,x0:x0+4]==0):return 1
    if np.all(g[y0+3,x0:x0+4]==0):return 2
    if np.all(g[y0:y0+4,x0]==0):return 3
    if np.all(g[y0:y0+4,x0+3]==0):return 4
    return None

def _border(r):
    return np.concatenate((r[0,:],r[3,:],r[1:3,0],r[1:3,3]))

def _captured_at(g,x,y,rim=11):
    if x<0 or y<0 or x+4>g.shape[1] or y+4>g.shape[0]:return False
    r=g[y:y+4,x:x+4]
    return np.all(r[1:3,1:3]==15) and np.all(_border(r)==rim)

def _block_at(g,x,y,rim=None):
    if x<0 or y<0 or x+4>g.shape[1] or y+4>g.shape[0]:return False
    r=g[y:y+4,x:x+4]
    if not np.all(r[1:3,1:3]==9):return False
    b=_border(r)
    return np.all(b==rim) if rim is not None else True

def _companions(g):
    """Top-lefts of solid 4x4 workers (color12 or color15), leftmost first."""
    out=[]
    H,W=g.shape
    for y in range(H-3):
        for x in range(W-3):
            col=int(g[y,x])
            if col not in (12,15):continue
            solid=np.all(g[y:y+4,x:x+4]==col)
            # A worker may stand partly behind the bottom budget strip:
            # its fourth row is hidden by the HUD and only three rows show.
            if y==H-4:
                solid=np.all(g[y:y+3,x:x+4]==col) and np.all((g[y+3,x:x+4]==7)|(g[y+3,x:x+4]==4))
            if solid:
                if (x==0 or g[y,x-1]!=col) and (y==0 or g[y-1,x]!=col):
                    out.append((x,y))
    return sorted(out,key=lambda p:(p[0],p[1]))

def _active_companions(g):
    comps=_companions(g)
    if CURRENT_LEVEL is not None and CURRENT_LEVEL>=3 and len(comps)>1:
        live=[]
        for cx,cy in comps:
            parked=False
            for dx,dy in _DIR.values():
                qx,qy=cx+dx,cy+dy
                if _block_at(g,qx,qy,4) and _socket_dest(qx,qy):
                    parked=True
            if not parked:live.append((cx,cy))
        if live:return live
    return comps

def _sockets():
    # Every connected color9 rectangular border is a socket.  Earlier levels
    # have one; level3 introduces several disjoint 4-aligned sockets.
    ent=np.array(ENTRY_GRID,dtype=int);H,W=ent.shape
    seen=set();out=[]
    for y in range(H):
        for x in range(W):
            if ent[y,x]!=9 or (x,y) in seen:continue
            q=[(x,y)];seen.add((x,y));i=0;pts=[]
            while i<len(q):
                xx,yy=q[i];i+=1;pts.append((xx,yy))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=xx+dx,yy+dy
                    if 0<=nx<W and 0<=ny<H and ent[ny,nx]==9 and (nx,ny) not in seen:
                        seen.add((nx,ny));q.append((nx,ny))
            x0=min(p[0] for p in pts);x1=max(p[0] for p in pts)+1
            y0=min(p[1] for p in pts);y1=max(p[1] for p in pts)+1
            if x1-x0>=4 and y1-y0>=4:
                out.append((x0,y0,x1,y1))
    return out

def _socket():
    ss=_sockets()
    return max(ss,key=lambda s:(s[2]-s[0])*(s[3]-s[1])) if ss else None

def _socket_dest(x,y):
    return any(L<=x and x+4<=R and T<=y and y+4<=B for L,T,R,B in _sockets())

def _phase15_sockets():
    """Large connected color2 pads are destinations for color15 workers."""
    ent=np.array(ENTRY_GRID,dtype=int);H,W=ent.shape
    seen=set();out=[]
    for y in range(H):
        for x in range(W):
            if ent[y,x]!=2 or (x,y) in seen:continue
            q=[(x,y)];seen.add((x,y));pts=[]
            for xx,yy in q:
                pts.append((xx,yy))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=xx+dx,yy+dy
                    if 0<=nx<W and 0<=ny<H and ent[ny,nx]==2 and (nx,ny) not in seen:
                        seen.add((nx,ny));q.append((nx,ny))
            L=min(p[0] for p in pts);R=max(p[0] for p in pts)+1
            T=min(p[1] for p in pts);B=max(p[1] for p in pts)+1
            # Phase pads are at least two 4x4 slots, arranged in either axis.
            if (R-L>=8 and B-T>=4) or (R-L>=4 and B-T>=8):out.append((L,T,R,B))
    return out

def _phase15_dest(x,y):
    return any(L<=x and x+4<=R and T<=y and y+4<=B for L,T,R,B in _phase15_sockets())

def _cargo_dest(wcol,x,y):
    return _phase15_dest(x,y) if wcol==15 else _socket_dest(x,y)

def _transfer_dest(g,x,y):
    # A patterned 1/2 tile is a transfer-wall slot: a held block can occupy it.
    ent=np.array(ENTRY_GRID,dtype=int)
    if x<0 or y<0 or x+4>g.shape[1] or y+4>g.shape[0]:return False
    tile=ent[y:y+4,x:x+4]
    return np.any(tile==2) and np.all((tile==1)|(tile==2)) and np.array_equal(g[y:y+4,x:x+4],tile)

def _restore_under_block(h,x,y):
    h[y:y+4,x:x+4]=1
    ent=np.array(ENTRY_GRID,dtype=int)
    tile=ent[y:y+4,x:x+4]
    # Transfer-wall slots restore their entry pattern. An entry block can hide
    # such a tile, whose repeating pattern is inferred from its neighbour.
    if np.any(tile==2) and np.all((tile==1)|(tile==2)):
        h[y:y+4,x:x+4]=tile
    elif _block_at(ent,x,y,4):
        if y>=4:h[y:y+4,x:x+4]=ent[y-4:y,x:x+4]
        elif y+8<=ent.shape[0]:h[y:y+4,x:x+4]=ent[y+4:y+8,x:x+4]
    ent=np.array(ENTRY_GRID,dtype=int)
    for L,T,R,B in _sockets():
        xa,xb=max(x,L),min(x+4,R)
        ya,yb=max(y,T),min(y+4,B)
        if xa<xb and ya<yb:
            h[ya:yb,xa:xb]=ent[ya:yb,xa:xb]

def _restore_worker(h,x,y,wcol):
    """Restore terrain hidden by a worker, including color15 phase pads."""
    if wcol!=15:
        h[y:y+4,x:x+4]=1
        if _socket_dest(x,y):_restore_under_block(h,x,y)
        return
    h[y:y+4,x:x+4]=1
    # Color15 can stand on its solid color2 destination pad.
    for L,T,R,B in _phase15_sockets():
        xa,xb=max(x,L),min(x+4,R);ya,yb=max(y,T),min(y+4,B)
        if xa<xb and ya<yb:h[ya:yb,xa:xb]=2
    # Reconstruct the color9 border/color2 interior of a source socket even
    # when its entry appearance was hidden by an initial block.
    for L,T,R,B in _sockets():
        for yy in range(max(y,T),min(y+4,B)):
            for xx in range(max(x,L),min(x+4,R)):
                h[yy,xx]=9 if xx in (L,R-1) or yy in (T,B-1) else 2

def _restore_main(h,x,y,phase=False):
    """Restore terrain hidden by the main, including phase-compatible color2."""
    h[y:y+4,x:x+4]=1
    if phase:
        ent=np.array(ENTRY_GRID,dtype=int)
        tile=ent[y:y+4,x:x+4]
        if np.all((tile==1)|(tile==2)):
            h[y:y+4,x:x+4]=tile

def _draw_player(g,x,y,face):
    g[y:y+4,x:x+4]=14
    if face==1:g[y,x:x+4]=0
    elif face==2:g[y+3,x:x+4]=0
    elif face==3:g[y:y+4,x]=0
    elif face==4:g[y:y+4,x+3]=0

def _highlight(g,b,face):
    blocks=[]
    H,W=g.shape
    for y in range(H-3):
        for x in range(W-3):
            if _block_at(g,x,y) and np.all((_border(g[y:y+4,x:x+4])==3)|(_border(g[y:y+4,x:x+4])==4)):
                blocks.append((x,y))
    for x,y in blocks:
        g[y,x:x+4]=4;g[y+3,x:x+4]=4
        g[y+1:y+3,x]=4;g[y+1:y+3,x+3]=4
    if b is None or face not in _DIR:return
    x,y,_,_=b;dx,dy=_DIR[face];q=(x+dx,y+dy)
    if q in blocks:
        x,y=q
        g[y,x:x+4]=3;g[y+3,x:x+4]=3
        g[y+1:y+3,x]=3;g[y+1:y+3,x+3]=3
    else:
        # A solid color15 exporter can be captured by direct main collision:
        # its outer cells become rim11 while its 2x2 core remains color15.
        x,y=q
        if 0<=x and 0<=y and x+4<=g.shape[1] and y+4<=g.shape[0] and np.all(g[y:y+4,x:x+4]==15) and not _worker_mobile(g,x,y):
            g[y,x:x+4]=11;g[y+3,x:x+4]=11
            g[y+1:y+3,x]=11;g[y+1:y+3,x+3]=11

def _companion_action5(g,worker=None):
    comps=_companions(g)
    if not comps:return False
    # A caller may nominate one worker so multiple selected pairs can each
    # advance exactly once on the same tick.
    picked=None
    if worker is not None:
        tx,ty=worker
        if any(_block_at(g,tx+dx,ty+dy,5) for dx,dy in _DIR.values()):picked=(tx,ty)
    else:
        for tx,ty in comps:
            if any(_block_at(g,tx+dx,ty+dy,5) for dx,dy in _DIR.values()):
                picked=(tx,ty);break
    if picked is None:return False
    cx,cy=picked
    wcol=int(g[cy,cx])
    # Once the selected block itself reaches its worker-specific destination,
    # the next tick parks.
    # the companion may still be standing just outside the socket edge.
    for dx,dy in _DIR.values():
        qx,qy=cx+dx,cy+dy
        if _block_at(g,qx,qy,5) and _cargo_dest(wcol,qx,qy):return False
    # A rim5 block adjacent to the companion is its selected rigid partner.
    for face,(dx,dy) in _DIR.items():
        qx,qy=cx+dx,cy+dy
        if not _block_at(g,qx,qy,5):continue
        # The selected rigid pair shortest-paths to a free socket placement.
        # This is westward for the first two observed blocks; lower/upper
        # blocks can turn vertically once aligned with an open socket slot.
        offx,offy=qx-cx,qy-cy
        h=g.copy();_restore_worker(h,cx,cy,wcol)
        _restore_under_block(h,qx,qy)
        ent=np.array(ENTRY_GRID,dtype=int)
        H,W=g.shape;L,T,R,B=_socket()
        outside2=(ent==2)
        for sL,sT,sR,sB in _sockets(): outside2[sT:sB,sL:sR]=False
        if CURRENT_LEVEL is not None and CURRENT_LEVEL>=3 or not np.any(outside2):
            # Ordinary boards and distributed-socket boards use a collision-
            # aware shortest path for the whole rigid pair.
            def ok(xx,yy,cargo=False):
                if xx<0 or yy<0 or xx+4>W or yy+4>H:return False
                tile=h[yy:yy+4,xx:xx+4]
                if np.all(tile==1):return True
                # Color15 workers are phase-compatible with color2 floor and
                # may cross those pads while carrying cargo.
                if wcol==15 and np.all((tile==1)|(tile==2)):return True
                if cargo and _transfer_dest(h,xx,yy):return True
                if yy==H-4 and np.all(tile[:3,:]==1) and np.all((tile[3,:]==7)|(tile[3,:]==4)):return True
                return _socket_dest(xx,yy) and np.array_equal(tile,ent[yy:yy+4,xx:xx+4])
            queue=[(cx,cy,None)];seen={(cx,cy)};i=0;chosen0=None;fallback0=None
            while i<len(queue):
                xx,yy,first=queue[i];i+=1
                bx,by=xx+offx,yy+offy
                if CURRENT_LEVEL is not None and CURRENT_LEVEL>=3:
                    # Color15 exports cargo to a large color2 phase pad.
                    if wcol==15:
                        if _phase15_dest(bx,by):
                            chosen0=first;break
                    else:
                        # Prefer a reachable placement of the cargo block.
                        if _socket_dest(bx,by):
                            chosen0=first;break
                        if _socket_dest(xx,yy) and fallback0 is None:
                            fallback0=first
                elif _socket_dest(xx,yy) and _socket_dest(bx,by):
                    chosen0=first;break
                for a in (3,4,1,2):
                    mx,my=_DIR[a];nx,ny=xx+mx,yy+my
                    if (nx,ny) in seen:continue
                    if ok(nx,ny) and ok(nx+offx,ny+offy,True):
                        seen.add((nx,ny));queue.append((nx,ny,a if first is None else first))
            if chosen0 is None:chosen0=fallback0
            if chosen0 is not None:
                mx,my=_DIR[chosen0];ncx,ncy=cx+mx,cy+my;nqx,nqy=qx+mx,qy+my
                pat=g[qy:qy+4,qx:qx+4].copy()
                g[:,:]=h;g[nqy:nqy+4,nqx:nqx+4]=pat;g[ncy:ncy+4,ncx:ncx+4]=wcol
            return True
        # Transfer-wall boards first align horizontally with the nearest free
        # socket row. If the vertical entrance is occupied, the pair detours
        # one column around the socket edge, descends, then returns horizontally.
        def empty(xx,yy):
            if xx<0 or yy<0 or xx+4>W or yy+4>H-1:return False
            if np.all(h[yy:yy+4,xx:xx+4]==1):return True
            return _socket_dest(xx,yy) and np.array_equal(h[yy:yy+4,xx:xx+4],ent[yy:yy+4,xx:xx+4])
        goals=[]
        for yy in range(T,B-3,4):
            for xx in range(L,R-3,4):
                bx,by=xx+offx,yy+offy
                if _socket_dest(bx,by) and empty(xx,yy) and empty(bx,by):
                    goals.append((abs(xx-cx)+abs(yy-cy),yy,xx))
        chosen=None
        if goals:
            _,tcy,tcx=min(goals)
            # A completely filled socket row is a solid barrier to the rigid
            # pair.  Align just outside the socket, cross the row vertically,
            # and only then move horizontally into the chosen open row.
            full_barrier=False
            for sy in range(T,B-3,4):
                between=(cy<=sy<tcy) if cy<tcy else (tcy<sy<=cy)
                if between:
                    if not empty(L,sy) and not empty(L+4,sy):
                        full_barrier=True
            if full_barrier and cy!=tcy:
                detx=L-4 if offx<0 else R
                if cx<detx: chosen=4
                elif cx>detx: chosen=3
                else: chosen=2 if cy<tcy else 1
            elif cy==tcy:
                chosen=4 if cx<tcx else (3 if cx>tcx else None)
            elif cx<tcx:
                chosen=4
            elif cx>tcx:
                chosen=2 if cy<tcy else 1
            else:
                chosen=2 if cy<tcy else 1
                mx,my=_DIR[chosen]
                if not (empty(cx+mx,cy+my) and empty(qx+mx,qy+my)):
                    chosen=4 if offx<0 else 3
        if chosen is not None:
            mx,my=_DIR[chosen];ncx,ncy=cx+mx,cy+my;nqx,nqy=qx+mx,qy+my
            if empty(ncx,ncy) and empty(nqx,nqy):
                pat=g[qy:qy+4,qx:qx+4].copy()
                g[:,:]=h;g[nqy:nqy+4,nqx:nqx+4]=pat
                g[ncy:ncy+4,ncx:ncx+4]=wcol
        return True
    return False

def _companion_dir(g,x0,y0):
    """Shortest-path one tick toward the nearest rim4 block."""
    H,W=g.shape
    wcol=int(g[y0,x0])
    targets=[]
    for yy in range(H-3):
        for xx in range(W-3):
            if (_block_at(g,xx,yy,4) or _block_at(g,xx,yy,3)) and (not _phase15_dest(xx,yy) if wcol==15 else not _socket_dest(xx,yy)):targets.append((xx,yy))
    if not targets:return None
    goals={}
    for bx,by in targets:
        for a,(dx,dy) in _DIR.items():
            # position from which moving action a enters the target
            goals[(bx-dx,by-dy)]=a
    h=g.copy();h[y0:y0+4,x0:x0+4]=1
    if _socket_dest(x0,y0):_restore_under_block(h,x0,y0)
    q=[(x0,y0,None)];seen={(x0,y0)};i=0
    ent0=np.array(ENTRY_GRID,dtype=int)
    outside2=(ent0==2)
    for sL,sT,sR,sB in _sockets(): outside2[sT:sB,sL:sR]=False
    order=((3,4,1,2) if CURRENT_LEVEL is not None and CURRENT_LEVEL>=3
           else ((4,3,1,2) if np.any(outside2) else (4,3,2,1)))
    while i<len(q):
        xx,yy,first=q[i];i+=1
        if (xx,yy) in goals:return goals[(xx,yy)] if first is None else first
        for a in order:
            dx,dy=_DIR[a];nx,ny=xx+dx,yy+dy
            if (nx,ny) in seen or nx<0 or ny<0 or nx+4>W or ny+4>H:continue
            tile=h[ny:ny+4,nx:nx+4]
            clear=np.all(tile==1)
            if wcol==15 and np.all((tile==1)|(tile==2)):clear=True
            if ny==H-4 and np.all(tile[:3,:]==1) and np.all((tile[3,:]==7)|(tile[3,:]==4)):clear=True
            if not clear and _socket_dest(nx,ny):
                ent=np.array(ENTRY_GRID,dtype=int)
                clear=np.array_equal(h[ny:ny+4,nx:nx+4],ent[ny:ny+4,nx:nx+4])
            if clear:
                seen.add((nx,ny));q.append((nx,ny,a if first is None else first))
    return None

def _worker_mobile(g,x,y):
    """Whether a solid exporter has an autonomous move/selection this tick."""
    # A selected rigid pair is mobile only if its transport actually changes
    # the frame; an orientation blocked by a filled phase pad is capturable.
    if any(_block_at(g,x+dx,y+dy,5) for dx,dy in _DIR.values()):
        h=g.copy()
        _companion_action5(h,(x,y))
        return not np.array_equal(h,g)
    return _companion_dir(g,x,y) is not None

def _move_companion(g,action,turn,post=False):
    # All unladen color12 workers with reachable cargo advance concurrently.
    if action not in _DIR:return False
    comps=_companions(g)
    if not comps:return False
    parked=False;just_parked=set()
    external_skip=set(post) if isinstance(post,set) else set()
    suppress_park=isinstance(post,set) or bool(post)
    # A pair transported earlier in this same tick must not park until the next
    # tick; otherwise scan every worker for cargo that has reached a socket.
    if not suppress_park:
        for x0,y0 in comps:
            for dx,dy in _DIR.values():
                qx,qy=x0+dx,y0+dy
                if _block_at(g,qx,qy,5) and _cargo_dest(int(g[y0,x0]),qx,qy):
                    g[qy,qx:qx+4]=4;g[qy+3,qx:qx+4]=4
                    g[qy+1:qy+3,qx]=4;g[qy+1:qy+3,qx+3]=4
                    parked=True;just_parked.add((x0,y0))
    for x0,y0 in comps:
        if (x0,y0) in just_parked or (x0,y0) in external_skip:continue
        # A worker currently owning rim5 cargo is handled by the rigid-pair
        # mechanism and must not also take an unladen step.
        if any(_block_at(g,x0+dx,y0+dy,5) for dx,dy in _DIR.values()):continue
        auto=_companion_dir(g,x0,y0)
        if auto is None:continue
        dx,dy=_DIR[auto];nx,ny=x0+dx,y0+dy
        wcol=int(g[y0,x0])
        h=g.copy();_restore_worker(h,x0,y0,wcol)
        clear=False
        if 0<=nx and 0<=ny and nx+4<=g.shape[1] and ny+4<=g.shape[0]:
            tile=h[ny:ny+4,nx:nx+4]
            clear=np.all(tile==1)
            if wcol==15 and np.all((tile==1)|(tile==2)):clear=True
            if ny==g.shape[0]-4 and np.all(tile[:3,:]==1) and np.all((tile[3,:]==7)|(tile[3,:]==4)):clear=True
            if not clear and _socket_dest(nx,ny):
                ent=np.array(ENTRY_GRID,dtype=int)
                clear=np.array_equal(tile,ent[ny:ny+4,nx:nx+4])
        # A rim4 entry block may exactly match the socket underlay; it is
        # still cargo and collision/selection takes precedence over walking.
        if _block_at(g,nx,ny,4):
            g[ny,nx:nx+4]=5;g[ny+3,nx:nx+4]=5
            g[ny+1:ny+3,nx]=5;g[ny+1:ny+3,nx+3]=5
        elif clear:
            g[:,:]=h;g[ny:ny+4,nx:nx+4]=wcol
    return parked

def _complete(g):
    ss=_sockets()
    if not ss:return False
    filled_pos=set()
    for L,T,R,B in ss:
        for yy in range(T,B-3):
            for xx in range(L,R-3):
                if _block_at(g,xx,yy):filled_pos.add((xx,yy))
    filled=len(filled_pos)
    ent=np.array(ENTRY_GRID,dtype=int);required=0
    for yy in range(ent.shape[0]-3):
        for xx in range(ent.shape[1]-3):
            if _block_at(ent,xx,yy,4):required+=1
    return required>0 and filled>=required

def _budget(g,turn):
    g[-1,:]=7
    # Level 1 has a 70-action budget rendered onto 64 cells (nearest pixel):
    # n=round(64*turn/70), giving skips at turns 6,18,30,41,53,65.
    n=((32*turn+17)//35) if CURRENT_LEVEL==1 else ((128*turn+75)//150 if CURRENT_LEVEL==5 else (((128*turn+125)//250) if CURRENT_LEVEL in (4,6) else (((16*turn+12)//25) if CURRENT_LEVEL is not None and CURRENT_LEVEL>=2 else ((turn+1)//3 if turn<=11 else (4+max(0,(turn-12)//3) if turn<=38 else 4+max(0,(turn-13)//3))))))
    if n:g[-1,max(0,g.shape[1]-n):]=4

def predict(state,grid,action,x=None,y=None):
    g=np.array(grid,dtype=int)
    raw=state.get("turn",None)
    if raw is None:
        base=np.array(ENTRY_GRID,dtype=int)
        n=int(np.sum(g[-1,:]==4))
        if n:raw=(n if CURRENT_LEVEL==1 else (3*n+1 if n<=4 else 12+3*(n-4)))
        elif not np.array_equal(g,base):raw=1
        else:raw=0
    # Reconcile the clock from the rendered strip after a model reinstall.
    if CURRENT_LEVEL==1:
        raw=max(int(raw),int(np.sum(g[-1,:]==4)))
    active=state.get("comp_active",None)
    if active is None:
        ys,xs=np.where((g==12)|(g==15))
        active=bool(len(xs) and int(xs.min())<36)
    post=state.get("comp_post",None)
    if post is None:
        ys,xs=np.where((g==12)|(g==15))
        post=bool(len(xs) and int(xs.min())<24 and not any(_block_at(g,int(xs.min())+dx,int(ys.min())+dy,5) for dx,dy in _DIR.values()))
    phase=bool(state.get("phase_power",False))
    st={"turn":int(raw),"comp_active":bool(active),"comp_post":bool(post),"phase_power":phase}
    info={"level_up":False,"dead":False,"win":False}
    # Preserve which queues were explicitly released by the main at tick start.
    # Workers can immediately take and transport rim3 cargo, whereas first
    # contact with an ordinary rim4 block consumes the tick selecting it.
    pre_rim3=set()
    for yy in range(g.shape[0]-3):
        for xx in range(g.shape[1]-3):
            if _block_at(g,xx,yy,3):pre_rim3.add((xx,yy))

    if action in _DIR:
        b=_box(g);moved=False
        if b is not None:
            px,py,_,_=b
            face=_facing(g,b)
            dx,dy=_DIR[action]
            # A grabbed rim0 block and player translate as a rigid pair.
            if face in _DIR:
                fx,fy=_DIR[face];qx,qy=px+fx,py+fy
            else:
                qx=qy=-99
            held=_block_at(g,qx,qy,0)
            if held:
                pat=g[qy:qy+4,qx:qx+4].copy()
                npx,npy=px+dx,py+dy
                nqx,nqy=qx+dx,qy+dy
                h=g.copy();_restore_main(h,px,py,st["phase_power"])
                _restore_under_block(h,qx,qy)
                pok=False
                if 0<=npx and 0<=npy and npx+4<=g.shape[1] and npy+4<=g.shape[0]:
                    pok=np.all(h[npy:npy+4,npx:npx+4]==1)
                    # On distributed transfer chambers the main can follow a
                    # held block into the patterned tile it just vacated.
                    if not pok and CURRENT_LEVEL is not None and CURRENT_LEVEL>=3:
                        pt=h[npy:npy+4,npx:npx+4]
                        pok=np.any(pt==2) and np.all((pt==1)|(pt==2))
                bok=False
                if 0<=nqx and 0<=nqy and nqx+4<=g.shape[1] and nqy+4<=g.shape[0]:
                    if np.all(h[nqy:nqy+4,nqx:nqx+4]==1):
                        bok=True
                    elif _transfer_dest(h,nqx,nqy):
                        bok=True
                    elif _socket_dest(nqx,nqy):
                        ent=np.array(ENTRY_GRID,dtype=int)
                        tile=h[nqy:nqy+4,nqx:nqx+4]
                        bok=np.array_equal(tile,ent[nqy:nqy+4,nqx:nqx+4])
                        # An entry cargo can hide a socket slot. After it is
                        # removed, the reconstructed color9/2 underlay is open.
                        if CURRENT_LEVEL==5 and np.all((tile==9)|(tile==2)):bok=True
                if pok and bok:
                    g=h;g[nqy:nqy+4,nqx:nqx+4]=pat
                    _draw_player(g,npx,npy,face)
                    moved=True
            else:
                nx,ny=px+dx,py+dy
                h=g.copy();_restore_main(h,px,py,st["phase_power"])
                clear=False
                if 0<=nx and 0<=ny and nx+4<=g.shape[1] and ny+4<=g.shape[0]:
                    tile=h[ny:ny+4,nx:nx+4]
                    clear=np.all(tile==1) or (st["phase_power"] and np.all((tile==1)|(tile==2)))
                if clear:
                    g=h;_draw_player(g,nx,ny,action);moved=True
                    _highlight(g,_box(g),action)
                else:
                    # A blocked arrow still turns the main player and selects
                    # an adjacent block in the attempted direction.
                    _draw_player(g,px,py,action)
                    _highlight(g,_box(g),action)
    elif action==5:
        b=_box(g);face=_facing(g,b)
        if b is not None and face in _DIR:
            px,py,_,_=b;dx,dy=_DIR[face];qx,qy=px+dx,py+dy
            if _captured_at(g,qx,qy):
                # Absorbing a captured exporter permanently grants the main
                # its color2-floor phase ability and releases any cargo the
                # exporter still owned (rim5 returns to ordinary rim4).
                for wx,wy in _DIR.values():
                    bx,by=qx+wx,qy+wy
                    if _block_at(g,bx,by,5):
                        g[by,bx:bx+4]=4;g[by+3,bx:bx+4]=4
                        g[by+1:by+3,bx]=4;g[by+1:by+3,bx+3]=4
                _restore_worker(g,qx,qy,15)
                st["phase_power"]=True
            elif _block_at(g,qx,qy):
                r=g[qy:qy+4,qx:qx+4];bd=_border(r)
                val=0 if np.all(bd==3) else (3 if np.all(bd==0) else None)
                if val is not None:
                    g[qy,qx:qx+4]=val;g[qy+3,qx:qx+4]=val
                    g[qy+1:qy+3,qx]=val;g[qy+1:qy+3,qx+3]=val
                    if val==3 and _complete(g):
                        if CURRENT_LEVEL is not None and CURRENT_LEVEL>=8:info["win"]=True
                        else:info["level_up"]=True
    # Every worker advances once per simple tick.  On distributed-socket
    # boards several workers may be active concurrently: snapshot their
    # start-of-tick roles, park old arrivals, transport every selected pair,
    # then advance every worker which started unladen.
    comp_used=False;parked_any=False
    multi=CURRENT_LEVEL is not None and CURRENT_LEVEL>=3
    if action in (1,2,3,4,5):
        ca=action if action in _DIR else 4
        if multi:
            selected=[];parked_workers=set()
            for cx,cy in _companions(g):
                for dx,dy in _DIR.values():
                    qx,qy=cx+dx,cy+dy
                    if _block_at(g,qx,qy,5):
                        selected.append((cx,cy,qx,qy));break
            old_cargo={(qx,qy) for cx,cy,qx,qy in selected}
            # Cargo already in a socket at tick start parks now.
            for cx,cy,qx,qy in selected:
                if _cargo_dest(int(g[cy,cx]),qx,qy):
                    g[qy,qx:qx+4]=4;g[qy+3,qx:qx+4]=4
                    g[qy+1:qy+3,qx]=4;g[qy+1:qy+3,qx+3]=4
                    parked_workers.add((cx,cy));parked_any=True
            # Unladen workers move first and may acquire new cargo.  A fresh
            # collision consumes the shared transport phase for this tick.
            _move_companion(g,ca,st["turn"],parked_workers)
            new_positions=set()
            for yy in range(g.shape[0]-3):
                for xx in range(g.shape[1]-3):
                    if _block_at(g,xx,yy,5) and (xx,yy) not in old_cargo:
                        new_positions.add((xx,yy))
            new_collision=bool(new_positions)
            fast_new=new_collision and all(p in pre_rim3 for p in new_positions)
            # A fresh collision with ordinary rim4 cargo consumes the shared
            # transport phase. Explicit rim3 queues are taken immediately;
            # otherwise every pair already selected at tick start moves once.
            if not new_collision or fast_new:
                movers=[]
                for cx,cy in _companions(g):
                    for dx,dy in _DIR.values():
                        qx,qy=cx+dx,cy+dy
                        if _block_at(g,qx,qy,5):
                            movers.append((cx,cy));break
                for worker in movers:
                    if worker not in parked_workers:
                        if _companion_action5(g,worker):comp_used=True
        else:
            comp_used=_companion_action5(g)
            if not comp_used:
                parked_any=_move_companion(g,ca,st["turn"],False)
        if parked_any:
            st["comp_post"]=True
            st["comp_active"]=False
            if _complete(g):
                if CURRENT_LEVEL is not None and CURRENT_LEVEL>=8:info["win"]=True
                else:info["level_up"]=True
        if action==5 and comp_used:st["comp_active"]=True
        st["turn"]+=1
        _budget(g,st["turn"])
        # The level-4 125-action meter is lethal as soon as it fills, unless
        # the same tick has already completed the level.
        if CURRENT_LEVEL==4 and st["turn"]>=125 and not info["level_up"]:
            info["dead"]=True
    return g.tolist(),info,st
