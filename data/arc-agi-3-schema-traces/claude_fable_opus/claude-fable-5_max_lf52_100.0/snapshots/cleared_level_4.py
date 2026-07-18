# v14: PEG SOLITAIRE + UNDO + MULTI-CART + 2D WORLD/CAMERA + WALLS.
# Camera: informative-pixel anchor; camtrack = cart the camera follows (retargeted to a loaded
# cart on unpredicted snaps); lock mode dcam=tracked cart's delta; q8 formula mode for L2-style.
# The 64x64 frame is a VIEWPORT onto a wider world. Row 0 = HUD move counter (screen-anchored).
# State: world map (64 x 192, -1 unknown), base map (world w/o carts), cam x-offset, undo stack.
# Camera: follows the single LOADED cart: cam = max(0, ((cart_x+2-32)//8)*8); else unchanged.
# Mechanics (in world coords): cells = 4x4 patterns (blocks + cart cores); jumps over adjacent
# peg into empty cell 2 away; click peg->select+outlines, click target->jump, else deselect;
# arrows move ALL carts 6px along rails (center 2x2 on rails); 7=undo. Counter ticks always.
# level_up guess: total pegs (blocks+carts) == 1 after a jump.

E = 14
CC = 12
CART_RING = 11
WCANV = 192
HCANV = 192
H = 64  # legacy viewport height

def _pat_peg(c):
    return [[c,E,E,c],[E,E,E,E],[E,E,E,E],[c,E,E,c]]

def _pat_target(b):
    return [[b,2,2,b],[2,b,b,2],[2,b,b,2],[b,2,2,b]]

def _match(w, x0, y0, pat):
    for dy in range(4):
        for dx in range(4):
            if w[y0+dy][x0+dx] != pat[dy][dx]:
                return False
    return True

def _find_carts(w):
    Ww = len(w[0])
    carts = []
    for y in range(len(w) - 1):
        for x in range(Ww - 1):
            if w[y][x] == CART_RING and w[y][x+1] in (CART_RING, 3, 15) and w[y+1][x] in (CART_RING, 3):
                core = (x + 1, y + 1)
                vals = {w[core[1]+dy][core[0]+dx]
                        for dy in range(4) for dx in range(4)
                        if core[1]+dy < len(w) and core[0]+dx < Ww}
                if vals and (vals <= {CC, E, 2, 3} or vals <= {15, 0, 7, 5}):
                    if not any(c == core for c in carts):
                        carts.append(core)
    return carts

def _cart_kind(w, cx, cy):
    vals = [w[cy+dy][cx+dx] for dy in range(4) for dx in range(4)]
    sel = w[cy][cx] == 3
    if 15 in vals:
        return ('wall', False, True)
    if E in vals:
        return ('peg', sel, True)
    if 2 in vals:
        return ('target', False, True)
    return ('empty', False, True)

def _find_cells(w):
    Ww = len(w[0])
    cells = {}
    for y in range(1, len(w) - 3):
        for x in range(1, Ww - 3):
            v = w[y][x]
            if v == 1:
                if w[y][x-1] != 1 and w[y-1][x] != 1 and _match(w, x, y, [[1]*4]*4):
                    cells[(x, y)] = ('empty', False, False)
                elif _match(w, x, y, _pat_peg(1)):
                    cells[(x, y)] = ('peg', False, False)
                elif _match(w, x, y, _pat_target(1)):
                    cells[(x, y)] = ('target', False, False)
            elif v == 3:
                if _match(w, x, y, _pat_peg(3)):
                    cells[(x, y)] = ('peg', True, False)
    WALL_PAT = [[15,15,15,15],[15,0,7,15],[15,7,7,15],[15,15,15,15],[5,5,5,5]]
    for y in range(2, len(w) - 4):
        for x in range(1, Ww - 3):
            if w[y-1][x] == 15 and w[y][x] == 15:
                ok = True
                for dy in range(5):
                    for dx in range(4):
                        if w[y-1+dy][x+dx] != WALL_PAT[dy][dx]:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    cells[(x, y)] = ('wall', False, False)
    for (cx, cy) in _find_carts(w):
        cells[(cx, cy)] = _cart_kind(w, cx, cy)
    return cells

