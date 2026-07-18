# Two identity-preserving 5x5 tokens on mirrored color-5 tracks.
def _components(a,color):
    h=len(a); w=len(a[0]); seen=set(); out=[]
    for y in range(h):
        for x in range(w):
            if a[y][x]!=color or (x,y) in seen: continue
            q=[(x,y)]; seen.add((x,y)); c=[]; qi=0
            while qi<len(q):
                xx,yy=q[qi]; qi+=1; c.append((xx,yy))
                for z in ((xx+1,yy),(xx-1,yy),(xx,yy+1),(xx,yy-1)):
                    nx,ny=z
                    if 0<=nx<w and 0<=ny<h and a[ny][nx]==color and z not in seen:
                        seen.add(z); q.append(z)
            out.append(c)
    return out

def _tops(grid):
    cs=_components(grid,10)
    ps=[(min(x for x,y in c),min(y for x,y in c)) for c in cs]
    return sorted(ps)

def init_state(entry_grid):
    return {"turns":0,"pos":_tops(entry_grid)}

def _entry_pos():
    return _tops(ENTRY_GRID)

def predict(state,grid,action,x=None,y=None):
    a=[r[:] for r in grid]
    prior=state.get("turns",0)
    pos=[tuple(p) for p in state.get("pos",_entry_pos())]

    # Replay skips the first-ever transition. Its resulting non-entry board
    # lets us recover both the omitted turn and token locations.
    if prior==0 and grid!=ENTRY_GRID:
        prior=1
        seen=_tops(grid)
        if len(seen)==2: pos=seen
    turns=prior+1

    if action in (1,2,3,4) and len(pos)==2:
        dest=[]; movable=[]
        for i,(px,py) in enumerate(pos):
            if action==1: dx,dy=0,-5
            elif action==2: dx,dy=0,5
            elif action==3: dx,dy=(-5 if i==0 else 5),0
            else: dx,dy=(5 if i==0 else -5),0
            np0=(px+dx,py+dy); dest.append(np0)
            nx,ny=np0
            ok=(0<=nx<=len(a[0])-5 and 0<=ny<=len(a)-5 and
                all(a[v][u]==5 for v in range(ny,ny+5)
                                   for u in range(nx,nx+5)))
            movable.append(ok)
        for i,ok in enumerate(movable):
            if ok:
                px,py=pos[i]
                for v in range(py,py+5):
                    for u in range(px,px+5): a[v][u]=5
        for i,ok in enumerate(movable):
            if ok:
                pos[i]=dest[i]; px,py=pos[i]
                for v in range(py,py+5):
                    for u in range(px,px+5): a[v][u]=10

    # 150-action level budget rendered to the 64-pixel border, nearest integer.
    meter=(turns*64+75)//150
    a[0]=[5]*len(a[0]); a[-1]=[5]*len(a[-1])
    for i in range(meter): a[-1][i]=0; a[0][-1-i]=0

    ns={"turns":turns,"pos":pos}
    goal=is_goal(ns,a)
    last=(CURRENT_LEVEL is not None and CURRENT_LEVEL>=5)
    info={"level_up":bool(goal and not last),"dead":False,"win":bool(goal and last)}
    return a,info,ns

def is_goal(state,grid):
    # The visually identical tokens must exchange their two entry squares.
    ep=_entry_pos(); p=[tuple(z) for z in (state or {}).get("pos",[])]
    return len(ep)==2 and len(p)==2 and p[0]==ep[1] and p[1]==ep[0]
