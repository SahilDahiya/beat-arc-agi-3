def _component(grid, x, y, color=None):
    h,w=len(grid),len(grid[0])
    if not (0<=x<w and 0<=y<h):
        return []
    if color is None:
        color=grid[y][x]
    out=[]; stack=[(x,y)]; seen={(x,y)}
    while stack:
        xx,yy=stack.pop()
        if not (0<=xx<w and 0<=yy<h) or grid[yy][xx]!=color:
            continue
        out.append((xx,yy))
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q=(xx+dx,yy+dy)
            if q not in seen:
                seen.add(q); stack.append(q)
    return out

def _consume_bar(g):
    if len(g)>1:
        for x in range(len(g[1])-1,-1,-1):
            if g[1][x]==9:
                g[1][x]=3
                return

def _small_controls(grid, right_only=False):
    """All disconnected 3-pixel program strokes, with color and centroid."""
    h,w=len(grid),len(grid[0]); seen=set(); ans=[]
    for y in range(h):
        for x in range(w):
            if (x,y) in seen or grid[y][x] not in (1,5):
                continue
            c=_component(grid,x,y)
            seen.update(c)
            if len(c)==3 and (not right_only or min(xx for xx,yy in c)>=32):
                cx=sum(xx for xx,yy in c)//3
                cy=sum(yy for xx,yy in c)//3
                ans.append((grid[y][x],cx,cy,c))
    return ans

def _right_program_codes(grid):
    """Read the right-hand 3xN two-stroke program as six-bit columns."""
    cs=_small_controls(grid,True)
    if not cs:
        return []
    xs=sorted(set(cx for col,cx,cy,c in cs))
    ys=sorted(set(cy for col,cx,cy,c in cs))
    if len(ys)!=6:
        return []
    lookup={(cx,cy):col for col,cx,cy,c in cs}
    codes=[]
    for cx in xs:
        if any((cx,cy) not in lookup for cy in ys):
            continue
        code=0
        for b,cy in enumerate(ys):
            if lookup[(cx,cy)]==5:
                code |= 1<<b
        codes.append(code)
    return codes

