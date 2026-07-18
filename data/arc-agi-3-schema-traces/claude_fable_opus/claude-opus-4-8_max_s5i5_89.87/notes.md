# Notes — ARC-AGI-3 game s5i5. Click-only puzzle (ACTION6). 8 levels. LEVEL 0 & 1 CLEARED. Now LEVEL 2.

## CORE GAME PATTERN (both levels): control boxes (color-2 border, interior shapes of a color, split by a
##  '3' divider) let you grow/shrink a same-colored BAR by +-3 (grow away from its '3' handle). Each bar has
##  a single 13 'pointer'. GOAL = dock every pointer into its matching DIAMOND (a 4-cell plus of 13, or of
##  another color). Docking all pointers = WIN. Counter (bottom row color-4 fill) is ADVERSARIAL & COSMETIC —
##  never model it (leave row 63 unchanged; grind multi-commits through its stops).
## L1 added: bars form a CHAIN and PUSH each other; 'f'(15) frame = WALLS that block bar movement.

## LEVEL 0 — SOLVED. Mechanic (may recur):
- 2 "template bars" (block-color rectangle + single 13 'pointer', attached to a '3' handle).
  value = pointer distance from anchored (handle) edge. Bar grows AWAY from handle.
- Control boxes (2-border, interior shapes of the bar color, split by a '3' divider). Vertical
  divider: click LEFT half = value-3, RIGHT = +3. Horizontal divider: TOP=-3, BOT=+3. clamp>=0.
- DOCK each bar's pointer into its aligned diamond CENTER (pointer reaches diamond center coord).
  Diamond arms (4 cells of 13) are PRESERVED on dock; pointer sits in center. BOTH docked => WIN.
- COUNTER (bottom row color-4 fill): UNSOLVED, cosmetic, irrelevant to win. Don't waste effort;
  commit 1 click at a time near goals if it mispredicts.
- world_model_v5.py auto-detects templates (13 adj to block color) + control boxes from ENTRY_GRID.

## LEVEL 1 — CURRENT (level 1/8). Layout (ENTRY):
- 4 CONTROL BOXES (y54-60), same style as L0 (vertical '3' divider => LEFT=-, RIGHT=+):
    box-c(12): x3-15   box-a(10): x18-30   box-b(11): x33-45   box-e(14): x48-60
    (box-e right subcell center ~ (57,57); left ~ (51,57).)
- SMALL STRUCTURE x9-17 y36-41: 2x2 of 4 color patches with ONE 'd'(13) pointer on the 'e' patch:
    b(11) block x13-14 y36-38;  e(14) block x15-17 y37-38 w/ 'd' at (16,37);
    c(12) block x10-11 y39-41;  a(10) block x12-14 y39-40.  '3' dividers around.
- BIG 'f'(15) frame: top bar x33-56 y9-11; left vert x33-35 y9-26; middle vert x42-44 y15-44.
- 1 DIAMOND (13) at x51-53 y30-32 (center 52,31).
- NO 'f' pointer. Only pointer is the 'd' on the 'e' patch.

## LEVEL 1 observations
- T: click box-e RIGHT (57,57) → 'e' bar grew DOWN: patch x15-17 y37-38 (val0, ptr(16,37)) →
  y37-41 (val3, ptr(16,40)). Standard L0 bar: anchored top y37, grows down, ptr=y37+val, len=val+2.
  COUNTER stayed 0 (level 1 counter differs from L0 — maybe off/irrelevant). Only 'e' has a pointer.
- e-bar grows DOWN at x16; diamond at (52,31) is far up-right → e-bar does NOT dock into diamond directly.
  So goal != simply dock e-bar. Need to understand other 3 bars + 'f' frame + diamond role.

