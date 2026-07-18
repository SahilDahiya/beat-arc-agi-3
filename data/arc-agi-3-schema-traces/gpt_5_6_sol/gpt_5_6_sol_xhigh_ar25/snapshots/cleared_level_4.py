# ARC3 world model: selectable source polyomino(es), a selectable mirror
# line, their geometric reflection, and target tiles. Graphics use 3x3 tiles.

def _blocks_with_value(a,value):
    ys,xs=np.where(a==value)
    return set((int(x)//3,int(y)//3) for y,x in zip(ys,xs)
               if int(x)<63 and int(y)<63)

def _source(a):
    return _blocks_with_value(a,5)

def _copy(a):
    return _blocks_with_value(a,4)

def _target():
    return _blocks_with_value(np.array(ENTRY_GRID,dtype=int),11)

def _axis_info(entry):
    a=np.array(entry,dtype=int)
    bs=_blocks_with_value(a,10)
    xs=[p[0] for p in bs]; ys=[p[1] for p in bs]
    if len(set(xs))<=len(set(ys)):
        vals=xs; orient="vertical"
    else:
        vals=ys; orient="horizontal"
    if not vals:
        return "vertical",10
    coord=max(set(vals),key=vals.count)
    return orient,int(coord)

def _axis_blocks(orient,coord):
    if orient=="vertical":
        return set((coord,i) for i in range(21))
    return set((i,coord) for i in range(21))

def _reflected(src,orient,coord):
    if orient=="vertical":
        return set((2*coord-x,y) for x,y in src)
    return set((x,2*coord-y) for x,y in src)

def _visible(bs):
    return set((x,y) for x,y in bs if 0<=x<21 and 0<=y<21)

def _initial_mode(entry):
    a=np.array(entry,dtype=int)
    src=_source(a)
    z=_blocks_with_value(a,0)
    orient,coord=_axis_info(entry)
    axis=_axis_blocks(orient,coord)
    return "axis" if len(z&axis)>len(z&src) else "source"

def _initial_sel(entry):
    a=np.array(entry,dtype=int)
    src=_source(a)
    return tuple(sorted(b for b in src if int(a[3*b[1]+1,3*b[0]+1])==0))

def init_state(entry_grid):
    axes=_multi_axis_infos(entry_grid)
    if len(axes)>1:
        a=np.array(entry_grid,dtype=int)
        src=_source(a); z=_blocks_with_value(a,0)
        scores={o:len(z & _axis_blocks(o,c)) for o,c in axes.items()}
        active_o=max(scores,key=scores.get)
        bases={}
        t=_blocks_with_value(a,11)
        for o,c in axes.items():
            vals=[]
            for bx,by in _axis_blocks(o,c)-t-src:
                vals.append(int(a[3*by+1,3*bx+1]))
            if 9 in vals: bases[o]=9
            elif 10 in vals: bases[o]=10
            else: bases[o]=9
        return {"multi":True,"active":"axis_"+active_o,"sel":(),
                "axes":axes,"bases":bases,"moves":[],"synced":False}
    orient,coord=_axis_info(entry_grid)
    return {"active":_initial_mode(entry_grid),
            "sel":_initial_sel(entry_grid),
            "orient":orient,"axis":coord,"moves":[],"synced":False}

def _pixels(blocks):
    out=set()
    for bx,by in blocks:
        for yy in range(3*by,3*by+3):
            for xx in range(3*bx,3*bx+3):
                if 0<=xx<63 and 0<=yy<63:
                    out.add((xx,yy))
    return out

def _paint(a,b,colour,centre=None):
    bx,by=b
    if not (0<=bx<21 and 0<=by<21):
        return
    x0,y0=3*bx,3*by
    a[y0:y0+3,x0:x0+3]=colour
    if centre is not None:
        a[y0+1,x0+1]=centre

def _axis_base():
    # Mirrors initially selected are movable/dotted and revert to background
    # centres when deselected. The fixed mirror of level 0 is solid.
    return 9 if _initial_mode(ENTRY_GRID)=="axis" else 10

def _redraw(a,oldsrc,oldcopy,oldaxis,src,orient,coord,active,sel):
    axis=_axis_blocks(orient,coord)
    copy=_visible(_reflected(src,orient,coord))
    for xx,yy in _pixels(oldsrc|oldcopy|oldaxis):
        a[yy,xx]=9
    # Mirror first; target may visually cover a crossing.
    for b in axis:
        _paint(a,b,10,0 if active=="axis" else _axis_base())
    target=_target()
    for b in target:
        _paint(a,b,11)
    # Reflection is behind the physical source when they coincide on the mirror.
    for b in copy:
        _paint(a,b,4,11 if b in target else None)
    ssel=set(sel)
    for b in src:
        if b in target:
            centre=11
        elif active=="axis" and b in axis:
            # The selected mirror's centre remains visible through a crossing.
            centre=0
        elif active=="source" and b in ssel:
            centre=0
        elif b in axis:
            centre=_axis_base()
        else:
            centre=9
        _paint(a,b,5,centre)
    return copy

def _component(src,start):
    if start not in src:
        return set()
    seen={start}; todo=[start]
    while todo:
        x,y=todo.pop()
        for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if q in src and q not in seen:
                seen.add(q); todo.append(q)
    return seen

def _selected_from_grid(a):
    src=_source(a)
    seeds=[b for b in src if int(a[3*b[1]+1,3*b[0]+1])==0]
    if not seeds:
        return set()
    # All black-centred seeds belong to the selected connected component.
    return _component(src,seeds[0])

def _goal(src,copy):
    t=_target()
    return bool(t and t <= (src|copy))

def _source_move(a,action,orient,coord,active,sel):
    src=_source(a); oldcopy=_copy(a); oldaxis=_axis_blocks(orient,coord)
    chosen=set(sel)
    if not chosen:
        return False,False,tuple(sel)
    dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
    moved=set((x+dx,y+dy) for x,y in chosen)
    other=src-chosen
    axis=oldaxis
    if any(not (0<=x<21 and 0<=y<21) for x,y in moved):
        return False,False,tuple(sel)
    # Source tiles may pass through the mirror and may overlap other source
    # pieces; layers of the same colour merge visually.
    ns=other|moved
    nc=_visible(_reflected(ns,orient,coord))
    _redraw(a,src,oldcopy,oldaxis,ns,orient,coord,active,moved)
    return True,_goal(ns,nc),tuple(sorted(moved))

def _axis_move(a,action,orient,coord,active,sel):
    delta=None
    if orient=="vertical" and action in (3,4):
        delta=-1 if action==3 else 1
    elif orient=="horizontal" and action in (1,2):
        delta=-1 if action==1 else 1
    if delta is None:
        return False,False,coord
    nc=coord+delta
    if not (0<=nc<21):
        return False,False,coord
    src=_source(a); oldcopy=_copy(a); oldaxis=_axis_blocks(orient,coord)
    naxis=_axis_blocks(orient,nc)
    # Mirror line may pass behind source/target tiles.
    copy=_visible(_reflected(src,orient,nc))
    _redraw(a,src,oldcopy,oldaxis,src,orient,nc,active,sel)
    return True,_goal(src,copy),nc

def predict(state,grid,action,x=None,y=None):
    if state and state.get("multi",False):
        return _predict_multi(state,grid,action,x,y)
    a=np.array(grid,dtype=int)
    st=dict(state or {})
    orient=st.get("orient",_axis_info(ENTRY_GRID)[0])
    coord=int(st.get("axis",_axis_info(ENTRY_GRID)[1]))
    active=st.get("active",_initial_mode(ENTRY_GRID))
    sel=tuple(st.get("sel",_initial_sel(ENTRY_GRID)))
    moves=list(st.get("moves",[]))
    info={"level_up":False,"dead":False,"win":False}
    goal=False
    synced=bool(st.get("synced",False))
    # The first recorded transition of a level can be skipped by the harness;
    # synchronize selection once from the real rendered frame, then preserve
    # the selected piece identity through later same-colour overlaps.
    if active=="source" and not synced:
        observed_sel=_selected_from_grid(a)
        if observed_sel:
            sel=tuple(sorted(observed_sel))
    synced=True

    if action in (1,2,3,4):
        if active=="source":
            moved,goal,nsel=_source_move(a,action,orient,coord,active,sel)
            if moved:
                moves.append(("source",action))
                sel=nsel
        else:
            moved,goal,ncoord=_axis_move(a,action,orient,coord,active,sel)
            if moved:
                moves.append(("axis",action))
                coord=ncoord
    elif action==6 and x is not None and y is not None:
        src=_source(a); oldcopy=_copy(a); oldaxis=_axis_blocks(orient,coord)
        b=(int(x)//3,int(y)//3)
        newactive=active; newsel=set(sel)
        comp=_component(src,b)
        if comp:
            newactive="source"; newsel=comp
        elif b in oldaxis:
            newactive="axis"; newsel=set()
        if newactive!=active or set(sel)!=newsel:
            active=newactive; sel=tuple(sorted(newsel))
            _redraw(a,src,oldcopy,oldaxis,src,orient,coord,active,sel)
    elif action==7 and moves:
        kind,last=moves.pop()
        inv={1:2,2:1,3:4,4:3}[last]
        # Undo the affected object even if selection later changed.
        if kind=="source":
            moved,g,nsel=_source_move(a,inv,orient,coord,"source",sel)
            if moved: sel=nsel
        else:
            moved,g,ncoord=_axis_move(a,inv,orient,coord,"axis",sel)
            if moved: coord=ncoord

    if goal:
        if CURRENT_LEVEL==7: info["win"]=True
        else: info["level_up"]=True

    if action in (1,2,3,4,5):
        meter_colour = 12 if orient=="horizontal" else 5
        k=0
        while k<63 and int(a[k,63])==meter_colour:
            k+=1
        if k<63: a[k,63]=meter_colour

    st.update({"active":active,"sel":sel,"orient":orient,
               "axis":coord,"moves":moves,"synced":synced})
    return a.tolist(),info,st

# --- Multiple perpendicular mirrors (introduced in level 4) ---

def _multi_axis_infos(entry):
    a=np.array(entry,dtype=int)
    bs=_blocks_with_value(a,10)
    xc={}; yc={}
    for x,y in bs:
        xc[x]=xc.get(x,0)+1; yc[y]=yc.get(y,0)+1
    out={}
    if xc:
        x,n=max(xc.items(),key=lambda z:z[1])
        if n>=10: out["vertical"]=int(x)
    if yc:
        y,n=max(yc.items(),key=lambda z:z[1])
        if n>=10: out["horizontal"]=int(y)
    return out

def _multi_axes_blocks(axes):
    u=set()
    for o,c in axes.items(): u |= _axis_blocks(o,int(c))
    return u

def _multi_copies(src,axes):
    # Closure of source under all non-empty combinations of perpendicular
    # reflections (V, H, and VH when both mirrors exist).
    variants=[set(src)]
    for o,c in sorted(axes.items()):
        added=[]
        for s in variants:
            added.append(_reflected(s,o,int(c)))
        variants += added
    out=set()
    for s in variants[1:]: out |= _visible(s)
    return out

def _multi_goal(src,copies):
    t=_target()
    return bool(t and t <= (src|copies))

def _multi_redraw(a,oldsrc,oldcopy,oldaxes,src,axes,bases,active,sel):
    newaxes=_multi_axes_blocks(axes)
    copies=_multi_copies(src,axes)
    for xx,yy in _pixels(oldsrc|oldcopy|oldaxes):
        a[yy,xx]=9
    # Inactive axes first, selected axis last so its zero centre wins at the
    # mirror intersection.
    order=sorted(axes, key=lambda o: active=="axis_"+o)
    for o in order:
        c=int(axes[o]); centre=0 if active=="axis_"+o else int(bases.get(o,9))
        for b in _axis_blocks(o,c): _paint(a,b,10,centre)
    target=_target()
    for b in target: _paint(a,b,11)
    for b in copies: _paint(a,b,4,11 if b in target else None)
    ssel=set(sel)
    for b in src:
        if b in target:
            centre=11
        elif active.startswith("axis_") and b in _axis_blocks(active[5:],int(axes[active[5:]])):
            centre=0
        elif active=="source" and b in ssel:
            centre=0
        else:
            vals=[int(bases.get(o,9)) for o,c in axes.items()
                  if b in _axis_blocks(o,int(c))]
            centre=vals[-1] if vals else 9
        _paint(a,b,5,centre)
    return copies

def _predict_multi(state,grid,action,x=None,y=None):
    a=np.array(grid,dtype=int)
    st=dict(state)
    axes={k:int(v) for k,v in dict(st.get("axes",{})).items()}
    bases={k:int(v) for k,v in dict(st.get("bases",{})).items()}
    active=st.get("active","source")
    sel=tuple(st.get("sel",()))
    moves=list(st.get("moves",[]))
    synced=bool(st.get("synced",False))
    info={"level_up":False,"dead":False,"win":False}
    goal=False
    src=_source(a); oldcopy=_copy(a); oldaxes=_multi_axes_blocks(axes)

    if active=="source" and not synced:
        observed=_selected_from_grid(a)
        if observed: sel=tuple(sorted(observed))
    synced=True

    if action in (1,2,3,4):
        if active=="source" and sel:
            chosen=set(sel)
            dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
            movedset=set((bx+dx,by+dy) for bx,by in chosen)
            if all(0<=bx<21 and 0<=by<21 for bx,by in movedset):
                ns=(src-chosen)|movedset
                copies=_multi_copies(ns,axes)
                _multi_redraw(a,src,oldcopy,oldaxes,ns,axes,bases,active,movedset)
                sel=tuple(sorted(movedset)); moves.append(("source",action))
                goal=_multi_goal(ns,copies)
        elif active.startswith("axis_"):
            o=active[5:]; delta=None
            if o=="vertical" and action in (3,4):
                delta=-1 if action==3 else 1
            elif o=="horizontal" and action in (1,2):
                delta=-1 if action==1 else 1
            if delta is not None and 0<=axes[o]+delta<21:
                axes[o]+=delta
                copies=_multi_copies(src,axes)
                _multi_redraw(a,src,oldcopy,oldaxes,src,axes,bases,active,sel)
                moves.append((active,action))
                goal=_multi_goal(src,copies)
    elif action==6 and x is not None and y is not None:
        b=(int(x)//3,int(y)//3)
        comp=_component(src,b)
        newactive=active; newsel=set(sel)
        if comp:
            newactive="source"; newsel=comp
        else:
            # Click an axis away from an ambiguous intersection when possible.
            hits=[o for o,c in axes.items() if b in _axis_blocks(o,int(c))]
            if hits:
                newactive="axis_"+hits[-1]; newsel=set()
        if newactive!=active or newsel!=set(sel):
            active=newactive; sel=tuple(sorted(newsel))
            _multi_redraw(a,src,oldcopy,oldaxes,src,axes,bases,active,sel)
    elif action==7 and moves:
        kind,last=moves.pop(); inv={1:2,2:1,3:4,4:3}[last]
        if kind=="source" and sel:
            chosen=set(sel); dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[inv]
            movedset=set((bx+dx,by+dy) for bx,by in chosen)
            ns=(src-chosen)|movedset
            _multi_redraw(a,src,oldcopy,oldaxes,ns,axes,bases,active,movedset)
            sel=tuple(sorted(movedset))
        elif kind.startswith("axis_"):
            o=kind[5:]
            delta=(-1 if inv==3 else 1) if o=="vertical" else (-1 if inv==1 else 1)
            axes[o]+=delta
            _multi_redraw(a,src,oldcopy,oldaxes,src,axes,bases,active,sel)

    if goal:
        if CURRENT_LEVEL==7: info["win"]=True
        else: info["level_up"]=True
    if action in (1,2,3,4,5):
        meter_colour=12 if "horizontal" in axes else 5
        k=0
        while k<63 and int(a[k,63])==meter_colour: k+=1
        if k<63: a[k,63]=meter_colour
    st.update({"multi":True,"active":active,"sel":sel,"axes":axes,
               "bases":bases,"moves":moves,"synced":synced})
    return a.tolist(),info,st

def is_goal(state,grid):
    a=np.array(grid,dtype=int)
    src=_source(a)
    if state and state.get("multi",False):
        axes={k:int(v) for k,v in dict(state.get("axes",{})).items()}
        return _multi_goal(src,_multi_copies(src,axes))
    return _goal(src,_copy(a))
