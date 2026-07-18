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
            np.all(q[:,0]==4) and
            np.all((q[:,-1]==4)|(q[:,-1]==12)|(q[:,-1]==13)) and
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
    # Both colored clock components are movable overlays.  The 3x3 token
    # initially substitutes for the composite frame's right wall; when it
    # departs, that underlying color-4 wall is exposed.
    for pts in _components((b==12)|(b==13)):
        if len(pts) in (9,36):
            for x,y in pts:
                b[y,x]=1
    for f in _frames():
        b[f["y"]:f["y"]+f["h"],f["x"]+f["w"]-1]=4
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
        return (v==14)|(v==0)|(v==5)|(v==11)|(v==12)|(v==13)
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

def _touches_base_color(o,val):
    b=_base(); H,W=b.shape
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    return ((x>0 and np.any(b[y:y+h,x-1]==val)) or
            (x+w<W and np.any(b[y:y+h,x+w]==val)) or
            (y>0 and np.any(b[y-1,x:x+w]==val)) or
            (y+h<H and np.any(b[y+h,x:x+w]==val)))

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
    xgaps=[]; ygaps=[]
    for j in range(len(anchors)):
        for k in range(j):
            dx=abs(anchors[j][0]-anchors[k][0])
            dy=abs(anchors[j][1]-anchors[k][1])
            if dx: xgaps.append(dx)
            if dy: ygaps.append(dy)
    # Macro stations are axis-specific.  A short horizontal source/target
    # offset must not fragment an unrelated longer vertical leg (or vice versa).
    if _l5_multi_gate_mode():
        # The L5 plus completes one coordinate of its diagonal route per impact.
        gaps=xgaps if action in (3,4) else ygaps
    else:
        # Earlier solid boards use one shared macro-lattice spacing across axes.
        gaps=xgaps+ygaps
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

def _l5_multi_gate_mode():
    # Later boards can start with several monochrome 6x6 colored reservoirs.
    # Their absence of color 12 distinguishes them from L4's one big + one
    # small clock, while the connected 13-components ground their identities.
    e=np.array(ENTRY_GRID,dtype=int)
    big=[p for p in _components((e==12)|(e==13)) if len(p)==36]
    return (not np.any(e==12) and len(big)>=2 and np.any(e==13))

def _l5_gate_layout_displaced(a):
    """Whether any six-cell reservoir has left its ENTRY rail station."""
    ee=np.array(ENTRY_GRID,dtype=int)
    entry={(min(x for x,y in p),min(y for x,y in p))
           for p in _components((ee==12)|(ee==13)) if len(p)==36}
    live={(min(x for x,y in p),min(y for x,y in p))
          for p in _components((a==12)|(a==13)) if len(p)==36}
    return live!=entry


def _l5_color_transfer(a,action,state=None,active_index=None):
    # Every successful arrow advances every 6x6 reservoir by one unary row.
    # The row grows inward from the horizontal color-2 support face: top-pocket
    # gates grow downward, while a gate resting above a rail grows upward.
    if action not in (1,2,3,4) or not _l5_multi_gate_mode():
        return
    # A passive elongated passenger resting flush on a charged c5 gate is
    # released one controller stride away when any arrow carries the shared
    # reservoirs.  This is not the active pusher's long recoil through a portal:
    # the unattended passenger merely detaches from the gate face, and the
    # release supplies one visible replacement beat.  L6 first exposed this when
    # V moved RIGHT while passive H below the top gate shifted (42,12)->(42,15).
    if state is not None:
        e=np.array(ENTRY_GRID,dtype=int)
        charged=[]
        for pts in _components((a==12)|(a==13)):
            if len(pts)!=36:
                continue
            xs=sorted(set(xx for xx,yy in pts))
            ys=sorted(set(yy for xx,yy in pts))
            crows=sum(all(int(a[yy,xx])==12 for xx in xs) for yy in ys)
            if crows==len(ys)-1:
                x0,y0,x1,y1=xs[0],ys[0],xs[-1]+1,ys[-1]+1
                support_above=(y0>0 and np.all(e[y0-1,x0:x1]==2))
                support_below=(y1<e.shape[0] and np.all(e[y1,x0:x1]==2))
                charged.append((x0,y0,x1,y1,support_above,support_below))
        released=False
        if charged:
            obs=_scan_objects(a)
            passive=[o for o in obs if o["val"] in (4,5)]
            for o in passive:
                rx=ry=0
                for x0,y0,x1,y1,support_above,support_below in charged:
                    xov=(o["x"]<x1 and x0<o["x"]+o["w"])
                    # A supported reservoir releases only through its opposite,
                    # open face.  Side-aligned passengers remain parked and can
                    # therefore act as cooperative rail stoppers.
                    if support_below and xov and o["y"]+o["h"]==y0:
                        ry=-3
                    elif support_above and xov and o["y"]==y1:
                        ry=3
                    if rx or ry:
                        break
                if not (rx or ry):
                    continue
                tx,ty=o["x"]+rx,o["y"]+ry
                if tx<0 or ty<0 or tx+o["w"]>a.shape[1] or ty+o["h"]>a.shape[0]:
                    continue
                others=[q for q in obs if q is not o]
                if any(_rect_overlap(tx,ty,o["w"],o["h"],q) for q in others):
                    continue
                trial=a.copy()
                _restore(trial,o)
                vals=trial[ty:ty+o["h"],tx:tx+o["w"]]
                if not np.all((vals==1)|(vals==4)):
                    continue
                a[:,:]=trial
                _draw(a,o,x=tx,y=ty,val=o["val"])
                oi=_state_index(state,o)
                if oi is not None:
                    state["objects"][oi]["x"]=tx
                    state["objects"][oi]["y"]=ty
                    # A gate carry is a real passive launch: when it is later
                    # selected it retains the phase it carried off the face,
                    # rather than being re-planted from checkerboard parity.
                    state["objects"][oi]["launched"]=True
                released=True
            if released:
                _mark_progress(a)
    e=np.array(ENTRY_GRID,dtype=int)
    for pts in _components((a==12)|(a==13)):
        if len(pts)!=36:
            continue
        xs=sorted(set(xx for xx,yy in pts))
        ys=sorted(set(yy for xx,yy in pts))
        if len(xs)!=6 or len(ys)!=6:
            continue
        x0,x1=xs[0],xs[-1]; y0,y1=ys[0],ys[-1]
        top=(y0>0 and np.all(e[y0-1,x0:x1+1]==2))
        bottom=(y1+1<e.shape[0] and np.all(e[y1+1,x0:x1+1]==2))
        # Once a gate has moved away from its entry pocket, its existing unary
        # edge still reveals orientation.  Location fallback matches it to the
        # nearest entry gate and inherits that gate's supported face.
        if not top and not bottom:
            ctop=all(int(a[y0,x])==12 for x in xs)
            cbot=all(int(a[y1,x])==12 for x in xs)
            if ctop!=cbot:
                top=ctop; bottom=cbot
            else:
                entries=[q for q in _components((e==12)|(e==13)) if len(q)==36]
                if entries:
                    q=min(entries,key=lambda z:
                          abs(min(xx for xx,yy in z)-x0)+abs(min(yy for xx,yy in z)-y0))
                    qx0=min(xx for xx,yy in q); qx1=max(xx for xx,yy in q)
                    qy0=min(yy for xx,yy in q); qy1=max(yy for xx,yy in q)
                    top=(qy0>0 and np.all(e[qy0-1,qx0:qx1+1]==2))
                    bottom=(qy1+1<e.shape[0] and np.all(e[qy1+1,qx0:qx1+1]==2))
        if not top and not bottom:
            continue
        crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
        newrows=(crows+1)%len(ys)
        for x,y in pts:
            a[y,x]=13
        rows=ys[:newrows] if top else ys[len(ys)-newrows:] if newrows else []
        for y in rows:
            for x in xs:
                a[y,x]=12

def _touches_l5_gate(a,o):
    if not _l5_multi_gate_mode():
        return False
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]; H,W=a.shape
    return ((x>0 and np.any((a[y:y+h,x-1]==12)|(a[y:y+h,x-1]==13))) or
            (x+w<W and np.any((a[y:y+h,x+w]==12)|(a[y:y+h,x+w]==13))) or
            (y>0 and np.any((a[y-1,x:x+w]==12)|(a[y-1,x:x+w]==13))) or
            (y+h<H and np.any((a[y+h,x:x+w]==12)|(a[y+h,x:x+w]==13))))

def _l5_gate_will_wrap(a,nx,ny,w,h):
    # A collision is charged only when the struck six-row reservoir is at c5.
    # (The L5 reservoirs normally remain synchronized, but grounding this in
    # the actually intersected component keeps the mechanic object-local.)
    if not _l5_multi_gate_mode():
        return False
    for pts in _components((a==12)|(a==13)):
        if len(pts)!=36:
            continue
        if not any(nx<=x<nx+w and ny<=y<ny+h for x,y in pts):
            continue
        xs=sorted(set(x for x,y in pts)); ys=sorted(set(y for x,y in pts))
        crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
        return crows==len(ys)-1
    return False

def _l5_charged_normal_shell_hold(a,o,nx,ny,action):
    # A charged six-row gate also projects a normal axial staging shell.  When
    # an elongated controller tries to enter the one-gate-span shell from one
    # lattice step farther out, the c5 carry is spent in place; unlike a
    # tangential shell entry it does not spring through the separator.  The
    # stationary replacement is silent and preserves the planted foot.
    if not _l5_multi_gate_mode() or o["w"]==o["h"]:
        return False
    for pts in _components((a==12)|(a==13)):
        if len(pts)!=36:
            continue
        xs=sorted(set(x for x,y in pts)); ys=sorted(set(y for x,y in pts))
        crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
        if crows!=len(ys)-1:
            continue
        x0,x1=xs[0],xs[-1]+1; y0,y1=ys[0],ys[-1]+1
        gw,gh=x1-x0,y1-y0
        xov=(o["x"]<x1 and x0<o["x"]+o["w"])
        yov=(o["y"]<y1 and y0<o["y"]+o["h"])
        if action==1 and xov and o["y"]-y1==gh+3 and ny-y1==gh:
            return True
        if (action==2 and xov and y0-(o["y"]+o["h"])==gh+3 and
            y0-(ny+o["h"])==gh):
            return True
        if action==3 and yov and o["x"]-x1==gw+3 and nx-x1==gw:
            return True
        if (action==4 and yov and x0-(o["x"]+o["w"])==gw+3 and
            x0-(nx+o["w"])==gw):
            return True
    return False


def _l5_uncharged_normal_shell_entry(a,old,new,action):
    # After the charged normal-shell hold wraps c5 to c0, repeating the same
    # approach enters that one-gate-span shell as a silent phase-preserving stage.
    if not _l5_multi_gate_mode() or old["w"]==old["h"]:
        return False
    for pts in _components((a==12)|(a==13)):
        if len(pts)!=36:
            continue
        xs=sorted(set(x for x,y in pts)); ys=sorted(set(y for x,y in pts))
        crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
        if crows!=0:
            continue
        x0,x1=xs[0],xs[-1]+1; y0,y1=ys[0],ys[-1]+1
        gw,gh=x1-x0,y1-y0
        xov=(old["x"]<x1 and x0<old["x"]+old["w"])
        yov=(old["y"]<y1 and y0<old["y"]+old["h"])
        if (action==1 and xov and old["y"]-y1==gh+3 and
            new["y"]-y1==gh):
            return True
        if (action==2 and xov and y0-(old["y"]+old["h"])==gh+3 and
            y0-(new["y"]+new["h"])==gh):
            return True
        if (action==3 and yov and old["x"]-x1==gw+3 and
            new["x"]-x1==gw):
            return True
        if (action==4 and yov and x0-(old["x"]+old["w"])==gw+3 and
            x0-(new["x"]+new["w"])==gw):
            return True
    return False


def _l5_hit_supported_above(a,nx,ny,w,h):
    # Return the support orientation of the struck 6x6 gate.  Entry geometry
    # grounds orientation even after its unary colors have advanced.
    e=np.array(ENTRY_GRID,dtype=int)
    for pts in _components((a==12)|(a==13)):
        if len(pts)!=36 or not any(nx<=x<nx+w and ny<=y<ny+h for x,y in pts):
            continue
        xs=sorted(set(x for x,y in pts)); y0=min(y for x,y in pts)
        return y0>0 and np.all(e[y0-1,xs[0]:xs[-1]+1]==2)
    return False

def _l5_recoil_destination(o,action):
    # A charged gate is a spring.  Its pusher is sent backward through the
    # first separator plane behind it and lands flush on that plane's far face.
    # Usually the center ray itself is color 15.  On the final two-axis board,
    # however, a three-cell doorway can cut through the separator; the spring
    # still crosses that locally dense color-2/15 plane and lands just beyond
    # the doorway rather than ignoring it for a more distant color-15 band.
    b=_base(); H,W=b.shape
    x,y,w,h=o["x"],o["y"],o["w"],o["h"]
    vx,hy=_separator_axes()
    if vx and hy:
        span=max(w,h)
        cx=x+w//2; cy=y+h//2
        def dense_row(yy):
            lo=max(0,cx-span); hi=min(W,cx+span+1)
            return int(np.sum((b[yy,lo:hi]==2)|(b[yy,lo:hi]==15)))>=span
        def dense_col(xx):
            lo=max(0,cy-span); hi=min(H,cy+span+1)
            return int(np.sum((b[lo:hi,xx]==2)|(b[lo:hi,xx]==15)))>=span
        if action==1:                  # pushed up -> recoil down
            k=y+h
            while k<H and not dense_row(k): k+=1
            if k<H:
                while k<H and dense_row(k): k+=1
                if k<H and int(b[k,cx]) in (1,4):
                    return (x,k)
        elif action==2:                # pushed down -> recoil up
            k=y-1
            while k>=0 and not dense_row(k): k-=1
            if k>=0:
                while k>=0 and dense_row(k): k-=1
                if k>=0 and int(b[k,cx]) in (1,4):
                    return (x,k-h+1)
        elif action==3:                # pushed left -> recoil right
            k=x+w
            while k<W and not dense_col(k): k+=1
            if k<W:
                while k<W and dense_col(k): k+=1
                if k<W and int(b[cy,k]) in (1,4):
                    return (k,y)
        elif action==4:                # pushed right -> recoil left
            k=x-1
            while k>=0 and not dense_col(k): k-=1
            if k>=0:
                while k>=0 and dense_col(k): k-=1
                if k>=0 and int(b[cy,k]) in (1,4):
                    return (k-w+1,y)
    if action==2:                       # pushed down -> recoil up
        k=y-1; cx=x+w//2
        while k>=0 and int(b[k,cx]) in (1,4): k-=1
        if k<0 or int(b[k,cx])!=15: return None
        while k>=0 and int(b[k,cx])==15: k-=1
        return (x,k-h+1) if k>=0 and int(b[k,cx]) in (1,4) else None
    if action==1:                       # pushed up -> recoil down
        k=y+h; cx=x+w//2
        while k<H and int(b[k,cx]) in (1,4): k+=1
        if k>=H or int(b[k,cx])!=15: return None
        while k<H and int(b[k,cx])==15: k+=1
        return (x,k) if k<H and int(b[k,cx]) in (1,4) else None
    if action==4:                       # pushed right -> recoil left
        k=x-1; cy=y+h//2
        while k>=0 and int(b[cy,k]) in (1,4): k-=1
        if k<0 or int(b[cy,k])!=15: return None
        while k>=0 and int(b[cy,k])==15: k-=1
        return (k-w+1,y) if k>=0 and int(b[cy,k]) in (1,4) else None
    if action==3:                       # pushed left -> recoil right
        k=x+w; cy=y+h//2
        while k<W and int(b[cy,k]) in (1,4): k+=1
        if k>=W or int(b[cy,k])!=15: return None
        while k<W and int(b[cy,k])==15: k+=1
        return (k,y) if k<W and int(b[cy,k]) in (1,4) else None
    return None

