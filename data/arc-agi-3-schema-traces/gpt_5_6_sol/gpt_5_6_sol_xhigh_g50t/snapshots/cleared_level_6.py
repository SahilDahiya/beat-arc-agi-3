import numpy as np

# Time-loop actors plus a wired remote block.
_RING9 = np.full((5,5), 9, dtype=int)
_RING9[2,2] = 5
_DIR = {1:(0,-6), 2:(0,6), 3:(-6,0), 4:(6,0)}
_RMASK = np.ones((5,5), dtype=bool)
_RMASK[2,2] = False
# The remote block is a 5x5 colour-8 shape open at the middle of
# its left edge (rows 1 and 3).
_BMASK = np.ones((5,5), dtype=bool)
_BMASK[1,0] = False
_BMASK[3,0] = False

def _find_entry_ring(a):
    h,w = a.shape
    for y in range(7,h-4):
        for x in range(w-4):
            if np.array_equal(a[y:y+5,x:x+5], _RING9):
                return (x,y)
    return None

def _find_remote(a):
    h,w = a.shape
    for y in range(7,h-4):
        for x in range(w-4):
            v = a[y:y+5,x:x+5]
            if np.all(v[_BMASK] == 8) and v[1,0] != 8 and v[3,0] != 8:
                return (x,y)
    return None

def _static_board():
    # Entry board stripped of the live actor and movable remote block.
    a = np.array(ENTRY_GRID, dtype=int).copy()
    p = _find_entry_ring(a)
    if p is not None:
        px,py = p
        a[py:py+5,px:px+5][_RMASK] = 5
        a[py+2,px+2] = 5
    q = _find_remote(a)
    if q is not None:
        qx,qy = q
        a[qy:qy+5,qx:qx+5][_BMASK] = 5
    return a

def init_state(entry_grid):
    a = np.array(entry_grid,dtype=int)
    if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 1:
        return _init_multi(a)
    p = _find_entry_ring(a)
    q = _find_remote(a)
    return {
        "start": p,
        "remote_start": q,
        "remote": q,
        "positions": [] if p is None else [p],
        "records": [],
        "current": [],
        "time": 0,
        "loop": 0,
        "cost": 0,
    }

def _visible_actors(a):
    out=[]
    h,w=a.shape
    for y in range(0,h-4):
        for x in range(w-4):
            v=a[y:y+5,x:x+5]
            col=int(v[0,0])
            if col in (2,3,4,6,7,9,14) and v[2,2] == 5 and np.all(v[_RMASK] == col):
                out.append((col,x,y))
    return out

def _clear_actors(a):
    b=a.copy()
    static=_static_board()
    for col,px,py in _visible_actors(a):
        # Actors also hide the centre of a wire tile, so restore all 25.
        b[py:py+5,px:px+5] = static[py:py+5,px:px+5]
    return b

def _clear_remote(a,pos):
    b=a.copy()
    if pos is not None:
        px,py=pos
        static=_static_board()
        v=b[py:py+5,px:px+5]
        sv=static[py:py+5,px:px+5]
        v[_BMASK]=sv[_BMASK]
    return b

def _sweep_remote_tile(a,pos):
    px,py=pos
    y0=max(0,py-1); y1=min(a.shape[0]-1,py+6)
    x0=max(0,px-1); x1=min(a.shape[1],px+6)
    a[y0:y1,x0:x1]=5

def _actor_move(base,pos,action):
    if action not in _DIR:
        return pos
    px,py=pos; dx,dy=_DIR[action]
    nx,ny=px+dx,py+dy
    if nx<0 or ny<0 or nx+5>base.shape[1] or ny+5>base.shape[0]:
        return pos
    static=_static_board()
    # Ordinary road, or the solid terminal pad (mixture of road and
    # wire but no void).  The thin one-pixel wire surrounded by 0 is
    # not itself walkable.
    v=base[ny:ny+5,nx:nx+5]
    if np.all((v == 5) | (v == 8) | (v == 9)):
        return (nx,ny)
    return pos

