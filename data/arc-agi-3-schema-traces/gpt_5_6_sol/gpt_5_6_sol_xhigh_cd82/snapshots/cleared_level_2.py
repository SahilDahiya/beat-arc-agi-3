def _main_red(grid):
    cells={(x,y) for y in range(18,len(grid)-1)
           for x in range(len(grid[0])) if grid[y][x]==2}
    comps=[]
    while cells:
        p=cells.pop(); comp=[p]; stack=[p]
        while stack:
            x,y=stack.pop()
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if q in cells:
                    cells.remove(q); stack.append(q); comp.append(q)
        comps.append(comp)
    return max(comps,key=len) if comps else []

def _main_zero(grid):
    cells={(x,y) for y in range(18,len(grid)-1)
           for x in range(len(grid[0])) if grid[y][x]==0}
    comps=[]
    while cells:
        p=cells.pop(); comp=[p]; stack=[p]
        while stack:
            x,y=stack.pop()
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if q in cells:
                    cells.remove(q); stack.append(q); comp.append(q)
        comps.append(comp)
    return max(comps,key=len) if comps else []

def _consume(g):
    # Effective moves consume the rightmost remaining cell of the color-4
    # action bar along the last row.
    for xx in range(len(g[0]) - 1, -1, -1):
        if g[-1][xx] == 4:
            g[-1][xx] = 5
            return

def _turn_from_flat(g, turn_right=False, fill=15):
    # Render the selected open rectangular tray after its first horizontal
    # turn. ACTION4 is the horizontal mirror of ACTION3.
    # Track the movable main component.  Auxiliary literal stamps vanish
    # as soon as the main stencil leaves its entry orientation.
    pts = _main_red(g)
    if not pts:
        return False
    minx = min(x for x,y in pts)
    miny = min(y for x,y in pts)
    maxx = max(x for x,y in pts)
    maxy = max(y for x,y in pts)
    if maxx-minx != 13 or maxy-miny != 8:
        return False
    # Remove every auxiliary entry component wholesale, including any
    # contrasting cells enclosed by its red outline.
    entry_main=set(_main_red(ENTRY_GRID))
    aux=[(x,y) for y in range(18,len(ENTRY_GRID)-1)
         for x in range(len(ENTRY_GRID[0]))
         if ENTRY_GRID[y][x]==2 and (x,y) not in entry_main]
    if aux:
        ax0,ax1=min(x for x,y in aux),max(x for x,y in aux)
        ay0,ay1=min(y for x,y in aux),max(y for x,y in aux)
        for yy in range(ay0,ay1+1):
            for xx in range(ax0,ax1+1):
                g[yy][xx]=5
    for y in range(18, len(g)-1):
        for x in range(len(g[0])):
            if g[y][x] in (2, fill):
                g[y][x] = 5
    ax, ay = minx - 1, miny - 3
    pixels = []
    def add(x, y, v):
        pixels.append((x, y, v))
    for k in range(17):
        y = ay + k
        if k == 0:
            add(ax, y, 2)
        elif k == 1:
            for x in range(ax-1, ax+2): add(x, y, 2)
        elif 2 <= k <= 6:
            for x in range(ax-k, ax-k+2): add(x, y, 2)
            for x in range(ax-k+2, ax+k-1): add(x, y, fill)
            for x in range(ax+k-1, ax+k+1): add(x, y, 2)
        elif 7 <= k <= 10:
            for x in range(ax-k, ax-k+2): add(x, y, 2)
            for x in range(ax-k+2, ax+12-k): add(x, y, fill)
        elif 11 <= k <= 14:
            s = ax + k - 20
            for x in range(s, s+2): add(x, y, 2)
            for x in range(s+2, ax+12-k): add(x, y, fill)
        elif k == 15:
            for x in range(ax-5, ax-3): add(x, y, 2)
        else:
            add(ax-4, y, 2)
    mirror_sum = minx + maxx
    for x, y, v in pixels:
        if turn_right:
            x = mirror_sum - x
        if 0 <= y < len(g)-1 and 0 <= x < len(g[0]):
            g[y][x] = v
    return True

