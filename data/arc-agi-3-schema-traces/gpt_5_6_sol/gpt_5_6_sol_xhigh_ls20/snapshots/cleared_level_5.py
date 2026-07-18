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
    # A completed checkpoint lock is consumed to corridor. Detect that state
    # after temporarily removing any part of the token that still overlaps its
    # 9x9 footprint. This also handles the next move from a former rim entrance,
    # where only two token rows/columns overlap the already-consumed lock.
    base=_base_grid()
    for gx,gy,_ in _goal_patterns(np.array(ENTRY_GRID,dtype=int)):
        ix0,iy0=max(x0,gx),max(y0,gy)
        ix1,iy1=min(x1,gx+8),min(y1,gy+8)
        if ix0<=ix1 and iy0<=iy1:
            region=out[gy:gy+9,gx:gx+9].copy()
            region[iy0-gy:iy1-gy+1,ix0-gx:ix1-gx+1]=3
            if np.all(region==3):
                out[y0:y1+1,x0:x1+1]=base[y0:y1+1,x0:x1+1]
                out[iy0:iy1+1,ix0:ix1+1]=3
                return
    z=base[y0:y1+1,x0:x1+1]
    # Refill rings are one-use pickups: after being covered, they are gone.
    # In dual-switch levels the 0/1 rotary is a moving object, so its entry
    # footprint is floor once it has patrolled away; never restore a static copy.
    switches=_floor_switches(base)
    mobile_entry=(any(has1 for _,_,has1 in switches) and
                  any(not has1 for _,_,has1 in switches) and
                  np.any(z==0) and np.all(np.isin(z,[0,1,3])) and
                  (np.any(z==1) or int(CURRENT_LEVEL or 0)>=5))
    mobile_palette=(int(CURRENT_LEVEL or 0)>=5 and np.any(z==14) and
                    np.any(z==0) and np.all(np.isin(z,[0,3,8,9,12,14])))
    if np.any(z==11) or mobile_entry or mobile_palette:
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
            goal=_matching_goal(out)
            if goal is not None:
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

def _goal_patterns(entry):
    # Find every 9x9 lock: colour-3 rim around a two-colour glyph on colour5.
    found=[]
    h,w=entry.shape
    for y in range(0,min(53,h-8)):
        for x in range(w-8):
            z=entry[y:y+9,x:x+9]
            rim=np.concatenate((z[0,:],z[-1,:],z[1:-1,0],z[1:-1,-1]))
            inner=z[1:-1,1:-1]
            vals=[int(v) for v in np.unique(inner)]
            if (np.all(rim==3) and len(vals)==2 and 5 in vals and
                    all(v in (5,8,9,12,14) for v in vals)):
                found.append((x,y,entry[y+2:y+7,x+2:x+7].copy()))
    return found

def _goal_pattern(entry):
    goals=_goal_patterns(entry)
    return goals[0] if goals else None

def _matching_goal(a):
    if a.shape[0]<63 or a.shape[1]<11:
        return None
    for goal in _goal_patterns(np.array(ENTRY_GRID,dtype=int)):
        pat=goal[2]
        ok=True
        for r in range(5):
            for c in range(5):
                if not np.all(a[53+2*r:55+2*r,1+2*c:3+2*c]==pat[r,c]):
                    ok=False
        if ok:
            return goal
    return None

def _hud_matches_goal(a):
    return _matching_goal(a) is not None

def _matching_goal_shape(a):
    # Lock rims test the silhouette independently of foreground colour; exact
    # colour remains relevant when the token attempts to complete the center.
    if a.shape[0]<63 or a.shape[1]<11:
        return None
    occ=np.array([[a[53+2*r,1+2*c]!=5 for c in range(5)] for r in range(5)])
    for goal in _goal_patterns(np.array(ENTRY_GRID,dtype=int)):
        if np.array_equal(occ,goal[2]!=5):
            return goal
    return None

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

