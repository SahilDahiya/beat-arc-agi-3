import numpy as np
from collections import deque

# ================= GAME MODEL =================
# A level = rigid PIECES on a 20x20 block lattice (block = 3x3 cells, lattice offset (2,2)).
# A piece is a connected shape; its CONNECTORS are exactly its degree-1 TERMINAL cells
# (verified on every piece of levels 0,1,2).
# Exactly one piece is ACTIVE (= movable). Actions 1-4 translate it 1 block, 5 rotates it
# 90deg CW anchored at its bbox TOP-LEFT, 6 (click) makes the clicked piece active.
# A move is blocked unless every overlap with another piece is CONNECTOR-on-CONNECTOR.
# Two coincident connectors render colour 3 ("bonded"); bonds are NOT persistent.
# GOAL: EVERY connector coincides with another connector (all terminals paired up).
#
# TWO RENDERING MODES (detected from ENTRY_GRID):
#   PLAIN (levels 0,1): active piece's body -> colour 0; other pieces -> their true colour;
#                       every connector visible as 8 (or 3 when bonded).
#   MASK  (level 2)   : active piece -> its TRUE colour, connectors visible as 8;
#                       INACTIVE pieces -> entirely MASK_COLOR 4, connectors HIDDEN.
#   -> in MASK mode a masked piece's true colour cannot be read from ENTRY_GRID; it is only
#      revealed by activating it. Learned values live in LEARNED_COLORS.

S, OX, OY = 3, 2, 2
NBX = (64 - OX) // S
NBY = (64 - OY) // S

SEL_COLOR   = 0
MARK_COLOR  = 8
DOCK_COLOR  = 3
MASK_COLOR  = 4
HIDDEN_TRUE = 15          # true colour of the PLAIN-mode initially-active piece
PALETTE = [15, 14, 11, 10, 9, 6, 7, 5, 2, 1, 13]
# level -> {piece_idx: true colour}. A MASKED piece's colour cannot be read from ENTRY_GRID;
# it is only revealed by activating it, so these are filled in as they are observed.
# Piece palette appears to be {15,14,11,10,9} minus the background, but the ORDER is not
# predictable (L1 piece0..3 = 15,14,11,9 in index order; L2 = 11,14,15 REVERSED) -> just learn them.
LEARNED_COLORS = {2: {2: 15, 0: 11},
                  3: {1: 14, 2: 12, 3: 11}}
# NB colour 12 IS a valid piece colour (level-3 piece2) even though it was the BACKGROUND in
# levels 1-2 -> the piece palette is not a small fixed set; only the current bg is excluded.

BODY, MARK = 1, 2
# sandbox: globals() and next() are NOT available -- use try/except NameError + explicit loops
# !! run_python writes to this file do NOT reinstall the live model. Only write_file/edit_file do.
HUD_Y, HUD_X0, HUD_N = 0, 16, 32
HUD_FULL, HUD_USED = 4, 0
DELTA = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
ROT, CLICK = 5, 6


# Per-level move budget, FITTED from the observed bar (used = round(32*m/B)):
#   L0 -> [74,75]   L1 -> exactly 100   L2 -> [123,128]   L3 -> [65,128] (2 obs so far)
# The old formula 75+25*level (=150 for L3) is REFUTED: L3's bar forces B <= 128.
# Budgets are non-decreasing and L2 >= 123, so L3 is in [123,128] -> 125.
# The model also narrows an exact [lo,hi] from every observation and clamps this guess into it.
LEARNED_BUDGET = {0: 75, 1: 100, 2: 125, 3: 125}


def _lvl():
    try:
        return int(CURRENT_LEVEL or 0)
    except (NameError, TypeError):
        return 0


def _budget_guess():
    return LEARNED_BUDGET.get(_lvl(), 125)


