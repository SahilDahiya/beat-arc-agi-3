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

def _target_shapes():
    # Closed color-4 contours may outline non-rectangular passengers.  Their
    # enclosed holes are the exact target masks (rectangles are a special case).
    e=np.array(ENTRY_GRID,dtype=int)
    ans=[]
    for pts in _components(e==4):
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
        h=y1-y0+1; w=x1-x0+1
        wall=np.zeros((h,w),dtype=bool)
        for x,y in pts:
            wall[y-y0,x-x0]=True
        outside=np.zeros((h,w),dtype=bool); stack=[]
        for yy in range(h):
            for xx in range(w):
                if (yy==0 or yy==h-1 or xx==0 or xx==w-1) and not wall[yy,xx] and not outside[yy,xx]:
                    outside[yy,xx]=True; stack.append((xx,yy))
        while stack:
            xx,yy=stack.pop()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=xx+dx,yy+dy
                if 0<=nx<w and 0<=ny<h and not wall[ny,nx] and not outside[ny,nx]:
                    outside[ny,nx]=True; stack.append((nx,ny))
        hole=(~wall)&(~outside)
        hp=np.argwhere(hole)
        if len(hp):
            gpts=[(x0+int(xx),y0+int(yy)) for yy,xx in hp]
            gx=[p[0] for p in gpts]; gy=[p[1] for p in gpts]
            ans.append({"pts":gpts,"x":min(gx),"y":min(gy),
                        "w":max(gx)-min(gx)+1,"h":max(gy)-min(gy)+1})
    ans.sort(key=lambda t:(t["y"],t["x"]))
    return ans

def _shape_signature(pts):
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    x0=min(xs); y0=min(ys)
    return tuple(sorted((x-x0,y-y0) for x,y in pts))

def _matching_solid_target(pts):
    sig=_shape_signature(pts)
    cand=[t for t in _target_shapes() if _shape_signature(t["pts"])==sig]
    if not cand:
        return None
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    sx,sy=min(xs),min(ys)
    aligned=[t for t in cand if t["y"]==sy]
    if not aligned:
        aligned=[t for t in cand if t["x"]==sx]
    return min(aligned or cand,key=lambda q:abs(q["x"]-sx)+abs(q["y"]-sy))

def _base():
    b=np.array(ENTRY_GRID,dtype=int).copy()
    for o in _entry_objects():
        b[o["y"]:o["y"]+o["h"],o["x"]:o["x"]+o["w"]]=1
    # Solid passengers also overlay ordinary floor at their entry positions.
    b[b==11]=1
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

def _paint_contacts(a,o):
    # A selected object's whole face is black when any part is flush against
    # another dynamic object.
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    H,W=a.shape
    def objpix(v):
        return (v==14)|(v==0)|(v==5)|(v==11)
    if x>0 and np.any(objpix(a[y:y+h,x-1])):
        a[y:y+h,x]=0
    if x+w<W and np.any(objpix(a[y:y+h,x+w])):
        a[y:y+h,x+w-1]=0
    if y>0 and np.any(objpix(a[y-1,x:x+w])):
        a[y,x:x+w]=0
    if y+h<H and np.any(objpix(a[y+h,x:x+w])):
        a[y+h-1,x:x+w]=0

def _touches_solid(a,o):
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    H,W=a.shape
    return ((x>0 and np.any(a[y:y+h,x-1]==11)) or
            (x+w<W and np.any(a[y:y+h,x+w]==11)) or
            (y>0 and np.any(a[y-1,x:x+w]==11)) or
            (y+h<H and np.any(a[y+h,x:x+w]==11)))

