def _component(grid, x, y, color=None):
    h, w = len(grid), len(grid[0])
    if not (0 <= x < w and 0 <= y < h):
        return []
    if color is None:
        color = grid[y][x]
    out, stack, seen = [], [(x,y)], {(x,y)}
    while stack:
        xx, yy = stack.pop()
        if not (0 <= xx < w and 0 <= yy < h) or grid[yy][xx] != color:
            continue
        out.append((xx,yy))
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q=(xx+dx,yy+dy)
            if q not in seen:
                seen.add(q); stack.append(q)
    return out

def _consume_bar(g):
    if len(g) > 1:
        for xx in range(len(g[1])-1, -1, -1):
            if g[1][xx] == 9:
                g[1][xx] = 3
                return

def _small_controls(grid):
    """Return all 3-pixel control strokes (each half of a T control)."""
    h,w=len(grid),len(grid[0])
    seen=set(); ans=[]
    for y in range(h):
        for x in range(w):
            if (x,y) in seen or grid[y][x] not in (1,5):
                continue
            c=_component(grid,x,y)
            seen.update(c)
            if len(c)==3:
                ans.append((grid[y][x],c))
    return ans

def step(grid, action, x=None, y=None):
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    if action != 6:
        return g,info

    # Determine the clicked object before changing the rendered counter.
    clicked = []
    clicked_color = None
    if x is not None and y is not None and 0 <= y < len(grid) and 0 <= x < len(grid[0]):
        clicked_color=grid[y][x]
        clicked=_component(grid,x,y)

    # L0 completes when RUN (the 69-pixel color-9 circle) is pressed with
    # every small two-part program stroke set to color 5.
    if CURRENT_LEVEL == 0 and clicked_color == 9 and len(clicked) == 69:
        ctrls=_small_controls(grid)
        if ctrls and all(col==5 for col,c in ctrls):
            info["level_up"]=True

    _consume_bar(g)

    # Clicking either disconnected 3-pixel half of a control flips 1 <-> 5.
    if clicked_color in (1,5) and len(clicked)==3:
        new=5 if clicked_color==1 else 1
        for xx,yy in clicked:
            g[yy][xx]=new

    return g,info
