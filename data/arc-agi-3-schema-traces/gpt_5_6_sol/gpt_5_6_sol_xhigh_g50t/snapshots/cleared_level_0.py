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
    for y in range(7,h-4):
        for x in range(w-4):
            v=a[y:y+5,x:x+5]
            col=int(v[0,0])
            if col in (2,3,4,6,7,9) and v[2,2] == 5 and np.all(v[_RMASK] == col):
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
    y0=max(7,py-1); y1=min(a.shape[0]-1,py+6)
    x0=max(0,px-1); x1=min(a.shape[1],px+6)
    a[y0:y1,x0:x1]=5

def _actor_move(base,pos,action):
    if action not in _DIR:
        return pos
    px,py=pos; dx,dy=_DIR[action]
    nx,ny=px+dx,py+dy
    if nx<0 or ny<7 or nx+5>base.shape[1] or ny+5>base.shape[0]:
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
    if nx<0 or ny<7 or nx+5>base.shape[1] or ny+5>base.shape[0]:
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

def _advance_hud(a,loop,tape_len):
    oldx=1+4*loop; newx=oldx+4; col=2+loop
    old=a[1:4,oldx:oldx+3]
    old[old!=0]=col
    a[5,oldx:oldx+3]=0
    if newx+3<=a.shape[1]:
        a[1:4,newx:newx+3]=9
        a[2,newx+1]=0
        a[5,newx:newx+3]=9
    if tape_len>0:
        a[-1,max(0,a.shape[1]-tape_len):]=1
    return a

def predict(state,grid,action,x=None,y=None):
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
            if n>0: out[-1,max(0,out.shape[1]-n):]=1
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
        if n>0: base[-1,max(0,base.shape[1]-n):]=1

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

def is_goal(state,grid):
    return False