## LEVEL 1 — PUSH mechanic (key!)
- T: box-b RIGHT (42,57) → 'b' bar grew RIGHT +3 (x13-14 → x13-17), PUSHING the 'e' bar (+its
  pointer + its '3' divider) right by 3: e-bar x15-17 → x18-20, pointer (16,40)→(19,40). Bars are
  BLOCKS in a shared channel; growing one pushes adjacent ones. Counter +1 on this push (was 0 on box-e).
- Bar growth dirs so far: 'e'(14) grows DOWN (anchored top y37). 'b'(11) grows RIGHT (anchored left x13).
- To move POINTER (on e-bar): RIGHT = grow 'b' (pushes e right). DOWN = grow 'e'. LEFT/UP = TBD
  (maybe shrink b / shrink e, or grow bars on other sides). Probing box-a, box-c next.
- Pointer now (19,40). Diamond (52,31). 'f' frame (x33-56) likely a WALL/maze between them.
  GOAL still unconfirmed — probably push pointer to dock in diamond (like L0), navigating around 'f'.

## LEVEL 1 — 4 boxes = 4 pointer moves (via bar-push):
- box-b RIGHT → pointer RIGHT +3.  box-a UP → pointer UP +3 (shifts whole e-bar up).
- box-e RIGHT → pointer DOWN +3 (grows e-bar down; top-anchor stays). box-c RIGHT → pointer RIGHT +3
  (like box-b; grows 'c' right, cascades push). So RIGHT-subcells give: b/c=RIGHT, a=UP, e=DOWN. No LEFT/down-shift.
- box-a LEFT (21,57) → pointer DOWN +3 (shifts e-bar down, shrinks 'a'; LIMITED by a-length).
- POINTER MOVES AS A POINT (±3 per click), position = f(net clicks):
    ptr_x = 16 + 3*(nB + nC)      [box-b/c RIGHT = +x; LEFT = -x, limited by bar len]
    ptr_y = 37 + 3*nE - 3*nA      [box-e RIGHT/box-a LEFT = +y down; box-a RIGHT/box-e LEFT = -y up]
    Unlimited: RIGHT(b/c right), UP(a right), DOWN(e right). Limited: LEFT, and down-via-a.
  Click coords: bRIGHT(42,57) bLEFT(36,57) cRIGHT(12,57) cLEFT(6,57) aRIGHT(27,57) aLEFT(21,57)
                eRIGHT(57,57) eLEFT(51,57).
