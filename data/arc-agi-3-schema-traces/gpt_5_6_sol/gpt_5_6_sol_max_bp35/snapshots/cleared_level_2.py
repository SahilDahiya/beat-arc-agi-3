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
    # Values hidden beneath the rendered player sprite. Initially it floats in
    # plain open space; later this preserves a traversed sparse c gate.
    return {"undo": [], "scroll": 0, "under": [[10]*5 for _ in range(5)]}

def _player_origin(g):
    # Colour 9 is unique to the player core; later levels contain unrelated
    # colour-b objects, so b alone must not be used for localisation.
    p = np.argwhere(g == 9)
    if len(p) < 1:
        return None
    mnx, oy = int(p[:,1].min()), int(p[:,0].min())
    # With a left-facing player the b pixels sit one column left of the
    # leftmost 9; with a right-facing player they sit two columns right.
    left_b = mnx > 0 and np.any(g[oy:oy+4, mnx-1] == 11)
    ox = mnx - 2 if left_b else mnx - 1
    return ox, oy

def _facing(g):
    pos = _player_origin(g)
    if pos is None:
        return 1
    ox, oy = pos
    b = np.argwhere(g[oy:oy+4, ox:ox+5] == 11)
    if len(b) < 1:
        return 1
    return -1 if float(b[:,1].mean()) < 2.0 else 1

def _tick(g):
    z = np.where(g[-1] == 0)[0]
    if len(z):
        g[-1, int(z[0])] = 15

def _erase(g, ox, oy, under=None):
    u = np.full((5,5), 10, dtype=int) if under is None else np.array(under,dtype=int)
    for yy in range(5):
        for xx in range(5):
            if PMASK[yy,xx] and 0 <= oy+yy < 63 and 0 <= ox+xx < 64:
                g[oy+yy, ox+xx] = int(u[yy,xx])

def _capture_under(g, ox, oy):
    u = np.full((5,5), 10, dtype=int)
    for yy in range(5):
        for xx in range(5):
            if PMASK[yy,xx] and 0 <= oy+yy < 63 and 0 <= ox+xx < 64:
                u[yy,xx] = int(g[oy+yy,ox+xx])
    return u.tolist()

def _fits(g, ox, oy):
    if ox < 0 or ox+5 > 64 or oy < 0 or oy+5 > 63:
        return False
    for yy in range(5):
        for xx in range(5):
            # Sparse colour-c gate cores are traversable; their dense
            # shell still blocks via its surrounding 5/3 frame.
            if PMASK[yy,xx] and g[oy+yy,ox+xx] not in (10,12):
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

def _l1_reveal1():
    e = np.array(ENTRY_GRID, dtype=int)
    t = e[24:30].copy()
    t[:,37:54] = 10
    return t

def _l1_reveal2():
    # 42 rows above the first six-row reveal, entered via the safe right shaft.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:42].copy()
    # Two single e bricks stacked at c5.
    t[0:6,30:36] = e[24:30,12:18]
    t[6:12,30:36] = e[24:30,12:18]
    # Upper room: open left side beneath three right-side f hazards.
    t[13:19,13:36] = 10
    t[19:30,13:54] = 10
    t[12:19,36:55] = e[6:13,12:31]
    t[13:19,36] = 10  # seam against the open left room
    # Next ceiling: one safe-left e and three hazardous-right e choices.
    t[30:36,12:18] = e[24:30,12:18]
    t[30:36,36:54] = e[24:30,12:30]
    # Current lower barrier: e c2..c5, open c6..c8.
    t[36:42,12:36] = e[30:36,12:36]
    t[37:42,37:54] = 10
    return t

def _l1_reveal3():
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:24].copy()
    t[1:6,13:54] = 10
    t[0,18:25] = 10
    for xx in (30,36,42,48):
        t[0,xx] = 10
    # Three e bricks in the next ceiling.
    t[6:12,12:30] = e[24:30,12:30]
    # Wide room with one far-right f hazard.
    t[13:19,13:49] = 10
    t[12:19,48:55] = e[6:13,12:19]
    t[13:19,48] = 10
    t[13:19,54] = 5
    t[19:24,13:54] = 10
    return t

def _l1_reveal4():
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:6].copy()
    dev = e[7:12,13:18]
    for c in (2,4,5,6,7,8):
        t[1:6,6*c+1:6*c+6] = dev
    t[1:6,18:25] = 10
    for xx in (30,36,42,48):
        t[1:6,xx] = 10
    return t