def _render_aux_side(g, west, fill, x0, x1, y0):
    # Auxiliary literal stamp is rigidly quarter-turned with the main
    # stencil.  At diagonal views it is fully occluded by the main sprite;
    # at a side view it sits just beyond the main stencil.
    main=set(_main_red(ENTRY_GRID))
    aux=[(x,y) for y in range(18,len(ENTRY_GRID)-1)
         for x in range(len(ENTRY_GRID[0]))
         if ENTRY_GRID[y][x]==2 and (x,y) not in main]
    if not aux:
        return
    ax0,ax1=min(x for x,y in aux),max(x for x,y in aux)
    ay0,ay1=min(y for x,y in aux),max(y for x,y in aux)
    w,h=ax1-ax0+1,ay1-ay0+1
    bx=(x0-16) if west else (x1+12)
    by=y0+2
    for sy in range(ay0,ay1+1):
        for sx in range(ax0,ax1+1):
            v=ENTRY_GRID[sy][sx]
            if v==5:
                continue
            if v==15:
                v=fill
            ix,iy=sx-ax0,sy-ay0
            if west:       # counter-clockwise
                dx,dy=iy,w-1-ix
            else:          # clockwise
                dx,dy=h-1-iy,ix
            g[by+dy][bx+dx]=v

def _turn_to_side(g, west=True, fill=15):
    # From an upper diagonal position, ACTION2 moves the open stencil to
    # the side of the fixed target, aimed inward.
    zeros = _main_zero(ENTRY_GRID)
    if not zeros:
        return
    x0, x1 = min(x for x,y in zeros), max(x for x,y in zeros)
    y0, y1 = min(y for x,y in zeros), max(y for x,y in zeros)
    for y in range(18, len(g)-1):
        for x in range(len(g[0])):
            if g[y][x] in (2,fill) and not (
                    x0 <= x <= x1 and y0 <= y <= y1):
                g[y][x] = 5
    if west:
        a, b = x0-10, x0-2
        wall = a
    else:
        a, b = x1+2, x1+10
        wall = b
    for x in range(a,b+1):
        g[y0-2][x] = 2
        g[y1+2][x] = 2
    for y in range(y0-1,y1+2):
        g[y][wall] = 2
        if west:
            for x in range(a+1,b):
                g[y][x] = fill
        else:
            for x in range(a+1,b):
                g[y][x] = fill
    _render_aux_side(g, west, fill, x0, x1, y0)

def _turn_to_upper_diag(g, west=True, fill=15):
    zeros=_main_zero(ENTRY_GRID)
    reds=_main_red(ENTRY_GRID)
    if not zeros or not reds:
        return
    x0,x1=min(x for x,y in zeros),max(x for x,y in zeros)
    y0,y1=min(y for x,y in zeros),max(y for x,y in zeros)
    minx,maxx=min(x for x,y in reds),max(x for x,y in reds)
    miny=min(y for x,y in reds)
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            if (not (x0<=x<=x1 and y0<=y<=y1)
                    and g[y][x] in (0,2,fill)):
                g[y][x]=5
    ax,ay=minx-1,miny-3
    pixels=[]
    def add(x,y,v): pixels.append((x,y,v))
    for k in range(17):
        y=ay+k
        if k==0: add(ax,y,2)
        elif k==1:
            for x in range(ax-1,ax+2): add(x,y,2)
        elif 2<=k<=6:
            for x in range(ax-k,ax-k+2): add(x,y,2)
            for x in range(ax-k+2,ax+k-1): add(x,y,fill)
            for x in range(ax+k-1,ax+k+1): add(x,y,2)
        elif 7<=k<=10:
            for x in range(ax-k,ax-k+2): add(x,y,2)
            for x in range(ax-k+2,ax+12-k): add(x,y,fill)
        elif 11<=k<=14:
            s=ax+k-20
            for x in range(s,s+2): add(x,y,2)
            for x in range(s+2,ax+12-k): add(x,y,fill)
        elif k==15:
            for x in range(ax-5,ax-3): add(x,y,2)
        else:
            add(ax-4,y,2)
    mirror_x=minx+maxx
    for x,y,v in pixels:
        if not west:
            x=mirror_x-x
        if 0<=x<len(g[0]) and 18<=y<len(g)-1:
            g[y][x]=v

