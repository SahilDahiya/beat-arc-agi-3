# LEVEL 4 (4/8). Levels 0,1,2,3 CLEARED.
## *** BREAKTHROUGH 2026-07-16 *** e=3 CONFIRMED at c=3 — e-bar CROSSES wall x15-17 at gap rows18-20! Wall constraint was FAKE.
##  The earlier "e=3 no-op" was the COUNTER stopping the plan, NOT a real block. COUNTER CRACKED (0 mismatches vs all history):
##  counter(na)=3*(na//7)+[0,0,1,1,2,2,3][na%7], na=clicks-since-reset. Installed in _predict_l4 (replaces na//2).
##  Test that confirmed: RESET,shrink-a x2,shrink-9 x1,grow-c x3,grow-e x3 => (c=3,e=3,n=-1,a=-2), e-ptr(19,19). ALL 10 matched.
##  Model has NO wall constraint (_l4_valid=rect+wall overlap only) => predicts (9,4)=(37,22) REACHABLE.
## *** WIN CONDITION FOUND: BOTH diamonds docked simultaneously - e-ptr@(37,22)[c=9,e=4] AND a-ptr@(25,37)[a=0]. ***
##  Confirmed: reached (9,4,-5,-2), e-ptr@(37,22) but a=-2 (a-diamond hollow, a-ptr@(25,31)) => NO win (grid matched exactly,
##  only win flag was wrong). FIX: grow-a x2 => a=0 re-docks a-ptr@(25,37) while e-ptr stays => both docked => WIN.
##  is_goal=(g[37,22]==13 AND g[25,37]==13); win flag at c==9,e==4,a==0. Committing grow-a x2 (57,57)x2 now.
##  Layout notes for pathing: wall B(rows21-26 x15-17) blocks WIDE e-bar(e>=2, covers x15-17) from grow-c through c=4-5 =>
##  e-bar must be NARROW(e<=1) to pass wall B rows, then widen below (rows27+, no wall). Right-c-block(x42-44) blocks grow-c/grow-e
##  vs 9-bar/blue => clear the x42-44 column via shrink-9 to n<=-5 (blue past x44). At e>=4 blue(rows18-35) clears wall C(rows36-38).
##  DISPATCH BUG (harmless): _is_l4 also matches L2 (color1+color15) => L2 misrouted in backtest (247/364), but L2 cleared. Tighten later.
## *** SOLUTION FOUND! *** Model (world_model_v5.py _predict_l4) now models box-a (a-bar x22..(38+3a), a-ptr d(25,37+3a),
## ring d FIXED&PASSABLE), backtest 31/33 (only cosmetic counter). BFS over (c,e,n,a) => e-ptr reaches (37,22)=c9,e4 (WIN hypothesis).
## PATH (26 clicks, from clean entry): ccc e N AA eee NN EEE ccc NN ccc eee  = 
##  (27,57)x3,(42,57),(6,57),(51,57)x2,(42,57)x3,(6,57)x2,(36,57)x3,(27,57)x3,(6,57)x2,(27,57)x3,(42,57)x3  -> (9,4,-5,-2).
##  Key: retract a-bar (a=-2) + shift 9-bar/blue RIGHT (n=-5) clears the right-c-block, so c can reach 9 AND e reach 4.
## Path FAILED at (3,3,-1,-2): grow-e e=3 no-op'd. NEW CONSTRAINT: e-bar can't cross wall column x15-17 (right end>17=e>2)
## unless e-bar is fully BELOW wall B (top row>=27, c>=6). Cell-check found no overlap => it's a horizontal-crossing rule.
## With this constraint + right-c-block(x42-44) vs 9-bar block, BFS finds (9,4) UNREACHABLE = INTERLOCK:
##  {grow-e>2 needs e-bar below wallB (c>=6)} but {grow-c to c>=6 needs 9-bar clear of right-c-block (n<=-5)}
##  but {shrink-9 to n<=-5 needs blue clear of wall C (e>=4)} but {e>=4 needs...} = circular.
## => EITHER the e-bar-wall constraint is too strong (maybe e CAN cross at gap in some config; re-verify), OR right-c-block
##  PASSES the 9-bar (re-test — maybe like the ring), OR the win is NOT e-ptr@(37,22). 
## TODO next: (a) test if right-c-block passes 9-bar (grow-c deep at a-retracted state). (b) test e>2 at c>=6 cleanly.
##  (c) reconsider win: maybe blue@(37,22) + a-ptr moved? or a totally different goal. RE-READ level fresh.
## Model backtest 31/33 (box-a modeled, ring/hollow-diamond passable). Counter=na//2. RESET to re-sync (model desynced at e).