def _l1_reveal5():
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:18].copy()
    cell = e[24:30,12:18]
    t[0:6,18:24] = cell
    t[0:6,48:54] = cell
    t[6:12,18:54] = e[24:30,12:48]
    t[12:18,18:24] = cell
    return t

def _l1_reveal6():
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:18].copy()
    t[0:7,31:54] = 10
    t[1:7,12:31] = e[7:13,12:31]
    t[1:7,30] = 10
    t[7:12,13:54] = 10
    cell = e[24:30,12:18]
    t[12:18,18:24] = cell
    t[12:18,48:54] = cell
    return t

def _l1_reveal7():
    t = _wall_screen()[:6].copy()
    t[1:6,31:54] = 10
    t[0,31:42] = 10
    return t

def _l1_reveal8():
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:6].copy()
    t[1:6,13:42] = 10
    t[0:6,42:54] = e[24:30,12:24]
    return t

def _l1_reveal9():
    return np.array(ENTRY_GRID, dtype=int)[24:30].copy()

def _l1_reveal10():
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:24].copy()
    t[13:19,13:37] = 10
    dev = e[7:13,13:18]
    for c in (6,7,8):
        t[13:19,6*c+1:6*c+6] = dev
    for xx in (36,42,48):
        t[13:19,xx] = 10
    # Framed goal in safe c5, immediately left of the hazards.
    goal = np.array([
        [5,5,7,5,5],
        [5,7,7,7,5],
        [5,5,7,5,5],
        [-1,5,5,5,-1],
    ], dtype=int)
    for yy in range(4):
        for xx in range(5):
            if goal[yy,xx] >= 0:
                t[13+yy,31+xx] = int(goal[yy,xx])
    t[19:24,13:54] = 10
    return t

def _l2_reveal1():
    # First room above L2: two closed c gates, a broad chamber, then a
    # four-device f hazard row with a safe far-left shaft.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:24].copy()
    t[1:7,19:30] = 10
    t[0:7,43:54] = 10
    cell = e[37:42,30:37]
    for cx in (30,36):
        t[1:6,cx:cx+7] = cell
    t[7:12,13:54] = 10
    t[12:19,13:18] = 10
    t[12:19,43:54] = 10
    t[19:24,13:19] = 10
    t[19:24,42:54] = 10
    for ox in (19,25,31,37):
        t[19:23,ox:ox+5] = 5
        t[19:23,ox+1:ox+4] = 15
        t[23,ox:ox+5] = np.array([5,11,0,11,5])
    t[19:24,24] = 10
    t[19:24,30] = 10
    t[19:24,36] = 10
    return t

def _l2_reveal2():
    # Safe-left shaft opens into a broad room. Above it, only the right side
    # continues, beneath two f devices and two already-open c gates.
    t = _wall_screen()[:30].copy()
    t[1:12,13:54] = 10
    t[0,25:42] = 10
    t[12:19,43:54] = 10
    t[19:25,42:54] = 10
    for ox in (31,37):
        t[19:23,ox:ox+5] = 5
        t[19:23,ox+1:ox+4] = 15
        t[23,ox:ox+5] = np.array([5,11,0,11,5])
    t[19:25,36] = 10
    t[25:30,31:54] = 10
    for cx in (30,36):
        for px, py in ((cx+2,26),(cx+4,26),(cx+3,27),
                       (cx+2,28),(cx+4,28)):
            t[py,px] = 12
    return t

def _l2_reveal3():
    # One-cell rise: two closed left gates and three sparse gates across the
    # open middle, forming the next switchback ceiling.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:6].copy()
    t[:,25:42] = 10
    cell = e[37:42,30:37]
    for cx in (12,18):
        t[1:6,cx:cx+7] = cell
    for cx in (24,30,36):
        for px, py in ((cx+2,2),(cx+4,2),(cx+3,3),
                       (cx+2,4),(cx+4,4)):
            t[py,px] = 12
    return t

