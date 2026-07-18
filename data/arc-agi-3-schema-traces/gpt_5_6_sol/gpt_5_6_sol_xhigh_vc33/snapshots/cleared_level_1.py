import numpy as np

def is_goal(grid):
    return False

def _bands(entry):
    ys = []
    for y,row in enumerate(entry):
        if 5 in row:
            ys.append(y)
    bands = []
    if not ys:
        return bands
    a = ys[0]
    p = ys[0]
    for y in ys[1:]:
        if y != p + 1:
            bands.append((a,p))
            a = y
        p = y
    bands.append((a,p))
    return bands

def _add_meter(g):
    # Fixed-rate clock: increments 1,2,1,1, repeating (5 cells/4 turns).
    n = sum(v == 4 for v in g[0])
    amount = 2 if n % 5 == 1 else 1
    for z in range(amount):
        for x in range(len(g[0])-1, -1, -1):
            if g[0][x] == 7:
                g[0][x] = 4
                break

def _solid_boundary(row, side, marker):
    solid = (3, 4, marker)
    if side == 'left':
        x = 0
        while x < len(row) and row[x] in solid:
            x += 1
        return x
    x = 0
    while x < len(row) and row[x] not in solid:
        x += 1
    return x

def _set_wall_interval(g, y0, y1, old, new, side):
    # y1 is exclusive. Pads (9) and any other decorations are preserved.
    a = min(old,new)
    b = max(old,new)
    expanding = (new > old) if side == 'left' else (new < old)
    val_from = 0 if expanding else 3
    val_to = 3 if expanding else 0
    for y in range(y0,y1):
        for x in range(a,b):
            if g[y][x] == val_from:
                g[y][x] = val_to

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {'level_up': False, 'dead': False, 'win': False}
    if action != 6 or x is None or y is None:
        return g, info

    _add_meter(g)
    if g[y][x] != 9:
        return g, info

    bands = _bands(g)
    if not bands:
        return g, info

    # A maroon pad controls its adjacent horizontal bridge.
    bi = 0
    best = 100000
    for i,(a,b) in enumerate(bands):
        d = a-y if y < a else (y-b if y > b else 0)
        if d < best:
            best = d
            bi = i
    by0,by1 = bands[bi]
    upper0 = bands[bi-1][1]+1 if bi > 0 else 1
    upper1 = by0
    lower0 = by1+1
    lower1 = bands[bi+1][0] if bi+1 < len(bands) else len(g)

    # Marker colour is the non-background colour shared by bridge and arrow.
    bridge_vals = set()
    for yy in range(by0,by1+1):
        for v in g[yy]:
            bridge_vals.add(v)
    arrow_vals = set()
    for yy,row in enumerate(g):
        if 4 in row:
            for v in row:
                arrow_vals.add(v)
    common = [v for v in bridge_vals if v in arrow_vals and v not in (0,3,4,5,7,9)]
    marker = common[0] if common else 11

    us = (upper0 + upper1 - 1)//2
    ls = (lower0 + lower1 - 1)//2
    # Both coupled slabs face the same side. Treat arrow pixels as wall.
    side = 'left' if g[ls][0] in (3,4,marker) else 'right'
    old_upper = _solid_boundary(g[us], side, marker)
    old_lower = _solid_boundary(g[ls], side, marker)

    # Clicking upper pad transfers green from upper to lower; lower pad inverse.
    click_above = y < by0
    if side == 'left':
        lower_delta = 4 if click_above else -4
    else:
        lower_delta = -4 if click_above else 4
    new_upper = old_upper - lower_delta
    new_lower = old_lower + lower_delta
    # A transfer is blocked if its donor slab has no full 4-cell unit.
    if new_upper < 0 or new_upper > len(g[0]) or new_lower < 0 or new_lower > len(g[0]):
        return g, info

    # Save/clear any arrow riding on the controlled lower slab.
    obj = []
    for yy in range(lower0,lower1):
        for xx in range(len(g[0])):
            if g[yy][xx] in (4,marker):
                obj.append((xx,yy,g[yy][xx]))
                g[yy][xx] = 3

    _set_wall_interval(g, upper0, upper1, old_upper, new_upper, side)
    _set_wall_interval(g, lower0, lower1, old_lower, new_lower, side)

    # Maroon pads are fixed foreground.
    for yy,row in enumerate(grid):
        for xx,v in enumerate(row):
            if v == 9:
                g[yy][xx] = 9
    for xx,yy,v in obj:
        nx = xx + lower_delta
        if 0 <= nx < len(g[0]):
            g[yy][nx] = v

    bridge_x = []
    for yy in range(by0,by1+1):
        for xx,v in enumerate(g[yy]):
            if v == marker:
                bridge_x.append(xx)
    arrow_x = [xx+lower_delta for xx,yy,v in obj if v == marker]
    if bridge_x and arrow_x and min(bridge_x) == min(arrow_x):
        info['level_up'] = True
    return g, info
