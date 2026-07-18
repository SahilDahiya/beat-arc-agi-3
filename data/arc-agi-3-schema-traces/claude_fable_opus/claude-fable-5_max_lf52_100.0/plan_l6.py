import heapq, itertools, pickle

# ---- static map (world coords, cell/node = 4x4 core top-left) ----
WALL_CELLS = {(84,24),(96,36),(96,42),(108,36),(108,42),
              (6,18),(12,48),(42,48),(72,48),(18,54),(30,54),(42,18)}
EMPTY_CELLS = {(90,24),(90,30),(90,36),(90,42),(102,36),(102,42),(114,36),(114,42),
               (138,36),(138,42),
               (6,12),(12,54),(24,54),(36,54),(42,54),(48,54),(54,54),(60,54),(72,54),(42,12)}
CELLS = WALL_CELLS | EMPTY_CELLS

EAST = {(102,18),(102,24),(108,6),(108,12),(108,18),(114,6),(114,18),(114,24),(114,30),
        (120,6),(120,18),(126,6),(126,18),(126,24),(126,30),(126,36),(132,6),(132,12),
        (132,18),(138,18),(138,24),(138,30)}
WESTC = {(72,12),(78,12),(84,12),(90,12),(90,18),
         (6,24),(12,24),(18,24),(24,24),(30,24),(36,24),(42,24),(60,24),(66,24),(72,24),(78,24),
         (12,36),(12,42),(18,36),(24,30),(24,36),(30,36),(36,36),(42,36),(42,42),
         (54,36),(54,42),(54,48),(60,30),(60,36),(60,48),(66,36),(66,48),(66,54),
         (72,18),(72,36),(72,42)}

DIRS = {1:(0,-6),2:(0,6),3:(-6,0),4:(6,0)}
E=14

# state: (pegs, C, Cload, walls, wc1, wc2)
#  pegs: frozenset of (pos,color); pos is a cell OR 'CART' (in C)
#  C: transport cart pos; Cload: color or None
#  walls: frozenset of 3 wall-cart positions (east net)
#  wc1: west transport pos (net WESTC); wc2: far-west transport pos (net WESTC)
START = (frozenset({((114,36),E),((138,36),8),((138,42),E)}),
         (132,18), None, frozenset({(102,18),(126,6),(138,24)}), (84,12), (6,24))

def carts_of(st):
    pegs,C,Cl,walls,w1,w2 = st
    d = {C:('empty' if Cl is None else 'peg')}
    for w in walls: d[w]='wall'
    d[w1]='empty'; d[w2]='empty'
    return d

def occupied_cells(st):
    pegs = st[0]
    return {p:c for p,c in pegs if p!='CART'}

def entity_at(st, pos, occ=None, cd=None):
    # returns kind,color: 'wall'/'peg'/'empty'/None
    if occ is None: occ=occupied_cells(st)
    if cd is None: cd=carts_of(st)
    if pos in occ: return ('peg',occ[pos])
    if pos in WALL_CELLS: return ('wall',None)
    if pos in EMPTY_CELLS: return ('empty',None)
    if pos in cd:
        k=cd[pos]
        if k=='peg': return ('peg',st[2])
        return (k,None)
    return (None,None)

def legal_jumps(st, visible_only=False):
    """yield (jpos,jcolor,mid,land,consumes) ; jpos may be 'CART' (peg in C)"""
    pegs,C,Cl,walls,w1,w2 = st
    occ=occupied_cells(st); cd=carts_of(st)
    out=[]
    js=[(p,c) for p,c in pegs]
    for p,c in js:
        pos = C if p=='CART' else p
        for d in DIRS.values():
            m=(pos[0]+d[0],pos[1]+d[1]); l=(pos[0]+2*d[0],pos[1]+2*d[1])
            mk,mc = entity_at(st,m,occ,cd)
            if mk not in ('peg','wall'): continue
            lk,lc = entity_at(st,l,occ,cd)
            if lk!='empty': continue
            if visible_only and not (84<=pos[0]<=144 and 84<=l[0]<=144 and 0<=pos[1]<=60 and 0<=l[1]<=60):
                continue
            consumes = (mk=='peg' and mc!=8 and c!=8 and m not in WALL_CELLS)
            out.append((p,c,m,l,consumes))
    return out

