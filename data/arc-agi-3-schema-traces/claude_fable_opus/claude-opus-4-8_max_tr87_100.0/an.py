import json, numpy as np

def frames():
    out=[]
    for l in open('events.jsonl'):
        d=json.loads(l)
        if d.get('kind')=='turn_started':
            g=d['grid']
            if isinstance(g,str): g=json.loads(g)
            out.append((int(d['turn']), int(d['level']), np.array(g)))
    return out

def acts():
    return [json.loads(l) for l in open('events.jsonl') if json.loads(l).get('kind')=='action_taken']

def draw(g): return '/'.join(''.join('#' if v else '.' for v in r) for r in g)
def canon(g):
    a=np.array(g); return min(tuple(map(tuple,np.rot90(a,k).tolist())) for k in range(4))
def gly(G,y,x,on=5):
    return tuple(tuple(1 if G[y+i][x+j]==on else 0 for j in range(5)) for i in range(5))

def runs(row,color):
    out=[];x=0
    while x<len(row):
        if row[x]==color:
            s=x
            while x<len(row) and row[x]==color: x+=1
            out.append((s,x-s))
        else: x+=1
    return out

def parse(G):
    """generic: find the two bottom word boxes (bg=3) and the cursor."""
    H,W=G.shape
    ymid=min(y for y in range(H) if (G[y]==3).sum()>W*0.6)
    # candidate border colours in the bottom region
    info={}
    boxes=[]
    for y in range(ymid,H-6):
        for c in set(G[y].tolist())-{3,0,1,4}:
            rs=runs(G[y],c)
            for (x,w) in rs:
                if w>=7 and (G[y+6,x:x+w]==c).all() and (G[y:y+7,x]==c).all() and (G[y:y+7,x+w-1]==c).all():
                    boxes.append((y,x,w,int(c)))
    boxes=[b for b in boxes if not any(b2[0]<b[0]<b2[0]+6 for b2 in boxes)]
    ys,xs=np.where(G==0)
    cur=(int(xs.min()),int(ys.min())) if len(xs) else None
    # answer box = the one whose x-range contains the cursor x and is below/above the brackets
    ans=None; clue=None
    for (y,x,w,c) in boxes:
        if cur and x<=cur[0]<x+w and y-3<=cur[1]<=y+9: ans=(y,x,w,c)
    for b in boxes:
        if b!=ans: clue=b
    info['boxes']=boxes; info['ans']=ans; info['clue']=clue; info['cursor']=cur
    if ans:
        y,x,w,c=ans
        n=(w-2+2)//7
        info['ans_slots']=[gly(G,y+1,x+1+7*s) for s in range(n)]
        info['ans_n']=n; info['ans_y']=y+1; info['ans_x']=x+1
        info['cursor_slot']=int(round((cur[0]-(x+1))/7.0))
    if clue:
        y,x,w,c=clue
        n=(w-2+2)//7
        info['clue_slots']=[gly(G,y+1,x+1+7*s) for s in range(n)]
    info['bar']=int((G[H-1]==4).sum())
    return info

if __name__=='__main__':
    F=frames(); A=acts()
    lvl=F[-1][1]
    Fl=[f for f in F if f[1]==lvl]
    print("level",lvl,"frames this level",len(Fl))
    for t,l,G in Fl:
        p=parse(G)
        print("turn",t,"cursor_slot",p.get('cursor_slot'),"bar",p['bar'])
        print("   ans:", [draw(g) for g in p['ans_slots']])
