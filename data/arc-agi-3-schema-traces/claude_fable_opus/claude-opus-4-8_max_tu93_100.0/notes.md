# Notes — scratchpad

## Rendering
- Grid 64x64, values are hex colors. Background = 5. Bottom row (63) = all 6 (border/HUD?).
- Content is rendered 3x: each logical cell = 3x3 pixel block. Content region pixels rows15..47, cols15..47 => 11x11 LOGICAL grid.
- Logical origin: pixel (15,15). logical (lx,ly) -> pixels rows 15+3*ly..+2, cols 15+3*lx..+2.

## Level 0 layout (11x11 logical), from ENTRY_GRID
- Player: block (lx=0,ly=0) color 9 with a single `4` pixel at local (row1,col2) = middle-right.
- Goal: block (lx=10,ly=10) color 14 (`e`).
- Interior cells are color 0 or 2 (maze walls/paths, TBD which is passable). 5 = empty/void.
- Downsampled 11x11 (col0..10):
  r0:  P  2  0  .  0  2  0  2  0  .  .
  r1:  .  .  2  .  2  .  .  .  2  .  .
  r2:  .  .  0  .  0  2  0  2  0  2  0
  r3:  .  .  2  .  2  .  2  .  .  .  2
  r4:  .  .  0  2  0  .  0  .  .  .  0
  r5:  .  .  .  .  .  .  2  .  .  .  2
  r6:  0  2  0  2  0  2  0  .  0  2  0
  r7:  2  .  2  .  .  .  .  .  .  .  .
  r8:  0  2  0  2  0  2  0  .  0  2  0
  r9:  .  .  2  .  .  .  2  .  2  .  2
  r10: 0  2  0  .  .  .  0  2  0  .  G
  (P=player9, G=goal14, .=5 void, digits are the color)

## Maze mechanics (CONFIRMED from analysis)
- Walkable = any non-5 cell (0 AND 2 both corridors; alternate 0/2 decoratively along path). 5 = WALL.
- Unique path start(0,0)->goal(10,10), 37 cells / 36 moves. Player walks corridor cell-by-cell.
- Path (y,x): (0,0)(0,1)(0,2)(1,2)(2,2)(3,2)(4,2)(4,3)(4,4)(3,4)(2,4)(2,5)(2,6)(3,6)(4,6)(5,6)(6,6)(6,5)(6,4)(6,3)(6,2)(7,2)(8,2)(8,3)(8,4)(8,5)(8,6)(9,6)(10,6)(10,7)(10,8)(9,8)(8,8)(8,9)(8,10)(9,10)(10,10)

## CONFIRMED MODEL (world_model_v5.py, backtest-green)
- ROOM-HOP maze: rooms at EVEN logical coords, doors at odd cells between them. A hop moves the
  player 2 cells (door+dest) iff door AND dest are walkable (block not all-5); else no move.
- Mapping (assumed, action4=east CONFIRMED): 1=up 2=down 3=left 4=right. 1/2/3 not yet directly confirmed.
- HUD row63: move counter, 0s fill from RIGHT. increment = max(1, cells_moved) => blocked +1, hop +2.
- Player pos + counter READ FROM INPUT GRID each predict (robust to state re-init). erase old cell->color 0.
- Player sprite = [[9,9,9],[9,9,4],[9,9,9]] (4 at local row1,col2 = east-facing). Rendered FIXED east.
  RISK: sprite may rotate to face move dir (untested for up/down/left). If a commit halts after a
  non-east move with only the 4-pixel differing, that's it -> model sprite as pointing to last-move dir
  (east=loc(1,2), west=(1,0), north=(0,1), south=(2,1)) and re-backtest.

