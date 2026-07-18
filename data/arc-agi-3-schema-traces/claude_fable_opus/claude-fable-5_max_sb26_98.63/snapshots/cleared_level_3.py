# World model v5 — ARC3 "nested-box block mover"
# CONFIRMED (L0-L2):
#  - Positions (4x4 zones): hold an OBJECT or are EMPTY (2x2 color-2 marker at center).
#  - OBJECTS: solid 4x4 color block, or PORTAL = hollow 4x4 square (ring color c, interior bg).
#  - Click occupied zone -> SELECT (0-ring around zone; previous ring erased).
#  - Click empty zone with selection -> MOVE object there (kind preserved);
#    source zone -> bg + 2x2 marker; counter row (all-2s at entry): rightmost 2 -> 3 per MOVE.
#  - Action 5 = SUBMIT: level_up iff DFS reading of boxes == top code sequence:
#    root box = box whose border color is no portal's color; walk its positions left-to-right:
#    solid block consumes next code color (must match); portal recurses into box of its color;
#    any empty traversed position fails; total consumed must equal code length.

def _entry_layout(entry):
    g = np.array(entry)
    H, W = g.shape
    counter_rows = [y for y in range(H) if int((g[y] == 2).sum()) == W]
    # code sequence: runs of non-(4,5) colors in row 1
    seq = []
    if H > 1:
        row = g[1]
        x = 0
        while x < W:
            v = int(row[x])
            if v not in (4, 5):
                x2 = x
                while x2 + 1 < W and int(row[x2 + 1]) == v:
                    x2 += 1
                seq.append(v)
                x = x2 + 1
            else:
                x += 1
    # marker zones: 2x2 of color 2 -> 4x4 zone (expand 1)
    zones = []
    for y in range(H - 1):
        if y in counter_rows or (y + 1) in counter_rows:
            continue
        for x in range(W - 1):
            if (g[y, x] == 2 and g[y, x + 1] == 2 and g[y + 1, x] == 2
                    and g[y + 1, x + 1] == 2):
                up = y > 0 and g[y - 1, x] == 2
                left = x > 0 and g[y, x - 1] == 2
                if not up and not left:
                    zones.append((x - 1, y - 1, x + 2, y + 2))
    # solid 4x4 blocks (colors not in 0,2,4,5)
    for y in range(H - 3):
        for x in range(W - 3):
            v = int(g[y, x])
            if v in (0, 2, 4, 5):
                continue
            if (g[y:y + 4, x:x + 4] == v).all():
                up = y > 0 and g[y - 1, x] == v
                left = x > 0 and g[y, x - 1] == v
                if not up and not left:
                    zones.append((x, y, x + 3, y + 3))
    # portal objects: 4x4 hollow squares (ring color c, interior bg 4)
    for y in range(H - 3):
        for x in range(W - 3):
            v = int(g[y, x])
            if v in (0, 2, 4, 5):
                continue
            blk = g[y:y + 4, x:x + 4]
            ring_ok = ((blk[0] == v).all() and (blk[3] == v).all()
                       and blk[1, 0] == v and blk[1, 3] == v
                       and blk[2, 0] == v and blk[2, 3] == v)
            if ring_ok and (blk[1:3, 1:3] == 4).all():
                zones.append((x, y, x + 3, y + 3))
    # boxes: per color, rows with >=15 cells of c, paired top/bottom with same x-extent
    boxes = {}
    for c in range(16):
        if c in (0, 2, 4, 5):
            continue
        rows = []
        for y in range(H):
            cnt = int((g[y] == c).sum())
            if cnt >= 15:
                xs = np.where(g[y] == c)[0]
                rows.append((y, int(xs.min()), int(xs.max())))
        i = 0
        while i + 1 < len(rows):
            y1, a1, b1 = rows[i]
            y2, a2, b2 = rows[i + 1]
            if abs(a1 - a2) <= 2 and abs(b1 - b2) <= 2 and y2 - y1 >= 4:
                boxes.setdefault(c, []).append(
                    (min(a1, a2), y1, max(b1, b2), y2))
                i += 2
            else:
                i += 1
    return {"seq": seq, "zones": zones, "boxes": boxes,
            "counter_rows": counter_rows}


def _ring_cells(x1, y1, x2, y2):
    cells = []
    for xx in range(x1 - 1, x2 + 2):
        cells.append((xx, y1 - 1))
        cells.append((xx, y2 + 1))
    for yy in range(y1, y2 + 1):
        cells.append((x1 - 1, yy))
        cells.append((x2 + 1, yy))
    return cells


