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
    # L7 movable blocks live in world coordinates because growth can place a
    # child just beyond the camera; a viewport alone cannot distinguish that
    # hidden child from the shared seam of a visible neighbour.
    if CURRENT_LEVEL == 7:
        blocks = _l7_initial_blocks()
    elif CURRENT_LEVEL == 8:
        # L8 reuses the same framed-f flower objects.  Besides the visible
        # entry seed, a second seed is hidden in the upper c7/world-126 room.
        blocks = set(_l7_block_cells(np.array(entry_grid, dtype=int)))
        blocks.add((42,-126))
        blocks = sorted(blocks)
    else:
        blocks = []
    sparse = _l7_initial_sparse() if CURRENT_LEVEL == 7 else []
    return {"undo": [], "scroll": 0, "under": [[10]*5 for _ in range(5)],
            "gravity": -1, "cap_under": [10,10,10], "switches": [],
            "l7_blocks": blocks, "l7_sparse": sparse}

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
        # L6+ first fill a safe/goal-colour phase.
        g[-1, int(z[0])] = 7 if (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 6) else 15
    elif CURRENT_LEVEL is not None and CURRENT_LEVEL >= 6:
        # Once all 64 cells are 7, the danger-colour phase overwrites them
        # left-to-right on subsequent actions.
        q = np.where(g[-1] == 7)[0]
        if len(q):
            g[-1, int(q[0])] = 15

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

