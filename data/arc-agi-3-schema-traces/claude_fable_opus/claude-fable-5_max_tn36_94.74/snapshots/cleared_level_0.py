# World model — "program & run" game.
# CONFIRMED level-0 mechanics (transitions 0-4):
# - Icon strip below board: N icons. Each icon = CAP (3-wide, row cap_y; color 5 or 1, TOGGLEABLE
#   by clicking anywhere in the icon's box; costs 1 time) + STEM (1-wide, rows cap_y+2..+4, FIXED so far).
# - Button (color-9 circle): click = RUN program. For each icon i (left to right): if cap==5 (gray),
#   EXECUTE move given by stem color: stem 5 => key moves DOWN one band (4px); stem 1 => key moves LEFT
#   one tile (4px). cap==1 (blue) => skip.
#   If key's final tile == lock interior top tile -> level_up. Else FAIL: board resets, time-1.
# - Time bar: row 1 color-9 cells; each icon click AND each failed run turns rightmost 9 -> 3.
# - Clicks elsewhere: assumed no-op & free (partially tested).
# OPEN: how to change stems (needed: 5 downs, stems only have 2) — or the goal is different.

def _features():
    e = ENTRY_GRID
    H = len(e); W = len(e[0])
    strip_rows = [yy for yy in range(30, H) if sum(1 for xx in range(W) if e[yy][xx] == 0) >= 20]
    y0, y1 = min(strip_rows), max(strip_rows)
    best_y, best_runs = None, []
    for yy in range(y0, y1 + 1):
        runs = []
        xx = 1
        while xx < W:
            v = e[yy][xx]
            if v != 0 and e[yy][xx - 1] == 0:
                j = xx
                while j < W and e[yy][j] == v:
                    j += 1
                if j < W and e[yy][j] == 0 and (j - xx) == 3:
                    runs.append((xx, j - 1))
                xx = j
            else:
                xx += 1
        if len(runs) > len(best_runs):
            best_runs, best_y = runs, yy
    icons = best_runs
    cap_y = best_y
    # stem colors (entry): center column of each cap, 2 rows below cap row
    stems = [e[cap_y + 2][x0 + 1] for (x0, x1) in icons]
    # button: bbox of color-9 cells below the strip
    pts = [(xx, yy) for yy in range(y1, H) for xx in range(W) if e[yy][xx] == 9]
    bx0 = min(p[0] for p in pts); bx1 = max(p[0] for p in pts)
    by0 = min(p[1] for p in pts); by1 = max(p[1] for p in pts)
    # key & lock from color-11 cells (tiles: origin x14,y9, pitch 4)
    bs = [(xx, yy) for yy in range(H) for xx in range(W) if e[yy][xx] == 11]
    cnt = {}
    for (xx, yy) in bs:
        t = ((xx - 14) // 4, (yy - 9) // 4)
        cnt[t] = cnt.get(t, 0) + 1
    key_tile = max(cnt, key=lambda k: cnt[k])
    # lock: cells not in key tile; interior col = between wall cols; target band = wall top band
    lock_cells = [(xx, yy) for (xx, yy) in bs
                  if ((xx - 14) // 4, (yy - 9) // 4) != key_tile]
    lx0 = min(xx for xx, yy in lock_cells)  # left wall x
    ly0 = min(yy for xx, yy in lock_cells)  # wall top y
    lock_target = ((lx0 + 1 - 14) // 4, (ly0 - 9) // 4)
    return {
        'strip_y0': y0, 'strip_y1': y1, 'cap_y': cap_y, 'icons': icons, 'stems': stems,
        'button': (bx0, by0, bx1, by1), 'key_start': key_tile, 'lock_target': lock_target,
    }


def _spend(g):
    row = g[1]
    for xx in range(len(row) - 1, -1, -1):
        if row[xx] == 9:
            row[xx] = 3
            return


def step(grid, action, x=None, y=None):
    info = {"level_up": False, "dead": False, "win": False}
    g = [r[:] for r in grid]
    if action != 6 or x is None:
        return g, info
    F = _features()
    # icon click? -> upper zone (y<=cap_y+2) toggles CAP; lower zone (y>=cap_y+3) toggles STEM.
    # (observed: y41,y43 -> cap; y45 -> stem; y44 boundary GUESSED as stem)
    if F['strip_y0'] <= y <= F['strip_y1']:
        for (x0, x1) in F['icons']:
            if x0 - 1 <= x <= x1 + 1:
                if y >= F['cap_y'] + 3:
                    sy = F['cap_y'] + 2
                    xc = x0 + 1
                    cur = g[sy][xc]
                    newc = 1 if cur == 5 else 5
                    for yy in range(sy, sy + 3):
                        g[yy][xc] = newc
                else:
                    cur = g[F['cap_y']][x0]
                    newc = 1 if cur == 5 else 5
                    for xx in range(x0, x1 + 1):
                        g[F['cap_y']][xx] = newc
                _spend(g)
                return g, info
    # button click? -> run program
    bx0, by0, bx1, by1 = F['button']
    if bx0 <= x <= bx1 and by0 <= y <= by1:
        caps = [g[F['cap_y']][x0] for (x0, x1) in F['icons']]
        stems = [g[F['cap_y'] + 2][x0 + 1] for (x0, x1) in F['icons']]
        tx, ty = F['key_start']
        for i, c in enumerate(caps):
            if c == 5:
                if stems[i] == 5:
                    ty += 1
                else:
                    tx -= 1
        if (tx, ty) == F['lock_target']:
            info['level_up'] = True
            return g, info
        _spend(g)
        return g, info
    # elsewhere: inert click, still costs 1 time (confirmed t7: key click)
    _spend(g)
    return g, info
