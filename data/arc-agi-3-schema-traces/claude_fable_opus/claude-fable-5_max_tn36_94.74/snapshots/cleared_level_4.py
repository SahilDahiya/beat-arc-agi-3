# World model — "program & run" puzzle game. See notes.md.
# CONFIRMED core: editable strip (bg 0) columns encode instructions via (cap1,s1,s2,s3);
# code table is PER-LEVEL (demo boxes are the codebook: pressing writes the code into the
# red demo strip bg 2). Button (9-circle) runs program column-wise; key moves/shrinks;
# success iff key size==1 tile at lock interior tile with matching notch/bump side.
# Every click costs 1 time (rightmost 9 on row1 -> 3). Fail run = visuals reset + time-1.

# Codes are 6-tuples: (cap1, cap2, cap3, s1, s2, s3). REMAPPED PER LEVEL (demo boxes = codebook).
DEFAULT_TABLE = {(5, 1, 1, 1, 1, 1): ('mv', -1, 0),
                 (5, 1, 1, 5, 1, 1): ('mv', 0, 1),
                 (5, 1, 1, 1, 1, 5): ('mv', 0, -1),
                 (1, 1, 1, 5, 1, 1): ('mv', 1, 0)}
CODE_TABLES = {
    0: DEFAULT_TABLE, 1: DEFAULT_TABLE, 2: DEFAULT_TABLE,
    3: {(1, 1, 1, 5, 1, 5): ('mv', -1, 0),
        (5, 1, 1, 5, 1, 1): ('mv', 0, 1),
        (5, 1, 1, 1, 5, 1): ('sz', -1)},
    4: {(5, 5, 1, 1, 1, 1): ('rot',),        # diamond box (CW) - confirmed t70
        (5, 1, 1, 1, 5, 1): ('sz', -1),      # shrink (entry display)
        (5, 1, 1, 5, 1, 1): ('mv', 0, 1),    # DOWN - confirmed t71
        (1, 1, 1, 1, 5, 1): ('sz', 1),       # GROW - confirmed t72
        (5, 5, 5, 5, 5, 5): ('fx',)},        # color-convert b->f - confirmed t83
}


