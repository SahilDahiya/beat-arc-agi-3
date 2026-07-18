# World model for ARC3 bp35
# numpy is preloaded by the framework.

PLAYER = np.array([
    [5,5,9,5,5],
    [5,9,9,11,5],
    [5,9,9,11,5],
    [5,5,9,5,5],
    [-1,5,5,5,-1],
], dtype=int)
PLAYER_LEFT = np.fliplr(PLAYER).copy()
PMASK = PLAYER >= 0

def init_state(entry_grid):
    return {"undo": [], "scroll": 0}

def _player_origin(g):
    p = np.argwhere((g == 9) | (g == 11))
    if len(p) < 1:
        return None
    # Coloured core always occupies relative x=1..3, y=0..3.
    return int(p[:,1].min() - 1), int(p[:,0].min())

def _facing(g):
    b = np.argwhere(g == 11)
    n = np.argwhere((g == 9) | (g == 11))
    if len(b) < 1 or len(n) < 1:
        return 1
    return -1 if float(b[:,1].mean()) < float(n[:,1].mean()) else 1

def _tick(g):
    z = np.where(g[-1] == 0)[0]
    if len(z):
        g[-1, int(z[0])] = 15

def _erase(g, ox, oy):
    for yy in range(5):
        for xx in range(5):
            if PMASK[yy,xx] and 0 <= oy+yy < 63 and 0 <= ox+xx < 64:
                g[oy+yy, ox+xx] = 10

def _fits(g, ox, oy):
    if ox < 0 or ox+5 > 64 or oy < 0 or oy+5 > 63:
        return False
    for yy in range(5):
        for xx in range(5):
            if PMASK[yy,xx] and g[oy+yy,ox+xx] != 10:
                return False
    return True

def _draw(g, ox, oy, face=1):
    p = PLAYER if face >= 0 else PLAYER_LEFT
    for yy in range(5):
        for xx in range(5):
            if PMASK[yy,xx]:
                g[oy+yy,ox+xx] = int(p[yy,xx])

def _wall_screen():
    w = np.full((63,64), 5, dtype=int)
    for yy in range(63):
        r = yy % 6
        if r == 1:
            w[yy, 2:64:6] = 3
        elif r == 4:
            w[yy, 1:64:6] = 3
        elif r == 5:
            w[yy, 4:64:6] = 3
    return w

def _first_reveal():
    # The first 18 rows immediately above the entry viewport.  They are
    # composed from the same room motifs and periodic wall texture in ENTRY_GRID.
    e = np.array(ENTRY_GRID, dtype=int)
    t = np.empty((18,64), dtype=int)
    t[0:6] = e[24:30]
    mid = _wall_screen()[6:12].copy()
    # Destructible e-brick tiles continue in the same three columns as
    # entry's top ledge (including their distinctive 3-valued tile edging).
    mid[:,12:30] = e[0:6,12:30]
    t[6:12] = mid
    t[12] = _wall_screen()[12]
    t[13:18] = e[1:6]
    return t

def _second_reveal():
    # World rows -42..-19, exposed by the first drilled ceiling.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:24].copy()
    t[1:12,13:54] = 10
    t[12:19,13:24] = 10
    t[12:19,43:54] = 10
    # Three adjacent e-bricks on a short floating ledge.
    t[12:19,24:43] = e[12:19,30:49]
    t[19:24,13:54] = 10
    return t

def _third_reveal():
    # World rows -60..-43: the first visible goal room.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:18].copy()
    t[1:12,13:54] = 10
    # Diamond-shaped colour-7 goal, framed like the player, at origin (19,1).
    goal = np.array([
        [5,5,7,5,5],
        [5,7,7,7,5],
        [5,5,7,5,5],
        [-1,5,5,5,-1],
    ], dtype=int)
    for yy in range(4):
        for xx in range(5):
            if goal[yy,xx] >= 0:
                t[1+yy,19+xx] = int(goal[yy,xx])
    # Three e-bricks in the ceiling below this room.
    t[12:18,30:49] = e[12:18,30:49]
    return t