def _turn_to_lower_diag(g, west=True, fill=15):
    # Side -> lower diagonal: vertical mirror of the upper diagonal stencil
    # around the fixed target's horizontal centerline.
    zeros = _main_zero(ENTRY_GRID)
    reds = _main_red(ENTRY_GRID)
    if not zeros or not reds:
        return
    x0,x1 = min(x for x,y in zeros),max(x for x,y in zeros)
    y0,y1 = min(y for x,y in zeros),max(y for x,y in zeros)
    minx,maxx = min(x for x,y in reds),max(x for x,y in reds)
    miny = min(y for x,y in reds)
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            if (not (x0 <= x <= x1 and y0 <= y <= y1)
                    and g[y][x] in (0,2,fill)):
                # At a diagonal view the auxiliary stencil is fully hidden;
                # clear its contrasting interior as well as its frame/fill.
                g[y][x] = 5
    ax,ay = minx-1,miny-3
    pixels=[]
    def add(x,y,v): pixels.append((x,y,v))
    for k in range(17):
        y=ay+k
        if k==0: add(ax,y,2)
        elif k==1:
            for x in range(ax-1,ax+2): add(x,y,2)
        elif 2<=k<=6:
            for x in range(ax-k,ax-k+2): add(x,y,2)
            for x in range(ax-k+2,ax+k-1): add(x,y,fill)
            for x in range(ax+k-1,ax+k+1): add(x,y,2)
        elif 7<=k<=10:
            for x in range(ax-k,ax-k+2): add(x,y,2)
            for x in range(ax-k+2,ax+12-k): add(x,y,fill)
        elif 11<=k<=14:
            s=ax+k-20
            for x in range(s,s+2): add(x,y,2)
            for x in range(s+2,ax+12-k): add(x,y,fill)
        elif k==15:
            for x in range(ax-5,ax-3): add(x,y,2)
        else: add(ax-4,y,2)
    mirror_x=minx+maxx
    mirror_y=y0+y1
    for x,y,v in pixels:
        if not west: x=mirror_x-x
        y=mirror_y-y
        if 0<=x<len(g[0]) and 18<=y<len(g)-1:
            g[y][x]=v

def _turn_to_south(g, fill=15):
    # Lower diagonal -> SOUTH: vertical mirror of the entry stencil, open
    # toward the target above it.
    zeros=_main_zero(ENTRY_GRID)
    if not zeros: return
    x0,x1=min(x for x,y in zeros),max(x for x,y in zeros)
    y0,y1=min(y for x,y in zeros),max(y for x,y in zeros)
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            if not (x0<=x<=x1 and y0<=y<=y1) and g[y][x] in (2,fill):
                g[y][x]=5
    sy=y0+y1
    for y in range(18,len(ENTRY_GRID)-1):
        for x in range(len(ENTRY_GRID[0])):
            v=ENTRY_GRID[y][x]
            if v in (2,15):
                yy=sy-y
                if 18<=yy<len(g)-1:
                    g[yy][x]=2 if v==2 else fill
    # Preserve contrasting interior pixels of an auxiliary literal stamp.
    main=set(_main_red(ENTRY_GRID))
    aux=[(x,y) for y in range(18,len(ENTRY_GRID)-1)
         for x in range(len(ENTRY_GRID[0]))
         if ENTRY_GRID[y][x]==2 and (x,y) not in main]
    if aux:
        ax0,ax1=min(x for x,y in aux),max(x for x,y in aux)
        ay0,ay1=min(y for x,y in aux),max(y for x,y in aux)
        for yy in range(ay0,ay1+1):
            for xx in range(ax0,ax1+1):
                v=ENTRY_GRID[yy][xx]
                if v!=5:
                    g[sy-yy][xx]=fill if v==15 else v

def _orientation(g):
    pts = _main_red(g)
    ent = _main_red(ENTRY_GRID)
    if not pts or not ent:
        return None
    minx, maxx = min(x for x,y in pts), max(x for x,y in pts)
    miny, maxy = min(y for x,y in pts), max(y for x,y in pts)
    emin = min(x for x,y in ent)
    emin_y = min(y for x,y in ent)
    if maxx-minx == 13 and maxy-miny == 8:
        return "south" if miny > emin_y + 10 else "flat"
    if maxx-minx == 8 and maxy-miny == 13:
        return "west" if minx < emin else "east"
    if miny > emin_y + 10:
        return "southwest" if minx < emin else "southeast"
    return "left" if minx < emin else "right"