def _l5_slide_gate_on_support(a,act,nx,ny,action,state=None):
    # A horizontal impact on a six-row gate slides that gate one station along
    # its horizontal color-2 support.  Station spacing is the span of the paired
    # six-row gate assembly elsewhere in ENTRY_GRID (gate + divider + gate),
    # rather than a hard-coded board distance.
    if action not in (3,4) or not _l5_multi_gate_mode():
        return None
    hit=None
    for p in _components((a==12)|(a==13)):
        if len(p)==36 and any(nx<=xx<nx+act["w"] and
                             ny<=yy<ny+act["h"] for xx,yy in p):
            hit=p
            break
    if hit is None:
        return None
    xs=[xx for xx,yy in hit]; ys=[yy for xx,yy in hit]
    x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
    bb=_base()
    supported=((y0>0 and np.all(bb[y0-1,x0:x1]==2)) or
               (y1<bb.shape[0] and np.all(bb[y1,x0:x1]==2)))
    if not supported:
        return None
    ee=np.array(ENTRY_GRID,dtype=int)
    gates=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    spans=[]
    for j in range(len(gates)):
        ax=[xx for xx,yy in gates[j]]; ay=[yy for xx,yy in gates[j]]
        for k in range(j):
            bx=[xx for xx,yy in gates[k]]; by=[yy for xx,yy in gates[k]]
            if min(ay)==min(by):
                spans.append(max(max(ax),max(bx))-min(min(ax),min(bx))+1)
    # When ENTRY shows paired gates on one rail, their total span gives
    # the station pitch directly.  The final board has only one gate per rail;
    # the same macro-cell is two gate widths plus one controller stride.
    stride=(min(spans) if spans else
            2*(x1-x0)+max(abs(v[0]) for v in DIRS.values()))
    tx=x0+(-stride if action==3 else stride)
    if tx<0 or tx+(x1-x0)>a.shape[1]:
        return None
    vals=np.array([[int(a[y,x]) for x in range(x0,x1)]
                   for y in range(y0,y1)],dtype=int)
    # A station must be static floor and remain supported by the rail.  On the
    # final cooperative board it may contain one passive elongated passenger:
    # the sliding 6x6 gate extrudes that passenger flush beyond its far face.
    target=a[y0:y1,tx:tx+(x1-x0)]
    base_target=bb[y0:y1,tx:tx+(x1-x0)]
    supported_target=((y0>0 and np.all(bb[y0-1,tx:tx+(x1-x0)]==2)) or
                      (y1<bb.shape[0] and
                       np.all(bb[y1,tx:tx+(x1-x0)]==2)))
    if (target.shape!=vals.shape or not np.all(base_target==1) or
        not supported_target):
        return None
    obs=_scan_objects(a)
    blockers=[o for o in obs if o["val"] in (4,5) and
              _rect_overlap(tx,y0,x1-x0,y1-y0,o)]
    work=a.copy(); pushed=[]
    if blockers:
        if (CURRENT_LEVEL!=6 or len(blockers)!=1 or
            blockers[0]["w"]==blockers[0]["h"]):
            return None
        for o in blockers:
            _restore(work,o)
        if not np.all(work[y0:y1,tx:tx+(x1-x0)]==1):
            return None
        for o in blockers:
            px=(tx+(x1-x0) if action==4 else tx-o["w"])
            py=o["y"]
            if (px<0 or py<0 or px+o["w"]>a.shape[1] or
                py+o["h"]>a.shape[0] or
                not np.all(work[py:py+o["h"],px:px+o["w"]]==1)):
                return None
            pushed.append((o,px,py))
    elif not np.all(target==1):
        return None
    out=work
    out[y0:y1,x0:x1]=bb[y0:y1,x0:x1]
    out[y0:y1,tx:tx+(x1-x0)]=vals
    for o,px,py in pushed:
        _draw(out,o,x=px,y=py,val=o["val"])
        if state is not None:
            oi=_state_index(state,o)
            if oi is not None:
                state["objects"][oi]["x"]=px
                state["objects"][oi]["y"]=py
                state["objects"][oi]["launched"]=True
    # The stationary pusher's formerly black contact face reopens.
    _draw(out,act,val=0)
    _paint_contacts(out,act)
    return out,bool(pushed)

def _at_vacated_l5_gate_anchor(a,o):
    # The gate's original ENTRY station remains a silent phase-preserving
    # controller alignment datum after the gate moves.  This includes either
    # exact half/full occupancy of its vacated 6x6 footprint or first orthogonal
    # face contact with that footprint; intermediate rail stations are floor.
    if not _l5_multi_gate_mode():
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    entry=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    gates=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    for p in gates:
        cx=min(xx for xx,yy in p); cy=min(yy for xx,yy in p)
        same=[q for q in entry if min(yy for xx,yy in q)==cy]
        if not same:
            continue
        q=min(same,key=lambda z:abs(min(xx for xx,yy in z)-cx))
        xs=[xx for xx,yy in q]; ys=[yy for xx,yy in q]
        ex0,ex1=min(xs),max(xs)+1; ey0,ey1=min(ys),max(ys)+1
        if cx==ex0:
            continue
        exact=(o["x"]==ex0 and o["y"]==ey0)
        inside=(ex0<=o["x"] and o["x"]+o["w"]<=ex1 and
                ey0<=o["y"] and o["y"]+o["h"]<=ey1)
        hface=((o["y"]+o["h"]==ey0 or ey1==o["y"]) and
               o["x"]<ex1 and ex0<o["x"]+o["w"])
        vface=((o["x"]+o["w"]==ex0 or ex1==o["x"]) and
               o["y"]<ey1 and ey0<o["y"]+o["h"])
        # Earlier rail boards confirmed only the exact vacated station.  The
        # final cooperative board additionally projects that datum to its faces
        # and elongated half-slots.
        if exact or (CURRENT_LEVEL==6 and (inside or hface or vface)):
            return True
    return False

def _entered_vacated_l5_gate_slot(a,old,new):
    # On the final cooperative board, completing face contact by moving fully
    # into either elongated half-slot of a moved gate's ENTRY footprint is a
    # visible docking cue.  The footprint itself remains an elastic anchor.
    if CURRENT_LEVEL!=6 or not _l5_multi_gate_mode():
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    entries=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    live=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    live_pos={(min(xx for xx,yy in p),min(yy for xx,yy in p)) for p in live}
    for p in entries:
        xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
        x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
        if (x0,y0) in live_pos:
            continue
        def inside(o):
            return (x0<=o["x"] and o["x"]+o["w"]<=x1 and
                    y0<=o["y"] and o["y"]+o["h"]<=y1)
        if inside(new) and not inside(old):
            return True
    return False

def _vacated_l5_gate_c2_projection_entry(a,old,new,action):
    # A moved top-rail gate leaves its supported ENTRY station clocked by the
    # live reservoir.  At c2, tangential entry from an outer diagonal projection
    # into the first half of its unsupported/open face is the visible half-charge
    # completion beat, even though the colored 6x6 body is now elsewhere.
    if (CURRENT_LEVEL!=6 or action not in (3,4) or
        old["w"]<=old["h"] or not _l5_multi_gate_mode()):
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    entries=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    live=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    for p in entries:
        xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
        x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
        same=[q for q in live if min(yy for xx,yy in q)==y0]
        if not same:
            continue
        q=min(same,key=lambda z:abs(min(xx for xx,yy in z)-x0))
        qx0=min(xx for xx,yy in q)
        if qx0==x0:
            continue
        qxs=sorted(set(xx for xx,yy in q))
        qys=sorted(set(yy for xx,yy in q))
        crows=sum(all(int(a[yy,xx])==12 for xx in qxs) for yy in qys)
        if crows!=len(qys)//2-1:
            continue
        support_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
        support_below=(y1<ee.shape[0] and np.all(ee[y1,x0:x1]==2))
        open_projection=(
            (support_above and old["y"]==y1+3 and new["y"]==old["y"]) or
            (support_below and old["y"]+old["h"]==y0-3 and
             new["y"]==old["y"]))
        from_side=(
            (action==3 and old["x"]==x1 and new["x"]==x1-3) or
            (action==4 and old["x"]+old["w"]==x0 and
             new["x"]+new["w"]==x0+3))
        if open_projection and from_side:
            return True
    return False

def _at_vacated_l5_gate_open_corner_route(a,old,new,action):
    # A moved rail gate leaves its ENTRY station as an elastic routing datum.
    # Along either side edge, the open-face corner and the following one-stride
    # projection are silent phase-preserving anchors.
    if action not in (1,2) or not _l5_multi_gate_mode():
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    entries=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    live=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    live_pos={(min(xx for xx,yy in p),min(yy for xx,yy in p)) for p in live}
    for p in entries:
        xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
        x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
        if (x0,y0) in live_pos:
            continue
        side=((old["x"]==x1 and new["x"]==x1) or
              (old["x"]+old["w"]==x0 and new["x"]+new["w"]==x0))
        if not side:
            continue
        support_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
        support_below=(y1<ee.shape[0] and np.all(ee[y1,x0:x1]==2))
        def on_route(o):
            overlap=(o["y"]<y1 and y0<o["y"]+o["h"])
            below=(o["y"] in (y1,y1+3))
            above=(o["y"]+o["h"] in (y0,y0-3))
            return overlap or (support_above and below) or (support_below and above)
        if on_route(old) and on_route(new):
            return True
    return False

def _departed_vacated_l5_gate_open_corner_route(a,old,new,action):
    # Leaving the outward side of a vacated open-corner route is its visible
    # complementary replacement and preserves the planted foot.
    if action not in (3,4) or not _l5_multi_gate_mode():
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    vx,hy=_separator_axes()
    if not (np.any(ee==11) and vx and hy):
        return False
    entries=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    live=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    live_pos={(min(xx for xx,yy in p),min(yy for xx,yy in p)) for p in live}
    for p in entries:
        xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
        x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
        if (x0,y0) in live_pos:
            continue
        support_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
        support_below=(y1<ee.shape[0] and np.all(ee[y1,x0:x1]==2))
        def open_level(o):
            overlap=(o["y"]<y1 and y0<o["y"]+o["h"])
            below=(o["y"] in (y1,y1+3))
            above=(o["y"]+o["h"] in (y0,y0-3))
            return overlap or (support_above and below) or (support_below and above)
        outward=((action==4 and old["x"]==x1 and new["x"]==x1+3) or
                 (action==3 and old["x"]+old["w"]==x0 and
                  new["x"]+new["w"]==x0-3))
        if outward and open_level(old) and open_level(new):
            return True
    return False

def _entered_vacated_l5_gate_outer_corner(a,old,new,action):
    # One stride beyond both the side and open face of a vacated ENTRY gate is
    # its outer diagonal shell.  Re-entering that shell from farther along the
    # open-face normal is a silent elastic alignment.
    if action not in (1,2) or not _l5_multi_gate_mode():
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    vx,hy=_separator_axes()
    if not (np.any(ee==11) and vx and hy):
        return False
    entries=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    live=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    live_pos={(min(xx for xx,yy in p),min(yy for xx,yy in p)) for p in live}
    for p in entries:
        xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
        x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
        if (x0,y0) in live_pos:
            continue
        outer_side=((new["x"]==x1+3 and old["x"]==x1+3) or
                    (new["x"]+new["w"]==x0-3 and
                     old["x"]+old["w"]==x0-3))
        if not outer_side:
            continue
        support_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
        support_below=(y1<ee.shape[0] and np.all(ee[y1,x0:x1]==2))
        if (support_above and action==1 and
            old["y"]==y1+6 and new["y"]==y1+3):
            return True
        if (support_below and action==2 and
            old["y"]+old["h"]==y0-6 and
            new["y"]+new["h"]==y0-3):
            return True
    return False

def _l5_terminal_gate_wrap(a,o=None):
    # Once a rail gate has reached its far terminal station, its c5->c0 carry is
    # a silent routing replacement only along that gate's own horizontal lane.
    # A remote controller elsewhere merely takes its ordinary gait beat.
    if not _l5_multi_gate_mode():
        return False
    ee=np.array(ENTRY_GRID,dtype=int)
    entry=[p for p in _components((ee==12)|(ee==13)) if len(p)==36]
    gates=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    spans=[]
    for j in range(len(entry)):
        ax=[xx for xx,yy in entry[j]]; ay=[yy for xx,yy in entry[j]]
        for k in range(j):
            bx=[xx for xx,yy in entry[k]]; by=[yy for xx,yy in entry[k]]
            if min(ay)==min(by):
                spans.append(max(max(ax),max(bx))-min(min(ax),min(bx))+1)
    if not spans:
        return False
    stride=min(spans)
    for p in gates:
        xs=sorted(set(xx for xx,yy in p)); ys=sorted(set(yy for xx,yy in p))
        crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
        if crows!=len(ys)-1:
            continue
        cx=min(xs); cy=min(ys)
        exs=[min(xx for xx,yy in q) for q in entry
             if min(yy for xx,yy in q)==cy]
        if exs and abs(cx-min(exs,key=lambda x:abs(x-cx)))>=2*stride:
            if o is None or (o["y"]<cy+len(ys) and cy<o["y"]+o["h"]):
                return True
    return False

def _l4_color_transfer(a,action):
    # Each successful arrow advances two visible unary phase dials:
    # the next all-13 row of the 6x6 reservoir becomes 12, while the
    # indicator's right-aligned 12-suffix grows modulo its three columns.
    # The colors themselves carry the clock state, so no hidden state is needed.
    if action not in (1,2,3,4):
        return
    e=np.array(ENTRY_GRID,dtype=int)
    if not (np.any(e==12) and np.any(e==13)):
        return
    cs=_components((a==12)|(a==13))
    big=[p for p in cs if len(p)==36]
    small=[p for p in cs if len(p)==9]
    if len(big)!=1 or len(small)!=1:
        return
    pts=big[0]
    xs=sorted(set(x for x,y in pts)); ys=sorted(set(y for x,y in pts))
    crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
    newrows=(crows+1)%len(ys)
    for x,y in pts:
        a[y,x]=13
    for y in ys[:newrows]:
        for x in xs:
            a[y,x]=12
    if newrows==0:
        # The carry is a visible beat only while the gate is loaded at its
        # entry anchor.  After launch it still resets the dial, but silently.
        entry_big=[p for p in _components((e==12)|(e==13)) if len(p)==36]
        loaded=(len(entry_big)==1 and
                (min(x for x,y in pts),min(y for x,y in pts)) ==
                (min(x for x,y in entry_big[0]),min(y for x,y in entry_big[0])))
        if loaded:
            _mark_progress(a)
    sp=small[0]
    sxs=sorted(set(x for x,y in sp))
    sys=sorted(set(y for x,y in sp))
    ccols=sum(all(int(a[y,x])==12 for y in sys) for x in sxs)
    newcols=(ccols+1)%len(sxs)
    for x,y in sp:
        a[y,x]=13
    if newcols:
        for x in sxs[-newcols:]:
            for y in sys:
                a[y,x]=12

def _l4_dial_will_wrap(a):
    e=np.array(ENTRY_GRID,dtype=int)
    if not (np.any(e==12) and np.any(e==13)):
        return False
    big=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    if len(big)!=1:
        return False
    pts=big[0]
    xs=sorted(set(x for x,y in pts)); ys=sorted(set(y for x,y in pts))
    crows=sum(all(int(a[y,x])==12 for x in xs) for y in ys)
    return crows==len(ys)-1

def _l4_token_dial_will_wrap(a):
    e=np.array(ENTRY_GRID,dtype=int)
    if not (np.any(e==12) and np.any(e==13)):
        return False
    small=[p for p in _components((a==12)|(a==13)) if len(p)==9]
    if len(small)!=1:
        return False
    pts=small[0]
    xs=sorted(set(x for x,y in pts)); ys=sorted(set(y for x,y in pts))
    ccols=sum(all(int(a[y,x])==12 for y in ys) for x in xs)
    return ccols==len(xs)-1


def _l4_clock_will_wrap(a):
    e=np.array(ENTRY_GRID,dtype=int)
    if not _l4_dial_will_wrap(a):
        return False
    big=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    pts=big[0]
    # A dial carry consumes the arrow only while the colored gate is still
    # loaded at its entry anchor.  Once the gate has been launched through its
    # separator, the same visible wrap remains a progress beat but no longer
    # arrests the freely moving controller.
    entry_big=[p for p in _components((e==12)|(e==13)) if len(p)==36]
    if len(entry_big)!=1:
        return False
    return (min(x for x,y in pts),min(y for x,y in pts)) == (
            min(x for x,y in entry_big[0]),min(y for x,y in entry_big[0]))

def _launch_l4_gate(a,act,nx,ny,action):
    e=np.array(ENTRY_GRID,dtype=int)
    if not (np.any(e==12) and np.any(e==13)):
        return None
    gates=[p for p in _components((a==12)|(a==13)) if len(p)==36]
    hit=[p for p in gates if any(nx<=x<nx+act["w"] and
                                  ny<=y<ny+act["h"] for x,y in p)]
    if len(hit)!=1:
        return None
    pts=hit[0]
    xs=[x for x,y in pts]; ys=[y for x,y in pts]
    sx,sy=min(xs),min(ys); sw=max(xs)-sx+1; sh=max(ys)-sy+1
    b=_base(); H,W=a.shape
    dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
    tx,ty=sx,sy
    if action==1:
        k=sy-1; cx=sx+sw//2
        while k>=0 and int(b[k,cx])!=15: k-=1
        if k<0: return None
        while k>=0 and int(b[k,cx])==15: k-=1
        ty=(k+1)-sh
    elif action==2:
        k=sy+sh; cx=sx+sw//2
        while k<H and int(b[k,cx])!=15: k+=1
        if k>=H: return None
        while k<H and int(b[k,cx])==15: k+=1
        ty=k
    elif action==3:
        k=sx-1; cy=sy+sh//2
        while k>=0 and int(b[cy,k])!=15: k-=1
        if k<0: return None
        while k>=0 and int(b[cy,k])==15: k-=1
        tx=(k+1)-sw
    else:
        k=sx+sw; cy=sy+sh//2
        while k<W and int(b[cy,k])!=15: k+=1
        if k>=W: return None
        while k<W and int(b[cy,k])==15: k+=1
        tx=k
    if tx<0 or ty<0 or tx+sw>W or ty+sh>H:
        return None
    out=a.copy()
    vals={(x-sx,y-sy):int(a[y,x]) for x,y in pts}
    for x,y in pts:
        out[y,x]=b[y,x]
    for (rx,ry),v in vals.items():
        if int(b[ty+ry,tx+rx]) not in (1,4):
            return None
        out[ty+ry,tx+rx]=v
    _restore(out,act)
    _draw(out,act,val=0)
    _paint_contacts(out,act)
    _l4_color_transfer(out,action)
    _mark_progress(out)
    return out

