import numpy as np

def _bg():
    e=np.array(ENTRY_GRID,dtype=int)
    vals,counts=np.unique(e[:-1],return_counts=True)
    return int(vals[np.argmax(counts)])

def _entry_data():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg()
    vals=[int(v) for v in np.unique(e) if int(v) not in (0,1,4,bg,15)]
    data={}
    # Plus and diagonal-X intersections.
    for q in vals:
        found=None
        for y in range(1,h-2):
            for x in range(1,w-1):
                if int(e[y,x]) not in (q,0): continue
                orth=[int(e[y-1,x]),int(e[y+1,x]),int(e[y,x-1]),int(e[y,x+1])]
                diag=[int(e[y-1,x-1]),int(e[y-1,x+1]),int(e[y+1,x-1]),int(e[y+1,x+1])]
                if all(v==q for v in orth):
                    l=r=t=b=0
                    while x-l-1>=0 and int(e[y,x-l-1])==q: l+=1
                    while x+r+1<w and int(e[y,x+r+1])==q: r+=1
                    while y-t-1>=0 and int(e[y-t-1,x])==q: t+=1
                    while y+b+1<h-1 and int(e[y+b+1,x])==q: b+=1
                    found={'kind':'plus','center':[x,y],'rad':[l,r,t,b]}
                    break
                if all(v==q for v in diag):
                    nw=ne=sw=se=0
                    while x-nw-1>=0 and y-nw-1>=0 and int(e[y-nw-1,x-nw-1])==q: nw+=1
                    while x+ne+1<w and y-ne-1>=0 and int(e[y-ne-1,x+ne+1])==q: ne+=1
                    while x-sw-1>=0 and y+sw+1<h-1 and int(e[y+sw+1,x-sw-1])==q: sw+=1
                    while x+se+1<w and y+se+1<h-1 and int(e[y+se+1,x+se+1])==q: se+=1
                    found={'kind':'x','center':[x,y],'rad':[nw,ne,sw,se]}
                    break
            if found: break
        if found: data[q]=found
    # Remaining large diagonal components are diamond outlines.
    for q in vals:
        if q in data: continue
        cells={(int(x),int(y)) for y,x in np.argwhere(e==q)}
        comps=[]
        while cells:
            p=cells.pop(); comp={p}; stack=[p]
            while stack:
                x,y=stack.pop()
                for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)):
                    z=(x+dx,y+dy)
                    if z in cells:
                        cells.remove(z); comp.add(z); stack.append(z)
            comps.append(comp)
        if comps:
            comp=max(comps,key=len)
            if len(comp)>=8:
                xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
                ymin,ymax=min(ys),max(ys); cy=(ymin+ymax)//2
                # Top/bottom vertices reveal cx even when a side vertex is
                # occluded by another shape (as in L1 diamond under plus 9).
                vx=[x for x,y in comp if y in (ymin,ymax)]
                cx=int(round(sum(vx)/len(vx))) if vx else (min(xs)+max(xs))//2
                R=(ymax-ymin)//2
                data[q]={'kind':'diamond','center':[cx,cy],'rad':R}
    active=None
    for y,x in np.argwhere(e==0):
        for q,d in data.items():
            if d['center']==[int(x),int(y)]: active=q
    return data,active

def init_state(entry_grid):
    ds,active=_entry_data()
    return {'centers':{q:list(d['center']) for q,d in ds.items()},'active':active}

