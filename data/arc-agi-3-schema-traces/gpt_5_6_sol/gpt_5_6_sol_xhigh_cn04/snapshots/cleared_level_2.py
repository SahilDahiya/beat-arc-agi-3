import numpy as np
from collections import deque

def _background(a):
    return int(np.bincount(a.ravel(), minlength=16).argmax())


def _entry_object_count():
    e = np.array(ENTRY_GRID, dtype=int)
    bg = _background(e); allowed = ~np.isin(e, [bg, 4, 8])
    seen = np.zeros(e.shape, dtype=bool); count = 0
    for y, x in np.argwhere(allowed):
        if seen[y,x]: continue
        q = deque([(int(y),int(x))]); seen[y,x] = True; size = 0
        while q:
            yy, xx = q.popleft(); size += 1
            for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                ny, nx = yy+dy, xx+dx
                if (0 <= ny < e.shape[0] and 0 <= nx < e.shape[1] and
                    allowed[ny,nx] and not seen[ny,nx]):
                    seen[ny,nx] = True; q.append((ny,nx))
        if size >= 9: count += 1
    return count


def _largest_zero_component(a):
    seen = np.zeros(a.shape, dtype=bool)
    best = []
    h, w = a.shape
    for y, x in np.argwhere((a == 0) & (~seen)):
        if seen[y, x]:
            continue
        comp = []; q = deque([(int(y), int(x))]); seen[y, x] = True
        while q:
            yy, xx = q.popleft(); comp.append((yy, xx))
            for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                ny, nx = yy+dy, xx+dx
                if 0 <= ny < h and 0 <= nx < w and not seen[ny,nx] and a[ny,nx] == 0:
                    seen[ny,nx] = True; q.append((ny,nx))
        if len(comp) > len(best): best = comp
    return best


def _logical_phase():
    e = np.array(ENTRY_GRID, dtype=int); ep = np.argwhere(e == 8)
    return ((int(ep[:,1].min() % 3), int(ep[:,0].min() % 3))
            if len(ep) else (2,2))


def _as_blocks(cells, px, py):
    return {((int(x)-px)//3, (int(y)-py)//3) for y,x in cells}


def _entry_templates():
    # Recover each entry object's exact logical core and terminal-block shape.
    e = np.array(ENTRY_GRID, dtype=int); bg = _background(e); px, py = _logical_phase()
    allowed = ~np.isin(e, [bg,4,8]); seen = np.zeros(e.shape,dtype=bool)
    cores = []
    for y,x in np.argwhere(allowed):
        if seen[y,x]: continue
        comp=[]; q=deque([(int(y),int(x))]); seen[y,x]=True
        while q:
            yy,xx=q.popleft(); comp.append((yy,xx))
            for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                ny,nx=yy+dy,xx+dx
                if (0<=ny<e.shape[0] and 0<=nx<e.shape[1] and
                    allowed[ny,nx] and not seen[ny,nx]):
                    seen[ny,nx]=True; q.append((ny,nx))
        if len(comp)>=9: cores.append(_as_blocks(comp,px,py))
    all_ports = _as_blocks(np.argwhere(e==8),px,py)
    templates=[]
    for c in cores:
        p={z for z in all_ports if any(abs(z[0]-u[0])+abs(z[1]-u[1])==1 for u in c)}
        if not p: continue
        x0=min(x for x,y in c|p); y0=min(y for x,y in c|p)
        c={(x-x0,y-y0) for x,y in c}; p={(x-x0,y-y0) for x,y in p}
        templates.append((c,p))
    # In grey-piece layouts, inactive pieces are rendered wholly color4. Their
    # degree-1 logical blocks are latent terminals; selecting the piece reveals
    # those blocks as8 and its remaining blocks as the active core.
    blocks=set()
    for by in range((e.shape[0]-py)//3):
        for bx in range((e.shape[1]-px)//3):
            y0=py+3*by; x0=px+3*bx
            if np.all(e[y0:y0+3,x0:x0+3]==4): blocks.add((bx,by))
    remaining=set(blocks)
    while remaining:
        seed=remaining.pop(); comp={seed}; q=[seed]
        for u in q:
            for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)):
                if v in remaining: remaining.remove(v); comp.add(v); q.append(v)
        ends={u for u in comp if sum(v in comp for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)))==1}
        core=comp-ends
        if len(core)>=1 and len(ends)>=1:
            x0=min(x for x,y in comp); y0=min(y for x,y in comp)
            templates.append(({(x-x0,y-y0) for x,y in core},
                              {(x-x0,y-y0) for x,y in ends}))
    return templates


