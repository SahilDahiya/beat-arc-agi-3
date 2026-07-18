import numpy as np
from collections import deque

BG = 5
DOT = 13
BAR_EMPTY = 3
BAR_USED = 4

def _component(a, x, y):
    h, w = len(a), len(a[0])
    c = a[y][x]
    q = deque([(x, y)])
    seen = {(x, y)}
    while q:
        xx, yy = q.popleft()
        for nx, ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
            if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in seen and a[ny][nx] == c:
                seen.add((nx,ny)); q.append((nx,ny))
    return seen

def _control(x, y):
    """Return (track_colour, dx,dy) for a 3x3 seven-cell directional glyph."""
    a = ENTRY_GRID
    h, w = len(a), len(a[0])
    if not (0 <= x < w and 0 <= y < h):
        return None
    c = a[y][x]
    if c in (BG, DOT, 2, 3, 4):
        return None
    comp = _component(a, x, y)
    if len(comp) != 7:
        return None
    xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
    x0,x1,y0,y1 = min(xs),max(xs),min(ys),max(ys)
    if x1-x0 != 2 or y1-y0 != 2:
        return None
    cx,cy = x0+1,y0+1
    # The one open edge of the bracket-shaped glyph is opposite its direction.
    mids = {
        (-1,0):(x0,cy), (1,0):(x1,cy),
        (0,-1):(cx,y0), (0,1):(cx,y1)
    }
    missing = [d for d,p in mids.items() if p not in comp]
    if len(missing) != 1:
        return None
    mx,my = missing[0]
    return c, -mx, -my

def _target_centres(a):
    h,w = len(a),len(a[0])
    out=[]
    for y in range(1,h-1):
        for x in range(1,w-1):
            if a[y][x] == BG and all(a[y+dy][x+dx] == DOT for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))):
                out.append((x,y))
    return out

def _move_track(g, colour, dx, dy):
    h,w=len(g),len(g[0])
    candidates=[]
    for y in range(h):
        for x in range(w):
            if g[y][x] == DOT:
                n=sum(0 <= x+ax < w and 0 <= y+ay < h and g[y+ay][x+ax] == colour
                      for ax,ay in ((1,0),(-1,0),(0,1),(0,-1)))
                if n >= 2:
                    candidates.append((x,y,n))
    if not candidates:
        return False
    x,y,_=max(candidates,key=lambda z:z[2])
    g[y][x]=colour
    # Controls advance the dot by one 3-cell tile, extending a 3-wide track.
    for k in range(1,5):
        bx,by=x+dx*k,y+dy*k
        for off in (-1,0,1):
            xx,yy=bx-dy*off,by+dx*off
            if 0 <= xx < w and 0 <= yy < h and g[yy][xx] != DOT:
                # Fixed hollow-diamond target arms persist when the track arrives.
                g[yy][xx]=colour
    nx,ny=x+3*dx,y+3*dy
    if 0 <= nx < w and 0 <= ny < h:
        g[ny][nx]=DOT
    return True

def _use_budget(g, amount=1):
    # A 50-turn counter is rendered across the 64-pixel bottom row using
    # nearest-integer scaling, hence some single clicks visibly add 2 cells.
    width=len(g[0])
    used=sum(v == BAR_USED for v in g[-1])
    turn=int(used * 50.0 / width + 0.5)
    wanted=int((turn + 1) * width / 50.0 + 0.5)
    for _ in range(max(0,wanted-used)):
        for xx in range(width-1,-1,-1):
            if g[-1][xx] == BAR_EMPTY:
                g[-1][xx]=BAR_USED
                break

def _all_targets_reached(g):
    centres=_target_centres(ENTRY_GRID)
    if not centres:
        return False
    return all(g[y][x] == DOT for x,y in centres)

def step(grid, action, x=None, y=None):
    g=[row[:] for row in grid]
    info={"level_up":False,"dead":False,"win":False}
    if action != 6:
        return g,info
    ctl=_control(x,y)
    valid=False
    extra_tick=False
    if ctl is not None:
        colour,dx,dy=ctl
        # Besides the ordinary click tick, advancing a track adds an extra
        # bar tick on movement numbers 1,5,9,... (each four 3-cell tiles).
        a=ENTRY_GRID
        starts=[]
        currents=[]
        for yy in range(len(a)):
            for xx in range(len(a[0])):
                if a[yy][xx] == DOT:
                    n=sum(0 <= xx+ax < len(a[0]) and 0 <= yy+ay < len(a) and
                          a[yy+ay][xx+ax] == colour
                          for ax,ay in ((1,0),(-1,0),(0,1),(0,-1)))
                    if n >= 2:
                        starts.append((xx,yy))
                if g[yy][xx] == DOT:
                    n=sum(0 <= xx+ax < len(a[0]) and 0 <= yy+ay < len(a) and
                          g[yy+ay][xx+ax] == colour
                          for ax,ay in ((1,0),(-1,0),(0,1),(0,-1)))
                    if n >= 2:
                        currents.append((xx,yy))
        if starts and currents:
            sx,sy=starts[0]; cx,cy=currents[0]
            moved=(abs(cx-sx)+abs(cy-sy))//3
            extra_tick=(moved % 4 == 0)
        valid=_move_track(g,colour,dx,dy)
    _use_budget(g,2 if valid and extra_tick else 1)
    if valid and _all_targets_reached(g):
        info["level_up"]=True
    return g,info

def is_goal(grid):
    return _all_targets_reached(grid)
