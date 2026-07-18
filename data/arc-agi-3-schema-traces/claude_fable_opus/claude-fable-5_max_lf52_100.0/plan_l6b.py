import pickle, sys
from collections import deque

EAST = {(102,18),(102,24),(108,6),(108,12),(108,18),(114,6),(114,18),(114,24),(114,30),
        (120,6),(120,18),(126,6),(126,18),(126,24),(126,30),(126,36),(132,6),(132,12),
        (132,18),(138,18),(138,24),(138,30)}
WESTC = {(72,12),(78,12),(84,12),(90,12),(90,18),
         (6,24),(12,24),(18,24),(24,24),(30,24),(36,24),(42,24),(60,24),(66,24),(72,24),(78,24),
         (12,36),(12,42),(18,36),(24,30),(24,36),(30,36),(36,36),(42,36),(42,42),
         (54,36),(54,42),(54,48),(60,30),(60,36),(60,48),(66,36),(66,48),(66,54),
         (72,18),(72,36),(72,42)}
DIRS = {1:(0,-6),2:(0,6),3:(-6,0),4:(6,0)}

def arrow(cfg, a):
    # cfg = (C, walls(frozenset), w1, w2); returns new cfg or same if nothing moves
    C, walls, w1, w2 = cfg
    items = [('C',C,EAST)] + [('W',w,EAST) for w in sorted(walls)] + [('x',w1,WESTC),('y',w2,WESTC)]
    d = DIRS[a]
    pos = {i:p for i,(n,p,net) in enumerate(items)}
    movers = {}
    for i,(n,p,net) in enumerate(items):
        t = (p[0]+d[0], p[1]+d[1])
        if t in net:
            movers[i] = t
    changed = True
    while changed:
        changed = False
        stay = {pos[i] for i in pos if i not in movers}
        for i in list(movers):
            if movers[i] in stay:
                del movers[i]; changed = True
    if not movers:
        return None
    np_ = {i: movers.get(i, pos[i]) for i in pos}
    nwalls = frozenset(np_[i] for i,(n,p,net) in enumerate(items) if n=='W')
    return (np_[0], nwalls, np_[len(items)-2], np_[len(items)-1])

def bfs(cfg0, targetf, maxn=400000):
    q = deque([cfg0]); prev = {cfg0: None}
    while q:
        c = q.popleft()
        if targetf(c):
            path = []
            x = c
            while prev[x] is not None:
                x, a = prev[x]
                path.append(a)
            path.reverse()
            return path, c
        for a in (1,2,3,4):
            n = arrow(c, a)
            if n is not None and n not in prev:
                prev[n] = (c, a)
                q.append(n)
        if len(prev) > maxn:
            raise RuntimeError('bfs cap')
    raise RuntimeError('no target')

# start config from replayed state
cfg = ((132,18), frozenset({(102,18),(126,6),(138,24)}), (84,12), (6,24))

plan = []  # list of (action, x, y) with screen coords cam=(84,0)
def clicks(*cells):
    for (wx,wy) in cells:
        plan.append((6, wx-84+1, wy+1))

# Phase A: C deepest in x=138 spur; (138,24),(138,18) free
pA, cfg = bfs(cfg, lambda c: c[0]==(138,30) and (138,24) not in c[1] and (138,18) not in c[1])
plan.extend((a,None,None) for a in pA)
print('Phase A arrows:', pA, 'cfg:', cfg)
# J1: fe boards C  (click fe(138,42), click C(138,30))
clicks((138,42),(138,30))

# Phase B: C-fe -> (114,30)
pB, cfg = bfs(cfg, lambda c: c[0]==(114,30))
plan.extend((a,None,None) for a in pB)
print('Phase B arrows:', pB, 'cfg:', cfg)
# J2: fe consume-drop over e -> (114,42)   *** consume ***
clicks((114,30),(114,42))
# J3,J4: fe walks west on row 42
clicks((114,42),(102,42))
clicks((102,42),(90,42))

# Phase C: C@(138,24), wall@(138,30), wall@(114,30), and (114,24),(114,18),(138,18) free
def tgtC(c):
    C,w,w1,w2 = c
    return (C==(138,24) and (138,30) in w and (114,30) in w
            and (114,24) not in w and (114,18) not in w and (138,18) not in w)
pC, cfg = bfs(cfg, tgtC)
plan.extend((a,None,None) for a in pC)
print('Phase C arrows:', pC, 'cfg:', cfg)
# J5: 8 boards C (click 8(138,36), click C(138,24))
clicks((138,36),(138,24))

# Phase D: C-8 -> (114,24) with wall still @(114,30)
pD, cfg = bfs(cfg, lambda c: c[0]==(114,24) and (114,30) in c[1])
plan.extend((a,None,None) for a in pD)
print('Phase D arrows:', pD, 'cfg:', cfg)
# J6: 8 drops -> (114,36)
clicks((114,24),(114,36))
# J7,J8: 8 walks west on row 36
clicks((114,36),(102,36))
clicks((102,36),(90,36))
# J9: fe column entry over 8 -> (90,30)
clicks((90,42),(90,30))
# J10,J11: 8 returns east on row 36
clicks((90,36),(102,36))
clicks((102,36),(114,36))
# J12: 8 re-boards C (click 8(114,36), click C(114,24))
clicks((114,36),(114,24))

# Phase E: separate C-8 from wall / everything; try press 1 then extras
# after J12: C loaded @(114,24), wall@(114,30)
pE, cfgE = bfs(cfg, lambda c: c[0]==(114,18) and (114,24) not in c[1].difference({(114,30)}) if False else c[0]==(114,18))
plan.extend((a,None,None) for a in pE)
print('Phase E arrows:', pE, 'cfg after:', cfgE)
print('TOTAL actions:', len(plan))
pickle.dump(plan, open('l6_action_plan.pkl','wb'))
for p in plan: print(p)
