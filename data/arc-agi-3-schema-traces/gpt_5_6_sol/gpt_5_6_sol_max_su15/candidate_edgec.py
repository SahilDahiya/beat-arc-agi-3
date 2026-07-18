# World model for ARC3 game su15
# numpy is preloaded as np in the restricted model sandbox.

def _components(a,value,y_stop=None):
    h,w=a.shape
    if y_stop is None: y_stop=h
    seen=set(); ans=[]
    for yy in range(y_stop):
        for xx in range(w):
            if int(a[yy,xx])!=value or (xx,yy) in seen: continue
            q=[(xx,yy)]; seen.add((xx,yy)); pts=[]
            while q:
                px,py=q.pop(); pts.append((px,py))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=px+dx,py+dy
                    if 0<=nx<w and 0<=ny<y_stop and int(a[ny,nx])==value and (nx,ny) not in seen:
                        seen.add((nx,ny)); q.append((nx,ny))
            ans.append(pts)
    return ans


def _components8(a,value,y_stop=None):
    # Diagonal-outline sprites are connected only under 8-neighbourhood.
    h,w=a.shape
    if y_stop is None: y_stop=h
    seen=set(); ans=[]
    for yy in range(y_stop):
        for xx in range(w):
            if int(a[yy,xx])!=value or (xx,yy) in seen: continue
            q=[(xx,yy)]; seen.add((xx,yy)); pts=[]
            while q:
                px,py=q.pop(); pts.append((px,py))
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        if dx==0 and dy==0: continue
                        nx,ny=px+dx,py+dy
                        if (0<=nx<w and 0<=ny<y_stop and
                            int(a[ny,nx])==value and (nx,ny) not in seen):
                            seen.add((nx,ny)); q.append((nx,ny))
            ans.append(pts)
    return ans


def _row_modes(a):
    ans=[]
    for yy in range(a.shape[0]):
        vals,cnt=np.unique(a[yy],return_counts=True)
        ans.append(int(vals[int(np.argmax(cnt))]))
    return ans


def _split_and_bg(a):
    modes=_row_modes(a); header=modes[0]; split=0
    for yy in range(a.shape[0]):
        if modes[yy]!=header:
            split=yy; break
    if split==0: split=min(10,a.shape[0]-1)
    return split,modes[split]


def _toolbar_stages(a,split):
    # Ordered 2x2 swatches in the informational header encode merge ranks.
    found=[]
    for value in range(16):
        for pts in _components(a,value):
            if len(pts)!=4 or max(y for x,y in pts)>=split: continue
            xs=[x for x,y in pts]; ys=[y for x,y in pts]
            if max(xs)-min(xs)==1 and max(ys)-min(ys)==1:
                found.append((min(xs),value))
    found.sort()
    return tuple(value for xx,value in found)


