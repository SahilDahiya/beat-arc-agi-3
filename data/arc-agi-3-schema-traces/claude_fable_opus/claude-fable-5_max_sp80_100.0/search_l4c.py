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
CUPZONE = set()
for (y,x) in CUP:
    for ay in (y-1,y,y+1):
        for ax in (x-1,x,x+1):
            CUPZONE.add((ay,ax))

def fcells(fy, fx):
    cells = set()
    for y in range(fy, fy+3):
        for x in range(fx, fx+6): cells.add((y,x))
    for y in range(fy+3, fy+6):
        for x in range(fx+3, fx+6): cells.add((y,x))
    return cells
def pcells(py, px, w):
    return set((y,x) for y in range(py,py+3) for x in range(px,px+w))
def legal(cells, occupied):
    for c in cells:
        y,x = c
        if not (0<=y<=63 and 0<=x<=63): return False
        if STATIC[y][x] != BG: return False
        if c in occupied: return False
        if c in CUPZONE: return False
    return True

sim = ns['_simulate_pour']
pys = [p for p in range(5, 51) if p % 3 == 2]
W = {"P1":12, "P2":9, "P3":15}

t0 = time.time()
stage1 = []
for fx in [p for p in range(8, 45) if p % 3 == 2]:
    FC = fcells(35, fx)
    if not legal(FC, set()): continue
    for c1n, c2n in itertools.permutations(["P1","P2","P3"], 2):
        w1, w2 = W[c1n], W[c2n]
        px1s = [p for p in range(5, 21) if p % 3 == 2 and p <= 20 and p + w1 - 1 >= 22]
        px2s = [p for p in range(30, 45) if p % 3 == 2 and p <= 44 and p + w2 - 1 >= 46]
        for px1 in px1s:
            for py1 in pys:
                C1 = pcells(py1, px1, w1)
                if not legal(C1, FC): continue
                for px2 in px2s:
                    for py2 in pys:
                        C2 = pcells(py2, px2, w2)
                        if not legal(C2, FC | C1): continue
                        g = [row[:] for row in STATIC]
                        for (y,x) in FC: g[y][x] = 15
                        for (y,x) in C1 | C2: g[y][x] = 8
                        r, strays, cups, fh = sim(g, entry, [FC])
                        if len(r) == 4 and strays <= 2:
                            stage1.append((strays, fx, c1n, (py1,px1), c2n, (py2,px2)))
    if time.time() - t0 > 150: break
stage1.sort()
print("stage1 candidates:", len(stage1), "time", round(time.time()-t0,1))
for s in stage1[:8]: print(s)

# stage 2: add the third piece to kill remaining strays
sols = []
t1 = time.time()
for (strays, fx, c1n, p1pos, c2n, p2pos) in stage1[:200]:
    hn = [n for n in W if n not in (c1n, c2n)][0]
    wh = W[hn]
    FC = fcells(35, fx)
    C1 = pcells(p1pos[0], p1pos[1], W[c1n])
    C2 = pcells(p2pos[0], p2pos[1], W[c2n])
    occ = FC | C1 | C2
    for pxh in [p for p in range(5, 62-wh+1) if p % 3 == 2]:
        for pyh in pys:
            CH = pcells(pyh, pxh, wh)
            if not legal(CH, occ): continue
            g = [row[:] for row in STATIC]
            for (y,x) in FC: g[y][x] = 15
            for (y,x) in C1 | C2 | CH: g[y][x] = 8
            r, s2, cups, fh = sim(g, entry, [FC])
            if len(r) == 4 and s2 == 0:
                sols.append((fx, c1n, p1pos, c2n, p2pos, hn, (pyh,pxh)))
    if sols or time.time()-t1 > 100: break
print("SOLUTIONS:", len(sols))
for s in sols[:10]: print(s)
