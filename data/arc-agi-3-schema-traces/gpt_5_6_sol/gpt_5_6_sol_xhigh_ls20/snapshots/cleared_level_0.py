# ARC3 world model: macro-grid movement with a finite move meter.
import numpy as np

def _token_bbox(a):
    # The moving 5x5 token is the only object containing colour 12.
    ys, xs = np.where(a == 12)
    if len(xs) == 0:
        return None
    # colour-12 components may later exist; choose the compact component joined to 9s.
    seen = set()
    comps = []
    cells = set(zip(xs.tolist(), ys.tolist()))
    for p in list(cells):
        if p in seen: continue
        stack=[p]; seen.add(p); cc=[]
        while stack:
            q=stack.pop(); cc.append(q)
            x,y=q
            for n in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if n in cells and n not in seen:
                    seen.add(n); stack.append(n)
        comps.append(cc)
    cc=max(comps,key=len)
    x0=min(x for x,y in cc); x1=max(x for x,y in cc)
    y0=min(y for x,y in cc); y1=max(y for x,y in cc)
    # Token is 5x5, with 12 in its top rows and 9 in the rest.
    return x0,y0,x0+4,y0+4

def _base_grid():
    # Static playfield under the token; ENTRY_GRID includes the initial token itself.
    b=np.array(ENTRY_GRID,dtype=int).copy()
    ib=_token_bbox(b)
    if ib is not None:
        x0,y0,x1,y1=ib
        b[y0:y1+1,x0:x1+1]=3
    return b

def _goal_pattern(entry):
    # Find a 9x9 lock: colour-3 rim around a 7x7 colour-5/9 glyph.
    h,w=entry.shape
    for y in range(0,min(30,h-8)):
        for x in range(w-8):
            z=entry[y:y+9,x:x+9]
            rim=np.concatenate((z[0,:],z[-1,:],z[1:-1,0],z[1:-1,-1]))
            inner=z[1:-1,1:-1]
            if np.all(rim==3) and np.all(np.isin(inner,[5,9])) and np.any(inner==9):
                return (x,y,entry[y+2:y+7,x+2:x+7].copy())
    return None

def _hud_matches_goal(a):
    goal=_goal_pattern(np.array(ENTRY_GRID,dtype=int))
    if goal is None or a.shape[0]<63 or a.shape[1]<11:
        return False
    pat=goal[2]
    for r in range(5):
        for c in range(5):
            if not np.all(a[53+2*r:55+2*r,1+2*c:3+2*c]==pat[r,c]):
                return False
    return True

def _set_hud_to_goal(out):
    # A 0/1 switch edits the enlarged current glyph toward the lock glyph.
    goal=_goal_pattern(np.array(ENTRY_GRID,dtype=int))
    if goal is None: return
    pat=goal[2]
    for r in range(5):
        for c in range(5):
            out[53+2*r:55+2*r,1+2*c:3+2*c]=pat[r,c]

def step(grid, action, x=None, y=None):
    a=np.array(grid,dtype=int)
    out=a.copy()
    info={"level_up":False,"dead":False,"win":False}
    vec={1:(0,-5),2:(0,5),3:(-5,0),4:(5,0)}
    if action not in vec:
        return out.tolist(),info
    box=_token_bbox(a)
    switch=False
    if box is not None:
        x0,y0,x1,y1=box
        dx,dy=vec[action]
        nx0,ny0=x0+dx,y0+dy
        nx1,ny1=x1+dx,y1+dy
        if 0<=nx0 and nx1<a.shape[1] and 0<=ny0 and ny1<53:
            old=a[y0:y1+1,x0:x1+1].copy()
            raw=a[ny0:ny1+1,nx0:nx1+1].copy()
            test=raw.copy()
            # overlap with current token counts as traversable
            for yy in range(max(y0,ny0),min(y1,ny1)+1):
                for xx in range(max(x0,nx0),min(x1,nx1)+1):
                    test[yy-ny0,xx-nx0]=3
            switch=np.any(np.isin(test,[0,1]))
            if np.all(np.isin(test,[0,1,3])):
                # 0/1 sprites are collectible switches embedded in the floor.
                base=_base_grid()
                out[y0:y1+1,x0:x1+1]=base[y0:y1+1,x0:x1+1]
                out[ny0:ny1+1,nx0:nx1+1]=old
                if switch:
                    _set_hud_to_goal(out)
            elif _hud_matches_goal(a):
                goal=_goal_pattern(np.array(ENTRY_GRID,dtype=int))
                gx,gy,_=goal if goal is not None else (-99,-99,None)
                if nx0==gx+2 and ny0==gy+7 and np.all(np.isin(test,[3,5])):
                    # The first step crosses the rim through the lock's bottom opening.
                    base=_base_grid()
                    out[y0:y1+1,x0:x1+1]=base[y0:y1+1,x0:x1+1]
                    out[ny0:ny1+1,nx0:nx1+1]=old
                elif nx0==gx+2 and ny0==gy+2:
                    # Centering the token on the matching 5x5 glyph advances.
                    info["level_up"]=True
    # Bottom HUD is a one-column-per-action move meter.
    if out.shape[0]>=63 and not switch:
        for xx in range(13,55):
            if out[61,xx]==11 and out[62,xx]==11:
                out[61:63,xx]=3
                break
    return out.tolist(),info
