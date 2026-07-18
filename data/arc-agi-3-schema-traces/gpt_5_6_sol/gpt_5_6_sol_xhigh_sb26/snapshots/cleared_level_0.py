# ARC3 world model: select and move colored 4x4 pieces into 2x2 empty sockets.

def init_state(entry_grid):
    # Successful piece transfers, for action-7 undo. Each entry is
    # (colour, source_piece_x, source_piece_y, dest_socket_x, dest_socket_y).
    return {"moves": []}

def _selected_lower(a):
    """Return (colour,x0,y0) for a lower 4x4 piece with a 0 selection frame."""
    h,w=a.shape
    for y0 in range(54,h-5):
        for x0 in range(1,w-5):
            # a 6x6 zero perimeter surrounding a uniform 4x4 non-background
            if (np.all(a[y0,x0:x0+6]==0) and np.all(a[y0+5,x0:x0+6]==0)
                and np.all(a[y0:y0+6,x0]==0) and np.all(a[y0:y0+6,x0+5]==0)):
                inner=a[y0+1:y0+5,x0+1:x0+5]
                v=int(inner[0,0])
                if v not in (0,2,4,5,8) and np.all(inner==v):
                    return v,x0+1,y0+1
    return None

def _solid_lower_at(a,x,y):
    if y<=53:
        return None
    v=int(a[y,x])
    if v in (0,2,4,5,8):
        return None
    # Find the connected component of this colour in the lower field.
    seen={(x,y)}; stack=[(x,y)]; cells=[]
    while stack:
        xx,yy=stack.pop(); cells.append((xx,yy))
        for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
            if 0<=nx<a.shape[1] and 54<=ny<a.shape[0] and (nx,ny) not in seen and int(a[ny,nx])==v:
                seen.add((nx,ny)); stack.append((nx,ny))
    xs=[p[0] for p in cells]; ys=[p[1] for p in cells]
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
    if x1-x0==3 and y1-y0==3 and len(cells)==16:
        return v,x0,y0
    return None

def _empty_socket_at(a,x,y):
    """A socket is a 2x2 colour-2 square in the central framed workspace."""
    if y>=53 or int(a[y,x])!=2:
        return None
    # bounding box of local 4-connected 2-component
    seen={(x,y)}; stack=[(x,y)]; cells=[]
    while stack:
        xx,yy=stack.pop(); cells.append((xx,yy))
        for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
            if 0<=nx<a.shape[1] and 0<=ny<53 and (nx,ny) not in seen and int(a[ny,nx])==2:
                seen.add((nx,ny)); stack.append((nx,ny))
    xs=[p[0] for p in cells]; ys=[p[1] for p in cells]
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
    if len(cells)==4 and x1-x0==1 and y1-y0==1:
        return x0,y0
    return None

def _advance_meter(b):
    # The long colour-2 row is a move/progress meter: successful moves
    # turn its rightmost remaining 2 into 3.
    best=None
    for yy in range(b.shape[0]):
        xs=np.where(b[yy]==2)[0]
        if len(xs)>=16 and (best is None or len(xs)>len(best[1])):
            best=(yy,xs)
    if best is not None:
        yy,xs=best
        b[yy,int(xs[-1])]=3

def predict(state, grid, action, x=None, y=None):
    a=np.array(grid,dtype=int); b=a.copy()
    moves=list(state.get("moves",[]))
    info={"level_up":False,"dead":False,"win":False}
    if action==6 and x is not None and y is not None and 0<=x<a.shape[1] and 0<=y<a.shape[0]:
        selected=_selected_lower(a)
        socket=_empty_socket_at(a,x,y)
        if selected is not None and socket is not None:
            c,px,py=selected
            sx,sy=socket
            # Remove selected piece and its 0 frame, leaving a centered
            # 2x2 empty socket in its former 4x4 footprint.
            b[py-1:py+5,px-1:px+5]=4
            b[py+1:py+3,px+1:px+3]=2
            # A 2x2 workspace socket receives the piece as a centered 4x4.
            b[sy-1:sy+3,sx-1:sx+3]=c
            _advance_meter(b)
            moves.append((c,px,py,sx,sy))
        else:
            piece=_solid_lower_at(a,x,y)
            if piece is not None:
                c,px,py=piece
                # Clear any prior lower selection frame, then outline this piece.
                old=_selected_lower(a)
                if old is not None:
                    _,ox,oy=old
                    b[oy-1:oy+5,ox-1]=4; b[oy-1:oy+5,ox+4]=4
                    b[oy-1,ox-1:ox+5]=4; b[oy+4,ox-1:ox+5]=4
                b[py-1:py+5,px-1]=0; b[py-1:py+5,px+4]=0
                b[py-1,px-1:px+5]=0; b[py+4,px-1:px+5]=0
    elif action==7:
        if moves:
            # Undo the latest transfer but do not refund the progress/cost
            # meter and do not restore the transient selection frame.
            c,px,py,sx,sy=moves.pop()
            b[sy-1:sy+3,sx-1:sx+3]=4
            b[sy:sy+2,sx:sx+2]=2
            b[py:py+4,px:px+4]=c
        else:
            # With merely a selection active, action 7 acts as cancel.
            old=_selected_lower(a)
            if old is not None:
                _,ox,oy=old
                b[oy-1:oy+5,ox-1]=4; b[oy-1:oy+5,ox+4]=4
                b[oy-1,ox-1:ox+5]=4; b[oy+4,ox-1:ox+5]=4
    # Action 5 is not characterized yet.
    return b.tolist(),info,{"moves":moves}

def is_goal(state, grid):
    # Read the ordered target colours from the top display in ENTRY_GRID.
    e=np.array(ENTRY_GRID,dtype=int); a=np.array(grid,dtype=int)
    target=[]
    y=1
    x=0
    while x<e.shape[1]:
        v=int(e[y,x])
        if v not in (0,2,3,4,5,8):
            x0=x
            while x<e.shape[1] and int(e[y,x])==v:
                x+=1
            if x-x0>=4:
                target.append(v)
        else:
            x+=1
    # Ordered workspace sockets are the four 2x2 colour-2 components above
    # the long lower meter in the entry layout.
    sockets=[]; seen=set()
    for yy in range(1,min(53,e.shape[0])):
        for xx in range(e.shape[1]):
            if int(e[yy,xx])!=2 or (xx,yy) in seen:
                continue
            st=[(xx,yy)]; seen.add((xx,yy)); cells=[]
            while st:
                qx,qy=st.pop(); cells.append((qx,qy))
                for nx,ny in ((qx-1,qy),(qx+1,qy),(qx,qy-1),(qx,qy+1)):
                    if 0<=nx<e.shape[1] and 0<=ny<53 and (nx,ny) not in seen and int(e[ny,nx])==2:
                        seen.add((nx,ny)); st.append((nx,ny))
            xs=[q[0] for q in cells]; ys=[q[1] for q in cells]
            if len(cells)==4 and max(xs)-min(xs)==1 and max(ys)-min(ys)==1:
                sockets.append((min(xs),min(ys)))
    sockets.sort()
    if not target or len(target)!=len(sockets):
        return False
    for c,(sx,sy) in zip(target,sockets):
        if not np.all(a[sy-1:sy+3,sx-1:sx+3]==c):
            return False
    return True
