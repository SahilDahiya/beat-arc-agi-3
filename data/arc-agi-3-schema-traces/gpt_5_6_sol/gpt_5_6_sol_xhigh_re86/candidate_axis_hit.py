import numpy as np
import itertools

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

def _l2_setup():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg()
    # The repeated framed hue is shared by all three movable outlines.
    marks=[]; hue=None
    for y in range(1,h-2):
        for x in range(1,w-1):
            v=int(e[y,x])
            if v not in (bg,4,15,0) and all(int(e[y+dy,x+dx])==4
                    for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1))):
                marks.append((x,y)); hue=v
    zs=np.argwhere(e==0)
    if not len(zs): return {},[],bg,hue
    zy,zx=map(int,zs[0])
    # Active horizontal line through 0.
    l=r=0
    while zx-l-1>=0 and int(e[zy,zx-l-1])==hue: l+=1
    while zx+r+1<w and int(e[zy,zx+r+1])==hue: r+=1
    line={'kind':'line','color':hue,'center':[zx,zy],'rad':[l,r]}
    # Four-armed diagonal X: choose the strongest four-way diagonal centre.
    best=None
    for y in range(1,h-2):
        for x in range(1,w-1):
            if int(e[y,x]) not in (hue,0): continue
            arms=[]
            for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)):
                k=0
                while 0<=x+dx*(k+1)<w and 0<=y+dy*(k+1)<h-1 and int(e[y+dy*(k+1),x+dx*(k+1)])==hue:
                    k+=1
                arms.append(k)
            if min(arms)>=3:
                score=sum(arms)
                if best is None or score>best[0]: best=(score,x,y,arms)
    if best is None: return {},marks,bg,hue
    _,xx,xy,arms=best
    xd={'kind':'x','color':hue,'center':[xx,xy],'rad':arms}
    def cells(d,center):
        cx,cy=center; out=set()
        if d['kind']=='line':
            a,b=d['rad']
            for x in range(cx-a,cx+b+1):
                if 0<=x<w and 0<=cy<h-1: out.add((x,cy))
        elif d['kind']=='x':
            for (dx,dy),n in zip(((-1,-1),(1,-1),(-1,1),(1,1)),d['rad']):
                for k in range(1,n+1):
                    px,py=cx+dx*k,cy+dy*k
                    if 0<=px<w and 0<=py<h-1: out.add((px,py))
        else:
            R=d['rad']
            for dx in range(-R,R+1):
                dy=R-abs(dx)
                for sy in ((-1,1) if dy else (1,)):
                    px,py=cx+dx,cy+sy*dy
                    if 0<=px<w and 0<=py<h-1: out.add((px,py))
        return out
    # Remove line, X and marker centres; the remaining large diagonal
    # component is the diamond.
    rem={(int(x),int(y)) for y,x in np.argwhere(e==hue)}
    rem-=cells(line,line['center']); rem-=cells(xd,xd['center']); rem-=set(marks)
    comps=[]
    while rem:
        p=rem.pop(); comp={p}; stack=[p]
        while stack:
            x,y=stack.pop()
            for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)):
                z=(x+dx,y+dy)
                if z in rem: rem.remove(z); comp.add(z); stack.append(z)
        comps.append(comp)
    comp=max(comps,key=len)
    xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
    dc=[(min(xs)+max(xs))//2,(min(ys)+max(ys))//2]
    dd={'kind':'diamond','color':hue,'center':dc,'rad':(max(xs)-min(xs))//2}
    return {0:line,1:xd,2:dd},marks,bg,hue

def _l2_cells(d,center,h=64,w=64):
    cx,cy=center; out=set()
    if d['kind']=='line':
        l,r=d['rad']
        for x in range(cx-l,cx+r+1):
            if 0<=x<w and 0<=cy<h-1: out.add((x,cy))
    elif d['kind']=='x':
        for (dx,dy),n in zip(((-1,-1),(1,-1),(-1,1),(1,1)),d['rad']):
            for k in range(1,n+1):
                px,py=cx+dx*k,cy+dy*k
                if 0<=px<w and 0<=py<h-1: out.add((px,py))
    else:
        R=d['rad']
        for dx in range(-R,R+1):
            dy=R-abs(dx)
            for sy in ((-1,1) if dy else (1,)):
                px,py=cx+dx,cy+sy*dy
                if 0<=px<w and 0<=py<h-1: out.add((px,py))
    return out

def _l2_goals(ds,marks):
    # All objects share one hue, so choosing each object's locally best marker
    # fit is ambiguous.  Solve the actual global exact cover: one reachable
    # placement per object, no marker used twice, and every marker covered.
    options=[]; ids=sorted(ds)
    for i in ids:
        d=ds[i]; ex,ey=d['center']; bymask={}
        for y in range(0,63):
            for x in range(64):
                if (x-ex)%3 or (y-ey)%3: continue
                cs=_l2_cells(d,[x,y])
                mask=0
                for k,p in enumerate(marks):
                    if p in cs: mask |= (1<<k)
                if not mask: continue
                z=(abs(x-ex)+abs(y-ey),x,y,mask)
                if mask not in bymask or z<bymask[mask]: bymask[mask]=z
        options.append(list(bymask.values()))
    full=(1<<len(marks))-1; best=None
    if all(options):
        for combo in itertools.product(*options):
            used=0; ok=True
            for dist,x,y,mask in combo:
                if used & mask: ok=False; break
                used |= mask
            if ok and used==full:
                key=(sum(z[0] for z in combo),tuple((z[1],z[2]) for z in combo))
                if best is None or key<best[0]: best=(key,combo)
    if best is not None:
        return {i:[z[1],z[2]] for i,z in zip(ids,best[1])}
    return {}

def _l2_hidden(st,ds,i,px,py,h,w):
    rank={'x':0,'diamond':1,'line':2}; r=rank[ds[i]['kind']]
    return any(j!=i and rank[ds[j]['kind']]>r and
               (px,py) in _l2_cells(ds[j],st['centers'][j],h,w) for j in ds)

def _l3_setup():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg()
    # Framed marker centres live in the playfield; the six coloured 2-border
    # swatches at top/bottom are a legend and are intentionally ignored here.
    marks=[]
    for y in range(10,h-10):
        for x in range(1,w-1):
            v=int(e[y,x])
            if v not in (bg,0,4,15) and all(int(e[y+dy,x+dx])==4
                    for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),
                                  (-1,1),(0,1),(1,1))):
                marks.append((x,y,v))
    # The active solid plus is the unique playfield 0 with orthogonal arms.
    plus=None; pc=None
    for y,x in np.argwhere(e==0):
        y=int(y); x=int(x)
        if not (10<=y<h-10 and 1<=x<w-1): continue
        ns=[int(e[y-1,x]),int(e[y+1,x]),int(e[y,x-1]),int(e[y,x+1])]
        if len(set(ns))==1 and ns[0] not in (bg,0,4,15):
            q=ns[0]; l=r=t=b=0
            while x-l-1>=0 and int(e[y,x-l-1])==q: l+=1
            while x+r+1<w and int(e[y,x+r+1])==q: r+=1
            while y-t-1>=0 and int(e[y-t-1,x])==q: t+=1
            while y+b+1<h-1 and int(e[y+b+1,x])==q: b+=1
            # The clipped horizontal arm has the same true radius as the
            # fully visible vertical arm.
            R=max(l,r,t,b)
            plus={'kind':'plus','color':q,'center':[x,y],'rad':[R,R,R,R]}
            pc=[x,y]; break
    # Find the strongest four-way diagonal centre away from legend/markers.
    best=None
    marker_cells=set()
    for mx,my,q in marks:
        for yy in range(my-1,my+2):
            for xx in range(mx-1,mx+2): marker_cells.add((xx,yy))
    for y in range(10,h-10):
        for x in range(1,w-1):
            q=int(e[y,x])
            if q in (bg,0,4,15) or (x,y) in marker_cells: continue
            arms=[]
            for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)):
                k=0
                while (0<=x+dx*(k+1)<w and 10<=y+dy*(k+1)<h-10
                       and int(e[y+dy*(k+1),x+dx*(k+1)])==q):
                    k+=1
                arms.append(k)
            if min(arms)>=3:
                z=(sum(arms),x,y,q,arms)
                if best is None or z[0]>best[0]: best=z
    shapes={}
    if plus is not None: shapes[0]=plus
    if best is not None:
        _,x,y,q,arms=best
        shapes[1]={'kind':'x','color':q,'center':[x,y],'rad':arms}
    return shapes,marks,bg

def _l3_palettes():
    """Return (hue, interior-cells) for 4x4 wells in a 2-bordered 6x6 box."""
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; out=[]
    for y in range(h-5):
        for x in range(w-5):
            border=(list(e[y,x:x+6])+list(e[y+5,x:x+6])+
                    list(e[y+1:y+5,x])+list(e[y+1:y+5,x+5]))
            if not border or any(int(v)!=2 for v in border): continue
            inn=e[y+1:y+5,x+1:x+5]
            vals=set(int(v) for v in inn.flat)
            if len(vals)==1:
                q=list(vals)[0]
                out.append((q,{(xx,yy) for yy in range(y+1,y+5)
                                      for xx in range(x+1,x+5)}))
    return out

def _l3_cells(d,center,h=64,w=64):
    cx,cy=center; out=set()
    if d['kind']=='plus':
        l,r,t,b=d['rad']
        for x in range(cx-l,cx+r+1):
            if 0<=x<w and 0<=cy<h-1: out.add((x,cy))
        for y in range(cy-t,cy+b+1):
            if 0<=y<h-1 and 0<=cx<w: out.add((cx,y))
    else:
        for (dx,dy),n in zip(((-1,-1),(1,-1),(-1,1),(1,1)),d['rad']):
            for k in range(1,n+1):
                x,y=cx+dx*k,cy+dy*k
                if 0<=x<w and 0<=y<h-1: out.add((x,y))
    return out

def _l3_goals(ds,marks):
    # The legend pairs different object/marker hues.  Infer the assignment
    # geometrically: the solid plus has a unique placement covering the most
    # centres of one marker hue; assign that hue, then fit X to the remaining
    # marker hue.  On L3 this yields plus=(15,30) over all three c markers and
    # X=(39,30) over the two far e markers.
    goals={}; used=set()
    for i in sorted(ds,key=lambda z:0 if ds[z]['kind']=='plus' else 1):
        d=ds[i]; ex,ey=d['center']; best=None
        for q in sorted(set(v for x,y,v in marks) - used):
            pts=[(x,y) for x,y,v in marks if v==q]
            for y in range(0,63):
                for x in range(64):
                    if (x-ex)%3 or (y-ey)%3: continue
                    cs=_l3_cells(d,[x,y])
                    n=sum(p in cs for p in pts)
                    if not n: continue
                    key=(-n,abs(x-ex)+abs(y-ey),x,y,q)
                    if best is None or key<best: best=key
        if best is not None:
            _,dist,x,y,q=best; goals[i]=[x,y]; used.add(q)
    return goals

def _l3_target_colors(ds,marks,goals=None):
    """Marker hue most strongly covered at each fitted placement."""
    if goals is None: goals=_l3_goals(ds,marks)
    out={}
    for i,p in goals.items():
        cells=_l3_cells(ds[i],p)
        cnt={}
        for x,y,q in marks:
            if (x,y) in cells: cnt[q]=cnt.get(q,0)+1
        if cnt: out[i]=max(cnt,key=cnt.get)
    return out