def _launch_l4_token(a,act,nx,ny,action):
    # The 3x3 colored token advances through three portal staging slots:
    # one token-width before the near face, flush with that face, then through
    # to the far face.  Static portal geometry and token size define the slots.
    e=np.array(ENTRY_GRID,dtype=int)
    if not (np.any(e==12) and np.any(e==13)):
        return None
    tokens=[p for p in _components((a==12)|(a==13)) if len(p)==9]
    hit=[p for p in tokens if any(nx<=x<nx+act["w"] and
                                  ny<=y<ny+act["h"] for x,y in p)]
    if len(hit)!=1:
        return None
    pts=hit[0]
    xs=[x for x,y in pts]; ys=[y for x,y in pts]
    sx,sy=min(xs),min(ys); sw=max(xs)-sx+1; sh=max(ys)-sy+1
    entry_tokens=[p for p in _components((e==12)|(e==13)) if len(p)==9]
    source_loaded=(len(entry_tokens)==1 and
                   (sx,sy)==(min(x for x,y in entry_tokens[0]),
                             min(y for x,y in entry_tokens[0])))
    # Only extraction from the composite source frame uses the remote staging
    # slot.  Once detached, every impact traverses the next connected guide
    # directly to its far face, even when the token begins several strides away.
    sxs=sorted(set(xs)); sys=sorted(set(ys))
    ccols=sum(all(int(a[y,x])==12 for y in sys) for x in sxs)
    token_clock_wrap=(ccols==len(sxs)-1)
    b=_base(); H,W=a.shape
    tx,ty=sx,sy
    portals=_components(b==15)
    def portal_at(px,py):
        for q in portals:
            if (px,py) in q:
                return q
        return None
    # A connected color-15 guide is one portal even when a ray intersects two
    # separated walls of a U-shape.  A remote token first moves to one-width
    # pre-stage; the next impact crosses the whole connected guide component.
    if action==1:
        k=sy-1; cx=sx+sw//2
        while k>=0 and int(b[k,cx])!=15: k-=1
        if k<0: return None
        q=portal_at(cx,k)
        if q is None: return None
        ymin=min(yy for xx,yy in q); ymax=max(yy for xx,yy in q)
        flush=ymax+1; stage=flush+sh; far=ymin-sh
        if source_loaded and sy>stage:
            ty=stage
        elif sy>far:
            ty=far
        else:
            return None
    elif action==2:
        k=sy+sh; cx=sx+sw//2
        while k<H and int(b[k,cx])!=15: k+=1
        if k>=H: return None
        q=portal_at(cx,k)
        if q is None: return None
        ymin=min(yy for xx,yy in q); ymax=max(yy for xx,yy in q)
        flush=ymin-sh; stage=flush-sh; far=ymax+1
        if source_loaded and sy<stage:
            ty=stage
        elif sy<far:
            ty=far
        else:
            return None
    elif action==3:
        k=sx-1; cy=sy+sh//2
        while k>=0 and int(b[cy,k])!=15: k-=1
        if k<0: return None
        q=portal_at(k,cy)
        if q is None: return None
        xmin=min(xx for xx,yy in q); xmax=max(xx for xx,yy in q)
        flush=xmax+1; stage=flush+sw; far=xmin-sw
        if source_loaded and sx>stage:
            tx=stage
        elif sx>far:
            tx=far
        else:
            return None
    else:
        k=sx+sw; cy=sy+sh//2
        while k<W and int(b[cy,k])!=15: k+=1
        if k>=W: return None
        q=portal_at(k,cy)
        if q is None: return None
        xmin=min(xx for xx,yy in q); xmax=max(xx for xx,yy in q)
        flush=xmin-sw; stage=flush-sw; far=xmax+1
        if source_loaded and sx<stage:
            tx=stage
        elif sx<far:
            tx=far
        else:
            return None
    if tx<0 or ty<0 or tx+sw>W or ty+sh>H:
        return None
    out=a.copy()
    vals={(x-sx,y-sy):int(a[y,x]) for x,y in pts}
    for x,y in pts:
        out[y,x]=b[y,x]
    for (rx,ry),v in vals.items():
        if int(b[ty+ry,tx+rx]) not in (1,4):
            return None
        out[ty+ry,tx+rx]=v
    _restore(out,act)
    _draw(out,act,val=0)
    _paint_contacts(out,act)
    _l4_color_transfer(out,action)
    # A token-indicator carry (two colored columns back to zero) consumes the
    # launch cue; other token launches report one progress beat.
    if not token_clock_wrap:
        _mark_progress(out)
    return out

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

