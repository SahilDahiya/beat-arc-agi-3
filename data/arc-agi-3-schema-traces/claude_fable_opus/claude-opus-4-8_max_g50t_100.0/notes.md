# Notes — living scratchpad

## GAME MECHANICS (confirmed on Level 0 — likely reused every level)
- MOVER = 5x5 ring (9s, center hole). Moves in TILES of PITCH=6. action 1=up,2=down,3=left,4=right.
  Passability is HOLE-AWARE: only the cells the ring OCCUPIES (pattern==9) must be clear (5); the
  center hole may pass OVER a peg/obstacle. Blocked by walls(0) and 8-trail.
- action5 = teleport mover to START + toggle legend state, IF the mover moved since last toggle; else noop.
- GHOST (2-ring): after a toggle, a ghost replays the OTHER state's mover POSITION path, synced to the
  current state's move count; freezes at the recording's end. It's an OVERLAY (mover passes through it).
- 8-TRAIL = a SPRING-LOADED PUSHABLE SNAKE. Moving the mover INTO its head advances it (tail/plug moves,
  clearing a corridor). It REVERTS when the mover leaves the head. KEY TRICK: the GHOST can HOLD the push
  (freeze at the head position) while the (state1) mover navigates the cleared corridor.
- LEGEND (top-left): shows avatar shapes per state. BORDER row63 counter = floor(actions/2) (cosmetic).
- WIN = slide the mover into the GOAL BOX (9-outline receptacle) so its center hole lands on the PEG
  (ring becomes "solid" = the legend's 1-solid). Goal box fills with 9s -> level_up.

## LEVEL 0 SOLUTION (done): push snake head at (8,38) [right], toggle, descend col14 while ghost holds
## the push, into comp1, right to goal (50,44).

## LEVEL 1 (current) LAYOUT (from grid_l1.txt / ENTRY_GRID)
- MOVER: 9-ring 5x5 at (26,50) [rows26-30 cols50-54].
- GOAL BOX: 9-outline 7x7 at rows19-25 cols25-31, peg at (22,28). (interior ~rows20-24 cols26-30)
- TWO 8-snakes (vertical, 5 wide): A = cols14-18 rows20-41; B = cols38-42 rows27-54.
- Legend has 3 slots now (9-ring + 1-solid + 1-solid). Bigger maze rows7-56 cols7-56.
- Snake heads/tails: find them (585858 = head marker?). B (cols38-42) separates mover-region from goal.
- TODO: map maze connectivity; find which snake blocks the path to the goal box; push it (ghost-hold)
  to clear, then reach goal box (26,?) -> hole on peg (22,28) means mover at (20,26).

## LEVEL 1 SNAKES = "plungers": 5x5 HEAD block (with 858585 cap) + thin STEM + small TAIL block.
- Snake A (cols14-18): HEAD rows20-24 (cap row20), stem col16 rows25-36, tail rows39-41.
- Snake B (cols38-42): tail rows27-29, stem col40 rows30-48, HEAD rows50-54 (cap row54).
- Snake A head at (20,14) BLOCKS the only gateway (20,14) from comp0 to goal comp1 (20,20)-(20,26).
- Level 1 HAS the floor(actions/2) border counter (now rendered generally in model).
- PLAN: navigate mover to (20,8) [left of snake A head], push RIGHT into it. Observe: does the
  mover push THROUGH to (20,20)->(20,26) goal? Or does it spring back (need ghost hold like L0)?
  Maybe pushing the head consumes it & mover passes through to the goal. TEST.
- WIN L1 = mover at (20,26) (hole on peg (22,28)).

## LEVEL 1 SPRING RULE (CONFIRMED)
- SPRING = HANDLE-block (3-wide, NO cap) + STEM + HEAD-block (5x5, WITH 858585 cap).
- A spring is COMPRESSED iff mover OR ghost occupies its HANDLE-TILE (the unique 5x5 pos covering
  the handle block). Direction of approach does NOT matter (perpendicular push works, confirmed).
- Compressed: HEAD-block moves 6 TOWARD the handle; stem shortens 6 on head-side; handle consumed.
- SPRINGS BACK when the handle-tile is vacated (mover leaves). GHOST can HOLD it (freeze on handle-tile).
- Snake B: handle-tile (26,38) [handle rows27-29 cols39-41], head rows50-54(cap54)->compressed rows44-48(cap48).
  Compressing clears (50,38) -> connects comp0<->comp3.
- Snake A: handle-tile (38,14) [handle rows39-41 cols15-17], head rows20-24(cap20)->compressed rows26-30.
  Compressing clears (20,14) -> connects comp0<->comp1(goal). (38,14) reachable ONLY via comp3 (needs B held).

## LEVEL 1 SOLUTION = NESTED DOUBLE-HOLD (ghost holds one spring, mover works other)
- Phase1 state0: RESET; [3,3] mover start(26,50)->(26,44)->(26,38) compress snake B. Record path=[start,(26,44),(26,38)].
- Phase2 toggle(5): mover->start; ghost replays P0, holds snake B from move2. Mover P1=
  [2,2,2,2,3,3,3,3,1,1,3,3]: down4 to (50,50)?,... reach (38,14) via (50,38)->comp3, compress snake A. VERIFY paths in sim.
- Phase3 toggle(5): mover->start; ghost replays P1, holds snake A. Mover: filler to (20,8), then [4,4,4]
  through cleared (20,14)->(20,20)->(20,26)=GOAL. Time so mover crosses (20,14) AFTER ghost reaches (38,14).
- MODEL doesn't capture spring/ghost -> must MODEL them to commit multi-step plans (else mispredict stops plan).
- WIN L1 = mover at (20,26), hole on peg (22,28).

## MODEL v (spring+ghost) — VERIFIED
- Spring compress + REVEAL halo (wall(0) 8-neighbors of compressed 8-cells -> 5): matches snake B obs.
- Ghost: ghost_pos = ghost_path[min(k,len-1)], ghost_path = state path incl start@idx0; hidden under mover
  when overlapping. VERIFIED vs level0 steps125-136 (holds push at (8,38)). Mover rendered on top.
- Counter resets on RESET; = floor(n_actions/2). VERIFIED.
- Level1 backtest FULLY GREEN. Level0 mismatches only = its L-shaped snake (not vertical spring) + loose is_goal (done).
- OPEN: level1 STATE1 legend unknown (never toggled) -> 1st toggle mispredicts on legend. Observe & hardcode.
- FULL PLAN (after RESET): [3,3, 5, 2,2,2,2,3,3,3,3,1,1,3,3, 5, 1,1,1,3,3,3,3,3,3,3,2,2, 4,4,4] -> mover (20,26)=WIN (sim-verified).

## MODEL COMPLETE (spring+ghost+legend+counter+peg-win) — level1 backtest GREEN
- WIN detect: mover(tracked cur[-1]) == goal = (peg-2). Peg = isolated 9 (all-5 neighbors). L1 peg (22,28)->goal(20,26).
- Executing double-hold. Done: [RESET,3,3,5] (in state1, ghost replaying [start,(26,44),(26,38)]).
- Remaining committed: [2,2,2,2,3,3,3,3,1,1,3,3, 5, 1,1,1,3,3,3,3,3,3,3,2,2, 4,4,4] -> WIN (forward-verified).
- If mispredict mid-plan: reality differs from model (ghost/spring in L1 config unseen) -> observe & fix.

## LEVEL 1 CLEARED (1->2)! Double-hold: [RESET,3,3,5,2,2,2,2,3,3,3,3,1,1,3,3,5,1,1,1,3,3,3,3,3,3,3,2,2,4,4,4]

## LEVEL 2 CLEARED (2->3)! Double-hold w/ toggle-b: P0->sp1, tog, P1->sp0, tog, P2->goal.

## LEVEL 3 (current): 3-slot legend. Mover(8,26), goal box(49,7) peg(52,10)->goal(50,8).
## - ONE horizontal 8-spring htile(26,32) (spring-back). gate at (26,8) [comp0<->comp1].
## - BIG color-15('f') network (rows27-55 cols25-53): boxes+lines. GOAL comp2=(50,8),(50,14),(50,20),(50,26)
##   is ISOLATED (even w/ 8-spring compressed). So 'f' must be the mechanism to open the goal.
## - Mover confined to top (rows8-20) [comp0]. 'f' HANDLE = block rows27-31 cols50-52, reachable at (26,50)
##   from (20,50) [comp0] — NO ghost needed to probe. PROBING: push down into 'f' handle at (26,50).
## 'f' MECHANIC: color-15 is PASSABLE terrain (mover walked ONTO (26,50) overlapping 'f'; overlapped 'f'
##   cells removed, none added). So the mover can walk on the 'f' network (a "highway"). Hole showed 5 (not f).
##   OPEN: does vacated 'f' REVERT to f or stay 5 (erased)? Testing by walking down the col52 'f' bar.
## PLAN: walk the 'f' network from (26,50) down col52/lines to lower 'f' box (50,26) -> goal (50,8).
## 'f' UPDATE: mover EATS 'f' (moves onto it, overlapped f-cells erased to 5/9, PERMANENT). But 'f' bars
##   are in 3-wide channels (5,f,5 flanked by walls) -> 5-wide mover CAN'T fit/traverse. Handle (26,50)
##   was a DEAD-END. Goal comp2=(50,8..26) is ISOLATED, only touching the untraversable 'f'. 8-spring
##   compressed connects comp0<->comp1(dead-end) but NOT comp2. => CONTRADICTION: goal unreachable w/ current understanding.
## MODEL now treats color-15 'f' as EATABLE-PASSABLE (mover's 5x5 footprint erases 'f' cells to 5, tracked
##   in st['eaten']). Backtest green (237/273, only L0 mismatches). BUT goal STILL unreachable (verified:
##   even 8sp-compressed + f-passable, reachable stops at row38/comp1; goal comp2 rows49-55 walled off rows45-47).
## The mover can only touch 'f' at the handle (26,50) [dead-end]; boxes' interiors have no 'f' in footprint,
##   walls/lines are stride-6/5-wide inaccessible. So 'f' handle eating is a DEAD-END.
## 'f' REVERTS! Ate handle, moved up -> handle reappeared. So color-15 'f' = PASSABLE OVERLAY (mover walks
##   through, reverts behind; ring->9, hole->5 while on it). NOT permanent-erase. MODEL FIX NEEDED: 'f'->5 in
##   base, render 'f' overlay(15) at f-cells NOT under mover/ghost footprint. (Currently model erases -> wrong.)
## But 'f'-passable STILL doesn't reach goal (narrow bars). NEW HYPOTHESIS: the two 'f' BOXES (upper (37,25),
##   lower (49,25), linked by 'f' lines) are TELEPORTERS - entering upper box (38,26) may teleport to lower
##   box (50,26)=goal region. TESTING: reach (38,26) via 8-spring hold; if mover teleports -> breakthrough.
## EXHAUSTIVE L3 MAP: goal comp2 (row50 cols8-30 + goal box) isolated by 3-row WALL gap rows45-47 between
##   the 'f' boxes (upper rows37-43, lower rows49-55, cols25-31). 'f' network bridges via col52 bar but ALL
##   'f' connectors 1-3 wide (walls flank) -> untraversable by 5-wide mover. 'f'=passable overlay (reverts),
##   doesn't move/slide (box push no-op). 8-spring spring-back gates comp0<->comp1(dead-end). Maze doesn't
##   change with legend state. Teleport FALSE. => goal UNREACHABLE by all found mechanics. MISSING SOMETHING.
## LEVEL 4 CLEARED (4->5)! (c8 ghost-hold + 'f' teleport arm + teleport-to-goal). Counter rate: full-width
##   9-border -> floor(n/2); border stopping at W-2 -> max(0, n//2 - 1).
## UNIFIED STEP SEMANTICS  (the big one — derived lvl6, consistent with ALL history)
- A step is SIMULTANEOUS: PASSABILITY is judged on the OLD configuration (each mover sees the
  others where they WERE); then ALL EFFECTS — spring settle/CRUSH, 'f' teleport arming, c11
  toggle — resolve on the NEW configuration.
- OCCUPANT = mover | ghost | 'e'. ALL of them compress springs, arm 'f' networks and toggle c11.
  Their cells are passable overlays for each other.
- => an occupant that ARRIVES on an 'f' handle this very step ALREADY arms the link. This is what
  makes lvl6 solvable: the mover graph is BIPARTITE (both teleports join same-parity boxes), so the
  mover only stands on (26,20) after ODD moves while the 'e' only sits on (26,2) after EVEN moves.
  Old-position arming => provably unsolvable. New-position arming => works. Trust the design.

## 'f' TELEPORT = N INDEPENDENT NETWORKS (generalised lvl6)
- Each connected component of 'f' wiring = one link: its own HANDLE-tile + the TWO boxes it wires.
  Armed while an OCCUPANT stands on that handle. L3/L4 had ONE network; L6 has TWO.

## SPRING CRUSH / 'e' DEATH  (CONFIRMED lvl5)
- The 'e' walker evaluates its move against the spring state incl. springs compressed by the
  mover's **OLD** position -> it CAN step into a tile the mover is currently holding open.
- Then springs re-settle on the NEW occupancy. If a restored spring cell overlaps the 'e's ring,
  the 'e' is **DESTROYED** (removed, 0 color-14 cells). Saw exactly this: mover on c8 handle
  (26,44) opened row8; 'e' walked (8,50)->(8,44); mover left handle -> spring sprang back -> 'e' gone.
- **action-5 REVIVES the 'e'** at its start (20,56) (same reset as mover + c11 toggles). CONFIRMED.
  => a crush during an early phase is HARMLESS; only the FINAL phase's walk must be safe, and it is,
  because there both c8 springs are pinned open by frozen GHOSTS (not by the transient mover).

## BACKTEST STATUS
- 36 mismatches, ALL in level 0 (blind-exploration tutorial, already cleared). Levels 1-5: GREEN.

## LEVEL 5 (current): mover(32,56) goal(50,44) peg(52,46). NEW COLOR 14 'e' = a 5x5 RING (mover-shaped,
##   center hole) at mover-tile (20,56), sealed in its OWN walled pocket (rows26-30 below are walls).
##   Springs: c8 (26,32),(26,44); c11 (8,2),(8,20),(50,14) [c11 htiles UNREACHABLE].
## *** COLOR-14 'e' = a CORRIDOR-WALKER (NOT a mirror!): a 2nd 5x5 ring that advances ONE step along its
##     own corridor per SUCCESSFUL mover move (it does NOT move if the mover was blocked). It keeps its
##     heading, turns when blocked, never backtracks (reverse only as last resort). Direction is INDEPENDENT
##     of the mover's direction. It TOGGLES c11 springs it enters. action-5 resets its pos+heading.
##     Modeled: st['epos'], st['edir']. All level-5 frames match. ***
## L5 SOLUTION CHAIN (found): mover can reach BOTH c8 handles (26,32),(26,44). Holding BOTH (2 ghosts)
##   opens row-8 so the 'e' can travel it and TOGGLE c11 (8,2) and (8,20) [mover can't reach those].
##   With those toggled, the mover can reach c11 (50,14); toggling THAT opens the GOAL (50,44).
##   NOTE: action-5 RESETS c11 toggles -> do all c11 toggling AFTER the last toggle (in state2).
##   action-5 RESETS the 'e' to its start too (confirmed + modeled).
## L5 FULL PLAN (sim-verified WIN, 60 acts after RESET):
##   P0=[3,3,1,3,3] -> c8(26,32); [5]; P1=[3,3,1] -> c8(26,44); [5];
##   P2=[3,2,3,2,3,3,3,3,3,4,1,4,4,4,4,4,1,4,4,4,3,3,3,2,2,2,2,2,4,4,1,2,3,3,1,1,1,1,1,4,4,4,2,2,4,4,2,2,4,4]
## LEVEL 3 CLEARED (3->4) via the teleport. MODEL now encodes it (_f_boxes/_f_handle + teleport in predict);
##   also FIXED _snap: mover grid is r ≡ 2 (mod 6) = 2,8,14,... (was hardcoded from 8, missed L4's col-2 handles).
## LEVEL 4 (current): mover(14,2) goal(44,8) peg(46,10). 3 springs: c8 htile(38,20) [spring-back],
##   c11 htile(8,2) + c11 htile(26,20) [persistent TOGGLES], + 'f' TELEPORT boxes (38,44)/(50,44) handle(26,56).
##   SOLUTION (sim-verified WIN): ghost0 holds c8(38,20) [opens lower-box->goal path]; ghost1 holds f-handle
##   (26,56) [arms teleport]; mover enters upper box (38,44) -> TELEPORTS to (50,44) -> walks to goal (44,8).
##   FULL = P0[2,2,2,4,4,4,2] +5+ P1[1,2,2,4,4,4,1,1,4,4,4,4,4,4,2,2,2] +5+ P2[2,4,4,4,2,1,1,1,4,4,4,2,2,2,2,2,4,3,2,3,3,3,3,3,1,1]
## *** L3 MECHANIC SOLVED: the color-15 'f' NETWORK IS A TELEPORT LINK BETWEEN ITS TWO BOXES. ***
## The 'f' HANDLE (26,50) is the SWITCH: while it is EATEN/OCCUPIED (mover or a GHOST standing on it),
## the link is ACTIVE, and ENTERING the upper 'f' box (38,26) TELEPORTS the mover to the lower 'f' box
## (50,26) — which is inside the walled-off goal region comp2! (With the handle NOT eaten, entering the
## upper box does nothing — that's why my earlier single-hold test showed no teleport.)
## => L3 SOLUTION: ghost0 holds the 8-spring (opens col8 gate (26,8) to comp1); ghost1 holds/eats the 'f'
##    handle (26,50) => activates the teleport; then the mover goes comp0 -> col8 -> comp1 -> row38 ->
##    enters upper box (38,26) -> TELEPORTS to (50,26) -> walk LEFT [3,3,3] to goal (50,8), hole on peg (52,10). WIN.
## The 'f' connectors (narrow bars/lines) are DECORATION showing the link - never meant to be walked.
## 8-spring RELEASE confirmed spring-back (reverts). Per-col: col8 clear rows [8,14,20,32,38,50] -> goal(50,8),
##   comp1(32,38), comp0 all clear on col8, separated ONLY by 8-spring(row26) + rows44-47 WALL GAP. Same col26
##   (boxes 38,26 & 50,26 split by row44 gap). PUZZLE = cross the rows44-47 gap OR widen col52 bar. No mechanic
##   found does either. TESTING double-hold (8-spring + 'f' handle simultaneously) = L1/L2 pattern.
## MODEL FIXED: color-15 'f' = passable OVERLAY over corridor (base f->5; render 15 at f-cells NOT under
##   mover/ghost footprint; reverts when vacated). Backtest 276/312 (only L0 mismatches). Multi-step 'f' tests now OK.
## GHOST-on-'f' test: NO change (ran clean) - 'f' is passable-overlay for ghosts too, NOT a holdable spring.
## KEY INSIGHT: the 'f' col52 BAR is at a mover-HOLE column (mover@col50 -> center col52). Designer INTENDS the
##   mover to descend the bar w/ hole on 'f'. Blocker = ring's OUTER flanks cols50,54 are WALLS below row31
##   (rows26-31 they're corridor=5, so mover fits at (26,50); rows32+ they're walls). So a mechanic must CLEAR
##   cols50,54 rows32-53. No spring near there found. BFS times out (ghost state too big). ALL interactions tested.
## NEXT: find what clears the bar's outer flanks. Re-read L1/L2 snapshots for a forgotten mechanic. Re-examine
##   if 'f' handle eat opens flanks over multiple steps, or if a 2nd structure exists. Question core abstraction.
## DEFINITIVE: most-permissive reachability (only walls=0 block, all else passable) = 24 tiles, goal (50,8)
##   NOT reachable. Goal walled off; ONLY bridge = 3-wide 'f' bar (cols51-53, flanks cols50,54 WALLS). 5-wide
##   mover can't fit. State2 no maze change. ALL interactions tested (8-spring compress/head, 'f' eat/box/teleport).
## => MISSING MECHANIC: something lets the mover cross the narrow 'f' bar OR moves a wide structure into the gap.
##   Ideas: (a) multi-hold 2 ghosts (8-spring + 'f') like L1/L2; (b) mover shrinks on 'f'?; (c) 'f' network SLIDES
##   from a push point not tried; (d) re-read history. Persisting.
## 8-spring HEAD push (26,8) = BLOCKED (spring-back confirmed). col52 bar flanks (cols50,54)=WALLS (verified
##   on entry grid) -> 3-wide, untraversable. ALL interactions tested: 8-spring(compress/head), 'f'(eat/box/teleport),
##   legend state0->1 (no maze change). Goal UNREACHABLE by all. Testing LAST: state2 (3rd phase) maze change? + 2 ghosts.
## If nothing: try multi-ghost (2 ghosts), re-read history for a mechanic clue, reconsider win condition.
## TELEPORT hypothesis FALSE (mover reached (38,26) inside upper box, no teleport). Confirmed goal comp2
##   (rows50-54 cols8-24 + lower box) ISOLATED (walls rows45-48 above; 'f' connectors all 1-wide untraversable).
## 'f' = passable overlay (reverts). Mover can only overlap 'f' at handle (26,50)=dead-end. 8-spring=spring-back
##   gates comp0<->comp1(dead-end). => NO mechanic found connects comp2. STILL MISSING SOMETHING.
## Currently at (38,26) inside upper 'f' box, 8-spring held by ghost. Testing: push box from inside (down [2]).
## IF nothing: RE-READ grid for mis-mapped corridor; reconsider win condition; reconsider 'f' as pushable SNAKE
##   (re-probe handle watching for flow); or reconsider 8-spring flow. DO NOT conclude impossible - it IS solvable.
##   If flow/feed -> new insight. Else re-examine (maybe 'f' network SLIDES from a push point I haven't found,
##   or the win condition differs, or a corridor mis-mapped). DO NOT give up - human-designed, solvable.

## LEVEL 2 (done): 3-slot legend (n_states=3). Mover(20,8), goal(20,20) peg(22,22).
## 3 SPRINGS: sp0 color8 htile(50,20) gate(32,20); sp1 color8 htile(32,38) gate(50,38); sp2 color11('b')
##   HORIZONTAL htile(20,32) gate(20,50). ALL 3 must be compressed to connect mover->goal (verified).
## Model generalized: springs color 8 OR 11, both orientations, head=full-cross-section end. Backtest GREEN.
## SPRING MECHANICS (CONFIRMED, backtest green L0/L1/L2):
## - color-8 = SPRING-BACK: compressed only while mover/ghost on handle-tile (need ghost to hold).
## - color-11 = persistent TOGGLE: each ENTRY into the handle-tile flips head between A(original) and
##   B(shifted 6 toward handle). PERSISTS when mover leaves. (idx202 A->B, idx203 stay B, idx204 B->A.)
##   Model: st['toggle']={htile:0/1} flip on rising edge of occupancy; renderings a_on/comp/rest1/cells.
## L2 SOLUTION IDEA: set 'b' to B (odd entries of (20,32)) -> clears (20,50). Hold sp0(50,20)+sp1(32,38)
##   color-8 with 2 ghosts (state2 double-hold). Walk to goal(20,20).
## ACTION-5 RESETS color-11 toggle to A (+ mover teleport). So each phase starts 'b'=A; the sp1-ghost
##   sets 'b'=B fresh by passing (20,32). NO parity conflict. Model fixed (backtest green L2).
## L2 SOLUTION (sim-verified WIN, mover->(20,20)):
##   P0=[1,1,4,4,4,4,2,2,2,2,4] ->sp1(32,38)  |  toggle 5
##   P1=[1,1,4,4,4,4,4,4,4,2,2,2,2,2,2,2,3,3,3,3,3] ->sp0(50,20)  |  toggle 5
##   P2=[1,1,4,4,4,4,4,4,4,2,2,2,2,2,2,2,3,3,3,3,3,3,3,1,1,1,4,4,1,1] -> goal(20,20) WIN
##   Phase3: ghost0(P0) sets b=B + holds sp1, ghost1(P1) holds sp0, mover walks. Already did P0+toggle; commit P1+5+P2.

## sp1 handle (32,38) reachable ONLY via (20,32) (confirmed) -> sp1-ghost toggles 'b'. PARITY CONFLICT:
##   Phase2 (reach sp0) needs ghost's (20,32) pass LATE (k_b>11); Phase3 (walk) needs it EARLY (k_b<=11). Same P0.
## KEY UNCERTAINTY: do GHOSTS toggle color-11? Model assumes YES (untested in L2, no ghosts yet).
##   TEST: Phase1->sp1 (b=B) + toggle + Phase2 descent. Model predicts ghost toggles 'b'->A at P2 step8,
##   mover BLOCKED at (20,50). If reality's 'b' stays B (ghosts DON'T toggle) -> mispredict at step19 -> plan simplifies
##   hugely (set 'b'=B with mover, ghosts hold sp0/sp1 without disturbing 'b').
## Winning path (all3 held): [1,1,4,4,4,4,4,4,4,2,2,2,2,2,2,2,3,3,3,3,3,3,3,1,1,1,4,4,1,1]. crit: (20,50)sp2,(50,38)sp1,(32,20)sp0.

## BIG DISCOVERY: 3-STATE CYCLE + MULTIPLE GHOSTS (not 2-state toggle!)
- action5 ADVANCES state (cycle mod n_states). n_states = #legend slots (L0=2, L1=3).
- Legend rule (general): slot<active=2-ring(recorded ghost), slot==active=9-ring, slot>active=1-solid; row5 indicator@active.
- GHOSTS: EACH recorded state s!=active spawns a ghost replaying recordings[s], synced to k. So state2 has
  TWO ghosts (P0 holds snake B, P1 holds snake A). Model refactored: recordings dict; backtest GREEN on L1.
- WIN PLAN state2 Phase3 (both ghosts hold both springs): [1,1,1,3,3,3,3,3,3,3,2,2,4,4,4] -> mover (20,26)=WIN (verified).
- Executed so far: [RESET,3,3,5, 2,2,2,2,3,3,3,3,1,1,3,3, 5]. Now committing Phase3.

## MODEL STATUS
- world_model_v5.py has LEVEL-0-SPECIFIC legend/counter rendering (hardcoded _LEGEND0/1) -> would
  CORRUPT level1 grid. MUST guard level-0 stuff by CURRENT_LEVEL==0 and add general handling.
- Mover movement (hole-aware) + action5=teleport-to-start are likely general.
- Probe level 1: confirm pitch/action-map/action5/snakes/counter, then rebuild model per level.

## Action map: 1=up 2=down 3=left 4=right 5=teleport-to-start+toggle