def _rails(base):
    Ww = len(base[0])
    Hh = len(base)
    rails = set()
    for y in range(Hh - 1):
        for x in range(Ww):
            if base[y][x] == 5 and base[y+1][x] == 5:
                above = base[y-1][x] if y > 0 else 10
                below = base[y+2][x] if y + 2 < Hh else 10
                if above != 5 and below != 5:
                    rails.add((x, y)); rails.add((x, y+1))
    for y in range(Hh):
        for x in range(Ww - 1):
            if base[y][x] == 5 and base[y][x+1] == 5:
                left = base[y][x-1] if x > 0 else 10
                right = base[y][x+2] if x + 2 < Ww else 10
                if left != 5 and right != 5:
                    rails.add((x, y)); rails.add((x+1, y))
    for _ in range(3):
        added = []
        for y in range(Hh):
            for x in range(Ww):
                if base[y][x] == 5 and (x, y) not in rails:
                    n = sum(1 for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))
                            if (x+dx, y+dy) in rails)
                    if n >= 2:
                        added.append((x, y))
        if not added:
            break
        rails.update(added)
    return rails

def _fill_cart_holes(base, carts):
    # ground under carts: extend 2px rail bands through the footprint, else background
    for (ex, ey) in carts:
        xs = range(ex - 2, ex + 7)
        ys = range(ey - 2, ey + 7)
        horiz = (0 <= ex-3 and base[ey+1][ex-3] == 5 and base[ey+2][ex-3] == 5) or \
                (ex+6 < len(base[0]) and base[ey+1][ex+6] == 5 and base[ey+2][ex+6] == 5)
        vert = (0 <= ey-3 and base[ey-3][ex+1] == 5 and base[ey-3][ex+2] == 5) or \
               (ey+6 < len(base) and base[ey+6][ex+1] == 5 and base[ey+6][ex+2] == 5)
        for y in ys:
            for x in xs:
                if 0 <= y < len(base) and 0 <= x < len(base[0]):
                    v = 10
                    if horiz and y in (ey+1, ey+2):
                        v = 5
                    if vert and x in (ex+1, ex+2):
                        v = 5
                    base[y][x] = v

def _erase_cart(w, cx, cy, base):
    for y in range(cy - 2, cy + 7):
        for x in range(cx - 2, cx + 7):
            if 0 <= y < len(w) and 0 <= x < len(w[0]):
                w[y][x] = base[y][x] if base[y][x] != -1 else 10

def _paint_cart(w, cx, cy, loaded, base):
    Ww = len(w[0])
    Hh = len(w)
    def bval(yy, xx):
        if 0 <= yy < Hh and 0 <= xx < Ww:
            return base[yy][xx]
        return -2
    def _set(yy, xx, v):
        if 0 <= yy < Hh and 0 <= xx < Ww:
            w[yy][xx] = v
    for i in range(8):
        for (xx, yy) in ((cx-2+i, cy-2), (cx-2+i, cy+5), (cx-2, cy-2+i), (cx+5, cy-2+i)):
            if bval(yy, xx) in (10, 5, 9, -1):
                _set(yy, xx, 5)
    for i in range(6):
        _set(cy-1, cx-1+i, CART_RING)
        _set(cy+4, cx-1+i, CART_RING)
        _set(cy-1+i, cx-1, CART_RING)
        _set(cy-1+i, cx+4, CART_RING)
    if loaded == 'wall':
        WP = [[15,15,15,15],[15,0,7,15],[15,7,7,15],[15,15,15,15],[5,5,5,5]]
        for dx in range(4):
            _set(cy-1, cx+dx, WP[0][dx])
        for dy in range(4):
            for dx in range(4):
                _set(cy+dy, cx+dx, WP[dy+1][dx])
    else:
        pat = _pat_peg(CC) if loaded else [[CC]*4 for _ in range(4)]
        for dy in range(4):
            for dx in range(4):
                _set(cy+dy, cx+dx, pat[dy][dx])
    for y in range(cy - 1, cy + 7):
        if 0 <= y < Hh and cx+6 < Ww and w[y][cx+6] == 10:
            w[y][cx+6] = 9
    for x in range(cx - 1, cx + 7):
        if cy + 6 < Hh and 0 <= x < Ww and w[cy+6][x] == 10:
            w[cy+6][x] = 9

