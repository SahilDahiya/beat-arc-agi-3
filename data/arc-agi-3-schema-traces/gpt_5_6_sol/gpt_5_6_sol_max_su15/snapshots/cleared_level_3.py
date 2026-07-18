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
        for rank,value in enumerate(stages):
            side=rank+1
            for pts in _components(a,value,h-1):
                if min(y for x,y in pts)<split: continue
                xs=[x for x,y in pts]; ys=[y for x,y in pts]
                # Piece anchor is the click-coordinate: top-left + floor(side/2).
                ax=min(xs)+side//2; ay=min(ys)+side//2
                initial.append((rank,ax,ay))
                initial_cells.extend(pts)
        # Large square previews to the right of the four swatches list
        # the required output ranks, left-to-right.
        shown=[]
        for rank,value in enumerate(stages):
            side=rank+1
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
        falling=[]
        # The glyph is outline-style and its diagonal cells are not
        # 4-connected, so treat the whole field-colour motif as one sprite.
        pts=[(xx,yy) for yy in range(split,h-1) for xx in range(w)
             if int(a[yy,xx])==7]
        if pts:
            height=max(yy for xx,yy in pts)-min(yy for xx,yy in pts)+1
            falling.append((7,tuple(pts),height))
        return {"mode":"merge","split":split,"bg":bg,"stages":stages,
                "initial":tuple(sorted(initial)),"initial_cells":tuple(initial_cells),
                "disks":tuple(pts for cx,pts in disks),"targets":targets,
                "falling":tuple(falling),
                # The clock denominator counts requested outputs plus
                # the falling hazard as an additional timed task.
                "meter_den":len(targets)+1+len(falling),"range":6}

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
    key=CURRENT_LEVEL
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

def _observe_merge(grid,f):
    a=np.array(grid,dtype=int); h,w=a.shape; objects=[]
    for rank,value in enumerate(f["stages"]):
        side=rank+1
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
    for value,base,stride in f["falling"]:
        now=[(xx,yy) for yy in range(f["split"],h-1) for xx in range(w)
             if int(a[yy,xx])==value]
        if now:
            ans.append((min(xx for xx,yy in now)-min(xx for xx,yy in base),
                        min(yy for xx,yy in now)-min(yy for xx,yy in base)))
        else: ans.append((0,0))
    return tuple(ans)


def _object_center(obj):
    rank,cx,cy=obj; side=rank+1
    # The click anchor is lower/right of centre for even-sided squares.
    return (cx-side//2+(side-1)/2.0,
            cy-side//2+(side-1)/2.0)


def _advance_chasers(offsets,objects,f):
    # Each orange pursuer targets the nearest movable square AFTER the click's
    # merge, moving independently by at most one sprite-height on each axis.
    if not f.get("falling"): return tuple()
    ans=[]
    for i,(value,pts,stride) in enumerate(f["falling"]):
        ox,oy=offsets[i] if i<len(offsets) else (0,0)
        hx=(min(xx for xx,yy in pts)+max(xx for xx,yy in pts))/2.0+ox
        hy=(min(yy for xx,yy in pts)+max(yy for xx,yy in pts))/2.0+oy
        if objects:
            target=min(objects,key=lambda o: (_object_center(o)[0]-hx)**2+
                                             (_object_center(o)[1]-hy)**2)
            tx,ty=_object_center(target)
            def toward(d):
                if d>stride: return stride
                if d<-stride: return -stride
                return int(d+0.5) if d>=0 else -int(-d+0.5)
            ox+=toward(tx-hx); oy+=toward(ty-hy)
        ans.append((ox,oy))
    return tuple(ans)


def _render_merge(records,hazards=None):
    f=_features(ENTRY_GRID); out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape
    for xx,yy in f["initial_cells"]: out[yy,xx]=f["bg"]
    # Chaser sprites translate as rigid outline motifs independently of pieces.
    clicks=len(records)-1
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
        side=rank+1; color=f["stages"][rank]
        x0=cx-side//2; y0=cy-side//2
        for yy in range(y0,y0+side):
            for xx in range(x0,x0+side):
                if 0<=xx<w and 0<=yy<h: out[yy,xx]=color
    nfill=min(w,(4*(len(records)-1))//f["meter_den"])
    if nfill: out[h-1,w-nfill:w]=f["bg"]
    return out.tolist()


def _merge_click(objects,x,y,f):
    near=[]; far=[]
    for obj in objects:
        rank,ox,oy=obj
        # Universal click radius: an object is attracted when the
        # click is within Euclidean distance 8 of ANY cell of its square.
        # Larger squares therefore have a larger effective anchor reach.
        side=rank+1
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


def _target_hits_disk(objects,f):
    # Solid maroon goals accept their corresponding displayed output square
    # only once it fits wholly inside. HUD outputs and disks correspond
    # left-to-right; this also handles the one-output levels.
    targets=f["targets"]; disks=f["disks"]
    if len(disks)<len(targets): return False
    for i,target in enumerate(targets):
        disk=set(disks[i]); found=False
        for rank,cx,cy in objects:
            if rank!=target: continue
            side=rank+1; x0=cx-side//2; y0=cy-side//2
            inside=True
            for yy in range(y0,y0+side):
                for xx in range(x0,x0+side):
                    if (xx,yy) not in disk: inside=False
            if inside: found=True
        if not found: return False
    return True


def init_state(entry_grid):
    f=_features(entry_grid)
    if f["mode"]=="runner": return {"records":[(f["start"],tuple())]}
    if f["mode"]=="merge":
        return {"records":[f["initial"]],
                "hazards":[tuple((0,0) for z in f.get("falling",()))]}
    return {"clicks":0}


def is_goal(state,grid):
    f=_features(ENTRY_GRID)
    if f["mode"]=="runner":
        pos,col,clicks=_observe_runner(grid,f); t=f["target"]
        return t is not None and abs(pos[0]-t[0])<=2 and abs(pos[1]-t[1])<=2 and len(col)==len(f["crosses"])
    if f["mode"]=="merge":
        objects,clicks=_observe_merge(grid,f)
        return _target_hits_disk(objects,f)
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
        ohaz=_observe_chasers(grid,f)
        if (records[-1]!=observed or len(records)-1!=nclicks or
            hazards[-1]!=ohaz):
            records=[observed for k in range(nclicks+1)]
            hazards=[ohaz for k in range(nclicks+1)]
        if action==6 and int(y)>=f["split"]:
            objects=_merge_click(records[-1],int(x),int(y),f)
            records.append(objects)
            hazards.append(_advance_chasers(hazards[-1],objects,f))
            if _target_hits_disk(objects,f):
                if CURRENT_LEVEL==8: info["win"]=True
                else: info["level_up"]=True
        elif action==7:
            if len(records)>1:
                records.pop()
                if len(hazards)>1: hazards.pop()
        ns={"records":records,"hazards":hazards}
        return _render_merge(records,hazards),info,ns

    clicks=_meter(grid,f["bg"])
    if action==6 and int(y)>=f["split"]: clicks+=1
    elif action==7 and clicks>0: clicks-=1
    ns={"clicks":clicks}
    out=np.array(ENTRY_GRID,dtype=int); h,w=out.shape; nfill=min(w,2*clicks)
    if nfill: out[h-1,w-nfill:w]=f["bg"]
    return out.tolist(),info,ns
