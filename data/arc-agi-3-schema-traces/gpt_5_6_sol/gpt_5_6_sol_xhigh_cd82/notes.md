# Notes — ARC3 stencil-paint game

## Mechanics
- Goal preview `ENTRY_GRID[3:13,3:13]`; paint 10x10 target.
- Ring: N→NW→W→SW→S = 3,2,2,4; N→NE→E→SE = 4,2,2. Reverse SE→S→SW→W→NW→N = 3,3,1,1,4; S→SE=4.
- ACTION5 masks are cardinal halves / inclusive diagonal halves; later stamps overwrite.
- Palette centers x23=0,29=f,35=c,41=b,47=e,53=8,59=9.
- Auxiliary literal positions: N target x3..6,y0..2; W x0..2,y3..6; E x7..9,y3..6; S x3..6,y7..9. It is hidden diagonally; click visible colored fill.
- Cost credit rule: a consuming main/aux stamp prepays the immediately following normally-consuming action (palette or movement); an intervening free action loses it. A paid palette prepays an immediate flat stamp. Other transition costs encoded.

## Cleared
L0 white S. L1 white N+c SE. L2 e SE+8 W+white NW+c aux N.
L3 c E+white SE+9 W+b aux W.
L4 9 N+8 aux N+e SW+c SE.

## Level 5 final
Goal decomposes:
- main: e E half, 0 W half, then 8 NW (leaves strict SE triangle split 0/e)
- auxiliaries after main: f N rectangle and b W rectangle.
Plan:
1 select e; N→E (4,2); stamp e.
2 E→SE→S→SW→W (2,3,3,1); select0; W stamp.
3 W→NW (1); select8; NW stamp.
4 NW→W (2); select b; W auxiliary click (~13,39).
5 W→NW→N (1,4); select f; N auxiliary click (31,21) => WIN.
Current L5: main complete (8 NW over black/e base), selected8 at NW. Next 2→W, select b, click W aux (~13,39); then 1,4→N, select f, click N aux (31,21) to win.
