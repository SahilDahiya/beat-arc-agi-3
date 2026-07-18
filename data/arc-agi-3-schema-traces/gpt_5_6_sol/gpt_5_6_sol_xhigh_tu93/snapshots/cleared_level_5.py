def _player(grid):
    a = np.array(grid)
    ys, xs = np.where((a == 9) | (a == 4))
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    if x1-x0 > 2 or y1-y0 > 2:
        return None
    return (x0+x1)//2, (y0+y1)//2

def is_goal(state, grid):
    # Goal colour may be covered by a walker; only level_up flags count.
    return False

def _clear_node(a, cx, cy, disabled_sentries=()):
    base = np.array(ENTRY_GRID)
    block = base[cy-1:cy+2, cx-1:cx+2]
    if np.any(block == 14):
        a[cy-1:cy+2, cx-1:cx+2] = 14
    elif np.any(block == 8) and (cx,cy) not in disabled_sentries:
        a[cy-1:cy+2, cx-1:cx+2] = block
    else:
        a[cy-1:cy+2, cx-1:cx+2] = 0

def _oriented_blocks(grid, body):
    a = np.array(grid)
    out = []
    fys, fxs = np.where(a == 15)
    face_for_offset = {(0,-1):1, (0,1):2, (-1,0):3, (1,0):4}
    for fx, fy in zip(fxs, fys):
        for ox, oy in face_for_offset:
            cx, cy = int(fx-ox), int(fy-oy)
            if cy-1 < 0 or cx-1 < 0 or cy+1 >= a.shape[0] or cx+1 >= a.shape[1]:
                continue
            block = a[cy-1:cy+2, cx-1:cx+2]
            if np.all((block == body) | (block == 15)):
                out.append((cx, cy, face_for_offset[(ox,oy)]))
                break
    return out

def _enemies(grid):
    return _oriented_blocks(grid, 8)

def _walkers(grid):
    return _oriented_blocks(grid, 12)

def init_state(entry_grid):
    # Preserve every walker separately even when several later overlap and
    # the rendered grid can show only one.  Conflict priority is stable per
    # actor and seeded by its initial facing (up, right, down, left).
    walkers = [tuple(w) for w in _walkers(entry_grid)]
    rank = {1:0, 4:1, 2:2, 3:3}
    walkers.sort(key=lambda w: (rank[w[2]], w[1], w[0]))
    return {"walkers": walkers, "disabled_sentries": []}

def _turn_limit():
    if CURRENT_LEVEL == 2:
        return 35
    if CURRENT_LEVEL == 3:
        return 20
    if CURRENT_LEVEL == 5:
        return 60
    return 50

def _rendered_turns(grid):
    a = np.array(grid)
    entry = np.array(ENTRY_GRID)
    bar = np.where(entry[-1] == 6)[0]
    limit = _turn_limit()
    if len(bar) == 0:
        return 0, bar, limit
    spent_pixels = int(np.sum(a[-1, bar] == 0))
    best = min(range(limit+1),
               key=lambda n: abs(int(len(bar)*n/float(limit)+0.5)-spent_pixels))
    return best, bar, limit

