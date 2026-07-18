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
    base=(_render_level6_fog(out.copy(),base_only=True)
          if int(CURRENT_LEVEL or 0)==6 else _base_grid())
    for gx,gy,_ in _level_goals(out):
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
    mobile_palette=(int(CURRENT_LEVEL or 0)==5 and np.any(z==14) and
                    np.any(z==0) and np.all(np.isin(z,[0,3,8,9,12,14])))
    if np.any(z==11) or mobile_entry or mobile_palette:
        out[y0:y1+1,x0:x1+1]=3
    else:
        out[y0:y1+1,x0:x1+1]=z

def _apply_bumper(out,x0,y0,token):
    # A solid 5-cell colour-1 bar launches the token away, sliding by macro-cells
    # until the next 5x5 footprint is not plain corridor.
    h,w=out.shape
    # On the fog board, newly discovered bumpers are absent from ENTRY_GRID but
    # are necessarily visible beside the token when they fire.
    base=(_render_level6_fog(out.copy(),base_only=True)
          if int(CURRENT_LEVEL or 0)==6 else _base_grid())
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
        footprint=(base[ny:ny+5,nx:nx+5]
                   if int(CURRENT_LEVEL or 0)==6 else out[ny:ny+5,nx:nx+5])
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

def _level_goals(a):
    # The fog board's lock is absent from ENTRY_GRID; derive it from the grounded
    # static map rather than from whichever portion happens to be illuminated.
    if int(CURRENT_LEVEL or 0)==6:
        base=_render_level6_fog(np.array(a,dtype=int).copy(),base_only=True)
        return _goal_patterns(base) if base is not None else []
    return _goal_patterns(np.array(ENTRY_GRID,dtype=int))

def _matching_goal(a):
    if a.shape[0]<63 or a.shape[1]<11:
        return None
    for goal in _level_goals(a):
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
    for goal in _level_goals(a):
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
    if int(CURRENT_LEVEL or 0)==6:
        # The lower-right refill powers a concealed vertical rotary patrol.
        # It begins at x54,y10 and advances through the six-cell y5..30 track.
        if not bool(st.get("rotary6_active",False)):
            return
        sprite=np.array([[3,3,3,3,3],
                         [3,3,0,3,3],
                         [3,1,0,0,3],
                         [3,3,1,3,3],
                         [3,3,3,3,3]])
        x0,y0=st.get("rotary6_pos",(54,10))
        d=1 if st.get("rotary6_dir",1)>=0 else -1
        hidden=bool(st.get("rotary6_hidden",False))
        if st.pop("rotary6_just",False):
            return
        tok=_token_bbox(out)
        if direct_contact and not hidden and tok is not None and tuple(tok[:2])==(x0,y0):
            st["rotary6_hidden"]=True
            return
        static=_render_level6_fog(out.copy(),base_only=True)
        if not hidden:
            # Clear the entire previous footprint even when fog exposed only part
            # of the sprite; otherwise a clipped glyph cell would trail behind.
            out[y0:y0+5,x0:x0+5]=static[y0:y0+5,x0:x0+5]
        ny=y0+5*d
        if ny<5 or ny>30:
            d=-d
            ny=y0+5*d
        tok=_token_bbox(out)
        if tok is not None and tuple(tok[:2])==(54,ny):
            _rotate_hud(out)
            hidden=True
        else:
            out[ny:ny+5,54:59]=sprite
            hidden=False
        st["rotary6_pos"]=(54,ny)
        st["rotary6_dir"]=d
        st["rotary6_hidden"]=hidden
        return
    entry_switches=_floor_switches(entry)
    starts=[(x,y) for x,y,has1 in entry_switches if has1]
    if not (starts and any(not has1 for _,_,has1 in entry_switches)):
        return
    sx,sy=starts[0]
    sprite=entry[sy:sy+5,sx:sx+5].copy()
    x0,y0=st.get("mobile_pos",(sx,sy))
    d=1 if st.get("mobile_dir",1)>=0 else -1
    hidden=bool(st.get("mobile_hidden",False))

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
    static=(_render_level6_fog(out.copy(),base_only=True)
            if int(CURRENT_LEVEL or 0)==6 else None)
    if not hidden and np.array_equal(out[y0:y0+5,x0:x0+5],sprite):
        out[y0:y0+5,x0:x0+5]=(static[y0:y0+5,x0:x0+5]
                              if static is not None else 3)

    tok=_token_bbox(out)
    if tok is not None and tuple(tok[:2])==(nx,y0):
        # The rotary can run into the player: this is the same activation.
        _rotate_hud(out)
        hidden=True
    elif np.all((static[y0:y0+5,nx:nx+5] if static is not None
                 else out[y0:y0+5,nx:nx+5])==3):
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
        "mobile_left":left,"mobile_right":right,"locks_done":(),"pads_done":(),
        "rotary6_active":False,"rotary6_pos":(54,10),"rotary6_dir":1,
        "rotary6_hidden":False}

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

