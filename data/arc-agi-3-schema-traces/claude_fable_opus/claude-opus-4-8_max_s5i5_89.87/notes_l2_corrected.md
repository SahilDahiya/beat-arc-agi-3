# LEVEL 2 — CORRECTED UNDERSTANDING (supersedes messy L2 section in notes.md)
# Derived from events.jsonl frame-diffs (L2 action_taken frames). Ground truth.

## EXACT ENTRY GEOMETRY (clean reset):
- a-bar: pointer 'd'(13) at (7,28); block 'a'(10) x7-8; handle '3' x6 y27-29. Grows RIGHT along y28.
- 7-bar: pointer 'd'(13) at (49,4); block '7' x48,50; handle '3' x48-50 y3. Grows DOWN along x49.
- LEFT diamond: arms (43,27)(42,28)(44,28)(43,29); CENTER (43,28) empty.
- RIGHT diamond: arms (49,27)(48,28)(50,28)(49,29); CENTER (49,28) empty.
- f-block (15): x45-47 y27-29 (3x3), BETWEEN the two diamonds. FIXED WALL.
- 8-bar (8): x27-29, y18-37, handle '3' y38 (anchored BOTTOM), grows UP. ALWAYS spans y27-29.
- top-bar (1): x27-50, y15-17. Rides on 8-bar top. Covers x49 (right-dia col) & x43 area.
- 1-vert (1): x36-38, y21-38. Adjacent-left of c-bar.
- c-bar (12): x39-55 (handle '3' x55, anchored RIGHT), y21-23. Grows LEFT / shrinks from left. ALWAYS covers x49.
- e-bar (14): x53-55, y24-26, handle '3' y26 (anchored bottom), grows UP.
- 9-bar (9): x30-31, y36-38, handle '3' x32 (anchored right), grows LEFT (pushes 8-bar).
- 6 control boxes: 8 L(10,48)R(16,48); a L(29,48)R(35,48); c L(48,48)R(54,48);
                   9 L(10,57)R(16,57); 7 L(29,57)R(35,57); e L(48,57)R(54,57).

## CONFIRMED BOX EFFECTS (from diffs):
- box-a R: grow a-bar right +3. BLOCKS vs 8-bar at x26 (a-bar can reach at most x26). box-a L: shrink.
- box-7 R: grow 7-bar down +3. BLOCKS vs top-bar (reaches ~y14 at entry). box-7 L: shrink.
- box-8 R: grow 8-bar UP +3, PUSHES top-bar up +3 (top-bar y15->12->9->6, STUCK y6-8: 7-bar handle y3-5 blocks).
- box-8 L: shrink 8-bar, top-bar FALLS. MIN: only 1 shrink works -> top-bar bottoms at y18-20 (8-bar top y21).
           Can't shrink more: top-bar can't fall into y21-23 (c-bar+1-vert there). top-bar NEVER reaches y28.
- box-c L: shrink c (left edge x39->x42->x45 MIN) AND PULLS 1-vert RIGHT +3 (x36-38->x39-41->x42-44 STUCK@f-block).
           c right end anchored x54-55 => c ALWAYS covers x49. 1-vert stuck x42-44 (f-block x45-47 blocks).
- box-c R: grow c left, push 1-vert left.
- box-e R: grow e up +3, PUSHES c-bar UP +3 (c y21->18->...). box-e L: shrink e, c falls back to y21-23 rest.
- box-9 R: grow 9-bar left, SHIFTS {8-bar, top-bar, 1-vert} ALL LEFT by 3 (top-bar x27-50->x24-47 => CLEARS x48-50!).

## KEY STRUCTURAL FACTS (proven, not hand-tracing):
- a-bar CANNOT reach left diamond (43,28): 8-bar anchored y37 always spans y28 at x27-29; can't clear or move right.
  => "dock a-pointer into left diamond" is IMPOSSIBLE.
- 1-vert FILLS left diamond center (43,28) with color '1' via 2x box-c L (arms stay 13, center becomes 1). CONFIRMED.
  => filling ONLY the left diamond did NOT win (frames f31-34). So need BOTH, or pointer-color fill.
- 7-bar always blocked on top-bar first (never reached c-bar). top-bar clearable from x49 via ONE box-9 R (shift left).
- c-bar always covers x49 (anchored right). If 7-bar BLOCKS vs c-bar -> right diamond unreachable by 7-bar.