def _color4_endpoint_mask():
    """Pixel mask of degree-1 logical blocks in static color4 structures."""
    e=np.array(ENTRY_GRID,dtype=int); px,py=_logical_phase(); blocks=set()
    for by in range((e.shape[0]-py)//3):
        for bx in range((e.shape[1]-px)//3):
            y0=py+3*by; x0=px+3*bx
            if np.all(e[y0:y0+3,x0:x0+3]==4): blocks.add((bx,by))
    ends=set(); remaining=set(blocks)
    while remaining:
        seed=remaining.pop(); comp={seed}; q=[seed]
        for u in q:
            for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)):
                if v in remaining: remaining.remove(v); comp.add(v); q.append(v)
        if len(comp) >= 2:
            for u in comp:
                deg=sum(v in comp for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)))
                if deg==1: ends.add(u)
    mask=np.zeros(e.shape,dtype=bool)
    for bx,by in ends:
        x0=px+3*bx; y0=py+3*by; mask[y0:y0+3,x0:x0+3]=True
    return mask


def _rot_template(c,p):
    h=max(y for x,y in c|p)+1
    c2={(h-1-y,x) for x,y in c}; p2={(h-1-y,x) for x,y in p}
    x0=min(x for x,y in c2|p2); y0=min(y for x,y in c2|p2)
    return ({(x-x0,y-y0) for x,y in c2},
            {(x-x0,y-y0) for x,y in p2})


def _moving_mask(a):
    # Match the selected core to a rotated ENTRY template, then take exactly
    # that object's terminal blocks.  This remains unambiguous even when an
    # unrelated terminal is incidentally adjacent during a close pass.
    core = _largest_zero_component(a); mask=np.zeros(a.shape,dtype=bool)
    # Ignore the tiny black meter fragment on row0; a selected object core is
    # always at least one full 3x3 block.
    if len(core) < 9:
        core = []
    # Some later layouts have a single directly-controlled colored piece and
    # no black selection state. In that case use the largest non-background,
    # non-wall, non-terminal color component as its core.
    if not core:
        bg = _background(a); allowed = ~np.isin(a, [bg, 4, 8, 3])
        seen = np.zeros(a.shape, dtype=bool); best = []
        for y, x in np.argwhere(allowed):
            if seen[y,x]: continue
            color = int(a[y,x]); comp=[]; q=deque([(int(y),int(x))]); seen[y,x]=True
            while q:
                yy,xx=q.popleft(); comp.append((yy,xx))
                for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny,nx=yy+dy,xx+dx
                    if (0<=ny<a.shape[0] and 0<=nx<a.shape[1] and not seen[ny,nx]
                            and allowed[ny,nx] and int(a[ny,nx])==color):
                        seen[ny,nx]=True; q.append((ny,nx))
            if len(comp)>len(best): best=comp
        core=best
    if not core: return mask
    for y,x in core: mask[y,x]=True
    px,py=_logical_phase(); selected=_as_blocks(core,px,py)
    best=None; best_score=-1
    for c0,p0 in _entry_templates():
        c,p=c0,p0
        for k in range(4):
            tx=min(x for x,y in selected)-min(x for x,y in c)
            ty=min(y for x,y in selected)-min(y for x,y in c)
            cc={(x+tx,y+ty) for x,y in c}
            if cc==selected:
                pp={(x+tx,y+ty) for x,y in p}
                score=0
                for bx,by in pp:
                    x0=px+3*bx; y0=py+3*by
                    score+=int(np.sum(np.isin(a[y0:y0+3,x0:x0+3],[8,3])))
                if score>best_score: best_score=score; best=pp
            c,p=_rot_template(c,p)
    if best is not None:
        for bx,by in best:
            x0=px+3*bx; y0=py+3*by
            for yy in range(y0,min(y0+3,a.shape[0])):
                for xx in range(x0,min(x0+3,a.shape[1])):
                    if a[yy,xx] in (8,3): mask[yy,xx]=True
    return mask


