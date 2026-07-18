import numpy as np

_DIR={1:(0,-4),2:(0,4),3:(-4,0),4:(4,0)}

def init_state(entry_grid):
    return {"turn":None,"comp_active":False,"comp_post":False}

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

def _companion_action5(g):
    ys,xs=np.where(g==12)
    if len(xs)==0:return False
    cx,cy=int(xs.min()),int(ys.min())
    # Once both members reach the socket, the next tick parks rather than
    # translating farther west. A partially entered pair keeps transporting.
    if _socket_dest(cx,cy):
        for dx,dy in _DIR.values():
            qx,qy=cx+dx,cy+dy
            if _block_at(g,qx,qy,5) and _socket_dest(qx,qy):return False
    # A rim5 block adjacent to the companion is its selected rigid partner.
    for face,(dx,dy) in _DIR.items():
        qx,qy=cx+dx,cy+dy
        if not _block_at(g,qx,qy,5):continue
        # The selected rigid pair shortest-paths to a free socket placement.
        # This is westward for the first two observed blocks; lower/upper
        # blocks can turn vertically once aligned with an open socket slot.
        offx,offy=qx-cx,qy-cy
        h=g.copy();h[cy:cy+4,cx:cx+4]=1
        if _socket_dest(cx,cy):_restore_under_block(h,cx,cy)
        _restore_under_block(h,qx,qy)
        ent=np.array(ENTRY_GRID,dtype=int)
        H,W=g.shape
        def ok(xx,yy):
            if xx<0 or yy<0 or xx+4>W or yy+4>H-1:return False
            if np.all(h[yy:yy+4,xx:xx+4]==1):return True
            return _socket_dest(xx,yy) and np.array_equal(h[yy:yy+4,xx:xx+4],ent[yy:yy+4,xx:xx+4])
        queue=[(cx,cy,None)];seen={(cx,cy)};i=0;chosen=None
        while i<len(queue):
            xx,yy,first=queue[i];i+=1
            bx,by=xx+offx,yy+offy
            if _socket_dest(xx,yy) and _socket_dest(bx,by):
                chosen=first;break
            for a in (3,1,2,4):
                mx,my=_DIR[a];nx,ny=xx+mx,yy+my
                if (nx,ny) in seen:continue
                if ok(nx,ny) and ok(nx+offx,ny+offy):
                    seen.add((nx,ny));queue.append((nx,ny,a if first is None else first))
        if chosen is not None:
            mx,my=_DIR[chosen];ncx,ncy=cx+mx,cy+my;nqx,nqy=qx+mx,qy+my
            pat=g[qy:qy+4,qx:qx+4].copy()
            g[:,:]=h;g[nqy:nqy+4,nqx:nqx+4]=pat
            g[ncy:ncy+4,ncx:ncx+4]=12
        return True
    return False

def _companion_dir(g,x0,y0):
    """Shortest-path one tick toward the nearest undelivered rim4 block."""
    H,W=g.shape
    targets=[]
    for yy in range(H-3):
        for xx in range(W-3):
            if (_block_at(g,xx,yy,4) or _block_at(g,xx,yy,3)) and not _socket_dest(xx,yy):targets.append((xx,yy))
    if not targets:return None
    goals={}
    for bx,by in targets:
        for a,(dx,dy) in _DIR.items():
            # position from which moving action a enters the target
            goals[(bx-dx,by-dy)]=a
    h=g.copy();h[y0:y0+4,x0:x0+4]=1
    if _socket_dest(x0,y0):_restore_under_block(h,x0,y0)
    q=[(x0,y0,None)];seen={(x0,y0)};i=0
    order=(4,2,1,3)  # prefer east, then south on equal shortest paths
    while i<len(q):
        xx,yy,first=q[i];i+=1
        if (xx,yy) in goals:return goals[(xx,yy)] if first is None else first
        for a in order:
            dx,dy=_DIR[a];nx,ny=xx+dx,yy+dy
            if (nx,ny) in seen or nx<0 or ny<0 or nx+4>W or ny+4>H-1:continue
            clear=np.all(h[ny:ny+4,nx:nx+4]==1)
            if not clear and _socket_dest(nx,ny):
                ent=np.array(ENTRY_GRID,dtype=int)
                clear=np.array_equal(h[ny:ny+4,nx:nx+4],ent[ny:ny+4,nx:nx+4])
            if clear:
                seen.add((nx,ny));q.append((nx,ny,a if first is None else first))
    return None

