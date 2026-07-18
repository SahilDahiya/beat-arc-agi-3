import numpy as np

# Each "ink" colour defines a constellation.  Its small endpoint diamonds
# have green or black bodies, its purple-centred large marker is the floor
# centroid of all endpoints, and a hollow ring of the ink colour is its goal.
# There is one black (selected/movable) endpoint globally.

def _inside(a,x,y):
    return 0 <= y < a.shape[0] and 0 <= x < a.shape[1]

def _bresenham(x0,y0,x1,y1):
    pts=[]
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy:
            err+=dy; x0+=sx
        if e2<=dx:
            err+=dx; y0+=sy
    return pts

def _diamond(a,cx,cy,body,ink):
    for dy in range(-2,3):
        w=2-abs(dy)
        for dx in range(-w,w+1):
            xx,yy=cx+dx,cy+dy
            if _inside(a,xx,yy): a[yy,xx]=body
    if _inside(a,cx,cy): a[cy,cx]=ink

def _disk(a,cx,cy,ink):
    for dy in range(-2,3):
        w=1 if abs(dy)==2 else 2
        for dx in range(-w,w+1):
            xx,yy=cx+dx,cy+dy
            if _inside(a,xx,yy): a[yy,xx]=ink
    if _inside(a,cx,cy): a[cy,cx]=6

def _entry_features():
    e=np.array(ENTRY_GRID,dtype=int)

    # Ink colours are exactly the colours surrounding purple centre cells.
    mids=[]
    inks=[]
    for yy,xx in np.argwhere(e==6):
        x,y=int(xx),int(yy)
        vals=[]
        for dx,dy in [(0,-1),(0,1),(-1,0),(1,0)]:
            if _inside(e,x+dx,y+dy): vals.append(int(e[y+dy,x+dx]))
        ink=max(set(vals),key=vals.count)
        mids.append((ink,x,y))
        if ink not in inks: inks.append(ink)

    endpoints=[]
    for ink in inks:
        for yy,xx in np.argwhere(e==ink):
            x,y=int(xx),int(yy)
            if not (0<y<e.shape[0]-1 and 0<x<e.shape[1]-1): continue
            orth=[int(e[y-1,x]),int(e[y+1,x]),int(e[y,x-1]),int(e[y,x+1])]
            if len(set(orth))==1 and orth[0] in (0,3):
                endpoints.append((ink,orth[0],x,y))

    base=e.copy()
    base[base==1]=5
    for ink,body,cx,cy in endpoints:
        for dy in range(-2,3):
            w=2-abs(dy)
            for dx in range(-w,w+1):
                xx,yy=cx+dx,cy+dy
                if _inside(base,xx,yy): base[yy,xx]=5
    for ink,cx,cy in mids:
        for dy in range(-2,3):
            w=1 if abs(dy)==2 else 2
            for dx in range(-w,w+1):
                xx,yy=cx+dx,cy+dy
                if _inside(base,xx,yy): base[yy,xx]=5

    # Once dynamic ink shapes are erased, remaining pixels of each ink are
    # its hollow target ring.  Ring centre is the mean of its symmetric arcs.
    targets={}
    for ink in inks:
        q=np.argwhere(base==ink)
        targets[ink]=(int(round(float(q[:,1].mean()))),
                      int(round(float(q[:,0].mean()))))
    return base,inks,endpoints,targets

def _parse_endpoints(grid,inks,fallback):
    a=np.array(grid,dtype=int)
    out=[]
    for ink in inks:
        for yy,xx in np.argwhere(a==ink):
            x,y=int(xx),int(yy)
            if not (0<y<a.shape[0]-1 and 0<x<a.shape[1]-1): continue
            orth=[int(a[y-1,x]),int(a[y+1,x]),int(a[y,x-1]),int(a[y,x+1])]
            if len(set(orth))==1 and orth[0] in (0,3):
                out.append((ink,orth[0],x,y))
    return out if out else list(fallback)

def init_state(entry_grid):
    base,inks,endpoints,targets=_entry_features()
    return {}

