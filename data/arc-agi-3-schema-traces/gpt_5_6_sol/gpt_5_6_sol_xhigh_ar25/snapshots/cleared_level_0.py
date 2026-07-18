# ARC3 world model: mirror-linked 3x3-tile polyominoes.

def init_state(entry_grid):
    return {"selected": 5, "moves": []}

def _blocks_with_value(a, value):
    ys,xs = np.where(a == value)
    return set((int(x)//3, int(y)//3) for y,x in zip(ys,xs)
               if int(x) < 63 and int(y) < 63)

def _target_blocks():
    # The target has the same colour as the right/bottom-right boundary.
    e = np.array(ENTRY_GRID, dtype=int)
    return _blocks_with_value(e, 11)

def _mover_blocks(a):
    # Left mover tiles have a 0 centre. Right mover tiles contain colour 4;
    # when a tile overlaps the target its centre remains target-coloured.
    ys,xs = np.where(a == 0)
    left = set((int(x)//3,int(y)//3) for y,x in zip(ys,xs))
    right = _blocks_with_value(a, 4)
    return left,right

def _pixels(blocks):
    out=set()
    for bx,by in blocks:
        for yy in range(3*by,3*by+3):
            for xx in range(3*bx,3*bx+3):
                out.add((xx,yy))
    return out

def _paint_block(a, block, colour, centre=None):
    bx,by=block
    x0,y0=3*bx,3*by
    a[y0:y0+3,x0:x0+3]=colour
    if centre is not None:
        a[y0+1,x0+1]=centre

def _redraw(a, old_left, old_right, new_left, new_right, target):
    # Erase the old mobile drawings, then restore the persistent target.
    for xx,yy in _pixels(old_left | old_right):
        a[yy,xx]=9
    for b in target:
        _paint_block(a,b,11)
    # Dotted left reference.
    for b in new_left:
        _paint_block(a,b,5,0)
    # Solid right copy; exact tile overlap is shown by a target-colour centre.
    for b in new_right:
        _paint_block(a,b,4,11 if b in target else None)

def _try_move(a, move_action):
    left,right = _mover_blocks(a)
    target = _target_blocks()
    if not left or not right:
        return False,False
    # Deltas are in logical 3x3 tiles. Horizontal movement is mirrored.
    ld = {1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[move_action]
    rd = (-ld[0],ld[1]) if move_action in (3,4) else ld
    nl=set((bx+ld[0],by+ld[1]) for bx,by in left)
    nr=set((bx+rd[0],by+rd[1]) for bx,by in right)
    oldpix=_pixels(left|right)
    # Left may enter background only; right may also enter persistent target.
    ok=True
    for blocks,allow_target in ((nl,False),(nr,True)):
        for xx,yy in _pixels(blocks):
            if not (0 <= xx < 63 and 0 <= yy < 63):
                ok=False; break
            if (xx,yy) in oldpix:
                continue
            v=int(a[yy,xx])
            if v != 9 and not (allow_target and v == 11):
                ok=False; break
        if not ok: break
    if not ok:
        return False,False
    _redraw(a,left,right,nl,nr,target)
    return True, bool(target and nr == target)

def predict(state, grid, action, x=None, y=None):
    a=np.array(grid,dtype=int)
    st=dict(state or {})
    moves=list(st.get("moves",[]))
    selected=int(st.get("selected",5))
    info={"level_up":False,"dead":False,"win":False}

    move_action=action if action in (1,2,3,4) else None
    undoing=False
    if action==7 and moves:
        last=moves.pop()
        move_action={1:2,2:1,3:4,4:3}[last]
        undoing=True

    if move_action is not None:
        moved,goal=_try_move(a,move_action)
        if moved and not undoing:
            moves.append(action)
        elif not moved and undoing:
            moves.append(last)
        if moved and goal and not undoing:
            info["level_up"]=True

    # Every ordinary action consumes the next top-to-bottom meter pixel.
    if action != 7:
        k=0
        while k < 63 and int(a[k,63]) == selected:
            k+=1
        if k < 63:
            a[k,63]=selected

    st["selected"]=selected
    st["moves"]=moves
    return a.tolist(),info,st

def is_goal(state,grid):
    a=np.array(grid,dtype=int)
    left,right=_mover_blocks(a)
    target=_target_blocks()
    return bool(target and right == target)
