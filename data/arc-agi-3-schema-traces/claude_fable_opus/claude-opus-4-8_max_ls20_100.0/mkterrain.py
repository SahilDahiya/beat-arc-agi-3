"""Rebuild the L6 KNOWN TERRAIN from every frame recorded at level 6 and patch it into
world_model_v5.py between the FOG_TERRAIN markers.  FOG rule (confirmed EXACT):
  visible(x,y) iff (x-(x0+1.5))^2 + (y-(y0+1.5))^2 <= 400,  (x0,y0)=block top-left.
The always-visible UI (HUD art + budget bar) = the non-PANEL pixels of the ENTRY frame that lie
OUTSIDE the entry fog circle; those are NOT map and are never fogged.  Re-run after each move.
Verified: renders every recorded L6 frame with 0 diff."""
import json, re, sys
import numpy as np

LVL = int(sys.argv[1]) if len(sys.argv) > 1 else 6
R2 = 400


def blocktl(g):
    """Block top-left = a 5x5 whose top rows are colour-12 (head) over colour-9 (body). Excludes the
    HUD colour-12 art (which is not a 12-over-9 5x5)."""
    ys, xs = np.where(g == 12)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if y + 5 <= 64 and x + 5 <= 64:
            sub = g[y:y + 5, x:x + 5]
            if (sub[:2] == 12).all() and (sub[3:] == 9).all():
                return x, y
    return None


ev = [json.loads(l) for l in open('events.jsonl')]
acts = [e for e in ev if e.get('kind') == 'action_taken']
frames = [np.array(e['grid']) for e in acts if e.get('level') == LVL]
if not frames:
    print("no frames for level", LVL); sys.exit(1)
E0 = frames[0]
Y, X = np.mgrid[0:64, 0:64]

# UI = always-visible non-PANEL pixels outside the ENTRY fog circle (HUD art + bar)
bx0, by0 = blocktl(E0)
circ0 = ((X - (bx0 + 1.5)) ** 2 + (Y - (by0 + 1.5)) ** 2) <= R2
ui_mask = (E0 != 5) & ~circ0

# accumulate the MAP terrain (everything but UI), first-sighting-wins so consumed rings stay intact.
# EXCLUDE the block's own 5x5 footprint each frame: the block occludes what's under it, and its colours
# 9/12 are REUSED by the pinwheel arms — so flooring all 9/12 (old approach) would erase the pinwheel.
# A footprint cell is filled in by another frame where the block has moved away (revealing true floor).
ter = np.full((64, 64), -1, np.int16)
for g in frames:
    tl = blocktl(g)
    if tl is None:
        continue
    bx, by = tl
    excl = np.zeros((64, 64), bool)
    excl[by:by + 5, bx:bx + 5] = True                       # the block occludes its own 5x5
    # ALSO exclude the MOBILE PLUS: it lives on col cx=7 (px 54..58) and its colour-0 arms are unique
    # (setter is at px20-22, pinwheel-centre at px11) -> any colour-0 elsewhere is the plus. Mask a
    # generous box around each such colour-0 so its transient position is never recorded as terrain.
    py_, px_ = np.where((g == 0) | (g == 1))
    for yy, xx in zip(py_.tolist(), px_.tolist()):
        setter_pin = (19 <= xx <= 23 and 40 <= yy <= 44) or (9 <= xx <= 13 and 40 <= yy <= 44)
        launcher = xx <= 50   # all real launchers are at px<=44; the plus lives on col cx=7 (px54-58)
        if not setter_pin and not launcher:
            excl[max(0, yy - 3):yy + 4, max(0, xx - 3):xx + 4] = True
    vis = (((X - (bx + 1.5)) ** 2 + (Y - (by + 1.5)) ** 2) <= R2) & ~ui_mask & ~excl
    fresh = vis & (ter < 0)
    ter[fresh] = g[fresh]
seen = int((ter >= 0).sum())

out = E0.copy()                                # UI (HUD+bar) comes from the entry frame verbatim
mapreg = ~ui_mask
out[mapreg & (ter >= 0)] = ter[mapreg & (ter >= 0)]
out[mapreg & (ter < 0)] = 5                    # unknown map -> PANEL (also "not walkable")
out[by0:by0 + 5, bx0:bx0 + 5] = E0[by0:by0 + 5, bx0:bx0 + 5]   # redraw block at entry pos

lit = "FOG_TERRAIN = {%d: [\n" % LVL
for r in range(64):
    lit += '    "' + ''.join('%x' % v for v in out[r]) + '",\n'
lit += "]}\n"

src = open('world_model_v5.py').read()
new = re.sub(r"# <<FOG_TERRAIN>>.*?# <</FOG_TERRAIN>>",
             "# <<FOG_TERRAIN>>\n" + lit + "# <</FOG_TERRAIN>>", src, flags=re.S)
open('world_model_v5.py', 'w').write(new)
print(f"level {LVL}: {len(frames)} frames, {seen} map px known ({seen * 100 // (64 * 64)}% of grid)")
print("patched world_model_v5.py" if new != src else "!! markers not found - nothing patched")
