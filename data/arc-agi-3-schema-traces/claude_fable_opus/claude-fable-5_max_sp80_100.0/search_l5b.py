import time, itertools
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
def sidecup_right(y0, x0=5):
    for y in range(y0, y0+3):
        for x in range(x0, x0+6): entry[y][x] = 11
    for y in range(y0+3, y0+6):
        for x in range(x0, x0+3): entry[y][x] = 11
    for y in range(y0+6, y0+9):
        for x in range(x0, x0+6): entry[y][x] = 11
def sidecup_left(y0, x0=53):
    for y in range(y0, y0+3):
        for x in range(x0, x0+6): entry[y][x] = 11
    for y in range(y0+3, y0+6):
        for x in range(x0+3, x0+6): entry[y][x] = 11
    for y in range(y0+6, y0+9):
        for x in range(x0, x0+6): entry[y][x] = 11
sidecup_right(20); sidecup_right(35); sidecup_left(29)
for y in range(53, 56):
    for x in range(26, 29): entry[y][x] = 11
    for x in range(32, 35): entry[y][x] = 11
for y in range(56, 59):
    for x in range(26, 35): entry[y][x] = 11
static = [row[:] for row in entry]
ns['ENTRY_GRID'] = entry
ns['CURRENT_LEVEL'] = 5
CUP = {(y,x) for y in range(64) for x in range(64) if entry[y][x] == 11}

S_shape = [(dy,dx) for dy in range(3) for dx in range(3)] + [(dy+3,dx) for dy in range(3) for dx in range(6)]
F_shape = [(dy,dx+3) for dy in range(3) for dx in range(3)] + [(dy+3,dx) for dy in range(3) for dx in range(6)]
T_shape = [(dy,dx) for dy in range(12) for dx in range(3)]
U_shape = [(dy,dx) for dy in range(3) for dx in range(15)]
U_spec  = [(dy,dx) for dy in range(3) for dx in range(6,9)]
PIECES = {
  "S": (S_shape, [], 15),
  "F": (F_shape, [], 15),
  "T": (T_shape, [], 8),
  "U": ([c for c in U_shape if c not in U_spec], U_spec, 8),
}
def place_ok(cells_all, occupied):
    for (yy,xx) in cells_all:
        if not (0<=yy<=63 and 0<=xx<=63): return False
        if static[yy][xx] != BG: return False
        if (yy,xx) in occupied: return False
        for ay in (yy-1,yy,yy+1):
            for ax in (xx-1,xx,xx+1):
                if (ay,ax) in CUP: return False
    return True
sim = ns['_simulate_pour']
def build_and_score(pos):
    g = [row[:] for row in static]
    occupied = set()
    fp = []
    for name,(py,px) in pos.items():
        body, spec, kind = PIECES[name]
        cells = [(py+dy, px+dx) for (dy,dx) in body]
        scells = [(py+dy, px+dx) for (dy,dx) in spec]
        allc = cells + scells
        if not place_ok(allc, occupied): return None
        occupied |= set(allc)
        for (yy,xx) in cells: g[yy][xx] = kind
        for (yy,xx) in scells: g[yy][xx] = 4
        if kind == 15: fp.append(set(allc))
    r, strays, cups, fh = sim(g, entry, fp)
    return (len(r), strays)

lat = lambda lo,hi: [v for v in range(lo,hi+1) if v%3==2]
t0=time.time()
U_opts = [(uy,ux) for uy in (8,11,14,17,20) for ux in (17,20,23,26,29)]
F_opts = [(fy,fx) for fy in (17,20,23,26,29,32,35,38,41) for fx in lat(5,50)]
S_opts = [(sy,sx) for sy in (17,20,23,26,29,32,35,38) for sx in lat(5,53)]
T_park = [(2,50),(2,5)]
res=[]
cnt=0
for U_p in U_opts:
    for F_p in F_opts:
        for S_p in S_opts:
            for T_p in T_park:
                pos={"U":U_p,"F":F_p,"S":S_p,"T":T_p}
                s=build_and_score(pos)
                cnt+=1
                if s and s[0]>=3:
                    res.append((s,dict(pos)))
                if s==(4,0):
                    print("FOUND", pos)
print("stage1", round(time.time()-t0,1), "tried", cnt, "≥3cups:", len(res))
import collections
print(collections.Counter(s for s,_ in res))
sols=[(s,p) for s,p in res if s==(4,0)]
if not sols:
    T_opts=[(ty,tx) for ty in lat(2,47) for tx in lat(5,56)]
    best=sorted(res,key=lambda t:(-(t[0][0]),t[0][1]))[:300]
    t1=time.time()
    for s0,p0 in best:
        for T_p in T_opts:
            pos=dict(p0); pos["T"]=T_p
            s=build_and_score(pos)
            if s==(4,0):
                sols.append((s,dict(pos)))
        if sols or time.time()-t1>120: break
    print("stage2 sols:", len(sols))
for s,p in sols[:6]: print(s,p)
