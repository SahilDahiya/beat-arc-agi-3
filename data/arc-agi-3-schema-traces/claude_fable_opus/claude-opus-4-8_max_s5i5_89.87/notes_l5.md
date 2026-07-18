# LEVEL 5 (5/8). Levels 0-4 CLEARED.
## Dispatch: L5 entry has NO color1, HAS color15(f) => _is_l4=False, _is_l3=False => falls to _step_012 (WRONG). Build L5 branch.
## ENTRY STRUCTURE (from parse):
- POINTER: single d at (13,49), inside the '9' structure. 9-struct: color9 x48-50 rows10-14, '333' cap row9.
- TOP BARS: 'b' bar color11 x40-47 rows9-11 (handle 3 x39); 'e' bar color14 x39-41 rows12-16 (handle 3 row17); 9-struct x48-50.
- DIAMOND (target, hollow): ring d (33,52),(34,51),(34,53),(35,52), center (34,52) EMPTY. Pointer must dock here.
- WALLS f(15): top horiz rows27-29 x17-58 (+x3-8 block); GAP x9-16 rows27-29. left vert x3-5 rows27-41; right vert x56-58 rows30-41;
  bottom-right block rows39-41 x45-58. Arena = rows30-41 between walls; diamond(34,52) in arena.
- CONTROLS (6 boxes):
  TOP ROW (rows45-51, 7x7, PLUS-shaped = 4-direction up/down/left/right):
    boxA '9' frame x9-15 center(48,12): up(47,12) down(49,12) left(48,11) right(48,13)
    boxB 'b' frame x28-34 center(48,31): up(47,31) down(49,31) left(48,30) right(48,32)
    boxC 'e' frame x47-53 center(48,50): up(47,50) down(49,50) left(48,49) right(48,51)
  BOTTOM ROW (rows54-60, 13w, DOUBLE = +/- grow/shrink, like L4):
    boxD '9' frame x6-18: shrink(8,57) grow(16,57) [left/right '999' groups x8-10/x14-16, div x12]
    boxE 'b' frame x24-36: shrink(26,57) grow(34,57)
    boxF 'e' frame x42-54: shrink(44,57) grow(52,57)