def _staged_near_solid(a,o,action):
    # A silent alignment cue occurs only on the useful pushing side of a solid:
    # opposite the direction from that shaped passenger to its same-row/column
    # matching contour.  These stride lanes are grounded in the entry layout
    # and remain after the passenger launches.
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    # Around a moved concave passenger, arriving exactly one controller
    # stride from any occupied face is the silent alignment beat before the
    # next pocket entry, whether the arriving stride is normal or tangential.
    entry_solid_sets=[set(p) for p in
                      _components(np.array(ENTRY_GRID,dtype=int)==11)]
    for pts in _components(a==11):
        ps=set(pts)
        if ps in entry_solid_sets:
            continue
        if (any((x+w+3,yy) in ps for yy in range(y,y+h)) or
            any((x-4,yy) in ps for yy in range(y,y+h)) or
            any((xx,y+h+3) in ps for xx in range(x,x+w)) or
            any((xx,y-4) in ps for xx in range(x,x+w))):
            return True
    targets=_target_shapes()
    for pts in _components(np.array(ENTRY_GRID,dtype=int)==11):
        sig=_shape_signature(pts)
        cand=[t for t in targets if _shape_signature(t["pts"])==sig]
        if not cand:
            continue
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        sx,sy=min(xs),min(ys)
        aligned=[t for t in cand if t["y"]==sy]
        if not aligned:
            aligned=[t for t in cand if t["x"]==sx]
        t=min(aligned or cand,key=lambda q:abs(q["x"]-sx)+abs(q["y"]-sy))
        ddx=t["x"]-sx; ddy=t["y"]-sy
        # An entry-source staging lane can remain meaningful after launch when
        # source and target share one axis.  For a diagonal route, however, the
        # first axial launch changes which side is useful; the vacated source's
        # other concavities no longer suppress gait.
        still_at_entry=all(int(a[py,px])==11 for px,py in pts)
        if ddx and ddy and not still_at_entry:
            continue
        ps=set(pts)
        if action in (1,2):
            if ddx>0 and any((x+w+3,yy) in ps for yy in range(y,y+h)):
                return True
            if ddx<0 and any((x-4,yy) in ps for yy in range(y,y+h)):
                return True
        if action in (3,4):
            if ddy>0 and any((xx,y+h+3) in ps for xx in range(x,x+w)):
                return True
            if ddy<0 and any((xx,y-4) in ps for xx in range(x,x+w)):
                return True
    return False

def _solid_partly_on_target(a):
    # True while a shaped passenger overlaps, but has not yet fully filled,
    # its own matching contour.
    for pts in _components(a==11):
        t=_matching_solid_target(pts)
        if t is None:
            continue
        ps=set(pts); ts=set(t["pts"])
        if ps & ts and not ts.issubset(ps):
            return True
    return False

def _at_vacated_solid_anchor(a,o):
    # Once an aligned shaped passenger advances a macro slot, its immediately
    # vacated lattice anchor remains a silent controller beat.  This is derived
    # from the same entry passenger/target spacing used by solid launches.
    targets=_target_shapes()
    entry_components=_components(np.array(ENTRY_GRID,dtype=int)==11)
    for pts in _components(a==11):
        sig=_shape_signature(pts)
        cand=[t for t in targets if _shape_signature(t["pts"])==sig]
        if not cand:
            continue
        sx=min(p[0] for p in pts); sy=min(p[1] for p in pts)
        aligned=[t for t in cand if t["y"]==sy]
        if not aligned:
            aligned=[t for t in cand if t["x"]==sx]
        t=min(aligned or cand,key=lambda q:abs(q["x"]-sx)+abs(q["y"]-sy))
        ddx=t["x"]-sx; ddy=t["y"]-sy
        if ddx and ddy:
            continue
        anchors=[]
        for q in entry_components:
            if _shape_signature(q)==sig:
                anchors.append((min(p[0] for p in q),min(p[1] for p in q)))
        for q in targets:
            if _shape_signature(q["pts"])==sig:
                anchors.append((q["x"],q["y"]))
        gaps=[]
        for j in range(len(anchors)):
            for k in range(j):
                dx=abs(anchors[j][0]-anchors[k][0])
                dy=abs(anchors[j][1]-anchors[k][1])
                if dx: gaps.append(dx)
                if dy: gaps.append(dy)
        if not gaps:
            continue
        stride=min(gaps)
        px=sx-(stride if ddx>0 else -stride if ddx<0 else 0)
        py=sy-(stride if ddy>0 else -stride if ddy<0 else 0)
        if o["x"]==px and o["y"]==py:
            return True
    return False

