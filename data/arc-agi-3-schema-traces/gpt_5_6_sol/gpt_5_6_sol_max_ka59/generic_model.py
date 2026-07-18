# General world model for ARC3 ka59.
# np, ENTRY_GRID and CURRENT_LEVEL are supplied by the harness.

DIRS = {1:(0,-3), 2:(0,3), 3:(-3,0), 4:(3,0)}

def _components(mask):
    h,w = mask.shape
    seen = np.zeros((h,w), dtype=bool)
    out = []
    for y in range(h):
        for x in range(w):
            if not mask[y,x] or seen[y,x]:
                continue
            stack=[(x,y)]; seen[y,x]=True; pts=[]
            while stack:
                xx,yy=stack.pop(); pts.append((xx,yy))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=xx+dx,yy+dy
                    if 0<=nx<w and 0<=ny<h and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=True; stack.append((nx,ny))
            out.append(pts)
    return out

def _entry_objects():
    e=np.array(ENTRY_GRID,dtype=int)
    ans=[]
    for pts in _components(e==14):
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
        q=e[y0:y1+1,x0:x1+1]
        inner=np.argwhere(q!=14)
        if len(inner)==0:
            continue
        vals=set(int(q[y,x]) for y,x in inner)
        if not vals <= {0,5} or len(vals)!=1:
            continue
        iy0,ix0=np.min(inner,axis=0); iy1,ix1=np.max(inner,axis=0)
        block=q[iy0:iy1+1,ix0:ix1+1]
        if not np.all(block==block[0,0]):
            continue
        # Everything outside the rectangular center block is color 14.
        test=q.copy(); test[iy0:iy1+1,ix0:ix1+1]=14
        if not np.all(test==14):
            continue
        ans.append({"x":x0,"y":y0,"w":x1-x0+1,"h":y1-y0+1,
                    "cx":int(ix0),"cy":int(iy0),
                    "cw":int(ix1-ix0+1),"ch":int(iy1-iy0+1),
                    "val":int(block[0,0])})
    ans.sort(key=lambda o:(o["y"],o["x"]))
    return ans

def _specs():
    out=[]
    for o in _entry_objects():
        s=(o["w"],o["h"],o["cx"],o["cy"],o["cw"],o["ch"])
        if s not in out:
            out.append(s)
    out.sort(key=lambda s:-(s[0]*s[1]))
    return out

def _scan_objects(a):
    h,w=a.shape
    found=[]
    occupied=np.zeros((h,w),dtype=bool)
    for sw,sh,cx,cy,cw,ch in _specs():
        for y in range(h-sh+1):
            for x in range(w-sw+1):
                if np.any(occupied[y:y+sh,x:x+sw]):
                    continue
                q=a[y:y+sh,x:x+sw]
                c=q[cy:cy+ch,cx:cx+cw]
                if c.size==0 or not np.all(c==c.flat[0]):
                    continue
                val=int(c.flat[0])
                if val not in (0,4,5):
                    continue
                outside=q.copy()
                outside[cy:cy+ch,cx:cx+cw]=14
                if val==0:
                    # A selected object's travel-facing outer edge may also
                    # be 0 while it is in contact.
                    if not np.all((outside==14)|(outside==0)):
                        continue
                    if not np.any(outside==14):
                        continue
                else:
                    if not np.all(outside==14):
                        continue
                o={"x":x,"y":y,"w":sw,"h":sh,"cx":cx,"cy":cy,
                   "cw":cw,"ch":ch,"val":val}
                found.append(o)
                occupied[y:y+sh,x:x+sw]=True
    found.sort(key=lambda o:(o["y"],o["x"]))
    return found

def _active(a):
    for o in _scan_objects(a):
        if o["val"]==0:
            return o
    return None

def _frames():
    e=np.array(ENTRY_GRID,dtype=int)
    ans=[]
    for pts in _components(e==4):
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
        w=x1-x0+1; h=y1-y0+1
        if w<3 or h<3:
            continue
        q=e[y0:y1+1,x0:x1+1]
        if (np.all(q[0,:]==4) and np.all(q[-1,:]==4) and
            np.all(q[:,0]==4) and np.all(q[:,-1]==4) and
            np.all(q[1:-1,1:-1]==1)):
            ans.append({"x":x0,"y":y0,"w":w,"h":h,
                        "ix":x0+1,"iy":y0+1,"iw":w-2,"ih":h-2})
    ans.sort(key=lambda f:(f["y"],f["x"]))
    return ans

def _base():
    b=np.array(ENTRY_GRID,dtype=int).copy()
    for o in _entry_objects():
        b[o["y"]:o["y"]+o["h"],o["x"]:o["x"]+o["w"]]=1
    return b

def _restore(a,o):
    b=_base()
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    a[y:y+h,x:x+w]=b[y:y+h,x:x+w]

def _draw(a,o,x=None,y=None,val=None):
    if x is None: x=o["x"]
    if y is None: y=o["y"]
    if val is None: val=o["val"]
    a[y:y+o["h"],x:x+o["w"]]=14
    a[y+o["cy"]:y+o["cy"]+o["ch"],
      x+o["cx"]:x+o["cx"]+o["cw"]]=val

def _rect_overlap(x,y,w,h,o):
    return x < o["x"]+o["w"] and o["x"] < x+w and y < o["y"]+o["h"] and o["y"] < y+h

def _mark_progress(a):
    xs=np.where(a[-1]==4)[0]
    if len(xs):
        a[-1,int(xs[-1])]=0

def _entry_active():
    for o in _entry_objects():
        if o["val"]==0:
            return o
    return None

def _mark_walk_phase(a,newx):
    p0=_entry_active()
    if p0 is not None and (newx-p0["x"])%6==3:
        _mark_progress(a)