def _at_separator_open_end_membrane(o):
    # On the final two-axis solid board, the unbounded end of a long
    # three-cell separator plane is an elastic one-sided membrane.  An
    # elongated controller whose core occupies the floor immediately beyond
    # that end is aligned with the membrane even though its full footprint is
    # not on separator terrain.  This same alignment makes both travel into
    # the slot and a selection handoff silent.  Only the observed horizontal
    # open-end geometry is included; short gate faces are not membranes.
    if (o is None or o["w"]==o["h"] or
        not np.any(np.array(ENTRY_GRID,dtype=int)==11)):
        return False
    vx,hy=_separator_axes()
    if not (vx and hy):
        return False
    b=_base(); h,w=b.shape
    sep=np.isin(b,(2,15))
    ox,ow=o["x"],o["w"]
    if not (0<ox and ox+ow<w):
        return False
    for sy in range(h-2):
        if not np.all(b[sy:sy+3,ox:ox+ow]==1):
            continue
        left=bool(np.all(sep[sy:sy+3,ox-1]))
        right=bool(np.all(sep[sy:sy+3,ox+ow]))
        dense=min(int(np.sum(sep[yy])) for yy in range(sy,sy+3))
        if left==right or dense<3*max(o["w"],o["h"]):
            continue
        c0=o["y"]+o["cy"]
        if c0<sy+3 and sy<c0+o["ch"]:
            return True
    return False

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
    # On the two-axis solid board, a lone elongated passenger can also be
    # launched along the matching target's long-axis projection while its lane
    # is exactly two controller strides to one side.  The target then catches
    # it on the interior row/column (a lateral approach stage), rather than at
    # the ordinary mirror point.  From there two perpendicular strides park it.
    vx_sep,hy_sep=_separator_axes()
    final_elongated=(len(train)==1 and
                     np.any(np.array(ENTRY_GRID,dtype=int)==11) and
                     vx_sep and hy_sep and lead["w"]!=lead["h"])
    if final_elongated:
        for f in _frames():
            if f["iw"]!=lead["w"] or f["ih"]!=lead["h"]:
                continue
            if action==3:
                side=f["x"]+f["w"]-1 < s/2
                projected=(abs(lead["y"]-f["iy"])==2*lead["h"])
            elif action==4:
                side=f["x"] > s/2
                projected=(abs(lead["y"]-f["iy"])==2*lead["h"])
            elif action==1:
                side=f["y"]+f["h"]-1 < s/2
                projected=(abs(lead["x"]-f["ix"])==2*lead["w"])
            else:
                side=f["y"] > s/2
                projected=(abs(lead["x"]-f["ix"])==2*lead["w"])
            if side and projected:
                if action in (3,4):
                    return [(lead,f["ix"],lead["y"])]
                return [(lead,lead["x"],f["iy"])]
    if not frames:
        # A lone projectile without a frame still mirrors through the portal.
        if len(train)==1:
            p=_reflect_object(hit,action)
            return [(hit,p[0],p[1])] if p is not None else None
        return None
    # On the two-axis solid board a lone elongated passenger launched toward
    # its own frame is delivered to the exact one-stride docking stage, not
    # merely packed outside the rim.  One more arrow then reaches the interior.
    vx_sep,hy_sep=_separator_axes()
    if (len(train)==1 and np.any(np.array(ENTRY_GRID,dtype=int)==11) and
        vx_sep and hy_sep and lead["w"]!=lead["h"]):
        matching=[f for f in frames if f["iw"]==lead["w"] and f["ih"]==lead["h"]]
        if matching:
            if action==3: f=max(matching,key=lambda q:q["x"])
            elif action==4: f=min(matching,key=lambda q:q["x"])
            elif action==1: f=max(matching,key=lambda q:q["y"])
            else: f=min(matching,key=lambda q:q["y"])
            dx,dy=DIRS[action]
            return [(lead,f["ix"]-dx,f["iy"]-dy)]
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
    solid_hy=(np.any(np.array(entry_grid,dtype=int)==11) and _separator_axes()[1])
    return {"l5_half_face_armed":False,
            "objects":[{"x":o["x"],"y":o["y"],"w":o["w"],"h":o["h"],
                         "val":o["val"],
                         # On a two-axis solid board the planted foot is the
                         # checkerboard parity of the controller's entry lattice
                         # cell; it is not a board-wide constant.
                         "phase":(((o["x"]//3)+(o["y"]//3))%2
                                  if solid_hy and o["val"]==0 else 0),
                         "launched":False} for o in obs]}

def _copy_state(state):
    if state is None or "objects" not in state:
        return init_state(ENTRY_GRID)
    return {"l5_half_face_armed":bool(state.get("l5_half_face_armed",False)),
            "objects":[dict(o) for o in state["objects"]]}

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
        if hy:
            # A horizontal separator couples both movement axes into one
            # two-beat walking cycle.  Every attempted stride switches the
            # shared foot; the departing phase-1 beat is visible.
            if action in (1,2,3,4):
                if emit and phase==1:
                    _mark_progress(a)
                return 1-phase
            return phase
        if action in (1,2):
            # Without a horizontal separator, vertical travel is an independent
            # always-visible beat and does not alter horizontal footing.
            if emit:
                _mark_progress(a)
            return phase
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
    if emit and cand==1:
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
    # The silent c3 half-face alignment arms only the immediately following
    # lower-gate impact.  Carry it for one action, then clear it unless this
    # transition creates a fresh alignment.
    l5_half_face_armed=bool(st.get("l5_half_face_armed",False))
    st["l5_half_face_armed"]=False

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
                    vx,hy=_separator_axes()
                    # On a two-axis solid board manual selection plants the
                    # controller on the checkerboard foot of its current lattice
                    # cell, just as at level entry; it is not a universal phase-0
                    # reset.  One-axis solid boards retain their reset-to-zero rule.
                    if (np.any(np.array(ENTRY_GRID,dtype=int)==11) and vx and hy):
                        st["objects"][ci]["phase"]=(
                            (chosen["x"]//3 + chosen["y"]//3) % 2)
                    else:
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
            final_elongated=(np.any(np.array(ENTRY_GRID,dtype=int)==11) and
                             chosen["w"]!=chosen["h"])
            # A passenger waiting one full stride off the open (unsupported)
            # face of a six-row reservoir acknowledges selection.  This is the
            # ready-to-approach cue exposed when the passively released H at
            # (42,15) was selected below the roof-supported top gate.  A piece
            # waiting tangentially beside a gate (e.g. the entry H left of the
            # lower gate) is not on its open-face route and remains silent.
            gate_preface_ready=False
            if final_elongated and _l5_multi_gate_mode():
                for gp in _components((a==12)|(a==13)):
                    if len(gp)!=36:
                        continue
                    gxs=[xx for xx,yy in gp]; gys=[yy for xx,yy in gp]
                    gx0,gx1=min(gxs),max(gxs)+1
                    gy0,gy1=min(gys),max(gys)+1
                    xov=(chosen["x"]<gx1 and gx0<chosen["x"]+chosen["w"])
                    support_above=(gy0>0 and np.all(b[gy0-1,gx0:gx1]==2))
                    support_below=(gy1<b.shape[0] and
                                   np.all(b[gy1,gx0:gx1]==2))
                    if (xov and
                        ((support_above and chosen["y"]==gy1+3) or
                         (support_below and
                          chosen["y"]+chosen["h"]+3==gy0))):
                        gate_preface_ready=True
                        break
            switch_face_contact=(
                ((act["y"]+act["h"]==chosen["y"] or
                  chosen["y"]+chosen["h"]==act["y"]) and
                 act["x"]<chosen["x"]+chosen["w"] and
                 chosen["x"]<act["x"]+act["w"]) or
                ((act["x"]+act["w"]==chosen["x"] or
                  chosen["x"]+chosen["w"]==act["x"]) and
                 act["y"]<chosen["y"]+chosen["h"] and
                 chosen["y"]<act["y"]+act["h"]))
            # Selecting a freshly launched elongated passenger on
            # the matching target's two-stride lateral projection is itself a
            # docking/alignment handoff, so it suppresses the outgoing foot
            # report just like direct passenger-face contact.
            matching_lateral_stage=False
            if final_elongated:
                for f in _frames():
                    if f["iw"]!=chosen["w"] or f["ih"]!=chosen["h"]:
                        continue
                    if ((chosen["h"]>chosen["w"] and chosen["y"]==f["iy"] and
                         abs(chosen["x"]-f["ix"])==2*chosen["w"]) or
                        (chosen["w"]>chosen["h"] and chosen["x"]==f["ix"] and
                         abs(chosen["y"]-f["iy"])==2*chosen["h"])):
                        matching_lateral_stage=True
                        break
            # A controller already parked exactly in its own matching target is
            # likewise in a completed alignment state; handing control away from
            # it is silent even when its stored walking foot would ordinarily report.
            outgoing_matching_parked=False
            for f in _frames():
                if (f["iw"]==act["w"] and f["ih"]==act["h"] and
                    act["x"]==f["ix"] and act["y"]==f["iy"]):
                    outgoing_matching_parked=True
                    break
            outgoing_report=(final_elongated and ai is not None and
                             st["objects"][ai].get("phase",0)==1 and
                             not st["objects"][ai].get("launched",False) and
                             not switch_face_contact and
                             not matching_lateral_stage and
                             not outgoing_matching_parked and
                             not _touches_l5_gate(a,act) and
                             not _at_vacated_l5_gate_anchor(a,act) and
                             not _at_separator_open_end_membrane(act))
            if ((np.any(np.array(ENTRY_GRID,dtype=int)==11) and
                 chosen["w"]==chosen["h"]) or
                (ready and ci is not None and st["objects"][ci].get("launched",False) and
                 not final_elongated) or
                (gate_preface_ready and ci is not None and
                 st["objects"][ci].get("launched",False)) or outgoing_report):
                # Square solid-board controllers acknowledge selection.  An
                # elongated switch reports the outgoing planted phase only when
                # it is not itself a face-contact handoff/alignment operation.
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
    # The six-row dial's carry consumes the requested arrow: the clocks
    # advance and report, but the controller and its walking foot stay put.
    if _l4_clock_will_wrap(a):
        _l4_color_transfer(a,action)
        return a.tolist(),info,st
    act=_active(a)
    if act is None:
        return a.tolist(),info,st
    ai=_sync_active_index(st,act)
    dx,dy=DIRS[action]
    nx,ny=act["x"]+dx,act["y"]+dy

    if _l5_charged_normal_shell_hold(a,act,nx,ny,action):
        # The clock carry consumes this spatial request but not the controller's
        # stored walking foot.
        _l5_color_transfer(a,action,st,ai)
        return a.tolist(),info,st

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
            # Reservoir clocks advance on every consumed arrow, including a
            # rectangular passenger collision/portal launch.
            _l5_color_transfer(temp,action,st,ai)
            # Delivery to the one-stride matching-frame stage has its own
            # visible launch/docking cue on the two-axis final board.
            vx_sep,hy_sep=_separator_axes()
            if (np.any(np.array(ENTRY_GRID,dtype=int)==11) and vx_sep and hy_sep):
                docking=False
                for oo,px,py in placed:
                    for f in _frames():
                        if f["iw"]!=oo["w"] or f["ih"]!=oo["h"]:
                            continue
                        axial_dock=(px+dx==f["ix"] and py+dy==f["iy"])
                        lateral_stage=(
                            (action in (3,4) and px==f["ix"] and
                             abs(py-f["iy"])==2*oo["h"]) or
                            (action in (1,2) and py==f["iy"] and
                             abs(px-f["ix"])==2*oo["w"]))
                        if axial_dock or lateral_stage:
                            docking=True
                if docking:
                    _mark_progress(temp)
            if _goals_filled(temp):
                _finish(info)
            return temp.tolist(),info,st
        return a.tolist(),info,st

    h,w=a.shape
    token_wrong_side_bounce=False
    token_projected_bounce=False
    token_projected_preserve=False
    # A token flush on a portal's far face rejects entry on the opposite
    # side, throwing the controller outward by that guide's span.  A filled
    # rectangular portal also has an elastic projected corner: turning from
    # an exact token corner into a side alignment recoils by the rectangle's
    # extent normal to the token.  Open U-guide bbox corners are not elastic.
    if np.any(np.array(ENTRY_GRID,dtype=int)==12):
        toks=[p for p in _components((temp==12)|(temp==13)) if len(p)==9]
        bb=_base(); portal_comps=_components(bb==15)
        if len(toks)==1:
            p=toks[0]
            sx=min(xx for xx,yy in p); sy=min(yy for xx,yy in p)
            sw=max(xx for xx,yy in p)-sx+1
            sh=max(yy for xx,yy in p)-sy+1
            corner_before=((act["x"]+act["w"]==sx or sx+sw==act["x"]) and
                           (act["y"]+act["h"]==sy or sy+sh==act["y"]))
            side=None; opposite_edge=set()
            if nx+act["w"]==sx and ny<sy+sh and sy<ny+act["h"]:
                side="left"; opposite_edge={(sx+sw,yy) for yy in range(sy,sy+sh)}
            elif sx+sw==nx and ny<sy+sh and sy<ny+act["h"]:
                side="right"; opposite_edge={(sx-1,yy) for yy in range(sy,sy+sh)}
            elif ny+act["h"]==sy and nx<sx+sw and sx<nx+act["w"]:
                side="up"; opposite_edge={(xx,sy+sh) for xx in range(sx,sx+sw)}
            elif sy+sh==ny and nx<sx+sw and sx<nx+act["w"]:
                side="down"; opposite_edge={(xx,sy-1) for xx in range(sx,sx+sw)}
            span=None
            # Confirmed far-face rejection (works for shaped and filled guides).
            for q in portal_comps:
                if opposite_edge & set(q):
                    if side in ("left","right"):
                        span=max(xx for xx,yy in q)-min(xx for xx,yy in q)+1
                    else:
                        span=max(yy for xx,yy in q)-min(yy for xx,yy in q)+1
                    break
            # Filled portals additionally project their elastic corner along
            # the adjoining portal-normal axis.
            if span is None and side is not None:
                left_edge={(sx-1,yy) for yy in range(sy,sy+sh)}
                right_edge={(sx+sw,yy) for yy in range(sy,sy+sh)}
                top_edge={(xx,sy-1) for xx in range(sx,sx+sw)}
                bottom_edge={(xx,sy+sh) for xx in range(sx,sx+sw)}
                for q in portal_comps:
                    xs=[xx for xx,yy in q]; ys=[yy for xx,yy in q]
                    filled=(len(q)==(max(xs)-min(xs)+1)*(max(ys)-min(ys)+1))
                    if not filled:
                        continue
                    qs=set(q)
                    if (left_edge|right_edge) & qs:
                        exterior=((side=="up" and sy<=min(ys)) or
                                  (side=="down" and sy+sh>=max(ys)+1))
                        if exterior:
                            span=max(xs)-min(xs)+1
                            token_projected_bounce=True
                            token_projected_preserve=(not corner_before)
                            break
                    if (top_edge|bottom_edge) & qs:
                        exterior=((side=="left" and sx<=min(xs)) or
                                  (side=="right" and sx+sw>=max(xs)+1))
                        if exterior:
                            span=max(ys)-min(ys)+1
                            token_projected_bounce=True
                            token_projected_preserve=(not corner_before)
                            break
            if span is not None:
                # Recoil lands at a fixed guide-span anchor measured from the
                # token, independent of whether side alignment was entered
                # head-on or tangentially.
                if side=="left":
                    nx=sx-span
                elif side=="right":
                    nx=sx+span
                elif side=="up":
                    ny=sy-span
                elif side=="down":
                    ny=sy+span
                token_wrong_side_bounce=True
    if nx<0 or ny<0 or nx+act["w"]>w or ny+act["h"]>h:
        return a.tolist(),info,st
    destvals=temp[ny:ny+act["h"],nx:nx+act["w"]]
    if np.any((destvals==12)|(destvals==13)):
        if _l5_multi_gate_mode():
            charged=_l5_gate_will_wrap(temp,nx,ny,act["w"],act["h"])
            supported_above=_l5_hit_supported_above(temp,nx,ny,act["w"],act["h"])
            out=a.copy()
            _l5_color_transfer(out,action,st,ai)
            launched_pusher=(ai is not None and
                              st["objects"][ai].get("launched",False))
            slide_result=_l5_slide_gate_on_support(
                out,act,nx,ny,action,st)
            if slide_result is not None:
                slid,shoved_passenger=slide_result
                if shoved_passenger or launched_pusher:
                    # Extruding a passenger, or immediately returning the gate
                    # with that freshly extruded passenger, makes the rail slide
                    # a cooperative replacement beat: silent and phase-preserving.
                    cand=st["objects"][ai]["phase"] if ai is not None else 0
                else:
                    # An unloaded clear-station rail slide takes ordinary gait.
                    cand=_attempt_phase(slid,st,ai,action,emit=True)
                if ai is not None:
                    st["objects"][ai]["phase"]=cand
                return slid.tolist(),info,st
            if charged:
                # At c5 the blocked replacement beat becomes a spring launch:
                # the gate wraps in place, while the controller crosses the
                # color-15 band behind it.  Feedback/foot handling depends on
                # support orientation and whether a rail gate is terminal.
                pos=_l5_recoil_destination(act,action)
                if pos is not None:
                    tx,ty=pos
                    _restore(out,act)
                    moved=dict(act); moved["x"]=tx; moved["y"]=ty
                    _draw(out,moved,val=0)
                    _paint_contacts(out,moved)
                    if ai is not None:
                        st["objects"][ai]["x"]=tx
                        st["objects"][ai]["y"]=ty
                    # A gate hanging below its color-2 support announces the
                    # charged spring, but the whole spring interaction is a
                    # replacement beat and preserves the planted foot.  A lower
                    # rail gate also preserves at ENTRY; only its delivered
                    # terminal station consumes the attempted foot.
                    if supported_above:
                        _mark_progress(out)
                    if _l5_terminal_gate_wrap(temp):
                        cand=_attempt_phase(out,st,ai,action,emit=False)
                        if ai is not None:
                            st["objects"][ai]["phase"]=cand
                    return out.tolist(),info,st
            # An uncharged impact stays flush and preserves the planted
            # foot.  A lower gate above its rail reports every such impact.  A
            # top gate hanging below its support reports only the half-filled
            # c3 staging impact; later uncharged presses are silent.
            report=(not supported_above)
            # On the two-axis final board an elongated lower-face impact does
            # not report merely because it is blocked.  Its visible c4 charge
            # beat is the completion of the immediately preceding silent c3
            # half-face alignment.  The initial V approach armed that beat;
            # returning from the left corner did not, and its c4 impact was silent.
            vx_imp,hy_imp=_separator_axes()
            if (report and act["w"]!=act["h"] and vx_imp and hy_imp):
                report=l5_half_face_armed
            if supported_above:
                for p in _components((temp==12)|(temp==13)):
                    if len(p)!=36 or not any(nx<=x<nx+act["w"] and
                                             ny<=y<ny+act["h"] for x,y in p):
                        continue
                    xs=sorted(set(x for x,y in p))
                    ys=sorted(set(y for x,y in p))
                    crows=sum(all(int(temp[y,x])==12 for x in xs) for y in ys)
                    report=(crows==len(ys)//2)
                    break
            if report:
                _mark_progress(out)
            return out.tolist(),info,st
        launched=_launch_l4_gate(temp,act,nx,ny,action)
        token_launch=False
        if launched is None:
            launched=_launch_l4_token(temp,act,nx,ny,action)
            token_launch=(launched is not None)
        if launched is not None:
            # A normal colored-token launch is a replacement beat and leaves
            # the stationary pusher's foot untouched.  When the token's own
            # three-column dial carries, that cue is suppressed and the
            # attempted walking foot advances silently instead.
            if token_launch and _l4_token_dial_will_wrap(temp) and ai is not None:
                st["objects"][ai]["phase"]=_attempt_phase(
                    launched,st,ai,action,emit=False)
            if _goals_filled(launched):
                _finish(info)
            return launched.tolist(),info,st
        return a.tolist(),info,st
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
            if diagonal_leg and not _l5_multi_gate_mode():
                # Earlier solid boards store the foot across a partial diagonal leg.
                cand=st["objects"][ai]["phase"] if ai is not None else 0
            else:
                # On the multi-gate board the impact is an ordinary attempted gait
                # beat: it reports the departing planted foot and consumes it.
                cand=_attempt_phase(launched,st,ai,action,
                                    emit=bool(diagonal_leg and _l5_multi_gate_mode()))
            # The final L5 landing is a silent replacement beat: it completes
            # the passenger without consuming the pusher's planted foot.
            if _l5_multi_gate_mode() and completed and ai is not None:
                cand=st["objects"][ai]["phase"]
            # Every arrow on the multi-gate board advances all supported unary
            # reservoirs, including arrows consumed by a shaped-passenger impact.
            _l5_color_transfer(launched,action,st,ai)
            # A full-slot landing emits the completion pulse.  If the
            # passenger was already partly seated, its preceding physical
            # contact supplied that single docking pulse instead.
            if (completed and not _solid_partly_on_target(temp) and
                not _l5_multi_gate_mode()):
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

    # The composite source frame is elastic only while its colored token
    # still replaces the open wall.  Once that token launches, the restored
    # color-4 contour is an ordinary traversable target frame, like prior levels.
    colored_rim_loaded=False
    if np.any(np.array(ENTRY_GRID,dtype=int)==12):
        ee=np.array(ENTRY_GRID,dtype=int)
        es=[p for p in _components((ee==12)|(ee==13)) if len(p)==9]
        cs=[p for p in _components((temp==12)|(temp==13)) if len(p)==9]
        if len(es)==1 and len(cs)==1:
            colored_rim_loaded=(
                (min(xx for xx,yy in es[0]),min(yy for xx,yy in es[0])) ==
                (min(xx for xx,yy in cs[0]),min(yy for xx,yy in cs[0])))
    if colored_rim_loaded and np.any(destvals==4):
        bx,by=act["x"]-dx,act["y"]-dy
        h,w=a.shape
        if (0<=bx and 0<=by and bx+act["w"]<=w and by+act["h"]<=h and
            np.all(temp[by:by+act["h"],bx:bx+act["w"]]==1)):
            _draw(temp,act,x=bx,y=by,val=0)
            cand=_attempt_phase(temp,st,ai,action,emit=False)
            _l4_color_transfer(temp,action)
            if ai is not None:
                st["objects"][ai]["x"]=bx
                st["objects"][ai]["y"]=by
                st["objects"][ai]["phase"]=cand
            return temp.tolist(),info,st
        return a.tolist(),info,st

    # On the final two-axis solid board, a head-on press into a filled
    # color-15 separator is a clocked portal impact rather than an inert wall.
    # The controller stays at its ready face, both unary gates advance, and the
    # stationary impact reports once while preserving the planted foot.
    vx_portal,hy_portal=_separator_axes()
    if (np.any(np.array(ENTRY_GRID,dtype=int)==11) and
        vx_portal and hy_portal and np.any(destvals==15) and
        _touches_base_color(act,15)):
        out=a.copy()
        # The uncharged stationary impact is a forced report that preserves
        # the planted foot.  The paired c5->c0 carry is instead a silent
        # ordinary attempted beat: it consumes/toggles the foot.
        portal_wrap=False
        for pp in _components((a==12)|(a==13)):
            if len(pp)!=36:
                continue
            px=sorted(set(xx for xx,yy in pp))
            py=sorted(set(yy for xx,yy in pp))
            crows=sum(all(int(a[yy,xx])==12 for xx in px) for yy in py)
            if crows==len(py)-1:
                portal_wrap=True
                break
        braced=_touches_l5_gate(a,act)
        if portal_wrap:
            cand=_attempt_phase(out,st,ai,action,emit=False)
            if braced:
                # At c5 the gate/portal bridge announces the spent planted
                # stride even though an isolated separator wrap stays silent.
                _mark_progress(out)
            if ai is not None:
                st["objects"][ai]["phase"]=cand
        elif not braced:
            _mark_progress(out)
        # An uncharged controller braced simultaneously against a colored gate
        # and the filled separator uses the press only to charge the reservoir.
        # The bridge impact is silent and retains its planted foot.
        _l5_color_transfer(out,action,st,ai)
        return out.tolist(),info,st
    if not np.all((destvals==1)|(destvals==4)):
        return a.tolist(),info,st

    _draw(temp,act,x=nx,y=ny,val=0)

    moved=act.copy(); moved["x"]=nx; moved["y"]=ny
    touches_solid=_touches_solid(temp,moved)
    touches_l5_gate=_touches_l5_gate(temp,moved)
    # Normal entry into the horizontal face of a top gate hanging below its
    # color-2 support is a silent replacement beat and preserves the planted
    # foot.  A lower rail gate's face entry and horizontal side-face entries
    # remain ordinary gait.
    l5_top_gate_contact=False
    l5_displaced_gate_half_face=False
    if (_l5_multi_gate_mode() and
        (action in (1,2) or act["h"]>act["w"]) and
        touches_l5_gate and not _touches_l5_gate(temp,act)):
        ee=np.array(ENTRY_GRID,dtype=int)
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            vertical_face=((moved["y"]+moved["h"]==y0 or y1==moved["y"]) and
                           moved["x"]<x1 and x0<moved["x"]+moved["w"])
            supported_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
            # A gate displaced along its rail exposes one ordinary c2->c3
            # lower-face alignment beat.  Unlike contact at its ENTRY station
            # (and other clock phases), that beat reports the current gait foot
            # and consumes it; the following charged stages still use the
            # silent top-contact replacement.
            sxs=sorted(set(xs)); sys=sorted(set(ys))
            crows=sum(all(int(temp[yy,xx])==12 for xx in sxs) for yy in sys)
            entry_same=[min(xx for xx,yy in q) for q in
                        _components((ee==12)|(ee==13))
                        if len(q)==36 and min(yy for xx,yy in q)==y0]
            displaced=bool(entry_same and x0 not in entry_same)
            if vertical_face and supported_above:
                if displaced and crows==len(sys)//2-1:
                    l5_displaced_gate_half_face=True
                else:
                    l5_top_gate_contact=True
                break
    l5_terminal_gate_wrap=_l5_terminal_gate_wrap(temp,act)
    l5_uncharged_normal_shell_entry=_l5_uncharged_normal_shell_entry(
        temp,act,moved,action)
    # Entering a six-row gate's axial projection from exactly one gate-span
    # away on c2->c3 is a silent staging beat.  It consumes the ordinary gait
    # foot; delayed evidence appears on the following stride.
    l5_gate_axis_entry=False
    l5_gate_axis_preserve=False
    l5_gate_axis_departure=False
    l5_gate_preface_stage=False
    l5_gate_pre_corner_stage=False
    l5_gate_open_preface_entry=False
    l5_gate_open_preface_tangent=False
    l5_gate_open_preface_departure=False
    l5_gate_open_preface_carried_departure=False
    l5_uncharged_full_face_alignment=False
    l5_precharged_full_face_alignment=False
    l5_charged_full_face_alignment=False
    l5_charged_full_face_departure=False
    l5_charged_partial_face_entry=False
    l5_axis_spring=None
    if _l5_multi_gate_mode():
        ee=np.array(ENTRY_GRID,dtype=int)
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            gw,gh=x1-x0,y1-y0
            def xov(o):
                return o["x"]<x1 and x0<o["x"]+o["w"]
            def yov(o):
                return o["y"]<y1 and y0<o["y"]+o["h"]
            xgap=max(x0-(moved["x"]+moved["w"]),moved["x"]-x1,0)
            ygap=max(y0-(moved["y"]+moved["h"]),moved["y"]-y1,0)
            old_xgap=max(x0-(act["x"]+act["w"]),act["x"]-x1,0)
            old_ygap=max(y0-(act["y"]+act["h"]),act["y"]-y1,0)
            entered=((action in (3,4) and ygap==gh and
                      xov(moved) and not xov(act)) or
                     (action in (1,2) and xgap==gw and
                      yov(moved) and not yov(act)))
            departed=((action in (3,4) and ygap==gh and
                       xov(act) and not xov(moved)) or
                      (action in (1,2) and xgap==gw and
                       yov(act) and not yov(moved)))
            sxs=sorted(set(xs)); sys=sorted(set(ys))
            crows=sum(all(int(temp[y,x])==12 for x in sxs) for y in sys)
            # Tangential alignment along the live roof gate's open face is
            # directed by its horizontal rail.  RIGHTward retreat is elastic;
            # LEFTward travel toward the useful gate-slide side is ordinary gait.
            support_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
            support_below=(y1<ee.shape[0] and np.all(ee[y1,x0:x1]==2))
            open_preface_row=(
                (support_above and act["y"]==y1+3 and moved["y"]==y1+3) or
                (support_below and act["y"]+act["h"]+3==y0 and
                 moved["y"]+moved["h"]+3==y0))
            if (act["w"]!=act["h"] and action in (3,4) and
                open_preface_row and not xov(act) and xov(moved)):
                # The live supported gate's open face begins one controller
                # stride beyond its body.  Tangential entry from the exterior
                # corner into that projected half-slot is the same silent
                # elastic alignment as travel within the projection.
                l5_gate_open_preface_entry=True
            if (action==4 and open_preface_row and
                ai is not None and st["objects"][ai].get("launched",False) and
                xov(act) and xov(moved)):
                # The supported roof gate's projected route is directed along
                # its rail: RIGHT travel is a silent elastic retreat, while
                # LEFT travel toward the useful gate-slide side is ordinary gait.
                l5_gate_open_preface_tangent=True
            if (action in (3,4) and open_preface_row and
                xov(act) and not xov(moved)):
                # Departure from the projected shell is always muted.  A
                # freshly released passenger carries a visible elastic
                # replacement through it; a manually routed passenger instead
                # consumes the silent gait attempt.
                l5_gate_open_preface_departure=True
                l5_gate_open_preface_carried_departure=(
                    ai is not None and
                    st["objects"][ai].get("launched",False))
            # Moving normally into the last open controller-stride before a
            # gate is a silent preserving preface either when c4 prepares a
            # charged spring, or when a displaced rail gate is approached from
            # the side that will return it toward its ENTRY station.
            preface=((action in (1,2) and xov(moved) and ygap==3 and
                      old_ygap==6) or
                     (action in (3,4) and yov(moved) and xgap==3 and
                      old_xgap==6))
            returning=False
            if preface and action in (3,4):
                entry_same=[min(xx for xx,yy in q) for q in
                            _components((ee==12)|(ee==13))
                            if len(q)==36 and min(yy for xx,yy in q)==y0]
                if entry_same:
                    ex=min(entry_same,key=lambda z:abs(z-x0))
                    returning=((action==4 and x0<ex) or
                               (action==3 and x0>ex))
            if preface and (crows==len(sys)-2 or returning):
                l5_gate_preface_stage=True
            # At c1 the gate projects a silent pre-corner shell one controller
            # stride before exact diagonal contact.  Like the c4 charged preface,
            # this is a replacement alignment beat and preserves the planted foot.
            diagonal_preface=(
                (action in (3,4) and xgap==3 and old_xgap==6 and
                 (moved["y"]+moved["h"]==y0 or y1==moved["y"])) or
                (action in (1,2) and ygap==3 and old_ygap==6 and
                 (moved["x"]+moved["w"]==x0 or x1==moved["x"])))
            if crows==1 and diagonal_preface:
                # The c1 projected diagonal shell is a gate-lattice datum shared
                # by square and elongated controllers.  V approaching the lower
                # gate from its left at x33->36 exposed the elongated case: the
                # reporting foot was muted and retained one stride before corner.
                l5_gate_pre_corner_stage=True
            # The remote axial shell is a replacement anchor only on the
            # transition into the half-filled c3 phase.  At other uncharged
            # phases crossing the same projection is ordinary gait.
            if entered:
                l5_gate_axis_entry=(crows==len(sys)//2-1)
                if l5_gate_axis_entry:
                    # The ENTRY and intermediate rail stations act as elastic
                    # alignment anchors.  At the far terminal station the same
                    # remote shell is instead a silent, gait-consuming stage.
                    entry_gates=[q for q in _components((ee==12)|(ee==13))
                                 if len(q)==36]
                    spans=[]
                    for jj,q in enumerate(entry_gates):
                        qx=[xx for xx,yy in q]; qy=[yy for xx,yy in q]
                        for rr in entry_gates[:jj]:
                            rx=[xx for xx,yy in rr]; ry=[yy for xx,yy in rr]
                            if min(qy)==min(ry):
                                spans.append(max(max(qx),max(rx))-
                                             min(min(qx),min(rx))+1)
                    same=[min(xx for xx,yy in q) for q in entry_gates
                          if min(yy for xx,yy in q)==y0]
                    terminal=(bool(spans and same) and
                              abs(x0-min(same,key=lambda z:abs(z-x0)))>=
                              2*min(spans))
                    l5_gate_axis_preserve=not terminal
            if departed and crows==len(sys)-2:
                # At the far rail terminal, leaving the remote shell while it
                # charges c4->c5 is a silent replacement that preserves gait.
                entry_gates=[q for q in _components((ee==12)|(ee==13))
                             if len(q)==36]
                spans=[]
                for jj,q in enumerate(entry_gates):
                    qx=[xx for xx,yy in q]; qy=[yy for xx,yy in q]
                    for rr in entry_gates[:jj]:
                        rx=[xx for xx,yy in rr]; ry=[yy for xx,yy in rr]
                        if min(qy)==min(ry):
                            spans.append(max(max(qx),max(rx))-
                                         min(min(qx),min(rx))+1)
                same=[min(xx for xx,yy in q) for q in entry_gates
                      if min(yy for xx,yy in q)==y0]
                terminal=(bool(spans and same) and
                          abs(x0-min(same,key=lambda z:abs(z-x0)))>=
                          2*min(spans))
                if terminal:
                    l5_gate_axis_departure=True
            # A charged gate's field fires either on remote axial-shell entry
            # or on any orthogonal face contact reached by a legal move.  This
            # includes tangential motion along a face.
            face_touch=(((moved["y"]+moved["h"]==y0 or y1==moved["y"]) and
                         xov(moved)) or
                        ((moved["x"]+moved["w"]==x0 or x1==moved["x"]) and
                         yov(moved)))
            # A non-square controller completing half->full alignment along a
            # gate's side spends the charged beat on alignment; it does not
            # spring until a later tangential move begins from the full face.
            old_full_side=(
                ((act["x"]+act["w"]==x0 or x1==act["x"]) and
                 act["y"]<=y0 and act["y"]+act["h"]>=y1) or
                ((act["y"]+act["h"]==y0 or y1==act["y"]) and
                 act["x"]<=x0 and act["x"]+act["w"]>=x1))
            new_full_side=(
                ((moved["x"]+moved["w"]==x0 or x1==moved["x"]) and
                 moved["y"]<=y0 and moved["y"]+moved["h"]>=y1) or
                ((moved["y"]+moved["h"]==y0 or y1==moved["y"]) and
                 moved["x"]<=x0 and moved["x"]+moved["w"]>=x1))
            fresh_elongated_full=(act["w"]!=act["h"] and
                                  new_full_side and not old_full_side)
            if crows==0 and fresh_elongated_full:
                l5_uncharged_full_face_alignment=True
            if crows==len(sys)-2 and fresh_elongated_full:
                l5_precharged_full_face_alignment=True
            if crows==len(sys)-1 and fresh_elongated_full:
                l5_charged_full_face_alignment=True
            if (crows==len(sys)-1 and act["w"]!=act["h"] and
                old_full_side and not new_full_side):
                l5_charged_full_face_departure=True
            if (crows==len(sys)-1 and act["w"]!=act["h"] and
                face_touch and not _touches_l5_gate(temp,act) and
                not new_full_side):
                # A charged diagonal-corner approach to an elongated half-face
                # spends the wrap as a visible contact cue.  It moves normally
                # and consumes gait; only remote axial shells recoil.
                l5_charged_partial_face_entry=True
            # At c5, tangential travel from one elongated half-face slot
            # to the other also fires the gate-normal spring.  This is distinct
            # from corner->half and half->full/full->half alignment beats, which
            # merely spend the charge in place.
            old_hface=((act["y"]+act["h"]==y0 or y1==act["y"]) and xov(act))
            new_hface=((moved["y"]+moved["h"]==y0 or y1==moved["y"]) and
                       xov(moved))
            old_vface=((act["x"]+act["w"]==x0 or x1==act["x"]) and yov(act))
            new_vface=((moved["x"]+moved["w"]==x0 or x1==moved["x"]) and
                       yov(moved))
            elongated_half_swap=(
                act["w"]!=act["h"] and not old_full_side and
                not new_full_side and
                ((action in (3,4) and old_hface and new_hface) or
                 (action in (1,2) and old_vface and new_vface)))
            if (crows==len(sys)-1 and
                (entered or (act["w"]==act["h"] and face_touch) or
                 elongated_half_swap)):
                toward=(2 if moved["y"]+moved["h"]<=y0 else
                        1 if moved["y"]>=y1 else
                        4 if moved["x"]+moved["w"]<=x0 else
                        3)
                supported_above=(y0>0 and np.all(ee[y0-1,x0:x1]==2))
                l5_axis_spring=(toward,supported_above,elongated_half_swap)
    if l5_axis_spring is not None:
        toward,supported_above,half_swap_launch=l5_axis_spring
        pos=_l5_recoil_destination(moved,toward)
        if pos is not None:
            tx,ty=pos
            _restore(temp,moved)
            moved["x"]=tx; moved["y"]=ty
            _draw(temp,moved,val=0)
            _paint_contacts(temp,moved)
            _l5_color_transfer(temp,action,st,ai)
            # Remote axial projection springs consume the attempted stride.
            # A charged tangential swap between two elongated half-face slots is
            # instead a true passenger launch: the spring replaces the stride,
            # preserves the planted foot, and leaves the controller carrying
            # that foot until its next manual selection/move.
            if half_swap_launch and ai is not None:
                cand=st["objects"][ai]["phase"]
            else:
                cand=_attempt_phase(temp,st,ai,action,emit=False)
            if supported_above:
                _mark_progress(temp)
            if ai is not None:
                st["objects"][ai]["phase"]=cand
                st["objects"][ai]["x"]=tx
                st["objects"][ai]["y"]=ty
                st["objects"][ai]["launched"]=bool(half_swap_launch)
            if _goals_filled(temp):
                _finish(info)
            return temp.tolist(),info,st
    # Entering a colored gate's right-side diagonal corner is a silent
    # staging beat: it advances gait but mutes the report.  The left-side
    # corner is the useful approach for returning a delivered rail gate and
    # remains ordinary gait.
    l5_charged_gate_corner=False
    if _l5_multi_gate_mode() and act["w"]==act["h"]:
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=sorted(set(xx for xx,yy in p)); ys=sorted(set(yy for xx,yy in p))
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            def gate_corner(o):
                return (x1==o["x"] and
                        (o["y"]+o["h"]==y0 or y1==o["y"]))
            if gate_corner(moved) and not gate_corner(act):
                l5_charged_gate_corner=True
                break
    # An elongated controller uses the same right-side diagonal datum, but
    # announces that alignment visibly while consuming its ordinary gait attempt.
    # The initial L6 vertical approach was compatible with ordinary phase1; H
    # arriving at the top gate on phase0 proves the pulse is forced.
    l5_rect_gate_corner_entry=False
    l5_rect_gate_corner_stage=False
    l5_rect_gate_side_to_corner=False
    if _l5_multi_gate_mode() and act["w"]!=act["h"]:
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            sxs=sorted(set(xs)); sys=sorted(set(ys))
            crows=sum(all(int(temp[yy,xx])==12 for xx in sxs) for yy in sys)
            def rect_gate_corner(o):
                return (x1==o["x"] and
                        (o["y"]+o["h"]==y0 or y1==o["y"]))
            if rect_gate_corner(moved) and not rect_gate_corner(act):
                if _touches_l5_gate(temp,act):
                    # Leaving a partial side face for its adjacent diagonal
                    # corner is a silent elastic reverse alignment which retains
                    # the planted foot. A true exterior approach may announce.
                    l5_rect_gate_side_to_corner=True
                elif crows==len(sys)//2:
                    # At the half-filled c3 phase this corner is a silent
                    # phase-preserving alignment anchor.  Delayed evidence is
                    # the later rail-slide pulse after the consuming face step.
                    l5_rect_gate_corner_stage=True
                else:
                    l5_rect_gate_corner_entry=True
                break
    # The elongated controller's opposite/left-side diagonal corner is a
    # silent phase-preserving alignment stage specifically on c2->c3.  V
    # approaching the lower gate from x36 exposed it on a reporting foot, and
    # the following ordinary face entry reported that retained foot.
    l5_rect_gate_left_corner_entry=False
    if _l5_multi_gate_mode() and act["w"]!=act["h"]:
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            sxs=sorted(set(xs)); sys=sorted(set(ys))
            crows=sum(all(int(temp[yy,xx])==12 for xx in sxs) for yy in sys)
            def rect_gate_left_corner(o):
                return (o["x"]+o["w"]==x0 and
                        (o["y"]+o["h"]==y0 or y1==o["y"]))
            if (crows==len(sys)//2-1 and
                rect_gate_left_corner(moved) and
                not rect_gate_left_corner(act)):
                # This is the c2->c3 half-charge alignment, not a blanket
                # left-corner rule: H reached the same corner at c1 and reported.
                l5_rect_gate_left_corner_entry=True
                break
    # Completing a right-side diagonal stage by entering its adjacent face is
    # a visible replacement cue.  Left-side corner-to-face travel stays ordinary.
    l5_gate_corner_to_face=False
    if (_l5_multi_gate_mode() and act["w"]==act["h"] and
        touches_l5_gate):
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            def gate_corner2(o):
                return (x1==o["x"] and
                        (o["y"]+o["h"]==y0 or y1==o["y"]))
            if gate_corner2(act) and not gate_corner2(moved):
                l5_gate_corner_to_face=True
                break
    # Completing the elongated right-corner stage by entering its adjacent
    # gate face is silent but consumes the ordinary gait attempt.  The initial
    # lower-gate approach hid this on foot0; the later H approach exposed foot1.
    l5_rect_gate_corner_to_face=False
    if (_l5_multi_gate_mode() and act["w"]!=act["h"] and
        touches_l5_gate):
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            sxs=sorted(set(xs)); sys=sorted(set(ys))
            crows=sum(all(int(temp[yy,xx])==12 for xx in sxs) for yy in sys)
            def rect_gate_corner2(o):
                return (x1==o["x"] and
                        (o["y"]+o["h"]==y0 or y1==o["y"]))
            horizontal_face=(
                (moved["y"]+moved["h"]==y0 or y1==moved["y"]) and
                moved["x"]<x1 and x0<moved["x"]+moved["w"])
            if (rect_gate_corner2(act) and not rect_gate_corner2(moved) and
                (horizontal_face or crows==len(sys)-2)):
                # Normal/top-bottom face completion is always a muted stride;
                # a side-face completion has the same staging role only at c4,
                # immediately before the charged full-face sequence.
                l5_rect_gate_corner_to_face=True
                break
    # A non-square controller can occupy either half of a 6x6 gate's
    # face.  At c3, sliding tangentially from one exact half-face slot to the
    # other is a silent alignment stage (the attempted foot is still consumed).
    l5_rect_gate_half_face=False
    if _l5_multi_gate_mode() and act["w"]!=act["h"]:
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=sorted(set(xx for xx,yy in p)); ys=sorted(set(yy for xx,yy in p))
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            crows=sum(all(int(temp[y,x])==12 for x in xs) for y in ys)
            if crows!=len(ys)//2:
                continue
            atop=(act["y"]+act["h"]==y0 and moved["y"]+moved["h"]==y0)
            abot=(y1==act["y"] and y1==moved["y"])
            aleft=(act["x"]+act["w"]==x0 and moved["x"]+moved["w"]==x0)
            aright=(x1==act["x"] and x1==moved["x"])
            if (action in (3,4) and (atop or abot) and
                x1-x0==2*act["w"] and
                {act["x"],moved["x"]}=={x0,x1-act["w"]}):
                l5_rect_gate_half_face=True
            if (action in (1,2) and (aleft or aright) and
                y1-y0==2*act["h"] and
                {act["y"],moved["y"]}=={y0,y1-act["h"]}):
                l5_rect_gate_half_face=True
            # The complementary elongated orientation spans the full face.
            # Its c3 alignment beat is directional: half-overlap -> exact full
            # overlap is silent, while departing full alignment is ordinary.
            xov0=max(0,min(act["x"]+act["w"],x1)-max(act["x"],x0))
            xov1=max(0,min(moved["x"]+moved["w"],x1)-max(moved["x"],x0))
            yov0=max(0,min(act["y"]+act["h"],y1)-max(act["y"],y0))
            yov1=max(0,min(moved["y"]+moved["h"],y1)-max(moved["y"],y0))
            if (action in (3,4) and (atop or abot) and
                xov0==(x1-x0)//2 and xov1==x1-x0):
                l5_rect_gate_half_face=True
            if (action in (1,2) and (aleft or aright) and
                yov0==(y1-y0)//2 and yov1==y1-y0):
                l5_rect_gate_half_face=True
    # At the half-filled c3 phase, tangential travel along the color-15
    # separator is a silent replacement beat which preserves the shared foot;
    # the same c3 transition normal to (or away from) the separator may report.
    l5_half_separator_tangent=False
    if _l5_multi_gate_mode() and action in (3,4):
        half=False
        for p in _components((temp==12)|(temp==13)):
            if len(p)==36:
                xs=sorted(set(xx for xx,yy in p)); ys=sorted(set(yy for xx,yy in p))
                half=(sum(all(int(temp[y,x])==12 for x in xs) for y in ys)==3)
                break
        # The c3 replacement belongs to departure from the diagonal
        # corner of the central color-2 junction while travelling tangentially
        # along color15; it is not a blanket property of the separator face.
        bb=_base(); H,W=bb.shape
        def corner2(o):
            cs=((o["x"]-1,o["y"]-1),(o["x"]+o["w"],o["y"]-1),
                (o["x"]-1,o["y"]+o["h"]),(o["x"]+o["w"],o["y"]+o["h"]))
            return any(0<=xx<W and 0<=yy<H and int(bb[yy,xx])==2
                       for xx,yy in cs)
        l5_half_separator_tangent=(half and _touches_base_color(act,15) and
                                   _touches_base_color(moved,15) and
                                   corner2(act) and not corner2(moved))
    departed_solid_contact=_touches_solid(a,act) and not touches_solid
    # On the colored-gate board, leaving the open end of the color-15 guide
    # rail is a one-shot departure cue, analogous to leaving a dynamic face.
    colored_board=np.any(np.array(ENTRY_GRID,dtype=int)==12)
    colored_frame_loaded=False
    if colored_board:
        ee=np.array(ENTRY_GRID,dtype=int)
        es=[p for p in _components((ee==12)|(ee==13)) if len(p)==9]
        cs=[p for p in _components((temp==12)|(temp==13)) if len(p)==9]
        if len(es)==1 and len(cs)==1:
            colored_frame_loaded=(
                (min(x for x,y in es[0]),min(y for x,y in es[0])) ==
                (min(x for x,y in cs[0]),min(y for x,y in cs[0])))
    # Once the small colored token has left its source frame, entering
    # exact corner contact with it is a one-stride tangential alignment cue:
    # the next stride would line the controller up beside the token.
    detached_token_corner=False
    detached_token_pre_corner=False
    detached_token_silent_corner=False
    detached_token_axis_entry=False
    if colored_board and not colored_frame_loaded:
        toks=[p for p in _components((temp==12)|(temp==13)) if len(p)==9]
        if len(toks)==1:
            pts=toks[0]
            sx=min(xx for xx,yy in pts); sy=min(yy for xx,yy in pts)
            sw=max(xx for xx,yy in pts)-sx+1
            sh=max(yy for xx,yy in pts)-sy+1
            def corner(o):
                return ((o["x"]+o["w"]==sx or sx+sw==o["x"]) and
                        (o["y"]+o["h"]==sy or sy+sh==o["y"]))
            def pre_corner(o):
                xadj=(o["x"]+o["w"]==sx or sx+sw==o["x"])
                yadj=(o["y"]+o["h"]==sy or sy+sh==o["y"])
                xgap=max(sx-(o["x"]+o["w"]),o["x"]-(sx+sw),0)
                ygap=max(sy-(o["y"]+o["h"]),o["y"]-(sy+sh),0)
                bb=_base(); portal_gap=False
                if xadj and ygap==o["h"]:
                    if o["y"]>=sy+sh:
                        slab=bb[sy+sh:sy+sh+o["h"],sx:sx+sw]
                    else:
                        slab=bb[sy-o["h"]:sy,sx:sx+sw]
                    portal_gap=(slab.shape==(o["h"],sw) and np.all(slab==15))
                if yadj and xgap==o["w"]:
                    if o["x"]>=sx+sw:
                        slab=bb[sy:sy+sh,sx+sw:sx+sw+o["w"]]
                    else:
                        slab=bb[sy:sy+sh,sx-o["w"]:sx]
                    portal_gap=(portal_gap or
                                (slab.shape==(sh,o["w"]) and np.all(slab==15)))
                return portal_gap
            before_pre=pre_corner(act)
            detached_token_silent_corner=(corner(moved) and before_pre)
            detached_token_corner=(corner(moved) and not corner(act) and
                                   not before_pre)
            detached_token_pre_corner=(pre_corner(moved) and not before_pre)
            # A filled portal projects one additional alignment shell around
            # its flush token.  Entering the token's axial projection while
            # still one stride from its side is a replacement pre-recoil cue.
            bb=_base()
            token_edge={(sx-1,yy) for yy in range(sy,sy+sh)} | \
                       {(sx+sw,yy) for yy in range(sy,sy+sh)} | \
                       {(xx,sy-1) for xx in range(sx,sx+sw)} | \
                       {(xx,sy+sh) for xx in range(sx,sx+sw)}
            filled_adjacent=False
            for q in _components(bb==15):
                xs=[xx for xx,yy in q]; ys=[yy for xx,yy in q]
                if (len(q)==(max(xs)-min(xs)+1)*(max(ys)-min(ys)+1) and
                    token_edge & set(q)):
                    filled_adjacent=True
                    break
            if filled_adjacent:
                def xproj(o):
                    return o["x"]<sx+sw and sx<o["x"]+o["w"]
                def yproj(o):
                    return o["y"]<sy+sh and sy<o["y"]+o["h"]
                xgap=max(sx-(moved["x"]+moved["w"]),
                         moved["x"]-(sx+sw),0)
                ygap=max(sy-(moved["y"]+moved["h"]),
                         moved["y"]-(sy+sh),0)
                if (action in (3,4) and ygap==moved["h"] and
                    xproj(moved) and not xproj(act)):
                    detached_token_axis_entry=True
                if (action in (1,2) and xgap==moved["w"] and
                    yproj(moved) and not yproj(act)):
                    detached_token_axis_entry=True
    # A wrong-side portal rejection leaves the controller one connected-guide
    # span away, exactly aligned with the token.  Leaving that recoil lane is a
    # visible replacement beat, but (unlike corner/guide staging) it still
    # consumes the ordinary walking foot.
    detached_token_rebound_departure=False
    if colored_board and not colored_frame_loaded:
        toks=[p for p in _components((temp==12)|(temp==13)) if len(p)==9]
        if len(toks)==1:
            pts=toks[0]
            sx=min(xx for xx,yy in pts); sy=min(yy for xx,yy in pts)
            sw=max(xx for xx,yy in pts)-sx+1
            sh=max(yy for xx,yy in pts)-sy+1
            bb=_base()
            left_edge={(sx-1,yy) for yy in range(sy,sy+sh)}
            right_edge={(sx+sw,yy) for yy in range(sy,sy+sh)}
            top_edge={(xx,sy-1) for xx in range(sx,sx+sw)}
            bottom_edge={(xx,sy+sh) for xx in range(sx,sx+sw)}
            for q in _components(bb==15):
                qs=set(q); span=None
                # Recoil distance is the portal extent normal to whichever
                # token face the component actually adjoins.
                if (left_edge|right_edge) & qs:
                    span=max(xx for xx,yy in q)-min(xx for xx,yy in q)+1
                elif (top_edge|bottom_edge) & qs:
                    span=max(yy for xx,yy in q)-min(yy for xx,yy in q)+1
                if span is None:
                    continue
                if (action in (1,2) and act["y"]==sy and ny!=sy and
                    abs(act["x"]-sx)==span):
                    detached_token_rebound_departure=True
                if (action in (3,4) and act["x"]==sx and nx!=sx and
                    abs(act["y"]-sy)==span):
                    detached_token_rebound_departure=True
    touch_channel_before=(colored_board and _touches_base_color(act,15))
    touch_channel_after=(colored_board and _touches_base_color(moved,15))
    # The exact three-cell bridge between the detached token and gate touches
    # two distinct colored components.  Entering it is a completion/staging
    # beat even when the six-row clock carries simultaneously.
    colored_bridge_dock=False
    colored_bridge_departure=False
    if colored_board:
        def colored_touch_count(o):
            n=0
            for p in _components((temp==12)|(temp==13)):
                xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
                q={"x":min(xs),"y":min(ys),
                   "w":max(xs)-min(xs)+1,"h":max(ys)-min(ys)+1}
                horiz=((o["x"]+o["w"]==q["x"] or
                        q["x"]+q["w"]==o["x"]) and
                       o["y"]<q["y"]+q["h"] and q["y"]<o["y"]+o["h"])
                vert=((o["y"]+o["h"]==q["y"] or
                       q["y"]+q["h"]==o["y"]) and
                      o["x"]<q["x"]+q["w"] and q["x"]<o["x"]+o["w"])
                if horiz or vert:
                    n+=1
            return n
        bridge_before=colored_touch_count(act)
        bridge_after=colored_touch_count(moved)
        colored_bridge_dock=(bridge_after>=2 and bridge_before<2)
        colored_bridge_departure=(bridge_before>=2 and bridge_after<2)
    # Moving outward from an exact diagonal corner of a larger colored gate
    # emits a replacement departure beat and preserves the walking foot.  The
    # small detached token has separate portal/corner rules.
    colored_gate_corner_departure=False
    colored_gate_rebound_departure=False
    if colored_board:
        for p in _components((temp==12)|(temp==13)):
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
            gw,gh=x1-x0,y1-y0
            if gw<=act["w"] and gh<=act["h"]:
                continue
            xcorner=(act["x"]+act["w"]==x0 or x1==act["x"])
            ycorner=(act["y"]+act["h"]==y0 or y1==act["y"])
            away=((action==3 and act["x"]+act["w"]==x0) or
                  (action==4 and x1==act["x"]) or
                  (action==1 and act["y"]+act["h"]==y0) or
                  (action==2 and y1==act["y"]))
            if xcorner and ycorner and away:
                colored_gate_corner_departure=True
            # The outward corner projects a second replacement anchor exactly
            # one gate-span away along the tangent.
            tangent_y=(act["y"]+act["h"]==y0 or y1==act["y"])
            tangent_x=(act["x"]+act["w"]==x0 or x1==act["x"])
            horiz_away=((action==4 and act["x"]-x1==gw) or
                        (action==3 and x0-(act["x"]+act["w"])==gw))
            vert_away=((action==2 and act["y"]-y1==gh) or
                       (action==1 and y0-(act["y"]+act["h"])==gh))
            if (tangent_y and horiz_away) or (tangent_x and vert_away):
                colored_gate_rebound_departure=True
    # Once both colored passengers have left their sources, the restored
    # small-token frame and the delivered large gate define a useful routing
    # cross.  Leaving the gate's row projection while travelling down/up its
    # frame-interior x-lane is a replacement alignment beat.
    colored_gate_frame_lane_departure=False
    if colored_board and not colored_frame_loaded and action in (1,2):
        for f in _frames():
            if act["x"]!=f["ix"] or nx!=f["ix"]:
                continue
            for p in _components((temp==12)|(temp==13)):
                xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
                x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
                if x1-x0<=act["w"] and y1-y0<=act["h"]:
                    continue
                was_y=(act["y"]<y1 and y0<act["y"]+act["h"])
                now_y=(ny<y1 and y0<ny+act["h"])
                toward=((action==2 and f["iy"]>=y1) or
                        (action==1 and f["iy"]+f["ih"]<=y0))
                if was_y and not now_y and toward:
                    colored_gate_frame_lane_departure=True
    # Entering exact diagonal corner contact with a connected guide is its
    # one-stride pre-face cue.  It precedes the ordinary exterior-side contact
    # beat and, like that beat, preserves the stored walking foot.
    guide_corner_entry=False
    guide_corner_before=False
    if colored_board:
        def guide_corner(o,p):
            x0=min(xx for xx,yy in p); x1=max(xx for xx,yy in p)+1
            y0=min(yy for xx,yy in p); y1=max(yy for xx,yy in p)+1
            return ((o["x"]+o["w"]==x0 or x1==o["x"]) and
                    (o["y"]+o["h"]==y0 or y1==o["y"]))
        for p in _components(_base()==15):
            # Bounding-box corners are meaningful only for a filled rectangular
            # portal; a U-guide's empty interior makes its bbox corners spurious.
            xs=[xx for xx,yy in p]; ys=[yy for xx,yy in p]
            if len(p)!=(max(xs)-min(xs)+1)*(max(ys)-min(ys)+1):
                continue
            before_corner=guide_corner(act,p)
            if before_corner:
                guide_corner_before=True
            if guide_corner(moved,p) and not before_corner:
                guide_corner_entry=True
    def exterior_side(contact_o,free_o):
        # Identify the connected guide actually touching contact_o.  A cue is
        # attached only to its exterior face; transitions between a wall and
        # the U-guide's interior projection are ordinary gait.
        bb=_base(); H,W=bb.shape
        ox,oy,ow,oh=contact_o["x"],contact_o["y"],contact_o["w"],contact_o["h"]
        near=set()
        for yy in range(oy,oy+oh):
            for xx in (ox-1,ox+ow):
                if 0<=xx<W and int(bb[yy,xx])==15: near.add((xx,yy))
        for xx in range(ox,ox+ow):
            for yy in (oy-1,oy+oh):
                if 0<=yy<H and int(bb[yy,xx])==15: near.add((xx,yy))
        for p in _components(bb==15):
            ps=set(p)
            if not (near & ps): continue
            if action in (3,4):
                c=free_o["x"]+(free_o["w"]-1)/2
                lo=min(xx for xx,yy in p); hi=max(xx for xx,yy in p)
            else:
                c=free_o["y"]+(free_o["h"]-1)/2
                lo=min(yy for xx,yy in p); hi=max(yy for xx,yy in p)
            if c<lo or c>hi:
                return True
        return False
    if colored_frame_loaded:
        entered_channel=False
        departed_channel=(touch_channel_before and not touch_channel_after)
    else:
        entered_channel=(not touch_channel_before and touch_channel_after and
                         not guide_corner_before and exterior_side(moved,act))
        departed_channel=(touch_channel_before and not touch_channel_after and
                          exterior_side(act,moved))
    # The apparent portal contact in the exact gap between two colored
    # passengers belongs to that dynamic bridge, not to the static channel.
    # Leaving it is ordinary gait (so it consumes and may report the foot).
    if colored_bridge_departure:
        departed_channel=False
    useful_solid_contact=_useful_side_contact(temp,moved,action)
    staged_near_solid=(not touches_solid) and _staged_near_solid(temp,moved,action)
    # On the multi-gate board the source plus follows a diagonal route to its
    # contour.  Reaching the useful concave stem from its exact one-stride
    # staging lane is an explicit reporting beat (and still consumes gait).
    l5_diagonal_solid_stage=False
    if _l5_multi_gate_mode() and staged_near_solid:
        for p in _components(temp==11):
            t=_matching_solid_target(p)
            if t is None:
                continue
            sx=min(xx for xx,yy in p); sy=min(yy for xx,yy in p)
            if t["x"]!=sx and t["y"]!=sy:
                l5_diagonal_solid_stage=True
                break
    # After the first axial leg has aligned a passenger with its target, a
    # tangential traverse across that useful-side staging line is ordinary gait
    # on L5; only travel normal toward the passenger is a silent ready beat.
    l5_tangential_solid_stage=False
    if _l5_multi_gate_mode() and staged_near_solid:
        for p in _components(temp==11):
            t=_matching_solid_target(p)
            if t is None:
                continue
            sx=min(xx for xx,yy in p); sy=min(yy for xx,yy in p)
            ddx=t["x"]-sx; ddy=t["y"]-sy
            if ((ddx==0 and ddy!=0 and action in (3,4)) or
                (ddy==0 and ddx!=0 and action in (1,2))):
                l5_tangential_solid_stage=True
                break
    # Entering a moved passenger's physical pocket from its exact one-stride
    # pre-stage is the second half of that alignment cue.  It reports once
    # independent of the alternating gait, while a normal head-on contact
    # remains the silent final beat before a push.
    entered_from_stage=(touches_solid and useful_solid_contact and
                        _staged_near_solid(temp,act,action) and
                        not _l5_multi_gate_mode())
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
    vacated_l5_gate_anchor=_at_vacated_l5_gate_anchor(temp,moved)
    vacated_l5_gate_slot_completion=(
        _entered_vacated_l5_gate_slot(temp,act,moved))
    vacated_l5_gate_c2_projection_entry=(
        _vacated_l5_gate_c2_projection_entry(temp,act,moved,action))
    vacated_l5_gate_open_corner_route=(
        _at_vacated_l5_gate_open_corner_route(temp,act,moved,action))
    # The first boundary crossing into the open-face projection is fully muted.
    # Travel wholly within that projection still reports the planted phase, but
    # remains an elastic replacement and therefore does not consume it.
    vacated_l5_gate_projection_travel=(
        vacated_l5_gate_open_corner_route and
        not _at_vacated_l5_gate_anchor(temp,act) and
        not _at_vacated_l5_gate_anchor(temp,moved))
    departed_vacated_l5_gate_open_corner_route=(
        _departed_vacated_l5_gate_open_corner_route(
            temp,act,moved,action))
    # The complementary inward crossing is the same elastic boundary in
    # reverse: it is silent (rather than announcing departure) and retains gait.
    entered_vacated_l5_gate_open_corner_route=(
        action in (3,4) and
        _departed_vacated_l5_gate_open_corner_route(
            temp,moved,act,4 if action==3 else 3))
    entered_vacated_l5_gate_outer_corner=(
        _entered_vacated_l5_gate_outer_corner(temp,act,moved,action))
    _paint_contacts(temp,moved)
    # First overlap with the rim of this object's matching frame is a staging
    # cue.  It emits exactly one pulse in place of the ordinary gait report.
    frame_entry=False; frame_parked=False; frame_departed=False
    launched_lateral_frame_entry=False
    launched_lateral_parked=False
    frame_lane_departed=False; frame_lane_entered=False; frame_prestage=False
    frame_axis_entry=False; restored_frame_lane_entry=False
    foreign_frame_lane_entered=False
    matching_frame_prelane_entered=False
    matching_frame_prelane_departed=False
    matching_frame_prerim_stage=False
    matching_frame_short_lane_departed=False
    matching_frame_short_lane_visible_departed=False
    matching_frame_short_lane_unpowered_departed=False
    matching_frame_long_axis_departed=False
    solid_board=np.any(np.array(ENTRY_GRID,dtype=int)==11)
    # On the two-axis solid board, first reaching exact diagonal corner contact
    # with another rectangular passenger is its visible alignment cue.  It is
    # one stride before face alignment/collision and replaces ordinary gait.
    passenger_corner_entry=False
    vx_sep0,hy_sep0=_separator_axes()
    # A rectangular controller's colored center is the datum used while it
    # threads an exact three-cell opening in a color-2 separator.  Its projected
    # slab is a directed routing membrane.  Departing its core on either side,
    # or entering it from the lower-coordinate side, is a silent preserving
    # anchor.  Only entry from the greater-coordinate side is a visible consuming
    # replacement.  The outer shell may still overlap the opening for one more
    # stride, so feedback is keyed to the center.
    separator_core_departure=False
    separator_core_far_boundary=False
    separator_channel_junction_entered=False
    separator_channel_junction_far_entry=False
    separator_channel_junction_crossed=False
    # A separator can also terminate beside an unbounded opening rather than
    # enclosing a three-cell doorway on both sides.  Entering such an open end
    # from the lower-coordinate side is the same directed near membrane: it is
    # silent and elastic.  The reverse (greater-coordinate) approach remains an
    # ordinary consuming beat.  Ground this in the dense separator plane plus
    # exactly one lateral wall, rather than in any fixed station coordinate.
    separator_open_end_near_entry=False
    # Reversing out through the bounded/near edge is also muted, but it
    # consumes the attempted foot.  Delayed selection feedback after earlier
    # returns distinguishes this from near-side entry, which preserves gait.
    separator_open_end_near_departure=(
        action==1 and _at_separator_open_end_membrane(act) and
        not _at_separator_open_end_membrane(moved))
    # Leaving the open-end membrane toward its far side mutes the walking
    # report but still consumes the attempted foot.  Delayed evidence is the
    # next ordinary y21->24 stride: it is silent only because this departure
    # changed phase1 to phase0.
    separator_open_end_departure=(
        action==2 and _at_separator_open_end_membrane(act) and
        not _at_separator_open_end_membrane(moved))
    # Seating either elongated controller in its matching contour closes the
    # cooperative routing circuit.  While closed, even the final/outer doorway
    # keeps its outward boundary elastic; before any controller is seated that
    # same boundary is ordinary access to the exterior bypass.
    parked_matching_controller=False
    if solid_board:
        for q in st.get("objects",[]):
            for f in _frames():
                if (q["w"]==f["iw"] and q["h"]==f["ih"] and
                    q["x"]==f["ix"] and q["y"]==f["iy"]):
                    parked_matching_controller=True
                    break
            if parked_matching_controller:
                break
    if solid_board and vx_sep0 and hy_sep0 and act["w"]!=act["h"]:
        bb=_base(); H0,W0=bb.shape
        if action in (3,4):
            oy,oh=act["y"],act["h"]
            if 0<oy and oy+oh<H0:
                for sx in range(W0-2):
                    opening=(np.all(bb[oy:oy+oh,sx:sx+3]==1) and
                             np.all(bb[oy-1,sx:sx+3]==2) and
                             np.all(bb[oy+oh,sx:sx+3]==2))
                    if not opening:
                        continue
                    def core_xover(o):
                        c0=o["x"]+o["cx"]
                        return c0<sx+3 and sx<c0+o["cw"]
                    was_core=core_xover(act); now_core=core_xover(moved)
                    if was_core != now_core:
                        # The doorway core is directed.  Its lower-coordinate
                        # boundary is elastic in both directions: RIGHT enters
                        # silently and LEFT departs silently.  Entry from the
                        # greater side (LEFT) is the visible replacement, while
                        # departure toward that side (RIGHT) is ordinary gait.
                        # An internal doorway still has another
                        # parallel separator plane beyond it; its outward edge
                        # remains elastic.  At the board's last such plane the
                        # same outward departure is ordinary bypass gait.
                        sep_mask=np.isin(bb,(2,15))
                        greater_parallel_opening=any(
                            int(np.sum(np.all(sep_mask[:,s2:s2+3],axis=1))) >=
                            3*min(act["w"],act["h"])
                            for s2 in range(sx+1,W0-2))
                        if ((was_core and
                             (action==3 or greater_parallel_opening or
                              parked_matching_controller or
                              _l5_gate_layout_displaced(temp))) or
                            (now_core and action==4)):
                            separator_core_departure=True
                        elif now_core and action==3:
                            separator_core_far_boundary=True
                        break
        if action in (1,2):
            ox,ow=act["x"],act["w"]
            if 0<ox and ox+ow<W0:
                for sy in range(H0-2):
                    opening=(np.all(bb[sy:sy+3,ox:ox+ow]==1) and
                             np.all(bb[sy:sy+3,ox-1]==2) and
                             np.all(bb[sy:sy+3,ox+ow]==2))
                    if not opening:
                        continue
                    def core_yover(o):
                        c0=o["y"]+o["cy"]
                        return c0<sy+3 and sy<c0+o["ch"]
                    was_core=core_yover(act); now_core=core_yover(moved)
                    if was_core != now_core:
                        # Vertical doorway cores use the same directed membrane:
                        # DOWN enters and UP departs at the elastic near edge;
                        # UP entry from the far side is visible, while DOWN
                        # departure toward that side is ordinary gait.
                        sep_mask=np.isin(bb,(2,15))
                        greater_parallel_opening=any(
                            int(np.sum(np.all(sep_mask[s2:s2+3,:],axis=0))) >=
                            3*min(act["w"],act["h"])
                            for s2 in range(sy+1,H0-2))
                        if ((was_core and
                             (action==1 or greater_parallel_opening or
                              parked_matching_controller or
                              _l5_gate_layout_displaced(temp))) or
                            (now_core and action==2)):
                            separator_core_departure=True
                        elif now_core and action==1:
                            separator_core_far_boundary=True
                        break
        bb_sep=np.isin(bb,(2,15))
        if action==2:
            # Moving down enters a horizontal plane from its smaller-y side.
            ox,ow=act["x"],act["w"]
            if 0<ox and ox+ow<W0:
                for sy in range(H0-2):
                    floor=np.all(bb[sy:sy+3,ox:ox+ow]==1)
                    left=np.all(bb_sep[sy:sy+3,ox-1])
                    right=np.all(bb_sep[sy:sy+3,ox+ow])
                    dense=min(int(np.sum(bb_sep[yy])) for yy in range(sy,sy+3))
                    if not (floor and (left != right) and
                            dense>=3*max(act["w"],act["h"])):
                        continue
                    def core_yover_open(o):
                        c0=o["y"]+o["cy"]
                        return c0<sy+3 and sy<c0+o["ch"]
                    if core_yover_open(moved) and not core_yover_open(act):
                        separator_open_end_near_entry=True
                        break
    # The three-cell doorway row/column projects beyond its color-2 wall.
    # Entering the perpendicular color-15 channel's full-width projection while
    # on that route is a silent preserving junction beat.  This is keyed to the
    # ENTRY geometry: it explains H x33->36 on the y30 doorway route, while the
    # same x39-channel alignment on y33 is ordinary gait.
    if solid_board and vx_sep0 and hy_sep0 and act["w"]!=act["h"]:
        bb=_base(); H0,W0=bb.shape
        if act["w"]>act["h"] and action in (3,4):
            oy,oh=act["y"],act["h"]
            route_spans=[]
            if 0<oy and oy+oh<H0:
                for sx in range(W0-2):
                    if (np.all(bb[oy:oy+oh,sx:sx+3]==1) and
                        np.all(bb[oy-1,sx:sx+3]==2) and
                        np.all(bb[oy+oh,sx:sx+3]==2)):
                        route_spans.append((sx,sx+3))
            if route_spans:
                bw=act["h"]
                for sx in range(W0-bw+1):
                    # The channel at the doorway wall itself is handled by the
                    # directed core membrane; this cue is for a remote crossing.
                    if any(sx<r1 and r0<sx+bw for r0,r1 in route_spans):
                        continue
                    rows=np.all(bb[:,sx:sx+bw]==15,axis=1)
                    run=best=0
                    for q in rows:
                        run=run+1 if q else 0; best=max(best,run)
                    if best<2*bw:
                        continue
                    was=(act["x"]<=sx and sx+bw<=act["x"]+act["w"])
                    now=(moved["x"]<=sx and sx+bw<=moved["x"]+moved["w"])
                    if now and not was:
                        # The projected channel is directed like the doorway
                        # membrane: entry from the lower-coordinate side is a
                        # silent preserving anchor, while entry from the
                        # greater-coordinate side is a visible consuming cue.
                        if action==4:
                            separator_channel_junction_entered=True
                        else:
                            separator_channel_junction_far_entry=True
                        break
                    if now and was and action==3:
                        # Crossing the embedded three-cell channel toward the
                        # lower-coordinate side is its silent elastic centre
                        # boundary.  The reverse/rightward crossing is ordinary
                        # reporting gait (as the earlier x36->39 traversal shows).
                        separator_channel_junction_crossed=True
                        break
                    if (_l5_gate_layout_displaced(temp) and was and not now and
                        action==4):
                        # Once a rail reservoir has left its ENTRY station, the
                        # route network opens the greater-coordinate exit of the
                        # remote projected channel as a silent elastic boundary.
                        # With the entry rail intact this same exit is ordinary.
                        separator_channel_junction_entered=True
                        break
        entry_gate_pos={(min(xx for xx,yy in p),min(yy for xx,yy in p))
                        for p in _components((np.array(ENTRY_GRID,dtype=int)==12)|
                                             (np.array(ENTRY_GRID,dtype=int)==13))
                        if len(p)==36}
        live_gate_pos={(min(xx for xx,yy in p),min(yy for xx,yy in p))
                       for p in _components((temp==12)|(temp==13)) if len(p)==36}
        if (act["h"]>act["w"] and action in (3,4) and
            live_gate_pos!=entry_gate_pos):
            # Once a rail gate has moved, the vertical passenger exposes the reverse side of the same
            # junction: its leading square lattice cell follows the doorway row,
            # and departure from a projected vertical channel is elastic too.
            oy=act["y"]; oh=act["w"]
            route_spans=[]
            if 0<oy and oy+oh<H0:
                for rx in range(W0-2):
                    if (np.all(bb[oy:oy+oh,rx:rx+3]==1) and
                        np.all(bb[oy-1,rx:rx+3]==2) and
                        np.all(bb[oy+oh,rx:rx+3]==2)):
                        route_spans.append((rx,rx+3))
            if route_spans:
                bw=act["w"]
                for sx in range(W0-bw+1):
                    if any(sx<r1 and r0<sx+bw for r0,r1 in route_spans):
                        continue
                    rows=np.all(bb[:,sx:sx+bw]==15,axis=1)
                    run=best=0
                    for q in rows:
                        run=run+1 if q else 0; best=max(best,run)
                    if best<2*bw:
                        continue
                    was=(act["x"]<=sx and sx+bw<=act["x"]+act["w"])
                    now=(moved["x"]<=sx and sx+bw<=moved["x"]+moved["w"])
                    if was and not now:
                        separator_channel_junction_entered=True; break
        if act["h"]>act["w"] and action in (1,2):
            ox,ow=act["x"],act["w"]
            route_spans=[]
            if 0<ox and ox+ow<W0:
                for sy in range(H0-2):
                    if (np.all(bb[sy:sy+3,ox:ox+ow]==1) and
                        np.all(bb[sy:sy+3,ox-1]==2) and
                        np.all(bb[sy:sy+3,ox+ow]==2)):
                        route_spans.append((sy,sy+3))
            if route_spans:
                bh=act["w"]
                for sy in range(H0-bh+1):
                    if any(sy<r1 and r0<sy+bh for r0,r1 in route_spans):
                        continue
                    cols=np.all(bb[sy:sy+bh,:]==15,axis=0)
                    run=best=0
                    for q in cols:
                        run=run+1 if q else 0; best=max(best,run)
                    if best<2*bh:
                        continue
                    was=(act["y"]<=sy and sy+bh<=act["y"]+act["h"])
                    now=(moved["y"]<=sy and sy+bh<=moved["y"]+moved["h"])
                    if now and not was:
                        if action==2:
                            separator_channel_junction_entered=True
                        else:
                            separator_channel_junction_far_entry=True
                        break
                    if now and was and action==1:
                        separator_channel_junction_crossed=True
                        break
    # First entering normal face contact with a color-15 separator on the
    # final two-axis solid board is a silent elastic staging beat.  This is the
    # ready position before an impact/portal attempt.
    solid_portal_face_entry=(solid_board and vx_sep0 and hy_sep0 and
                             not touches_l5_gate and
                             not _touches_base_color(act,15) and
                             _touches_base_color(moved,15))
    # A shaped solid and its contour can share a long routing axis.  On the
    # two-axis board, that route projects an elastic near-side boundary at the
    # source/target's shared top-left coordinate.  An elongated foreign
    # controller crossing this boundary in either direction while between the
    # endpoints takes a silent preserving beat.  Crossing the opposite
    # (greater-coordinate) boundary is a visible replacement that consumes the
    # walking attempt and therefore survives a simultaneous clock carry.
    solid_lane_departure=False
    solid_lane_far_boundary=False
    if solid_board and vx_sep0 and hy_sep0 and act["w"]!=act["h"]:
        for pp in _components(np.array(ENTRY_GRID,dtype=int)==11):
            tt=_matching_solid_target(pp)
            if tt is None:
                continue
            px=[xx for xx,yy in pp]; py=[yy for xx,yy in pp]
            sx,sy=min(px),min(py)
            sw=max(px)-sx+1; sh=max(py)-sy+1
            if sx==tt["x"] and sy!=tt["y"] and action in (3,4):
                between=((sy+sh<=act["y"] and act["y"]+act["h"]<=tt["y"]) or
                         (tt["y"]+tt["h"]<=act["y"] and
                          act["y"]+act["h"]<=sy))
                if (between and
                    ((act["x"]==sx and moved["x"]<sx) or
                     (act["x"]<sx and moved["x"]==sx))):
                    solid_lane_departure=True
                if (between and
                    ((act["x"]==sx and moved["x"]>sx) or
                     (act["x"]>sx and moved["x"]==sx))):
                    solid_lane_far_boundary=True
            if sy==tt["y"] and sx!=tt["x"] and action in (1,2):
                between=((sx+sw<=act["x"] and act["x"]+act["w"]<=tt["x"]) or
                         (tt["x"]+tt["w"]<=act["x"] and
                          act["x"]+act["w"]<=sx))
                if (between and
                    ((act["y"]==sy and moved["y"]<sy) or
                     (act["y"]<sy and moved["y"]==sy))):
                    solid_lane_departure=True
                if (between and
                    ((act["y"]==sy and moved["y"]>sy) or
                     (act["y"]>sy and moved["y"]==sy))):
                    solid_lane_far_boundary=True
    if solid_board and vx_sep0 and hy_sep0 and act["w"]!=act["h"]:
        def rect_corner(u,v):
            return ((u["x"]+u["w"]==v["x"] or v["x"]+v["w"]==u["x"]) and
                    (u["y"]+u["h"]==v["y"] or v["y"]+v["h"]==u["y"]))
        for oo in others:
            if oo["val"] in (4,5) and rect_corner(moved,oo) and not rect_corner(act,oo):
                passenger_corner_entry=True
                break
    if solid_board or colored_board:
        for f in _frames():
            if f["iw"]==act["w"] and f["ih"]==act["h"]:
                was=_rect_overlap(act["x"],act["y"],act["w"],act["h"],f)
                now=_rect_overlap(nx,ny,act["w"],act["h"],f)
                was_parked=(act["x"]==f["ix"] and act["y"]==f["iy"])
                # After the colored token leaves this composite source, rim
                # entry/parking and projection are inert for the controller.
                if now and not was and (solid_board or colored_frame_loaded):
                    frame_entry=True
                    # A matching passenger launched onto the target's exact
                    # long-axis row/column but two perpendicular strides away
                    # has already announced docking on the launch.  Its first
                    # lateral rim entry is therefore silent (but consumes gait).
                    if (solid_board and ai is not None and
                        st["objects"][ai].get("launched",False) and
                        f["iw"]==act["w"] and f["ih"]==act["h"] and
                        (((act["h"]>act["w"] and act["y"]==f["iy"]) and
                          ((action==3 and act["x"]==f["ix"]+2*act["w"]) or
                           (action==4 and act["x"]==f["ix"]-2*act["w"]))) or
                         ((act["w"]>act["h"] and act["x"]==f["ix"]) and
                          ((action==1 and act["y"]==f["iy"]+2*act["h"]) or
                           (action==2 and act["y"]==f["iy"]-2*act["h"]))))):
                        launched_lateral_frame_entry=True
                # The loaded colored composite frame announces the exact
                # one-stride approach beat before its rim is first entered.
                if colored_board and colored_frame_loaded and not now:
                    tx,ty=nx+dx,ny+dy
                    if _rect_overlap(tx,ty,act["w"],act["h"],f):
                        frame_prestage=True
                # While loaded, first horizontal projection onto the colored
                # component's useful axis is also a replacement cue.
                if colored_board and colored_frame_loaded and action in (3,4):
                    was_axis=(act["x"] < f["x"]+f["w"] and
                              f["x"] < act["x"]+act["w"])
                    now_axis=(nx < f["x"]+f["w"] and
                              f["x"] < nx+act["w"])
                    if now_axis and not was_axis:
                        frame_axis_entry=True
                # After unloading, exact entry onto the restored frame's
                # interior x-lane from its left is again a useful alignment cue.
                if (colored_board and not colored_frame_loaded and action==4 and
                    act["x"]<f["ix"] and nx==f["ix"]):
                    restored_frame_lane_entry=True
                if (solid_board or colored_frame_loaded) and nx==f["ix"] and ny==f["iy"]:
                    frame_parked=True
                    # The second lateral docking stride of a launched matching
                    # passenger reaches the exact interior and supplies the
                    # deferred visible completion cue, even on a c5 wrap.
                    # The first lateral entry stride records this two-beat
                    # launch route, so ordinary one-step perpendicular parking
                    # does not receive the deferred completion report.
                    if (solid_board and ai is not None and
                        st["objects"][ai].get("lateral_docking",False) and
                        f["iw"]==act["w"] and f["ih"]==act["h"] and
                        (((act["h"]>act["w"]) and
                          ((action==3 and act["x"]==f["ix"]+act["w"]) or
                           (action==4 and act["x"]==f["ix"]-act["w"]))) or
                         ((act["w"]>act["h"]) and
                          ((action==1 and act["y"]==f["iy"]+act["h"]) or
                           (action==2 and act["y"]==f["iy"]-act["h"]))))):
                        launched_lateral_parked=True
                if (solid_board or colored_frame_loaded) and was_parked and not frame_parked:
                    # On the two-gate board an elongated passenger leaving its
                    # matching interior along its long axis uses a silent elastic
                    # replacement, rather than the inherited visible rectangular-
                    # frame cue.  Delayed feedback after V's UP departure proves
                    # that this beat preserves its planted foot.  Perpendicular H
                    # departure remains the confirmed visible cue.
                    long_axis_departure=(
                        _l5_multi_gate_mode() and act["w"]!=act["h"] and
                        ((act["w"]>act["h"] and action in (3,4)) or
                         (act["h"]>act["w"] and action in (1,2))))
                    if long_axis_departure:
                        matching_frame_long_axis_departed=True
                    else:
                        frame_departed=True
                # Exact approach lanes persist as geometry after unloading,
                # but only departure along the token's horizontal useful axis
                # remains a cue.  Vertical departure is then inert.
                was_lane=(act["x"]==f["ix"] or act["y"]==f["iy"])
                now_lane=(nx==f["ix"] or ny==f["iy"])
                if (was_lane and not now_lane and
                    (solid_board or colored_frame_loaded or
                     (colored_board and action in (3,4)))):
                    frame_lane_departed=True
                # An elongated passenger's matching short-axis routing line is
                # directed.  Toward the greater-coordinate/useful side, H leaves
                # its y-lane DOWN and V leaves its x-lane RIGHT silently while
                # preserving the foot.  The complementary lower-coordinate
                # departure is a visible consuming replacement, rather than
                # ordinary gait: H's y24->21 report survives even a c5 carry.
                # Its long-axis lane departure remains ordinary gait.
                if (_l5_multi_gate_mode() and act["w"]!=act["h"] and
                    not was_parked and
                    ((act["w"]>act["h"] and action==2 and
                      act["y"]==f["iy"] and ny!=f["iy"]) or
                     (act["h"]>act["w"] and action==4 and
                      act["x"]==f["ix"] and nx!=f["ix"]))):
                    matching_frame_short_lane_departed=True
                if (_l5_multi_gate_mode() and act["w"]!=act["h"] and
                    not was_parked and not staged_near_solid and
                    not solid_portal_face_entry and
                    ((act["w"]>act["h"] and action==1 and
                      act["y"]==f["iy"] and ny!=f["iy"]) or
                     (act["h"]>act["w"] and action==3 and
                      act["x"]==f["ix"] and nx!=f["ix"]))):
                    if parked_matching_controller:
                        matching_frame_short_lane_visible_departed=True
                    else:
                        # Before the cooperative circuit is closed, the same
                        # lower-side lane departure is a muted elastic alignment:
                        # delayed feedback on the following stride proves that
                        # it preserves the planted gait phase.
                        matching_frame_short_lane_unpowered_departed=True
                # On the multi-gate solid board, an approach axis is a
                # directional route into the target: its x-lane is entered from
                # the right, and its y-lane from below.  Entering the same line
                # from the far side is ordinary gait.  The alignment beat is
                # silent but still consumes the shared walking phase.
                entered_x=(nx==f["ix"] and act["x"]!=f["ix"])
                entered_y=(ny==f["iy"] and act["y"]!=f["iy"])
                if (_l5_multi_gate_mode() and
                    ((entered_x and action==3) or (entered_y and action==1))):
                    frame_lane_entered=True
        # A matching target first projects an approach line one whole
        # controller extent outside its interior axis.  Entry from the useful
        # side (right/below) is silent and preserving.  Leaving the line is
        # always visible: outward departure preserves, targetward departure consumes.
        if (_l5_multi_gate_mode() and act["w"]!=act["h"] and
            not _l5_gate_layout_displaced(temp)):
            for f in _frames():
                if f["iw"]==act["w"] and f["ih"]==act["h"]:
                    if (act["w"]>act["h"] and action==3 and
                        nx==f["ix"]+act["w"] and act["x"]!=nx and
                        not _rect_overlap(nx,ny,act["w"],act["h"],f)):
                        matching_frame_prelane_entered=True
                    if (act["w"]>act["h"] and action in (3,4) and
                        act["x"]==f["ix"]+act["w"] and nx!=act["x"] and
                        not _rect_overlap(act["x"],act["y"],act["w"],act["h"],f)):
                        matching_frame_prelane_departed=True
                    if (act["h"]>act["w"] and action==1 and
                        ny==f["iy"]+act["h"] and act["y"]!=ny and
                        not _rect_overlap(nx,ny,act["w"],act["h"],f)):
                        matching_frame_prelane_entered=True
                    if (act["h"]>act["w"] and action in (1,2) and
                        act["y"]==f["iy"]+act["h"] and ny!=act["y"] and
                        not _rect_overlap(act["x"],act["y"],act["w"],act["h"],f)):
                        matching_frame_prelane_departed=True
        # One stride before an elongated piece first overlaps its matching
        # rim, entering the exact pre-rim staging position is silent but consumes
        # ordinary gait.  The following stride is the visible rim-entry cue.
        if _l5_multi_gate_mode() and act["w"]!=act["h"]:
            for f in _frames():
                if f["iw"]==act["w"] and f["ih"]==act["h"]:
                    now=_rect_overlap(nx,ny,act["w"],act["h"],f)
                    tx,ty=nx+dx,ny+dy
                    nxt=_rect_overlap(tx,ty,act["w"],act["h"],f)
                    if not now and nxt:
                        matching_frame_prerim_stage=True
        # On a multi-target board the directional axis is a board routing line,
        # not an ownership test: an elongated controller also mutes its stride
        # when it first reaches the interior row/column of a differently shaped
        # target.  Rim entry and parking below remain shape-matched.
        if _l5_multi_gate_mode():
            for f in _frames():
                foreign=(f["iw"]!=act["w"] or f["ih"]!=act["h"])
                entered_y=(ny==f["iy"] and act["y"]!=f["iy"])
                # Foreign target rows are shared upward-routing lines: entering
                # one from below is a silent preserving replacement.  Foreign
                # target columns are not shared lanes; LEFT across x27 on L6 is
                # ordinary gait.  Matching x/y lanes were handled above.
                if foreign and entered_y and action==1:
                    frame_lane_entered=True
                    foreign_frame_lane_entered=True
    # Rim entry/departure are one-shot staging cues.  Solid contact and exact
    # parking suppress ordinary feedback; blocked impact is reported above.
    cue=(frame_prestage or frame_axis_entry or launched_lateral_parked or
         (frame_entry and not launched_lateral_frame_entry) or frame_departed or
             restored_frame_lane_entry or
             (frame_lane_departed and not staged_near_solid and
              (not _l5_multi_gate_mode() or
               (action in (3,4) and act["w"]==act["h"]))) or
         detached_token_pre_corner or detached_token_corner or
         detached_token_axis_entry or detached_token_rebound_departure or
         colored_gate_corner_departure or colored_gate_rebound_departure or
         colored_gate_frame_lane_departure or l5_gate_corner_to_face or
         l5_gate_open_preface_carried_departure or
         l5_rect_gate_corner_entry or
         solid_bbox_cue or solid_lane_far_boundary or
         separator_core_far_boundary or separator_channel_junction_far_entry or
         matching_frame_prelane_departed or
         matching_frame_short_lane_visible_departed or
         departed_solid_contact or
         guide_corner_entry or entered_channel or departed_channel or
         departed_vacated_l5_gate_open_corner_route or
         vacated_l5_gate_c2_projection_entry or
         colored_bridge_dock or entered_from_stage or
         (passenger_corner_entry and not separator_channel_junction_crossed) or
         l5_diagonal_solid_stage or partial_target_contact)
    dial_wrap=_l4_dial_will_wrap(temp)
    # After the colored token has left its source, departing the restored
    # frame's horizontal interior lane remains an explicit replacement beat.
    # Unlike loaded-frame staging, this cue survives a simultaneous dial carry.
    unloaded_horizontal_lane=(colored_board and not colored_frame_loaded and
                              action in (3,4) and frame_lane_departed)
    # On the two-axis final board the paired six-row reservoirs have a global
    # silent carry: c5->c0 suppresses the walking report while the attempted
    # stride still advances the planted foot.  Earlier wraps were all masked by
    # springs or naturally silent feet; the first reporting-foot wrap exposed it.
    vx_sep,hy_sep=_separator_axes()
    l6_clock_wrap=False
    if solid_board and vx_sep and hy_sep:
        for p in _components((temp==12)|(temp==13)):
            if len(p)!=36:
                continue
            xs=sorted(set(xx for xx,yy in p)); ys=sorted(set(yy for xx,yy in p))
            crows=sum(all(int(temp[y,x])==12 for x in xs) for y in ys)
            if crows==len(ys)-1:
                l6_clock_wrap=True
                break
    cand=_attempt_phase(temp,st,ai,action,
                        emit=(not l6_clock_wrap) and
                             (not touches_solid or useful_solid_contact) and
                             not frame_lane_entered and
                             not separator_core_departure and
                             not separator_channel_junction_entered and
                             not separator_channel_junction_crossed and
                             not separator_open_end_near_entry and
                             not separator_open_end_near_departure and
                             not separator_open_end_departure and
                             not solid_lane_departure and
                             not solid_portal_face_entry and
                             not matching_frame_prelane_entered and
                             not matching_frame_prerim_stage and
                             not launched_lateral_frame_entry and
                             not matching_frame_short_lane_departed and
                             not matching_frame_short_lane_unpowered_departed and
                             not matching_frame_long_axis_departed and
                             not l5_gate_axis_entry and
                             not l5_gate_axis_departure and
                             not l5_gate_preface_stage and
                             not l5_gate_pre_corner_stage and
                             not l5_gate_open_preface_entry and
                             not l5_gate_open_preface_tangent and
                             not l5_gate_open_preface_departure and
                             not l5_uncharged_normal_shell_entry and
                             not l5_uncharged_full_face_alignment and
                             not l5_precharged_full_face_alignment and
                             not l5_top_gate_contact and
                             not l5_displaced_gate_half_face and
                             not l5_charged_gate_corner and
                             not l5_charged_partial_face_entry and
                             not l5_terminal_gate_wrap and
                             not l5_rect_gate_corner_stage and
                             not l5_rect_gate_corner_to_face and
                             not l5_rect_gate_side_to_corner and
                             not l5_rect_gate_left_corner_entry and
                             not l5_rect_gate_half_face and
                             not l5_half_separator_tangent and
                             (not staged_near_solid or l5_tangential_solid_stage) and not cue and
                             not frame_parked and not vacated_solid_anchor and
                             not vacated_l5_gate_anchor and
                             (not vacated_l5_gate_open_corner_route or
                              vacated_l5_gate_projection_travel) and
                             not entered_vacated_l5_gate_open_corner_route and
                             not entered_vacated_l5_gate_outer_corner and
                             not token_wrong_side_bounce and
                             not detached_token_silent_corner)
    if l5_displaced_gate_half_face:
        # Completing the lower-face alignment at a displaced roof station is
        # the visible half-charge beat itself (rather than an ordinary walking
        # report) and leaves the controller planted on phase zero.
        _mark_progress(temp)
        cand=0
    if l5_charged_full_face_alignment:
        # A c5 half->full elongated side alignment spends the charge without a
        # recoil, but its completion cue survives the otherwise-silent wrap.
        _mark_progress(temp)
    if l5_charged_full_face_departure:
        # Leaving an elongated full side face at c5 likewise spends the charge
        # as a visible alignment beat; side-tangential travel itself does not
        # recoil. Charged portal crossing is a separate head-on mechanism.
        _mark_progress(temp)
    if l5_charged_partial_face_entry:
        _mark_progress(temp)
    if vacated_l5_gate_slot_completion:
        _mark_progress(temp)
    if vacated_l5_gate_c2_projection_entry:
        # Like live displaced-gate half completion, this clocked projection
        # cue plants the completed alignment on phase zero.
        cand=0
    # A departure from the exact bridge still enters the token's diagonal
    # corner.  The replacement cue is visually silent only when the entire
    # colored assembly is in its monochrome all-13 phase.
    monochrome_bridge_departure=(colored_bridge_departure and
                                 not np.any(temp==12))
    if (cue and not l5_uncharged_normal_shell_entry and
        not l5_displaced_gate_half_face and
        not monochrome_bridge_departure and
        (not dial_wrap or unloaded_horizontal_lane or colored_bridge_dock or
         matching_frame_short_lane_visible_departed)):
        _mark_progress(temp)
    # A filled portal projects an elastic side around its flush token.  That
    # recoil is itself the single visible replacement beat; shaped-guide
    # far-face rejection remains silent.
    if token_projected_bounce:
        _mark_progress(temp)
    _l4_color_transfer(temp,action)
    _l5_color_transfer(temp,action,st,ai)
    # Entering a filled projection head-on is a visible replacement beat and
    # preserves the foot; a tangential corner turn still consumes its attempt.
    if token_projected_preserve and ai is not None:
        cand=st["objects"][ai]["phase"]
    # A differently shaped target axis is a board-level alignment
    # replacement: it mutes the arriving stride and preserves the planted foot.
    # Delayed evidence on departure distinguishes this from the matching-frame
    # lane, whose entry consumes the ordinary gait attempt.
    if (foreign_frame_lane_entered or matching_frame_prelane_entered) and ai is not None:
        cand=st["objects"][ai]["phase"]
    if passenger_corner_entry and ai is not None:
        cand=st["objects"][ai]["phase"]
    if (separator_core_departure or separator_channel_junction_entered or
        separator_channel_junction_crossed or
        separator_open_end_near_entry or
        solid_lane_departure or solid_portal_face_entry or
        matching_frame_short_lane_departed or
        matching_frame_short_lane_unpowered_departed or
        matching_frame_long_axis_departed or
        l5_rect_gate_left_corner_entry or
        (matching_frame_prelane_departed and
         ((act["w"]>act["h"] and action==4) or
          (act["h"]>act["w"] and action==2)))) and ai is not None:
        cand=st["objects"][ai]["phase"]
    # Most L5 routing cues are silent replacements which preserve the foot.
    # The remote c2->c3 axial-shell cue is deliberately absent here: it mutes
    # its report but consumes the ordinary gait foot.
    if ((l5_gate_axis_entry and l5_gate_axis_preserve) or
        l5_gate_axis_departure or l5_gate_preface_stage or
        l5_gate_pre_corner_stage or l5_gate_open_preface_entry or
        l5_gate_open_preface_tangent or l5_gate_open_preface_departure or
        l5_uncharged_full_face_alignment or
        l5_precharged_full_face_alignment or l5_rect_gate_corner_stage or
        l5_rect_gate_side_to_corner or l5_top_gate_contact or
        l5_half_separator_tangent or l5_gate_corner_to_face or
        vacated_l5_gate_anchor or vacated_l5_gate_open_corner_route or
        departed_vacated_l5_gate_open_corner_route or
        entered_vacated_l5_gate_open_corner_route or
        entered_vacated_l5_gate_outer_corner or
        l5_terminal_gate_wrap) and ai is not None:
        cand=st["objects"][ai]["phase"]
    if ((l5_charged_full_face_alignment or
         l5_charged_full_face_departure) and ai is not None):
        # The charged full-face alignment/departure pulse is visible but
        # consumes the planted stride; apply after preservation overrides.
        cand=0
    # Leaving a matching approach lane supplies the visible beat in place
    # of ordinary walking.  The elastic colored frame preserves the stored
    # foot (like the static-guide departure); solid target lanes close/reset
    # their alignment cycle.
    if (frame_lane_departed and not staged_near_solid and
        (not _l5_multi_gate_mode() or
         (action in (3,4) and act["w"]==act["h"]))):
        if colored_board:
            if (not dial_wrap or unloaded_horizontal_lane) and ai is not None:
                cand=st["objects"][ai]["phase"]
        else:
            cand=0
    # First projection onto an elastic frame axis is likewise a replacement
    # cue: it preserves the stored foot unless a silent dial carry suppresses it.
    if (frame_axis_entry or restored_frame_lane_entry) and colored_board and not dial_wrap and ai is not None:
        cand=st["objects"][ai]["phase"]
    # Tangential corner alignment with a detached colored token is the same
    # kind of replacement cue and therefore does not consume a walking foot.
    if (detached_token_corner or detached_token_axis_entry or
        colored_gate_corner_departure or colored_gate_rebound_departure or
        colored_gate_frame_lane_departure
        ) and not dial_wrap and ai is not None:
        cand=st["objects"][ai]["phase"]
    # Stepping out of the static guide reports the departure in place of the
    # walking beat, so it does not advance the stored foot.
    if (guide_corner_entry or entered_channel or departed_channel) and not dial_wrap and ai is not None:
        cand=st["objects"][ai]["phase"]
    if l5_uncharged_normal_shell_entry and ai is not None:
        # The delayed shell entry is the elastic second half of the hold and
        # preserves the same planted foot.
        cand=st["objects"][ai]["phase"]
    if ai is not None:
        st["objects"][ai]["x"]=nx
        st["objects"][ai]["y"]=ny
        st["objects"][ai]["phase"]=cand
        # A freshly released passenger keeps its launch carry while retreating
        # tangentially inside the supported gate's elastic open-face projection.
        # Manual passengers do not acquire this carry; any other normal stride
        # ends it.
        st["objects"][ai]["launched"]=bool(
            st["objects"][ai].get("launched",False) and
            l5_gate_open_preface_tangent)
        st["objects"][ai]["lateral_docking"]=bool(launched_lateral_frame_entry)
    st["l5_half_face_armed"]=bool(l5_rect_gate_half_face)
    if _goals_filled(temp):
        _finish(info)
    return temp.tolist(),info,st
