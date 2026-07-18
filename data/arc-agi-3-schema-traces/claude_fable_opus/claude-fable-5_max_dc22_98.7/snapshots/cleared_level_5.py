# dc22 world model (predict form, stateful)
# GENERAL MECHANICS (confirmed L0+L1):
# - e(14) = 2x2 SWIMMER. 1/2/3/4 = up/down/left/right by 2 cells.
#   May enter 2x2 dest iff all 4 cells are ONE color not in {0,3,4,5,14}.
#   On move: vacated cells := carried color; carried := dest color.
#   carried starts 2 (e begins inside a 2-container).
# - Entering a uniform-11 (b) destination => LEVEL UP (confirmed L0).
# - BUTTONS (click regions) toggle their color's slot PAIRS by swapping the
#   two slots' FILL-STATES (not cells!): full = all c; half = c iff (x+y) odd
#   else 4; empty = all 4. Confirmed by L1 flask-9: 4x4-full <-> 4x8-half.
#   If a slot's state is unrecognized (e inside / debris): treat as no-op pour.
# - First pour removes right-panel 0-outlines (L0 only; harmless otherwise).
# - Row63 clock: per-level time slope! cost units: normal action = 1, effective
#   pour = 2. bar cells = ceil(cum / den) where den = CURRENT_LEVEL + 2
#   (L0: /2, L1: /3 — both confirmed exactly; den for later levels is a guess).
#   First-call calibration: cum = den*(T-1)+1 if T>0 else 0 (run-start quirk).

DIRS = {1: (0, -2), 2: (0, 2), 3: (-2, 0), 4: (2, 0)}
# t208: e blocked by the 5-strip -> 5 IS a barrier (like right-panel bg).
BLOCKED = (0, 3, 4, 5, 14)

def _buttons():
    # list of ((x0,y0,x1,y1) inclusive region, color-key)
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return [((41, 16, 55, 22), 8), ((41, 33, 55, 39), 9)]
    if lvl == 1:
        return [((46, 20, 60, 24), 6), ((46, 38, 60, 42), 9),
                ((46, 29, 58, 33), 8)]  # flask-8 appears after item-box collected
    if lvl == 2:
        return [((45, 16, 57, 20), 8), ((45, 25, 57, 29), 9),
                ((45, 34, 57, 38), 6), ((45, 43, 57, 47), 15)]  # f-flask once collected
    if lvl == 3:
        return [((47, 17, 59, 21), 6), ((43, 25, 49, 31), 11),
                ((54, 26, 59, 31), "deploy")]  # right-panel 2-block button
    if lvl == 5:
        return [((45, 23, 58, 27), 6),   # 6-hexagon
                ((53, 5, 59, 11), 11),   # b-flask (stem+bowl)
                ((47, 17, 55, 19), 8),   # 8-block (after 8-item collected)
                ((49, 46, 50, 47), "dial8"), ((51, 46, 52, 47), "dialb"),
                ((49, 48, 50, 49), "diala"), ((51, 48, 52, 49), "dial7"),
                ((49, 31, 52, 34), "drvN"), ((45, 35, 48, 38), "drvW"),
                ((53, 35, 56, 38), "drvE"), ((49, 39, 52, 42), "drvS")]
    if lvl == 4:
        return [((44, 19, 50, 25), 11), ((48, 34, 56, 36), 8),
                ((46, 39, 58, 43), 9), ((47, 46, 59, 50), 6),
                ((43, 28, 46, 31), "snakeL"), ((48, 28, 51, 31), "snakeU"),
                ((53, 28, 56, 31), "snakeR"), ((58, 28, 61, 31), "snakeD"),
                ((54, 20, 59, 25), "deploy4"),  # 2-block: fills 5-rail y44-45
                ((46, 12, 58, 16), 15)]  # flask-f (materializes after f-item)
    return []

def _slides():
    # flask key -> list of (colors, band(y0,h), dx): the contiguous run of any
    # color in colors within the band translates by dx per click.
    # L3 quirk: when track-1's run reaches x>=18 (docked at column), BOTH runs
    # recolor 1 -> c(12). (Observed t205; semantics guessed as 'docked'.)
    lvl = CURRENT_LEVEL
    if lvl == 3:
        return {11: [((1, 12), (28, 2), 2, 8), ((1, 12), (38, 2), 2, 4)]}
    if lvl == 4:
        return {11: [((1, 12), (54, 2), 2, 14)]}
    return {}

def _slots():
    # color-key -> list of (material, (x,y,w,h), stateA, stateB): a click FLIPS
    # every slot between its two states (skip slots matching neither).
    F, H, E = "full", "half", "empty"
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return {
            8: [(8, (12, 30, 6, 4), F, E), (8, (18, 24, 4, 6), E, F)],
            9: [(9, (18, 20, 4, 4), F, H), (9, (8, 34, 4, 4), H, F)],
        }
    if lvl == 1:
        return {
            6: [(7, (8, 40, 8, 4), F, E), (7, (16, 32, 4, 8), E, F),
                (7, (20, 40, 8, 4), F, E), (7, (16, 44, 4, 8), E, F)],
            9: [(9, (8, 28, 4, 4), F, H), (9, (4, 32, 4, 8), H, F)],
            8: [(8, (12, 24, 8, 4), F, E), (8, (20, 16, 4, 8), E, F),
                (8, (24, 24, 8, 4), F, E), (8, (20, 28, 4, 8), E, F)],
        }
    if lvl == 2:
        return {
            9: [(9, (8, 24, 4, 4), F, H), (9, (4, 20, 4, 4), H, F),
                (9, (24, 16, 4, 4), H, F), (9, (12, 40, 4, 4), H, F)],
            8: [(8, (12, 24, 8, 4), F, E), (8, (20, 16, 4, 8), E, F),   # GUESS
                (8, (24, 24, 8, 4), F, E), (8, (20, 28, 4, 8), E, F)],  # d-rotation like L1
            15: [(15, (16, 32, 4, 8), H, F),
                 (15, (24, 32, 10, 4), H, F)],  # GUESS: flask-f flips half<->full
            6: [("cellswap", (6, 16, 2, 2), (12, 46, 2, 2))],  # PORTAL: cell-wise
            # content swap of the two 6/7 duals — e RIDES it (confirmed t175)!
        }
    if lvl == 3:
        return {
            6: [("cellswap", (4, 24, 2, 2), (18, 32, 2, 2))],  # portal duals
        }
    if lvl == 4:
        return {
            9: [(9, (26, 34, 4, 4), H, F), (9, (10, 38, 4, 4), F, H)],  # state-flips (e-inside = penalty, t290)
            6: [("cellswap", (24, 6, 2, 2), (10, 34, 2, 2))],  # portal duals (t274)
            15: [(15, (26, 46, 4, 8), H, F), (15, (14, 50, 10, 4), F, H)],  # checker & pool
        }
    return {}

