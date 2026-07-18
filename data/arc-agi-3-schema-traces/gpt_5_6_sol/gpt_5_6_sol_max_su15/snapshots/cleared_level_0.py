# World model for ARC3 game su15
# numpy is preloaded as np in the restricted model sandbox.

def _components(a, value, y_stop=None):
    h,w=a.shape
    if y_stop is None: y_stop=h
    seen=set(); ans=[]
    for yy in range(y_stop):
        for xx in range(w):
            if int(a[yy,xx]) != value or (xx,yy) in seen:
                continue
            q=[(xx,yy)]; seen.add((xx,yy)); pts=[]
            while q:
                px,py=q.pop(); pts.append((px,py))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=px+dx,py+dy
                    if 0<=nx<w and 0<=ny<y_stop and int(a[ny,nx])==value and (nx,ny) not in seen:
                        seen.add((nx,ny)); q.append((nx,ny))
            ans.append(pts)
    return ans


def _features(entry):
    a=np.array(entry,dtype=int); h,w=a.shape
    modes=[]
    for yy in range(h):
        vals,cnt=np.unique(a[yy],return_counts=True)
        modes.append(int(vals[int(np.argmax(cnt))]))
    header_bg=modes[0]
    split=0
    for yy in range(h):
        if modes[yy]!=header_bg:
            split=yy
            break

    whites=_components(a,15)
    candidates=[p for p in whites if max(y for x,y in p)>=split]
    movable=max(candidates,key=len)
    sx=int(round(sum(x for x,y in movable)/len(movable)))
    sy=int(round(sum(y for x,y in movable)/len(movable)))
    play_bg=modes[min(max(split,sy),h-2)]

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

    # In the tutorial entry the cross lies six cells diagonally from the token.
    # It marks the maximum displacement allowed by one click.
    move_range=6
    if crosses:
        ds=[max(abs(cx-sx),abs(cy-sy)) for cx,cy,pts in crosses]
        positive=[d for d in ds if d>0]
        if positive: move_range=min(positive)

    return {"split":split,"bg":play_bg,"movable":tuple(movable),
            "start":(sx,sy),"crosses":tuple(crosses),"target":target,
            "range":move_range}


def _observe(grid,f):
    a=np.array(grid,dtype=int); h,w=a.shape
    whites=_components(a,15)
    cand=[p for p in whites if max(y for x,y in p)>=f["split"]]
    if cand:
        p=max(cand,key=len)
        pos=(int(round(sum(x for x,y in p)/len(p))),
             int(round(sum(y for x,y in p)/len(p))))
    else:
        pos=f["start"]

    trail=0
    for xx in range(w-1,-1,-1):
        if int(a[h-1,xx])==f["bg"]: trail+=1
        else: break
    clicks=trail//2

    collected=set()
    for i,(cx,cy,pts) in enumerate(f["crosses"]):
        if abs(pos[0]-cx)<=1 and abs(pos[1]-cy)<=1:
            collected.add(i)
        elif int(a[cy,cx])==3 and all((xx==cx and yy==cy) or int(a[yy,xx])==f["bg"] for xx,yy in pts):
            collected.add(i)
    return pos,tuple(sorted(collected)),clicks


def init_state(entry_grid):
    f=_features(entry_grid)
    return {"records":[(f["start"],tuple())]}


def _render(records):
    f=_features(ENTRY_GRID)
    out=np.array(ENTRY_GRID,dtype=int)
    h,w=out.shape
    for xx,yy in f["movable"]:
        out[yy,xx]=f["bg"]
    pos,collected=records[-1]
    for i in collected:
        ccx,ccy,pts=f["crosses"][i]
        for xx,yy in pts:
            out[yy,xx]=f["bg"]
        # A visited black cross joins the green dotted guide.
        out[ccy,ccx]=3
    cx,cy=pos
    for yy in range(cy-1,cy+2):
        for xx in range(cx-1,cx+2):
            if 0<=xx<w and 0<=yy<h:
                out[yy,xx]=15
    nfill=min(w,2*(len(records)-1))
    if nfill:
        out[h-1,w-nfill:w]=f["bg"]
    return out.tolist()


def is_goal(state,grid):
    f=_features(ENTRY_GRID)
    pos,col,clicks=_observe(grid,f)
    t=f["target"]
    return t is not None and abs(pos[0]-t[0])<=1 and abs(pos[1]-t[1])<=1 and len(col)==len(f["crosses"])


def predict(state,grid,action,x=None,y=None):
    f=_features(ENTRY_GRID)
    records=list(state.get("records",[(f["start"],tuple())]))

    # A model may be installed after exploratory clicks, and transition #0 has no
    # checkable before-frame. Synchronise the latent undo stack to visible state.
    opos,ocol,nclicks=_observe(grid,f)
    if records[-1][0]!=opos or len(records)-1!=nclicks:
        records=[(opos,ocol) for _ in range(nclicks+1)]

    info={"level_up":False,"dead":False,"win":False}
    if action==6:
        oldpos,oldcol=records[-1]
        nx,ny=int(x),int(y)
        valid=max(abs(nx-oldpos[0]),abs(ny-oldpos[1]))<=f["range"]
        newpos=(nx,ny) if valid else oldpos
        col=set(oldcol)
        if valid:
            for i,(cx,cy,pts) in enumerate(f["crosses"]):
                if abs(nx-cx)<=1 and abs(ny-cy)<=1:
                    col.add(i)
        records.append((newpos,tuple(sorted(col))))

        t=f["target"]
        if valid and t is not None and abs(nx-t[0])<=1 and abs(ny-t[1])<=1 and len(col)==len(f["crosses"]):
            if CURRENT_LEVEL==8: info["win"]=True
            else: info["level_up"]=True
    elif action==7:
        if len(records)>1: records.pop()

    ns={"records":records}
    return _render(records),info,ns
