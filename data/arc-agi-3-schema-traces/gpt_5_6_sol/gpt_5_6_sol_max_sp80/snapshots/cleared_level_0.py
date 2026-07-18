# ARC3 falling-block world model (incrementally learned)
# np, ENTRY_GRID, CURRENT_LEVEL are preloaded.
import math

def _timer_tick(a):
    # A 28-turn budget is rasterised across the ENTRY_GRID top-row e bar.
    # Width after k turns is ceil(W * (28-k) / 28), causing 2/2/2/3... loss.
    entry = np.array(ENTRY_GRID, dtype=int)
    W = int(np.sum(entry[0] == 14))
    w = int(np.sum(a[0] == 14))
    k = 0
    best = 10**9
    for q in range(29):
        qw = int(math.ceil(W * (28-q) / 28.0 - 1e-12))
        d = abs(qw - w)
        if d < best:
            best, k = d, q
    nw = int(math.ceil(W * (28-min(28,k+1)) / 28.0 - 1e-12))
    timer_xs = np.where(entry[0] == 14)[0]
    if len(timer_xs):
        lo = int(timer_xs[0])
        a[0, timer_xs] = 0
        a[0, lo:lo+nw] = 14

def _shift_colour(a, colour, dx, dy):
    mask = (a == colour)
    if not mask.any():
        return
    ys, xs = np.where(mask)
    bg = 12
    a[mask] = bg
    ny, nx = ys + dy, xs + dx
    ok = (ny >= 1) & (ny < a.shape[0]-4) & (nx >= 0) & (nx < a.shape[1])
    a[ny[ok], nx[ok]] = colour

def _routing_solution(a):
    # A test pulse splits around the movable 9 platform.  Win when its two
    # outside fall columns line up with the open centres of the two b cups.
    entry = np.array(ENTRY_GRID, dtype=int)
    by, bx = np.where(entry == 11)
    py, px = np.where(a == 9)
    sy, sx = np.where(entry == 6)
    if len(bx) == 0 or len(px) == 0 or len(sx) == 0:
        return False
    cols = sorted(set(int(v) for v in bx))
    runs = []
    for v in cols:
        if not runs or v > runs[-1][-1] + 1:
            runs.append([v])
        else:
            runs[-1].append(v)
    holes = []
    for run in runs:
        ys = by[np.isin(bx, run)]
        top = int(ys.min())
        hole = [v for v in run if entry[top, v] != 11]
        if hole:
            holes.append(hole)
    if len(holes) != 2:
        return False
    w = len(holes[0])
    left_fall = list(range(int(px.min())-w, int(px.min())))
    right_fall = list(range(int(px.max())+1, int(px.max())+1+w))
    source_hits = int(sx.min()) <= int(px.max()) and int(sx.max()) >= int(px.min())
    return source_hits and left_fall == holes[0] and right_fall == holes[1]

def step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    if action == 2:
        _shift_colour(a, 9, 0, 4)
    elif action == 4:
        _shift_colour(a, 9, 4, 0)
    # Other controls are not yet established; presently model them as wait.
    solved = (action == 5 and _routing_solution(a))
    if action in (1,2,3,4,5,6):
        _timer_tick(a)
    return a.tolist(), {"level_up": bool(solved), "dead": False, "win": False}

def is_goal(grid):
    # Completion requires pressing test/fire; step's level_up is the BFS goal.
    return False
