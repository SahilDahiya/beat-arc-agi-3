import numpy as np

BASE = (0,3,4,5,7,9,12)

def is_goal(grid):
    return False

def _bands(g):
    ys = []
    for y,row in enumerate(g):
        if 5 in row:
            ys.append(y)
    out = []
    if not ys:
        return out
    a = ys[0]
    p = a
    for y in ys[1:]:
        if y != p+1:
            out.append((a,p))
            a = y
        p = y
    out.append((a,p))
    return out

def _meter_target(g,turn):
    # The 64-cell meter is elapsed-turn fraction of the level budget,
    # rendered to the nearest cell. Standard levels have 50 turns,
    # the yellow-framed chain 75, and L4's two-arrow gate board 200.
    if CURRENT_LEVEL == 4:
        return (64*turn + 100)//200
    if CURRENT_LEVEL == 6:
        # Final star is long-budget like L4 (t1=0, t2=1 observed).
        return (64*turn + 100)//200
    framed = len(g) > 1 and all(v == 4 for v in g[1])
    if framed:
        return (64*turn + 37)//75
    return (64*turn + 25)//50

def _add_meter(g,turn):
    n = sum(v == 4 for v in g[0])
    target = _meter_target(g,turn)
    amount = max(0,target-n)
    for z in range(amount):
        for x in range(len(g[0])-1,-1,-1):
            if g[0][x] == 7:
                g[0][x] = 4
                break

def _boundary(row, side, marker_vals, lo, hi):
    def solid(v):
        return v == 3 or v == 4 or v in marker_vals
    if side == 'left':
        x = lo
        while x < hi and solid(row[x]):
            x += 1
        return x
    x = lo
    while x < hi and not solid(row[x]):
        x += 1
    return x

def _set_interval(g,y0,y1,old,new,side):
    a = min(old,new)
    b = max(old,new)
    expanding = (new > old) if side == 'left' else (new < old)
    src = 0 if expanding else 3
    dst = 3 if expanding else 0
    for y in range(y0,y1):
        for x in range(a,b):
            if g[y][x] == src:
                g[y][x] = dst

def _objects(g,y0,y1,x0,x1):
    # All colored arrows riding on one slab: connected color-4 plus a
    # non-background marker. Border color 4 has no marker and is ignored.
    seeds = []
    for y in range(y0,y1):
        for x in range(x0,x1):
            if g[y][x] not in BASE:
                seeds.append((x,y))
    seen = set()
    stack = seeds[:]
    while stack:
        x,y = stack.pop()
        if (x,y) in seen or not (x0 <= x < x1 and y0 <= y < y1):
            continue
        if g[y][x] == 4 or g[y][x] not in BASE:
            seen.add((x,y))
            stack.append((x-1,y))
            stack.append((x+1,y))
            stack.append((x,y-1))
            stack.append((x,y+1))
    return [(x,y,g[y][x]) for x,y in seen]

def _initial_geometry(initial,marker,unit):
    ib = _bands(initial)
    br = set()
    for a,b in ib:
        for y in range(a,b+1):
            br.add(y)
    target = []
    arrow = []
    for y,row in enumerate(initial):
        for x,v in enumerate(row):
            if v == marker:
                if y in br:
                    target.append(x)
                else:
                    arrow.append(x)
    if not target or not arrow:
        return None
    sign = 1 if min(arrow) > min(target) else -1
    return min(target) + sign*unit, sign

def _initial_stop(initial,marker,unit):
    z = _initial_geometry(initial,marker,unit)
    return None if z is None else z[0]

def _all_aligned(g,bands,unit,framed,initial,axis0=None,axis1=None,
                 space0=None,space1=None):
    bridge_rows = set()
    for a,b in bands:
        for y in range(a,b+1):
            bridge_rows.add(y)
    found = False
    for a,b in bands:
        marks = set()
        for y in range(a,b+1):
            for v in g[y]:
                if v not in BASE:
                    marks.add(v)
        for m in marks:
            target = []
            arrow = []
            arrow_axis = []
            for y,row in enumerate(g):
                for x,v in enumerate(row):
                    if v == m:
                        if a <= y <= b:
                            target.append(x)
                        elif y not in bridge_rows:
                            arrow.append(x)
                            arrow_axis.append(y)
            if arrow:
                found = True
                # As in the horizontal levels, the colored bars
                # themselves must share the target coordinate exactly.
                if min(target) != min(arrow):
                    return False
                # A target accepts its arrow from either immediately adjacent
                # chamber.  L4 confirms that the entry-facing side is not
                # privileged: the two arrows can finish on the opposite sides.
                bi = None
                for ii,(ia,ibb) in enumerate(bands):
                    if ia == a and ibb == b:
                        bi = ii
                        break
                if bi is not None:
                    chamber0 = (bands[bi-1][1]+1 if bi > 0
                                else (axis0 if axis0 is not None else 0))
                    chamber1 = (bands[bi+1][0] if bi+1 < len(bands)
                                else (axis1 if axis1 is not None else len(g)))
                    before = all(chamber0 <= q < a for q in arrow_axis)
                    after = all(b < q < chamber1 for q in arrow_axis)
                    if not (before or after):
                        return False
    return found