def _board_objects(grid):
    """Locate a scaled/oriented plug and its possibly recolored socket."""
    # Board top/bottom are the long black horizontal runs above the program.
    candidates=[]
    for y in range(3,min(33,len(grid))):
        xs=[x for x in range(30,len(grid)) if grid[y][x]==0]
        if len(xs)>=20:
            candidates.append((y,min(xs),max(xs)))
    if not candidates:
        return None
    top,left,right=candidates[0]
    bottoms=[y for y,l,r in candidates[1:] if l==left and r==right]
    if not bottoms:
        return None
    bottom=bottoms[0]
    bx,by=left+1,top+1
    bw=(right-left-1)//4
    bh=(bottom-top-1)//4

    # Objects use non-background colors; walls are color 6.
    seen=set(); objs=[]
    for y in range(by,bottom):
        for x in range(bx,right):
            col=grid[y][x]
            if col in (0,3,4,5,6) or (x,y) in seen:
                continue
            c=_component(grid,x,y,col); seen.update(c)
            c=[p for p in c if bx<=p[0]<right and by<=p[1]<bottom]
            if c:
                objs.append((col,c))

    movable=None; socket=None
    scale=1; target_scale=1
    for col,c in objs:
        xa=min(x for x,y in c); xb=max(x for x,y in c)
        ya=min(y for x,y in c); yb=max(y for x,y in c)
        ww,hh=xb-xa+1,yb-ya+1
        for s in range(1,8):
            if movable is None and len(c)==14*s*s and ww==4*s and hh==4*s:
                movable=(col,c); scale=s
            if socket is None and len(c)==16*s*s and ((ww==6*s and hh==5*s) or (ww==5*s and hh==6*s)):
                socket=(col,c); target_scale=s
    if movable is None or socket is None:
        return None

    mcol,mc=movable; tcol,sc=socket
    mset=set(mc); sset=set(sc)
    mxa=min(x for x,y in mc); mxb=max(x for x,y in mc)
    mya=min(y for x,y in mc); myb=max(y for x,y in mc)
    # The plug's one deficient outer edge is the direction it points.
    edge_counts=[
        sum(1 for x in range(mxa,mxb+1) if (x,mya) in mset),
        sum(1 for y in range(mya,myb+1) if (mxb,y) in mset),
        sum(1 for x in range(mxa,mxb+1) if (x,myb) in mset),
        sum(1 for y in range(mya,myb+1) if (mxa,y) in mset)]
    dirs=("U","R","D","L")
    orientation=dirs[edge_counts.index(min(edge_counts))]

    sxa=min(x for x,y in sc); sxb=max(x for x,y in sc)
    sya=min(y for x,y in sc); syb=max(y for x,y in sc)
    sw,sh=sxb-sxa+1,syb-sya+1
    # The socket's deficient edge is its entrance; target points opposite it.
    topn=sum(1 for x in range(sxa,sxb+1) if (x,sya) in sset)
    rightn=sum(1 for y in range(sya,syb+1) if (sxb,y) in sset)
    botn=sum(1 for x in range(sxa,sxb+1) if (x,syb) in sset)
    leftn=sum(1 for y in range(sya,syb+1) if (sxa,y) in sset)
    if topn<sw:
        target_orientation="D"; txpix,typix=sxa+target_scale,sya
    elif botn<sw:
        target_orientation="U"; txpix,typix=sxa+target_scale,sya+target_scale
    elif leftn<sh:
        target_orientation="R"; txpix,typix=sxa,sya+target_scale
    else:
        target_orientation="L"; txpix,typix=sxa+target_scale,sya+target_scale

    pos=((mxa-bx)//4,(mya-by)//4)
    target=((txpix-bx)//4,(typix-by)//4)
    obstacles=set()
    for r in range(bh):
        for q in range(bw):
            vals=[grid[by+4*r+dy][bx+4*q+dx] for dy in range(4) for dx in range(4)]
            if vals.count(6)>=8:
                obstacles.add((q,r))
    return (pos,target,obstacles,bw,bh,scale,target_scale,
            orientation,target_orientation,mcol,tcol)

def _known_path_goal(grid):
    codes=_right_program_codes(grid)
    obj=_board_objects(grid)
    if not codes or obj is None:
        return False
    (pos,target,obstacles,bw,bh,scale,target_scale,
     orientation,target_orientation,color,target_color)=obj

    # Confirmed opcodes.
    moves={0:(0,0),1:(-1,0),2:(1,0),3:(0,1),4:(0,0),
           10:(2,0),11:(2,0),12:(-2,0),13:(-2,0),
           33:(0,-1),34:(-1,0)}
    recolor={14:9,15:8,63:15}
    dirs=("U","R","D","L")
    x,y=pos

    def clear(px,py,ss):
        if px<0 or py<0 or px+ss>bw or py+ss>bh:
            return False
        for rr in range(py,py+ss):
            for qq in range(px,px+ss):
                if (qq,rr) in obstacles:
                    return False
        return True

    for code in codes:
        if code==8:
            scale+=1
            continue
        if code==9:
            if scale>1:
                scale-=1
            continue
        if code==5:                 # clockwise quarter-turn
            orientation=dirs[(dirs.index(orientation)+1)%4]
            continue
        if code in (6,16):          # counter-clockwise quarter-turn
            orientation=dirs[(dirs.index(orientation)-1)%4]
            continue
        if code==7:                 # half-turn
            orientation=dirs[(dirs.index(orientation)+2)%4]
            continue
        if code in recolor:
            color=recolor[code]
            continue
        if code not in moves:
            return False
        dx,dy=moves[code]
        steps=max(abs(dx),abs(dy))
        ux=0 if dx==0 else (1 if dx>0 else -1)
        uy=0 if dy==0 else (1 if dy>0 else -1)
        for k in range(steps):
            nx,ny=x+ux,y+uy
            if not clear(nx,ny,scale):
                break
            x,y=nx,ny
    return ((x,y)==target and scale==target_scale and
            orientation==target_orientation and color==target_color)

def _l5_execute(grid):
    """L5 commits each RUN's final sprite position and consumes checker tokens."""
    obj=_board_objects(grid)
    codes=_right_program_codes(grid)
    if obj is None or not codes:
        return [row[:] for row in grid],False
    (pos,target,obstacles,bw,bh,scale,target_scale,
     orientation,target_orientation,color,target_color)=obj

    # Recover board frame.
    candidates=[]
    for yy in range(3,min(33,len(grid))):
        xs=[xx for xx in range(30,len(grid)) if grid[yy][xx]==0]
        if len(xs)>=20:
            candidates.append((yy,min(xs),max(xs)))
    top,left,right=candidates[0]
    bottoms=[yy for yy,ll,rr in candidates[1:] if ll==left and rr==right]
    bottom=bottoms[0]
    bx,by=left+1,top+1

    # Eight alternating object pixels mark persistent save checkpoints.
    # Read them from ENTRY_GRID because the plug visually hides one while parked.
    checkpoints=set()
    for rr in range(bh):
        for qq in range(bw):
            vals=[ENTRY_GRID[by+4*rr+dy][bx+4*qq+dx]
                  for dy in range(4) for dx in range(4)]
            if vals.count(11)==8:
                checkpoints.add((qq,rr))

    moves={0:(0,0),1:(-1,0),2:(1,0),3:(0,1),4:(0,0),
           10:(2,0),11:(2,0),12:(-2,0),13:(-2,0),
           33:(0,-1),34:(-1,0)}
    recolor={14:9,15:8,63:15}
    dirs=("U","R","D","L")
    x,y=pos

    def clear(px,py,ss):
        if px<0 or py<0 or px+ss>bw or py+ss>bh:
            return False
        for rr in range(py,py+ss):
            for qq in range(px,px+ss):
                if (qq,rr) in obstacles:
                    return False
        return True

    for code in codes:
        if code==8:
            scale+=1
            continue
        if code==9:
            if scale>1:
                scale-=1
            continue
        if code==5:
            orientation=dirs[(dirs.index(orientation)+1)%4]
            continue
        if code in (6,16):
            orientation=dirs[(dirs.index(orientation)-1)%4]
            continue
        if code==7:
            orientation=dirs[(dirs.index(orientation)+2)%4]
            continue
        if code in recolor:
            color=recolor[code]
            continue
        if code not in moves:
            continue
        dx,dy=moves[code]
        steps=max(abs(dx),abs(dy))
        ux=0 if dx==0 else (1 if dx>0 else -1)
        uy=0 if dy==0 else (1 if dy>0 else -1)
        for k in range(steps):
            nx,ny=x+ux,y+uy
            if not clear(nx,ny,scale):
                break
            x,y=nx,ny

    # A maze RUN commits only when its FINAL footprint lands on a checker
    # checkpoint. Passing over one and continuing does not save progress.
    landing=[]
    for q in checkpoints:
        if x<=q[0]<x+scale and y<=q[1]<y+scale:
            landing.append(q)

    goal=((x,y)==target and scale==target_scale and
          orientation==target_orientation and color==target_color)
    out=[row[:] for row in grid]
    if goal:
        return out,True
    if not landing:
        return out,False

    # Leaving a saved checkpoint reveals its original marker again.
    ox,oy=pos
    for rr in range(oy,oy+obj[5]):
        for qq in range(ox,ox+obj[5]):
            base=5 if (qq+rr)%2==0 else 4
            for dy in range(4):
                for dx in range(4):
                    if (qq,rr) in checkpoints:
                        out[by+4*rr+dy][bx+4*qq+dx]=ENTRY_GRID[by+4*rr+dy][bx+4*qq+dx]
                    else:
                        out[by+4*rr+dy][bx+4*qq+dx]=base

    # A parked plug hides its destination marker over plain cell base.
    for qq,rr in landing:
        base=5 if (qq+rr)%2==0 else 4
        for dy in range(4):
            for dx in range(4):
                out[by+4*rr+dy][bx+4*qq+dx]=base

    # Draw the final nearest-neighbour plug mask.
    px,py=bx+4*x,by+4*y
    for sy in range(4):
        for sx in range(4):
            missing=((orientation=="U" and sy==0 and sx in (1,2)) or
                     (orientation=="D" and sy==3 and sx in (1,2)) or
                     (orientation=="L" and sx==0 and sy in (1,2)) or
                     (orientation=="R" and sx==3 and sy in (1,2)))
            if missing:
                continue
            for dy in range(scale):
                for dx in range(scale):
                    out[py+sy*scale+dy][px+sx*scale+dx]=color
    return out,False

def _run_goal(grid):
    if CURRENT_LEVEL==0:
        cs=_small_controls(grid)
        return bool(cs) and all(col==5 for col,cx,cy,c in cs)
    return _known_path_goal(grid)

def init_state(entry_grid):
    # Number of actions since this level entry or RESET.
    return 0

def predict(state, grid, action, x=None, y=None):
    n=state if isinstance(state,int) else 0
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    if action!=6:
        return g,info,0

    clicked=[]; clicked_color=None
    if x is not None and y is not None and 0<=y<len(grid) and 0<=x<len(grid[0]):
        clicked_color=grid[y][x]
        clicked=_component(grid,x,y)

    # The 69-pixel color-9 wired circle is RUN.
    is_run=(clicked_color==9 and len(clicked)==69)
    if is_run and CURRENT_LEVEL==5:
        g,goal=_l5_execute(grid)
        info["level_up"]=goal
    elif is_run and _run_goal(grid):
        info["level_up"]=True

    # L5's meter advances once per pair of clicks: odd-numbered clicks are
    # free and even-numbered clicks consume one cell.
    free_click=(CURRENT_LEVEL==5 and n%2==0)
    if not free_click:
        _consume_bar(g)

    # Either disconnected half of a T control toggles independently.
    if clicked_color in (1,5) and len(clicked)==3:
        new=5 if clicked_color==1 else 1
        for xx,yy in clicked:
            g[yy][xx]=new
    return g,info,n+1
