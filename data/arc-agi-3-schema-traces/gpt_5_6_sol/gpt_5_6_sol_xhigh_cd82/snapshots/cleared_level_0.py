def _consume(g):
    # Effective moves consume the rightmost remaining cell of the color-4
    # action bar along the last row.
    for xx in range(len(g[0]) - 1, -1, -1):
        if g[-1][xx] == 4:
            g[-1][xx] = 5
            return

def _turn_from_flat(g, turn_right=False):
    # Render the selected open rectangular tray after its first horizontal
    # turn. ACTION4 is the horizontal mirror of ACTION3.
    pts = [(x, y) for y in range(18, len(g)-1) for x in range(len(g[0]))
           if g[y][x] == 2]
    if not pts:
        return False
    minx = min(x for x,y in pts)
    miny = min(y for x,y in pts)
    maxx = max(x for x,y in pts)
    maxy = max(y for x,y in pts)
    if maxx-minx != 13 or maxy-miny != 8:
        return False
    for y in range(18, len(g)-1):
        for x in range(len(g[0])):
            if g[y][x] in (2, 15):
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
            for x in range(ax-k+2, ax+k-1): add(x, y, 15)
            for x in range(ax+k-1, ax+k+1): add(x, y, 2)
        elif 7 <= k <= 10:
            for x in range(ax-k, ax-k+2): add(x, y, 2)
            for x in range(ax-k+2, ax+12-k): add(x, y, 15)
        elif 11 <= k <= 14:
            s = ax + k - 20
            for x in range(s, s+2): add(x, y, 2)
            for x in range(s+2, ax+12-k): add(x, y, 15)
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