def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    info = {"level_up": False, "dead": False, "win": False}
    delta = {1:(0,-6), 2:(0,6), 3:(-6,0), 4:(6,0)}
    lead = {1:(0,-1), 2:(0,1), 3:(-1,0), 4:(1,0)}
    opposite = {1:2, 2:1, 3:4, 4:3}
    walkers = [tuple(w) for w in state.get("walkers", _walkers(a))]
    disabled_sentries = set(tuple(p) for p in
                            state.get("disabled_sentries", []))
    player_moved = False
    player_node = None
    disabled_walker_node = None

    p = _player(a)
    if p is not None and action in delta:
        px, py = p
        dx, dy = delta[action]
        tx, ty = px+dx, py+dy
        mx, my = px+dx//2, py+dy//2
        if (0 <= tx < a.shape[1] and 0 <= ty < a.shape[0] and
            a[my, mx] == 2 and a[ty, tx] in (0, 8, 12, 14)):
            player_moved = True
            player_node = (tx, ty)
            if a[ty, tx] == 12:
                disabled_walker_node = (tx, ty)
            if np.any(np.array(ENTRY_GRID)[ty-1:ty+2, tx-1:tx+2] == 8):
                disabled_sentries.add((tx,ty))
            goal = (a[ty, tx] == 14 or
                    np.any(np.array(ENTRY_GRID)[ty-1:ty+2, tx-1:tx+2] == 14))
            _clear_node(a, px, py, disabled_sentries)
            if goal:
                info["level_up"] = True
                if CURRENT_LEVEL == 8:
                    info["win"] = True
            else:
                a[ty-1:ty+2, tx-1:tx+2] = 9
                lx, ly = lead[action]
                a[ty+ly, tx+lx] = 4

    if disabled_walker_node is not None:
        walkers = [w for w in walkers if (w[0],w[1]) != disabled_walker_node]

    turns, bar, turn_limit = _rendered_turns(grid)
    turns += 1

    # Stationary 8/f sentries lunge only when the player ends directly ahead.
    if not info["level_up"]:
        for ex, ey, ef in _enemies(ENTRY_GRID):
            if (ex,ey) in disabled_sentries:
                continue
            dx, dy = delta[ef]
            tx, ty = ex+dx, ey+dy
            mx, my = ex+dx//2, ey+dy//2
            if 0 <= tx < a.shape[1] and 0 <= ty < a.shape[0] and a[my,mx] == 2:
                target = a[ty-1:ty+2, tx-1:tx+2]
                if np.any((target == 9) | (target == 4)):
                    _clear_node(a, ex, ey, disabled_sentries)
                    a[ty-1:ty+2, tx-1:tx+2] = 8
                    lx, ly = lead[ef]
                    a[ty+ly, tx+lx] = 15
                    info["dead"] = True
                    break

    # Mobile c/f walkers update simultaneously after successful player moves.
    # State retains walkers hidden by overlaps with other sprites.
    if player_moved and not info["dead"] and walkers:
        old = list(walkers)
        old_positions = {(w[0],w[1]) for w in old}
        pp = _player(a)
        for ex, ey in old_positions:
            # A walker hidden under a stationary sentry does not erase it.
            if a[ey, ex] == 8:
                continue
            if pp is None or pp != (ex,ey):
                _clear_node(a, ex, ey, disabled_sentries)

        stationary = {(sx,sy):sf for sx,sy,sf in _enemies(ENTRY_GRID)
                      if (sx,sy) not in disabled_sentries}
        hidden_nodes = set()
        overwritten_sentries = set()
        new_walkers = []
        for ex, ey, ef in old:
            dx, dy = delta[ef]
            tx, ty = ex+dx, ey+dy
            mx, my = ex+dx//2, ey+dy//2
            if (0 <= tx < a.shape[1] and 0 <= ty < a.shape[0] and
                a[my,mx] == 2):
                # Collinear contact passes visually under a sentry; side
                # contact renders the walker above it.  Both persist.
                sf = stationary.get((tx,ty))
                if sf == ef or sf == opposite[ef]:
                    hidden_nodes.add((tx,ty))
                elif sf is not None:
                    overwritten_sentries.add((tx,ty))
                nface = ef
                ax, ay = tx+dx, ty+dy
                amx, amy = tx+dx//2, ty+dy//2
                wall_ahead = not (0 <= amx < a.shape[1] and
                                  0 <= amy < a.shape[0] and
                                  np.array(ENTRY_GRID)[amy,amx] == 2)
                if wall_ahead:
                    nface = opposite[ef]
                new_walkers.append((tx,ty,nface))
            else:
                new_walkers.append((ex,ey,opposite[ef]))

        for sx, sy in overwritten_sentries:
            _clear_node(a, sx, sy, disabled_sentries)
        hidden_nodes -= overwritten_sentries

        # Walkers pass through one another while retaining stable actor
        # priority for the single sprite an overlap can render.
        render_walkers = list(new_walkers)
        walkers = list(new_walkers)

        # Reaching a goal and a walker arriving there on the same tick is
        # lethal; hazards resolve before completion.
        if player_node is not None and any((w[0], w[1]) == player_node
                                           for w in walkers):
            info["dead"] = True
            info["level_up"] = False

        pp = _player(a)
        rendered = set()
        for ex, ey, ef in render_walkers:
            # Same-facing rear contact stays hidden for this collision tick.
            if (ex,ey) in hidden_nodes:
                continue
            if pp is not None and pp == (ex,ey):
                info["dead"] = True
            if (ex,ey) in rendered:
                continue
            rendered.add((ex,ey))
            a[ey-1:ey+2, ex-1:ex+2] = 12
            lx, ly = lead[ef]
            a[ey+ly, ex+lx] = 15

    if len(bar):
        a[-1,bar] = 6
        spent = int(len(bar)*turns/float(turn_limit)+0.5)
        if spent:
            a[-1,bar[-spent:]] = 0

    if not info["level_up"] and turns >= turn_limit:
        info["dead"] = True
    return a.tolist(), info, {"walkers": walkers,
                                   "disabled_sentries": list(disabled_sentries)}
