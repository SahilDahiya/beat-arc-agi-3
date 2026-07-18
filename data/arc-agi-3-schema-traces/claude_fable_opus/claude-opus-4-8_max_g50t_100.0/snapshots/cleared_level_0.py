import numpy as np
from collections import deque

# ===================== Level 0: maze navigation + layer toggle =====================
# MOVER: 5x5 block of 9s (ring, center hole) translating PITCH=6 cells/move.
#   action 1=up, 2=down, 3=left, 4=right (normal moves; blocked by 0 and 8).
#   action 5 = if mover != START: teleport mover to START + toggle legend state0<->state1;
#              else noop. (Verified across act#3,4,14,16.)
# Corridors=5 (passable). Walls=0. 8-trail=impassable.
# BORDER COUNTER: row63 fills from RIGHT with color 1; count=floor(true_actions/2).
#   Framework skips predict() on the level's first action, so n_actions is 1 short:
#   render count = (n_actions+1)//2.
# LEGEND (top-left rows1-5 cols1-7): reflects legend_state (0 or 1).
# 2-RING: a ghost that appears in state1 after the mover moves >=2 tiles from start. NOT yet
#   modeled (its rule is still unknown) -> backtest mismatches only on its spawn/move steps.
# BOX (bottom-right): changed once on very first move (un-backtestable) -> left as-is.

PITCH = 6
SIZE = 5

_LEGEND0 = {  # state0: L=9-ring, R=1-solid, row5 999@L
    (1,1):9,(1,2):9,(1,3):9, (1,5):1,(1,6):1,(1,7):1,
    (2,1):9,(2,2):0,(2,3):9, (2,5):1,(2,6):1,(2,7):1,
    (3,1):9,(3,2):9,(3,3):9, (3,5):1,(3,6):1,(3,7):1,
    (5,1):9,(5,2):9,(5,3):9, (5,5):0,(5,6):0,(5,7):0,
}
_LEGEND1 = {  # state1: L=2-ring, R=9-ring, row5 999@R
    (1,1):2,(1,2):2,(1,3):2, (1,5):9,(1,6):9,(1,7):9,
    (2,1):2,(2,2):0,(2,3):2, (2,5):9,(2,6):0,(2,7):9,
    (3,1):2,(3,2):2,(3,3):2, (3,5):9,(3,6):9,(3,7):9,
    (5,1):0,(5,2):0,(5,3):0, (5,5):9,(5,6):9,(5,7):9,
}

def _components(grid, val):
    H, W = grid.shape
    seen = np.zeros((H, W), dtype=bool); comps = []
    for y in range(H):
        for x in range(W):
            if grid[y, x] == val and not seen[y, x]:
                q = deque([(y, x)]); seen[y, x] = True; cells = [(y, x)]
                while q:
                    cy, cx = q.popleft()
                    for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                        ny, nx = cy+dy, cx+dx
                        if 0<=ny<H and 0<=nx<W and grid[ny,nx]==val and not seen[ny,nx]:
                            seen[ny,nx]=True; q.append((ny,nx)); cells.append((ny,nx))
                ys=[c[0] for c in cells]; xs=[c[1] for c in cells]
                comps.append({'cells':cells,'y0':min(ys),'y1':max(ys),
                              'x0':min(xs),'x1':max(xs),'n':len(cells)})
    return comps

def _find_mover(grid):
    for c in _components(grid, 9):
        if (c['y1']-c['y0']+1)==SIZE and (c['x1']-c['x0']+1)==SIZE and c['x0']>10:
            return c
    return None

def _has_legend(g):
    try:
        return (g[1,1] in (9,2) and g[2,2]==0 and g[1,3] in (9,2)
                and g[3,1] in (9,2) and g[1,2] in (9,2))
    except Exception:
        return False