def _apply_coupled(g,x,y,axis0,axis1,space0,space1,unit,initial=None,goal_initial=None):
    info = {'level_up':False,'dead':False,'win':False}
    if g[y][x] != 9:
        return g,info

    bands = _bands(g)
    if not bands:
        return g,info

    bi = 0
    best = 100000
    for i,(a,b) in enumerate(bands):
        d = a-y if y < a else (y-b if y > b else 0)
        if d < best:
            best = d
            bi = i
    by0,by1 = bands[bi]
    upper0 = bands[bi-1][1]+1 if bi > 0 else axis0
    upper1 = by0
    lower0 = by1+1
    lower1 = bands[bi+1][0] if bi+1 < len(bands) else axis1

    # All arrow-marker colors are solid foreground when finding a slab edge.
    marker_vals = set()
    for row in g:
        for v in row:
            if v not in BASE:
                marker_vals.add(v)
    us = (upper0+upper1-1)//2
    ls = (lower0+lower1-1)//2
    side = 'left' if (g[ls][space0] == 3 or g[ls][space0] == 4 or
                      g[ls][space0] in marker_vals) else 'right'
    old_upper = _boundary(g[us],side,marker_vals,space0,space1)
    old_lower = _boundary(g[ls],side,marker_vals,space0,space1)

    click_above = y < by0
    if side == 'left':
        lower_delta = unit if click_above else -unit
    else:
        lower_delta = -unit if click_above else unit
    upper_delta = -lower_delta
    new_upper = old_upper+upper_delta
    new_lower = old_lower+lower_delta
    # A transfer is blocked if the donor lacks a full unit.
    if (new_upper < space0 or new_upper > space1 or
        new_lower < space0 or new_lower > space1):
        return g,info

    upper_obj = _objects(g,upper0,upper1,space0,space1)
    lower_obj = _objects(g,lower0,lower1,space0,space1)

    # If the moving donor carries this bridge's own target marker, the final
    # alignment transfer cannot dump its displaced unit through a receiver
    # that has just reached the outer capacity edge.  It must be aligned in
    # another chamber and then carried across the gate.  Nonmatching arrows
    # may still discharge surplus at that edge (observed on L4 bridge 3).
    donor_upper = ((side == 'left' and upper_delta < 0) or
                   (side == 'right' and upper_delta > 0))
    donor_obj = upper_obj if donor_upper else lower_obj
    receiver_new = new_lower if donor_upper else new_upper
    receiver_full = (receiver_new == (space1 if side == 'left' else space0))
    bridge_targets = set()
    for yy in range(by0,by1+1):
        for v in g[yy]:
            if v not in BASE:
                bridge_targets.add(v)
    # On the two-arrow gate board, a donor carrying its own bridge target
    # cannot be pulled past the common left edge of the gate system.  Finish
    # the remaining coordinate shift through a neighboring (non-target)
    # bridge instead; this is the routing constraint behind the final weave.
    gate_xs = [xx for row in g for xx,v in enumerate(row) if v == 1 or v == 12]
    donor_new = new_upper if donor_upper else new_lower
    locked_goal_chamber = False
    if CURRENT_LEVEL == 4 and donor_obj and goal_initial is not None:
        entry_bands = _bands(goal_initial)
        entry_bridge_rows = set()
        for aa,bb in entry_bands:
            for ry in range(aa,bb+1):
                entry_bridge_rows.add(ry)
        donor_chamber = bi if donor_upper else bi+1
        for xx,yy,v in donor_obj:
            target_i = None
            for jj,(aa,bb) in enumerate(entry_bands):
                if any(goal_initial[ry][rx] == v
                       for ry in range(aa,bb+1)
                       for rx in range(len(goal_initial[0]))):
                    target_i = jj
                    break
            init_ys = [ry for ry,row0 in enumerate(goal_initial)
                       for z in row0 if z == v and ry not in entry_bridge_rows]
            if target_i is not None and init_ys:
                aa,bb = entry_bands[target_i]
                goal_chamber = target_i if max(init_ys) < aa else target_i+1
                if donor_chamber == goal_chamber:
                    locked_goal_chamber = True
                    break
    if (gate_xs and donor_new < min(gate_xs) and locked_goal_chamber):
        return g,info

    # Framed reservoirs have limited native stock. Markerless donors can
    # draw one unit below their entry fill; upstream transfers replenish them.
    # A donor feeding a downstream arrow starts one unit short of the amount
    # needed to align that arrow, forcing stock to be routed through the chain.
    if initial is not None and space0 > 0:
        imarkers = set()
        for row in initial:
            for v in row:
                if v not in BASE:
                    imarkers.add(v)
        iupper = _boundary(initial[us],side,imarkers,space0,space1)
        ilower = _boundary(initial[ls],side,imarkers,space0,space1)
        if click_above and not upper_obj:
            if ((side == 'left' and new_upper < iupper-unit) or
                (side == 'right' and new_upper > iupper+unit)):
                return g,info
        if (not click_above) and not lower_obj:
            if ((side == 'left' and new_lower < ilower-unit) or
                (side == 'right' and new_lower > ilower+unit)):
                return g,info

        # Native stock limit for a marker-bearing downstream receiver.
        targets = set()
        for yy in range(by0,by1+1):
            for v in initial[yy]:
                if v not in BASE:
                    targets.add(v)
        if click_above and lower_obj and targets:
            for xx,yy,v in lower_obj:
                if v not in targets:
                    continue
                br = set()
                for aa,bb in _bands(initial):
                    for ry in range(aa,bb+1):
                        br.add(ry)
                itarget = []
                iarrow = []
                for ry,row in enumerate(initial):
                    for rx,z in enumerate(row):
                        if z == v:
                            (itarget if ry in br else iarrow).append(rx)
                if itarget and iarrow:
                    required = min(itarget)-min(iarrow)
                    if required*lower_delta > 0:
                        native_shift = required-lower_delta
                        donor_limit = iupper-native_shift
                        if ((upper_delta < 0 and new_upper < donor_limit) or
                            (upper_delta > 0 and new_upper > donor_limit)):
                            return g,info
    for xx,yy,v in upper_obj+lower_obj:
        g[yy][xx] = 3

    _set_interval(g,upper0,upper1,old_upper,new_upper,side)
    _set_interval(g,lower0,lower1,old_lower,new_lower,side)

    # Pads remain fixed foreground.
    # (Caller's grid copy still supplies their original positions.)
    for xx,yy,v in upper_obj:
        nx = xx+upper_delta
        if space0 <= nx < space1:
            g[yy][nx] = v
    for xx,yy,v in lower_obj:
        nx = xx+lower_delta
        if space0 <= nx < space1:
            g[yy][nx] = v

    if _all_aligned(g,bands,unit,space0 > 0,
                    goal_initial if goal_initial is not None else initial,
                    axis0,axis1,space0,space1):
        info['level_up'] = True
    return g,info

