"""Abstract-state BFS planner. Uses world_model_v5.abstract_step as single source of truth.
State: (top, L, cc0, KL, active, blocks). Actions: 1-4 + hub-toggle clicks."""
import json, sys, importlib.util
from collections import deque

spec = importlib.util.spec_from_file_location('wm', 'world_model_v5.py')
wm = importlib.util.module_from_spec(spec)
wm.__dict__['ENTRY_GRID'] = None
spec.loader.exec_module(wm)


def latest_grids():
    events = [json.loads(l) for l in open('events.jsonl')]
    cur = None; level = None
    for e in reversed(events):
        if e['kind'] in ('turn_started', 'action_taken'):
            g = e['grid']
            cur = json.loads(g) if isinstance(g, str) else g
            level = int(e['level']) if 'level' in e else None
            break
    entry = None
    prev_level = None
    for e in events:
        if e['kind'] == 'turn_started' and e.get('env_step') in ('0', 0):
            g = e['grid']
            entry = json.loads(g) if isinstance(g, str) else g
            prev_level = 0
        if e['kind'] == 'action_taken':
            g = json.loads(e['grid']) if isinstance(e['grid'], str) else e['grid']
            lv = int(e['level'])
            if e.get('level_up') in ('True', True) or lv != prev_level:
                entry = g
            if e.get('action') in (0, '0'):
                entry = g
            prev_level = lv
    return entry, cur, level


def plan(entry, cur, max_states=4_000_000):
    wm.ENTRY_GRID = entry
    ly = wm.layout(entry)
    S0 = wm.extract(cur, ly)

    def key(S):
        top, L, cc0, KL, active, blocks = S
        return (top, L, cc0, KL, active, tuple(sorted(blocks)))

    def actions_of(S):
        acts = [(1, None, None), (2, None, None), (3, None, None), (4, None, None)]
        top, L, cc0, KL, active, blocks = S
        if ly['crane']:
            if active != 6:
                acts.append((6, ly['ec0'] + 2, top + 2))       # activate engine
            if active == 6:
                acts.append((6, cc0 + 2, ly['crane']['htr'][0]))  # activate crane
        return acts

    start = key(S0)
    seen = {start: (None, None)}
    q = deque([start])
    expanded = 0
    while q:
        sk = q.popleft()
        expanded += 1
        S = (sk[0], sk[1], sk[2], sk[3], sk[4], list(sk[5]))
        if wm.goal_satisfied(ly, S):
            path = []
            cur_k = sk
            while seen[cur_k][0] is not None:
                path.append(seen[cur_k][1])
                cur_k = seen[cur_k][0]
            path.reverse()
            return path, sk, expanded
        if expanded > max_states:
            break
        for (a, x, y) in actions_of(S):
            S2, dead, _ = wm.abstract_step(ly, (S[0], S[1], S[2], S[3], S[4], list(S[5])), a, x, y)
            if dead:
                continue
            nk = key(S2)
            if nk == sk or nk in seen:
                continue
            seen[nk] = (sk, (a, x, y))
            q.append(nk)
    return None, None, expanded


if __name__ == '__main__':
    entry, cur, level = latest_grids()
    print('level:', level)
    path, final, expanded = plan(entry, cur)
    print('expanded:', expanded)
    if path:
        print('PLAN len', len(path), ':')
        print(json.dumps([{'action': a, **({'x': x, 'y': y} if x is not None else {})}
                          for a, x, y in path]))
        print('final:', final)
    else:
        print('NO SOLUTION found')
