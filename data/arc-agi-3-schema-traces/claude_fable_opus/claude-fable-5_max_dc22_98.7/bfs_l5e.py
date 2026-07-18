import json, hashlib, sys
from collections import deque
import numpy as np

acts=[]
for l in open('events.jsonl'):
    r=json.loads(l)
    if r.get('kind')=='action_taken': acts.append(r)

# L4 entry = after-grid of the 4th level_up
ups=[i for i,a in enumerate(acts) if a.get('level_up')]
i4=ups[4]
ENTRY=acts[i4]['grid']

src=open('world_model_v5.py').read()
ns={'np':np,'ENTRY_GRID':ENTRY,'CURRENT_LEVEL':5}
exec(src,ns)
predict=ns['predict']; init_state=ns['init_state']

# thread state along real L4 history
state=init_state(ENTRY)
g=ENTRY
for i in range(i4+1,len(acts)):
    a=acts[i]
    if a['action']==0:
        state=init_state(ENTRY); g=acts[i]['grid']; continue
    ng,info,state=predict(state,g,a['action'],a.get('x'),a.get('y'))
    g=acts[i]['grid']  # use real grid (should equal ng)

print("threaded; state keys:",list(state.keys()))

ACTIONS=[(1,None,None),(2,None,None),(3,None,None),(4,None,None),
         (6,52,25),(6,56,8)]

def key(grid,st):
    h=hashlib.md5()
    for row in grid[:63]: h.update(bytes(row))
    h.update(repr(st.get('carried')).encode()); h.update(repr(st.get('l5dial',(6,7))).encode()); h.update(repr(sorted(st.get('rcover',{}).items())).encode())
    h.update(repr(sorted(st.get('gcover',{}).items())).encode())
    return h.digest()

start=(g,state)
seen={key(g,state):0}
frontier=deque([(g,state,0,())])
nodes=0; found=None
MAXDEPTH=90; MAXNODES=2600000
epos=set()
def eof(grid):
    for yy in range(63):
        for xx in range(38):
            if grid[yy][xx]==14: return (xx,yy)
    return None
epos.add(eof(g))
while frontier and found is None:
    grid,st,d,path=frontier.popleft()
    if d>=MAXDEPTH: continue
    for (a,x,y) in ACTIONS:
        try:
            ng,info,nst=predict(st,grid,a,x,y)
        except Exception as e:
            print("ERR",a,x,y,e); continue
        nodes+=1
        if info.get('level_up'):
            found=path+((a,x,y),); break
        ep2=eof(ng)
        if ep2 is not None and ep2[1]<=22 and ep2[0]<=12:
            found=path+((a,x,y),); print("REACHED items-box zone", ep2); break
        if info.get('dead'): continue
        k=key(ng,nst)
        if k in seen: continue
        seen[k]=d+1
        epos.add(eof(ng))
        frontier.append((ng,nst,d+1,path+((a,x,y),)))
    if nodes>MAXNODES: break
print("nodes expanded:",nodes,"unique states:",len(seen),"frontier left:",len(frontier))
print("e positions reachable:",sorted(epos))
if found:
    print("PATH FOUND len",len(found))
    for s in found: print(s)
else:
    print("NO PATH within depth",MAXDEPTH)
