
import json,collections
ev=[json.loads(x) for x in open("events.jsonl")]
entry=[x for x in ev if x["kind"]=="turn_started" and x["level"]==3][0]["grid"]
def add(q,o,c,x,y,dx,dy,L,head=False):
 if dx==1:cx,cy=x,y+1
 elif dx==-1:cx,cy=x+2,y+1
 elif dy==1:cx,cy=x+1,y
 else:cx,cy=x+1,y+2
 for off in(-1,0,1):q[(cx-dy*off,cy+dx*off)].append((3,'cap',o))
 for k in range(1,L+1):
  bx,by=cx+dx*k,cy+dy*k
  for off in(-1,0,1):q[(bx-dy*off,by+dx*off)].append((c,'body',o))
 if head:q[(cx+dx*(L-1),cy+dy*(L-1))].append((13,'head',o))
def render(s):
 a,b,c,k,m=s; la,lb,lc,ld,L=2+3*a,2+3*b,2+3*c,26+3*k,2+3*m
 q=collections.defaultdict(list)
 for o,col,x,y,dx,dy,l in [('9',9,51,15,0,-1,la),('A',11,51,15-(la+1),-1,0,L),('e',14,9,18,0,-1,lb),('B',11,9,18-(lb+1),1,0,L),('8',8,45,21,0,-1,lc),('C',11,45,21-(lc+1),-1,0,L),('c',12,18,51,0,-1,ld),('D',11,18,51-(ld+1),1,0,L)]:
  add(q,o,col,x,y,dx,dy,l)
 add(q,'H',11,30,42,0,-1,L,True)
 return q
q0=render((0,0,0,0,0));dyn=set(q0);target={(31,9),(30,10),(32,10),(31,11)}
static={(x,y) for y,r in enumerate(entry) for x,v in enumerate(r) if v!=5 and(x,y)not in dyn and(x,y)not in target}
# UI rectangle interiors are foreground overlays, not blockers
seen=set(); overlay=set()
for yy,row in enumerate(entry):
 for xx,v in enumerate(row):
  if v!=2 or (xx,yy) in seen: continue
  dq2=collections.deque([(xx,yy)]); comp={(xx,yy)};seen.add((xx,yy))
  while dq2:
   ux,uy=dq2.popleft()
   for vx,vy in ((ux-1,uy),(ux+1,uy),(ux,uy-1),(ux,uy+1)):
    if 0<=vx<64 and 0<=vy<64 and (vx,vy) not in seen and entry[vy][vx]==2:
     seen.add((vx,vy));comp.add((vx,vy));dq2.append((vx,vy))
  if len(comp)>=12:
   xs=[z[0] for z in comp];ys=[z[1] for z in comp]
   x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
   if x1-x0>=5 and y1-y0>=5:
    overlay.update((vx,vy) for vy in range(y0,y1+1) for vx in range(x0,x1+1))
static-=overlay
def valid(s):
 a,b,c,k,m=s
 if not(0<=a<=4 and 0<=b<=5 and 0<=c<=6 and -8<=k<=8 and 0<=m<=11):return False
 q=render(s)
 for p,cs in q.items():
  x,y=p
  if not(0<=x<64 and 0<=y<64)or p in static:return False
  base=[z for z in cs if z[1]!='head'];heads=[z for z in cs if z[1]=='head']
  if len(base)>1:return False
  if heads and(len(base)!=1 or base[0][2]!='H'):return False
 return True
acts=[('A+',(1,0,0,0,0)),('A-',(-1,0,0,0,0)),('B+',(0,1,0,0,0)),('B-',(0,-1,0,0,0)),('C+',(0,0,1,0,0)),('C-',(0,0,-1,0,0)),('D+',(0,0,0,1,0)),('D-',(0,0,0,-1,0)),('b+',(0,0,0,0,1)),('b-',(0,0,0,0,-1))]
start=(0,0,0,0,0);dq=collections.deque([start]);prev={start:(None,None)};goal=None
while dq:
 s=dq.popleft()
 if s[4]==11:goal=s;break
 for n,d in acts:
  z=tuple(s[i]+d[i] for i in range(5))
  if z not in prev and valid(z):prev[z]=(s,n);dq.append(z)
print("seen",len(prev),"goal",goal)
if goal:
 p=[];z=goal
 while prev[z][0] is not None:
  zz,n=prev[z];p.append((n,z));z=zz
 print("len",len(p));print(list(reversed(p)))
print("mcounts",collections.Counter(z[4] for z in prev),"maxm",max(z[4] for z in prev))
# enumerate valid goal states even if BFS fails
goals=[]
for a in range(5):
 for b in range(6):
  for c in range(7):
   for k in range(-8,9):
    if valid((a,b,c,k,11)):goals.append((a,b,c,k,11))
print("valid goals",len(goals),goals[:30])