def _useful_side_contact(a,o,action):
    # Useful-side contact permits ordinary gait feedback only when the stride
    # was tangential.  A normal stride into the passenger is the final staging
    # beat before a push and is silent.
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    targets=_target_shapes()
    for pts in _components(a==11):
        sig=_shape_signature(pts)
        cand=[t for t in targets if _shape_signature(t["pts"])==sig]
        if not cand:
            continue
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        sx,sy=min(xs),min(ys)
        aligned=[t for t in cand if t["y"]==sy]
        if not aligned:
            aligned=[t for t in cand if t["x"]==sx]
        t=min(aligned or cand,key=lambda q:abs(q["x"]-sx)+abs(q["y"]-sy))
        ddx=t["x"]-sx; ddy=t["y"]-sy
        ps=set(pts)
        if ddx>0 and any((x+w,yy) in ps for yy in range(y,y+h)):
            return action!=4
        if ddx<0 and any((x-1,yy) in ps for yy in range(y,y+h)):
            return action!=3
        if ddy>0 and any((xx,y+h) in ps for xx in range(x,x+w)):
            return action!=2
        if ddy<0 and any((xx,y-1) in ps for xx in range(x,x+w)):
            return action!=1
    return False

def _launch_solid(a,act,nx,ny,action):
    # A useful-side impact advances the contacted shaped passenger by one
    # macro-lattice slot toward its matching contour.  It may therefore take
    # several impacts to cross a longer lane.
    hit=None
    for pts in _components(a==11):
        if any(nx<=px<nx+act["w"] and ny<=py<ny+act["h"] for px,py in pts):
            hit=pts; break
    if hit is None:
        return None
    t=_matching_solid_target(hit)
    if t is None:
        return None
    xs=[p[0] for p in hit]; ys=[p[1] for p in hit]
    sx,sy=min(xs),min(ys)
    ddx=t["x"]-sx; ddy=t["y"]-sy
    needed=(4 if ddx>0 else 3 if ddx<0 else
            2 if ddy>0 else 1 if ddy<0 else None)
    if action!=needed:
        return None

    # Derive the macro spacing from all same-shaped entry passengers and
    # contours rather than hard-coding this board's 15-cell lattice.
    sig=_shape_signature(hit); anchors=[]
    for q in _components(np.array(ENTRY_GRID,dtype=int)==11):
        if _shape_signature(q)==sig:
            anchors.append((min(p[0] for p in q),min(p[1] for p in q)))
    for q in _target_shapes():
        if _shape_signature(q["pts"])==sig:
            anchors.append((q["x"],q["y"]))
    gaps=[]
    for j in range(len(anchors)):
        for k in range(j):
            dx=abs(anchors[j][0]-anchors[k][0])
            dy=abs(anchors[j][1]-anchors[k][1])
            if dx: gaps.append(dx)
            if dy: gaps.append(dy)
    stride=min(gaps) if gaps else max(abs(ddx),abs(ddy))
    # An impact advances exactly one macro slot along the impact axis; the
    # remaining target offset is handled by later impacts from another side.
    if action in (3,4):
        mx=(min(abs(ddx),stride) if ddx>0 else
            -min(abs(ddx),stride) if ddx<0 else 0)
        my=0
    else:
        mx=0
        my=(min(abs(ddy),stride) if ddy>0 else
            -min(abs(ddy),stride) if ddy<0 else 0)
    dest=[(px+mx,py+my) for px,py in hit]

    out=a.copy(); b=_base()
    # If the nominal macro slot overlaps a separator, the separator carries
    # the whole shaped passenger through and packs it flush on the far side.
    # Shift only far enough along the impact direction for every occupied
    # shape cell to clear the color-15 band.
    ux,uy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
    portal_leg=False
    for _ in range(max(out.shape)):
        if not any(0<=px<out.shape[1] and 0<=py<out.shape[0] and
                   int(b[py,px])==15 for px,py in dest):
            break
        dest=[(px+ux,py+uy) for px,py in dest]
        portal_leg=True
    for px,py in hit:
        out[py,px]=b[py,px]
    if not all(0<=px<out.shape[1] and 0<=py<out.shape[0] and
               int(out[py,px]) in (1,4) for px,py in dest):
        return None
    for px,py in dest:
        out[py,px]=11
    return out,portal_leg