def _turn_to_side(g, west=True):
    # From an upper diagonal position, ACTION2 moves the open stencil to
    # the side of the fixed target, aimed inward.
    zeros = [(x,y) for y in range(18, len(ENTRY_GRID)-1)
             for x in range(len(ENTRY_GRID[0])) if ENTRY_GRID[y][x] == 0]
    if not zeros:
        return
    x0, x1 = min(x for x,y in zeros), max(x for x,y in zeros)
    y0, y1 = min(y for x,y in zeros), max(y for x,y in zeros)
    # Preserve the currently selected fill color.
    vals = [g[y][x] for y in range(18, len(g)-1)
            for x in range(len(g[0])) if g[y][x] in (0,15)
            and not (x0 <= x <= x1 and y0 <= y <= y1)]
    fill = 15 if 15 in vals else 0
    for y in range(18, len(g)-1):
        for x in range(len(g[0])):
            if g[y][x] in (2,15) and not (
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

def _turn_to_lower_diag(g, west=True, fill=15):
    # Side -> lower diagonal: vertical mirror of the upper diagonal stencil
    # around the fixed target's horizontal centerline.
    zeros = [(x,y) for y in range(18, len(ENTRY_GRID)-1)
             for x in range(len(ENTRY_GRID[0])) if ENTRY_GRID[y][x] == 0]
    reds = [(x,y) for y in range(18, len(ENTRY_GRID)-1)
            for x in range(len(ENTRY_GRID[0])) if ENTRY_GRID[y][x] == 2]
    if not zeros or not reds:
        return
    x0,x1 = min(x for x,y in zeros),max(x for x,y in zeros)
    y0,y1 = min(y for x,y in zeros),max(y for x,y in zeros)
    minx,maxx = min(x for x,y in reds),max(x for x,y in reds)
    miny = min(y for x,y in reds)
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            if not (x0 <= x <= x1 and y0 <= y <= y1) and g[y][x] in (2,15):
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
    zeros=[(x,y) for y in range(18,len(ENTRY_GRID)-1)
           for x in range(len(ENTRY_GRID[0])) if ENTRY_GRID[y][x]==0]
    if not zeros: return
    x0,x1=min(x for x,y in zeros),max(x for x,y in zeros)
    y0,y1=min(y for x,y in zeros),max(y for x,y in zeros)
    for y in range(18,len(g)-1):
        for x in range(len(g[0])):
            if not (x0<=x<=x1 and y0<=y<=y1) and g[y][x] in (2,15):
                g[y][x]=5
    sy=y0+y1
    for y in range(18,len(ENTRY_GRID)-1):
        for x in range(len(ENTRY_GRID[0])):
            v=ENTRY_GRID[y][x]
            if v in (2,15):
                yy=sy-y
                if 18<=yy<len(g)-1:
                    g[yy][x]=2 if v==2 else fill

def _orientation(g):
    pts = [(x,y) for y in range(18, len(g)-1) for x in range(len(g[0]))
           if g[y][x] == 2]
    ent = [(x,y) for y in range(18, len(ENTRY_GRID)-1)
           for x in range(len(ENTRY_GRID[0])) if ENTRY_GRID[y][x] == 2]
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

def _restore_flat(g):
    # Restore only the selected color-2/white object from the entry layout;
    # fixed black objects and UI remain untouched.
    for y in range(18, len(g)-1):
        for x in range(len(g[0])):
            if g[y][x] in (2, 15):
                g[y][x] = 5
    for y in range(18, len(g)-1):
        for x in range(len(g[0])):
            if ENTRY_GRID[y][x] in (2, 15):
                g[y][x] = ENTRY_GRID[y][x]

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
            _turn_from_flat(g, False)
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "right":
            _restore_flat(g)
            if st.get("down", 0) == 0:
                _consume(g)
    elif action == 4:
        if ori == "flat":
            _turn_from_flat(g, True)
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "left":
            _restore_flat(g)
            if st.get("down", 0) == 0:
                _consume(g)
        elif ori == "southwest":
            _turn_to_south(g, st.get("selected",15))
            _consume(g)
    elif action == 1:
        # Vertical/depth state is visually hidden. From neutral, ACTION1
        # enters the opposite mode and consumes one bar cell. From the
        # ACTION2 mode it changes mode without another visible bar change.
        if all(v == 4 for v in g[-1]):
            _consume(g)
        st["down"] = -1
    elif action == 2:
        if ori == "left":
            _turn_to_side(g, True)
        elif ori == "right":
            _turn_to_side(g, False)
        elif ori == "west":
            _turn_to_lower_diag(g, True, st.get("selected",15))
            _consume(g)
        elif ori == "east":
            _turn_to_lower_diag(g, False, st.get("selected",15))
            _consume(g)
        else:
            _consume(g)
        st["down"] = 1
    elif action == 5:
        zeros = [(x,y) for y in range(18, len(ENTRY_GRID)-1)
                 for x in range(len(ENTRY_GRID[0])) if ENTRY_GRID[y][x] == 0]
        if zeros:
            x0, x1 = min(x for x,y in zeros), max(x for x,y in zeros)
            y0, y1 = min(y for x,y in zeros), max(y for x,y in zeros)
            if all(g[y][x] == 0 for y in range(y0,y1+1)
                   for x in range(x0,x1+1)):
                mid = (y0+y1+1)//2
                if st.get("selected", 15) == 0:
                    # Applying black to an all-black target is invalid.
                    pass
                elif ori == "south":
                    # Stamping from below paints the lower half: level target.
                    for y in range(mid, y1+1):
                        for x in range(x0,x1+1):
                            g[y][x]=15
                    info["level_up"]=True
                elif ori == "left":
                    span = x1 - x0
                    for y in range(y0, y1+1):
                        for x in range(x0, x1+1):
                            if (x-x0) + (y-y0) <= span:
                                g[y][x] = 15
                elif ori == "right":
                    span = x1 - x0
                    for y in range(y0, y1+1):
                        for x in range(x0, x1+1):
                            if (x1-x) + (y-y0) <= span:
                                g[y][x] = 15
                else:
                    # Up/down hidden modes do not change the flat mask:
                    # the selected color still occupies the upper half.
                    for y in range(y0, mid):
                        for x in range(x0, x1+1):
                            g[y][x] = 15
                if (st.get("selected", 15) != 0
                        and ((ori == "flat" and st.get("down", 0) == 0)
                             or (ori in ("left","right")
                                 and st.get("down", 0) < 0))):
                    _consume(g)
            elif st.get("selected", 15) == 0 and any(
                    g[y][x] == 15 for y in range(y0,y1+1)
                    for x in range(x0,x1+1)):
                # A black stamp removes the existing white stamped region.
                for y in range(y0, y1+1):
                    for x in range(x0, x1+1):
                        g[y][x] = 0
                _consume(g)
    elif action == 6:
        # Click the black or white color button in the top-right UI.
        # The actual button bands are y=2..6; centers are around x=39/45.
        if x is not None and y is not None and 2 <= y <= 6 and 37 <= x <= 41:
            if st.get("selected", 15) != 0:
                st["selected"] = 0
                # Recolor the selected source (all playfield white outside
                # the fixed target) and move the selector underline left.
                target = {(xx,yy) for yy in range(18, len(ENTRY_GRID)-1)
                          for xx in range(len(ENTRY_GRID[0]))
                          if ENTRY_GRID[yy][xx] == 0}
                pristine_target = all(g[yy][xx] == 0 for xx,yy in target)
                for yy in range(18, len(g)-1):
                    for xx in range(len(g[0])):
                        if g[yy][xx] == 15 and (xx,yy) not in target:
                            g[yy][xx] = 0
                for xx in range(41, 46):
                    g[7][xx] = 3
                for xx in range(35, 40):
                    g[7][xx] = 0
                if pristine_target:
                    _consume(g)
    # ACTION1 is a confirmed invalid/no-op here.
    return g, info, st
