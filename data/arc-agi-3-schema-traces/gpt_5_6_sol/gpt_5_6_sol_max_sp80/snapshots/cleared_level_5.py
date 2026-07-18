# ARC3 falling-block world model (incrementally learned)
# np, ENTRY_GRID, CURRENT_LEVEL are preloaded.
import math

def _timer_tick(a, turn=None):
    # A per-level turn budget is rasterised across an e line on one edge.
    # Timer length is rendered from a hidden per-level budget; state tracks turns.
    entry = np.array(ENTRY_GRID, dtype=int)
    edge_lines = [
        ("row", 0, np.where(entry[0] == 14)[0]),
        ("row", entry.shape[0]-1, np.where(entry[-1] == 14)[0]),
        ("col", 0, np.where(entry[:,0] == 14)[0]),
        ("col", entry.shape[1]-1, np.where(entry[:,-1] == 14)[0]),
    ]
    orient, pos, cells = max(edge_lines, key=lambda z: len(z[2]))
    W = len(cells)
    if W == 0:
        return
    if orient == "row":
        w = int(np.sum(a[pos, cells] == 14))
    else:
        w = int(np.sum(a[cells, pos] == 14))
    # Per-level configured budgets learned from rasterisation.
    budgets = {0:30, 1:45, 2:100, 3:120, 4:100, 5:120}
    budget = budgets.get(int(CURRENT_LEVEL or 0), max(1, 15 * len(_components(entry == 11))))
    if turn is None:
        k, best = 0, 10**9
        for q in range(budget+1):
            qw = int(math.floor(W * (budget-q) / float(budget) + 0.5))
            if abs(qw-w) < best:
                best, k = abs(qw-w), q
        turn = k + 1
    nw = int(math.floor(W * (budget-min(budget,int(turn))) / float(budget) + 0.5))
    forward = ((orient == "row" and pos == 0) or
               (orient == "col" and pos == entry.shape[1]-1))
    kept = cells[:nw] if forward else cells[-nw:]
    if orient == "row":
        a[pos, cells] = 0
        a[pos, kept] = 14
    else:
        a[cells, pos] = 0
        a[kept, pos] = 14

def _shift_colour(a, colour, dx, dy):
    mask = (a == colour)
    if not mask.any():
        return
    ys, xs = np.where(mask)
    bg = 12
    a[mask] = bg
    ny, nx = ys + dy, xs + dx
    ok = (ny >= 1) & (ny < a.shape[0]-4) & (nx >= 0) & (nx < a.shape[1])
    a[ny[ok], nx[ok]] = colour

def _select_at(a, x, y):
    if x is None or y is None or not (0 <= x < a.shape[1] and 0 <= y < a.shape[0]):
        return
    if a[y, x] != 8:
        return
    stack = [(int(x), int(y))]
    seen = set(stack)
    comp = []
    while stack:
        cx, cy = stack.pop()
        if a[cy, cx] != 8:
            continue
        comp.append((cx, cy))
        for nx, ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
            if 0 <= nx < a.shape[1] and 0 <= ny < a.shape[0] and (nx,ny) not in seen and a[ny,nx] == 8:
                seen.add((nx,ny))
                stack.append((nx,ny))
    a[a == 9] = 8
    for cx, cy in comp:
        a[cy, cx] = 9

def _components(mask):
    h, w = mask.shape
    unseen = set((int(x), int(y)) for y, x in zip(*np.where(mask)))
    out = []
    while unseen:
        seed = unseen.pop()
        stack, pts = [seed], [seed]
        while stack:
            cx, cy = stack.pop()
            for q in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                if q in unseen:
                    unseen.remove(q)
                    stack.append(q)
                    pts.append(q)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out.append({"x0":min(xs),"x1":max(xs),"y0":min(ys),"y1":max(ys)})
    return out

def _unit_size(entry):
    src = _components(np.array(entry, dtype=int) == 6)
    if not src:
        return 4
    return min(min(s["x1"]-s["x0"]+1, s["y1"]-s["y0"]+1) for s in src)

def _runs(vals):
    ans = []
    for v in sorted(set(vals)):
        if not ans or v > ans[-1][-1] + 1:
            ans.append([v])
        else:
            ans[-1].append(v)
    return ans