def _table():
    try:
        lvl = CURRENT_LEVEL
    except Exception:
        lvl = None
    return CODE_TABLES.get(lvl, DEFAULT_TABLE)


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
    # ---- caps: 3-wide runs flanked by bg (0 editable / 2 demo), stems below
    caps = []
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
    cols = {}
    for (y, x) in ecaps:
        cols.setdefault(x, []).append(y)
    for x in cols:
        cols[x].sort()
    dcols = {}
    for (y, x) in dcaps:
        dcols.setdefault(x, []).append(y)
    for x in dcols:
        dcols[x].sort()
    # ---- button: biggest color-9 comp below caps
    nines = [(x, y) for y in range(maxcapy + 6, H) for x in range(W) if e[y][x] == 9]
    btn = None
    if nines:
        cs = _comps(nines)
        cs.sort(key=len, reverse=True)
        c = cs[0]
        btn = (min(p[0] for p in c), min(p[1] for p in c),
               max(p[0] for p in c), max(p[1] for p in c))
    # ---- small boxes: square rings (pair identical runs at dy == width)
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
                    if not all(e[yy][bx0] == col and e[yy][bx1] == col
                               for yy in range(by0 + 1, brow)):
                        continue
                    cxm = (bx0 + bx1) // 2
                    cym = (by0 + brow) // 2
                    if e[cym][cxm] == col:
                        continue
                    if btn and not (bx1 < btn[0] or bx0 > btn[2]
                                    or brow < btn[1] or by0 > btn[3]):
                        continue
                    ring = ([(xx, by0) for xx in range(bx0, bx1 + 1)]
                            + [(xx, brow) for xx in range(bx0, bx1 + 1)]
                            + [(bx0, yy) for yy in range(by0 + 1, brow)]
                            + [(bx1, yy) for yy in range(by0 + 1, brow)])
                    boxes.append({'bbox': (bx0, by0, bx1, brow), 'ring': ring,
                                  'kind': None})
    # ---- color-11/15 comps: glyphs (inside boxes) vs key/lock
    key = lock = None
    lock_color = 11
    for colr in (11, 15):
        els = [(x, y) for y in range(H) for x in range(W) if e[y][x] == colr]
        for c in _comps(els):
            x0 = min(p[0] for p in c); x1 = max(p[0] for p in c)
            y0 = min(p[1] for p in c); y1 = max(p[1] for p in c)
            host = None
            for bx in boxes:
                b0, b1, b2, b3 = bx['bbox']
                if b0 < x0 and x1 < b2 and b1 < y0 and y1 < b3:
                    host = bx
                    break
            if host is not None:
                w = x1 - x0 + 1; h = y1 - y0 + 1
                n = len(c)
                if colr == 15:
                    host['kind'] = ('fx',)  # unknown f-instruction
                elif n == 1:
                    host['kind'] = ('sz', -1)
                elif w == h and n >= 0.9 * w * h and n >= 9:
                    host['kind'] = ('sz', 1)
                elif w == h and w >= 5 and n < 0.9 * w * h and n >= 12:
                    host['kind'] = ('rot',)  # diamond-ish glyph (GUESS)
                else:
                    b0, b1, b2, b3 = host['bbox']
                    dots = [(xx, yy) for yy in range(b1 + 1, b3)
                            for xx in range(b0 + 1, b2) if e[yy][xx] == 0]
                    if dots:
                        bcx = (x0 + x1) / 2.0
                        bcy = (y0 + y1) / 2.0
                        dcx = sum(p[0] for p in dots) / float(len(dots))
                        dcy = sum(p[1] for p in dots) / float(len(dots))
                        vx, vy = bcx - dcx, bcy - dcy
                        if abs(vx) > abs(vy):
                            host['kind'] = ('mv', 1 if vx > 0 else -1, 0)
                        else:
                            host['kind'] = ('mv', 0, 1 if vy > 0 else -1)
                continue
            if len(c) >= 10:
                w = x1 - x0 + 1; h = y1 - y0 + 1
                if colr == 11 and w == h and w % 4 == 0 and len(c) >= 0.75 * w * h:
                    key = (x0, y0, w, c)
                else:
                    lock = (x0, y0, x1, y1, c)
                    lock_color = colr
                    lock_color = colr
    # ---- key derived: notch side, walls, bounds, target
    walls = set()
    bounds = None
    target = None
    notch_side = bump_side = None
    if key:
        kx0, ky0, ksz, kc = key
        kcs = set(kc)
        missing = [(x - kx0, y - ky0) for y in range(ky0, ky0 + ksz)
                   for x in range(kx0, kx0 + ksz) if (x, y) not in kcs]
        if missing:
            if all(ry >= ksz - 2 for (rx, ry) in missing):
                notch_side = 'bottom'
            elif all(ry <= 1 for (rx, ry) in missing):
                notch_side = 'top'
            elif all(rx <= 1 for (rx, ry) in missing):
                notch_side = 'left'
            elif all(rx >= ksz - 2 for (rx, ry) in missing):
                notch_side = 'right'
        for yy in range(H):
            for xx in range(W):
                if e[yy][xx] == 6:
                    walls.add(((xx - kx0) // 4, (yy - ky0) // 4))
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
    s_target = 1
    if key and lock:
        kx0, ky0, ksz, kc = key
        lx0, ly0, lx1, ly1, lc = lock
        lcs = set(lc)
        ix0, iy0, ix1, iy1 = lx0, ly0, lx1, ly1
        changed = True
        while changed and ix0 < ix1 and iy0 < iy1:
            changed = False
            if all((xx, iy0) in lcs for xx in range(ix0, ix1 + 1)):
                iy0 += 1; changed = True
            if all((xx, iy1) in lcs for xx in range(ix0, ix1 + 1)):
                iy1 -= 1; changed = True
            if all((ix0, yy) in lcs for yy in range(iy0, iy1 + 1)):
                ix0 += 1; changed = True
            if all((ix1, yy) in lcs for yy in range(iy0, iy1 + 1)):
                ix1 -= 1; changed = True
        target = ((ix0 - kx0) // 4, (iy0 - ky0) // 4)
        s_target = max(1, (ix1 - ix0 + 1) // 4)
        bumps = [(x, y) for (x, y) in lc if ix0 <= x <= ix1 and iy0 <= y <= iy1]
        if bumps:
            bxs = [p[0] for p in bumps]; bys = [p[1] for p in bumps]
            if max(bys) == iy1:
                bump_side = 'bottom'
            elif min(bys) == iy0:
                bump_side = 'top'
            elif min(bxs) == ix0:
                bump_side = 'left'
            elif max(bxs) == ix1:
                bump_side = 'right'
    # ---- billboard
    threes = [(x, y) for y in range(H) for x in range(W) if e[y][x] == 3]
    bb = None
    if len(threes) > 100:
        bb = (min(p[0] for p in threes), min(p[1] for p in threes),
              max(p[0] for p in threes), max(p[1] for p in threes))
    return {
        'ecaps': ecaps, 'dcaps': dcaps, 'cols': cols, 'dcols': dcols,
        'btn': btn, 'key': key, 'target': target, 'boxes': boxes, 'bb': bb,
        'walls': walls, 'bounds': bounds, 's_target': s_target,
        'notch_side': notch_side, 'bump_side': bump_side, 'lock_color': lock_color,
    }


def _spend(g):
    row = g[1]
    for xx in range(len(row) - 1, -1, -1):
        if row[xx] == 9:
            row[xx] = 3
            return


def _colcode(g, x0, ys):
    caps = [g[cy][x0] for cy in ys]
    stems = [g[cy + 2][x0 + 1] for cy in ys]
    while len(caps) < 3:
        caps.append(1)
    while len(stems) < 3:
        stems.append(1)
    return (caps[0], caps[1], caps[2], stems[0], stems[1], stems[2])


def _prog_actions(g, cols):
    tbl = _table()
    out = []
    for x0 in sorted(cols):
        code = _colcode(g, x0, cols[x0])
        act = tbl.get(code) if code else None
        if act:
            out.append(act)
    return out


def _canon4(notch_side):
    cells = [(i, j) for j in range(4) for i in range(4)]
    drop = {'bottom': [(1, 3), (2, 3)], 'top': [(1, 0), (2, 0)],
            'left': [(0, 1), (0, 2)], 'right': [(3, 1), (3, 2)]}.get(notch_side, [])
    return [c for c in cells if c not in drop]


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    g = [r[:] for r in grid]
    if action != 6 or x is None:
        return g, info
    D = _detect()
    # --- editable icon toggle
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
    # --- demo icon: inert
    for (cy, x0) in D['dcaps']:
        if x0 - 1 <= x <= x0 + 3 and cy - 1 <= y <= cy + 4:
            _spend(g)
            return g, info
    # --- run button
    if D['btn']:
        bx0, by0, bx1, by1 = D['btn']
        if bx0 <= x <= bx1 and by0 <= y <= by1:
            ok = True
            tx = ty = 0
            s = (D['key'][2] // 4) if D['key'] else 1
            notch = D['notch_side']
            conv = False
            b0, b1, b2, b3 = D['bounds'] if D['bounds'] else (-99, -99, 99, 99)
            for act in _prog_actions(g, D['cols']):
                if act[0] == 'mv':
                    nx, ny = tx + act[1], ty + act[2]
                    bad = False
                    for ix in range(nx, nx + s):
                        for iy in range(ny, ny + s):
                            if (ix, iy) in D['walls'] or not (b0 <= ix <= b2 and b1 <= iy <= b3):
                                bad = True
                    if bad:
                        ok = False
                        break
                    tx, ty = nx, ny
                elif act[0] == 'sz':
                    s += act[1]
                    if s < 1:
                        ok = False
                        break
                    bad = False
                    for ix in range(tx, tx + s):
                        for iy in range(ty, ty + s):
                            if (ix, iy) in D['walls'] or not (b0 <= ix <= b2 and b1 <= iy <= b3):
                                bad = True
                    if bad:
                        ok = False
                        break
                elif act[0] == 'rot':
                    order = ['right', 'bottom', 'left', 'top']  # CW confirmed (t82)
                    if notch in order:
                        notch = order[(order.index(notch) + 1) % 4]
                elif act[0] == 'fx':
                    conv = True  # key color b -> f
            if (ok and s == D['s_target'] and D['target'] is not None
                    and (tx, ty) == D['target'] and notch == D['bump_side']
                    and (D['lock_color'] != 15 or conv)):
                info['level_up'] = True
                return g, info
            _spend(g)
            return g, info
    # --- demo boxes
    for i, bx in enumerate(D['boxes']):
        x0, y0, x1, y1 = bx['bbox']
        if x0 <= x <= x1 and y0 <= y <= y1:
            for (px, py) in bx['ring']:
                g[py][px] = 9
            for j, ob in enumerate(D['boxes']):
                if j != i:
                    for (px, py) in ob['ring']:
                        g[py][px] = 2
            kind = bx['kind']
            code = None
            for k, v in _table().items():
                if v == kind:
                    code = k
            if kind and code and D['dcols']:
                xs = sorted(D['dcols'])
                mid = xs[len(xs) // 2]
                for dx0 in xs:
                    ys = sorted(D['dcols'][dx0])
                    # fx-demo: only middle column carries the code, others all-NOP
                    ccode = code if (kind[0] != 'fx' or dx0 == mid) else (1, 1, 1, 1, 1, 1)
                    for ri, cy in enumerate(ys):
                        capc = ccode[ri] if ri < 3 else 1
                        for xx in range(dx0, dx0 + 3):
                            g[cy][xx] = capc
                        sc = ccode[3 + ri] if ri < 3 else 1
                        for yy in range(cy + 2, cy + 5):
                            g[yy][dx0 + 1] = sc
                if D['bb'] and D['key']:
                    bbx0, bby0, bbx1, bby1 = D['bb']
                    for yy in range(bby0, bby1 + 1):
                        for xx in range(bbx0, bbx1 + 1):
                            if g[yy][xx] == 4:
                                g[yy][xx] = 3
                    shape = _canon4(D['notch_side'])
                    kx0, ky0, ksz, kc = D['key']
                    n = len(D['dcols'])
                    if kind[0] == 'fx':
                        # fx-demo: 12x12 f-colored key, centered in billboard, notch bottom
                        bbw = bbx1 - bbx0 + 1
                        bbh = bby1 - bby0 + 1
                        gx0 = bbx0 + (bbw - 12 + 1) // 2
                        gy0 = bby0 + (bbh - 12 + 1) // 2
                        for (ri, rj) in _canon4('bottom'):
                            for pi in range(3):
                                for pj in range(3):
                                    gx = gx0 + ri * 3 + pi
                                    gy = gy0 + rj * 3 + pj
                                    if bbx0 <= gx <= bbx1 and bby0 <= gy <= bby1:
                                        g[gy][gx] = 15
                    elif kind[0] == 'sz':
                        # sz-demo: corner ghost, notch 'bottom', scale 1 (shrink) or 4 (grow)
                        sc = 1 if kind[1] == -1 else 4
                        gx0, gy0 = bbx0 + 1, bby0 + 1
                        for (ri, rj) in _canon4('bottom'):
                            for pi in range(sc):
                                for pj in range(sc):
                                    gx = gx0 + ri * sc + pi
                                    gy = gy0 + rj * sc + pj
                                    if bbx0 <= gx <= bbx1 and bby0 <= gy <= bby1:
                                        g[gy][gx] = 4
                    elif kind[0] == 'rot':
                        # rot demo: ghost at board-center tile, key's current notch
                        b0, b1, b2, b3 = D['bounds'] if D['bounds'] else (0, 0, 0, 0)
                        cxt = (b0 + b2) // 2
                        cyt = (b1 + b3) // 2
                        offx = bbx0 - (bbx1 + 2)
                        for (rx, ry) in shape:
                            gx = kx0 + rx + cxt * 4 + offx
                            gy = ky0 + ry + cyt * 4
                            if bbx0 <= gx <= bbx1 and bby0 <= gy <= bby1:
                                g[gy][gx] = 4
                    elif kind[0] == 'mv':
                        d = (kind[1], kind[2])
                        b0, b1, b2, b3 = D['bounds'] if D['bounds'] else (0, 0, 0, 0)
                        cxt = (b0 + b2) // 2
                        cyt = (b1 + b3) // 2
                        # start: key tile, perpendicular axis snapped to board center
                        start = (0, cyt) if d[1] == 0 else (cxt, 0)
                        # notch: move direction if the level has a rot box, else key's notch
                        has_rot = any(b.get('kind') and b['kind'][0] == 'rot'
                                      for b in D['boxes'])
                        if has_rot:
                            nmap = {(0, 1): 'bottom', (0, -1): 'top',
                                    (1, 0): 'right', (-1, 0): 'left'}
                            shape = _canon4(nmap[d])
                        fx, fy = start[0] + d[0] * n, start[1] + d[1] * n
                        offx = bbx0 - (bbx1 + 2)
                        for (rx, ry) in shape:
                            gx = kx0 + rx + fx * 4 + offx
                            gy = ky0 + ry + fy * 4
                            if bbx0 <= gx <= bbx1 and bby0 <= gy <= bby1:
                                g[gy][gx] = 4
            _spend(g)
            return g, info
    # --- elsewhere: inert
    _spend(g)
    return g, info