def _restore_flat(g, fill=15):
    # Return the movable objects to their entry orientation without touching
    # the painted main target.
    zeros=_main_zero(ENTRY_GRID)
    if not zeros:
        return
    x0,x1=min(x for x,y in zeros),max(x for x,y in zeros)
    y0,y1=min(y for x,y in zeros),max(y for x,y in zeros)
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            if (not (x0<=x<=x1 and y0<=y<=y1)
                    and g[y][x] in (0,2,fill)):
                g[y][x]=5
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            v=ENTRY_GRID[y][x]
            if v in (2,15):
                g[y][x]=2 if v==2 else fill
    # Restore the full auxiliary box, including contrasting interior cells.
    main=set(_main_red(ENTRY_GRID))
    aux=[(x,y) for y in range(18,len(ENTRY_GRID)-1)
         for x in range(len(ENTRY_GRID[0]))
         if ENTRY_GRID[y][x]==2 and (x,y) not in main]
    if aux:
        ax0,ax1=min(x for x,y in aux),max(x for x,y in aux)
        ay0,ay1=min(y for x,y in aux),max(y for x,y in aux)
        for yy in range(ay0,ay1+1):
            for xx in range(ax0,ax1+1):
                v=ENTRY_GRID[yy][xx]
                if v!=5:
                    g[yy][xx]=fill if v==15 else v

def init_state(entry_grid):
    # White is initially selected in the top-right color selector.
    return {"down": 0, "selected": 15}

