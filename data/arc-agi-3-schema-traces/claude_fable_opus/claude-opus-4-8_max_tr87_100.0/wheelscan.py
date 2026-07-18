"""Print the wheel enumeration at slot 0 for the current level."""
import numpy as np, sys
from an import frames
LV = int(sys.argv[1]) if len(sys.argv) > 1 else 2
Y, X = 52, 8   # answer-word glyph row / slot0 x  (level 2)
if len(sys.argv) > 3:
    Y, X = int(sys.argv[2]), int(sys.argv[3])

def g5(G, y, x):
    return tuple(tuple(1 if G[y+i][x+j] == 5 else 0 for j in range(5)) for i in range(5))
def rot(g, k):
    return tuple(map(tuple, np.rot90(np.array(g), k).tolist()))
def canon(g):
    return min(rot(g, k) for k in range(4))
def rw(g):
    return '/'.join(''.join('#' if v else '.' for v in r) for r in g)

acl = [tuple(map(tuple, x)) for x in np.load('acl.npy').tolist()]
seen = []
for t, l, G in frames():
    if l != LV:
        continue
    g = g5(G, Y, X)
    if g not in seen:
        seen.append(g)
print("wheel so far (%d letters), slot0 orientation:" % len(seen))
for i, g in enumerate(seen):
    c = [j for j in range(len(acl)) if acl[j] == canon(g)]
    print("  pos%d class=%s  %s" % (i, c[0] if c else 'NEW', rw(g)))
print()
print("WHEELS[10] = [")
for g in seen:
    print("    " + repr(g) + ",")
print("]")