def _reveal(scroll, n):
    if scroll == 0 and n == 18:
        return _first_reveal()
    if scroll == 18 and n == 24:
        return _second_reveal()
    if scroll == 42 and n == 18:
        return _third_reveal()
    # Provisional continuation, refined whenever another section is exposed.
    return _wall_screen()[:n].copy()

def _finish_float(g, ox, oy, scroll, face=1):
    ny = oy
    while _fits(g, ox, ny-6):
        ny -= 6
    rise = oy - ny
    _draw(g, ox, ny, face)
    if rise:
        hud = g[63].copy()
        old = g[:63].copy()
        g[rise:63] = old[:63-rise]
        g[:rise] = _reveal(scroll, rise)
        g[63] = hud
        scroll += rise
    return g, scroll

def _move_and_float(g, dx, scroll):
    pos = _player_origin(g)
    if pos is None:
        return g, scroll
    ox, oy = pos
    _erase(g, ox, oy)
    nx = ox + dx
    if not _fits(g, nx, oy):
        nx = ox
    return _finish_float(g, nx, oy, scroll, 1 if dx > 0 else -1)

def _click_and_float(g, x, y, scroll):
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return g, scroll
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy)
    cx, cy = (int(x)//6)*6, (int(y)//6)*6
    # Confirmed click: an e-brick tile is drilled into a five-pixel-wide
    # vertical passage, clearing both horizontal seams around it.
    if np.any(g[max(0,cy):min(63,cy+6), max(0,cx):min(64,cx+6)] == 14):
        # Removing an e tile opens its 5x5 interior.  Each shared seam also
        # vanishes exactly when the neighbouring logical cell is already open;
        # seams against another solid/e tile remain.
        g[max(0,cy+1):min(63,cy+6), max(0,cx+1):min(64,cx+6)] = 10
        def open_at(px, py):
            return 0 <= px < 64 and 0 <= py < 63 and g[py,px] == 10
        left = open_at(cx-3, cy+3)
        right = open_at(cx+9, cy+3)
        top = open_at(cx+3, cy-3)
        bottom = open_at(cx+3, cy+9)
        if left:
            g[max(0,cy+1):min(63,cy+6), cx] = 10
        if right and cx+6 < 64:
            g[max(0,cy+1):min(63,cy+6), cx+6] = 10
        if top:
            g[cy, max(0,cx+1):min(64,cx+6)] = 10
        if bottom and cy+6 < 63:
            g[cy+6, max(0,cx+1):min(64,cx+6)] = 10
        # A wall-grid intersection disappears when both incident seams open.
        if left and top: g[cy,cx] = 10
        if left and bottom and cy+6 < 63: g[cy+6,cx] = 10
        if right and top and cx+6 < 64: g[cy,cx+6] = 10
        if right and bottom and cx+6 < 64 and cy+6 < 63: g[cy+6,cx+6] = 10
    return _finish_float(g, ox, oy, scroll, face)

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid, dtype=int).copy()
    undo = list(state.get("undo", []))
    scroll = int(state.get("scroll", 0))
    info = {"level_up": False, "dead": False, "win": False}
    if action == 7:
        if undo:
            ent = undo.pop()
            g = np.array(ent[0], dtype=int)
            scroll = int(ent[1])
        return g.tolist(), info, {"undo": undo, "scroll": scroll}
    if action in (3,4):
        undo.append((np.array(grid,dtype=int).tolist(), scroll))
        g, scroll = _move_and_float(g, -6 if action == 3 else 6, scroll)
        _tick(g)
    elif action == 6:
        undo.append((np.array(grid,dtype=int).tolist(), scroll))
        g, scroll = _click_and_float(g, x, y, scroll)
        _tick(g)
    return g.tolist(), info, {"undo": undo, "scroll": scroll}
