"""Fast hand-rolled L5 simulator + exhaustive BFS.
State: (epos, dial_idx, rotorH, cage(x,y), bands) where bands = per-band
(frozen tuple of logical (lo,hi) runs, dock (lo,hi) or None).
Rules per the validated world model. Goal: e reaches any cell adjacent-move
onto (46,6) 2x2 (uniform b) OR e enters the top complex at all (report).
"""
import json, sys
from collections import deque
import numpy as np

acts=[]
for l in open('events.jsonl'):
    r=json.loads(l)
    if r.get('kind')=='action_taken': acts.append(r)
ups=[i for i,a in enumerate(acts) if a.get('level_up')]
E=np.array(acts[ups[4]]['grid'])

# ---------- static base map (what's under everything) ----------
# swim[y][x] = True if cell is e-swimmable when not covered by a piece
# base categories from ENTRY with pieces removed:
CAGE0=(22,30)   # entry cage anchor
ROTORH0=True    # entry rotor horizontal
BASE=np.zeros((64,64),dtype=int)  # 0=wall,1=swim(2s etc),2=pipe0(track, not swim)
for y in range(63):
    for x in range(40):
        v=E[y][x]
        if v in (2,6,7,9,10,11,12,13,1) or (v==8 and 32<=x<=39 and 48<=y<=53):
            BASE[y][x]=1
        elif v==0:
            BASE[y][x]=2
# entry pieces: remove rotor cells (c at x0-19 y30-37 area) & cage 8s & runs
# rotor entry H cells + ring/knob: treat ring+knob as permanent swim (8s/c)
RING={(x,y) for x in range(8,12) for y in range(32,36)}
for (x,y) in RING: BASE[y][x]=1  # ring & knob: swimmable always
# rotor arm cells at entry (c in zone minus ring) -> base under them:
# H-arm west x0-7 y32-35 over 4s; x12-13 stubs over 4s; x14-19 over pipe-ext
for y in range(32,36):
    for x in range(0,20):
        if (x,y) in RING: continue
        if E[y][x]==12:
            BASE[y][x]= 2 if x>=14 else 0
# caps rows 30-31/36-37 x7-12 over 4s
for y in (30,31,36,37):
    for x in range(0,20):
        if E[y][x]==12: BASE[y][x]=0
# cage entry cells over pipe/0s
for y in range(30,38):
    for x in range(22,30):
        if E[y][x]==8: BASE[y][x]=2
# conveyor entry runs (1s) & dock (c y56) over 4s (band floors when present)
for y in range(54,60):
    for x in range(0,32):
        if E[y][x] in (1,12): BASE[y][x]=0
# legend ports: special-enterable
PORTS={(34,56):'N',(32,58):'W',(36,58):'E',(34,60):'S'}
# top complex & goal
GOAL=(46,6)

# ---------- piece geometry ----------
def rotor_cells(h):
    cells=set()
    if h:
        for y in range(32,36):
            for x in range(0,20):
                if not (8<=x<=11): cells.add((x,y))
        for y in (30,31,36,37):
            for x in (7,8,9,10,11,12):
                if ((y in (30,36) and 7<=x<=12) or (y in (31,37) and 8<=x<=11)):
                    pass
        # exact caps from entry H shape:
        for (x,y) in [(7,30),(8,30),(9,30),(10,30),(11,30),(12,30),
                      (8,31),(9,31),(10,31),(11,31),
                      (8,36),(9,36),(10,36),(11,36),
                      (7,37),(8,37),(9,37),(10,37),(11,37),(12,37)]:
            cells.add((x,y))
    else:
        for x in range(8,12):
            for y in range(24,44):
                if not (32<=y<=35): cells.add((x,y))
        for (x,y) in [(6,31),(6,32),(6,33),(6,34),(6,35),(6,36),
                      (7,32),(7,33),(7,34),(7,35),
                      (12,32),(12,33),(12,34),(12,35),
                      (13,31),(13,32),(13,33),(13,34),(13,35),(13,36)]:
            cells.add((x,y))
    return cells

def cage_cells(cx,cy):
    cells=set()
    for x in range(cx,cx+8):
        cells.add((x,cy)); cells.add((x,cy+7))
    for y in range(cy+1,cy+7):
        cells.add((cx,y)); cells.add((cx+7,y))
    return cells