def _hud_used(m, B):
    return min((64 * m + B) // (2 * B), HUD_N)


def _narrow(lo, hi, m, u):
    if m <= 0:
        return lo, hi
    lo = max(lo, 64 * m // (2 * u + 1) + 1)
    if u >= 1:
        hi = min(hi, 64 * m // (2 * u - 1))
    return lo, hi


def _blocks(grid):
    g = np.array(grid, dtype=int)
    return g, g[OY:OY + NBY * S:S, OX:OX + NBX * S:S].copy()


def _components(B, bg):
    seen = np.zeros(B.shape, dtype=bool)
    out = []
    for y in range(NBY):
        for x in range(NBX):
            if B[y, x] != bg and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                cs = []
                while q:
                    cy, cx = q.popleft()
                    cs.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < NBY and 0 <= nx < NBX and B[ny, nx] != bg and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                out.append(cs)
    return out


_CACHE = {}


def _entry_info():
    try:
        eg = ENTRY_GRID
    except NameError:
        return None
    if eg is None:
        return None
    g = np.asarray(eg, dtype=int)
    ck = (g.tobytes(), _lvl())
    if ck in _CACHE:
        return _CACHE[ck]

    _, B = _blocks(g)
    v, c = np.unique(B, return_counts=True)
    bg = int(v[np.argmax(c)])
    comps = sorted(_components(B, bg), key=lambda cc: min(cc))
    plain = any(B[y, x] == SEL_COLOR for cc in comps for (y, x) in cc)

    pieces = []
    for cc in comps:
        Sset = set(cc)
        # CONNECTORS are a DESIGNED subset of the piece, marked colour 8 -- NOT simply every
        # degree-1 leaf (level-3 piece0 has 4 leaves but only 2 connectors).  When the piece is
        # ACTIVE its 8s are visible, so read them.  When MASKED they are hidden; every masked
        # piece seen so far has exactly 2 leaves and both are connectors, so fall back to leaves.
        leaves = {p for p in Sset
                  if sum(((p[0] + d[0], p[1] + d[1]) in Sset)
                         for d in ((1, 0), (-1, 0), (0, 1), (0, -1))) == 1}
        eights = {p for p in Sset if B[p] == MARK_COLOR}
        term = eights if eights else leaves
        ys = [y for y, _ in cc]
        xs = [x for _, x in cc]
        y0, x0 = min(ys), min(xs)
        pat = np.zeros((max(ys) - y0 + 1, max(xs) - x0 + 1), dtype=int)
        for p in Sset:
            pat[p[0] - y0, p[1] - x0] = MARK if p in term else BODY
        bodycols = {int(B[p]) for p in (Sset - term)}
        col = bodycols.pop() if len(bodycols) == 1 else None
        pieces.append({"col": col, "r0": y0, "c0": x0,
                       "oris": [np.rot90(pat, k=-k) for k in range(4)],
                       "shows8": any(B[p] == MARK_COLOR for p in term)})

    # who is ACTIVE at entry?
    sel0 = None
    if plain:
        for i, p in enumerate(pieces):
            if p["col"] == SEL_COLOR:
                sel0 = i
                pieces[i]["col"] = HIDDEN_TRUE     # real colour hidden by the highlight
                break
    else:
        for i, p in enumerate(pieces):
            if p["shows8"]:
                sel0 = i
                break

    # masked pieces: true colour unknowable from ENTRY_GRID -> use learned, else palette
    learned = LEARNED_COLORS.get(_lvl(), {})
    used = {p["col"] for p in pieces if p["col"] not in (None, MASK_COLOR)}
    used |= set(learned.values())          # reserve learned colours BEFORE palette-filling
    used.add(bg)                           # never guess the background colour
    for i, p in enumerate(pieces):
        if p["col"] in (None, MASK_COLOR) and not (plain and i == sel0):
            if i in learned:
                p["col"] = learned[i]
            else:
                for cand in PALETTE:
                    if cand not in used:
                        p["col"] = cand
                        break
            used.add(p["col"])

    info = {"bg": bg, "pieces": pieces, "sel0": sel0, "mask": not plain}
    _CACHE[ck] = info
    return info


def _cells(info, i, pose):
    k, r, c = pose
    o = info["pieces"][i]["oris"][k]
    return {(r + a, c + b): int(o[a, b])
            for a in range(o.shape[0]) for b in range(o.shape[1]) if o[a, b]}


def _canvas(info, poses, sel):
    """MASKING WINS OVER BONDING: in MASK mode a cell belonging only to inactive pieces is
    rendered MASK_COLOR even when two of their connectors are bonded there (CONFIRMED at
    block (13,9): two masked pieces bonded -> rendered 4, not 3)."""
    cv = np.full((NBY, NBX), info["bg"], dtype=int)
    conn = {}
    for i, pose in enumerate(poses):
        for p, kind in _cells(info, i, pose).items():
            if kind == MARK:
                conn.setdefault(p, []).append(i)
            else:
                if info["mask"]:
                    cv[p] = info["pieces"][i]["col"] if i == sel else MASK_COLOR
                else:
                    cv[p] = SEL_COLOR if i == sel else info["pieces"][i]["col"]
    for p, owners in conn.items():
        visible = (not info["mask"]) or (sel in owners)
        if not visible:
            cv[p] = MASK_COLOR
        elif len(owners) >= 2:
            cv[p] = DOCK_COLOR
        else:
            cv[p] = MARK_COLOR
    return cv, {p: len(o) for p, o in conn.items()}


def _render(g, cv, m, B):
    out = g.copy()
    out[OY:OY + NBY * S, OX:OX + NBX * S] = np.kron(cv, np.ones((S, S), dtype=int))
    used = _hud_used(m, B)
    for i in range(HUD_N):
        out[HUD_Y, HUD_X0 + i] = HUD_USED if i < used else HUD_FULL
    return out


def _find_piece_plain(B, info, i, selected):
    """PLAIN mode only: locate piece i from the grid by its BODY colour."""
    col = SEL_COLOR if selected else info["pieces"][i]["col"]
    mask = np.zeros((NBY, NBX), dtype=int)
    mask[B == col] = 1
    for comp in _components(mask, 0):
        oy = min(y for y, _ in comp)
        ox = min(x for _, x in comp)
        norm = frozenset((y - oy, x - ox) for (y, x) in comp)
        for k, p in enumerate(info["pieces"][i]["oris"]):
            z = [(a, b) for a in range(p.shape[0]) for b in range(p.shape[1]) if p[a, b] == BODY]
            if len(z) != len(comp):
                continue
            zy = min(a for a, _ in z)
            zx = min(b for _, b in z)
            if frozenset((a - zy, b - zx) for (a, b) in z) == norm:
                return (k, oy - zy, ox - zx)
    return None


def init_state(entry_grid):
    info = _entry_info()
    if info is None:
        return {"m": 0, "lo": 1, "hi": 10 ** 9, "sel": None, "poses": ()}
    return {"m": 0, "lo": 1, "hi": 10 ** 9, "sel": info["sel0"],
            "poses": tuple((0, p["r0"], p["c0"]) for p in info["pieces"])}


def predict(state, grid, action, x=None, y=None):
    g, B = _blocks(grid)
    info = _entry_info()
    flags = {"level_up": False, "dead": False, "win": False}
    m = int(state.get("m", 0))
    poses = [tuple(p) for p in state.get("poses", ())]
    sel = state.get("sel")

    if info is None:
        return g.tolist(), flags, dict(state, m=m + 1)

    # harness quirk: the GLOBAL FIRST transition is replayed without advancing state.
    # Recover it: one unobserved move happened; re-read the poses straight from the grid.
    if m == 0 and not np.array_equal(g, np.asarray(ENTRY_GRID, dtype=int)):
        m = 1
        if not info["mask"]:
            got = [_find_piece_plain(B, info, i, i == sel) for i in range(len(info["pieces"]))]
            if all(p is not None for p in got):
                poses = got

    nm = m + 1
    lo, hi = _narrow(int(state.get("lo", 1)), int(state.get("hi", 10 ** 9)), m,
                     int(np.sum(g[HUD_Y, HUD_X0:HUD_X0 + HUD_N] != HUD_FULL)))
    bud = min(max(_budget_guess(), lo), hi)

    if action == CLICK and x is not None and y is not None:
        by, bx = (int(y) - OY) // S, (int(x) - OX) // S
        for i, pose in enumerate(poses):
            if (by, bx) in _cells(info, i, pose):
                sel = i
                break
    elif sel is not None and (action in DELTA or action == ROT):
        cur = _cells(info, sel, poses[sel])
        k, r, c = poses[sel]
        cand_pose = (k, r + DELTA[action][0], c + DELTA[action][1]) if action in DELTA \
            else ((k + 1) % 4, r, c)
        cand = _cells(info, sel, cand_pose)
        others = {}
        for i, pose in enumerate(poses):
            if i != sel:
                for p, kk in _cells(info, i, pose).items():
                    others[p] = max(others.get(p, 0), kk)
        ok = True
        for p, kk in cand.items():
            if not (0 <= p[0] < NBY and 0 <= p[1] < NBX):
                ok = False
                break
            if p in others and not (kk == MARK and others[p] == MARK):
                ok = False
                break
        if ok:
            poses[sel] = cand_pose

    cv, conn = _canvas(info, poses, sel)
    if conn and all(n >= 2 for n in conn.values()):
        flags["level_up"] = True
    ns = {"m": nm, "lo": lo, "hi": hi, "sel": sel, "poses": tuple(poses)}
    return _render(g, cv, nm, bud).tolist(), flags, ns


def is_goal(state, grid):
    info = _entry_info()
    if info is None or not state:
        return False
    poses = [tuple(p) for p in state.get("poses", ())]
    if not poses:
        return False
    conn = {}
    for i, pose in enumerate(poses):
        for p, kind in _cells(info, i, pose).items():
            if kind == MARK:
                conn[p] = conn.get(p, 0) + 1
    return bool(conn) and all(n >= 2 for n in conn.values())