# Model misroutes L4 as L2 (L4 has color1 AND color15) -> mispredicts until I build an L4 branch.

## ENTRY STRUCTURE (from parse):
- 4 CONTROL BOXES (row56-58, color2, vertical divider): box9 x4-14(div x9), boxc x19-29(div24), boxe x34-44(div39), boxa x49-59(div54).
  RIGHT subcell=grow(+), LEFT=shrink(-) [L0/L2 convention]. Grow coords approx: 9R(12,57) cR(27,57) eR(42,57) aR(57,57); shrink 9L(6,57) cL(21,57) eL(36,57) aL(51,57).
- BARS:
  - 9-bar: rows30-32 x33-55, handle '3' x56 (right) => grows LEFT. LEFT end x33 touches blue bar.
  - a-bar: rows24-26 x22-36, handle '3' x21 (left) => grows RIGHT. Right end near diamond (37,25).
  - blue '1' bar: rows30-47 x30-32 (VERTICAL). 9-bar sits on top-right of it.
  - e-struct A: rows6-11 x9-11: 333/ccc/ccc/3ee/3de/3ee -> has d-POINTER at (10,10), c(12) block above, handle x9.
  - e-struct B: rows33-35 x54-56 'eee' + '333' row35.
  - c-structs: rows6-8 x9-11 & x42-44 (333/ccc/ccc) tops of bars?
- WALLS f(15): x15-17 rows9-17 & rows21-26 (vertical), x36-38 rows36-38 (3x3 block near diamond (22,37)).
- DIAMONDS/POINTERS (color d=13): 
  - (10,10) single d adjacent to e-bar => POINTER.
  - (37,25) plus-shape d (filled) at a-bar right end.
  - (22,37) hollow diamond (d at (36,22)?? center (22,37)) isolated => TARGET.
- COUNTER row63 all-3 (0). 

## GOAL (hypothesis): dock a d-pointer into a hollow diamond (like L0/L1/L3). Which pointer->which diamond = TBD.
## MECHANIC (hypothesis): grow/shrink bars via boxes; maybe CHAIN (like L1) or independent (L0). Walls f block growth.