def _solid_bbox_entry(a,old,new,action):
    # Concave passengers have an implicit rectangular boundary.  Entering a
    # non-useful side cues regardless of travel direction.  On the useful side,
    # a tangential alignment stride is silent, but a normal stride toward the
    # passenger cues even before physical pixels touch.
    def sides(o,pts):
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        sx,sy=min(xs),min(ys); sw=max(xs)-sx+1; sh=max(ys)-sy+1
        x,y,w,h=o["x"],o["y"],o["w"],o["h"]
        yr=(y<sy+sh and sy<y+h); xr=(x<sx+sw and sx<x+w)
        return {"left":x+w==sx and yr, "right":x==sx+sw and yr,
                "up":y+h==sy and xr, "down":y==sy+sh and xr}
    for pts in _components(a==11):
        t=_matching_solid_target(pts)
        if t is None:
            continue
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        sx,sy=min(xs),min(ys)
        ddx=t["x"]-sx; ddy=t["y"]-sy
        if ddx and ddy:
            # Diagonal macro routes have no single rectangular staging axis;
            # their empty bbox concavities do not emit edge-entry cues.
            continue
        useful=("left" if ddx>0 else "right" if ddx<0 else
                "up" if ddy>0 else "down" if ddy<0 else None)
        normal={"left":4,"right":3,"up":2,"down":1}.get(useful)
        def in_useful_end_band(o):
            # A concave shape can be approached through a corner pocket.  Once
            # the controller is aligned with the target-facing end band, a
            # tangential move along that pocket is useful staging, even if its
            # outer bbox edge is nominally a different side.
            x,y,w,h=o["x"],o["y"],o["w"],o["h"]
            return ((useful=="down" and y+h==sy+(max(p[1] for p in pts)-sy+1)) or
                    (useful=="up" and y==sy) or
                    (useful=="right" and x+w==sx+(max(p[0] for p in pts)-sx+1)) or
                    (useful=="left" and x==sx))
        so=sides(old,pts); sn=sides(new,pts)
        old_cue=(not in_useful_end_band(old) and
                 any(v and (k!=useful or action==normal) for k,v in so.items()))
        new_cue=(not in_useful_end_band(new) and
                 any(v and (k!=useful or action==normal) for k,v in sn.items()))
        if new_cue and not old_cue:
            return True
    return False

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

def _separator_axes():
    # A separator axis is a color-15 run bounded by traversable terrain.
    # Exterior color-15 regions are therefore ignored.
    b=_base(); h,w=b.shape
    vertical=False; horizontal=False
    for y in range(h):
        x=0
        while x<w:
            if int(b[y,x])!=15:
                x+=1; continue
            s=x
            while x<w and int(b[y,x])==15:
                x+=1
            if s>0 and x<w and int(b[y,s-1]) in (1,4) and int(b[y,x]) in (1,4):
                vertical=True
    for x in range(w):
        y=0
        while y<h:
            if int(b[y,x])!=15:
                y+=1; continue
            s=y
            while y<h and int(b[y,x])==15:
                y+=1
            if s>0 and y<h and int(b[s-1,x]) in (1,4) and int(b[y,x]) in (1,4):
                horizontal=True
    return vertical,horizontal

def _mark_walk_phase(a,newx,newy,action):
    p0=_entry_active()
    # The bar samples a checkerboard on the room-transition lattice.  Only
    # coordinates along separator axes participate: L0 has x only, while L1
    # has x and y, explaining why consecutive orthogonal moves can both mark.
    if p0 is not None:
        vx,hy=_separator_axes()
        d=0
        if vx: d += newx-p0["x"]
        if hy: d += newy-p0["y"]
        if not vx and not hy:
            d=(newx-p0["x"])+(newy-p0["y"])
        if d%6==3:
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

