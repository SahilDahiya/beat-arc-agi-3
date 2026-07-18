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


def _toolbar_rows(a,split):
    # A board may show multiple independent merge vocabularies on separate
    # header rows (L7: square ranks above, pursuer colours below).
    rows={}
    for value in range(16):
        for pts in _components(a,value):
            if len(pts)!=4 or max(y for x,y in pts)>=split: continue
            xs=[x for x,y in pts]; ys=[y for x,y in pts]
            if max(xs)-min(xs)==1 and max(ys)-min(ys)==1:
                rows.setdefault(min(ys),[]).append((min(xs),value))
    return tuple((yy,tuple(v for xx,v in sorted(items)))
                 for yy,items in sorted(rows.items()))


def _toolbar_stages(a,split):
    rows=_toolbar_rows(a,split)
    if not rows: return tuple()
    # The ordinary square chain is the longest vocabulary row; ties choose
    # the upper row.  Large target previews on other rows stay excluded.
    yy,vals=max(rows,key=lambda z:(len(z[1]),-z[0]))
    return vals


def _compute_features(entry):
    a=np.array(entry,dtype=int); h,w=a.shape
    split,bg=_split_and_bg(a)
    rows=_toolbar_rows(a,split)
    stages=_toolbar_stages(a,split)
    aux_rows=[vals for yy,vals in rows if vals!=stages and len(vals)>=2]
    chaser_stages=max(aux_rows,key=len) if aux_rows else tuple()

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
        shown=[]; preview_cells=[]
        for rank,value in enumerate(stages):
            side=sides[rank]
            for pts in _components(a,value):
                if max(y for x,y in pts)>=split: continue
                xs=[x for x,y in pts]; ys=[y for x,y in pts]
                if min(xs)<16: continue
                if len(pts)==side*side and max(xs)-min(xs)==side-1 and max(ys)-min(ys)==side-1:
                    shown.append((min(xs),rank))
                    preview_cells.extend(pts)
        shown.sort()
        targets=tuple(rank for xx,rank in shown)
        if not targets: targets=(len(stages)-1,)

        disks=[]
        for pts in _components(a,9,h-1):
            if min(y for x,y in pts)>=split:
                cx=sum(x for x,y in pts)/len(pts)
                disks.append((cx,tuple(pts)))
        disks.sort()

        # Each 8-connected outline glyph is a pursuer.  L7 adds a second
        # toolbar vocabulary (7→e→d); its large header glyph previews the
        # requested pursuer rank independently of the square previews.
        falling=[]; chaser_targets=[]; chaser_shapes={}
        base_chaser=chaser_stages[0] if chaser_stages else 7
        for hrank,value in enumerate(chaser_stages):
            for pts in _components8(a,value,h-1):
                if max(yy for xx,yy in pts)<split and len(pts)>4:
                    chaser_targets.append((min(xx for xx,yy in pts),hrank))
                    preview_cells.extend(pts)
                    height=max(yy for xx,yy in pts)-min(yy for xx,yy in pts)+1
                    cx=min(xx for xx,yy in pts)+height//2
                    cy=min(yy for xx,yy in pts)+height//2
                    chaser_shapes[hrank]=tuple(sorted(
                        (xx-cx,yy-cy) for xx,yy in pts))
        if not chaser_stages:
            for pts in _components8(a,7,h-1):
                if max(yy for xx,yy in pts)<split and len(pts)>4:
                    chaser_targets.append((min(xx for xx,yy in pts),0))
        for pts in _components8(a,base_chaser,h-1):
            if min(yy for xx,yy in pts)<split: continue
            height=max(yy for xx,yy in pts)-min(yy for xx,yy in pts)+1
            falling.append((base_chaser,tuple(pts),height))
        falling.sort(key=lambda z:min(xx for xx,yy in z[1]))
        if falling and 0 not in chaser_shapes:
            pts=falling[0][1]; stride=falling[0][2]
            cx=min(xx for xx,yy in pts)+stride//2
            cy=min(yy for xx,yy in pts)+stride//2
            chaser_shapes[0]=tuple(sorted((xx-cx,yy-cy) for xx,yy in pts))
        chaser_targets=tuple(rank for xx,rank in sorted(chaser_targets))
        return {"mode":"merge","split":split,"bg":bg,"stages":stages,
                "sides":tuple(sides),
                "initial":tuple(sorted(initial)),"initial_cells":tuple(initial_cells),
                "disks":tuple(pts for cx,pts in disks),"targets":targets,
                "preview_cells":tuple(preview_cells),
                "falling":tuple(falling),"chaser_stages":tuple(chaser_stages),
                "chaser_shapes":chaser_shapes,
                "chaser_targets":chaser_targets,
                "chaser_target":bool(chaser_targets),
                # The single-pursuer four-rank challenge slows the clock;
                # extended-rank boards retain the ordinary output stride.
                "meter_den":(len(targets)+len(chaser_targets)
                    if chaser_stages else
                    (2 if len(stages)>4 else
                     len(targets)+1+
                     (1 if len(falling)==1 and len(stages)==4 else 0))),
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


def _ranked_template(f,rank=0):
    """Canonical sprite of a colour-rank, centred at logical (0,0)."""
    shapes=f.get("chaser_shapes",{})
    if rank in shapes: return tuple(shapes[rank])
    pts=f["falling"][0][1]
    cx=min(x for x,y in pts)+f["falling"][0][2]//2
    cy=min(y for x,y in pts)+f["falling"][0][2]//2
    base=set((x-cx,y-cy) for x,y in pts)
    # The intermediate e template is invariant even when only the final d
    # preview is shown: carry fills the hollow centre and removes raw's S key.
    if rank==1:
        base.discard((0,1)); base.add((0,0))
    return tuple(sorted(base))


def _initial_ranked_chasers(f):
    ans=[]
    for value,pts,stride in f.get("falling",()):
        cx=min(x for x,y in pts)+stride//2
        cy=min(y for x,y in pts)+stride//2
        ans.append((0,cx,cy))
    return tuple(sorted(ans,key=lambda z:(z[1],z[2],z[0])))


def _observe_ranked_chasers(grid,f):
    a=np.array(grid,dtype=int); h,w=a.shape; ans=[]
    stride=f["falling"][0][2]
    for rank,value in enumerate(f.get("chaser_stages",())):
        expected=len(_ranked_template(f,rank))
        for pts in _components8(a,value,h-1):
            if min(y for x,y in pts)<f["split"] or len(pts)!=expected: continue
            ans.append((rank,min(x for x,y in pts)+stride//2,
                        min(y for x,y in pts)+stride//2))
    return tuple(sorted(ans,key=lambda z:(z[1],z[2],z[0])))


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

    # On ranked-pursuer boards a nearby sprite claims the click before any
    # other pursuer can react to it.  A carried sprite accepts every claimed
    # click; a raw sprite accepts only one of its D-pad cells.  If the nearest
    # raw claims an otherwise blank halo click, the pursuer update is a no-op.
    claimant=None; attract_group=set()
    if click is not None and f.get("chaser_stages"):
        qx,qy=click; choices=[]
        for j,(v,p,s) in enumerate(f["falling"]):
            oo=offsets[j] if j<len(offsets) else (0,0)
            jox,joy=(0,0) if oo is None else oo
            bx0=min(px for px,py in p)+jox; bx1=max(px for px,py in p)+jox
            by0=min(py for px,py in p)+joy; by1=max(py for px,py in p)+joy
            dx=bx0-qx if qx<bx0 else qx-bx1 if qx>bx1 else 0
            dy=by0-qy if qy<by0 else qy-by1 if qy>by1 else 0
            choices.append((dx*dx+dy*dy,j))
        nearby=[j for d,j in choices if d<=64]
        values={f["falling"][j][0] for j in nearby}
        raw=f["chaser_stages"][0]
        # Equal carried sprites share attraction just like equal squares: all
        # land at the click and immediately carry there.
        if nearby and len(values)==1 and raw not in values:
            attract_group=set(nearby)
        else:
            d2,claimant=min(choices)
            if d2>64:
                claimant=None
            else:
                v,p,s=f["falling"][claimant]
                oo=offsets[claimant] if claimant<len(offsets) else (0,0)
                jox,joy=(0,0) if oo is None else oo
                occ={(px+jox,py+joy) for px,py in p}
                ccx=min(px for px,py in p)+s//2+jox
                ccy=min(py for px,py in p)+s//2+joy
                inner=(abs(qx-ccx)<=1 and abs(qy-ccy)<=1 and
                       (qx,qy)!=(ccx,ccy))
                carried=v!=raw
                if not carried and (qx,qy) not in occ and not inner:
                    return tuple((0,0) if z is None else z for z in offsets)

    for i,(value,pts,stride) in enumerate(f["falling"]):
        old=offsets[i] if i<len(offsets) else (0,0)
        ox,oy=(0,0) if old is None else old
        hx=(min(xx for xx,yy in pts)+max(xx for xx,yy in pts))/2.0+ox
        hy=(min(yy for xx,yy in pts)+max(yy for xx,yy in pts))/2.0+oy

        # Rank-0 outline cells form an eight-way D-pad.  Once two equal
        # pursuers carry into a higher colour, the carried sprite instead
        # behaves like a movable piece: any click within Euclidean radius 8
        # of one of its occupied cells places its logical centre at the click.
        if click is not None and (not f.get("chaser_stages") or
                                  i==claimant or i in attract_group):
            qx,qy=click
            occupied={(px+ox,py+oy) for px,py in pts}
            cx=min(px for px,py in pts)+stride//2+ox
            cy=min(py for px,py in pts)+stride//2+oy
            carried=(bool(f.get("chaser_stages")) and
                     value!=f["chaser_stages"][0])
            if carried:
                bx0=min(px for px,py in occupied); bx1=max(px for px,py in occupied)
                by0=min(py for px,py in occupied); by1=max(py for px,py in occupied)
                bdx=bx0-qx if qx<bx0 else qx-bx1 if qx>bx1 else 0
                bdy=by0-qy if qy<by0 else qy-by1 if qy>by1 else 0
            if carried and bdx*bdx+bdy*bdy<=64:
                ox+=qx-cx; oy+=qy-cy
                ans.append((ox,oy))
                continue
            # Besides the eight painted buttons, each inner neighbour of the
            # hollow centre is part of the raw sprite's directional controls.
            # (The hollow centre itself remains an ordinary field click.)
            inner=(abs(qx-cx)<=1 and abs(qy-cy)<=1 and (qx,qy)!=(cx,cy))
            if (qx,qy) in occupied or inner:
                dx=1 if qx>cx else -1 if qx<cx else 0
                dy=1 if qy>cy else -1 if qy<cy else 0
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
            if target[0] == 4 and not f.get("chaser_stages"):
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
            stage_rank=(f["chaser_stages"].index(value)
                        if f.get("chaser_stages") and
                           value in f["chaser_stages"] else 0)
            if stage_rank>=2:
                # Final carried d retains two constituent pursuit impulses,
                # but an axis whose occupied intervals already overlap is
                # inactive.  This is face pursuit rather than centre pursuit:
                # d C41,45 followed c C25,50→C19,44 by (-8,0), since their
                # vertical spans already overlapped.
                tr,tcx,tcy=target; tside=_side(f,tr)
                tx0=tcx-tside//2; tx1=tx0+tside-1
                ty0=tcy-tside//2; ty1=ty0+tside-1
                limit=stage_rank*stride
                if tr==5:
                    # Oversized rank8 engages the tunnel/strike resolver, so a
                    # separated axis keeps the full constituent impulse.
                    mx=(limit if hx1<tx0 else -limit if hx0>tx1 else 0)
                    my=(limit if hy1<ty0 else -limit if hy0>ty1 else 0)
                else:
                    # Against ordinary squares d stops as soon as an occupied
                    # interval reaches the target face.  In particular its
                    # approach to f closed a six-cell vertical gap, not eight.
                    mx=(min(limit,tx0-hx1) if hx1<tx0 else
                        -min(limit,hx0-tx1) if hx0>tx1 else 0)
                    my=(min(limit,ty0-hy1) if hy1<ty0 else
                        -min(limit,hy0-ty1) if hy0>ty1 else 0)
                ox+=mx
                oy+=my
            else:
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

        # Pursuers update in field order.  If an earlier pursuer changed a
        # square's rank/location this tick, later pursuers choose targets from
        # that already-updated object set rather than the start-of-tick set.
        if tuple(sorted(out))!=tuple(sorted(objects)):
            refreshed=_advance_chasers(old_offsets,tuple(sorted(out)),f,(x,y))
            if i<len(refreshed): hz[i]=refreshed[i]

        # Direct D-pad dashes are normally player-controlled phasing moves.
        # If an even b already covers one outline cell and is moved on that
        # same tick, however, its old contact also ejects the dashing sprite:
        # two strides on the dominant block axis, one on the other.
        occupied={(px+oldoff[0],py+oldoff[1]) for px,py in pts}
        pcx=min(px for px,py in pts)+stride//2+oldoff[0]
        pcy=min(py for px,py in pts)+stride//2+oldoff[1]
        inner=(abs(x-pcx)<=1 and abs(y-pcy)<=1 and (x,y)!=(pcx,pcy))
        carried=(bool(f.get("chaser_stages")) and
                 value!=f["chaser_stages"][0])
        bx0=min(px for px,py in occupied); bx1=max(px for px,py in occupied)
        by0=min(py for px,py in occupied); by1=max(py for px,py in occupied)
        bdx=bx0-x if x<bx0 else x-bx1 if x>bx1 else 0
        bdy=by0-y if y<by0 else y-by1 if y>by1 else 0
        attracted=(carried and bdx*bdx+bdy*bdy<=64)
        direct=(x,y) in occupied or inner or attracted
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
                # If ordinary pursuit itself lands with exactly one outline
                # button exposed in loose rank8, it shears immediately.  The
                # fragment is expelled by (side+stride) on the dominant entry
                # axis and (stride-1) on the other; the pursuer rebounds one
                # cell from its old position on each active axis.
                if hit[0]>=5 and covered==len(pts)-1:
                    side=_side(f,hit[0]); kx=sgn(mx); ky=sgn(my)
                    if abs(mx)>=abs(my):
                        ex=kx*(side+stride); ey=ky*(stride-1)
                    else:
                        ex=kx*(stride-1); ey=ky*(side+stride)
                    out.remove(hit)
                    out.append((hit[0]-1,hit[1]+ex,hit[2]+ey))
                    hz[i]=(oldoff[0]+kx,oldoff[1]+ky)
                # A raw mergeable pursuer's three-button leading wedge cleanly
                # shears a stationary c on a horizontal strike.  The b fragment
                # exits by side+2 and the pursuer settles stride-1 into the face.
                elif (f.get("chaser_stages") and
                      value==f["chaser_stages"][0] and hit[0]==4 and
                      covered==3 and abs(mx)>abs(my) and mdx==0 and mdy==0):
                    side=_side(f,hit[0]); kx=sgn(mx)
                    out.remove(hit)
                    out.append((hit[0]-1,hit[1]+kx*(side+2),hit[2]))
                    hz[i]=(oldoff[0]+kx*(stride-1),oldoff[1])
                # A stationary rigid c is cut by the same clean upward
                # one-button strike: its b fragment exits two old sides above,
                # and an exactly centred impact deflects the pursuer right.
                elif (hit[0]==4 and covered==1 and my<0 and
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


def _invalid_ranked_halo(chasers,x,y,f):
    """Whether the nearest ranked sprite claims an unusable raw halo click."""
    choices=[]
    for i,(rank,cx,cy) in enumerate(chasers):
        pts={(cx+dx,cy+dy) for dx,dy in _ranked_template(f,rank)}
        bx0=min(px for px,py in pts); bx1=max(px for px,py in pts)
        by0=min(py for px,py in pts); by1=max(py for px,py in pts)
        dx=bx0-x if x<bx0 else x-bx1 if x>bx1 else 0
        dy=by0-y if y<by0 else y-by1 if y>by1 else 0
        choices.append((dx*dx+dy*dy,i,pts))
    if not choices: return False
    d2,i,pts=min(choices,key=lambda z:(z[0],z[1]))
    if d2>64: return False
    rank,cx,cy=chasers[i]
    if rank>0: return False
    inner=(abs(x-cx)<=1 and abs(y-cy)<=1 and (x,y)!=(cx,cy))
    return (x,y) not in pts and not inner


def _advance_ranked_chasers(chasers,old_objects,objects,x,y,f):
    """Move/resolve L7's mergeable coloured pursuers, then binary-merge hits."""
    stride=f["falling"][0][2]
    ordered=tuple(sorted(chasers,key=lambda z:(z[1],z[2],z[0])))
    tf=dict(f)
    tf["falling"]=tuple((f["chaser_stages"][rank],
                          _ranked_template(f,rank),stride)
                         for rank,cx,cy in ordered)
    old_offsets=tuple((cx,cy) for rank,cx,cy in ordered)
    new_offsets=_advance_chasers(old_offsets,objects,tf,(x,y))
    objects,new_offsets=_resolve_chaser_hits(
        old_objects,objects,old_offsets,new_offsets,x,y,tf)

    # A final-rank carried pursuer advances in repeated stride impulses.  When
    # its next autonomous impulse meets the broad top face of a stationary
    # rank8, the face absorbs the lateral component: the pursuer advances one
    # stride straight to contact and chips the block.  The fragment is expelled
    # through the opposite face by the old side plus the pursuer rank, with a
    # one-cell lateral tie-break away from the off-centre impact.
    new_offsets=list(new_offsets)
    objects=list(objects)
    for i,(rank,cx,cy) in enumerate(ordered):
        if rank<2:
            continue
        pts=_ranked_template(f,rank)
        hx0=cx+min(px for px,py in pts); hx1=cx+max(px for px,py in pts)
        hy1=cy+max(py for px,py in pts)
        # Direct click-attraction phases through squares; only an autonomous
        # pursuit impulse can deliver this heavy face strike.
        qdx=(hx0-x if x<hx0 else x-hx1 if x>hx1 else 0)
        hy0=cy+min(py for px,py in pts)
        qdy=(hy0-y if y<hy0 else y-hy1 if y>hy1 else 0)
        if qdx*qdx+qdy*qdy<=64:
            continue
        hit=None
        for old in old_objects:
            r,sx,sy=old
            if r!=5 or old not in objects:
                continue
            side=_side(f,r)
            x0=sx-side//2; x1=x0+side-1
            y0=sy-side//2
            if hx1<x0 or hx0>x1 or not (hy1<y0):
                continue
            # One repeated rank impulse must be able to reach the face.
            if y0-hy1<=rank*stride:
                hit=old
                break
        if hit is not None:
            r,sx,sy=hit
            objects.remove(hit)
            lateral=(1 if sx>cx else -1)*(stride-1)
            objects.append((r-1,sx+lateral,
                            sy+_side(f,r)+rank))
            new_offsets[i]=(cx,cy+stride)
    objects=tuple(sorted(objects))
    new_offsets=tuple(new_offsets)
    moved=[(ordered[i][0],new_offsets[i][0],new_offsets[i][1])
           for i in range(len(ordered))]

    # A direct raw dash may sweep through another raw before that other sprite's
    # autonomous endpoint is applied.  Such an in-flight collision carries at
    # the midpoint of their pre-tick centres.  If the dash ends short, ordinary
    # endpoint overlap below still carries at the moved midpoint (the L7 case).
    swept_pair=None
    choices=[]
    for i,(rank,cx,cy) in enumerate(ordered):
        pts={(cx+dx,cy+dy) for dx,dy in _ranked_template(f,rank)}
        bx0=min(px for px,py in pts); bx1=max(px for px,py in pts)
        by0=min(py for px,py in pts); by1=max(py for px,py in pts)
        qdx=bx0-x if x<bx0 else x-bx1 if x>bx1 else 0
        qdy=by0-y if y<by0 else y-by1 if y>by1 else 0
        choices.append((qdx*qdx+qdy*qdy,i,pts))
    if choices:
        d2,i,pts=min(choices,key=lambda z:(z[0],z[1]))
        rank,cx,cy=ordered[i]
        inner=(abs(x-cx)<=1 and abs(y-cy)<=1 and (x,y)!=(cx,cy))
        if d2<=64 and rank==0 and ((x,y) in pts or inner):
            dx=1 if x>cx else -1 if x<cx else 0
            dy=1 if y>cy else -1 if y<cy else 0
            jump=(2 if dx and dy else 3)*stride
            base=_ranked_template(f,rank)
            hits=[]
            for j,(r2,cx2,cy2) in enumerate(ordered):
                if j==i or r2!=rank: continue
                other={(cx2+px,cy2+py) for px,py in base}
                for t in range(1,jump+1):
                    swept={(cx+t*dx+px,cy+t*dy+py) for px,py in base}
                    if swept & other:
                        hits.append((t,j)); break
            if hits:
                t,j=min(hits)
                swept_pair=(i,j)
    if swept_pair is not None:
        i,j=swept_pair; a=ordered[i]; b=ordered[j]
        nr=min(a[0]+1,len(f["chaser_stages"])-1)
        moved=[z for k,z in enumerate(moved) if k not in (i,j)]
        moved.append((nr,(a[1]+b[1])//2,(a[2]+b[2])//2))

    def occupied(ch):
        rank,cx,cy=ch
        return {(cx+dx,cy+dy) for dx,dy in _ranked_template(f,rank)}
    # Equal-colour sprites that physically overlap carry to the next colour.
    # The carried sprite is centred at the integer midpoint of the two hollows.
    while True:
        pair=None
        for i in range(len(moved)):
            for j in range(i+1,len(moved)):
                if moved[i][0]==moved[j][0] and occupied(moved[i]) & occupied(moved[j]):
                    pair=(i,j); break
            if pair is not None: break
        if pair is None: break
        i,j=pair; a=moved[i]; b=moved[j]
        nr=min(a[0]+1,len(f["chaser_stages"])-1)
        merged=(nr,(a[1]+b[1])//2,(a[2]+b[2])//2)
        moved=[z for k,z in enumerate(moved) if k not in (i,j)]
        moved.append(merged)
    return objects,tuple(sorted(moved,key=lambda z:(z[1],z[2],z[0])))


def _render_merge(records,hazards=None,clicks=None,active=False):
    f=_features(ENTRY_GRID); out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape
    for xx,yy in f["initial_cells"]: out[yy,xx]=f["bg"]
    if active and f.get("chaser_stages"):
        for xx,yy in f.get("preview_cells",()): out[yy,xx]=2
        for disk in f.get("disks",()):
            for xx,yy in disk: out[yy,xx]=2
    # Undo restores geometry but does not refund the click meter, so elapsed
    # clicks are state independent of the undo stack depth.
    if clicks is None: clicks=len(records)-1
    if hazards is None:
        hazards=[(_initial_ranked_chasers(f) if f.get("chaser_stages") else
                  tuple((0,0) for z in f.get("falling",())))]
    offsets=hazards[-1]
    # Erase every entry sprite before redrawing the threaded dynamic state.
    for value,pts,stride in f.get("falling",()):
        for xx,yy in pts: out[yy,xx]=f["bg"]
    if f.get("chaser_stages"):
        for rank,cx,cy in offsets:
            value=f["chaser_stages"][rank]
            for dx,dy in _ranked_template(f,rank):
                nx=cx+dx; ny=cy+dy
                if 0<=nx<w and 0<=ny<h-1: out[ny,nx]=value
    else:
        for i,(value,pts,stride) in enumerate(f.get("falling",())):
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


def _square_targets_hit(objects,f):
    if len(f["disks"])<len(f["targets"]): return False
    for i,target in enumerate(f["targets"]):
        disk=set(f["disks"][i])
        if not any(rank==target and (cx,cy) in disk
                   for rank,cx,cy in objects):
            return False
    return True


def _ranked_overlay_trigger(chasers,x,y,f):
    # The blue goal preview is a carried-sprite activation: it appears only
    # when the click is on an occupied cell of a non-raw ranked pursuer.
    for rank,cx,cy in chasers:
        if rank<=0: continue
        if (x,y) in {(cx+dx,cy+dy)
                     for dx,dy in _ranked_template(f,rank)}:
            return True
    return False


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
        if f.get("chaser_stages"):
            wanted=f["chaser_targets"][0]
            for rank,cx,cy in hazards:
                # Ranked chaser previews are centred targets: their logical
                # centre, not the left outline button, must enter the disk.
                if rank==wanted and (cx,cy) in disk: found=True
        else:
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
        initial_haz=(_initial_ranked_chasers(f) if f.get("chaser_stages")
                     else tuple((0,0) for z in f.get("falling",())))
        return {"records":[f["initial"]],
                "hazards":[initial_haz],
                "phases":[False],
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
        initial_haz=(_initial_ranked_chasers(f) if f.get("chaser_stages")
                     else tuple((0,0) for z in f.get("falling",())))
        hazards=list(state.get("hazards",[initial_haz]))
        phases=list(state.get("phases",[False for z in records]))
        if not phases: phases=[False]
        observed,nclicks=_observe_merge(grid,f)
        clicks=int(state.get("clicks",nclicks))
        hlast=hazards[-1]
        if f.get("chaser_stages"):
            ohaz=_observe_ranked_chasers(grid,f)
            # Only a complete full-sprite observation can override threaded
            # dynamic ranks; solid squares may temporarily occlude buttons.
            haz_bad=(len(ohaz)==len(hlast) and ohaz!=hlast)
        else:
            ohaz=_observe_chasers(grid,f)
            haz_bad=(len(hlast)!=len(ohaz) or
                     any(o is not None and o!=hlast[i]
                         for i,o in enumerate(ohaz) if i<len(hlast)))
        # Geometry undo depth and the monotonically consumed click meter are
        # independent.  Trust the observed meter without discarding a valid
        # undo stack merely because their lengths differ.
        clicks=nclicks
        if records[-1]!=observed or haz_bad:
            records=[observed]
            phases=[phases[-1]]
            if f.get("chaser_stages"):
                hazards=[ohaz if len(ohaz)==len(hlast) else hlast]
            else:
                merged_haz=tuple((o if o is not None else
                                  (hlast[i] if i<len(hlast) else (0,0)))
                                 for i,o in enumerate(ohaz))
                hazards=[merged_haz]
        if action==6 and int(y)>=f["split"]:
            ix,iy=int(x),int(y)
            old_objects=records[-1]; old_hazards=hazards[-1]
            invalid_halo=(bool(f.get("chaser_stages")) and
                          _invalid_ranked_halo(old_hazards,ix,iy,f))
            active=(phases[-1] or
                    (bool(f.get("chaser_stages")) and
                     _ranked_overlay_trigger(old_hazards,ix,iy,f)))
            objects=_merge_click(old_objects,ix,iy,f)
            if f.get("chaser_stages"):
                objects,new_hazards=_advance_ranked_chasers(
                    old_hazards,old_objects,objects,ix,iy,f)
            else:
                new_hazards=_advance_chasers(
                    old_hazards,objects,f,(ix,iy))
                objects,new_hazards=_resolve_chaser_hits(
                    old_objects,objects,old_hazards,new_hazards,ix,iy,f)
            records.append(objects)
            hazards.append(new_hazards)
            phases.append(active)
            clicks+=1+(1 if invalid_halo else 0)
            if _target_hits_disk(objects,f,new_hazards):
                if CURRENT_LEVEL==8: info["win"]=True
                else: info["level_up"]=True
        elif action==7:
            if len(records)>1:
                records.pop()
                if len(hazards)>1: hazards.pop()
                if len(phases)>1: phases.pop()
        ns={"records":records,"hazards":hazards,
            "phases":phases,"clicks":clicks}
        return _render_merge(records,hazards,clicks,phases[-1]),info,ns

    clicks=_meter(grid,f["bg"])
    if action==6 and int(y)>=f["split"]: clicks+=1
    elif action==7 and clicks>0: clicks-=1
    ns={"clicks":clicks}
    out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape; nfill=min(w,2*clicks)
    if nfill: out[h-1,w-nfill:w]=f["bg"]
    return out.tolist(),info,ns