def _move_companion(g,action,turn,post=False):
    # The solid color12 companion autonomously seeks undelivered rim4 blocks.
    if action not in _DIR:return
    ys,xs=np.where(g==12)
    if len(xs)==0:return
    x0,y0=int(xs.min()),int(ys.min())
    if _socket_dest(x0,y0):
        # The first arrow after a companion pair reaches the socket parks its
        # selected rim5 block. That arrow does not move the companion; later
        # arrows let it leave the socket and restore the socket underneath.
        parked=False
        for dx,dy in _DIR.values():
            qx,qy=x0+dx,y0+dy
            if _block_at(g,qx,qy,5) and _socket_dest(qx,qy):
                g[qy,qx:qx+4]=4;g[qy+3,qx:qx+4]=4
                g[qy+1:qy+3,qx]=4;g[qy+1:qy+3,qx+3]=4
                parked=True
        if parked:return True
    if CURRENT_LEVEL==1:
        auto=_companion_dir(g,x0,y0)
        if auto is None:return False
        action=auto
    dx,dy=_DIR[action];nx,ny=x0+dx,y0+dy
    h=g.copy();h[y0:y0+4,x0:x0+4]=1
    if _socket_dest(x0,y0):_restore_under_block(h,x0,y0)
    clear=False
    if 0<=nx and 0<=ny and nx+4<=g.shape[1] and ny+4<=g.shape[0]:
        clear=np.all(h[ny:ny+4,nx:nx+4]==1)
        if not clear and _socket_dest(nx,ny):
            ent=np.array(ENTRY_GRID,dtype=int)
            clear=np.array_equal(h[ny:ny+4,nx:nx+4],ent[ny:ny+4,nx:nx+4])
    if clear:
        g[:,:]=h;g[ny:ny+4,nx:nx+4]=12
    elif _block_at(g,nx,ny,4):
        # The solid companion's directly-ahead selectable block uses rim5.
        g[ny,nx:nx+4]=5;g[ny+3,nx:nx+4]=5
        g[ny+1:ny+3,nx]=5;g[ny+1:ny+3,nx+3]=5
    return False

def _budget(g,turn):
    g[-1,:]=7
    # Level 1 has a 70-action budget rendered onto 64 cells (nearest pixel):
    # n=round(64*turn/70), giving skips at turns 6,18,30,41,53,65.
    n=((32*turn+17)//35) if CURRENT_LEVEL==1 else ((turn+1)//3 if turn<=11 else (4+max(0,(turn-12)//3) if turn<=38 else 4+max(0,(turn-13)//3)))
    if n:g[-1,max(0,g.shape[1]-n):]=4

def predict(state,grid,action,x=None,y=None):
    g=np.array(grid,dtype=int)
    raw=state.get("turn",None)
    if raw is None:
        base=np.array(ENTRY_GRID,dtype=int)
        n=int(np.sum(g[-1,:]==4))
        if n:raw=(n if CURRENT_LEVEL==1 else (3*n+1 if n<=4 else 12+3*(n-4)))
        elif not np.array_equal(g,base):raw=1
        else:raw=0
    # Reconcile the clock from the rendered strip after a model reinstall.
    if CURRENT_LEVEL==1:
        raw=max(int(raw),int(np.sum(g[-1,:]==4)))
    active=state.get("comp_active",None)
    if active is None:
        ys,xs=np.where(g==12)
        active=bool(len(xs) and int(xs.min())<36)
    post=state.get("comp_post",None)
    if post is None:
        ys,xs=np.where(g==12)
        post=bool(len(xs) and int(xs.min())<24 and not any(_block_at(g,int(xs.min())+dx,int(ys.min())+dy,5) for dx,dy in _DIR.values()))
    st={"turn":int(raw),"comp_active":bool(active),"comp_post":bool(post)}
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
                            filled=0
                            for yy in range(T,B-3):
                                for xx in range(L,R-3):
                                    if _block_at(g,xx,yy): filled+=1
                            ent=np.array(ENTRY_GRID,dtype=int)
                            required=0
                            for yy in range(ent.shape[0]-3):
                                for xx in range(ent.shape[1]-3):
                                    if _block_at(ent,xx,yy,4): required+=1
                            if required>0 and filled>=required:
                                if CURRENT_LEVEL is not None and CURRENT_LEVEL>=8:
                                    info["win"]=True
                                else:
                                    info["level_up"]=True
    # Companion advances on every simple action. If it has a rim5 partner,
    # the rigid pair transports west; otherwise the unladen companion follows
    # its autonomous route (even during a remote main interact).
    comp_used=_companion_action5(g) if action in (1,2,3,4,5) else False
    if action in (1,2,3,4,5) and not comp_used:
        ca=action if action in _DIR else 4
        if _move_companion(g,ca,st["turn"],st["comp_post"]):
            st["comp_post"]=True
            st["comp_active"]=False
    if action in (1,2,3,4,5):
        if action==5 and comp_used:st["comp_active"]=True
        st["turn"]+=1
        _budget(g,st["turn"])
    return g.tolist(),info,st
