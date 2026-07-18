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
def sidecup_right(y0, x0=5):   # opens right (back at left)
    for y in range(y0, y0+3):
        for x in range(x0, x0+6): entry[y][x] = 11
    for y in range(y0+3, y0+6):
        for x in range(x0, x0+3): entry[y][x] = 11
    for y in range(y0+6, y0+9):
        for x in range(x0, x0+6): entry[y][x] = 11
def sidecup_left(y0, x0=53):   # opens left (back at right x56-58)
    for y in range(y0, y0+3):
        for x in range(x0, x0+6): entry[y][x] = 11
    for y in range(y0+3, y0+6):
        for x in range(x0+3, x0+6): entry[y][x] = 11
    for y in range(y0+6, y0+9):
        for x in range(x0, x0+6): entry[y][x] = 11
sidecup_right(20); sidecup_right(35); sidecup_left(29)
# bottom cup x26-34: legs x26-28,x32-34 rows53-55; base rows56-58
for y in range(53, 56):
    for x in range(26, 29): entry[y][x] = 11
    for x in range(32, 35): entry[y][x] = 11
for y in range(56, 59):
    for x in range(26, 35): entry[y][x] = 11
static = [row[:] for row in entry]
ns['ENTRY_GRID'] = entry
ns['CURRENT_LEVEL'] = 5
CUP = {(y,x) for y in range(64) for x in range(64) if entry[y][x] == 11}

# piece shapes as cell-offset sets (dy,dx) + kind
S_shape = [(dy,dx) for dy in range(3) for dx in range(3)] + [(dy+3,dx) for dy in range(3) for dx in range(6)]
# S: stem 3x3 at top-left? stem x29-31 = px+0..+2, bar px+0..+5 rows +3..+5
F_shape = [(dy,dx+3) for dy in range(3) for dx in range(3)] + [(dy+3,dx) for dy in range(3) for dx in range(6)]
# F: stem x32-34 = px+3..+5 top, bar px+0..+5 below
T_shape = [(dy,dx) for dy in range(12) for dx in range(3)]
U_shape = [(dy,dx) for dy in range(3) for dx in range(15)]
U_spec  = [(dy,dx) for dy in range(3) for dx in range(6,9)]   # emitter cells
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
        for (yy,xx) in cells: g[yy][xx] = kind if kind != 15 else 15
        for (yy,xx) in scells: g[yy][xx] = 4
        if kind == 15: fp.append(set(allc))
    r, strays, cups, fh = sim(g, entry, fp)
    return (len(r), strays)

t0 = time.time()
S_pos = (32, 29)
results = []
lat = lambda lo, hi: [v for v in range(lo, hi+1) if v % 3 == 2]
F_opts = [(py, px) for py in (23, 38) for px in lat(5, 53)]
U_opts = [(py, px) for py in lat(2, 56) for px in (17, 20, 23, 26, 29, 32, 35)]
T_parks = [(2, 53), (2, 5), (11, 53), (2, 44)]
best = {}
for F_p in F_opts:
    for U_p in U_opts:
        for T_p in T_parks:
            pos = {"S": S_pos, "F": F_p, "U": U_p, "T": T_p}
            s = build_and_score(pos)
            if s is None: continue
            key = s
            if s[0] >= 3:
                results.append((s, dict(pos)))
            best[key] = best.get(key, 0) + 1
print("pass1", round(time.time()-t0,1), "s; dist:", sorted(best.items(), key=lambda kv:(-kv[0][0], kv[0][1]))[:8])
sols = [(s,p) for s,p in results if s == (4,0)]
print("solutions:", len(sols))
for s,p in sols[:5]: print(s,p)
if not sols:
    # pass 2: near misses + T everywhere
    T_opts = [(py, px) for py in lat(2, 47) for px in lat(5, 56)]
    seen = set()
    t1 = time.time()
    cand = sorted(results, key=lambda t: (-(t[0][0]), t[0][1]))[:250]
    for s0, p0 in cand:
        for T_p in T_opts:
            pos = dict(p0); pos["T"] = T_p
            s = build_and_score(pos)
            if s == (4, 0):
                sols.append((s, pos))
        if sols or time.time()-t1 > 150: break
    print("pass2 sols:", len(sols))
    for s,p in sols[:5]: print(s,p)