def _shape_cells(d,center,h=64,w=64):
    cx,cy=center; kind=d['kind']; out=set()
    if kind=='plus':
        l,r,t,b=d['rad']
        for x in range(cx-l,cx+r+1):
            if 0<=x<w and 0<=cy<h-1: out.add((x,cy))
        for y in range(cy-t,cy+b+1):
            if 0<=y<h-1 and 0<=cx<w: out.add((cx,y))
    elif kind=='x':
        nw,ne,sw,se=d['rad']
        # X arms have a hollow intersection; 0 marks it only while active.
        for k in range(1,nw+1): out.add((cx-k,cy-k))
        for k in range(1,ne+1): out.add((cx+k,cy-k))
        for k in range(1,sw+1): out.add((cx-k,cy+k))
        for k in range(1,se+1): out.add((cx+k,cy+k))
        out={(x,y) for x,y in out if 0<=x<w and 0<=y<h-1}
    else:
        R=d['rad']
        for dx in range(-R,R+1):
            dy=R-abs(dx)
            for y in ({cy-dy,cy+dy} if dy else {cy}):
                x=cx+dx
                if 0<=x<w and 0<=y<h-1: out.add((x,y))
    return out

def _markers(q):
    e=np.array(ENTRY_GRID,dtype=int); out=[]
    for y in range(1,e.shape[0]-2):
        for x in range(1,e.shape[1]-1):
            if (int(e[y,x])==q and int(e[y-1,x])==4 and int(e[y+1,x])==4 and
                int(e[y,x-1])==4 and int(e[y,x+1])==4): out.append((x,y))
    return out