def _place(a, mask, ny, nx, vals):
    ys, xs = np.where(mask)
    if (np.any(ny < 0) or np.any(ny >= a.shape[0]) or
        np.any(nx < 0) or np.any(nx >= a.shape[1])):
        return a, False, False
    bg = _background(a)
    move_vals = np.where(vals == 3, 8, vals)
    fixed = (a[ny,nx] != bg) & (~mask[ny,nx])
    # Pieces may pass through/occlude one another. Blue-on-blue terminals and
    # blue terminals covering degree-1 color4 endpoint blocks render purple3.
    endpoints = _color4_endpoint_mask()
    allowed_overlap = ((fixed & (move_vals == 8) & (a[ny,nx] == 8)) |
                       ((move_vals == 8) & endpoints[ny,nx]))
    out = a.copy(); out[ys,xs] = bg
    # Static color4 target/wall cells from the entry layer reappear when a
    # moving piece vacates them.
    entry = np.array(ENTRY_GRID, dtype=int)
    restore4 = (entry[ys,xs] == 4) & (ys != 0)
    out[ys[restore4], xs[restore4]] = 4
    # Pulling a piece out of a purple overlap restores the stationary
    # partner's terminal to blue; the moving terminal is blue as well.
    old_joint = (vals == 3)
    old_static = old_joint & (entry[ys,xs] == 4)
    out[ys[old_joint], xs[old_joint]] = 8
    out[ys[old_static], xs[old_static]] = 4
    out[ny,nx] = move_vals
    # Every exact 8-on-8 overlap welds into color 3.
    if np.any(allowed_overlap):
        out[ny[allowed_overlap], nx[allowed_overlap]] = 3
    # Complete when every free blue terminal has become a valid purple joint.
    docked = not np.any(out == 8)
    return out, True, docked


def _raw_step(grid, action, x=None, y=None):
    a = np.array(grid, dtype=int)
    info = {"level_up": False, "dead": False, "win": False}
    mask = _moving_mask(a)
    if not np.any(mask): return a.tolist(), info
    ys, xs = np.where(mask); vals = a[ys,xs].copy()

    delta = {1:(-3,0), 2:(3,0), 3:(0,-3), 4:(0,3)}
    if action in delta:
        dy, dx = delta[action]
        out, moved, docked = _place(a, mask, ys+dy, xs+dx, vals)
        info["level_up"] = docked
        return out.tolist(), info

    if action == 5:
        # Clockwise quarter-turn of the piece's tight bounding box, with its
        # top-left corner anchored.
        y0, x0 = int(ys.min()), int(xs.min())
        height = int(ys.max()-y0+1)
        ry, rx = ys-y0, xs-x0
        ny = y0 + rx
        nx = x0 + (height-1-ry)
        out, moved, docked = _place(a, mask, ny, nx, vals)
        info["level_up"] = docked
        return out.tolist(), info

    return a.tolist(), info


def _init_l2_pieces(entry_grid):
    e=np.array(entry_grid,dtype=int); px,py=_logical_phase()
    active_core=_as_blocks(np.argwhere(e==14),px,py)
    ports_all=_as_blocks(np.argwhere(e==8),px,py)
    active_ports={z for z in ports_all if any(abs(z[0]-u[0])+abs(z[1]-u[1])==1 for u in active_core)}
    pieces=[{"core":active_core,"ports":active_ports,"id":14}]
    blocks=set()
    for by in range((e.shape[0]-py)//3):
        for bx in range((e.shape[1]-px)//3):
            y0=py+3*by; x0=px+3*bx
            if np.all(e[y0:y0+3,x0:x0+3]==4): blocks.add((bx,by))
    comps=[]; rem=set(blocks)
    while rem:
        seed=rem.pop(); comp={seed}; q=[seed]
        for u in q:
            for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)):
                if v in rem: rem.remove(v); comp.add(v); q.append(v)
        if len(comp)>=2: comps.append(comp)
    for comp in sorted(comps,key=len):
        ends={u for u in comp if sum(v in comp for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)))==1}
        ident=0 if len(comp)<10 else 15
        pieces.append({"core":comp-ends,"ports":ends,"id":ident})
    return pieces


def _render_l2(pieces, selected, turn):
    e=np.array(ENTRY_GRID,dtype=int); bg=_background(e); px,py=_logical_phase()
    out=np.full(e.shape,bg,dtype=int); out[0]=e[0]
    # Inactive pieces are grey silhouettes including their latent terminals.
    for i,p in enumerate(pieces):
        if i==selected: continue
        for bx,by in p["core"]|p["ports"]:
            x0=px+3*bx; y0=py+3*by
            if 0<=x0<out.shape[1]-2 and 0<=y0<out.shape[0]-2:
                out[y0:y0+3,x0:x0+3]=4
    p=pieces[selected]
    for bx,by in p["core"]:
        x0=px+3*bx; y0=py+3*by
        if 0<=x0<out.shape[1]-2 and 0<=y0<out.shape[0]-2:
            out[y0:y0+3,x0:x0+3]=int(p["id"])
    latent=set()
    for i,q in enumerate(pieces):
        if i!=selected: latent |= q["ports"]
    for bx,by in p["ports"]:
        x0=px+3*bx; y0=py+3*by
        if 0<=x0<out.shape[1]-2 and 0<=y0<out.shape[0]-2:
            out[y0:y0+3,x0:x0+3]=3 if (bx,by) in latent else 8
    desired=int(np.ceil(max(0,turn)*32.0/128.0))
    out[0]=e[0]
    fours=np.where(out[0]==4)[0]
    for xx in fours[:desired]: out[0,xx]=0
    return out