## REVISED: L4 IS A CHAIN/LINKAGE (L1-style), not independent. Effects table (grow=+3):
##  grow-a (57,57): a-pointer(d) moves +x RIGHT +3: (25,37)->(25,40). LOCAL (a is chain-terminal).
##  grow-e (42,57): e-pointer(d) moves +x RIGHT +3: (10,10)->(10,13) [heading into f-wall x15-17];
##      AND shifts GROUP {9-bar rows30-32 x33-55, blue-bar x30-32 rows30-47, e-structB x54-56} UP -y +3 (rigid group).
##  Counter row63 increments (adversarial, like L3) — ignore for now.
## Pointers(d at bar tip): e-ptr (10,13 now), a-ptr (25,40 now). Diamonds(hollow target): a-target ring (25,37),
##   isolated hollow (37,22)[d at (36,22),(37,21),(37,23),(38,22)]. Blue/9 bars carry NO d.
##  grow-9 (12,57): 9-bar grows LEFT +3 (x33->x30), PUSHES blue-bar LEFT -x +3 (x30-32->x27-29). blue rows unchanged.
## => BLUE BAR moves in 2D: UP via grow-e, LEFT via grow-9. Blue = 3-wide vertical, currently rows27-44 x27-29.
##    Likely the piece to dock at hollow diamond (37,22)[ring (36,22),(37,21),(37,23),(38,22)]: blue covers row37 already;
##    need col 21-23 -> 2 more grow-9 moves blue x27-29->x21-23 so blue(37,22) fills the diamond center. TEST this.
## FULL LINKAGE MODELED & INSTALLED (world_model_v5.py _predict_l4, guard _is_l4 = entry has color1 AND color15).
##  render(c,e,n) VERIFIED exact vs entry + grow-e/9/c states. Params: c=grow-c, e=grow-e, n=grow-9 (a kept 0, static).
##  Positions: e-ptr=(10+3c,10+3e); e-bar rows(9+3c..11+3c) x9-.. ; c-blocks x9-11 & x42-44 rows7..8+3c;
##   9-bar rows(30-3e..32-3e) x(33-3n..55) hdl x56; blue x(30-3n..32-3n) rows(30-3e..47-3e); eStructB eee rows(33-3e..34) x54-56 hdl row35.
##  Collision rule (GUESS): grow no-ops if any dyn rect overlaps another / a wall / a-region(24-26,22-38) / off-grid.
##  Counter row63 = na (raw count, placeholder — refine).
## WIN HYPOTHESIS: e-ptr docks at hollow diamond (37,22) => c=9,e=4 (is_goal g[37,22]==13; info.win at c9e4).
##  RISK: at c=9 the right c-block (x42-44 rows7-35) may overlap the 9-bar -> collision blocks. May be wrong; test.
## CONFIRMED (test grow-c x3 + grow-e x2 all matched model): e MAXES at 1. grow-e is ALL-OR-NOTHING & needs the 9-bar
##  to move UP; the a-bar (rows24-26 x22-35) BLOCKS the 9-bar (path x33-55 rows24-26) at e=2. So e-ptr stuck col<=13.
##  => e-ptr CANNOT reach hollow diamond (37,22)[needs e=4] UNLESS the a-bar is cleared from x33-55.
## HYPOTHESIS: shrink-a retracts a-bar right end (x35->x32 at shrink x1) -> clears 9-bar path -> grow-e can pass e>1.
##  Then e-ptr can navigate to (37,22): c=9(down),e=4(right). BUT right-c-block(x42-44) vs 9-bar collision also limits c.
##  Also c=9 needs 9-bar NOT at rows18-35 while e=4 puts it at rows18-20 -> another conflict. TIGHT puzzle.
## MODEL box-a not yet modeled (no-op). Counter=floor(na/2) confirmed.
## DEADLOCK CONFIRMED (both collisions tested): (1) grow-e all-or-nothing, a-bar(rows24-26 x22-35) blocks 9/blue moving up => e maxes 1.
##  (2) wall C(x36-38 r36-38) blocks blue moving right (shrink-9 stuck at n=-1). => 9/blue unit (x(30-3n)..55) can NEVER clear
##  the a-bar (need left end>35 i.e. n<=-2, but wall C blocks blue there; lifting blue above wall needs grow-e which a-bar blocks = circular).
##  => e-ptr CANNOT reach (37,22). blue-on-(37,22) tested = NO win. a-ptr on row25 can't reach row37. 
## => MY POINTER-DOCK FRAMING IS WRONG or a mechanic is hidden. d-cells: e-ptr(10,10), a-ptr DOCKED(25,37)[filled plus], hollow target(37,22).
## grow-c blocks at c=7 (right c-block rows7-29 ADJACENT to 9-bar rows30-32; reality stricter than my overlap rule). e-ptr row<=28.
## DIAMOND BLOCKS BLUE: blue moving left DOCKS at (37,22) (x21-23, n=3) & can't pass (grow-9 no-op at n=4). blue range n in [-1,3].
## => e-ptr reach: rows10-28, cols10-13. CANNOT reach any diamond. DEADLOCK AIRTIGHT. My pointer-dock framing must be incomplete.
## click(22,37) INERT. clicks non-interactive in L4.
## A-REGION PARAMETRIZED (from a=-1,0,1): a-bar 'a'(color10) rows24-26 x22..(38+3a); a-ptr d (25,37+3a);
##  FIXED ring d (24,37),(25,36),(25,38),(26,37); handle '3' (24-26,21). shrink-a retracts bar 3/step.
## DEADLOCK-BREAK TEST: shrink-a x2 -> a-bar x22-32 (a=-2). Then at n=-1 (blue x33-35, 9-bar x36-55): blue CLEARS the a-bar
##  (x33>32); 9-bar overlaps only the RING (x36-38). => if the RING is PASSABLE for the 9-bar, grow-e UNBLOCKS => e-ptr can move
##  right => deadlock BREAKS => route e-ptr to (37,22)=WIN. TEST seq: shrink-9 x1, grow-c x3, shrink-a x2, grow-e.
##  (grind: shrink-a/box-a unmodeled -> mispredicts; observe if the final grow-e MOVES the e-ptr right = e>1 achieved.)
## *** DEADLOCK BROKEN (2026)! grow-e e=2 SUCCEEDED at a=-2,n=-1,c=3 => a-diamond RING IS PASSABLE for the 9-bar. ***
##  Recipe: shrink-a x2 (a-bar->x22-32), shrink-9 x1 (n=-1, blue x33-35 clears a-bar), grow-c x3 (e-bar to gap), then grow-e works.
##  a-bar = x22..(38+3a) [color10]; ring d(24,37),(25,36),(25,38),(26,37) FIXED & PASSABLE; a-ptr d(25,37+3a).
## BUT: e-ptr needs (37,22)=c9,e4. Right-c-block(x42-44) vs 9-bar(rows30-3e) limits c+e<=6 (blocked at c=7,e=0). So (37,22) UNREACHABLE
##  IF that limit holds. TEST: does the right-c-block PASS the 9-bar (like the ring passed)? grow-c past c=6 while 9-bar in its column.
##  If it passes => c+e limit gone => e-ptr may reach (37,22). If blocks => e-ptr max region row+col<=38, NO diamond there => 
##  win is NOT e-ptr docking (reconsider: maybe win = blue@(37,22)+other, or a-ptr, or a full config). MODEL box-a & BFS to settle.
## ISOLATION TEST: grow-e block may be ONLY blue (not the 9-bar) hitting the a-bar. Move blue far LEFT (grow-9 to n=4 -> blue x18-20,
##  clear of a-bar x22-35) then grow-e: if 9-bar(x21-55) passing the a-bar/diamond DOESN'T block => only blue blocked => deadlock BREAKS
##  (route via n>=4). Test: RESET, grow-9 x4, grow-c x3 (e-bar to gap r18-20), grow-e x2. Model predicts last grow-e no-op (9-bar hits a-region).
##  If reality does e=2 => 9-bar passes => re-model (a-region blocks only blue, or a-diamond passable) & BFS e-ptr to (37,22).
## OTHER untested ideas if that fails: click non-control cells (diamond/e-ptr/bars); grow-a extends a-bar (does a-ptr reach a right target?);
##  reconsider if grow-c/e is really a CHAIN that shifts (not collides) — re-read L1 snapshot mechanic; maybe e-ptr routes to diamond via chain shifts.
## shrink-a RESULT: moves a-PTR left (25,37)->(25,34) & hollows a-diamond(25,37); but a-bar BODY stays ~x22-35 (rows24,26).
##  So a-bar still blocks 9-bar path (x33-35) -> clearing it needs multiple shrinks & e-ptr path is extremely tight (c9,e4
##  w/ right-c-block vs 9-bar conflicts). LOW confidence in e-ptr->(37,22).
## a-ptr = (25,37+3a), a can go NEGATIVE (shrink). a-bar body right-end retracts slowly. a-diamond ring (24,37),(25,36),(25,38),(26,37) FIXED.
## PIVOT: only BLUE can reach hollow diamond (37,22): blue is vertical x(30-3n)..(32-3n) rows(30-3e)..(47-3e); covers row37;
##  grow-9 x3 -> blue x21-23 covers (37,22). TEST NOW: RESET (model out of sync at a=-1) then grow-9 x3; if blue on diamond WINS => done.
##  If not: model grow-a/shrink-a properly & BFS the e-ptr path, or reconsider goal (maybe e-ptr must reach a-diamond after
##  it's hollowed? e-ptr(10+3c,10+3e) vs a-diamond(25,37): c=5,e=9 -> still needs e>1 via cleared a-bar).
## (old plan below)
## PLAN: RESET to clean entry (a=0). Then run_backtest (post-reset should match). Then run_bfs clicks=[[27,57],[42,57],[12,57],[21,57],[36,57],[6,57]] target advance.
##  If BFS finds path to c9e4 -> execute, see if it WINS (confirms win hypothesis). If no path (collision) or no win -> 
##  reconsider: maybe win=blue at (37,22) [grow-9 x?], or a different diamond, or right-c-block PUSHES 9-bar (not no-op). 
##  Re-diff a grow-c that hits the 9-bar to learn collision behavior.
## (below: old independent-bar hypothesis, SUPERSEDED)
## MECHANIC LEARNED (grow-a): INDEPENDENT bars (NOT a chain — grow-a only changed a-region, no distant shift).
##  grow-a (+3) moved the a-bar POINTER (single d) RIGHT by 3: (25,37)->(25,40); bar filled behind it.
##  There is a FIXED hollow diamond ring at center (25,37) [d at (24,37),(25,36),(25,38),(26,37)] = a-TARGET.
##  At ENTRY the a-pointer was AT (25,37) = DOCKED. (I undocked it by growing; shrink-a should re-dock.)
##  => L4 = L0-like: each bar has a pointer d + a target diamond; grow/shrink slides the pointer. Dock ALL to win (hypothesis).
##  Box RIGHT=grow moves pointer in growth dir; LEFT=shrink reverses.
## PLAN: map each bar's pointer+diamond by grow/shrink, then dock all. a-pointer target=(25,37) (re-dock via shrink-a x1).
## Exploring: grow-e (42,57) next (e-struct A has pointer d at (10,10)).
