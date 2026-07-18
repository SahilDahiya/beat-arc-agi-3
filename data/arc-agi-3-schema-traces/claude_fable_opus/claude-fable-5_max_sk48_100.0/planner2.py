"""Staged BFS planner for L5: chain of subgoal predicates, each solved by bounded BFS."""
import json, importlib.util
from collections import deque
from planner import latest_grids

spec = importlib.util.spec_from_file_location('wm', 'world_model_v5.py')
wm = importlib.util.module_from_spec(spec)
wm.__dict__['ENTRY_GRID'] = None
spec.loader.exec_module(wm)

entry, cur, level = latest_grids()
wm.ENTRY_GRID = entry
ly = wm.layout(entry)
S0 = wm.extract(cur, ly)


def key(S):
    return (S[0], S[1], S[2], S[3], S[4], tuple(sorted(S[5])))


def actions_of(S, mode='both'):
    top, L, cc0, KL, active, blocks = S
    acts = []
    want_engine = mode in ('both', 'engine')
    want_crane = mode in ('both', 'crane')
    cur_is_engine = active == 6
    if (cur_is_engine and want_engine) or (not cur_is_engine and want_crane):
        acts += [(1, None, None), (2, None, None), (3, None, None), (4, None, None)]
    if ly['crane']:
        if not cur_is_engine and want_engine:
            acts.append((6, ly['ec0'] + 2, top + 2))
        if cur_is_engine and want_crane:
            acts.append((6, cc0 + 2, ly['crane']['htr'][0]))
    return acts


def bfs_stage(S_start, pred, mode='both', max_states=2_000_000):
    start = key(S_start)
    seen = {start: (None, None)}
    q = deque([start])
    expanded = 0
    while q:
        sk = q.popleft()
        expanded += 1
        S = (sk[0], sk[1], sk[2], sk[3], sk[4], list(sk[5]))
        if pred(S):
            path = []
            cur_k = sk
            while seen[cur_k][0] is not None:
                path.append(seen[cur_k][1])
                cur_k = seen[cur_k][0]
            path.reverse()
            return path, S, expanded
        if expanded > max_states:
            return None, None, expanded
        for (a, x, y) in actions_of(S, mode):
            S2, dead, _ = wm.abstract_step(ly, (S[0], S[1], S[2], S[3], S[4], list(S[5])), a, x, y)
            if dead:
                continue
            nk = key(S2)
            if nk == sk or nk in seen:
                continue
            seen[nk] = (sk, (a, x, y))
            q.append(nk)
    return None, None, expanded


def nines(S):
    return sorted((r0, c0) for v, r0, c0 in S[5] if v == 9)

def eights(S):
    return sorted((r0, c0) for v, r0, c0 in S[5] if v == 8)

# master sequence stages (see analysis): park 9s high at 18/24/36, stack 8s at col12
# (rows 9/15/21), plow 9s down to row 33, engine hooks them from below the wall,
# crane re-collects the 8-stack (band-jams at 27) -> goal.

def es(S):
    return sorted((r0, c0) for v, r0, c0 in S[5] if v == 14)

def occ(S):
    return wm.crane_occupants(ly, S[2], S[3], S[5])

def cars(S):
    return wm.cars_of(ly, S[0], S[1], S[5])

def b2(S):  # 8 and c parked at (33,24),(33,30); engine below-track clear
    bl = sorted(S[5])
    return (8, 33, 24) in bl and (12, 33, 30) in bl and S[1] == 1 and S[0] == 32

def b3(S):  # crane holds the 8 (bottom-cap probe happens here)
    return occ(S) == [8]

def b4(S):
    return occ(S) == [8, 12]

def b5(S):
    return occ(S) == [8, 12, 9] and (9, 33, 24) in sorted(S[5])

def b6(S):  # 9 handed to engine at (33,24)
    return cars(S) == [9] and (9, 33, 24) in sorted(S[5])

def b7(S):  # crane released the 9
    return occ(S) == [8, 12] and (9, 33, 24) in sorted(S[5]) and cars(S) == [9]

def b8(S):  # e fetched and held at the handoff spot (bottom-cap probe #2)
    return occ(S) == [8, 12, 14] and cars(S) == [9] and (14, 33, 30) in sorted(S[5])

def b9(S):
    return cars(S) == [9, 14]

def b10(S):
    return wm.goal_satisfied(ly, S)


plan_all = []
S = S0
STAGES = [(b2, 'engine'), (b3, 'crane'), (b4, 'crane'), (b5, 'crane'),
          (b6, 'engine'), (b7, 'crane'), (b8, 'crane'),
          (b9, 'engine'), (b10, 'crane')]
# skip stages already satisfied (start after the furthest-satisfied stage)
start_idx = 0
for j in range(len(STAGES) - 1, -1, -1):
    if STAGES[j][0](S):
        start_idx = j + 1
        break
STAGES = STAGES[start_idx:]
print('skipping to stage', start_idx + 1)
for i, (pred, mode) in enumerate(STAGES, 1):
    path, S2, expanded = bfs_stage(S, pred, mode)
    if path is None:
        print(f'stage {i}: FAILED (expanded {expanded})')
        break
    print(f'stage {i}: {len(path)} steps (expanded {expanded}) mode={mode}')
    plan_all += path
    S = S2
else:
    print('TOTAL plan len:', len(plan_all))
    print(json.dumps([{'action': a, **({'x': x, 'y': y} if x is not None else {})}
                      for a, x, y in plan_all]))
    print('final goal_satisfied:', wm.goal_satisfied(ly, S))
