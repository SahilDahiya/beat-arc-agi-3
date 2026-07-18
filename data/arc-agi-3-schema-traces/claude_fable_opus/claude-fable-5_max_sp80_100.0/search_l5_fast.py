import time, itertools, sys
# Block-level level-5 sim: board 20x19 blocks (x=2+3X, y=2+3Y), CELL=1 block.
# Statics (block coords): walls outside x0..18? playfield X:1..18, Y:0..18 (Y0=row2..)
# Real: x5..58 playfield => X = (x-2)//3: x5->1, x58->18. y2..58 => Y = (y-2)//3: y2->0, y58->18. Floor at Y19 (wall).
W = 20; H = 20
WALL, BGB, CUPB, TANK, SPOUT = 1, 0, 11, 4, 6
static = [[BGB]*W for _ in range(H)]
for Y in range(H):
    for X in range(W):
        if X == 0 or X >= 19 or Y >= 19:
            static[Y][X] = WALL
static[0][9] = TANK   # tank x29-31 rows2-4 -> X9,Y0
static[1][9] = SPOUT  # spout rows5-7 -> Y1
# cups: cupA rows20-28 x5-10 -> Y6-8, X1-2: ledge Y6 X1-2, back Y7 X1, ledge Y8 X1-2 (interior Y7 X2)
def addcup(cells):
    for (Y,X) in cells: static[Y][X] = CUPB
addcup([(6,1),(6,2),(7,1),(8,1),(8,2)])       # cupA (interior (7,2)) opens right
addcup([(11,1),(11,2),(12,1),(13,1),(13,2)])  # cupB (interior (12,2)) rows35-43 -> Y11-13
addcup([(9,17),(9,18),(10,18),(11,17),(11,18)])# cupC rows29-37 x53-58 -> Y9-11 X17-18; back X18, interior (10,17) opens left
addcup([(17,8),(17,10),(18,8),(18,9),(18,10)]) # cupD rows53-58 x26-34 -> Y17: legs X8,X10; Y18 base X8-10; interior (17,9)
CUPS = [
    {"cells": {(6,1),(6,2),(7,1),(8,1),(8,2)}, "interior": {(7,2)}},
    {"cells": {(11,1),(11,2),(12,1),(13,1),(13,2)}, "interior": {(12,2)}},
    {"cells": {(9,17),(9,18),(10,18),(11,17),(11,18)}, "interior": {(10,17)}},
    {"cells": {(17,8),(17,10),(18,8),(18,9),(18,10)}, "interior": {(17,9)}},
]
CUPCELLS = set().union(*[c["cells"] for c in CUPS])
FORBID = set()
for (Y,X) in CUPCELLS:
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            FORBID.add((Y+dy,X+dx))
STREAM_X, STREAM_Y = 9, 2   # starts just below spout (block Y2 = rows8-10)

# piece shapes (block offsets): S: stem (0,0), bar (1,0),(1,1); F: stem (0,1), bar (1,0),(1,1); T: (0,0),(1,0),(2,0),(3,0); U: (0,0..4) emitter at (0,2)
S_cells = [(0,0),(1,0),(1,1)]
F_cells = [(0,1),(1,0),(1,1)]
T_cells = [(0,0),(1,0),(2,0),(3,0)]
U_cells = [(0,0),(0,1),(0,2),(0,3),(0,4)]
U_em = (0,2)