def _select_goal_shape(out):
    # The all-0 button advances through four fixed six-cell families while
    # preserving the orientation set by the rotary. The observed cycle is
    # P -> canonical -> C -> T -> P.
    pat=np.array([[out[53+2*r,1+2*c] for c in range(5)] for r in range(5)])
    fg=[int(v) for v in np.unique(pat) if int(v)!=5]
    if not fg: return
    families=[
        np.array([[0,0,0,0,0],
                  [0,0,1,0,0],
                  [0,1,1,0,0],
                  [0,0,1,1,0],
                  [0,0,0,0,0]],dtype=bool),
        np.array([[0,0,0,0,0],
                  [0,1,1,1,0],
                  [0,0,0,1,0],
                  [0,1,0,1,0],
                  [0,0,0,0,0]],dtype=bool),
        np.array([[0,0,0,0,0],
                  [0,1,1,0,0],
                  [0,0,1,1,0],
                  [0,1,0,1,0],
                  [0,0,0,0,0]],dtype=bool),
        np.array([[0,0,0,0,0],
                  [0,0,1,0,0],
                  [0,0,1,0,0],
                  [0,1,1,1,0],
                  [0,0,0,0,0]],dtype=bool)]
    occ=pat!=5
    # The catalogue continues beyond the four six-cell families: at the
    # 180-degree C state the next two observed silhouettes are top-T then
    # top-U. Keep these exact catalogue edges rather than forcing a family
    # rotation abstraction that the screen disproves.
    top_t=np.array([[0,0,0,0,0],
                    [0,1,1,1,0],
                    [0,0,1,0,0],
                    [0,0,1,0,0],
                    [0,0,0,0,0]],dtype=bool)
    top_u=np.array([[0,0,0,0,0],
                    [0,1,1,1,0],
                    [0,1,0,1,0],
                    [0,1,0,1,0],
                    [0,0,0,0,0]],dtype=bool)
    q_shape=np.array([[0,0,0,0,0],
                      [0,0,1,0,0],
                      [0,1,0,1,0],
                      [0,1,1,0,0],
                      [0,0,0,0,0]],dtype=bool)
    p180=np.array([[0,0,0,0,0],
                   [0,1,1,0,0],
                   [0,0,1,1,0],
                   [0,0,1,0,0],
                   [0,0,0,0,0]],dtype=bool)
    if np.array_equal(occ,top_t):
        target=top_u
    elif np.array_equal(occ,top_u):
        target=q_shape
    elif np.array_equal(occ,q_shape):
        target=p180
    else:
        target=None
    if target is None:
        for i,fam in enumerate(families):
            for k in range(4):
                if np.array_equal(occ,np.rot90(fam,-k)):
                    target=np.rot90(families[(i+1)%len(families)],-k)
                    break
            if target is not None:
                break
    if target is None:
        return
    colour=fg[0]
    for r in range(5):
        for c in range(5):
            val=colour if target[r,c] else 5
            out[53+2*r:55+2*r,1+2*c:3+2*c]=val

def _floor_switches(a):
    found=[]
    h,w=a.shape
    for y in range(min(51,h-4)):
        for x in range(w-4):
            z=a[y:y+5,x:x+5]
            border=np.concatenate((z[0],z[-1],z[1:-1,0],z[1:-1,-1]))
            inner=z[1:4,1:4]
            if (np.all(border==3) and np.any(inner==0) and
                    np.all(np.isin(inner,[0,1,3]))):
                found.append((x,y,bool(np.any(inner==1))))
    return found

def _floor_palettes(a):
    found=[]
    h,w=a.shape
    for y in range(min(51,h-4)):
        for x in range(w-4):
            z=a[y:y+5,x:x+5]
            border=np.concatenate((z[0],z[-1],z[1:-1,0],z[1:-1,-1]))
            inner=z[1:4,1:4]
            if (np.all(border==3) and all(np.any(inner==v) for v in (0,8,9,12,14))
                    and np.all(np.isin(inner,[0,3,8,9,12,14]))):
                found.append((x,y))
    return found

