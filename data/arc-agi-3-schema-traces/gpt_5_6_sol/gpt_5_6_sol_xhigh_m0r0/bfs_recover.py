import json,collections,time
acts=[e for e in map(json.loads,open('events.jsonl')) if e.get('kind')=='action_taken']
ev=next(e for e in acts if e['level']==5);g=ev['grid'];n=4
# comps helper
def comps(c):
 seen=set();out=[]
 for y,r in enumerate(g):
  for x,z in enumerate(r):
   if z!=c or (x,y) in seen:continue
   q=[(x,y)];seen.add((x,y));k=0
   while k<len(q):
    xx,yy=q[k];k+=1
    for p in ((xx+1,yy),(xx-1,yy),(xx,yy+1),(xx,yy-1)):
     u,v=p
     if 0<=u<64 and 0<=v<64 and g[v][u]==c and p not in seen:seen.add(p);q.append(p)
   out.append(q)
 return out
for c in [8,9,12,14]:print(c,[len(q) for q in comps(c)])
btnc=comps(9)[0]; bx=min(x for x,y in btnc);by=min(y for x,y in btnc);B0=(bx,by)
print('B0',B0)
tr={};D={}
for c in [12,14]:
 D[c]=set()
 for q in comps(c):
  if len(q)==16:tr.update({p:c for p in q})
  elif len(q)>16:D[c]|=set(q)
haz={(x,y) for y,r in enumerate(g) for x,z in enumerate(r) if z==8}
base={(x,y) for y,r in enumerate(g) for x,z in enumerate(r) if z==5}
Pentry=((18,22),(42,22));Pcur=((18,18),(42,18))
def add(p,k):
 for v in range(p[1],p[1]+k):
  for u in range(p[0],p[0]+k):base.add((u,v))
for p in Pentry+Pcur:add(p,4)
add(B0,2)
# exact rectangle bit sets cache
def R(p,k):return {(u,v) for v in range(p[1],p[1]+k) for u in range(p[0],p[0]+k)}
def ov(p,k,q,m):return not(p[0]+k-1<q[0] or q[0]+m-1<p[0] or p[1]+k-1<q[1] or q[1]+m-1<p[1])
def keys(p):return {tr[z] for z in R(p,4) if z in tr}
start=(Pcur[0],Pcur[1],B0,-1)
def step(s,a):
 p=[s[0],s[1]];b=s[2];sel=s[3]
 if isinstance(a,tuple):
  # click button toggles; cancel
  return (p[0],p[1],b,(-1 if (a[1] is None or sel==0) else 0))
 if sel==0:
  d={1:(0,-4),2:(0,4),3:(-4,0),4:(4,0)}[a];q=(b[0]+d[0],b[1]+d[1])
  active=keys(p[0])|keys(p[1]);allowed=base.copy()
  for c in active:allowed|=D[c]
  rq=R(q,2)
  if rq<=allowed and not ov(q,2,p[0],4) and not ov(q,2,p[1],4):b=q
 else:
  ds=[]
  for i,z in enumerate(p):
   d=(0,-4) if a==1 else (0,4) if a==2 else ((4,0) if i==0 else (-4,0)) if a==3 else ((-4,0) if i==0 else (4,0))
   ds.append((z[0]+d[0],z[1]+d[1]))
  if any(R(q,4)&haz for q in ds):
   return (Pentry[0],Pentry[1],B0,-1)
  active=keys(p[0])|keys(p[1]);allowed=base|set(tr)
  for c in active:allowed|=D[c]
  for i,q in enumerate(ds):
   rq=R(q,4)
   if rq<=allowed and not ov(q,4,b,2) and not ov(q,4,p[1-i],4):p[i]=q
 return (p[0],p[1],b,sel)
Q=collections.deque([start]);pre={start:None};how={};goal=None;nexp=0;t=time.time()
while Q and nexp<2000000 and time.time()-t<100:
 s=Q.popleft();nexp+=1
 if s[0]==s[1]:
  goal=(s,None);break
 if s[3]<0 and s[0][1]==s[1][1] and abs(s[0][0]-s[1][0])==4:
  goal=(s,3);break
 actions=[1,2,3,4]
 if s[3]<0:actions.append(('c',0))
 else:actions.append(('c',None))
 for a in actions:
  q=step(s,a)
  if q!=s and q not in pre:pre[q]=s;how[q]=a;Q.append(q)
print('expanded',nexp,'seen',len(pre),'goal',goal,'secs',time.time()-t)
if goal:
 z,finala=goal;path=[]
 while pre[z] is not None:path.append(how[z]);z=pre[z]
 path=path[::-1]
 if finala:path.append(finala)
 print('len',len(path),path)
 # dynamic click labels
 s=start;out=[]
 for a in path:
  if isinstance(a,tuple):
   out.append('clickB' if a[1]==0 else 'cancel')
  else:out.append(str(a))
  s=step(s,a)
 print('plan',' '.join(out),'end',s)
