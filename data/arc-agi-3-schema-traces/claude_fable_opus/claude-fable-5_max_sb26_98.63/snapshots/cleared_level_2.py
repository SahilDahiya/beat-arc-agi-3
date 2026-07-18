# World model v5 — ARC3 "block mover with nested boxes"
# CONFIRMED (L0):
#  - Positions: 4x4 zones; hold a solid 4x4 color block or EMPTY (2x2 color-2 marker at center).
#  - Click occupied zone -> SELECT (0-ring around zone, previous ring erased).
#  - Click empty zone with selection -> MOVE block there (source -> bg+marker, ring erased);
#    counter row (all-2s at entry): rightmost 2 -> 3 per MOVE.
#  - Action 5 = SUBMIT: level_up iff every marker zone holds its TARGET color.
# TARGETS (L1 hypothesis): top panel row1 = code sequence. Boxes are rectangles (1px border,
#  >=15-cell horizontal lines). A 4x4 hollow square (border c, bg interior) inside a box is a
#  PORTAL to the box with border color c. Reading = DFS: walk root box elements (markers +
#  portals) left-to-right; marker consumes next code color; portal expands to its target box.

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
    markers = []
    for y in range(H - 1):
        if y in counter_rows or (y + 1) in counter_rows:
            continue
        for x in range(W - 1):
            if (g[y, x] == 2 and g[y, x + 1] == 2 and g[y + 1, x] == 2
                    and g[y + 1, x + 1] == 2):
                up = y > 0 and g[y - 1, x] == 2
                left = x > 0 and g[y, x - 1] == 2
                if not up and not left:
                    markers.append((x - 1, y - 1, x + 2, y + 2))
    # source blocks: solid 4x4, color not in (0,2,4,5)
    blocks = []
    for y in range(H - 3):
        for x in range(W - 3):
            v = int(g[y, x])
            if v in (0, 2, 4, 5):
                continue
            if (g[y:y + 4, x:x + 4] == v).all():
                up = y > 0 and g[y - 1, x] == v
                left = x > 0 and g[y, x - 1] == v
                if not up and not left:
                    blocks.append((x, y, x + 3, y + 3))
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
    # portals: 4x4 hollow squares (ring color c, interior bg 4)
    portals = []
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
                portals.append((v, x, y, x + 3, y + 3))

    def inside(z, box):
        return (z[0] > box[0] and z[2] < box[2]
                and z[1] > box[1] and z[3] < box[3])

    # DFS target assignment
    targets = {}
    portal_colors = {p[0] for p in portals}
    box_items = [(c, b) for c, bl in boxes.items() for b in bl]
    roots = sorted([(b[1], c, b) for (c, b) in box_items
                    if c not in portal_colors])
    kk = [0]
    visited = set()

    def traverse(box):
        if box in visited:
            return
        visited.add(box)
        elems = []
        for z in markers:
            if inside(z, box):
                elems.append((z[0], 'm', z))
        for p in portals:
            pz = (p[1], p[2], p[3], p[4])
            if inside(pz, box):
                elems.append((p[1], 'p', p))
        elems.sort()
        for _, kind, obj in elems:
            if kind == 'm':
                if kk[0] < len(seq):
                    targets[obj] = seq[kk[0]]
                    kk[0] += 1
            else:
                for b in boxes.get(obj[0], []):
                    traverse(b)

    for _, c, b in roots:
        traverse(b)

    zones = markers + blocks
    return {"seq": seq, "zones": zones, "markers": markers,
            "targets": targets, "counter_rows": counter_rows}


def _ring_cells(x1, y1, x2, y2):
    cells = []
    for xx in range(x1 - 1, x2 + 2):
        cells.append((xx, y1 - 1))
        cells.append((xx, y2 + 1))
    for yy in range(y1, y2 + 1):
        cells.append((x1 - 1, yy))
        cells.append((x2 + 1, yy))
    return cells


def _targets_met(g, lay):
    tg = lay["targets"]
    if not tg or len(tg) < len(lay["seq"]):
        return False
    for (x1, y1, x2, y2), tc in tg.items():
        if g[y1][x1] != tc:
            return False
    return True


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    g = [list(map(int, r)) for r in grid]
    H = len(g)
    W = len(g[0])
    lay = _entry_layout(ENTRY_GRID)
    zones = lay["zones"]

    def content(i):
        x1, y1, x2, y2 = zones[i]
        v = g[y1][x1]
        return None if v in (2, 4) else v

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
        c = content(hit)
        if c is not None:
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
            color = content(sel)
            if color is None:
                return g, info
            x1, y1, x2, y2 = zones[sel]
            for (cx, cy) in _ring_cells(x1, y1, x2, y2):
                if 0 <= cx < W and 0 <= cy < H:
                    g[cy][cx] = 4
            for yy in range(y1, y2 + 1):
                for xx in range(x1, x2 + 1):
                    g[yy][xx] = 4
            for yy in range(y1 + 1, y1 + 3):
                for xx in range(x1 + 1, x1 + 3):
                    g[yy][xx] = 2
            tx1, ty1, tx2, ty2 = zones[hit]
            for yy in range(ty1, ty2 + 1):
                for xx in range(tx1, tx2 + 1):
                    g[yy][xx] = color
            for cy in lay["counter_rows"]:
                for cx in range(W - 1, -1, -1):
                    if g[cy][cx] == 2:
                        g[cy][cx] = 3
                        break
            return g, info
        return g, info
    if action == 5:
        if _targets_met(g, lay):
            info["level_up"] = True
        return g, info
    # action 7: unknown -> identity
    return g, info
