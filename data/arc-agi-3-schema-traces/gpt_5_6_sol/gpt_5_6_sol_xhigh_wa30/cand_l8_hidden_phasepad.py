import numpy as np

_DIR={1:(0,-4),2:(0,4),3:(-4,0),4:(4,0)}

def init_state(entry_grid):
    return {"turn":None,"comp_active":False,"comp_post":False,"phase_power":False,"lane_started":0,"export_wait":set(),"export_follow":set(),"export_pin":set()}

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
    # Direct scalar tests are much faster than constructing/reducing tiny numpy
    # slices; this predicate is called millions of times during route searches.
    if not (g[y+1,x+1]==9 and g[y+1,x+2]==9 and
            g[y+2,x+1]==9 and g[y+2,x+2]==9):return False
    if rim is None:return True
    return (g[y,x]==rim and g[y,x+1]==rim and g[y,x+2]==rim and g[y,x+3]==rim and
            g[y+3,x]==rim and g[y+3,x+1]==rim and g[y+3,x+2]==rim and g[y+3,x+3]==rim and
            g[y+1,x]==rim and g[y+2,x]==rim and g[y+1,x+3]==rim and g[y+2,x+3]==rim)

def _companions(g):
    """Top-lefts of solid 4x4 workers (color12 or color15), leftmost first."""
    out=[];H,W=g.shape
    ys,xs=np.where((g==12)|(g==15))
    for y,x in zip(ys,xs):
        y=int(y);x=int(x);col=int(g[y,x])
        if x>W-4 or y>H-4:continue
        if (x>0 and g[y,x-1]==col) or (y>0 and g[y-1,x]==col):continue
        solid=np.all(g[y:y+4,x:x+4]==col)
        # A worker may stand partly behind the bottom budget strip.
        if y==H-4:
            solid=np.all(g[y:y+3,x:x+4]==col) and np.all((g[y+3,x:x+4]==7)|(g[y+3,x:x+4]==4))
        if solid:out.append((x,y))
    return sorted(out,key=lambda p:(p[0],p[1]))

def _tick_companions(g,started=None):
    """Level7 lanes become permanently autonomous once the main visits them."""
    comps=_companions(g)
    if CURRENT_LEVEL==7:
        b=_box(g)
        if b is not None:
            current=1 if b[1]<32 else 2
            mask=current if started is None else (int(started)|current)
            comps=[p for p in comps if mask & (1 if p[1]<32 else 2)]
    return comps

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

def _sockets(_cache={}):
    # Layout is immutable within a level.  A function-default cache avoids tens
    # of thousands of repeated component scans during full-history verification.
    key=CURRENT_LEVEL
    if key in _cache:return _cache[key]
    # Every connected color9 rectangular border is a socket.  Iterate only the
    # sparse color9 cells (rather than all 4096 screen cells).
    ent=np.array(ENTRY_GRID,dtype=int)
    ys,xs=np.where(ent==9)
    rem={(int(x),int(y)) for y,x in zip(ys,xs)}
    out=[]
    while rem:
        seed=rem.pop();q=[seed];pts=[];i=0
        while i<len(q):
            xx,yy=q[i];i+=1;pts.append((xx,yy))
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=(xx+dx,yy+dy)
                if p in rem:rem.remove(p);q.append(p)
        x0=min(p[0] for p in pts);x1=max(p[0] for p in pts)+1
        y0=min(p[1] for p in pts);y1=max(p[1] for p in pts)+1
        if x1-x0>=4 and y1-y0>=4:out.append((x0,y0,x1,y1))
    _cache[key]=tuple(out)
    return _cache[key]

def _socket():
    ss=_sockets()
    return max(ss,key=lambda s:(s[2]-s[0])*(s[3]-s[1])) if ss else None

def _socket_dest(x,y):
    return any(L<=x and x+4<=R and T<=y and y+4<=B for L,T,R,B in _sockets())

def _phase15_sockets(_cache={}):
    """Large connected color2 pads are destinations for color15 workers."""
    key=CURRENT_LEVEL
    if key in _cache:return _cache[key]
    ent=np.array(ENTRY_GRID,dtype=int)
    ys,xs=np.where(ent==2)
    rem={(int(x),int(y)) for y,x in zip(ys,xs)}
    out=[];socks=_sockets()
    while rem:
        seed=rem.pop();q=[seed];pts=[];i=0
        while i<len(q):
            xx,yy=q[i];i+=1;pts.append((xx,yy))
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=(xx+dx,yy+dy)
                if p in rem:rem.remove(p);q.append(p)
        L=min(p[0] for p in pts);R=max(p[0] for p in pts)+1
        T=min(p[1] for p in pts);B=max(p[1] for p in pts)+1
        # Socket interiors can themselves be large color2 components; they are
        # delivery goals, not exporter phase pads.
        in_socket=any(sL<=L and R<=sR and sT<=T and B<=sB for sL,sT,sR,sB in socks)
        if not in_socket and ((R-L>=8 and B-T>=4) or (R-L>=4 and B-T>=8)):
            out.append((L,T,R,B))
    # A phase pad may be mostly concealed by entry cargo.  At 4x4 object
    # granularity, grow uniform color2 tiles through cardinally adjacent rim4
    # entry blocks; accept only a completely tiled rectangle, so unrelated
    # source blocks beside a phase tile cannot create a spurious destination.
    phase_tiles=set();covered=set()
    H,W=ent.shape
    for ty in range(0,H-3,4):
        for tx in range(0,W-3,4):
            if _socket_dest(tx,ty):continue
            if np.all(ent[ty:ty+4,tx:tx+4]==2):
                phase_tiles.add((tx,ty));covered.add((tx,ty))
            elif _block_at(ent,tx,ty,4):
                covered.add((tx,ty))
    rem_tiles=set(covered)
    while rem_tiles:
        seed=rem_tiles.pop();q=[seed];comp=[];i=0
        while i<len(q):
            xx,yy=q[i];i+=1;comp.append((xx,yy))
            for dx,dy in ((4,0),(-4,0),(0,4),(0,-4)):
                p=(xx+dx,yy+dy)
                if p in rem_tiles:rem_tiles.remove(p);q.append(p)
        if not any(p in phase_tiles for p in comp):continue
        L=min(p[0] for p in comp);R=max(p[0] for p in comp)+4
        T=min(p[1] for p in comp);B=max(p[1] for p in comp)+4
        rectangular=(len(comp)*16==(R-L)*(B-T))
        large=((R-L>=8 and B-T>=4) or (R-L>=4 and B-T>=8))
        if rectangular and large and (L,T,R,B) not in out:
            out.append((L,T,R,B))
    _cache[key]=tuple(out)
    return _cache[key]

def _phase15_dest(x,y):
    ent=np.array(ENTRY_GRID,dtype=int)
    if x<0 or y<0 or x+4>ent.shape[1] or y+4>ent.shape[0]:return False
    inside=any(L<=x and x+4<=R and T<=y and y+4<=B for L,T,R,B in _phase15_sockets())
    # Cargo can hide a phase-pad slot in the entry frame.  Such a block is
    # already parked phase cargo, not fresh source cargo for an exporter.
    return inside and (np.all(ent[y:y+4,x:x+4]==2) or _block_at(ent,x,y,4))

def _cargo_dest(wcol,x,y):
    return _phase15_dest(x,y) if wcol==15 else _socket_dest(x,y)

def _transfer_dest(g,x,y):
    # A patterned 1/2 tile is a transfer-wall slot: a held block can occupy it.
    # It may either be visible in ENTRY_GRID or become visible only after an
    # entry block leaves and reveals the phase terrain it concealed.
    ent=np.array(ENTRY_GRID,dtype=int)
    if x<0 or y<0 or x+4>g.shape[1] or y+4>g.shape[0]:return False
    cur=g[y:y+4,x:x+4]
    tile=ent[y:y+4,x:x+4]
    visible=(np.any(tile==2) and np.all((tile==1)|(tile==2))
             and np.array_equal(cur,tile))
    revealed=(np.any(cur==2) and np.all((cur==1)|(cur==2)))
    return visible or revealed

def _restore_under_block(h,x,y):
    h[y:y+4,x:x+4]=1
    # A block can hide one whole slot of an exporter phase pad in the entry
    # frame. Removing that parked block reveals uniform color2 floor.
    phase_slot=_phase15_dest(x,y)
    if phase_slot:h[y:y+4,x:x+4]=2
    ent=np.array(ENTRY_GRID,dtype=int)
    tile=ent[y:y+4,x:x+4]
    # Transfer-wall slots restore their entry pattern. An entry block can hide
    # such a tile, whose repeating pattern is inferred from its neighbour.
    if np.any(tile==2) and np.all((tile==1)|(tile==2)):
        h[y:y+4,x:x+4]=tile
    elif _block_at(ent,x,y,4) and not phase_slot:
        # An entry block can hide patterned 1/2 terrain. Infer it only from a
        # clean neighbouring terrain tile, never from another object/worker.
        candidates=[]
        # Prefer terrain already revealed during play as well as terrain visible
        # in the entry frame.  Adjacent entry blocks can conceal an entire run
        # of phase tiles, so only consulting ENTRY_GRID misses the interior of
        # that run after an earlier block has exposed its neighbour.
        if y>=4:candidates.extend((h[y-4:y,x:x+4],ent[y-4:y,x:x+4]))
        if y+8<=ent.shape[0]:candidates.extend((h[y+4:y+8,x:x+4],ent[y+4:y+8,x:x+4]))
        if x>=4:candidates.extend((h[y:y+4,x-4:x],ent[y:y+4,x-4:x]))
        if x+8<=ent.shape[1]:candidates.extend((h[y:y+4,x+4:x+8],ent[y:y+4,x+4:x+8]))
        # Hidden phase terrain can continue from any cardinal neighbour. If
        # plain background and color2 candidates disagree, prefer informative
        # color2 rather than an arbitrary scan-order plain tile.
        candidates.sort(key=lambda base: bool(np.any(base==2)),reverse=True)
        for base in candidates:
            if np.all((base==1)|(base==2)):
                h[y:y+4,x:x+4]=base;break
    ent=np.array(ENTRY_GRID,dtype=int)
    for L,T,R,B in _sockets():
        xa,xb=max(x,L),min(x+4,R)
        ya,yb=max(y,T),min(y+4,B)
        if xa<xb and ya<yb:
            h[ya:yb,xa:xb]=ent[ya:yb,xa:xb]