def _predict_l2(state, grid, action, x=None, y=None):
    st=dict(state or {}); turn=int(st.get("turn",-1))+1
    raw=st.get("l2_pieces") or _init_l2_pieces(ENTRY_GRID)
    pieces=[{"core":set(p["core"]),"ports":set(p["ports"]),"id":int(p["id"])} for p in raw]
    selected=int(st.get("selected",0)); px,py=_logical_phase()
    if action==6 and x is not None and y is not None:
        bx=(int(x)-px)//3; by=(int(y)-py)//3; z=(bx,by)
        if int(x)>=px and int(y)>=py:
            for i,p in enumerate(pieces):
                if i!=selected and z in (p["core"]|p["ports"]):
                    selected=i; break
    elif action in (1,2,3,4):
        dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[action]
        p=pieces[selected]
        p["core"]={(bx+dx,by+dy) for bx,by in p["core"]}
        p["ports"]={(bx+dx,by+dy) for bx,by in p["ports"]}
    elif action==5:
        p=pieces[selected]; full=p["core"]|p["ports"]
        x0=min(bx for bx,by in full); y0=min(by for bx,by in full)
        h=max(by for bx,by in full)-y0+1
        p["core"]={(x0+h-1-(by-y0), y0+(bx-x0)) for bx,by in p["core"]}
        p["ports"]={(x0+h-1-(by-y0), y0+(bx-x0)) for bx,by in p["ports"]}
        # Quarter-turns keep the tight-box top-left unless the new box would
        # leave the board; then the whole piece is translated just far enough
        # back inside the complete 3x3 logical-cell playfield.
        full=p["core"]|p["ports"]
        maxbx=(64-px-3)//3; maxby=(64-py-3)//3
        dx=max(0-min(bx for bx,by in full), 0)
        dx+=min(0, maxbx-max(bx+dx for bx,by in full))
        dy=max(0-min(by for bx,by in full), 0)
        dy+=min(0, maxby-max(by+dy for bx,by in full))
        if dx or dy:
            p["core"]={(bx+dx,by+dy) for bx,by in p["core"]}
            p["ports"]={(bx+dx,by+dy) for bx,by in p["ports"]}
    out=_render_l2(pieces,selected,turn)
    counts={}
    for q in pieces:
        for z in q["ports"]: counts[z]=counts.get(z,0)+1
    complete=bool(counts) and all(v>=2 for v in counts.values())
    # A solved assembly may overlap only at paired terminal cells; occlusion is
    # allowed during manipulation but core/core or core/terminal overlap is not final.
    for i in range(len(pieces)):
        fi=pieces[i]["core"]|pieces[i]["ports"]
        for j in range(i+1,len(pieces)):
            fj=pieces[j]["core"]|pieces[j]["ports"]
            if (fi&fj) - (pieces[i]["ports"]&pieces[j]["ports"]):
                complete=False
    info={"level_up":complete,"dead":False,"win":False}
    ns={"turn":turn,"active_identity":int(pieces[selected]["id"]),"docked":0,
        "meter_mode":None,"meter_offset":0,"l2_pieces":pieces,"selected":selected}
    return out.tolist(),info,ns


def init_state(entry_grid):
    # Identity color 15 belongs to the initially-active black piece in L0-L1.
    # L2 instead keeps explicit object-layer poses because inactive grey pieces
    # occlude one another and must be re-rendered from their latent shapes.
    if CURRENT_LEVEL == 2:
        return {"turn":-1,"active_identity":14,"docked":0,
                "meter_mode":None,"meter_offset":0,
                "l2_pieces":_init_l2_pieces(entry_grid),"selected":0}
    return {"turn": 0 if CURRENT_LEVEL == 0 else -1,
            "active_identity": 15, "docked": 0,
            "meter_mode": None, "meter_offset": 0}


def _color_component(a, y, x):
    color = int(a[y,x]); seen = {(y,x)}; q = deque([(y,x)])
    while q:
        yy, xx = q.popleft()
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny, nx = yy+dy, xx+dx
            if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1] and (ny,nx) not in seen and a[ny,nx] == color:
                seen.add((ny,nx)); q.append((ny,nx))
    return seen


