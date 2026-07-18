def _consume_bar(g):
    if len(g) <= 1:
        return
    for xx in range(len(g[1]) - 1, -1, -1):
        if g[1][xx] == 9:
            g[1][xx] = 3
            return

def _toggle_panel_component(g, x, y):
    """The five controls are disconnected colored strokes in the lower panel."""
    if not (0 <= y < len(g) and 0 <= x < len(g[0])):
        return
    if not (42 <= y <= 46 and 19 <= x <= 43):
        return
    old = g[y][x]
    if old not in (1, 5):
        return
    new = 5 if old == 1 else 1
    stack = [(x, y)]
    seen = {(x, y)}
    while stack:
        xx, yy = stack.pop()
        if not (19 <= xx <= 43 and 42 <= yy <= 46) or g[yy][xx] != old:
            continue
        g[yy][xx] = new
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q = (xx+dx, yy+dy)
            if q not in seen:
                seen.add(q)
                stack.append(q)

def step(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}
    if action == 6:
        _consume_bar(g)
        if x is not None and y is not None:
            _toggle_panel_component(g, x, y)
    return g, info
