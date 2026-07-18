# v7: PEG SOLITAIRE + UNDO(7) + CART on rails + DOCKING (cart core = extra cell).
# Cells detected from CURRENT grid by exact 4x4 pattern match:
#   block empty: all 1; peg: corners 1 rest 14; selected peg: corners 3 rest 14;
#   target: 1/2 hollow diamond. Cart core (ring b=11): empty=all 12, loaded=corners 12 rest 14,
#   target-in-cart (GUESS): 12/2 hollow diamond.
# Adjacency: nearest cell in direction, center gap <= 8 (pitch 6). Docked cart core sits 6 from
# edge block -> participates in jumps like a block.
# Click peg/loaded-cart with legal jump -> select + outlines; click outlined target -> jump;
# click elsewhere -> deselect. 7 = undo (stack; counter still ticks). Arrows move cart on rails
# (6px, center 2x2 on rails); success clears selection. DOCK/UNDOCK reflow NOT modeled (hand-play).
# level_up guess: total pegs (blocks + cart) == 1 after a jump.

E = 14
CC = 12  # cart core color
CART_RING = 11

def _pat_empty():
    return [[1]*4 for _ in range(4)]

def _pat_peg(corner):
    return [[corner,E,E,corner],[E,E,E,E],[E,E,E,E],[corner,E,E,corner]]

def _pat_target(base):
    return [[base,2,2,base],[2,base,base,2],[2,base,base,2],[base,2,2,base]]

def _match(g, x0, y0, pat):
    for dy in range(4):
        for dx in range(4):
            if g[y0+dy][x0+dx] != pat[dy][dx]:
                return False
    return True

def _find_cart(g):
    for y in range(len(g)):
        for x in range(len(g[0])):
            if g[y][x] == CART_RING:
                return (x + 1, y + 1)
    return None

def _find_cells(g):
    """Return dict (x0,y0) -> (kind, selected, is_cart). Kinds: empty/peg/target."""
    H = len(g); W = len(g[0])
    cells = {}
    for y in range(1, H - 3):
        for x in range(W - 3):
            v = g[y][x]
            if v == 1:
                if _match(g, x, y, _pat_empty()) and (x, y):
                    # avoid matching interior of a larger 1-field: require left/up not 1
                    if g[y][x-1] != 1 and g[y-1][x] != 1:
                        cells[(x, y)] = ('empty', False, False)
                elif _match(g, x, y, _pat_peg(1)):
                    cells[(x, y)] = ('peg', False, False)
                elif _match(g, x, y, _pat_target(1)):
                    cells[(x, y)] = ('target', False, False)
            elif v == 3:
                if _match(g, x, y, _pat_peg(3)):
                    cells[(x, y)] = ('peg', True, False)
    cart = _find_cart(g)
    if cart is not None:
        cx, cy = cart
        if _match(g, cx, cy, [[CC]*4 for _ in range(4)]):
            cells[(cx, cy)] = ('empty', False, True)
        elif _match(g, cx, cy, _pat_peg(CC)):
            cells[(cx, cy)] = ('peg', False, True)
        elif _match(g, cx, cy, _pat_target(CC)):
            cells[(cx, cy)] = ('target', False, True)
        elif _match(g, cx, cy, _pat_peg(3)):
            cells[(cx, cy)] = ('peg', True, True)
    return cells

def _rails(entry):
    H = len(entry); W = len(entry[0])
    rails = set()
    for y in range(H - 1):
        for x in range(W):
            if entry[y][x] == 5 and entry[y+1][x] == 5:
                above = entry[y-1][x] if y > 0 else 10
                below = entry[y+2][x] if y + 2 < H else 10
                if above != 5 and below != 5:
                    rails.add((x, y)); rails.add((x, y+1))
    for y in range(H):
        for x in range(W - 1):
            if entry[y][x] == 5 and entry[y][x+1] == 5:
                left = entry[y][x-1] if x > 0 else 10
                right = entry[y][x+2] if x + 2 < W else 10
                if left != 5 and right != 5:
                    rails.add((x, y)); rails.add((x+1, y))
    c = _find_cart(entry)
    if c:
        ex, ey = c
        if (ex - 3, ey + 1) in rails or (ex + 6, ey + 1) in rails:
            for x in range(ex - 2, ex + 6):
                rails.add((x, ey + 1)); rails.add((x, ey + 2))
        if (ex + 1, ey - 3) in rails or (ex + 1, ey + 6) in rails:
            for y in range(ey - 2, ey + 6):
                rails.add((ex + 1, y)); rails.add((ex + 2, y))
    for _ in range(3):
        added = []
        for y in range(H):
            for x in range(W):
                if entry[y][x] == 5 and (x, y) not in rails:
                    n = sum(1 for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))
                            if (x+dx, y+dy) in rails)
                    if n >= 2:
                        added.append((x, y))
        if not added:
            break
        rails.update(added)
    return rails

def _base_grid(entry, rails):
    """entry grid with the entry-cart footprint replaced by rails/background."""
    base = [row[:] for row in entry]
    c = _find_cart(entry)
    if c:
        ex, ey = c
        for y in range(ey - 2, ey + 7):
            for x in range(ex - 2, ex + 7):
                if 0 <= y < len(base) and 0 <= x < len(base[0]):
                    base[y][x] = 5 if (x, y) in rails else 10
    return base

def _erase_cart(g, cx, cy, base):
    for y in range(cy - 2, cy + 7):
        for x in range(cx - 2, cx + 7):
            if 0 <= y < len(g) and 0 <= x < len(g[0]):
                g[y][x] = base[y][x]

