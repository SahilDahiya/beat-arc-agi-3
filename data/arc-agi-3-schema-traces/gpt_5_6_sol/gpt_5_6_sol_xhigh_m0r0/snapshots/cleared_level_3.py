# Paired mirrored tokens with hazards and clickable hazard switches.
def _components(a,color):
    h=len(a); w=len(a[0]); seen=set(); out=[]
    for y in range(h):
        for x in range(w):
            if a[y][x]!=color or (x,y) in seen: continue
            q=[(x,y)]; seen.add((x,y)); c=[]; qi=0
            while qi<len(q):
                xx,yy=q[qi]; qi+=1; c.append((xx,yy))
                for z in ((xx+1,yy),(xx-1,yy),(xx,yy+1),(xx,yy-1)):
                    nx,ny=z
                    if 0<=nx<w and 0<=ny<h and a[ny][nx]==color and z not in seen:
                        seen.add(z); q.append(z)
            out.append(c)
    return out

def _tops(grid):
    cs=_components(grid,10)
    return sorted((min(x for x,y in c),min(y for x,y in c)) for c in cs)

def _token_size(grid):
    cs=_components(grid,10)
    if not cs: return 1
    c=cs[0]
    return max(max(x for x,y in c)-min(x for x,y in c)+1,
               max(y for x,y in c)-min(y for x,y in c)+1)

def _hazards():
    bg0=ENTRY_GRID[1][0]; bg1=ENTRY_GRID[1][-1]
    return set(v for row in ENTRY_GRID for v in row
               if v not in (0,5,10,bg0,bg1))

def _special_data(entry,size):
    buttons=[]; colors=[]; teleport=[]
    for col in _hazards():
        allcells=[(x,y) for y,row in enumerate(entry)
                  for x,z in enumerate(row) if z==col]
        # A sparse/broad special field is a teleport hazard as a whole,
        # even when its checkerboard cells are not 4-connected.  A small
        # collection of compact components is instead clickable and solid.
        if len(allcells)>=size*size:
            teleport.extend(allcells)
        else:
            for c in _components(entry,col):
                buttons.append(c); colors.append(col)
    return buttons,colors,teleport

def init_state(entry_grid):
    size=_token_size(entry_grid)
    buttons,base,teleport=_special_data(entry_grid,size)
    return {"turns":0,"pos":_tops(entry_grid),"size":size,
            "hazards":list(_hazards()),"teleport":teleport,
            "buttons":buttons,"button_orig":[list(c) for c in buttons],
            "button_base":base,"button_on":[False]*len(buttons),
            "token_color":10}

def _entry_pos():
    return _tops(ENTRY_GRID)

def _under(u,v,buttons,button_orig,button_base,button_on):
    for k,cells in enumerate(buttons):
        if (u,v) in cells:
            return 11 if button_on[k] else button_base[k]
    z=ENTRY_GRID[v][u]
    origins=set(q for cells in button_orig for q in cells)
    return 5 if z==10 or (u,v) in origins else z