def _obj_at(g, zone):
    x1, y1, x2, y2 = zone
    v = g[y1][x1]
    if v in (2, 4):
        return None
    kind = 'solid' if g[y1 + 1][x1 + 1] == v else 'portal'
    return (v, kind)


def _inside(z, box):
    return (z[0] > box[0] and z[2] < box[2]
            and z[1] > box[1] and z[3] < box[3])


def _eval_goal(g, lay):
    seq = lay["seq"]
    zones = lay["zones"]
    boxes = lay["boxes"]
    objs = {}
    for z in zones:
        o = _obj_at(g, z)
        if o:
            objs[z] = o
    portal_colors = {o[0] for o in objs.values() if o[1] == 'portal'}
    roots = []
    for c, rects in boxes.items():
        if c not in portal_colors:
            for r in rects:
                roots.append((r[1], r[0], c, r))
    roots.sort()
    if not roots:
        return False
    ok = [True]
    k = [0]
    seen = set()

    def trav(rect):
        if not ok[0] or rect in seen:
            ok[0] = False
            return
        seen.add(rect)
        elems = sorted([z for z in zones if _inside(z, rect)],
                       key=lambda z: (z[0], z[1]))
        for z in elems:
            if not ok[0]:
                return
            o = objs.get(z)
            if o is None:
                ok[0] = False
                return
            color, kind = o
            if kind == 'solid':
                if k[0] >= len(seq) or seq[k[0]] != color:
                    ok[0] = False
                    return
                k[0] += 1
            else:
                rects = boxes.get(color)
                if not rects:
                    ok[0] = False
                    return
                for r in rects:
                    trav(r)

    for _, _, c, rect in roots:
        trav(rect)
    return ok[0] and k[0] == len(seq)


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    g = [list(map(int, r)) for r in grid]
    H = len(g)
    W = len(g[0])
    lay = _entry_layout(ENTRY_GRID)
    zones = lay["zones"]

    def selected():
        for i, (x1, y1, x2, y2) in enumerate(zones):
            if x1 - 1 >= 0 and y1 - 1 >= 0 and x2 + 1 < W and y2 + 1 < H:
                if (g[y1 - 1][x1 - 1] == 0 and g[y2 + 1][x2 + 1] == 0
                        and g[y1 - 1][x2 + 1] == 0):
                    return i
        return None

    if action == 6 and x is not None and y is not None and zones:
        hit = None
        for i, (x1, y1, x2, y2) in enumerate(zones):
            if x1 <= x <= x2 and y1 <= y <= y2:
                hit = i
                break
        if hit is None:
            return g, info
        sel = selected()
        obj = _obj_at(g, zones[hit])
        if obj is not None:
            # select this object
            if sel is not None:
                x1, y1, x2, y2 = zones[sel]
                for (cx, cy) in _ring_cells(x1, y1, x2, y2):
                    if 0 <= cx < W and 0 <= cy < H:
                        g[cy][cx] = 4
            x1, y1, x2, y2 = zones[hit]
            for (cx, cy) in _ring_cells(x1, y1, x2, y2):
                if 0 <= cx < W and 0 <= cy < H:
                    g[cy][cx] = 0
            return g, info
        if sel is not None:
            mobj = _obj_at(g, zones[sel])
            if mobj is None:
                return g, info
            color, kind = mobj
            x1, y1, x2, y2 = zones[sel]
            for (cx, cy) in _ring_cells(x1, y1, x2, y2):
                if 0 <= cx < W and 0 <= cy < H:
                    g[cy][cx] = 4
            # vacate source: bg + center 2x2 marker
            for yy in range(y1, y2 + 1):
                for xx in range(x1, x2 + 1):
                    g[yy][xx] = 4
            for yy in range(y1 + 1, y1 + 3):
                for xx in range(x1 + 1, x1 + 3):
                    g[yy][xx] = 2
            # draw object at target per kind
            tx1, ty1, tx2, ty2 = zones[hit]
            for yy in range(ty1, ty2 + 1):
                for xx in range(tx1, tx2 + 1):
                    if kind == 'solid':
                        g[yy][xx] = color
                    else:
                        edge = (yy == ty1 or yy == ty2
                                or xx == tx1 or xx == tx2)
                        g[yy][xx] = color if edge else 4
            for cy in lay["counter_rows"]:
                for cx in range(W - 1, -1, -1):
                    if g[cy][cx] == 2:
                        g[cy][cx] = 3
                        break
            return g, info
        return g, info
    if action == 5:
        if _eval_goal(g, lay):
            info["level_up"] = True
        return g, info
    # action 7: unknown -> identity
    return g, info
