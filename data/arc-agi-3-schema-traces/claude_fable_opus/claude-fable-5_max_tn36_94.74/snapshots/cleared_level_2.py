# World model — "program & run" puzzle game.
# CONFIRMED mechanics:
# - Icon strips: caps = exactly-3-wide runs flanked by strip bg; stems = 1-wide 3-tall at
#   (cap_y+2..cap_y+4, x0+1). Editable strip bg=0; demo strip bg=2 (clicks inert).
# - Click in icon box (x0-1..x0+3): y<=cap_y+2 toggles CAP 1<->5; y=cap_y+3..cap_y+4 toggles STEM 1<->5.
# - Program = COLUMNS (caps sharing x0, all rows), executed left->right. Column executes iff any cap==5.
#   Direction from column stems top->bottom: all-1 -> LEFT; s[0]==5 -> DOWN; s[2]==5 -> UP;
#   s[1]==5 -> RIGHT (GUESS untested). 1-row strip: [5]->DOWN, [1]->LEFT.
# - Key = solid 4x4 color-11 block (comp>=10 cells, 4x4 bbox); lock = hollow color-11 container.
#   Lock interior = bbox shrunk on closed sides. Success iff key final tile == lock interior -> level_up.
#   Fail: visuals reset, time-1.
# - Every click costs 1 time: rightmost 9 in row 1 -> 3.
# - Small glyph boxes (square rings below strips; glyph = 6-cell color-11 bar + dots):
#   box_v = box whose glyph bar is wider than tall (vertical motion), box_h = other.
#   Clicking box_v: rings recolor (clicked=9, other=2), demo strip BOTTOM row stems := 5,
#   billboard ghost := key shape translated by demo-program net delta (drawn color 4 on bg 3).
#   box_h click: ring swap only (GUESS - avoid).
# - Billboard: bg-3 panel left of board; offset_x = bb_x0 - (bb_x1+2).

def _comps(cells):
    cells = set(cells)
    seen = set()
    out = []
    for c in cells:
        if c in seen:
            continue
        stack = [c]; comp = [c]
        seen.add(c)
        while stack:
            (cx, cy) = stack.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cx + dx, cy + dy)
                if n in cells and n not in seen:
                    seen.add(n); comp.append(n); stack.append(n)
        out.append(comp)
    return out


