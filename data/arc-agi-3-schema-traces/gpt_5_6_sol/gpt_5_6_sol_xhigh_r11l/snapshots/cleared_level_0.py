import numpy as np

# A click moves the black endpoint.  Clicking the green endpoint instead
# swaps the endpoints.  The purple marker is their integer midpoint.

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

def _features():
    e=np.array(ENTRY_GRID,dtype=int)
    # Original purple midpoint.
    q=np.argwhere(e==6)
    px,py=(int(q[0,1]),int(q[0,0]))

    # Original black endpoint: white cell orthogonally surrounded by black.
    b=None
    for yy,xx in np.argwhere(e==15):
        y,x=int(yy),int(xx)
        if 0<y<e.shape[0]-1 and 0<x<e.shape[1]-1:
            if e[y-1,x]==0 and e[y+1,x]==0 and e[y,x-1]==0 and e[y,x+1]==0:
                b=(x,y); break

    # Original green endpoint: white cell orthogonally surrounded by green.
    g=None
    for yy,xx in np.argwhere(e==15):
        y,x=int(yy),int(xx)
        if 0<y<e.shape[0]-1 and 0<x<e.shape[1]-1:
            if e[y-1,x]==3 and e[y+1,x]==3 and e[y,x-1]==3 and e[y,x+1]==3:
                g=(x,y); break

    sx,sy=b; gx,gy=g

    # Static scenery is the entry frame with both endpoints, midpoint and
    # blue connector removed.  The hollow white target is deliberately kept.
    base=e.copy()
    base[base==1]=5
    for cx,cy in [(sx,sy),(gx,gy)]:
        for dy in range(-2,3):
            w=2-abs(dy)
            for dx in range(-w,w+1):
                xx,yy=cx+dx,cy+dy
                if _inside(base,xx,yy): base[yy,xx]=5
    for dy in range(-2,3):
        w=1 if abs(dy)==2 else 2
        for dx in range(-w,w+1):
            xx,yy=px+dx,py+dy
            if _inside(base,xx,yy): base[yy,xx]=5

    # The remaining white pixels are the hollow target.  Its rotational
    # centre is their mean (rings can consist of disconnected arcs).
    ys=[]; xs=[]
    for yy,xx in np.argwhere(base==15):
        ys.append(int(yy)); xs.append(int(xx))
    target=(int(round(sum(xs)/len(xs))),int(round(sum(ys)/len(ys))))
    return base,b,g,target

def init_state(entry_grid):
    base,b,g,target=_features()
    return {"clicks":0,"black":b,"green":g}

def _diamond(a,cx,cy,color):
    for dy in range(-2,3):
        w=2-abs(dy)
        for dx in range(-w,w+1):
            xx,yy=cx+dx,cy+dy
            if _inside(a,xx,yy): a[yy,xx]=color
    if _inside(a,cx,cy): a[cy,cx]=15

def predict(state,grid,action,x=None,y=None):
    if action!=6 or x is None or y is None:
        return [row[:] for row in grid],{"level_up":False,"dead":False,"win":False},dict(state)

    base,entry_b,entry_g,target=_features()
    cur=np.array(grid,dtype=int)

    # Parse live endpoints from the rendered input.  This also makes replay
    # robust when the framework skips the uncheckable very first transition.
    live_b=[]; live_g=[]
    for yy,xx in np.argwhere(cur==15):
        cy,cx=int(yy),int(xx)
        if 0<cy<cur.shape[0]-1 and 0<cx<cur.shape[1]-1:
            if (cur[cy-1,cx]==0 and cur[cy+1,cx]==0 and
                cur[cy,cx-1]==0 and cur[cy,cx+1]==0):
                live_b.append((cx,cy))
            if (cur[cy-1,cx]==3 and cur[cy+1,cx]==3 and
                cur[cy,cx-1]==3 and cur[cy,cx+1]==3):
                live_g.append((cx,cy))
    bx,by=live_b[0] if live_b else tuple(state.get("black",entry_b))
    gx,gy=live_g[0] if live_g else tuple(state.get("green",entry_g))
    x,y=int(x),int(y)

    # The green centre is the control for changing which endpoint is movable.
    if (x,y)==(gx,gy):
        bx,by,gx,gy=gx,gy,bx,by
    else:
        bx,by=x,y

    spent=0
    while spent<cur.shape[0] and cur[spent,0]==5:
        spent+=1
    n=spent+1
    for yy in range(min(n,base.shape[0])):
        base[yy,0]=5

    mx,my=(bx+gx)//2,(by+gy)//2
    for ax,ay,cx,cy in [(bx,by,mx,my),(mx,my,gx,gy)]:
        for xx,yy in _bresenham(ax,ay,cx,cy):
            if _inside(base,xx,yy): base[yy,xx]=1

    # Hollow target is static and was already in base.  Render endpoint
    # diamonds and midpoint above their connector.
    _diamond(base,gx,gy,3)
    for dy in range(-2,3):
        w=1 if abs(dy)==2 else 2
        for dx in range(-w,w+1):
            xx,yy=mx+dx,my+dy
            if _inside(base,xx,yy): base[yy,xx]=15
    if _inside(base,mx,my): base[my,mx]=6
    _diamond(base,bx,by,0)

    won_midpoint=(mx,my)==tuple(target)
    # There are more levels, so target occupation advances rather than
    # winning the whole game; later terminal observations can refine this.
    info={"level_up":bool(won_midpoint),"dead":False,"win":False}
    ns={"clicks":n,"black":(bx,by),"green":(gx,gy)}
    return base.tolist(),info,ns