def _compute_features(entry):
    a=np.array(entry,dtype=int); h,w=a.shape
    split,bg=_split_and_bg(a)
    stages=_toolbar_stages(a,split)

    # Merge levels have a four-rank HUD and singleton/square pieces in the field.
    if len(stages)>=2:
        initial=[]; initial_cells=[]
        # Side length normally rises 1,2,3,4...; extended boards can show a
        # larger solid square, whose entry geometry defines that rank's side.
        sides=[rank+1 for rank in range(len(stages))]
        field_parts=[]
        for rank,value in enumerate(stages):
            parts=[]
            for pts in _components(a,value,h-1):
                if min(y for x,y in pts)<split: continue
                xs=[x for x,y in pts]; ys=[y for x,y in pts]
                ww=max(xs)-min(xs)+1; hh=max(ys)-min(ys)+1
                if ww==hh and len(pts)==ww*hh: sides[rank]=ww
                parts.append(pts)
            field_parts.append(parts)
        for rank,parts in enumerate(field_parts):
            side=sides[rank]
            for pts in parts:
                xs=[x for x,y in pts]; ys=[y for x,y in pts]
                # Piece anchor is the click-coordinate: top-left + floor(side/2).
                ax=min(xs)+side//2; ay=min(ys)+side//2
                initial.append((rank,ax,ay))
                initial_cells.extend(pts)
        # Large square previews to the right of the swatches list the
        # requested output ranks, left-to-right.
        shown=[]
        for rank,value in enumerate(stages):
            side=sides[rank]
            for pts in _components(a,value):
                if max(y for x,y in pts)>=split: continue
                xs=[x for x,y in pts]; ys=[y for x,y in pts]
                if min(xs)<16: continue
                if len(pts)==side*side and max(xs)-min(xs)==side-1 and max(ys)-min(ys)==side-1:
                    shown.append((min(xs),rank))
        shown.sort()
        targets=tuple(rank for xx,rank in shown)
        if not targets: targets=(len(stages)-1,)

        disks=[]
        for pts in _components(a,9,h-1):
            if min(y for x,y in pts)>=split:
                cx=sum(x for x,y in pts)/len(pts)
                disks.append((cx,tuple(pts)))
        disks.sort()

        # Some later boards add an orange falling timer glyph.  It advances
        # downward by one whole glyph-height after every field click.
        falling=[]; chaser_target=False
        # Each outline glyph is an 8-connected sprite (its diagonals are not
        # 4-connected); later boards can contain several independent pursuers.
        # A matching large glyph in the HUD is an additional requested output.
        for pts in _components8(a,7,h-1):
            if max(yy for xx,yy in pts)<split:
                if len(pts)>4: chaser_target=True
                continue
            if min(yy for xx,yy in pts)<split: continue
            height=max(yy for xx,yy in pts)-min(yy for xx,yy in pts)+1
            falling.append((7,tuple(pts),height))
        falling.sort(key=lambda z:min(xx for xx,yy in z[1]))
        return {"mode":"merge","split":split,"bg":bg,"stages":stages,
                "sides":tuple(sides),
                "initial":tuple(sorted(initial)),"initial_cells":tuple(initial_cells),
                "disks":tuple(pts for cx,pts in disks),"targets":targets,
                "falling":tuple(falling),"chaser_target":chaser_target,
                # The single-pursuer four-rank challenge slows the clock;
                # extended-rank boards retain the ordinary output stride.
                "meter_den":(2 if len(stages)>4 else
                    len(targets)+1+
                    (1 if len(falling)==1 and len(stages)==4 else 0)),
                "range":6}

    # Runner/tutorial levels contain one 3x3 white movable piece below the HUD.
    whites=_components(a,15)
    candidates=[p for p in whites if max(y for x,y in p)>=split]
    if candidates:
        movable=max(candidates,key=len)
        sx=int(round(sum(x for x,y in movable)/len(movable)))
        sy=int(round(sum(y for x,y in movable)/len(movable)))
        bg=_row_modes(a)[min(max(split,sy),h-2)]
        crosses=[]
        for pts in _components(a,0,h-1):
            cx=int(round(sum(x for x,y in pts)/len(pts)))
            cy=int(round(sum(y for x,y in pts)/len(pts)))
            crosses.append((cx,cy,tuple(pts)))
        target=None
        for yy in range(1,h-1):
            for xx in range(1,w-1):
                if bool(np.all(a[yy-1:yy+2,xx-1:xx+2]==3)):
                    target=(xx,yy); break
            if target is not None: break
        move_range=6
        if crosses:
            ds=[max(abs(cx-sx),abs(cy-sy)) for cx,cy,pts in crosses]
            positive=[d for d in ds if d>0]
            if positive: move_range=min(positive)
        return {"mode":"runner","split":split,"bg":bg,"movable":tuple(movable),
                "start":(sx,sy),"crosses":tuple(crosses),"target":target,
                "range":move_range}

    return {"mode":"unknown","split":split,"bg":bg}


_FEATURE_CACHE={}
def _features(entry):
    # ENTRY_GRID is fixed for each level (including RESET), and CURRENT_LEVEL
    # is swapped with it during backtest.  Cache the expensive visual parse.
    # A level-up transition may be tagged with the destination level while
    # still receiving the source ENTRY_GRID, so include layout content too.
    key=(CURRENT_LEVEL,np.array(entry,dtype=np.uint8).tobytes())
    if key not in _FEATURE_CACHE:
        _FEATURE_CACHE[key]=_compute_features(entry)
    return _FEATURE_CACHE[key]


def _meter(grid,bg,step=2):
    a=np.array(grid,dtype=int); h,w=a.shape; trail=0
    for xx in range(w-1,-1,-1):
        if int(a[h-1,xx])==bg: trail+=1
        else: break
    return trail//step


# ---------- runner mechanism ----------

def _observe_runner(grid,f):
    a=np.array(grid,dtype=int)
    whites=_components(a,15)
    cand=[p for p in whites if max(y for x,y in p)>=f["split"]]
    if cand:
        p=max(cand,key=len)
        pos=(int(round(sum(x for x,y in p)/len(p))),
             int(round(sum(y for x,y in p)/len(p))))
    else: pos=f["start"]
    collected=set()
    for i,(cx,cy,pts) in enumerate(f["crosses"]):
        if abs(pos[0]-cx)<=1 and abs(pos[1]-cy)<=1: collected.add(i)
        elif int(a[cy,cx])==3 and all((xx==cx and yy==cy) or int(a[yy,xx])==f["bg"] for xx,yy in pts):
            collected.add(i)
    return pos,tuple(sorted(collected)),_meter(grid,f["bg"])