def _detect():
    e = ENTRY_GRID
    H = len(e); W = len(e[0])
    caps = []  # (y, x0, bg)
    for y in range(1, H - 5):
        x = 1
        while x < W - 1:
            v = e[y][x]
            l = e[y][x - 1]
            if v != 0 and v != l:
                j = x
                while j < W and e[y][j] == v:
                    j += 1
                if (j - x == 3 and j < W and e[y][j] == l and l in (0, 2)
                        and v in (1, 5)
                        and y + 4 < H and e[y + 2][x + 1] in (1, 5)
                        and e[y + 2][x] == l and e[y + 2][x + 2] == l):
                    caps.append((y, x, l))
                x = j
            else:
                x += 1
    ecaps = [(y, x) for (y, x, bg) in caps if bg == 0]
    dcaps = [(y, x) for (y, x, bg) in caps if bg == 2]
    maxcapy = max(y for (y, x, bg) in caps) if caps else 0
    # editable columns: group by x0
    cols = {}
    for (y, x) in ecaps:
        cols.setdefault(x, []).append(y)
    for x in cols:
        cols[x].sort()
    # demo columns
    dcols = {}
    for (y, x) in dcaps:
        dcols.setdefault(x, []).append(y)
    for x in dcols:
        dcols[x].sort()
    # button: biggest color-9 comp below strips
    nines = [(x, y) for y in range(maxcapy + 6, H) for x in range(W) if e[y][x] == 9]
    btn = None
    if nines:
        cs = _comps(nines)
        cs.sort(key=len, reverse=True)
        c = cs[0]
        btn = (min(p[0] for p in c), min(p[1] for p in c),
               max(p[0] for p in c), max(p[1] for p in c))
    # key & lock: color-11 comps with >=10 cells
    els = [(x, y) for y in range(H) for x in range(W) if e[y][x] == 11]
    key = lock = None
    glyphs = []
    for c in _comps(els):
        x0 = min(p[0] for p in c); x1 = max(p[0] for p in c)
        y0 = min(p[1] for p in c); y1 = max(p[1] for p in c)
        if len(c) >= 10:
            if x1 - x0 == 3 and y1 - y0 == 3:
                key = (x0, y0, c)
            else:
                lock = (x0, y0, x1, y1, c)
        else:
            glyphs.append((x0, y0, x1, y1))
    # walls: color-6 cells -> tiles relative to key; board bounds from color-4/6 cells
    walls = set()
    bounds = None
    if key:
        kx0, ky0 = key[0], key[1]
        wcells = [(x, y) for y in range(H) for x in range(W) if e[y][x] == 6]
        for (x, y) in wcells:
            walls.add(((x - kx0) // 4, (y - ky0) // 4))
        # board interior bounds: walk from key origin to the 0-border in each direction
        lx = kx0
        while lx > 0 and e[ky0][lx] != 0:
            lx -= 1
        rx = kx0
        while rx < W - 1 and e[ky0][rx] != 0:
            rx += 1
        ty = ky0
        while ty > 0 and e[ty][kx0] != 0:
            ty -= 1
        dy = ky0
        while dy < H - 1 and e[dy][kx0] != 0:
            dy += 1
        bounds = ((lx + 1 - kx0) // 4, (ty + 1 - ky0) // 4,
                  (rx - 1 - kx0) // 4, (dy - 1 - ky0) // 4)
    target = None
    key_cells_rel = None
    if key and lock:
        kx0, ky0, kc = key
        key_cells_rel = sorted((p[0] - kx0, p[1] - ky0) for p in kc)
        lx0, ly0, lx1, ly1, lc = lock
        lcs = set(lc)
        ix0, iy0, ix1, iy1 = lx0, ly0, lx1, ly1
        if all((x, ly0) in lcs for x in range(lx0 + 1, lx1)):  # top closed
            iy0 += 1
        if all((x, ly1) in lcs for x in range(lx0 + 1, lx1)):  # bottom closed
            iy1 -= 1
        if all((lx0, y) in lcs for y in range(ly0 + 1, ly1)):  # left closed
            ix0 += 1
        if all((lx1, y) in lcs for y in range(ly0 + 1, ly1)):  # right closed
            ix1 -= 1
        target = ((ix0 - kx0) // 4, (iy0 - ky0) // 4)
    # small boxes: square rings of color 9 or 2 below strips.
    # Detect by pairing identical horizontal runs (top & bottom edges) at dy == width.
    boxes = []
    runs_by_span = {}
    for col in (9, 2):
        for yy in range(maxcapy + 6, H):
            xx = 1
            while xx < W:
                if e[yy][xx] == col and e[yy][xx - 1] != col:
                    j = xx
                    while j < W and e[yy][j] == col:
                        j += 1
                    if j - xx >= 7:
                        runs_by_span.setdefault((xx, j - 1, col), []).append(yy)
                    xx = j
                else:
                    xx += 1
    for (rx0, rx1, col), yys in runs_by_span.items():
        for ti in range(len(yys)):
            for bi in range(ti + 1, len(yys)):
                if yys[bi] - yys[ti] == rx1 - rx0:
                    bx0, by0, bx1, brow = rx0, yys[ti], rx1, yys[bi]
                    # verify side columns exist
                    if not all(e[yy][bx0] == col and e[yy][bx1] == col
                               for yy in range(by0 + 1, brow)):
                        continue
                    # must be hollow (not part of the filled button blob)
                    cx = (bx0 + bx1) // 2
                    cym = (by0 + brow) // 2
                    if e[cym][cx] == col:
                        continue
                    if btn and not (bx1 < btn[0] or bx0 > btn[2]
                                    or brow < btn[1] or by0 > btn[3]):
                        continue
                    ring = ([(xx, by0) for xx in range(bx0, bx1 + 1)]
                            + [(xx, brow) for xx in range(bx0, bx1 + 1)]
                            + [(bx0, yy) for yy in range(by0 + 1, brow)]
                            + [(bx1, yy) for yy in range(by0 + 1, brow)])
                    # glyph inside? direction = from dots centroid toward bar centroid
                    bdir = None
                    for (gx0, gy0, gx1, gy1) in glyphs:
                        if bx0 < gx0 and gx1 < bx1 and by0 < gy0 and gy1 < brow:
                            bcx = (gx0 + gx1) / 2.0
                            bcy = (gy0 + gy1) / 2.0
                            dots = [(xx, yy) for yy in range(by0 + 1, brow)
                                    for xx in range(bx0 + 1, bx1) if e[yy][xx] == 0]
                            if dots:
                                dcx = sum(p[0] for p in dots) / float(len(dots))
                                dcy = sum(p[1] for p in dots) / float(len(dots))
                                vx, vy = bcx - dcx, bcy - dcy
                                if abs(vx) > abs(vy):
                                    bdir = (1, 0) if vx > 0 else (-1, 0)
                                else:
                                    bdir = (0, 1) if vy > 0 else (0, -1)
                    boxes.append({'bbox': (bx0, by0, bx1, brow), 'ring': ring, 'dir': bdir})
    # billboard: bg-3 region
    threes = [(x, y) for y in range(H) for x in range(W) if e[y][x] == 3]
    bb = None
    if len(threes) > 100:
        bx0 = min(p[0] for p in threes); bx1 = max(p[0] for p in threes)
        by0 = min(p[1] for p in threes); by1 = max(p[1] for p in threes)
        bb = (bx0, by0, bx1, by1)
    return {
        'ecaps': ecaps, 'dcaps': dcaps, 'cols': cols, 'dcols': dcols,
        'btn': btn, 'key': key, 'key_cells_rel': key_cells_rel, 'target': target,
        'boxes': boxes, 'bb': bb, 'walls': walls, 'bounds': bounds,
    }


def _spend(g):
    row = g[1]
    for xx in range(len(row) - 1, -1, -1):
        if row[xx] == 9:
            row[xx] = 3
            return


# Column code -> move. NO separate execute flag: cap of row1 is PART of the code.
# key = (cap1, s1, s2, s3); missing rows pad with 1.
CODES = {
    (5, 1, 1, 1): (-1, 0),   # LEFT
    (5, 5, 1, 1): (0, 1),    # DOWN
    (5, 1, 1, 5): (0, -1),   # UP
    (1, 5, 1, 1): (1, 0),    # RIGHT
}


def _colmove(g, x0, ys):
    cap1 = g[ys[0]][x0]
    # caps of rows 2,3 must be 1 (blue) for a valid code (all observations)
    for cy in ys[1:]:
        if g[cy][x0] != 1:
            return None
    stems = [g[cy + 2][x0 + 1] for cy in ys]
    while len(stems) < 3:
        stems.append(1)
    return CODES.get((cap1, stems[0], stems[1], stems[2]))


def _prog_moves(g, cols):
    out = []
    for x0 in sorted(cols):
        d = _colmove(g, x0, cols[x0])
        if d:
            out.append(d)
    return out


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    g = [r[:] for r in grid]
    if action != 6 or x is None:
        return g, info
    D = _detect()
    # editable icon?
    for (cy, x0) in D['ecaps']:
        if x0 - 1 <= x <= x0 + 3 and cy - 1 <= y <= cy + 4:
            if y <= cy + 2:
                cur = g[cy][x0]
                nc = 1 if cur == 5 else 5
                for xx in range(x0, x0 + 3):
                    g[cy][xx] = nc
            else:
                cur = g[cy + 2][x0 + 1]
                nc = 1 if cur == 5 else 5
                for yy in range(cy + 2, cy + 5):
                    g[yy][x0 + 1] = nc
            _spend(g)
            return g, info
    # demo icon? inert
    for (cy, x0) in D['dcaps']:
        if x0 - 1 <= x <= x0 + 3 and cy - 1 <= y <= cy + 4:
            _spend(g)
            return g, info
    # button?
    if D['btn']:
        bx0, by0, bx1, by1 = D['btn']
        if bx0 <= x <= bx1 and by0 <= y <= by1:
            # simulate path step-by-step with wall/bounds blocking
            px = py = 0
            ok = True
            for d in _prog_moves(g, D['cols']):
                nx, ny = px + d[0], py + d[1]
                if (nx, ny) in D['walls']:
                    ok = False
                    break
                if D['bounds']:
                    b0, b1, b2, b3 = D['bounds']
                    if not (b0 <= nx <= b2 and b1 <= ny <= b3):
                        ok = False
                        break
                px, py = nx, ny
            if ok and D['target'] is not None and (px, py) == D['target']:
                info['level_up'] = True
                return g, info
            _spend(g)
            return g, info
    # small boxes? (direction selector: writes direction code to demo strip + ghost demo)
    for i, bx in enumerate(D['boxes']):
        x0, y0, x1, y1 = bx['bbox']
        if x0 <= x <= x1 and y0 <= y <= y1:
            other = [b for j, b in enumerate(D['boxes']) if j != i]
            for (px, py) in bx['ring']:
                g[py][px] = 9
            for ob in other:
                for (px, py) in ob['ring']:
                    g[py][px] = 2
            d = bx.get('dir')
            code = None
            for k, v in CODES.items():
                if v == d:
                    code = k
            if d and code and D['dcols']:
                # write code into demo strip
                for dx0, ys in sorted(D['dcols'].items()):
                    ys = sorted(ys)
                    for ri, cy in enumerate(ys):
                        capc = code[0] if ri == 0 else 1
                        for xx in range(dx0, dx0 + 3):
                            g[cy][xx] = capc
                        sc = code[1 + ri] if 1 + ri < 4 else 1
                        for yy in range(cy + 2, cy + 5):
                            g[yy][dx0 + 1] = sc
                # billboard ghost: erase, then draw key at demo-final position
                if D['bb'] and D['key']:
                    bbx0, bby0, bbx1, bby1 = D['bb']
                    for yy in range(bby0, bby1 + 1):
                        for xx in range(bbx0, bbx1 + 1):
                            if g[yy][xx] == 4:
                                g[yy][xx] = 3
                    n = len(D['dcols'])
                    # start = key tile + perpendicular offset (0,-1,+1,-2,+2,...) s.t. path fits
                    perp = (0, 1) if d[1] == 0 else (1, 0)
                    b0, b1, b2, b3 = D['bounds'] if D['bounds'] else (-99, -99, 99, 99)

                    def fits(sx, sy):
                        px_, py_ = sx, sy
                        if not (b0 <= px_ <= b2 and b1 <= py_ <= b3) or (px_, py_) in D['walls']:
                            return False
                        for _ in range(n):
                            px_, py_ = px_ + d[0], py_ + d[1]
                            if not (b0 <= px_ <= b2 and b1 <= py_ <= b3) or (px_, py_) in D['walls']:
                                return False
                        return True
                    start = (0, 0)
                    for mag in (0, 1, 2, 3):
                        for sgn in ((1,) if mag == 0 else (-1, 1)):
                            cand = (perp[0] * mag * sgn, perp[1] * mag * sgn)
                            if fits(cand[0], cand[1]):
                                start = cand
                                break
                        else:
                            continue
                        break
                    fx = start[0] + d[0] * n
                    fy = start[1] + d[1] * n
                    offx = bbx0 - (bbx1 + 2)
                    kx0, ky0, _ = D['key']
                    for (rx, ry) in D['key_cells_rel']:
                        gx = kx0 + rx + fx * 4 + offx
                        gy = ky0 + ry + fy * 4
                        if bbx0 <= gx <= bbx1 and bby0 <= gy <= bby1:
                            g[gy][gx] = 4
            _spend(g)
            return g, info
    # elsewhere: inert
    _spend(g)
    return g, info