def _adjacent(cells, b, d):
    bx, by = b
    best = None
    for (x0, y0) in cells:
        if d[0] != 0:
            if y0 != by:
                continue
            dist = (x0 - bx) * d[0]
        else:
            if x0 != bx:
                continue
            dist = (y0 - by) * d[1]
        if dist <= 0:
            continue
        if best is None or dist < best[0]:
            best = (dist, (x0, y0))
    if best is not None and best[0] <= 8:
        return best[1]
    return None

def _draw(w, cell, cells_meta, kind, sel=False):
    x0, y0 = cell
    is_cart = cells_meta.get(cell, (None, None, False))[2]
    b = CC if is_cart else 1
    if kind == 'empty':
        pat = [[b]*4 for _ in range(4)]
    elif kind == 'peg':
        c = 3 if sel else b
        pat = _pat_peg(c)
    else:
        pat = _pat_target(b)
    for dy in range(4):
        for dx in range(4):
            w[y0+dy][x0+dx] = pat[dy][dx]

def _ring(w, cell, on, cells_meta):
    x0, y0 = cell
    is_cart = cells_meta.get(cell, (None, None, False))[2]
    v = 3 if on else (CART_RING if is_cart else 0)
    for dx in range(4):
        w[y0-1][x0+dx] = v
        w[y0+4][x0+dx] = v
    for dy in range(4):
        w[y0+dy][x0-1] = v
        w[y0+dy][x0+4] = v

def _clear_sel(w, cells):
    for b, (k, s, isc) in cells.items():
        if k == 'peg' and s:
            _draw(w, b, cells, 'peg', sel=False)
            _ring(w, b, False, cells)
        elif k == 'target':
            _draw(w, b, cells, 'empty')

def _tick(row):
    r = row[:]
    m = min(r)
    for i, v in enumerate(r):
        if v == m:
            r[i] = v + 1
            break
    return r

def _count_pegs(w):
    cells = _find_cells(w)
    return sum(1 for k, s, isc in cells.values() if k == 'peg')

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
ARROW_DIR = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}

def _anchor_score(world, grid, cx, cy):
    score = 0
    tot = 0
    sinf = 0
    tinf = 0
    for y in range(1, 64):
        wr = world[cy + y]
        gr = grid[y]
        for x in range(64):
            wv = wr[x + cx]
            if wv != -1:
                gv = gr[x]
                tot += 1
                m = 1 if wv == gv else 0
                score += m
                if wv != 10 or gv != 10:
                    tinf += 1
                    sinf += m
    return score, tot, sinf, tinf

def _anchor(world, grid, prev_cam):
    px, py = prev_cam
    s, t, si, ti = _anchor_score(world, grid, px, py)
    if ti > 300 and si >= 0.97 * ti:
        return (px, py)
    def search(x0, x1, y0, y1, step):
        best = (-1.0, prev_cam)
        for cy in range(max(0, y0), min(HCANV - 64, y1) + 1, step):
            for cx in range(max(0, x0), min(WCANV - 64, x1) + 1, step):
                sc, tt, sinf, tinf = _anchor_score(world, grid, cx, cy)
                if tinf < 300:
                    continue
                frac = sinf / tinf
                if frac > best[0]:
                    best = (frac, (cx, cy))
        return best
    b = search(px - 40, px + 40, py - 12, py + 12, 1)
    if b[0] >= 0.98:
        return b[1]
    b2 = search(0, WCANV - 64, 0, HCANV - 64, 2)
    if b2[0] > b[0]:
        bx, by = b2[1]
        b3 = search(bx - 2, bx + 2, by - 2, by + 2, 1)
        if b3[0] >= b2[0]:
            return b3[1]
        return b2[1]
    return b[1]

def _cart_mask(world):
    carts = _find_carts(world)
    fp = set()
    Ww = len(world[0])
    for (cx, cy) in carts:
        for y in range(cy - 2, cy + 6):
            for x in range(cx - 2, cx + 6):
                fp.add((x, y))
        for y in range(cy - 1, cy + 7):
            if 0 <= y < len(world) and cx + 6 < Ww and world[y][cx + 6] == 9:
                fp.add((cx + 6, y))
        for x in range(cx - 1, cx + 7):
            if cy + 6 < len(world) and 0 <= x < Ww and world[cy + 6][x] == 9:
                fp.add((x, cy + 6))
    return fp

