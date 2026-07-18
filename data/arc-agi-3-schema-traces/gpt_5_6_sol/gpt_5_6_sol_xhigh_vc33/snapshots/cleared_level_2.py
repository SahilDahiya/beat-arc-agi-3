import numpy as np

BASE = (0,3,4,5,7,9)

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

def _add_meter(g,turn):
    n = sum(v == 4 for v in g[0])
    framed = len(g) > 1 and all(v == 4 for v in g[1])
    # Clock rates are 5/4 cells/turn at full scale and 17/20 in the
    # framed board, with their observed rendering phases.
    target = ((17*turn+11)//20) if framed else ((5*turn+2)//4)
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
    return found

def _apply_coupled(g,x,y,axis0,axis1,space0,space1,unit,initial=None):
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

    if _all_aligned(g,bands,unit,space0 > 0,initial,
                    axis0,axis1,space0,space1):
        info['level_up'] = True
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
            shown = ((17*k+11)//20) if framed0 else ((5*k+2)//4)
            if shown == n0:
                turn = k
                break
    turn += 1
    _add_meter(g,turn)
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
        t,info = _apply_coupled(t,y,x,axis0,axis1,space0,space1,
                                max(1,_bands(t)[0][1]-_bands(t)[0][0]+1),et)
        g = [list(row) for row in zip(*t)]
    else:
        rows3 = [yy for yy,row in enumerate(g) if yy > 0 and 3 in row]
        axis0,axis1 = min(rows3),max(rows3)+1
        unit = max(1,_bands(g)[0][1]-_bands(g)[0][0]+1)
        g,info = _apply_coupled(g,x,y,axis0,axis1,0,len(g[0]),unit)

    # Restore all fixed pads (wall interval updates can expose their underlay).
    for xx,yy in pads:
        g[yy][xx] = 9
    return g,info,{'turn':turn}