## HYPOTHESIS: top plus-controls MOVE a bar in 4 dirs; bottom +/- controls GROW/SHRINK. Pointer in 9-struct => 9-controls move it.
##  Goal: pointer(13,49) -> diamond(34,52): down ~21 rows, right ~3 cols. Must pass top wall (gap x9-16) OR through arena.
## !!! COORD CONVENTION: commit uses x=COL, y=ROW. My box coords above are (row,col) => SWAP for commit: boxA-down (row49,col12)=>{x:12,y:49}.
## FIRST TEST {x:49,y:12}=(col49,row12) was WRONG (clicked the 9-struct near pointer, not boxA) => no-op. Retesting with correct swap.
## Correct control click coords {x,y}: boxA-9: down{12,49} up{12,47} left{11,48} right{13,48} '4'arms down{12,50} up{12,46} L{10,48} R{14,48}
##   boxB-b: center col31 row48 => down{31,49} up{31,47} L{30,48} R{32,48}.  boxC-e: center col50 row48 => down{50,49} up{50,47} L{49,48} R{51,48}
##   boxD-9(bottom +/-): grow{16,57} shrink{8,57}.  boxE-b: grow{34,57} shrink{26,57}.  boxF-e: grow{52,57} shrink{44,57}
## *** MECHANIC (partial): top plus-control ROTATES the bar (not translate)! boxA-9-down {12,49} rotated the 9-bar 90deg CCW:
##  BEFORE vertical 3wide(col48-50)x5tall(row10-14), handle '3' TOP(row9), pointer d(13,49) [points DOWN].
##  AFTER horizontal 5wide(col49-53)x3tall(row9-11), handle '3' LEFT(col48), pointer d(10,52) [points RIGHT]. (CCW: top->left, pointer bottom->right)
##  counter row63 0->1 (increments per action). Bar = 3-thick x 5-long, rotates around center; pointer at tip opposite handle.
## *** 9-BAR = ROTATING ARM. Root/pivot FIXED at (10,49). 3-wide x 5-long. Points in dir D (down/right/up/left). ***
##  Cells: for dist 0..4 along D from root, perp{-1,0,+1} => '9'; pointer 'd' at dist 3 center; handle '3' at dist -1 (behind root).
##  Entry D=down: body rows10-14 cols48-50, ptr(13,49), handle row9. boxA-9-down {12,49} rotates D by 90deg: down->right->up->left->down.
##   D=right: cols49-53 rows9-11 ptr(10,52) handle col48. D=up: rows6-10 cols48-50 ptr(7,49) handle row11. (verified 3 states, root always (10,49))
## PROBLEM: fixed pivot (10,49) + length 5 => pointer only reaches radius-3 circle around (10,49). CANNOT reach diamond(34,52).
##  => need EXTENSION (bottom +/- box) and/or the pivot MOVES (maybe 9-bar is the end of a CHAIN: e-bar->b-bar->9-bar robot arm).
##  b-bar: cols40-47 rows9-11 (horiz), handle col39. e-bar: cols39-41 rows12-16 (vert), handle row17. 9-root(10,49) is at b-bar's right end.
##  => LIKELY 3-joint arm: e(base row17) -> b -> 9(tip w/ pointer). Rotating/extending e,b moves the 9-pivot.
## *** CONFIRMED boxD-9-grow {16,57} EXTENDS the 9-arm +3 length (5->8). handle fixed (dist-1), body+ptr extend along dir D, ptr stays at tip-1.
##  So 9-arm has 2 controls: boxA(top plus)=ROTATE 90deg/click; boxD(bottom +/-)=grow/shrink length +/-3. Root/pivot fixed (10,49).
##  State now: D=up, length8, body rows3-10 cols48-50, ptr(4,49), handle row11. counter row63=2.
## Fixed pivot => 9-arm alone can't reach diamond(34,52) (would hit top wall at col49 row27). => MUST move pivot via chain.
## *** CHAIN CONFIRMED: e->b->9 ARTICULATED ROBOT ARM. boxB-b-down rotated b (right->up around pivot (10,40)) AND swung the 9-bar rigidly (up->left) around (10,40). ***
##  RULE: box-X-down rotates bar X 90deg (cycle down->right->up->left->down); ALL child bars (+pointer) rotate RIGIDLY with X around X's pivot.
##  Each bar = 3-thick, length L, rooted at parent's tip (+handle offset), points in dir; pointer = 9-bar tip-1. Extension (bottom box) grows L by 3.
## CURRENT ARM (after b-rotate): e(root~(16,40) up len5 body r12-16, handle r17) -> b(root~(10,40) up len8 body r3-10, handle r11)
##   -> 9(root~(3,40) LEFT len8 body r0-2 cols33-40, handle col41, ptr(1,34)). Base pivot P_e near (16,40) FIXED.
## b-pivot=(10,40) (its root=e's tip, fixed unless e rotates). Offsets ~2 cells (handle+gap) between a bar's tip and child's root - derive exactly.
## TESTING boxC-e-down {50,49}: rotate the BASE 'e' => whole arm (e+b+9+ptr) swings around P_e. Reveals P_e and the chain transform. Goal: swing arm DOWN into arena, extend to diamond(34,52).
## *** MODEL ENCODED & BACKTEST-CLEAN (all L5 grids match). Fwd-kinematics: PE=(16,40); Pb=Pe+(Le+1)*de; P9=Pb+(Lb+1)*db; ptr=P9+(L9-2)*d9.
##  rot(down-click)=(r,c)->(-c,r) [down->right->up->left]; grow +3 len; counter=L4 formula 3*(na//7)+[0,0,1,1,2,2,3][na%7]. init e(up,5)/b(right,8)/9(down,5).
## *** BFS PROBLEM: with rotate+extend + walls-block, ptr CANNOT reach diamond(34,52). Full BFS 14821 states, closest (25,52) dist9. ptr reaches arena (332 states) but not (34,52).
##  => MISSING MECHANIC. Hypotheses: (A) walls DON'T block the arm (untested - arm never touched a wall yet). (B) plus up/left/right arms do MORE than rotate (translate the pivot? rotate other way?). Only 'down' arm tested=rotate.
## TESTING (A): grow-9 x3 to extend the down-pointing 9-arm into the top wall (rows27-29 at col25). Model says blocked (stops L9=11); if reality passes => walls DON'T block => remove wall constraint, re-BFS.
## RESOLVED: (A) walls DO block (grow-9 stopped at L9=11 at wall row27, matched model). NO missing mechanic!
## *** GOAL REACHABLE with LONGER bars (my BFS cap 26 was too low). At CAP=40 the goal state = e(left,23),b(down,17),9(right,38), ptr=(34,52). ***
##  The 9-arm just needs to be very long (38) pointing right across the arena. Added length cap 41 to _l5_valid to focus BFS. Re-run run_bfs.
## Reachable arena ptr cells (row>=27,col>=40) form a grid at 3-spacing: (31,40),(34,52),(37,49)... => ptr moves in 3-cell steps.
## *** SOLUTION PATH (19 clicks) from state e(left,5)/b(left,8)/9(down,11): bgrow(34,57)x2, egrow(52,57)x6, brot(31,49),
##  9grow(16,57)x9, bgrow(34,57) => e(left,23)/b(down,17)/9(right,38), ptr=(34,52)=WIN. Verified valid each step in Python.
##  RISK: b-grow(34,57) & e-grow(52,57) coords are GUESSES (only 9-grow (16,57) confirmed). If wrong => plan stops at first mispredict, fix coord.
##  Also untested: self-intersection (model doesn't check bars overlapping each other) & long-bar behavior. If reality blocks, learn & re-plan.
## GOAL PATH: pointer must reach diamond(34,52) in arena (below top wall rows27-29). Top wall gap only at cols9-16 (far left).
##  So pointer at col52 is blocked from going down by top wall => must route bar LEFT to the gap, down through it, then to (34,52). MAZE.
## counter row63: increments per action (like L4). Formula TBD.
