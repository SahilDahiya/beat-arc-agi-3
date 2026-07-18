# ARC3 falling-block world model (incrementally learned)
# np, ENTRY_GRID, CURRENT_LEVEL are preloaded.
import math

def _timer_tick(a, turn=None):
    # A per-level turn budget is rasterised across an e line on one edge.
    # Timer length is rendered from a hidden per-level budget; state tracks turns.
    entry = np.array(ENTRY_GRID, dtype=int)
    edge_lines = [
        ("row", 0, np.where(entry[0] == 14)[0]),
        ("row", entry.shape[0]-1, np.where(entry[-1] == 14)[0]),
        ("col", 0, np.where(entry[:,0] == 14)[0]),
        ("col", entry.shape[1]-1, np.where(entry[:,-1] == 14)[0]),
    ]
    orient, pos, cells = max(edge_lines, key=lambda z: len(z[2]))
    W = len(cells)
    if W == 0:
        return
    if orient == "row":
        w = int(np.sum(a[pos, cells] == 14))
    else:
        w = int(np.sum(a[cells, pos] == 14))
    # Per-level configured budgets learned from rasterisation.
    budgets = {0:30, 1:45, 2:100}
    budget = budgets.get(int(CURRENT_LEVEL or 0), max(1, 15 * len(_components(entry == 11))))
    if turn is None:
        k, best = 0, 10**9
        for q in range(budget+1):
            qw = int(math.floor(W * (budget-q) / float(budget) + 0.5))
            if abs(qw-w) < best:
                best, k = abs(qw-w), q
        turn = k + 1
    nw = int(math.floor(W * (budget-min(budget,int(turn))) / float(budget) + 0.5))
    forward = ((orient == "row" and pos == 0) or
               (orient == "col" and pos == entry.shape[1]-1))
    kept = cells[:nw] if forward else cells[-nw:]
    if orient == "row":
        a[pos, cells] = 0
        a[pos, kept] = 14
    else:
        a[cells, pos] = 0
        a[kept, pos] = 14

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

def _select_at(a, x, y):
    if x is None or y is None or not (0 <= x < a.shape[1] and 0 <= y < a.shape[0]):
        return
    if a[y, x] != 8:
        return
    stack = [(int(x), int(y))]
    seen = set(stack)
    comp = []
    while stack:
        cx, cy = stack.pop()
        if a[cy, cx] != 8:
            continue
        comp.append((cx, cy))
        for nx, ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
            if 0 <= nx < a.shape[1] and 0 <= ny < a.shape[0] and (nx,ny) not in seen and a[ny,nx] == 8:
                seen.add((nx,ny))
                stack.append((nx,ny))
    a[a == 9] = 8
    for cx, cy in comp:
        a[cy, cx] = 9

def _components(mask):
    h, w = mask.shape
    unseen = set((int(x), int(y)) for y, x in zip(*np.where(mask)))
    out = []
    while unseen:
        seed = unseen.pop()
        stack, pts = [seed], [seed]
        while stack:
            cx, cy = stack.pop()
            for q in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                if q in unseen:
                    unseen.remove(q)
                    stack.append(q)
                    pts.append(q)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out.append({"x0":min(xs),"x1":max(xs),"y0":min(ys),"y1":max(ys)})
    return out

def _runs(vals):
    ans = []
    for v in sorted(set(vals)):
        if not ans or v > ans[-1][-1] + 1:
            ans.append([v])
        else:
            ans[-1].append(v)
    return ans

