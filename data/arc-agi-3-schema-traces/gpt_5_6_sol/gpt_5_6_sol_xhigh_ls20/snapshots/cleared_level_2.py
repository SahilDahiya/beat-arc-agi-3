# ARC3 world model: macro-grid movement with a finite move meter.
import numpy as np

def _token_bbox(a):
    # Exact moving-token sprite: two full colour-12 rows over three colour-9 rows.
    h,w=a.shape
    for y in range(min(55,h-4)):
        for x in range(w-4):
            z=a[y:y+5,x:x+5]
            if np.all(z[:2,:]==12) and np.all(z[2:,:]==9):
                return x,y,x+4,y+4
    return None

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

def _apply_bumper(out,x0,y0,token):
    # A solid 5-cell colour-1 bar launches the token away, sliding by macro-cells
    # until the next 5x5 footprint is not plain corridor.
    h,w=out.shape
    base=_base_grid()
    dirs=[]
    if x0>0 and np.all(base[y0:y0+5,x0-1]==1): dirs.append((5,0))
    if x0+5<w and np.all(base[y0:y0+5,x0+5]==1): dirs.append((-5,0))
    if y0>0 and np.all(base[y0-1,x0:x0+5]==1): dirs.append((0,5))
    if y0+5<h and np.all(base[y0+5,x0:x0+5]==1): dirs.append((0,-5))
    if not dirs: return
    dx,dy=dirs[0]
    cx,cy=x0,y0
    while True:
        nx,ny=cx+dx,cy+dy
        if nx<0 or ny<0 or nx+4>=w or ny+4>=55: break
        footprint=out[ny:ny+5,nx:nx+5]
        if not np.all(footprint==3):
            # A matched lock entrance is a valid terminal landing for a launch:
            # the bumper crosses onto the rim entrance, but never auto-centres.
            goal=_goal_pattern(np.array(ENTRY_GRID,dtype=int))
            if goal is not None and _hud_matches_goal(out):
                gx,gy,_=goal
                center=(gx+2,gy+2)
                entrances={(center[0]-5,center[1]),(center[0]+5,center[1]),
                           (center[0],center[1]-5),(center[0],center[1]+5)}
                if (nx,ny) in entrances and np.all(np.isin(footprint,[3,5])):
                    _restore_under_token(out,cx,cy,cx+4,cy+4)
                    out[ny:ny+5,nx:nx+5]=token
            break
        _restore_under_token(out,cx,cy,cx+4,cy+4)
        out[ny:ny+5,nx:nx+5]=token
        cx,cy=nx,ny

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

def _cycle_hud_color(out):
    # Multicolor selector advances foreground 12 -> 9 -> 14 -> 8 -> 12.
    order={12:9,9:14,14:8,8:12}
    pat=np.array([[out[53+2*r,1+2*c] for c in range(5)] for r in range(5)])
    vals=[int(v) for v in np.unique(pat) if int(v) in order]
    if not vals: return
    old=vals[0]; new=order[old]
    for r in range(5):
        for c in range(5):
            if pat[r,c]==old:
                out[53+2*r:55+2*r,1+2*c:3+2*c]=new

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
    palette=False
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
            switch=np.any(np.isin(test,[0,1])) and np.all(np.isin(test,[0,1,3]))
            palette=np.any(test==14) and np.any(test==0) and np.all(np.isin(test,[0,3,8,9,12,14]))
            pad=np.any(test==11) and np.all(np.isin(test,[3,11]))
            if switch or palette or np.all(test==3) or pad:
                # 0/1 glyph buttons and 11-ring refill pads are floor specials.
                _restore_under_token(out,x0,y0,x1,y1)
                out[ny0:ny1+1,nx0:nx1+1]=old
                if switch:
                    _rotate_hud(out)
                if palette:
                    _cycle_hud_color(out)
                if pad:
                    out[61:63,13:55]=11
                if not switch and not palette and not pad:
                    _apply_bumper(out,nx0,ny0,old)
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
        cost=1 if int(CURRENT_LEVEL or 0)==0 else 2
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