def _restore_worker(h,x,y,wcol):
    """Restore terrain hidden by a worker, including color15 phase pads."""
    if wcol!=15 and CURRENT_LEVEL!=7:
        h[y:y+4,x:x+4]=1
        if _socket_dest(x,y):_restore_under_block(h,x,y)
        return
    h[y:y+4,x:x+4]=1
    if CURRENT_LEVEL==7:
        # A level-7 worker can stand on a phase slot that an entry cargo
        # originally concealed. Restore it with the same layout-grounded
        # reconstruction used when that cargo itself is removed.
        _restore_under_block(h,x,y)
        return
    ent=np.array(ENTRY_GRID,dtype=int)
    # Restore only actual color2 cells of a qualifying pad; a pad may be
    # L-shaped, so painting its whole bounding box would invent terrain.
    for L,T,R,B in _phase15_sockets():
        xa,xb=max(x,L),min(x+4,R);ya,yb=max(y,T),min(y+4,B)
        if xa<xb and ya<yb:
            part=h[ya:yb,xa:xb];base=ent[ya:yb,xa:xb]
            part[base==2]=2
    # Reconstruct the color9 border/color2 interior of a source socket even
    # when its entry appearance was hidden by an initial block.
    for L,T,R,B in _sockets():
        for yy in range(max(y,T),min(y+4,B)):
            for xx in range(max(x,L),min(x+4,R)):
                h[yy,xx]=9 if xx in (L,R-1) or yy in (T,B-1) else 2

def _restore_main(h,x,y,phase=False):
    """Restore terrain hidden by the main, including phase/socket underlay."""
    h[y:y+4,x:x+4]=1
    if phase:
        # A phase-capable main may stand on terrain that an entry-frame block
        # originally concealed.  Use the same layout-grounded reconstruction as
        # a moved block, so hidden phase-pad slots restore color2 (not empty 1),
        # while transfer tiles and socket borders are also preserved.
        _restore_under_block(h,x,y)

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
            # If the exporter is captured only after its held cargo has
            # already reached the phase destination, that cargo parks on the
            # capture tick even though its owner is no longer autonomous.
            for wx,wy in _DIR.values():
                bx,by=x+wx,y+wy
                if _block_at(g,bx,by,5) and _cargo_dest(15,bx,by):
                    g[by,bx:bx+4]=4;g[by+3,bx:bx+4]=4
                    g[by+1:by+3,bx]=4;g[by+1:by+3,bx+3]=4