def _launch_train(hit,others,action):
    # A struck passive object carries the impulse through the separator.  It
    # gathers every passive in its lane ahead of it; on the far side the train
    # packs against the first frame that intersects the leading object's lane.
    s=_find_separator(hit,action)
    if s is None:
        return None
    train=[hit]
    changed=True
    while changed:
        changed=False
        for o in others:
            if o in train:
                continue
            if action in (3,4):
                overlap=any(o["y"] < q["y"]+q["h"] and q["y"] < o["y"]+o["h"] for q in train)
                ahead=(o["x"]<hit["x"]) if action==3 else (o["x"]>hit["x"])
            else:
                overlap=any(o["x"] < q["x"]+q["w"] and q["x"] < o["x"]+o["w"] for q in train)
                ahead=(o["y"]<hit["y"]) if action==1 else (o["y"]>hit["y"])
            if overlap and ahead:
                train.append(o); changed=True
    if action==3:
        train.sort(key=lambda o:o["x"])
    elif action==4:
        train.sort(key=lambda o:-(o["x"]+o["w"]))
    elif action==1:
        train.sort(key=lambda o:o["y"])
    else:
        train.sort(key=lambda o:-(o["y"]+o["h"]))
    lead=train[0]
    frames=[]
    for f in _frames():
        if action==3:
            side=f["x"]+f["w"]-1 < s/2
            cross=f["y"] <= lead["y"]+lead["h"]-1 and lead["y"] <= f["y"]+f["h"]-1
        elif action==4:
            side=f["x"] > s/2
            cross=f["y"] <= lead["y"]+lead["h"]-1 and lead["y"] <= f["y"]+f["h"]-1
        elif action==1:
            side=f["y"]+f["h"]-1 < s/2
            cross=f["x"] <= lead["x"]+lead["w"]-1 and lead["x"] <= f["x"]+f["w"]-1
        else:
            side=f["y"] > s/2
            cross=f["x"] <= lead["x"]+lead["w"]-1 and lead["x"] <= f["x"]+f["w"]-1
        if side and cross:
            frames.append(f)
    if not frames:
        # A lone projectile without a frame still mirrors through the portal.
        if len(train)==1:
            p=_reflect_object(hit,action)
            return [(hit,p[0],p[1])] if p is not None else None
        return None
    if action==3:
        f=max(frames,key=lambda q:q["x"]+q["w"])
        cursor=f["x"]+f["w"]-1
        placed=[]
        for o in train:
            placed.append((o,cursor,o["y"])); cursor+=o["w"]
    elif action==4:
        f=min(frames,key=lambda q:q["x"])
        cursor=f["x"]
        placed=[]
        for o in train:
            nx=cursor-o["w"]+1
            placed.append((o,nx,o["y"])); cursor=nx
    elif action==1:
        f=max(frames,key=lambda q:q["y"]+q["h"])
        cursor=f["y"]+f["h"]-1
        placed=[]
        for o in train:
            placed.append((o,o["x"],cursor)); cursor+=o["h"]
    else:
        f=min(frames,key=lambda q:q["y"])
        cursor=f["y"]
        placed=[]
        for o in train:
            ny=cursor-o["h"]+1
            placed.append((o,o["x"],ny)); cursor=ny
    return placed

def init_state(entry_grid):
    obs=_entry_objects()
    return {"objects":[{"x":o["x"],"y":o["y"],"w":o["w"],"h":o["h"],
                         "val":o["val"],"phase":0,"launched":False} for o in obs]}

def _copy_state(state):
    if state is None or "objects" not in state:
        return init_state(ENTRY_GRID)
    return {"objects":[dict(o) for o in state["objects"]]}

def _state_index(state,o):
    for i,q in enumerate(state["objects"]):
        if q["x"]==o["x"] and q["y"]==o["y"] and q["w"]==o["w"] and q["h"]==o["h"]:
            return i
    return None