def init_state(entry_grid):
    g = np.array(entry_grid)
    mover = _find_mover(g)
    start = (mover['y0'], mover['x0']) if mover else (8, 14)
    return {'n_actions': 0, 'legend_state': 0, 'has_legend': _has_legend(g),
            'start': start}

def _place_ring(out, pattern, y0, x0):
    for i in range(SIZE):
        for j in range(SIZE):
            if pattern[i, j] == 9:
                out[y0+i, x0+j] = 9

def _try_move(g, out, mover, dr, dc):
    H, W = g.shape
    y0, x0 = mover['y0'], mover['x0']
    ny0, nx0 = y0+dr, x0+dc
    if ny0<0 or nx0<0 or ny0+SIZE>H or nx0+SIZE>W:
        return False
    mset = set(mover['cells'])
    pattern = g[y0:y0+SIZE, x0:x0+SIZE].copy()
    # Only the cells the mover OCCUPIES (pattern==9) must be clear; the ring's center HOLE
    # (pattern!=9) can pass over anything (e.g. the goal-box peg fits in the hole).
    for i in range(SIZE):
        for j in range(SIZE):
            if pattern[i, j] != 9:
                continue
            yy, xx = ny0+i, nx0+j
            if (yy, xx) in mset:
                continue
            if g[yy, xx] not in (5, 2):  # 5=corridor, 2=ghost overlay (passable)
                return False
    for (cy,cx) in mover['cells']:
        out[cy,cx]=5
    _place_ring(out, pattern, ny0, nx0)
    return True

_DIRS = {1:(-PITCH,0), 2:(PITCH,0), 3:(0,-PITCH), 4:(0,PITCH)}

def predict(state, grid, action, x=None, y=None):
    g = np.array(grid); out = g.copy()
    info = {"level_up": False, "dead": False, "win": False}
    st = {'n_actions': state.get('n_actions', 0),
          'legend_state': state.get('legend_state', 0),
          'has_legend': state.get('has_legend', _has_legend(g)),
          'start': state.get('start', (8, 14)),
          'moved': state.get('moved', False)}  # moved since last toggle
    st['n_actions'] += 1

    mover = _find_mover(g)

    if action in _DIRS and mover is not None:
        dr, dc = _DIRS[action]
        if _try_move(g, out, mover, dr, dc):
            st['moved'] = True
    elif action == 5 and mover is not None:
        # action5 toggles legend + teleports mover to start, IF the mover has moved since the
        # last toggle; otherwise noop. (Verified: tour ending at start still toggled.)
        if st['moved']:
            sy, sx = st['start']
            if (mover['y0'], mover['x0']) != (sy, sx):
                pattern = g[mover['y0']:mover['y0']+SIZE, mover['x0']:mover['x0']+SIZE].copy()
                for (cy,cx) in mover['cells']:
                    out[cy,cx]=5
                _place_ring(out, pattern, sy, sx)
            st['legend_state'] = 1 - st['legend_state']
            st['moved'] = False

    # toggling to state0 removes the 2-ring ghost from the maze
    if st['has_legend'] and st['legend_state'] == 0:
        out[out == 2] = 5

    # render legend to match state
    if st['has_legend']:
        leg = _LEGEND1 if st['legend_state']==1 else _LEGEND0
        for (yy,xx),v in leg.items():
            out[yy,xx]=v
        # border counter = floor(actions_this_life / 2). Framework skips predict on the level's
        # very first action but NOT the first post-reset action, so post-reset n_actions == true
        # action count -> floor(n_actions/2). (Pre-reset history is off-by-one here; cosmetic.)
        H, W = out.shape
        cnt = st['n_actions'] // 2
        for k in range(cnt):
            if W-1-k >= 0:
                out[H-1, W-1-k] = 1

    return out.tolist(), info, st

def is_goal(state, grid):
    g = np.array(grid)
    m = _find_mover(g)
    if m is None:
        return False
    # WIN hypothesis: the 5x5 mover reaches the bottom component / goal box (y0 >= 44)
    return m['y0'] >= 44