def _find_separator(o,action):
    b=_base(); h,w=b.shape
    cx=o["x"]+o["w"]//2; cy=o["y"]+o["h"]//2
    if action in (3,4):
        step=1 if action==4 else -1
        k=(o["x"]+o["w"]) if step>0 else (o["x"]-1)
        # Skip ordinary traversable space to the first color-15 run.
        while 0<=k<w and int(b[cy,k]) in (1,4):
            k+=step
        if not (0<=k<w and int(b[cy,k])==15):
            return None
        s=k
        while 0<=k<w and int(b[cy,k])==15:
            k+=step
        e=k-step
        if not (0<=k<w and int(b[cy,k]) in (1,4)):
            return None
        return min(s,e)+max(s,e)
    else:
        step=1 if action==2 else -1
        k=(o["y"]+o["h"]) if step>0 else (o["y"]-1)
        while 0<=k<h and int(b[k,cx]) in (1,4):
            k+=step
        if not (0<=k<h and int(b[k,cx])==15):
            return None
        s=k
        while 0<=k<h and int(b[k,cx])==15:
            k+=step
        e=k-step
        if not (0<=k<h and int(b[k,cx]) in (1,4)):
            return None
        return min(s,e)+max(s,e)

def _reflect_object(o,action):
    s=_find_separator(o,action)
    if s is None:
        return None
    if action in (3,4):
        return (s-(o["x"]+o["w"]-1),o["y"])
    return (o["x"],s-(o["y"]+o["h"]-1))

def _goals_filled(a):
    fs=_frames()
    if not fs:
        return False
    obs=_scan_objects(a)
    for f in fs:
        ok=False
        for o in obs:
            if (o["val"] in (0,4) and o["x"]==f["ix"] and
                o["y"]==f["iy"] and o["w"]==f["iw"] and o["h"]==f["ih"]):
                ok=True; break
        if not ok:
            return False
    return True

def _finish(info):
    if CURRENT_LEVEL==6:
        info["win"]=True
    else:
        info["level_up"]=True

def is_goal(grid):
    return _goals_filled(np.array(grid,dtype=int))

def step(grid,action,x=None,y=None):
    a=np.array(grid,dtype=int).copy()
    info={"level_up":False,"dead":False,"win":False}

    if action==6:
        obs=_scan_objects(a)
        act=None
        for oo in obs:
            if oo["val"]==0:
                act=oo
                break
        chosen=None
        if x is not None and y is not None:
            for o in obs:
                if o["val"] in (4,5) and o["x"]<=x<o["x"]+o["w"] and o["y"]<=y<o["y"]+o["h"]:
                    chosen=o; break
        if act is not None and chosen is not None:
            oldval=chosen["val"]
            _draw(a,act,val=4)
            _draw(a,chosen,val=0)
            if oldval==5:
                _mark_progress(a)
        if _goals_filled(a):
            _finish(info)
        return a.tolist(),info

    if action not in DIRS:
        return a.tolist(),info
    act=_active(a)
    if act is None:
        return a.tolist(),info
    dx,dy=DIRS[action]
    nx,ny=act["x"]+dx,act["y"]+dy

    # Remove the selected object's old overlay before testing its destination.
    temp=a.copy(); _restore(temp,act)
    others=[o for o in _scan_objects(a) if not (o["x"]==act["x"] and o["y"]==act["y"] and o["w"]==act["w"] and o["h"]==act["h"] and o["val"]==0)]
    hit=None
    for o in others:
        if _rect_overlap(nx,ny,act["w"],act["h"],o):
            hit=o; break

    if hit is not None:
        # Collision launches the passive object through the separator ahead;
        # the selected object stays put and its contact face closes.
        dest=_reflect_object(hit,action)
        if dest is not None:
            _restore(temp,hit)
            _draw(temp,act,val=0)
            _draw(temp,hit,x=dest[0],y=dest[1],val=hit["val"])
            _mark_progress(temp)
            if _goals_filled(temp):
                _finish(info)
            return temp.tolist(),info
        return a.tolist(),info

    h,w=a.shape
    if nx<0 or ny<0 or nx+act["w"]>w or ny+act["h"]>h:
        return a.tolist(),info
    destvals=temp[ny:ny+act["h"],nx:nx+act["w"]]
    if not np.all((destvals==1)|(destvals==4)):
        return a.tolist(),info

    _draw(temp,act,x=nx,y=ny,val=0)

    # Contact feedback: blacken the travel-facing outer edge when immediately
    # flush against a non-floor/non-frame object.
    contact=False
    if dx>0 and nx+act["w"]<w:
        strip=temp[ny:ny+act["h"],nx+act["w"]]
        if np.any((strip!=1)&(strip!=4)):
            temp[ny:ny+act["h"],nx+act["w"]-1]=0; contact=True
    elif dx<0 and nx>0:
        strip=temp[ny:ny+act["h"],nx-1]
        if np.any((strip!=1)&(strip!=4)):
            temp[ny:ny+act["h"],nx]=0; contact=True
    elif dy>0 and ny+act["h"]<h:
        strip=temp[ny+act["h"],nx:nx+act["w"]]
        if np.any((strip!=1)&(strip!=4)):
            temp[ny+act["h"]-1,nx:nx+act["w"]]=0; contact=True
    elif dy<0 and ny>0:
        strip=temp[ny-1,nx:nx+act["w"]]
        if np.any((strip!=1)&(strip!=4)):
            temp[ny,nx:nx+act["w"]]=0; contact=True
    if not contact:
        _mark_walk_phase(temp,nx)
    if _goals_filled(temp):
        _finish(info)
    return temp.tolist(),info