def _traverse_gate(g,cx,cy,axis0,axis1,space0,space1):
    # Clicking an activated (12) gate carries an aligned arrow component to
    # the same relative position in the chamber on the other side.
    if not (0 <= cy < len(g) and 0 <= cx < len(g[0])) or g[cy][cx] != 12:
        return False
    bands = _bands(g)
    bi = None
    for i,(a,b) in enumerate(bands):
        if a <= cy <= b:
            bi = i
            break
    if bi is None:
        return False
    a,b = bands[bi]
    lo = cx
    hi = cx
    while lo > 0 and any(g[yy][lo-1] == 12 for yy in range(a,b+1)):
        lo -= 1
    while hi+1 < len(g[0]) and any(g[yy][hi+1] == 12 for yy in range(a,b+1)):
        hi += 1
    upper0 = bands[bi-1][1]+1 if bi > 0 else axis0
    upper1 = a
    lower0 = b+1
    lower1 = bands[bi+1][0] if bi+1 < len(bands) else axis1
    upper = _objects(g,upper0,upper1,space0,space1)
    lower = _objects(g,lower0,lower1,space0,space1)
    choices = []
    if upper and min(p[0] for p in upper) >= lo and max(p[0] for p in upper) <= hi:
        omin = min(p[1] for p in upper)
        oh = max(p[1] for p in upper)-omin+1
        delta = lower0+(lower1-lower0-oh)//2-omin
        choices.append((upper,delta,lower0,lower1))
    if lower and min(p[0] for p in lower) >= lo and max(p[0] for p in lower) <= hi:
        omin = min(p[1] for p in lower)
        oh = max(p[1] for p in lower)-omin+1
        delta = upper0+(upper1-upper0-oh)//2-omin
        choices.append((lower,delta,upper0,upper1))
    if not choices:
        return False
    for obj,delta,d0,d1 in choices:
        if any(not (d0 <= yy+delta < d1) for xx,yy,v in obj):
            return False
    # With aligned arrows on both sides an activated gate swaps them.
    for obj,delta,d0,d1 in choices:
        for xx,yy,v in obj:
            g[yy][xx] = 3
    for obj,delta,d0,d1 in choices:
        for xx,yy,v in obj:
            g[yy+delta][xx] = v
    return True


