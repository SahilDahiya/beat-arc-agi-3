# ARC3 world model: select and move colored 4x4 pieces into 2x2 empty sockets.

def init_state(entry_grid):
    # Successful piece transfers, for action-7 undo. Each entry is
    # (colour, source_piece_x, source_piece_y, dest_socket_x, dest_socket_y).
    return {"moves": []}

def _piece_shape(w):
    """Return (colour,is_hollow) for a solid or hollow 4x4 piece."""
    if w.shape!=(4,4):
        return None
    v=int(w[0,0])
    if v in (0,2,4,5):
        return None
    if np.all(w==v):
        return v,False
    per=np.concatenate((w[0,:],w[3,:],w[1:3,0],w[1:3,3]))
    if np.all(per==v) and np.all(w[1:3,1:3]==4):
        return v,True
    return None

def _selected_lower(a):
    """Return (colour,x0,y0,is_hollow) for a selected lower piece."""
    h,w=a.shape
    for y0 in range(54,h-5):
        for x0 in range(1,w-5):
            if (np.all(a[y0,x0:x0+6]==0) and np.all(a[y0+5,x0:x0+6]==0)
                and np.all(a[y0:y0+6,x0]==0) and np.all(a[y0:y0+6,x0+5]==0)):
                shape=_piece_shape(a[y0+1:y0+5,x0+1:x0+5])
                if shape is not None:
                    v,hollow=shape
                    return v,x0+1,y0+1,hollow
    return None

def _solid_lower_at(a,x,y):
    """Find a lower solid OR hollow piece containing the clicked cell."""
    if y<=53:
        return None
    # Scanning boxes also lets a click in a hollow piece's background centre
    # select that piece.
    for py in range(max(54,y-3),min(y+1,a.shape[0]-3)):
        for px in range(max(0,x-3),min(x+1,a.shape[1]-3)):
            shape=_piece_shape(a[py:py+4,px:px+4])
            if shape is None:
                continue
            v,hollow=shape
            # Require the box to be maximal so a 4x4 subwindow of a larger
            # coloured area is not mistaken for a piece.
            if ((px==0 or not np.all(a[py:py+4,px-1]==v)) and
                (px+4==a.shape[1] or not np.all(a[py:py+4,px+4]==v))):
                return v,px,py,hollow
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
            c,px,py,hollow=selected
            sx,sy=socket
            # Remove selected piece and its 0 frame, leaving a centered
            # 2x2 empty socket in its former 4x4 footprint.
            b[py-1:py+5,px-1:px+5]=4
            b[py+1:py+3,px+1:px+3]=2
            # A 2x2 workspace socket receives the same solid/hollow 4x4 shape.
            b[sy-1:sy+3,sx-1:sx+3]=c
            if hollow:
                b[sy:sy+2,sx:sx+2]=4
            _advance_meter(b)
            moves.append((c,px,py,sx,sy,hollow))
        else:
            piece=_solid_lower_at(a,x,y)
            if piece is not None:
                c,px,py,hollow=piece
                # Clear any prior lower selection frame, then outline this piece.
                old=_selected_lower(a)
                if old is not None:
                    _,ox,oy,_=old
                    b[oy-1:oy+5,ox-1]=4; b[oy-1:oy+5,ox+4]=4
                    b[oy-1,ox-1:ox+5]=4; b[oy+4,ox-1:ox+5]=4
                b[py-1:py+5,px-1]=0; b[py-1:py+5,px+4]=0
                b[py-1,px-1:px+5]=0; b[py+4,px-1:px+5]=0
    elif action==7:
        if moves:
            # Undo the latest transfer but do not refund the progress/cost
            # meter and do not restore the transient selection frame.
            c,px,py,sx,sy,hollow=moves.pop()
            b[sy-1:sy+3,sx-1:sx+3]=4
            b[sy:sy+2,sx:sx+2]=2
            b[py:py+4,px:px+4]=c
            if hollow:
                b[py+1:py+3,px+1:px+3]=4
        else:
            # With merely a selection active, action 7 acts as cancel.
            old=_selected_lower(a)
            if old is not None:
                _,ox,oy,_=old
                b[oy-1:oy+5,ox-1]=4; b[oy-1:oy+5,ox+4]=4
                b[oy-1,ox-1:ox+5]=4; b[oy+4,ox-1:ox+5]=4
    elif action==5:
        # Submit advances exactly when the displayed socket ordering matches
        # the target display. (The terminal next-level grid is not predicted.)
        if is_goal({"moves":moves},a.tolist()):
            info["level_up"]=True
    return b.tolist(),info,{"moves":moves}