def predict(state,grid,action,x=None,y=None):
    if action!=6 or x is None or y is None:
        return [row[:] for row in grid],{"level_up":False,"dead":False,"win":False},dict(state)

    base,inks,entry_endpoints,targets=_entry_features()
    endpoints=_parse_endpoints(grid,inks,entry_endpoints)
    before_endpoints=list(endpoints)
    x,y=int(x),int(y)

    blacks=[i for i,p in enumerate(endpoints) if p[1]==0]
    bi=blacks[0]
    green_hit=None
    for i,(ink,body,px,py) in enumerate(endpoints):
        if body==3 and (x,y)==(px,py):
            green_hit=i; break

    if green_hit is not None:
        # Selection transfers to the clicked endpoint; identities/positions
        # remain fixed, hence no constellation centroid moves on this click.
        ink,body,px,py=endpoints[bi]
        endpoints[bi]=(ink,3,px,py)
        ink,body,px,py=endpoints[green_hit]
        endpoints[green_hit]=(ink,0,px,py)
    else:
        ink,body,px,py=endpoints[bi]
        candidate=list(endpoints)
        candidate[bi]=(ink,0,x,y)

        # A relocation is accepted only when its entire resulting
        # constellation (endpoint diamonds, centroid disk, and spokes) fits
        # on the safe field.  Hollow target-ring pixels are also traversable.
        ps=[(qx,qy) for ii,bb,qx,qy in candidate if ii==ink]
        cx=sum(qx for qx,qy in ps)//len(ps)
        cy=sum(qy for qx,qy in ps)//len(ps)
        cells=[]
        for qx,qy in ps:
            for dy in range(-2,3):
                w=2-abs(dy)
                for dx in range(-w,w+1): cells.append((qx+dx,qy+dy))
            cells.extend(_bresenham(cx,cy,qx,qy))
        for dy in range(-2,3):
            w=1 if abs(dy)==2 else 2
            for dx in range(-w,w+1): cells.append((cx+dx,cy+dy))
        fits=True
        for qx,qy in cells:
            if not _inside(base,qx,qy) or int(base[qy,qx]) not in ([5]+list(inks)):
                fits=False; break
        if fits:
            endpoints=candidate

    cur=np.array(grid,dtype=int)
    spent=0
    while spent<cur.shape[0] and cur[spent,0]==5: spent+=1
    # Every action spends one left-edge budget cell.  The first actual
    # relocation in a larger constellation additionally pays its setup
    # surcharge (n-2); subsequent relocations in that group cost one.
    cost=1
    if green_hit is None:
        moved_ink=endpoints[bi][0]
        cur_positions=sorted((px,py) for ii,body,px,py in before_endpoints
                             if ii==moved_ink)
        entry_positions=sorted((px,py) for ii,body,px,py in entry_endpoints
                               if ii==moved_ink)
        if cur_positions==entry_positions:
            group_size=len(cur_positions)
            cost=max(1,group_size-1)
    n=spent+cost
    for yy in range(min(n,base.shape[0])): base[yy,0]=5

    centroids={}
    for ink in inks:
        ps=[(px,py) for ii,body,px,py in endpoints if ii==ink]
        cx=sum(p[0] for p in ps)//len(ps)
        cy=sum(p[1] for p in ps)//len(ps)
        centroids[ink]=(cx,cy)
        # A constellation already on its target turns the hollow target
        # ring black as a persistent solved indicator.
        if (cx,cy)==targets[ink]:
            base[base==ink]=0
        for px,py in ps:
            # Renderer starts each spoke at the centroid.  Bresenham is not
            # perfectly reversal-symmetric on half-error ties.
            for xx,yy in _bresenham(cx,cy,px,py):
                if _inside(base,xx,yy): base[yy,xx]=1

    # Dynamic objects overlay their blue connectors.
    for ink,body,px,py in endpoints:
        if body==3: _diamond(base,px,py,3,ink)
    for ink in inks:
        cx,cy=centroids[ink]
        _disk(base,cx,cy,ink)
    for ink,body,px,py in endpoints:
        if body==0: _diamond(base,px,py,0,ink)

    solved=all(centroids[ink]==targets[ink] for ink in inks)
    final_level=(CURRENT_LEVEL is not None and int(CURRENT_LEVEL)>=5)
    info={"level_up":bool(solved and not final_level),
          "dead":False,
          "win":bool(solved and final_level)}
    return base.tolist(),info,{}
