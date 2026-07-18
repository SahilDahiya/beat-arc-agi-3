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
    return {"undo": [], "scroll": 0, "under": [[10]*5 for _ in range(5)],
            "gravity": -1, "cap_under": [10,10,10]}

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

def _l3_reveal1():
    t = _wall_screen()[:6].copy()
    cx = 30
    for ry in range(1,6):
        t[ry,cx:cx+7] = 5
        if ry in (1,5):
            t[ry,cx+1] = 3
            t[ry,cx+2:cx+5] = 8
            t[ry,cx+5] = 3
        else:
            t[ry,cx+1:cx+6] = 8
    return t

def _wall_world(start, n):
    w = np.full((n,64), 5, dtype=int)
    for i in range(n):
        r = (start+i) % 6
        if r == 1:
            w[i,2:64:6] = 3
        elif r == 4:
            w[i,1:64:6] = 3
        elif r == 5:
            w[i,4:64:6] = 3
    return w

def _l4_down_reveal1():
    # World rows 63..90 first exposed when the entry c8 switch flips gravity.
    rows = [
        '5555555555555555555555555555555555555eeeee5eeeee5555555555555555',
        '5355555355555355555355555355555355555eeeee5eeeee5355555355555355',
        '55553555553555553555553555553555553553eee353eee35555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555355555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaa5555555555555555',
        '5535555535555aaaaa5535555535555535555aaaaaaaaaaaa5fff5a5fff55535',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaa5fff5a5fff55555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaa5fff5a5fff55555',
        '5355555355555aaaaa5355555355555355555aaaaaaaaaaaa5fff5a5fff55355',
        '5555355555355aaaaa5555355555355555355aaaaaaaaaaaa5b0b5a5b0b55555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaa55555a555555555',
        '5535555535555aaaaa5535555535555535555aaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555355555aaaaa5355555355555355555aaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355555355aaaaa5555355555355555355aaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaa5555555555555555555555555555555aaaaaaaaaaa5555',
        '5535555535555aaaaaa5fff5a5fff555355553eee353eee35aaaaaaaaaaa5535',
        '5555555555555aaaaaa5fff5a5fff55555555eeeee5eeeee5aaaaaaaaaaa5555',
        '5555555555555aaaaaa5fff5a5fff55555555eeeee5eeeee5aaaaaaaaaaa5555',
        '5355555355555aaaaaa5fff5a5fff55355555eeeee5eeeee5aaaaaaaaaaa5355',
        '5555355555355aaaaaa5b0b5a5b0b555553553eee353eee35aaaaaaaaaaa5555',
        '5555555555555aaaaaa55555a555555555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l4_down_reveal2():
    # World rows 91..114 exposed by drilling the first c7 floor.
    rows = [
        '5535555535555aaaaaaaaaaaaaaaaa55355555355555355553eee353eee35535',
        '5555555555555aaaaaaacacaaacaca5555555555555555555eeeee5eeeee5555',
        '5555555555555aaaaaaaacaaaaacaa5555555555555555555eeeee5eeeee5555',
        '5355555355555aaaaaaacacaaacaca5355555355555355555eeeee5eeeee5355',
        '5555355555355aaaaaaaaaaaaaaaaa55553555553555553553eee353eee35555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555555555555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5535555535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535555535',
        '5555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5355555355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355555355',
        '5555355555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555355555',
        '5555555555555555555aaaaaaaaaaa5555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l4_down_reveal3():
    # World rows 115..120 exposed by drilling the second c7 floor.
    rows = [
        '5535555535555535555aaaaaaaaaaa5535555535555535555535555535555535',
        '5555555555555555555aaaaaaaaaaa5555555555555555555555555555555555',
        '5555555555555555555aaaaaaaaaaa5555555555555555555555555555555555',
        '5355555355555355555aaaaaaaaaaa5355555355555355555355555355555355',
        '5555355555355555355aaaaaaaaaaa5555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l4_down_reveal4():
    # World rows 121..138 exposed by the c8 e descent.
    rows = [
        '55355555355555355553eee353eee35535555535555535555535555535555535',
        '5555555555555555555eeeee5eeeee5555555555555555555555555555555555',
        '5555555555555555555eeeee5eeeee5555555555555555555555555555555555',
        '5355555355555355555eeeee5eeeee5355555355555355555355555355555355',
        '55553555553555553553eee353eee35555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555aaaaaaaaaaa5535555535555535555535555535555535',
        '5555555555555555555aaaaaaaaaaa5555555555555555555555555555555555',
        '5555555555555555555aaaaaaaaaaa5555555555555555555555555555555555',
        '5355555355555355555aaaaaaaaaaa5355555355555355555355555355555355',
        '5555355555355555355aaaaaaaaaaa5555355555355555355555355555355555',
        '555555555555555555555555a555555555555555555555555555555555555555',
        '55355555355555355555b0b5a5b0b55535555535555535555535555535555535',
        '55555555555555555555fff5a5fff55555555555555555555555555555555555',
        '55555555555555555555fff5a5fff55555555555555555555555555555555555',
        '53555553555553555555fff5a5fff55355555355555355555355555355555355',
        '55553555553555553555fff5a5fff55555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l4_down_reveal5():
    # World rows 139..144 exposed by the c8-to-c7 switchback fall.
    rows = [
        '5535555535555535555535555535555535555535555535555388835535555535',
        '5555555555555555555555555555555555555555555555555888885555555555',
        '5555555555555555555555555555555555555555555555555888885555555555',
        '5355555355555355555355555355555355555355555355555888885355555355',
        '5555355555355555355555355555355555355555355555355388835555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l4_deeper_rows(start, n):
    out = _wall_world(start, n)
    a, b = max(start, 63), min(start+n, 91)
    if a < b:
        known = _l4_down_reveal1()
        out[a-start:b-start] = known[a-63:b-63]
    a, b = max(start, 91), min(start+n, 115)
    if a < b:
        known = _l4_down_reveal2()
        out[a-start:b-start] = known[a-91:b-91]
    a, b = max(start, 115), min(start+n, 121)
    if a < b:
        known = _l4_down_reveal3()
        out[a-start:b-start] = known[a-115:b-115]
    a, b = max(start, 121), min(start+n, 139)
    if a < b:
        known = _l4_down_reveal4()
        out[a-start:b-start] = known[a-121:b-121]
    a, b = max(start, 139), min(start+n, 145)
    if a < b:
        known = _l4_down_reveal5()
        out[a-start:b-start] = known[a-139:b-139]
    return out

def _l4_flip_down(g, x, y, scroll, under):
    # Consume the entry c8 switch, fall to the c7 floor, and change from the
    # y37 up-anchor to the y27 down-anchor (ten extra camera pixels).
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    # The switch has open neighbours on both sides, so consuming its core also
    # removes both vertical side seams while retaining the solid ceiling above.
    g[cy+1:cy+6, cx:cx+7] = 10
    ny = oy
    while _fits(g, ox, ny+6):
        ny += 6
    shift = (ny-oy) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[:63-shift] = old[shift:63]
    first_world = 63 - scroll
    g[63-shift:63] = _l4_deeper_rows(first_world, shift)
    g[63] = hud
    scroll -= shift
    under, cap_under = _draw_down(g, ox, 27, face)
    return g, scroll, under, cap_under

def _l4_up_reveal1():
    # World rows 60..81 restored above the viewport by the deep switch.
    rows = [
        '5555555555555555555555555555555555555555555aaaaa5555555555555555',
        '55355555355555355555355555355555355553eee35aaaaa5535555535555535',
        '5555555555555555555555555555555555555eeeee5aaaaa5555555555555555',
        '5555555555555555555555555555555555555eeeee5aaaaa5555555555555555',
        '5355555355555355555355555355555355555eeeee5aaaaa5355555355555355',
        '55553555553555553555553555553555553553eee35aaaaa5555355555355555',
        '5555555555555555555555555555555555555555555aaaaa5555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555355555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaa5555555555555555',
        '5535555535555aaaaa5535555535555535555aaaaaaaaaaaa5fff5a5fff55535',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaa5fff5a5fff55555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaa5fff5a5fff55555',
        '5355555355555aaaaa5355555355555355555aaaaaaaaaaaa5fff5a5fff55355',
        '5555355555355aaaaa5555355555355555355aaaaaaaaaaaa5b0b5a5b0b55555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaa55555a555555555',
        '5535555535555aaaaa5535555535555535555aaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaa5555555555555555555aaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l4_flip_up(g, x, y, scroll, under, cap_under):
    # Consume the deep c8 switch.  The c7 player rises 12px, while changing
    # from the y27 down-anchor to y37 adds ten camera pixels (scroll -82→-60).
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, under
    ox, oy = pos
    face = _facing(g)
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[cy+1:min(63,cy+6), cx+1:cx+6] = 10
    ny = oy
    while _fits(g, ox, ny-6):
        ny -= 6
    shift = (oy-ny) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[shift:63] = old[:63-shift]
    g[:shift] = _l4_up_reveal1()
    g[63] = hud
    scroll += shift
    new_under = _capture_under(g, ox, 37)
    _draw(g, ox, 37, face)
    return g, scroll, new_under

def _l4_up_reveal2():
    # World rows 30..59 restored when the gated c2 shaft lifts the player.
    rows = [
        '5555555555555555555555555555555555555555555555555555555aaaaa5555',
        '5535555535555535555535555535555535555535555535555535555aaaaa5535',
        '5555555555555555555555555555555555555555555555555555555aaaaa5555',
        '5555555555555555555555555555555555555555555555555555555aaaaa5555',
        '5355555355555355555355555355555355555355555355555355555aaaaa5355',
        '5555355555355555355555355555355555355555355555355555355aaaaa5555',
        '5555555555555555555555555555555555555555555555555555555aaaaa5555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555355555',
        '555555555555555555a55555a55555a55555aaaaaaaaaaaa5555555555555555',
        '55355555355555b0b5a5b0b5a5b0b5a5b0b5aaaaaaaaaaaa5535555535555535',
        '55555555555555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaa5555555555555555',
        '55555555555555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaa5555555555555555',
        '53555553555555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaa5355555355555355',
        '55553555553555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaa5555355555355555',
        '5555555555555555555555555555555555555aaaaaaaaaaa5555555555555555',
        '5535555535555535555535555535555535555aaaaaaaaaaa5535555535555535',
        '5555555555555555555555555555555555555aaaaaaaaaaa5555555555555555',
        '5555555555555555555555555555555555555aaaaaaaaaaa5555555555555555',
        '5355555355555355555355555355555355555aaaaaaaaaaa5355555355555355',
        '5555355555355555355555355555355555355aaaaaaaaaaa5555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l3_flip_down(g):
    # Clicking the 8 switch reverses gravity. The player falls from world y=7
    # to y=49 and the camera offset changes from +30 to -22.
    e = np.array(ENTRY_GRID, dtype=int).copy()
    ep = _player_origin(e)
    if ep is not None:
        _erase(e, ep[0], ep[1])
    out = np.empty((64,64), dtype=int)
    out[:41] = e[22:63]
    h = _wall_world(63,22)
    h[0:3,13:54] = 10
    h[3:10,13:30] = 10
    cell = e[55:60,12:19]
    for cx in (30,36,42,48):
        h[4:9,cx:cx+7] = cell
    h[10:15,13:54] = 10
    h[15:21,13:36] = 10
    h[15:22,43:54] = 10
    out[41:63] = h
    out[63] = g[63]
    ox, oy = 49, 27
    under = _capture_under(out, ox, oy)
    cap_under = out[oy-1,ox+1:ox+4].tolist()
    _draw(out, ox, oy, _facing(g))
    out[oy-1,ox+1:ox+4] = 5
    return out, under, cap_under

def _l3_flip_up(g, x, y, scroll, under, cap_under):
    # A later 8 switch consumes its core and reverses gravity upward.  The
    # player rises to the next blocker; changing from the down-anchor y27 to
    # the up-anchor y37 adds ten pixels to the camera shift.
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, under
    ox, oy = pos
    face = _facing(g)
    if scroll <= -100:
        out = np.empty((64,64), dtype=int)
        out[:63] = _l3_up_return_frame()
        out[63] = g[63]
        new_under = _capture_under(out, ox, 37)
        _draw(out, ox, 37, face)
        return out, -36, new_under
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[cy+1:cy+6, cx+1:cx+6] = 10
    ny = oy
    while _fits(g, ox, ny-6):
        ny -= 6
    shift = (oy-ny) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[shift:63] = old[:63-shift]
    new_scroll = scroll + shift
    e = np.array(ENTRY_GRID, dtype=int).copy()
    ep = _player_origin(e)
    if ep is not None:
        _erase(e, ep[0], ep[1])
    start_world = -new_scroll
    g[:shift] = e[start_world:start_world+shift]
    g[63] = hud
    new_under = _capture_under(g, ox, 37)
    _draw(g, ox, 37, face)
    return g, new_scroll, new_under

def _l3_up_return_frame():
    # World rows 36..98 after the deep switch, including persistence of both
    # consumed mid switches and the two drilled c7 e gates.
    rows = [
        '5555555555555555555555555555555555555aaaaaaaaaaaaaaaaa5555555555',
        '55355555355555fff5a5fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '55555555555555fff5a5fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '55555555555555fff5a5fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '53555553555555fff5a5fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '55553555553555b0b5a5b0b5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '555555555555555555a55555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555555555aaaaa5555555555555555555555555555555555555555',
        '55355555355553eee35aaaaa5535555535555535555535555535555535555535',
        '5555555555555eeeee5aaaaa5555555555555555555555555555555555555555',
        '5555555555555eeeee5aaaaa5555555555555555555555555555555555555555',
        '5355555355555eeeee5aaaaa5355555355555355555355555355555355555355',
        '55553555553553eee35aaaaa5555355555355555355555355555355555355555',
        '5555555555555555555aaaaa5555555555555555555555555555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555555555555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaa53eee353eee353eee353eee35535555535',
        '5555555555555aaaaaaaaaaaaaaaaa5eeeee5eeeee5eeeee5eeeee5555555555',
        '5555555555555aaaaaaaaaaaaaaaaa5eeeee5eeeee5eeeee5eeeee5555555555',
        '5355555355555aaaaaaaaaaaaaaaaa5eeeee5eeeee5eeeee5eeeee5355555355',
        '5555355555355aaaaaaaaaaaaaaaaa53eee353eee353eee353eee35555355555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555555555555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaa5535555aaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaa5355555aaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaa5555355aaaaaaaaaaa5555355555',
        '5555555555555555555555555555555555555555555aaaaaaaaaaa5555555555',
        '5535555535555535555535555535555535555535555aaaaaaaaaaa5535555535',
        '5555555555555555555555555555555555555555555aaaaaaaaaaa5555555555',
        '5555555555555555555555555555555555555555555aaaaaaaaaaa5555555555',
        '5355555355555355555355555355555355555355555aaaaaaaaaaa5355555355',
        '5555355555355555355555355555355555355555355aaaaaaaaaaa5555355555',
        '5555555555555555555555555555555555555555555aaaaa5555555555555555',
        '5535555535555535555aaaaa5535555aaaaa5535555aaaaa53eee35535555535',
        '5555555555555555555aaaaa5555555aaaaa5555555aaaaa5eeeee5555555555',
        '5555555555555555555aaaaa5555555aaaaa5555555aaaaa5eeeee5555555555',
        '5355555355555355555aaaaa5355555aaaaa5355555aaaaa5eeeee5355555355',
        '5555355555355555355aaaaa5555355aaaaa5555355aaaaa53eee35555355555',
        '5555555555555555555555555555555555555555555aaaaa5555555555555555',
        '5535555535555535555535555535555535555535555aaaaa53eee35535555535',
        '5555555555555555555555555555555555555555555aaaaa5eeeee5555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l3_deeper_rows(start, n):
    # Compose learned reversed-gravity world rows; unknown continuation remains
    # periodic wall until its first reveal.
    out = _wall_world(start, n)
    a, b = max(start, 85), min(start+n, 115)
    if a < b:
        known = _l3_down_reveal1()
        out[a-start:b-start] = known[a-85:b-85]
    a, b = max(start, 115), min(start+n, 121)
    if a < b:
        known = _l3_down_reveal2()
        out[a-start:b-start] = known[a-115:b-115]
    a, b = max(start, 121), min(start+n, 127)
    if a < b:
        known = _l3_down_reveal3()
        out[a-start:b-start] = known[a-121:b-121]
    a, b = max(start, 127), min(start+n, 163)
    if a < b:
        known = _l3_down_reveal4()
        out[a-start:b-start] = known[a-127:b-127]
    return out

def _l3_flip_down_later(g, x, y, scroll, under):
    # Subsequent 8 switches reverse an upward-gravity player back downward.
    # The y37 -> y27 anchor change contributes ten extra pixels to the camera
    # shift in addition to the physical fall.
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[cy+1:cy+6, cx+1:cx+6] = 10
    ny = oy
    while _fits(g, ox, ny+6):
        ny += 6
    shift = (ny-oy) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[:63-shift] = old[shift:63]
    first_world = 63 - scroll
    g[63-shift:63] = _l3_deeper_rows(first_world, shift)
    g[63] = hud
    new_scroll = scroll - shift
    new_under, cap_under = _draw_down(g, ox, 27, face)
    return g, new_scroll, new_under, cap_under

def _l3_down_reveal1():
    # World rows 85..114 exposed by the first reversed-gravity fall.
    rows = [
        '5535555535555535555535555535555535555535555aaaaaaaaaaa5535555535',
        '5555555555555555555555555555555555555555555aaaaaaaaaaa5555555555',
        '5555555555555555555555555555555555555555555aaaaaaaaaaa5555555555',
        '5355555355555355555355555355555355555355555aaaaaaaaaaa5355555355',
        '5555355555355555355555355555355555355555355aaaaaaaaaaa5555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '55355555355555355553888355355553888355355553eee353eee35535555535',
        '5555555555555555555888885555555888885555555eeeee5eeeee5555555555',
        '5555555555555555555888885555555888885555555eeeee5eeeee5555555555',
        '5355555355555355555888885355555888885355555eeeee5eeeee5355555355',
        '55553555553555553553888355553553888355553553eee353eee35555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '55355555355555355555355555355555355555355553eee353eee35535555535',
        '5555555555555555555555555555555555555555555eeeee5eeeee5555555555',
        '5555555555555555555555555555555555555555555eeeee5eeeee5555555555',
        '5355555355555355555355555355555355555355555eeeee5eeeee5355555355',
        '55553555553555553555553555553555553555553553eee353eee35555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '55355555355555fff5a5fff5aaaaaaa5fff5a5fff5aaaaaaaaaaaa5535555535',
        '55555555555555fff5a5fff5aaaaaaa5fff5a5fff5aaaaaaaaaaaa5555555555',
        '55555555555555fff5a5fff5aaaaaaa5fff5a5fff5aaaaaaaaaaaa5555555555',
        '53555553555555fff5a5fff5aaaaaaa5fff5a5fff5aaaaaaaaaaaa5355555355',
        '55553555553555b0b5a5b0b5aaaaaaa5b0b5a5b0b5aaaaaaaaaaaa5555355555',
        '555555555555555555a55555aaaaaaa55555a55555aaaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaa555aaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l3_down_reveal2():
    rows = [
        '5535555535555aaaaaaaaaaaa55755aaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaa57775aaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaa55755aaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaa555aaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l3_down_reveal3():
    rows = [
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _l3_down_reveal4():
    # World rows 127..162; the player overlay in the observed frame has been
    # restored to its open terrain underlay.
    rows = [
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555535555535555535555535555535555535555535',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5355555355555355555355555355555355555355555355555355555355555355',
        '5555355555355555355555355555355555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555388835535555535555535555535555535555535',
        '5555555555555555555555555888885555555555555555555555555555555555',
        '5555555555555555555555555888885555555555555555555555555555555555',
        '5355555355555355555355555888885355555355555355555355555355555355',
        '5555355555355555355555355388835555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555535555535555535555535555535555535555535',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5355555355555355555355555355555355555355555355555355555355555355',
        '5555355555355555355555355555355555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555535555535555535555535555535555535555535',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5355555355555355555355555355555355555355555355555355555355555355',
        '5555355555355555355555355555355555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555535555535555535555535555535555535555535',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5355555355555355555355555355555355555355555355555355555355555355',
        '5555355555355555355555355555355555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)

def _reveal(scroll, n):
    if CURRENT_LEVEL == 4 and scroll == -60 and n == 30:
        return _l4_up_reveal2()
    if CURRENT_LEVEL == 4 and scroll == -30 and n == 30:
        # The final c7 ascent revisits the untouched top of the entry viewport.
        return np.array(ENTRY_GRID, dtype=int)[:30].copy()
    if CURRENT_LEVEL == 3 and scroll < 0:
        # While gravity is upward again, the camera revisits still-unmodified
        # rows of the level-entry world.  screen = world + new_scroll.
        new_scroll = scroll + n
        start = -new_scroll
        e = np.array(ENTRY_GRID, dtype=int).copy()
        ep = _player_origin(e)
        if ep is not None:
            _erase(e, ep[0], ep[1])
        if 0 <= start and start+n <= 63:
            return e[start:start+n].copy()
    if CURRENT_LEVEL == 3 and scroll == 0 and n == 6:
        return _l3_reveal1()
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

def _erase_down(g, ox, oy, under, cap_under):
    if oy > 0 and ox+4 < 64:
        g[oy-1,ox+1:ox+4] = np.array(cap_under,dtype=int)
    _erase(g, ox, oy, under)

def _draw_down(g, ox, oy, face):
    under = _capture_under(g, ox, oy)
    cap_under = g[oy-1,ox+1:ox+4].tolist() if oy > 0 else [10,10,10]
    _draw(g, ox, oy, face)
    if oy > 0:
        g[oy-1,ox+1:ox+4] = 5
    return under, cap_under

def _finish_fall(g, ox, oy, scroll, face=1):
    ny = oy
    dead = False
    level_up = False
    while True:
        cand = ny + 6
        if _fits(g, ox, cand):
            ny = cand
            continue
        hidden = None
        if CURRENT_LEVEL == 3 and scroll < 0 and cand+5 > 63:
            hidden = _l3_deeper_rows(cand-scroll, 5)
            ok = True
            for yy in range(5):
                for xx in range(5):
                    if PMASK[yy,xx] and hidden[yy,ox+xx] not in (10,12):
                        ok = False
            if ok:
                ny = cand
                continue
        if cand+5 <= 63:
            region = g[cand:cand+5,ox:ox+5]
        else:
            region = hidden[:,ox:ox+5] if hidden is not None else np.empty((0,0),dtype=int)
        if np.any(region == 15):
            dead = True
        elif np.any(region == 7):
            level_up = True
        break
    fall = ny - oy
    if fall and not dead:
        hud = g[63].copy()
        old = g[:63].copy()
        g[:63-fall] = old[fall:63]
        first_world = 63 - scroll
        if CURRENT_LEVEL == 3 and scroll < 0:
            g[63-fall:63] = _l3_deeper_rows(first_world, fall)
        elif CURRENT_LEVEL == 4 and scroll < 0:
            g[63-fall:63] = _l4_deeper_rows(first_world, fall)
        else:
            # Provisional deeper terrain; refined whenever a fall exposes it.
            g[63-fall:63] = _wall_world(first_world, fall)
        g[63] = hud
        scroll -= fall
        under, cap_under = _draw_down(g, ox, oy, face)
    else:
        under, cap_under = _draw_down(g, ox, ny, face)
    return g, scroll, dead, level_up, under, cap_under

def _move_and_fall(g, dx, scroll, under, cap_under):
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, False, False, under, cap_under
    ox, oy = pos
    _erase_down(g, ox, oy, under, cap_under)
    nx = ox + dx
    if not _fits(g, nx, oy):
        nx = ox
    return _finish_fall(g, nx, oy, scroll, 1 if dx > 0 else -1)

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

def _click_and_fall(g, x, y, scroll, under, cap_under):
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return g, scroll, False, False, under, cap_under
    ox, oy = pos
    face = _facing(g)
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    # The vertical lattice shifts with camera offset after gravity reversal.
    cy = ((int(y)-scroll)//6)*6 + scroll
    tile = g[max(0,cy):min(63,cy+6), max(0,cx):min(64,cx+6)]
    c_count = int(np.sum(tile == 12))
    if np.any(tile == 14) or c_count:
        g[max(0,cy+1):min(63,cy+6), max(0,cx+1):min(64,cx+6)] = 10
        def open_at(px, py):
            if not (0 <= px < 64 and 0 <= py < 63):
                return False
            if g[py,px] == 10:
                return True
            if g[py,px] == 12:
                ncx = (px//6)*6
                ncy = ((py-scroll)//6)*6 + scroll
                reg = g[max(0,ncy):min(63,ncy+6),ncx:min(64,ncx+6)]
                return int(np.sum(reg == 12)) <= 5
            return False
        left = open_at(cx-3,cy+3)
        right = open_at(cx+9,cy+3)
        top = open_at(cx+3,cy-3)
        bottom = open_at(cx+3,cy+9)
        if left:
            g[max(0,cy+1):min(63,cy+6),cx] = 10
        if right and cx+6 < 64:
            g[max(0,cy+1):min(63,cy+6),cx+6] = 10
        if top and cy >= 0:
            g[cy,max(0,cx+1):min(64,cx+6)] = 10
        if bottom and cy+6 < 63:
            g[cy+6,max(0,cx+1):min(64,cx+6)] = 10
        if left and top and cy >= 0: g[cy,cx] = 10
        if left and bottom and cy+6 < 63: g[cy+6,cx] = 10
        if right and top and cy >= 0 and cx+6 < 64: g[cy,cx+6] = 10
        if right and bottom and cx+6 < 64 and cy+6 < 63: g[cy+6,cx+6] = 10
        if c_count > 5 and 0 <= cy+4 < 63 and cx+4 < 64:
            for px,py in ((cx+2,cy+2),(cx+4,cy+2),(cx+3,cy+3),
                          (cx+2,cy+4),(cx+4,cy+4)):
                g[py,px] = 12
        elif c_count and 0 <= cy and cy+6 < 63 and cx+6 < 64:
            g[cy,cx:cx+7] = 5
            g[cy+6,cx:cx+7] = 5
            for ry in range(1,6):
                g[cy+ry,cx:cx+7] = 5
                if ry in (1,5):
                    g[cy+ry,cx+1] = 3
                    g[cy+ry,cx+2:cx+5] = 12
                    g[cy+ry,cx+5] = 3
                else:
                    g[cy+ry,cx+1:cx+6] = 12
    return _finish_fall(g,ox,oy,scroll,face)

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid, dtype=int).copy()
    undo = list(state.get("undo", []))
    scroll = int(state.get("scroll", 0))
    under = state.get("under", [[10]*5 for _ in range(5)])
    gravity = int(state.get("gravity", -1))
    cap_under = state.get("cap_under", [10,10,10])
    info = {"level_up": False, "dead": False, "win": False}
    if action == 7:
        # In this game action7 has no spatial effect; it only consumes a turn.
        _tick(g)
        ns = {"undo":undo,"scroll":scroll,"under":under,
              "gravity":gravity,"cap_under":cap_under}
        return g.tolist(), info, ns
    if action in (3,4):
        undo.append((np.array(grid,dtype=int).tolist(), scroll, under,
                     gravity, cap_under))
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
            if gravity > 0:
                g, scroll, dead, rose_into_goal, under, cap_under = _move_and_fall(
                    g, dx, scroll, under, cap_under)
            else:
                g, scroll, dead, rose_into_goal, under = _move_and_float(
                    g, dx, scroll, under)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            _tick(g)
    elif action == 6:
        undo.append((np.array(grid,dtype=int).tolist(), scroll, under,
                     gravity, cap_under))
        near = g[max(0,int(y or 0)-3):min(63,int(y or 0)+4),
                 max(0,int(x or 0)-3):min(64,int(x or 0)+4)]
        if (CURRENT_LEVEL == 4 and np.any(near == 8)
                and gravity < 0 and scroll == 0):
            g, scroll, under, cap_under = _l4_flip_down(
                g, x, y, scroll, under)
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 4 and np.any(near == 8)
                and gravity > 0):
            g, scroll, under = _l4_flip_up(
                g, x, y, scroll, under, cap_under)
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif CURRENT_LEVEL == 3 and np.any(near == 8):
            if gravity < 0:
                if scroll >= 0:
                    g, under, cap_under = _l3_flip_down(g)
                    scroll = -22
                else:
                    g, scroll, under, cap_under = _l3_flip_down_later(
                        g, x, y, scroll, under)
                gravity = 1
            else:
                # Resolve a visible upward hazard/goal encountered on the new
                # gravity trajectory (the deep c5 route crosses the 7 goal).
                pos = _player_origin(g)
                if pos is not None:
                    ox, ny = pos
                    while _fits(g, ox, ny-6):
                        ny -= 6
                    cand = ny-6
                    if cand >= 0:
                        region = g[cand:cand+5, ox:ox+5]
                        info["dead"] = bool(np.any(region == 15))
                        info["level_up"] = bool(np.any(region == 7))
                g, scroll, under = _l3_flip_up(
                    g, x, y, scroll, under, cap_under)
                gravity = -1
                cap_under = [10,10,10]
            _tick(g)
        else:
            if gravity > 0:
                g, scroll, dead, rose_into_goal, under, cap_under = _click_and_fall(
                    g, x, y, scroll, under, cap_under)
            else:
                g, scroll, dead, rose_into_goal, under = _click_and_float(
                    g, x, y, scroll, under)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            _tick(g)
    ns = {"undo":undo,"scroll":scroll,"under":under,
          "gravity":gravity,"cap_under":cap_under}
    return g.tolist(), info, ns