def _routing_solution_elbow(entry, fmask, direction, sources, platforms,
                             fparts=None):
    """Route a board containing a colour-15 elbow.  Rays may change axis, so
    the one-axis sweep used on earlier boards is replaced by a small event
    tracer.  The colour-15 device can send a stripe sideways; when that
    sideways stripe reaches an ordinary horizontal bar, it wets the bar and
    resumes the board's global upward flow from the bar's left/right ends.

    The observed ff/.f elbow accepts an upward ray and turns it left along the
    row of the first colour-15 cell that ray reaches.  Geometry is derived from
    the entry mask rather than fixed coordinates.
    """
    if direction not in ("up", "down"):
        return False
    fmask = np.array(fmask, dtype=bool)
    if fparts is None:
        fcomps = _components(fmask)
        for f in fcomps:
            f["_cells"] = set((x,y)
                              for y in range(f["y0"], f["y1"]+1)
                              for x in range(f["x0"], f["x1"]+1)
                              if fmask[y,x])
    else:
        fcomps = fparts
    if not fcomps:
        return False

    # Record the direction-facing opening of every cup.  A top U-cup has an
    # "up" opening on its bottom edge; the side U-cup has a "left" opening on
    # its right edge.
    wanted = {"up": [], "down": [], "left": [], "right": []}
    for c in _components(entry == 11):
        sides = {
            "up": [x for x in range(c["x0"], c["x1"]+1)
                    if entry[c["y1"], x] != 11],
            "down": [x for x in range(c["x0"], c["x1"]+1)
                      if entry[c["y0"], x] != 11],
            "left": [y for y in range(c["y0"], c["y1"]+1)
                      if entry[y, c["x1"]] != 11],
            "right": [y for y in range(c["y0"], c["y1"]+1)
                       if entry[y, c["x0"]] != 11],
        }
        for d, vals in sides.items():
            for run in _runs(vals):
                wanted[d].append((run[0], run[-1]))
    if not any(wanted.values()):
        return False

    def tspan(p, d):
        return ((p["x0"], p["x1"]) if d in ("up", "down")
                else (p["y0"], p["y1"]))

    def blocked(p, d, interval):
        lo, hi = interval
        for q in platforms:
            if q is p:
                continue
            qlo, qhi = tspan(q, d)
            if hi < qlo or lo > qhi:
                continue
            if d == "up" and q["y0"] == p["y1"] + 1:
                return True
            if d == "down" and q["y1"] == p["y0"] - 1:
                return True
            if d == "left" and q["x0"] == p["x1"] + 1:
                return True
            if d == "right" and q["x1"] == p["x0"] - 1:
                return True
        return False

    def special_lateral_blocked(f, interval):
        # Two elbow sprites can be placed edge-to-edge.  A cell of the upstream
        # elbow occupying an otherwise open lateral band seals that straight
        # outlet, while the elbow's turned arm remains active.
        lo, hi = interval
        for g in fcomps:
            if g is f or g["y0"] >= f["y0"]:
                continue
            for xx,yy in g.get("_cells", set()):
                if lo <= xx <= hi and f["y0"] <= yy <= f["y1"]:
                    return True
        for p in platforms:
            if (p["y0"] < f["y0"] and
                    not (hi < p["x0"] or lo > p["x1"] or
                         p["y1"] < f["y0"] or p["y0"] > f["y1"])):
                return True
        return False

    def lateral_outlet_occupied(f, d, interval):
        # A turned ray needs one clear cell beside the elbow before it can
        # propagate.  An object touching that outlet seals it; with a gap, the
        # ray reaches the object normally and is split by it.  Level 5 directly
        # contrasts these two cases.
        lo, hi = interval
        xx = f["x0"]-1 if d == "left" else f["x1"]+1
        for g in fcomps:
            if g is f:
                continue
            if any(x == xx and lo <= y <= hi
                   for x,y in g.get("_cells", set())):
                return True
        for p in platforms:
            if p["x0"] <= xx <= p["x1"] and not (hi < p["y0"] or lo > p["y1"]):
                return True
        return False

    # Rays are (direction, transverse lo, transverse hi, longitudinal start).
    queue = [(direction, int(lo), int(hi), int(pos))
             for lo, hi, pos in sources]
    seen = set()
    terminal = {"up": [], "down": [], "left": [], "right": []}
    while queue and len(seen) < 512:
        d, lo, hi, pos = queue.pop(0)
        key = (d, lo, hi, pos)
        if key in seen:
            continue
        seen.add(key)
        candidates = []
        for p in platforms:
            pl, pr = tspan(p, d)
            if hi < pl or lo > pr:
                continue
            if d == "up" and p["y1"] <= pos:
                candidates.append((pos-p["y1"], "platform", p))
            elif d == "down" and p["y0"] >= pos:
                candidates.append((p["y0"]-pos, "platform", p))
            elif d == "left" and p["x1"] <= pos:
                candidates.append((pos-p["x1"], "platform", p))
            elif d == "right" and p["x0"] >= pos:
                candidates.append((p["x0"]-pos, "platform", p))

        # For each transverse pixel, an upward ray first reaches that
        # column's lowest colour-15 pixel.  A different leg of the same elbow
        # can therefore turn the ray on a different row.
        if d == "up":
            for f in fcomps:
                contacts = []
                for xx in range(max(lo, f["x0"]), min(hi, f["x1"])+1):
                    ys = [yy for yy in range(f["y0"], f["y1"]+1)
                          if (xx,yy) in f["_cells"]]
                    if ys:
                        contacts.append((max(ys), xx))
                if contacts:
                    cy = max(z[0] for z in contacts)
                    cxs = [xx for yy,xx in contacts if yy == cy]
                    if cy <= pos:
                        candidates.append((pos-cy, "elbow",
                                           (f, cy, min(cxs), max(cxs))))
        elif d == "down":
            for f in fcomps:
                contacts = []
                for xx in range(max(lo, f["x0"]), min(hi, f["x1"])+1):
                    ys = [yy for yy in range(f["y0"], f["y1"]+1)
                          if (xx,yy) in f["_cells"] and yy >= pos]
                    if ys:
                        contacts.append((min(ys), xx))
                if contacts:
                    cy = min(z[0] for z in contacts)
                    cxs = [xx for yy,xx in contacts if yy == cy]
                    if cy >= pos:
                        candidates.append((cy-pos, "elbow",
                                           (f, cy, min(cxs), max(cxs))))
        elif d in ("left", "right"):
            # A sideways ray treats an elbow's occupied 2x2 envelope as a
            # solid splitter if it encounters one downstream.
            for f in fcomps:
                if hi < f["y0"] or lo > f["y1"]:
                    continue
                if d == "left" and f["x1"] <= pos:
                    candidates.append((pos-f["x1"], "special_block", f))
                elif d == "right" and f["x0"] >= pos:
                    candidates.append((f["x0"]-pos, "special_block", f))

        if not candidates:
            limit = entry.shape[1] if d in ("up", "down") else entry.shape[0]
            if not (hi < 0 or lo >= limit):
                terminal[d].append((lo, hi))
            continue

        _, kind, obj = min(candidates, key=lambda z: z[0])
        if kind == "elbow":
            f, cy, bx0, bx1 = obj
            width = hi-lo+1
            if d == "up":
                bottom_xs = [x for x in range(f["x0"], f["x1"]+1)
                             if (x,f["y1"]) in f["_cells"]]
                arm_left = bool(bottom_xs and min(bottom_xs) > f["x0"])
                # Upward ff/.f funnels to its bottom row, then turns toward
                # its horizontal arm (level 4).
                out_y = f["y1"]
                if arm_left:
                    queue.append(("left", out_y-width+1, out_y, f["x0"]-1))
                else:
                    queue.append(("right", out_y-width+1, out_y, f["x1"]+1))
            else:
                top_xs = [x for x in range(f["x0"], f["x1"]+1)
                          if (x,f["y0"]) in f["_cells"]]
                top_left = bool(top_xs and max(top_xs) < f["x1"])
                mid = (f["x0"] + f["x1"]) // 2
                enters_left = ((lo+hi)//2 <= mid)
                out_y = f["y0"]
                if top_left:
                    # f./ff entered down its left leg: one stripe continues
                    # down outside the left edge and one turns right.
                    if enters_left:
                        straight = (f["x0"]-width, f["x0"]-1)
                        if not special_lateral_blocked(f, straight):
                            queue.append(("down", straight[0], straight[1],
                                          f["y1"]+1))
                    lateral = (out_y, out_y+width-1)
                    if not lateral_outlet_occupied(f, "right", lateral):
                        queue.append(("right", lateral[0], lateral[1], f["x1"]+1))
                else:
                    # .f/ff is the mirror: left-arm entry turns left only;
                    # right-leg entry additionally continues down on the right.
                    lateral = (out_y, out_y+width-1)
                    if not lateral_outlet_occupied(f, "left", lateral):
                        queue.append(("left", lateral[0], lateral[1], f["x0"]-1))
                    if not enters_left:
                        straight = (f["x1"]+1, f["x1"]+width)
                        if not special_lateral_blocked(f, straight):
                            queue.append(("down", straight[0], straight[1],
                                          f["y1"]+1))
            continue

        p = obj
        width = hi-lo+1
        pl, pr = tspan(p, d)
        exits = [(pl-width, pl-1), (pr+1, pr+width)]
        outdir = d
        if d == "up":
            npos = p["y0"]-1
        elif d == "down":
            npos = p["y1"]+1
        elif d == "left":
            npos = p["x0"]-1
        else:
            npos = p["x1"]+1
        for out in exits:
            if not blocked(p, outdir, out):
                queue.append((outdir, out[0], out[1], npos))

    def merged(items):
        ans = []
        for lo, hi in sorted((int(lo), int(hi)) for lo, hi in items):
            if ans and lo <= ans[-1][1]:
                ans[-1] = (ans[-1][0], max(ans[-1][1], hi))
            else:
                ans.append((lo, hi))
        return ans

    for d in terminal:
        if merged(terminal[d]) != sorted(wanted[d]):
            return False
    return True


def _routing_solution(a, objects=None):
    # Trace each source stripe through every 8/9 splitter.  On hitting a
    # splitter, flow continues from equal-width stripes just outside both ends.
    entry = np.array(ENTRY_GRID, dtype=int)
    y6, x6 = np.where(entry == 6)
    source_comps = _components(entry == 6)
    # Embedded emitter caps can move with a composite sprite, so read their
    # current rendered positions rather than their entry positions.
    cap_comps = _components(np.array(a, dtype=int) == 4)
    if not source_comps or not cap_comps:
        return False
    # Colour 4 may also mark fixed blockers.  Emitter caps are the 4
    # components nearest/adjacent to a 6 source.
    def gap(p, q):
        gx = max(0, p["x0"]-q["x1"]-1, q["x0"]-p["x1"]-1)
        gy = max(0, p["y0"]-q["y1"]-1, q["y0"]-p["y1"]-1)
        return gx + gy
    scores = [(min(gap(c,s) for s in source_comps), c) for c in cap_comps]
    bestgap = min(z[0] for z in scores)
    caps = [c for d,c in scores if d == bestgap]
    sxmean = sum((s["x0"]+s["x1"])/2.0 for s in source_comps)/len(source_comps)
    symean = sum((s["y0"]+s["y1"])/2.0 for s in source_comps)/len(source_comps)
    cxmean = sum((c["x0"]+c["x1"])/2.0 for c in caps)/len(caps)
    cymean = sum((c["y0"]+c["y1"])/2.0 for c in caps)/len(caps)
    dx, dy = sxmean-cxmean, symean-cymean
    sources = []
    if abs(dy) >= abs(dx):
        direction = "down" if dy > 0 else "up"
        for s in source_comps:
            start = s["y1"]+1 if direction == "down" else s["y0"]-1
            sources.append((s["x0"], s["x1"], start))
    else:
        direction = "right" if dx > 0 else "left"
        for s in source_comps:
            start = s["x1"]+1 if direction == "right" else s["x0"]-1
            sources.append((s["y0"], s["y1"], start))
    # A standalone yellow cap is also an emitter in the same direction,
    # beginning immediately beyond itself (level 3 introduces this motif).
    isolated_caps = [c for c in cap_comps if min(gap(c,s) for s in source_comps) > 0]
    for c in isolated_caps:
        if direction == "down":
            sources.append((c["x0"], c["x1"], c["y1"]+1))
        elif direction == "up":
            sources.append((c["x0"], c["x1"], c["y0"]-1))
        elif direction == "right":
            sources.append((c["y0"], c["y1"], c["x1"]+1))
        else:
            sources.append((c["y0"], c["y1"], c["x0"]-1))

    # Locate movable colour-15 elbows.  State preserves separate sprite
    # identities even when two same-colour elbows touch; the rendered mask alone
    # would merge them into one component.
    special = np.zeros_like(a, dtype=bool)
    fparts = []
    if objects is not None:
        for o in objects:
            if not any(int(col) == 15 for dx,dy,col in o["cells"]):
                continue
            pts = set()
            for dx,dy,col in o["cells"]:
                if int(col) != 15:
                    continue
                xx, yy = int(o["x"])+int(dx), int(o["y"])+int(dy)
                if 0 <= yy < a.shape[0] and 0 <= xx < a.shape[1]:
                    pts.add((xx,yy))
                    special[yy,xx] = True
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                fparts.append({"x0":min(xs),"x1":max(xs),
                               "y0":min(ys),"y1":max(ys),
                               "_cells":pts})
    elif np.any(entry == 15):
        special = (a == 15)
        ef = _components(entry == 15)[0]
        eh, ew = ef["y1"]-ef["y0"]+1, ef["x1"]-ef["x0"]+1
        en = int(np.sum(entry[ef["y0"]:ef["y1"]+1,
                              ef["x0"]:ef["x1"]+1] == 15))
        for q in _components(a == 9):
            sub9 = (a[q["y0"]:q["y1"]+1, q["x0"]:q["x1"]+1] == 9)
            if (q["y1"]-q["y0"]+1 == eh and q["x1"]-q["x0"]+1 == ew
                    and int(np.sum(sub9)) == en):
                special[q["y0"]:q["y1"]+1, q["x0"]:q["x1"]+1] |= sub9

    # A multicolour sprite is one continuous flow-spreading platform
    # across its whole visible span, even when an embedded yellow emitter
    # separates its platform-coloured lobes.  Selected elbow pixels (also 9)
    # are excluded from ordinary platforms.
    platform_pixels = (a == 8) | ((a == 9) & (~special))
    logical = platform_pixels | (a == 4)
    platforms = []
    for p in _components(logical):
        subp = platform_pixels[p["y0"]:p["y1"]+1, p["x0"]:p["x1"]+1]
        if np.any(subp):
            platforms.append(p)
    if np.any(entry == 15):
        return _routing_solution_elbow(entry, special, direction, sources, platforms,
                                         fparts if fparts else None)

    cups = _components(entry == 11)
    holes = []
    for c in cups:
        if direction == "down":
            vals = [x for x in range(c["x0"],c["x1"]+1) if entry[c["y0"],x] != 11]
        elif direction == "up":
            vals = [x for x in range(c["x0"],c["x1"]+1) if entry[c["y1"],x] != 11]
        elif direction == "right":
            vals = [y for y in range(c["y0"],c["y1"]+1) if entry[y,c["x0"]] != 11]
        else:
            vals = [y for y in range(c["y0"],c["y1"]+1) if entry[y,c["x1"]] != 11]
        for run in _runs(vals):
            holes.append((run[0], run[-1]))
    if not holes:
        return False

    def merge_streams(items):
        # Coincident/overlapping stripes merge; merely adjacent unit stripes
        # remain distinct unless a platform surface brings them together.
        ans = []
        for lo,hi in sorted((int(lo),int(hi)) for lo,hi in items):
            if ans and lo <= ans[-1][1]:
                ans[-1] = (ans[-1][0], max(ans[-1][1],hi))
            else:
                ans.append((lo,hi))
        return ans

    # Sweep along the flow axis. Sources are injected at their longitudinal
    # start; all coexisting transverse stripes are merged before the next
    # platform layer. This fixes the adjacent-stream widening seen on level 3.
    source_events = {}
    for lo,hi,pos in sources:
        source_events.setdefault(int(pos), []).append((lo,hi))
    platform_events = {}
    for p in platforms:
        if direction == "down":
            pos = p["y0"]
        elif direction == "up":
            pos = p["y1"]
        elif direction == "right":
            pos = p["x0"]
        else:
            pos = p["x1"]
        platform_events.setdefault(int(pos), []).append(p)
    positions = sorted(set(source_events) | set(platform_events),
                       reverse=(direction in ("up","left")))
    active = []
    for pos in positions:
        if pos in source_events:
            active = merge_streams(active + source_events[pos])
        layer = platform_events.get(pos, [])
        if not layer or not active:
            continue

        def transverse_span(p):
            return ((p["x0"],p["x1"]) if direction in ("down","up")
                    else (p["y0"],p["y1"]))

        def exit_blocked(p, interval):
            # A platform immediately upstream and diagonally beside p occupies
            # the lateral spreading band and seals that outlet. This is why
            # level3's P5 directly above-right of P0 suppressed P0's right arm.
            lo,hi = interval
            for q in platforms:
                if q is p:
                    continue
                qlo,qhi = transverse_span(q)
                if hi < qlo or lo > qhi:
                    continue
                if direction == "down" and q["y1"] == p["y0"]-1:
                    return True
                if direction == "up" and q["y0"] == p["y1"]+1:
                    return True
                if direction == "right" and q["x1"] == p["x0"]-1:
                    return True
                if direction == "left" and q["x0"] == p["x1"]+1:
                    return True
            return False

        outgoing = []
        for lo,hi in active:
            hits = []
            for p in layer:
                pl,pr = transverse_span(p)
                if not (hi < pl or lo > pr):
                    hits.append((p,pl,pr))
            if not hits:
                outgoing.append((lo,hi))
                continue
            width = hi-lo+1
            for p,pl,pr in hits:
                left = (pl-width, pl-1)
                right = (pr+1, pr+width)
                if not exit_blocked(p,left):
                    outgoing.append(left)
                if not exit_blocked(p,right):
                    outgoing.append(right)
        active = merge_streams(outgoing)

    transverse_limit = entry.shape[1] if direction in ("up","down") else entry.shape[0]
    visible = [q for q in active if not (q[1] < 0 or q[0] >= transverse_limit)]
    return sorted(visible) == sorted(holes)

def _initial_objects(entry):
    """Persistent sprites may contain several platform lobes joined by a
    differently-coloured cell (level 3's 8-4-8 emitter/splitter sprite)."""
    arr = np.array(entry, dtype=int)
    candidate = (arr == 8) | (arr == 9) | (arr == 4) | (arr == 15)
    comps = sorted(_components(candidate),
                   key=lambda q: (q["y0"], q["x0"], q["y1"], q["x1"]))
    # A selected colour-15 elbow is rendered entirely as 9, hiding its
    # base type.  Recover it by matching the dimensions/cell-count of another
    # visible colour-15 elbow on the same entry board.
    f_templates = []
    for f in _components(arr == 15):
        f_templates.append((f["x1"]-f["x0"]+1,
                            f["y1"]-f["y0"]+1,
                            int(np.sum(arr[f["y0"]:f["y1"]+1,
                                           f["x0"]:f["x1"]+1] == 15))))
    objects = []
    selected = None
    for q in comps:
        sub = arr[q["y0"]:q["y1"]+1, q["x0"]:q["x1"]+1]
        sig = (q["x1"]-q["x0"]+1, q["y1"]-q["y0"]+1,
               int(np.sum(sub == 9)))
        selected_elbow = (np.any(sub == 9) and
                          not np.any((sub == 8) | (sub == 4) | (sub == 15)) and
                          sig in f_templates)
        if not np.any((sub == 8) | (sub == 9) | (sub == 15)):
            continue
        cells = []
        for yy in range(q["y0"], q["y1"]+1):
            for xx in range(q["x0"], q["x1"]+1):
                if arr[yy,xx] in (4,8,9,15):
                    # Platform pixels remember neutral colour8; selection is
                    # an object property. Embedded 4 and elbow 15 retain type.
                    if arr[yy,xx] == 4:
                        col = 4
                    elif arr[yy,xx] == 15 or (arr[yy,xx] == 9 and selected_elbow):
                        col = 15
                    else:
                        col = 8
                    cells.append([xx-q["x0"], yy-q["y0"], col])
        i = len(objects)
        objects.append({"x":int(q["x0"]), "y":int(q["y0"]),
                        "home_x":int(q["x0"]), "home_y":int(q["y0"]),
                        "w":int(q["x1"]-q["x0"]+1),
                        "h":int(q["y1"]-q["y0"]+1),
                        "cells":cells})
        if np.any(sub == 9):
            selected = i
    return objects, selected

def _render_objects(objects, selected):
    # Remove each sprite at its home pose, then redraw all current poses.
    # The selected sprite is topmost; embedded non-platform colours retain
    # their own colour while its platform lobes toggle 8/9 together.
    a = np.array(ENTRY_GRID, dtype=int).copy()
    h, w = a.shape
    for o in objects:
        for dx,dy,col in o["cells"]:
            hx, hy = int(o["home_x"])+int(dx), int(o["home_y"])+int(dy)
            if 0 <= hx < w and 0 <= hy < h:
                a[hy,hx] = 12
    order = [i for i in range(len(objects)) if i != selected]
    if selected is not None and 0 <= selected < len(objects):
        order.append(selected)
    for i in order:
        o = objects[i]
        for dx,dy,col in o["cells"]:
            xx, yy = int(o["x"])+int(dx), int(o["y"])+int(dy)
            if 0 <= xx < w and 0 <= yy < h:
                if col in (8,15):
                    a[yy,xx] = 9 if i == selected else col
                else:
                    a[yy,xx] = col
    return a

def init_state(entry_grid):
    objects, selected = _initial_objects(entry_grid)
    turn = 1 if CURRENT_LEVEL == 0 else 0
    # The run's first-ever action (level 0 action2) is unscored and is not
    # rolled through predict(), so seed both its timer and sprite displacement.
    if CURRENT_LEVEL == 0 and selected is not None:
        objects[selected]["y"] += _unit_size(entry_grid)
    return {"turn": turn, "tests": 0, "objects": objects, "selected": selected}

def predict(state, grid, action, x=None, y=None):
    if not state or "objects" not in state:
        state = init_state(ENTRY_GRID)
    objects = [dict(o) for o in state.get("objects", [])]
    selected = state.get("selected", None)
    unit = _unit_size(ENTRY_GRID)

    if selected is not None and 0 <= selected < len(objects):
        if action == 1:
            objects[selected]["y"] -= unit
        elif action == 2:
            objects[selected]["y"] += unit
        elif action == 3:
            objects[selected]["x"] -= unit
        elif action == 4:
            objects[selected]["x"] += unit
    if action == 6 and x is not None and y is not None:
        # A click selects a visible unselected ordinary platform (8) or
        # colour-15 elbow.  Both render as 9 while selected.
        shown = np.array(grid, dtype=int)
        if (0 <= int(y) < shown.shape[0] and 0 <= int(x) < shown.shape[1] and
                shown[int(y),int(x)] in (8,15)):
            hits = []
            for i,o in enumerate(objects):
                if (i != selected and o["x"] <= int(x) < o["x"]+o["w"] and
                        o["y"] <= int(y) < o["y"]+o["h"]):
                    hits.append(i)
            if hits:
                selected = hits[-1]

    a = _render_objects(objects, selected)
    tests = int(state.get("tests", 0))
    # Four animated flow previews are available.  A fifth press is rejected
    # immediately as game-over (observed as a one-cell timer tick, no animation).
    test_exhausted = (action == 5 and tests >= 4)
    solved = (action == 5 and not test_exhausted and _routing_solution(a, objects))
    # After an unsuccessful test, a displaced composite emitter sprite becomes
    # the active/selected sprite again (the UI's routing-error focus).
    if action == 5 and not solved:
        moved_emitters = []
        for i,o in enumerate(objects):
            has_emitter = any(int(col) == 4 for dx,dy,col in o["cells"])
            moved = (int(o["x"]) != int(o["home_x"]) or
                     int(o["y"]) != int(o["home_y"]))
            if has_emitter and moved:
                moved_emitters.append(i)
        if moved_emitters:
            selected = moved_emitters[-1]
            a = _render_objects(objects, selected)
        elif np.any(np.array(ENTRY_GRID, dtype=int) == 15):
            special_count = sum(1 for o in objects
                if any(int(col) == 15 for dx,dy,col in o["cells"]))
            selected_special = (selected is not None and
                any(int(col) == 15 for dx,dy,col in objects[selected]["cells"]))
            # A one-elbow board always refocuses its main splitter.  With two
            # elbows, an elbow selection persists, but a failed ordinary
            # selection refocuses the widest ordinary composite.
            if not (special_count > 1 and selected_special):
                ordinary = []
                for i,o in enumerate(objects):
                    if any(int(col) == 8 for dx,dy,col in o["cells"]):
                        ordinary.append((int(o["w"]), i))
                if ordinary:
                    selected = max(ordinary)[1]
                    a = _render_objects(objects, selected)
    turn = int(state.get("turn", 0)) + (1 if action in (1,2,3,4,5,6) else 0)
    if action in (1,2,3,4,5,6):
        _timer_tick(a, turn)
    tests = tests + (1 if action == 5 else 0)
    final_level = (CURRENT_LEVEL is not None and int(CURRENT_LEVEL) >= 5)
    info = {"level_up": bool(solved), "dead": bool(test_exhausted),
            "win": bool(solved and final_level)}
    next_state = {"turn": turn, "tests": tests,
                  "objects": objects, "selected": selected}
    return a.tolist(), info, next_state

def is_goal(state, grid):
    # Completion requires pressing test/fire; step's level_up is the BFS goal.
    return False
