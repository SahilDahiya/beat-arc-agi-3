import time
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
    for x in range(5): entry[y][x] = 1
    for x in range(59, 64): entry[y][x] = 1
for y in range(2, 5):
    for x in range(29, 32): entry[y][x] = 4
for y in range(5, 8):
    for x in range(29, 32): entry[y][x] = 6
def scr(y0, x0=5):
    for y in range(y0, y0+3):
        for x in range(x0, x0+6): entry[y][x] = 11
    for y in range(y0+3, y0+6):
        for x in range(x0, x0+3): entry[y][x] = 11
    for y in range(y0+6, y0+9):
        for x in range(x0, x0+6): entry[y][x] = 11
def scl(y0, x0=53):
    for y in range(y0, y0+3):
        for x in range(x0, x0+6): entry[y][x] = 11
    for y in range(y0+3, y0+6):
        for x in range(x0+3, x0+6): entry[y][x] = 11
    for y in range(y0+6, y0+9):
        for x in range(x0, x0+6): entry[y][x] = 11
scr(20); scr(35); scl(29)
for y in range(53, 56):
    for x in range(26, 29): entry[y][x] = 11
    for x in range(32, 35): entry[y][x] = 11
for y in range(56, 59):
    for x in range(26, 35): entry[y][x] = 11
static = [row[:] for row in entry]
ns['ENTRY_GRID'] = entry
ns['CURRENT_LEVEL'] = 5
CUP = {(y,x) for y in range(64) for x in range(64) if entry[y][x] == 11}
FORBID = set()
for (y,x) in CUP:
    for ay in (y-1,y,y+1):
        for ax in (x-1,x,x+1):
            FORBID.add((ay,ax))

S_shape = [(dy,dx) for dy in range(3) for dx in range(3)] + [(dy+3,dx) for dy in range(3) for dx in range(6)]
F_shape = [(dy,dx+3) for dy in range(3) for dx in range(3)] + [(dy+3,dx) for dy in range(3) for dx in range(6)]
T_shape = [(dy,dx) for dy in range(12) for dx in range(3)]
U_body  = [(dy,dx) for dy in range(3) for dx in range(15) if not (6 <= dx <= 8)]
U_spec  = [(dy,dx) for dy in range(3) for dx in range(6,9)]

def cellsafe(cells):
    for (yy,xx) in cells:
        if not (0<=yy<=63 and 0<=xx<=63): return False
        if static[yy][xx] != BG: return False
        if (yy,xx) in FORBID: return False
    return True

sim = ns['_simulate_pour']
def score(U_p, F_p, S_p, T_p):
    g = [row[:] for row in static]
    occ = set()
    fp = []
    for shape, spec, kind, (py,px) in (
        (U_body, U_spec, 8, U_p), (F_shape, [], 15, F_p),
        (S_shape, [], 15, S_p), (T_shape, [], 8, T_p)):
        cells = [(py+dy, px+dx) for (dy,dx) in shape]
        sc = [(py+dy, px+dx) for (dy,dx) in spec]
        allc = cells + sc
        if not cellsafe(allc): return None
        if occ & set(allc): return None
        occ |= set(allc)
        for (yy,xx) in cells: g[yy][xx] = kind
        for (yy,xx) in sc: g[yy][xx] = 4
        if kind == 15: fp.append(set(allc))
    r, strays, cups, fh = sim(g, entry, fp)
    return (len(r), strays)

lat = lambda lo,hi: [v for v in range(lo,hi+1) if v%3==2]
t0 = time.time()
U_opts = [(uy,ux) for uy in (8,11) for ux in (17,20,23,26,29)]
F_opts = [(fy,fx) for fy in (20,23,26,35,38,41) for fx in lat(5,47)]
S_opts = [(sy,sx) for sy in (17,20,26,29,32,35) for sx in lat(5,50)]
T_opts = [(2,50),(2,38),(2,35),(2,5),(14,44),(20,44),(23,44),(17,44),(23,11),(20,11),(26,11),(2,14),(11,23),(29,35)]
res = []
cnt = 0
sols = []
for U_p in U_opts:
    for F_p in F_opts:
        for S_p in S_opts:
            for T_p in T_opts:
                s = score(U_p, F_p, S_p, T_p)
                cnt += 1
                if s is None: continue
                if s[0] >= 4:
                    sols.append((s, U_p, F_p, S_p, T_p))
                    if s == (4,0):
                        print("WIN", U_p, F_p, S_p, T_p, flush=True)
                elif s[0] == 3 and s[1] == 0:
                    res.append((s, U_p, F_p, S_p, T_p))
    print("U", U_p, "done", cnt, round(time.time()-t0,1), "sols:", len(sols), flush=True)
print("total", cnt, "4cup:", len(sols), "3cup0stray:", len(res))
for s in sols[:10]: print(s)