def _render_runner(records):
    f=_features(ENTRY_GRID); out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape
    for xx,yy in f["movable"]: out[yy,xx]=f["bg"]
    pos,collected=records[-1]
    for i in collected:
        ccx,ccy,pts=f["crosses"][i]
        for xx,yy in pts: out[yy,xx]=f["bg"]
        out[ccy,ccx]=3
    cx,cy=pos
    for yy in range(cy-1,cy+2):
        for xx in range(cx-1,cx+2):
            if 0<=xx<w and 0<=yy<h: out[yy,xx]=15
    nfill=min(w,2*(len(records)-1))
    if nfill: out[h-1,w-nfill:w]=f["bg"]
    return out.tolist()


# ---------- equal-piece merge mechanism ----------

def _side(f,rank):
    return f.get("sides",tuple(k+1 for k in range(len(f["stages"]))))[rank]


def _observe_merge(grid,f):
    a=np.array(grid,dtype=int); h,w=a.shape; objects=[]
    for rank,value in enumerate(f["stages"]):
        side=_side(f,rank)
        for pts in _components(a,value,h-1):
            if min(y for x,y in pts)<f["split"]: continue
            xs=[x for x,y in pts]; ys=[y for x,y in pts]
            objects.append((rank,min(xs)+side//2,min(ys)+side//2))
    trail=_meter(grid,f["bg"],1)
    clicks=(trail*f["meter_den"]+3)//4
    return tuple(sorted(objects)),clicks


def _observe_chasers(grid,f):
    # Orange outline cells form one translated sprite (diagonal cells make it
    # disconnected, so compare whole-colour bounding boxes).
    if not f.get("falling"): return tuple()
    a=np.array(grid,dtype=int); h,w=a.shape; ans=[]
    groups=[p for p in _components8(a,7,h-1)
            if min(yy for xx,yy in p)>=f["split"]]
    groups.sort(key=lambda p:min(xx for xx,yy in p))
    for i,(value,base,stride) in enumerate(f["falling"]):
        now=groups[i] if i<len(groups) else []
        if len(now)==len(base):
            ans.append((min(xx for xx,yy in now)-min(xx for xx,yy in base),
                        min(yy for xx,yy in now)-min(yy for xx,yy in base)))
        else:
            # A square drawn later may occlude most/all of a pursuer; retain
            # its threaded hidden offset rather than fabricating one.
            ans.append(None)
    return tuple(ans)


def _object_center(obj,f):
    # Pursuers home on the object's click anchor.  For odd squares this is
    # the geometric centre; for even squares it is the lower/right centre
    # cell, which resolves close half-cell approaches toward the anchor.
    rank,cx,cy=obj
    return (float(cx),float(cy))


def _advance_chasers(offsets,objects,f,click=None):
    # Each orange pursuer targets the nearest movable square AFTER the click's
    # merge, moving independently by at most one sprite-height on each axis.
    if not f.get("falling"): return tuple()
    ans=[]
    for i,(value,pts,stride) in enumerate(f["falling"]):
        old=offsets[i] if i<len(offsets) else (0,0)
        ox,oy=(0,0) if old is None else old
        hx=(min(xx for xx,yy in pts)+max(xx for xx,yy in pts))/2.0+ox
        hy=(min(yy for xx,yy in pts)+max(yy for xx,yy in pts))/2.0+oy

        # The eight outline cells are also an eight-way directional pad.
        # Clicking one directly dashes the sprite three body-lengths in that
        # cell's compass direction, replacing autonomous pursuit for this tick.
        if click is not None:
            qx,qy=click
            occupied={(px+ox,py+oy) for px,py in pts}
            if (qx,qy) in occupied:
                cx=min(px for px,py in pts)+stride//2+ox
                cy=min(py for px,py in pts)+stride//2+oy
                dx=1 if qx>cx else -1 if qx<cx else 0
                dy=1 if qy>cy else -1 if qy<cy else 0
                # Cardinal buttons dash 12 cells; diagonal buttons dash
                # 8 per axis (for the observed height/stride four sprite).
                jump=(2 if dx and dy else 3)*stride
                ox+=dx*jump; oy+=dy*jump
                ans.append((ox,oy))
                continue
        if objects:
            hx0=min(xx for xx,yy in pts)+ox; hx1=max(xx for xx,yy in pts)+ox
            hy0=min(yy for xx,yy in pts)+oy; hy1=max(yy for xx,yy in pts)+oy
            def edge_distance(o):
                rank,cx,cy=o; side=_side(f,rank)
                x0=cx-side//2; x1=x0+side-1
                y0=cy-side//2; y1=y0+side-1
                dx=hx0-x1 if x1<hx0 else x0-hx1 if x0>hx1 else 0
                dy=hy0-y1 if y1<hy0 else y0-hy1 if y0>hy1 else 0
                return dx*dx+dy*dy
            target=min(objects,key=edge_distance)
            tx,ty=_object_center(target,f)
            # A remote rigid c is approached via its nearest occupied point.
            # Once a centre-directed stride would reach an adjacent/overlap
            # contact, the pursuer aims through its centre and the collision
            # resolver below handles the hit/tunnel.
            if target[0] == 4:
                rank,cx,cy=target; side=_side(f,rank)
                x0=cx-side//2; x1=x0+side-1
                y0=cy-side//2; y1=y0+side-1
                def capped(d):
                    if d>stride: return stride
                    if d<-stride: return -stride
                    return int(np.floor(d))
                mx=capped(tx-hx); my=capped(ty-hy)
                ax0=hx0+mx; ax1=hx1+mx
                ay0=hy0+my; ay1=hy1+my
                reaches=(ax0<=x1+1 and ax1>=x0-1 and
                         ay0<=y1+1 and ay1>=y0-1)
                if not reaches:
                    # On a separated axis aim at the nearest face; on an
                    # already-overlapping axis continue toward c's centre.
                    if hx<x0: tx=x0
                    elif hx>x1: tx=x1
                    if hy<y0: ty=y0
                    elif hy>y1: ty=y1
            def toward(d):
                if d>stride: return stride
                if d<-stride: return -stride
                return int(np.floor(d))
            ox+=toward(tx-hx); oy+=toward(ty-hy)
        ans.append((ox,oy))
    return tuple(ans)


def _resolve_chaser_hits(old_objects,objects,old_offsets,new_offsets,x,y,f):
    """Two-phase interaction between a pursuer and an oversized (c/8) block.

    On first edge contact the pursuer tunnels eight cells through the block,
    leaving the block intact and overlapping it.  On the following click an
    already-overlapping pursuer bites one rank off: the moved block continues
    by old-side-1 and the pursuer follows one cell in the same direction.
    """
    if not f.get("falling") or not objects:
        return objects,new_offsets
    out=list(objects); hz=list(new_offsets)

    def bounds(obj):
        rank,cx,cy=obj; side=_side(f,rank)
        x0=cx-side//2; y0=cy-side//2
        return x0,x0+side-1,y0,y0+side-1

    def overlaps(obj,pts,off):
        x0,x1,y0,y1=bounds(obj); ox,oy=off
        return any(x0<=px+ox<=x1 and y0<=py+oy<=y1 for px,py in pts)

    def sgn(v):
        return 1 if v>0 else -1 if v<0 else 0

    for i,(value,pts,stride) in enumerate(f["falling"]):
        oldoff=old_offsets[i] if i<len(old_offsets) else (0,0)
        if oldoff is None: oldoff=(0,0)

        # Direct D-pad dashes are normally player-controlled phasing moves.
        # If an even b already covers one outline cell and is moved on that
        # same tick, however, its old contact also ejects the dashing sprite:
        # two strides on the dominant block axis, one on the other.
        direct=(x,y) in {(px+oldoff[0],py+oldoff[1]) for px,py in pts}
        if direct:
            shallow=[]
            for o in old_objects:
                if o[0]!=3: continue
                x0,x1,y0,y1=bounds(o)
                covered=sum(x0<=px+oldoff[0]<=x1 and
                            y0<=py+oldoff[1]<=y1 for px,py in pts)
                if covered==1: shallow.append(o)
            if shallow:
                source=shallow[0]
                candidates=[o for o in out if o[0]==source[0]]
                if candidates:
                    hit=min(candidates,
                            key=lambda o:(o[1]-source[1])**2+
                                         (o[2]-source[2])**2)
                    mdx=hit[1]-source[1]; mdy=hit[2]-source[2]
                    if mdx or mdy:
                        nox,noy=hz[i]
                        if abs(mdy)>=abs(mdx):
                            hz[i]=(nox+sgn(mdx)*stride,
                                   noy+sgn(mdy)*2*stride)
                        else:
                            hz[i]=(nox+sgn(mdx)*2*stride,
                                   noy+sgn(mdy)*stride)
            continue

        # Exactly one exposed outline cell distinguishes a deep 7/8 hit.
        # The anomalous maximum 8/side7 sheds a rank; the lower c/side5 is
        # rigid and instead rebounds the embedded pursuer away from its core.
        covered_old=[]; six_high=[]; full_high=[]
        for o in old_objects:
            if o[0]<4: continue
            x0,x1,y0,y1=bounds(o)
            covered=sum(x0<=px+oldoff[0]<=x1 and
                        y0<=py+oldoff[1]<=y1 for px,py in pts)
            if covered==len(pts)-1: covered_old.append(o)
            if covered==len(pts)-2 and o[0]>=5: six_high.append(o)
            if covered==len(pts) and o[0]>=5: full_high.append(o)

        # With two exposed compass cells, moving rank8 shears one rank.
        # The fragment is expelled across the horizontal face and one cell
        # across the vertical face; the sprite follows the block by one.
        if six_high:
            source=six_high[0]
            candidates=[o for o in out if o[0]==source[0]]
            if candidates:
                hit=min(candidates,key=lambda o:(o[1]-x)**2+(o[2]-y)**2)
                sx=sgn(hit[1]-source[1]); sy=sgn(hit[2]-source[2])
                pax=min(px for px,py in pts)+stride//2+oldoff[0]
                pay=min(py for px,py in pts)+stride//2+oldoff[1]
                dx=source[1]-pax; dy=source[2]-pay
                side=_side(f,hit[0])
                out.remove(hit)
                out.append((hit[0]-1,
                            hit[1]+sgn(dx)*side,
                            hit[2]+sgn(dy)))
                hz[i]=(oldoff[0]+sx,oldoff[1]+sy)
                continue

        # A completely engulfed sprite cannot bite the loose rank8.  Moving
        # the block ejects it along the block's dominant displacement axis:
        # 3 strides on that axis and 2 on the other.
        if full_high:
            source=full_high[0]
            candidates=[o for o in out if o[0]==source[0]]
            hit=(min(candidates,key=lambda o:(o[1]-x)**2+(o[2]-y)**2)
                 if candidates else source)
            mdx=hit[1]-source[1]; mdy=hit[2]-source[2]
            if mdx==0: mdx=x-source[1]
            if mdy==0: mdy=y-source[2]
            if abs(mdx)>=abs(mdy):
                hz[i]=(oldoff[0]+sgn(mdx)*3*stride,
                       oldoff[1]+sgn(mdy)*2*stride)
            else:
                hz[i]=(oldoff[0]+sgn(mdx)*2*stride,
                       oldoff[1]+sgn(mdy)*3*stride)
            continue

        rigid=[o for o in covered_old if o[0]==4]
        if rigid:
            source=rigid[0]
            candidates=[o for o in out if o[0]==source[0]]
            hit=(min(candidates,key=lambda o:(o[1]-x)**2+(o[2]-y)**2)
                 if candidates else source)
            mdx=hit[1]-source[1]; mdy=hit[2]-source[2]
            if mdx or mdy:
                # A deeply latched rigid c ejects the sprite with the moving
                # block: 3 strides on its dominant axis, 2 on the other.
                if abs(mdx)>=abs(mdy):
                    hz[i]=(oldoff[0]+sgn(mdx)*3*stride,
                           oldoff[1]+sgn(mdy)*2*stride)
                else:
                    hz[i]=(oldoff[0]+sgn(mdx)*2*stride,
                           oldoff[1]+sgn(mdy)*3*stride)
            else:
                # A stationary c lets autonomous pursuit close the final
                # exposed cell.  That completed 7→8 latch shears c to b,
                # ejecting the smaller fragment two old sides upward while
                # retaining the just-computed one-cell pursuit motion.
                side=_side(f,source[0])
                if hit in out: out.remove(hit)
                out.append((source[0]-1,source[1],source[2]-2*side))
            continue
        old_high=[o for o in covered_old if o[0]>=5]
        if old_high:
            source=old_high[0]
            candidates=[o for o in out if o[0]==source[0]]
            if candidates:
                hit=min(candidates,key=lambda o:(o[1]-x)**2+(o[2]-y)**2)
                sx=sgn(hit[1]-source[1]); sy=sgn(hit[2]-source[2])
                # If the square did not move, the click still supplies the
                # intended ejection direction.
                if sx==0: sx=sgn(x-source[1])
                if sy==0: sy=sgn(y-source[2])
                out.remove(hit)
                if hit[0]>0:
                    side=_side(f,hit[0])
                    out.append((hit[0]-1,hit[1]+sx*(side-1),
                                hit[2]+sy*(side-1)))
                hz[i]=(oldoff[0]+sx,oldoff[1]+sy)
                continue

        # Phase one: after ordinary pursuit, exact edge contact with an
        # oversized block tunnels the sprite 2*stride through that edge.
        if i>=len(hz): continue
        nox,noy=hz[i]
        sx0=min(px for px,py in pts)+nox
        sx1=max(px for px,py in pts)+nox
        sy0=min(py for px,py in pts)+noy
        sy1=max(py for px,py in pts)+noy
        for hit in [o for o in out if o[0]>=3]:
            x0,x1,y0,y1=bounds(hit)
            source_candidates=[o for o in old_objects if o[0]==hit[0]]
            source=(min(source_candidates,
                        key=lambda o:(o[1]-hit[1])**2+(o[2]-hit[2])**2)
                    if source_candidates else hit)
            mdx=hit[1]-source[1]; mdy=hit[2]-source[2]

            # Even-sided b has an off-centre click anchor.  Its collision halo
            # therefore catches a pursuer with one blank raster row/column
            # still visible.  The pursuer tunnels two strides through the
            # contacted face and one stride toward the anchor on the other axis.
            if hit[0]==3 and not overlaps(hit,pts,(nox,noy)):
                hx=(sx0+sx1)/2.0; hy=(sy0+sy1)/2.0
                ax=sgn(hit[1]-hx); ay=sgn(hit[2]-hy)
                if (not (sx1<x0 or sx0>x1) and
                        ((sy0>y1 and sy0-y1<=2) or
                         (sy1<y0 and y0-sy1<=2))):
                    hz[i]=(nox+ax*stride,noy+ay*2*stride)
                    break
                if (not (sy1<y0 or sy0>y1) and
                        ((sx0>x1 and sx0-x1<=2) or
                         (sx1<x0 and x0-sx1<=2))):
                    hz[i]=(nox+ax*2*stride,noy+ay*stride)
                    break
            if overlaps(hit,pts,(nox,noy)):
                mx=nox-oldoff[0]; my=noy-oldoff[1]
                covered=sum(x0<=px+nox<=x1 and y0<=py+noy<=y1
                            for px,py in pts)
                # A stationary rigid c is cut by the same clean upward
                # one-button strike: its b fragment exits two old sides above,
                # and an exactly centred impact deflects the pursuer right.
                if (hit[0]==4 and covered==1 and my<0 and
                        mdx==0 and mdy==0):
                    side=_side(f,hit[0])
                    out.remove(hit)
                    out.append((hit[0]-1,hit[1],hit[2]-2*side))
                    hz[i]=(nox,noy)
                # The asymmetric sprite's first upward penetration exposes only
                # its north button.  A loose maximum-rank block shears on this
                # clean below-face strike: the smaller fragment is knocked
                # through the opposite face while the pursuer stays at impact.
                elif hit[0]>=5 and covered==1 and my<0:
                    side=_side(f,hit[0])
                    hx=(sx0+sx1)/2.0
                    kx=sgn(hit[1]-hx)
                    if kx==0: kx=-1
                    out.remove(hit)
                    out.append((hit[0]-1,hit[1]+kx,
                                hit[2]-(side+stride)))
                    hz[i]=(nox,noy)
                # Six-cell penetration of loose rank8 settles one more stride
                # along each pursuit axis, producing the observed 7/8 latch
                # that will bite on the following non-direct tick.
                elif hit[0]>=5 and covered==len(pts)-2:
                    hz[i]=(nox+sgn(mx)*stride,noy+sgn(my)*stride)
                # Other penetrations continue through on the dominant axis.
                elif abs(my)>=abs(mx) and my!=0:
                    hz[i]=(nox+sgn(mx)*(stride+1),
                           noy+sgn(my)*2*stride)
                elif mx!=0:
                    hz[i]=(nox+sgn(mx)*2*stride,
                           noy+sgn(my)*(stride+1))
                break
            hleft=(x0-sx1 if sx1<x0 else 0)
            hright=(sx0-x1 if sx0>x1 else 0)
            contact_left=(hleft==1 or (hit[0]==4 and hleft==2))
            contact_right=(hright==1 or (hit[0]==4 and hright==2))

            # A clean landing immediately above the loose maximum-rank
            # side7/8 block chips it to c.  The lower side5/c is rigid and
            # tunnels the pursuer instead.  The fragment is knocked away from
            # the pursuer's centre while the pursuer rebounds.
            if (hit[0]>=5 and sy1<y0 and y0-sy1==1 and
                    not (sx1<x0 or sx0>x1)):
                hx=(sx0+sx1)/2.0
                kx=sgn(hit[1]-hx)
                if kx==0: kx=sgn(mdx)
                side=_side(f,hit[0])
                out.remove(hit)
                out.append((hit[0]-1,hit[1]+kx*(side-1),hit[2]-1))
                hz[i]=(nox-kx*(stride-1),noy-(stride-1))
                break

            # The loose side7/8 block only catches an adjacent pursuer while
            # held stationary; moving it merely relocates beside the sprite.
            # Rigid side5/c retains its wider collision response while moved.
            edge_active=(hit[0]!=5 or (mdx==0 and mdy==0))
            if edge_active and contact_left and not (sy1<y0 or sy0>y1):
                hz[i]=(nox+2*stride,noy-sgn(mdy)); break
            if edge_active and contact_right and not (sy1<y0 or sy0>y1):
                hz[i]=(nox-2*stride,noy-sgn(mdy)); break
            if edge_active and sy1<y0 and y0-sy1==1 and not (sx1<x0 or sx0>x1):
                # Rigid c transfers a full stride of the block's lateral
                # motion into the vertical tunnel; loose rank8 transfers one.
                comp=stride if hit[0]==4 else 1
                hz[i]=(nox-sgn(mdx)*comp,noy+2*stride); break
            if edge_active and sy0>y1 and sy0-y1==1 and not (sx1<x0 or sx0>x1):
                # A below-face impact on rigid c tunnels straight upward; its
                # asymmetric top-face response alone inherits lateral motion.
                comp=0 if hit[0]==4 else 1
                hz[i]=(nox-sgn(mdx)*comp,noy-2*stride); break

    # Pursuers are rigid sprites confined to the playable field.  Collision
    # tunnels that would overshoot are clamped against the left/right walls,
    # the HUD boundary, and the meter row (observed at L5's top-left corner).
    h,w=np.array(ENTRY_GRID).shape
    for i,(value,pts,stride) in enumerate(f["falling"]):
        ox,oy=hz[i]
        ox=max(-min(px for px,py in pts),
               min(ox,(w-1)-max(px for px,py in pts)))
        oy=max(f["split"]-min(py for px,py in pts),
               min(oy,(h-2)-max(py for px,py in pts)))
        hz[i]=(ox,oy)
    return tuple(sorted(out)),tuple(hz)


def _render_merge(records,hazards=None,clicks=None):
    f=_features(ENTRY_GRID); out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape
    for xx,yy in f["initial_cells"]: out[yy,xx]=f["bg"]
    # Undo restores geometry but does not refund the click meter, so elapsed
    # clicks are state independent of the undo stack depth.
    if clicks is None: clicks=len(records)-1
    if hazards is None: hazards=[tuple((0,0) for z in f.get("falling",()))]
    offsets=hazards[-1]
    for i,(value,pts,stride) in enumerate(f.get("falling",())):
        for xx,yy in pts: out[yy,xx]=f["bg"]
        sx,sy=offsets[i] if i<len(offsets) else (0,0)
        for xx,yy in pts:
            nx=xx+sx; ny=yy+sy
            if 0<=nx<w and 0<=ny<h-1: out[ny,nx]=value
    objects=records[-1]
    for rank,cx,cy in objects:
        side=_side(f,rank); color=f["stages"][rank]
        x0=cx-side//2; y0=cy-side//2
        for yy in range(y0,y0+side):
            for xx in range(x0,x0+side):
                if 0<=xx<w and 0<=yy<h: out[yy,xx]=color
    nfill=min(w,(4*clicks)//f["meter_den"])
    if nfill: out[h-1,w-nfill:w]=f["bg"]
    return out.tolist()


def _merge_click(objects,x,y,f):
    near=[]; far=[]
    for obj in objects:
        rank,ox,oy=obj
        # Universal click radius: an object is attracted when the
        # click is within Euclidean distance 8 of ANY cell of its square.
        # Larger squares therefore have a larger effective anchor reach.
        side=_side(f,rank)
        x0=ox-side//2; x1=x0+side-1
        y0=oy-side//2; y1=y0+side-1
        dx=(x0-x if x<x0 else (x-x1 if x>x1 else 0))
        dy=(y0-y if y<y0 else (y-y1 if y>y1 else 0))
        if dx*dx+dy*dy<=64: near.append(obj)
        else: far.append(obj)
    if not near: return tuple(sorted(objects))

    counts=[0 for _ in f["stages"]]
    for rank,ox,oy in near: counts[rank]+=1
    placed=[]
    for rank in range(len(counts)):
        if counts[rank]%2: placed.append((rank,x,y))
        if rank+1<len(counts): counts[rank+1]+=counts[rank]//2
        elif counts[rank]//2:
            # More than one maximum-rank piece: retain them at the click.
            for k in range(counts[rank]//2): placed.append((rank,x,y))
    return tuple(sorted(far+placed))


def _target_hits_disk(objects,f,hazards=None):
    # HUD outputs and disks correspond left-to-right.  Each square is accepted
    # when its click anchor is a disk cell.  Some extended boards append an
    # orange-sprite target after the ordinary square previews.
    targets=f["targets"]; disks=f["disks"]
    needed=len(targets)+(1 if f.get("chaser_target") else 0)
    if len(disks)<needed: return False
    for i,target in enumerate(targets):
        disk=set(disks[i]); found=False
        for rank,cx,cy in objects:
            if rank==target and (cx,cy) in disk:
                found=True
        if not found: return False
    if f.get("chaser_target"):
        if hazards is None: return False
        disk=set(disks[len(targets)]); found=False
        for i,(value,pts,stride) in enumerate(f.get("falling",())):
            if i>=len(hazards) or hazards[i] is None: continue
            ox,oy=hazards[i]
            anchor=(min(xx for xx,yy in pts)+ox,
                    min(yy for xx,yy in pts)+stride//2+oy)
            if anchor in disk: found=True
        if not found: return False
    return True


def init_state(entry_grid):
    f=_features(entry_grid)
    if f["mode"]=="runner": return {"records":[(f["start"],tuple())]}
    if f["mode"]=="merge":
        return {"records":[f["initial"]],
                "hazards":[tuple((0,0) for z in f.get("falling",()))],
                "clicks":0}
    return {"clicks":0}


def is_goal(state,grid):
    f=_features(ENTRY_GRID)
    if f["mode"]=="runner":
        pos,col,clicks=_observe_runner(grid,f); t=f["target"]
        return t is not None and abs(pos[0]-t[0])<=2 and abs(pos[1]-t[1])<=2 and len(col)==len(f["crosses"])
    if f["mode"]=="merge":
        objects,clicks=_observe_merge(grid,f)
        hazards=(state or {}).get("hazards",[])
        offsets=hazards[-1] if hazards else _observe_chasers(grid,f)
        return _target_hits_disk(objects,f,offsets)
    return False


def predict(state,grid,action,x=None,y=None):
    f=_features(ENTRY_GRID)
    info={"level_up":False,"dead":False,"win":False}

    if f["mode"]=="runner":
        records=list(state.get("records",[(f["start"],tuple())]))
        opos,ocol,nclicks=_observe_runner(grid,f)
        if records[-1][0]!=opos or len(records)-1!=nclicks:
            records=[(opos,ocol) for k in range(nclicks+1)]
        if action==6:
            oldpos,oldcol=records[-1]; nx,ny=int(x),int(y)
            # Runner is likewise a 3x3 square attracted when the click
            # is within Euclidean radius 8 of one of its occupied cells.
            ox,oy=oldpos
            dx=(ox-1-nx if nx<ox-1 else (nx-(ox+1) if nx>ox+1 else 0))
            dy=(oy-1-ny if ny<oy-1 else (ny-(oy+1) if ny>oy+1 else 0))
            valid=dx*dx+dy*dy<=64
            newpos=(nx,ny) if valid else oldpos; col=set(oldcol)
            if valid:
                for i,(cx,cy,pts) in enumerate(f["crosses"]):
                    if abs(nx-cx)<=1 and abs(ny-cy)<=1: col.add(i)
            records.append((newpos,tuple(sorted(col))))
            t=f["target"]
            if valid and t is not None and abs(nx-t[0])<=2 and abs(ny-t[1])<=2 and len(col)==len(f["crosses"]):
                if CURRENT_LEVEL==8: info["win"]=True
                else: info["level_up"]=True
        elif action==7:
            if len(records)>1: records.pop()
        ns={"records":records}
        return _render_runner(records),info,ns

    if f["mode"]=="merge":
        records=list(state.get("records",[f["initial"]]))
        hazards=list(state.get("hazards",
                     [tuple((0,0) for z in f.get("falling",()))]))
        observed,nclicks=_observe_merge(grid,f)
        clicks=int(state.get("clicks",nclicks))
        ohaz=_observe_chasers(grid,f)
        # A later-drawn solid square can hide part or all of a pursuer.
        # Partial observations are None and must not destroy its threaded
        # full-sprite offset.
        hlast=hazards[-1]
        haz_bad=(len(hlast)!=len(ohaz) or
                 any(o is not None and o!=hlast[i]
                     for i,o in enumerate(ohaz) if i<len(hlast)))
        # Geometry undo depth and the monotonically consumed click meter are
        # independent.  Trust the observed meter without discarding a valid
        # undo stack merely because their lengths differ.
        clicks=nclicks
        if records[-1]!=observed or haz_bad:
            records=[observed]
            merged_haz=tuple((o if o is not None else
                              (hlast[i] if i<len(hlast) else (0,0)))
                             for i,o in enumerate(ohaz))
            hazards=[merged_haz]
        if action==6 and int(y)>=f["split"]:
            ix,iy=int(x),int(y)
            old_objects=records[-1]; old_hazards=hazards[-1]
            objects=_merge_click(old_objects,ix,iy,f)
            new_hazards=_advance_chasers(
                old_hazards,objects,f,(ix,iy))
            objects,new_hazards=_resolve_chaser_hits(
                old_objects,objects,old_hazards,new_hazards,ix,iy,f)
            records.append(objects)
            hazards.append(new_hazards)
            clicks+=1
            if _target_hits_disk(objects,f,new_hazards):
                if CURRENT_LEVEL==8: info["win"]=True
                else: info["level_up"]=True
        elif action==7:
            if len(records)>1:
                records.pop()
                if len(hazards)>1: hazards.pop()
        ns={"records":records,"hazards":hazards,"clicks":clicks}
        return _render_merge(records,hazards,clicks),info,ns

    clicks=_meter(grid,f["bg"])
    if action==6 and int(y)>=f["split"]: clicks+=1
    elif action==7 and clicks>0: clicks-=1
    ns={"clicks":clicks}
    out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape; nfill=min(w,2*clicks)
    if nfill: out[h-1,w-nfill:w]=f["bg"]
    return out.tolist(),info,ns