def _move_mobile_rotary(out,action,st,direct_contact=False):
    # When a level contains both switch types, the 0/1 rotary patrols its
    # short horizontal track. Contact in either direction rotates the HUD.
    entry=np.array(ENTRY_GRID,dtype=int)
    entry_switches=_floor_switches(entry)
    starts=[(x,y) for x,y,has1 in entry_switches if has1]
    if not (starts and any(not has1 for _,_,has1 in entry_switches)):
        return
    sx,sy=starts[0]
    x0,y0=st.get("mobile_pos",(sx,sy))
    d=1 if st.get("mobile_dir",1)>=0 else -1
    hidden=bool(st.get("mobile_hidden",False))
    sprite=entry[sy:sy+5,sx:sx+5].copy()

    # Direct player entry already rotated in the ordinary switch mechanism.
    if direct_contact and not hidden and _token_bbox(out) is not None:
        if tuple(_token_bbox(out)[:2])==(x0,y0):
            st["mobile_hidden"]=True
            st["mobile_pos"]=(x0,y0)
            st["mobile_dir"]=d
            return

    left=int(st.get("mobile_left",sx))
    right=int(st.get("mobile_right",sx))
    nx=x0+5*d
    if nx<left or nx>right:
        d=-d
        nx=x0+5*d

    # Remove the visible patrol sprite from its old position before advancing.
    if not hidden and np.array_equal(out[y0:y0+5,x0:x0+5],sprite):
        out[y0:y0+5,x0:x0+5]=3

    tok=_token_bbox(out)
    if tok is not None and tuple(tok[:2])==(nx,y0):
        # The rotary can run into the player: this is the same activation.
        _rotate_hud(out)
        hidden=True
    elif np.all(out[y0:y0+5,nx:nx+5]==3):
        out[y0:y0+5,nx:nx+5]=sprite
        hidden=False
    else:
        # A transient obstruction holds it at its previous track position.
        nx=x0
        if not hidden and np.all(out[y0:y0+5,x0:x0+5]==3):
            out[y0:y0+5,x0:x0+5]=sprite

    st["mobile_pos"]=(nx,y0)
    st["mobile_dir"]=d
    st["mobile_hidden"]=hidden

def _move_mobile_aux(out,st,prefix,kind,direct_contact=False):
    # On the advanced dual-lock board the other floor controls patrol too.
    if not bool(st.get(prefix+"_active",False)):
        return
    entry=np.array(ENTRY_GRID,dtype=int)
    x0,y0=st[prefix+"_pos"]
    sx,sy=st[prefix+"_start"]
    d=1 if st.get(prefix+"_dir",1)>=0 else -1
    hidden=bool(st.get(prefix+"_hidden",False))
    sprite=entry[sy:sy+5,sx:sx+5].copy()

    if direct_contact and not hidden and _token_bbox(out) is not None:
        if tuple(_token_bbox(out)[:2])==(x0,y0):
            st[prefix+"_hidden"]=True
            st[prefix+"_pos"]=(x0,y0)
            st[prefix+"_dir"]=d
            return

    if not hidden and np.array_equal(out[y0:y0+5,x0:x0+5],sprite):
        out[y0:y0+5,x0:x0+5]=3

    tok=_token_bbox(out)
    tpos=tuple(tok[:2]) if tok is not None else None
    if kind=="palette":
        # The palette follows the corridor: continue forward, otherwise take
        # the right turn, then left, then reverse. This makes straight lanes
        # and corners one continuous patrol path.
        vx,vy=st.get(prefix+"_vec",(5*d,0))
        dirs=[(vx,vy),(-vy,vx),(vy,-vx),(-vx,-vy)]
        nx,ny=x0,y0
        for qx,qy in dirs:
            tx,ty=x0+qx,y0+qy
            if (0<=tx and 0<=ty and tx+4<out.shape[1] and ty+4<55 and
                    (tpos==(tx,ty) or np.all(out[ty:ty+5,tx:tx+5]==3))):
                nx,ny=tx,ty
                vx,vy=qx,qy
                break
        st[prefix+"_vec"]=(vx,vy)
    else:
        left=int(st[prefix+"_left"])
        right=int(st[prefix+"_right"])
        nx,ny=x0+5*d,y0
        if nx<left or nx>right:
            d=-d
            nx=x0+5*d

    if tpos==(nx,ny):
        if kind=="shape":
            _select_goal_shape(out)
        else:
            _cycle_hud_color(out)
        hidden=True
    elif np.all(out[ny:ny+5,nx:nx+5]==3):
        out[ny:ny+5,nx:nx+5]=sprite
        hidden=False
    else:
        nx,ny=x0,y0
        if not hidden and np.all(out[y0:y0+5,x0:x0+5]==3):
            out[y0:y0+5,x0:x0+5]=sprite

    st[prefix+"_pos"]=(nx,ny)
    st[prefix+"_dir"]=d
    st[prefix+"_hidden"]=hidden