def _remote_move(base,pos,action):
    if pos is None or action not in _DIR:
        return pos
    px,py=pos; dx,dy=_DIR[action]
    nx,ny=px+dx,py+dy
    if nx<0 or ny<0 or nx+5>base.shape[1] or ny+5>base.shape[0]:
        return pos
    # The remote rides a thin track: its centre marks valid road.
    c=int(base[ny+2,nx+2])
    if c in (5,9):
        return (nx,ny)
    # The tether can be shortened by exactly one pitch from its entry
    # configuration; it cannot be compressed farther along itself.
    if c == 8 and pos == _find_remote(np.array(ENTRY_GRID,dtype=int)) and action == 4:
        return (nx,ny)
    return pos

def _on_wire(pos):
    if pos is None:
        return False
    x,y=pos
    s=_static_board()
    return 0 <= y+2 < s.shape[0] and 0 <= x+2 < s.shape[1] and s[y+2,x+2] == 8

def _draw_remote(a,pos):
    if pos is not None:
        px,py=pos
        a[py:py+5,px:px+5][_BMASK]=8
        # Its tether currently leaves through the middle of the right edge.
        if px+5 < a.shape[1]:
            a[py+2,px+5]=8
    return a

def _draw_actors(a,positions):
    for i,(px,py) in enumerate(positions):
        col=9 if i==len(positions)-1 else 2+i
        v=a[py:py+5,px:px+5]
        v[_RMASK]=col
        v[2,2]=5
    return a

def _paint_tape(a,n):
    if n>0:
        x0=max(0,a.shape[1]-n)
        v=a[-1,x0:]
        ent=np.array(ENTRY_GRID,dtype=int)[-1,x0:]
        v[ent==9]=1
    return a

def _advance_hud(a,loop,tape_len):
    # ENTRY_GRID shows every earlier slot in its initial state, so on a
    # rewind recolour/clear ALL completed slots, not merely the newest.
    col=2
    for i in range(loop+1):
        oldx=1+4*i
        old=a[1:4,oldx:oldx+3]
        old[old!=0]=col
        a[2,oldx+1]=0
        a[5,oldx:oldx+3]=0
    newx=1+4*(loop+1)
    if newx+3<=a.shape[1]:
        a[1:4,newx:newx+3]=9
        a[2,newx+1]=0
        a[5,newx:newx+3]=9
    _paint_tape(a,tape_len)
    return a

