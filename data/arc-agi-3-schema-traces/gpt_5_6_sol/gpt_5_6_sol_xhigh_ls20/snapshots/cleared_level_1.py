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

def _restore_under_token(out,x0,y0,x1,y1):
    base=_base_grid()
    z=base[y0:y1+1,x0:x1+1]
    # Refill rings are one-use pickups: after being covered, they are gone.
    if np.any(z==11):
        out[y0:y1+1,x0:x1+1]=3
    else:
        out[y0:y1+1,x0:x1+1]=z

def _soft_reset(a):
    # Running out of meter spends the rightmost remaining life and restores ENTRY_GRID.
    entry=np.array(ENTRY_GRID,dtype=int)
    out=entry.copy()
    starts=[]
    for x in range(entry.shape[1]-1):
        if np.all(entry[61:63,x:x+2]==8) and (x==0 or entry[61,x-1]!=8):
            starts.append(x)
    # Preserve lives already spent in earlier soft resets.
    for x in starts:
        if np.all(a[61:63,x:x+2]==3):
            out[61:63,x:x+2]=3
    for x in reversed(starts):
        if np.all(out[61:63,x:x+2]==8):
            out[61:63,x:x+2]=3
            break
    return out

def _goal_pattern(entry):
    # Find a 9x9 lock: colour-3 rim around a 7x7 colour-5/9 glyph.
    h,w=entry.shape
    for y in range(0,min(53,h-8)):
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

def _rotate_hud(out):
    # A 0/1 rotary button turns the current 5x5 glyph 90 degrees clockwise.
    pat=np.array([[out[53+2*r,1+2*c] for c in range(5)] for r in range(5)])
    pat=np.rot90(pat,-1)
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
    pad=False
    if box is not None:
        x0,y0,x1,y1=box
        dx,dy=vec[action]
        nx0,ny0=x0+dx,y0+dy
        nx1,ny1=x1+dx,y1+dy
        if 0<=nx0 and nx1<a.shape[1] and 0<=ny0 and ny1<55:
            old=a[y0:y1+1,x0:x1+1].copy()
            raw=a[ny0:ny1+1,nx0:nx1+1].copy()
            test=raw.copy()
            # overlap with current token counts as traversable
            for yy in range(max(y0,ny0),min(y1,ny1)+1):
                for xx in range(max(x0,nx0),min(x1,nx1)+1):
                    test[yy-ny0,xx-nx0]=3
            switch=np.any(np.isin(test,[0,1]))
            pad=np.any(test==11) and np.all(np.isin(test,[3,11]))
            if np.all(np.isin(test,[0,1,3])) or pad:
                # 0/1 glyph buttons and 11-ring refill pads are floor specials.
                _restore_under_token(out,x0,y0,x1,y1)
                out[ny0:ny1+1,nx0:nx1+1]=old
                if switch:
                    _rotate_hud(out)
                if pad:
                    out[61:63,13:55]=11
            elif _hud_matches_goal(a):
                goal=_goal_pattern(np.array(ENTRY_GRID,dtype=int))
                gx,gy,_=goal if goal is not None else (-99,-99,None)
                center=(gx+2,gy+2)
                entrances={(center[0]-5,center[1]),(center[0]+5,center[1]),
                           (center[0],center[1]-5),(center[0],center[1]+5)}
                if (nx0,ny0) in entrances and np.all(np.isin(test,[3,5])):
                    # First cross the rim through whichever side opens to a corridor.
                    _restore_under_token(out,x0,y0,x1,y1)
                    out[ny0:ny1+1,nx0:nx1+1]=old
                elif (nx0,ny0)==center:
                    # Centering the token on the matching 5x5 glyph advances.
                    info["level_up"]=True
    # Bottom HUD is a one-column-per-action move meter.
    # The tutorial level exempts its rotary-button press; later levels charge normally.
    switch_free = switch and int(CURRENT_LEVEL or 0)==0
    if out.shape[0]>=63 and not switch_free and not pad:
        # Each successive level spends one more meter column per ordinary action.
        cost=(int(CURRENT_LEVEL)+1) if CURRENT_LEVEL is not None else 1
        available=sum(1 for xx in range(13,55)
                      if a[61,xx]==11 and a[62,xx]==11)
        if available < cost:
            return _soft_reset(a).tolist(),{"level_up":False,"dead":False,"win":False}
        for _ in range(cost):
            for xx in range(13,55):
                if out[61,xx]==11 and out[62,xx]==11:
                    out[61:63,xx]=3
                    break
    return out.tolist(),info

def is_goal(grid):
    # Advancement is emitted by step when the token centers in a matched lock.
    return False