def _l2_reveal4():
    # Safe-right rise reveals a switchback to the left, three middle hazards,
    # two stacked c gates, and the eventual goal in c7.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:30].copy()
    t[1:12,13:54] = 10
    cell = e[37:42,30:37]
    t[1:6,30:37] = cell
    t[7:12,30:37] = cell
    t[6,30:37] = 5
    goal = np.array([
        [5,5,7,5,5],
        [5,7,7,7,5],
        [5,5,7,5,5],
        [-1,5,5,5,-1],
    ], dtype=int)
    for yy in range(4):
        for xx in range(5):
            if goal[yy,xx] >= 0:
                t[1+yy,43+xx] = int(goal[yy,xx])
    t[12:19,13:24] = 10
    t[19:25,13:25] = 10
    for ox in (25,31,37):
        t[19:23,ox:ox+5] = 5
        t[19:23,ox+1:ox+4] = 15
        t[23,ox:ox+5] = np.array([5,11,0,11,5])
    t[19:25,30] = 10
    t[19:25,36] = 10
    t[25:30,13:42] = 10
    return t

def _l2_reveal5():
    # Final gauntlet: every column has an f device, followed by a full row of
    # closed c gates. The player must stay below and route horizontally.
    e = np.array(ENTRY_GRID, dtype=int)
    t = _wall_screen()[:36].copy()
    t[19:25,13:54] = 10
    for ox in range(13,50,6):
        t[19:23,ox:ox+5] = 5
        t[19:23,ox+1:ox+4] = 15
        t[23,ox:ox+5] = np.array([5,11,0,11,5])
        t[24,ox:ox+5] = 5
    t[25:30,13:54] = 10
    cell = e[37:42,30:37]
    for cx in range(12,49,6):
        t[31:36,cx:cx+7] = cell
    return t

def _reveal(scroll, n):
    if CURRENT_LEVEL == 2 and scroll == 90 and n == 36:
        return _l2_reveal5()
    if CURRENT_LEVEL == 2 and scroll == 60 and n == 30:
        return _l2_reveal4()
    if CURRENT_LEVEL == 2 and scroll == 54 and n == 6:
        return _l2_reveal3()
    if CURRENT_LEVEL == 2 and scroll == 24 and n == 30:
        return _l2_reveal2()
    if CURRENT_LEVEL == 2 and scroll == 0 and n == 24:
        return _l2_reveal1()
    if CURRENT_LEVEL == 1 and scroll == 0 and n == 6:
        return _l1_reveal1()
    if CURRENT_LEVEL == 1 and scroll == 6 and n == 42:
        return _l1_reveal2()
    if CURRENT_LEVEL == 1 and scroll == 48 and n == 24:
        return _l1_reveal3()
    if CURRENT_LEVEL == 1 and scroll == 72 and n == 6:
        return _l1_reveal4()
    if CURRENT_LEVEL == 1 and scroll == 78 and n == 18:
        return _l1_reveal5()
    if CURRENT_LEVEL == 1 and scroll == 96 and n == 18:
        return _l1_reveal6()
    if CURRENT_LEVEL == 1 and scroll == 114 and n == 6:
        return _l1_reveal7()
    if CURRENT_LEVEL == 1 and scroll == 120 and n == 6:
        return _l1_reveal8()
    if CURRENT_LEVEL == 1 and scroll == 126 and n == 6:
        return _l1_reveal9()
    if CURRENT_LEVEL == 1 and scroll == 132 and n == 24:
        return _l1_reveal10()
    if CURRENT_LEVEL == 0 and scroll == 0 and n == 18:
        return _first_reveal()
    if CURRENT_LEVEL == 0 and scroll == 18 and n == 24:
        return _second_reveal()
    if CURRENT_LEVEL == 0 and scroll == 42 and n == 18:
        return _third_reveal()
    # Provisional continuation, refined whenever another section is exposed.
    return _wall_screen()[:n].copy()

def _finish_float(g, ox, oy, scroll, face=1):
    ny = oy
    dead = False
    level_up = False
    while True:
        cand = ny - 6
        if _fits(g, ox, cand):
            ny = cand
            continue
        # Special framed objects resolve on attempted contact: colour-f devices
        # kill, while the colour-7 diamond completes the level.
        if cand >= 0:
            region = g[cand:cand+5, ox:ox+5]
            if np.any(region == 15):
                dead = True
            elif np.any(region == 7):
                level_up = True
        break
    # In the L1 safe-right shaft the open run continues one logical cell
    # above the old viewport before meeting its hidden ceiling.
    if (not dead and CURRENT_LEVEL == 1 and scroll == 6 and ox >= 37
            and ny == 1):
        ny -= 6
    rise = oy - ny
    if rise and not dead:
        hud = g[63].copy()
        old = g[:63].copy()  # player was erased before this routine
        g[rise:63] = old[:63-rise]
        g[:rise] = _reveal(scroll, rise)
        g[63] = hud
        scroll += rise
        new_under = _capture_under(g, ox, oy)
        _draw(g, ox, oy, face)  # camera keeps the player anchored
    else:
        new_under = _capture_under(g, ox, ny)
        _draw(g, ox, ny, face)
    return g, scroll, dead, level_up, new_under