def _goals():
    ds,_=_entry_data(); ans={}
    for q,d in ds.items():
        pts=_markers(q)
        if not pts: continue
        if d['kind']=='plus':
            gx=max(set(x for x,y in pts),key=lambda z:sum(x==z for x,y in pts))
            gy=max(set(y for x,y in pts),key=lambda z:sum(y==z for x,y in pts))
            ans[q]=[gx,gy]
        elif d['kind']=='x':
            sums={}; diffs={}
            for x,y in pts:
                sums[x+y]=sums.get(x+y,0)+1; diffs[y-x]=diffs.get(y-x,0)+1
            ss=max(sums,key=sums.get); dd=max(diffs,key=diffs.get)
            # If only one diagonal constant repeats, take the other from the
            # marker not on that repeated diagonal.
            if sums[ss]>=2:
                rem=[y-x for x,y in pts if x+y!=ss]
                if rem: dd=rem[0]
            if diffs[dd]>=2:
                rem=[x+y for x,y in pts if y-x!=dd]
                if rem: ss=rem[0]
            if (ss-dd)%2==0: ans[q]=[(ss-dd)//2,(ss+dd)//2]
        else:
            R=d['rad']; ex,ey=d['center']; cand=[]
            for y in range(0,63):
                for x in range(64):
                    if (x-ex)%3 or (y-ey)%3: continue
                    if all(abs(px-x)+abs(py-y)==R for px,py in pts):
                        cand.append((abs(x-ex)+abs(y-ey),x,y))
            if cand:
                _,x,y=min(cand); ans[q]=[x,y]
    return ans

def _aligned(st):
    if not isinstance(st,dict): return False
    gs=_goals()
    return bool(gs) and all(st.get('centers',{}).get(q)==p for q,p in gs.items())

def is_goal(state,grid): return _aligned(state)

def _cell_hidden(st,ds,q,px,py,h,w):
    if q not in ds: return False
    ranks={'x':0,'diamond':1,'plus':2}
    key=lambda z:(ranks.get(ds.get(z,{}).get('kind','x'),0),-z)
    qk=key(q)
    for z,oc in st.get('centers',{}).items():
        if z!=q and z in ds and key(z)>qk:
            if (px,py) in set(_shape_cells(ds[z],oc,h,w)):
                return True
    return False

def _active_hidden(st,ds,q,h,w):
    if q not in st.get('centers',{}): return False
    px,py=st['centers'][q]
    return _cell_hidden(st,ds,q,px,py,h,w)

def predict(state,grid,action,x=None,y=None):
    cur=np.array(grid,dtype=int); ds,_=_entry_data(); bg=_bg()
    st={'centers':{int(q):list(p) for q,p in state.get('centers',{}).items()},
        'active':state.get('active')}
    # Resync a visible 0 with a known shape centre.
    zs=np.argwhere(cur==0)
    for yy,xx in zs:
        for q,p in st['centers'].items():
            if p==[int(xx),int(yy)]: st['active']=q
        for q,d in ds.items():
            ns=[]
            if d['kind']=='plus': ns=[cur[yy-1,xx],cur[yy+1,xx],cur[yy,xx-1],cur[yy,xx+1]]
            elif d['kind']=='x': ns=[cur[yy-1,xx-1],cur[yy-1,xx+1],cur[yy+1,xx-1],cur[yy+1,xx+1]]
            if ns and sum(int(v)==q for v in ns)>=3:
                st['active']=q; st['centers'][q]=[int(xx),int(yy)]
    c=st['active']; delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    moved=False; dx=dy=0; nx=ny=0
    if c in st['centers'] and delta is not None:
        cx,cy=st['centers'][c]; dx,dy=delta; nx,ny=cx+dx,cy+dy
        if 0<=nx<cur.shape[1] and 0<=ny<cur.shape[0]-1:
            st['centers'][c]=[nx,ny]; moved=True
    if action==5 and c in st['centers']:
        order=sorted(st['centers'])
        if len(order)>1:
            st['active']=order[(order.index(c)+1)%len(order)]
    footer=cur[-1].copy()
    # Switching away from a completed hollow outline locks that placement.
    # A switch whose new active centre is hidden under a higher layer also
    # spends a footer cell (9->c while d covers c's centre).
    switch_charge=False
    if action==5 and c in ds:
        if ds[c]['kind'] in ('x','diamond'):
            gs=_goals()
            switch_charge=(c in gs and tuple(st['centers'][c])==tuple(gs[c]))
        na=st.get('active')
        switch_charge=(switch_charge or
                       _active_hidden(st,ds,na,cur.shape[0],cur.shape[1]))
    if switch_charge:
        ff=np.where(footer==15)[0]
        if len(ff): footer[int(ff[-1])]=1
    if moved:
        newv=nx if dx else ny
        # Solid pluses have a hue/coordinate phase. Hollow X/diamond
        # outlines instead move free only when the outline hits a marker.
        kind=ds[c]['kind']
        if kind=='plus': free=(newv%9==(3*c)%9)
        elif kind=='x': free=(newv%9==0)
        elif kind=='diamond': free=(newv%9==6)
        else: free=False
        # Confirmed L0 plus exception: leading endpoint touching an outside
        # aligned marker is free; hue 9 on goal column has a 6-row phase.
        if ds[c]['kind']=='plus':
            if c==9 and dy:
                gs=_goals(); free=(c in gs and nx==gs[c][0] and newv%6==0)
            l,r,t,b=ds[c]['rad']
            for mx,my in _markers(c):
                if dy<0 and nx==mx and ny-t==my+1: free=True
                if dy>0 and nx==mx and ny+b==my-1: free=True
                if dx<0 and ny==my and nx-l==mx+1: free=True
                if dx>0 and ny==my and nx+r==mx-1: free=True
            # A move immediately before first contacting one's own marker is
            # free. At L1 x=30, the next left move puts the vertical 9 arm
            # through the marker at (27,36); exact contact itself charges.
            cells=set(_shape_cells(ds[c],[nx,ny],cur.shape[0],cur.shape[1]))
            ahead=set(_shape_cells(ds[c],[nx+dx,ny+dy],cur.shape[0],cur.shape[1]))
            own=_markers(c)
            if (not any((mx,my) in cells for mx,my in own)
                    and any((mx,my) in ahead for mx,my in own)):
                free=True
            # The following move's first exact contact spends a cell, even
            # when its coordinate would otherwise be on the free hue phase.
            prevcells=set(_shape_cells(ds[c],[cx,cy],cur.shape[0],cur.shape[1]))
            if (not any((mx,my) in prevcells for mx,my in own)
                    and any((mx,my) in cells for mx,my in own)):
                free=False
        # Hollow outline shapes get a free move when their outline lands on
        # a framed marker centre.  Confirmed for the d diamond at x=24,
        # whose lower-right edge crosses the 9 marker at (27,36).
        if ds[c]['kind'] in ('x','diamond'):
            cells=set(_shape_cells(ds[c],[nx,ny],cur.shape[0],cur.shape[1]))
            contact_rank={'x':0,'diamond':1,'plus':2}
            # Any movable-shape contact overrides the coordinate phase. A
            # visible singleton (active above the other) is free; a hidden
            # contact or an overlap segment charges.
            for q,oc in st['centers'].items():
                if q==c or q not in ds or ds[q]['kind']=='plus': continue
                inter=cells & set(_shape_cells(ds[q],oc,cur.shape[0],cur.shape[1]))
                if inter:
                    free=(contact_rank.get(kind,0)>contact_rank.get(ds[q]['kind'],0)
                          and len(inter)==1)
            # Foreign-marker contacts override again: exactly one is free,
            # while simultaneous landing on two or more markers charges.
            marker_hits=[]
            for q in ds:
                if q!=c:
                    marker_hits += [(mx,my) for mx,my in _markers(q)
                                    if (mx,my) in cells]
            if marker_hits:
                free=(len(marker_hits)==1)
            ahead=set(_shape_cells(ds[c],[nx+dx,ny+dy],cur.shape[0],cur.shape[1]))
            # An X gets a free approach step immediately before one of its
            # arms reaches a diamond vertex (L1 y=21 before the y=24 overlap).
            if kind=='x':
                for q,oc in st['centers'].items():
                    if q==c or q not in ds or ds[q]['kind']!='diamond': continue
                    other=set(_shape_cells(ds[q],oc,cur.shape[0],cur.shape[1]))
                    xs=[p[0] for p in other]; ys=[p[1] for p in other]
                    verts={p for p in other if p[0] in (min(xs),max(xs)) or
                                             p[1] in (min(ys),max(ys))}
                    if not (cells & other) and (ahead & verts): free=True
            # Approaching the complete framed landing counts one move early.
            gs=_goals()
            if c in gs and [nx+dx,ny+dy]==list(gs[c]): free=True
            # Reaching the goal coordinate along the axis just moved is a
            # placement step and charges even if it lies on the phase.
            if c in gs and ((dx and nx==gs[c][0]) or (dy and ny==gs[c][1])):
                free=False
        if not free:
            ff=np.where(footer==15)[0]
            if len(ff): footer[int(ff[-1])]=1
    # Static backdrop: erase all entry shapes, then redraw at state centres.
    out=np.array(ENTRY_GRID,dtype=int).copy()
    for q,d in ds.items():
        for xx,yy in _shape_cells(d,d['center'],out.shape[0],out.shape[1]):
            if int(out[yy,xx]) in (q,0): out[yy,xx]=bg
        # Hollow shapes (X/diamond) do not include their centre in their
        # painted cells, but the entry board still puts the active 0 there.
        ex,ey=d['center']
        if int(out[ey,ex])==0:
            out[ey,ex]=bg
    # Layer priority is shape-based: X below diamond below plus. Within the
    # same shape family, lower hue is on top (confirmed b/9 plus overlap).
    ranks={'x':0,'diamond':1,'plus':2}
    order=sorted(st['centers'],key=lambda q:(ranks.get(ds.get(q,{}).get('kind','x'),0),-q))
    for q in order:
        if q in ds:
            for xx,yy in _shape_cells(ds[q],st['centers'][q],out.shape[0],out.shape[1]):
                out[yy,xx]=q
    ac=st['active']
    if ac in st['centers'] and not _active_hidden(st,ds,ac,out.shape[0],out.shape[1]):
        ax,ay=st['centers'][ac]; out[ay,ax]=0
    out[-1]=footer
    done=_aligned(st)
    return out.tolist(),{'level_up':bool(done and CURRENT_LEVEL!=7),'dead':False,
                         'win':bool(done and CURRENT_LEVEL==7)},st
