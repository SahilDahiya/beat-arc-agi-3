import numpy as np
from collections import deque

BG = 10


def _largest_zero_component(a):
    seen = np.zeros(a.shape, dtype=bool)
    best = []
    h, w = a.shape
    for y, x in np.argwhere((a == 0) & (~seen)):
        if seen[y, x]:
            continue
        comp = []; q = deque([(int(y), int(x))]); seen[y, x] = True
        while q:
            yy, xx = q.popleft(); comp.append((yy, xx))
            for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                ny, nx = yy+dy, xx+dx
                if 0 <= ny < h and 0 <= nx < w and not seen[ny,nx] and a[ny,nx] == 0:
                    seen[ny,nx] = True; q.append((ny,nx))
        if len(comp) > len(best): best = comp
    return best


def _moving_mask(a):
    # Movable piece = largest black component plus its attached 3x3 color-8
    # terminals.  Limit traversal through 8 to depth 3 so face-adjacent fixed
    # terminals are not accidentally absorbed into the movable component.
    core = _largest_zero_component(a)
    mask = np.zeros(a.shape, dtype=bool)
    if not core: return mask
    for y, x in core: mask[y,x] = True
    q = deque((y,x,0) for y,x in core); best = {(y,x):0 for y,x in core}
    while q:
        y, x, d = q.popleft()
        if d >= 3: continue
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
            yy, xx = y+dy, x+dx
            if 0 <= yy < a.shape[0] and 0 <= xx < a.shape[1] and a[yy,xx] == 8:
                nd = d+1
                if nd < best.get((yy,xx), 99):
                    best[(yy,xx)] = nd; mask[yy,xx] = True; q.append((yy,xx,nd))
    return mask


def _place(a, mask, ny, nx, vals):
    ys, xs = np.where(mask)
    if (np.any(ny < 0) or np.any(ny >= a.shape[0]) or
        np.any(nx < 0) or np.any(nx >= a.shape[1])):
        return a, False, False
    fixed = (a[ny,nx] != BG) & (~mask[ny,nx])
    # Docking allows only like-for-like overlap of blue terminal pixels.
    allowed_overlap = fixed & (vals == 8) & (a[ny,nx] == 8)
    if np.any(fixed & (~allowed_overlap)):
        return a, False, False
    fixed8 = set(map(tuple, np.argwhere((a == 8) & (~mask))))
    moved8 = set((int(y),int(x)) for y,x,v in zip(ny,nx,vals) if v == 8)
    docked = bool(fixed8) and moved8 == fixed8
    out = a.copy(); out[ys,xs] = BG; out[ny,nx] = vals
    return out, True, docked


def _raw_step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    info = {"level_up": False, "dead": False, "win": False}
    mask = _moving_mask(a)
    if not np.any(mask): return a.tolist(), info
    ys, xs = np.where(mask); vals = a[ys,xs].copy()

    delta = {1:(-3,0), 2:(3,0), 3:(0,-3), 4:(0,3)}
    if action in delta:
        dy, dx = delta[action]
        out, moved, docked = _place(a, mask, ys+dy, xs+dx, vals)
        info["level_up"] = docked
        return out.tolist(), info

    if action == 5:
        # Clockwise quarter-turn of the piece's tight bounding box, with its
        # top-left corner anchored.
        y0, x0 = int(ys.min()), int(xs.min())
        height = int(ys.max()-y0+1)
        ry, rx = ys-y0, xs-x0
        ny = y0 + rx
        nx = x0 + (height-1-ry)
        out, moved, docked = _place(a, mask, ny, nx, vals)
        info["level_up"] = docked
        return out.tolist(), info

    return a.tolist(), info


def init_state(entry_grid):
    # The harness has no before-frame for the run's very first action and
    # cannot replay it; seed level 0 past that one already-taken action.
    return {"turn": 1 if CURRENT_LEVEL == 0 else 0}


def predict(state, grid, action, x=None, y=None):
    # Track actions used in this level for the proportional budget bar.
    turn = int((state or {}).get("turn", 0)) + 1
    nxt, info = _raw_step(grid, action, x, y)
    out = np.array(nxt, dtype=int)
    # The 32-pixel bar renders a 75-action level budget proportionally.
    # Rounding makes its early fill thresholds occur at turns 2,4,6,9,...
    desired = int(np.floor(turn * 32.0 / 75.0 + 0.5))
    black_meter = int(np.sum(out[0] == 0))
    while black_meter < desired:
        fours = np.where(out[0] == 4)[0]
        if not len(fours): break
        out[0, int(fours.min())] = 0
        black_meter += 1
    return out.tolist(), info, {"turn": turn}


def is_goal(grid):
    a = np.array(grid, dtype=int)
    mask = _moving_mask(a)
    if not np.any(mask): return False
    fixed8 = set(map(tuple, np.argwhere((a == 8) & (~mask))))
    moving8 = set(map(tuple, np.argwhere((a == 8) & mask)))
    return bool(fixed8) and moving8 == fixed8
