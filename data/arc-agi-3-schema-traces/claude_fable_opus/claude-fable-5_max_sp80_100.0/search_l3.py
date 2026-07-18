import itertools, time, sys
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

def lattice(name):
    w = W[name]
    py_mod = 2 if name in ("A","B") else 1
    pys = [p for p in range(2, 51) if p % 3 == py_mod]
    pxs = [p for p in range(2, 62-w+1) if p % 3 == 2]
    return pys, pxs

def compose(pl):
    cells = {}
    for (name, w, em) in PIECES:
        py, px = pl[name]
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
    for (name, w, em) in PIECES:
        py, px = pl[name]
        for yy in range(py, py+3):
            for xx in range(px, px+w):
                g[yy][xx] = 8
        if em:
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
    for n in W:
        (ey, ex), (py, px) = ENTRYPOS[n], pl[n]
        d = (abs(py-ey) + abs(px-ex)) // 3
        c += d + (1 if d else 0)  # moves + click
    return c

t0 = time.time()
results = []
pysC, pxsC = lattice("C")
catchers = []
for cn in ("A","B","D","E"):
    pys, pxs = lattice(cn)
    for px in [p for p in pxs if p <= 23 and p+W[cn]-1 >= 25]:
        for py in pys:
            catchers.append((cn, py, px))
for pxC in pxsC:
    for pyC in pysC:
        for (cn, pyK, pxK) in catchers:
            if cn == "C": continue
            pl = dict(ENTRYPOS)
            pl["C"] = (pyC, pxC)
            pl[cn] = (pyK, pxK)
            s = score(pl)
            if s and s[0] == 4:
                results.append((s, pl.copy()))
print("stage1", time.time()-t0, "4-cup:", len(results))
zero = [(s,pl) for s,pl in results if s[1]==0]
print("already zero-stray:", len(zero))
best_sols = []
if zero:
    for s,pl in sorted(zero, key=lambda t: cost(t[1]))[:5]:
        print("SOLUTION cost", cost(pl), pl)
        best_sols.append(pl)
else:
    # stage2: relocate one spare
    seen_sol = []
    results.sort(key=lambda t: (t[0][1], cost(t[1])))
    t1 = time.time()
    for s, base in results[:400]:
        moved = [n for n in W if base[n] != ENTRYPOS[n]]
        spares = [n for n in W if n not in moved]
        for nm in spares:
            pys, pxs = lattice(nm)
            for py in pys:
                for px in pxs:
                    pl = dict(base); pl[nm] = (py, px)
                    sc = score(pl)
                    if sc == (4, 0):
                        seen_sol.append((cost(pl), pl))
        if len(seen_sol) > 30 or time.time()-t1 > 150:
            break
    seen_sol.sort(key=lambda t: t[0])
    for c, pl in seen_sol[:6]:
        print("SOLUTION cost", c, pl)
        best_sols.append(pl)
print("done", time.time()-t0)
