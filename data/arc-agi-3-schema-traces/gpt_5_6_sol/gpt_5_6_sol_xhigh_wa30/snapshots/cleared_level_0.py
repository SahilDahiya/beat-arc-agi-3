import numpy as np

_DIR={1:(0,-4),2:(0,4),3:(-4,0),4:(4,0)}

def init_state(entry_grid):
    return {"turn":None}

def _box(g):
    ys,xs=np.where(g==14)
    if len(xs)==0:return None
    x0,x1=int(xs.min()),int(xs.max())+1
    y0,y1=int(ys.min()),int(ys.max())+1
    if x1-x0==3:
        if x0>0 and np.all(g[y0:y1,x0-1]==0):x0-=1
        else:x1+=1
    if y1-y0==3:
        if y0>0 and np.all(g[y0-1,x0:x1]==0):y0-=1
        else:y1+=1
    return x0,y0,x0+4,y0+4

def _facing(g,b):
    if b is None:return None
    x0,y0,_,_=b
    if np.all(g[y0,x0:x0+4]==0):return 1
    if np.all(g[y0+3,x0:x0+4]==0):return 2
    if np.all(g[y0:y0+4,x0]==0):return 3
    if np.all(g[y0:y0+4,x0+3]==0):return 4
    return None

def _border(r):
    return np.concatenate((r[0,:],r[3,:],r[1:3,0],r[1:3,3]))

def _block_at(g,x,y,rim=None):
    if x<0 or y<0 or x+4>g.shape[1] or y+4>g.shape[0]:return False
    r=g[y:y+4,x:x+4]
    if not np.all(r[1:3,1:3]==9):return False
    b=_border(r)
    return np.all(b==rim) if rim is not None else True

def _socket():
    ent=np.array(ENTRY_GRID,dtype=int)
    ys,xs=np.where(ent==2)
    if len(xs)==0:return None
    return int(xs.min())-1,int(ys.min())-1,int(xs.max())+2,int(ys.max())+2

def _socket_dest(x,y):
    s=_socket()
    return s is not None and s[0]<=x and x+4<=s[2] and s[1]<=y and y+4<=s[3]

def _restore_under_block(h,x,y):
    h[y:y+4,x:x+4]=1
    s=_socket()
    if s is None:return
    L,T,R,B=s
    xa,xb=max(x,L),min(x+4,R)
    ya,yb=max(y,T),min(y+4,B)
    if xa<xb and ya<yb:
        ent=np.array(ENTRY_GRID,dtype=int)
        h[ya:yb,xa:xb]=ent[ya:yb,xa:xb]

def _draw_player(g,x,y,face):
    g[y:y+4,x:x+4]=14
    if face==1:g[y,x:x+4]=0
    elif face==2:g[y+3,x:x+4]=0
    elif face==3:g[y:y+4,x]=0
    elif face==4:g[y:y+4,x+3]=0

def _highlight(g,b,face):
    blocks=[]
    H,W=g.shape
    for y in range(H-3):
        for x in range(W-3):
            if _block_at(g,x,y) and np.all((_border(g[y:y+4,x:x+4])==3)|(_border(g[y:y+4,x:x+4])==4)):
                blocks.append((x,y))
    for x,y in blocks:
        g[y,x:x+4]=4;g[y+3,x:x+4]=4
        g[y+1:y+3,x]=4;g[y+1:y+3,x+3]=4
    if b is None or face not in _DIR:return
    x,y,_,_=b;dx,dy=_DIR[face];q=(x+dx,y+dy)
    if q in blocks:
        x,y=q
        g[y,x:x+4]=3;g[y+3,x:x+4]=3
        g[y+1:y+3,x]=3;g[y+1:y+3,x+3]=3

def _budget(g,turn):
    g[-1,:]=7
    n=(turn+1)//3 if turn<=11 else (4+max(0,(turn-12)//3) if turn<=38 else 4+max(0,(turn-13)//3))
    if n:g[-1,max(0,g.shape[1]-n):]=4

def predict(state,grid,action,x=None,y=None):
    g=np.array(grid,dtype=int)
    raw=state.get("turn",None)
    if raw is None:
        base=np.array(ENTRY_GRID,dtype=int)
        n=int(np.sum(g[-1,:]==4))
        if n:raw=(3*n+1 if n<=4 else 12+3*(n-4))
        elif not np.array_equal(g,base):raw=1
        else:raw=0
    st={"turn":int(raw)}
    info={"level_up":False,"dead":False,"win":False}

    if action in _DIR:
        b=_box(g);moved=False
        if b is not None:
            px,py,_,_=b
            face=_facing(g,b)
            dx,dy=_DIR[action]
            # A grabbed rim0 block and player translate as a rigid pair.
            if face in _DIR:
                fx,fy=_DIR[face];qx,qy=px+fx,py+fy
            else:
                qx=qy=-99
            held=_block_at(g,qx,qy,0)
            if held:
                pat=g[qy:qy+4,qx:qx+4].copy()
                npx,npy=px+dx,py+dy
                nqx,nqy=qx+dx,qy+dy
                h=g.copy();h[py:py+4,px:px+4]=1
                _restore_under_block(h,qx,qy)
                pok=(0<=npx and 0<=npy and npx+4<=g.shape[1] and npy+4<=g.shape[0]
                     and np.all(h[npy:npy+4,npx:npx+4]==1))
                bok=False
                if 0<=nqx and 0<=nqy and nqx+4<=g.shape[1] and nqy+4<=g.shape[0]:
                    if np.all(h[nqy:nqy+4,nqx:nqx+4]==1):
                        bok=True
                    elif _socket_dest(nqx,nqy):
                        ent=np.array(ENTRY_GRID,dtype=int)
                        bok=np.array_equal(h[nqy:nqy+4,nqx:nqx+4],ent[nqy:nqy+4,nqx:nqx+4])
                if pok and bok:
                    g=h;g[nqy:nqy+4,nqx:nqx+4]=pat
                    _draw_player(g,npx,npy,face)
                    moved=True
            else:
                nx,ny=px+dx,py+dy
                h=g.copy();h[py:py+4,px:px+4]=1
                if (0<=nx and 0<=ny and nx+4<=g.shape[1] and ny+4<=g.shape[0]
                    and np.all(h[ny:ny+4,nx:nx+4]==1)):
                    g=h;_draw_player(g,nx,ny,action);moved=True
                    _highlight(g,_box(g),action)
    elif action==5:
        b=_box(g);face=_facing(g,b)
        if b is not None and face in _DIR:
            px,py,_,_=b;dx,dy=_DIR[face];qx,qy=px+dx,py+dy
            if _block_at(g,qx,qy):
                r=g[qy:qy+4,qx:qx+4];bd=_border(r)
                val=0 if np.all(bd==3) else (3 if np.all(bd==0) else None)
                if val is not None:
                    g[qy,qx:qx+4]=val;g[qy+3,qx:qx+4]=val
                    g[qy+1:qy+3,qx]=val;g[qy+1:qy+3,qx+3]=val
                    if val==3:
                        s=_socket()
                        if s is not None:
                            L,T,R,B=s
                            filled=sum(1 for xx in range(L,R-3) if _block_at(g,xx,T))
                            if filled>=3:
                                if CURRENT_LEVEL is not None and CURRENT_LEVEL>=8:
                                    info["win"]=True
                                else:
                                    info["level_up"]=True
    if action in (1,2,3,4,5):
        st["turn"]+=1
        _budget(g,st["turn"])
    return g.tolist(),info,st
