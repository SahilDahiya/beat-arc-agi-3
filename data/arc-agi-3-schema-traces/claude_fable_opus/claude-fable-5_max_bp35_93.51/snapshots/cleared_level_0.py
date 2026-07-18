# World model v3 — tile-lattice scrolling world + balloon character + click-pop
# Colors: 5=bg(solid), 3=texture dots(solid), 10(a)=open, 14(e)=poppable tiles, 9=body, 11=eye, 15=HUD, 0=HUD empty
# Tile lattice: 6px pitch, tile origins at rows/cols ≡ 1 (mod 6); each tile is the 5x5 interior;
#   1px gap strips between tiles are COSMETIC (bg there does not block movement).
# Char: 5x5 box sprite at a tile; actions 3/4 = move one tile L/R if destination tile open;
#   then auto-RISES tile by tile while tile above is open (balloon). All in one transition.
# Click (action 6) on an 'e' tile POPS it: its 25 cells -> 'a' (10). (Distance limits unknown yet.)
# Camera: vertical only, pins char box top at VIEW ROW 37; row 63 = HUD counter (+1 f/action).

BODY, EYE, FLOOR, BG, DOT, TILE = 9, 11, 10, 5, 3, 14
ANCHOR_ROW = 37

LEVEL0_TOP = [
    (-60, '5555555555555555555555555555555555555555555555555555555555555555'),
    (-59, '5535555535555aaaaaa55755aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-58, '5555555555555aaaaaa57775aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-57, '5555555555555aaaaaa55755aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-56, '5355555355555aaaaaaa555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-55, '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555'),
    (-54, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-53, '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-52, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-51, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-50, '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-49, '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555'),
    (-48, '5555555555555555555555555555555555555555555555555555555555555555'),
    (-47, '55355555355555355555355555355553eee353eee353eee35535555535555535'),
    (-46, '5555555555555555555555555555555eeeee5eeeee5eeeee5555555555555555'),
    (-45, '5555555555555555555555555555555eeeee5eeeee5eeeee5555555555555555'),
    (-44, '5355555355555355555355555355555eeeee5eeeee5eeeee5355555355555355'),
    (-43, '55553555553555553555553555553553eee353eee353eee35555355555355555'),
    (-42, '5555555555555555555555555555555555555555555555555555555555555555'),
    (-41, '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-40, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-39, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-38, '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-37, '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555'),
    (-36, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-35, '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-34, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-33, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-32, '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-31, '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555'),
    (-30, '5555555555555aaaaaaaaaaa5555555555555555555aaaaaaaaaaa5555555555'),
    (-29, '5535555535555aaaaaaaaaaa53eee353eee353eee35aaaaaaaaaaa5535555535'),
    (-28, '5555555555555aaaaaaaaaaa5eeeee5eeeee5eeeee5aaaaaaaaaaa5555555555'),
    (-27, '5555555555555aaaaaaaaaaa5eeeee5eeeee5eeeee5aaaaaaaaaaa5555555555'),
    (-26, '5355555355555aaaaaaaaaaa5eeeee5eeeee5eeeee5aaaaaaaaaaa5355555355'),
    (-25, '5555355555355aaaaaaaaaaa53eee353eee353eee35aaaaaaaaaaa5555355555'),
    (-24, '5555555555555aaaaaaaaaaa5555555555555555555aaaaaaaaaaa5555555555'),
    (-23, '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-22, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-21, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-20, '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-19, '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555'),
    (-18, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-17, '5535555535555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-16, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-15, '5555555555555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-14, '5355555355555aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-13, '5555355555355aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5555355555'),
    (-12, '5555555555555555555555555555555555555555555555555555555555555555'),
    (-11, '55355555355553eee353eee353eee35535555535555535555535555535555535'),
    (-10, '5555555555555eeeee5eeeee5eeeee5555555555555555555555555555555555'),
    (-9, '5555555555555eeeee5eeeee5eeeee5555555555555555555555555555555555'),
    (-8, '5355555355555eeeee5eeeee5eeeee5355555355555355555355555355555355'),
    (-7, '55553555553553eee353eee353eee35555355555355555355555355555355555'),
    (-6, '5555555555555555555555555555555555555555555555555555555555555555'),
    (-5, '55355555355553eee353eee353eee35aaaaaaaaaaaaaaaaaaaaaaa5535555535'),
    (-4, '5555555555555eeeee5eeeee5eeeee5aaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-3, '5555555555555eeeee5eeeee5eeeee5aaaaaaaaaaaaaaaaaaaaaaa5555555555'),
    (-2, '5355555355555eeeee5eeeee5eeeee5aaaaaaaaaaaaaaaaaaaaaaa5355555355'),
    (-1, '55553555553553eee353eee353eee35aaaaaaaaaaaaaaaaaaaaaaa5555355555'),
]

def bg_at(wr, wc):
    m = wr % 6
    if m == 1 and wc % 6 == 2: return DOT
    if m == 4 and wc % 6 == 1: return DOT
    if m == 5 and wc % 6 == 4: return DOT
    return BG

def find_sprite_view(grid):
    cells9 = [(r, c) for r in range(63) for c in range(64) if grid[r][c] == BODY]
    if not cells9:
        return None
    cellsb = [(r, c) for r in range(63) for c in range(64) if grid[r][c] == EYE]
    r0 = min(r for r, c in cells9)
    allc = [c for r, c in cells9 + cellsb]
    c0 = min(allc) - 1
    facing = 'R'
    if cellsb and cellsb[0][1] == c0 + 1:
        facing = 'L'
    return r0, c0, facing

def ingest(st, grid):
    off = st['offset']
    for v in range(63):
        for c in range(64):
            st['world'][(v + off, c)] = grid[v][c]
    sp = find_sprite_view(grid)
    if sp:
        r0, c0, facing = sp
        for rr in range(5):
            for cc in range(5):
                st['world'][(r0 + rr + off, c0 + cc)] = FLOOR
        st['char'] = (r0 + off, c0, facing)

def init_state(entry_grid):
    st = {'world': {}, 'offset': 0, 'char': None}
    if CURRENT_LEVEL == 0:
        for wr, rowstr in LEVEL0_TOP:
            for wc, ch in enumerate(rowstr):
                st['world'][(wr, wc)] = int(ch, 16)
    ingest(st, entry_grid)
    return st

def wget(st, wr, wc):
    v = st['world'].get((wr, wc))
    if v is None:
        v = bg_at(wr, wc)
    return v

def tile_open(st, tr, tc):
    """Is the 5x5 tile at origin (tr,tc) fully open ('a')?"""
    return all(wget(st, tr + rr, tc + cc) == FLOOR for rr in range(5) for cc in range(5))

def tile_is_e(st, tr, tc):
    """Is the 5x5 tile at origin (tr,tc) an 'e' tile? (center cell = 14)"""
    return wget(st, tr + 2, tc + 2) == TILE

def tile_origin(wr, wc):
    """Tile origin containing world cell (wr,wc), or None if in a gap strip."""
    ro = (wr - 1) % 6
    co = (wc - 1) % 6
    if ro > 4 or co > 4:
        return None
    return wr - ro, wc - co

def pop_tile(st, tr, tc):
    # pop opens the 5x5 tile cells...
    for rr in range(5):
        for cc in range(5):
            st['world'][(tr + rr, tc + cc)] = FLOOR
    # ...then adjacent 1px gap cells MELT iff both across-gap neighbors are open
    for cc in range(5):
        c = tc + cc
        if wget(st, tr - 2, c) == FLOOR and wget(st, tr, c) == FLOOR:
            st['world'][(tr - 1, c)] = FLOOR
        if wget(st, tr + 4, c) == FLOOR and wget(st, tr + 6, c) == FLOOR:
            st['world'][(tr + 5, c)] = FLOOR
    for rr in range(5):
        r = tr + rr
        if wget(st, r, tc - 2) == FLOOR and wget(st, r, tc) == FLOOR:
            st['world'][(r, tc - 1)] = FLOOR
        if wget(st, r, tc + 4) == FLOOR and wget(st, r, tc + 6) == FLOOR:
            st['world'][(r, tc + 5)] = FLOOR

def draw_sprite(g, r0, c0, facing):
    for rr in range(4):
        for cc in range(5):
            g[r0 + rr][c0 + cc] = BG
    for cc in (1, 2, 3):
        g[r0 + 4][c0 + cc] = BG
    g[r0 + 4][c0 + 0] = FLOOR
    g[r0 + 4][c0 + 4] = FLOOR
    g[r0 + 0][c0 + 2] = BODY
    g[r0 + 3][c0 + 2] = BODY
    for rr in (1, 2):
        g[r0 + rr][c0 + 2] = BODY
        if facing == 'L':
            g[r0 + rr][c0 + 1] = EYE
            g[r0 + rr][c0 + 3] = BODY
        else:
            g[r0 + rr][c0 + 1] = BODY
            g[r0 + rr][c0 + 3] = EYE

def render(st, grid, action):
    off = st['offset']
    g = []
    for v in range(63):
        row = [wget(st, v + off, c) for c in range(64)]
        g.append(row)
    wr, wc, facing = st['char']
    draw_sprite(g, wr - off, wc, facing)
    hud = list(grid[63])
    if action != 0:
        for i in range(64):
            if hud[i] == 0:
                hud[i] = 15
                break
    g.append(hud)
    return g

def predict(state, grid, action, x=None, y=None):
    st = {'world': dict(state['world']), 'offset': state['offset'], 'char': state['char']}
    ingest(st, grid)
    wr, wc, facing = st['char']
    info = {}
    if action == 3 and tile_open(st, wr, wc - 6):
        wc -= 6
        facing = 'L'
    elif action == 4 and tile_open(st, wr, wc + 6):
        wc += 6
        facing = 'R'
    elif action == 6 and x is not None:
        to = tile_origin(y + st['offset'], x)
        if to and tile_is_e(st, to[0], to[1]):
            pop_tile(st, to[0], to[1])
    # settle: balloon rise
    while tile_open(st, wr - 6, wc):
        wr -= 6
    st['char'] = (wr, wc, facing)
    st['offset'] = wr - ANCHOR_ROW
    g = render(st, grid, action)
    return g, info, st