def _predict_l3(state,grid,action):
    cur=np.array(grid,dtype=int); ds,marks,bg=_l3_setup(); h,w=cur.shape
    st={'mode':'l3','centers':{int(i):list(p) for i,p in state['centers'].items()},
        'active':int(state['active']),
        'colors':{int(i):int(v) for i,v in state.get('colors',{}).items()},
        'meter':{int(i):int(v) for i,v in state.get('meter',{}).items()},
        'grace':{int(i):bool(v) for i,v in state.get('grace',{}).items()}}
    for i in ds:
        if i not in st['colors']: st['colors'][i]=ds[i]['color']
        if i not in st['meter']: st['meter'][i]=0
        if i not in st['grace']: st['grace'][i]=False
    c=st['active']; moved=False
    delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    if delta is not None and c in st['centers']:
        dx,dy=delta; cx,cy=st['centers'][c]; nx,ny=cx+dx,cy+dy
        if 0<=nx<w and 0<=ny<h-1:
            st['centers'][c]=[nx,ny]; moved=True
    if action==5 and len(ds)>1:
        ids=sorted(ds); st['active']=ids[(ids.index(c)+1)%len(ids)]
    footer=cur[-1].copy()
    # L3 handoff cost: leaving the solid plus spends one.  The hollow X is
    # free at entry (#111), but leaving it from the marker-fit placement
    # spends one (#135), matching the completed-outline lock rule.
    gs=_l3_goals(ds,marks); ts=_l3_target_colors(ds,marks,gs)
    fit=(c in gs and st['centers'][c]==gs[c])
    proper=(fit and c in ts and st['colors'][c]==ts[c])
    # An unpainted plus handoff always spends one; a marker-fit unpainted X
    # also spends one.  Correctly painted+placed shapes lock for free (#152).
    switch_charge=(action==5 and c in ds and
                   ((ds[c]['kind']=='plus' and not proper) or
                    (ds[c]['kind']=='x' and fit and not proper)))
    if switch_charge:
        ff=np.where(footer==15)[0]
        if len(ff): footer[int(ff[-1])]=1
        # A handoff from an unpainted marker-fit placement resets its meter.
        if fit:
            # Completed handoff restores the shape's intrinsic phase: plus=0,
            # hollow X=1.  After X was handed off at #135, x42 was free and
            # x45 charged (#153-154), proving the staggered restart.
            st['meter'][c]=0 if ds[c]['kind']=='plus' else 1
            st['grace'][c]=False
    # Ordinary translations spend every third move.  Passing the solid plus
    # behind the hollow X centre grants a one-use grace to the NEXT due move:
    # x24 armed it, x21 was waived with meter still due, then x18 charged.
    if moved:
        center_hit=(ds[c]['kind']=='plus' and any(
            j!=c and ds[j]['kind']=='x' and tuple(st['centers'][j]) in
            _l3_cells(ds[c],[nx,ny],h,w) for j in ds))
        # Once painted to a marker hue, the established one-step approach
        # waiver applies: at #147 c-plus (18,21) did not yet cover c(15,18),
        # but the next left placement would.  A due charge is deferred.
        cells_now=_l3_cells(ds[c],[nx,ny],h,w)
        cells_ahead=_l3_cells(ds[c],[nx+dx,ny+dy],h,w)
        own={(mx,my) for mx,my,q in marks if q==st['colors'][c]}
        approach=(not any(p in cells_now for p in own) and
                  any(p in cells_ahead for p in own))
        if st['meter'][c]>=2:
            if st['grace'][c]:
                st['grace'][c]=False
            elif approach:
                pass
            else:
                ff=np.where(footer==15)[0]
                if len(ff): footer[int(ff[-1])]=1
                st['meter'][c]=0
        else:
            st['meter'][c]+=1
            if center_hit: st['grace'][c]=True
        # A coloured palette well paints the entire active shape as soon as
        # any painted cell enters its 4x4 interior.  At #143 the plus's top
        # endpoint (30,8) entered the c well and all 52 visible cells became c.
        cells=_l3_cells(ds[c],st['centers'][c],h,w)
        hits=[(len(cells & ps),q) for q,ps in _l3_palettes() if cells & ps]
        if hits: st['colors'][c]=max(hits)[1]
    out=np.array(ENTRY_GRID,dtype=int).copy()
    for i,d in ds.items():
        for px,py in _l3_cells(d,d['center'],h,w):
            if int(out[py,px]) in (d['color'],0): out[py,px]=bg
        ex,ey=d['center']
        if d['kind']=='x' and (st['centers'][i]!=d['center'] or st['active']==i):
            out[ey,ex]=bg
    for mx,my,q in marks:
        out[my-1:my+2,mx-1:mx+2]=4; out[my,mx]=q
    # L3's hollow X is above the solid plus: at plus x33 the X cell
    # (33,30) remains hue-a rather than being overpainted (#118).
    for i in sorted(ds,key=lambda z:1 if ds[z]['kind']=='x' else 0):
        for px,py in _l3_cells(ds[i],st['centers'][i],h,w):
            out[py,px]=st['colors'][i]
    # In L3 an inactive X has a hue-filled centre even after it has moved.
    # This was first hidden by the entry coincidence (#121) and confirmed
    # directly when the moved X was deselected at (39,30) (#135).
    for i,d in ds.items():
        if d['kind']=='x' and st['active']!=i:
            ex,ey=st['centers'][i]; out[ey,ex]=st['colors'][i]
    ac=st['active']; ax,ay=st['centers'][ac]
    hidden=(ds[ac]['kind']=='plus' and any(j!=ac and ds[j]['kind']=='x' and
            (ax,ay) in _l3_cells(ds[j],st['centers'][j],h,w) for j in ds))
    if not hidden: out[ay,ax]=0
    out[-1]=footer
    # L3 requires both geometric placement and palette-painted marker hues.
    # The unpainted positions were nonterminal (#134/#135); #143 confirmed
    # direct palette contact recolours an entire shape.
    goals=_l3_goals(ds,marks); targets=_l3_target_colors(ds,marks,goals)
    done=(bool(goals) and all(st['centers'].get(i)==p for i,p in goals.items())
          and all(st['colors'].get(i)==q for i,q in targets.items()))
    return out.tolist(),{'level_up':bool(done and CURRENT_LEVEL!=7),'dead':False,
                         'win':bool(done and CURRENT_LEVEL==7)},st

def _l4_setup():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg()
    wells=_l3_palettes()
    well_cells=set()
    for q,ps in wells: well_cells |= ps
    marks=[]; marker_cells=set()
    for y in range(1,h-2):
        for x in range(1,w-1):
            v=int(e[y,x])
            if v not in (bg,0,4,15) and all(int(e[y+dy,x+dx])==4
                    for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),
                                  (-1,1),(0,1),(1,1))):
                marks.append((x,y,v))
                marker_cells |= {(x+dx,y+dy) for dx in (-1,0,1)
                                                 for dy in (-1,0,1)}
    # Active hollow X is grounded by the unique 0 and four diagonal arms.
    zy,zx=map(int,np.argwhere(e==0)[0]); qx=int(e[zy-1,zx-1]); arms=[]
    for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)):
        k=0
        while (0<=zx+dx*(k+1)<w and 0<=zy+dy*(k+1)<h-1 and
               int(e[zy+dy*(k+1),zx+dx*(k+1)])==qx): k+=1
        arms.append(k)
    xd={'kind':'x','color':qx,'center':[zx,zy],'rad':arms}
    # Strongest orthogonal cross outside wells/marker centres is the plus.
    best=None
    for y in range(1,h-2):
        for x in range(1,w-1):
            q=int(e[y,x])
            if q in (bg,0,2,4,15) or (x,y) in well_cells: continue
            if not all(int(e[y+dy,x+dx])==q for dx,dy in
                       ((-1,0),(1,0),(0,-1),(0,1))): continue
            l=r=t=b=0
            while x-l-1>=0 and int(e[y,x-l-1])==q: l+=1
            while x+r+1<w and int(e[y,x+r+1])==q: r+=1
            while y-t-1>=0 and int(e[y-t-1,x])==q: t+=1
            while y+b+1<h-1 and int(e[y+b+1,x])==q: b+=1
            z=(l+r+t+b,x,y,q,max(l,r,t,b))
            if best is None or z[0]>best[0]: best=z
    _,px,py,qp,R=best
    pd={'kind':'plus','color':qp,'center':[px,py],'rad':[R,R,R,R]}
    # Remaining large diagonal component is the diamond outline.
    skip={qx,qp}; dcan=None
    vals=[int(v) for v in np.unique(e) if int(v) not in
          (bg,0,2,4,15) and int(v) not in skip]
    for q in vals:
        rem={(int(x),int(y)) for y,x in np.argwhere(e==q)
             if (int(x),int(y)) not in well_cells and
                (int(x),int(y)) not in marker_cells}
        while rem:
            p=rem.pop(); comp={p}; stack=[p]
            while stack:
                x,y=stack.pop()
                for dx,dy in ((-1,-1),(1,-1),(-1,1),(1,1)):
                    z=(x+dx,y+dy)
                    if z in rem: rem.remove(z); comp.add(z); stack.append(z)
            if len(comp)>=8:
                xs=[z[0] for z in comp]; ys=[z[1] for z in comp]
                cx=(min(xs)+max(xs))//2; cy=(min(ys)+max(ys))//2
                R=(max(xs)-min(xs))//2
                good=all(abs(x-cx)+abs(y-cy)==R for x,y in comp)
                z=(len(comp),q,cx,cy,R)
                if good and (dcan is None or z[0]>dcan[0]): dcan=z
    _,qd,dx,dy,DR=dcan
    dd={'kind':'diamond','color':qd,'center':[dx,dy],'rad':DR}
    return {0:pd,1:xd,2:dd},marks,bg

def _l4_goals(ds,marks):
    # One reachable placement per shape, jointly covering every visible or
    # entry-occluded marker.  The hidden pair disambiguates the two covers.
    marks=list(marks)+_l4_hidden_marks(ds,marks)
    options=[]; ids=sorted(ds)
    for i in ids:
        d=ds[i]; ex,ey=d['center']; bymask={}
        for y in range(63):
            for x in range(64):
                if (x-ex)%3 or (y-ey)%3: continue
                cs=set(_shape_cells(d,[x,y]))
                mask=0
                for k,(mx,my,q) in enumerate(marks):
                    if (mx,my) in cs: mask |= (1<<k)
                if not mask: continue
                z=(abs(x-ex)+abs(y-ey),x,y,mask)
                if mask not in bymask or z<bymask[mask]: bymask[mask]=z
        options.append(list(bymask.values()))
    full=(1<<len(marks))-1; best=None
    if all(options):
        for combo in itertools.product(*options):
            used=0; ok=True
            for dist,x,y,mask in combo:
                if used&mask: ok=False; break
                used |= mask
            if ok and used==full:
                key=(sum(z[0] for z in combo),tuple((z[1],z[2]) for z in combo))
                if best is None or key<best[0]: best=(key,combo)
    if best is None: return {}
    return {i:[z[1],z[2]] for i,z in zip(ids,best[1])}

def _l4_targets(ds,marks,goals=None):
    if goals is None: goals=_l4_goals(ds,marks)
    all_marks=list(marks)+_l4_hidden_marks(ds,marks)
    out={}
    for i,p in goals.items():
        cs=set(_shape_cells(ds[i],p)); cnt={}
        for x,y,q in all_marks:
            if (x,y) in cs: cnt[q]=cnt.get(q,0)+1
        if cnt: out[i]=max(cnt,key=cnt.get)
    return out

def _l4_hidden_marks(ds,marks):
    """Recover marker centres occluded by an entry-position shape.

    A partial 3x3 frame has two complete 4-columns (or rows) around a centre
    painted with a movable shape.  Its missing hue is the nearest visible
    framed-marker family.  These are genuine goal markers, not decoration:
    including both hidden hue8 centres makes the global exact cover unique.
    """
    a=np.array(ENTRY_GRID,dtype=int); h,w=a.shape
    moving={d['color'] for d in ds.values()}; cand=set()
    for y in range(1,h-2):
        for x in range(1,w-1):
            if int(a[y,x]) not in moving: continue
            vert=all(int(a[y+dy,x-1])==4 and int(a[y+dy,x+1])==4
                     for dy in (-1,0,1))
            horiz=all(int(a[y-1,x+dx])==4 and int(a[y+1,x+dx])==4
                      for dx in (-1,0,1))
            if vert or horiz: cand.add((x,y))
    out=[]
    for x,y in sorted(cand):
        if marks:
            q=min(marks,key=lambda z:(abs(z[0]-x)+abs(z[1]-y),z))[2]
            out.append((x,y,q))
    return out