def predict(state, grid, action, x=None, y=None):
    st = dict(state)
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action == 0:
        return [row[:] for row in ENTRY_GRID], info, {"down": 0, "selected": 15}
    ori = _orientation(g)
    if action == 3:
        if ori == "flat":
            _turn_from_flat(g, False, st.get("selected",15))
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "right":
            _restore_flat(g, st.get("selected",15))
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "southeast":
            _turn_to_south(g, st.get("selected",15))
            _consume(g)
        elif ori == "south":
            _turn_to_lower_diag(g, True, st.get("selected",15))
            _consume(g)
    elif action == 4:
        if ori == "flat":
            _turn_from_flat(g, True, st.get("selected",15))
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "left":
            _restore_flat(g, st.get("selected",15))
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "southwest":
            _turn_to_south(g, st.get("selected",15))
            _consume(g)
    elif action == 1:
        # ACTION1 moves upward on the eight-position ring; at the original
        # N position it merely changes a visually hidden depth state.
        if ori == "southwest":
            _turn_to_side(g, True, st.get("selected",15))
        elif ori == "southeast":
            _turn_to_side(g, False, st.get("selected",15))
            _consume(g)
        elif ori == "west":
            _turn_to_upper_diag(g, True, st.get("selected",15))
        elif ori == "east":
            _turn_to_upper_diag(g, False, st.get("selected",15))
        elif all(v == 4 for v in g[-1]):
            _consume(g)
        st["down"] = -1
    elif action == 2:
        if ori == "left":
            _turn_to_side(g, True, st.get("selected",15))
        elif ori == "right":
            _turn_to_side(g, False, st.get("selected",15))
            # With an auxiliary literal stencil the side move is free.
            main=set(_main_red(ENTRY_GRID))
            has_aux=any(ENTRY_GRID[yy][xx]==2 and (xx,yy) not in main
                        for yy in range(18,len(ENTRY_GRID)-1)
                        for xx in range(len(ENTRY_GRID[0])))
            if not has_aux:
                _consume(g)
        elif ori == "west":
            _turn_to_lower_diag(g, True, st.get("selected",15))
            _consume(g)
        elif ori == "east":
            _turn_to_lower_diag(g, False, st.get("selected",15))
            main=set(_main_red(ENTRY_GRID))
            has_aux=any(ENTRY_GRID[yy][xx]==2 and (xx,yy) not in main
                        for yy in range(18,len(ENTRY_GRID)-1)
                        for xx in range(len(ENTRY_GRID[0])))
            if has_aux:
                _consume(g)
        else:
            _consume(g)
        st["down"] = 1
    elif action == 5:
        zeros=_main_zero(ENTRY_GRID)
        if zeros:
            x0,x1=min(x for x,y in zeros),max(x for x,y in zeros)
            y0,y1=min(y for x,y in zeros),max(y for x,y in zeros)
            midx=(x0+x1+1)//2
            midy=(y0+y1+1)//2
            span=x1-x0
            color=st.get("selected",15)
            mask=[]
            for y in range(y0,y1+1):
                for x in range(x0,x1+1):
                    dx,dy=x-x0,y-y0
                    hit=False
                    if ori=="flat": hit=y<midy
                    elif ori=="south": hit=y>=midy
                    elif ori=="west": hit=x<midx
                    elif ori=="east": hit=x>=midx
                    elif ori=="left": hit=dx+dy<=span
                    elif ori=="right": hit=(x1-x)+dy<=span
                    elif ori=="southwest": hit=dx+(y1-y)<=span
                    elif ori=="southeast": hit=dx+dy>=span
                    if hit: mask.append((x,y))
            changed=any(g[y][x]!=color for x,y in mask)
            if changed:
                for x,y in mask:
                    g[y][x]=color
                if ((ori=="flat" and st.get("down",0)==0)
                        or (ori in ("left","right","west","east")
                            and st.get("down",0)<0)):
                    _consume(g)
            # The goal preview is always the 10x10 block at (3,3).
            if x1-x0==9 and y1-y0==9:
                solved=all(g[y0+dy][x0+dx]==ENTRY_GRID[3+dy][3+dx]
                           for dy in range(10) for dx in range(10))
                if solved:
                    if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 5:
                        info["win"]=True
                    else:
                        info["level_up"]=True
    elif action == 6:
        # Palette buttons are the separate five-cell color-4 runs at y=2.
        runs=[]
        xx=18
        while xx<len(g[0]):
            if ENTRY_GRID[2][xx]==4:
                a=xx
                while xx<len(g[0]) and ENTRY_GRID[2][xx]==4:
                    xx+=1
                if xx-a==5: runs.append((a,xx-1))
            else:
                xx+=1
        hit=None
        if x is not None and y is not None and 2<=y<=6:
            for a,b in runs:
                if a<=x<=b:
                    hit=(a,b)
                    break
        if hit is not None:
            a,b=hit
            new_color=ENTRY_GRID[4][(a+b)//2]
            old_color=st.get("selected",15)
            if new_color!=old_color:
                target=set(_main_zero(ENTRY_GRID))
                pristine=all(g[ty][tx]==0 for tx,ty in target)
                for yy in range(18,len(g)-1):
                    for xx in range(len(g[0])):
                        if g[yy][xx]==old_color and (xx,yy) not in target:
                            g[yy][xx]=new_color
                for ra,rb in runs:
                    for xx in range(ra,rb+1):
                        g[7][xx]=3
                for xx in range(a,b+1):
                    g[7][xx]=0
                st["selected"]=new_color
                # Palette changes are free only after a complete uniform
                # top-half layer has been laid down.  On a pristine or
                # partially painted canvas they consume one cost unit.
                if target:
                    tx0,tx1=min(tx for tx,ty in target),max(tx for tx,ty in target)
                    ty0,ty1=min(ty for tx,ty in target),max(ty for tx,ty in target)
                    mid=(ty0+ty1+1)//2
                    base=g[ty0][tx0]
                    full_top=(base!=0 and all(g[ty][tx]==base
                              for ty in range(ty0,mid)
                              for tx in range(tx0,tx1+1)))
                else:
                    full_top=False
                if not full_top:
                    _consume(g)
        else:
            # Clicking the smaller filled stencil stamps its literal shape
            # directly into the fixed target (level 2+).
            cells={(sx,sy) for sy in range(18,len(ENTRY_GRID)-1)
                   for sx in range(len(ENTRY_GRID[0]))
                   if ENTRY_GRID[sy][sx]==15}
            comps=[]
            while cells:
                p=cells.pop(); comp=[p]; stack=[p]
                while stack:
                    sx,sy=stack.pop()
                    for q in ((sx-1,sy),(sx+1,sy),(sx,sy-1),(sx,sy+1)):
                        if q in cells:
                            cells.remove(q); stack.append(q); comp.append(q)
                comps.append(comp)
            if len(comps)>=2 and x is not None and y is not None:
                small=min(comps,key=len)
                sx0,sx1=min(sx for sx,sy in small),max(sx for sx,sy in small)
                sy0,sy1=min(sy for sx,sy in small),max(sy for sx,sy in small)
                if sx0<=x<=sx1 and sy0<=y<=sy1:
                    zeros=_main_zero(ENTRY_GRID)
                    tx0=min(tx for tx,ty in zeros)
                    ty0=min(ty for tx,ty in zeros)
                    color=st.get("selected",15)
                    for sx,sy in small:
                        tx=tx0+(sx-sx0)+(sx0-tx0)
                        ty=ty0+(sy-sy0)
                        g[ty][tx]=color
                    solved=all(g[ty0+dy][tx0+dx]==ENTRY_GRID[3+dy][3+dx]
                               for dy in range(10) for dx in range(10))
                    if solved:
                        if CURRENT_LEVEL is not None and CURRENT_LEVEL>=5:
                            info["win"]=True
                        else:
                            info["level_up"]=True
    # ACTION1 is a confirmed invalid/no-op here.
    return g, info, st