def predict(state,grid,action,x=None,y=None):
    a=[r[:] for r in grid]
    prior=state.get("turns",0)
    pos=[tuple(p) for p in state.get("pos",_entry_pos())]
    size=state.get("size",_token_size(ENTRY_GRID))
    hazards=set(state.get("hazards",list(_hazards())))
    default_buttons,default_base,default_teleport=_special_data(ENTRY_GRID,size)
    teleport=set(tuple(z) for z in state.get("teleport",default_teleport))
    buttons=[list(c) for c in state.get("buttons",default_buttons)]
    button_orig=[list(c) for c in state.get("button_orig",default_buttons)]
    button_base=state.get("button_base",default_base)
    button_on=list(state.get("button_on",[False]*len(buttons)))
    token_color=state.get("token_color",10)
    safe=set(z for k,cells in enumerate(buttons) if button_on[k] for z in cells)

    # Replay skips only the first-ever transition.
    if prior==0 and grid!=ENTRY_GRID:
        prior=1
        seen=_tops(grid)
        if len(seen)==2: pos=seen
    turns=prior+1

    if action==6 and x is not None and y is not None:
        hit=False
        for j,cells in enumerate(buttons):
            if (x,y) in cells:
                # Radio selection: at most one compact hazard is disabled.
                # Selecting another restores the previous switch to its base
                # hazard color; clicking the selected one toggles all off.
                new_on=not button_on[j]
                button_on=[False]*len(buttons)
                if new_on: button_on[j]=True
                for k,bcells in enumerate(buttons):
                    val=11 if button_on[k] else button_base[k]
                    for u,v in bcells: a[v][u]=val
                new_color=(1 if any(button_on) else 10)
                for px,py in pos:
                    for v in range(py,py+size):
                        for u in range(px,px+size): a[v][u]=new_color
                token_color=new_color
                hit=True
                break
        # The top/bottom meter border is outside the clickable playfield.
        # Interior non-switch clicks cancel selection.
        if not hit and any(button_on) and 0<y<len(a)-1:
            button_on=[False]*len(buttons)
            for k,bcells in enumerate(buttons):
                for u,v in bcells: a[v][u]=button_base[k]
            token_color=10
            for px,py in pos:
                for v in range(py,py+size):
                    for u in range(px,px+size): a[v][u]=10

    # Selecting a compact special transfers directional control to it.
    # It keeps its own 2x2 shape but moves by the large-token stride.
    if action in (1,2,3,4) and token_color==1 and any(button_on):
        j=button_on.index(True)
        cells=buttons[j]
        if action==1: dx,dy=0,-size
        elif action==2: dx,dy=0,size
        elif action==3: dx,dy=-size,0
        else: dx,dy=size,0
        shifted=[(u+dx,v+dy) for u,v in cells]
        inside=all(0<=u<len(a[0]) and 0<=v<len(a) for u,v in shifted)
        if inside and all(a[v][u]==5 for u,v in shifted):
            for u,v in cells: a[v][u]=5
            buttons[j]=shifted
            for u,v in shifted: a[v][u]=11

    if action in (1,2,3,4) and len(pos)==2 and token_color==10:
        dest=[]; movable=[]; hazard=False
        for i,(px,py) in enumerate(pos):
            if action==1: dx,dy=0,-size
            elif action==2: dx,dy=0,size
            elif action==3: dx,dy=(-size if i==0 else size),0
            else: dx,dy=(size if i==0 else -size),0
            np0=(px+dx,py+dy); dest.append(np0)
            nx,ny=np0
            inside=0<=nx<=len(a[0])-size and 0<=ny<=len(a)-size
            vals=([a[v][u] for v in range(ny,ny+size)
                              for u in range(nx,nx+size)] if inside else [])
            if inside and any((u,v) in teleport
                              for v in range(ny,ny+size)
                              for u in range(nx,nx+size)):
                hazard=True
            movable.append(inside and all(
                a[v][u]==5 or (u,v) in safe
                for v in range(ny,ny+size) for u in range(nx,nx+size)))
        if hazard:
            # A broad checker collision resets every dynamic piece to the
            # level-entry arrangement (but the outer action timer continues).
            a=[r[:] for r in ENTRY_GRID]
            pos=_entry_pos()
            buttons=[list(c) for c in button_orig]
            button_on=[False]*len(buttons)
            token_color=10
        else:
            for i,ok in enumerate(movable):
                if ok:
                    px,py=pos[i]
                    for v in range(py,py+size):
                        for u in range(px,px+size): a[v][u]=_under(u,v,buttons,button_orig,button_base,button_on)
            for i,ok in enumerate(movable):
                if ok:
                    pos[i]=dest[i]; px,py=pos[i]
                    for v in range(py,py+size):
                        for u in range(px,px+size): a[v][u]=token_color

    meter=(turns*64+75)//150
    a[0]=[5]*len(a[0]); a[-1]=[5]*len(a[-1])
    for i in range(meter): a[-1][i]=0; a[0][-1-i]=0

    ns={"turns":turns,"pos":pos,"size":size,"hazards":list(hazards),
        "teleport":list(teleport),"buttons":buttons,
        "button_orig":button_orig,"button_base":button_base,
        "button_on":button_on,
        "token_color":token_color}
    goal=is_goal(ns,a)
    last=(CURRENT_LEVEL is not None and CURRENT_LEVEL>=5)
    info={"level_up":bool(goal and not last),"dead":False,"win":bool(goal and last)}
    return a,info,ns

def is_goal(state,grid):
    p=[tuple(z) for z in (state or {}).get("pos",[])]
    return len(p)==2 and p[0]==p[1]