def _routing_solution(a):
    # Trace each source stripe through every 8/9 splitter.  On hitting a
    # splitter, flow continues from equal-width stripes just outside both ends.
    entry = np.array(ENTRY_GRID, dtype=int)
    y4, x4 = np.where(entry == 4)
    y6, x6 = np.where(entry == 6)
    if len(x4) == 0 or len(x6) == 0:
        return False
    dx = float(np.mean(x6)-np.mean(x4))
    dy = float(np.mean(y6)-np.mean(y4))
    source_comps = _components(entry == 6)
    sources = []
    if abs(dy) >= abs(dx):
        direction = "down" if dy > 0 else "up"
        for s in source_comps:
            start = s["y1"]+1 if direction == "down" else s["y0"]-1
            sources.append((s["x0"], s["x1"], start))
    else:
        direction = "right" if dx > 0 else "left"
        for s in source_comps:
            start = s["x1"]+1 if direction == "right" else s["x0"]-1
            sources.append((s["y0"], s["y1"], start))

    platforms = _components((a == 8) | (a == 9))
    cups = _components(entry == 11)
    holes = []
    for c in cups:
        if direction == "down":
            vals = [x for x in range(c["x0"],c["x1"]+1) if entry[c["y0"],x] != 11]
        elif direction == "up":
            vals = [x for x in range(c["x0"],c["x1"]+1) if entry[c["y1"],x] != 11]
        elif direction == "right":
            vals = [y for y in range(c["y0"],c["y1"]+1) if entry[y,c["x0"]] != 11]
        else:
            vals = [y for y in range(c["y0"],c["y1"]+1) if entry[y,c["x1"]] != 11]
        for run in _runs(vals):
            holes.append((run[0], run[-1]))
    if not holes:
        return False

    todo = list(sources)
    terminal = []
    guard = 0
    while todo and guard < 100:
        guard += 1
        lo, hi, pos = todo.pop()
        candidates = []
        for p in platforms:
            if direction in ("down","up"):
                overlap = not (hi < p["x0"] or lo > p["x1"])
                if not overlap:
                    continue
                if direction == "down" and p["y0"] >= pos:
                    candidates.append((p["y0"], p))
                elif direction == "up" and p["y1"] <= pos:
                    candidates.append((-p["y1"], p))
            else:
                overlap = not (hi < p["y0"] or lo > p["y1"])
                if not overlap:
                    continue
                if direction == "right" and p["x0"] >= pos:
                    candidates.append((p["x0"], p))
                elif direction == "left" and p["x1"] <= pos:
                    candidates.append((-p["x1"], p))
        if not candidates:
            terminal.append((lo,hi))
            continue
        p = min(candidates, key=lambda z:z[0])[1]
        width = hi-lo+1
        if direction in ("down","up"):
            npos = p["y1"]+1 if direction == "down" else p["y0"]-1
            todo.append((p["x0"]-width, p["x0"]-1, npos))
            todo.append((p["x1"]+1, p["x1"]+width, npos))
        else:
            npos = p["x1"]+1 if direction == "right" else p["x0"]-1
            todo.append((p["y0"]-width, p["y0"]-1, npos))
            todo.append((p["y1"]+1, p["y1"]+width, npos))
    transverse_limit = entry.shape[1] if direction in ("up","down") else entry.shape[0]
    # Branches sent wholly beyond a side edge leave the board harmlessly.
    visible = [q for q in terminal if not (q[1] < 0 or q[0] >= transverse_limit)]
    return sorted(set(visible)) == sorted(set(holes))

def init_state(entry_grid):
    # The run's very first transition has no prior frame and is skipped by the
    # harness rollout; seed its already-consumed turn only on level 0.
    return {"turn": 1 if CURRENT_LEVEL == 0 else 0}

def predict(state, grid, action, x=None, y=None):
    a = np.array(grid, dtype=int).copy()
    if action == 2:
        _shift_colour(a, 9, 0, 4)
    elif action == 3:
        _shift_colour(a, 9, -4, 0)
    elif action == 4:
        _shift_colour(a, 9, 4, 0)
    elif action == 6:
        _select_at(a, x, y)
    solved = (action == 5 and _routing_solution(a))
    turn = int((state or {}).get("turn", 0)) + (1 if action in (1,2,3,4,5,6) else 0)
    if action in (1,2,3,4,5,6):
        _timer_tick(a, turn)
    info = {"level_up": bool(solved), "dead": False, "win": False}
    return a.tolist(), info, {"turn": turn}

def is_goal(state, grid):
    # Completion requires pressing test/fire; step's level_up is the BFS goal.
    return False