def init_state(entry_grid):
    entry=np.array(entry_grid,dtype=int)
    switches=_floor_switches(entry)
    palettes=_floor_palettes(entry)
    base=entry.copy()
    ib=_token_bbox(base)
    if ib is not None:
        base[ib[1]:ib[3]+1,ib[0]:ib[2]+1]=3
    for x0,y0,_ in switches:
        base[y0:y0+5,x0:x0+5]=3
    for x0,y0 in palettes:
        base[y0:y0+5,x0:x0+5]=3

    def track(sx,sy,tie_dir=1):
        lc=0
        xx=sx-5
        while xx>=0 and np.all(base[sy:sy+5,xx:xx+5]==3):
            lc+=1
            xx-=5
        rc=0
        xx=sx+5
        while xx+4<base.shape[1] and np.all(base[sy:sy+5,xx:xx+5]==3):
            rc+=1
            xx+=5
        d=1 if rc>lc else (-1 if lc>rc else tie_dir)
        # Patrol lanes span at most five macro-cells including the start;
        # longer corridors do not extend the mover's range indefinitely.
        n=min(rc if d>0 else lc,4)
        end=sx+5*n*d
        return d,min(sx,end),max(sx,end)

    movers=[(x,y) for x,y,has1 in switches if has1]
    sx,sy=movers[0] if movers else (0,0)
    d,left,right=track(sx,sy,1) if movers else (1,0,0)
    st={"mobile_dir":d,"mobile_pos":(sx,sy),"mobile_hidden":False,
        "mobile_left":left,"mobile_right":right,"locks_done":()}

    # Level 5 introduces simultaneous patrol of all three floor controls.
    advanced=int(CURRENT_LEVEL or 0)>=5
    shapes=[(x,y) for x,y,has1 in switches if not has1]
    for prefix,items,tie in (("shape",shapes,1),("palette",palettes,-1)):
        ax,ay=items[0] if items else (0,0)
        ad,al,ar=track(ax,ay,tie) if items else (tie,0,0)
        st[prefix+"_active"]=bool(advanced and items)
        st[prefix+"_start"]=(ax,ay)
        st[prefix+"_pos"]=(ax,ay)
        st[prefix+"_dir"]=ad
        st[prefix+"_vec"]=(5*ad,0)
        st[prefix+"_left"]=al
        st[prefix+"_right"]=ar
        st[prefix+"_hidden"]=False
    return st