def _predict_l4(state,grid,action):
    cur=np.array(grid,dtype=int); ds,marks,bg=_l4_setup(); h,w=cur.shape
    st={'mode':'l4','centers':{int(i):list(p) for i,p in state['centers'].items()},
        'active':int(state['active']),
        'colors':{int(i):int(v) for i,v in state.get('colors',{}).items()},
        'meter':{int(i):int(v) for i,v in state.get('meter',{}).items()},
        'grace':{int(i):bool(v) for i,v in state.get('grace',{}).items()},
        'locked':{int(i):bool(v) for i,v in state.get('locked',{}).items()}}
    for i in ds:
        if i not in st['colors']: st['colors'][i]=ds[i]['color']
        if i not in st['meter']: st['meter'][i]=0
        if i not in st['grace']: st['grace'][i]=False
        if i not in st['locked']: st['locked'][i]=False
    c=st['active']; delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    moved=False
    if delta is not None:
        dx,dy=delta; cx,cy=st['centers'][c]; nx,ny=cx+dx,cy+dy
        if 0<=nx<w and 0<=ny<h-1:
            st['centers'][c]=[nx,ny]; moved=True
            st['locked'][c]=False
    if action==5:
        # L4 has an explicit per-object lock step. Switching away from a
        # correctly painted fitted object locks it; all three must be locked,
        # so moving the final plus into place is not terminal (#239).
        goals_lock=_l4_goals(ds,marks)
        targets_lock=_l4_targets(ds,marks,goals_lock)
        if (c in goals_lock and c in targets_lock and
                st['centers'][c]==goals_lock[c] and
                st['colors'][c]==targets_lock[c]):
            st['locked'][c]=True
        # L4 handoff parks the object at the due phase, but a contact credit
        # already earned at its fitted placement remains attached to it while
        # inactive.
        st['meter'][c]=2
        ids=sorted(ds); st['active']=ids[(ids.index(c)+1)%len(ids)]
    footer=cur[-1].copy()
    if moved:
        cells=set(_shape_cells(ds[c],st['centers'][c],h,w))
        prev_cells=set(_shape_cells(ds[c],[cx,cy],h,w))
        ahead=set(_shape_cells(ds[c],[nx+dx,ny+dy],h,w))
        own={(mx,my) for mx,my,q in marks if q==st['colors'][c]}
        other_shape_cells=set().union(*(set(_shape_cells(ds[j],st['centers'][j],h,w))
                                        for j in ds if j!=c))
        available_own={p for p in own if p not in other_shape_cells}
        own_contact=any(p in cells for p in own)
        goals_now=_l4_goals(ds,marks)
        # A hollow X receives exactly one two-step pre-landing waiver: at
        # (30,21), two further up moves reach its true centre (30,15), so #263
        # is free.  The immediate approach to (30,18) is not waived and #264
        # charges normally; this is a pre-landing cue, not a persistent phase.
        x_goal_approach=(ds[c]['kind']=='x' and c in goals_now and
             [nx+2*dx,ny+2*dy]==goals_now[c])
        # Covering only part of the assigned marker set is constructive and
        # waives a due charge (diamond (30,48) covers 9@(24,51)).  A fully
        # fitted placement is a lock instead and does not receive this waiver.
        # Exact partial marker placement is constructive for the diamond
        # outline only.  A painted plus merely sliding along an owned marker
        # still charges when due (#237 at centre x27).
        partial_own=(ds[c]['kind']=='diamond' and
                     any(p in cells for p in available_own) and
                     (c not in goals_now or st['centers'][c]!=goals_now[c]))
        # One-step framed-marker approach is constructive for the solid plus
        # and diamond, but not for a hollow X: after reselection the X's due
        # left move toward 8@(42,36) charged normally (#241).
        approach=(ds[c]['kind']!='x' and not own_contact and
                  any(p in ahead for p in available_own))
        # Entering the three-cell playfield margin is another constructive
        # contact: the diamond's due move to x12 puts its left vertex at x3.
        # It waives that one due charge, without resetting the meter.
        def at_margin(cs):
            # The side rails grant contact credit; the top/bottom are occupied
            # by palettes/footer and are not equivalent rails (#213 y12).
            return any(x in (3,w-4) for x,y in cs)
        margin_entry=at_margin(cells) and not at_margin(prev_cells)
        # Contact with another movable shape arms one deferred charge waiver.
        # On L4 the X first enters the plus at x33; its due x39 translation is
        # therefore free, but the credit is consumed rather than resetting.
        # Palette collision uses the whole bordered 6x6 well, not only its
        # 4x4 coloured interior.  At diamond (12,48), its outline first lands
        # on the hue9 well's border and the entire diamond repaints.
        palette_contacts=[]; new_palette_contacts=[]; near_palette=False
        for q,ps in _l3_palettes():
            zone={(x+ox,y+oy) for x,y in ps for ox in (-1,0,1)
                  for oy in (-1,0,1) if 0<=x+ox<w and 0<=y+oy<h-1}
            near={(x+ox,y+oy) for x,y in ps for ox in (-2,-1,0,1,2)
                  for oy in (-2,-1,0,1,2) if 0<=x+ox<w and 0<=y+oy<h-1}
            if cells&zone:
                hit=(len(cells&zone),q); palette_contacts.append(hit)
                if not (prev_cells&zone): new_palette_contacts.append(hit)
            if cells&near: near_palette=True
        # Any framed marker is also constructive contact, regardless of
        # whether the active shape has already been repainted to that hue.
        # At #231 the still-c plus crosses foreign 9@(33,45), arming the
        # deferred credit consumed by its due move to y48.
        marker_contact=any((mx,my) in cells for mx,my,q in marks)
        plus_cells=set().union(*(set(_shape_cells(ds[j],st['centers'][j],h,w))
                                 for j in ds if j!=c and ds[j]['kind']=='plus'))
        plus_entry=(ds[c]['kind']=='diamond' and bool(cells & plus_cells)
                    and not bool(prev_cells & plus_cells))
        contact=(any(cells & set(_shape_cells(ds[j],st['centers'][j],h,w))
                     for j in ds if j!=c) or bool(palette_contacts)
                 or near_palette or marker_contact or at_margin(cells))
        if st['meter'][c]>=2:
            # Entering a new palette is a forced repaint step: if the meter is
            # due it charges even when an older contact credit is banked.
            # At X (18,42), sustained e contact supplied a credit but the new
            # hue9 well still charged and replaced the outline (#252).
            if new_palette_contacts and len(palette_contacts)>1:
                # Simultaneously entering a new palette while still touching
                # another palette is forced; a lone palette entry may consume
                # an already-earned contact credit.
                ff=np.where(footer==15)[0]
                if len(ff): footer[int(ff[-1])]=1
                st['meter'][c]=0
                st['grace'][c]=False
            elif st['grace'][c]:
                st['grace'][c]=False
            elif (margin_entry or partial_own or approach or x_goal_approach
                  or plus_entry):
                # The solid plus grants its contact credit on entry, so a due
                # diamond first touching it at (30,33) is free (#275).
                pass
            else:
                ff=np.where(footer==15)[0]
                if len(ff): footer[int(ff[-1])]=1
                st['meter'][c]=0
        else:
            st['meter'][c]+=1
            if contact: st['grace'][c]=True
        if palette_contacts:
            # If one outline spans two wells, the newly entered well paints it,
            # rather than a still-touched old well.  X descending at (18,42)
            # remains on e with its NW arm but newly enters 9 with SW, so 9 wins.
            st['colors'][c]=max(new_palette_contacts or palette_contacts)[1]
    out=np.array(ENTRY_GRID,dtype=int).copy()
    for i,d in ds.items():
        for x,y in _shape_cells(d,d['center'],h,w):
            if int(out[y,x]) in (d['color'],0): out[y,x]=bg
        ex,ey=d['center']
        if int(out[ey,ex])==0: out[ey,ex]=bg
    for mx,my,q in list(marks)+_l4_hidden_marks(ds,marks):
        out[my-1:my+2,mx-1:mx+2]=4; out[my,mx]=q
    rank={'plus':0,'x':1,'diamond':2}
    for i in sorted(ds,key=lambda z:rank[ds[z]['kind']]):
        for x,y in _shape_cells(ds[i],st['centers'][i],h,w):
            out[y,x]=st['colors'][i]
    ac=st['active']
    # A hollow X displays its painted centre while inactive; selection cuts
    # that centre back to 0.  This is visible when the fitted hue8 X hands
    # control to the diamond.
    for i,d in ds.items():
        if d['kind']=='x' and i!=ac:
            ix,iy=st['centers'][i]; out[iy,ix]=st['colors'][i]
    ax,ay=st['centers'][ac]
    hidden=any(j!=ac and rank[ds[j]['kind']]>rank[ds[ac]['kind']] and
               ((ax,ay) in set(_shape_cells(ds[j],st['centers'][j],h,w)) or
                (ds[j]['kind']=='x' and (ax,ay)==tuple(st['centers'][j])))
               for j in ds)
    if not hidden: out[ay,ax]=0
    out[-1]=footer
    gs=_l4_goals(ds,marks); ts=_l4_targets(ds,marks,gs)
    done=(bool(gs) and all(st['centers'][i]==p for i,p in gs.items())
          and all(st['colors'][i]==q for i,q in ts.items())
          and all(st['locked'].get(i,False) for i in ds))
    return out.tolist(),{'level_up':bool(done and CURRENT_LEVEL!=7),'dead':False,
                         'win':bool(done and CURRENT_LEVEL==7)},st

def _predict_l2(state,grid,action):
    cur=np.array(grid,dtype=int); ds,marks,bg,hue=_l2_setup(); h,w=cur.shape
    default_meter={i:{'line':1,'x':0,'diamond':2}[d['kind']]
                   for i,d in ds.items()}
    st={'mode':'l2','centers':{int(i):list(p) for i,p in state['centers'].items()},
        'active':int(state['active']),
        'meter':{int(i):int(v) for i,v in state.get('meter',default_meter).items()}}
    c=st['active']; delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    moved=False
    if delta is not None:
        dx,dy=delta; cx,cy=st['centers'][c]; nx,ny=cx+dx,cy+dy
        if 0<=nx<w and 0<=ny<h-1:
            st['centers'][c]=[nx,ny]; moved=True
    if action==5:
        st['active']=(c+1)%3
    footer=cur[-1].copy()
    if action==5:
        # In the three-object board, switching away from a completed shape
        # locks that placement and spends one footer cell.
        goals=_l2_goals(ds,marks)
        if (c in goals and st['centers'][c]==goals[c]
                and ds[c]['kind']=='line'):
            ff=np.where(footer==15)[0]
            if len(ff): footer[int(ff[-1])]=1
    if moved:
        kind=ds[c]['kind']
        # Each object charges every third ordinary translation.  Their entry
        # meters are staggered (line=1, X=0, diamond=2), which produced the
        # apparent coordinate phases.  A constructive diamond/marker landing
        # waives a due charge without resetting the meter, so the charge is
        # deferred to its next ordinary move (x24 free, then x21 charges).
        due=(st['meter'][c]>=2)
        contact=False
        goals=_l2_goals(ds,marks)
        # Exact-cover marker contact can constructively waive a due charge
        # for the line/diamond.  X crossings never did (#88/#89/#91).
        if c in goals and ds[c]['kind']!='x':
            goal_cells=_l2_cells(ds[c],goals[c],h,w)
            owned=[p for p in marks if p in goal_cells]
            cells=_l2_cells(ds[c],[nx,ny],h,w)
            contact=any(p in cells for p in owned)
        if due and contact:
            free=True
        elif due:
            free=False; st['meter'][c]=0
        else:
            free=True; st['meter'][c]+=1
        if not free:
            ff=np.where(footer==15)[0]
            if len(ff): footer[int(ff[-1])]=1
    out=np.array(ENTRY_GRID,dtype=int).copy()
    for i,d in ds.items():
        for px,py in _l2_cells(d,d['center'],h,w):
            if int(out[py,px]) in (hue,0): out[py,px]=bg
        ex,ey=d['center']
        # Hollow centres are not painted cells.  In the same-hue entry board
        # the inactive X centre can look coloured, but moving it reveals
        # background, so erase hollow centres explicitly before redraw.
        if ((d['kind'] in ('x','diamond') and
             (st['centers'][i]!=d['center'] or st['active']==i))
             or int(out[ey,ex])==0):
            out[ey,ex]=bg
    for mx,my in marks:
        out[my-1:my+2,mx-1:mx+2]=4; out[my,mx]=hue
    rank={'x':0,'diamond':1,'line':2}
    for i in sorted(ds,key=lambda z:rank[ds[z]['kind']]):
        for px,py in _l2_cells(ds[i],st['centers'][i],h,w): out[py,px]=hue
    ac=st['active']; ax,ay=st['centers'][ac]
    if not _l2_hidden(st,ds,ac,ax,ay,h,w): out[ay,ax]=0
    out[-1]=footer
    goals=_l2_goals(ds,marks)
    done=bool(goals) and all(st['centers'][i]==p for i,p in goals.items())
    return out.tolist(),{'level_up':bool(done and CURRENT_LEVEL!=7),'dead':False,
                         'win':bool(done and CURRENT_LEVEL==7)},st