## CONFIRMED extras (backtest-green, 2/2)
- SPRITE ROTATES: '4' pixel points toward last SUCCESSFUL move dir. local pos: up=(0,1) down=(2,1) left=(1,0) right=(1,2). Blocked move keeps current facing (read from grid). Entry default=east.
- HUD increment: TRUE RULE STILL UNKNOWN. Movement+sprite are EXACT (backtest mismatches are HUD-only).
  Some hops cost +2 instead of +1; it's POSITIONAL (depends on source cell, NOT direction/path-history —
  same (prevdir,curdir) & same (D,D) gave both +1 and +2). Refuted: div-4, diagonal, first-hop, degree, distance.
  CONFIRMED +2 SOURCES: (0,0),(4,4),(6,4),(2,8),(8,10).  CONFIRMED +1: (2,0),(2,2),(2,4),(4,2),(6,2),(6,6),(4,6),(2,6),(4,8),(6,8),(6,10).
  deg3 always +1 so far; deg2 MIXED. No rule yet. (LEVEL-SPECIFIC coords, so rule must be structural/general for next levels.)
  dHUD seq over 9 moves [U*,E,D,D,E,U,E,D,D] = [1,2,1,1,1,2,1,1,2] (blocked U* =+1). counter=actions+(#+2 so far).
  STRATEGY: model uses inc=+1 always (simplest, right for majority). Plans chain +1 moves & halt at each
  +2 move -> record that source into the +2 list above. After a few, brute-force the rule with more points.
  When halt: source pos = position BEFORE the mispredicted action (get from read_history/events).
- Sprite '4' faces last move dir CONFIRMED for E(1,2),S(2,1),U(0,1). West L=(1,0) inferred.
- mapping CONFIRMED: 1=up 2=down 4=east(right). 3=left inferred.

## HUD deep data (level 0, exact from events.jsonl)
- counter sequence: 0,1,3,4,5,6,8,9,10,12,13,14,15,17,18,19,20,22,23. SKIPPED 2,7,11,16,21.
- +2 at counter_before {1,6,10,15,20}, sources (0,0),(4,4),(6,4),(2,8),(8,10), dirs R,U,D,R,U.
- HUD +2 rule is GLOBAL (cumulative counter across ALL levels; +2 at global-before in {1,6}∪mult-of-5,
  i.e. 1,6,10,15,20,25,30,35,40,...). DISPLAY resets to 0 each level but the +2 rule uses the persistent
  global counter. Since state re-inits per level, the global counter is NOT derivable from the grid ->
  can't predict +2. => USE +1-ALWAYS in model. Movement/boxes/death/level_up all EXACT (backtest mismatches
  are HUD-only at +2 moves). Counter <<64 so it NEVER blocks winning; +2 halts are harmless.
  WORKFLOW: commit plan -> it chains +1 moves, halts at first +2 (move still executes) -> re-commit rest.
  (Don't waste more effort trying to predict HUD; grind ~4-5 moves/commit.)

## PROGRESS: levels 0-5 SOLVED. On level 6/9.
## LEVEL 6 (13x9) origin(12,18): P(0,4) G(12,4). NEW color-13(d) box facing S @(4,0); color-8 static 8W@(10,2).
##   Row4 has walls at (7,4),(9,4),(11,4) - not a straight corridor. color-13 mechanic UNKNOWN (patrol? static? diff?).
##   HUD base=2. *** color-13 = DORMANT SENTRY *** (CONFIRMED + MODELED, backtest lvl6 3/3). marker 15=asleep, 11=active.
##   While asleep: does NOT move. The turn the player enters its facing LINE-OF-SIGHT (rooms straight ahead, walls block) it
##   ACTIVATES (15->11) but does NOT move that turn. Once active: PATROLS in facing dir every hop (same as color-12).
##   Contact kills like a patrol. LOS itself did NOT kill. Box tuple 6-elem [x,y,fx,fy,col,active].
##   *** ACTIVE SENTRY RULE = BFS-PATHFIND chase, targeting the player's OLD (pre-hop) position *** CONFIRMED
##   (greedy & new-pos-target REFUTED). Each hop: 1 room-hop along shortest room-path toward player's PRE-HOP cell;
##   facing = first-step dir from NEW cell toward same target. _sentry_step uses _bfs_first. Matches ALL 8 transitions.
##   (Targeting OLD pos disambiguates ties: e.g. sentry(8,6)->player-old(10,4) is uniquely via (10,6) since door(9,4) walled.)
##   color-12 patrol REVERSES at wall; color-13 sentry CHASES. MAZE: only W<->E crossing = (4,4)-(6,4) via door(5,4);
##   player MUST pass (4,4) -> sentry ALWAYS wakes. But player keeps a head-start lead down a single corridor and the
##   chaser stays >=2 rooms behind -> VERIFIED SAFE under greedy-chase AND worst-case perfect-pathfinding chase.
##   PLAN (from player (6,8), sentry (6,4)S active): remaining [4,1,4,1,1,1,4,2,2] -> goal(12,4) via
##   (8,8)(8,6)(10,6)(10,4)(10,2)[destroy color-8 from S](10,0)(12,0)(12,2)(12,4). HUD base=2, +3 was a minority.
##   BASE_BY_LEVEL {0:1,1:1,2:2,3:3,4:1,5:1,6:2}. If halt: HUD-minority -> re-commit suffix from current player pos.
## LEVEL 6 SOLVED (sentry=BFS-pathfind chase toward player's PRE-HOP pos, contact-kills).
## LEVEL 7 (11x11, origin(14,14)): player(0,10) goal(4,0). color-8 box @(2,6) faces S (killzone (2,8)).
##   color-13 SENTRY @(8,2) faces S, dormant. LOS=col8 south {(8,4),(8,6)} (wall at (8,7)).
##   *** COLUMN 8 is the ONLY vertical corridor to the goal row (y0). Sentry @(8,2) GATES it. Player MUST pass (8,2). ***
##   Path shell: (0,10)(2,10)(4,10)(4,8)(4,6)(6,6)(8,6)[enters LOS->activates sentry](8,4)(8,2)?(8,0)(6,0)(4,0)=goal.
##   HUD base lvl7 = 1 (BASE_BY_LEVEL[7]=1, confirmed 0->1). Maze is a TREE (no cycles; (2,8) deadly killzone breaks the
##   x2 loop) -> a 1-lag chaser ALWAYS corners the player when doubling back (verified by hand-sim: every double-back
##   collides). So sentry CANNOT be passed by maneuvering -> must DESTROY it via contact. PROBE: approach (8,6) [activates
##   sentry, no move], then (8,6)->(8,4) [action 1]: sentry chases to (8,4) = same cell as player. My model predicts DEATH.
##   OBSERVE reality: DIED (contact=death -> need new idea, maybe sentry can't be activated / different route) OR sentry
##   DESTROYED/passed (-> solution: continue (8,4)(8,2)(8,0)(6,0)(4,0)=goal; add player-onto-sentry destroy to model).
##   *** PROBE RESULT: sentry CONTACT = DEATH (confirmed). *** Player (8,6)->(8,4), sentry (8,2)->(8,4)=same cell -> DIED.
##   Tree maze + same-speed chaser = chaser ALWAYS wins (fleeing only MAINTAINS distance d, never increases). So on a pure
##   tree the gate is unsolvable. *** KEY: color-8 box @(2,6) killzone (2,8) BREAKS the only cycle. DESTROY it (hop onto
##   (2,6) from (4,6)=west, non-facing side) -> (2,8) opens -> maze gains a CYCLE: (2,6)-(4,6)-(4,8)-(4,10)-(2,10)-(2,8).
##   With a cycle the evader can shake the chaser / get it BEHIND on the goal path, then race up col8 (fleeing keeps it
##   behind = safe). Plan: destroy box FIRST (sentry dormant, safe), THEN maneuver sentry via cycle, THEN race to goal(4,0).
##   Model already: destroy color-8 removes it + its killzone. Sentry paths on base(no boxes) so post-destroy it's realistic.
##   SOLUTION FOUND + SIM-VERIFIED (no collision/swap/killzone, reaches goal): 21 steps
##   [4,4,1,1,4,4,3,3,3,2,2,4,1,1,4,4,1,1,1,3,3]. Activate sentry @(8,6), retreat W destroying color-8 @(2,6) (step9),
##   drop through opened (2,8)->(2,10), loop back up, then race up col8 (8,6)(8,4)(8,2)(8,0)(6,0)(4,0)=goal with sentry
##   chasing 1-2 rooms BEHIND. ALL sentry moves are UNIQUE shortest paths (no tie-break ambiguity) -> robust.
##   CONFIRMED: destroying a color-8 box CLEARS its killzone (player walked (2,6)->(2,8)->... alive). Cycle opened as planned.
##   Sentry followed the sim EXACTLY through 13/21 moves. HUD base=1 -> re-BFS+recommit on minority halts.
## LEVEL 7 SOLVED.
## *** LVL8 SENTRY RULE FIX (BREAKTHROUGH): sentry chases player's PRE-HOP cell via shortest path, tie-break S,N,E,W,
##   BUT AVOIDS stepping onto the player's NEW cell when an ALTERNATIVE shortest-path step exists (only lands on the
##   player = kills when FORCED, no alternative). Encoded in _bfs_first(avoid=npos). This makes the (14,x) crossing work.
##   WINNING PATH from (12,6): [2,3,2,2,3,3,1,4] -> (12,8)(10,8)(10,10)(10,12)(8,12)(6,12)destroy(6,10)destroy(8,10)=GOAL.
## *** LVL8 MODEL COMPLETE (backtest GREEN on all of level 8, #184-235). Three final mechanics found:
##  1. PATROL destroy-on-hop-onto: hopping onto a color-12 patrol's cell DESTROYS it (player survives),
##     exactly like color-8 (dest==patrol.cell -> destroy). Confirmed step46: player (12,0)->(12,2) killed patrol B.
##  2. RENDER priority on overlap: patrol(12) draws OVER sentry(13); box8(8) on top. (_cgrp={13:0,12:1,8:2}).
##  3. HUD move-counter is EXACTLY round(64*n/BUDGET), n=moves taken; BUDGET[8]=50. (Not fixed +1; the "+2"
##     moves are just rounding bumps.) Encoded via inversion n=round(cur*bud/64). (levels 0-7 still use approx BASE.)
##  WINNING PATH from (12,8): [3,2,2,3,3,1,4] -> (10,8)(10,10)(10,12)(8,12)(6,12)destroy(6,10)destroy(8,10)=GOAL.
## LEVEL 8: sentry=through-chase (validated, disappears under patrols=overlap-survive). Goal UNREACHABLE in base model
##   (3108 states exhausted). Sentry-DISABLED -> pocket reachable in 16 (via (14,x) branch crossing col12). So sentry blocks
##   it. Refuted: chase-in-LOS, give-up, swap-safe, hop-destroys, avoids-patrols, dies-on-patrol, killzone-kills-enemy.
##   PARITY: bipartite graph -> crossing timing locked, vertical patrol @(12,4) never favorable at reachable hop-counts.
##   Blocked move does NOT advance patrols (confirmed). *** HYPOTHESIS: PATROLS (color-12) do NOT KILL by contact — only the
##   SENTRY (col13) + killzones kill. *** Never actually observed a patrol-onto-player death (always avoided them in lvl4-6).
##   With this, pocket reachable in 16: [3,3,1,1,4,1,1,4,4,4,2,2,2,2,3,2] -> (10,10), sentry TRAILS (never collides).
##   Backtest still green (no recorded patrol-death). *** DECISIVE TEST: move5 = player (6,4)->(6,2) where @(6,2) patrol also
##   ->(6,2). If player SURVIVES -> patrols-don't-kill CONFIRMED -> continue to (10,10) then to goal (8,10, killzone: destroy
##   color-8 @(6,10) via (10,12)(8,12)(6,12)(6,10) OR goal>killzone). Model _c==13 only for contact-death (patrols excluded).
## LEVEL 8 (15x13, origin(9,10)): player(8,8) goal(8,10). Boxes: color-13 SENTRY @(6,4) faces S (dormant); color-12
##   patrols @(6,2)W,(12,2)W,(12,4)S; color-8 @(6,10) faces E (killzone=(8,10)=GOAL!), color-8 @(6,12) faces N (killzone(6,10)).
##   (6,4)[sentry] is a CUT VERTEX: player's 6-room pocket {(8,8)(6,8)(4,8)(6,6)(4,6)(4,4)} connects to rest ONLY via (6,4).
##   Pocket forms a HEXAGON cycle (6,4)-(6,6)-(6,8)-(4,8)-(4,6)-(4,4). Player's only 1st move (8,8)->(6,8) enters sentry LOS
##   -> activates it. Goal in killzone -> must destroy color-8 @(6,10) (chain: reach (8,12)->(6,12)destroy->(6,10)destroy->(8,10)).
##   *** BFS says goal UNREACHABLE (exhausted 106 states) — but level IS solvable, so my model MISSES a mechanic. ***
##   Hexagon escape [3,3,1,1,4,1] beats the SENTRY (reaches gate (6,4)) but dies to PATROL @(6,2) landing on exit cell (6,2)
##   at hop 6 (patrol oscillates (0,2)<->(8,2), at (6,2) on hops 0,6,8,14..). BFS finds no timing works. Prime suspects for
##   missing mechanic: SWAP-pass (hop through a box safely) OR hopping ONTO a patrol/sentry DESTROYS it. Need to PROBE.
##   HUD base lvl8 = 1. All mechanics MATCH reality (sentry activate + 3 patrols moved exactly as modeled on hop1).
##   Faithful search: goal UNREACHABLE (62 states); player can only reach depth (12,4)/(14,6); vertical patrol @(12,4)
##   roams (12,0)-(12,8) + always-chasing sentry block the crossing to goal pocket via (12,6)(12,8)(10,8)(10,10).
##   *** HYPOTHESIS: sentry may CHASE ONLY IN LINE-OF-SIGHT (untested! lvl6/7 chases were all straight corridors). ***
##   If chase-in-LOS, cyclic top region lets player break LOS -> lose sentry -> time the patrols -> solvable.
##   TEST: circle hexagon [3,3,1,1] from (6,8). My ALWAYS-CHASE model predicts sentry: after m1->(6,6), m2->(6,8), m3->(4,8),
##   m4->(4,6). If reality's sentry LAGS/STOPS when LOS breaks (player at (4,8) not aligned w/ sentry) -> chase-in-LOS CONFIRMED.
##   m1 DONE: sentry (6,4)->(6,6) MATCHES always-chase (target (6,8) was visible). patrols (2,2)(12,2)(12,8) all match.
##   DECISIVE m2: player (4,8)->(4,6). Player pre-hop (4,8) is NOT on any straight line from sentry (6,6) -> if always-chase
##   sentry->(6,8); if chase-in-LOS sentry can't see target -> stays (6,6)/reverts. Re-committing [3,1,1], watch m2 sentry.
##   RESULT: sentry chased to (4,8) w/o LOS -> ALWAYS-CHASE confirmed (chase-in-LOS refuted). Swap & hop-onto-destroy also
##   don't help (still confined). *** BREAKTHROUGH HYPOTHESIS: PATROLS BLOCK the sentry's pathfinding (it detours around
##   them). *** With this, goal becomes REACHABLE. Encoded: _sentry_step gets patrol_cells as `blocked`. Backtest still green
##   (lvl6/7 have no patrol+sentry; lvl8 sentry moves so far had no patrol in path). BFS(new model) found 27-move path from
##   current state (player(4,4) sentry(4,8) pats (2,2)E,(12,2)W,(12,4)N): [4,2,2,3,1,1,4,1,1,4,4,4,2,2,1,3,2,4,2,2,3,2,2,3,3,1,4]
##   -> goal (8,10). Sim: AVOIDS survives to goal; THROUGH dies move14 (sentry->(12,2)=player). So moves 0-13 safe under BOTH;
##   *** MOVE 14 is the decisive test *** of patrols-block-sentry. If player survives move14 -> hypothesis CONFIRMED, path -> goal = LVL8 SOLVED.
## LEVEL 5 (13x13) origin(12,12): P(12,2) G(0,2). Row2 = straight W corridor P->G. Boxes: color-12 patrols cN@(6,4),cW@(12,10);
##   color-8 static 8S@(4,6),8S@(10,6),8N@(4,10),8W@(6,10),8N@(4,12),8N@(6,12). cN oscillates col6 (6,0)<->(6,4) [blocked S at (6,5)], reaches (6,2) on row2 -> TIME passing (6,2). cW patrols row10 (far). Straight-ish W shot dodging cN.
##   HUD base lvl5 = 1 (set BASE_BY_LEVEL[5]=1). NEW: patrol cW overlapped STATIC box 8W(6,10). Render fix:
##   color-8 (static) draws ON TOP of color-12 (patrol) at overlaps. Backtest lvl5 green. cW keeps moving (model
##   passes it through static boxes, invisible under them). UNVERIFIED: is a patrol ABSORBED by a static box? If cW
##   "emerges" at a plain cell (2,10) & reality is empty -> patrol is absorbed on hitting static -> remove it. Watch.
##   28-step BFS plan committed; player path (rows2-8) far from cW(row10) so cW fate shouldn't affect solution.
## LEVEL 4 (15x11) origin(9,14): P(14,0) G(6,6). FOUR color-12 patrols: cS@(6,4), cN@(6,8), cS@(4,6), cE@(0,6).
##   Goal (6,6) guarded: col6 has cS(6,4) moving down + cN(6,8) moving up (may collide/interact!), col4 cS(4,6), row6 cE(0,6).
##   FIXED (backtest-green): box move needs DOOR+DEST both walkable (added _bcan); box-box collision -> later-processed
##   box overwrites (one survives) via new_boxes dict; boxes DO move onto goal cell. HUD base=1 for lvl4 (BASE_BY_LEVEL,
##   NOT max(1,level) - that broke at lvl4). Boxes+player move in lockstep (box moves 1room/hop, indep of player dir).
##   *** BOXES OVERLAP (never merge) ***. Model REWRITTEN to track boxes in STATE (list [x,y,fdx,fdy,col]),
##   move each independently (door+dest via _bcan; flip-on-arrival). Grid can't show overlaps -> can't read from grid.
##   Overlap DISPLAY: box with highest-priority FACING shows on top, priority E>N>W>S. Backtest lvl1-4 green (only HUD-minority).
##   Box positions depend ONLY on hop-count (blocked moves don't advance boxes). Offline-BFS over (player,hopN).
##   OFFLINE SOLUTION (29 steps) from entry (14,0): [3,3,3,4,3,3,3,3,3,2,1,2,1,2,1,2,1,2,2,2,4,2,2,4,4,4,1,1,3]
##   (shuffles (0,0)<->(0,2) to time the patrols, then down-around to goal(6,6)). Live state is OLD-format ->
##   COMMIT [0(RESET)]+plan: RESET re-inits clean state at entry. Chains until HUD-minority halt -> re-commit tail.
## BASE_BY_LEVEL HUD majority: {0:1,1:1,2:2,3:3,4:1}. Per NEW level, probe 1st move's HUD delta -> set its base entry.
## LEVEL 3 (9x9): P(0,8) G(0,2). Boxes: color-8 South@(2,0) [kill (2,2)], color-12(c) South@(6,2) [kill (6,4)].
##   NEW color-12 box - mechanic maybe differs from color-8; VERIFY on interaction. Both kill zones on path.
## HUD *** base = max(1, CURRENT_LEVEL) *** (lvl0/1 majority+1, lvl2 majority+2, lvl3 +3). Modeled via CURRENT_LEVEL global.
## Minority of moves differ by +-1 (unpredictable) -> those halt (harmless). Backtest: only minority-HUD mismatches.
## *** COLOR-12 box = MOVING ENEMY *** advances 1 ROOM per player-turn in its FACING dir (S=down).
##   Trajectory observed: (6,2)->(6,4)->(6,6) down column 6 (facing stays S). color-8 box is STATIC.
##   TODO model: each turn move every color-12 box 1 room in facing dir. Boundary behavior UNKNOWN (box near (6,8)) - observe.
##   Death: likely collision (box lands on player / player onto box). color-12 kill-on-contact TBD.
##   SOLUTION = timing puzzle: ascend to top avoiding the patrolling box. Box already passed (6,4),(6,2),(6,0) going down,
##     so those are clear ABOVE the box now. Route idea: up column 8 (8,8)-(8,6)-(8,4)->(6,4)->up column 6 while box is below.
##   But column 8 entry = (6,8) which box passes -> TIMING. Need boundary behavior. Player stuck in row 8 (col4 has no up).
##   MODELED color-12 moving box in world_model_v5.py. Boundary=stay (PROVISIONAL). Current: player(4,8), box(6,6).
##   OBSERVING boundary: commit blocked up-moves [1,1,1] at (4,8) (up blocked there) -> box goes (6,6)->(6,8)->boundary?.
##   box moves ONLY on successful HOP (blocked move = box stays). Modeled. BFS w/ boundary=STAY = NO solution (box blocks (6,8)).
##   => boundary must BOUNCE. Set model to BOUNCE (reverse facing at wall/oob). BFS(bounce)=15-step sol:
##   [3,3,4,4,4,4,1,1,3,1,1,3,3,2,3] from (4,8). Uses col8 to get above box, dodges oscillation, destroys color-8 b8S, ->goal.
##   *** CORRECT c12 rule (backtest-green): box moves forward 1 room in facing dir on each HOP; on ARRIVAL, if the
##   onward cell (same dir) is wall/oob, FLIP facing (so next hop it patrols back). 'f' pixel shows new facing.
##   So box oscillates (6,0)<->(6,8) flipping at the ends. NOT a same-turn bounce. Modeled in world_model_v5.py.
##   BFS(correct) = 14-step sol from (2,8): [3,4,4,4,4,1,1,3,1,1,3,3,2,3]. Up col8 to (8,4)->W(6,4)->up col6 (box away)->
##   (6,0)->W to destroy color-8 b8S(2,0)->D(2,2)->W goal(0,2). Timing dodges the patrol. COMMITTED.
##   Observing boundary via [3,4] (box (6,6)->(6,8)->boundary?). If box STAYS at (6,8) -> level unsolvable (blocks col6&col8 entry)
##   => box must reverse/wrap/vanish. Update _find_boxes movement + re-BFS once boundary known.
##   BFS state includes box positions (deterministic move) -> handles timing. Use run_bfs after boundary confirmed.

## BOX / ENEMY mechanic (CONFIRMED, modeled in world_model_v5.py, backtest green thru lvl 1)
- A BOX = 3x3 color 8 with one 15('f') pixel; its local pos = FACING dir (W=(1,0),E=(1,2),N=(0,1),S=(2,1) local).
- KILL ZONE = the room 2 cells (1 room) in the facing dir (box+2*dir). Hopping INTO that room = DEATH (box lunges).
- Hopping onto the box's OWN cell from any non-kill side = SAFE and DESTROYS the box (vanishes -> corridor).
  (lvl1: box (8,2) faced W, kill=(6,2); entered (8,2) from south -> box gone -> passed to goal.)
- Multi-box puzzles: destroying a box removes its kill zone -> can chain (destroy A to unblock entering B).
  Model reads boxes from grid each step so destruction threads correctly. Offline+run_bfs agree.
- SOLVE: BFS over (player, alive-boxes); avoid kill zones; pass thru box cells to destroy.

## LEVEL 2 (13x9) — 3 boxes, SOLVED plan committed
- P(10,8) G(4,8). Boxes BE(4,2),BS(6,2),BE(0,6). Kill zones (6,2),(6,4),(2,6). Path needs (6,4),(2,6) cleared.
- 19-move plan (run_bfs==offline): [1,1,4,1,3,3,1,3,3,2,4,2,3,3,3,2,4,2,4]. Destroys BE(4,2) from N, then BS(6,2) from W(now safe), then BE(0,6) from N. counter maxes 24 (+2 at {1,6,10,15,20} only).

## LEVEL 1 (13x5 non-square maze) — SOLVED. box object
- origin px (12,21). Player start (0,4) [sprite '4' faces UP now]. Goal G at (12,0).
- BOX at logical (8,2): 3x3 color 8 with a single 15('f') pixel at local(1,0)=left. Sits in row-2 corridor.
- Box is ON THE ONLY PATH to goal: goal side {(10,2),(11,2),(12,2),(12,1),(12,0)} reachable ONLY via (8,2).
- *** BOX IS A CHASER/ENEMY (deadly on contact) ***. Entering its cell or it moving onto you = DEATH -> auto-RESET to entry.
- Observed: box static at (8,2) while player 3-4 rooms away (at (0,2),(2,2)). When player reached (4,2) [dist 2 rooms]
  and hopped E toward (6,2), the box moved (8,2)->(6,2) [1 room WEST toward player] and they collided at (6,2) -> DEATH.
  So box moves ~1 room toward player when player is within ~2 rooms. 'f'(15) pixel = facing/move direction (was left=west).
- Chokepoint: box guards (8,2), the ONLY link to goal side. MUST lure/dodge it. Need exact movement rule.
- DATA: box moves ONLY when player ends orthogonally ADJACENT to it (then lunges onto player=death).
  player at (4,2)[2 rooms,same row]: box static. player->(6,2)[adjacent]: box->(6,2) death. player->(4,4)[not adj]: box static.
  So NOT a roamer at range 2. Either pure adjacent-lunge (any dir) OR directional (faces west='f' local(1,0)).
  PROBLEM: goal needs passing (8,2)/(10,2) adjacent to box -> if pure adjacent-lunge, unsolvable => I'm missing something.
- CONFIRMED: box is WEST-FACING hazard. Player safely reached (8,4)=SOUTH of box, box did NOT react/kill. 'f' stays west.
  So ONLY the box's WEST neighbor (6,2) is deadly (box lunges onto you there). South/east/north approach = safe so far.
- Maze fully mapped (code): goal (12,0) reachable ONLY via box cell (8,2). Path must be ...->(8,2)->(10,2)->(12,2)->(12,0).
- KEY TEST: enter (8,2) from SOUTH: (8,4)->(8,2)->(10,2)->(12,2)->(12,0)[up]. Committing [1,4,4,1] from (8,4).
  If move1 (enter box cell) = DEATH -> can't pass through box cell; need to lure box off (8,2) somehow (hard: box only moves to (6,2) when player steps there=death). If move1 SAFE -> may SOLVE level (avoids deadly (6,2)).
- deaths are CHEAP (auto-reset to entry). Model treats box as walkable (may halt on box-render mismatch even if safe).

## Level 0 status  [SOLVED]
- Player at logical (4,8), counter=17. Committing remaining movement-correct plan [4,2,4,1,4,2] to goal(10,10).
  Sources: (4,8),(6,8),(6,10),(8,10),(8,8),(10,8). Halts at first +2 among these -> record it.
  Last move action2 D from (10,8)->(10,10) triggers level_up (goal). HUD << 64, never blocks winning.

## If commit halts early
- read_history brief for actual player pos + sprite + HUD zeros. Usual culprit: west HUD increment. Fix, backtest, bfs, recommit.
