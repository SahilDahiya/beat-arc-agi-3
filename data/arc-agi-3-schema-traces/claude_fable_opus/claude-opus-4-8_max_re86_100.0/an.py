import json, numpy as np
from collections import Counter

def frames():
    """[(action_or_None, grid)] : the true per-action chain (initial frame first)."""
    out=[]
    first=None
    for line in open("events.jsonl"):
        e=json.loads(line)
        if e["kind"]=="turn_started" and first is None:
            first=np.array(e["grid"]); out.append((None, first))
        elif e["kind"]=="action_taken":
            out.append((e["action"], np.array(e["grid"])))
    return out

def analyze(g, verbose=True):
    boxes=[]
    for y in range(1,63):
        for x in range(1,63):
            c=g[y][x]
            if c not in (4,5) and all(g[y+dy][x+dx]==4 for dy in(-1,0,1) for dx in(-1,0,1) if (dy,dx)!=(0,0)):
                boxes.append((x,y,int(c)))
    boxset={(x,y) for x,y,c in boxes}
    info={'boxes':boxes,'crosses':{}}
    for col in np.unique(g):
        col=int(col)
        if col in (4,5,15): continue
        ys,xs=np.where(g==col)
        pts=[(int(a),int(b)) for a,b in zip(xs,ys) if (int(a),int(b)) not in boxset and int(b)<63]
        if len(pts)<3: continue
        cx=Counter(p[0] for p in pts).most_common(1)[0][0]
        cy=Counter(p[1] for p in pts).most_common(1)[0][0]
        info['crosses'][col]=(cx,cy)
    info['bar']=int(np.count_nonzero(g[63]!=15))
    return info

if __name__=="__main__":
    fs=frames()
    acts=[a for a,_ in fs[1:]]
    print("actions:", acts)
    changes=0
    for i in range(len(fs)):
        a,g=fs[i]
        inf=analyze(g)
        if i>0:
            hist=acts[:i]
            ch=sum(1 for j in range(1,len(hist)) if hist[j]!=hist[j-1])
            pred_bar=len(hist)-ch
        else:
            pred_bar=0
        print(f"t={i} act={a} crosses={inf['crosses']} bar={inf['bar']}  [n-changes = {pred_bar}] {'OK' if pred_bar==inf['bar'] else '<<< MISMATCH'}")