def simulate(pos, cupfill_mode):
    # pos: dict name -> (Y,X). build occupancy
    occ = {}   # (Y,X) -> name
    for name, (py,px) in pos.items():
        cells = {"S": S_cells, "F": F_cells, "T": T_cells, "U": U_cells}[name]
        for (dy,dx) in cells:
            c = (py+dy, px+dx)
            if c in occ: return None
            if static[c[0]][c[1]] != BGB: return None
            if c in FORBID: return None
            occ[c] = name
    def cellv(Y,X):
        if not (0<=Y<H and 0<=X<W): return WALL
        if (Y,X) in occ: return occ[(Y,X)]
        return static[Y][X]
    fills = set(); strays = [0]
    seen = set()
    queue = [("col", STREAM_X, STREAM_Y)]
    # U emitter
    if "U" in pos:
        uy, ux = pos["U"]
        queue.append(("col", ux+2, uy+1))
    def cup_at(Y,X):
        for i,c in enumerate(CUPS):
            if (Y,X) in c["cells"] or (Y,X) in c["interior"]: return i
        return None
    def flow(Y, X, step):
        # horizontal 1-block flow at row Y moving step; on vertical face: spread along the
        # face (unbounded), overflow past both ends (end +/-1 block), each continuing in dir.
        stack = [(Y, X)]
        g = 0
        while stack and g < 120:
            g += 1
            Y, X = stack.pop()
            steps2 = 0
            while steps2 < 40:
                steps2 += 1
                if not (0 <= X < W):
                    strays[0] += 1; break
                v = cellv(Y, X)
                if v == BGB:
                    ci = cup_at(Y, X)
                    if ci is not None and (Y, X) in CUPS[ci]["interior"]:
                        fills.add(ci); break
                    X += step; continue
                if v == WALL:
                    strays[0] += 1; break
                if v == CUPB and (Y, X) in CUPS[cup_at(Y, X)]["interior"]:
                    fills.add(cup_at(Y, X)); break
                # vertical face (cup ledge/back or piece): find face extent in column X
                top = Y
                while cellv(top - 1, X) not in (BGB,) and cellv(top - 1, X) != WALL:
                    top -= 1
                bot = Y
                while cellv(bot + 1, X) not in (BGB,) and cellv(bot + 1, X) != WALL:
                    bot += 1
                # if face is CUP cells and contact mode fills:
                if v == CUPB and cupfill_mode == "contact":
                    fills.add(cup_at(Y, X)); break
                # up overflow
                if cellv(top - 1, X) == BGB and cellv(top - 1, X - step) == BGB:
                    stack.append((top - 1, X))
                elif cellv(top - 1, X) == WALL:
                    pass
                # down overflow
                if cellv(bot + 1, X) == BGB and cellv(bot + 1, X - step) == BGB:
                    stack.append((bot + 1, X))
                elif cellv(bot + 1, X) == WALL:
                    strays[0] += 1
                break
    it = 0
    while queue and it < 80:
        it += 1
        kind, X, Y = queue.pop(0)
        if (X,Y) in seen: continue
        seen.add((X,Y))
        # column falls from (Y) down
        while True:
            v = cellv(Y,X)
            if v == BGB:
                ci = cup_at(Y,X)
                if ci is not None and (Y,X) in CUPS[ci]["interior"]:
                    fills.add(ci); break
                Y += 1; continue
            if v == WALL:
                strays[0]+=1; break
            if v == CUPB:
                # generic obstacle run on cup cells (ledge tops etc)
                run0 = X
                while cellv(Y,run0-1) not in (BGB,): run0 -= 1
                run1 = X
                while cellv(Y,run1+1) not in (BGB,): run1 += 1
                bandY = Y-1
                lok = cellv(bandY, run0-1) == BGB and all(cellv(bandY,xx)==BGB for xx in range(run0-1, X)) and cellv(Y, run0-1) == BGB
                rok = cellv(bandY, run1+1) == BGB and all(cellv(bandY,xx)==BGB for xx in range(X+1, run1+2)) and cellv(Y, run1+1) == BGB
                if lok: queue.append(("col", run0-1, Y))
                if rok: queue.append(("col", run1+1, Y))
                break
            # piece
            name = v
            py,px = pos[name]
            if name in ("S","F"):
                stem = (py, px) if name=="S" else (py, px+1)
                barxs = {px, px+1}
                stemX = stem[1]
                step = 1 if name=="S" else -1
                if (Y,X) == stem:
                    # stem-hit: stem-split: opposite-side fall + flow
                    bandY = Y-1
                    opp = stemX - step
                    if cellv(bandY, opp) == BGB and cellv(Y, opp) == BGB:
                        queue.append(("col", opp, Y))
                    flow(Y, stemX+step, step)
                else:
                    flow(stem[0], stemX+step, step)
                break
            # T or U: generic run split
            run0 = X
            while cellv(Y,run0-1) not in (BGB, WALL) and isinstance(cellv(Y,run0-1), str): run0 -= 1
            run1 = X
            while cellv(Y,run1+1) not in (BGB, WALL) and isinstance(cellv(Y,run1+1), str): run1 += 1
            bandY = Y-1
            lok = cellv(bandY, run0-1) == BGB and all(cellv(bandY,xx)==BGB for xx in range(run0-1, X)) and cellv(Y, run0-1) == BGB
            rok = cellv(bandY, run1+1) == BGB and all(cellv(bandY,xx)==BGB for xx in range(X+1, run1+2)) and cellv(Y, run1+1) == BGB
            if lok: queue.append(("col", run0-1, Y))
            if rok: queue.append(("col", run1+1, Y))
            break
    return (len(fills), strays[0], tuple(sorted(fills)))