def _activate_gates(g):
    # A color-1 section is active (12) exactly while the two neighboring
    # slab interfaces coincide just beyond its far edge.  Its inset side
    # vents are holes only in that active state; otherwise the natural slab
    # fill is restored.
    bands = _bands(g)
    marker_vals = set()
    for row in g:
        for v in row:
            if v not in BASE:
                marker_vals.add(v)
    for bi,(a,b) in enumerate(bands):
        xs = sorted(set(x for y in range(a,b+1)
                        for x,v in enumerate(g[y]) if v == 1 or v == 12))
        if not xs:
            continue
        groups = []
        lo = prev = xs[0]
        for x in xs[1:]:
            if x != prev+1:
                groups.append((lo,prev))
                lo = x
            prev = x
        groups.append((lo,prev))
        upper0 = bands[bi-1][1]+1 if bi > 0 else 0
        lower1 = bands[bi+1][0] if bi+1 < len(bands) else len(g)
        us = (upper0+a-1)//2
        ls = (b+1+lower1-1)//2
        bu = _boundary(g[us],'left',marker_vals,1,len(g[0]))
        bl = _boundary(g[ls],'left',marker_vals,1,len(g[0]))
        for lo,hi in groups:
            active = (bu == hi+1 and bl == hi+1)
            for yy in range(a,b+1):
                for xx in range(lo,hi+1):
                    if g[yy][xx] == 1 or g[yy][xx] == 12:
                        g[yy][xx] = 12 if active else 1
            ru = a-2
            rl = b+2
            if ru < 0 or rl >= len(g):
                continue
            for yy,bound in ((ru,bu),(rl,bl)):
                for xx in range(lo+2,hi-1):
                    g[yy][xx] = 0 if active or xx >= bound else 3




def _star_layout(g):
    # Final framed board: two vertical bridge columns and a horizontal divider
    # split four outer arms around one shared central reservoir.
    if CURRENT_LEVEL != 6:
        return None
    # Exclude the meter row: it is color 7/4 across the full screen and is
    # not part of the framed playfield.  Non-frame cells below it define the
    # fixed inner rectangle (x8..55, y8..55 on L6).
    inner_y=[y for y in range(1,len(g)) if any(v != 4 for v in g[y])]
    inner_x=[x for x in range(len(g[0]))
             if any(g[y][x] != 4 for y in inner_y)]
    if not inner_x or not inner_y:
        return None
    x0,x1=min(inner_x),max(inner_x)+1
    y0,y1=min(inner_y),max(inner_y)+1
    cols=[x for x in range(x0,x1)
          if sum(g[y][x] in (5,1,11,14,15) for y in range(y0,y1)) >= 12]
    groups=[]
    if cols:
        s=p=cols[0]
        for x in cols[1:]:
            if x != p+1:
                groups.append((s,p));s=x
            p=x
        groups.append((s,p))
    if len(groups) < 2:
        return None
    vg=(groups[0],groups[-1])
    rows=[y for y in range(y0,y1)
          if sum(g[y][x] == 5 for x in range(x0,x1)) >= 12]
    if not rows:
        return None
    return x0,x1,y0,y1,vg[0],vg[1],min(rows),max(rows)