def _sync_active_index(state,o):
    i=_state_index(state,o)
    if i is not None:
        return i
    # Backtest's first-ever transition has no prior frame and is unscored.
    # Recover the selected identity/phase from its displacement since the
    # initialized state, then continue exact state tracking.
    cand=[]
    for j,q in enumerate(state["objects"]):
        if q["val"]==0 and q["w"]==o["w"] and q["h"]==o["h"]:
            cand.append((abs(q["x"]-o["x"])+abs(q["y"]-o["y"]),j))
    if not cand:
        return None
    i=min(cand)[1]; q=state["objects"][i]
    vx,hy=_separator_axes()
    turns=0
    if vx: turns += (o["x"]-q["x"])//3
    if hy: turns += (o["y"]-q["y"])//3
    q["phase"]=(q["phase"]+turns)%2
    q["x"]=o["x"]; q["y"]=o["y"]
    return i

def _attempt_phase(a,state,i,action,emit=True):
    if i is None:
        return 0
    vx,hy=_separator_axes()
    if np.any(np.array(ENTRY_GRID,dtype=int)==11):
        # Solid boards have directional horizontal feet.  Vertical travel
        # always reports; a horizontal separator makes each vertical attempt
        # switch the stored foot as well.  Portal-train collisions suppress
        # their report at the call site while leaving the pusher phase stored.
        phase=state["objects"][i]["phase"]
        if action in (1,2):
            # Without a horizontal separator, vertical motion does not switch
            # feet and always reports.  With one, both vertical directions
            # report the departing foot, then switch it.
            if not hy:
                if emit:
                    _mark_progress(a)
                return phase
            if emit and phase==1:
                _mark_progress(a)
            return 1-phase
        if action==4:
            phase=1-phase
            if emit and phase==1:
                _mark_progress(a)
            return phase
        if action==3:
            if emit and phase==1:
                _mark_progress(a)
            return 1-phase
        return phase
    toggle=((action in (3,4) and vx) or (action in (1,2) and hy) or
            (not vx and not hy))
    cand=state["objects"][i]["phase"]
    if toggle:
        cand=1-cand
    if cand==1:
        _mark_progress(a)
    return cand

def _goals_filled(a):
    e=np.array(ENTRY_GRID,dtype=int)
    if np.any(e==11):
        targets=_target_shapes()
        solids=[_shape_signature(p) for p in _components(e==11)]
        obs=_scan_objects(a)
        for t in targets:
            sig=_shape_signature(t["pts"])
            if sig in solids:
                if not all(int(a[y,x])==11 for x,y in t["pts"]):
                    return False
            else:
                ok=False
                for o in obs:
                    if (o["val"] in (0,4) and o["x"]==t["x"] and
                        o["y"]==t["y"] and o["w"]==t["w"] and o["h"]==t["h"]):
                        ok=True; break
                if not ok:
                    return False
        return bool(targets)
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

