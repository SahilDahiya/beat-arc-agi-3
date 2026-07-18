import numpy as np

# Two long monochrome pluses move over a static field.  Their intersection is
# marked 0 when active.  Directional moves are three cells; ACTION5 switches
# the active plus.  State keeps the hidden full geometry when an arm is
# visually occluded by another object.

def _entry_data():
    e = np.array(ENTRY_GRID, dtype=int)
    crosses = {}
    for y in range(1, e.shape[0]-2):
        for x in range(1, e.shape[1]-1):
            v = int(e[y,x])
            if v == 0:
                ns = [int(e[y,x-1]),int(e[y,x+1]),int(e[y-1,x]),int(e[y+1,x])]
                if ns[0] == ns[1] == ns[2] == ns[3]: v = ns[0]
            if v in (0,4,5,15):
                continue
            # Intersection may itself be 0 in ENTRY_GRID.
            def same(xx,yy):
                q=int(e[yy,xx])
                return q == v
            if same(x-1,y) and same(x+1,y) and same(x,y-1) and same(x,y+1):
                xl=x
                while xl-1 >= 0 and int(e[y,xl-1]) == v: xl-=1
                xr=x
                while xr+1 < e.shape[1] and int(e[y,xr+1]) == v: xr+=1
                yt=y
                while yt-1 >= 0 and int(e[yt-1,x]) == v: yt-=1
                yb=y
                while yb+1 < e.shape[0]-1 and int(e[yb+1,x]) == v: yb+=1
                crosses[v] = {'center':[x,y], 'rad':[x-xl,xr-x,y-yt,yb-y]}
    # Locate a 0 centre separately (the scan above sees its neighbours' hue).
    active = None
    for y,x in np.argwhere(e == 0):
        if 0<y<e.shape[0]-1 and 0<x<e.shape[1]-1:
            ns=[int(e[y,x-1]),int(e[y,x+1]),int(e[y-1,x]),int(e[y+1,x])]
            if ns[0] == ns[1] == ns[2] == ns[3] and ns[0] not in (0,4,5,15):
                active=ns[0]
                # The 0 prevented normal intersection detection.
                v=active
                xl=x-1
                while xl-1>=0 and int(e[y,xl-1])==v: xl-=1
                xr=x+1
                while xr+1<e.shape[1] and int(e[y,xr+1])==v: xr+=1
                yt=y-1
                while yt-1>=0 and int(e[yt-1,x])==v: yt-=1
                yb=y+1
                while yb+1<e.shape[0]-1 and int(e[yb+1,x])==v: yb+=1
                crosses[v]={'center':[int(x),int(y)],'rad':[int(x-xl),int(xr-x),int(y-yt),int(yb-y)]}
                break
    return crosses, active

def init_state(entry_grid):
    cs, active = _entry_data()
    return {'centers':{int(c):list(d['center']) for c,d in cs.items()},
            'active':active, 'last_dir':None, 'run_len':0,
            'last_pause':None}

def _static_data():
    cs,_ = _entry_data()
    e=np.array(ENTRY_GRID,dtype=int)
    vals,counts=np.unique(e[:-1],return_counts=True)
    bg=int(vals[np.argmax(counts)])
    return cs,bg

def _goals():
    cs,_=_entry_data()
    e=np.array(ENTRY_GRID,dtype=int)
    ans={}
    for c in cs:
        pts=[]
        for y in range(1,e.shape[0]-2):
            for x in range(1,e.shape[1]-1):
                if (int(e[y,x])==c and int(e[y-1,x])==4 and
                    int(e[y+1,x])==4 and int(e[y,x-1])==4 and
                    int(e[y,x+1])==4): pts.append((x,y))
        if pts:
            gx=max(set(x for x,y in pts),key=lambda z:sum(x==z for x,y in pts))
            gy=max(set(y for x,y in pts),key=lambda z:sum(y==z for x,y in pts))
            ans[c]=[gx,gy]
    return ans

def _aligned(st):
    if not isinstance(st,dict): return False
    gs=_goals()
    return bool(gs) and all(st.get('centers',{}).get(c)==p for c,p in gs.items())

def is_goal(state, grid):
    return _aligned(state)

