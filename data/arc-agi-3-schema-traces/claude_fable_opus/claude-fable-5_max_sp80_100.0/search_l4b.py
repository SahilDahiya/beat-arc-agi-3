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

P2C = pcells(35, 41, 9)
best = []
t0 = time.time()
tried = 0
for fx in [p for p in range(8, 45) if p % 3 == 2]:
    FC = fcells(35, fx)
    if not legal(FC, set()): continue
    if FC & P2C: continue
    for px3 in (8, 11, 14, 17, 20):
        for py3 in pys:
            C3 = pcells(py3, px3, 15)
            if not legal(C3, FC | P2C): continue
            base_occ = FC | P2C | C3
            for px1 in [p for p in range(5, 51) if p % 3 == 2]:
                for py1 in pys:
                    C1 = pcells(py1, px1, 12)
                    if not legal(C1, base_occ): continue
                    tried += 1
                    g = [row[:] for row in STATIC]
                    for (y,x) in FC: g[y][x] = 15
                    for (y,x) in P2C | C3 | C1: g[y][x] = 8
                    r, strays, cups, fh = sim(g, entry, [FC])
                    if len(r) == 4 and strays == 0:
                        best.append((fx, (py3,px3), (py1,px1)))
            if best: break
        if best: break
    if best or time.time()-t0 > 230: break
print("tried", tried, "time", round(time.time()-t0,1))
for b in best[:10]:
    print("SOL F=(35,%d) P3=%s P1=%s P2=(35,41)" % b)
