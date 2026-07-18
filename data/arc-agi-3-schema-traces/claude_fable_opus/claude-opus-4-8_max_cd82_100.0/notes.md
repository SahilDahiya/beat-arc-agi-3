# Notes — ARC3 game, 6 levels

## Grid layout (level 0, from ENTRY_GRID) — colors: 5=bg(gray), 3=bg2, 4=border/divider, 0, 2, 15(f)
Panels:
- TOP-LEFT (rows0-15, cols0-15; walled off by col16-17=4 and rows16-17=4):
  "template" box: block of 0 at rows3-7 cols3-13, block of f at rows8-12 cols3-13. (0 on top, f below)
- TOP-RIGHT (bg=3, cols18-63 rows0-8): legend/buttons:
  mini-box A cols35-39 rows2-6 border4 interior 0(rows3-5 cols36-38)
  mini-box B cols41-45 rows2-6 border4 interior f(rows3-5 cols42-44)
  row of 00000 at row7 cols41-45 (below box B)
- CENTER canvas:
  box border2 rows24-32 cols25-38, interior f (rows25-31 cols26-37, 12w x7h)
  solid 0 block rows34-43 cols27-37 (11w x10h), no border

## Action semantics (probing)
- action1: changed ONLY grid[63][63] 4->5 (nothing else). 
- action2: changed NOTHING (0 cells). So grid[63][63] is NOT a per-action counter (didn't tick on a2).
  Theory A: hidden cursor; a1=valid move(ticks corner as move-count), a2=blocked at edge(no tick).
  Theory B: simple actions mostly inert; core mechanic is clicks (action6). TBD.
- bottom row63 = all 4s (UI bar). grid[63][63] flips to 5 on some moves.
- action5: filled TOP 5 of 10 rows of the bottom 0-block (cols27-36 rows34-43, a 10x10 tank) with f (50 cells 0->f), AND ticked counter col62->5. Total 51 cells.
  -> center f-box (rows25-31 cols26-37) UNCHANGED. Only the tank filled, from the top.
- counter row63 fills right->left on EFFECTIVE actions: a1=col63, a5=col62; a2(no-op)=no tick.
- 6=click(x,y). TODO test 3,4, clicks.
- CORRECTED geometry: bottom tank = cols27-36 x rows34-43 (10w x10h). Template top-left = 0(rows3-7) over f(rows8-12), 5+5 rows.

- 2nd action5: NO change to tank (still top5 f / bottom5 0), but counter ticked (col61->5).
  Tick pattern so far: a1 tick, a2 NO tick, a5 tick, a5 tick. So a2 is 'rejected'; others accepted.
  Tank fill seems one-shot: first a5 -> 50% f (top), further a5 no effect. A precondition may gate more fill.

- action3: HUGE change. Static center f-box (was rows25-31 cols26-37, 2-border) became a DIAGONAL
  DIAMOND blob of f with 2-border, spanning rows~21-37, shifted LEFT (center col31->~22). Looks like
  the box was launched/rotated moving DOWN-LEFT (like a spinning projectile). Tank UNCHANGED.
  a3 did NOT tick the counter.
  Vertices approx: top(21,24) right(27,30) left(31,14) bottom(37,20) — like a rotated square, drifted left.
- Counter tick pattern is now messy: tick on a1,a5,a5; NO tick on a2,a3. Maybe counter tracks only
  certain action ids (1,5?) — SET ASIDE, it's a side UI, not the core.
- CORE mechanic = the center f-object moves/rotates when you press a direction. a3=left/rotate-ccw?

- cell-change counts: a1=1(corner), a2=0(NOTHING), a5=51(50 tank+corner), a5=1(corner),
  a3=200(blob transform, NO corner tick), a3=1(corner). So each 'real effect' is ONE-SHOT;
  repeats only tick corner. a2 does literally nothing. a3-first(big) did NOT tick corner.
  -> corner tick rule still unclear; treat as UI side-counter, model later.
- HYPOTHESIS: pressing a direction sets the f-square into a transformed state (rotate/launch),
  one-shot per direction. a3 => down-left diamond. Neutral box = start.

- a4 from diamond -> REVERTED to neutral box (big transform, NO corner tick). So a3 & a4 are INVERSE.
  Refined corner rule: transform-actions do NOT tick; non-transform actions DO tick, EXCEPT a2
  (a2 is fully ignored, never ticks). (still just a UI counter; model later.)
- Object = a square that ROTATES/ROLLS: a3=>down-left diamond(45deg), a4=>revert. One-shot each.

- CONFIRMED: a4 from neutral => down-RIGHT diamond (mirror of a3's down-left). Object ROTATION state:
  LEFT-diamond <-a3- NEUTRAL box -a4-> RIGHT-diamond. 3 states, a3=rot-left, a4=rot-right, clamped at ends.
  (a3 at left / a4 at right => no shape change, just ticks corner.)
- Diamonds are big rhombi (~178-200 cells of 2+f), drift toward the pressed side; don't reach tank.
- Counter (row63, right->left): messy, NOT a clean transform rule. IGNORE for now; brute-force later.
- a1/a2 do nothing from NEUTRAL box. Untested: a1/a2 from diamond; a5 from diamond; CLICKS(a6).

## a5 POUR MECHANIC (key!)
- a5 pours f into the tank (cols27-36 rows34-43); fill measured as f-DEPTH from the TOP per column.
- NEUTRAL pour: flat, depth 5 all cols (rows34-38 f). Repeat neutral a5 = no change (capped at 5).
- RIGHT-diamond pour: added a 45deg ramp on the RIGHT (col31:+0..col36:+5), union(max) with existing.
  Tank depths now cols27-36 = [5,5,5,5,5,6,7,8,9,10]. (col36 full=10). 15 cells added.
- => pour slope follows object TILT; pours ACCUMULATE via max-depth. Left tilt should ramp LEFT.
- Remaining 0s = bottom-LEFT triangle (cols27-35 lower rows), 35 cells.

## a5 POUR MODEL (precise, depth-from-TOP per column, cols27-36 = index0..9):
- RIGHT-diamond pour: depth = max(current, [1,2,3,4,5,6,7,8,9,10])  (ramp up to the right)
- LEFT-diamond pour:  depth = max(current, [10,9,8,7,6,5,4,3,2,1])  (ramp up to the left)  [by symmetry, unconfirmed]
- NEUTRAL pour:        depth = max(current, [5,5,5,5,5,5,5,5,5,5])  (flat half)
- ALL pours fill from the TOP. => middle cols cap at 6, CANNOT fully fill; CANNOT put f on bottom.
- So to match template (0-top/f-bot) I need a FILL-FROM-BOTTOM mechanic. Prime suspects: a1/a2 (never cracked; inert from neutral). a3=rot-left, a4=rot-right confirmed.

- CONFIRMED a1 & a2 are INERT (only tick counter). No hidden pour mode. So simple actions =
  {a3 rot-left, a4 rot-right, a5 pour}; a1,a2 do nothing.
- Achievable tank f-regions = top-anchored unions of ramps {flat5, leftramp[10..1], rightramp[1..10]}.
  Middle cols cap at depth 6 => CANNOT fully fill, CANNOT put f on bottom. So goal is NOT full-fill and
  NOT template(0-top/f-bot) via pours. => a MECHANIC IS MISSING. Prime suspect: CLICKS (a6).

## CLICKS = COLOR SELECTOR (key mechanic!)
- Legend has 2 palette boxes: box A(cols35-39,interior 0), box B(cols41-45,interior f).
- Click 0-box(37,4) => SELECTED color := 0: source box interior f->0, and marker '00000'(row7) moved
  under box A. So the source box shows the currently-selected POUR color; a5 pours that color.
- Click f-box(~43,4) presumably selects f. So I can pour EITHER 0 or f.

## POUR MODEL (CONFIRMED, matches all history)
- a5 OVERWRITES tank cells (col c, depth d from top, d=1..10) with SELECTED color, for all d <= D_tilt(c):
  neutral D=[5]*10 ; right D=[1,2,3,4,5,6,7,8,9,10] ; left D=[10,9,8,7,6,5,4,3,2,1] (left UNCONFIRMED).
  Cells beyond D_tilt keep their prior color. Pour = one overwrite of a top-anchored triangle.
- Selected color toggled by clicking legend boxes: 0-box(37,4)->0, f-box(43,4)->f. Source box shows it.
- Coverable depth per col = max over tilts = [10,9,8,7,6,6,7,8,9,10]. Bottom-MIDDLE diamond is NEVER
  coverable -> stays initial 0. => flat template (f on bottom, all cols) is UNREACHABLE. Goal != template-match.
- Object tilt states: LEFT<-a3-NEUTRAL-a4->RIGHT (3, clamped). a1,a2 INERT. a5 pours. a6 selects color.

## GOAL: still unknown. Must discover by real play (model can't tell me; only level_up does).
Reachable tank patterns = layered overwrites of the 3 triangles in 0/f. Candidates to try & watch level_up:
  (A) f-CUP: pour f neutral+left+right => f everywhere except bottom-middle 0-diamond (most 'complete').
  (B) clean single diagonal (one tilt f-pour).
  (C) flat f-top5 (already tried after 1st pour -> did NOT win).

- Clicking on the TANK (27,43) = NO-OP (didn't paint, didn't even tick counter). Clicks only affect
  the legend palette boxes. So TANK is ONLY modifiable via a5 pours. Direct paint NOT available.
- NOTE: f-cup = f-left-pour UNION f-right-pour already covers the full top too (max(left,right)>=5 all cols),
  so cup = pour f LEFT then f RIGHT (neutral pour redundant).
- STILL never tested: a1/a2 from a DIAMOND state (only tested from neutral). Could unlock fill-from-bottom.

- LEFT pour CONFIRMED: D=[10,9,8,7,6,5,4,3,2,1], overwrite selected color. Matched prediction exactly.
  So pour model fully confirmed (neutral flat5 / left[10..1] / right[1..10]).
- f-CUP (pour f left+right) = f everywhere EXCEPT bottom-middle inverted-triangle 0-notch:
  row40 cols31-32=0, row41 cols30-33=0, row42 cols29-34=0, row43 cols28-35=0 (20 cells). This is the always-0 region.

- a1 inert even from diamond => a1 & a2 FULLY INERT. Mechanic set COMPLETE:
  a3=rot-left, a4=rot-right (3 clamped tilt states), a5=pour selected color (top-anchored triangle by tilt),
  a6=click legend box to select color (0-box 37,4 / f-box 43,4), a1/a2 = nothing.

## GOAL HYPOTHESIS (new, testing): center = SOURCE-box(top, rows24-32) OVER TANK(bottom, rows34-43).
  Template = 0(top)/f(bottom). => maybe WIN when source shows 0 (select color 0) AND tank filled with f (cup).
  i.e. the vertical layout matches the template's 0-over-f. TEST: build f-cup, then select 0, watch level_up.

- f-CUP COMPLETE (tank rows34-39 all f, row40 ffff00ffff, row41 fff0000fff, row42 ff000000ff,
  row43 f00000000f). NO win from tank=cup alone (source was f, object right-diamond).

- Tried: f-cup tank + source=0 + object=right-diamond => NO win.
- Tried earlier: flat f-top5 + neutral + source f => NO win. So neither flat nor cup is the win (with those states).

## *** POUR depends on BLOCK ORIENTATION+POSITION (revised) ***
- VERTICAL box (12tall x7wide) placed just RIGHT of tank => pour fills tank's RIGHT 5 cols (32-36) to
  FULL depth (rows34-43 all f). cols27-31 unchanged. So full-fill IS reachable (earlier '3-state, notch' model WRONG).
- SOLVE PLAN for template: (1) fill cols32-36 full (vertical box right + pour); (2) fill cols27-31 full
  (vertical box LEFT of tank + pour) => tank ALL f; (3) select 0, NEUTRAL 0-pour (depth5) => clears top-5 to 0
  => tank = 0-top5 / f-bottom5 = TEMPLATE. Then hopefully WIN.
- Need to learn ROLL state machine to move block to tank's LEFT. Rolls so far: neutral -a4-> right-diamond
  -a2-> vertical box (down-right, right of tank). Mirror likely: neutral -a3-> left-diamond -a2-> left vertical box.
- ROLL MACHINE (confirmed): neutral -a4-> right-diamond -a2-> vertical-box-RIGHT; a1 reverses a2, a3 reverses a4.
  So path to LEFT vertical box from right-diamond: a3(->neutral), a3(->left-diamond), a2(->left vertical box), a5(pour left cols).
- DONE: left vertical box pour filled cols27-31 full => TANK IS ALL f (100 cells). CONFIRMED full-fill works.
- FINAL steps: roll block back to neutral [a1(->left-diamond), a4(->neutral)], a6 click 0-box(37,4)=select 0,
  a5 (neutral 0-pour depth5) clears rows34-38 -> 0 => tank = 0-top5/f-bottom5 = TEMPLATE => WIN(hopefully).

## *** LEVEL 0 SOLVED! *** Confirmed goal = make TANK match top-left TEMPLATE. Winning seq worked:
##   fill tank all-f (vertical box right pour + vertical box left pour), then neutral 0-pour to clear top5 => template.
## *** LEVEL 1 SOLVED! *** seq: RESET, a5(f@N), a4,a2,a2(->SE), click c-box(46,4), a5(c@SE). Compass model works.
## *** LEVEL 2 SOLVED *** (S:8, E:e, NW:f, cblk:c via small box). ROLL CYCLE fully confirmed:
##   N-a4->NE-a2->E-a2->SE-a3->S(-a3->SW...) ; reverse: S-a4->SE-a1->E-a1->NE-a3->N-a3->NW(-a4->N).
##   POURS CONFIRMED: N=rows0-4, S=rows5-9, E=cols5-9, W=cols0-4, NE={c>=r}, NW={c+r<=9}, SE={c+r>=9}, SW={c<=r}.
##   SMALL BOX (only at N, click ~31,20) = preset pour of a sub-region (L2: {r0-2,c3-6}) with selected color.
##     Each position may have its own small-box preset. cblk region may DIFFER per level - detect it.
## METHOD for each level: parse template -> run_python BFS over pour set {8 compass + presets} -> execute (roll->select color->pour/click).

## *** LEVEL 3 SOLVED *** (N:c, SE:f, W:9, W-smallbox:b). PRESETS are POSITION-SPECIFIC small boxes:
##   N-box pours {r0-2,c3-6} (top-middle 3x4). W-box pours {r3-6,c0-2} (left-middle 4x3).
##   By symmetry likely: S-box {r7-9,c3-6}, E-box {r3-6,c7-9}. (verify). Each small box interior clickable when block at that position.
##   W small box interior ~(14,38); N small box ~(31,20); S small box below tank; E small box right of tank.
## *** LEVEL 4 SOLVED *** (N:9, SW:e, SE:c, pN:8). SW pour = {c<=r} CONFIRMED.
## *** LEVEL 5 (LAST) *** colors 8,f,b,e,0. SOLUTION (search, verified): E(e=14), NW(8), pN(f=15), pW(b=11).
##   pN=N small box {r0-2,c3-6} (confirmed). pW=W small box {r3-6,c0-2} (confirmed). E=cols5-9, NW={c+r<=9} confirmed.
## L5 EXEC: [N] roll N-a4->NE-a2->E: sel e(47,4),a5 -> roll E-a1->NE-a3->N-a3->NW: sel 8(53,4),a5
##   -> roll NW-a4->N: sel f(29,4), click N smallbox(31,20) -> roll N-a3->NW-a2->W: sel b(41,4), click W smallbox(14,38) => WIN.
## Legend y=4: f=29,b=41,e=47,8=53. W small box interior ~(14,38); N small box ~(31,20).

## LEVEL 4 SOLUTION (search, verified): N(9), SW(e=14), SE(c=12), pN(8) [pN = N small box {r0-2,c3-6}].
##   SW pour region = {c<=r} UNCONFIRMED (verify when pouring e at SW).
## L4 EXEC: [N] sel 9(59,4),a5 -> roll N-a3->NW-a2->W-a2->SW: sel e(47,4),a5 -> roll SW-a4->S-a4->SE: sel c(35,4),a5
##   -> roll SE-a1->E-a1->NE-a3->N: sel 8(53,4), click N small box(31,20) => WIN.
## Reverse rolls: N-a3->NW-a2->W-a2->SW-a4->S-a4->SE-a1->E-a1->NE-a3->N. Legend y=4: 9=59,e=47,c=35,8=53.

## LEVEL 3 (solved) target: b-block {r3-6,c0-2}; 9={c<=4}\b-block; c={c>=5 & c+r<=8}; f={c>=5 & c+r>=9}.
## SOLUTION (verified): N(color c=12), SE(color f=15), W(color 9), bblk(color b=11) where bblk=preset {r3-6,c0-2}.
##   N small box pours {r0-2,c3-6} (top-middle, same as L2). By SYMMETRY the W small box should pour {r3-6,c0-2} (b-block). Verify at W.
## L3 LEGEND coords (same as L2, y=4): 0=23,f=29,c=35,b=41,e=47,8=53,9=59.
## L3 EXEC: [N] select c(35,4), a5. -> roll N-a4-NE-a2-E-a2-SE: select f(29,4), a5. -> roll SE-a3-S-a3-SW-a1-W: select 9(59,4), a5;
##          then select b(41,4), click W small box (find its coords when at W) => bblk {r3-6,c0-2}=b => WIN.
## Solution works from current tank (f residue at {r0-2,c3-6} harmless; N(c) overwrites it).

## LEVEL 2 target tank (r0-9,c0-9): colors f,c,e(=14),8.
##   c-block: r0-2, c3-6.
##   e = {c+r>=10 AND c>=5} (right region).   8 = {c+r>=10 AND c<=4} (lower-left wedge).   f = everything else.
##   NOTE e/8 diagonal is c+r>=10, but my SE pour = {c+r>=9} (off by ONE) => likely MORE pour positions exist (shifted diagonals). MUST explore.
## legend L2 boxes (row3, cols): 0-box int~34-35? then f,c,b(=11),e,8,9 across cols33-63. click interiors to select.
## NEW small box rows17-21 cols29-34, interior "0022"/"ffff" — UNKNOWN purpose (preview? 2nd tank? control?). Investigate.
## Legend confirmed pour COMPASS (8 pos): N=rows0-4,S=rows5-9,E=cols5-9,W=cols0-4,NE={c>=r},NW={c+r<=9},SE={c+r>=9},SW={c<=r}.
##   Rolls: N-a4->NE-a2->E-a2->SE (CW), reverse a1/a3. Need to find shifted-diagonal positions for {c+r>=10} etc.
## PROVEN via run_python search: the 8 compass pours CANNOT build L2 target (full reachable set=21997 grids, target not in it).
##   => MORE block positions/pour regions exist. Need shifted diagonals {c+r>=10}, top-k rows, middle cols, etc.
##   TOOL: I can run_python a real BFS over hypothesized pour-region sets to find the solve sequence once atlas known.
## *** SMALL BOX = PRESET FINE-POURER *** at N, clicking its interior (e.g. 31,20) pours a 3x4 region {r0-2,c3-6}
##   (= the c-block spot) with the SELECTED color. Call this pour 'cblk'.
## L2 SOLUTION (run_python search, verified == target): pour order:
##   1) S color 8    2) E color e(=14)   3) NW color f(=15)   4) cblk color c(=12) [click small box at N]
## ROLL MACHINE (8-cycle, CW advance): N-a4->NE-a2->E-a2->SE-a3->S-a3->SW-a1->W-a1->NW-a4->N. Reverse = a1/a3 swap.
##   CONFIRMED: N-a4->NE-a2->E-a2->SE and reverses (SE-a1->E-a1->NE-a3->N). REST (SE-a3->S etc.) HYPOTHESIZED - verify while executing.
## EXEC PLAN L2 (after RESET; block N,color f,tank0): 
##   ->S: a4,a2,a2,a3 ; select8; a5 ;  ->E: a4,a1 ; select e; a5 ;  ->NW: a1,a3,a3 ; select f; a5 ;  ->N: a4 ; select c; click smallbox(31,20).
##   VERIFY block position after each roll (transitions partly hypothesized).
## LEGEND CLICK COORDS (L2, y=4): 0->x23, f->x29, c->x35, b->x41, e->x47, 8->x53, 9->x59. Small box pour: click (31,20).
## Solution works from CURRENT tank too (NW re-establishes f broadly). S pour region (rows5-9) UNVERIFIED - check when pouring 8 at S.
## Uncertain rolls to verify: SE-a3->S, S-a4->SE, N-a3->NW, NW-a4->N.
## MULTIPLE SMALL BOXES: each block position seems to have its own preset small-pourer (N-box pours cblk {r0-2,c3-6};
##   E position shows a small box to the right rows35-40 cols49-52). So more fine pours available per position. (Not needed for current L2 solve.)

## LEVEL 1 (solved): template was 3-color. Tank target (10x10, 0-idx row r col c):
##   c(=12) where c+r>=9 (lower-right triangle); f where c+r<=8 & r<=4 (upper-left); 0 where c+r<=8 & r>=5 (lower-left=initial).
## legend 3 boxes: 0-box cols32-36(int33-35), f-box cols38-42(int39-41), c-box cols44-48(int45-47). click interior to select.
## SOLVE plan L1: (a) neutral f-pour => rows0-4 f; (b) fill {c+r>=9} with c. Need a LOWER-RIGHT-triangle pour =
##   180deg rotation of left-diamond pour {c+r<=9}. = an "up-pointing diamond". NOT YET produced -> must find via rolling.
## *** POUR = COMPASS MODEL (block rolls around tank, 8 positions; each pours a region of selected color, OVERWRITE) ***
##   N  (above, horiz box)      : rows0-4 (top-5)          [neutral]
##   S  (below, horiz box)      : rows5-9 (bottom-5)       [unconfirmed]
##   E  (right, vert box)       : cols5-9 (right-5)        [vbox-right]
##   W  (left, vert box)        : cols0-4 (left-5)         [vbox-left]
##   NW (above-left diamond)    : {c+r<=9} upper-left      [a3 from neutral]
##   NE (above-right diamond)   : {r<=c}  upper-right      [a4 from neutral]  (r<=c means c>=r)
##   SE (below-right diamond)   : {c+r>=9} lower-right     [a4,a2,a2 from neutral] *** CONFIRMED = the c region! ***
##   SW (below-left diamond)    : {r>=c}  lower-left       [a3,a2,a2 ; unconfirmed]
## ROLL transitions: N -a4-> NE -a2-> E -a2-> SE ; reverse via a1 (up) / a3 (left). i.e. a4/a2 advance CW-ish, a1/a3 reverse.
##   (need to map full cycle incl S, SW, W, NW roll edges for a model)
## LEVEL 1 SOLVE (verified on paper): current tank has f in {c+r>=9}, block=SE, color=f.
##   1) roll SE->N: a1,a1,a3.  2) pour f (neutral) => rows0-4 f.  3) roll N->SE: a4,a2,a2.
##   4) select c (click c-box ~46,4), pour c (SE) => {c+r>=9}=c => TARGET (c lower-right, f top-left, 0 lower-left). WIN.

## *** GOAL (high confidence): make TANK == TEMPLATE ***
- TEMPLATE = 0-block rows3-7 cols3-12 (5tall x10wide) OVER f-block rows8-12 cols3-12. Total 10x10.
- TANK = cols27-36 x rows34-43 = 10x10. SAME dims. So target tank = 0 in TOP-5 rows, f in BOTTOM-5 rows.
- PROBLEM: pours fill from the TOP => f-on-bottom NOT reachable by pours. Need a FILL-FROM-BOTTOM or
  FLIP mechanic not yet found. Candidates: a2 (fully ignored from neutral = suspicious!), a click on
  object/template/elsewhere. Clean diagonal (right f-pour) also did NOT win, consistent (goal is flat 0/f).

## *** MECHANIC REVISION: object is a ROLLING BLOCK (not 3 clamped tilts) ***
- a2 from the RIGHT-DIAMOND rolled the block into a VERTICAL box (interior f, 7 wide x12 tall,
  border rows32-45 cols38-46) positioned to the RIGHT of the tank. So the block TRANSLATES + ROTATES
  as it rolls; there are MORE orientations/positions than {L,N,R}. a2/a1 roll down/up; a3/a4 roll left/right.
  (a2 was 'ignored' from neutral = roll-down blocked there, but works from a diamond.)
- neutral box interior = 7tall x12wide (rows25-31 cols26-37); vertical box = 12tall x7wide. Same rect rotated 90 + moved down-right.
- IMPLICATION: I can probably roll the block to BELOW the tank and pour f into the tank's BOTTOM
  (=> match template 0-top/f-bottom). Pour target likely depends on block POSITION. TESTING now.

## TRIED (no win): flat f-top5 (neutral,srcF); f-cup (variants); clean right diagonal.
## Untried strong candidate: CLEAN single-tilt f-pour on EMPTY tank.
  right f-pour on empty tank => clean diagonal:
    r34 ffffffffff / r35 0fffffffff / r36 00ffffffff / ... / r43 000000000f  (f upper-right, 0 lower-left).

## Current plan
- RESET (a0): clean tank all-0, object neutral, source f, selected f. Refunds move budget too.
  (post-reset also gives CLEAN counter data to crack the row63 counter.)
- Then: a4 (->right-diamond), a5 (right f-pour) => clean diagonal. Check level_up.
- If no win: a3,a3 (->left), a5 (adds left tri => cup, known no-win) OR try 0-pours variants.
- If clean patterns all fail => the goal likely isn't a simple tank pattern; re-read board / build model / reconsider.
- BUDGET: counter row63 depletes right->left; RESET refunds it. ~ maybe a move limit -> be efficient.
- Open Qs: exact win condition? death risk if counter fills?

## Hypotheses
- Maybe paint center canvas to match template? Or swap 0/f arrangement? Unknown.
- Legend boxes (0 and f) may be color selectors clickable.

## Confirmed facts
- (none yet)