def predict(state, grid, action, x=None, y=None):
    st=dict(state or {})
    a=np.array(grid,dtype=int)
    out=a.copy()
    info={"level_up":False,"dead":False,"win":False}
    vec={1:(0,-5),2:(0,5),3:(-5,0),4:(5,0)}
    if action not in vec:
        return out.tolist(),info,st
    box=_token_bbox(a)
    switch=False
    palette=False
    pad=False
    lock_center_blocked=False
    test=None
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
                    if np.any(test==1):
                        _rotate_hud(out)
                    else:
                        _select_goal_shape(out)
                if palette:
                    _cycle_hud_color(out)
                if pad:
                    out[61:63,13:55]=11
                if not switch and not palette and not pad:
                    _apply_bumper(out,nx0,ny0,old)
            elif _matching_goal_shape(a) is not None:
                # A matching silhouette opens the rim even when its foreground
                # colour is wrong. Completing the center still needs the exact
                # coloured glyph.
                goal=_matching_goal_shape(a)
                exact_goal=_matching_goal(a)
                gx,gy,_=goal
                center=(gx+2,gy+2)
                entrances={(center[0]-5,center[1]),(center[0]+5,center[1]),
                           (center[0],center[1]-5),(center[0],center[1]+5)}
                if (nx0,ny0) in entrances and np.all(np.isin(test,[3,5])):
                    # First cross the rim through whichever side opens to a corridor.
                    _restore_under_token(out,x0,y0,x1,y1)
                    out[ny0:ny1+1,nx0:nx1+1]=old
                elif ((nx0,ny0)==center and exact_goal is not None and
                      exact_goal[0]==gx and exact_goal[1]==gy):
                    goals=_goal_patterns(np.array(ENTRY_GRID,dtype=int))
                    idx=0
                    for i,g in enumerate(goals):
                        if g[0]==gx and g[1]==gy:
                            idx=i
                            break
                    done=set(st.get("locks_done",()))
                    done.add(idx)
                    st["locks_done"]=tuple(sorted(done))
                    if len(done)>=len(goals):
                        info["level_up"]=True
                    else:
                        # Multi-lock boards checkpoint each matching lock; only
                        # completing the final outstanding lock advances.
                        _restore_under_token(out,x0,y0,x1,y1)
                        out[gy:gy+9,gx:gx+9]=3
                        out[ny0:ny1+1,nx0:nx1+1]=old
                elif (nx0,ny0)==center:
                    # A wrong-colour center attempt is rejected without
                    # advancing patrols or spending any meter.
                    lock_center_blocked=True
    direct_mobile = switch and test is not None and np.any(test==1)
    direct_shape = switch and test is not None and not np.any(test==1)
    moved_box=_token_bbox(out)
    player_moved=(box is not None and moved_box is not None and
                  tuple(moved_box[:2])!=tuple(box[:2]))
    # The patrol clock advances only on a successful player displacement;
    # blocked wall actions still spend meter but freeze every mobile control.
    if player_moved:
        _move_mobile_rotary(out,action,st,direct_mobile)
        _move_mobile_aux(out,st,"shape","shape",direct_shape)
        _move_mobile_aux(out,st,"palette","palette",palette)
    # Bottom HUD is a one-column-per-action move meter.
    # The tutorial level exempts its rotary-button press; later levels charge normally.
    switch_free = switch and int(CURRENT_LEVEL or 0)==0
    if out.shape[0]>=63 and not switch_free and not pad and not lock_center_blocked:
        # Each successive level spends one more meter column per ordinary action.
        # Meter rate is level-specific: confirmed levels 0 and 3 spend one
        # column/action, while levels 1 and 2 spend two.
        cost=2 if int(CURRENT_LEVEL or 0) in (1,2,4) else 1
        available=sum(1 for xx in range(13,55)
                      if a[61,xx]==11 and a[62,xx]==11)
        if available < cost:
            reset_state=init_state(ENTRY_GRID)
            return (_soft_reset(a).tolist(),
                    {"level_up":False,"dead":False,"win":False},reset_state)
        for _ in range(cost):
            for xx in range(13,55):
                if out[61,xx]==11 and out[62,xx]==11:
                    out[61:63,xx]=3
                    break
    return out.tolist(),info,st

def is_goal(state,grid):
    # Focused planning milestone: canonical silhouette at 90 degrees, matching
    # the outstanding second lock independently of its still-needed colour.
    a=np.array(grid,dtype=int)
    pat=np.array([[a[53+2*r,1+2*c] for c in range(5)] for r in range(5)])
    canonical270=np.array([[0,0,0,0,0],
                           [0,1,1,1,0],
                           [0,1,0,0,0],
                           [0,1,0,1,0],
                           [0,0,0,0,0]],dtype=bool)
    return np.array_equal(pat!=5,canonical270)
