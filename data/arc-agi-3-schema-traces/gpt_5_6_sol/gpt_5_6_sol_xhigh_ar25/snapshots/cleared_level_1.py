# ARC3 world model: a source polyomino, its mirror image, movable mirror,
# and a target. Graphics use aligned 3x3 logical tiles.

def _blocks_with_value(a,value):
    ys,xs=np.where(a==value)
    return set((int(x)//3,int(y)//3) for y,x in zip(ys,xs)
               if int(x)<63 and int(y)<63)

def _initial_mode(entry):
    e=np.array(entry,dtype=int)
    z=_blocks_with_value(e,0)
    src=_blocks_with_value(e,5)
    axis=_blocks_with_value(e,10)
    if len(z & axis) > len(z & src):
        return "axis"
    return "source"

def init_state(entry_grid):
    return {"active":_initial_mode(entry_grid),"moves":[]}

def _scene(a):
    return (_blocks_with_value(a,5),  # source
            _blocks_with_value(a,4),  # reflected copy
            _blocks_with_value(a,10)) # vertical mirror

def _target():
    return _blocks_with_value(np.array(ENTRY_GRID,dtype=int),11)

def _pixels(blocks):
    out=set()
    for bx,by in blocks:
        for yy in range(3*by,3*by+3):
            for xx in range(3*bx,3*bx+3):
                out.add((xx,yy))
    return out

def _shift(blocks,dx,dy):
    return set((bx+dx,by+dy) for bx,by in blocks)

def _paint(a,b,colour,centre=None):
    bx,by=b; x0,y0=3*bx,3*by
    a[y0:y0+3,x0:x0+3]=colour
    if centre is not None:
        a[y0+1,x0+1]=centre

def _redraw(a,old_scene,new_scene,active):
    osrc,ocopy,oaxis=old_scene
    src,copy,axis=new_scene
    for xx,yy in _pixels(osrc|ocopy|oaxis):
        a[yy,xx]=9
    target=_target()
    for b in target:
        _paint(a,b,11)
    # The selected object is marked by black centres. An unselected source
    # has background centres; an unselected mirror is solid colour 10.
    axis_base = 9 if _initial_mode(ENTRY_GRID)=="axis" else 10
    for b in axis:
        _paint(a,b,10,0 if active=="axis" else axis_base)
    for b in src:
        _paint(a,b,5,0 if active=="source" else 9)
    for b in copy:
        _paint(a,b,4,11 if b in target else None)

def _can_place(a,blocks,old_dynamic,allowed):
    for xx,yy in _pixels(blocks):
        if not (0<=xx<63 and 0<=yy<63):
            return False
        if (xx,yy) in old_dynamic:
            continue
        if int(a[yy,xx]) not in allowed:
            return False
    return True

def _source_move(a,action,active):
    src,copy,axis=_scene(a)
    old=(src,copy,axis); oldpix=_pixels(src|copy|axis)
    dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
    cdx=-dx if action in (3,4) else dx
    ns=_shift(src,dx,dy)
    nc=_shift(copy,cdx,dy)
    if not _can_place(a,ns,oldpix,{9}):
        return False,False
    if not _can_place(a,nc,oldpix,{9,11}):
        return False,False
    _redraw(a,old,(ns,nc,axis),active)
    return True,bool(_target() and nc==_target())

def _axis_move(a,action,active):
    src,copy,axis=_scene(a)
    if action not in (3,4):
        return False,False
    old=(src,copy,axis); oldpix=_pixels(src|copy|axis)
    dx=-1 if action==3 else 1
    na=_shift(axis,dx,0)
    # Moving a vertical mirror one tile translates its reflection two tiles.
    nc=_shift(copy,2*dx,0)
    if not _can_place(a,na,oldpix,{9}):
        return False,False
    if not _can_place(a,nc,oldpix,{9,11}):
        return False,False
    _redraw(a,old,(src,nc,na),active)
    return True,bool(_target() and nc==_target())

def _undo(a,record,active):
    mode,action=record
    inv={1:2,2:1,3:4,4:3}[action]
    if mode=="source":
        _source_move(a,inv,active)
    else:
        _axis_move(a,inv,active)

def predict(state,grid,action,x=None,y=None):
    a=np.array(grid,dtype=int)
    st=dict(state or {})
    active=st.get("active",_initial_mode(ENTRY_GRID))
    moves=list(st.get("moves",[]))
    info={"level_up":False,"dead":False,"win":False}

    goal=False
    if action in (1,2,3,4):
        if active=="source":
            moved,goal=_source_move(a,action,active)
        else:
            moved,goal=_axis_move(a,action,active)
        if moved:
            moves.append((active,action))
    elif action==6 and x is not None and y is not None:
        src,copy,axis=_scene(a)
        b=(int(x)//3,int(y)//3)
        newactive=active
        if b in src:
            newactive="source"
        elif b in axis:
            newactive="axis"
        if newactive!=active:
            old=(src,copy,axis)
            active=newactive
            _redraw(a,old,old,active)
    elif action==7 and moves:
        rec=moves.pop()
        _undo(a,rec,active)

    if goal:
        if CURRENT_LEVEL==7:
            info["win"]=True
        else:
            info["level_up"]=True

    # Every ordinary input consumes one cell of the right-edge meter.
    if action not in (6,7):
        k=0
        while k<63 and int(a[k,63])==5:
            k+=1
        if k<63:
            a[k,63]=5

    st["active"]=active
    st["moves"]=moves
    return a.tolist(),info,st

def is_goal(state,grid):
    a=np.array(grid,dtype=int)
    src,copy,axis=_scene(a)
    t=_target()
    return bool(t and copy==t)