def _render_level6_fog(out,base_only=False,st=None):
    """Build the static fog-board map or render its token-centred light disk.

    The visible region is the radius-20 raster disk centred at (+1.5,+1.5)
    inside the token.  ENTRY_GRID supplies its initially visible static map;
    later observations ground terrain that was initially concealed by colour5.
    """
    if int(CURRENT_LEVEL or 0)!=6:
        return
    entry=np.array(ENTRY_GRID,dtype=int)
    start=_token_bbox(entry)
    now=_token_bbox(out)
    if start is None or now is None:
        return
    # Visibility is a radius-20 disk.  Its raster centre lies at (+1.5,+1.5)
    # inside the 5x5 token footprint; the half-cell centre explains the one-cell
    # asymmetry of opposite arcs that a translated ENTRY stencil cannot capture.
    px,py=now[0],now[1]
    yy,xx=np.ogrid[:out.shape[0],:out.shape[1]]
    mask=((xx-(px+1.5))**2 + (yy-(py+1.5))**2 <= 400.0)
    base=_base_grid()
    # Colour5 is genuine outside-map void as well as the visibility veil, so
    # unseen cells remain 5 until a translated view exposes their static map
    # content.  The first upward probe exposed this northern wall fringe.
    north=[(4,36),(4,37),(4,38),(4,38),(4,39)]
    for yy,(lo,hi) in enumerate(north):
        for xx in range(lo,hi+1):
            if base[yy,xx]==5: base[yy,xx]=4
    base[5,4]=4; base[5,37:39]=4
    base[6,38]=4
    # A refill pad is partially exposed at x39,y5; its standard 5x5 ring
    # determines the still-veiled pixels of that object.
    base[5:10,39:44]=np.array([[3,3,3,3,3],
                               [3,11,11,11,3],
                               [3,11,3,11,3],
                               [3,11,11,11,3],
                               [3,3,3,3,3]])
    base[10:13,40]=3
    # Lower-left wall pixels exposed after translating the view two cells west.
    base[28:31,4]=4
    base[30,5]=4
    # Southern boundary/corridor exposed while descending the left column.
    base[31,4:7]=4
    base[32,4:8]=4
    base[33,4:9]=4; base[33,9]=3
    base[34,4:9]=4; base[34,9:11]=3
    base[35,4:9]=4; base[35,9:13]=3
    base[36,7:9]=4; base[36,9:15]=3
    # Further north/south static map revealed at x9,y20.
    base[2,7:15]=4
    base[3,4:19]=4
    base[4,4:21]=4
    base[36,4:7]=4; base[36,15:17]=3
    base[37,4:9]=4; base[37,9:24]=3
    base[38,4:9]=4; base[38,9:22]=3
    base[39,4:9]=4; base[39,9:21]=3
    base[40,4:9]=4; base[40,9:19]=3
    base[41,7:9]=4; base[41,14]=3
    # The southern reveal identifies the top of a standard palette at x9,y40.
    base[40:45,9:14]=np.array([[3,3,3,3,3],
                               [3,9,14,14,3],
                               [3,9,0,8,3],
                               [3,12,12,8,3],
                               [3,3,3,3,3]])
    # View at x9,y25 exposes the southern control room and boundary.
    base[36,25:29]=4
    base[37,24:28]=4
    base[38,22:24]=3; base[38,24:27]=4
    base[39,21:24]=3; base[39,24:27]=4
    base[40,19:24]=3; base[40,24:26]=4
    base[41,4:7]=4; base[41,15:20]=3; base[41,24]=4
    base[42:45,4:9]=4
    base[42,14:21]=3
    base[43,14:21]=3
    base[44,14:21]=3
    base[45,4:14]=4; base[45,14:19]=3
    base[46,7:14]=4; base[46,14]=3
    # The partially exposed glyph is the standard all-zero selector at x19,y40.
    base[40:45,19:24]=np.array([[3,3,3,3,3],
                                [3,0,3,3,3],
                                [3,3,0,0,3],
                                [3,3,0,3,3],
                                [3,3,3,3,3]])
    # Moving east from x9,y25 exposes the control room's southeast wall
    # taper and a fourth standard refill centred at x14,y45.
    base[32,34]=3
    base[33,32:35]=3
    base[34,31:35]=3
    base[35:37,29:34]=3
    base[37,28]=4; base[37,29:33]=3
    base[38:40,27:29]=4; base[38:40,29:32]=3
    base[40,26:29]=4; base[40,29:31]=3
    base[41,25:29]=4; base[41,29]=3
    base[42,24:29]=4
    base[43,24:27]=4
    base[44,24:26]=4
    base[45,19:24]=4
    base[45:50,14:19]=np.array([[3,3,3,3,3],
                                [3,11,11,11,3],
                                [3,11,3,11,3],
                                [3,11,11,11,3],
                                [3,3,3,3,3]])
    base[46,19]=4
    # The next eastward view exposes the long right-hand floor wedge and the
    # horizontal colour-1 bumper that caps its southeast branch.
    base[23:25,40]=3
    base[25:27,39:41]=3
    base[27,38:41]=3
    base[28:30,37:41]=3
    base[30,36:41]=3
    base[31:35,35:40]=3
    base[35,34:39]=1
    base[36,34:39]=4
    base[37,33]=3; base[37,34:38]=4
    base[38:40,32:34]=3; base[38:40,34:37]=4
    base[40,31:34]=3; base[40,34:36]=4
    base[41,30:34]=3; base[41,34]=4
    base[42,29:34]=3
    base[43,27:29]=4; base[43,29:32]=3
    base[44,26:29]=4; base[44,29:31]=3
    base[45,24:29]=4
    base[46,20:25]=4
    # A second eastward translation exposes the west wall continuation and the
    # far-right zig-zag corridor, including its two colour-1 bumper segments.
    base[17:19,8]=4
    base[19:21,7:9]=4
    base[21:23,7:9]=4
    base[23:31,6:9]=4
    base[31:35,7:9]=4
    base[35:37,8]=4
    base[14,41]=3
    base[15,41]=4
    base[16,41:43]=4
    base[17:19,41:44]=4
    base[19,41:44]=1; base[19,44]=4
    base[20,41:44]=3; base[20,44]=4
    base[21:23,40:44]=3; base[21:23,44]=4
    base[23:30,41:44]=3; base[23:30,44:46]=4
    base[30,41:44]=3; base[30,44]=1; base[30,45]=4
    base[31:35,40:44]=3; base[31:35,44]=1
    base[35:37,39:44]=3
    base[37,38]=4; base[37,39:43]=3
    base[38:40,37:39]=4; base[38:40,39:42]=3
    base[40,36:39]=4; base[40,39:41]=3
    base[41,35:39]=4; base[41,39]=3
    base[42,34:39]=4
    base[43,32:34]=3; base[43,34:37]=4
    base[44,31:34]=3; base[44,34:36]=4
    base[45,29:34]=3
    base[46,25:29]=4; base[46,29]=3
    # At x29,y25 the light reaches the outer-right wall and the return corridor
    # behind it; these cells complete the next five-column slice of the maze.
    base[10,41]=3
    base[11,41:44]=3
    base[12,41:44]=3; base[12,44]=4
    base[13,41:44]=3; base[13,44:46]=4
    base[14,42:44]=3; base[14,44:47]=4
    base[15,42:47]=4
    base[16,43:48]=4
    base[17:19,44:49]=4
    base[19:23,45:49]=4; base[19:23,49]=3
    base[23:31,46:49]=4; base[23:31,49:51]=3
    base[31:35,45:49]=4; base[31:35,49]=3
    base[35:37,44:49]=3
    base[37,43:48]=3
    base[38:40,42:47]=3
    base[40,41:46]=3
    base[41,40:45]=3
    base[42,39:44]=3
    base[43,37:39]=4; base[43,39:42]=3
    base[44,36:39]=4; base[44,39:41]=3
    base[45,34:39]=4
    base[46,30:34]=3; base[46,34]=4
    # Entering the central refill shifts the disk north and exposes the upper
    # outer-wall taper plus the beginning of its east-side floor lane.
    base[4,40]=4
    base[7,44]=4
    base[8,44:46]=4
    base[9,44:47]=4
    base[10,42:44]=3; base[10,44:47]=4
    base[11,44:48]=4
    base[12,45:49]=4
    base[13,46:49]=4
    base[14:16,47:49]=4; base[14:16,49]=3
    base[16,48]=4; base[16,49]=3
    base[17,49]=3
    base[18,49:51]=3
    base[19:23,50]=3
    # The east step from the central refill exposes the far-right open chamber,
    # its upper wall taper, and the edge of another standard refill at x49,y5.
    base[2,39]=4
    base[3,39:44]=4
    base[4,41:46]=4
    base[5,44:47]=4
    base[6,44:49]=4
    base[7,45:49]=4
    base[8,46:49]=4
    base[9,47:49]=4
    base[5:10,49:54]=np.array([[3,3,3,3,3],
                               [3,11,11,11,3],
                               [3,11,3,11,3],
                               [3,11,11,11,3],
                               [3,3,3,3,3]])
    base[10,47:49]=4; base[10,49:52]=3
    base[11,48]=4; base[11,49:53]=3
    base[12:14,49:54]=3
    base[14:18,50:55]=3
    base[18:26,51:56]=3
    base[26:30,51:55]=3
    base[30,51:54]=3
    base[31,50:54]=3
    base[32,50:53]=3
    base[33:35,50:52]=3
    base[35,49:51]=3
    base[36,49]=3
    base[37,48]=3
    # The upper bumper reveals the entire lower-right chamber in one launch.
    # Ground every non-fog pixel from that view; colour5 remains unknown/void.
    lower_rows=[
      '5555555555555555555555555533333333333333333344444333333355555555',
      '5555555555555555555555555333333333333333333344444333333335555555',
      '5555555555555555555555555444433333333333333314444333333335555555',
      '5555555555555555555555554444433333333333333314444333333333555555',
      '5555555555555555555555544444433333333333333314444333333333355555',
      '5555555555555555555555544444433333333333333314444333333333355555',
      '5555555555555555555555444444433333333333333314444333333333345555',
      '5555555555555555555555334444433333111113333333333333333333345555',
      '5555555555555555555555334444433333444443333333333333333333345555',
      '5555555555555555555555334444433333444443333333333333333333345555',
      '5555555555555555555553334444433333444443333333333333333333344555',
      '5555555555555555555553334444433333444443333333333333333333344555',
      '555555555555555555555333444443333344444ccccc33333333333333344555',
      '555555555555555555555333444443333344444ccccc33333333333333344555',
      '5555555555555555555550034444433333444449999933333333333333344555',
      '5555555555555555555550334444433333444449999933333333333333344555',
      '5555555555555555555553334444433333444449999933333333333333344555',
      '5555555555555555555554444444433333444444444444444333334444444555',
      '5555555555555555555555444444433333444444444444444333334444445555',
      '5555555555555555555555444444433333444444444444444333334444445555',
      '5555555555555555555555444443333333334444444444444333334444445555',
      '5555555555555555555555444443555555534444444444444333334444445555',
      '5555555555555555555555544443555555534444444433333333333333355555',
      '5555555555555555555555544443558585534444444433333333333bbb355555',
      '5555555555555555555555554443558855534444444433333333333b3b555555',
      '5555555555555555555555555443555885534444444433333333333bb5555555',
      '5555555555555555555555555443555555534444444433333333333335555555',
      '55555cc555555555555555555543555555534444444444444444444455555555',
      '55555cc555555555555555555553333333334444444444444444444555555555',
      '55555cc555555555555555555555444444444444444444444444445555555555',
      '55555cc555555555555555555555554444444444444444444444555555555555',
      '555cccccc5555555555555555555555444444444444444444445555555555555',
      '555cccccc5555555555555555555555555555555555555555555555555555555']
    for yy,row in enumerate(lower_rows,28):
        for xx,ch in enumerate(row):
            if ch!='5':
                base[yy,xx]=int(ch,16)
    # The token hides corridor at its landing footprint.
    base[40:45,39:44]=3
    # The lower-right partial 11-ring is another standard refill.
    base[50:55,54:59]=np.array([[3,3,3,3,3],
                                [3,11,11,11,3],
                                [3,11,3,11,3],
                                [3,11,11,11,3],
                                [3,3,3,3,3]])
    # Eastward motion in the lower chamber exposes the screen-edge wall curve.
    base[25,56]=3
    base[26,55:59]=3
    base[27,55:59]=3; base[27,59]=4
    base[28,56:59]=3; base[28,59:61]=4
    base[29:31,57:59]=3; base[29:31,59:62]=4
    base[31,58]=3; base[31,59:63]=4
    base[32:34,59:64]=4
    base[34:38,60:64]=4
    base[38:46,61:64]=4
    base[46:50,60:64]=4
    base[50:52,59:64]=4
    base[52,59:63]=4
    base[53:55,59:62]=4
    base[55,56:61]=4
    base[56,55:60]=4
    base[57,54:59]=4
    base[58,52:57]=4
    base[59,51:56]=4
    # Final eastward screen-edge arcs.
    base[23,56:59]=3
    base[24,56:59]=3; base[24,59:61]=4
    base[25,57:59]=3; base[25,59:62]=4
    base[26,59:64]=4
    base[27,60:64]=4
    base[28,61:64]=4
    base[29:31,62:64]=4
    base[31,63]=4
    base[52,63]=4
    base[53:55,62:64]=4
    base[55,61:64]=4
    base[56,60:64]=4
    base[57,59:64]=4
    base[58,57:62]=4
    base[59,56:61]=4
    base[58,62:64]=4
    base[59,61:64]=4
    # Northward return in the powered chamber exposes the remaining east wall.
    base[12,54]=3
    base[13,54:59]=3
    base[14,55:59]=3; base[14,59:61]=4
    base[15,59:62]=4
    base[16:19,59:64]=4
    base[19,61:64]=4
    base[20,62:64]=4
    base[18,56:59]=3
    base[19,56:59]=3; base[19,59:61]=4
    base[20,56:59]=3; base[20,59:62]=4
    base[21:23,56:59]=3; base[21:23,59:64]=4
    base[23,59:64]=4
    base[24,61:64]=4
    base[25,62:64]=4
    # Final northern fringe exposed while synchronizing the powered rotary.
    base[7,54]=3
    base[8,54:59]=3
    base[9,54:59]=3; base[9,59:61]=4
    base[10,52:54]=3; base[10,59:62]=4
    base[11,53]=3; base[11,59:64]=4
    base[12:14,59:64]=4
    base[14,61:64]=4
    base[15,55:59]=3; base[15,62:64]=4
    base[16:18,55:59]=3
    # Extreme northern wall arc revealed when the patrol reaches y5.
    base[2,47:55]=4
    base[3,44:59]=4
    base[4,46:61]=4
    base[5,47:49]=4; base[5,59:62]=4
    base[6:9,59:64]=4
    base[9,61:64]=4
    base[10,54:59]=3; base[10,62:64]=4
    base[11,54:59]=3
    base[12,55:59]=3
    # Top screen-edge wall exposed at the northernmost player position.
    base[0,40:62]=4
    base[1,38:64]=4
    base[2,40:47]=4; base[2,55:64]=4
    base[3,59:64]=4
    base[4,61:64]=4
    base[5,54:59]=3; base[5,62:64]=4
    base[6,54:59]=3
    base[7,55:59]=3
    # Tiny southwest wall fringe exposed by the upper bumper landing.
    base[47,19:22]=4
    base[48,20:22]=4
    base[49,21]=4
    # Last northern launch fringe.
    base[0,37:40]=4
    # Lower-left wall arc revealed while approaching the palette.
    base[46,4:7]=4
    base[47,4:14]=4
    base[48,4:14]=4; base[48,19]=4
    base[49,4:14]=4; base[49,19:21]=4
    base[50,4:19]=4
    base[51,7:15]=4
    # Bottom-left screen boundary revealed one row farther south.
    base[50,19:23]=4
    base[51,4:23]=4
    base[52,0:24]=4
    base[53,0]=4; base[53,11:22]=4
    base[54,11:21]=4
    base[55,11:19]=4
    base[56,11:15]=4
    # Deepest southwest arc; it is visible through colour-5 HUD background.
    base[53,22:25]=4
    base[54,0]=4; base[54,21:25]=4
    base[55,0]=4; base[55,19:26]=4
    base[56,0]=4; base[56,15:25]=4
    base[57,0]=4; base[57,11:24]=4
    base[58,0]=4; base[58,11:22]=4
    base[59,11:21]=4
    base[60,11]=4
    base[61,11]=4
    # ENTRY contains the initial HUD glyph; it is not static maze terrain.
    # Keep its background transparent, then restore the grounded x=0 wall arc.
    base[53:63,0:11]=5
    base[53:59,0]=4
    # Southeast edge of the same HUD-overlapping wall arc.
    base[56,25:27]=4
    base[57,24:28]=4
    base[58,22:27]=4
    base[59,21:26]=4
    base[58,27:30]=4
    base[59,26:31]=4
    # Bottom screen edge exposed from the lower-left refill.
    base[59,0]=4
    base[62,11]=4
    base[63,5:12]=4
    # One-use refills must stay consumed after they leave the light disk.
    if st is not None:
        for qx,qy in st.get("pads_done",()):
            base[qy:qy+5,qx:qx+5]=3
    if base_only:
        return base
    for yy in range(55):
        for xx in range(out.shape[1]):
            if not mask[yy,xx]:
                out[yy,xx]=5
            elif out[yy,xx]==5:
                out[yy,xx]=base[yy,xx]
    # The HUD foreground is opaque but its colour-5 background is transparent:
    # illuminated maze walls can therefore show through even at x<11.
    hud_colours=(8,9,12,14)
    for yy in range(55,61):
        for xx in range(out.shape[1]):
            if xx<11 and out[yy,xx] in hud_colours:
                continue
            if not mask[yy,xx]:
                out[yy,xx]=5
            elif out[yy,xx]==5:
                out[yy,xx]=base[yy,xx]
    # On the two meter rows, only x<13 belongs to the HUD/background; preserve
    # the action meter and lives to the right.
    for yy in range(61,63):
        for xx in range(13):
            if xx<11 and out[yy,xx] in hud_colours:
                continue
            if not mask[yy,xx]:
                out[yy,xx]=5
            elif out[yy,xx]==5:
                out[yy,xx]=base[yy,xx]
    # The final screen row contains no HUD or meter and is ordinary fogged terrain.
    yy=out.shape[0]-1
    for xx in range(out.shape[1]):
        if not mask[yy,xx]:
            out[yy,xx]=5
        elif out[yy,xx]==5:
            out[yy,xx]=base[yy,xx]
    # The powered rotary patrols vertically and is clipped cell-by-cell by
    # the light disk, just like static terrain (a boundary may reveal one glyph cell).
    if st is not None and bool(st.get("rotary6_active",False)):
        rx,ry=st.get("rotary6_pos",(54,10))
        if tuple(now[:2])!=(rx,ry):
            sprite=np.array([[3,3,3,3,3],
                             [3,3,0,3,3],
                             [3,1,0,0,3],
                             [3,3,1,3,3],
                             [3,3,3,3,3]])
            for qy in range(ry,ry+5):
                for qx in range(rx,rx+5):
                    out[qy,qx]=sprite[qy-ry,qx-rx] if mask[qy,qx] else 5

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
                    done=set(st.get("pads_done",()))
                    done.add((nx0,ny0))
                    st["pads_done"]=tuple(sorted(done))
                    if int(CURRENT_LEVEL or 0)==6 and (nx0,ny0)==(54,50):
                        st.update({"rotary6_active":True,"rotary6_pos":(54,10),
                                   "rotary6_dir":1,"rotary6_hidden":False,
                                   "rotary6_just":True})
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
                    goals=_level_goals(a)
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
        cost=2 if int(CURRENT_LEVEL or 0) in (1,2,4,6) else 1
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
    _render_level6_fog(out,st=st)
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