TRACK_OK=lambda ncx,ncy: all(E[yy][xx] in (0,8)
    for yy in (ncy,ncy+1) for xx in (ncx,ncx+1))

def band_cells(bands):
    cells=set()
    for i,y0 in enumerate((54,56,58)):
        runs,dock=bands[i]
        for (lo,hi) in runs:
            for x in range(lo,hi+1):
                cells.add((x,y0)); cells.add((x,y0+1))
        if dock:
            for x in range(dock[0],dock[1]+1):
                cells.add((x,y0)); cells.add((x,y0+1))
    return cells

def swim_ok(pos,rot,cage,bandc):
    x,y=pos
    if (x,y) in PORTS: return True
    ok=True
    for (xx,yy) in ((x,y),(x+1,y),(x,y+1),(x+1,y+1)):
        if not (0<=xx<40 and 0<=yy<63): return False
        if (xx,yy) in rot or (xx,yy) in cage or (xx,yy) in bandc:
            continue
        if BASE[yy][xx]!=1: ok=False
    return ok

CYC=[(6,7),(13,8),(12,11),(9,10)]
NODES={0:(32,52),3:(34,58),2:(4,4)}

def step(state,action):
    epos,dial,rotH,cage,bands=state
    rot=rotor_cells(rotH); cg=cage_cells(*cage); bc=band_cells(bands)
    if action in (1,2,3,4):
        dx,dy={1:(0,-2),2:(0,2),3:(-2,0),4:(2,0)}[action]
        np_=(epos[0]+dx,epos[1]+dy)
        if swim_ok(np_,rot,cg,bc):
            return (np_,dial,rotH,cage,bands),False
        return state,False
    if action=='dial':
        return (epos,(dial+1)%4,rotH,cage,bands),False
    if action=='six':
        # aboard check: e on arms
        ex,ey=epos
        aboard=((24<=ey<=43 and 8<=ex<=11 and not(32<=ey<=35)) or
                (32<=ey<=35 and ex<=19 and not(8<=ex<=11)))
        if aboard: return state,False
        ne=epos
        d=NODES.get(dial)
        if d:
            if epos==(18,48): ne=d
            elif epos==d: ne=(18,48)
        return (ne,dial,not rotH,cage,bands),False
    if action in ('N','W','E','S'):
        if PORTS.get(epos)!=action: return state,False
        dx,dy={'N':(0,-4),'S':(0,4),'W':(-4,0),'E':(4,0)}[action]
        ncx,ncy=cage[0]+3+dx,cage[1]+3+dy
        if TRACK_OK(ncx,ncy):
            return (epos,dial,rotH,(cage[0]+dx,cage[1]+dy),bands),False
        return state,False
    if action=='b':
        nb=[]
        for i in range(3):
            runs,dock=bands[i]
            moved=[];fused=None
            for (lo,hi) in runs:
                lo2,hi2=lo+2,hi+2
                if hi2==21: fused=(lo2,hi2)
                else: moved.append((lo2,hi2))
            newdock=dock
            if fused: newdock=fused
            if dock is not None:
                clip=[]
                for (lo,hi) in moved:
                    if hi<=11: continue
                    clip.append((max(lo,12),hi))
                moved=[(6,11)]+clip
                newdock=fused
            nb.append((tuple(moved),newdock))
        return (epos,dial,rotH,cage,tuple(nb)),False
    return state,False

# current real state:
start=((8,34),3,True,(18,30),(((14,19),),None,((12,17),),(18,21),((8,13),),None))
# bands tuple: ((runs),dock) x3 — fix structure:
start=((28,52),0,True,(22,30),
       ((((6,11),),None),(((8,13),),(16,21)),(((12,17),),None)))
ACTS=[1,2,3,4,'six','dial','b','N','W','E','S']
seen={start}
q=deque([(start,())])
found=None;n=0
while q and not found:
    st,path=q.popleft()
    if len(path)>=140: continue
    for a in ACTS:
        ns,win=step(st,a)
        n+=1
        if ns in seen: continue
        seen.add(ns)
        ex,ey=ns[0]
        if ey<=11 and ex>=30:
            found=path+(a,); print("REACHED TOP COMPLEX at",ns[0]); break
        q.append((ns,path+(a,)))
    if n>60_000_000: break
print("states:",len(seen),"nodes:",n)
if found: print("PATH:",found)
else: print("TOP COMPLEX UNREACHABLE under current rules")