def _vbound(g,x0,x1,y0,y1):
    marker=set(v for row in g for v in row if v not in BASE)
    xs=[x for x in range(x0,x1)
        if not any(g[y][x] not in BASE for y in range(y0,y1))
        and not any(g[y][x] == 9 for y in range(y0,min(y1,y0+3)))]
    x=xs[len(xs)//2] if xs else (x0+x1-1)//2
    y=y0
    while y<y1 and not (g[y][x] == 3 or g[y][x] == 4 or g[y][x] in marker):
        y+=1
    return y


def _set_vinterval(g,x0,x1,old,new):
    a=min(old,new);b=max(old,new)
    expanding=new<old
    src,dst=(0,3) if expanding else (3,0)
    for y in range(a,b):
        for x in range(x0,x1):
            if g[y][x] == src:
                g[y][x]=dst


def _apply_star(g,x,y,z):
    info={'level_up':False,'dead':False,'win':False}
    if g[y][x] != 9:
        return g,info
    x0,x1,y0,y1,v0,v1,ha,hb=z
    # Choose the nearby vertical bridge and its top/bottom outer arm.
    bridges=[v0,v1]
    bi=min(range(2),key=lambda i:min(abs(x-bridges[i][0]),abs(x-bridges[i][1])))
    vl,vr=bridges[bi]
    top=y < ha
    oy0,oy1=(y0,ha) if top else (hb+1,y1)
    if bi == 0:
        ox0,ox1=x0,vl
        central_click=x > vr
    else:
        ox0,ox1=vr+1,x1
        central_click=x < vl
    cx0,cx1=v0[1]+1,v1[0]
    co=_vbound(g,cx0,cx1,y0,y1)
    oo=_vbound(g,ox0,ox1,oy0,oy1)
    # Clicking the central-side pad donates shared stock to the outer arm.
    dc=2 if central_click else -2
    do=-dc
    cn,on=co+dc,oo+do
    if cn<y0 or cn>y1 or on<oy0 or on>oy1:
        return g,info
    cobj=_objects(g,y0,y1,cx0,cx1)
    oobj=_objects(g,oy0,oy1,ox0,ox1)
    for xx,yy,v in cobj+oobj:
        g[yy][xx]=3
    _set_vinterval(g,cx0,cx1,co,cn)
    _set_vinterval(g,ox0,ox1,oo,on)
    for xx,yy,v in cobj:
        ny=yy+dc
        if y0 <= ny < y1:g[ny][xx]=v
    for xx,yy,v in oobj:
        ny=yy+do
        if oy0 <= ny < oy1:g[ny][xx]=v
    return g,info


def _object_components(g,y0,y1,x0,x1):
    # Return each arrow separately.  The older _objects helper deliberately
    # unions all arrows riding one reservoir, but a gate only carries the
    # component whose full movement-axis span lies inside that gate.
    out=[]
    marks=sorted(set(g[y][x] for y in range(y0,y1) for x in range(x0,x1)
                     if g[y][x] not in BASE))
    for m in marks:
        stack=[(x,y) for y in range(y0,y1) for x in range(x0,x1)
               if g[y][x] == m]
        seen=set()
        while stack:
            x,y=stack.pop()
            if ((x,y) in seen or not (x0 <= x < x1 and y0 <= y < y1)
                    or g[y][x] not in (4,m)):
                continue
            seen.add((x,y))
            stack.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
        if seen:
            out.append([(x,y,g[y][x]) for x,y in seen])
    return out


def _traverse_star(g,x,y,z):
    if not (0 <= y < len(g) and 0 <= x < len(g[0])) or g[y][x] != 12:
        return False
    x0,x1,y0,y1,v0,v1,ha,hb=z
    which=None
    for bi,(vl,vr) in enumerate((v0,v1)):
        if vl <= x <= vr:
            which=(bi,vl,vr)
            break
    if which is None:
        return False
    bi,vl,vr=which
    ys=[yy for yy in range(y0,y1)
        if any(g[yy][xx] == 12 for xx in range(vl,vr+1))]
    if y not in ys:
        return False
    lo=hi=y
    while lo-1 in ys:lo-=1
    while hi+1 in ys:hi+=1
    top=y < ha
    oy0,oy1=(y0,ha) if top else (hb+1,y1)
    ox0,ox1=((x0,vl) if bi == 0 else (vr+1,x1))
    cx0,cx1=v0[1]+1,v1[0]
    choices=[]
    for obj,dx0,dx1 in [(q,cx0,cx1) for q in _object_components(g,oy0,oy1,ox0,ox1)]:
        if min(yy for xx,yy,v in obj) >= lo and max(yy for xx,yy,v in obj) <= hi:
            omin=min(xx for xx,yy,v in obj);ow=max(xx for xx,yy,v in obj)-omin+1
            choices.append((obj,dx0+(dx1-dx0-ow+1)//2-omin,dx0,dx1))
    for obj,dx0,dx1 in [(q,ox0,ox1) for q in _object_components(g,y0,y1,cx0,cx1)]:
        if min(yy for xx,yy,v in obj) >= lo and max(yy for xx,yy,v in obj) <= hi:
            omin=min(xx for xx,yy,v in obj);ow=max(xx for xx,yy,v in obj)-omin+1
            choices.append((obj,dx0+(dx1-dx0-ow+1)//2-omin,dx0,dx1))
    if not choices:
        return False
    if any(not (d0 <= xx+delta < d1)
           for obj,delta,d0,d1 in choices for xx,yy,v in obj):
        return False
    for obj,delta,d0,d1 in choices:
        for xx,yy,v in obj:g[yy][xx]=3
    for obj,delta,d0,d1 in choices:
        for xx,yy,v in obj:g[yy][xx+delta]=v
    return True


def _star_goal(g,z,initial):
    x0,x1,y0,y1,v0,v1,ha,hb=z
    cx0,cx1=v0[1]+1,v1[0]
    bridges=[v0,v1]
    found=False
    for bi,(vl,vr) in enumerate(bridges):
        marks=set(initial[yy][xx] for yy in range(y0,y1)
                  for xx in range(vl,vr+1)
                  if initial[yy][xx] not in BASE and initial[yy][xx] != 1)
        for m in marks:
            target=[yy for yy in range(y0,y1) for xx in range(vl,vr+1)
                    if initial[yy][xx] == m]
            arrow=[(xx,yy) for yy,row in enumerate(g) for xx,v in enumerate(row)
                   if v == m and not (vl <= xx <= vr)]
            if not arrow:
                continue
            found=True
            if min(yy for xx,yy in arrow) != min(target):
                return False
            top=min(target) < ha
            oy0,oy1=(y0,ha) if top else (hb+1,y1)
            ox0,ox1=((x0,vl) if bi == 0 else (vr+1,x1))
            center_ok=all(cx0 <= xx < cx1 and y0 <= yy < y1 for xx,yy in arrow)
            outer_ok=all(ox0 <= xx < ox1 and oy0 <= yy < oy1 for xx,yy in arrow)
            if not (center_ok or outer_ok):
                return False
    return found


def _activate_star(g,z,initial):
    # The final star reuses the conditional color-1 gates, rotated into the
    # vertical bridge columns.  A gate opens when the shared-center and its
    # particular outer-arm boundaries both meet the gate's upper edge.
    x0,x1,y0,y1,v0,v1,ha,hb=z
    cx0,cx1=v0[1]+1,v1[0]
    co=_vbound(g,cx0,cx1,y0,y1)
    for bi,(vl,vr) in enumerate((v0,v1)):
        for top,oy0,oy1 in ((True,y0,ha),(False,hb+1,y1)):
            ys=sorted(set(yy for yy in range(oy0,oy1)
                          if any(initial[yy][xx] == 1
                                 for xx in range(vl,vr+1))))
            if not ys:
                continue
            groups=[];lo=pr=ys[0]
            for yy in ys[1:]:
                if yy != pr+1:
                    groups.append((lo,pr));lo=yy
                pr=yy
            groups.append((lo,pr))
            ox0,ox1=((x0,vl) if bi == 0 else (vr+1,x1))
            oo=_vbound(g,ox0,ox1,oy0,oy1)
            for lo,hi in groups:
                active=(co == lo and oo == lo)
                for yy in range(lo,hi+1):
                    for xx in range(vl,vr+1):
                        if g[yy][xx] in (1,12):
                            g[yy][xx]=12 if active else 1
                # Active gates carve inset vents on both reservoir faces.
                for xx,bound in ((vl-2,oo if bi == 0 else co),
                                 (vr+2,co if bi == 0 else oo)):
                    if not (0 <= xx < len(g[0])):
                        continue
                    # Unit-2 bridges use a one-cell inset (observed rows
                    # 17..22 for gate 16..23), rather than the unit-3
                    # gates' two-cell inset.
                    for yy in range(lo+1,hi):
                        g[yy][xx]=0 if active else (3 if yy >= bound else 0)


def _crossed_layout(g):
    # L5: a horizontal bridge is split into two independently supplied
    # top reservoirs by a vertical wall; both feed one shared bottom slab.
    hrows = [y for y,row in enumerate(g)
             if sum(v == 5 or v == 1 or v == 12 or v not in BASE
                    for v in row) >= 20]
    if not hrows:
        return None
    a,b = min(hrows),max(hrows)
    # Keep only the compact three-row horizontal band.
    groups=[]; s=p=hrows[0]
    for y in hrows[1:]:
        if y != p+1:
            groups.append((s,p));s=y
        p=y
    groups.append((s,p))
    a,b=max(groups,key=lambda q: sum(g[y].count(5) for y in range(q[0],q[1]+1)))
    if b-a+1 > 4:
        return None
    cols=[]
    for x in range(len(g[0])):
        if sum(g[y][x] == 5 for y in range(1,a)) >= max(3,a//2):
            cols.append(x)
    if not cols:
        return None
    return a,b,min(cols),max(cols)


def _branch_objects(g,y0,y1,x0,x1):
    return _objects(g,y0,y1,x0,x1)



def _crossed_bounds(g,z):
    a,b,vl,vr=z
    marker_vals=set(v for row in g for v in row if v not in BASE)
    def sample(y0,y1,x0,x1):
        ys=[yy for yy in range(y0,y1)
            if not any(g[yy][xx] not in BASE for xx in range(x0,x1))]
        yy=ys[len(ys)//2] if ys else (y0+y1-1)//2
        return _boundary(g[yy],'right',marker_vals,x0,x1)
    left=sample(1,a,0,vl)
    right=sample(1,a,vr+1,len(g[0]))
    bottom=sample(b+1,len(g),0,len(g[0]))
    return left,right,bottom


def _activate_crossed(g,z):
    a,b,vl,vr=z
    left,right,bottom=_crossed_bounds(g,z)
    xs=sorted(set(x for yy in range(a,b+1) for x,v in enumerate(g[yy])
                  if v == 1 or v == 12))
    if not xs:
        return
    groups=[];lo=pr=xs[0]
    for x in xs[1:]:
        if x != pr+1:
            groups.append((lo,pr));lo=x
        pr=x
    groups.append((lo,pr))
    for lo,hi in groups:
        top=left if (lo+hi)//2 < vr else right
        active=(top == lo and bottom == lo)
        for yy in range(a,b+1):
            for xx in range(lo,hi+1):
                if g[yy][xx] == 1 or g[yy][xx] == 12:
                    g[yy][xx]=12 if active else 1
        for yy,bound in ((a-2,top),(b+2,bottom)):
            if 0 <= yy < len(g):
                for xx in range(lo+2,hi-1):
                    g[yy][xx]=0 if active else (3 if xx >= bound else 0)


def _traverse_crossed(g,cx,cy,z):
    a,b,vl,vr=z
    if not (a <= cy <= b and 0 <= cx < len(g[0]) and g[cy][cx] == 12):
        return False
    lo=hi=cx
    while lo>0 and any(g[yy][lo-1] == 12 for yy in range(a,b+1)):
        lo-=1
    while hi+1<len(g[0]) and any(g[yy][hi+1] == 12 for yy in range(a,b+1)):
        hi+=1
    tx0,tx1=(0,vl) if (lo+hi)//2 < vr else (vr+1,len(g[0]))
    top=_branch_objects(g,1,a,tx0,tx1)
    bottom=_branch_objects(g,b+1,len(g),0,len(g[0]))
    choices=[]
    if top and min(x for x,y,v in top) >= lo and max(x for x,y,v in top) <= hi:
        omin=min(y for x,y,v in top);oh=max(y for x,y,v in top)-omin+1
        d0,d1=b+1,len(g)
        delta=d0+(d1-d0-oh)//2-omin
        choices.append((top,delta,d0,d1))
    if bottom and min(x for x,y,v in bottom) >= lo and max(x for x,y,v in bottom) <= hi:
        omin=min(y for x,y,v in bottom);oh=max(y for x,y,v in bottom)-omin+1
        d0,d1=1,a
        delta=d0+(d1-d0-oh)//2-omin
        choices.append((bottom,delta,d0,d1))
    if not choices:
        return False
    for obj,delta,d0,d1 in choices:
        if any(not(d0 <= yy+delta < d1) for xx,yy,v in obj):
            return False
    for obj,delta,d0,d1 in choices:
        for xx,yy,v in obj:g[yy][xx]=3
    for obj,delta,d0,d1 in choices:
        for xx,yy,v in obj:g[yy+delta][xx]=v
    return True


def _crossed_goal(g,z):
    a,b,vl,vr=z
    bridge=set(range(a,b+1))
    marks=set(v for yy in bridge for v in g[yy] if v not in BASE)
    found=False
    for m in marks:
        target=[x for yy in bridge for x,v in enumerate(g[yy]) if v == m]
        arrow=[(x,yy) for yy,row in enumerate(g) for x,v in enumerate(row)
               if v == m and yy not in bridge]
        if not arrow:
            continue
        found=True
        if min(x for x,y in arrow) != min(target):
            return False
        # For a target in the right bridge segment, either top-right or the
        # shared bottom is adjacent (symmetrically for a left target).
        if min(target) > vr:
            top_ok=all(1 <= y < a and x > vr for x,y in arrow)
        else:
            top_ok=all(1 <= y < a and x < vl for x,y in arrow)
        bottom_ok=all(b < y < len(g) for x,y in arrow)
        if not(top_ok or bottom_ok):
            return False
    return found

def _apply_crossed(g,x,y,goal_initial):
    info={'level_up':False,'dead':False,'win':False}
    z=_crossed_layout(goal_initial)
    if z is None or g[y][x] != 9:
        return g,info
    a,b,vl,vr=z
    # Four pad components surround the bridge/wall junction.  The two upper
    # pads donate from their respective top reservoirs to the shared bottom
    # reservoir; the lower pads reverse that transfer.
    top = y < a
    left = x < vl
    ty0,ty1=1,a
    by0,by1=b+1,len(g)
    tx0,tx1=(0,vl) if left else (vr+1,len(g[0]))
    # Boundaries are left edges of right-filled reservoirs.
    marker_vals=set(v for row in g for v in row if v not in BASE)
    ts=(ty0+ty1-1)//2
    # Avoid the movable arrow when sampling if possible.
    sample_rows=[yy for yy in range(ty0,ty1)
                 if not any(g[yy][xx] not in BASE for xx in range(tx0,tx1))]
    if sample_rows:
        ts=sample_rows[len(sample_rows)//2]
    bs=(by0+by1-1)//2
    sample_bottom=[yy for yy in range(by0,by1)
                   if not any(g[yy][xx] not in BASE for xx in range(len(g[0])))]
    if sample_bottom:
        bs=sample_bottom[len(sample_bottom)//2]
    ot=_boundary(g[ts],'right',marker_vals,tx0,tx1)
    ob=_boundary(g[bs],'right',marker_vals,0,len(g[0]))
    dt=3 if top else -3
    db=-dt
    nt,nb=ot+dt,ob+db
    if nt < tx0 or nt > tx1 or nb < 0 or nb > len(g[0]):
        return g,info
    tobj=_branch_objects(g,ty0,ty1,tx0,tx1)
    bobj=_branch_objects(g,by0,by1,0,len(g[0]))
    for xx,yy,v in tobj+bobj:
        g[yy][xx]=3
    _set_interval(g,ty0,ty1,ot,nt,'right')
    _set_interval(g,by0,by1,ob,nb,'right')
    for xx,yy,v in tobj:
        nx=xx+dt
        if tx0 <= nx < tx1:
            g[yy][nx]=v
    for xx,yy,v in bobj:
        nx=xx+db
        if 0 <= nx < len(g[0]):
            g[yy][nx]=v
    return g,info

def init_state(entry_grid):
    return {'turn':0}

def predict(state,grid,action,x=None,y=None):
    g = [row[:] for row in grid]
    info = {'level_up':False,'dead':False,'win':False}
    turn = state.get('turn',0)
    if action != 6 or x is None or y is None:
        return g,info,{'turn':turn}

    # The very first recorded transition has no before-grid and is skipped
    # by backtest; recover that one missing state tick from its visible meter.
    n0 = sum(v == 4 for v in g[0])
    if turn == 0 and n0 > 0:
        framed0 = len(g) > 1 and all(v == 4 for v in g[1])
        for k in range(1,100):
            shown = _meter_target(g,k)
            if shown == n0:
                turn = k
                break
    turn += 1
    _add_meter(g,turn)
    # The final framed board is a five-node star reservoir graph.
    star=_star_layout(ENTRY_GRID)
    if star is not None:
        pads=[(xx,yy) for yy,row in enumerate(g) for xx,v in enumerate(row)
              if v == 9]
        traversed=_traverse_star(g,x,y,star)
        if not traversed:
            g,info=_apply_star(g,x,y,star)
        _activate_star(g,star,ENTRY_GRID)
        for xx,yy in pads:g[yy][xx]=9
        if _star_goal(g,star,ENTRY_GRID):
            if CURRENT_LEVEL == 6:
                info['win']=True
            else:
                info['level_up']=True
        return g,info,{'turn':turn}
    # The crossed L5 board is a branching reservoir graph rather than one
    # globally horizontal or vertical chain.
    crossed=_crossed_layout(ENTRY_GRID)
    if crossed is not None:
        pads=[(xx,yy) for yy,row in enumerate(g) for xx,v in enumerate(row)
              if v == 9]
        traversed=_traverse_crossed(g,x,y,crossed)
        if not traversed:
            g,info=_apply_crossed(g,x,y,ENTRY_GRID)
        _activate_crossed(g,crossed)
        for xx,yy in pads:
            g[yy][xx]=9
        if _crossed_goal(g,crossed):
            info['level_up']=True
        return g,info,{'turn':turn}
    # Determine whether gray bridges run horizontally or vertically.
    maxrow = max([sum(v == 5 for v in row) for row in g])
    maxcol = 0
    for xx in range(len(g[0])):
        c = sum(g[yy][xx] == 5 for yy in range(len(g)))
        if c > maxcol:
            maxcol = c
    vertical = maxcol > maxrow

    pads = [(xx,yy) for yy,row in enumerate(g) for xx,v in enumerate(row)
            if v == 9]
    if vertical:
        # Rotate by transpose; the same coupled-slab rule then applies.
        # The yellow frame is outside the playfield; include black empty
        # capacity inside it rather than mistaking current green extent for
        # the transfer limit.
        inner_rows = [yy for yy in range(1,len(g))
                      if any(v != 4 for v in g[yy])]
        space0,space1 = min(inner_rows),max(inner_rows)+1
        inner_cols = [xx for xx in range(len(g[0]))
                      if any(g[yy][xx] != 4 for yy in inner_rows)]
        axis0,axis1 = min(inner_cols),max(inner_cols)+1
        t = [list(row) for row in zip(*g)]
        et = [list(row) for row in zip(*ENTRY_GRID)]
        yellow_framed = len(g) > 1 and all(v == 4 for v in g[1])
        traversed = _traverse_gate(t,y,x,axis0,axis1,space0,space1)
        if not traversed:
            t,info = _apply_coupled(
                t,y,x,axis0,axis1,space0,space1,
                max(1,_bands(t)[0][1]-_bands(t)[0][0]+1),
                et if yellow_framed else None,et)
        _activate_gates(t)
        g = [list(row) for row in zip(*t)]
    else:
        rows3 = [yy for yy,row in enumerate(g) if yy > 0 and 3 in row]
        axis0,axis1 = min(rows3),max(rows3)+1
        unit = max(1,_bands(g)[0][1]-_bands(g)[0][0]+1)
        traversed = _traverse_gate(g,x,y,axis0,axis1,0,len(g[0]))
        if not traversed:
            g,info = _apply_coupled(g,x,y,axis0,axis1,0,len(g[0]),unit,
                                    None,ENTRY_GRID)
        _activate_gates(g)

    # Restore all fixed pads (wall interval updates can expose their underlay).
    for xx,yy in pads:
        g[yy][xx] = 9
    return g,info,{'turn':turn}