def _sync_base(world, base):
    fp = _cart_mask(world)
    Ww = len(world[0])
    for y in range(1, len(world)):
        for x in range(Ww):
            if world[y][x] != -1 and (x, y) not in fp:
                base[y][x] = world[y][x]

def _merge(world, base, grid, cam):
    cx, cy = cam
    for y in range(1, 64):
        for x in range(64):
            world[cy + y][cx + x] = grid[y][x]
    _sync_base(world, base)

def _snapshot(world, base, cam):
    return ([r[:] for r in world], [r[:] for r in base], cam)

def init_state(entry_grid):
    world = [[-1] * WCANV for _ in range(HCANV)]
    base = [[-1] * WCANV for _ in range(HCANV)]
    for y in range(1, 64):
        for x in range(64):
            world[y][x] = entry_grid[y][x]
            base[y][x] = entry_grid[y][x]
    carts = _find_carts(world)
    _fill_cart_holes(base, carts)
    return {"stack": [], "world": world, "base": base, "cam": (0, 0),
            "wtrue": 64, "htrue": 64, "wanted": (0, 0)}

def predict(state, grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    if not isinstance(state, dict) or "world" not in state:
        state = init_state(grid)
    world = [r[:] for r in state["world"]]
    base = [r[:] for r in state["base"]]
    cam = state["cam"]
    if isinstance(cam, int):
        cam = (cam, 0)
    stack = state["stack"]
    wtrue = state.get("wtrue", 64)
    htrue = state.get("htrue", 64)
    wanted = state.get("wanted", cam)
    cammode = state.get("cammode")
    campreds = state.get("campreds")
    camtrack = state.get("camtrack")
    prevcam0 = cam
    cam = _anchor(world, grid, cam)
    if campreds and cammode is None:
        for mode, pc in campreds.items():
            if tuple(pc) == tuple(cam):
                cammode = mode
                break
    if wtrue is not None and cam[0] > wtrue - 64:
        wtrue = None  # world wider than believed
    if cam[0] < wanted[0]:
        wtrue = cam[0] + 64  # observed clamp: learn right edge
    if htrue is not None and cam[1] > htrue - 64:
        htrue = None
    if cam[1] < wanted[1]:
        htrue = cam[1] + 64
    _merge(world, base, grid, cam)
    if tuple(cam) != tuple(prevcam0):
        # unpredicted pan (snap): re-target camera tracking to a loaded cart
        cs = _find_carts(world)
        ld = [c for c in cs if _cart_kind(world, c[0], c[1])[0] == 'peg']
        if ld:
            camtrack = ld[0]
    row0 = _tick(grid[0])
    camwant = [None]

    def render(w, c):
        _sync_base(w, base)
        out = [row0]
        for yy in range(1, 64):
            out.append([w[c[1] + yy][xx + c[0]] if w[c[1] + yy][xx + c[0]] != -1 else 10
                        for xx in range(64)])
        return out

    if action == 7:
        if stack:
            world2, base2, cam2 = stack[-1]
            world2 = [r[:] for r in world2]
            base2 = [r[:] for r in base2]
            return render(world2, cam2), info, {
                "stack": stack[:-1], "world": world2, "base": base2, "cam": cam2,
                "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}
        return render(world, cam), info, {
            "stack": stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}

    new_stack = stack + [_snapshot(world, base, cam)]
    cells = _find_cells(world)

    def cam_update(c):
        carts = _find_carts(world)
        loaded = [cc for cc in carts if _cart_kind(world, cc[0], cc[1])[0] == 'peg']
        if loaded and carts:
            vx = max(0, ((carts[0][0] + 2 - 32) // 8) * 8)
            capx = (wtrue - 64) if wtrue is not None else (WCANV - 64)
            vy = max(0, ((carts[0][1] + 2 - 32) // 8) * 8)
            capy = (htrue - 64) if htrue is not None else (HCANV - 64)
            camwant[0] = (vx, vy)
            return (min(vx, max(0, capx)), min(vy, max(0, capy)))
        return c

    if action in ARROW_DIR:
        carts = _find_carts(world)
        dx, dy = ARROW_DIR[action]
        rails = _rails(base)
        moves = []
        for (cx, cy) in carts:
            tx, ty = cx + 6 * dx, cy + 6 * dy
            if tx < 0 or ty < 0 or tx + 3 >= WCANV or ty + 3 >= HCANV:
                continue
            ok = all((xx, yy) in rails
                     for xx in (tx + 1, tx + 2) for yy in (ty + 1, ty + 2))
            if ok:
                k = _cart_kind(world, cx, cy)[0]
                loaded = 'wall' if k == 'wall' else (k == 'peg')
                moves.append(((cx, cy), (tx, ty), loaded))
        campreds = None
        if moves:
            _clear_sel(world, cells)
            for (old, new, loaded) in moves:
                _erase_cart(world, old[0], old[1], base)
            for (old, new, loaded) in moves:
                _paint_cart(world, new[0], new[1], loaded, base)
            anyloaded = any(l is True for (_o, _n, l) in moves) or any(
                _cart_kind(world, c[0], c[1])[0] == 'peg' for c in _find_carts(world))
            if anyloaded:
                mdx, mdy = 0, 0
                src_mv = None
                if camtrack is not None:
                    for (o, n, l) in moves:
                        if tuple(o) == tuple(camtrack):
                            src_mv = (o, n)
                            break
                elif moves:
                    src_mv = (moves[0][0], moves[0][1])
                if src_mv is not None:
                    mdx = src_mv[1][0] - src_mv[0][0]
                    mdy = src_mv[1][1] - src_mv[0][1]
                    if camtrack is not None:
                        camtrack = src_mv[1]
                capx = (wtrue - 64) if wtrue is not None else (WCANV - 64)
                capy = (htrue - 64) if htrue is not None else (HCANV - 64)
                lock = (max(0, min(max(0, capx), cam[0] + mdx)),
                        max(0, min(max(0, capy), cam[1] + mdy)))
                q8 = cam_update(cam)
                campreds = {"lock": lock, "q8": q8}
                cam = campreds.get(cammode or "lock", lock)
        return render(world, cam), info, {
            "stack": new_stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}

    if action != 6:
        return render(world, cam), info, {
            "stack": new_stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}

    wx = x + cam[0]
    wy = y + cam[1]
    clicked = None
    for (bx, by) in cells:
        if bx <= wx <= bx + 3 and by <= wy <= by + 3:
            clicked = (bx, by)
            break
    if clicked is None:
        _clear_sel(world, cells)
        return render(world, cam), info, {
            "stack": new_stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}
    kind, sel, isc = cells[clicked]
    selected = [b for b, (k, s, i2) in cells.items() if k == 'peg' and s]
    if kind == 'peg':
        lands = []
        for d in DIRS:
            mid = _adjacent(cells, clicked, d)
            if mid is None or cells[mid][0] not in ('peg', 'wall'):
                continue
            land = _adjacent(cells, mid, d)
            if land is not None and cells[land][0] in ('empty', 'target'):
                lands.append(land)
        if lands:
            _clear_sel(world, cells)
            _draw(world, clicked, cells, 'peg', sel=True)
            _ring(world, clicked, True, cells)
            for land in lands:
                _draw(world, land, cells, 'target')
        return render(world, cam), info, {
            "stack": new_stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}
    if kind == 'target' and selected:
        s = selected[0]
        mid = None
        for d in DIRS:
            m = _adjacent(cells, s, d)
            if m is None:
                continue
            l = _adjacent(cells, m, d)
            if l == clicked:
                mid = m
                break
        for b, (k, ss, i2) in cells.items():
            if k == 'target':
                _draw(world, b, cells, 'empty')
        _draw(world, s, cells, 'empty')
        _ring(world, s, False, cells)
        if mid is not None and cells[mid][0] == 'peg':
            _draw(world, mid, cells, 'empty')
        _draw(world, clicked, cells, 'peg')
        if _count_pegs(world) == 1:
            info["level_up"] = True
        return render(world, cam), info, {
            "stack": new_stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}
    _clear_sel(world, cells)
    return render(world, cam), info, {
        "stack": new_stack, "world": world, "base": base, "cam": cam, "wtrue": wtrue, "htrue": htrue, "wanted": camwant[0] or cam, "cammode": cammode, "campreds": campreds if action in ARROW_DIR else None, "camtrack": camtrack}

def is_goal(state, grid):
    if not isinstance(state, dict) or "world" not in state:
        return _count_pegs(grid) == 1
    return _count_pegs(state["world"]) == 1