def main():
    t0=time.time()
    mode = sys.argv[1] if len(sys.argv)>1 else "contact"
    def valid(name, py, px):
        cells = {"S": S_cells, "F": F_cells, "T": T_cells, "U": U_cells}[name]
        for (dy,dx) in cells:
            Y,X = py+dy, px+dx
            if not (0<=Y<19 and 1<=X<=18): return False
            if static[Y][X] != BGB: return False
            if (Y,X) in FORBID: return False
        return True
    U_opts=[(y,x) for y in range(0,17) for x in range(5,10) if valid("U",y,x)]
    S_opts=[(y,x) for y in range(0,18) for x in range(3,13) if valid("S",y,x)]
    F_opts=[(y,x) for y in range(0,18) for x in range(3,13) if valid("F",y,x)]
    T_parks=[(t,4) for t in (14,) if valid("T",14,4)] + [(2,16)] * (1 if valid("T",2,16) else 0) + [(0,6)] * (1 if valid("T",0,6) else 0)
    if not T_parks: T_parks=[(3,16)]
    print("opts:", len(U_opts), len(S_opts), len(F_opts), "parks:", T_parks, flush=True)
    sols=[]; near=[]
    cnt=0
    for U_p in U_opts:
        for S_p in S_opts:
            for F_p in F_opts:
                for T_p in T_parks:
                    cnt+=1
                    r = simulate({"S":S_p,"F":F_p,"T":T_p,"U":U_p}, mode)
                    if r is None: continue
                    if r[0]==4 and r[1]==0:
                        sols.append((U_p,S_p,F_p,T_p,r))
                        print("WIN", U_p,S_p,F_p,T_p, flush=True)
                    elif r[0]>=3 and r[1]<=1:
                        near.append((r,(U_p,S_p,F_p,T_p)))
        if sols or time.time()-t0 > 200: break
    print("stage1 done", cnt, round(time.time()-t0,1), "sols", len(sols), "near", len(near), flush=True)
    if not sols and near:
        T_all=[(y,x) for y in range(0,16) for x in range(1,19) if valid("T",y,x)]
        near.sort(key=lambda t:(-(t[0][0]), t[0][1]))
        t1=time.time()
        for r0,(U_p,S_p,F_p,_) in near[:400]:
            for T_p in T_all:
                r = simulate({"S":S_p,"F":F_p,"T":T_p,"U":U_p}, mode)
                if r and r[0]==4 and r[1]==0:
                    sols.append((U_p,S_p,F_p,T_p,r))
                    print("WIN2", U_p,S_p,F_p,T_p, flush=True)
                    break
            if sols or time.time()-t1>60: break
    print("done sols", len(sols), sols[:3])
main()
