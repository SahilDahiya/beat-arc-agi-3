import itertools, time
src = open('world_model_v5.py').read()
ns = {}
exec(compile(src, 'wm', 'exec'), ns)
BG = 12
entry = [[BG]*64 for _ in range(64)]
for x in range(64):
    for y in range(5): entry[y][x] = 1
    entry[62][x] = 1
    entry[63][x] = 14
for y in range(5, 62):
    for x in range(5): entry[y][x] = 1
    entry[y][62] = entry[y][63] = 1
def cupdown(x0):
    for y in range(5, 8):
        for x in range(x0, x0+9): entry[y][x] = 11
    for y in range(8, 11):
        for x in range(x0, x0+3): entry[y][x] = 11
        for x in range(x0+6, x0+9): entry[y][x] = 11
cupdown(17); cupdown(35); cupdown(47)
for y in range(35, 38):
    for x in range(5, 11): entry[y][x] = 11
for y in range(38, 41):
    for x in range(5, 8): entry[y][x] = 11
for y in range(41, 44):
    for x in range(5, 11): entry[y][x] = 11
for sx in (20, 44):
    for y in range(56, 59):
        for x in range(sx, sx+3): entry[y][x] = 6
    for y in range(59, 62):
        for x in range(sx, sx+3): entry[y][x] = 4
STATIC = [row[:] for row in entry]
ns['ENTRY_GRID'] = entry
ns['CURRENT_LEVEL'] = 4
CUP = {(y,x) for y in range(64) for x in range(64) if entry[y][x]==11}

def fcells(fy, fx):  # bar rows fy..fy+2 x fx..fx+5; stem rows fy+3..fy+5 x fx+3..fx+5
    cells = set()
    for y in range(fy, fy+3):
        for x in range(fx, fx+6): cells.add((y,x))
    for y in range(fy+3, fy+6):
        for x in range(fx+3, fx+6): cells.add((y,x))
    return cells

def pcells(py, px, w):
    return set((y,x) for y in range(py,py+3) for x in range(px,px+w))

def legal(cells, occupied):
    for (y,x) in cells:
        if not (0<=y<=63 and 0<=x<=63): return False
        if STATIC[y][x] != BG: return False
        if (y,x) in occupied: return False
        for ay in (y-1,y,y+1):
            for ax in (x-1,x,x+1):
                if (ay,ax) in CUP: return False
    return True

sim = ns['_simulate_pour']
def trial(fpos, p1, p2, p3):
    occ = set()
    fc = fcells(*fpos)
    if not legal(fc, occ): return None
    occ |= fc
    c1 = pcells(p1[0], p1[1], 12)
    if not legal(c1, occ): return None
    occ |= c1
    c2 = pcells(p2[0], p2[1], 9)
    if not legal(c2, occ): return None
    occ |= c2
    c3 = pcells(p3[0], p3[1], 15)
    if not legal(c3, occ): return None
    occ |= c3
    g = [row[:] for row in STATIC]
    for (y,x) in fc: g[y][x] = 15
    for (y,x) in c1|c2|c3: g[y][x] = 8
    r, strays, cups, fh = sim(g, entry, [fc])
    return (len(r), strays)

pys = [p for p in range(5, 51) if p % 3 == 2]
pxs = lambda w: [p for p in range(5, 62-w+1) if p % 3 == 2]

t0 = time.time()
best = []
# F: stem rows must be 38-40 => fy = 35; fx range
Fs = [(35, fx) for fx in pxs(6)]
# P2 fixed role guess removed - full search over roles is too big; instead:
# enumerate P3 (catcher of one stream), P2, P1 over "meaningful" spots:
spots3 = [(py, px) for py in pys for px in pxs(15)]
spots1 = [(py, px) for py in pys for px in pxs(12)]
spots2 = [(py, px) for py in pys for px in pxs(9)]
# restrict: P3 must cover a stream column (20-22 or 44-46) OR park top-right
def covers(px, w, sx):
    return px <= sx and px + w - 1 >= sx + 2
cand3 = [s for s in spots3 if covers(s[1], 15, 20) or covers(s[1], 15, 44)]
cand2 = [s for s in spots2 if covers(s[1], 9, 20) or covers(s[1], 9, 44) or s[0] in (11, 14)]
cand1 = [s for s in spots1 if covers(s[1], 12, 20) or covers(s[1], 12, 44) or s[0] in (11, 14)]
parks3 = [(11, 47), (14, 47), (11, 26), (47, 47)]
parks2 = [(11, 26), (47, 5), (11, 5), (50, 50)]
parks1 = [(47, 5), (50, 20), (11, 26), (47, 50)]
cand3 += parks3; cand2 += parks2; cand1 += parks1
print("space:", len(Fs), len(cand3), len(cand2), len(cand1))
cnt = 0
for fpos in Fs:
    for p3 in cand3:
        for p2 in cand2:
            for p1 in cand1:
                cnt += 1
                s = trial(fpos, p1, p2, p3)
                if s and s[0] == 4 and s[1] == 0:
                    best.append((fpos, p1, p2, p3))
                    if len(best) >= 12: break
            if len(best) >= 12: break
        if len(best) >= 12: break
    if len(best) >= 12 or time.time()-t0 > 240: break
print("tried", cnt, "time", round(time.time()-t0,1))
ENTRYPOS = {"P1": (20,29), "P2": (32,20), "P3": (47,38), "F": (41,32)}
def cost(fpos, p1, p2, p3):
    c = 0
    for nm, pos in (("F",fpos),("P1",p1),("P2",p2),("P3",p3)):
        (ey,ex),(py,px2) = ENTRYPOS[nm], pos
        d = (abs(py-ey)+abs(px2-ex))//3
        c += d + (1 if d else 0)
    return c
best.sort(key=lambda t: cost(*t))
for b in best[:6]:
    print("SOL cost", cost(*b), "F",b[0],"P1",b[1],"P2",b[2],"P3",b[3])
