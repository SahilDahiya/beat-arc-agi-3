import itertools, time
src = open('world_model_v5.py').read()
ns = {}
exec(compile(src, 'wm', 'exec'), ns)
BG = 12
entry = [[BG]*64 for _ in range(64)]
for x in range(64):
    entry[0][x] = 14
    entry[1][x] = 1
    for y in range(59, 64): entry[y][x] = 1
for y in range(2, 59):
    entry[y][0] = entry[y][1] = 1
    entry[y][62] = entry[y][63] = 1
for y in range(2, 5):
    for x in range(23, 26): entry[y][x] = 4
for y in range(5, 8):
    for x in range(23, 26): entry[y][x] = 6
def cup(x0):
    for y in range(53, 56):
        for x in range(x0, x0+3): entry[y][x] = 11
        for x in range(x0+6, x0+9): entry[y][x] = 11
    for y in range(56, 59):
        for x in range(x0, x0+9): entry[y][x] = 11
for x0 in (8, 27, 39, 51): cup(x0)
static = [row[:] for row in entry]
ns['ENTRY_GRID'] = entry
ns['CURRENT_LEVEL'] = 3
CUPCELLS = {(y,x) for y in range(64) for x in range(64) if entry[y][x] == 11}
PIECES = [("A",15,False),("B",15,False),("C",21,True),("D",12,False),("E",12,False)]
ENTRYPOS = {"A":(17,17),"B":(17,38),"C":(28,8),"D":(31,44),"E":(40,38)}
W = {n:w for n,w,_ in PIECES}
EM = {n:e for n,_,e in PIECES}

def compose(pl):
    cells = {}
    for name in pl:
        py, px = pl[name]
        w = W[name]
        for yy in range(py, py+3):
            for xx in range(px, px+w):
                if not (0<=yy<=63 and 0<=xx<=63): return None
                if static[yy][xx] != BG: return None
                if (yy,xx) in cells: return None
                cells[(yy,xx)] = name
    for (yy,xx) in cells:
        for (ay,ax) in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
            if (ay,ax) in CUPCELLS: return None
    g = [row[:] for row in static]
    for name in pl:
        py, px = pl[name]
        for yy in range(py, py+3):
            for xx in range(px, px+w if False else px+W[name]):
                g[yy][xx] = 8
        if EM[name]:
            for yy in range(py, py+3):
                for xx in range(px+9, px+12):
                    g[yy][xx] = 4
    return g

sim = ns['_simulate_pour']
def score(pl):
    g = compose(pl)
    if g is None: return None
    reached, strays, cups, fh = sim(g, entry)
    return (len(reached), strays)

def cost(pl):
    c = 0
    for n in pl:
        (ey, ex), (py, px) = ENTRYPOS[n], pl[n]
        d = (abs(py-ey) + abs(px-ex)) // 3
        c += d + (1 if d else 0)
    return c

def lat(name):
    w = W[name]
    py_mod = 2 if name in ("A","B") else 1
    return ([p for p in range(2, 51) if p % 3 == py_mod],
            [p for p in range(2, 62-w+1) if p % 3 == 2])

# spot sets for spares: parks + low rows
def spots(name):
    pys, pxs = lat(name)
    parks = [(2,2),(2,26),(2,47),(5,47),(8,2)]
    out = []
    for (py,px) in parks:
        py2 = py if py in pys else py+1 if (py+1) in pys else py+2
        if py2 in pys and px in pxs: out.append((py2,px))
    for py in pys:
        if py >= 43:
            for px in pxs:
                out.append((py,px))
    return sorted(set(out))

t0 = time.time()
# stage 1: (C, K) with spares parked far
PARKS1 = {"A":(2,2),"B":(2,2),"C":(4,2),"D":(2,47),"E":(8,47)}
base_list = []
pysC, pxsC = lat("C")
for cn in ("A","B","D","E"):
    pysK, pxsK = lat(cn)
    for pxK in [p for p in pxsK if p <= 23 and p+W[cn]-1 >= 25]:
        for pyK in pysK:
            for pxC in pxsC:
                for pyC in pysC:
                    pl = dict(PARKS1)
                    pl["C"] = (pyC, pxC)
                    pl[cn] = (pyK, pxK)
                    s = score(pl)
                    if s and s[0] == 4:
                        base_list.append((s[1], pl.copy(), cn))
base_list.sort(key=lambda t: (t[0], cost(t[1])))
print("stage1", round(time.time()-t0,1), "4cup bases:", len(base_list), "beststrays:", base_list[0][0] if base_list else None)

sols = []
t1 = time.time()
for stray0, base, cn in base_list[:40]:
    spares = [n for n in W if n != cn and n != "C"]
    # single spare
    for nm in spares:
        for sp in spots(nm):
            pl = dict(base); pl[nm] = sp
            if score(pl) == (4,0):
                sols.append((cost(pl), pl))
    if sols: break
    # pairs
    for nm1, nm2 in itertools.combinations(spares, 2):
        for sp1 in spots(nm1):
            pl1 = dict(base); pl1[nm1] = sp1
            for sp2 in spots(nm2):
                pl = dict(pl1); pl[nm2] = sp2
                if score(pl) == (4,0):
                    sols.append((cost(pl), pl))
        if sols: break
    if sols or time.time()-t1 > 200:
        break
sols.sort(key=lambda t: t[0])
for c, pl in sols[:8]:
    print("SOL cost", c, pl)
print("done", round(time.time()-t0,1), "sols:", len(sols))
