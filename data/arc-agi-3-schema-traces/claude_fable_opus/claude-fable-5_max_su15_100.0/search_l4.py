"""L4 search: two glyphs, disk at (32,15), goal b@(32,15).
Pieces: 4 sixes (the b materials) + 4 spare a-dots (bait).
Rules (validated to 71/71 on history via world_model_v5.py):
- pull: min CELL d^2 <= 64; bystander margin: reject clicks with any piece cell-d^2 in (64,100)
- glyphs step per paid click (top-left order): target = nearest piece (anchor euclid from int center);
  pre cellΔ<=(4,4) -> half-step floor(Δcellcentroid/2+.5) + EAT;
  else clamp4 step toward anchor; post cellΔ<=(2,2) -> EAT;
  consumed/moved target: successor within (3,3) of old spot -> mirror dash 2T-C;
  successor >=6 away on an axis -> normal; 4-5 zone -> reject (unknown).
- EAT of tier1 spare: allowed (piece destroyed). EAT of tier>=2: prune (dead).
"""
import json, heapq, itertools, sys, math

def span(t): lo = -(t//2); return lo, lo+t-1
def cells_of(t, ax, ay):
    lo, hi = span(t)
    return [(ax+dx, ay+dy) for dy in range(lo,hi+1) for dx in range(lo,hi+1)]
def in_bounds_piece(t, ax, ay):
    return all(0 <= x <= 63 and 10 <= y <= 62 for (x,y) in cells_of(t,ax,ay))
def cell_delta(p, gx, gy):
    cs = cells_of(*p)
    bx, by = min(cs, key=lambda c: (c[0]-gx)**2 + (c[1]-gy)**2)
    return bx-gx, by-gy
def centroid_int(cells):
    n = len(cells)
    return (int(sum(c[0] for c in cells)/n + 0.5), int(sum(c[1] for c in cells)/n + 0.5))

DEST = (32, 15)
ENTRY_PIECES = [(3,15,25),(3,38,20),(1,3,60),(1,14,54),(1,44,53),(1,58,59)]
G1 = ((19,21),(18,22),(20,22),(17,23),(21,23),(18,24),(19,24),(20,24))
G2 = ((44,49),(43,50),(45,50),(42,51),(46,51),(43,52),(44,52),(45,52))

class State:
    __slots__ = ('pieces','glyphs','dead','won')
    def __init__(self, pieces, glyphs):
        self.pieces = frozenset(pieces)
        self.glyphs = tuple(sorted(tuple(sorted(gc)) for gc in glyphs))
        self.dead = False; self.won = False
    def key(self): return (self.pieces, self.glyphs)

def move_one_glyph(gcells, pre_target, pieces):
    """Returns (new_gcells, eaten_piece_or_None, invalid_bool). pieces=list post-click.
    FINAL RULES: half-step when pre cellD<=(4,4) else clamp4 toward anchor;
    EAT iff glyph body overlaps a piece cell after moving.
    Consumed/moved target: new nearest >=12 away -> normal (5 obs);
    closer -> UNPREDICTABLE -> invalid (reject candidate)."""
    gx, gy = centroid_int(gcells)
    if pre_target is not None and pre_target not in pieces:
        if not pieces:
            return gcells, None, False
        t2 = min(pieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2)
        if (t2[1]-gx)**2 + (t2[2]-gy)**2 < 144:
            return gcells, None, True     # consumed-target with near successor: unpredictable
        # normal chase (confirmed regime)
    if not pieces:
        return gcells, None, False
    t2 = min(pieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2)
    d2s = sorted(((p[1]-gx)**2+(p[2]-gy)**2) for p in pieces)
    if len(d2s)>1 and d2s[0]==d2s[1]:
        return gcells, None, True         # target tie: ambiguous
    cdx, cdy = cell_delta(t2, gx, gy)
    if abs(cdx)<=4 and abs(cdy)<=4:
        pc = cells_of(*t2)
        pcx = sum(c[0] for c in pc)/len(pc); pcy = sum(c[1] for c in pc)/len(pc)
        n = len(gcells)
        cgx = sum(c[0] for c in gcells)/n; cgy = sum(c[1] for c in gcells)/n
        mvx = int(math.floor((pcx-cgx)/2.0 + 0.5)); mvy = int(math.floor((pcy-cgy)/2.0 + 0.5))
    else:
        dx, dy = t2[1]-gx, t2[2]-gy
        mvx = max(-4,min(4,dx)); mvy = max(-4,min(4,dy))
    moved = tuple((cx+mvx, cy+mvy) for (cx,cy) in gcells)
    if (mvx,mvy) != (0,0) and all(0<=cx<=63 and 10<=cy<=62 for (cx,cy) in moved):
        gcells = moved
    body = set(gcells)
    for p in pieces:
        if body & set(cells_of(*p)):
            return gcells, p, False
    return gcells, None, False

def click(state, x, y):
    pieces = list(state.pieces)
    def celld2(p):
        return min((cx-x)**2 + (cy-y)**2 for (cx,cy) in cells_of(*p))
    pulled = [p for p in pieces if celld2(p) <= 64]
    gray   = [p for p in pieces if 64 < celld2(p) < 100]
    if gray: return None
    by_tier = {}
    for p in pulled: by_tier.setdefault(p[0], []).append(p)
    newpieces = [p for p in pieces if p not in pulled]
    made = []
    for t, lst in by_tier.items():
        if len(lst) > 2: return None
        nt = t if len(lst)==1 else t+1
        if nt > 4: return None
        if not in_bounds_piece(nt, x, y): return None
        made.append((nt, x, y))
    if len(made) > 1: return None
    for (nt,ax,ay) in made:
        nc = set(cells_of(nt,ax,ay))
        for q in newpieces:
            if nc & set(cells_of(*q)): return None
        for gc in state.glyphs:
            if nc & set(gc): return None
    newpieces += made
    # glyph pre-targets (from pre-click pieces)
    pre = []
    for gc in state.glyphs:
        gx, gy = centroid_int(gc)
        t = min(pieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2) if pieces else None
        pre.append((gc, t))
    # process glyphs in top-left order
    pre.sort(key=lambda e: (min(c[1] for c in e[0]), min(c[0] for c in e[0])))
    cur_pieces = list(newpieces)
    new_glyphs = []
    for (gc, tgt) in pre:
        gc2, eaten, invalid = move_one_glyph(gc, tgt, cur_pieces)
        if invalid: return None
        if eaten is not None:
            if eaten[0] >= 2: 
                out = State(cur_pieces, [gc2]+new_glyphs)
                out.dead = True
                return out
            cur_pieces = [p for p in cur_pieces if p != eaten]
        new_glyphs.append(gc2)
    # glyph collision (unknown): reject overlaps
    allc = set()
    for gc in new_glyphs:
        s = set(gc)
        if allc & s: return None
        allc |= s
    out = State(cur_pieces, new_glyphs)
    if (4, DEST[0], DEST[1]) in out.pieces:
        out.won = True
    return out

HOP_DIRS2 = [(dx,dy) for dx in range(-10,11) for dy in range(-10,11) if 16 <= dx*dx+dy*dy <= 121]

def threatened(state):
    """Pieces in danger next click (cellΔ<=(6,6) from a glyph)."""
    thr = []
    for gc in state.glyphs:
        gx, gy = centroid_int(gc)
        if not state.pieces: continue
        t2 = min(state.pieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2)
        cdx, cdy = cell_delta(t2, gx, gy)
        if abs(cdx) <= 6 and abs(cdy) <= 6:
            thr.append(t2)
    return thr

def candidates(state):
    ps = sorted(state.pieces)
    thr = [p for p in threatened(state) if p[0] >= 2]  # only protect tier>=2
    gxs = [centroid_int(gc) for gc in state.glyphs]
    cands = set()
    for i in range(len(ps)):
        for j in range(i+1,len(ps)):
            p,q = ps[i], ps[j]
            if p[0]!=q[0]: continue
            if thr and p not in thr and q not in thr: continue
            if (p[1]-q[1])**2+(p[2]-q[2])**2 > 500: continue
            x0=(p[1]+q[1])//2; y0=(p[2]+q[2])//2
            pcells=cells_of(*p); qcells=cells_of(*q)
            def cd2(cs,x,y): return min((cx-x)**2+(cy-y)**2 for (cx,cy) in cs)
            pts=[]
            for x in range(x0-7,x0+8):
                for y in range(y0-7,y0+8):
                    if cd2(pcells,x,y)<=64 and cd2(qcells,x,y)<=64:
                        pts.append((x,y))
            pts.sort(key=lambda c: (abs(c[0]-DEST[0])+abs(c[1]-DEST[1])) - 0.5*min(abs(c[0]-gx)+abs(c[1]-gy) for gx,gy in gxs))
            cands.update(pts[:10])
    for p in ps:
        if p[0] == 1: continue              # never move bait dots
        if thr and p not in thr: continue
        pcells=cells_of(*p)
        pts=[]
        for (dx,dy) in HOP_DIRS2:
            x,y = p[1]+dx, p[2]+dy
            if min((cx-x)**2+(cy-y)**2 for (cx,cy) in pcells)<=64:
                pts.append((x,y))
        pts.sort(key=lambda c: (abs(c[0]-DEST[0])+abs(c[1]-DEST[1])) - 0.7*min(abs(c[0]-gx)+abs(c[1]-gy) for gx,gy in gxs))
        cands.update(pts[:14])
        # also escape hops: maximize distance from nearest glyph
        pts.sort(key=lambda c: -min((c[0]-gx)**2+(c[1]-gy)**2 for gx,gy in gxs))
        cands.update(pts[:10])
    if not thr:
        for corner in ((62,12),(1,12),(32,61),(62,61)):
            ok=True
            for p in ps:
                if min((cx-corner[0])**2+(cy-corner[1])**2 for (cx,cy) in cells_of(*p)) < 100:
                    ok=False; break
            if ok:
                cands.add(corner); break
    return cands

def h(state):
    s = 0.0
    gxs = [centroid_int(gc) for gc in state.glyphs]
    for (t,ax,ay) in state.pieces:
        if t == 1: continue
        units = 2**(t-1)
        s += units * max(abs(ax-DEST[0]), abs(ay-DEST[1]))
    s += sum(1 for p in state.pieces if p[0]>=2)*30
    return s

def search(max_depth=20, beam=3000):
    st0 = State(ENTRY_PIECES, [G1, G2])
    layer = [(h(st0), st0, [])]
    seen = {st0.key()}
    nodes = 0
    for depth in range(max_depth):
        nxt = []
        for (_, st, path) in layer:
            for (x,y) in candidates(st):
                st2 = click(st, x, y)
                nodes += 1
                if st2 is None or st2.dead: continue
                if st2.won:
                    return path+[(x,y)], nodes
                k = st2.key()
                if k in seen: continue
                seen.add(k)
                nxt.append((h(st2), st2, path+[(x,y)]))
        nxt.sort(key=lambda e: e[0])
        layer = nxt[:beam]
        print(f"depth {depth+1}: layer={len(layer)} nodes={nodes}", flush=True)
        if not layer: break
    return None, nodes

if __name__ == '__main__':
    plan, nodes = search()
    print("nodes:", nodes, flush=True)
    if plan:
        print("PLAN:", json.dumps(plan))
    else:
        print("NO PLAN FOUND")