def _l6_down_reveal1():
    # World rows 63..78 exposed by the first sidebar flip.  The c8 hazard and
    # c3 goal announce the lower switchback section.
    rows = [
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa55555aaaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5b0b5aaaaaa5535',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5555',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5555',
        '5555555555555aaaaaaa555aaaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaa55755aaaaaa5535555535555aaaaa5535555aaaaa5535',
        '5888885555555aaaaaa57775aaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5888885555555aaaaaa55755aaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5888885355555aaaaaaa555aaaaaaa5355555355555aaaaa5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaa5555355555355aaaaa5555355aaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555aaaaa5555555aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_up_reveal1():
    # World rows above the entry viewport, exposed by rising c8 from the
    # post-sidebar-flip corridor.  c8 is the safe gap beside the c7 hazard.
    rows = [
        '5555555555555aaaaaaaaaaaa55555aaaaaa5555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaa53ccc35aaaaa5535555aaaaa5535',
        '5888885555555aaaaaaacacaaacacaaaaaaa5ccccc5acaca5555555aaaaa5555',
        '5888885555555aaaaaaaacaaaaacaaaaaaaa5ccccc5aacaa5555555aaaaa5555',
        '5888885355555aaaaaaacacaaacacaaaaaaa5ccccc5acaca5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaa53ccc35aaaaa5555355aaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5535555aaaaa5535',
        '5888885555555aaaaaaacacaaaaaaa5ccccc5aaaaaaacaca5555555aaaaa5555',
        '5888885555555aaaaaaaacaaaaaaaa5ccccc5aaaaaaaacaa5555555aaaaa5555',
        '5888885355555aaaaaaacacaaaaaaa5ccccc5aaaaaaacaca5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5555355aaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555aaaaaa555555555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaa5b0b5aaaaaaa5b0b55535555aaaaa5535',
        '5888885555555aaaaaaacacaaaaaaaa5fff5aaaaaaa5fff55555555aaaaa5555',
        '5888885555555aaaaaaaacaaaaaaaaa5fff5aaaaaaa5fff55555555aaaaa5555',
        '5888885355555aaaaaaacacaaaaaaaa5fff5aaaaaaa5fff55355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaa5fff5aaaaaaa5fff55555355aaaaa5555',
        '5555555555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        '5388835535555aaaaa5535555535555535555535555535555535555aaaaa5535',
        '5888885555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        '5888885555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        '5888885355555aaaaa5355555355555355555355555355555355555aaaaa5355',
        '5388835555355aaaaa5555355555355555355555355555355555355aaaaa5555',
        '5555555555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        '5388835535555aaaaa5535555aaaaaaaaaaaaaaaaaaaaaaa5535555aaaaa5535',
        '5888885555555aaaaa5555555acacaaacacaaacacaaaaaaa5555555aaaaa5555',
        '5888885555555aaaaa5555555aacaaaaacaaaaacaaaaaaaa5555555aaaaa5555',
        '5888885355555aaaaa5355555acacaaacacaaacacaaaaaaa5355555aaaaa5355',
        '5388835555355aaaaa5555355aaaaaaaaaaaaaaaaaaaaaaa5555355aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_up_reveal2():
    # World rows -36..-25 exposed by moving c8 -> c7.  The world -30
    # hazards cap c4 and c6; c7 remains protected by the world -6 wall.
    rows = [
        '5555555555555555555555555555555555555555555aaaaaaaaaaaaaaaaa5555',
        '5388835535555535555535555535555535555535555aaaaaaaaaaaaaaaaa5535',
        '5888885555555555555555555555555555555555555acacaaaaaaaaaaaaa5555',
        '5888885555555555555555555555555555555555555aacaaaaaaaaaaaaaa5555',
        '5888885355555355555355555355555355555355555acacaaaaaaaaaaaaa5355',
        '5388835555355555355555355555355555355555355aaaaaaaaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaa5fff5aaaaaaa5fff5aaaaaa5535555aaaaa5535',
        '5888885555555aaaaaaacacaa5fff5aaaaaaa5fff5aacaca5555555aaaaa5555',
        '5888885555555aaaaaaaacaaa5fff5aaaaaaa5fff5aaacaa5555555aaaaa5555',
        '5888885355555aaaaaaacacaa5fff5aaaaaaa5fff5aacaca5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaa5b0b5aaaaaaa5b0b5aaaaaa5555355aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_down_reveal2():
    # World rows 27..54, re-entered when the third sidebar switch drops c6
    # from world0 onto the deliberately closed world24 gate.
    rows = [
        '5888885555555aaaaaa5fff5aaacaaaaacaa5ccccc55fff5aaaaaaaaaaaa5555',
        '5888885355555aaaaaa5fff5aacacaaacaca5ccccc55fff5aaaaaaaaaaaa5355',
        '5388835555355aaaaaa5fff5aaaaaaaaaaaa53ccc355fff5aaaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5388835535555535555535555535555535555535555535555aaaaaaaaaaa5535',
        '5888885555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5888885555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5888885355555355555355555355555355555355555355555aaaaaaaaaaa5355',
        '5388835555355555355555355555355555355555355555355aaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555aaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaacaca5555555aaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaacaa5555555aaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaacaca5355555aaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355aaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaa5555555555555aaaaaaaaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaa53ccc35535555aaaaaaaaaaa5535',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaa5ccccc5555555aaaaaaaaaaa5555',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaa5ccccc5555555aaaaaaaaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaa5ccccc5355555aaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaa53ccc35555355aaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555555555aaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_up_reveal3():
    # World rows -18..-9 revisited by the zero-rise fourth sidebar flip.
    rows = [
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5535555aaaaa5535',
        '5888885555555aaaaaaacacaaaaaaa5ccccc5aaaaaaacaca5555555aaaaa5555',
        '5888885555555aaaaaaaacaaaaaaaa5ccccc5aaaaaaaacaa5555555aaaaa5555',
        '5888885355555aaaaaaacacaaaaaaa5ccccc5aaaaaaacaca5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5555355aaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555aaaaaa555555555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaa5b0b5aaaaaaa5b0b55535555aaaaa5535',
        '5888885555555aaaaaaacacaaaaaaaa5fff5aaaaaaa5fff55555555aaaaa5555',
        '5888885555555aaaaaaaacaaaaaaaaa5fff5aaaaaaa5fff55555555aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_up_reveal4():
    # World rows -66..-25 exposed by the long safe c2 ascent.
    rows = [
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
        '5535555535555535555535555535555535555535555aaaaa55355555fff55535',
        '5555555555555555555555555555555555555555555acaca55555555fff55555',
        '5555555555555555555555555555555555555555555aacaa55555555fff55555',
        '5355555355555355555355555355555355555355555acaca53555555fff55355',
        '5555355555355555355555355555355555355555355aaaaa55553555b0b55555',
        '5555555555555555555555555555555555555555555aaaaa5555555555555555',
        '5388835535555535555535555535555535555535555aaaaa5535555aaaaa5535',
        '5888885555555555555555555555555555555555555acaca5555555aaaaa5555',
        '5888885555555555555555555555555555555555555aacaa5555555aaaaa5555',
        '5888885355555355555355555355555355555355555acaca5355555aaaaa5355',
        '5388835555355555355555355555355555355555355aaaaa5555355aaaaa5555',
        '5555555555555555555555555555555555555555555aaaaa5555555aaaaa5555',
        '5388835535555535555535555535555535555535555aaaaaaaaaaaaaaaaa5535',
        '5888885555555555555555555555555555555555555acacaaaaaaaaaaaaa5555',
        '5888885555555555555555555555555555555555555aacaaaaaaaaaaaaaa5555',
        '5888885355555355555355555355555355555355555acacaaaaaaaaaaaaa5355',
        '5388835555355555355555355555355555355555355aaaaaaaaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555aaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555535555535555535555535555535555aaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555555555555555555555555555555555acacaaaaaaaaaaaaa5555',
        'aaaaaa5555555555555555555555555555555555555aacaaaaaaaaaaaaaa5555',
        'aaaaaa5355555355555355555355555355555355555acacaaaaaaaaaaaaa5355',
        'aaaaaa5555355555355555355555355555355555355aaaaaaaaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaa5fff5aaaaaaa5fff5aaaaaa5535555aaaaa5535',
        '5888885555555aaaaaaacacaa5fff5aaaaaaa5fff5aacaca5555555aaaaa5555',
        '5888885555555aaaaaaaacaaa5fff5aaaaaaa5fff5aaacaa5555555aaaaa5555',
        '5888885355555aaaaaaacacaa5fff5aaaaaaa5fff5aacaca5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaa5b0b5aaaaaaa5b0b5aaaaaa5555355aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_down_reveal4():
    # World rows 13..24 exposed by c4's fall from -24 to -12.
    rows = [
        '5388835535555aaaaaaaaaaa53ccc353ccc353ccc35aaaaaaaaaaaaaaaaa5535',
        '5888885555555aaaaaaaaaaa5ccccc5ccccc5ccccc5aaaaaaaaaaaaaaaaa5555',
        '5888885555555aaaaaaaaaaa5ccccc5ccccc5ccccc5aaaaaaaaaaaaaaaaa5555',
        '5888885355555aaaaaaaaaaa5ccccc5ccccc5ccccc5aaaaaaaaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaa53ccc353ccc353ccc35aaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaa5555555555555555555aaaaaaaaaaaaaaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5888885555555aaaaaaaaaaaaacacaaacacaaacacaaaaaaaaaaaaaaaaaaa5555',
        '5888885555555aaaaaaaaaaaaaacaaaaacaaaaacaaaaaaaaaaaaaaaaaaaa5555',
        '5888885355555aaaaaaaaaaaaacacaaacacaaacacaaaaaaaaaaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaa55555aaaaaaaaaaaa555555555555aaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_down_reveal3():
    # World rows -3..12 re-entered by the fifth switch's one-cell descent.
    rows = [
        'aaaaaa5555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        'aaaaaa5355555aaaaa5355555355555355555355555355555355555aaaaa5355',
        'aaaaaa5555355aaaaa5555355555355555355555355555355555355aaaaa5555',
        '5555555555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        '5388835535555aaaaa5535555aaaaaaaaaaaaaaaaaaaaaaa5535555aaaaa5535',
        '5888885555555aaaaa5555555acacaaacacaaacacaaaaaaa5555555aaaaa5555',
        '5888885555555aaaaa5555555aacaaaaacaaaaacaaaaaaaa5555555aaaaa5555',
        '5888885355555aaaaa5355555acacaaacacaaacacaaaaaaa5355555aaaaa5355',
        '5388835555355aaaaa5555355aaaaaaaaaaaaaaaaaaaaaaa5555355aaaaa5555',
        '5555555555555aaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555555aaaaa5555',
        '5388835535555aaaaa5535555aaaaaaaaaaaaaaaaaaaaaaa5535555aaaaa5535',
        '5888885555555aaaaa5555555acacaaacacaaacacaaaaaaa5555555aaaaa5555',
        '5888885555555aaaaa5555555aacaaaaacaaaaacaaaaaaaa5555555aaaaa5555',
        '5888885355555aaaaa5355555acacaaacacaaacacaaaaaaa5355555aaaaa5355',
        '5388835555355aaaaa5555355aaaaaaaaaaaaaaaaaaaaaaa5555355aaaaa5555',
        '5555555555555aaaaa5555555555555555555555555aaaaa5555555aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_down_reveal5():
    # World rows -15..-6 revisited when the c7 bracket reverses gravity.
    # They preserve the staged dense c4/c5 gates and the c5/c7 hazard bank.
    rows = [
        '5888885555555aaaaa5ccccc5aaaaa5ccccc5aaaaaaaacaa5555555aaaaa5555',
        '5888885355555aaaaa5ccccc5aaaaa5ccccc5aaaaaaacaca5355555aaaaa5355',
        '5388835555355aaaaa53ccc35aaaaa53ccc35aaaaaaaaaaa5555355aaaaa5555',
        '5555555555555aaaaa5555555aaaaa5555555aaaaaa555555555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaa5b0b5aaaaaaa5b0b55535555aaaaa5535',
        '5888885555555aaaaaaacacaaaaaaaa5fff5aaaaaaa5fff55555555aaaaa5555',
        '5888885555555aaaaaaaacaaaaaaaaa5fff5aaaaaaa5fff55555555aaaaa5555',
        '5888885355555aaaaaaacacaaaaaaaa5fff5aaaaaaa5fff55355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaa5fff5aaaaaaa5fff55555355aaaaa5555',
        '5555555555555aaaaa5555555555555555555555555555555555555aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_down_reveal6():
    # World rows -5..0 exposed by the one-cell c8 descent.  The world -6 wall
    # fills its first five rows; world 0 starts the known entry-room pattern.
    rows = [
        'aaaaaa5535555aaaaa5535555535555535555535555535555535555aaaaa5535',
        'aaaaaa5555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        'aaaaaa5555555aaaaa5555555555555555555555555555555555555aaaaa5555',
        'aaaaaa5355555aaaaa5355555355555355555355555355555355555aaaaa5355',
        'aaaaaa5555355aaaaa5555355555355555355555355555355555355aaaaa5555',
        '5555555555555aaaaa5555555555555555555555555555555555555aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_down_view2():
    # World rows 52..114 reached by descending the unobstructed c9 bypass.
    # The player lands at world78 on the world84 floor; the c3/world72 goal
    # and c8/world66 hazard are both visible in the lower chamber.
    rows = [
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaa5ccccc5355555aaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaa53ccc35555355aaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5388835535555535555535555535555535555535555535555aaaaaaaaaaa5535',
        '5888885555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5888885555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5888885355555355555355555355555355555355555355555aaaaaaaaaaa5355',
        '5388835555355555355555355555355555355555355555355aaaaaaaaaaa5555',
        '5555555555555555555555555555555555555555555555555aaaaaaaaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa55555aaaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5b0b5aaaaaa5535',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5555',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff5aaaaaa5555',
        '5555555555555aaaaaaa555aaaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaa55755aaaaaa5535555535555aaaaa5535555aaaaa5535',
        '5888885555555aaaaaa57775aaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5888885555555aaaaaa55755aaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5888885355555aaaaaaa555aaaaaaa5355555355555aaaaa5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaa5555355555355aaaaa5555355aaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555aaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaa5535555535555aaaaaaaaaaaaaaaaa5535',
        '5888885555555aaaaaaaaaaaaaaaaa5555555555555aaaaaaaaaaaaaaaaa5555',
        '5888885555555aaaaaaaaaaaaaaaaa5555555555555aaaaaaaaaaaaaaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaa5355555355555aaaaaaaaaaaaaaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaa5555355555355aaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555555555555555555555555',
        '5388835535555aaaaaaaaaaaaaaaaa5535555535555535555535555535555535',
        '5888885555555aaaaaaaaaaaaaaaaa5555555555555555555555555555555555',
        '5888885555555aaaaaaaaaaaaaaaaa5555555555555555555555555555555555',
        '5888885355555aaaaaaaaaaaaaaaaa5355555355555355555355555355555355',
        '5388835555355aaaaaaaaaaaaaaaaa5555355555355555355555355555355555',
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
        '5535555535555535555535555535555535555535555535555535555535555535',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5355555355555355555355555355555355555355555355555355555355555355',
        '5555355555355555355555355555355555355555355555355555355555355555',
        '5555555555555555555555555555555555555555555555555555555555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l6_final_up_reveal():
    # World rows 24..51 revisited on the lower-chamber c7 ascent.
    # Rebuild the entry terrain, erase the old start sprite, and replay the
    # persistent gate edits that lie in this world interval.
    e = np.array(ENTRY_GRID, dtype=int).copy()
    ep = _player_origin(e)
    if ep is not None:
        _erase(e, ep[0], ep[1])
    _toggle_breakable(e, 36, 48, 0)  # c6/world48: sparse -> dense
    _toggle_breakable(e, 36, 24, 0)  # first close c6/world24
    _toggle_breakable(e, 36, 24, 0)  # later open and re-close c6/world24
    _toggle_breakable(e, 36, 24, 0)
    return e[24:52].copy()


def _l6_flip_up4(g, x, y, scroll, under, cap_under):
    # From c7/world78, the world54 wall stops the upward trajectory at world60.
    # The 18px physical rise plus anchor change shifts scroll -52 -> -24.
    pos = _player_origin(g)
    if pos is None:
        return g, under, scroll
    ox, oy = pos
    face = _facing(g)
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[max(0,cy+1):min(63,cy+6), cx:min(64,cx+6)] = 10
    ny = oy
    while _fits(g, ox, ny-6):
        ny -= 6
    shift = (oy-ny) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[shift:63] = old[:63-shift]
    if scroll == -52 and shift == 28:
        g[:shift] = _l6_final_up_reveal()
    else:
        g[:shift] = _wall_world(-scroll-shift, shift)
    g[63] = hud
    new_under = _capture_under(g, ox, 37)
    _draw(g, ox, 37, face)
    return g, new_under, scroll + shift


def _l6_flip_down4(g, x, y, scroll, under):
    # Dense c7 gates at world -48 and -36 bracket the player at world -42.
    # Thus up->down changes only the anchor, shifting scroll 78 -> 68 by 10.
    pos = _player_origin(g)
    if pos is None:
        return g, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[max(0,cy+1):min(63,cy+6), cx:min(64,cx+6)] = 10
    ny = oy
    while _fits(g, ox, ny+6):
        ny += 6
    shift = (ny-oy) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[:63-shift] = old[shift:63]
    if scroll == 78 and shift == 10:
        g[63-shift:63] = _l6_down_reveal5()
    else:
        g[63-shift:63] = _wall_world(63-scroll, shift)
    g[63] = hud
    new_under, cap_under = _draw_down(g, ox, 27, face)
    return g, new_under, cap_under


def _l6_flip_down3(g, x, y, scroll, under):
    # c3 drops one cell from world -30 to -24; the anchor contributes ten
    # further pixels, shifting scroll 66 -> 50.
    pos = _player_origin(g)
    if pos is None:
        return g, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[max(0,cy+1):min(63,cy+6), cx:min(64,cx+6)] = 10
    ny = oy
    while _fits(g, ox, ny+6):
        ny += 6
    shift = (ny-oy) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[:63-shift] = old[shift:63]
    g[63-shift:63] = _l6_down_reveal3()
    g[63] = hud
    new_under, cap_under = _draw_down(g, ox, 27, face)
    return g, new_under, cap_under


def _l6_apply_switches(g, scroll, switches):
    """Render every consumed sidebar switch at its fixed world coordinate."""
    done = set(int(v) for v in switches)
    for wy in done:
        cy = wy + int(scroll)
        lo, hi = max(0,cy+1), min(63,cy+6)
        if lo < hi:
            g[lo:hi, 0:6] = 10
        # Adjacent consumed cells merge through their shared horizontal seam.
        if wy-6 in done and 0 <= cy < 63:
            g[cy,0:6] = 10
    return g


def _l6_flip_up2(g, x, y, scroll, under, cap_under):
    # The closed c6/world12 ceiling prevents physical rise; only the ten-pixel
    # down->up anchor shift moves the viewport.
    pos = _player_origin(g)
    if pos is None:
        return g, under
    ox, oy = pos
    face = _facing(g)
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[max(0,cy+1):min(63,cy+6), cx:min(64,cx+6)] = 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[10:63] = old[:53]
    g[:10] = _l6_up_reveal3()
    g[63] = hud
    new_under = _capture_under(g, ox, 37)
    _draw(g, ox, 37, face)
    return g, new_under


def _l6_flip_up3(g, x, y, scroll, under, cap_under):
    # In the upper zigzag, the closed c4/world-24 gate lets the player rise one
    # cell from world -12 to -18.  The physical 6px rise plus the 10px anchor
    # change moves the camera from scroll38 to scroll54.
    pos = _player_origin(g)
    if pos is None:
        return g, under, scroll
    ox, oy = pos
    face = _facing(g)
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[max(0,cy+1):min(63,cy+6), cx:min(64,cx+6)] = 10
    ny = oy
    while _fits(g, ox, ny-6):
        ny -= 6
    shift = (oy-ny) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[shift:63] = old[:63-shift]
    # These are the already-observed world rows -54..-39.
    if scroll == 38 and shift == 16:
        g[:shift] = _l6_up_reveal4()[12:28]
    else:
        g[:shift] = _wall_world(-scroll-shift, shift)
    g[63] = hud
    new_under = _capture_under(g, ox, 37)
    _draw(g, ox, 37, face)
    return g, new_under, scroll + shift


def _l6_flip_down2(g, x, y, under):
    # General up->down sidebar physics in this section: c6 falls three cells,
    # and the anchor change adds ten pixels, for a 28-pixel camera shift.
    pos = _player_origin(g)
    if pos is None:
        return g, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx = (int(x)//6)*6
    cy = ((int(y)-36)//6)*6 + 36
    g[max(0,cy+1):min(63,cy+6), cx:min(64,cx+6)] = 10
    ny = oy
    while _fits(g, ox, ny+6):
        ny += 6
    shift = (ny-oy) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[:63-shift] = old[shift:63]
    g[63-shift:63] = _l6_down_reveal2()
    g[63] = hud
    new_under, cap_under = _draw_down(g, ox, 27, face)
    return g, new_under, cap_under


def _l6_flip_down(g, x, y, under):
    # Close-gate staging makes the c6 player fall one cell.  Together with the
    # y37 -> y27 anchor change this scrolls the camera down by 16 pixels.
    pos = _player_origin(g)
    if pos is None:
        return g, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx = (int(x)//6)*6
    cy = (int(y)//6)*6
    # A sidebar segment opens only its six-column interior; the right seam and
    # horizontal seams remain, so other visible segments stay usable.
    g[cy+1:min(63,cy+6), cx:min(64,cx+6)] = 10
    ny = oy
    while _fits(g, ox, ny+6):
        ny += 6
    shift = (ny-oy) + 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[:63-shift] = old[shift:63]
    g[63-shift:63] = _l6_down_reveal1()
    g[63] = hud
    new_under, cap_under = _draw_down(g, ox, 27, face)
    return g, new_under, cap_under


def _l6_flip_up(g, x, y, scroll, under, cap_under):
    # At c7 the ceiling blocks physical rise, so only the ten-pixel anchor
    # change moves the camera (-16 -> -6).  Consume the selected sidebar cell
    # while retaining all other segments.
    pos = _player_origin(g)
    if pos is None:
        return g, under
    ox, oy = pos
    face = _facing(g)
    _erase_down(g, ox, oy, under, cap_under)
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    g[cy+1:min(63,cy+6), cx:min(64,cx+6)] = 10
    hud = g[63].copy()
    old = g[:63].copy()
    g[10:63] = old[:53]
    g[:10] = np.array(ENTRY_GRID, dtype=int)[6:16]
    # Adjacent consumed sidebar segments merge: their shared horizontal seam
    # disappears, leaving one continuous eleven-row opening.
    g[31:42, 0:6] = 10
    g[63] = hud
    new_under = _capture_under(g, ox, 37)
    _draw(g, ox, 37, face)
    return g, new_under


def _l7_up_reveal1():
    # World rows -6..-1 exposed when the framed-block canopy stops c5 at
    # world30.  A dense c gate waits in the far-right upper shaft.
    rows = [
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5ccccc5aaaaaaaaaaa5555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5ccccc5aaaaaaaaaaa5555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5ccccc5aaaaaaaaaaa5355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal2():
    # World rows -12..-7 exposed by removing the first canopy cell while the
    # player floats from world30 to world24.
    rows = [
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535555535555535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355555355555355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal3():
    # World rows -18..-13: an open upper room behind a solid top seam.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal4():
    # World rows -24..-19 are a solid bank of dense c gates.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '55355553ccc353ccc353ccc353ccc353ccc353ccc353ccc353ccc353ccc35535',
        '5555555ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5555',
        '5555555ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5555',
        '5355555ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5355',
        '55553553ccc353ccc353ccc353ccc353ccc353ccc353ccc353ccc353ccc35555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal5():
    # World rows -30..-25: another open room, with a cap only over c7+.
    rows = [
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal6():
    # World rows -36..-31: the open-left room is capped over c7 and farther.
    rows = [
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535555535555535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355555355555355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal7():
    # World rows -42..-37.  The framed goal is at c9/world-42, behind
    # the solid c7 barrier; the middle-left region remains open.
    rows = [
        '5555555aaaaaaaaaaa5555555aaaaaaaaaaaaaaaaa5555555555555555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555aaaaaa557555535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaa577755555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaa557555555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555aaaaaaa555a5355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355aaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal8():
    # World rows -54..-43.  A fresh movable framed-f seed is at c3/world-48,
    # and a dense c8/world-48 gate is the eventual downward approach to goal.
    rows = [
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555aaaaaaaaaaa5555555aaaaaaaaaaaaaaaaa5555555555555555555555',
        '5535555aaaaaaaaaaa53fff35aaaaaaaaaaaaaaaaa55355553ccc35535555535',
        '5555555aaaaaaaaaaa5fffff5aaaaaaaaaaaaaaaaa5555555ccccc5555555555',
        '5555555aaaaaaaaaaa5fffff5aaaaaaaaaaaaaaaaa5555555ccccc5555555555',
        '5355555aaaaaaaaaaa5fffff5aaaaaaaaaaaaaaaaa5355555ccccc5355555355',
        '5555355aaaaaaaaaaa53fff35aaaaaaaaaaaaaaaaa55553553ccc35555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal9():
    # World rows -78..-55 are four featureless open logical rows.
    t = _wall_world(-78, 24)
    t[:,7:60] = 10
    return t


def _l7_up_reveal10():
    # World rows -90..-85; only the top seam extends across c1.
    rows = [
        '555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa555555555',
        '5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        '5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        '5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal11():
    # World rows -96..-91: lethal devices guard the far-left and far-right
    # columns, leaving the central surf route open.
    rows = [
        '555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa555555555555555',
        '55355555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55535',
        '55555555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55555',
        '55555555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55555',
        '53555555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55355',
        '55553555b0b5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5b0b55555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal12():
    # World rows -102..-97: the lethal pair moves inward to c2/c8.
    rows = [
        '555555555555555555555555aaaaaaaaaaaaaaaaaaa555555555555555555555',
        '55355555355555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55535555535',
        '55555555555555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55555555555',
        '55555555555555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55555555555',
        '53555553555555fff5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5fff55355555355',
        '55553555553555b0b5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5b0b55555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal13():
    # World rows -108..-103: the lethal pair moves inward again to c3/c7.
    rows = [
        '5555555555555555555555555aaaaaaaaaaaaaaaaa5555555555555555555555',
        '55355555355555355555fff5aaaaaaaaaaaaaaaaaaa5fff55535555535555535',
        '55555555555555555555fff5aaaaaaaaaaaaaaaaaaa5fff55555555555555555',
        '55555555555555555555fff5aaaaaaaaaaaaaaaaaaa5fff55555555555555555',
        '53555553555553555555fff5aaaaaaaaaaaaaaaaaaa5fff55355555355555355',
        '55553555553555553555b0b5aaaaaaaaaaaaaaaaaaa5b0b55555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal14():
    # World rows -114..-109: the hazard funnel closes to the three safe
    # central columns c4-c6.
    rows = [
        '555555555555555555555555555555a55555a555555555555555555555555555',
        '5535555535555535555535555aaaaaaaaaaaaaaaaa5535555535555535555535',
        '5555555555555555555555555aaaaaaaaaaaaaaaaa5555555555555555555555',
        '5555555555555555555555555aaaaaaaaaaaaaaaaa5555555555555555555555',
        '5355555355555355555355555aaaaaaaaaaaaaaaaa5355555355555355555355',
        '5555355555355555355555355aaaaaaaaaaaaaaaaa5555355555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l8_up_reveal1():
    # World rows -18..-1 exposed by the flower-capped c5 entry ascent.
    # Three e gates sit in the world-18 ceiling; the c5-c9 world-12 devices
    # form the lethal bank reached by an uncapped ascent.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        'aaaaaa55355553eee353eee353eee35535555535555535555535555535555535',
        'aaaaaa5555555eeeee5eeeee5eeeee5555555555555555555555555555555555',
        'aaaaaa5555555eeeee5eeeee5eeeee5555555555555555555555555555555555',
        'aaaaaa5355555eeeee5eeeee5eeeee5355555355555355555355555355555355',
        'aaaaaa55553553eee353eee353eee35555355555355555355555355555355555',
        'aaaaaa5555555555555555555555555555555555555555555555555555555555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaa5fff5a5fff5a5fff5a5fff5a5fff55535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaa5fff5a5fff5a5fff5a5fff5a5fff55555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaa5fff5a5fff5a5fff5a5fff5a5fff55555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaa5fff5a5fff5a5fff5a5fff5a5fff55355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaa5b0b5a5b0b5a5b0b5a5b0b5a5b0b55555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaa55555a55555a55555a55555a555555555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal2():
    # World rows -48..-19 exposed by moving from capped c5/w18 into the
    # c4 shaft.  Sidebar switches occur at w-48 and w-24; c5 is a wall
    # through w-42..-24 and c6-c9 carry the w-24 hazard bank.
    rows = [
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaa5555',
        '5388835535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555aaaaa5535',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaa5555',
        '5888885555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaa5555',
        '5888885355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555aaaaa5355',
        '5388835555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355aaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555aaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaa5535555aaaaaaaaaaa5535555aaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555aaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555aaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaa5355555aaaaaaaaaaa5355555aaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaa5555355aaaaaaaaaaa5555355aaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555aaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaa5555',
        '5555555555555aaaaaaaaaaaaaaaaa555555555555a55555a55555a555555555',
        '5388835535555aaaaaaaaaaaaaaaaa55355555b0b5a5b0b5a5b0b5a5b0b55535',
        '5888885555555aaaaaaaaaaaaaaaaa55555555fff5a5fff5a5fff5a5fff55555',
        '5888885555555aaaaaaaaaaaaaaaaa55555555fff5a5fff5a5fff5a5fff55555',
        '5888885355555aaaaaaaaaaaaaaaaa53555555fff5a5fff5a5fff5a5fff55355',
        '5388835555355aaaaaaaaaaaaaaaaa55553555fff5a5fff5a5fff5a5fff55555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal3():
    # World rows -54..-49 exposed by the first staged c4 canopy lift.
    rows = [
        '555555555555555555a55555a55555a55555a55555a555555555555aaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555aaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555aaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555aaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal4():
    # World rows -60..-55: a sidebar switch and a lethal device bank across
    # c2-c7; c8 is solid and the c9 edge shaft remains open.
    rows = [
        '5555555555555555555555555555555555555555555555555555555aaaaa5555',
        '53888355355555fff5a5fff5a5fff5a5fff5a5fff5a5fff55535555aaaaa5535',
        '58888855555555fff5a5fff5a5fff5a5fff5a5fff5a5fff55555555aaaaa5555',
        '58888855555555fff5a5fff5a5fff5a5fff5a5fff5a5fff55555555aaaaa5555',
        '58888853555555fff5a5fff5a5fff5a5fff5a5fff5a5fff55355555aaaaa5355',
        '53888355553555b0b5a5b0b5a5b0b5a5b0b5a5b0b5a5b0b55555355aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal5():
    # World rows -66..-61: a solid c1-c8 bank separates the two edge shafts.
    rows = [
        'aaaaaa5555555555555555555555555555555555555555555555555aaaaa5555',
        'aaaaaa5535555535555535555535555535555535555535555535555aaaaa5535',
        'aaaaaa5555555555555555555555555555555555555555555555555aaaaa5555',
        'aaaaaa5555555555555555555555555555555555555555555555555aaaaa5555',
        'aaaaaa5355555355555355555355555355555355555355555355555aaaaa5355',
        'aaaaaa5555355555355555355555355555355555355555355555355aaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal6():
    # World rows -72..-67: c2-c8 are lethal devices; c0 and c9 remain
    # open shafts separated by the c1 divider.
    rows = [
        'aaaaaa555555555555a55555a55555a55555a55555a55555a55555aaaaaa5555',
        'aaaaaa55355555b0b5a5b0b5a5b0b5a5b0b5a5b0b5a5b0b5a5b0b5aaaaaa5535',
        'aaaaaa55555555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5aaaaaa5555',
        'aaaaaa55555555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5aaaaaa5555',
        'aaaaaa53555555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5aaaaaa5355',
        'aaaaaa55553555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5aaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal7():
    # World rows -78..-73: an open chamber c2-c9 above the world-72
    # hazard bank; the c1 sidebar divider still persists.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal8():
    # World rows -84..-79: sidebar switch plus a full dense-c gate bank
    # across c2-c9, above the open world-78 chamber.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '53888355355553ccc353ccc353ccc353ccc353ccc353ccc353ccc353ccc35535',
        '5888885555555ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5555',
        '5888885555555ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5555',
        '5888885355555ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5ccccc5355',
        '53888355553553ccc353ccc353ccc353ccc353ccc353ccc353ccc353ccc35555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal9():
    # World rows -90..-85 exposed while surfing the c9 edge shaft.  The
    # c1 sidebar divider persists; c2-c9 form an otherwise-open chamber.
    rows = [
        'aaaaaa5555555aaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal10():
    # World rows -96..-91: a drillable e gate at c4 hangs above the open
    # world-90 chamber; the c0 shaft and the c9 edge route remain open.
    rows = [
        'aaaaaa5555555aaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaa53eee35aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaa5eeeee5aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaa5eeeee5aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaa5eeeee5aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaa53eee35aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal11():
    # World rows -102..-97 are an open chamber above the c4/world-96 e
    # gate.  The c1 divider persists and the c9 edge shaft remains open.
    rows = [
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal12():
    # World rows -108..-103 continue the open upper chamber.
    rows = [
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal13():
    # World rows -114..-109 are another open row in the c2-c9 chamber.
    rows = [
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal14():
    # World rows -126..-115: a drillable e gate replaces the c1 divider at
    # world -126, opening the first route into the sidebar.  The static
    # underlay is otherwise open; the c7/world-126 flower is dynamic state.
    rows = [
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa53eee35aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5eeeee5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5eeeee5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5eeeee5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa53eee35aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal15():
    # World rows -132..-127: c0 and c2-c9 are open while c1 remains the
    # divider.  Row -132 is also the bottom seam of the lethal bank above.
    rows = [
        '555555555555555555a55555a55555a55555a55555a55555a55555a555555555',
        'aaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
        'aaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355',
        'aaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_up_reveal16():
    # World rows -156..-133 form the upper ceiling: three complete solid rows
    # followed by lethal f/b0b devices across c2-c9 at world -138.
    out = _wall_world(-156,24)
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '55355555355555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff55535',
        '55555555555555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff55555',
        '55555555555555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff55555',
        '53555553555555fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff5a5fff55355',
        '55553555553555b0b5a5b0b5a5b0b5a5b0b5a5b0b5a5b0b5a5b0b5a5b0b55555',
    ]
    out[18:24] = np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)
    return out


def _l8_down_reveal1():
    # World rows 63..84 exposed by the first sidebar down-flip.  The framed
    # goal sits at c2/world66; a second full bank begins at world72.
    rows = [
        'aaaaaaaaaaaaaaaaaaaaaaaa5555555555555555555555555555555555555555',
        'aaaaaaaaaaaaaaaaaaaaaaaa5355555355555355555355555355555355555355',
        'aaaaaaaaaaaaaaaaaaaaaaaa5555355555355555355555355555355555355555',
        'aaaaaaaaaaaaaa555aaaaaaa5555555555555555555555555555555555555555',
        'aaaaaaaaaaaaa55755aaaaaa5535555535555535555535555535555535555535',
        'aaaaaaaaaaaaa57775aaaaaa5555555555555555555555555555555555555555',
        'aaaaaaaaaaaaa55755aaaaaa5555555555555555555555555555555555555555',
        'aaaaaaaaaaaaaa555aaaaaaa5355555355555355555355555355555355555355',
        'aaaaaaaaaaaaaaaaaaaaaaaa5555355555355555355555355555355555355555',
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
    return np.array([[int(ch,16) for ch in row] for row in rows],dtype=int)


def _l8_flip_down(g, x, y, under):
    """Consume one c0 sidebar switch and drop c3/world36 to world48."""
    pos = _player_origin(g)
    if pos is None:
        return g,under,[10,10,10]
    ox,oy = pos
    face = _facing(g)
    _erase(g,ox,oy,under)
    cy = (int(y)//6)*6
    g[cy:cy+7,0:6] = 10
    hud = g[63].copy()
    old = g[:63].copy()
    out = np.empty_like(g)
    out[:41] = old[22:63]
    out[41:63] = _l8_down_reveal1()
    out[63] = hud
    new_under,cap_under = _draw_down(out,ox,27,face)
    return out,new_under,cap_under


def _l8_switch_key(cx, wy):
    """Compact consumed-switch key; legacy sidebar switches remain row ints."""
    return int(wy) if int(cx) == 0 else (int(cx), int(wy))


def _l8_switch_done(switches, cx, wy):
    key = _l8_switch_key(cx, wy)
    return key in switches


def _l8_high_switch_bank():
    """World -168: c0 wall, with one colour-8 switch in every c1-c9 tile."""
    out = _wall_world(-168, 6)
    source = np.array(ENTRY_GRID, dtype=int)[24:30, 0:6]
    for cx in range(6, 60, 6):
        out[:, cx:cx+6] = source
    return out


def _l8_known_rows(start, n):
    """Static L8 world terrain for all sections observed so far."""
    out = _wall_world(start, n)
    high = _l8_high_switch_bank()
    a, b = max(start, -168), min(start+n, -162)
    if a < b:
        out[a-start:b-start] = high[a+168:b+168]
    upper16 = _l8_up_reveal16()
    a, b = max(start, -156), min(start+n, -132)
    if a < b:
        out[a-start:b-start] = upper16[a+156:b+156]
    upper15 = _l8_up_reveal15()
    a, b = max(start, -132), min(start+n, -126)
    if a < b:
        out[a-start:b-start] = upper15[a+132:b+132]
    upper14 = _l8_up_reveal14()
    a, b = max(start, -126), min(start+n, -114)
    if a < b:
        out[a-start:b-start] = upper14[a+126:b+126]
    upper13 = _l8_up_reveal13()
    a, b = max(start, -114), min(start+n, -108)
    if a < b:
        out[a-start:b-start] = upper13[a+114:b+114]
    upper12 = _l8_up_reveal12()
    a, b = max(start, -108), min(start+n, -102)
    if a < b:
        out[a-start:b-start] = upper12[a+108:b+108]
    upper11 = _l8_up_reveal11()
    a, b = max(start, -102), min(start+n, -96)
    if a < b:
        out[a-start:b-start] = upper11[a+102:b+102]
    upper10 = _l8_up_reveal10()
    a, b = max(start, -96), min(start+n, -90)
    if a < b:
        out[a-start:b-start] = upper10[a+96:b+96]
    upper9 = _l8_up_reveal9()
    a, b = max(start, -90), min(start+n, -84)
    if a < b:
        out[a-start:b-start] = upper9[a+90:b+90]
    upper8 = _l8_up_reveal8()
    a, b = max(start, -84), min(start+n, -78)
    if a < b:
        out[a-start:b-start] = upper8[a+84:b+84]
    upper7 = _l8_up_reveal7()
    a, b = max(start, -78), min(start+n, -72)
    if a < b:
        out[a-start:b-start] = upper7[a+78:b+78]
    upper6 = _l8_up_reveal6()
    a, b = max(start, -72), min(start+n, -66)
    if a < b:
        out[a-start:b-start] = upper6[a+72:b+72]
    upper5 = _l8_up_reveal5()
    a, b = max(start, -66), min(start+n, -60)
    if a < b:
        out[a-start:b-start] = upper5[a+66:b+66]
    upper4 = _l8_up_reveal4()
    a, b = max(start, -60), min(start+n, -54)
    if a < b:
        out[a-start:b-start] = upper4[a+60:b+60]
    upper3 = _l8_up_reveal3()
    a, b = max(start, -54), min(start+n, -48)
    if a < b:
        out[a-start:b-start] = upper3[a+54:b+54]
    upper2 = _l8_up_reveal2()
    a, b = max(start, -48), min(start+n, -18)
    if a < b:
        out[a-start:b-start] = upper2[a+48:b+48]
    upper = _l8_up_reveal1()
    a, b = max(start, -18), min(start+n, 0)
    if a < b:
        out[a-start:b-start] = upper[a+18:b+18]
    # Entry world 0..62, with rendered dynamic objects removed.
    a, b = max(start, 0), min(start+n, 63)
    if a < b:
        e = np.array(ENTRY_GRID, dtype=int).copy()
        ep = _player_origin(e)
        if ep is not None:
            _erase(e, ep[0], ep[1])
        for bx, by in _l7_block_cells(e):
            e[by:by+7, bx:bx+7] = 10
        out[a-start:b-start] = e[a:b]
    # Lower chamber first exposed by the entry down-flip.
    known = _l8_down_reveal1()
    a, b = max(start, 63), min(start+n, 63+len(known))
    if a < b:
        out[a-start:b-start] = known[a-63:b-63]
    return out


def _l8_compose_view(g, scroll, blocks, opened=(), switches=()):
    """Render authoritative L8 terrain, consumed switches, drills, flowers."""
    out = np.empty_like(g)
    out[:63] = _l8_known_rows(-scroll, 63)
    out[63] = g[63]
    for sw in switches:
        if isinstance(sw, (tuple, list)):
            sx, swy = int(sw[0]), int(sw[1])
        else:
            sx, swy = 0, int(sw)
        sy = swy + scroll
        y0,y1 = max(0,sy),min(63,sy+7)
        x0,x1 = max(0,sx),min(64,sx+6)
        if y0 < y1 and x0 < x1:
            out[y0:y1,x0:x1] = 10
    for ex, ewy in {tuple(v) for v in opened}:
        sy = ewy + scroll
        if sy < 63 and sy+6 >= 0:
            _toggle_breakable(out, ex, sy, scroll)
            # A sparse gate whose body is exactly one cell above the viewport
            # still opens its shared bottom seam when the visible cell below is
            # open.  Its centre is clipped, so _toggle_breakable cannot sample it.
            if sy == -6:
                below = _l8_known_rows(ewy+7,5)[:,ex+1:ex+6]
                if np.all(below == 10):
                    out[0,ex+1:ex+6] = 10
    for bx, by in {tuple(v) for v in blocks}:
        sy = by + scroll
        if sy < 63 and sy+6 >= 0:
            _l7_draw_block(out, bx, sy)
    return out


def _l8_click_block(g, x, y, scroll, blocks, opened=(), switches=()):
    """Split an L8 flower under upward gravity."""
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return None
    ox, oy = pos
    face = _facing(g)
    cells = {tuple(v) for v in blocks}
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    wy = cy-scroll
    if (cx,wy) not in cells:
        return None
    cells.remove((cx,wy))
    player_cell = ((ox//6)*6, ((oy-scroll)//6)*6)
    for tx,ty in ((cx-6,wy),(cx+6,wy),(cx,wy-6),(cx,wy+6)):
        terrain = (_l8_known_rows(ty+1,5)[:,tx+1:tx+6]
                   if 0 <= tx and tx+6 < 64 else None)
        terrain_open = (tx == -6 or (terrain is not None and np.all(terrain == 10)))
        # A consumed colour-8 sidebar switch leaves ordinary open terrain;
        # flowers may subsequently grow through that vacated world cell.
        if _l8_switch_done(switches, tx, ty):
            terrain_open = True
        if (tx,ty) in {tuple(v) for v in opened}:
            # Drilled e gates become genuine empty terrain, but a sparse c gate
            # remains a gate layer: players traverse it while flower children
            # are suppressed in both its dense and sparse states.
            static_full = (_l8_known_rows(ty,6)[:,tx:tx+6]
                           if 0 <= tx and tx+6 <= 64 else np.empty((0,0)))
            if np.any(static_full == 14):
                terrain_open = True
        if (terrain_open and (tx,ty) not in cells
                and (tx,ty) != player_cell):
            cells.add((tx,ty))
    # Resolve the ascent in world coordinates, then compose the new camera
    # view authoritatively.  Shifting a clipped viewport loses off-screen gate
    # and consumed-switch seams at the newly exposed top row.
    pcx, pwy = player_cell
    opened_set = {tuple(v) for v in opened}
    dead = level_up = False
    while _l8_tile_kind(pcx,pwy-6,cells,opened_set,switches) == "open":
        pwy -= 6
    hit = _l8_tile_kind(pcx,pwy-6,cells,opened_set,switches)
    if hit == "hazard":
        dead = True
    elif hit == "goal":
        level_up = True
    new_scroll = 36-pwy
    out = _l8_compose_view(g,new_scroll,cells,opened_set,switches)
    new_under = _capture_under(out,pcx+1,37)
    _draw(out,pcx+1,37,face)
    result = (out,new_scroll,dead,level_up,new_under)
    return result, sorted(cells)


def _l8_tile_kind(cx, wy, blocks, opened, switches=()):
    key = (cx,wy)
    if key in {tuple(v) for v in blocks}:
        return "block"
    if key in {tuple(v) for v in opened}:
        return "open"
    if _l8_switch_done(switches, cx, wy):
        return "open"
    if not (0 <= cx and cx+6 < 64):
        return "wall"
    inner = _l8_known_rows(wy+1,5)[:,cx+1:cx+6]
    if np.any(inner == 7):
        return "goal"
    if np.any(inner == 15):
        return "hazard"
    if np.all(inner == 10):
        return "open"
    return "wall"


def _l8_click_block_down(g, x, y, scroll, blocks, opened=(), switches=()):
    """Split an L8 flower, then resolve downward gravity in world space."""
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return None
    ox,oy = pos
    face = _facing(g)
    cells = {tuple(v) for v in blocks}
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    wy = cy-scroll
    if (cx,wy) not in cells:
        return None
    cells.remove((cx,wy))
    opened_set = {tuple(v) for v in opened}
    player_cell = ((ox//6)*6, ((oy-scroll)//6)*6)
    for tx,ty in ((cx-6,wy),(cx+6,wy),(cx,wy-6),(cx,wy+6)):
        terrain = (_l8_known_rows(ty+1,5)[:,tx+1:tx+6]
                   if 0 <= tx and tx+6 < 64 else None)
        terrain_open = (tx == -6 or (terrain is not None and np.all(terrain == 10)))
        # A consumed colour-8 sidebar switch leaves ordinary open terrain;
        # flowers may subsequently grow through that vacated world cell.
        if _l8_switch_done(switches, tx, ty):
            terrain_open = True
        if (tx,ty) in opened_set:
            static_full = (_l8_known_rows(ty,6)[:,tx:tx+6]
                           if 0 <= tx and tx+6 <= 64 else np.empty((0,0)))
            if np.any(static_full == 14):
                terrain_open = True
        if (terrain_open and (tx,ty) not in cells
                and (tx,ty) != player_cell):
            cells.add((tx,ty))
    pcx,pwy = player_cell
    dead=level_up=False
    while _l8_tile_kind(pcx,pwy+6,cells,opened_set,switches) == "open":
        pwy += 6
    hit = _l8_tile_kind(pcx,pwy+6,cells,opened_set,switches)
    if hit == "hazard":
        dead=True
    elif hit == "goal":
        level_up=True
    new_scroll = 26-pwy
    out = _l8_compose_view(g,new_scroll,cells,opened_set,switches)
    under,cap = _draw_down(out,pcx+1,27,face)
    return (out,new_scroll,dead,level_up,under,cap),sorted(cells)


def _l8_move_and_fall(g, dx, scroll, under0, cap0,
                      blocks, opened, switches):
    pos = _player_origin(g)
    if pos is None:
        return g,scroll,False,False,under0,cap0
    ox,oy = pos
    face = 1 if dx>0 else -1
    _erase_down(g,ox,oy,under0,cap0)
    nx=ox+dx
    if not _fits(g,nx,oy):
        nx=ox
    cx=(nx//6)*6
    pwy=((oy-scroll)//6)*6
    dead=level_up=False
    while _l8_tile_kind(cx,pwy+6,blocks,opened,switches) == "open":
        pwy += 6
    hit=_l8_tile_kind(cx,pwy+6,blocks,opened,switches)
    if hit=="hazard": dead=True
    elif hit=="goal": level_up=True
    new_scroll=26-pwy
    out=_l8_compose_view(g,new_scroll,blocks,opened,switches)
    under,cap=_draw_down(out,cx+1,27,face)
    return out,new_scroll,dead,level_up,under,cap


def _l8_flip_down_general(g, scroll, blocks, opened, switches):
    pos=_player_origin(g)
    if pos is None:
        return g,scroll,False,False,[[10]*5 for _ in range(5)],[10,10,10]
    ox,oy=pos
    face=_facing(g)
    cx=(ox//6)*6
    pwy=((oy-scroll)//6)*6
    dead=level_up=False
    while _l8_tile_kind(cx,pwy+6,blocks,opened,switches)=="open":
        pwy += 6
    hit=_l8_tile_kind(cx,pwy+6,blocks,opened,switches)
    if hit=="hazard": dead=True
    elif hit=="goal": level_up=True
    new_scroll=26-pwy
    out=_l8_compose_view(g,new_scroll,blocks,opened,switches)
    under,cap=_draw_down(out,cx+1,27,face)
    return out,new_scroll,dead,level_up,under,cap


def _l8_flip_up_general(g, scroll, blocks, opened, switches):
    """Reverse L8 gravity upward and resolve the world-space ascent."""
    pos = _player_origin(g)
    if pos is None:
        return g,scroll,False,False,[[10]*5 for _ in range(5)]
    ox,oy = pos
    face = _facing(g)
    cx = (ox//6)*6
    pwy = ((oy-scroll)//6)*6
    dead=level_up=False
    while _l8_tile_kind(cx,pwy-6,blocks,opened,switches) == "open":
        pwy -= 6
    hit = _l8_tile_kind(cx,pwy-6,blocks,opened,switches)
    if hit == "hazard":
        dead=True
    elif hit == "goal":
        level_up=True
    # Up-gravity sprites are kept at origin y37, one pixel inside their cell.
    new_scroll = 36-pwy
    out = _l8_compose_view(g,new_scroll,blocks,opened,switches)
    new_under = _capture_under(out,cx+1,37)
    _draw(out,cx+1,37,face)
    return out,new_scroll,dead,level_up,new_under


def _l7_down_reveal1():
    # World rows 79..84, first visible below the four-row world54 wall bank,
    # are a completely open lower chamber.
    return np.full((6,64),10,dtype=int)


def _l7_up_reveal16():
    # World rows -144..-139: a colour-8 gravity switch is embedded in the
    # otherwise-solid c5 ceiling.  Surfing the central funnel reveals it.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555535555388835535555535555535555535555535',
        '5555555555555555555555555555555888885555555555555555555555555555',
        '5555555555555555555555555555555888885555555555555555555555555555',
        '5355555355555355555355555355555888885355555355555355555355555355',
        '5555355555355555355555355555355388835555355555355555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_up_reveal15():
    # World rows -120..-115 are a complete ceiling: lethal devices fill the
    # three central openings c4-c6 and ordinary walls fill both sides.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '55355555355555355555355555fff5a5fff5a5fff55535555535555535555535',
        '55555555555555555555555555fff5a5fff5a5fff55555555555555555555555',
        '55555555555555555555555555fff5a5fff5a5fff55555555555555555555555',
        '53555553555553555553555555fff5a5fff5a5fff55355555355555355555355',
        '55553555553555553555553555b0b5a5b0b5a5b0b55555355555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l7_known_rows(start, n):
    """Static L7 world terrain, with every movable seed/player removed."""
    out = _wall_world(start, n)
    # The observed upper chamber is open only from world -120 through -55.
    # Above the lethal world-120 ceiling, world -126 is an ordinary solid wall
    # row (confirmed when the player first surfaced to world -90); retain the
    # periodic wall base there instead of extrapolating open space forever.
    for iy in range(n):
        if -120 <= start+iy <= -55:
            out[iy,7:60] = 10
    sections = ((79, _l7_down_reveal1()),
                (-144, _l7_up_reveal16()),
                (-120, _l7_up_reveal15()), (-114, _l7_up_reveal14()),
                (-108, _l7_up_reveal13()),
                (-102, _l7_up_reveal12()),
                (-96, _l7_up_reveal11()),
                (-90, _l7_up_reveal10()),
                (-78, _l7_up_reveal9()),
                (-54, _l7_up_reveal8()),
                (-42, _l7_up_reveal7()),
                (-36, _l7_up_reveal6()), (-30, _l7_up_reveal5()),
                (-24, _l7_up_reveal4()), (-18, _l7_up_reveal3()),
                (-12, _l7_up_reveal2()), (-6, _l7_up_reveal1()))
    seed_world = []
    for base, known in sections:
        for bx,sy in _l7_block_cells(known):
            seed_world.append((bx,base+sy))
        a, b = max(start, base), min(start+n, base+len(known))
        if a < b:
            out[a-start:b-start] = known[a-base:b-base]
    a, b = max(start, 0), min(start+n, 63)
    if a < b:
        e = np.array(ENTRY_GRID, dtype=int).copy()
        ep = _player_origin(e)
        if ep is not None:
            _erase(e, ep[0], ep[1])
        for bx,by in _l7_block_cells(e):
            seed_world.append((bx,by))
            e[by:by+7,bx:bx+7] = 10
        out[a-start:b-start] = e[a:b]
    # Remove each known dynamic seed by WORLD coordinates, so even an unaligned
    # five-row terrain query (used to validate a neighbour) sees open underlay.
    for bx,by in seed_world:
        lo, hi = max(start,by), min(start+n,by+7)
        if lo < hi:
            out[lo-start:hi-start,bx:bx+7] = 10
    return out


def _l7_block_cells(g):
    """Locate the framed 7x7 f blocks (distinct from f/b0b devices)."""
    out = set()
    for cy in range(0, 60, 6):
        for cx in range(0, 60, 6):
            if cy+6 >= 63 or cx+6 >= 64:
                continue
            inner = g[cy+1:cy+6, cx+1:cx+6]
            if int(np.sum(inner == 15)) == 21 and not np.any(inner == 11):
                out.add((cx,cy))
    return out


def _l7_initial_blocks():
    """All L7 seed blocks, including the one initially above the viewport."""
    out = set(_l7_block_cells(np.array(ENTRY_GRID, dtype=int)))
    hidden = _l7_up_reveal8()
    for bx, sy in _l7_block_cells(hidden):
        out.add((bx, -54+sy))
    return sorted(out)


def _l7_initial_sparse():
    """Initial sparse-c gates in world coordinates (normally none on L7)."""
    out = set()
    for wy in range(-120, 61, 6):
        row = _l7_known_rows(wy, 6)
        for cx in range(0,60,6):
            n = int(np.sum(row[:,cx:cx+6] == 12))
            if 0 < n <= 5:
                out.add((cx,wy))
    return sorted(out)


def _l7_draw_block(g, cx, cy):
    # Clip at every viewport edge.  In L8 a flower on logical c0 can grow one
    # cell beyond the left edge; only that child's right-hand frame seam is
    # visible at x=0.
    tile = np.full((7,7), 5, dtype=int)
    tile[1,1] = tile[1,5] = tile[5,1] = tile[5,5] = 3
    tile[1,2:5] = 15
    tile[5,2:5] = 15
    tile[2:5,1:6] = 15
    y0,y1 = max(0,cy),min(63,cy+7)
    x0,x1 = max(0,cx),min(64,cx+7)
    if y0 < y1 and x0 < x1:
        g[y0:y1,x0:x1] = tile[y0-cy:y1-cy, x0-cx:x1-cx]


def _l7_screen_blocks(g, scroll):
    """Visible L7 blocks plus the one-cell fragments just beyond each edge."""
    terrain_view = _l7_known_rows(-scroll, 63)
    cells = _l7_block_cells(g)
    # A block one cell above contributes only its solid bottom seam at y=0.
    # Require open static underlay and no full block beginning at y=0.
    for bx in range(0,60,6):
        if ((bx,0) not in cells
                and np.all(g[0,bx+1:bx+6] == 5)
                and np.all(terrain_view[0,bx+1:bx+6] == 10)):
            cells.add((bx,-6))
    # A bottom-clipped block still exposes some of its f interior.
    cy_edge = 60
    for bx in range(0,60,6):
        vis = g[cy_edge+1:63,bx+1:bx+6]
        base = terrain_view[cy_edge+1:63,bx+1:bx+6]
        if np.any(vis == 15) and np.all(base == 10):
            cells.add((bx,cy_edge))
    return cells


def _l7_cell_open(cx, wy, sparse):
    if not (0 <= cx and cx+6 < 64):
        return False
    if (cx,wy) in sparse:
        return True
    terrain = _l7_known_rows(wy+1, 5)[:,cx+1:cx+6]
    return bool(np.all(terrain == 10))


def _l7_draw_sparse_gate(g, cx, wy, scroll, l7_sparse):
    """Render an explicitly-open c gate, including viewport-clipped gates."""
    sparse = {tuple(v) for v in l7_sparse}
    sy = wy + scroll
    # Clear its five-pixel interior and open a shared seam exactly when the
    # neighbouring logical cell is traversable.  Movable blocks are drawn
    # afterward and naturally close any seam they occupy.
    y0, y1 = max(0,sy+1), min(63,sy+6)
    if y0 < y1:
        g[y0:y1,cx+1:cx+6] = 10
    left = _l7_cell_open(cx-6,wy,sparse)
    right = _l7_cell_open(cx+6,wy,sparse)
    top = _l7_cell_open(cx,wy-6,sparse)
    bottom = _l7_cell_open(cx,wy+6,sparse)
    if left and y0 < y1:
        g[y0:y1,cx] = 10
    if right and y0 < y1 and cx+6 < 64:
        g[y0:y1,cx+6] = 10
    if top and 0 <= sy < 63:
        g[sy,cx+1:cx+6] = 10
    if bottom and 0 <= sy+6 < 63:
        g[sy+6,cx+1:cx+6] = 10
    if left and top and 0 <= sy < 63: g[sy,cx] = 10
    if right and top and 0 <= sy < 63 and cx+6 < 64: g[sy,cx+6] = 10
    if left and bottom and 0 <= sy+6 < 63: g[sy+6,cx] = 10
    if right and bottom and 0 <= sy+6 < 63 and cx+6 < 64: g[sy+6,cx+6] = 10
    for px,py in ((cx+2,sy+2),(cx+4,sy+2),(cx+3,sy+3),
                  (cx+2,sy+4),(cx+4,sy+4)):
        if 0 <= py < 63 and 0 <= px < 64:
            g[py,px] = 12


def _l7_click_block(g, x, y, scroll, l7_blocks, l7_sparse):
    """Split a movable framed-f block in world coordinates at any camera offset."""
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return None
    ox, oy = pos
    face = _facing(g)
    terrain_view = _l7_known_rows(-scroll, 63)
    cells = {tuple(v) for v in l7_blocks}
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    wy = cy-scroll
    if (cx,wy) not in cells:
        return None

    cells.remove((cx,wy))
    # A child is born only in a statically open, dynamically empty cell.  The
    # player itself counts as occupied: this suppresses the child below an
    # overhead split and lets upward gravity lift the player into that vacancy.
    player_cell = ((ox//6)*6, ((oy-scroll)//6)*6)
    for tx,ty in ((cx-6,wy),(cx+6,wy),(cx,wy-6),(cx,wy+6)):
        terrain = _l7_known_rows(ty+1, 5)[:,tx+1:tx+6] if 0 <= tx and tx+6 < 64 else None
        valid = (terrain is not None and np.all(terrain == 10)
                 and (tx,ty) not in cells and (tx,ty) != player_cell)
        if valid:
            cells.add((tx,ty))

    out = np.empty_like(g)
    out[:63] = terrain_view
    out[63] = g[63]
    # Reapply every toggled sparse gate from authoritative world state.  This
    # matters when the avatar covers all five c pixels: the rendered viewport
    # alone then cannot tell an open gate from its dense static form.
    for gx, gwy in {tuple(v) for v in l7_sparse}:
        sy = gwy + scroll
        if sy < 63 and sy+6 >= 0:
            _l7_draw_sparse_gate(out, gx, gwy, scroll, l7_sparse)
    for bx,by in cells:
        sy = by+scroll
        if sy < 63 and sy+6 >= 0:
            _l7_draw_block(out,bx,sy)
    result = _finish_float(out, ox, oy, scroll, face, cells)
    return result, sorted(cells)


def _l7_click_block_down(g, x, y, scroll, l7_blocks, l7_sparse):
    """Split an L7 flower in world coordinates, then resolve downward fall."""
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return None
    ox, oy = pos
    face = _facing(g)
    cells = {tuple(v) for v in l7_blocks}
    cx = (int(x)//6)*6
    cy = ((int(y)-scroll)//6)*6 + scroll
    wy = cy-scroll
    if (cx,wy) not in cells:
        return None
    cells.remove((cx,wy))
    sparse = {tuple(v) for v in l7_sparse}
    player_cell = ((ox//6)*6, ((oy-scroll)//6)*6)
    for tx,ty in ((cx-6,wy),(cx+6,wy),(cx,wy-6),(cx,wy+6)):
        terrain = (_l7_known_rows(ty+1,5)[:,tx+1:tx+6]
                   if 0 <= tx and tx+6 < 64 else None)
        # Both dense and sparse c gates suppress flower children; only static
        # background-a cells accept growth.
        valid = (terrain is not None and np.all(terrain == 10)
                 and (tx,ty) not in cells and (tx,ty) != player_cell)
        if valid:
            cells.add((tx,ty))

    pcx, pwy = player_cell
    dead = False
    level_up = False
    while _l7_tile_kind(pcx,pwy+6,cells,sparse) == "open":
        pwy += 6
    hit = _l7_tile_kind(pcx,pwy+6,cells,sparse)
    if hit == "hazard":
        dead = True
    elif hit == "goal":
        level_up = True
    start_wy = ((oy-scroll)//6)*6
    new_scroll = scroll-(pwy-start_wy)
    out = _l7_compose_view(g,new_scroll,cells,sparse)
    under, cap_under = _draw_down(out,pcx+1,oy,face)
    return (out,new_scroll,dead,level_up,under,cap_under), sorted(cells)


def _l7_compose_view(g, scroll, l7_blocks, l7_sparse):
    """Render authoritative L7 terrain, gates, and flowers at a camera offset."""
    out = np.empty_like(g)
    out[:63] = _l7_known_rows(-scroll, 63)
    out[63] = g[63]
    for gx, gwy in {tuple(v) for v in l7_sparse}:
        sy = gwy + scroll
        if sy < 63 and sy+6 >= 0:
            _l7_draw_sparse_gate(out, gx, gwy, scroll, l7_sparse)
    for bx, by in {tuple(v) for v in l7_blocks}:
        sy = by + scroll
        if sy < 63 and sy+6 >= 0:
            _l7_draw_block(out, bx,sy)
    return out


def _l7_tile_kind(cx, wy, l7_blocks, l7_sparse):
    """Classify one aligned world cell for L7 player/gravity physics."""
    key = (cx,wy)
    if key in {tuple(v) for v in l7_blocks}:
        return "block"
    if key in {tuple(v) for v in l7_sparse}:
        return "open"
    if not (0 <= cx and cx+6 < 64):
        return "wall"
    inner = _l7_known_rows(wy+1,5)[:,cx+1:cx+6]
    if np.any(inner == 7):
        return "goal"
    if np.any(inner == 15):
        return "hazard"
    if np.all(inner == 10):
        return "open"
    # A canonical sparse c has only five coloured interior pixels.
    if 0 < int(np.sum(inner == 12)) <= 5:
        return "open"
    return "wall"


def _l7_move_and_fall(g, dx, scroll, under0, cap0,
                      l7_blocks, l7_sparse):
    """World-coordinate horizontal move plus downward gravity for L7."""
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, False, False, [[10]*5 for _ in range(5)], [10,10,10]
    ox, oy = pos
    face = 1 if dx > 0 else -1
    _erase_down(g, ox, oy, under0, cap0)
    # The authoritative redraw below makes the saved pixel underlay irrelevant;
    # use the rendered frame only to preserve the exact shaped horizontal fit.
    nx = ox + dx
    if not _fits(g,nx,oy):
        nx = ox
    cx = (nx//6)*6
    wy = ((oy-scroll)//6)*6
    dead = False
    level_up = False
    while _l7_tile_kind(cx,wy+6,l7_blocks,l7_sparse) == "open":
        wy += 6
    hit = _l7_tile_kind(cx,wy+6,l7_blocks,l7_sparse)
    if hit == "hazard":
        dead = True
    elif hit == "goal":
        level_up = True
    fall = wy - ((oy-scroll)//6)*6
    new_scroll = scroll-fall
    out = _l7_compose_view(g,new_scroll,l7_blocks,l7_sparse)
    under, cap_under = _draw_down(out,cx+1,oy,face)
    return out,new_scroll,dead,level_up,under,cap_under


def _l7_flip_down(g, scroll, l7_blocks, l7_sparse):
    """Consume the world-144 switch and fall to the first staged/static floor."""
    pos = _player_origin(g)
    if pos is None:
        return (g,scroll,False,False,[[10]*5 for _ in range(5)],
                [10,10,10])
    ox, oy = pos
    face = _facing(g)
    cx = (ox//6)*6
    wy = ((oy-scroll)//6)*6
    dead = False
    level_up = False
    while _l7_tile_kind(cx,wy+6,l7_blocks,l7_sparse) == "open":
        wy += 6
    hit = _l7_tile_kind(cx,wy+6,l7_blocks,l7_sparse)
    if hit == "hazard":
        dead = True
    elif hit == "goal":
        level_up = True
    # Down-gravity sprites are anchored at pixel y27, one pixel inside their
    # logical world cell, hence scroll = 26 - cell_world.
    new_scroll = 26-wy
    out = _l7_compose_view(g,new_scroll,l7_blocks,l7_sparse)
    new_under, cap_under = _draw_down(out,cx+1,27,face)
    return out,new_scroll,dead,level_up,new_under,cap_under


def _l5_up_reveal1():
    # World rows -12..-1, exposed by climbing the consumed c6 switch shaft.
    # Four f devices cap the left columns; c6-c8 remain the safe upper route.
    rows = [
        '555555555555555555a55555a55555a55555aaaaaaaaaaaaaaaaaa5555555555',
        '55355555355555b0b5a5b0b5a5b0b5a5b0b5aaaaaaaaaaaaaaaaaa5535555535',
        '55555555555555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaaaaaaaa5555555555',
        '55555555555555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaaaaaaaa5555555555',
        '53555553555555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaaaaaaaa5355555355',
        '55553555553555fff5a5fff5a5fff5a5fff5aaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555555555555555555555555555aaaaa5555555555555555555555',
        '5535555535555535555535555535555535555aaaaa5535555535555535555535',
        '5555555555555555555555555555555555555aaaaa5555555555555555555555',
        '5555555555555555555555555555555555555aaaaa5555555555555555555555',
        '5355555355555355555355555355555355555aaaaa5355555355555355555355',
        '5555355555355555355555355555355555355aaaaa5555355555355555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l5_up_reveal2():
    # World rows -30..-13, exposed by entering the upper c8 shaft.  A full
    # sparse-c row crosses world -24, except for the closed c6 gate.
    rows = [
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5535555535',
        '5555555555555acacaaacacaaacacaaacaca5ccccc5acacaaacaca5555555555',
        '5555555555555aacaaaaacaaaaacaaaaacaa5ccccc5aacaaaaacaa5555555555',
        '5355555355555acacaaacacaaacacaaacaca5ccccc5acacaaacaca5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaa53ccc35aaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaa5555555aaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l5_up_reveal3():
    # World rows -54..-31, exposed below the closed c6 gate.  The next hazard
    # bank covers c5-c8; c4 is its sole safe vertical shaft.
    rows = [
        '5555555555555555555555555555555555555555555aaaaaaaaaaa5555555555',
        '5535555535555535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555555555555555aaaaa5555555555555555555555555555555555',
        '5535555535555535555535555aaaaa5535555535555535555535555535555535',
        '5555555555555555555555555aaaaa5555555555555555555555555555555555',
        '5555555555555555555555555aaaaa5555555555555555555555555555555555',
        '5355555355555355555355555aaaaa5355555355555355555355555355555355',
        '5555355555355555355555355aaaaa5555355555355555355555355555355555',
        '5555555555555555555555555aaaaa5555555555555555555555555555555555',
        '5535555535555535555535555aaaaaa5fff5a5fff5a5fff5a5fff55535555535',
        '5555555555555555555555555aaaaaa5fff5a5fff5a5fff5a5fff55555555555',
        '5555555555555555555555555aaaaaa5fff5a5fff5a5fff5a5fff55555555555',
        '5355555355555355555355555aaaaaa5fff5a5fff5a5fff5a5fff55355555355',
        '5555355555355555355555355aaaaaa5b0b5a5b0b5a5b0b5a5b0b55555355555',
        '5555555555555555555555555aaaaaa55555a55555a55555a555555555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l5_up_reveal4():
    # World rows -90..-55.  The c4 safe shaft ends at a long solid section;
    # only c7-c8 open in its lowest cell to form the next switchback.
    t = _wall_world(-90, 36)
    t[31:36,43:54] = 10
    return t


def _l5_up_reveal5():
    # World rows -96..-91: the third gravity switch, framed in c8.
    rows = [
        '5555555555555555555555555555555555555555555555555555555555555555',
        '5535555535555535555535555535555535555535555535555388835535555535',
        '5555555555555555555555555555555555555555555555555888885555555555',
        '5555555555555555555555555555555555555555555555555888885555555555',
        '5355555355555355555355555355555355555355555355555888885355555355',
        '5555355555355555355555355555355555355555355555355388835555355555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l5_known_rows(start, n):
    # Compose already observed L5 world rows for later downward revisits.
    out = _wall_world(start, n)
    sections = [
        (-96, _l5_up_reveal5()),
        (-90, _l5_up_reveal4()),
        (-54, _l5_up_reveal3()),
        (-30, _l5_up_reveal2()),
        (-12, _l5_up_reveal1()),
    ]
    for base, known in sections:
        a, b = max(start, base), min(start+n, base+len(known))
        if a < b:
            out[a-start:b-start] = known[a-base:b-base]
    # Entry-world terrain after both early switches: remove the original player
    # and the consumed c6 switch, but otherwise retain its grounded layout.
    a, b = max(start, 0), min(start+n, 63)
    if a < b:
        e = np.array(ENTRY_GRID, dtype=int).copy()
        ep = _player_origin(e)
        if ep is not None:
            _erase(e, ep[0], ep[1])
        pts = np.argwhere(e[:63] == 8)
        if len(pts):
            y0, x0 = pts.min(axis=0)
            y1, x1 = pts.max(axis=0)
            e[max(0,int(y0)-1):min(63,int(y1)+2),
              int(x0):int(x1)+1] = 10
        out[a-start:b-start] = e[a:b]
    # Hidden goal chamber after the c4 switch has been consumed.  Preserve the
    # c2 goal but clear the switch's five-column frame to reopen the corridor.
    a, b = max(start, 63), min(start+n, 121)
    if a < b:
        d = _l5_down_reveal1().copy()
        pts = np.argwhere(d == 8)
        if len(pts):
            y0, x0 = pts.min(axis=0)
            y1, x1 = pts.max(axis=0)
            # Open neighbours on both sides remove the vertical seams,
            # while the solid ceiling/floor seams above and below remain.
            d[int(y0):int(y1)+1,
              max(0,int(x0)-1):min(64,int(x1)+2)] = 10
        out[a-start:b-start] = d[a-63:b-63]
    return out


def _l5_down_reveal1():
    # World rows 63..120 exposed by the entry c6 switch.  Most are periodic
    # wall; a c8 shaft leads to the hidden goal/switch chamber at world84.
    t = _wall_world(63, 58)
    t[:16,49:54] = 10
    rows = [
        '5535555aaaaaaaaaaaaaaaaa5535555aaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555aaaaaaaaaaaaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555aaaaaaaaaaaaaaaaa5355555aaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355aaaaaaaaaaaaaaaaa5555355aaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555aaaaaaa555aaaaaaa5555555aaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5535555aaaaaa55755aaaaaa5388835aaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555aaaaaa57775aaaaaa5888885aaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555aaaaaa55755aaaaaa5888885aaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555aaaaaaa555aaaaaaa5888885aaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355aaaaaaaaaaaaaaaaa5388835aaaaaaaaaaaaaaaaaaaaaaa5555355555',
    ]
    t[16:27] = np.array([[int(ch,16) for ch in row] for row in rows],
                        dtype=int)
    return t

def _l5_flip_down(g, under):
    # At c8 the player falls 48px through the lower hazard row.  Switching from
    # the y37 up-anchor to y27 adds ten camera pixels, so scroll becomes -58.
    pos = _player_origin(g)
    if pos is None:
        return g, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    out = np.empty((64,64), dtype=int)
    out[:5] = g[58:63]
    out[5:63] = _l5_down_reveal1()
    out[63] = g[63]
    new_under, cap_under = _draw_down(out, ox, 27, face)
    return out, new_under, cap_under

def _l5_flip_up(g, under, cap_under):
    # The hidden c4 switch reverses gravity while the player is aligned with
    # the safe c8 shaft.  It climbs 48px, and changing from the y27 down-anchor
    # to the y37 up-anchor contributes the other ten pixels: scroll -58 -> 0.
    # Reconstruct the revisited entry viewport from ENTRY_GRID, consuming the
    # entry c6 switch and relocating the player from its original c3 start.
    pos = _player_origin(g)
    if pos is None:
        return g, under
    ox, oy = pos
    face = _facing(g)
    out = np.array(ENTRY_GRID, dtype=int).copy()

    # Restore the entry player's old footprint to the open chamber.
    ep = _player_origin(out)
    if ep is not None:
        _erase(out, ep[0], ep[1])

    # Consume the sole entry-viewport colour-8 switch, including its frame.
    pts = np.argwhere(out[:63] == 8)
    if len(pts):
        y0, x0 = pts.min(axis=0)
        y1, x1 = pts.max(axis=0)
        # The switch occupies a five-column cell; its colour-8 core
        # already spans the full width, while the 5/3 frame adds one row above
        # and below.
        out[max(0,int(y0)-1):min(63,int(y1)+2),
            max(0,int(x0)):min(64,int(x1)+1)] = 10

    # The budget meter is global and is not reset by camera reconstruction.
    out[63] = g[63]
    new_under = [[10]*5 for _ in range(5)]
    _draw(out, ox, 37, face)
    return out, new_under


def _l5_flip_down2_rows():
    # World rows -33..-18, revealed at the bottom of the third-switch flip.
    # This includes persistence of the player-closed c5 gate beside closed c6.
    rows = [
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555',
        '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355',
        '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555aaaaaaaaaaa5555555555',
        '5535555535555aaaaaaaaaaaaaaaaa53ccc353ccc35aaaaaaaaaaa5535555535',
        '5555555555555acacaaacacaaacaca5ccccc5ccccc5acacaaacaca5555555555',
        '5555555555555aacaaaaacaaaaacaa5ccccc5ccccc5aacaaaaacaa5555555555',
        '5355555355555acacaaacacaaacaca5ccccc5ccccc5acacaaacaca5355555355',
        '5555355555355aaaaaaaaaaaaaaaaa53ccc353ccc35aaaaaaaaaaa5555355555',
        '5555555555555aaaaaaaaaaaaaaaaa5555555555555aaaaaaaaaaa5555555555',
    ]
    return np.array([[int(ch,16) for ch in row] for row in rows], dtype=int)


def _l5_flip_down2(g, under):
    # At c7 the third switch causes a one-cell physical fall.  The y37 -> y27
    # anchor change adds ten pixels, for a total 16px camera shift (96 -> 80).
    pos = _player_origin(g)
    if pos is None:
        return g, under, [10,10,10]
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    hud = g[63].copy()
    old = g[:63].copy()
    g[:47] = old[16:63]
    g[47:63] = _l5_flip_down2_rows()
    g[63] = hud
    new_under, cap_under = _draw_down(g, ox, 27, face)
    return g, new_under, cap_under


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
    if CURRENT_LEVEL == 8:
        # L8 terrain is accumulated in world coordinates as flower surfing
        # exposes successive slices.
        return _l8_known_rows(-scroll-n, n)
    if CURRENT_LEVEL == 8 and scroll == 18 and n == 30:
        return _l8_up_reveal2()
    if CURRENT_LEVEL == 8 and scroll == 0 and n == 18:
        return _l8_up_reveal1()
    if CURRENT_LEVEL == 7 and scroll == 114 and n == 6:
        return _l7_up_reveal15()
    if CURRENT_LEVEL == 7 and scroll == 108 and n == 6:
        return _l7_up_reveal14()
    if CURRENT_LEVEL == 7 and scroll == 102 and n == 6:
        return _l7_up_reveal13()
    if CURRENT_LEVEL == 7 and scroll == 96 and n == 6:
        return _l7_up_reveal12()
    if CURRENT_LEVEL == 7 and scroll == 90 and n == 6:
        return _l7_up_reveal11()
    if CURRENT_LEVEL == 7 and scroll == 84 and n == 6:
        return _l7_up_reveal10()
    if CURRENT_LEVEL == 7 and scroll >= 54:
        # Draw the newly exposed world slice from the authoritative terrain map.
        # This preserves the solid world-126 row above the lethal ceiling instead
        # of extrapolating the open world-90 chamber indefinitely.
        return _l7_known_rows(-scroll-n, n)
    if CURRENT_LEVEL == 7 and scroll == 54 and n == 24:
        return _l7_up_reveal9()
    if CURRENT_LEVEL == 7 and scroll == 42 and n == 12:
        return _l7_up_reveal8()
    if CURRENT_LEVEL == 7 and scroll == 36 and n == 6:
        return _l7_up_reveal7()
    if CURRENT_LEVEL == 7 and scroll == 30 and n == 6:
        return _l7_up_reveal6()
    if CURRENT_LEVEL == 7 and scroll == 24 and n == 6:
        return _l7_up_reveal5()
    if CURRENT_LEVEL == 7 and scroll == 18 and n == 6:
        return _l7_up_reveal4()
    if CURRENT_LEVEL == 7 and scroll == 12 and n == 6:
        return _l7_up_reveal3()
    if CURRENT_LEVEL == 7 and scroll == 6 and n == 6:
        return _l7_up_reveal2()
    if CURRENT_LEVEL == 7 and scroll == 0 and n == 6:
        return _l7_up_reveal1()
    if CURRENT_LEVEL == 6 and scroll == 54 and n == 36:
        # c7 rises to world -54.  World -90..-79 is a featureless open room;
        # world -78..-55 is the solid four-cell cap above the c7 shaft.
        t = _wall_screen()[:36].copy()
        t[:12] = 10
        return t
    if CURRENT_LEVEL == 6 and scroll == 54 and n == 12:
        # c5 rises from world -18 to -30, exposing known world -66..-55.
        return _l6_up_reveal4()[:12].copy()
    if CURRENT_LEVEL == 6 and scroll == -6 and n == 30:
        return _l6_up_reveal1()
    if CURRENT_LEVEL == 6 and scroll == 24 and n == 42:
        return _l6_up_reveal4()
    if CURRENT_LEVEL == 6 and scroll == 24 and n == 12:
        return _l6_up_reveal2()
    if CURRENT_LEVEL == 6 and scroll == 18 and n == 6:
        # Revisit the already observed world -24..-19 rows.
        return _l6_up_reveal1()[:6].copy()
    if CURRENT_LEVEL == 5 and scroll == 0 and n == 12:
        return _l5_up_reveal1()
    if CURRENT_LEVEL == 5 and scroll == 12 and n == 18:
        return _l5_up_reveal2()
    if CURRENT_LEVEL == 5 and scroll == 30 and n == 24:
        return _l5_up_reveal3()
    if CURRENT_LEVEL == 5 and scroll == 54 and n == 36:
        return _l5_up_reveal4()
    if CURRENT_LEVEL == 5 and scroll == 90 and n == 6:
        return _l5_up_reveal5()
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

def _finish_float(g, ox, oy, scroll, face=1, l7_blocks=None):
    ny = oy
    dead = False
    level_up = False
    # L7 callers thread the authoritative world-coordinate block set.  The
    # viewport cannot recover a hidden child when it shares a seam with a full
    # block at the top edge, so inference is only a compatibility fallback.
    if CURRENT_LEVEL in (7,8):
        l7_blocks = (_l7_screen_blocks(g, scroll) if l7_blocks is None
                     else {tuple(v) for v in l7_blocks})
    else:
        l7_blocks = set()
    while True:
        cand = ny - 6
        if _fits(g, ox, cand):
            ny = cand
            continue
        # Special framed objects resolve on attempted contact: colour-f devices
        # kill, while the colour-7 diamond completes the level.
        if cand >= 0:
            region = g[cand:cand+5, ox:ox+5]
            # L7's framed-f split blocks are safe solid canopies; only the
            # distinct f/b0b devices are lethal.
            safe_l7_block = (CURRENT_LEVEL in (7,8)
                             and ((ox//6)*6, cand-1) in _l7_block_cells(g))
            if np.any(region == 15) and not safe_l7_block:
                dead = True
            elif np.any(region == 7):
                level_up = True
        elif (CURRENT_LEVEL == 6 and scroll == 24 and ox >= 55):
            # The apparent c9 edge shaft is a long open ascent, but eventually
            # terminates at the f device now observed at c9/world -54.
            dead = True
        break
    # In the L1 safe-right shaft the open run continues one logical cell
    # above the old viewport before meeting its hidden ceiling.
    if (not dead and CURRENT_LEVEL == 1 and scroll == 6 and ox >= 37
            and ny == 1):
        ny -= 6
    if (not dead and CURRENT_LEVEL == 6 and scroll == 24 and ox == 13
            and ny == 1):
        # c2 remains open for one hidden logical cell above the viewport,
        # stopping at the known world -36 wall.
        ny -= 6
    rise = oy - ny
    if rise and not dead:
        hud = g[63].copy()
        old = g[:63].copy()  # player was erased before this routine
        g[rise:63] = old[:63-rise]
        g[:rise] = _reveal(scroll, rise)
        if CURRENT_LEVEL in (7,8):
            for bx, by in l7_blocks:
                nsy = by + scroll + rise
                if nsy < 63 and nsy+6 >= 0:
                    _l7_draw_block(g, bx, nsy)
        g[63] = hud
        scroll += rise
        new_under = _capture_under(g, ox, oy)
        _draw(g, ox, oy, face)  # camera keeps the player anchored
    else:
        new_under = _capture_under(g, ox, ny)
        _draw(g, ox, ny, face)
    return g, scroll, dead, level_up, new_under

def _move_and_float(g, dx, scroll, under, l7_blocks=None):
    pos = _player_origin(g)
    if pos is None:
        return g, scroll, False, False, under
    ox, oy = pos
    _erase(g, ox, oy, under)
    nx = ox + dx
    if not _fits(g, nx, oy):
        nx = ox
    return _finish_float(g, nx, oy, scroll, 1 if dx > 0 else -1,
                         l7_blocks)

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
    if CURRENT_LEVEL == 6 and scroll == 62 and ox == 55:
        # c9 stays open far beyond the old viewport.  It bypasses the hanging
        # c8/world66 hazard and lands on the world84 floor at world78.
        g[:63] = _l6_down_view2()
        under, cap_under = _draw_down(g, ox, oy, face)
        return g, -52, False, False, under, cap_under
    while True:
        cand = ny + 6
        if _fits(g, ox, cand):
            ny = cand
            continue
        hidden = None
        if cand+5 > 63 and ((CURRENT_LEVEL == 3 and scroll < 0)
                            or CURRENT_LEVEL == 5):
            if CURRENT_LEVEL == 3:
                hidden = _l3_deeper_rows(cand-scroll, 5)
            else:
                hidden = _l5_known_rows(cand-scroll, 5)
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
        elif CURRENT_LEVEL == 5:
            g[63-fall:63] = _l5_known_rows(first_world, fall)
        elif CURRENT_LEVEL == 6 and scroll == 68 and fall == 6:
            g[63-fall:63] = _l6_down_reveal6()
        elif CURRENT_LEVEL == 6 and scroll == 50 and fall == 12:
            g[63-fall:63] = _l6_down_reveal4()
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

def _tile_point_open(g, px, py, scroll):
    """Whether a point just outside a tile belongs to traversable underlay."""
    if not (0 <= px < 64 and 0 <= py < 63):
        return False
    v = int(g[py,px])
    if v == 10:
        return True
    if v != 12:
        return False
    ncx = (px//6)*6
    ncy = ((py-scroll)//6)*6 + scroll
    reg = g[max(0,ncy):min(63,ncy+6),ncx:min(64,ncx+6)]
    return int(np.sum(reg == 12)) <= 5


def _toggle_breakable(g, cx, cy, scroll):
    """Drill e or toggle c, preserving shared seams and hidden underlay."""
    tile = g[max(0,cy):min(63,cy+6), max(0,cx):min(64,cx+6)]
    c_count = int(np.sum(tile == 12))
    if not np.any(tile == 14) and not c_count:
        return g

    g[max(0,cy+1):min(63,cy+6), max(0,cx+1):min(64,cx+6)] = 10
    left = _tile_point_open(g,cx-3,cy+3,scroll)
    right = _tile_point_open(g,cx+9,cy+3,scroll)
    top = _tile_point_open(g,cx+3,cy-3,scroll)
    bottom = _tile_point_open(g,cx+3,cy+9,scroll)
    # A clipped L8 e gate can have an observed-open continuation just above
    # the viewport.  Consult authoritative world terrain so its shared top
    # seam opens even though the sampling point is off-screen.
    if CURRENT_LEVEL == 8 and cy == 0:
        wy = cy-scroll
        above = _l8_known_rows(wy-5,5)[:,cx+1:cx+6]
        top = bool(np.all(above == 10))
    if CURRENT_LEVEL == 8 and cy+6 < 63 and cy+9 >= 63:
        wy = cy-scroll
        below = _l8_known_rows(wy+7,5)[:,cx+1:cx+6]
        bottom = bool(np.all(below == 10))
    # If the tile centre itself is clipped below the HUD, the ordinary
    # horizontal probes are unavailable.  The visible neighbour interiors are
    # still authoritative and determine whether the two vertical seams open.
    if CURRENT_LEVEL == 8 and cy+3 >= 63:
        vy0,vy1 = max(0,cy+1),63
        if vy0 < vy1:
            if cx >= 6:
                left = bool(np.all(g[vy0:vy1,cx-5:cx] == 10))
            if cx+11 <= 64:
                right = bool(np.all(g[vy0:vy1,cx+7:cx+12] == 10))
    if left and 0 <= cx < 64:
        g[max(0,cy+1):min(63,cy+6),cx] = 10
    if right and cx+6 < 64:
        g[max(0,cy+1):min(63,cy+6),cx+6] = 10
    if top and 0 <= cy < 63:
        g[cy,max(0,cx+1):min(64,cx+6)] = 10
    if bottom and 0 <= cy+6 < 63:
        g[cy+6,max(0,cx+1):min(64,cx+6)] = 10
    if left and top and 0 <= cy < 63: g[cy,cx] = 10
    if left and bottom and 0 <= cy+6 < 63: g[cy+6,cx] = 10
    if right and top and 0 <= cy < 63 and cx+6 < 64: g[cy,cx+6] = 10
    if right and bottom and 0 <= cy+6 < 63 and cx+6 < 64: g[cy+6,cx+6] = 10

    if c_count > 5 and 0 <= cy+4 < 63 and cx+4 < 64:
        for px,py in ((cx+2,cy+2),(cx+4,cy+2),(cx+3,cy+3),
                      (cx+2,cy+4),(cx+4,cy+4)):
            g[py,px] = 12
        # Each corner opens only when both continuations at that exact
        # corner are open: its horizontal neighbour and the vertical underlay.
        if 0 <= cy < 63:
            if 0 <= cx < 64:
                g[cy,cx] = 10 if (left and _tile_point_open(g,cx,cy-1,scroll)) else 5
            if 0 <= cx+6 < 64:
                g[cy,cx+6] = 10 if (right and _tile_point_open(g,cx+6,cy-1,scroll)) else 5
        if 0 <= cy+6 < 63:
            if 0 <= cx < 64:
                g[cy+6,cx] = 10 if (left and _tile_point_open(g,cx,cy+7,scroll)) else 5
            if 0 <= cx+6 < 64:
                g[cy+6,cx+6] = 10 if (right and _tile_point_open(g,cx+6,cy+7,scroll)) else 5
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
    return g


def _click_and_float(g, x, y, scroll, under, l7_blocks=None):
    pos = _player_origin(g)
    if pos is None or x is None or y is None:
        return g, scroll, False, False, under
    ox, oy = pos
    face = _facing(g)
    _erase(g, ox, oy, under)
    cx, cy = (int(x)//6)*6, (int(y)//6)*6
    # Breakable hitboxes are only the five-pixel tile interior; lattice seams
    # belong to neither neighbour and clicks on them are inert.
    if cx < int(x) < cx+6 and cy < int(y) < cy+6:
        _toggle_breakable(g, cx, cy, 0)
    return _finish_float(g, ox, oy, scroll, face, l7_blocks)

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
    if cx < int(x) < cx+6 and cy < int(y) < cy+6:
        _toggle_breakable(g, cx, cy, scroll)
    return _finish_fall(g,ox,oy,scroll,face)

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid, dtype=int).copy()
    undo = list(state.get("undo", []))
    scroll = int(state.get("scroll", 0))
    under = state.get("under", [[10]*5 for _ in range(5)])
    gravity = int(state.get("gravity", -1))
    cap_under = state.get("cap_under", [10,10,10])
    switches = list(state.get("switches", []))
    l7_blocks = [tuple(v) for v in state.get("l7_blocks", [])]
    l7_sparse = [tuple(v) for v in state.get("l7_sparse", [])]
    info = {"level_up": False, "dead": False, "win": False}
    # L6+ have a 128-action two-colour budget.  The action which replaces
    # the final remaining 7 with f exhausts it and kills the run.
    meter_dead = (CURRENT_LEVEL is not None and CURRENT_LEVEL >= 6
                  and not np.any(g[-1] == 0)
                  and int(np.sum(g[-1] == 7)) == 1)
    if action == 7:
        # Undo the most recent spatial action, but do not refund either action's
        # HUD cost: preserve the current meter and tick once more for the undo.
        if undo:
            (prev_grid, scroll, under, gravity, cap_under,
             l7_blocks, l7_sparse, switches) = undo.pop()
            hud = g[63].copy()
            g = np.array(prev_grid, dtype=int).copy()
            g[63] = hud
        _tick(g)
        if meter_dead:
            info["dead"] = True
        ns = {"undo":undo,"scroll":scroll,"under":under,
              "gravity":gravity,"cap_under":cap_under,"switches":switches,
              "l7_blocks":l7_blocks,"l7_sparse":l7_sparse}
        return g.tolist(), info, ns
    if action in (3,4):
        undo.append((np.array(grid,dtype=int).tolist(), scroll, under,
                     gravity, cap_under, list(l7_blocks),
                     list(l7_sparse), list(switches)))
        dx = -6 if action == 3 else 6
        pos = _player_origin(g)
        # Entering the framed colour-7 diamond completes the current level.
        hit_goal = False
        if pos is not None:
            ox, oy = pos
            nx = ox + dx
            if 0 <= nx and nx+5 <= 64:
                hit_goal = bool(np.any(g[oy:oy+5, nx:nx+5] == 7))
        # On L8 the apparently open c5 shaft above the entry room leads
        # directly into a hidden f/b0b hazard bank.  Moving right from the
        # capped c4 entry cell under upward gravity is therefore terminal.
        l8_hidden_shaft_death = (
            CURRENT_LEVEL == 8 and gravity < 0 and scroll == 0
            and pos is not None and pos[0] == 25 and dx > 0
            and (30,12) not in {tuple(v) for v in l7_blocks})
        if l8_hidden_shaft_death:
            info["dead"] = True
            _tick(g)
        elif hit_goal:
            info["level_up"] = True
        else:
            if CURRENT_LEVEL == 7 and gravity > 0:
                g, scroll, dead, rose_into_goal, under, cap_under = _l7_move_and_fall(
                    g, dx, scroll, under, cap_under, l7_blocks, l7_sparse)
            elif CURRENT_LEVEL == 8 and gravity > 0:
                g, scroll, dead, rose_into_goal, under, cap_under = _l8_move_and_fall(
                    g, dx, scroll, under, cap_under, l7_blocks, l7_sparse,
                    switches)
            elif gravity > 0:
                g, scroll, dead, rose_into_goal, under, cap_under = _move_and_fall(
                    g, dx, scroll, under, cap_under)
            else:
                g, scroll, dead, rose_into_goal, under = _move_and_float(
                    g, dx, scroll, under, l7_blocks)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            _tick(g)
    elif action == 6:
        undo.append((np.array(grid,dtype=int).tolist(), scroll, under,
                     gravity, cap_under, list(l7_blocks),
                     list(l7_sparse), list(switches)))
        # The avatar owns its entire 5x5 click box, including the two visually
        # transparent lower corners.  A gate hidden under that box cannot be
        # toggled by clicking through the player.
        pclick = _player_origin(g)
        if (pclick is not None and x is not None and y is not None
                and pclick[0] <= int(x) < pclick[0]+5
                and pclick[1] <= int(y) < pclick[1]+5):
            _tick(g)
            if meter_dead:
                info["dead"] = True
            ns = {"undo":undo,"scroll":scroll,"under":under,
                  "gravity":gravity,"cap_under":cap_under,"switches":switches,
                  "l7_blocks":l7_blocks,"l7_sparse":l7_sparse}
            return g.tolist(), info, ns
        near = g[max(0,int(y or 0)-3):min(63,int(y or 0)+4),
                 max(0,int(x or 0)-3):min(64,int(x or 0)+4)]
        # L8 switches own their whole logical 6x6 tile, including its
        # ordinary-colour frame.  A seam belongs to the tile on its right.
        l8_switch_hit = False
        l8_switch_key = None
        if (CURRENT_LEVEL == 8 and x is not None and y is not None
                and 0 <= int(y) < 63 and 0 <= int(x) < 60):
            scx = (int(x)//6)*6
            scy = ((int(y)-scroll)//6)*6 + scroll
            sworld = scy - scroll
            static_switch = _l8_known_rows(sworld,6)[:,scx:scx+6]
            l8_switch_key = _l8_switch_key(scx, sworld)
            l8_switch_hit = (l8_switch_key not in switches
                             and np.any(static_switch == 8))
        if ((CURRENT_LEVEL == 6 and np.any(near == 8)) or l8_switch_hit):
            scy = ((int(y)-scroll)//6)*6 + scroll
            sworld = scy - scroll
            key = (l8_switch_key if CURRENT_LEVEL == 8 else sworld)
            if key not in switches:
                switches.append(key)
        if CURRENT_LEVEL == 8 and x is not None and y is not None:
            ecx = (int(x)//6)*6
            ecy = ((int(y)-scroll)//6)*6 + scroll
            ewy = ecy-scroll
            etile = g[max(0,ecy):min(63,ecy+6),
                      max(0,ecx):min(64,ecx+6)]
            inside = (ecx < int(x) < ecx+6 and ecy < int(y) < ecy+6)
            if inside:
                opened = {tuple(v) for v in l7_sparse}
                key = (ecx,ewy)
                static = (_l8_known_rows(ewy,6)[:,ecx:ecx+6]
                          if 0 <= ecx and ecx+6 <= 64 else np.empty((0,0)))
                if np.any(etile == 14):
                    # e gates drill open permanently.
                    opened.add(key)
                elif np.any(static == 12):
                    # c gates toggle dense/sparse and must persist in world
                    # coordinates across the camera ascent.
                    if key in opened:
                        opened.remove(key)
                    else:
                        opened.add(key)
                l7_sparse = sorted(opened)
        l7res = None
        if CURRENT_LEVEL == 7:
            if gravity < 0:
                l7res = _l7_click_block(g, x, y, scroll, l7_blocks,
                                          l7_sparse)
            else:
                l7res = _l7_click_block_down(g, x, y, scroll, l7_blocks,
                                               l7_sparse)
        elif CURRENT_LEVEL == 8:
            if gravity < 0:
                l7res = _l8_click_block(g, x, y, scroll, l7_blocks,
                                         l7_sparse, switches)
            else:
                l7res = _l8_click_block_down(g, x, y, scroll, l7_blocks,
                                              l7_sparse, switches)
        if l7res is not None:
            result, l7_blocks = l7res
            if gravity > 0:
                g, scroll, dead, rose_into_goal, under, cap_under = result
            else:
                g, scroll, dead, rose_into_goal, under = result
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            _tick(g)
        elif (l8_switch_hit and gravity < 0):
            g,scroll,dead,rose_into_goal,under,cap_under = _l8_flip_down_general(
                g,scroll,l7_blocks,l7_sparse,switches)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            gravity = 1
            _tick(g)
        elif (l8_switch_hit and gravity > 0):
            g,scroll,dead,rose_into_goal,under = _l8_flip_up_general(
                g,scroll,l7_blocks,l7_sparse,switches)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif (CURRENT_LEVEL == 7 and np.any(near == 8)
              and gravity < 0):
            g, scroll, dead, rose_into_goal, under, cap_under = _l7_flip_down(
                g, scroll, l7_blocks, l7_sparse)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity < 0 and scroll == -24):
            # From c3/world60 the downward trajectory crosses open world66 and
            # contacts the framed c3/world72 goal.  Terminal grids auto-switch.
            info["level_up"] = True
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity < 0 and scroll == 78):
            g, under, cap_under = _l6_flip_down4(
                g, x, y, scroll, under)
            scroll = 68
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity < 0 and scroll == 66):
            g, under, cap_under = _l6_flip_down3(
                g, x, y, scroll, under)
            scroll = 50
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity < 0 and scroll == 36):
            g, under, cap_under = _l6_flip_down2(g, x, y, under)
            scroll = 8
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity < 0 and scroll == 0):
            g, under, cap_under = _l6_flip_down(g, x, y, under)
            scroll = -16
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity > 0 and scroll == -52):
            g, under, scroll = _l6_flip_up4(
                g, x, y, scroll, under, cap_under)
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity > 0 and scroll == 38):
            g, under, scroll = _l6_flip_up3(
                g, x, y, scroll, under, cap_under)
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity > 0 and scroll == 8):
            g, under = _l6_flip_up2(g, x, y, scroll, under, cap_under)
            scroll = 18
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif (CURRENT_LEVEL == 6 and np.any(near == 8)
                and gravity > 0 and scroll == -16):
            g, under = _l6_flip_up(g, x, y, scroll, under, cap_under)
            scroll = -6
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif (CURRENT_LEVEL == 5 and np.any(near == 8)
                and gravity < 0 and scroll == 0):
            g, under, cap_under = _l5_flip_down(g, under)
            scroll = -58
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 5 and np.any(near == 8)
                and gravity > 0 and scroll == -58):
            g, under = _l5_flip_up(g, under, cap_under)
            scroll = 0
            gravity = -1
            cap_under = [10,10,10]
            _tick(g)
        elif (CURRENT_LEVEL == 5 and np.any(near == 8)
                and gravity < 0 and scroll == 96):
            g, under, cap_under = _l5_flip_down2(g, under)
            scroll = 80
            gravity = 1
            _tick(g)
        elif (CURRENT_LEVEL == 4 and np.any(near == 8)
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
            if (CURRENT_LEVEL == 7 and gravity < 0
                    and x is not None and y is not None):
                gcx = (int(x)//6)*6
                gcy = ((int(y)-scroll)//6)*6 + scroll
                gwy = gcy-scroll
                static = (_l7_known_rows(gwy, 6)[:,gcx:gcx+6]
                          if 0 <= gcx and gcx+6 <= 64 else np.empty((0,0)))
                if (gcx < int(x) < gcx+6 and gcy < int(y) < gcy+6
                        and np.any(static == 12)):
                    key = (gcx,gwy)
                    sparse_set = {tuple(v) for v in l7_sparse}
                    if key in sparse_set:
                        sparse_set.remove(key)
                    else:
                        sparse_set.add(key)
                    l7_sparse = sorted(sparse_set)
            if gravity > 0:
                if CURRENT_LEVEL == 8:
                    # L8 support objects and gates persist in world space.  A
                    # remote click can remove/toggle the last support far from
                    # the avatar, so settle against the authoritative world
                    # map rather than the clipped viewport (which can invent
                    # an off-screen floor and stop the fall too early).
                    g, scroll, dead, rose_into_goal, under, cap_under = _l8_flip_down_general(
                        g, scroll, l7_blocks, l7_sparse, switches)
                else:
                    g, scroll, dead, rose_into_goal, under, cap_under = _click_and_fall(
                        g, x, y, scroll, under, cap_under)
            else:
                g, scroll, dead, rose_into_goal, under = _click_and_float(
                    g, x, y, scroll, under, l7_blocks)
            info["dead"] = bool(dead)
            info["level_up"] = bool(rose_into_goal)
            _tick(g)
    if CURRENT_LEVEL == 6:
        _l6_apply_switches(g, scroll, switches)
    # L8 is the ninth and final board: entering its framed goal wins the game
    # rather than auto-switching to another level.
    if CURRENT_LEVEL == 8 and info["level_up"]:
        info["level_up"] = False
        info["win"] = True
    if meter_dead and not info["level_up"] and not info["win"]:
        info["dead"] = True
    ns = {"undo":undo,"scroll":scroll,"under":under,
          "gravity":gravity,"cap_under":cap_under,"switches":switches,
          "l7_blocks":l7_blocks,"l7_sparse":l7_sparse}
    return g.tolist(), info, ns