def predict(state,grid,action,x=None,y=None):
    if state.get("multi",False):
        return _predict_multi(state,grid,action,x,y)
    a=np.array(grid,dtype=int)
    info={"level_up":False,"dead":False,"win":False}
    s={
        "start":state.get("start"),
        "remote_start":state.get("remote_start"),
        "remote":state.get("remote"),
        "positions":list(state.get("positions",[])),
        "records":[list(r) for r in state.get("records",[])],
        "current":list(state.get("current",[])),
        "time":int(state.get("time",0)),
        "loop":int(state.get("loop",0)),
        "cost":int(state.get("cost",0)),
    }
    if s["start"] is None:
        return a.tolist(),info,s

    visible=_visible_actors(a)
    live=[(px,py) for col,px,py in visible if col==9]
    if live and s["positions"]:
        s["positions"][-1]=live[0]
        # Recover the single globally-unrolled opening transition.
        if not s["records"] and not s["current"]:
            sx,sy=s["start"]; px,py=live[0]
            if px==sx and py!=sy and (py-sy)%6==0:
                s["current"]=[2 if py>sy else 1]*(abs(py-sy)//6)
                s["time"]=len(s["current"])
            elif py==sy and px!=sx and (px-sx)%6==0:
                s["current"]=[4 if px>sx else 3]*(abs(px-sx)//6)
                s["time"]=len(s["current"])
            s["cost"]=max(s["cost"],len(s["current"]))
    vr=_find_remote(a)
    if vr is not None:
        s["remote"]=vr

    base=_clear_actors(a)
    base=_clear_remote(base,s["remote"])

    if action in (1,2,3,4,5):
        s["cost"]+=1

    if action==5:
        if s["loop"] >= 1:
            # There are exactly two recording slots.  ACTION5 on the
            # second slot starts a fresh recording cycle, while the
            # cumulative action-cost tape remains spent.
            out=np.array(ENTRY_GRID,dtype=int).copy()
            n=s["cost"]//2
            _paint_tape(out,n)
            s["remote"]=s["remote_start"]
            s["positions"]=[s["start"]]
            s["records"]=[]
            s["current"]=[]
            s["time"]=0
            s["loop"]=0
            return out.tolist(),info,s
        s["records"].append(list(s["current"]))
        s["current"]=[]
        s["loop"]+=1
        s["time"]=0
        s["positions"]=[s["start"]]*(len(s["records"])+1)
        s["remote"]=s["remote_start"]
        # Starting playback rewinds the board dynamics to entry.
        base=np.array(ENTRY_GRID,dtype=int).copy()
        base=_advance_hud(base,s["loop"]-1,s["cost"]//2)
        base=_draw_remote(base,s["remote"])
        out=_draw_actors(base,s["positions"])
        return out.tolist(),info,s

    if action in _DIR:
        # Playback time advances only when the live actor actually moves.
        # Blocked live inputs leave every replay actor at its current point.
        old_positions=list(s["positions"])
        live_new=_actor_move(base,old_positions[-1],action)
        advance=(live_new != old_positions[-1])
        tentative=list(old_positions)
        replay_acts=[None]*len(s["records"])
        if advance:
            for i,rec in enumerate(s["records"]):
                ac=rec[s["time"]] if s["time"]<len(rec) else None
                replay_acts[i]=ac
                tentative[i]=_actor_move(base,old_positions[i],ac)
            tentative[-1]=live_new
            s["current"].append(action)
            s["time"]+=1

        # A replay actor's recorded signal takes precedence on the tick
        # it acts on/into the terminal.  Otherwise any actor holding the
        # terminal routes the CURRENT live direction.
        signal=None
        for i,ac in enumerate(replay_acts):
            if ac in _DIR and (_on_wire(old_positions[i]) or _on_wire(tentative[i])):
                signal=ac
                break
        if signal is None and (_on_wire(old_positions[-1]) or _on_wire(tentative[-1])):
            signal=action
        if signal is not None:
            old_remote=s["remote"]
            new_remote=_remote_move(base,old_remote,signal)
            if new_remote != old_remote:
                if new_remote == s["remote_start"]:
                    ent=np.array(ENTRY_GRID,dtype=int)
                    base[7:-1,:]=ent[7:-1,:]
                    sx,sy=s["start"]
                    base[sy:sy+5,sx:sx+5][_RMASK]=5
                    base[sy+2,sx+2]=5
                else:
                    _sweep_remote_tile(base,old_remote)
                    _sweep_remote_tile(base,new_remote)
            s["remote"]=new_remote
        s["positions"]=tentative

        n=s["cost"]//2
        _paint_tape(base,n)

        # The colour-9 socket is the level destination (whether
        # reached by the live actor or, on some layouts, the remote).
        lx,ly=s["positions"][-1]
        if int(np.array(ENTRY_GRID)[ly+2,lx+2])==9:
            info["level_up"]=True
            info["win"]=(CURRENT_LEVEL==6)
            return base.tolist(),info,s
        if s["remote"] is not None:
            rx,ry=s["remote"]
            if int(np.array(ENTRY_GRID)[ry+2,rx+2])==9:
                info["level_up"]=True
                info["win"]=(CURRENT_LEVEL==6)
                return base.tolist(),info,s

        base=_draw_remote(base,s["remote"])
        out=_draw_actors(base,s["positions"])
        return out.tolist(),info,s

    return a.tolist(),info,s

# ---------- Multi-device layouts (levels with 3+ recording slots) ----------

def _remote_masks():
    out=[]
    for side in range(4):
        m=np.ones((5,5),dtype=bool)
        if side==0: m[0,1]=False; m[0,3]=False       # holes top
        elif side==1: m[4,1]=False; m[4,3]=False    # holes bottom
        elif side==2: m[1,0]=False; m[3,0]=False    # holes left
        else: m[1,4]=False; m[3,4]=False            # holes right
        out.append(m)
    return out

def _components8(a):
    unseen=set()
    ys,xs=np.where(a==8)
    for y,x in zip(ys.tolist(),xs.tolist()):
        if 0 <= y < a.shape[0]-1: unseen.add((y,x))
    comps=[]
    while unseen:
        q=unseen.pop(); stack=[q]; cc={q}
        while stack:
            y,x=stack.pop()
            for z in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if z in unseen:
                    unseen.remove(z); cc.add(z); stack.append(z)
        comps.append(cc)
    return comps

def _find_devices(a,start):
    masks=_remote_masks(); found=[]
    h,w=a.shape
    for y in range(0,h-4):
        for x in range(w-4):
            v=a[y:y+5,x:x+5]
            for side,m in enumerate(masks):
                if np.all(v[m]==8) and np.all(v[~m]!=8):
                    found.append((x,y,side))
    comps=_components8(a)
    devs=[]
    sx,sy=start
    xmod=sx%6; ymod=sy%6
    for rx,ry,side in found:
        comp=None
        for cc in comps:
            if any((ry+yy,rx+xx) in cc for yy in range(5) for xx in range(5)):
                comp=cc; break
        term=None
        if comp is not None:
            for ty in range(ymod, h-4, 6):
                for tx in range(xmod,w-4,6):
                    v=a[ty:ty+5,tx:tx+5]
                    n=int(np.sum(v==8))
                    if (ty+2,tx+2) in comp and 5 <= n < 20 and np.all((v==5)|(v==8)):
                        term=(tx,ty)
        attach={0:(0,1),1:(0,-1),2:(1,0),3:(-1,0)}[side]
        devs.append({"remote_start":(rx,ry),"remote":(rx,ry),
                     "terminal":term,"side":side,"attach":attach})
    return devs

def _components_color(a,col):
    unseen=set()
    ys,xs=np.where(a==col)
    for y,x in zip(ys.tolist(),xs.tolist()):
        if 0 <= y < a.shape[0]-1: unseen.add((y,x))
    comps=[]
    while unseen:
        q=unseen.pop(); stack=[q]; cc={q}
        while stack:
            y,x=stack.pop()
            for z in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if z in unseen:
                    unseen.remove(z); cc.add(z); stack.append(z)
        comps.append(cc)
    return comps

def _find_solid_devices(a,start):
    # Colour-11 devices use a solid 5x5 remote at one end of a thin
    # tether and a mixed 5/11 terminal aligned to the actor lattice.
    if start is None: return []
    remotes=[]
    h,w=a.shape
    for y in range(0,h-4):
        for x in range(w-4):
            if np.all(a[y:y+5,x:x+5]==11):
                remotes.append((x,y))
    comps=_components_color(a,11)
    sx,sy=start; xmod=sx%6; ymod=sy%6
    out=[]
    for rx,ry in remotes:
        comp=None
        for cc in comps:
            if (ry+2,rx+2) in cc:
                comp=cc; break
        term=None
        if comp is not None:
            for ty in range(ymod,h-4,6):
                if ty<7: continue
                for tx in range(xmod,w-4,6):
                    v=a[ty:ty+5,tx:tx+5]
                    n=int(np.sum(v==11))
                    if (ty+2,tx+2) in comp and 5<=n<20 and np.all((v==5)|(v==11)):
                        term=(tx,ty)
        if term is None: continue
        tx,ty=term
        dx=0 if tx==rx else (1 if tx>rx else -1)
        dy=0 if ty==ry else (1 if ty>ry else -1)
        # Human layouts use a straight tether.
        if dx!=0 and dy!=0: continue
        out.append({"remote_start":(rx,ry),"remote":(rx,ry),
                    "terminal":term,"attach":(dx,dy)})
    return out

def _find_portal_system(a,start):
    # Each connected colour-15 component is an independent pressure-powered
    # portal system: one mixed terminal wired to two outlined 7x7 pads.
    if start is None: return {"systems":[]}
    h,w=a.shape; allpads=[]
    border=np.ones((7,7),dtype=bool); border[1:6,1:6]=False
    for y in range(0,h-6):
        for x in range(w-6):
            v=a[y:y+7,x:x+7]
            if np.all(v[border]==15) and np.all(v[1:6,1:6]!=15):
                cells={(y+yy,x+xx) for yy in range(7) for xx in range(7) if border[yy,xx]}
                allpads.append(((x+1,y+1),cells))
    sx,sy=start; terms=[]
    for ty in range(sy%6,h-4,6):
        for tx in range(sx%6,w-4,6):
            v=a[ty:ty+5,tx:tx+5]; n=int(np.sum(v==15))
            if 5<=n<20 and np.all((v==5)|(v==15)):
                terms.append((tx,ty))
    systems=[]
    for comp in _components_color(a,15):
        pads=[p for p,cells in allpads if any(z in comp for z in cells)]
        cterms=[p for p in terms if (p[1]+2,p[0]+2) in comp]
        if cterms and len(pads)>=2:
            systems.append({"terminal":cterms[0],"pads":pads})
    return {"systems":systems}

def _slot_count(a):
    n=0
    while 1+4*n+3 <= a.shape[1]:
        v=a[1:4,1+4*n:1+4*n+3]
        if not (np.any(v!=0) and np.all((v==0)|(v==1)|(v==2)|(v==9))): break
        n+=1
    return max(1,n)

def _init_multi(a):
    p=_find_entry_ring(a)
    aux=None
    for col,x,y in _visible_actors(a):
        if col==14: aux=(x,y); break
    return {"multi":True,"start":p,"positions":[p],
            "records":[],"current":[],"time":0,"loop":0,"cost":0,
            "slots":_slot_count(a),"devices":_find_devices(a,p),
            "solid_devices":_find_solid_devices(a,p),"solid_focus":None,
            "portal":_find_portal_system(a,p),
            "aux_start":aux,"aux":aux,"aux_prev":None}

def _multi_static(devs,solid_devs):
    a=np.array(ENTRY_GRID,dtype=int).copy()
    p=_find_entry_ring(a)
    if p is not None:
        px,py=p; a[py:py+5,px:px+5][_RMASK]=5; a[py+2,px+2]=5
    for col,px,py in _visible_actors(a):
        if col==14:
            a[py:py+5,px:px+5][_RMASK]=5; a[py+2,px+2]=5
    masks=_remote_masks()
    for d in devs:
        rx,ry=d["remote_start"]; a[ry:ry+5,rx:rx+5][masks[d["side"]]]=5
    for d in solid_devs:
        rx,ry=d["remote_start"]; a[ry:ry+5,rx:rx+5]=5
    return a

def _multi_clear_actors(a,devs,solid_devs):
    b=a.copy(); st=_multi_static(devs,solid_devs)
    for col,px,py in _visible_actors(a):
        b[py:py+5,px:px+5]=st[py:py+5,px:px+5]
    return b

def _multi_clear_remotes(a,devs,solid_devs):
    b=a.copy(); st=_multi_static(devs,solid_devs); masks=_remote_masks()
    for d in devs:
        rx,ry=d["remote"]; m=masks[d["side"]]
        b[ry:ry+5,rx:rx+5][m]=st[ry:ry+5,rx:rx+5][m]
        ax,ay=d["attach"]; cx=rx+2+3*ax; cy=ry+2+3*ay
        if 0<=cx<b.shape[1] and 0<=cy<b.shape[0]-1:
            b[cy,cx]=st[cy,cx]
    return b

def _multi_clear_solid_remotes(a,solid_devs):
    b=a.copy()
    for d in solid_devs:
        rx,ry=d["remote"]
        # Once shifted, the swept gate area is ordinary floor.
        b[ry:ry+5,rx:rx+5]=5
    return b

def _multi_actor_move(base,pos,action,blocked_remotes=()):
    if action not in _DIR: return pos
    px,py=pos; dx,dy=_DIR[action]; nx,ny=px+dx,py+dy
    if nx<0 or ny<0 or nx+5>base.shape[1] or ny+5>base.shape[0]-1: return pos
    # Dynamic remotes are cleared from `base` so their old artwork can be
    # redrawn cleanly, but they remain physical blocks at their lattice tile.
    if (nx,ny) in blocked_remotes: return pos
    v=base[ny:ny+5,nx:nx+5]
    if np.all((v==5)|(v==8)|(v==9)|(v==11)|(v==15)): return (nx,ny)
    return pos

def _multi_remote_move(base,d,action):
    pos=d["remote"]
    if action not in _DIR: return pos
    px,py=pos; dx,dy=_DIR[action]; nx,ny=px+dx,py+dy
    if nx<0 or ny<0 or nx+5>base.shape[1] or ny+5>base.shape[0]-1: return pos
    c=int(base[ny+2,nx+2])
    if c in (5,9): return (nx,ny)
    # Permit one-pitch shortening along the original tether.
    ax,ay=d["attach"]
    if c==8 and pos==d["remote_start"] and (dx,dy)==(6*ax,6*ay): return (nx,ny)
    return pos

def _multi_draw_remotes(a,devs):
    masks=_remote_masks()
    for d in devs:
        rx,ry=d["remote"]; a[ry:ry+5,rx:rx+5][masks[d["side"]]]=8
        ax,ay=d["attach"]; cx=rx+2+3*ax; cy=ry+2+3*ay
        if 0<=cx<a.shape[1] and 0<=cy<a.shape[0]-1: a[cy,cx]=8
    return a

def _multi_draw_solid_remotes(a,solid_devs):
    for d in solid_devs:
        rx,ry=d["remote"]
        a[ry:ry+5,rx:rx+5]=11
        ax,ay=d["attach"]; cx=rx+2+3*ax; cy=ry+2+3*ay
        if 0<=cx<a.shape[1] and 0<=cy<a.shape[0]-1:
            a[cy,cx]=11
    return a

def _clone_colour(i):
    # Every completed replay is the same colour-2 ghost; slot identity is
    # conveyed by its trajectory rather than a different colour.
    return 2

def _multi_draw_actors(a,positions):
    for i,(px,py) in enumerate(positions):
        col=9 if i==len(positions)-1 else _clone_colour(i)
        v=a[py:py+5,px:px+5]; v[_RMASK]=col; v[2,2]=5
    return a

def _multi_aux_move(base,pos,prev,blocked_remotes=()):
    # Colour-14 is an automatic track runner: on each successful live tick
    # it takes the unique walkable continuation other than the tile it came
    # from.  At a closed gate/no continuation it waits rather than reversing.
    if pos is None: return pos,prev,None
    choices=[]
    for ac in (1,2,3,4):
        q=_multi_actor_move(base,pos,ac,blocked_remotes)
        if q!=pos and q!=prev: choices.append((ac,q))
    if len(choices)==1:
        ac,q=choices[0]; return q,pos,ac
    if len(choices)==0 and prev is not None:
        # At a true endpoint or a temporarily closed gate the runner bounces
        # back along the tile it came from rather than waiting in place.
        px,py=pos; qx,qy=prev
        ac=1 if qy<py else 2 if qy>py else 3 if qx<px else 4
        q=_multi_actor_move(base,pos,ac,blocked_remotes)
        if q==prev: return q,pos,ac
    return pos,prev,None

def _multi_draw_aux(a,pos):
    if pos is not None:
        px,py=pos; v=a[py:py+5,px:px+5]; v[_RMASK]=14; v[2,2]=5
    return a

def _predict_multi(state,grid,action,x=None,y=None):
    a=np.array(grid,dtype=int)
    info={"level_up":False,"dead":False,"win":False}
    s={"multi":True,"start":state["start"],"positions":list(state["positions"]),
       "records":[list(r) for r in state["records"]],"current":list(state["current"]),
       "time":int(state["time"]),"loop":int(state["loop"]),"cost":int(state["cost"]),
       "slots":int(state["slots"]),"devices":[dict(d) for d in state["devices"]],
       "solid_devices":[dict(d) for d in state.get("solid_devices",[])],
       "solid_focus":state.get("solid_focus"),
       "portal":{"systems":[{"terminal":q.get("terminal"),"pads":list(q.get("pads",[]))}
                              for q in state.get("portal",{}).get("systems",[])]},
       "aux_start":state.get("aux_start"),"aux":state.get("aux"),
       "aux_prev":state.get("aux_prev")}
    base=_multi_clear_actors(a,s["devices"],s["solid_devices"])
    base=_multi_clear_remotes(base,s["devices"],s["solid_devices"])
    base=_multi_clear_solid_remotes(base,s["solid_devices"])
    # An empty ACTION5 cannot finalize/rewind a slot, but it still spends
    # one action on the cumulative tape.  The cost can be visually latent
    # until the next action crosses a floor(cost/2) boundary.
    if action==5 and not s["current"]:
        s["cost"]+=1
        out=a.copy(); _paint_tape(out,s["cost"]//2)
        return out.tolist(),info,s
    if action in (1,2,3,4,5): s["cost"]+=1

    if action==5:
        # A rewind preserves only the most recently activated solid
        # device; other solid latches return to their entry positions.
        focus=s.get("solid_focus")
        if s["loop"] >= s["slots"]-1:
            out=np.array(ENTRY_GRID,dtype=int).copy()
            fresh=_init_multi(np.array(ENTRY_GRID,dtype=int)); fresh["cost"]=s["cost"]
            fresh["solid_focus"]=focus
            for i,d in enumerate(s["solid_devices"]):
                if i<len(fresh["solid_devices"]):
                    remote=d["remote"] if i==focus else d["remote_start"]
                    fresh["solid_devices"][i]["remote"]=remote
                    if remote!=d["remote_start"]:
                        _sweep_remote_tile(out,d["remote_start"])
                        _sweep_remote_tile(out,remote)
            out=_multi_draw_solid_remotes(out,fresh["solid_devices"])
            n=s["cost"]//2
            _paint_tape(out,n)
            return out.tolist(),info,fresh
        s["records"].append(list(s["current"])); s["current"]=[]
        s["loop"]+=1; s["time"]=0
        s["positions"]=[s["start"]]*(len(s["records"])+1)
        s["aux"]=s.get("aux_start"); s["aux_prev"]=None
        for d in s["devices"]: d["remote"]=d["remote_start"]
        for i,d in enumerate(s["solid_devices"]):
            if i!=focus: d["remote"]=d["remote_start"]
        base=np.array(ENTRY_GRID,dtype=int).copy()
        base=_advance_hud(base,s["loop"]-1,s["cost"]//2)
        for d in s["solid_devices"]:
            if d["remote"]!=d["remote_start"]:
                _sweep_remote_tile(base,d["remote_start"])
                _sweep_remote_tile(base,d["remote"])
        base=_multi_draw_solid_remotes(base,s["solid_devices"])
        base=_multi_draw_aux(base,s.get("aux"))
        out=_multi_draw_actors(base,s["positions"])
        return out.tolist(),info,s

    if action in _DIR:
        old=list(s["positions"])
        blocked=tuple(d["remote"] for d in s["devices"]+s["solid_devices"])
        live_new=_multi_actor_move(base,old[-1],action,blocked)
        advance=(live_new!=old[-1])
        tentative=list(old); racts=[None]*len(s["records"])
        aux_old=s.get("aux"); aux_prev=s.get("aux_prev"); aux_new=aux_old; aux_act=None
        if advance:
            for i,rec in enumerate(s["records"]):
                ac=rec[s["time"]] if s["time"]<len(rec) else None
                racts[i]=ac; tentative[i]=_multi_actor_move(base,old[i],ac,blocked)
            tentative[-1]=live_new
            if aux_old is not None:
                aux_new,aux_prev,aux_act=_multi_aux_move(base,aux_old,aux_prev,blocked)
            s["current"].append(action); s["time"]+=1

        # Each colour-15 controller independently powers its paired pads.
        # Normal, replay, and automatic auxiliary actors can power or traverse.
        for ps in s["portal"].get("systems",[]):
            pterm=ps.get("terminal"); pads=ps.get("pads",[])
            powered=(pterm is not None and len(pads)==2 and
                     (any(p==pterm for p in tentative) or aux_new==pterm))
            if not powered: continue
            warped=list(tentative)
            for i,p in enumerate(tentative):
                if p==pads[0] and old[i]!=pads[0]: warped[i]=pads[1]
                elif p==pads[1] and old[i]!=pads[1]: warped[i]=pads[0]
            tentative=warped
            if aux_new==pads[0] and aux_old!=pads[0]:
                aux_new=pads[1]; aux_prev=None
            elif aux_new==pads[1] and aux_old!=pads[1]:
                aux_new=pads[0]; aux_prev=None

        # Colour-8 devices are pressure plates: the remote is retracted
        # exactly while at least one actor occupies the connected terminal.
        for d in s["devices"]:
            ox,oy=d["remote"]; sx,sy=d["remote_start"]; ax,ay=d["attach"]
            occupied=any(p==d["terminal"] for p in tentative) or aux_new==d["terminal"]
            nr=(sx+6*ax,sy+6*ay) if occupied else (sx,sy)
            if nr!=(ox,oy):
                if occupied:
                    _sweep_remote_tile(base,(ox,oy)); _sweep_remote_tile(base,nr)
                else:
                    ent=np.array(ENTRY_GRID,dtype=int)
                    x0=max(0,min(ox,sx)-1); x1=min(base.shape[1],max(ox,sx)+6)
                    y0=max(0,min(oy,sy)-1); y1=min(base.shape[0]-1,max(oy,sy)+6)
                    base[y0:y1,x0:x1]=ent[y0:y1,x0:x1]
                d["remote"]=nr

        solid_signals={}
        for i,ac in enumerate(racts):
            if ac not in _DIR: continue
            for j,d in enumerate(s["solid_devices"]):
                # Solid toggles are edge-triggered only when an actor ENTERS.
                if old[i]!=d["terminal"] and tentative[i]==d["terminal"]:
                    solid_signals[j]=ac
        # The rotated auxiliary can trigger a solid like another non-live
        # actor, without changing which latch persists through a rewind.
        if aux_old is not None and aux_act in _DIR:
            for j,d in enumerate(s["solid_devices"]):
                if aux_old!=d["terminal"] and aux_new==d["terminal"]:
                    solid_signals[j]=aux_act
        # Replay actors can toggle a latch for this run, but only a LIVE
        # activation changes which solid device is retained on the rewind.
        live_solid_entries=set()
        for j,d in enumerate(s["solid_devices"]):
            if old[-1]!=d["terminal"] and tentative[-1]==d["terminal"]:
                live_solid_entries.add(j)
                if j not in solid_signals: solid_signals[j]=action
        for j,ac in solid_signals.items():
            d=s["solid_devices"][j]
            if j in live_solid_entries: s["solid_focus"]=j
            # Solid devices are persistent two-position toggles: every
            # activation reverses the remote between extended and retracted.
            ox,oy=d["remote"]; sx,sy=d["remote_start"]; ax,ay=d["attach"]
            if (ox,oy)==(sx,sy):
                nr=(sx+6*ax,sy+6*ay)
                _sweep_remote_tile(base,(ox,oy)); _sweep_remote_tile(base,nr)
            else:
                # Toggling closed restores the original wall/tether around
                # both positions rather than leaving the swept opening.
                nr=(sx,sy); ent=np.array(ENTRY_GRID,dtype=int)
                x0=max(0,min(ox,sx)-1); x1=min(base.shape[1],max(ox,sx)+6)
                y0=max(0,min(oy,sy)-1); y1=min(base.shape[0]-1,max(oy,sy)+6)
                base[y0:y1,x0:x1]=ent[y0:y1,x0:x1]
            d["remote"]=nr

        s["positions"]=tentative; s["aux"]=aux_new; s["aux_prev"]=aux_prev
        n=s["cost"]//2
        _paint_tape(base,n)
        lx,ly=s["positions"][-1]
        if int(np.array(ENTRY_GRID)[ly+2,lx+2])==9:
            info["level_up"]=True; info["win"]=(CURRENT_LEVEL==6)
            return base.tolist(),info,s
        for d in s["devices"]+s["solid_devices"]:
            rx,ry=d["remote"]
            if int(np.array(ENTRY_GRID)[ry+2,rx+2])==9:
                info["level_up"]=True; info["win"]=(CURRENT_LEVEL==6)
                return base.tolist(),info,s
        base=_multi_draw_remotes(base,s["devices"])
        base=_multi_draw_solid_remotes(base,s["solid_devices"])
        base=_multi_draw_aux(base,s.get("aux"))
        out=_multi_draw_actors(base,s["positions"])
        return out.tolist(),info,s
    return a.tolist(),info,s

def is_goal(state,grid):
    return False
