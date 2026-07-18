
import json,collections
ev=[json.loads(x) for x in open("events.jsonl")]
entry=[x for x in ev if x["kind"]=="turn_started" and x["level"]==3][0]["grid"]
# renderer claims: (value,kind,owner). kind body/cap/head
def add_segment(claims,owner,c,x,y,dx,dy,L,headed=False):
    # x,y tile top-left at current translated position
    if dx==1: cx,cy=x,y+1
    elif dx==-1: cx,cy=x+2,y+1
    elif dy==1: cx,cy=x+1,y
    else: cx,cy=x+1,y+2
    for off in (-1,0,1):
        p=(cx-dy*off,cy+dx*off); claims[p].append((3,'cap',owner))
    for q in range(1,L+1):
        bx,by=cx+dx*q,cy+dy*q
        for off in (-1,0,1):
            p=(bx-dy*off,by+dx*off);claims[p].append((c,'body',owner))
    if headed:
        p=(cx+dx*(L-1),cy+dy*(L-1)); claims[p].append((13,'head',owner))
def render(st):
    a,b,c,k,m=st
    la,lb,lc,ld=2+3*a,2+3*b,2+3*c,26+3*k
    L=2+3*m
    q=collections.defaultdict(list)
    # parent plus translated b terminal
    add_segment(q,'9',9,51,15,0,-1,la)
    add_segment(q,'A',11,51,15-(la+1),-1,0,L)
    add_segment(q,'e',14,9,18,0,-1,lb)
    add_segment(q,'B',11,9,18-(lb+1),1,0,L)
    add_segment(q,'8',8,45,21,0,-1,lc)
    add_segment(q,'C',11,45,21-(lc+1),-1,0,L)
    add_segment(q,'c',12,18,51,0,-1,ld)
    add_segment(q,'D',11,18,51-(ld+1),1,0,L)
    add_segment(q,'H',11,30,42,0,-1,L,True)
    return q
# derive initial dynamic cells and static blockers
q0=render((0,0,0,0,0))
dynamic=set(q0)
target={(31,9),(30,10),(32,10),(31,11)}
static={(x,y) for y,row in enumerate(entry) for x,v in enumerate(row)
        if v!=5 and (x,y) not in dynamic and (x,y) not in target}
def valid(st,verbose=False):
    a,b,c,k,m=st
    if not(0<=a<=4 and 0<=b<=5 and 0<=c<=6 and -8<=k<=8 and 0<=m<=11):return False
    q=render(st)
    for p,cs in q.items():
        x,y=p
        if not(0<=x<64 and 0<=y<64):
            return False
        if p in static:return False
        base=[z for z in cs if z[1]!='head']
        heads=[z for z in cs if z[1]=='head']
        # all multiple non-head claims allowed only when every claim is b body
        if len(base)>1 and not all(z[0]==11 and z[1]=='body' for z in base):
            return False
        if heads:
            # exactly its own body must be underneath; any other base claim blocks head
            if len(base)!=1 or base[0][2]!='H':
                return False
    return True
def transvalid(old,new):
    q=render(new)
    p=(31,43-3*old[4])
    base=[z for z in q.get(p,[]) if z[1] != 'head']
    return len(base)==1 and base[0][2]=='H'
print("init",valid((0,0,0,0,0)),"current pack",valid((2,4,4,6,1)))
# BFS
start=(0,0,0,0,0)
acts=[('A+',(1,0,0,0,0)),('A-',(-1,0,0,0,0)),('B+',(0,1,0,0,0)),('B-',(0,-1,0,0,0)),('C+',(0,0,1,0,0)),('C-',(0,0,-1,0,0)),('D+',(0,0,0,1,0)),('D-',(0,0,0,-1,0)),('b+',(0,0,0,0,1)),('b-',(0,0,0,0,-1))]
dq=collections.deque([start]);prev={start:(None,None)};goal=None
while dq:
 s=dq.popleft()
 if s[4]==11:
  goal=s;break
 for name,d in acts:
  z=tuple(s[i]+d[i] for i in range(5))
  if z not in prev and valid(z) and transvalid(s,z):
   prev[z]=(s,name);dq.append(z)
print("states",len(prev),"goal",goal)
if goal:
 path=[];z=goal
 while prev[z][0] is not None:
  z0,name=prev[z];path.append((name,z));z=z0
 path.reverse()
 print("len",len(path))
 print(path)