def is_goal(state, grid):
    e=np.array(ENTRY_GRID,dtype=int); a=np.array(grid,dtype=int)
    # Ordered target colours in the top display.
    target=[]; x=0
    while x<e.shape[1]:
        v=int(e[1,x])
        if v not in (0,2,3,4,5):
            x0=x
            while x<e.shape[1] and int(e[1,x])==v:
                x+=1
            if x-x0>=4:
                target.append(v)
        else:
            x+=1

    # All entry-layout 2x2 sockets in the workspace.
    sockets=[]; seen=set()
    for yy in range(10,min(53,e.shape[0])):
        for xx in range(e.shape[1]):
            if int(e[yy,xx])!=2 or (xx,yy) in seen:
                continue
            st=[(xx,yy)]; seen.add((xx,yy)); cells=[]
            while st:
                qx,qy=st.pop(); cells.append((qx,qy))
                for nx,ny in ((qx-1,qy),(qx+1,qy),(qx,qy-1),(qx,qy+1)):
                    if 0<=nx<e.shape[1] and 10<=ny<53 and (nx,ny) not in seen and int(e[ny,nx])==2:
                        seen.add((nx,ny)); st.append((nx,ny))
            xs=[q[0] for q in cells]; ys=[q[1] for q in cells]
            if len(cells)==4 and max(xs)-min(xs)==1 and max(ys)-min(ys)==1:
                sockets.append((min(xs),min(ys)))

    items_by_y={}
    # An original socket is normally a leaf. If its CURRENT 4x4 footprint
    # contains a hollow piece, that movable piece has instead made the socket
    # into a structural child reference.
    for sx,sy in sockets:
        shape=_piece_shape(a[sy-1:sy+3,sx-1:sx+3])
        if shape is not None and shape[1]:
            items_by_y.setdefault(sy,[]).append((sx+0.5,"token",shape[0]))
        else:
            items_by_y.setdefault(sy,[]).append((sx+0.5,"socket",(sx,sy)))

    # Fixed hollow child-reference tokens already drawn in the entry layout.
    for ty in range(10,min(50,e.shape[0]-3)):
        for tx in range(1,e.shape[1]-3):
            shape=_piece_shape(e[ty:ty+4,tx:tx+4])
            if shape is not None and shape[1]:
                items_by_y.setdefault(ty+1,[]).append((tx+1.5,"token",shape[0]))

    # A child tray can also contain a fixed prefilled solid 4x4 leaf. Detect
    # only exact isolated 4x4 colour components in the central workspace.
    seen_col=set()
    for yy in range(10,min(50,e.shape[0])):
        for xx in range(e.shape[1]):
            v=int(e[yy,xx])
            if v in (0,2,3,4,5) or (xx,yy) in seen_col:
                continue
            st=[(xx,yy)]; seen_col.add((xx,yy)); cells=[]
            while st:
                qx,qy=st.pop(); cells.append((qx,qy))
                for nx,ny in ((qx-1,qy),(qx+1,qy),(qx,qy-1),(qx,qy+1)):
                    if 0<=nx<e.shape[1] and 10<=ny<50 and (nx,ny) not in seen_col and int(e[ny,nx])==v:
                        seen_col.add((nx,ny)); st.append((nx,ny))
            xs=[q[0] for q in cells]; ys=[q[1] for q in cells]
            if len(cells)==16 and max(xs)-min(xs)==3 and max(ys)-min(ys)==3:
                px,py=min(xs),min(ys)
                items_by_y.setdefault(py+1,[]).append((px+1.5,"fixed",(v,px,py)))

    # Split each tier into side-by-side trays at gaps larger than the normal
    # six-cell item spacing.
    segments=[]
    for yy in sorted(items_by_y):
        vals=sorted(items_by_y[yy]); cur=[]
        for item in vals:
            if cur and item[0]-cur[-1][0]>7.1:
                segments.append({"y":yy,"items":cur,"center":sum(q[0] for q in cur)/len(cur)})
                cur=[]
            cur.append(item)
        if cur:
            segments.append({"y":yy,"items":cur,"center":sum(q[0] for q in cur)/len(cur)})
    if not segments:
        return False
    root=min(range(len(segments)),key=lambda i:(segments[i]["y"],-len(segments[i]["items"])))
    used={root}; token_map={}
    def flatten(si):
        seg=segments[si]; out=[]
        for pos,kind,val in seg["items"]:
            if kind!="token":
                out.append((kind,val))
                continue
            # Repeated hollow tokens of the same colour reference (and thus
            # repeat) the SAME child tray rather than consuming another one.
            if val in token_map:
                out.extend(flatten(token_map[val])); continue
            candidates=[j for j,s in enumerate(segments) if j not in used and s["y"]>seg["y"]]
            if candidates:
                md=min(segments[j]["y"]-seg["y"] for j in candidates)
                candidates=[j for j in candidates if segments[j]["y"]-seg["y"]==md]
                j=min(candidates,key=lambda k:abs(segments[k]["center"]-pos))
                token_map[val]=j; used.add(j); out.extend(flatten(j))
        return out
    leaves=flatten(root)
    if not target or len(target)!=len(leaves):
        return False
    for c,(kind,val) in zip(target,leaves):
        if kind=="socket":
            sx,sy=val
            if not np.all(a[sy-1:sy+3,sx-1:sx+3]==c):
                return False
        else:
            v,px,py=val
            if v!=c or not np.all(a[py:py+4,px:px+4]==c):
                return False
    return True