def _item_boxes():
    # (x,y,w,h, item_color, flask_pixels) — e may enter mixed {2,item} cells
    # inside the box; on entry all item cells in the box -> 2, flask appears.
    lvl = CURRENT_LEVEL
    if lvl == 1:
        px = [(xx, yy) for yy in (29, 30, 31) for xx in range(49, 56)] + \
             [(xx, yy) for yy in (32, 33) for xx in range(46, 59)]
        return [(16, 52, 4, 4, 8, px)]
    if lvl == 2:
        px = [(xx, yy) for yy in (43, 44, 45) for xx in range(48, 55)] + \
             [(xx, yy) for yy in (46, 47) for xx in range(45, 58)]
        return [(16, 40, 4, 4, 15, px)]  # flask-f box; 6/7-mix boxes NOT encoded yet
    if lvl == 4:
        px = [(xx, yy) for yy in (12, 13, 14) for xx in range(49, 56)] + \
             [(xx, yy) for yy in (15, 16) for xx in range(46, 59)]
        return [(10, 18, 4, 4, 15, px)]  # f-box -> flask-f at rows 12-16
    if lvl == 5:
        px8 = [(xx, yy) for yy in (17, 18, 19) for xx in range(47, 56)]
        pxq = ([(xx, yy, 8) for yy in (46, 47) for xx in (49, 50)] +
               [(xx, yy, 11) for yy in (46, 47) for xx in (51, 52)] +
               [(xx, yy, 10) for yy in (48, 49) for xx in (49, 50)] +
               [(xx, yy, 7) for yy in (48, 49) for xx in (51, 52)])
        return [(32, 48, 6, 6, 8, px8),          # 8-item -> 8-block rows 17-19
                (4, 16, 8, 8, (7, 8, 10, 11), pxq)]  # ba/8877 -> QUAD (49,46)
    return []

def _divider_x():
    lvl = CURRENT_LEVEL
    if lvl == 0:
        return 34
    if lvl == 5:
        return 64  # L5: divider zebra 00s at x40-41 are permanent; no cleanup
    return 40  # levels 1 and 2: dashes at x38-39, right panel x>=40

def init_state(entry_grid):
    return {"cum": None, "carried": 2, "tdir": 1}

E_HINT = [None]  # e's last known anchor (for when cage walls hide e cells)

def _find_player(g, color=14):
    # the player is a 2x2 block of 14s in the LEFT PANEL (L5 has decor
    # single 14s AND a lit port-block rendered in 14 on the right panel!)
    for y in range(63):
        for x in range(38):
            if (g[y][x] == color and g[y][x + 1] == color and
                    g[y + 1][x] == color and g[y + 1][x + 1] == color):
                return x, y
    return E_HINT[0]

