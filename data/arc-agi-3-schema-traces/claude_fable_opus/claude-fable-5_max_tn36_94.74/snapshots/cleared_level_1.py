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
    # small boxes: ring comps of color 9 or 2 below strips (exclude button comp)
    boxes = []
    for col in (9, 2):
        pts = [(x, y) for y in range(maxcapy + 6, H) for x in range(W) if e[y][x] == col]
        for c in _comps(pts):
            x0 = min(p[0] for p in c); x1 = max(p[0] for p in c)
            y0 = min(p[1] for p in c); y1 = max(p[1] for p in c)
            if btn and x0 >= btn[0] and x1 <= btn[2] and y0 >= btn[1] and y1 <= btn[3]:
                continue
            area = (x1 - x0 + 1) * (y1 - y0 + 1)
            if area >= 49 and len(c) < 0.7 * area:
                # ring = square whose bottom row is the max-y row with >=8 cells
                rows = {}
                for p in c:
                    rows.setdefault(p[1], []).append(p[0])
                brow = max(yy for yy in rows if len(rows[yy]) >= 8)
                bx0, bx1 = min(rows[brow]), max(rows[brow])
                by0 = brow - (bx1 - bx0)
                ring = [p for p in c if bx0 <= p[0] <= bx1 and by0 <= p[1] <= brow]
                # glyph inside?
                orient = None
                for (gx0, gy0, gx1, gy1) in glyphs:
                    if bx0 < gx0 and gx1 < bx1 and by0 < gy0 and gy1 < brow:
                        orient = 'v' if (gx1 - gx0) > (gy1 - gy0) else 'h'
                boxes.append({'bbox': (bx0, by0, bx1, brow), 'ring': ring, 'orient': orient})
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
        'boxes': boxes, 'bb': bb,
    }


def _spend(g):
    row = g[1]
    for xx in range(len(row) - 1, -1, -1):
        if row[xx] == 9:
            row[xx] = 3
            return


def _dir(stems):
    if all(s == 1 for s in stems):
        return (-1, 0)
    n = len(stems)
    if stems[0] == 5:
        return (0, 1)
    if n >= 3 and stems[2] == 5:
        return (0, -1)
    if n >= 2 and stems[1] == 5:
        return (1, 0)  # GUESS
    return None


def _prog_delta(g, cols):
    tx = ty = 0
    for x0 in sorted(cols):
        ys = cols[x0]
        capv = [g[cy][x0] for cy in ys]
        if 5 in capv:
            stems = [g[cy + 2][x0 + 1] for cy in ys]
            d = _dir(stems)
            if d:
                tx += d[0]; ty += d[1]
    return (tx, ty)


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
            delta = _prog_delta(g, D['cols'])
            if D['target'] is not None and delta == D['target']:
                info['level_up'] = True
                return g, info
            _spend(g)
            return g, info
    # small boxes?
    for i, bx in enumerate(D['boxes']):
        x0, y0, x1, y1 = bx['bbox']
        if x0 <= x <= x1 and y0 <= y <= y1:
            other = [b for j, b in enumerate(D['boxes']) if j != i]
            if bx['orient'] == 'v':
                for (px, py) in bx['ring']:
                    g[py][px] = 9
                for ob in other:
                    for (px, py) in ob['ring']:
                        g[py][px] = 2
                # demo strip bottom-row stems := 5
                if D['dcols']:
                    maxy = max(max(v) for v in D['dcols'].values())
                    for dx0, ys in D['dcols'].items():
                        for cy in ys:
                            if cy == maxy:
                                for yy in range(cy + 2, cy + 5):
                                    g[yy][dx0 + 1] = 5
                # billboard ghost
                if D['bb'] and D['key']:
                    bbx0, bby0, bbx1, bby1 = D['bb']
                    for yy in range(bby0, bby1 + 1):
                        for xx in range(bbx0, bbx1 + 1):
                            if g[yy][xx] == 4:
                                g[yy][xx] = 3
                    dt = _prog_delta(g, D['dcols'])
                    offx = bbx0 - (bbx1 + 2)
                    kx0, ky0, _ = D['key']
                    for (rx, ry) in D['key_cells_rel']:
                        gx = kx0 + rx + dt[0] * 4 + offx
                        gy = ky0 + ry + dt[1] * 4
                        if bbx0 <= gx <= bbx1 and bby0 <= gy <= bby1:
                            g[gy][gx] = 4
            # box_h: ring swap only (GUESS)
            else:
                for (px, py) in bx['ring']:
                    g[py][px] = 9
                for ob in other:
                    for (px, py) in ob['ring']:
                        g[py][px] = 2
            _spend(g)
            return g, info
    # elsewhere: inert
    _spend(g)
    return g, info
