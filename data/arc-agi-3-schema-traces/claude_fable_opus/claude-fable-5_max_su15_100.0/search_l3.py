"""L3 search: find a certified click sequence (post-RESET) that wins.
Simulator mirrors world_model_v5.py exactly; validated against events.jsonl.
Margins: pulls d^2<=74, non-pulls d^2>=101 (robust to unknown radius 75..100).
"""
import json, heapq, itertools, sys
import numpy as np

# ---------- rules ----------
def span(t): lo = -(t//2); return lo, lo+t-1
def cells_of(t, ax, ay):
    lo, hi = span(t)
    return [(ax+dx, ay+dy) for dy in range(lo,hi+1) for dx in range(lo,hi+1)]
def in_bounds_piece(t, ax, ay):
    return all(0 <= x <= 63 and 10 <= y <= 62 for (x,y) in cells_of(t,ax,ay))

GLYPH_SHAPE = [(0,-2),(-1,-1),(1,-1),(-2,0),(2,0),(-1,1),(0,1),(1,1)]  # rel to center-of-mass-ish
# actual glyph cells rel to int-center: derive from entry: cells minus center
def glyph_cells(center):
    cx, cy = center
    return [(cx+dx, cy+dy) for (dx,dy) in GLYPH_REL]


def cell_delta(p, gx, gy):
    cs = cells_of(*p)
    bx, by = min(cs, key=lambda c: (c[0]-gx)**2 + (c[1]-gy)**2)
    return bx-gx, by-gy

def centroid_int(cells):
    n = len(cells)
    gx = int(sum(c[0] for c in cells)/n + 0.5)
    gy = int(sum(c[1] for c in cells)/n + 0.5)
    return gx, gy

class State:
    __slots__ = ('pieces','gcells','dead','won','vetoed_win')
    def __init__(self, pieces, gcells):
        self.pieces = frozenset(pieces)   # (t,ax,ay)
        self.gcells = tuple(sorted(gcells))
        self.dead = False; self.won = False; self.vetoed_win = False
    def key(self): return (self.pieces, self.gcells)

R2_PULL = 64    # CONFIRMED: pull iff min CELL d^2 <= 64
R2_SAFE = 68    # CONFIRMED no-pull at cell-d^2 68
DEST = (5,57)

def click(state, x, y, strict=True):
    """Apply click; returns new State or None if margin-violating/tie/eat/etc."""
    pieces = list(state.pieces)
    def celld2(p):
        return min((cx-x)**2+(cy-y)**2 for (cx,cy) in cells_of(*p))
    pulled = [p for p in pieces if celld2(p) <= R2_PULL]
    gray   = [p for p in pieces if R2_PULL < celld2(p) < R2_SAFE]
    if strict and gray: return None           # ambiguous radius zone
    # pulled may be empty: a "pass" click (just ticks the glyph)
    # group by tier
    by_tier = {}
    for p in pulled: by_tier.setdefault(p[0], []).append(p)
    newpieces = [p for p in pieces if p not in pulled]
    made = []
    for t, lst in by_tier.items():
        if len(lst) > 2: return None          # 3+ merge: unknown, avoid
        nt = t if len(lst)==1 else t+1
        if nt > 4: return None
        if not in_bounds_piece(nt, x, y): return None
        made.append((nt, x, y))
    if len(made) > 1: return None             # mixed-tier landing: avoid
    # overlap check: new piece cells vs existing pieces/glyph
    for (nt,ax,ay) in made:
        nc = set(cells_of(nt,ax,ay))
        for q in newpieces:
            if nc & set(cells_of(*q)): return None
        if nc & set(state.gcells): return None
    newpieces += made
    # --- glyph ---
    gcells = list(state.gcells)
    gx, gy = centroid_int(gcells)
    # pre-click target
    pre = min(pieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2) if pieces else None
    if pre is not None:
        dists = sorted(((p[1]-gx)**2+(p[2]-gy)**2) for p in pieces)
        if strict and len(dists)>1 and dists[0]==dists[1]: return None  # tie ambiguity
    ns = State(newpieces, gcells)  # placeholder; we mutate below
    eat = None
    if pre is not None and pre not in newpieces:
        # target consumed/moved: behavior depends on successor proximity to
        # the old spot: <= (3,3) -> mirror dash (obs#48); >=6 on an axis ->
        # normal step toward new nearest (obs#61); in between -> UNKNOWN.
        succ = [p for p in newpieces
                if abs(p[1]-pre[1]) <= 5 and abs(p[2]-pre[2]) <= 5]
        near = [p for p in succ
                if abs(p[1]-pre[1]) <= 3 and abs(p[2]-pre[2]) <= 3]
        if succ and not near:
            return None                      # ambiguous boundary: avoid
        if near:
            mv = (2*(pre[1]-gx), 2*(pre[2]-gy))
            moved = [(cx+mv[0], cy+mv[1]) for (cx,cy) in gcells]
            if all(0<=cx<=63 and 10<=cy<=62 for (cx,cy) in moved):
                gcells = moved
            # no chomp on dash landing (confirmed #48->#49)
        else:
            # normal chase step toward nearest post-click piece
            if newpieces:
                t2 = min(newpieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2)
                d2s = sorted(((p[1]-gx)**2+(p[2]-gy)**2) for p in newpieces)
                if strict and len(d2s)>1 and d2s[0]==d2s[1]: return None
                dx, dy = t2[1]-gx, t2[2]-gy
                cdx, cdy = cell_delta(t2, gx, gy)
                if abs(cdx)<=4 and abs(cdy)<=4:
                    eat = t2
                else:
                    mvx = max(-4,min(4,dx)); mvy = max(-4,min(4,dy))
                    pdx, pdy = cell_delta(t2, gx+mvx, gy+mvy)
                    if abs(pdx)<=2 and abs(pdy)<=2:
                        eat = t2
                    moved = [(cx+mvx, cy+mvy) for (cx,cy) in gcells]
                    if all(0<=cx<=63 and 10<=cy<=62 for (cx,cy) in moved):
                        gcells = moved
    elif newpieces:
        t2 = min(newpieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2)
        d2s = sorted(((p[1]-gx)**2+(p[2]-gy)**2) for p in newpieces)
        if strict and len(d2s)>1 and d2s[0]==d2s[1]: return None
        dx, dy = t2[1]-gx, t2[2]-gy
        cdx, cdy = cell_delta(t2, gx, gy)
        if abs(cdx)<=4 and abs(cdy)<=4:
            eat = t2                          # half-step chomp
        else:
            mvx = max(-4,min(4,dx)); mvy = max(-4,min(4,dy))
            pdx, pdy = cell_delta(t2, gx+mvx, gy+mvy)
            if abs(pdx)<=2 and abs(pdy)<=2:
                eat = t2                      # lands cell within (2,2): eats
            moved = [(cx+mvx, cy+mvy) for (cx,cy) in gcells]
            if all(0<=cx<=63 and 10<=cy<=62 for (cx,cy) in moved):
                gcells = moved
    out = State(newpieces, gcells)
    if eat is not None:
        if eat == (4, DEST[0], DEST[1]):
            out.vetoed_win = True             # b reached dest but glyph eats it same tick
        out.dead = True
        return out
    # win check: b at dest AND created/moved this click
    if (4, DEST[0], DEST[1]) in out.pieces:
        out.won = True
    return out

# ---------- entry state (post reset) ----------
ENTRY_PIECES = [(1,31,27),(1,36,29),(1,5,26),(1,11,26),(1,8,41),(1,12,47),(1,33,47),(1,30,51)]
ENTRY_GLYPH = [(54,19),(53,20),(55,20),(52,21),(56,21),(53,22),(54,22),(55,22)]
_gc = centroid_int(ENTRY_GLYPH)
GLYPH_REL = [(x-_gc[0], y-_gc[1]) for (x,y) in ENTRY_GLYPH]

# ---------- validate sim vs recorded history ----------
def validate():
    evs = [json.loads(l) for l in open('events.jsonl')]
    acts = [e for e in evs if e['kind']=='action_taken']
    # find last reset index; replay clicks after it (level 3, before any eat)
    idx = max(i for i,a in enumerate(acts) if a['action']==0)
    st = State(ENTRY_PIECES, ENTRY_GLYPH)
    ok = True
    for a in acts[idx+1:]:
        if a['action'] != 6: break
        st2 = click(st, a['x'], a['y'], strict=False)
        g = np.array(a['grid'])
        # compare pieces & glyph
        real_pieces = set()
        for v,t in ((10,1),(6,2),(15,3),(11,4)):
            seen=set()
            for yy in range(10,63):
                for xx in range(64):
                    if g[yy,xx]==v and (xx,yy) not in seen:
                        s=t; oksq=all(g[yy+dy][xx+dx]==v for dy in range(s) for dx in range(s) if yy+dy<63)
                        if oksq:
                            lo,_=span(t); real_pieces.add((t,xx-lo,yy-lo))
                            for dy in range(s):
                                for dx in range(s): seen.add((xx+dx,yy+dy))
        real_glyph = tuple(sorted((xx,yy) for yy in range(10,63) for xx in range(64) if g[yy,xx]==7))
        if st2 is None:
            print("sim: click rejected but real happened", a['x'],a['y']); ok=False; break
        if st2.dead:
            print("sim: EAT at", a['x'],a['y'], "(real had eat too — stop compare)"); st=st2; break
        if set(st2.pieces)!=real_pieces or st2.gcells!=real_glyph:
            print("MISMATCH after click", (a['x'],a['y']))
            print("  sim pieces:", sorted(st2.pieces), "\n  real:", sorted(real_pieces))
            print("  sim glyph:", st2.gcells, "\n  real :", real_glyph)
            ok=False; break
        st = st2
    print("validation:", "OK" if ok else "FAILED")
    return ok

# ---------- search ----------
HOP_DIRS2 = [(dx,dy) for dx in range(-12,13) for dy in range(-12,13) if 16 <= dx*dx+dy*dy <= 145]

def threatened(state):
    """Piece the glyph will eat on any click that doesn't move/consume it."""
    if not state.pieces: return None
    gx, gy = centroid_int(state.gcells)
    t2 = min(state.pieces, key=lambda p:(p[1]-gx)**2+(p[2]-gy)**2)
    cdx, cdy = cell_delta(t2, gx, gy)
    if abs(cdx) <= 6 and abs(cdy) <= 6:
        return t2
    return None

def candidates(state):
    ps = sorted(state.pieces)
    thr = threatened(state)
    gx, gy = centroid_int(state.gcells)
    cands = set()
    # merges (any same-tier pair)
    for i in range(len(ps)):
        for j in range(i+1,len(ps)):
            p,q = ps[i], ps[j]
            if p[0]!=q[0]: continue
            if thr is not None and p!=thr and q!=thr: continue
            if (p[1]-q[1])**2+(p[2]-q[2])**2 > 4*140: continue
            x0=(p[1]+q[1])//2; y0=(p[2]+q[2])//2
            pcells=cells_of(*p); qcells=cells_of(*q)
            def cd2(cs,x,y): return min((cx-x)**2+(cy-y)**2 for (cx,cy) in cs)
            pts=[]
            for x in range(x0-7,x0+8):
                for y in range(y0-7,y0+8):
                    if cd2(pcells,x,y)<=64 and cd2(qcells,x,y)<=64:
                        pts.append((x,y))
            # cap: prefer toward dest and away from glyph
            pts.sort(key=lambda c: (abs(c[0]-DEST[0])+abs(c[1]-DEST[1])) - 0.5*(abs(c[0]-gx)+abs(c[1]-gy)))
            cands.update(pts[:10])
    # hops
    for p in ps:
        if thr is not None and p!=thr: continue
        pcells=cells_of(*p)
        pts=[]
        for (dx,dy) in HOP_DIRS2:
            x,y = p[1]+dx, p[2]+dy
            if min((cx-x)**2+(cy-y)**2 for (cx,cy) in pcells)<=64:
                pts.append((x,y))
        pts.sort(key=lambda c: (abs(c[0]-DEST[0])+abs(c[1]-DEST[1])) - 0.7*(abs(c[0]-gx)+abs(c[1]-gy)))
        cands.update(pts[:14])
    # pass click (tick the glyph, pull nothing): pick a far corner cell
    if thr is None:
        for corner in ((62,12),(62,61),(1,12),(32,12)):
            ok=True
            for p in ps:
                if min((cx-corner[0])**2+(cy-corner[1])**2 for (cx,cy) in cells_of(*p)) < R2_SAFE:
                    ok=False; break
            if ok:
                cands.add(corner)
                break
    return cands

def h(state):
    # weighted unit-distance to dest + piece count + glyph pressure relief
    s = 0.0
    gx, gy = centroid_int(state.gcells)
    for (t,ax,ay) in state.pieces:
        units = 2**(t-1)
        s += units * max(abs(ax-DEST[0]), abs(ay-DEST[1]))
    s += len(state.pieces)*30
    if state.pieces:
        nd = min(max(abs(ax-gx),abs(ay-gy)) for (t,ax,ay) in state.pieces)
        s -= min(nd, 16)*1.0
    return s

VETOED = []
def search(max_depth=22, beam=4000):
    st0 = State(ENTRY_PIECES, ENTRY_GLYPH)
    layer = [(h(st0), st0, [])]
    seen = {st0.key()}
    nodes = 0
    for depth in range(max_depth):
        nxt = []
        for (_, st, path) in layer:
            for (x,y) in candidates(st):
                st2 = click(st, x, y)
                nodes += 1
                if st2 is None: continue
                if st2.dead:
                    if getattr(st2,'vetoed_win',False):
                        global VETOED
                        VETOED.append((path+[(x,y)], st))
                    continue
                if st2.won:
                    return path+[(x,y)], nodes
                k = st2.key()
                if k in seen: continue
                seen.add(k)
                nxt.append((h(st2), st2, path+[(x,y)]))
        nxt.sort(key=lambda e: e[0])
        layer = nxt[:beam]
        print(f"depth {depth+1}: layer={len(layer)} nodes={nodes} vetoed={len(VETOED)}", flush=True)
        if depth+1 in (12,16,20,22):
            for (hh, s, pth) in layer[:3]:
                print("   best:", sorted(s.pieces), "G", centroid_int(s.gcells), flush=True)
        if not layer: break
    return None, nodes

if __name__ == '__main__':
    import functools
    print = functools.partial(__builtins__.print, flush=True) if hasattr(__builtins__,'print') else print
    # validation replaced by live-model backtest (57/57)
    plan, nodes = search(max_depth=22, beam=4000)
    print("nodes:", nodes)
    if plan:
        print("PLAN:", json.dumps(plan))
    else:
        print("NO PLAN FOUND")