def _paint_cart(g, cx, cy, loaded, base):
    # outer 5-border: only over background/rails/shadow pixels (skips board interiors -> docking)
    for i in range(8):
        for (xx, yy) in ((cx-2+i, cy-2), (cx-2+i, cy+5), (cx-2, cy-2+i), (cx+5, cy-2+i)):
            if base[yy][xx] in (10, 5, 9):
                g[yy][xx] = 5
    for i in range(6):
        g[cy-1][cx-1+i] = CART_RING
        g[cy+4][cx-1+i] = CART_RING
        g[cy-1+i][cx-1] = CART_RING
        g[cy-1+i][cx+4] = CART_RING
    pat = _pat_peg(CC) if loaded else [[CC]*4 for _ in range(4)]
    for dy in range(4):
        for dx in range(4):
            g[cy+dy][cx+dx] = pat[dy][dx]
    for y in range(cy - 1, cy + 7):
        if 0 <= y < len(g) and g[y][cx+6] == 10:
            g[y][cx+6] = 9
    for x in range(cx - 1, cx + 7):
        if 0 <= x < len(g[0]) and g[cy+6][x] == 10:
            g[cy+6][x] = 9

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

def _draw(g, cell, cells_meta, kind, sel=False):
    x0, y0 = cell
    is_cart = cells_meta.get(cell, (None, None, False))[2]
    base = CC if is_cart else 1
    if kind == 'empty':
        pat = [[base]*4 for _ in range(4)]
    elif kind == 'peg':
        c = 3 if sel else base
        pat = _pat_peg(c)
    else:
        pat = _pat_target(base)
    for dy in range(4):
        for dx in range(4):
            g[y0+dy][x0+dx] = pat[dy][dx]

def _ring(g, cell, on, cells_meta):
    x0, y0 = cell
    is_cart = cells_meta.get(cell, (None, None, False))[2]
    if is_cart:
        v = 3 if on else CART_RING
    else:
        v = 3 if on else 0
    for dx in range(4):
        g[y0-1][x0+dx] = v
        g[y0+4][x0+dx] = v
    for dy in range(4):
        g[y0+dy][x0-1] = v
        g[y0+dy][x0+4] = v

def _clear_sel(g, cells):
    for b, (k, s, isc) in cells.items():
        if k == 'peg' and s:
            _draw(g, b, cells, 'peg', sel=False)
            _ring(g, b, False, cells)
        elif k == 'target':
            _draw(g, b, cells, 'empty')

def _tick(row):
    r = row[:]
    for i, v in enumerate(r):
        if v == 0:
            r[i] = 1
            break
    return r

def _count_pegs(g):
    cells = _find_cells(g)
    return sum(1 for k, s, isc in cells.values() if k == 'peg')

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
ARROW_DIR = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}

def init_state(entry_grid):
    return {"stack": []}

def predict(state, grid, action, x=None, y=None):
    stack = state.get("stack", [])
    info = {"level_up": False, "dead": False, "win": False}
    if action == 7:
        if stack:
            g2 = [row[:] for row in stack[-1]]
            g2[0] = _tick(grid[0])
            return g2, info, {"stack": stack[:-1]}
        g = [row[:] for row in grid]
        g[0] = _tick(g[0])
        return g, info, {"stack": stack}
    new_stack = stack + [[row[:] for row in grid]]
    g = [row[:] for row in grid]
    g[0] = _tick(g[0])
    cells = _find_cells(g)
    if action in ARROW_DIR:
        cart = _find_cart(g)
        if cart is not None:
            dx, dy = ARROW_DIR[action]
            cx, cy = cart
            tx, ty = cx + 6 * dx, cy + 6 * dy
            rails = _rails(ENTRY_GRID)
            ok = all((xx, yy) in rails
                     for xx in (tx + 1, tx + 2) for yy in (ty + 1, ty + 2))
            if ok:
                loaded = cells.get((cx, cy), ('empty',))[0] == 'peg'
                base = _base_grid(ENTRY_GRID, rails)
                _clear_sel(g, cells)
                _erase_cart(g, cx, cy, base)
                _paint_cart(g, tx, ty, loaded, base)
        return g, info, {"stack": new_stack}
    if action != 6:
        return g, info, {"stack": new_stack}
    clicked = None
    for (bx, by) in cells:
        if bx <= x <= bx + 3 and by <= y <= by + 3:
            clicked = (bx, by)
            break
    if clicked is None:
        _clear_sel(g, cells)
        return g, info, {"stack": new_stack}
    kind, sel, isc = cells[clicked]
    selected = [b for b, (k, s, i2) in cells.items() if k == 'peg' and s]
    if kind == 'peg':
        lands = []
        for d in DIRS:
            mid = _adjacent(cells, clicked, d)
            if mid is None or cells[mid][0] != 'peg':
                continue
            land = _adjacent(cells, mid, d)
            if land is not None and cells[land][0] in ('empty', 'target'):
                lands.append(land)
        if not lands:
            return g, info, {"stack": new_stack}
        _clear_sel(g, cells)
        _draw(g, clicked, cells, 'peg', sel=True)
        _ring(g, clicked, True, cells)
        for land in lands:
            _draw(g, land, cells, 'target')
        return g, info, {"stack": new_stack}
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
                _draw(g, b, cells, 'empty')
        _draw(g, s, cells, 'empty')
        _ring(g, s, False, cells)
        if mid is not None:
            _draw(g, mid, cells, 'empty')
        _draw(g, clicked, cells, 'peg')
        if _count_pegs(g) == 1:
            info["level_up"] = True
        return g, info, {"stack": new_stack}
    _clear_sel(g, cells)
    return g, info, {"stack": new_stack}

def is_goal(state, grid):
    return _count_pegs(grid) == 1