def _move_and_float(g, dx, scroll, under):
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, False, False, under
    ox, oy = pos
    _erase(g, ox, oy, under)
    nx = ox + dx
    if not _fits(g, nx, oy):
        nx = ox
    return _finish_float(g, nx, oy, scroll, 1 if dx > 0 else -1)

def _click_and_float(g, x, y, scroll, under):
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return g, scroll, False, False, under
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx, cy = (int(x)//6)*6, (int(y)//6)*6
    # e is a one-hit brick. A c gate toggles between a solid shell
    # and a sparse five-pixel X state.
    tile = g[max(0,cy):min(63,cy+6), max(0,cx):min(64,cx+6)]
    c_count = int(np.sum(tile == 12))
    if np.any(tile == 14) or c_count:
        # Removing a tile opens its 5x5 interior. Each shared seam also
        # vanishes exactly when the neighbouring logical cell is already open;
        # seams against another solid tile remain.
        g[max(0,cy+1):min(63,cy+6), max(0,cx+1):min(64,cx+6)] = 10
        def open_at(px, py):
            if not (0 <= px < 64 and 0 <= py < 63):
                return False
            if g[py,px] == 10:
                return True
            if g[py,px] == 12:
                # Centre c can be either a sparse five-pixel gate or a dense
                # 25-pixel closed gate; only the former is logically open.
                ncx, ncy = (px//6)*6, (py//6)*6
                reg = g[ncy:min(63,ncy+6), ncx:min(64,ncx+6)]
                return int(np.sum(reg == 12)) <= 5
            return False
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
        if c_count > 5 and cy+4 < 63 and cx+4 < 64:
            for px, py in ((cx+2,cy+2),(cx+4,cy+2),(cx+3,cy+3),
                           (cx+2,cy+4),(cx+4,cy+4)):
                g[py,px] = 12
        elif c_count and cy+6 < 63 and cx+6 < 64:
            # Clicking the sparse X toggles the gate shut again, restoring
            # all four frame seams around its solid shell.
            g[cy, cx:cx+7] = 5
            g[cy+6, cx:cx+7] = 5
            for ry in range(1,6):
                g[cy+ry, cx:cx+7] = 5
                if ry in (1,5):
                    g[cy+ry, cx+1] = 3
                    g[cy+ry, cx+2:cx+5] = 12
                    g[cy+ry, cx+5] = 3
                else:
                    g[cy+ry, cx+1:cx+6] = 12
    return _finish_float(g, ox, oy, scroll, face)

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid, dtype=int).copy()
    undo = list(state.get("undo", []))
    scroll = int(state.get("scroll", 0))
    under = state.get("under", [[10]*5 for _ in range(5)])
    info = {"level_up": False, "dead": False, "win": False}
    if action == 7:
        if undo:
            ent = undo.pop()
            g = np.array(ent[0], dtype=int)
            scroll = int(ent[1])
            under = ent[2] if len(ent) > 2 else [[10]*5 for _ in range(5)]
        return g.tolist(), info, {"undo": undo, "scroll": scroll, "under": under}
    if action in (3,4):
        undo.append((np.array(grid,dtype=int).tolist(), scroll, under))
        dx = -6 if action == 3 else 6
        pos = _player_origin(g)
        # Entering the framed colour-7 diamond completes the current level.
        hit_goal = False
        if pos is not None:
            ox, oy = pos
            nx = ox + dx
            if 0 <= nx and nx+5 <= 64:
                hit_goal = bool(np.any(g[oy:oy+5, nx:nx+5] == 7))
        if hit_goal:
            info["level_up"] = True
        else:
            g, scroll, dead, rose_into_goal, under = _move_and_float(g, dx, scroll, under)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            _tick(g)
    elif action == 6:
        undo.append((np.array(grid,dtype=int).tolist(), scroll, under))
        g, scroll, dead, rose_into_goal, under = _click_and_float(g, x, y, scroll, under)
        info["dead"] = bool(dead)
        info["level_up"] = bool(rose_into_goal)
        _tick(g)
    return g.tolist(), info, {"undo": undo, "scroll": scroll, "under": under}
