def _player(grid):
    a = np.array(grid)
    ys, xs = np.where((a == 9) | (a == 4))
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    if x1 - x0 > 2 or y1 - y0 > 2:
        return None
    cx, cy = (x0+x1)//2, (y0+y1)//2
    return cx, cy

def is_goal(grid):
    return not np.any(np.array(grid) == 14)

def _oriented_blocks(grid, body):
    a = np.array(grid)
    out = []
    fys, fxs = np.where(a == 15)
    face_for_offset = {(0,-1):1, (0,1):2, (-1,0):3, (1,0):4}
    # Each f is one leading-edge cell of a 3x3 body-coloured block.
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

def _turn_limit():
    # The bar's logical budget is a per-level parameter.
    return 35 if CURRENT_LEVEL == 2 else (20 if CURRENT_LEVEL == 3 else 50)

def _rendered_turns(grid):
    a = np.array(grid)
    entry = np.array(ENTRY_GRID)
    bar = np.where(entry[-1] == 6)[0]
    limit = _turn_limit()
    if len(bar) == 0:
        return 0, bar, limit
    spent_pixels = int(np.sum(a[-1, bar] == 0))
    best = min(range(limit+1),
               key=lambda n: abs(int(len(bar)*n/float(limit) + 0.5) - spent_pixels))
    return best, bar, limit

def step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    info = {"level_up": False, "dead": False, "win": False}
    delta = {1:(0,-6), 2:(0,6), 3:(-6,0), 4:(6,0)}
    lead = {1:(0,-1), 2:(0,1), 3:(-1,0), 4:(1,0)}
    p = _player(a)
    player_moved = False

    if p is not None and action in delta:
        px, py = p
        dx, dy = delta[action]
        tx, ty = px + dx, py + dy
        mx, my = px + dx//2, py + dy//2
        h, w = a.shape
        if (0 <= tx < w and 0 <= ty < h and
            a[my, mx] == 2 and a[ty, tx] in (0, 8, 12, 14)):
            player_moved = True
            goal = (a[ty, tx] == 14)
            a[py-1:py+2, px-1:px+2] = 0
            if goal:
                info["level_up"] = True
                if CURRENT_LEVEL == 8:
                    info["win"] = True
            else:
                a[ty-1:ty+2, tx-1:tx+2] = 9
                lx, ly = lead[action]
                a[ty+ly, tx+lx] = 4

    # Every input advances one logical turn.  The 64-pixel bar displays
    # round(turns * 64 / 50), hence its nonuniform 1,2,1,1,1,2... drain.
    turns, bar, turn_limit = _rendered_turns(grid)
    turns += 1

    # An 8/f sentry watches the adjacent node in the direction marked
    # by its f edge.  After the player's move, it lunges one node only
    # when the player is directly in front, which is lethal.
    if not info["level_up"]:
        for ex, ey, ef in _enemies(a):
            dx, dy = delta[ef]
            tx, ty = ex+dx, ey+dy
            mx, my = ex+dx//2, ey+dy//2
            if 0 <= tx < a.shape[1] and 0 <= ty < a.shape[0] and a[my, mx] == 2:
                collision = np.any((a[ty-1:ty+2, tx-1:tx+2] == 9) |
                                   (a[ty-1:ty+2, tx-1:tx+2] == 4))
                if collision:
                    a[ey-1:ey+2, ex-1:ex+2] = 0
                    a[ty-1:ty+2, tx-1:tx+2] = 8
                    lx, ly = lead[ef]
                    a[ty+ly, tx+lx] = 15
                    info["dead"] = True
                    break

    # A c/f walker advances one node forward after every player input.
    # It keeps its facing; a simultaneous arrival/entry onto the player is lethal.
    if player_moved and not info["level_up"] and not info["dead"]:
        for ex, ey, ef in _walkers(a):
            dx, dy = delta[ef]
            tx, ty = ex+dx, ey+dy
            mx, my = ex+dx//2, ey+dy//2
            if 0 <= tx < a.shape[1] and 0 <= ty < a.shape[0] and a[my, mx] == 2:
                target = a[ty-1:ty+2, tx-1:tx+2]
                collision = np.any((target == 9) | (target == 4))
                if a[ty, tx] == 0 or collision:
                    a[ey-1:ey+2, ex-1:ex+2] = 0
                    a[ty-1:ty+2, tx-1:tx+2] = 12
                    # Reverse immediately upon arriving at a dead end.
                    nmx, nmy = tx+dx//2, ty+dy//2
                    nface = ef
                    if not (0 <= nmx < a.shape[1] and 0 <= nmy < a.shape[0] and
                            a[nmy, nmx] == 2):
                        nface = {1:2, 2:1, 3:4, 4:3}[ef]
                    lx, ly = lead[nface]
                    a[ty+ly, tx+lx] = 15
                    if collision:
                        info["dead"] = True
                        break

    if len(bar):
        a[-1, bar] = 6
        spent = int(len(bar)*turns/float(turn_limit) + 0.5)
        if spent:
            a[-1, bar[-spent:]] = 0

    if not info["level_up"] and turns >= turn_limit:
        info["dead"] = True
    return a.tolist(), info