def _click_select(grid, x, y, active_identity):
    a = np.array(grid, dtype=int); bg = _background(a)
    if x is None or y is None or not (0 <= x < a.shape[1] and 0 <= y < a.shape[0]):
        return a.tolist(), active_identity
    c = int(a[y,x])
    if CURRENT_LEVEL == 2 and c == 4:
        e=np.array(ENTRY_GRID,dtype=int); px,py=_logical_phase()
        if int(e[y,x]) != 4:
            return a.tolist(), active_identity
        epix=_color_component(e,int(y),int(x))
        blocks=_as_blocks(epix,px,py)
        ends={u for u in blocks if sum(v in blocks for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)))==1}
        if not ends: return a.tolist(), active_identity
        # Hide the formerly active piece as grey, then reveal the clicked
        # piece's intrinsic core and its degree-1 terminal blocks.
        moving=_moving_mask(a); a[moving]=4
        new_color = 15 if len(blocks) > 10 else 0
        for bx,by in blocks:
            x0=px+3*bx; y0=py+3*by
            a[y0:y0+3,x0:x0+3] = 8 if (bx,by) in ends else new_color
        return a.tolist(), new_color
    if c in (bg, 0, 4, 8):
        return a.tolist(), active_identity
    clicked = _color_component(a, int(y), int(x))
    old = _largest_zero_component(a)
    for yy, xx in old: a[yy,xx] = int(active_identity)
    for yy, xx in clicked: a[yy,xx] = 0
    return a.tolist(), c


def predict(state, grid, action, x=None, y=None):
    if CURRENT_LEVEL == 2:
        return _predict_l2(state,grid,action,x,y)
    # All actions consume budget after the first free action of each level.
    st = dict(state or {})
    turn = int(st.get("turn", -1)) + 1
    active_identity = int(st.get("active_identity", 15))
    if action == 6:
        nxt, active_identity = _click_select(grid, x, y, active_identity)
        info = {"level_up": False, "dead": False, "win": False}
    else:
        nxt, info = _raw_step(grid, action, x, y)
    out = np.array(nxt, dtype=int)
    before_ports = int(np.sum(np.array(grid, dtype=int) == 3) // 9)
    after_ports = int(np.sum(out == 3) // 9)
    mode = st.get("meter_mode")
    offset = int(st.get("meter_offset", 0))
    if CURRENT_LEVEL == 0:
        budget, progress = 75, max(0, turn)
    elif CURRENT_LEVEL == 1:
        # The original exploratory route and the post-RESET clean route reveal
        # two distinct UI meter phases. Identify them from their second move.
        if mode is None and turn == 1 and action in (1,4):
            mode = "clean" if action == 1 else "explore"
        if mode == "clean":
            # In the clean phase the second completed assembly edge holds the
            # meter for one use; otherwise pixels advance every three uses.
            if before_ports == 2 and after_ports == 4:
                offset += 1
            budget, progress = 96, max(0, turn - offset)
        else:
            # Entry phase: 105-use scale plus one unit per complete edge.
            budget = 105
            progress = max(0, turn + after_ports // 2)
    elif CURRENT_LEVEL == 2:
        budget, progress = 135, max(0, turn)
    else:
        budget = 75 + 30 * int(CURRENT_LEVEL or 0)
        progress = max(0, turn)
    desired = int(np.ceil(progress * 32.0 / budget))
    black_meter = int(np.sum(out[0] == 0))
    while black_meter < desired:
        fours = np.where(out[0] == 4)[0]
        if not len(fours): break
        out[0, int(fours.min())] = 0
        black_meter += 1
    return out.tolist(), info, {"turn": turn,
                                "active_identity": active_identity,
                                "docked": int(st.get("docked", 0)),
                                "meter_mode": mode,
                                "meter_offset": offset}


def is_goal(state, grid):
    if CURRENT_LEVEL == 2 and state and state.get("l2_pieces"):
        pieces=state["l2_pieces"]; counts={}
        for q in pieces:
            for z in q["ports"]: counts[z]=counts.get(z,0)+1
        ok=bool(counts) and all(v>=2 for v in counts.values())
        for i in range(len(pieces)):
            fi=set(pieces[i]["core"])|set(pieces[i]["ports"])
            for j in range(i+1,len(pieces)):
                fj=set(pieces[j]["core"])|set(pieces[j]["ports"])
                if (fi&fj) - (set(pieces[i]["ports"])&set(pieces[j]["ports"])): ok=False
        return ok
    return not np.any(np.array(grid, dtype=int) == 8)