def _cells(slot):
    x0, y0, w, hh = slot
    return [(x0 + i % w, y0 + i // w) for i in range(w * hh)]

def _slot_state(g, slot, c):
    if isinstance(c, tuple) and c[0] == "dual":
        c1, c2 = c[1], c[2]
        isA = all(g[y][x] == (c1 if (x + y) % 2 == 0 else c2) for (x, y) in _cells(slot))
        isB = all(g[y][x] == (c2 if (x + y) % 2 == 0 else c1) for (x, y) in _cells(slot))
        return "A" if isA else ("B" if isB else None)
    full = empty = half = True
    for (x, y) in _cells(slot):
        v = g[y][x]
        if v != c:
            full = False
        if v != 4:
            empty = False
        if v != (c if (x + y) % 2 == 1 else 4):
            half = False
    if full:
        return "full"
    if empty:
        return "empty"
    if half:
        return "half"
    return None

def _render(g, slot, c, st):
    if isinstance(c, tuple) and c[0] == "dual":
        c1, c2 = c[1], c[2]
        for (x, y) in _cells(slot):
            even = (x + y) % 2 == 0
            g[y][x] = (c1 if even else c2) if st == "A" else (c2 if even else c1)
        return
    for (x, y) in _cells(slot):
        if st == "full":
            g[y][x] = c
        elif st == "half":
            g[y][x] = c if (x + y) % 2 == 1 else 4
        else:
            g[y][x] = 4

L5PORTS = {  # legend port (e 2x2 anchor) -> (drive key, block rect, color)
    (34, 56): ("N", (49, 31, 52, 34), 15),
    (32, 58): ("W", (45, 35, 48, 38), 12),
    (36, 58): ("E", (53, 35, 56, 38), 14),
    (34, 60): ("S", (49, 39, 52, 42), 10),
}
L5MARK = {"N": (52, 34, 15), "W": (48, 38, 12), "E": (56, 38, 14),
          "S": (52, 42, 10)}

def _l5_render_ports(g):
    ep = _find_player(g)
    for anchor, (dk, (x0, y0, x1, y1), col) in L5PORTS.items():
        lit = (ep == anchor)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                g[yy][xx] = col if lit else 4
        if not lit:
            mx, my, mc = L5MARK[dk]
            g[my][mx] = mc

RECOLORED_E = [None]  # set when a recolor covered e's cells (carried update)
FREECLICK = [False]   # blocked snake-clicks cost 0 units (t295)
SNAKEMOVE = [False]   # successful snake-clicks cost 5 units (t297)
DOCKED = [False]      # dock-recolor pours cost 10 in L4 (t321)

# L4 CLAW ("8-glyph" is a C-clamp): OPEN 8x8 (30 cells, mouth on right,
# arm zigzag on left) / CLOSED 8x6 (28 cells, jaws gripping the column's
# T-knob -> chain-link). sq8 button closes the claw when the knob's
# crossbar (a 1-wide c-column at rel x+6, rows +2..+5) is inside the mouth.
# While CLOSED, L/R tows the whole train (claw + tab + column) by 4;
# c-cells only move onto {0,4}; claw rolls over anything (gcover memory).
CLAW_OPEN = frozenset([(3,0),(4,0),(5,0),(6,0),(7,0),(3,1),(7,1),
    (1,2),(2,2),(3,2),(4,2),(0,3),(1,3),(2,3),(3,3),(0,4),(1,4),(2,4),(3,4),
    (1,5),(2,5),(3,5),(4,5),(3,6),(7,6),(3,7),(4,7),(5,7),(6,7),(7,7)])
CLAW_CLOSED = frozenset([(3,0),(4,0),(5,0),(6,0),(7,0),
    (1,1),(2,1),(3,1),(4,1),(7,1),(0,2),(1,2),(2,2),(3,2),
    (0,3),(1,3),(2,3),(3,3),(1,4),(2,4),(3,4),(4,4),(7,4),
    (3,5),(4,5),(5,5),(6,5),(7,5)])

def _claw(g):
    cells = [(xx, yy) for yy in range(63) for xx in range(38) if g[yy][xx] == 8]
    if not cells:
        return None
    ax = min(x for x, y in cells)
    ay = min(y for x, y in cells)
    rel = frozenset((x - ax, y - ay) for x, y in cells)
    form = "open" if rel == CLAW_OPEN else ("closed" if rel == CLAW_CLOSED else "?")
    return ax, ay, form, cells

def _pipe():
    pipe = set()
    for yy in range(14, 18):
        for xx in range(3, 21):  # top run reaches x20 (revealed by tow, t421)
            pipe.add((xx, yy))
    for yy in range(14, 30):
        for xx in range(3, 7):
            pipe.add((xx, yy))
    for yy in range(26, 30):
        for xx in range(3, 19):
            pipe.add((xx, yy))
    return pipe

def _translate(g, state, cells, dest_of, pipe):
    """Move the rigid set `cells` (each keeps its own color) to dest_of(cell),
    with cover/restore memory in state['gcover']. Returns new state."""
    cover = dict(state.get("gcover", {}))
    vals = {(xx, yy): g[yy][xx] for (xx, yy) in cells}
    cellset = set(cells)
    dest = [dest_of(c) for c in cells]
    newcover = {}
    for (xx, yy) in dest:
        k = "%d,%d" % (xx, yy)
        if (xx, yy) in cellset:
            if k in cover:
                newcover[k] = cover[k]
            continue
        old = cover.get(k)
        if old is None:
            v = g[yy][xx]
            old = v if v not in (0, 4) else None
        if old is not None:
            newcover[k] = old
    for (xx, yy) in cells:
        k = "%d,%d" % (xx, yy)
        if k in cover:
            g[yy][xx] = cover[k]
        else:
            g[yy][xx] = 0 if (xx, yy) in pipe else 4
    for i, (xx, yy) in enumerate(dest):
        g[yy][xx] = vals[cells[i]]
    st = dict(state)
    st["gcover"] = newcover
    return st

def _pour(g, key):
    """Flip each slot between its two states. Returns (changed, net_delta)."""
    RECOLORED_E[0] = None
    changed_any = False
    slides = _slides().get(key, [])
    if slides:
        runs = []
        any_blocked = False
        starts = {}
        for colors, (y0, hh), dx, sx in slides:
            starts[y0] = sx
            cells = [(x, y) for y in range(y0, y0 + hh) for x in range(64)
                     if g[y][x] in colors]
            if not cells:
                continue
            cur = g[cells[0][1]][cells[0][0]]
            # run = full span including e-holes; e-holes stay at absolute pos
            x_lo = min(x for x, y in cells)
            x_hi = max(x for x, y in cells)
            exs = [x for y in range(y0, y0 + hh) for x in range(64) if g[y][x] == 14]
            if exs and min(exs) <= x_hi + 1 and max(exs) >= x_lo - 1:
                x_lo = min(x_lo, min(exs))
                x_hi = max(x_hi, max(exs))
            span = [(x, y) for y in range(y0, y0 + hh) for x in range(x_lo, x_hi + 1)]
            ok = all(0 <= x + dx < 64 and
                     (g[y][x + dx] in colors or g[y][x + dx] == 4 or g[y][x + dx] == 14)
                     for (x, y) in span)
            runs.append((span, cur, y0, dx, ok))
            if not ok:
                any_blocked = True
        if runs:
            docked = any(cur == 12 for cells, cur, y0, dx, ok in runs)
            if docked:
                any_blocked = True  # docked + press = reset
            if any_blocked:
                # any blocked run -> whole system RESETS to entry pos, color 1
                for cells, cur, y0, dx, ok in runs:
                    for (x, y) in cells:
                        g[y][x] = 4
                    for yy in range(y0, y0 + 2):
                        for xx in range(starts.get(y0, 4), starts.get(y0, 4) + 6):
                            g[yy][xx] = 1
                changed_any = True
            else:
                newruns = []
                for span, cur, y0, dx, ok in runs:
                    for (x, y) in span:
                        if g[y][x] != 14:
                            g[y][x] = 4
                    moved = [(x + dx, y) for (x, y) in span]
                    for (x, y) in moved:
                        if g[y][x] != 14:
                            g[y][x] = cur
                    newruns.append((moved, y0))
                    changed_any = True
                t1 = [m for m, y0 in newruns if y0 == 28]
                if t1 and min(x for (x, y) in t1[0]) >= 18:
                    for m, y0 in newruns:
                        for (x, y) in m:
                            if g[y][x] != 14:
                                g[y][x] = 12
                            else:
                                RECOLORED_E[0] = 12  # e embedded in recolored run
                if CURRENT_LEVEL == 4:
                    for m, y0 in newruns:
                        if y0 == 54 and min(x for (x, y) in m) == 24:
                            DOCKED[0] = True
                            for (x, y) in m:
                                if g[y][x] != 14:
                                    g[y][x] = 12
                                else:
                                    RECOLORED_E[0] = 12
    slots = _slots()
    if key not in slots:
        return changed_any, 0
    changed = changed_any
    net = 0
    for entry in slots[key]:
        if entry[0] == "cellswap":
            _, a, b = entry
            for (xa, ya), (xb, yb) in zip(_cells(a), _cells(b)):
                va, vb = g[ya][xa], g[yb][xb]
                if va != vb:
                    g[ya][xa], g[yb][xb] = vb, va
                    changed = True
            continue
        c, slot, sa, sb = entry
        st = _slot_state(g, slot, c)
        if st == sa:
            new = sb
        elif st == sb:
            new = sa
        else:
            continue
        before = sum(1 for (xx, yy) in _cells(slot) if g[yy][xx] == c)
        _render(g, slot, c, new)
        after = sum(1 for (xx, yy) in _cells(slot) if g[yy][xx] == c)
        net += after - before
        changed = True
    return changed, net

def predict(state, grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    info = {"level_up": False, "dead": False, "win": False}

    lvl0 = CURRENT_LEVEL if CURRENT_LEVEL is not None else 0
    # clock in x5-scaled units: action=5, pour=10, blocked-move={L4:6 else 5},
    # penalty={L4:115 else 100}; bar cells = ceil(cum/den5)
    den = {0: 10, 1: 15, 2: 15, 3: 15, 4: 40, 5: 80}.get(lvl0, 80)  # L5 den in [80,89] (t760)
    T0 = sum(1 for xx in range(64) if grid[63][xx] == 3)
    cum = state.get("cum")
    if cum is None or -(-cum // den) != T0:
        # (re)calibrate from the visible bar when desynced
        cum = 0 if T0 == 0 else den * (T0 - 1) + 1

    carried = state.get("carried", 2)
    tdir = state.get("tdir", 1)
    E_HINT[0] = tuple(state["epos"]) if state.get("epos") else None
    if not isinstance(carried, (list, tuple)):
        carried = ((carried, carried), (carried, carried))
    carried = tuple(tuple(r) for r in carried)
    moved = False
    if action in DIRS:
        p = _find_player(g)
        if p is not None:
            px, py = p
            dx, dy = DIRS[action]
            nx, ny = px + dx, py + dy
            if 0 <= nx <= 62 and 0 <= ny <= 62:
                dest = [[g[ny][nx], g[ny][nx + 1]], [g[ny + 1][nx], g[ny + 1][nx + 1]]]
                vals = {dest[0][0], dest[0][1], dest[1][0], dest[1][1]}
                # movement rule: allowed iff NO cell is empty/background/border
                # L5 exception: the legend PORT 2x2s are enterable (t863)
                port_ok = (CURRENT_LEVEL == 5 and (nx, ny) in L5PORTS)
                if port_ok or not (vals & set(BLOCKED)):
                    moved = True
                    # item-box: entering a flask-picture box consumes the item
                    # and materializes the flask button on the right panel
                    for bx, by, bw, bh, ic, fpx in _item_boxes():
                        ics = ic if isinstance(ic, tuple) else (ic,)
                        inside = (bx <= nx and nx + 1 < bx + bw and
                                  by <= ny and ny + 1 < by + bh)
                        if inside and (vals & set(ics)) and any(
                                g[yy][xx] in ics for yy in range(by, by + bh)
                                for xx in range(bx, bx + bw)):
                            for yy in range(by, by + bh):
                                for xx in range(bx, bx + bw):
                                    if g[yy][xx] in ics:
                                        g[yy][xx] = 2
                            for entry in fpx:
                                if len(entry) == 3:
                                    xx, yy, cc = entry
                                    g[yy][xx] = cc
                                else:
                                    xx, yy = entry
                                    g[yy][xx] = ic
                            dest = [[2, 2], [2, 2]]  # consumed under e
                            break
                    for i, yy in enumerate((py, py + 1)):
                        for j, xx in enumerate((px, px + 1)):
                            g[yy][xx] = carried[i][j]
                    for i, yy in enumerate((ny, ny + 1)):
                        for j, xx in enumerate((nx, nx + 1)):
                            # L5 cage walls (8s at x>=16, y>=14) render OVER e
                            # (t1001; post-grip rotor-ring 8s at y<14 do NOT
                            # hide e - t1188 shows e visible on ring)
                            if (CURRENT_LEVEL == 5 and xx >= 16 and yy >= 14 and
                                    dest[i][j] == 8):
                                g[yy][xx] = 8
                            else:
                                g[yy][xx] = 14
                    carried = tuple(tuple(r) for r in dest)
                    E_HINT[0] = (nx, ny)
                    if CURRENT_LEVEL == 5:
                        _l5_render_ports(g)
                    if vals == {11}:
                        info["level_up"] = True

    poured = False
    penalty = False
    net = 0
    if action == 6 and x is not None and y is not None:
        for (x0, y0, x1, y1), key in _buttons():
            if x0 <= x <= x1 and y0 <= y <= y1:
                if key == "deploy":
                    # L3 transfer PENDULUM: 8 cells of 1s shift between c-rail
                    # (y40-41,x16-31) and tube (y20-21,x8-23) each click; the
                    # direction reverses at the ends (tdir in state).
                    # wt = tube end-cart width (0..8); wc = 8-wt.
                    # width 8 renders FUSED as solid c(12); partial renders 1.
                    wt = 0
                    while wt < 8 and g[20][8 + wt] in (1, 12):
                        wt += 1
                    nwt = wt + 2 * tdir
                    if nwt > 8:
                        nwt, tdir = 6, -1
                    elif nwt < 0:
                        nwt, tdir = 2, 1
                    nwc = 8 - nwt
                    tc = 12 if nwt >= 8 else 1
                    cc = 12 if nwc >= 8 else 1
                    for yy in (20, 21):
                        for xx in range(8, 24):
                            if g[yy][xx] != 14:
                                g[yy][xx] = tc if (xx < 8 + nwt or xx >= 24 - nwt) else 5
                    for yy in (40, 41):
                        for xx in range(16, 32):
                            if g[yy][xx] != 14:
                                g[yy][xx] = cc if (xx < 16 + nwc or xx >= 32 - nwc) else 5
                    poured = True
                    break
                if key == "deploy4":
                    # L4 rail-fill pendulum (t427): each press grows the 1-runs
                    # at BOTH ends of the 5-rail (y44-45, x14-29) by 2, from a
                    # hidden reservoir. Adapted from L3 pendulum: reverse at
                    # full; at w>=8 the rail fuses solid c(12). (w>2 UNVERIFIED)
                    wt = 0
                    while wt < 8 and g[44][14 + wt] in (1, 12):
                        wt += 1
                    nwt = wt + 2 * tdir
                    if nwt > 8:
                        nwt, tdir = 6, -1
                    elif nwt < 0:
                        nwt, tdir = 2, 1
                    tc = 12 if nwt >= 8 else 1
                    for yy in (44, 45):
                        for xx in range(14, 30):
                            if g[yy][xx] != 14:
                                g[yy][xx] = tc if (xx < 14 + nwt or xx >= 30 - nwt) else 5
                    poured = True
                    break
                if isinstance(key, str) and key.startswith("snake"):
                    # L4 D-pad: the CLAW translates 4 cells. Constraints:
                    # - its ARM (rows of the shape holding rel-x<3 cells)
                    #   must stay inside the pipe (or poke past x<3);
                    # - when CLOSED, the towed c-cells (tab+column) may only
                    #   land on {0,4}; the claw rolls over anything (gcover).
                    dxy = {"snakeL": (-4, 0), "snakeU": (0, -4),
                           "snakeR": (4, 0), "snakeD": (0, 4)}[key]
                    pipe = _pipe()
                    cl = _claw(g)
                    if cl is None:
                        break
                    ax, ay, form, ccells = cl
                    armrows = set(yy for (xx, yy) in ccells if xx - ax < 3)
                    # arm = zigzag + ring-left in those rows; EXCLUDE the jaw
                    # tips (rel-x 7) — they grip the knob outside the pipe.
                    arm = [(xx, yy) for (xx, yy) in ccells
                           if yy in armrows and xx - ax <= 4]
                    arm_ok = all((xx + dxy[0], yy + dxy[1]) in pipe or xx + dxy[0] < 3
                                 for (xx, yy) in arm)
                    train = list(ccells)
                    if form == "closed":
                        # flood-fill c(12) cells 4-connected from the claw
                        seen = set(ccells)
                        stack = list(ccells)
                        while stack:
                            cx, cy = stack.pop()
                            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                                nx2, ny2 = cx + ddx, cy + ddy
                                if (0 <= nx2 < 38 and 0 <= ny2 < 63 and
                                        (nx2, ny2) not in seen and g[ny2][nx2] == 12):
                                    seen.add((nx2, ny2))
                                    stack.append((nx2, ny2))
                                    train.append((nx2, ny2))
                    dest = [(xx + dxy[0], yy + dxy[1]) for (xx, yy) in train]
                    inb = all(0 <= yy < 63 and 0 <= xx < 38 and g[yy][xx] != 14
                              for (xx, yy) in dest)
                    # e ABOARD the train (its 2x2 inside the train bbox) =>
                    # tow refused with PENALTY +100 (t657), like e-in-slot.
                    ep = _find_player(g)
                    if ep is not None and train:
                        txs = [c[0] for c in train]; tys = [c[1] for c in train]
                        if (min(txs) <= ep[0] and ep[0] + 1 <= max(txs) and
                                min(tys) <= ep[1] and ep[1] + 1 <= max(tys)):
                            penalty = True
                            break
                    if arm_ok and inb:
                        state = _translate(g, state, train,
                                           lambda c: (c[0] + dxy[0], c[1] + dxy[1]),
                                           pipe)
                    SNAKEMOVE[0] = True  # snake press costs 5, moved or refused
                    break
                if isinstance(key, str) and key.startswith("drv") and lvl0 == 5:
                    # CAGE DRIVE (t864): pressing a LIT port-block moves the
                    # 8-cage ring 4 cells in that direction; the hollow ring
                    # rolls over terrain (cover memory in state['ccover']).
                    dk = key[3]
                    ep = _find_player(g)
                    lit = any(ep == anc and L5PORTS[anc][0] == dk
                              for anc in L5PORTS)
                    if lit:
                        dxy = {"N": (0, -4), "S": (0, 4),
                               "W": (-4, 0), "E": (4, 0)}[dk]
                        cp = state.get("cagepos")
                        if cp is None:
                            # detect the 8x8 ring among 8s (top bar heuristic)
                            for yy in range(4, 46):
                                for xx in range(2, 34):
                                    if all(g[yy][xx + i] == 8 for i in range(8)) and \
                                       all(g[yy + 7][xx + i] == 8 for i in range(8)):
                                        cp = (xx, yy)
                                        break
                                if cp:
                                    break
                        if cp is None:
                            break
                        cxx, cyy = cp
                        cage = ([(cxx + i, cyy) for i in range(8)] +
                                [(cxx + i, cyy + 7) for i in range(8)] +
                                [(cxx, cyy + j) for j in range(1, 7)] +
                                [(cxx + 7, cyy + j) for j in range(1, 7)])
                        # TRACK RULE (t864 ok,t866 refused,t868 ok): the ring's
                        # center 2x2 must land on entry-{0,8} track cells.
                        ok_track = False
                        if cage:
                            cx0 = min(c[0] for c in cage)
                            cy0 = min(c[1] for c in cage)
                            ncx, ncy = cx0 + 3 + dxy[0], cy0 + 3 + dxy[1]
                            ok_track = all(
                                ENTRY_GRID[yy][xx] in (0, 8, 12)
                                for yy in (ncy, ncy + 1) for xx in (ncx, ncx + 1))
                        if cage and ok_track:
                            pipe5 = set()
                            for yy in range(0, 63):
                                for xx in range(20, 33):
                                    if ENTRY_GRID[yy][xx] in (0, 8):
                                        pipe5.add((xx, yy))
                            st2 = dict(state)
                            st2["gcover"] = state.get("ccover", {})
                            st2 = _translate(g, st2, cage,
                                             lambda c: (c[0] + dxy[0], c[1] + dxy[1]),
                                             pipe5)
                            state = dict(state)
                            state["ccover"] = st2["gcover"]
                            state["cagepos"] = (cxx + dxy[0], cyy + dxy[1])
                            poured = True
                    break
                if isinstance(key, str) and key.startswith("dial") and lvl0 == 5:
                    # QUAD DIAL v2 (t821/822/823/885): ANY quadrant press
                    # advances the dial one step in the cycle
                    # 67 -> d8 -> cb -> 9a -> 67 (quadrant colors decorative).
                    cyc = [(6, 7), (13, 8), (12, 11), (9, 10)]
                    cur = tuple(state.get("l5dial", (6, 7)))
                    pair = cyc[(cyc.index(cur) + 1) % 4] if cur in cyc else cyc[1]
                    ca, cb2 = pair
                    for (xx, yy) in ((18, 48), (19, 48), (18, 49), (19, 49)):
                        if g[yy][xx] == 14:
                            continue
                        # position-parity recolor (t821-823): even(x+y)->ca
                        g[yy][xx] = ca if (xx + yy) % 2 == 0 else cb2
                    state = dict(state)
                    state["l5dial"] = pair
                    state["l5dialed"] = True
                    poured = True
                    break
                if key == 11 and lvl0 == 5:
                    # L5 CONVEYOR v2 (t758-772): bands hold LOGICAL runs
                    # (state['l5runs']); per press: each run slides +2 and
                    # FUSES to c when its east edge hits x21; then any dock
                    # (c) present at press-start is removed and a fresh 6-wide
                    # run deploys at x6-11, CLIPPING overlapped older runs.
                    lr = state.get("l5runs")
                    if lr is None:
                        lr = {}
                        for y0 in (54, 56, 58):
                            ones = [x for x in range(0, 32) if g[y0][x] in (1, 14)]
                            rr = []
                            if ones:
                                s0 = p0 = ones[0]
                                for x in ones[1:]:
                                    if x == p0 + 1:
                                        p0 = x
                                    else:
                                        rr.append([s0, p0]); s0 = p0 = x
                                rr.append([s0, p0])
                            lr[str(y0)] = rr
                    lr = {k: [list(r) for r in v] for k, v in lr.items()}
                    ep6 = _find_player(g)
                    # STRAND-GUARD (t1043): if e stands on a band and the
                    # slide would leave e uncovered, the WHOLE press is
                    # refused with a penalty.
                    strand = False
                    if ep6 is not None and ep6[1] in (54, 56, 58):
                        runs0 = lr.get(str(ep6[1]), [])
                        onband = any(lo <= ep6[0] and ep6[0] + 1 <= hi
                                     for (lo, hi) in runs0)
                        cov2 = any(lo + 2 <= ep6[0] and ep6[0] + 1 <= hi + 2
                                   for (lo, hi) in runs0)
                        if onband and not cov2:
                            strand = True
                    if strand:
                        penalty = True
                        break
                    for y0 in (54, 56, 58):
                        key0 = str(y0)
                        had_dock = any(g[y0][xx] == 12 for xx in range(0, 32))
                        moved = []
                        fused = []
                        for (lo, hi) in lr.get(key0, []):
                            lo2, hi2 = lo + 2, hi + 2
                            if hi2 == 21:
                                fused.append((lo2, hi2))
                            else:
                                moved.append([lo2, hi2])
                        if had_dock:
                            # remove old dock, deploy fresh, clip overlaps
                            clipped = []
                            for (lo, hi) in moved:
                                if hi <= 11:
                                    continue
                                clipped.append([max(lo, 12), hi])
                            moved = [[6, 11]] + clipped
                        # render band
                        for xx in range(0, 32):
                            for yy in (y0, y0 + 1):
                                if g[yy][xx] != 14 and g[yy][xx] in (1, 12):
                                    g[yy][xx] = 4
                        for (lo, hi) in moved:
                            for xx in range(lo, hi + 1):
                                for yy in (y0, y0 + 1):
                                    if g[yy][xx] != 14:
                                        g[yy][xx] = 1
                        for (lo, hi) in fused:
                            for xx in range(lo, hi + 1):
                                for yy in (y0, y0 + 1):
                                    if g[yy][xx] != 14:
                                        g[yy][xx] = 12
                        lr[key0] = moved
                    state = dict(state)
                    state["l5runs"] = lr
                    poured = True
                    break
                if key == 11 and lvl0 == 5 and False:
                    # L5 CONVEYOR (t758-760): bands y54/y56/y58 (x6..21+).
                    # Per press, per band: docked c-block (at x16-21) vanishes
                    # and a FRESH 1-run deploys at x6-11 (not slid this press);
                    # existing 1-runs slide +2 (e-holes absolute); a run
                    # landing exactly at x16-21 fuses to c (docked).
                    for y0 in (54, 56, 58):
                        # bands live in x0-31 (x32-37 holds a decor pictogram)
                        has_dock = any(g[y0][xx] == 12 for xx in range(0, 32))
                        # collect 1-cells (with e-holes: e cells inside span)
                        ones = [xx for xx in range(0, 32) if g[y0][xx] == 1]
                        exs = [xx for xx in range(0, 32) if g[y0][xx] == 14]
                        if has_dock:
                            for xx in range(0, 40):
                                if g[y0][xx] == 12:
                                    g[y0][xx] = 4
                                    g[y0 + 1][xx] = 4
                        if ones:
                            x_lo, x_hi = min(ones), max(ones)
                            if exs and min(exs) <= x_hi + 1 and max(exs) >= x_lo - 1:
                                x_lo = min(x_lo, min(exs))
                                x_hi = max(x_hi, max(exs))
                            span = list(range(x_lo, x_hi + 1))
                            for xx in span:
                                for yy in (y0, y0 + 1):
                                    if g[yy][xx] != 14:
                                        g[yy][xx] = 4
                            newc = 12 if (x_lo + 2 == 16 and x_hi + 2 == 21) else 1
                            for xx in span:
                                for yy in (y0, y0 + 1):
                                    if g[yy][xx + 2] != 14:
                                        g[yy][xx + 2] = newc
                        if has_dock:
                            for xx in range(6, 12):
                                for yy in (y0, y0 + 1):
                                    if g[yy][xx] != 14:
                                        g[yy][xx] = 1
                    poured = True
                    break
                if key == 8 and lvl0 == 5:
                    # L5 8-block: dead button so far (t757: no-op, cost 0) —
                    # likely a grip/claw trigger like L4 sq8; condition TBD.
                    FREECLICK[0] = "sq8"
                    break
                if key == 8 and lvl0 == 4:
                    cl = _claw(g)
                    if (cl is not None and cl[2] == "open" and
                            all(g[yy][cl[0] + 6] == 12
                                for yy in range(cl[1] + 2, cl[1] + 6))):
                        # knob crossbar inside the mouth -> CLOSE the claw:
                        # morph OPEN@(ax,ay) -> CLOSED@(ax,ay+1)
                        ax, ay = cl[0], cl[1]
                        # 30 -> 28 cells isn't 1:1; do a remove+place morph.
                        pipe = _pipe()
                        cover = dict(state.get("gcover", {}))
                        newcells = [(ax + rx, ay + 1 + ry) for (rx, ry) in CLAW_CLOSED]
                        newset = set(newcells)
                        newcover = {}
                        for (xx, yy) in newcells:
                            k = "%d,%d" % (xx, yy)
                            if (xx, yy) in set(cl[3]):
                                if k in cover:
                                    newcover[k] = cover[k]
                                continue
                            old = cover.get(k)
                            if old is None:
                                v = g[yy][xx]
                                old = v if v not in (0, 4) else None
                            if old is not None:
                                newcover[k] = old
                        for (xx, yy) in cl[3]:
                            k = "%d,%d" % (xx, yy)
                            if k in cover:
                                g[yy][xx] = cover[k]
                            else:
                                g[yy][xx] = 0 if (xx, yy) in pipe else 4
                        for (xx, yy) in newcells:
                            g[yy][xx] = 8
                        state = dict(state)
                        state["gcover"] = newcover
                        SNAKEMOVE[0] = True  # close costs 5
                    elif cl is not None and cl[2] == "closed":
                        SNAKEMOVE[0] = True  # no-op but still costs 5
                    else:
                        FREECLICK[0] = "sq8"  # away from knob: dead button, 0
                    break
                if grid[y][x] != key:
                    break  # flask not present/clicked off its fill: plain click
                # clicking a flask while e occupies one of its slots:
                # NO swap + big time penalty (+20 units; pinned by t82-t84)
                occupied = False
                for entry in _slots().get(key, []):
                    if entry[0] == "cellswap":
                        continue  # cellswap pairs carry e along — no penalty
                    c, slot, sa, sb = entry
                    for (xx, yy) in _cells(slot):
                        if g[yy][xx] == 14:
                            occupied = True
                if occupied:
                    penalty = True
                elif key == 6 and CURRENT_LEVEL == 5 and (
                        lambda ep5: ep5 is not None and (
                            # aboard = e on the rotor ARMS (not the static
                            # ring-square x8-11,y32-35: t996 rotated fine)
                            (24 <= ep5[1] <= 43 and 8 <= ep5[0] <= 11 and
                             not (32 <= ep5[1] <= 35)) or
                            (32 <= ep5[1] <= 35 and ep5[0] <= 19 and
                             not (8 <= ep5[0] <= 11)))
                        )(_find_player(g)):
                    # e ABOARD the rotor => whole press voided w/ penalty
                    # (t800; frame later settled to the H+V PLUS union —
                    # entered as a history discontinuity).
                    penalty = True
                else:
                    poured, net = _pour(g, key)
                    if key == 6 and CURRENT_LEVEL == 5:
                        # L5 PORTAL NETWORK (t854): the (18,48) slot cellswaps
                        # with the node matching the DIAL colors; the OTHER
                        # nodes phase-flip in place.
                        dial = tuple(state.get("l5dial", (6, 7)))
                        nodes = {(6, 7): (32, 52), (9, 10): (34, 58),
                                 (12, 11): (4, 4)}
                        dest5 = nodes.get(dial)
                        if dest5 is not None:
                            dx5, dy5 = dest5
                            for i in range(4):
                                xa, ya = 18 + i % 2, 48 + i // 2
                                xb, yb = dx5 + i % 2, dy5 + i // 2
                                g[ya][xa], g[yb][xb] = g[yb][xb], g[ya][xa]
                            if E_HINT[0] == (18, 48):
                                E_HINT[0] = dest5
                            elif E_HINT[0] == dest5:
                                E_HINT[0] = (18, 48)
                            # a swapped slot NOT holding e re-renders the dial
                            # pattern with a per-node parity (t753/768/854/878):
                            # (18,48)&(32,52) -> even=dial[0]; others -> dial[1]
                            # on a RIDE the arriving pattern lands FLIPPED
                            # (cA<->cB) at the slot e vacated — but only once
                            # any dial press has happened (raw before: t753/768;
                            # flipped after: t854/878/882).
                            # arrival phase heuristic (imperfect; #890 is a
                            # known 1-off): flip the arriving pattern iff
                            # dial == (9,10).
                            if dial == (9, 10) and not state.get("l5raw9a"):
                                for (sx, sy) in ((18, 48), (dx5, dy5)):
                                    cells5 = [(sx + i % 2, sy + i // 2) for i in range(4)]
                                    other = [(dx5, dy5), (18, 48)][(sx, sy) == (dx5, dy5)]
                                    oc = [(other[0] + i % 2, other[1] + i // 2) for i in range(4)]
                                    if (not all(g[yy][xx] == 14 for xx, yy in oc) or
                                            any(g[yy][xx] == 14 for xx, yy in cells5)):
                                        continue
                                    for (xx, yy) in cells5:
                                        if g[yy][xx] == dial[0]:
                                            g[yy][xx] = dial[1]
                                        elif g[yy][xx] == dial[1]:
                                            g[yy][xx] = dial[0]
                            poured = True
                        for pr, (nx5, ny5) in nodes.items():
                            if (nx5, ny5) == dest5:
                                continue
                            cA, cB = pr
                            for i in range(4):
                                xx, yy = nx5 + i % 2, ny5 + i // 2
                                if g[yy][xx] == cA:
                                    g[yy][xx] = cB
                                elif g[yy][xx] == cB:
                                    g[yy][xx] = cA
                        poured = True  # every L5 6-press is a pour (t899)
                        # L5 ROTOR: all c-cells in zone x0-19,y24-43 rotate
                        # 90deg CW around (9.5,33.5) (t753); covered cells
                        # remembered in state['rcover'] (pipe 0s revealed).
                        rc = dict(state.get("rcover", {}))
                        rot = [(xx, yy) for yy in range(24, 44)
                               for xx in range(0, 20) if g[yy][xx] == 12
                               and not (8 <= xx <= 11 and 32 <= yy <= 35)]
                        newc = [(int(9.5 - (yy - 33.5)), int(33.5 + (xx - 9.5)))
                                for (xx, yy) in rot]
                        rotset = set(rot)
                        newset = set(newc)
                        nrc = {}
                        for (xx, yy) in newc:
                            k = "%d,%d" % (xx, yy)
                            if (xx, yy) in rotset:
                                if k in rc:
                                    nrc[k] = rc[k]
                                continue
                            old = rc.get(k)
                            if old is None:
                                v = g[yy][xx]
                                old = v if v not in (0, 4) else None
                            if old is not None:
                                nrc[k] = old
                        for (xx, yy) in rot:
                            if (xx, yy) in newset or g[yy][xx] == 14:
                                continue
                            k = "%d,%d" % (xx, yy)
                            if k in rc:
                                g[yy][xx] = rc[k]
                            elif 14 <= xx <= 21 and 32 <= yy <= 35:
                                g[yy][xx] = 0  # hidden pipe extension
                            else:
                                g[yy][xx] = 4
                        for (xx, yy) in newc:
                            if g[yy][xx] not in (14, 8):
                                g[yy][xx] = 12
                        state = dict(state)
                        state["rcover"] = nrc
                break
        if poured:
            dv = _divider_x()
            for yy in range(63):
                for xx in range(dv, 64):
                    if g[yy][xx] == 0:
                        g[yy][xx] = 5

    if RECOLORED_E[0] is not None:
        c2 = RECOLORED_E[0]
        carried = ((c2, c2), (c2, c2))
        RECOLORED_E[0] = None
    acts = state.get("acts", 0) + 1
    # UNIFORM cost law (refit over all data): action=5, flask-pour=10,
    # penalty=100, disabled-button (L4 8-square) = 0. den: L0=10,L1-3=15,L4=40.
    if penalty:
        cum += 100
    elif FREECLICK[0] == "sq8":
        cum += 0
    elif poured and not SNAKEMOVE[0]:
        cum += 10
    else:
        cum += 5
    FREECLICK[0] = False
    SNAKEMOVE[0] = False
    DOCKED[0] = False
    ticks = -(-cum // den)
    if ticks > 64:
        info["dead"] = True  # cum beyond full bar = death (t601); bar 64 alive (t600)
        ticks = 64
    for xx in range(64):
        if xx < ticks:
            g[63][xx] = 3
        elif g[63][xx] == 3:
            g[63][xx] = 0

    return g, info, {"cum": cum, "carried": carried, "tdir": tdir, "acts": acts,
                     "gcover": state.get("gcover", {}),
                     "rcover": state.get("rcover", {}),
                     "l5runs": state.get("l5runs"),
                     "l5dial": state.get("l5dial", (6, 7)),
                     "l5dialed": state.get("l5dialed", False),
                     "ccover": state.get("ccover", {}),
                     "cagepos": state.get("cagepos"),
                     "epos": E_HINT[0]}