def predict(state,grid,action,x=None,y=None):
    a=np.array(grid,dtype=int).copy()
    st=_copy_state(state)
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
            ai=_sync_active_index(st,act); ci=_state_index(st,chosen)
            _draw(a,act,val=4)
            _draw(a,chosen,val=0)
            _paint_contacts(a,chosen)
            if ai is not None: st["objects"][ai]["val"]=4
            if ci is not None:
                st["objects"][ci]["val"]=0
                # Selecting a manually staged piece restarts its walking foot;
                # a freshly launched passenger retains its carried phase.
                if not st["objects"][ci].get("launched",False):
                    st["objects"][ci]["phase"]=0
            # Selecting a piece staged on the rim of its own matching frame
            # emits a bar pulse (the ready-to-enter cue).
            ready=False
            b=_base()
            for f in _frames():
                if f["iw"]==chosen["w"] and f["ih"]==chosen["h"]:
                    if (chosen["x"] < f["x"]+f["w"] and f["x"] < chosen["x"]+chosen["w"] and
                        chosen["y"] < f["y"]+f["h"] and f["y"] < chosen["y"]+chosen["h"] and
                        np.any(b[chosen["y"]:chosen["y"]+chosen["h"],
                                 chosen["x"]:chosen["x"]+chosen["w"]]==4)):
                        ready=True
            if (np.any(np.array(ENTRY_GRID,dtype=int)==11) or
                (ready and ci is not None and st["objects"][ci].get("launched",False))):
                # Solid-passenger boards acknowledge controller selection just
                # as they acknowledge a direct click on a shaped passenger.
                _mark_progress(a)
        if chosen is None and x is not None and y is not None:
            if 0<=y<a.shape[0] and 0<=x<a.shape[1] and int(a[y,x])==11:
                # Solid shaped passengers acknowledge a click with a bar
                # pulse but do not become the visible controller.
                _mark_progress(a)
                # This acknowledgment does not alter the visible controller's
                # horizontal gait/phase.
        if _goals_filled(a):
            _finish(info)
        return a.tolist(),info,st

    if action not in DIRS:
        return a.tolist(),info,st
    act=_active(a)
    if act is None:
        return a.tolist(),info,st
    ai=_sync_active_index(st,act)
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
        # Collision launches a lane of passive objects through the separator;
        # the selected object stays put and its contact face closes.
        placed=_launch_train(hit,others,action)
        if placed is not None:
            ids=[_state_index(st,oo) for oo,px,py in placed]
            for oo,px,py in placed:
                _restore(temp,oo)
            _draw(temp,act,val=0)
            for k,(oo,px,py) in enumerate(placed):
                _draw(temp,oo,x=px,y=py,val=oo["val"])
                if ids[k] is not None:
                    st["objects"][ids[k]]["x"]=px
                    st["objects"][ids[k]]["y"]=py
                    st["objects"][ids[k]]["launched"]=True
            # The pusher does not move, so its stored phase is unchanged;
            # feedback uses the phase of the attempted stride.
            _attempt_phase(temp,st,ai,action,emit=not np.any(np.array(ENTRY_GRID,dtype=int)==11))
            if _goals_filled(temp):
                _finish(info)
            return temp.tolist(),info,st
        return a.tolist(),info,st

    h,w=a.shape
    if nx<0 or ny<0 or nx+act["w"]>w or ny+act["h"]>h:
        return a.tolist(),info,st
    destvals=temp[ny:ny+act["h"],nx:nx+act["w"]]
    if np.any(destvals==11):
        launch_result=_launch_solid(temp,act,nx,ny,action)
        if launch_result is not None:
            launched,portal_leg=launch_result
            # The selected pusher stays in place.  Reaching a shaped contour
            # emits one completion pulse in place of (not in addition to) the
            # ordinary attempted-gait report.
            completed=False
            # A landing only completes a contour for the same solid shape.
            # (A wide plus may geometrically cover an unrelated 3x3 hole.)
            solid_sigs=set(_shape_signature(p) for p in
                           _components(np.array(ENTRY_GRID,dtype=int)==11))
            for t in _target_shapes():
                if _shape_signature(t["pts"]) not in solid_sigs:
                    continue
                before=all(int(temp[py,px])==11 for px,py in t["pts"])
                after=all(int(launched[py,px])==11 for px,py in t["pts"])
                if after and not before:
                    completed=True
            _draw(launched,act,val=0)
            _paint_contacts(launched,act)
            diagonal_leg=False
            for pts in _components(temp==11):
                if any(nx<=px<nx+act["w"] and ny<=py<ny+act["h"]
                       for px,py in pts):
                    t=_matching_solid_target(pts)
                    sx=min(p[0] for p in pts); sy=min(p[1] for p in pts)
                    diagonal_leg=(t is not None and t["x"]!=sx and t["y"]!=sy)
                    break
            cand=((st["objects"][ai]["phase"] if ai is not None else 0)
                  if diagonal_leg else
                  _attempt_phase(launched,st,ai,action,emit=False))
            # A full-slot landing emits the completion pulse.  If the
            # passenger was already partly seated, its preceding physical
            # contact supplied that single docking pulse instead.
            if completed and not _solid_partly_on_target(temp):
                _mark_progress(launched)
            if ai is not None:
                st["objects"][ai]["phase"]=cand
                st["objects"][ai]["launched"]=False
            if _goals_filled(launched):
                _finish(info)
            return launched.tolist(),info,st
        # Wrong-side or occupied-target impacts are rejected but still advance
        # and report the attempted horizontal gait.
        cand=_attempt_phase(a,st,ai,action)
        if ai is not None:
            st["objects"][ai]["phase"]=cand
        return a.tolist(),info,st
    if not np.all((destvals==1)|(destvals==4)):
        return a.tolist(),info,st

    _draw(temp,act,x=nx,y=ny,val=0)

    moved=act.copy(); moved["x"]=nx; moved["y"]=ny
    touches_solid=_touches_solid(temp,moved)
    departed_solid_contact=_touches_solid(a,act) and not touches_solid
    useful_solid_contact=_useful_side_contact(temp,moved,action)
    staged_near_solid=(not touches_solid) and _staged_near_solid(temp,moved,action)
    # Entering a moved passenger's physical pocket from its exact one-stride
    # pre-stage is the second half of that alignment cue.  It reports once
    # independent of the alternating gait, while a normal head-on contact
    # remains the silent final beat before a push.
    entered_from_stage=(touches_solid and useful_solid_contact and
                        _staged_near_solid(temp,act,action))
    # Once a passenger is partly seated in its matching contour, its exact
    # one-stride pre-stage is silent and takes precedence over the otherwise
    # visible implicit-bbox entry cue.
    partial_target=_solid_partly_on_target(temp)
    partial_target_stage=(staged_near_solid and partial_target)
    # Once partly seated, the normal ready cue moves from the outer bbox edge
    # to the following physical-contact beat.
    partial_target_contact=(touches_solid and partial_target)
    solid_bbox_cue=((not touches_solid) and (not partial_target_stage) and
                    _solid_bbox_entry(a,act,moved,action))
    vacated_solid_anchor=_at_vacated_solid_anchor(temp,moved)
    _paint_contacts(temp,moved)
    # First overlap with the rim of this object's matching frame is a staging
    # cue.  It emits exactly one pulse in place of the ordinary gait report.
    frame_entry=False; frame_parked=False; frame_departed=False
    frame_lane_departed=False
    if np.any(np.array(ENTRY_GRID,dtype=int)==11):
        for f in _frames():
            if f["iw"]==act["w"] and f["ih"]==act["h"]:
                was=_rect_overlap(act["x"],act["y"],act["w"],act["h"],f)
                now=_rect_overlap(nx,ny,act["w"],act["h"],f)
                was_parked=(act["x"]==f["ix"] and act["y"]==f["iy"])
                if now and not was:
                    frame_entry=True
                if nx==f["ix"] and ny==f["iy"]:
                    frame_parked=True
                if was_parked and not frame_parked:
                    frame_departed=True
                # A matching frame also defines its approach row and column.
                # Moving off one of those exact lanes is a one-shot departure
                # cue even when the controller has not yet reached the frame.
                was_lane=(act["x"]==f["ix"] or act["y"]==f["iy"])
                now_lane=(nx==f["ix"] or ny==f["iy"])
                if was_lane and not now_lane:
                    frame_lane_departed=True
    # Rim entry/departure are one-shot staging cues.  Solid contact and exact
    # parking suppress ordinary feedback; blocked impact is reported above.
    cue=(frame_entry or frame_departed or
             (frame_lane_departed and not staged_near_solid) or
         solid_bbox_cue or departed_solid_contact or entered_from_stage or
         partial_target_contact)
    cand=_attempt_phase(temp,st,ai,action,
                        emit=(not touches_solid or useful_solid_contact) and
                             not staged_near_solid and not cue and
                             not frame_parked and not vacated_solid_anchor)
    if cue:
        _mark_progress(temp)
    if ai is not None:
        st["objects"][ai]["x"]=nx
        st["objects"][ai]["y"]=ny
        st["objects"][ai]["phase"]=cand
        st["objects"][ai]["launched"]=False
    if _goals_filled(temp):
        _finish(info)
    return temp.tolist(),info,st
