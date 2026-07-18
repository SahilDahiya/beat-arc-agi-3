# World model v5 — ARC3 game
# L0 mechanic (block-mover, confirmed t0-t1):
#  - POSITIONS: 4x4 zones. A position either holds a solid 4x4 color block, or is EMPTY
#    (shown as bg 4 with a 2x2 color-2 marker at its center).
#  - Click a position holding a block -> SELECT it (1px ring of 0 around its 4x4 zone;
#    previous ring erased).
#  - Click an EMPTY position while a block is selected -> MOVE: source zone -> bg+marker,
#    ring erased, target zone filled with the color. Counter row (full-width 2s at entry,
#    row 52): rightmost remaining 2 turns 3 per MOVE (selections don't count).
#  - Goal (guess): middle slot positions (those empty at entry) L->R match top code
#    (hollow-square border colors L->R) => level_up.

def _entry_layout(entry):
    g = np.array(entry)
    H, W = g.shape
    counter_rows = [y for y in range(H) if int((g[y] == 2).sum()) == W]
    # top sequence: runs of non-(4,5) colors in row 1
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
    zones = []      # (x1,y1,x2,y2) 4x4 zones
    slot_idx = []   # zones that started EMPTY (2x2 marker) — the answer slots
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
                    slot_idx.append(len(zones) - 1)
    # solid 4x4 blocks of colors not in {0,2,4,5,8}
    for y in range(H - 3):
        for x in range(W - 3):
            v = int(g[y, x])
            if v in (0, 2, 4, 5, 8):
                continue
            if (g[y:y + 4, x:x + 4] == v).all():
                up = y > 0 and g[y - 1, x] == v
                left = x > 0 and g[y, x - 1] == v
                if not up and not left:
                    zones.append((x, y, x + 3, y + 3))
    return {"seq": seq, "zones": zones, "slots": slot_idx,
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


def _slot_colors(g, lay):
    out = []
    for i in lay["slots"]:
        x1, y1, x2, y2 = lay["zones"][i]
        v = g[y1][x1]
        out.append(None if v in (2, 4) else v)
    return out


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
            # select this block (re-select allowed)
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
            # erase ring
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
            # fill target
            tx1, ty1, tx2, ty2 = zones[hit]
            for yy in range(ty1, ty2 + 1):
                for xx in range(tx1, tx2 + 1):
                    g[yy][xx] = color
            # counter: rightmost 2 -> 3 per move
            for cy in lay["counter_rows"]:
                for cx in range(W - 1, -1, -1):
                    if g[cy][cx] == 2:
                        g[cy][cx] = 3
                        break
            return g, info
        return g, info
    if action == 5:
        # GUESS: submit — level_up if slot arrangement matches the code
        sc = _slot_colors(g, lay)
        if len(sc) == len(lay["seq"]) and all(
                a == b for a, b in zip(sc, lay["seq"])):
            info["level_up"] = True
        return g, info
    # action 7: unknown -> identity
    return g, info
