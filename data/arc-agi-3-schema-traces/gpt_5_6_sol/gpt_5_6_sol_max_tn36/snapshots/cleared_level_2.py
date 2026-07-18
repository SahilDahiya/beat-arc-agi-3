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
    """Locate the 7x7 right board's movable 14-pixel plug and 16-pixel socket."""
    # Board top/bottom are the long black horizontal runs above the program.
    candidates=[]
    for y in range(3,min(33,len(grid))):
        xs=[x for x in range(30,len(grid)) if grid[y][x]==0]
        if len(xs)>=20:
            candidates.append((y,min(xs),max(xs)))
    if not candidates:
        return None
    top,left,right=candidates[0]
    # A later matching run is the board bottom.
    bottoms=[y for y,l,r in candidates[1:] if l==left and r==right]
    if not bottoms:
        return None
    bottom=bottoms[0]
    bx,by=left+1,top+1
    bw=(right-left-1)//4
    bh=(bottom-top-1)//4

    # Color-11 objects wholly within the board.
    seen=set(); objs=[]
    for y in range(by,bottom):
        for x in range(bx,right):
            if grid[y][x]!=11 or (x,y) in seen:
                continue
            c=_component(grid,x,y,11); seen.update(c)
            c=[p for p in c if bx<=p[0]<right and by<=p[1]<bottom]
            if c:
                objs.append(c)
    movable=None; socket=None
    for c in objs:
        if len(c)==14 and movable is None:
            movable=c
        if len(c)==16 and socket is None:
            socket=c
    if movable is None or socket is None:
        return None
    def cell(c):
        cx=(min(x for x,y in c)+max(x for x,y in c))/2
        cy=(min(y for x,y in c)+max(y for x,y in c))/2
        return int((cx-bx)//4),int((cy-by)//4)
    obstacles=set()
    for r in range(bh):
        for q in range(bw):
            vals=[grid[by+4*r+dy][bx+4*q+dx] for dy in range(4) for dx in range(4)]
            if vals.count(6)>=8:
                obstacles.add((q,r))
    return cell(movable),cell(socket),obstacles,bw,bh

def _known_path_goal(grid):
    codes=_right_program_codes(grid)
    obj=_board_objects(grid)
    if not codes or obj is None:
        return False
    pos,target,obstacles,bw,bh=obj
    # Confirmed movement codes (bit order is top-to-bottom control strokes):
    # 0 stay, 1 left, 2 right, 3 down, 33 up.
    moves={0:(0,0),1:(-1,0),2:(1,0),3:(0,1),33:(0,-1)}
    x,y=pos
    for code in codes:
        if code not in moves:
            return False
        dx,dy=moves[code]; nx,ny=x+dx,y+dy
        if not (0<=nx<bw and 0<=ny<bh) or (nx,ny) in obstacles:
            return False
        x,y=nx,ny
    return (x,y)==target

def _run_goal(grid):
    if CURRENT_LEVEL==0:
        cs=_small_controls(grid)
        return bool(cs) and all(col==5 for col,cx,cy,c in cs)
    return _known_path_goal(grid)

def step(grid, action, x=None, y=None):
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    if action!=6:
        return g,info

    clicked=[]; clicked_color=None
    if x is not None and y is not None and 0<=y<len(grid) and 0<=x<len(grid[0]):
        clicked_color=grid[y][x]
        clicked=_component(grid,x,y)

    # The 69-pixel color-9 wired circle is RUN.
    if clicked_color==9 and len(clicked)==69 and _run_goal(grid):
        info["level_up"]=True

    _consume_bar(g)

    # Either disconnected half of a T control toggles independently.
    if clicked_color in (1,5) and len(clicked)==3:
        new=5 if clicked_color==1 else 1
        for xx,yy in clicked:
            g[yy][xx]=new
    return g,info
