import numpy as np


def _components(a, excluded=(4,)):
    h, w = a.shape
    seen = set()
    out = []
    for y in range(h):
        for x in range(w):
            v = int(a[y, x])
            if v in excluded or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            cells = []
            while stack:
                xx, yy = stack.pop()
                cells.append((xx, yy))
                for nx, ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in seen and int(a[ny,nx]) == v:
                        seen.add((nx,ny)); stack.append((nx,ny))
            out.append((v, cells))
    return out


def _layout():
    a = np.array(ENTRY_GRID, dtype=int)
    comps = _components(a)
    tiles = []
    small = []
    large = []
    for v, cells in comps:
        xs = [p[0] for p in cells]; ys = [p[1] for p in cells]
        box = (min(xs), min(ys), max(xs), max(ys))
        bw, bh = box[2]-box[0]+1, box[3]-box[1]+1
        if len(cells) == 16 and bw == 4 and bh == 4:
            tiles.append((box[0], box[1], v))
        elif len(cells) == 4 and bw == 2 and bh == 2:
            small.append((box, v))
        elif len(cells) > 16 and bw > 1 and bh > 1:
            large.append((box, v, len(cells)))
    xs = sorted(set(x for x,y,v in tiles))
    ys = sorted(set(y for x,y,v in tiles))
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    pos = {(x,y):v for x,y,v in tiles}
    order = []
    for x in xs:
        if (x,ymin) in pos: order.append((x,ymin))
    for y in ys[1:]:
        if (xmax,y) in pos: order.append((xmax,y))
    for x in reversed(xs[:-1]):
        if (x,ymax) in pos: order.append((x,ymax))
    for y in reversed(ys[1:-1]):
        if (xmin,y) in pos: order.append((xmin,y))

    # The four small corner marks identify the target tile and their color
    # identifies the unique marker tile that must be rotated into it.
    best = None
    for tx, ty in order:
        near = [(b,v) for b,v in small
                if b[2] >= tx-3 and b[0] <= tx+6 and
                   b[3] >= ty-3 and b[1] <= ty+6]
        if best is None or len(near) > best[0]:
            best = (len(near), (tx,ty), near)
    target = best[1]
    marker = best[2][0][1] if best[2] else pos[target]

    # The two wide components outside the tile rectangle are arrow buttons.
    left = right = None
    for box,v,n in large:
        if box[3] < ymin or box[1] > ymax+3: continue
        if box[2] < xmin:
            left = box
        elif box[0] > xmax+3:
            right = box
    return order, target, marker, left, right


def _inside(box, x, y):
    return box is not None and x is not None and y is not None and box[0] <= x <= box[2] and box[1] <= y <= box[3]


def _goal(grid):
    order, target, marker, left, right = _layout()
    x,y = target
    return int(grid[y][x]) == marker


def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action != 6:
        return g, info
    order, target, marker, left, right = _layout()
    direction = 0
    if _inside(left, x, y): direction = -1   # each position receives next clockwise tile
    if _inside(right, x, y): direction = 1
    if direction == 0:
        return g, info

    old = [int(grid[py][px]) for px,py in order]
    n = len(order)
    for i,(px,py) in enumerate(order):
        val = old[(i - direction) % n]
        for yy in range(py,py+4):
            for xx in range(px,px+4):
                g[yy][xx] = val

    # Each effective arrow press consumes one five-pixel unit of the left meter.
    used = 0
    for yy in range(len(g)):
        if g[yy][0] == 14 and used < 5:
            g[yy][0] = 5
            used += 1

    if _goal(g):
        if CURRENT_LEVEL is not None and CURRENT_LEVEL >= 7:
            info["win"] = True
        else:
            info["level_up"] = True
    return g, info


def is_goal(grid):
    return _goal(grid)
