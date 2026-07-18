import heapq, itertools, pickle

TOPB={(24,4),(30,4),(36,4)}
CENT={(x,y) for x in (18,24,30,36,42) for y in (34,40,46,52,58)} - {(18,40)}
CELLS=TOPB|CENT
TOP={(x,10) for x in range(6,55,6)}
LCOL={(6,y) for y in (10,16,22,28,34,40)}
BAY={(12,40),(18,40)}
SPURS={(18,16),(18,22),(30,16),(30,22),(42,16),(42,22)}
RCOL={(54,y) for y in range(10,59,6)}
NODES=TOP|LCOL|BAY|SPURS|RCOL
D=[(6,0),(-6,0),(0,6),(0,-6)]
ARROW={1:(0,-6),2:(0,6),3:(-6,0),4:(6,0)}

# state: (carts, loads, e1, e2, nines)
#  carts: tuple of 4 positions; loads: tuple of 4 (None,'E','9'); e1/e2: pos,'CART0'..'CART3', or None(consumed)
start=((18,22),(30,22),(42,22),(54,58)), (None,None,None,'9'), (30,4), (42,58), frozenset({(36,34),(42,34),(24,40),(30,46),(18,52)})

def solve(start, maxn=8_000_000):
    tie=itertools.count()
    h=[(0,next(tie),start)]
    prev={start:None}
    popped=0
    while h:
        cost,_,st=heapq.heappop(h)
        carts,loads,e1,e2,nines=st
        popped+=1
        if popped%400000==0: print('...',popped,len(prev),cost)
        occ=set(nines)|{p for p in (e1,e2) if isinstance(p,tuple)}
        cartset=set(carts)
        # arrows
        for a,(dx,dy) in ARROW.items():
            movers={}
            for i,p in enumerate(carts):
                t=(p[0]+dx,p[1]+dy)
                if t in NODES and t not in occ:
                    movers[i]=t
            changed=True
            while changed:
                changed=False
                stay={carts[i] for i in range(4) if i not in movers}
                for i in list(movers):
                    if movers[i] in stay: del movers[i]; changed=True
            if not movers: continue
            nc=tuple(movers.get(i,carts[i]) for i in range(4))
            nst=(nc,loads,e1,e2,nines)
            if nst not in prev:
                prev[nst]=(st,('arrow',a)); heapq.heappush(h,(cost+1,next(tie),nst))
        # jumps
        pieces=[]
        if isinstance(e1,tuple): pieces.append((e1,'E1',None))
        elif isinstance(e1,str): pieces.append((carts[int(e1[4])],'E1',int(e1[4])))
        if isinstance(e2,tuple): pieces.append((e2,'E2',None))
        elif isinstance(e2,str): pieces.append((carts[int(e2[4])],'E2',int(e2[4])))
        for p in nines: pieces.append((p,'9',None))
        for i,ld in enumerate(loads):
            if ld=='9': pieces.append((carts[i],'9',i))
        for pos,col,cidx in pieces:
            for dx,dy in D:
                m=(pos[0]+dx,pos[1]+dy); l=(pos[0]+2*dx,pos[1]+2*dy)
                # mid: peg on cell, or loaded cart (not self)
                mid_load = None
                if m in occ: mid_ok=True; mid_is_e = (m==e1 or m==e2)
                else:
                    mid_ok=False; mid_is_e=False
                    for j,cp in enumerate(carts):
                        if cp==m and loads[j] is not None and j!=cidx:
                            mid_ok=True; mid_load=j
                            mid_is_e = (loads[j]=='E')
                            break
                if not mid_ok: continue
                land_cell = l in CELLS and l not in occ and l not in cartset
                land_cart = None
                for j,cp in enumerate(carts):
                    if cp==l and loads[j] is None and j!=cidx:
                        land_cart=j; break
                if not (land_cell or land_cart is not None): continue
                consumes = col in ('E1','E2') and (mid_is_e or (mid_load is not None and loads[mid_load]=='E'))
                # build next
                nl=list(loads); ne1,ne2=e1,e2; nn=set(nines); ncarts=carts
                if cidx is not None:
                    nl[cidx]=None
                if col=='E1':
                    ne1 = ('CART%d'%land_cart) if land_cart is not None else l
                    if land_cart is not None: nl[land_cart]='E'
                elif col=='E2':
                    ne2 = ('CART%d'%land_cart) if land_cart is not None else l
                    if land_cart is not None: nl[land_cart]='E'
                else:
                    if cidx is None: nn.discard(pos)
                    if land_cart is not None: nl[land_cart]='9'
                    else: nn.add(l)
                if consumes:
                    if m==e1: ne1=None
                    elif m==e2: ne2=None
                    elif mid_load is not None: nl[mid_load]=None  # consumed e in cart
                nst=(ncarts,tuple(nl),ne1,ne2,frozenset(nn))
                act=('jump',pos,m,l,col,consumes)
                if consumes:
                    prev[nst]=(st,act); return nst,prev
                if nst not in prev:
                    prev[nst]=(st,act); heapq.heappush(h,(cost+2,next(tie),nst))
        if len(prev)>maxn:
            print('cap',len(prev)); break
    return None,prev

g,prev=solve(start)
if g:
    path=[]; st=g
    while prev[st] is not None:
        pst,act=prev[st]; path.append(act); st=pst
    path.reverse()
    print('SOLVED %d steps (%d actions)'%(len(path),sum(1 if a[0]=='arrow' else 2 for a in path)))
    for a in path: print('  ',a)
    pickle.dump(path,open('l9_path.pkl','wb'))
else:
    print('NO SOLUTION')