def apply_jump(st, jump):
    pegs,C,Cl,walls,w1,w2 = st
    p,c,m,l,consumes = jump
    pegs=set(pegs); pegs.discard((p,c))
    if p=='CART': Cl=None
    occ=occupied_cells(st); cd=carts_of(st)
    # landing
    if l==C and Cl is None and l not in CELLS:
        Cl=c  # board the transport
    else:
        pegs.add((l,c))
    # mid consumption
    if consumes:
        if m==C and st[2] is not None:
            Cl=None
            pegs.discard(('CART',st[2]))
        else:
            for q in list(pegs):
                if q[0]==m: pegs.discard(q)
    return (frozenset(pegs),C,Cl,walls,w1,w2)

def apply_arrow(st, a):
    pegs,C,Cl,walls,w1,w2 = st
    d=DIRS[a]
    carts=[('C',C,EAST)]+[('W%d'%i,w,EAST) for i,w in enumerate(sorted(walls))]+[('w1',w1,WESTC),('w2',w2,WESTC)]
    pos={n:p for n,p,_ in carts}
    net={n:nt for n,p,nt in carts}
    movers={}
    for n,p,nt in carts:
        t=(p[0]+d[0],p[1]+d[1])
        if t in nt: movers[n]=t
    changed=True
    while changed:
        changed=False
        stay={pos[n] for n,_,_ in carts if n not in movers}
        for n in list(movers):
            if movers[n] in stay:
                del movers[n]; changed=True
    if not movers: return None
    np_={n:movers.get(n,pos[n]) for n in pos}
    nw=frozenset(np_[n] for n in np_ if n.startswith('W'))
    return (pegs,np_['C'],Cl,nw,np_['w1'],np_['w2'])

def ne_count(st):
    pegs,C,Cl,walls,w1,w2=st
    n=sum(1 for p,c in pegs if c==E)
    return n

def is_goal_state(st, last_was_consume):
    if not last_was_consume: return False
    if ne_count(st)>1: return False
    return len(legal_jumps(st,visible_only=False))==0

def search(start, maxnodes=4_000_000):
    h=[(0,0,start,None,None,False)]
    seen={start:0}
    parent={}
    cnt=0; tie=itertools.count()
    h=[(0,next(tie),start)]
    parent={start:None}
    while h:
        cost,_,st=heapq.heappop(h)
        if cost>seen.get(st,1e9): continue
        cnt+=1
        if cnt%200000==0: print('...',cnt,'popped, frontier',len(h),'cost',cost)
        if cnt>maxnodes: print('node cap'); break
        # expand arrows
        for a in (1,2,3,4):
            ns=apply_arrow(st,a)
            if ns is None: continue
            nc=cost+1
            if nc<seen.get(ns,1e9):
                seen[ns]=nc; parent[ns]=(st,('arrow',a))
                heapq.heappush(h,(nc,next(tie),ns))
        # expand jumps
        for j in legal_jumps(st,visible_only=True):
            ns=apply_jump(st,j)
            nc=cost+2
            if is_goal_state(ns,j[4]):
                print('GOAL at cost',nc)
                parent[ns]=(st,('jump',j))
                return ns,parent,seen
            if nc<seen.get(ns,1e9):
                seen[ns]=nc; parent[ns]=(st,('jump',j))
                heapq.heappush(h,(nc,next(tie),ns))
    return None,parent,seen

if __name__=='__main__':
    goal,parent,seen=search(START)
    if goal is None:
        print('NO STRICT GOAL FOUND, states:',len(seen))
    else:
        # reconstruct
        path=[]
        st=goal
        while parent[st] is not None:
            pst,act=parent[st]
            path.append((act,st))
            st=pst
        path.reverse()
        print('PLAN length (actions):',sum(1 if a[0]=='arrow' else 2 for a,_ in path))
        for a,s in path:
            if a[0]=='arrow':
                print('ARROW',a[1])
            else:
                p,c,m,l,cons=a[1]
                print('JUMP',p,'col',c,'over',m,'->',l,'CONSUME' if cons else '')
        pickle.dump((START,path),open('l6_plan.pkl','wb'))
        print('saved l6_plan.pkl')
