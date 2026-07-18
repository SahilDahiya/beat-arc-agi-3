import numpy as np

def is_goal(grid):
    # Planning goals are emitted through info.level_up on marker alignment.
    return False

def _layout():
    e = ENTRY_GRID
    # Four-row horizontal bridge is the run containing colour 5.
    ys = [y for y,row in enumerate(e) if 5 in row]
    return min(ys), max(ys)

def _add_meter(g, amount):
    # Yellow (4) consumes the orange (7) bar from right to left.
    for _ in range(amount):
        inds = [x for x,v in enumerate(g[0]) if v == 7]
        if inds:
            g[0][inds[-1]] = 4

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6 or x is None or y is None:
        return g, info

    # The meter advances at a fixed 5/4 cells per turn: observed
    # increments repeat 1,2,1,1 (equivalently +2 when length mod 5 is 1).
    n = sum(v == 4 for v in g[0])
    _add_meter(g, 2 if n % 5 == 1 else 1)

    by0, by1 = _layout()
    # The two maroon pads on the far right are the actual controls.
    on_pad = (g[y][x] == 9)
    if not on_pad:
        return g, info

    lower_delta = 4 if y < by0 else -4

    # Current straight green boundaries, sampled away from decorations.
    sample_top = 1
    sample_lower = by1 + 8
    old_top = len(g[0])
    for i,v in enumerate(g[sample_top]):
        if v != 3:
            old_top = i
            break
    old_lower = len(g[0])
    for i,v in enumerate(g[sample_lower]):
        if v != 3:
            old_lower = i
            break
    new_top = old_top - lower_delta
    new_lower = old_lower + lower_delta

    # Coupled upper wall.
    if new_top < old_top:
        for yy in range(1, by0):
            for xx in range(new_top, old_top):
                if g[yy][xx] == 3:
                    g[yy][xx] = 0
    else:
        for yy in range(1, by0):
            for xx in range(old_top, new_top):
                if g[yy][xx] == 0:
                    g[yy][xx] = 3

    # Save and clear the yellow/light-gray arrow embedded in lower wall.
    obj = []
    for yy in range(by1 + 1, len(g)):
        for xx in range(len(g[0])):
            if g[yy][xx] in (4, 11):
                obj.append((xx, yy, g[yy][xx]))
                g[yy][xx] = 3

    # Coupled lower wall.
    if new_lower < old_lower:
        for yy in range(by1 + 1, len(g)):
            for xx in range(new_lower, old_lower):
                if g[yy][xx] == 3:
                    g[yy][xx] = 0
    else:
        for yy in range(by1 + 1, len(g)):
            for xx in range(old_lower, new_lower):
                if g[yy][xx] == 0:
                    g[yy][xx] = 3

    # Fixed maroon pads remain fixed, and the arrow rides with its wall.
    for yy,row in enumerate(ENTRY_GRID):
        for xx,v in enumerate(row):
            if v == 9:
                g[yy][xx] = 9
    for xx,yy,v in obj:
        nx = xx + lower_delta
        if 0 <= nx < len(g[0]):
            g[yy][nx] = v

    # Goal: align the arrow's light-gray vertical marker to bridge marker.
    bridge_x = sorted({xx for yy in range(by0, by1+1)
                       for xx,v in enumerate(g[yy]) if v == 11})
    arrow_x = sorted({xx for xx,yy,v in obj if v == 11})
    arrow_x = [xx + lower_delta for xx in arrow_x]
    if bridge_x and arrow_x and min(bridge_x) == min(arrow_x):
        info["level_up"] = True
    return g, info