def _l5_setup():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg()
    marks=[]
    for y in range(1,h-2):
        for x in range(1,w-1):
            q=int(e[y,x])
            if q in (bg,0,1,4,15): continue
            if all(int(e[y+dy,x+dx])==4 for dx,dy in
                   ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),
                    (-1,1),(0,1),(1,1))):
                marks.append((x,y,q))
    # Solid plus: choose the strongest four-way orthogonal intersection.
    best=None
    for q in [int(v) for v in np.unique(e) if int(v) not in (bg,0,1,4,15)]:
        for y in range(1,h-2):
            for x in range(1,w-1):
                if int(e[y,x])!=q: continue
                arms=[]
                for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                    k=0
                    while (0<=x+dx*(k+1)<w and 0<=y+dy*(k+1)<h-1
                           and int(e[y+dy*(k+1),x+dx*(k+1)])==q):
                        k+=1
                    arms.append(k)
                if min(arms)>=2:
                    z=(sum(arms),q,x,y,arms)
                    if best is None or z>best: best=z
    ds={}
    if best is not None:
        _,q,x,y,arms=best
        ds[1]={'kind':'plus','color':q,'center':[x,y],
               'rad':[arms[0],arms[1],arms[2],arms[3]]}
    # The selected hollow square is identified by the 0 at its geometric centre.
    zs=np.argwhere(e==0)
    if len(zs):
        cy,cx=map(int,zs[0]); sqbest=None
        vals=[int(v) for v in np.unique(e) if int(v) not in (bg,0,1,4,15)]
        for q in vals:
            for R in range(2,min(h,w)//2):
                pts=((cx-R,cy),(cx+R,cy),(cx,cy-R),(cx,cy+R))
                n=sum(0<=x<w and 0<=y<h-1 and int(e[y,x])==q for x,y in pts)
                z=(n,R,q)
                if n>=3 and (sqbest is None or z>sqbest): sqbest=z
        if sqbest is not None:
            _,R,q=sqbest
            ds[0]={'kind':'square','color':q,'center':[cx,cy],'rad':R}
    return ds,marks,bg


def _l5_cells(d,center,h=64,w=64):
    cx,cy=center; out=set()
    if d['kind']=='plus':
        l,r,t,b=d['rad']
        for x in range(cx-l,cx+r+1):
            if 0<=x<w and 0<=cy<h-1: out.add((x,cy))
        for y in range(cy-t,cy+b+1):
            if 0<=cx<w and 0<=y<h-1: out.add((cx,y))
    else:
        R=d['rad']
        for x in range(cx-R,cx+R+1):
            for y in (cy-R,cy+R):
                if 0<=x<w and 0<=y<h-1: out.add((x,y))
        for y in range(cy-R+1,cy+R):
            for x in (cx-R,cx+R):
                if 0<=x<w and 0<=y<h-1: out.add((x,y))
    return out


def _l5_plus_cells(lines,h=64,w=64):
    hx0,hx1,hy,vx,vy0,vy1=lines; out=set()
    for x in range(hx0,hx1+1):
        if 0<=x<w and 0<=hy<h-1: out.add((x,hy))
    for y in range(vy0,vy1+1):
        if 0<=vx<w and 0<=y<h-1: out.add((vx,y))
    return out


def _l5_rect_cells(box,h=64,w=64):
    x0,x1,y0,y1=box; out=set()
    for x in range(x0,x1+1):
        if 0<=x<w:
            if 0<=y0<h-1: out.add((x,y0))
            if 0<=y1<h-1: out.add((x,y1))
    for y in range(y0+1,y1):
        if 0<=y<h-1:
            if 0<=x0<w: out.add((x0,y))
            if 0<=x1<w: out.add((x1,y))
    return out


def _predict_l5(state,grid,action):
    cur=np.array(grid,dtype=int)
    # The recorded level-up step is tagged with the newly entered level and
    # therefore reinitializes this branch while its input grid is still L4.
    # L4 is uniquely identified here by its bordered hue2 palette panels.
    if np.any(cur==2):
        return cur.tolist(),{'level_up':True,'dead':False,'win':False},state
    ds,marks,bg=_l5_setup(); h,w=cur.shape
    st={'mode':'l5',
        'centers':{int(i):list(p) for i,p in state['centers'].items()},
        'active':int(state['active']),
        'meter':{int(i):int(v) for i,v in state.get('meter',{}).items()},
        'covered':set(int(k) for k in state.get('covered',set())),
        'bbox':{int(i):list(v) for i,v in state.get('bbox',{}).items()},
        'plines':{int(i):list(v) for i,v in state.get('plines',{}).items()}}
    for i in ds:
        if i not in st['meter']: st['meter'][i]=0
        if ds[i]['kind']=='square' and i not in st['bbox']:
            sx,sy=st['centers'][i]; R=ds[i]['rad']
            st['bbox'][i]=[sx-R,sx+R,sy-R,sy+R]
        if ds[i]['kind']=='plus' and i not in st['plines']:
            sx,sy=st['centers'][i]; l,r,t,b=ds[i]['rad']
            st['plines'][i]=[sx-l,sx+r,sy,sx,sy-t,sy+b]
    c=st['active']; moved=False; device_deform=False
    delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    if delta is not None:
        dx,dy=delta; cx,cy=st['centers'][c]; nx,ny=cx+dx,cy+dy
        if ds[c]['kind']=='square':
            x0,x1,y0,y1=st['bbox'][c]
            cand=[x0+dx,x1+dx,y0+dy,y1+dy]
            device={(int(x),int(y)) for y,x in np.argwhere(np.array(ENTRY_GRID)==1)}
            hit=bool(_l5_rect_cells(cand,h,w) & device)
            if hit and action==3:
                # Pushing the flexible loop left into the device holds its
                # left side, retracts the right side, and extends the shorter-
                # centre-error vertical side by three. Odd/even heights thus
                # alternate top then bottom (#325-326), conserving perimeter.
                if (y1-y0+1)%2:
                    cand=[x0,x1-3,y0-3,y1]
                else:
                    cand=[x0,x1-3,y0,y1+3]
                device_deform=True
            if cand[0]<=cand[1] and cand[2]<=cand[3]:
                st['bbox'][c]=cand
                st['centers'][c]=[(cand[0]+cand[1]+1)//2,
                                  (cand[2]+cand[3]+1)//2]
                nx,ny=st['centers'][c]; moved=True
        elif 0<=nx<w and 0<=ny<h-1:
            oldpl=list(st['plines'][c])
            hx0,hx1,hy,vx,vy0,vy1=oldpl
            cand=[hx0+dx,hx1+dx,hy+dy,vx+dx,vy0+dy,vy1+dy]
            device={(int(x),int(y)) for y,x in np.argwhere(np.array(ENTRY_GRID)==1)}
            hit=bool(_l5_plus_cells(cand,h,w) & device)
            if hit and action in (1,2):
                # A vertical push whose vertical stroke meets the rigid device
                # pins that stroke (and the selection anchor); only the
                # perpendicular horizontal stroke slides by three (#340).
                vpart={(cand[3],y) for y in range(cand[4],cand[5]+1)}
                if vpart & device:
                    cand=[hx0+dx,hx1+dx,hy+dy,vx,vy0,vy1]
                    nx,ny=cx,cy; device_deform=True
            elif hit and action in (3,4):
                # Symmetrically, a blocked horizontal stroke is pinned while
                # the vertical stroke slides sideways.
                hpart={(x,cand[2]) for x in range(cand[0],cand[1]+1)}
                if hpart & device:
                    cand=[hx0,hx1,hy,vx+dx,vy0+dy,vy1+dy]
                    nx,ny=cx,cy; device_deform=True
            st['plines'][c]=cand
            st['centers'][c]=[nx,ny]; moved=True
    if action==5:
        # A handoff records every matching framed marker covered by the parked
        # shape. L5 therefore asks each shape to visit two disjoint pair
        # placements; the frames reappear later, but completion is remembered.
        parked=(_l5_rect_cells(st['bbox'][c],h,w) if ds[c]['kind']=='square'
                else _l5_plus_cells(st['plines'][c],h,w))
        for k,(mx,my,q) in enumerate(marks):
            if q==ds[c]['color'] and (mx,my) in parked:
                st['covered'].add(k)
        ids=sorted(ds); st['active']=ids[(ids.index(c)+1)%len(ids)]
    footer=cur[-1].copy()
    # ACTION5 reads but does not advance/reset the object's translation phase:
    # the due square handoff charged and remained due (#302,#315), while the
    # phase1 plus handoff was free (#314).
    if action==5 and st['meter'][c]>=2:
        ff=np.where(footer==15)[0]
        if len(ff): footer[int(ff[-1])]=1
    if moved:
        d=ds[c]; px,py=st['centers'][c]
        if d['kind']=='plus':
            hx0,hx1,hy,vx,vy0,vy1=st['plines'][c]
            ohx0,ohx1,ohy,ovx,ovy0,ovy1=oldpl
            left,right,top,bottom=min(hx0,vx),max(hx1,vx),min(hy,vy0),max(hy,vy1)
            pleft,pright,ptop,pbottom=min(ohx0,ovx),max(ohx1,ovx),min(ohy,ovy0),max(ohy,ovy1)
            clipped=(left<0 or right>=w or top<0 or bottom>=h-1)
            prev_clipped=(pleft<0 or pright>=w or ptop<0 or pbottom>=h-1)
        else:
            left,right,top,bottom=st['bbox'][c]
            pleft,pright,ptop,pbottom=x0,x1,y0,y1
            clipped=(left<0 or right>=w or top<0 or bottom>=h-1)
            prev_clipped=(pleft<0 or pright>=w or ptop<0 or pbottom>=h-1)
        # First arrival at a screen clip or either x=3/60 playfield side rail
        # grants one waiver (#305,#320). Sustained margin travel is ordinary
        # and the next due move charges (#306).
        own_marks=[(mx,my) for mx,my,q in marks if q==d['color']]
        target_width=(max(x for x,y in own_marks)-min(x for x,y in own_marks)+1
                      if own_marks else 0)
        # Device reshapes are constructive while still approaching the marker
        # aspect (width 16,13), but the exact target width10 move is due and
        # charges (#327).
        device_credit=(d['kind']=='square' and device_deform and
                       (right-left+1)>target_width)
        if own_marks:
            minmx,maxmx=min(x for x,y in own_marks),max(x for x,y in own_marks)
            axis_fit=(d['kind']=='square' and left==minmx and right==maxmx and
                      not (pleft==minmx and pright==maxmx))
        else:
            axis_fit=False
        # First exact alignment of the reshaped rectangle's horizontal span is
        # another constructive waiver (#330).  A plus stroke endpoint likewise
        # receives a guide waiver when it first reaches the outermost framed-
        # marker row (#355), even before its orthogonal coordinate is aligned.
        ally=[my for mx,my,q in marks]
        repeated_x=[x for x,y in own_marks if sum(xx==x for xx,yy in own_marks)>1]
        guide_entry=(d['kind']=='plus' and bool(ally) and
                     ((bottom==max(ally) and pbottom<bottom) or
                      (bool(repeated_x) and top==repeated_x[0] and ptop>top)))
        margin_entry=(device_credit or axis_fit or guide_entry or
                      (clipped and not prev_clipped) or
                      (left==3 and pleft>3) or
                      (right==w-4 and pright<w-4))
        if st['meter'][c]>=2 and not margin_entry:
            ff=np.where(footer==15)[0]
            if len(ff): footer[int(ff[-1])]=1
            st['meter'][c]=0
        elif st['meter'][c]<2:
            st['meter'][c]+=1
    out=np.array(ENTRY_GRID,dtype=int).copy()
    for i,d in ds.items():
        for px,py in _l5_cells(d,d['center'],h,w):
            if int(out[py,px])==d['color']: out[py,px]=bg
        ex,ey=d['center']
        if int(out[ey,ex])==0: out[ey,ex]=bg
    # Solid plus below the hollow square.
    for i in sorted(ds,key=lambda z:0 if ds[z]['kind']=='plus' else 1):
        cells=(_l5_rect_cells(st['bbox'][i],h,w) if ds[i]['kind']=='square'
               else _l5_plus_cells(st['plines'][i],h,w))
        for px,py in cells:
            out[py,px]=ds[i]['color']
    ac=st['active']; ax,ay=st['centers'][ac]
    # The hollow rectangle is the upper L5 layer.  It can hide even the
    # active plus's selection hole when the anchor crosses its perimeter
    # (#369); the selected rectangle itself remains on top.
    hidden=(ds[ac]['kind']=='plus' and any(
        ds[j]['kind']=='square' and (ax,ay) in _l5_rect_cells(st['bbox'][j],h,w)
        for j in ds))
    if not hidden: out[ay,ax]=0
    out[-1]=footer
    # Pairwise visits do not finish L5 (#324): after reshaping, both parked
    # shapes must simultaneously cover every framed marker of their own hue.
    # This is the same simultaneous exact-cover objective as earlier levels.
    done=True
    for i,d in ds.items():
        cells=(_l5_rect_cells(st['bbox'][i],h,w) if d['kind']=='square'
               else _l5_plus_cells(st['plines'][i],h,w))
        if any(q==d['color'] and (mx,my) not in cells for mx,my,q in marks):
            done=False
    return out.tolist(),{'level_up':done,'dead':False,'win':False},st


def _l6_setup():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg(); ds={}
    # L6 introduces three overlapping flexible figures in hues a,c,7.  Their
    # full strokes/outlines are reconstructed from geometric runs so cells
    # hidden at entry by an upper figure reappear when it moves.
    zs=np.argwhere(e==0); cy,cx=(map(int,zs[0]) if len(zs) else (48,12))
    qa=10
    xs=[x for x in range(w) if int(e[cy,x]) in (qa,0)]
    ys=[y for y in range(h-1) if int(e[y,cx]) in (qa,0)]
    # retain the contiguous runs containing the selection anchor
    def run(vals,v):
        s={v}
        k=v-1
        while k in vals: s.add(k); k-=1
        k=v+1
        while k in vals: s.add(k); k+=1
        return s
    xr=run(set(xs),cx); yr=run(set(ys),cy)
    ac={(x,cy) for x in xr}|{(cx,y) for y in yr}
    ds[0]={'kind':'plus','color':qa,'anchor':[cx,cy],'cells':ac}
    qc=12; pts=np.argwhere(e==qc)
    if len(pts):
        y0,x0=map(int,pts.min(axis=0)); y1,x1=map(int,pts.max(axis=0))
        cc={(x,y0) for x in range(x0,x1+1)}|{(x,y1) for x in range(x0,x1+1)}
        cc|={(x0,y) for y in range(y0,y1+1)}|{(x1,y) for y in range(y0,y1+1)}
        ds[1]={'kind':'rect','color':qc,'anchor':[(x0+x1)//2,(y0+y1)//2],'cells':cc}
    q7=7; pts=np.argwhere(e==q7)
    if len(pts):
        # longest row and column identify the two strokes even when they are
        # independently offset or clipped.
        rows={int(y):set(map(int,np.where(e[y]==q7)[0])) for y in range(h-1)}
        cols={int(x):set(map(int,np.where(e[:,x]==q7)[0])) for x in range(w)}
        hy=max(rows,key=lambda y:len(rows[y])); vx=max(cols,key=lambda x:len(cols[x]))
        # Fill across holes made by upper-layer figures (the a vertical hides
        # x=12 on the long 7 row at entry).
        hx=set(range(min(rows[hy]),max(rows[hy])+1))
        vy0,vy1=min(cols[vx]),max(cols[vx])
        # A stroke ending immediately above the footer is clipped by that fixed
        # row rather than intrinsically shorter.  L6's 7 vertical is the same
        # 19-cell length as its marker-axis span: its hidden y63 endpoint first
        # appears at y60 after an upward translation (#445).
        if vy1==h-2: vy1=h-1
        vy=set(range(vy0,vy1+1))
        sc={(x,hy) for x in hx}|{(vx,y) for y in vy}
        ds[2]={'kind':'cross','color':q7,'anchor':[vx,hy],'cells':sc}
    return ds,bg


def _l6_shifted(d,off,h=64,w=64):
    dx,dy=off
    return {(x+dx,y+dy) for x,y in d['cells'] if 0<=x+dx<w and 0<=y+dy<h-1}


def _l6_markers():
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; out=[]
    for y in range(1,h-2):
        for x in range(1,w-1):
            q=int(e[y,x])
            if q not in (0,4,5,15) and all(
                int(e[y+dy,x+dx])==4 for dy in (-1,0,1)
                for dx in (-1,0,1) if dx or dy):
                out.append((x,y,q))
    return out


def _l6_palettes():
    """Top-row 3x3 hue interiors enclosed by a 5x5 color-2 frame."""
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; out=[]
    for y in range(h-4):
        for x in range(w-4):
            border=(list(e[y,x:x+5])+list(e[y+4,x:x+5])+
                    list(e[y+1:y+4,x])+list(e[y+1:y+4,x+4]))
            if not border or any(int(v)!=2 for v in border): continue
            inn=e[y+1:y+4,x+1:x+4]
            vals=set(int(v) for v in inn.flat)
            if len(vals)==1:
                q=list(vals)[0]
                out.append((q,{(xx,yy) for yy in range(y,y+5)
                                      for xx in range(x,x+5)},x))
    return out


def _predict_l6(state,grid,action):
    cur=np.array(grid,dtype=int); ds,bg=_l6_setup(); h,w=cur.shape
    st={'mode':'l6','offsets':{int(i):list(v) for i,v in state['offsets'].items()},
        'active':int(state['active']),
        'meter':{int(i):int(v) for i,v in state.get('meter',{}).items()},
        'palette_tail':{int(i):int(v) for i,v in state.get('palette_tail',{}).items()},
        'palette_dir':{int(i):int(v) for i,v in state.get('palette_dir',{}).items()},
        'axis_grace':{int(i):int(v) for i,v in state.get('axis_grace',{}).items()},
        'marker_grace':{int(i):bool(v) for i,v in state.get('marker_grace',{}).items()},
        'colors':{int(i):int(v) for i,v in state.get('colors',{}).items()},
        'bbox':{int(i):list(v) for i,v in state.get('bbox',{}).items()},
        'crosslines':{int(i):list(v) for i,v in state.get('crosslines',{}).items()}}
    for i,d in ds.items():
        st['offsets'].setdefault(i,[0,0]); st['meter'].setdefault(i,0)
        st['palette_tail'].setdefault(i,0); st['palette_dir'].setdefault(i,0)
        st['axis_grace'].setdefault(i,0); st['marker_grace'].setdefault(i,False)
        st['colors'].setdefault(i,d['color'])
        if d['kind']=='rect' and i not in st['bbox']:
            xs=[x for x,y in d['cells']]; ys=[y for x,y in d['cells']]
            st['bbox'][i]=[min(xs),max(xs),min(ys),max(ys)]
        if d['kind'] in ('cross','plus') and i not in st['crosslines']:
            ax,ay=d['anchor']
            hxs=[x for x,y in d['cells'] if y==ay]
            vys=[y for x,y in d['cells'] if x==ax]
            ox,oy=st['offsets'][i]
            st['crosslines'][i]=[min(hxs)+ox,max(hxs)+ox,ay+oy,
                                 ax+ox,min(vys)+oy,max(vys)+oy]
    c=st['active']; moved=False; device_deform=False; near_device=False; axis_fit=False
    axis_exact=False; figure_axis_fit=False; figure_contact=False; figure_exit_fit=False
    palette_credit=False; marker_contact=False; switch_charge=False
    painted_target=False
    prev_active_cells=(_l5_rect_cells(st['bbox'][c],h,w)
                       if ds[c]['kind']=='rect' else
                       _l5_plus_cells(st['crosslines'][c],h,w)
                       if ds[c]['kind'] in ('cross','plus') else
                       _l6_shifted(ds[c],st['offsets'][c],h,w))
    delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    if delta is not None and c in ds:
        dx,dy=delta; ox,oy=st['offsets'][c]
        if ds[c]['kind']=='rect':
            x0,x1,y0,y1=st['bbox'][c]
            cand=[x0+dx,x1+dx,y0+dy,y1+dy]
            device={(int(x),int(y)) for y,x in np.argwhere(np.array(ENTRY_GRID)==1)}
            hit=bool(_l5_rect_cells(cand,h,w)&device)
            if hit and action==1:
                device_deform=True
                # Upward pressure pins the near/top edge, retracts the bottom
                # by three and alternately grows left then right, conserving
                # the rectangle's 48-cell perimeter (#404).
                if (x1-x0+1)%2: cand=[x0-3,x1,y0,y1-3]
                else: cand=[x0,x1+3,y0,y1-3]
            if cand[0]<=cand[1] and cand[2]<=cand[3]:
                newcells=_l5_rect_cells(cand,h,w)
                def adjacent(cs):
                    return any((x+ddx,y+ddy) in device for x,y in cs
                               for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1)))
                # The post-reshape upward approach is credited only while the
                # rectangle still projects below the device: once its bottom
                # passes the device's lower edge, continued flush sliding is due.
                max_device_y=max(y for x,y in device)
                near_device=(action==1 and not hit and adjacent(newcells)
                             and cand[3]>max_device_y)
                # A reshaped rectangle earns a one-move guide waiver when one
                # moved axis first exactly spans the marker family whose overall
                # dimensions match its conserved-perimeter aspect.
                ent=np.array(ENTRY_GRID,dtype=int)
                groups={}
                for my in range(1,h-2):
                    for mx in range(1,w-1):
                        q=int(ent[my,mx])
                        if q not in (0,4,5,15) and all(
                            int(ent[my+ddy,mx+ddx])==4
                            for ddy in (-1,0,1) for ddx in (-1,0,1)
                            if ddx or ddy):
                            groups.setdefault(q,[]).append((mx,my))
                rw,rh=cand[1]-cand[0]+1,cand[3]-cand[2]+1
                for pts in groups.values():
                    tx0,tx1=min(x for x,y in pts),max(x for x,y in pts)
                    ty0,ty1=min(y for x,y in pts),max(y for x,y in pts)
                    if tx1-tx0+1==rw and ty1-ty0+1==rh:
                        axis_fit = axis_fit or (
                            (dx and cand[0]==tx0 and cand[1]==tx1 and
                             not (x0==tx0 and x1==tx1)) or
                            (dy and cand[2]==ty0 and cand[3]==ty1 and
                             not (y0==ty0 and y1==ty1)))
                st['bbox'][c]=cand
                nc=[(cand[0]+cand[1]+1)//2,(cand[2]+cand[3]+1)//2]
                st['offsets'][c]=[nc[0]-ds[c]['anchor'][0],nc[1]-ds[c]['anchor'][1]]
                moved=True
        else:
            ax,ay=ds[c]['anchor']; nx,ny=ax+ox+dx,ay+oy+dy
            if 0<=nx<w and 0<=ny<h-1:
                st['offsets'][c]=[ox+dx,oy+dy]; moved=True
                if ds[c]['kind'] in ('cross','plus'):
                    oldline=list(st['crosslines'][c])
                    hx0,hx1,hy,vx,vy0,vy1=oldline
                    candline=[hx0+dx,hx1+dx,hy+dy,
                              vx+dx,vy0+dy,vy1+dy]
                    device={(int(x),int(y)) for y,x in
                            np.argwhere(np.array(ENTRY_GRID)==1)}
                    hpart={(x,candline[2]) for x in
                           range(candline[0],candline[1]+1)}
                    vpart={(candline[3],y) for y in
                           range(candline[4],candline[5]+1)}
                    hhit=bool(hpart & device); vhit=bool(vpart & device)
                    if hhit and not vhit:
                        # The perpendicular H hits on this downward push: pin H
                        # while V and the logical selection anchor translate.
                        candline=[hx0,hx1,hy,candline[3],
                                  candline[4],candline[5]]
                        device_deform=True
                    elif vhit and not hhit:
                        # Symmetric side push pins V while H translates.
                        candline=[candline[0],candline[1],candline[2],
                                  vx,vy0,vy1]
                        device_deform=True
                    st['crosslines'][c]=candline
                # Coinciding parallel axes of two flexible crosses is a
                # constructive guide event.  When the rising 7 horizontal first
                # exactly met the parked a horizontal at y48, its due move was
                # waived (#446).  The symmetric vertical-axis event occurs on a
                # horizontal translation.
                if ds[c]['kind'] in ('cross','plus'):
                    for j,dj in ds.items():
                        if j==c or dj['kind'] not in ('cross','plus'): continue
                        jox,joy=st['offsets'][j]; jax,jay=dj['anchor']
                        jx,jy=jax+jox,jay+joy
                        figure_axis_fit = figure_axis_fit or (
                            (dy and ny==jy and ay+oy!=jy) or
                            (dx and nx==jx and ax+ox!=jx))
                        # Crossing the far endpoint of a parked perpendicular
                        # stroke is a final constructive guide.  Moving right
                        # through the parked 8 horizontal reached its right end
                        # at x36 and waived #521; entering from the opposite end
                        # while moving up (#504) is not the far endpoint.
                        ol=st['crosslines'][j]; nl=st['crosslines'][c]
                        figure_exit_fit = figure_exit_fit or (
                            (dx>0 and oldline[3]<ol[1] and nl[3]==ol[1] and
                             nl[4]<=ol[2]<=nl[5]) or
                            (dx<0 and oldline[3]>ol[0] and nl[3]==ol[0] and
                             nl[4]<=ol[2]<=nl[5]) or
                            (dy>0 and oldline[2]<ol[5] and nl[2]==ol[5] and
                             nl[0]<=ol[3]<=nl[1]) or
                            (dy<0 and oldline[2]>ol[4] and nl[2]==ol[4] and
                             nl[0]<=ol[3]<=nl[1]))
                if ds[c]['kind']=='cross':
                    hxs=[x for x,y in ds[c]['cells'] if y==ay]
                    vys=[y for x,y in ds[c]['cells'] if x==ax]
                    hr=max(ax-min(hxs),max(hxs)-ax)
                    vr=max(ay-min(vys),max(vys)-ay)
                    groups={}
                    for mx,my,q in _l6_markers():
                        groups.setdefault(q,[]).append((mx,my))
                    if groups:
                        # The 7 target is the widest marker family.  Its fixed
                        # stroke is three cells longer than the marker span, so
                        # directional guide alignment occurs when the leading
                        # endpoint first reaches the corresponding outer marker.
                        pts=max(groups.values(),key=lambda ps:
                                max(x for x,y in ps)-min(x for x,y in ps))
                        tx0,tx1=min(x for x,y in pts),max(x for x,y in pts)
                        ty0,ty1=min(y for x,y in pts),max(y for x,y in pts)
                        # Directional stroke-end guidance.  Once the cross is
                        # already painted its target hue, merely reaching the
                        # near horizontal marker (x3) is final placement rather
                        # than a construction guide (#480), so that contact does
                        # not waive a due move.
                        tq,pts=max(groups.items(),key=lambda kv:
                                max(x for x,y in kv[1])-min(x for x,y in kv[1]))
                        tx0,tx1=min(x for x,y in pts),max(x for x,y in pts)
                        ty0,ty1=min(y for x,y in pts),max(y for x,y in pts)
                        painted_target=(st['colors'][c]==tq)
                        guide_event=(
                            (dx<0 and nx-hr==tx0 and ax+ox-hr!=tx0 and
                             not painted_target) or
                            (dx>0 and nx+hr==tx1 and ax+ox+hr!=tx1) or
                            (dy<0 and ny-vr==ty0 and ay+oy-vr!=ty0) or
                            (dy>0 and ny+vr==ty1 and ay+oy+vr!=ty1))
                        axis_fit = axis_fit or guide_event
                        if guide_event:
                            ln=st['crosslines'][c]
                            axis_exact = axis_exact or (
                                (bool(dx) and ln[0]==tx0 and ln[1]==tx1) or
                                (bool(dy) and ln[4]==ty0 and ln[5]==ty1))
                if ds[c]['kind']=='plus':
                    # The three-marker plus family fixes relative stroke offsets:
                    # its paired horizontal markers give H's left guide and row,
                    # while the singleton above gives V's x and top guide.
                    groups={}
                    for mx,my,q in _l6_markers():
                        groups.setdefault(q,[]).append((mx,my))
                    p3=[(q,ps) for q,ps in groups.items() if len(ps)==3]
                    if p3:
                        ptq,ps=p3[0]
                        painted_target=(st['colors'][c]==ptq)
                        rows={}
                        for px,py in ps: rows.setdefault(py,[]).append(px)
                        hy,hpair=max(rows.items(),key=lambda kv:len(kv[1]))
                        single=[(px,py) for px,py in ps if py!=hy][0]
                        hrad=(len([1 for px,py in ds[c]['cells'] if py==ay])-1)//2
                        vrad=(len([1 for px,py in ds[c]['cells'] if px==ax])-1)//2
                        target_rx=min(hpair)+hrad-single[0]
                        target_ry=hy-(single[1]+vrad)
                        ln=st['crosslines'][c]
                        old_rx=(oldline[0]+oldline[1])//2-oldline[3]
                        new_rx=(ln[0]+ln[1])//2-ln[3]
                        old_ry=oldline[2]-(oldline[4]+oldline[5])//2
                        new_ry=ln[2]-(ln[4]+ln[5])//2
                        plus_fit=((bool(dx) and new_rx==target_rx and old_rx!=target_rx) or
                                  (bool(dy) and new_ry==target_ry and old_ry!=target_ry))
                        axis_fit=axis_fit or plus_fit
                        axis_exact=axis_exact or plus_fit
    if moved:
        moved_cells=(_l5_rect_cells(st['bbox'][c],h,w)
                     if ds[c]['kind']=='rect' else
                     _l5_plus_cells(st['crosslines'][c],h,w)
                     if ds[c]['kind'] in ('cross','plus') else
                     _l6_shifted(ds[c],st['offsets'][c],h,w))
        # First contact between two flexible figures is also constructive.  The
        # rising plus's V endpoint first met the parked 8 horizontal at y15 and
        # its due move was waived (#502).  Markers already occupied by another
        # parked figure are no longer available as guides (#504).
        occupied_flexible=set()
        for j,dj in ds.items():
            if j==c: continue
            other=(_l5_rect_cells(st['bbox'][j],h,w) if dj['kind']=='rect'
                   else _l5_plus_cells(st['crosslines'][j],h,w)
                   if dj['kind'] in ('cross','plus')
                   else _l6_shifted(dj,st['offsets'][j],h,w))
            if dj['kind'] in ('cross','plus'):
                occupied_flexible |= other
                if (moved_cells & other) and not (prev_active_cells & other):
                    figure_contact=True
        available=[(mx,my,q) for mx,my,q in _l6_markers()
                   if (mx,my) not in occupied_flexible]
        marker_contact=any((mx,my) in moved_cells for mx,my,q in available)
        marker_entries=[(mx,my,q) for mx,my,q in available
                        if (mx,my) in moved_cells and (mx,my) not in prev_active_cells]
        marker_entry=bool(marker_entries)
        marker_entry_color=any(q==st['colors'][c] for mx,my,q in marker_entries)
        palettes=_l6_palettes()
        palette_hits=[(px,q) for q,zone,px in palettes if moved_cells & zone]
        palette_entries=[(px,q) for q,zone,px in palettes
                         if moved_cells & zone and not (prev_active_cells & zone)]
        # Entering a palette is constructive and banks departure grace.  Merely
        # sliding while still touching the same panel is not a new entry and can
        # charge normally (#513).
        if palette_entries:
            # Hollow rectangles retain a two-step departure ray, while a plus
            # receives only its first step away from the panel (#507-508).
            st['palette_tail'][c]=(1 if ds[c]['kind']=='plus' else 2)
            # A plus's one-step grace continues straight through the panel;
            # unlike a hollow rectangle it cannot turn on departure (#518).
            st['palette_dir'][c]=(action if ds[c]['kind']=='plus' else 0)
            palette_credit=True
        elif palette_hits and ds[c]['kind']=='plus':
            # Sliding along a panel is not constructive, but it establishes the
            # plus's exit ray.  Thus the last in-panel right at #506 licensed
            # #507, whereas entering b left then immediately turning down at
            # #518 did not.
            st['palette_dir'][c]=action
        elif not palette_hits and st['palette_tail'][c]>0:
            # The grace begins on the actual departure from the panel and then
            # follows a straight ray.  Turning after one step ends it (#419).
            if st['palette_dir'][c] in (0,action):
                palette_credit=True; st['palette_tail'][c]-=1
                st['palette_dir'][c]=action
            else:
                st['palette_tail'][c]=0; st['palette_dir'][c]=0
        if palette_hits:
            # Multiple simultaneous panels repaint in scan/rightmost order;
            # the wide c outline touched 9 and b together and ended b (#417).
            st['colors'][c]=max(palette_hits)[1]
    if action==5 and c in ds:
        # Switching checks (but does not advance/reset) the outgoing figure's
        # meter.  Parking the due, exactly placed c rectangle charged (#438).
        switch_charge=st['meter'][c]>=2
        ids=sorted(ds); st['active']=ids[(ids.index(c)+1)%len(ids)]
        # L6 re-selection restores the incoming figure's intrinsic phase:
        # returning to c made its next move due again (#401).
        st['meter'][st['active']]=(2 if st['active']==1 else 0)
    footer=cur[-1].copy()
    if switch_charge:
        ff=np.where(footer==15)[0]
        if len(ff): footer[int(ff[-1])]=1
    if moved:
        # Exact alignment or first endpoint entry banks two due-waiver tokens.
        # If the event itself is due it consumes the first immediately, leaving
        # one; the rising 7's q8 endpoint contact and its next departure were
        # both free (#450-451).
        endpoint_entry=(marker_entry and ds[c]['kind'] in ('cross','plus') and
                        not (ds[c]['kind']=='cross' and bool(dx) and painted_target) and
                        not (ds[c]['kind']=='plus' and painted_target and
                             not marker_entry_color))
        if endpoint_entry:
            st['axis_grace'][c]=2
        elif axis_fit:
            # A directional stroke-end guide contributes one due waiver; the
            # rectangle's exact-axis fit contributes two.  Thus 7's right end
            # reaching x36 waived that move but not the following x21 move
            # (#456-457), while its earlier x3 event carried through one due.
            st['axis_grace'][c]=(1 if ds[c]['kind'] in ('cross','plus')
                                  and not axis_exact else 2)
        axis_credit=st['axis_grace'][c]>0
        marker_credit=bool(st['marker_grace'][c])
        # A constructive rectangle reshape defers a due charge while it is
        # still approaching the 19-cell target width (#404); exact width will
        # no longer receive this waiver, as in L5.
        rect_credit=(ds[c]['kind']=='rect' and
                     ((device_deform and
                       (st['bbox'][c][1]-st['bbox'][c][0]+1)<19) or
                      near_device or axis_credit or palette_credit))
        # A device deformation is constructive when it brings the plus's two
        # stroke axes back into coincidence.  The first H-pinned rise reunited
        # H y36 with V's midpoint and was waived (#493); the next rise separated
        # them again and charged (#494).
        if ds[c]['kind']=='plus':
            pl=st['crosslines'][c]
            plus_deform_credit=(device_deform and
                ((dy and pl[2]==(pl[4]+pl[5])//2) or
                 (dx and (pl[0]+pl[1])//2==pl[3])))
        else:
            plus_deform_credit=False
        noncross_palette_credit=(palette_credit and ds[c]['kind']!='cross')
        move_credit=(rect_credit or marker_credit or axis_credit or noncross_palette_credit or
                     figure_axis_fit or figure_exit_fit or figure_contact or plus_deform_credit)
        if st['meter'][c]>=2:
            if not move_credit:
                ff=np.where(footer==15)[0]
                if len(ff): footer[int(ff[-1])]=1
                st['meter'][c]=0
            else:
                if axis_credit: st['axis_grace'][c]-=1
                if marker_credit: st['marker_grace'][c]=False
        else:
            st['meter'][c]+=1
            if marker_contact and not endpoint_entry:
                st['marker_grace'][c]=True
    out=np.array(ENTRY_GRID,dtype=int).copy()
    # Remove entry figures and selection hole, then redraw bottom-to-top:
    # rectangle c, cross 7, plus a.
    for i,d in ds.items():
        for x,y in d['cells']:
            if int(out[y,x]) in (d['color'],0): out[y,x]=bg
    for yy,xx in np.argwhere(out==0): out[yy,xx]=bg
    def cells_now(i):
        return (_l5_rect_cells(st['bbox'][i],h,w) if ds[i]['kind']=='rect'
                else _l5_plus_cells(st['crosslines'][i],h,w)
                if ds[i]['kind'] in ('cross','plus')
                else _l6_shifted(ds[i],st['offsets'][i],h,w))
    for i in (1,2,0):
        if i not in ds: continue
        for px,py in cells_now(i): out[py,px]=st['colors'][i]
    ac=st['active']; ox,oy=st['offsets'][ac]
    if ds[ac]['kind']=='rect':
        x0,x1,y0,y1=st['bbox'][ac]; ax,ay=(x0+x1+1)//2,(y0+y1+1)//2
    elif ds[ac]['kind'] in ('cross','plus'):
        # A flexible cross's selector combines the two independent axis
        # positions: H's horizontal midpoint and V's vertical midpoint.  Thus
        # it followed neither whole stroke during the plus deformations
        # (#489,#497), and the same rule explains the parked 7 selector.
        ln=st['crosslines'][ac]
        ax,ay=(ln[0]+ln[1])//2,(ln[4]+ln[5])//2
    else:
        ax,ay=ds[ac]['anchor']; ax+=ox; ay+=oy
    rank={1:0,2:1,0:2}
    hidden=any(rank.get(j,0)>rank.get(ac,0) and (ax,ay) in cells_now(j)
               for j in ds)
    if not hidden: out[ay,ax]=0
    out[-1]=footer
    # L6 completes when each differently shaped figure, repainted to its own
    # marker hue, simultaneously covers that marker family.
    mg={}
    for mx,my,q in _l6_markers(): mg.setdefault(q,set()).add((mx,my))
    solved=True
    for i,d in ds.items():
        if d['kind']=='rect': fam=[(q,ps) for q,ps in mg.items() if len(ps)==2]
        elif d['kind']=='plus': fam=[(q,ps) for q,ps in mg.items() if len(ps)==3]
        else: fam=[max(mg.items(),key=lambda kv:max(x for x,y in kv[1])-min(x for x,y in kv[1]))]
        if not fam:
            solved=False; continue
        q,pts=fam[0]
        if st['colors'][i]!=q or not pts.issubset(cells_now(i)):
            solved=False
    return out.tolist(),{'level_up':bool(solved),'dead':False,'win':False},st


def _l7_setup():
    """Two overlapping 13x13 hollow outlines on the final board."""
    e=np.array(ENTRY_GRID,dtype=int); h,w=e.shape; bg=_bg(); ds={}
    # Ignore the many 3x3 palette swatches and take the large lower-board
    # outline of each entry hue.  Reconstruct the complete perimeter through
    # cells hidden by the upper outline and by the selector.
    for i,q in enumerate((10,12)):
        pts=np.argwhere((e==q) & (np.indices(e.shape)[0]>=33))
        if not len(pts): continue
        y0,x0=map(int,pts.min(axis=0)); y1,x1=map(int,pts.max(axis=0))
        cells=({(x,y0) for x in range(x0,x1+1)} |
               {(x,y1) for x in range(x0,x1+1)} |
               {(x0,y) for y in range(y0,y1+1)} |
               {(x1,y) for y in range(y0,y1+1)})
        ds[i]={'kind':'rect','color':q,'bbox':[x0,x1,y0,y1],
               'center':[(x0+x1)//2,(y0+y1)//2],'cells':cells}
    return ds,bg


def _l7_rect_cells(box,h=64,w=64):
    x0,x1,y0,y1=box
    return ({(x,y0) for x in range(x0,x1+1) if 0<=x<w and 0<=y0<h-1} |
            {(x,y1) for x in range(x0,x1+1) if 0<=x<w and 0<=y1<h-1} |
            {(x0,y) for y in range(y0,y1+1) if 0<=x0<w and 0<=y<h-1} |
            {(x1,y) for y in range(y0,y1+1) if 0<=x1<w and 0<=y<h-1})


def _predict_l7(state,grid,action):
    cur=np.array(grid,dtype=int); ds,bg=_l7_setup(); h,w=cur.shape
    st={'mode':'l7','bbox':{int(i):list(v) for i,v in state['bbox'].items()},
        'active':int(state['active']),
        'colors':{int(i):int(v) for i,v in state.get('colors',{}).items()},
        'meter':{int(i):int(v) for i,v in state.get('meter',{}).items()},
        'axis_grace':{int(i):int(v) for i,v in state.get('axis_grace',{}).items()},
        'guide_grace':{int(i):int(v) for i,v in state.get('guide_grace',{}).items()}}
    c=st['active']
    for i in ds:
        st['axis_grace'].setdefault(i,0)
        st['guide_grace'].setdefault(i,0)
    delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    moved=False; device_credit=False; palette_credit=False; object_credit=False
    axis_new=False; guide_new=False
    if delta is not None and c in ds:
        dx,dy=delta; x0,x1,y0,y1=st['bbox'][c]
        oldbox=[x0,x1,y0,y1]; oldcells=_l7_rect_cells(oldbox,h,w)
        cand=[x0+dx,x1+dx,y0+dy,y1+dy]
        device={(int(x),int(y)) for y,x in
                np.argwhere(np.array(ENTRY_GRID)==1)}
        hit=bool(_l7_rect_cells(cand,h,w) & device)
        if hit:
            # Direct pressure pins the device-facing edge, retracts the far
            # parallel edge by three, and alternately grows the perpendicular
            # sides.  Perimeter is conserved: 13x13 -> 10x16 at #540.
            # A side cannot be compressed below four cells (#580).
            if action in (3,4) and (x1-x0+1)<=4:
                cand=None
            elif action in (1,2) and (y1-y0+1)<=4:
                cand=None
            elif action==3:
                cand=([x0,x1-3,y0-3,y1] if (y1-y0+1)%2
                      else [x0,x1-3,y0,y1+3])
            elif action==4:
                cand=([x0+3,x1,y0-3,y1] if (y1-y0+1)%2
                      else [x0+3,x1,y0,y1+3])
            elif action==1:
                cand=([x0-3,x1,y0,y1-3] if (x1-x0+1)%2
                      else [x0,x1+3,y0,y1-3])
            elif action==2:
                cand=([x0-3,x1,y0+3,y1] if (x1-x0+1)%2
                      else [x0,x1+3,y0+3,y1])
        if cand is not None and cand[0]>=0 and cand[1]<w and cand[2]>=0 and cand[3]<h-1:
            st['bbox'][c]=cand; moved=True
            cc=_l7_rect_cells(cand,h,w)
            device_near=(hit or bool(cc & device) or any(
                (x+ddx,y+ddy) in device for x,y in cc
                for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1))))
            # A final one-cell/corner contact between the two conserved
            # outlines is a constructive endpoint alignment (#550).
            others=set()
            for j in ds:
                if j!=c:
                    others |= _l7_rect_cells(st['bbox'][j],h,w)
            object_credit=(len(cc & others)==1)
            # The selector is itself a guide feature.  First orthogonal
            # adjacency between the moving selector and the parked outline is
            # constructive even while their perimeters already overlap (#638).
            osel=((oldbox[0]+oldbox[1]+1)//2,
                  (oldbox[2]+oldbox[3]+1)//2)
            nsel=((cand[0]+cand[1]+1)//2,
                  (cand[2]+cand[3]+1)//2)
            def selector_near(p):
                return any((p[0]+ux,p[1]+uy) in others
                           for ux,uy in ((1,0),(-1,0),(0,1),(0,-1)))
            if selector_near(nsel) and not selector_near(osel):
                object_credit=True
            def selector_inside(p):
                return any(ob[0]<p[0]<ob[1] and ob[2]<p[1]<ob[3]
                           for j,ob in st['bbox'].items() if j!=c)
            # Crossing the parked perimeter into its hollow interior is the
            # next constructive selector phase after adjacency (#639).
            if selector_inside(nsel) and not selector_inside(osel):
                object_credit=True
            # Projected endpoint guidance also fires when the active selector
            # first lines up with an edge of the other conserved rectangle,
            # even before their outlines meet (#575; also latent at #539).
            def projected_rel(box,ob):
                ax=[box[0],(box[0]+box[1]+1)//2,box[1]]
                ay=[box[2],(box[2]+box[3]+1)//2,box[3]]
                bx=[ob[0],(ob[0]+ob[1]+1)//2,ob[1]]
                by=[ob[2],(ob[2]+ob[3]+1)//2,ob[3]]
                return ({('x',i,j) for i,u in enumerate(ax)
                                     for j,v in enumerate(bx) if u==v} |
                        {('y',i,j) for i,u in enumerate(ay)
                                     for j,v in enumerate(by) if u==v})
            palette_touch=any(bool(cc & zone)
                              for q,zone,px in _l6_palettes())
            for j in ds:
                if j==c: continue
                ob=st['bbox'][j]
                nr=projected_rel(cand,ob); orels=projected_rel(oldbox,ob)
                if ((nr-orels) and not (cc & others) and
                    not device_near and not palette_touch):
                    object_credit=True
                    # A newly reached coordinate banks one following waiver;
                    # exchanging endpoint/centre identity at a coordinate
                    # still credits this move but does not refresh the bank
                    # (#577 versus #613,#615).
                    def projection_coords(box,other):
                        xs={box[0],(box[0]+box[1]+1)//2,box[1]}
                        ys={box[2],(box[2]+box[3]+1)//2,box[3]}
                        ox={other[0],(other[0]+other[1]+1)//2,other[1]}
                        oy={other[2],(other[2]+other[3]+1)//2,other[3]}
                        return ({('x',v) for v in xs & ox} |
                                {('y',v) for v in ys & oy})
                    if (projection_coords(cand,ob)-
                        projection_coords(oldbox,ob)):
                        st['guide_grace'][c]+=1
                        guide_new=True
            groups={}
            for mx,my,q in _l6_markers():
                groups.setdefault(q,[]).append((mx,my))
            # A three-cell move is guided at the final safe staging position
            # whose following translation would first enter any marker centre,
            # including another outline's family (#650).
            marker_pts={p for ps in groups.values() for p in ps}
            marker_q={p:q for q,ps in groups.items() for p in ps}
            owner_q=(6 if ds[c]['color']==10 else 11)
            future=[cand[0]+dx,cand[1]+dx,cand[2]+dy,cand[3]+dy]
            if ((_l7_rect_cells(future,h,w) & marker_pts) -
                (cc & marker_pts)):
                object_credit=True
            # The following direct first entry into those marker centres is a
            # second constructive phase, even for a foreign family (#651).
            entered_markers=(cc-oldcells) & marker_pts
            own_marker_completion=(st['colors'][c]==owner_q and
                any(marker_q[p]==owner_q for p in entered_markers))
            # A painted outline's first direct entry into its own marker centre
            # is a completed placement milestone.  It overrides simultaneous
            # foreign-marker construction (#653).
            if entered_markers and not own_marker_completion:
                object_credit=True
            cw,ch=cand[1]-cand[0]+1,cand[3]-cand[2]+1
            # Each conserved outline has its own marker family: the
            # entry-a outline belongs to q6 (wide), while entry-c belongs to
            # qb (tall).  Passing through the other outline's aspect is only
            # an intermediate constructive deformation (#588).
            target_q=owner_q
            target_ps=groups.get(target_q,[])
            if target_ps:
                target_box=[min(x for x,y in target_ps),
                            max(x for x,y in target_ps),
                            min(y for x,y in target_ps),
                            max(y for x,y in target_ps)]
                # Even in a transport aspect, newly reaching a coordinate
                # used by one's own marker family is constructive (#600).
                # Merely exchanging which feature occupies an already-aligned
                # coordinate is not a new event (#566).
                def marker_rel(box,tb):
                    xs={box[0],(box[0]+box[1]+1)//2,box[1]}
                    ys={box[2],(box[2]+box[3]+1)//2,box[3]}
                    tx={tb[0],(tb[0]+tb[1]+1)//2,tb[1]}
                    ty={tb[2],(tb[2]+tb[3]+1)//2,tb[3]}
                    return ({('x',v) for v in xs & tx} |
                            {('y',v) for v in ys & ty})
                if (not own_marker_completion and
                    marker_rel(cand,target_box)-marker_rel(oldbox,target_box)):
                    object_credit=True
            matching=[ps for q,ps in groups.items() if q==target_q and
                      len(ps)>1 and
                      cw==max(x for x,y in ps)-min(x for x,y in ps)+1 and
                      ch==max(y for x,y in ps)-min(y for x,y in ps)+1]
            exact_aspect=bool(matching)
            any_exact_aspect=any(
                len(ps)>1 and
                cw==max(x for x,y in ps)-min(x for x,y in ps)+1 and
                ch==max(y for x,y in ps)-min(y for x,y in ps)+1
                for ps in groups.values())
            painted=(st['colors'][c]==target_q)
            # Before painting, completing one's own aspect is the milestone;
            # after painting, that same aspect is constructive final assembly,
            # while the other outline's aspect is the completed detour
            # (#541,#588,#622,#626).
            completion_aspect=((exact_aspect and not painted) or
                (painted and any_exact_aspect and not exact_aspect))
            axis_new=False
            for ps in matching:
                tx0=min(x for x,y in ps); tx1=max(x for x,y in ps)
                ty0=min(y for x,y in ps); ty1=max(y for x,y in ps)
                nf=(cand[0]==tx0 and cand[1]==tx1) or (cand[2]==ty0 and cand[3]==ty1)
                of=(oldbox[0]==tx0 and oldbox[1]==tx1) or (oldbox[2]==ty0 and oldbox[3]==ty1)
                if nf and not of: axis_new=True
            if axis_new: st['axis_grace'][c]=(1 if hit else 2)
            # Adjacency and intermediate deformation are constructive, but
            # completing an exact marker-family aspect normally spends the due
            # charge (#541: 10x16 -> target 7x19).  Expanding away from the
            # four-cell compression limit is itself constructive (#584).
            ow,oh=oldbox[1]-oldbox[0]+1,oldbox[3]-oldbox[2]+1
            # Likewise, arriving at the four-cell compression limit is a
            # completed endpoint and charges (#591); only departure from that
            # limit is constructive (#584).
            old_dd=min(abs(x-u)+abs(y-v) for x,y in oldcells
                       for u,v in device)
            new_dd=min(abs(x-u)+abs(y-v) for x,y in cc
                       for u,v in device)
            device_horizon=(new_dd<=4 and old_dd>4)
            def device_adj_count(cells):
                return sum(any((x+ux,y+uy) in device
                               for ux,uy in ((1,0),(-1,0),(0,1),(0,-1)))
                           for x,y in cells)
            old_adj=device_adj_count(oldcells)
            new_adj=device_adj_count(cc)
            device_credit=((device_near and
                           ((hit and min(cw,ch)>4 and
                             (not completion_aspect or min(ow,oh)<=4)) or
                            ((not hit) and
                             (not exact_aspect or
                              (painted and new_adj<old_adj) or
                              min(ow,oh)<=4)))) or
                           (device_horizon and not exact_aspect))
            phits=[]
            palettes=_l6_palettes()
            strip_union=set()
            for _q,_zone,_px in palettes:
                if min(y for x,y in _zone)>=28:
                    strip_union |= _zone
            # The palette strip is one continuous device for adjacency.  Sliding
            # parallel to it must not create a fresh approach merely because the
            # nearest framed swatch changes (#660).
            strip_old_near=any(
                (x+ddx,y+ddy) in strip_union for x,y in oldcells
                for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1)))
            for q,zone,px in palettes:
                ni=cc & zone; oi=oldcells & zone
                nh=bool(ni); oh=bool(oi)
                nn=any((x+ddx,y+ddy) in zone for x,y in cc
                       for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1)))
                on=any((x+ddx,y+ddy) in zone for x,y in oldcells
                       for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1)))
                # Approach, entry, and a changing overlap with the palette
                # frame are constructive.  Once a long side merely slides
                # while covering the identical frame cells, it charges
                # normally (#547), unlike the changed overlap at #546.
                strip_panel=(min(y for x,y in zone)>=28)
                adjacent_phase=(strip_panel or action!=4)
                fbox=[cand[0]+dx,cand[1]+dx,
                      cand[2]+dy,cand[3]+dy]
                fh=bool(_l7_rect_cells(fbox,h,w) & zone)
                if ((st['colors'][c]!=target_q and
                     ((nh and ni!=oi) or
                      (adjacent_phase and nn and not nh and not on and not oh and
                       (not strip_panel or not strip_old_near)) or
                      (adjacent_phase and nn and not nh and oh))) or
                    # With three-cell translations, the final safe staging
                    # position one move before palette entry is constructive
                    # even though it can leave a one/two-cell visual gap
                    # (#606).  Rightward approach remains excluded.
                    (adjacent_phase and not nh and fh)):
                    # The strip frame has symmetric adjacency phases
                    # (#544,#552).  Standalone panels also guide left/up/down
                    # departure (#559), but not rightward exit (#572).
                    palette_credit=True
                gain=len(ni)-len(oi)
                if action==4 and nh:
                    # Rightward traversal ranks the current overlap.  A tied
                    # panel containing a rectangle corner wins, otherwise the
                    # lower tied panel wins (#569-571).
                    corners=((cand[0],cand[2]),(cand[1],cand[2]),
                             (cand[0],cand[3]),(cand[1],cand[3]))
                    corner=any(p in zone for p in corners)
                    phits.append((px,len(ni),int(corner),
                                  min(y for x,y in zone),q))
                elif gain>0:
                    # Left/vertical traversal ranks newly gained frame cells,
                    # breaking equal gains upward (#556, #558, #563).
                    phits.append((px,gain,0,-min(y for x,y in zone),q))
            # The five-row palette strip is also a continuous transport
            # channel through its visible background gaps.  First entering a
            # gap is constructive without repainting (#634); continued travel
            # inside it is ordinary movement (#635).
            strip_zones=[zone for q,zone,px in _l6_palettes()
                         if min(y for x,y in zone)>=28]
            if strip_zones:
                sy0=min(y for zone in strip_zones for x,y in zone)
                sy1=max(y for zone in strip_zones for x,y in zone)
                band={(x,y) for x in range(w) for y in range(sy0,sy1+1)}
                ni=cc & band; oi=oldcells & band
                fbox=[cand[0]+dx,cand[1]+dx,cand[2]+dy,cand[3]+dy]
                fi=_l7_rect_cells(fbox,h,w) & band
                # The gap grants only its first channel entry; unlike a framed
                # palette it has no painted cells whose changing overlap can
                # keep construction active (#634 versus #635).
                if ni and not oi:
                    palette_credit=True
            if phits:
                st['colors'][c]=max(phits)[4]
    if action==5 and c in ds:
        ids=sorted(ds); st['active']=ids[(ids.index(c)+1)%len(ids)]
    out=np.array(ENTRY_GRID,dtype=int).copy()
    # Erase both entry outlines and the entry selector, then redraw bottom a
    # followed by top c so hidden perimeter cells are conserved.
    for i,d in ds.items():
        for x,y in d['cells']:
            if int(out[y,x]) in (d['color'],0): out[y,x]=bg
    for yy,xx in np.argwhere(out==0): out[yy,xx]=bg
    for i in sorted(ds):
        for x,y in _l7_rect_cells(st['bbox'][i],h,w):
            out[y,x]=st['colors'][i]
    ac=st['active']; b=st['bbox'][ac]
    ax,ay=(b[0]+b[1]+1)//2,(b[2]+b[3]+1)//2
    # c is above a.  After a's first rise its centre lands on c's top
    # perimeter, so the active selector is hidden rather than overwriting c.
    hidden=any(j>ac and (ax,ay) in _l7_rect_cells(st['bbox'][j],h,w)
               for j in ds)
    if not hidden: out[ay,ax]=0
    footer=cur[-1].copy()
    if moved:
        if st['meter'][c]>=2:
            axis_credit=False
            # Exact placement of either axis for the matching marker aspect
            # banks two subsequent due waivers.  They are spent on due moves
            # even when another constructive event also fires (#542-547);
            # the alignment move itself does not spend one (#563-565).
            if (not axis_new) and st['axis_grace'][c]>0:
                axis_credit=True
                st['axis_grace'][c]-=1
            guide_credit=False
            if (not guide_new) and st['guide_grace'][c]>0:
                guide_credit=True
                st['guide_grace'][c]-=1
            if not (device_credit or palette_credit or object_credit or
                    axis_credit or guide_credit):
                ff=np.where(footer==15)[0]
                if len(ff): footer[int(ff[-1])]=1
                st['meter'][c]=0
        else:
            st['meter'][c]+=1
    out[-1]=footer
    return out.tolist(),{'level_up':False,'dead':False,'win':False},st


def init_state(entry_grid):
    if CURRENT_LEVEL==7:
        ds,bg=_l7_setup()
        return {'mode':'l7','bbox':{i:list(d['bbox']) for i,d in ds.items()},
                'active':1,'colors':{i:d['color'] for i,d in ds.items()},
                'meter':{i:0 for i in ds},
                'axis_grace':{i:0 for i in ds},
                'guide_grace':{i:0 for i in ds}}
    if CURRENT_LEVEL==6:
        ds,bg=_l6_setup()
        return {'mode':'l6','offsets':{i:[0,0] for i in ds},'active':0,
                # L6 figures have staggered intrinsic phases; the hollow c
                # rectangle starts due and charges on its first move (#396).
                'meter':{i:(2 if i==1 else 0) for i in ds},
                'palette_tail':{i:0 for i in ds},
                'palette_dir':{i:0 for i in ds},
                'axis_grace':{i:0 for i in ds},
                'marker_grace':{i:False for i in ds},
                'colors':{i:d['color'] for i,d in ds.items()},
                'bbox':{i:[min(x for x,y in d['cells']),max(x for x,y in d['cells']),
                           min(y for x,y in d['cells']),max(y for x,y in d['cells'])]
                        for i,d in ds.items() if d['kind']=='rect'},
                'crosslines':{i:[min(x for x,y in d['cells'] if y==d['anchor'][1]),
                                   max(x for x,y in d['cells'] if y==d['anchor'][1]),
                                   d['anchor'][1],d['anchor'][0],
                                   min(y for x,y in d['cells'] if x==d['anchor'][0]),
                                   max(y for x,y in d['cells'] if x==d['anchor'][0])]
                              for i,d in ds.items() if d['kind'] in ('cross','plus')}}
    if CURRENT_LEVEL==5:
        ds,marks,bg=_l5_setup()
        return {'mode':'l5','centers':{i:list(d['center']) for i,d in ds.items()},
                'active':0,
                # The hollow square starts one phase ahead: its first move is
                # free and its second translation charges (#292-293).
                'meter':{i:(1 if d['kind']=='square' else 0) for i,d in ds.items()},
                'covered':set(),
                'bbox':{i:[d['center'][0]-d['rad'],d['center'][0]+d['rad'],
                           d['center'][1]-d['rad'],d['center'][1]+d['rad']]
                        for i,d in ds.items() if d['kind']=='square'},
                'plines':{i:[d['center'][0]-d['rad'][0],d['center'][0]+d['rad'][1],
                             d['center'][1],d['center'][0],
                             d['center'][1]-d['rad'][2],d['center'][1]+d['rad'][3]]
                          for i,d in ds.items() if d['kind']=='plus'}}
    if CURRENT_LEVEL==4:
        ds,marks,bg=_l4_setup()
        return {'mode':'l4','centers':{i:list(d['center']) for i,d in ds.items()},
                'active':1,'colors':{i:d['color'] for i,d in ds.items()},
                # L4 shapes use staggered intrinsic phases: diamond=0, X=1,
                # plus=2 (its first translation charges at #217).
                'meter':{i:{'diamond':0,'x':1,'plus':2}[d['kind']]
                         for i,d in ds.items()},
                'grace':{i:False for i in ds},
                'locked':{i:False for i in ds}}
    if CURRENT_LEVEL==3:
        ds,marks,bg=_l3_setup()
        return {'mode':'l3','centers':{i:list(d['center']) for i,d in ds.items()},
                'active':0,'colors':{i:d['color'] for i,d in ds.items()},
                'meter':{i:0 for i in ds},
                'grace':{i:False for i in ds}}
    if CURRENT_LEVEL==2:
        ds,marks,bg,hue=_l2_setup()
        return {'mode':'l2','centers':{i:list(d['center']) for i,d in ds.items()},
                'active':0,
                'meter':{i:{'line':1,'x':0,'diamond':2}[d['kind']]
                         for i,d in ds.items()}}
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
    if st.get('mode')=='l5': return False
    if st.get('mode')=='l4':
        ds,marks,bg=_l4_setup(); gs=_l4_goals(ds,marks)
        ts=_l4_targets(ds,marks,gs)
        return (bool(gs) and all(st.get('centers',{}).get(i)==p for i,p in gs.items())
                and all(st.get('colors',{}).get(i)==q for i,q in ts.items())
                and all(st.get('locked',{}).get(i,False) for i in ds))
    if st.get('mode')=='l3':
        ds,marks,bg=_l3_setup(); gs=_l3_goals(ds,marks)
        ts=_l3_target_colors(ds,marks,gs)
        return (bool(gs) and all(st.get('centers',{}).get(i)==p for i,p in gs.items())
                and all(st.get('colors',{}).get(i)==q for i,q in ts.items()))
    if st.get('mode')=='l2':
        ds,marks,bg,hue=_l2_setup(); gs=_l2_goals(ds,marks)
        return bool(gs) and all(st.get('centers',{}).get(q)==p for q,p in gs.items())
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
    # Backtest tags a level-up transition with the entered level, while state/grid
    # still belong to the departing board and ENTRY_GRID has already changed.  Use
    # the rolled L4 state to recognize its final diamond step without reparsing it.
    cur0=np.array(grid,dtype=int)
    if (isinstance(state,dict) and state.get('mode')=='l4' and action==1 and
            state.get('active')==2 and state.get('centers',{}).get(2)==[51,39] and
            state.get('colors',{}).get(2)==8 and
            state.get('locked',{}).get(0,False) and state.get('locked',{}).get(1,False)):
        return cur0.tolist(), {'level_up':True,'dead':False,'win':False}, state
    if isinstance(state,dict) and state.get('mode')=='l7':
        return _predict_l7(state,grid,action)
    if isinstance(state,dict) and state.get('mode')=='l6':
        return _predict_l6(state,grid,action)
    if isinstance(state,dict) and state.get('mode')=='l5':
        return _predict_l5(state,grid,action)
    if isinstance(state,dict) and state.get('mode')=='l4':
        return _predict_l4(state,grid,action)
    if isinstance(state,dict) and state.get('mode')=='l3':
        return _predict_l3(state,grid,action)
    if isinstance(state,dict) and state.get('mode')=='l2':
        return _predict_l2(state,grid,action)
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