def _companion_action5(g,worker=None,allow_phase_detour=False):
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
    # A rim5 block adjacent to the companion is its selected rigid partner.
    # Chains can make another worker's rim5 cargo adjacent too; ownership uses
    # the first direction in scan order, exactly as acquisition does.
    partner=None
    for face,(dx,dy) in _DIR.items():
        qx,qy=cx+dx,cy+dy
        if _block_at(g,qx,qy,5):
            partner=(face,dx,dy,qx,qy);break
    if partner is None:return False
    face,dx,dy,qx,qy=partner
    # Once this selected block reaches its worker-specific destination, the
    # next tick parks; ignore any adjacent cargo belonging to another worker.
    if _cargo_dest(wcol,qx,qy):return False
    if True:
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
                if (wcol==15 or CURRENT_LEVEL==7) and np.all((tile==1)|(tile==2)):return True
                if cargo and _transfer_dest(h,xx,yy):return True
                if yy==H-4 and np.all(tile[:3,:]==1) and np.all((tile[3,:]==7)|(tile[3,:]==4)):return True
                return _socket_dest(xx,yy) and np.array_equal(tile,ent[yy:yy+4,xx:xx+4])
            queue=[(cx,cy,None)];seen={(cx,cy)};i=0;chosen0=None;fallback0=None
            # If no complete pair placement is currently open, a receiver can
            # still approach a socket row whose worker-side slot is already
            # clear and whose cargo-side slot has the correct geometry.  It
            # stops before the blocked cargo slot; it does not route toward a
            # worker-only socket slot with no compatible cargo neighbour.
            stage_goals=set()
            if CURRENT_LEVEL==7 and wcol==12:
                for sL,sT,sR,sB in _sockets():
                    for sy in range(sT,sB-3,4):
                        for sx in range(sL,sR-3,4):
                            if _socket_dest(sx+offx,sy+offy) and ok(sx,sy):
                                stage_goals.add((sx,sy))
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
                        if (_socket_dest(xx,yy) and _socket_dest(bx,by)
                            and fallback0 is None):
                            fallback0=first
                elif _socket_dest(xx,yy) and _socket_dest(bx,by):
                    chosen0=first;break
                for a in (3,4,1,2):
                    mx,my=_DIR[a];nx,ny=xx+mx,yy+my
                    if (nx,ny) in seen:continue
                    if fallback0 is None and (nx,ny) in stage_goals:
                        fallback0=a if first is None else first
                    if ok(nx,ny) and ok(nx+offx,ny+offy,True):
                        seen.add((nx,ny));queue.append((nx,ny,a if first is None else first))
            if chosen0 is None:chosen0=fallback0
            if chosen0 is not None:
                mx,my=_DIR[chosen0];ncx,ncy=cx+mx,cy+my;nqx,nqy=qx+mx,qy+my
                if ok(ncx,ncy) and ok(nqx,nqy,True):
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
    # The exposed lane immediately above the bottom budget strip is a one-way
    # westbound return conveyor for receivers.  Once a receiver has peeled onto
    # y=H-4 it keeps clearing left instead of recomputing a route around the
    # moving main or nearby socket cargo each tick.
    if CURRENT_LEVEL==7 and wcol==12 and y0==H-4:
        lower_exits=[R-4 for L,T,R,B in _phase15_sockets() if T>=H//2]
        # Clear west along the HUD return lane until aligned with the
        # rightmost slot of the lower phase pad; there the ordinary route
        # turns north.  This grounds the exit column from the layout.
        if lower_exits:
            exit_x=max(lower_exits)
            if x0>exit_x:return 3
            # At the exit column the locally attended lane turns north.  When
            # the main is working in the other factory, leave the conveyor and
            # resume ordinary target routing; a diagonal target can require one
            # more west step before rising.
            mb_lane=_box(g)
            if x0==exit_x and mb_lane is not None and mb_lane[1]>=H//2:return 1
    targets=[];export_fallback=[];fallback_mode=False;fallback_diagonal=False;receiver_diagonal=False
    for yy in range(H-3):
        for xx in range(W-3):
            if not (_block_at(g,xx,yy,4) or _block_at(g,xx,yy,3)):continue
            if CURRENT_LEVEL==7 and (yy<32)!=(y0<32):continue
            if wcol==15:
                if _phase15_dest(xx,yy):continue
                if CURRENT_LEVEL==7 and _socket_dest(xx,yy):
                    export_fallback.append((xx,yy));continue
            elif _socket_dest(xx,yy):continue
            targets.append((xx,yy))
    # Exporters first process genuine source cargo. Once none remains they
    # antagonistically steal completed socket cargo and send it back to phase.
    if CURRENT_LEVEL==7 and wcol==15 and not targets:
        targets=export_fallback;fallback_mode=bool(targets)
        # A diagonally adjacent completed socket block is the immediate theft
        # assignment. Otherwise the exporter's entry-home territory breaks
        # ties (notably when it stands between upper and lower socket cargo).
        adjacent=[p for p in targets if abs(p[0]-x0)+abs(p[1]-y0)==4]
        diagonal=[p for p in targets if abs(p[0]-x0)==4 and abs(p[1]-y0)==4]
        if len(adjacent)==1:
            targets=adjacent;fallback_diagonal=True
        elif not adjacent and diagonal:
            targets=diagonal;fallback_diagonal=True
    if CURRENT_LEVEL==7 and wcol==12:
        adjacent=[p for p in targets if abs(p[0]-x0)+abs(p[1]-y0)==4]
        diagonal=[p for p in targets if abs(p[0]-x0)==4 and abs(p[1]-y0)==4]
        if len(adjacent)==1:
            targets=adjacent;receiver_diagonal=True
        elif not adjacent and diagonal:
            targets=diagonal;receiver_diagonal=True
        elif not adjacent:
            # Immediately after losing shared cargo, a receiver can be two cells
            # from the next loose block on that same local queue.  It continues
            # toward that nearby block before resuming entry-home territory.
            near=[p for p in targets if abs(p[0]-x0)+abs(p[1]-y0)<=8]
            if near:
                best=min(abs(p[0]-x0)+abs(p[1]-y0) for p in near)
                targets=[p for p in near if abs(p[0]-x0)+abs(p[1]-y0)==best]
                receiver_diagonal=True
    home_goal=None
    if CURRENT_LEVEL==7 and not fallback_diagonal and not receiver_diagonal:
        # Genuine source work uses a fixed service territory derived
        # from their entry homes. They choose the nearest remaining cargo to
        # that home (rather than the nearest to their post-delivery position).
        ent=np.array(ENTRY_GRID,dtype=int)
        homes=[p for p in _companions(ent) if (p[1]<32)==(y0<32)]
        own=[p for p in homes if int(ent[p[1],p[0]])==wcol]
        other=[p for p in homes if int(ent[p[1],p[0]])!=wcol]
        if own:
            hx,hy=own[0]
            assigned=[]
            for bx,by in targets:
                d0=(bx-hx)**2+(by-hy)**2
                keep=True
                if other and wcol!=15:
                    ox,oy=other[0];d1=(bx-ox)**2+(by-oy)**2
                    if d0>d1:keep=False
                    elif d0==d1:
                        mid=(hx+ox)/2
                        keep=(bx<mid) if wcol==15 else (bx>=mid)
                if keep:assigned.append((bx,by))
            if assigned:
                best=min((bx-hx)**2+(by-hy)**2 for bx,by in assigned)
                targets=[p for p in assigned if (p[0]-hx)**2+(p[1]-hy)**2==best]
            elif wcol==15:
                # An exporter which has exhausted its own source territory
                # returns to its entry home.  It does not steal the ordinary
                # worker's remaining source cargo.
                targets=[];home_goal=(hx,hy)
    if CURRENT_LEVEL==7 and wcol==12 and not targets and home_goal is None:
        # Once its own cargo is exhausted, an unladen receiver follows the other
        # loaded receiver in its current factory lane instead of idling at the
        # socket edge.  Aim two cells behind the selected worker; the ordinary
        # collision-aware BFS supplies the first chase step.
        loaded=[]
        for sx,sy in _companions(g):
            if (sx,sy)==(x0,y0) or (sy<32)!=(y0<32):continue
            if int(g[sy,sx])==12 and any(_block_at(g,sx+dx,sy+dy,5) for dx,dy in _DIR.values()):
                loaded.append((sx,sy))
        if loaded:
            sx,sy=min(loaded,key=lambda p:abs(p[0]-x0)+abs(p[1]-y0))
            entg=np.array(ENTRY_GRID,dtype=int)
            by=y0+4
            at_gate_edge=(by+4<=H and x0+8<=W
                          and np.all((entg[by:by+4,x0:x0+4]==1)|(entg[by:by+4,x0:x0+4]==2))
                          and np.all(entg[by:by+4,x0+4:x0+8]==5))
            # After escorting an upward pair through the narrow gate, the
            # sidecar guards the destination-side edge while the loaded pair
            # turns laterally away; it does not restart the chase.
            gate_guard=(at_gate_edge and sy==y0 and sx<=x0-8
                        and _block_at(g,sx,sy-4,5))
            if not gate_guard:
                if abs(x0-sx)>=abs(y0-sy):
                    home_goal=(sx+(8 if x0>sx else -8),sy)
                else:
                    home_goal=(sx,sy+(8 if y0>sy else -8))
    if not targets and home_goal is None:return None
    goals={}
    if home_goal is not None:goals[home_goal]=None
    for bx,by in targets:
        for a,(dx,dy) in _DIR.items():
            # position from which moving action a enters the target
            # If a worker is simultaneously adjacent to two targets, the
            # first target/direction in scan order wins (up before down).
            goals.setdefault((bx-dx,by-dy),a)
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
            if (wcol==15 or CURRENT_LEVEL==7) and np.all((tile==1)|(tile==2)):clear=True
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
        if not np.array_equal(h,g):return True
        # Cargo already at the exporter's destination can still be shared with
        # a receiver on its far side.  If that receiver can translate the
        # shared cargo away this tick, the exporter escapes into the vacated
        # cargo square and is not yet capturable.
        if CURRENT_LEVEL==7 and int(g[y,x])==15:
            shared=[]
            for dx,dy in _DIR.values():
                qx,qy=x+dx,y+dy
                if _block_at(g,qx,qy,5):shared.append((qx,qy))
            for qx,qy in shared:
                for rx,ry in _companions(g):
                    if int(g[ry,rx])!=12 or abs(rx-qx)+abs(ry-qy)!=4:continue
                    rh=g.copy();_companion_action5(rh,(rx,ry))
                    if not _block_at(rh,qx,qy,5):return True
        return False
    return _companion_dir(g,x,y) is not None

def _move_companion(g,action,turn,post=False,started=None,only=None,forced=None,followers=None,follow_out=None):
    # All unladen color12 workers with reachable cargo advance concurrently.
    if action not in _DIR:return False
    followers=set() if followers is None else set(followers)
    comps=_tick_companions(g,started)
    if only is not None:comps=[p for p in comps if p==only]
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
    # Precompute fresh acquisitions. If an earlier acquisition will freeze a
    # selected lane leader, a close unladen follower cannot advance into its
    # reserved queue spacing on the same tick.
    fresh_x={}
    selected_start=[]
    for ux,uy in comps:
        owned=any(_block_at(g,ux+dx,uy+dy,5) for dx,dy in _DIR.values())
        if int(g[uy,ux])==15 and (ux,uy) in followers:owned=False
        if owned:
            selected_start.append((ux,uy));continue
        ua=_companion_dir(g,ux,uy)
        if ua in _DIR:
            dx,dy=_DIR[ua]
            if _block_at(g,ux+dx,uy+dy,4):
                fresh_x.setdefault(int(g[uy,ux]),[]).append(ux)
    blocked_unladen=set()
    ordered_comps=sorted(comps,key=lambda p:(p[1],p[0])) if CURRENT_LEVEL==7 else comps
    for x0,y0 in ordered_comps:
        if (x0,y0) in just_parked or (x0,y0) in external_skip:continue
        # A worker currently owning rim5 cargo is handled by the rigid-pair
        # mechanism and must not also take an unladen step.
        if any(_block_at(g,x0+dx,y0+dy,5) for dx,dy in _DIR.values()) and not (int(g[y0,x0])==15 and (x0,y0) in followers):continue
        wcol=int(g[y0,x0])
        if CURRENT_LEVEL==7 and wcol in blocked_unladen:continue
        convoy_auto=None
        if CURRENT_LEVEL==7 and wcol==15 and (x0,y0) in followers:
            # If an adjacent receiver-owned cargo is about to translate away,
            # keep the exporter in its start square for the unladen phase.  It
            # will enter the cargo's vacated square after the selected pair is
            # resolved below, producing a simultaneous convoy step.
            mirror_wait=False
            for sx,sy in selected_start:
                if int(g[sy,sx])!=12:continue
                for cdx,cdy in _DIR.values():
                    qx,qy=sx+cdx,sy+cdy
                    if (not _block_at(g,qx,qy,5)
                        or abs(qx-x0)+abs(qy-y0)!=4):continue
                    ph=g.copy();_companion_action5(ph,(sx,sy))
                    for mdx,mdy in _DIR.values():
                        if not _block_at(ph,qx+mdx,qy+mdy,5):continue
                        tx,ty=x0+mdx,y0+mdy
                        # Entering the cargo's old square is simultaneous.
                        if (tx,ty)==(qx,qy):
                            mirror_wait=True;break
                        # A lateral convoy step is valid only if the follower's
                        # mirrored destination is also free after the selected
                        # pair moves. If it is blocked (notably by the main),
                        # hold now so the pair can take its axial escape route.
                        hp=ph.copy();_restore_worker(hp,x0,y0,15)
                        in_bounds=(0<=tx and 0<=ty and tx+4<=g.shape[1] and ty+4<=g.shape[0])
                        tile=hp[ty:ty+4,tx:tx+4] if in_bounds else np.zeros((0,0),dtype=int)
                        clear=in_bounds and np.all((tile==1)|(tile==2))
                        # Static walls merely split the escort.  Only the main
                        # physically blocking the follower's mirrored square
                        # makes the selected pair take the axial convoy route.
                        blocked_by_main=in_bounds and np.any((tile==14)|(tile==0))
                        mbm=_box(g);mfm=_facing(g,mbm);intercept=False
                        if mbm is not None and mfm in _DIR:
                            imdx,imdy=_DIR[mfm]
                            intercept=(qx+mdx,qy+mdy)==(mbm[0]+imdx,mbm[1]+imdy)
                        # A main-facing cargo interception has priority: the
                        # pair keeps its route and the follower enters the old
                        # cargo square rather than forcing an axial detour.
                        main_faces_follower=False
                        if mbm is not None and mfm in _DIR:
                            smdx,smdy=_DIR[mfm]
                            main_faces_follower=(mbm[0]+smdx,mbm[1]+smdy)==(x0,y0)
                        # At the lower HUD edge, a perpendicular/away-facing
                        # main directly shadowing the follower locks the escort
                        # lane: a clear lateral receiver move carries the whole
                        # three-body convoy. Facing straight at the follower is
                        # ordinary pursuit and keeps the normal priority rules.
                        edge_shadow=(mbm is not None and not main_faces_follower
                                     and abs(mbm[0]-x0)+abs(mbm[1]-y0)==4
                                     and qy==g.shape[0]-8 and y0==qy-4
                                     and mdy==0)
                        edge_socket_clear=False
                        if in_bounds and edge_shadow and _socket_dest(tx,ty):
                            ent_shadow=np.array(ENTRY_GRID,dtype=int)
                            edge_socket_clear=np.array_equal(tile,ent_shadow[ty:ty+4,tx:tx+4])
                        if (clear or edge_socket_clear) and edge_shadow and not intercept:
                            mirror_wait=True;break
                        # Away from the special HUD-edge train, an escort whose
                        # mirrored destination is free takes the same translation
                        # as its receiver/cargo pair.  This is its committed convoy
                        # step, not an independent nearest-cargo route.
                        if clear and not intercept:
                            for aa,vv in _DIR.items():
                                if vv==(mdx,mdy):convoy_auto=aa;break
                            break
                        if not clear and blocked_by_main and not intercept:
                            mirror_wait=True;break
                    if mirror_wait:break
                if mirror_wait:break
            if mirror_wait:
                if follow_out is not None:follow_out.add((x0,y0))
                continue
            # A released block wedged between a following exporter and its
            # receiver is a reserved interception barrier.  The receiver may
            # peel away, but the exporter holds instead of following through.
            contested_barrier=False
            for bdx,bdy in _DIR.values():
                bx,by=x0+bdx,y0+bdy
                if not _block_at(g,bx,by,3):continue
                ox,oy=bx+bdx,by+bdy
                if (0<=ox and 0<=oy and ox+4<=g.shape[1] and oy+4<=g.shape[0]
                    and np.all(g[oy:oy+4,ox:ox+4]==12)):
                    contested_barrier=True;break
            if contested_barrier:continue
        if isinstance(forced,dict):
            fv=forced.get((x0,y0))
            auto=fv if fv in _DIR else _companion_dir(g,x0,y0)
        else:
            auto=forced if forced in _DIR else _companion_dir(g,x0,y0)
        if convoy_auto in _DIR:auto=convoy_auto
        if CURRENT_LEVEL==7 and wcol==12:
            # Once the main has intercepted cargo into a faced rim3 square, a
            # receiver still flanking that square clears perpendicular traffic
            # by moving opposite the main's facing instead of re-acquiring it.
            mbc=_box(g);mfc=_facing(g,mbc)
            if mbc is not None and mfc in _DIR:
                mdx,mdy=_DIR[mfc];claim=(mbc[0]+mdx,mbc[1]+mdy)
                if _block_at(g,claim[0],claim[1],3):
                    sep=abs(x0-claim[0])+abs(y0-claim[1])
                    if sep==4:
                        auto={1:2,2:1,3:4,4:3}[mfc]
                    elif sep==8 and abs(y0-claim[1])==4:
                        auto=1 if y0<claim[1] else 2
                    elif sep==8 and abs(x0-claim[0])==4:
                        auto=3 if x0<claim[0] else 4
                # If the main has just turned away, the old claimed rim3 is
                # diagonal to the flanking receiver while the main itself is
                # still orthogonally adjacent.  Clear along the receiver's
                # cargo-offset axis.
                if abs(x0-mbc[0])+abs(y0-mbc[1])==4:
                    for rdx in (-4,4):
                        for rdy in (-4,4):
                            rx,ry=x0+rdx,y0+rdy
                            if _block_at(g,rx,ry,3) or _block_at(g,rx,ry,4):
                                auto=1 if rdy>0 else 2
        chasing=False
        if CURRENT_LEVEL==7 and wcol==15:
            # After dropping cargo into a phase row, an exporter sidesteps
            # toward an immediately neighbouring parked phase block instead of
            # taking its ordinary home/socket route.  This preserves spacing
            # between the receiver train and the just-completed delivery.
            above=(x0,y0-4);above_left=(x0-4,y0-4)
            source_left=False
            for by in range(g.shape[0]-3):
                for bx in range(g.shape[1]-3):
                    if (by<32)==(y0<32) and (_block_at(g,bx,by,4) or _block_at(g,bx,by,3)):
                        if not _phase15_dest(bx,by) and not _socket_dest(bx,by):
                            source_left=True;break
                if source_left:break
            phase_pair=False
            for by in range(g.shape[0]-3):
                for bx in range(g.shape[1]-7):
                    if ((by<32)==(y0<32)
                        and _block_at(g,bx,by,4) and _phase15_dest(bx,by)
                        and _block_at(g,bx+4,by,4) and _phase15_dest(bx+4,by)):
                        phase_pair=True;break
                if phase_pair:break
            if y0>=32 and phase_pair and _phase15_dest(x0,y0):
                # Once the lower phase pad has a completed adjacent cargo row,
                # its exhausted exporter follows that row west. At the pad edge
                # it turns north only when all genuine source work is exhausted.
                # If a source queue remains and the just-completed row blocks the
                # north side, it leaves west around the row instead.
                at_left=any(L==x0 and T<=y0 and y0+4<=B
                            for L,T,R,B in _phase15_sockets())
                row_above=(_block_at(g,x0,y0-4,4)
                           and _block_at(g,x0+4,y0-4,4))
                if source_left and at_left and row_above:auto=3
                elif not source_left:auto=1 if at_left else 3
            # Exporters also chase cargo already owned by a receiver.  When a
            # horizontal pair is two cells directly below/above, its cargo
            # will translate into the receiver's old column; the exporter
            # advances vertically to meet that projected cargo.
            projected_wait=False
            for sx,sy in selected_start:
                if int(g[sy,sx])!=12 or abs(sy-y0)!=8:continue
                horizontal_cargo=[]
                if _block_at(g,sx-4,sy,5):horizontal_cargo.append((sx-4,sy))
                if _block_at(g,sx+4,sy,5):horizontal_cargo.append((sx+4,sy))
                # If the receiver's horizontal cargo is already in the
                # exporter's column, its next vertical translation will place
                # it adjacent. The exporter reserves that rendezvous square.
                aligned=[(qx,qy) for qx,qy in horizontal_cargo if qx==x0]
                if aligned:
                    # Reserve only when this pair's actual next route is
                    # vertical toward the exporter.  While it is still
                    # aligning horizontally, the exporter follows alongside.
                    ph=g.copy();_companion_action5(ph,(sx,sy))
                    step_y=4 if y0>sy else -4
                    if any(_block_at(ph,qx,qy+step_y,5) for qx,qy in aligned):
                        projected_wait=True;chasing=True;break
                if sx==x0 and horizontal_cargo:
                    auto=2 if sy>y0 else 1;chasing=True;break
            if projected_wait:
                if follow_out is not None:follow_out.add((x0,y0))
                continue
        if auto is None:continue
        dx,dy=_DIR[auto];nx,ny=x0+dx,y0+dy
        h=g.copy();_restore_worker(h,x0,y0,wcol)
        clear=False
        if 0<=nx and 0<=ny and nx+4<=g.shape[1] and ny+4<=g.shape[0]:
            tile=h[ny:ny+4,nx:nx+4]
            clear=np.all(tile==1)
            if (wcol==15 or CURRENT_LEVEL==7) and np.all((tile==1)|(tile==2)):clear=True
            if ny==g.shape[0]-4 and np.all(tile[:3,:]==1) and np.all((tile[3,:]==7)|(tile[3,:]==4)):clear=True
            if not clear and _socket_dest(nx,ny):
                ent=np.array(ENTRY_GRID,dtype=int)
                clear=np.array_equal(tile,ent[ny:ny+4,nx:nx+4])
        # An exporter may immediately take an explicitly released rim3 queue
        # and spend the same tick transporting it.  Mark the resulting pair as
        # already handled so the later shared mover pass cannot translate it a
        # second time.
        rim3_main_claim=False
        if CURRENT_LEVEL==7 and wcol==15 and _block_at(g,nx,ny,3):
            mb3=_box(g);mf3=_facing(g,mb3)
            if mb3 is not None and mf3 in _DIR:
                cdx,cdy=_DIR[mf3]
                rim3_main_claim=(mb3[0]+cdx,mb3[1]+cdy)==(nx,ny)
        if (CURRENT_LEVEL==7 and wcol==15 and _block_at(g,nx,ny,3)
            and not rim3_main_claim):
            g[ny,nx:nx+4]=5;g[ny+3,nx:nx+4]=5
            g[ny+1:ny+3,nx]=5;g[ny+1:ny+3,nx+3]=5
            _companion_action5(g,(x0,y0))
            if isinstance(post,set):
                for ux,uy in _companions(g):
                    if int(g[uy,ux])==15 and any(_block_at(g,ux+adx,uy+ady,5) for adx,ady in _DIR.values()):
                        post.add((ux,uy))
            blocked_unladen.add(wcol)
        # A rim4 entry block may exactly match the socket underlay; it is
        # still cargo and collision/selection takes precedence over walking.
        elif _block_at(g,nx,ny,4):
            # Cargo directly adjacent to the main player is reserved for the
            # player: an autonomous receiver cannot acquire it from the other
            # side on that tick.
            mb=_box(g);mf=_facing(g,mb)
            main_claim=False
            if mb is not None and mf in _DIR:
                mcx,mcy=_DIR[mf]
                main_claim=(mb[0]+mcx,mb[1]+mcy)==(nx,ny)
            if not main_claim:
                g[ny,nx:nx+4]=5;g[ny+3,nx:nx+4]=5
                g[ny+1:ny+3,nx]=5;g[ny+1:ny+3,nx+3]=5
                if CURRENT_LEVEL==7:blocked_unladen.add(wcol)
        elif clear:
            stall=False
            if CURRENT_LEVEL==7:
                for sx,sy in selected_start:
                    if sy==y0 and abs(sx-x0)==12 and (sx-x0)*(nx-x0)>0:
                        scol=int(g[sy,sx])
                        if any(fx<sx for fx in fresh_x.get(scol,[])):
                            stall=True;break
                    # A horizontally oriented selected pair directly above or
                    # below will translate its cargo into the worker's old
                    # cell, making it adjacent to this unladen worker.  That
                    # adjacent ownership slot is reserved for the pair, so the
                    # unladen worker waits rather than leaving/compressing it.
                    if sx==x0 and abs(sy-y0)==4 and (
                        _block_at(g,sx-4,sy,5) or _block_at(g,sx+4,sy,5)
                    ):
                        stall=True;break
            if not stall:
                g[:,:]=h;g[ny:ny+4,nx:nx+4]=wcol
                if follow_out is not None and wcol==15 and (chasing or (x0,y0) in followers):
                    follow_out.add((nx,ny))
            elif follow_out is not None and wcol==15 and (x0,y0) in followers:
                follow_out.add((x0,y0))
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
    n=((32*turn+17)//35) if CURRENT_LEVEL in (1,8) else ((128*turn+75)//150 if CURRENT_LEVEL==5 else (((64*turn+75)//150) if CURRENT_LEVEL==7 else (((128*turn+125)//250) if CURRENT_LEVEL in (4,6) else (((16*turn+12)//25) if CURRENT_LEVEL is not None and CURRENT_LEVEL>=2 else ((turn+1)//3 if turn<=11 else (4+max(0,(turn-12)//3) if turn<=38 else 4+max(0,(turn-13)//3)))))))
    if n:g[-1,max(0,g.shape[1]-n):]=4

def predict(state,grid,action,x=None,y=None):
    g=np.array(grid,dtype=int)
    pre_main=_box(g)
    # A direct collision is resolved after the autonomous worker phase.  A
    # worker which looked mobile in the start frame can still be held by
    # same-tick traffic; if it remains in the collided square, it is captured.
    capture_probe=None
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
    elif CURRENT_LEVEL==7:
        # Live state can be left a tick behind when a surprise rejects a queued
        # continuation.  The rendered 150-turn meter supplies a safe lower bound
        # for the real clock and prevents the next pixel threshold from causing
        # a grid-only false surprise.
        meter=int(np.sum(g[-1,:]==4))
        raw=max(int(raw),max(0,(150*meter-75+63)//64))
    active=state.get("comp_active",None)
    if active is None:
        ys,xs=np.where((g==12)|(g==15))
        active=bool(len(xs) and int(xs.min())<36)
    post=state.get("comp_post",None)
    if post is None:
        ys,xs=np.where((g==12)|(g==15))
        post=bool(len(xs) and int(xs.min())<24 and not any(_block_at(g,int(xs.min())+dx,int(ys.min())+dy,5) for dx,dy in _DIR.values()))
    phase=bool(state.get("phase_power",False))
    lanes=int(state.get("lane_started",0))
    st={"turn":int(raw),"comp_active":bool(active),"comp_post":bool(post),"phase_power":phase,"lane_started":lanes,"export_wait":set(state.get("export_wait",set())),"export_follow":set(state.get("export_follow",set())),"export_pin":set(state.get("export_pin",set()))}
    info={"level_up":False,"dead":False,"win":False}
    # Preserve which queues were explicitly released by the main at tick start.
    # Workers can immediately take and transport rim3 cargo, whereas first
    # contact with an ordinary rim4 block consumes the tick selecting it.
    pre_rim3=set()
    for yy in range(g.shape[0]-3):
        for xx in range(g.shape[1]-3):
            if _block_at(g,xx,yy,3):pre_rim3.add((xx,yy))
    # Receivers commit their unladen route while a main-facing rim3 block is
    # still reserved by the player.  If the player's action turns away and
    # releases that block to rim4, they do not retarget to it until next tick.
    # Compute that committed route with the reserved cargo omitted.
    pre_receiver_forced={}
    if CURRENT_LEVEL==7 and pre_main is not None:
        pf=_facing(g,pre_main)
        if pf in _DIR:
            pdx,pdy=_DIR[pf];pq=(pre_main[0]+pdx,pre_main[1]+pdy)
            reserved_rim3=_block_at(g,pq[0],pq[1],3)
            released_rim0=(action==5 and _block_at(g,pq[0],pq[1],0))
            if reserved_rim3 or released_rim0:
                pg=g.copy()
                # Rim3 is ordinary cargo to the route finder, so erase the
                # player's reservation. A held rim0 is already non-target
                # terrain and remains as the start-frame obstacle.
                if reserved_rim3:_restore_under_block(pg,pq[0],pq[1])
                for ux,uy in _companions(g):
                    if int(g[uy,ux])==12 and not any(_block_at(g,ux+udx,uy+udy,5) for udx,udy in _DIR.values()):
                        # A nearby release is visible soon enough for the
                        # receiver to retarget on this tick.  Only distant
                        # receivers keep the route committed while rim0 was
                        # still a non-target obstacle.
                        near_release=(released_rim0
                                      and abs(ux-pq[0])+abs(uy-pq[1])<=12)
                        if not near_release:
                            pre_receiver_forced[(ux,uy)]=_companion_dir(pg,ux,uy)

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
                    if not clear and st["phase_power"] and _socket_dest(nx,ny):
                        entm=np.array(ENTRY_GRID,dtype=int)
                        clear=np.array_equal(tile,entm[ny:ny+4,nx:nx+4])
                if clear:
                    g=h;_draw_player(g,nx,ny,action);moved=True
                    _highlight(g,_box(g),action)
                    # A successful pursuit step threatens the cell immediately
                    # ahead of the moved player.  Resolve it after traffic too:
                    # an exporter which convoys into that cell is captured just
                    # like one that failed to vacate a blocked collision square.
                    tx,ty=nx+dx,ny+dy
                    if 0<=tx and 0<=ty and tx+4<=g.shape[1] and ty+4<=g.shape[0]:
                        capture_probe=(tx,ty)
                else:
                    # A blocked arrow still turns the main player and selects
                    # an adjacent block in the attempted direction.
                    if (0<=nx and 0<=ny and nx+4<=g.shape[1] and ny+4<=g.shape[0]
                        and np.all(g[ny:ny+4,nx:nx+4]==15)):
                        capture_probe=(nx,ny)
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
                        # Release only cargo owned exclusively by the captive.
                        # A follower may be captured beside receiver-owned cargo;
                        # absorbing it must not break that surviving pair.
                        shared=any(abs(ux-bx)+abs(uy-by)==4
                                   for ux,uy in _companions(g))
                        if not shared:
                            g[by,bx:bx+4]=4;g[by+3,bx:bx+4]=4
                            g[by+1:by+3,bx]=4;g[by+1:by+3,bx+3]=4
                _restore_worker(g,qx,qy,15)
                st["phase_power"]=True
            elif _block_at(g,qx,qy):
                r=g[qy:qy+4,qx:qx+4];bd=_border(r)
                val=0 if np.all(bd==3) else (3 if np.all(bd==0) else None)
                # A released rim3 block still wedged between autonomous
                # workers is contested traffic, not yet a main-held block;
                # action5 is consumed without toggling it.
                contested=False
                if CURRENT_LEVEL==7 and val==0:
                    for wdx,wdy in _DIR.values():
                        wx,wy=qx+wdx,qy+wdy
                        if (0<=wx and 0<=wy and wx+4<=g.shape[1] and wy+4<=g.shape[0]
                            and int(g[wy,wx]) in (12,15)
                            and np.all(g[wy:wy+4,wx:wx+4]==int(g[wy,wx]))):
                            contested=True;break
                if val is not None and not contested:
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
        if CURRENT_LEVEL==7:
            bnow=_box(g)
            if bnow is not None:st["lane_started"]|=(1 if bnow[1]<32 else 2)
        if multi:
            selected=[];parked_workers=set();parked_cargo=set()
            follow_old=set(st.get("export_follow",set()));follow_next=set()
            pin_old=set(st.get("export_pin",set()));pin_next=set()
            # A following exporter normally ignores the receiver-owned cargo it
            # is escorting.  Exception: if that cargo is shared with a receiver
            # occupying the square directly faced by the main, the impending
            # interception makes the exporter participate in the handoff.
            intercept_follow=set();pinched_follow=set()
            if CURRENT_LEVEL==7 and follow_old:
                mbi=_box(g);mfi=_facing(g,mbi);faced_i=None
                if mbi is not None and mfi in _DIR:
                    idxi,idyi=_DIR[mfi];faced_i=(mbi[0]+idxi,mbi[1]+idyi)
                if faced_i is not None:
                    fxr,fyr=faced_i
                    if (0<=fxr and 0<=fyr and fxr+4<=g.shape[1] and fyr+4<=g.shape[0]
                        and np.all(g[fyr:fyr+4,fxr:fxr+4]==12)):
                        for ex,ey in follow_old:
                            if int(g[ey,ex])!=15:continue
                            for edx,edy in _DIR.values():
                                qx,qy=ex+edx,ey+edy
                                if (_block_at(g,qx,qy,5)
                                    and abs(fxr-qx)+abs(fyr-qy)==4):
                                    intercept_follow.add((ex,ey));break
                # If the main enters the square directly opposite a shared
                # receiver cargo, it pins the follower against that cargo. The
                # exporter reclaims the cargo instead of continuing as escort.
                if mbi is not None:
                    for ex,ey in follow_old:
                        if int(g[ey,ex])!=15:continue
                        # Facing the exporter itself is an ordinary pursuit:
                        # the escort convoy keeps moving.  A pinch occurs only
                        # when the main occupies the opposite square while facing
                        # away/perpendicular, sealing the follower behind cargo.
                        faces_exporter=False
                        if mfi in _DIR:
                            mdx,mdy=_DIR[mfi]
                            faces_exporter=(mbi[0]+mdx,mbi[1]+mdy)==(ex,ey)
                        for edx,edy in _DIR.values():
                            qx,qy=ex+edx,ey+edy
                            # At the lower HUD edge a cargo-below convoy
                            # cannot peel its receiver farther south as the pinch
                            # handoff requires, so it retains escort priority and
                            # continues laterally instead.
                            edge_unpeel=(edy==4 and qy==g.shape[0]-8)
                            if (_block_at(g,qx,qy,5)
                                and (ex-edx,ey-edy)==(mbi[0],mbi[1])
                                and not faces_exporter and not edge_unpeel):
                                pinched_follow.add((ex,ey))
                                intercept_follow.add((ex,ey));break
            for cx,cy in _companions(g):
                if (CURRENT_LEVEL==7 and int(g[cy,cx])==15
                    and (cx,cy) in follow_old and (cx,cy) not in intercept_follow):continue
                for dx,dy in _DIR.values():
                    qx,qy=cx+dx,cy+dy
                    if _block_at(g,qx,qy,5):
                        selected.append((cx,cy,qx,qy));break
            selected_cols={(cx,cy):int(g[cy,cx]) for cx,cy,qx,qy in selected}
            # When the main newly enters opposite a non-following exporter
            # across receiver-shared cargo, both claimants hold for this tick.
            # The pin grants exporter priority on the following tick.
            pin_hold=set()
            if CURRENT_LEVEL==7:
                mbh=_box(g)
                main_entered=(mbh is not None and pre_main is not None
                              and (mbh[0],mbh[1])!=(pre_main[0],pre_main[1]))
                if main_entered:
                    for ex,ey,qx,qy in selected:
                        if int(g[ey,ex])!=15 or (ex,ey) in follow_old:continue
                        odx,ody=qx-ex,qy-ey
                        if (mbh[0],mbh[1])!=(ex-odx,ey-ody):continue
                        for rx,ry,rqx,rqy in selected:
                            if int(g[ry,rx])==12 and (rqx,rqy)==(qx,qy):
                                pin_hold.update(((ex,ey),(rx,ry)))
                                pin_next.add((ex,ey))
            parked_workers.update(pin_hold)
            old_cargo={(qx,qy) for cx,cy,qx,qy in selected}
            # Cache every selected worker's unladen route against the start
            # frame. If an earlier worker steals its shared cargo, this is the
            # direction it uses when its own left-to-right turn arrives.
            selected_auto={(cx,cy):_companion_dir(g,cx,cy) for cx,cy,qx,qy in selected}
            # Cache unladen routes against the start-of-tick frame.  A delivery
            # which parks this tick becomes ordinary rim4 cargo only after route
            # assignment, so another unladen worker cannot retarget to it until
            # the following tick.
            unladen_forced={}
            for ux,uy in _companions(g):
                if not any(_block_at(g,ux+udx,uy+udy,5) for udx,udy in _DIR.values()):
                    if (ux,uy) in pre_receiver_forced:
                        unladen_forced[(ux,uy)]=pre_receiver_forced[(ux,uy)]
                    else:
                        unladen_forced[(ux,uy)]=_companion_dir(g,ux,uy)
            # A screen-earlier fresh acquisition consumes a colour's parking
            # phase too: a later same-colour arrival holds rim5 for this tick,
            # rather than parking before the earlier worker has resolved.
            deferred_park=set()
            if CURRENT_LEVEL==7:
                for cx,cy,qx,qy in selected:
                    if not _cargo_dest(int(g[cy,cx]),qx,qy):continue
                    for ux,uy in _companions(g):
                        if ((uy,ux)>=(cy,cx) or int(g[uy,ux])!=int(g[cy,cx])
                            or any(_block_at(g,ux+adx,uy+ady,5) for adx,ady in _DIR.values())):
                            continue
                        ua=unladen_forced.get((ux,uy),_companion_dir(g,ux,uy))
                        if ua in _DIR:
                            udx,udy=_DIR[ua]
                            if _block_at(g,ux+udx,uy+udy,4):
                                deferred_park.add((cx,cy));break
            # Cargo already in a socket at tick start parks now.
            for cx,cy,qx,qy in selected:
                if (cx,cy) in pin_hold or (cx,cy) in deferred_park:continue
                if _cargo_dest(int(g[cy,cx]),qx,qy):
                    g[qy,qx:qx+4]=4;g[qy+3,qx:qx+4]=4
                    g[qy+1:qy+3,qx]=4;g[qy+1:qy+3,qx+3]=4
                    parked_workers.add((cx,cy));parked_cargo.add((qx,qy));parked_any=True
            # A following exporter does not immediately re-take the receiver
            # cargo it has just escorted to its socket.  It chooses its route
            # with that newly parked cargo omitted, allowing another adjacent
            # socket block (if any) to become its next export assignment.
            follower_forced=dict(unladen_forced)
            for fx,fy in follow_old:
                adjacent=[q for q in parked_cargo if abs(q[0]-fx)+abs(q[1]-fy)==4]
                if adjacent:
                    # If the follower is sandwiched between the just-parked
                    # receiver cargo and a main-reserved rim3 on the opposite
                    # side, both ownership reservations persist through this
                    # delivery tick.  It holds rather than peeling laterally.
                    reserved_sandwich=False
                    for qx,qy in adjacent:
                        odx,ody=qx-fx,qy-fy
                        if _block_at(g,fx-odx,fy-ody,3):
                            reserved_sandwich=True;break
                    if reserved_sandwich:
                        parked_workers.add((fx,fy));follow_next.add((fx,fy))
                    else:
                        tmp=g.copy()
                        for qx,qy in adjacent:_restore_under_block(tmp,qx,qy)
                        follower_forced[(fx,fy)]=_companion_dir(tmp,fx,fy)
            # A follower immediately abandons escort duty when the main turns
            # away from a rim3 reservation beside it.  The released block was
            # already queued at tick start, so the exporter may acquire and
            # transport it on this same tick (unlike ordinary rim4 contact).
            released_follow=set()
            for fx,fy in follow_old:
                for dx,dy in _DIR.values():
                    q=(fx+dx,fy+dy)
                    if q in pre_rim3 and _block_at(g,q[0],q[1],4):
                        released_follow.add((fx,fy))
                        # Queue priority is tied to the released square itself,
                        # not the exporter's ordinary nearest-cargo routing.
                        for a,v in _DIR.items():
                            if v==(dx,dy):follower_forced[(fx,fy)]=a;break
                        # The receiver which just parked the escort cargo peels
                        # along the opposite axis while the exporter services
                        # the released queue, rather than immediately retargeting
                        # that parked block at the socket edge.
                        for rx,ry in _companions(g):
                            if int(g[ry,rx])!=12:continue
                            shared_park=False
                            for cdx,cdy in _DIR.values():
                                cx,cy=fx+cdx,fy+cdy
                                if ((cx,cy)!=q and _block_at(g,cx,cy,4)
                                    and abs(rx-cx)+abs(ry-cy)==4):
                                    shared_park=True;break
                            if shared_park:
                                for a,v in _DIR.items():
                                    if v==(-dx,-dy):follower_forced[(rx,ry)]=a;break
                        break
            # Unladen workers move first and may acquire new cargo.  A fresh
            # collision consumes the shared transport phase for this tick.
            _move_companion(g,ca,st["turn"],parked_workers,st.get("lane_started",0),forced=follower_forced,followers=(follow_old-intercept_follow-released_follow),follow_out=follow_next)
            new_positions=set();new_collision_lanes=set();new_collision_colors=set()
            for cx,cy in _tick_companions(g,st.get("lane_started",0)):
                for dx,dy in _DIR.values():
                    qx,qy=cx+dx,cy+dy
                    if _block_at(g,qx,qy,5) and (qx,qy) not in old_cargo:
                        new_positions.add((qx,qy));new_collision_colors.add(int(g[cy,cx]))
                        if CURRENT_LEVEL==7:new_collision_lanes.add(1 if cy<32 else 2)
            new_collision=bool(new_positions)
            fast_new=new_collision and all(p in pre_rim3 for p in new_positions)
            # A fresh collision with ordinary rim4 cargo consumes the shared
            # transport phase. Explicit rim3 queues are taken immediately;
            # otherwise every pair already selected at tick start moves once.
            if not new_collision or fast_new or CURRENT_LEVEL==7:
                movers=[]
                for cx,cy in _companions(g):
                    if (cx,cy) in deferred_park:continue
                    edge_held=False
                    if (CURRENT_LEVEL==7 and int(g[cy,cx])==15
                        and (cx,cy) in follow_old and (cx,cy) in follow_next):
                        mbh2=_box(g);mfh2=_facing(g,mbh2);faces_h2=False
                        if mbh2 is not None and mfh2 in _DIR:
                            hdx2,hdy2=_DIR[mfh2]
                            faces_h2=(mbh2[0]+hdx2,mbh2[1]+hdy2)==(cx,cy)
                        edge_held=(mbh2 is not None and not faces_h2
                                   and abs(mbh2[0]-cx)+abs(mbh2[1]-cy)==4
                                   and any(_block_at(g,cx+dx,cy+dy,5)
                                           and cy+dy==g.shape[0]-8
                                           for dx,dy in _DIR.values()))
                    if edge_held:continue
                    for dx,dy in _DIR.values():
                        qx,qy=cx+dx,cy+dy
                        if _block_at(g,qx,qy,5):
                            movers.append((cx,cy));break
                active_now=set(_tick_companions(g,st.get("lane_started",0)))
                # The distributed factories resolve in screen scan order:
                # upper-lane workers before lower-lane workers, then left to
                # right within a row. This lets an upper old pair move before
                # a lower fresh acquisition, while the reverse blocks later.
                if CURRENT_LEVEL==7:
                    movers.sort(key=lambda p:(0 if p in pinched_follow or p in pin_old else 1,p[1],p[0]))
                    # A main-facing interception reserves the receiver's old
                    # square for its translated cargo.  When an exporter and a
                    # receiver share that cargo, resolve the receiver first so
                    # it vacates the faced square and shifts the cargo into it;
                    # the exporter then advances into the cargo's old square.
                    mbp=_box(g);mfp=_facing(g,mbp)
                    faced=None
                    if mbp is not None and mfp in _DIR:
                        fdx,fdy=_DIR[mfp];faced=(mbp[0]+fdx,mbp[1]+fdy)
                    if faced is not None:
                        for i,(ex,ey) in enumerate(list(movers)):
                            if int(g[ey,ex])!=15:continue
                            shared=[]
                            for edx,edy in _DIR.values():
                                eq=(ex+edx,ey+edy)
                                if _block_at(g,eq[0],eq[1],5):shared.append(eq)
                            for j,(rx,ry) in enumerate(list(movers)):
                                if (rx,ry)!=faced or int(g[ry,rx])!=12:continue
                                if any(abs(rx-qx)+abs(ry-qy)==4 for qx,qy in shared):
                                    if i<j:movers[i],movers[j]=movers[j],movers[i]
                                    break
                    # Resolve a nose-to-tail handoff rear-first.  If an exporter
                    # carrying above itself can enter a phase slot only after a
                    # receiver eight cells below shifts its intervening cargo
                    # sideways, the receiver vacates that slot first and the
                    # exporter advances into it on the same simultaneous tick.
                    for i,(ex,ey) in enumerate(list(movers)):
                        if int(g[ey,ex])!=15 or not _block_at(g,ex,ey-4,5) or not _phase15_dest(ex,ey):continue
                        rear=(ex,ey+8)
                        if rear in movers and int(g[rear[1],rear[0]])==12 and _block_at(g,ex,ey+4,5):
                            j=movers.index(rear)
                            if i<j:movers[i],movers[j]=movers[j],movers[i]
                # When a downward-cargo exporter is diagonally nose-to-tail
                # with a receiver carrying upward on the same cargo row, the
                # receiver reserves the west cargo slot.  They resolve as one
                # simultaneous weave: exporter up, receiver right.
                weave_done=set()
                if CURRENT_LEVEL==7:
                    for ex,ey in list(movers):
                        rx,ry=ex-8,ey+8
                        if (int(g[ey,ex])==15 and _block_at(g,ex,ey+4,5)
                            and (rx,ry) in movers and int(g[ry,rx])==12
                            and _block_at(g,rx,ry-4,5)):
                            ep=g[ey+4:ey+8,ex:ex+4].copy()
                            rp=g[ry-4:ry,rx:rx+4].copy()
                            h=g.copy()
                            _restore_worker(h,ex,ey,15);_restore_under_block(h,ex,ey+4)
                            _restore_worker(h,rx,ry,12);_restore_under_block(h,rx,ry-4)
                            h[ey:ey+4,ex:ex+4]=ep;h[ey-4:ey,ex:ex+4]=15
                            h[ry-4:ry,rx+4:rx+8]=rp;h[ry:ry+4,rx+4:rx+8]=12
                            g[:,:]=h;weave_done.update(((ex,ey),(rx,ry)));comp_used=True
                    movers=[p for p in movers if p not in weave_done]
                blocked_colors=set()
                for worker in movers:
                    if CURRENT_LEVEL==7:
                        wcol_now=int(g[worker[1],worker[0]])
                        old_pair=any(_block_at(g,worker[0]+dx,worker[1]+dy,5) and (worker[0]+dx,worker[1]+dy) in old_cargo for dx,dy in _DIR.values())
                        # Workers resolve left-to-right. A fresh acquisition
                        # consumes that color's transport phase only for later
                        # same-color workers; earlier old pairs already moved.
                        if old_pair:
                            lane_ok=wcol_now not in blocked_colors
                            # A selected receiver one translation from placing its
                            # cargo in a socket completes that placement even if an
                            # earlier same-colour worker acquired fresh cargo this
                            # tick; destination entry has priority over the shared
                            # transport-phase freeze.
                            if not lane_ok and wcol_now==12:
                                for pdx,pdy in _DIR.values():
                                    pqx,pqy=worker[0]+pdx,worker[1]+pdy
                                    if _block_at(g,pqx,pqy,5):
                                        if any(_socket_dest(pqx+mdx,pqy+mdy) for mdx,mdy in _DIR.values()):
                                            lane_ok=True
                                        break
                        else:
                            lane_ok=fast_new
                            if not fast_new:blocked_colors.add(wcol_now)
                    else:
                        lane_ok=(not new_collision or fast_new or worker not in active_now)
                    if worker not in parked_workers and lane_ok:
                        wx,wy=worker;pair_key=None
                        for dx,dy in _DIR.values():
                            tq=(wx+dx,wy+dy)
                            if _block_at(g,tq[0],tq[1],5):pair_key=(wx,wy,tq[0],tq[1]);break
                        before_pair=g.copy()
                        sidecars=[]
                        if CURRENT_LEVEL==7 and wcol_now==12:
                            # Adjacent unladen same-colour workers can merge into
                            # an 8x4 solid bar and disappear from _companions().
                            # Remember those sidecars before transporting the
                            # selected pair so they can mirror its turn.
                            for sdx,sdy in _DIR.values():
                                fx,fy=wx+sdx,wy+sdy
                                if (0<=fx and 0<=fy and fx+4<=g.shape[1] and fy+4<=g.shape[0]
                                    and np.all(g[fy:fy+4,fx:fx+4]==12)
                                    and not any(_block_at(g,fx+adx,fy+ady,5) for adx,ady in _DIR.values())):
                                    sidecars.append((fx,fy))
                        allow=(CURRENT_LEVEL==7 and pair_key in st["export_wait"])
                        traffic_hold=False
                        if CURRENT_LEVEL==7 and wcol_now==12 and _block_at(g,wx,wy+4,5):
                            # A receiver aligned at the edge cell of a narrow wall
                            # gate has committed to the socket beyond that gate.
                            # If another loaded receiver on the far side still owns
                            # that delivery route, it waits rather than rerouting
                            # to a different socket.  (At non-edge gate cells it
                            # may still align laterally alongside the other pair.)
                            ent0=np.array(ENTRY_GRID,dtype=int)
                            gy=wy+8
                            gate_edge=(gy+4<=g.shape[0] and wx+8<=g.shape[1]
                                       and np.all((ent0[gy:gy+4,wx:wx+4]==1)|(ent0[gy:gy+4,wx:wx+4]==2))
                                       and np.all(ent0[gy:gy+4,wx+4:wx+8]==5))
                            if gate_edge:
                                for ox,oy in movers:
                                    other_loaded=any(_block_at(g,ox+odx,oy+ody,5) and (ox+odx,oy+ody) in old_cargo for odx,ody in _DIR.values())
                                    if ((ox,oy)!=worker and int(g[oy,ox])==12
                                        and other_loaded and oy>wy):
                                        traffic_hold=True;break
                        if not traffic_hold:
                            # A receiver pair and an adjacent following exporter
                            # form a three-body convoy. Normally the follower
                            # mirrors the pair. If that mirrored square is
                            # blocked, the whole train instead advances along
                            # its axis, away from the follower.
                            convoy_forced=False
                            if CURRENT_LEVEL==7 and wcol_now==12 and pair_key is not None:
                                oqx,oqy=pair_key[2],pair_key[3]
                                for ex,ey in list(follow_old):
                                    bottom_ex=(ey==g.shape[0]-4
                                               and np.all(g[ey:ey+3,ex:ex+4]==15))
                                    if (abs(ex-oqx)+abs(ey-oqy)!=4
                                        or int(g[ey,ex])!=15
                                        or not (np.all(g[ey:ey+4,ex:ex+4]==15)
                                                or bottom_ex)):
                                        continue
                                    # A lower-edge escort shadowed by the main
                                    # moves as a simultaneous lateral train.  If
                                    # the exporter were left in place while the
                                    # receiver planned, it would falsely alter
                                    # that receiver's route; clear all three from
                                    # the start frame, then translate together.
                                    mbec=_box(g);mfec=_facing(g,mbec)
                                    main_faces=False
                                    if mbec is not None and mfec in _DIR:
                                        efdx,efdy=_DIR[mfec]
                                        main_faces=(mbec[0]+efdx,mbec[1]+efdy)==(ex,ey)
                                    ldx,ldy=wx-oqx,wy-oqy
                                    edge_train=(mbec is not None and not main_faces
                                                and abs(mbec[0]-ex)+abs(mbec[1]-ey)==4
                                                and oqy==g.shape[0]-8
                                                and (ex,ey)==(oqx,oqy-4)
                                                and abs(ldx)+abs(ldy)==4 and ldy==0)
                                    if edge_train:
                                        hcv=g.copy()
                                        _restore_worker(hcv,wx,wy,12)
                                        _restore_under_block(hcv,oqx,oqy)
                                        _restore_worker(hcv,ex,ey,15)
                                        nwx,nwy=wx+ldx,wy
                                        nqx,nqy=oqx+ldx,oqy
                                        nex,ney=ex+ldx,ey
                                        def edgeok(xx,yy,worker=False):
                                            if not (0<=xx and 0<=yy and xx+4<=g.shape[1] and yy+4<=g.shape[0]):
                                                return False
                                            tile=hcv[yy:yy+4,xx:xx+4]
                                            if np.all((tile==1)|(tile==2)):return True
                                            if worker and _socket_dest(xx,yy):
                                                ent_edge=np.array(ENTRY_GRID,dtype=int)
                                                return np.array_equal(tile,ent_edge[yy:yy+4,xx:xx+4])
                                            return False
                                        if edgeok(nwx,nwy,True) and edgeok(nqx,nqy,True) and edgeok(nex,ney,True):
                                            pat=g[oqy:oqy+4,oqx:oqx+4].copy()
                                            g[:,:]=hcv
                                            g[nqy:nqy+4,nqx:nqx+4]=pat
                                            g[nwy:nwy+4,nwx:nwx+4]=12
                                            g[ney:ney+4,nex:nex+4]=15
                                            follow_next.discard((ex,ey));follow_next.add((nex,ney))
                                            convoy_forced=True
                                            break
                                    trial=g.copy();_companion_action5(trial,worker,allow)
                                    moved_cargo=None
                                    for tdx,tdy in _DIR.values():
                                        if _block_at(trial,oqx+tdx,oqy+tdy,5):
                                            moved_cargo=(oqx+tdx,oqy+tdy);break
                                    if moved_cargo is None:continue
                                    ndx,ndy=moved_cargo[0]-oqx,moved_cargo[1]-oqy
                                    mbf=_box(g);mff=_facing(g,mbf);faced_cargo=False
                                    if mbf is not None and mff in _DIR:
                                        ifdx,ifdy=_DIR[mff]
                                        faced_cargo=moved_cargo==(mbf[0]+ifdx,mbf[1]+ifdy)
                                    if faced_cargo:continue
                                    ftx,fty=ex+ndx,ey+ndy
                                    ht=trial.copy();_restore_worker(ht,ex,ey,15)
                                    mirror_clear=((ftx,fty)==(oqx,oqy) or
                                        (0<=ftx and 0<=fty and ftx+4<=g.shape[1] and fty+4<=g.shape[0]
                                         and np.all((ht[fty:fty+4,ftx:ftx+4]==1)
                                                    |(ht[fty:fty+4,ftx:ftx+4]==2))))
                                    if mirror_clear:continue
                                    if not (0<=ftx and 0<=fty and ftx+4<=g.shape[1] and fty+4<=g.shape[0]):continue
                                    ftile=ht[fty:fty+4,ftx:ftx+4]
                                    if not np.any((ftile==14)|(ftile==0)):continue
                                    pdx,pdy=oqx-ex,oqy-ey
                                    if abs(pdx)+abs(pdy)!=4:continue
                                    hcv=g.copy()
                                    _restore_worker(hcv,wx,wy,12)
                                    _restore_under_block(hcv,oqx,oqy)
                                    _restore_worker(hcv,ex,ey,15)
                                    nwx,nwy=wx+pdx,wy+pdy
                                    nqx,nqy=oqx+pdx,oqy+pdy
                                    nex,ney=ex+pdx,ey+pdy
                                    def cvok(xx,yy,cargo=False):
                                        if xx<0 or yy<0 or xx+4>g.shape[1] or yy+4>g.shape[0]:return False
                                        tile=hcv[yy:yy+4,xx:xx+4]
                                        if np.all((tile==1)|(tile==2)):return True
                                        if yy==g.shape[0]-4 and np.all(tile[:3,:]==1):return True
                                        if cargo and (_transfer_dest(hcv,xx,yy) or _socket_dest(xx,yy)):return True
                                        return False
                                    if not (cvok(nwx,nwy) and cvok(nqx,nqy,True) and cvok(nex,ney)):continue
                                    pat=g[oqy:oqy+4,oqx:oqx+4].copy()
                                    g[:,:]=hcv
                                    g[nqy:nqy+4,nqx:nqx+4]=pat
                                    g[nwy:nwy+4,nwx:nwx+4]=12
                                    g[ney:ney+4,nex:nex+4]=15
                                    follow_next.discard((ex,ey));follow_next.add((nex,ney))
                                    convoy_forced=True
                                    break
                            if not convoy_forced:_companion_action5(g,worker,allow)
                            comp_used=True
                            # A following exporter can occupy the receiver
                            # cargo's just-vacated square on the same tick.  The
                            # unladen pass ran against the start frame, where
                            # that square was still occupied, so mirror the
                            # selected pair's translation here after it vacates
                            # the cargo square.
                            if (CURRENT_LEVEL==7 and wcol_now==12 and pair_key is not None
                                and not np.array_equal(before_pair,g)):
                                oqx,oqy=pair_key[2],pair_key[3]
                                moved_cargo=None
                                for madx,mady in _DIR.values():
                                    tqx,tqy=oqx+madx,oqy+mady
                                    if _block_at(g,tqx,tqy,5):
                                        moved_cargo=(tqx,tqy);break
                                if moved_cargo is not None:
                                    mdx,mtdy=moved_cargo[0]-oqx,moved_cargo[1]-oqy
                                    if abs(mdx)+abs(mtdy)==4:
                                        for ex,ey in list(follow_old):
                                            bottom_worker=(ey==g.shape[0]-4
                                                           and np.all(g[ey:ey+3,ex:ex+4]==15))
                                            if (abs(ex-oqx)+abs(ey-oqy)!=4
                                                or int(g[ey,ex])!=15
                                                or not (np.all(g[ey:ey+4,ex:ex+4]==15)
                                                        or bottom_worker)):
                                                continue
                                            tx,ty=ex+mdx,ey+mtdy
                                            if (tx,ty)!=(oqx,oqy):continue
                                            hf=g.copy();_restore_worker(hf,ex,ey,15)
                                            if (0<=tx and 0<=ty and tx+4<=g.shape[1] and ty+4<=g.shape[0]
                                                and np.all((hf[ty:ty+4,tx:tx+4]==1)
                                                           |(hf[ty:ty+4,tx:tx+4]==2))):
                                                g[:,:]=hf;g[ty:ty+4,tx:tx+4]=15
                                                follow_next.discard((ex,ey))
                                                follow_next.add((tx,ty))
                            if sidecars and not np.array_equal(before_pair,g):
                                # Locate the moved selected worker by its rim5
                                # partner, then translate every still-unmoved
                                # adjacent sidecar by the same vector.
                                neww=None
                                for aa,(adx,ady) in ((0,(0,0)),)+tuple(_DIR.items()):
                                    nxw,nyw=wx+adx,wy+ady
                                    if (0<=nxw and 0<=nyw and nxw+4<=g.shape[1] and nyw+4<=g.shape[0]
                                        and np.all(g[nyw:nyw+4,nxw:nxw+4]==12)
                                        and any(_block_at(g,nxw+bdx,nyw+bdy,5) for bdx,bdy in _DIR.values())):
                                        neww=(nxw,nyw);break
                                if neww is not None:
                                    mdx,mdy=neww[0]-wx,neww[1]-wy
                                    for fx,fy in sidecars:
                                        # A sidecar mirrors motion along the
                                        # convoy axis (perpendicular to their
                                        # separation).  When the selected pair
                                        # turns away laterally, the sidecar stays
                                        # put and the merged bar separates.
                                        if mdx*(fx-wx)+mdy*(fy-wy)!=0:continue
                                        if not np.all(g[fy:fy+4,fx:fx+4]==12):continue
                                        tx,ty=fx+mdx,fy+mdy
                                        hside=g.copy();_restore_worker(hside,fx,fy,12)
                                        if 0<=tx and 0<=ty and tx+4<=g.shape[1] and ty+4<=g.shape[0]:
                                            tile=hside[ty:ty+4,tx:tx+4]
                                            clear=np.all((tile==1)|(tile==2))
                                            if not clear and _socket_dest(tx,ty):
                                                ent1=np.array(ENTRY_GRID,dtype=int)
                                                clear=np.array_equal(tile,ent1[ty:ty+4,tx:tx+4])
                                            if clear:
                                                g[:,:]=hside;g[ty:ty+4,tx:tx+4]=12
                        if CURRENT_LEVEL==7 and pair_key is not None and int(before_pair[wy,wx])==15:
                            if np.array_equal(before_pair,g):st["export_wait"].add(pair_key)
                            else:st["export_wait"].discard(pair_key)
                if CURRENT_LEVEL==7:
                    # Resolution is left-to-right.  An earlier worker can take
                    # and translate a shared adjacent rim5 cargo away from a
                    # later selected worker.  When that later worker's turn
                    # arrives it is now unladen and immediately takes its
                    # ordinary autonomous step in the same tick.
                    for cx,cy,qx,qy in selected:
                        parked_escape=((cx,cy) in parked_workers and int(g[cy,cx])==15
                                       and not _block_at(g,qx,qy)
                                       and not any(_block_at(g,cx+dx,cy+dy,5) for dx,dy in _DIR.values()))
                        if (cx,cy) in parked_workers and not parked_escape:continue
                        if int(g[cy,cx]) not in (12,15) or not np.all(g[cy:cy+4,cx:cx+4]==int(g[cy,cx])):continue
                        if any(_block_at(g,cx+dx,cy+dy,5) for dx,dy in _DIR.values()):continue
                        lost_export=(int(g[cy,cx])==15)
                        if not fast_new and int(g[cy,cx]) in new_collision_colors and not lost_export:continue
                        forced_lost=selected_auto.get((cx,cy))
                        # A receiver which loses shared cargo to an exporter
                        # peels away on the side opposite that exporter.  This
                        # handoff direction is geometric and does not retarget to
                        # other cargo released elsewhere earlier in the tick.
                        if int(g[cy,cx])==12:
                            for ex,ey,eqx,eqy in selected:
                                if ((eqx,eqy)==(qx,qy)
                                    and selected_cols.get((ex,ey))==15
                                    and (ex,ey) not in pin_old):
                                    av=(qx-ex,qy-ey)
                                    for aa,vv in _DIR.items():
                                        if vv==av:forced_lost=aa;break
                                    break
                        # If another worker translates a shared cargo away, the
                        # now-unladen exporter advances into that cargo's freshly
                        # vacated square rather than following its stale route.
                        if int(g[cy,cx])==15:
                            for fa,(fdx,fdy) in _DIR.items():
                                if (qx-cx,qy-cy)==(fdx,fdy):
                                    forced_lost=fa;break
                        _move_companion(g,ca,st["turn"],set(),st.get("lane_started",0),(cx,cy),forced_lost)
            if CURRENT_LEVEL==7:
                st["export_follow"]=follow_next
                st["export_pin"]=pin_next
        else:
            comp_used=_companion_action5(g)
            if not comp_used:
                parked_any=_move_companion(g,ca,st["turn"],False)
        if CURRENT_LEVEL==7:
            # If selected cargo transports into the cell directly faced by the
            # main, the main intercepts it after worker resolution: ownership
            # is broken and rim5 becomes a released rim3 block.
            mb=_box(g);mf=_facing(g,mb)
            if mb is not None and mf in _DIR:
                mx,my=mb[0],mb[1];dx,dy=_DIR[mf];ix,iy=mx+dx,my+dy
                if _block_at(g,ix,iy,5):
                    g[iy,ix:ix+4]=3;g[iy+3,ix:ix+4]=3
                    g[iy+1:iy+3,ix]=3;g[iy+1:iy+3,ix+3]=3
        # Re-test a collided exporter after all simultaneous traffic.  Capture
        # occurs exactly when it failed to vacate the probed square this tick.
        if capture_probe is not None:
            cx,cy=capture_probe
            if np.all(g[cy:cy+4,cx:cx+4]==15):
                g[cy,cx:cx+4]=11;g[cy+3,cx:cx+4]=11
                g[cy+1:cy+3,cx]=11;g[cy+1:cy+3,cx+3]=11
                for wx,wy in _DIR.values():
                    bx,by=cx+wx,cy+wy
                    if _block_at(g,bx,by,5) and _cargo_dest(15,bx,by):
                        g[by,bx:bx+4]=4;g[by+3,bx:bx+4]=4
                        g[by+1:by+3,bx]=4;g[by+1:by+3,bx+3]=4
        if parked_any:
            st["comp_post"]=True
            st["comp_active"]=False
            if _complete(g):
                if CURRENT_LEVEL is not None and CURRENT_LEVEL>=8:info["win"]=True
                else:info["level_up"]=True
        if action==5 and comp_used:st["comp_active"]=True
        st["turn"]+=1
        _budget(g,st["turn"])
        # Timed boards are lethal as soon as their meter fills,
        # unless the same tick has already completed the level.
        if ((CURRENT_LEVEL==4 and st["turn"]>=125)
            or (CURRENT_LEVEL==7 and st["turn"]>=150)
            or (CURRENT_LEVEL==8 and st["turn"]>=70)) and not info["level_up"]:
            info["dead"]=True
    return g.tolist(),info,st

def is_goal(state,grid):
    return _complete(np.array(grid,dtype=int))