## NEW GOAL HYPOTHESIS (dock-pointers is impossible for a-bar):
  Maybe WIN = fill BOTH diamond centers (left by 1-vert via shrink-c; right by 7-bar or top-bar), regardless of color.
  OR win needs pointer(13) in each center (then a-bar impossibility means I'm still missing a mechanic).

## DECISIVE UNTESTED CRUX (testing now):
  After box-9 R clears top-bar from x49, grow 7-bar DOWN (box-7 R xN). Does 7-bar PUSH the c-bar (y21-23) down,
  or BLOCK? If PUSH -> 7-bar can reach (49,28) -> right diamond fillable -> goal "fill both" viable.
  If BLOCK -> right diamond unreachable by 7-bar -> rethink goal.
  (Pushing c down: c right end x53-55 may hit e-bar y24-26 -> may cascade or block. Watch.)

## *** MAJOR: 7-BAR DOCKED RIGHT DIAMOND but level NOT won -> WIN NEEDS BOTH DIAMONDS ***
## Executed full plan: raised 1-vert over f-block, slid it to x51-53 via shrink-c, shifted top-bar off x49,
## grew 7-bar down x49 -> DOCKED (49,28)=13, arms intact. STATE STILL NOT_FINISHED. So WIN = BOTH diamonds
## docked with pointers (like L0's 2-pointer dock). LEFT diamond (43,28) still EMPTY.
## LEFT diamond must be docked by the a-bar (1-vert can't return: 7-bar now blocks x48-50). a-bar at (7,28)
## grows right along y28; blocked by 8-bar. But like the 7-bar, the 8-bar block MAY be clearable now:
## 1-vert & c moved AWAY (to x51-55), so region x27-47 is CLEAR -> the top-bar can finally FALL, so box-8 L
## can shrink the 8-bar fully (top y9->y35, bar to y35-37), dropping top-bar to ~y32-34 -> BOTH below y29 ->
## a-bar's path y27-29 CLEARS -> grow a-bar right to (43,28) to DOCK left diamond -> WIN (both docked).
## PLAN: box-8 L (10,48) xN shrink 8-bar until top>=y30 (top-bar falls below y29); verify a-rows y27-29 clear
## at x24-26; then box-a R (35,48) grow a-bar right to ptr(43,28)=dock. VERIFY top-bar doesn't land in y27-29.
## Test box-8 L first: does top-bar fall freely now (past old limit y18-20)? If yes, continue to full shrink.
## 7-bar dock is SAFE from box-8 L / box-a (different columns). Don't disturb x48-55.
##
## *** BREAKTHROUGH MECHANIC (confirmed via diffs) ***
## box-e R (54,57): grows e-bar UP +3, PUSHES c-bar UP +3, and RAISES the 1-vert +3 (1-vert attached to
##   c's left edge, rises with c). E.g. 1-vert y21-38 -> y18-35 -> (blocked). c y21-23 -> y18-20 -> (blocked).
## BLOCK: the rise stops when c/1-vert would hit the TOP-BAR (y15-17). So must RAISE TOP-BAR FIRST.
## box-e L (48,57) = reverse (lowers c + 1-vert). box-8 R raises top-bar (grows 8-bar up).
## => The 1-vert can be RAISED above y27-29, then it PASSES the f-block (f-block only at y27-29), then
##   box-c L slides it far right. This is the KEY to clearing c from x49.
##
## *** 7-BAR DOCK PLAN (to reach right diamond 49,28) ***
##  1) box-8 R (16,48) x3: raise top-bar y15-17 -> y6-8 (clears y9-14 above 1-vert).
##  2) box-e R (54,57) x3: raise 1-vert to ~y9-26 (bottom<=y26, clears f-block rows y27-29); c to ~y9-11.
##  3) box-c L (48,48) xN: slide 1-vert right PAST f-block to x48-50 (c-left -> x51, clears x49). 1-vert must
##     end at x48-50 (NOT x47-49) so it doesn't overlap f-block (x45-47) when lowered.
##  4) box-e L (48,57) xN: LOWER 1-vert below y28 (to y30+) so x49 clears in the 7-bar's path y5-27.
##     (WATCH: does 1-vert pass THROUGH the right diamond y27-29, or fill/stop at it? unknown - OBSERVE.)
##  5) box-9 R (16,57): shift top-bar left off x49 (if not already). 
##  6) box-7 R (35,57) xN: grow 7-bar down x49 to (49,28) = DOCK -> WIN? (test if docking is the goal)
##  UNCERTAIN: whether docking IS the goal (a-bar can't dock left, so maybe only 7-bar docks, or goal differs).
##  Each click ~1/commit (model mispredicts L2). Grind. If 1-vert fills right diamond instead of passing, that
##  may itself be a/the goal - observe for level_up. CURRENTLY: top-bar y15-17, 1-vert y18-35, c y18-20, e y21-25.
##
## PLAN(old): 1) box-9 R (16,57) shift left, clear top-bar from x49.
        2) box-7 R (35,57) repeatedly, watch 7-bar at c-bar (y21). Single clicks (counter/model mispredict grind).
        3) Based on result: build full L2 model + BFS(is_goal = both centers filled), or rethink.