def predict(state, grid, action, x=None, y=None):
    cur=np.array(grid,dtype=int)
    st={'centers':{int(c):list(p) for c,p in state['centers'].items()},
        'active':state['active'], 'last_dir':state.get('last_dir'),
        'run_len':state.get('run_len',0),
        'last_pause':state.get('last_pause')}
    cs,bg=_static_data()
    # Resynchronise the active hue/centre from the rendered 0. This also
    # makes replay exact when the very first historical action is skipped.
    for yy,xx in np.argwhere(cur == 0):
        if 0<yy<cur.shape[0]-1 and 0<xx<cur.shape[1]-1:
            ns=[int(cur[yy,xx-1]),int(cur[yy,xx+1]),int(cur[yy-1,xx]),int(cur[yy+1,xx])]
            cand=[q for q in ns if q in cs]
            if cand:
                q=max(set(cand), key=cand.count)
                st['active']=q
                st['centers'][q]=[int(xx),int(yy)]
                break
    c=st['active']
    delta={1:(0,-3),2:(0,3),3:(-3,0),4:(3,0)}.get(action)
    moved=False
    moved_axis=None
    if c in st['centers'] and delta is not None:
        cx,cy=st['centers'][c]
        dx,dy=delta
        nx,ny=cx+dx,cy+dy
        # The intersection stays onscreen; arms themselves may be clipped.
        if 0 <= nx < cur.shape[1] and 0 <= ny < cur.shape[0]-1:
            st['centers'][c]=[nx,ny]
            moved=True
            moved_axis=('x',cx,nx) if dx else ('y',cy,ny)
    if action == 5 and c in st['centers']:
        others=[q for q in st['centers'] if q != c]
        if others: st['active']=others[0]

    # A directional move normally grows the unary footer by one. It is free
    # on every third lattice line selected by the active hue: destination
    # coordinate/3 mod 3 == hue mod 3 (equivalently coord mod 9 == 3*hue mod 9).
    footer=cur[-1].copy()
    if moved:
        axis,oldv,newv=moved_axis
        free=(newv % 9 == (3*c) % 9)
        # For hue 9 moving vertically on its repeated target column, the
        # observed free lattice is every 6 rows (36,30,...), not the generic
        # 9-cell hue phase. This is derived from the paired vertical markers.
        if c==9 and dy!=0:
            gs=_goals()
            free=(c in gs and nx==gs[c][0] and newv % 6 == 0)
        # Also free when the leading arm endpoint just touches the near edge
        # of an aligned same-hue framed marker (the marker remains outside
        # the arm). Example: 9 moving up to y=30 has top endpoint 17,
        # touching the bottom edge of its marker centred at (48,16).
        if c in cs:
            l,r,t,b=cs[c]['rad']
            e=np.array(ENTRY_GRID,dtype=int)
            for my in range(1,e.shape[0]-2):
                for mx in range(1,e.shape[1]-1):
                    if (int(e[my,mx])==c and int(e[my-1,mx])==4 and
                        int(e[my+1,mx])==4 and int(e[my,mx-1])==4 and
                        int(e[my,mx+1])==4):
                        if dy<0 and nx==mx and ny-t==my+1: free=True
                        if dy>0 and nx==mx and ny+b==my-1: free=True
                        if dx<0 and ny==my and nx-l==mx+1: free=True
                        if dx>0 and ny==my and nx+r==mx-1: free=True
        if not free:
            ff=np.where(footer == 15)[0]
            if len(ff): footer[int(ff[-1])]=1
    if action in (1,2,3,4):
        st['last_dir']=action

    # Render from a static background every frame. This restores targets when
    # an arm moves away; arms paint over their framed markers while present.
    out=np.array(ENTRY_GRID,dtype=int).copy()
    for q,d in cs.items():
        ex,ey=d['center']; l,r,t,b=d['rad']
        for xx in range(max(0,ex-l),min(out.shape[1],ex+r+1)):
            if int(out[ey,xx]) in (q,0): out[ey,xx]=bg
        for yy in range(max(0,ey-t),min(out.shape[0]-1,ey+b+1)):
            if int(out[yy,ex]) in (q,0): out[yy,ex]=bg
    # Fixed render order: hue 9 is on top of hue b at crossings.
    for q in sorted(st['centers'], reverse=True):
        if q not in cs: continue
        cx,cy=st['centers'][q]; l,r,t,b=cs[q]['rad']
        for xx in range(max(0,cx-l),min(out.shape[1],cx+r+1)):
            out[cy,xx]=q
        for yy in range(max(0,cy-t),min(out.shape[0]-1,cy+b+1)):
            out[yy,cx]=q
    ac=st['active']
    if ac in st['centers']:
        ax,ay=st['centers'][ac]
        out[ay,ax]=0
    out[-1]=footer
    done=_aligned(st)
    return out.tolist(), {'level_up':bool(done and CURRENT_LEVEL != 7),
                          'dead':False,
                          'win':bool(done and CURRENT_LEVEL == 7)}, st