- CRITICAL UNTESTED: do 'f' walls BLOCK the pointer/e-bar? e-bar has extent (grows). If extent blocks,
  crossing the mid vert (x42-44 y15-44) may be impossible (e-bar top stuck ~y37, can't get below y44).
  Diamond (52,31) is across that wall → if blocked, goal may NOT be the diamond. TESTING: march pointer
  RIGHT (box-c) from (22,40) toward x42 wall; watch if it stops (~x39-41) or passes.
- COUNTER incremented on box-b/c RIGHT (horizontal) but NOT box-e/box-a — odd, still irrelevant.
- WALL analysis: f-frame = TOP bar (x33-56,y9-11) + LEFT vert (x33-35,y9-26) + MID vert (x42-44,y15-44).
  Diamond (52,31) is RIGHT of the MID vert. Pointer/e-bar must CROSS the mid vert (y15-44) to reach it.
  - Over-top blocked (top bar y9-11 + left vert). Under-bottom (y45+) is OPEN past the mid vert.
  - PROBLEM: e-bar top-anchor is stuck (~y34); box-e only lengthens down, box-a shifts up. Need a DOWN
    shift (move whole bar down) to get e-bar entirely below y44 to cross under. box-c may provide it.
- GOAL hypothesis: navigate pointer to diamond center (52,31) & dock (L0-style). Path likely goes under wall.
- CONCERN: bars have physical extent; pushing blocked by walls. Full model = sliding-block puzzle (hard).

## LEVEL 2 layout (ENTRY):
- 6 CONTROL BOXES (color-2, vertical '3' divider -> LEFT subcell=shrink, RIGHT=grow):
    top row y45-51: box-8 x7-19, box-a(10) x26-38, box-c(12) x45-57
    bot row y54-60: box-9 x7-19, box-7 x26-38, box-e(14) x45-57
    subcell centers: 8 L(10,48)R(16,48); a L(29,48)R(35,48); c L(48,48)R(54,48);
                     9 L(10,57)R(16,57); 7 L(29,57)R(35,57); e L(48,57)R(54,57).
- 2 POINTERS: a-bar pointer (7,28) [a-block x6-8 y27-29, '3' handle left x6, grows RIGHT];
              7-bar pointer (49,4) [7-block x48-50 y3-5, '3' handle top y3, grows DOWN].
- 2 DIAMONDS (plus of 13): LEFT center (43,28); RIGHT center (49,28); f-block (15) between them x45-47.
- COLOR-1 (blue) = likely WALLS (no box). Big 1-structure: top bar x27-49 y15-17; vert x36-38 y21-38.
- Other bars (obstacles/chain?): 8 (x27-29 y18-38, vert, '3' handle bottom y38, has '99' at x30-31 y36-38),
     c (x39-54 y21-23, horiz), e (x53-55 y24-26, vert, '3' handle bottom y26), 9 (x30-31 y36-38).
- GOAL hypothesis: dock a-pointer -> a diamond (grow a right along y28 to x43?), 7-pointer -> other diamond
     (grow 7 down along x49 to y28?). Obstacles: 8-bar, c-bar, 1-walls in the paths. Manipulate bars to clear.
- T: box-a RIGHT (35,48) → a-bar grew RIGHT +3 (pointer (7,28)→(10,28)), NO push, NO counter change.
  => L2 bars are INDEPENDENT (L0-style grow/shrink), NOT chain-push. Likely walls block growth.
- PUZZLE: a-bar (y27-29) grows right but 1-vert wall (x36-38, y21-38) blocks at x36; left diamond at x43 is
  PAST the wall. So a-bar can't reach it by straight growth?? Need to understand walls / how paths clear.
  Maybe central bars (8,c,e,9) are movable obstacles; maybe 1 is a movable structure after all; TBD.
- T: box-7 RIGHT (35,57) → 7-bar grew DOWN +3 (pointer (49,4)→(49,7)), independent. Counter +1 this time
  (a-probe was +0; counter still adversarial, ignore).
- Both a-bar & 7-bar grow toward diamonds but color-1 walls block: 1-top-bar (x27-49 y15-17) blocks 7-bar@x49;
  1-vert (x36-38 y21-38) blocks a-bar@y28. If 1 is a fixed wall, pointers can't reach diamonds -> misunderstanding.
- TEST: is color-1 MOVABLE? 8-bar (x27-29, top y18) sits right under the 1-top-bar (y15-17). Probe box-8 RIGHT
  (16,48) = grow 8-bar UP; if the 1-top-bar moves up -> central structure is a CHAIN (1 movable). If blocked -> wall.
- NOTE gap: at x36-38, y18-20 is OPEN (between 1-top-bar y15-17 and 1-vert y21-38).
- T: box-8 RIGHT (16,48) → 8-bar grew UP +3 AND PUSHED the 1-top-bar UP +3 (y15-17→y12-14). So COLOR-1
  IS MOVABLE and L2 = CHAIN-PUSH (like L1)! 8-bar(x27-29,grows up) pushes 1-top-bar(x27-50,horizontal).
  The 1-vert (x36-38 y21-38) & c-bar did NOT move (separate from top-bar in this push).
- So L2 is a big CHAIN-PUSH MAZE. Bars: a,7 (pointers), 8,c,e,9 (movable), plus movable 1-blocks. Walls?
  Need to map full chain: which bar pushes which. Then clear paths so a-ptr->left-diamond(43,28),
  7-ptr->right-diamond(49,28). This is L1-scale-up; will need a full L2 model + BFS. LONG level.
- T: box-c LEFT (48,48) → c shrank left-edge x39->x42 AND PULLED the 1-vert right +3 (x36-38->x39-41).
  So chain link: c-left-edge ADJACENT to 1-vert-right; shrink c pulls 1-vert right, grow c pushes 1-vert left.
  Diamonds (left ctr43,28 / right ctr49,28) did NOT move. 8-bar & top-bar unchanged by c-move.
## L2 CHAIN MAP so far:
  - 8-bar (x27-29 vert, anchored bottom y38, grows UP) --pushes--> 1-top-bar (x27-50 horiz) UP. (shrink 8 pulls it down?)
  - c-bar (x42-54 now, horiz, anchored right x55, grows LEFT) <--adjacent--> 1-vert (x39-41 now, vert y21-38).
  - a-bar (x6-11 now, horiz, grows right, PTR (10,28)) toward LEFT diamond (43,28). blocked by 8-bar(x27-29)+1-vert.
  - 7-bar (x48-50 vert, grows down, PTR (49,7)) toward RIGHT diamond (49,28). blocked by 1-top-bar(x27-50 covers x48-50)+c-bar.
  - e-bar (x53-55 vert, anchored bottom y26, grows up) - chain link TBD. 9-bar (x30-31, near 8) - TBD.
  - 1-top-bar is x27-50 (covers x48-50) -> blocks 7-bar horizontally; must move it vertically OUT of y5-28
    (grow 8 pushes up / shrink 8 pulls down) so x48-50 clears. c-bar also covers x48-50 -> shrink c to clear.
- BIG chain-push maze. NEXT: probe box-e RIGHT (54,57)=grow e up, box-9 to finish map. Then build L2 model + BFS.
- T: box-e RIGHT (54,57) → e grew UP +3 (y24-26->y21-26) and PUSHED c-bar UP +3 (c y21-23->y18-20);
  c moving up also shifted the 1-vert (lost bottom rows). So chain: e --pushes--> c (vertical, e at x53-55 overlaps c right end).
## L2 chain (messy after probes): 8→top-bar(up); e→c(up); c↔1-vert(horiz). Interlocked. My probes moved things around.
## STRATEGY (context is long): this is a hard interlocking chain-push maze. Consider RESET to clean entry, then
   build a full L2 chain-push MODEL (calibrate render+push rules from probes on clean state) + BFS is_goal
   (both pointers at diamond centers 43,28 & 49,28). Then commit the solution (grinding counter stops).
- T: box-9 RIGHT (16,57) → 9-bar grew right AND pushed 8-bar + 1-top-bar LEFT +3. Another chain link (9↔8).
## L2 chain links found: 8→top-bar(vert push); e→c(vert push); c↔1-vert(horiz); 9↔8(horiz). Multi-directional, complex.
## DECISION: RESET (undo messy probes) -> clean entry. Then TEST the SIMPLE hypothesis first:
   maybe just GROW the a-bar right (it will CHAIN-PUSH the 8-bar/1-vert out of the way as it advances) until
   pointer reaches left diamond (43,28); likewise grow 7-bar DOWN (pushing top-bar/c) to right diamond (49,28).
   Grow a-bar via box-a RIGHT (35,48); grow 7-bar via box-7 RIGHT (35,57). Grind single clicks (counter stops).
   Watch: does the pointer advance and push obstacles, or block at a wall/diamond? If chain-push clears the path,
   the solution is just: grow a-bar until ptr=(43,28) AND grow 7-bar until ptr=(49,28). If it blocks, build full model+BFS.
## CONFIRMED: a-bar BLOCKS against the 8-bar (does NOT push it; a-bar stuck at value 18, right edge x26).
   So DIRECT-GROWTH FAILS. Must CLEAR obstacles first: to advance a-ptr past x26, shrink/move the 8-bar
   (x27-29 y18-38, anchored bottom y38, grows up) OUT of rows y27-29. Then 1-vert (x36-38) blocks next.
   This is a SEQUENTIAL CLEAR-THE-MAZE puzzle → needs a FULL L2 chain-push model + BFS (big build).
   Order to clear a-path (y27-29): 8-bar(shrink top below y30), then 1-vert(move right via c) past x43.
   7-path (x48-50): 1-top-bar (x27-49 covers x48-49; move it vertically out of y5-28 via 8-bar grow/shrink),
   c-bar (x39-54 covers x48-50; shrink via box-c) — but shrinking c pulls 1-vert right (side effect).
   T: box-8 LEFT → 8-bar shrank top y18->y21 AND 1-top-bar FELL DOWN with it (y15-17->y18-20). They're chained
   (top-bar rides on 8-bar's top). 8-bar still covers a-rows y27-29. To clear y27-29 need 8-bar top BELOW y30
   AND the trailing top-bar also below y29 -> shrink 8-bar to y33-38 (top-bar falls to y30-32) => y27-29 clear.
   From current 8-bar top y21, shrink ~4 more (top y21->y33). Then grow a-bar past x29 to x35 (1-vert x36 blocks next).
   a-bar value 18 (ptr (25,28)); 7-bar value 0 (ptr (49,4)).
   ## STATE ASSESSMENT: L2 is a very hard multi-step chain-push maze; interdependent (c moves 1-vert & 7-path;
   ## 8 moves top-bar). Full model+BFS is the robust path but a big build. Hand-solve = grind (counter stops).
   ## Have used heavy context. Keep documenting; make incremental clearing progress.
   ## box-8 LEFT INCONSISTENT: over 4 clicks, only 1 actually shrank 8-bar (y18->y21, top-bar fell y15-17->y18-20);
   ## others were counter-only or full no-ops. Chain interactions are subtle/hard to predict. 8-bar now y21-37, top-bar y18-20.
   ## L2 REMAINING WORK (large): clear 8-bar+top-bar off y27-29 (shrink 8-bar so top>y29 AND top-bar<y27 => 8-bar ~y33-37),
   ## grow a-bar past x29, clear 1-vert(x36-38) via box-c moving it right past x43, grow a-bar to ptr=(43,28).
   ## Then 7-bar path: clear 1-top-bar & c-bar off x48-50, grow 7-bar down to ptr=(49,28). Both docked = win.
   ## RECOMMENDATION for future: build a full L2 chain-push model (calibrate each box's push/pull from probes) + BFS;
   ## OR hand-solve grinding single clicks. Very hard level. Levels 0,1 already cleared (2/8).
   ## KEY INTERDEPENDENCY: box-8 LEFT is now a NO-OP — 8-bar can't shrink because the chained 1-top-bar (x27-49,
   ## at y18-20) can't FALL into y21-23 (blocked there by c-bar x39-54 y21-23 and 1-vert x36-38 y21-23). So must
   ## FIRST clear y21-23 (shrink c-bar via box-c LEFT (48,48) — pulls 1-vert right; and/or move 1-vert), THEN the
   ## top-bar can fall, THEN 8-bar can shrink to clear a-rows y27-29. Deeply ordered puzzle. This is the crux to solve.
   ## Current: a-bar val18 ptr(25,28); 8-bar y21-37; top-bar y18-20; c-bar x42-54 y21-23; 1-vert x39-41 y21-38; 7-bar val0.
   ## DEADLOCK: 8-bar shrink needs top-bar(x27-49) to fall into y21-23, but y21-23 blocked by 8-bar(x27-29 itself!),
   ## 1-vert(x39-41), c-bar(x42-54). Circular. Try LEVER: box-e RIGHT pushes c-bar UP (out of y21-23) -> may free it.
   ## Honestly this level may need a full calibrated chain-model + BFS. Very hard. 2/8 cleared (L0,L1).
   ## RESET to CLEAN ENTRY (my probes deadlocked the board: box-8/box-e became no-ops). Solve from clean entry.
   ## CLEAN-ENTRY plan: build full L2 chain-push model — calibrate each box's exact effect from recorded probe
   ## diffs (events.jsonl), then run_bfs(is_goal: a-ptr@(43,28) AND 7-ptr@(49,28)). Box coords & chain links above.
   ## CONFIRMED BOTH pointer-bars BLOCK against obstacles (a-bar blocks vs 8-bar at x26; 7-bar blocks vs top-bar
   ## at y14 — top-bar did NOT move). So DIRECT GROWTH FULLY FAILS; obstacles MUST be cleared. The clearing is a
   ## hard ORDERED chain-deadlock (8-bar shrink needs top-bar to fall into y21-23, blocked by c-bar+1-vert; c can be
   ## pushed up by e but conflicts; 1-vert chained to c). SOLUTION REQUIRES a full calibrated L2 chain model + BFS,
   ## OR discovering the exact clear-order by hand. This is the hardest level so far. DEFINITELY build model+BFS next.
   ## Box effects to encode (from probes): box-a R=grow a right (BLOCKS at obstacle); box-7 R=grow 7 down (BLOCKS);
   ## box-8 R=grow 8 up (pushes top-bar up), box-8 L=shrink 8 (drops top-bar, blocked if top-bar can't fall);
   ## box-c L=shrink c + pull 1-vert right, box-c R=grow c left + push 1-vert left; box-e R=grow e up + push c up;
   ## box-9 R=grow 9 + push 8-bar horizontally. Diamonds fixed (walls when a bar tries to enter? untested — the
   ## pointer should DOCK into the diamond center like L0/L1, not block. Test: grow a-bar into left diamond once cleared).
   ## *** DEADLOCK-BREAK INSIGHT ***: box-c LEFT shrinks c AND pulls 1-vert RIGHT. Shrinking c FULLY should move
   ## BOTH c-bar and 1-vert off x27-49 (to x50+), clearing y21-23 -> then 8-bar can shrink (top-bar falls to y30-32)
   ## -> a-rows y27-29 clear -> grow a-bar right to dock left diamond (43,28)! (Does 1-vert collide with diamonds/f
   ## at x42-50 when moving right? TEST.) Then similarly clear 7-path (x48-50) & dock 7-ptr at (49,28).
   ## TESTING NOW: box-c LEFT (48,48) repeatedly; watch 1-vert move right & x27-49 y21-23 clear.
   ## FINDING: 1-vert (2 shrinks) reached x42-44 and COEXISTS with left diamond (diamond 13-cells preserved,
   ## 1-vert fills around them) — passes THROUGH the diamond, doesn't block! Continue shrinking c: 1-vert ->
   ## x45-47 (f-block 15 — does it pass or BLOCK? TEST) -> x48-50 (right diamond) -> x51-53. Need 1-vert & c-bar
   ## both past x49 to clear y21-23 x42-49. Then top-bar can fall, 8-bar shrinks, a-path clears. Deadlock-break LOOKS VIABLE.
   ## c-bar now x45-54, 1-vert x42-44.
   ## BLOCKED: 1-vert stuck at x42-44 — the f-block (x45-47, color15 WALL) blocks it; c can't shrink further
   ## (chained 1-vert can't pass f-block). So y21-23 x42-49 stays blocked -> top-bar can't fall -> 8-bar can't
   ## shrink -> a-path stays blocked. Deadlock persists via the f-block wall. NOTE: 1-vert now coexists with LEFT
   ## diamond, FILLING its center (43,28)=1 while arms stay d. Odd — maybe the goal/mechanic is different than I think.
   ## CONCLUSION: hand-clearing hits walls. MUST build a full L2 chain-push model (all bars + push/pull/block/wall
   ## rules, esp. f-block & diamonds as walls-that-coexist) + BFS to find the real solution order. Big build for future.
   ## Alternatively the a-ptr may not target the left diamond as I assumed — reconsider goal with a full model.
   CLEAN ENTRY reminder: a-ptr(7,28) grows right; 7-ptr(49,4) grows down; diamonds L(43,28) R(49,28);
   8-bar x27-29 y18-38; 1-top-bar x27-49 y15-17; 1-vert x36-38 y21-38; c-bar x39-54 y21-23; e-bar x53-55 y24-26; 9-bar x30-31 y36-38.

## Model status: world_model_v5.py has L0 + L1 branches. L2 = new mechanic (TBD, probe first).
   Dispatch: ENTRY has color15 -> L1 else L0. L1 model has NO wall-blocking yet (used to discover walls).
   L0 backtest 13/16 (mismatches = unmodeled docking #10/#15 + win-flag #16; harmless, L0 done).
   is_goal(L1) = pointer at diamond center (52,31).
   L1 render: bars from lengths (b,c,a,e); pointer=(e_x+1, e_top+e_len-2). Counter row63 +1 only on b/c grow.
## COUNTER (L1) = ABANDONED. Tried 4 rules (per-type, floor(N/2), new-run, k-pattern) — all broke.
   It's cosmetic & adversarial. MODEL NOW LEAVES row 63 UNCHANGED. Backtest shows counter-only
   mismatches on ~4 moves (m2,m4,m6,m9); bars/pointer are EXACT. Trust BFS on pointer position.
   Single clicks always execute (counter mispredict only drops the REST of a multi-queue).
## Pointer now (28,40), e-bar x27-29, b grown to 11. Diamond (52,31) across mid-vert wall (x42-44 y15-44).
## WALL BLOCKS (confirmed): a click that would move ANY bar cell onto an 'f'(15) cell OR off the playfield
   (y<0..52, x<0..63) is a COMPLETE no-op (0 cells change). Encoded in _step_l1. Backtest L1: only cosmetic
   counter-only mismatches remain (5 moves); bars/pointer/walls all EXACT.
## GEOMETRY constraints: e_top = 37-(a_len-2) <= 37 (only 'a' shifts e vertically; e grows down). So e-bar
   top is CAPPED at y37 -> can't cross UNDER wall (y45+). b_top = e_top-1 (b sits 1 above e).
   Walls: TOP bar y9-11 x33-56; LEFT vert x33-35 y9-26; MID vert x42-44 y15-44. Diamond (52,31) is RIGHT of mid vert.
   ONLY crossing to the right side: the GAP y12-14 (below top bar, above mid vert) where x36-63 is FREE.
   To use it: shrink e to 2 tall (e at y13-14), a_len=26 so b at y12-14 (fits gap, below top bar), move RIGHT
   across x42-44 at y12-14, then DOWN to y31 and RIGHT to x52 to dock. Intricate but reachable. Use BFS.
## *** LEVEL 1 SOLUTION (simulated valid, pointer -> (52,31) diamond, no wall-blocks) ***
   From CLEAN ENTRY (RESET first!): grow c->26 (8x box-c RIGHT @12,57), then a->26 (8x box-a RIGHT @27,57),
   then b->14 (4x box-b RIGHT @42,57), then e->20 (6x box-e RIGHT @57,57).  Final L=(b14,c26,a26,e20).
   Idea: c/ a lift e-bar into the gap y12-14; b pushes it across the mid-vert at y12-14; e grows DOWN on the
   far side (x51-53, clear) to the diamond row y31. Diamond reachable (my earlier deadlock analysis was wrong).
   COUNTER (k-pattern, 11/12) may still stop the multi-commit occasionally -> just re-commit the remainder
   (a-phase & e-phase are up/down = no counter change = execute in bulk; c/b phases may stop a few times).
   is_goal fires at pointer (52,31); expect level_up (win) on the final e-click.

## Model status: world_model_v5.py = L0 model (auto-detect). Untested on L1. Backtest L1 empty (no history).
