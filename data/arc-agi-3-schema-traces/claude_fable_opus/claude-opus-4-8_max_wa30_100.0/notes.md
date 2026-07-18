# ARC3 — world model notes (levels 0-7 CLEARED; on level 8)

## Actions
1=UP 2=DOWN 3=LEFT 4=RIGHT 5=grab/release(/KILL agent) 0=RESET

## Rendering (4x4 px per cell; cell (cx,cy) = px (4cx,4cy))
BG=1. E body=14, head=0 on the FACING side.
Box = 9 inner + border: 4=normal, 3=E-faced, 0=E-carried, 5=CARRIER-carried.
D cell = 9 ring + 2 fill (a big D region is ONE ring; interior cells are all-2).
Solid-2 cell = the AGENT'S goal (passable floor for E).
STRIPE = 2s MIXED with 1s -> blocks E's BODY, but a CARRIED BOX PASSES THROUGH.
Solid-5 = wall. 12 = block. 15 = agent (11 ring + 15 inner when E faces it).
Row 63 = move-counter BAR: 7 empty / 4 filled. 64 filled => DEAD.

## Core mechanics (all encoded + backtested, 734+/803)
- E carries a box with the offset LOCKED to the facing at grab time. E cannot PUSH.
- Pressing into an obstacle TURNS E in place (free re-facing).
- Carried boxes pass STRIPE walls but NOT colour-5 walls. Through a 1-row gap, carry the box
  BESIDE E (horizontal grip), never trailing.
- BLOCKS (12) and AGENTS (15) are autonomous BFS carriers:
  * neighbour order L,R,U,D; they tick ONCE PER E ACTION (on EVERY action, incl. 5).
  * target = nearest box by **ACTUAL PATH (BFS) DISTANCE, not Manhattan** (tie-break y,x).
  * 1 tick to GRAB (adjacent), carry with locked offset, 1 tick to DROP. Idle if no target.
  * A block that DELIVERS stays put that tick.
  * BLOCK drops on an empty D cell. AGENT drops on its solid-2 goal (and steals off D!).
- **E's BODY IS AN OBSTACLE TO CARRIERS.** Delivered boxes wall off corridors -> keep E OUT of a
  block's delivery lane or it reroutes unpredictably.
- KILL AN AGENT: E EMPTY-HANDED + adjacent + FACING it + [5]. A DYING AGENT DROPS ITS BOX
  (else it stays 'bgrab' forever = orphan => is_goal can NEVER fire).
- WALL-FEEDING (lvl2/3): park a box IN a stripe cell; a block on the far side grabs and delivers.

## WIN (levels 0-7)
EVERY box sits on a D cell AND none is carried. NOT "every D cell covered".

## Bar rates  filled = (mult*n + off) // D
lvl0=1/3  lvl1=1/1  lvl2=2/3  lvl3=2/3  lvl4=1/2  lvl5=6/7  lvl6=1/2+off1  lvl7=3/7+off3(~148)
Unknown => (2,1,1) prior, _fit_bar() learns after 3 obs. Irregular SKIPS are absorbed by the
self-correcting `off` (one mispredict, then re-sync).
**A WRONG RATE CORRUPTS PLANNING, NOT JUST PREDICTION** — on lvl7 I believed the level was
"too tight" at 12/13 when my budget was ~20 actions short. PIN THE RATE OVER >=8 FRAMES
(through at least one SKIP) before trusting any near-limit plan.

## Planning recipe that works
- AMBUSH, DON'T CHASE: E and carriers move at the SAME speed, so pursuit never closes and greedy
  chasers LIVELOCK. Park E on a cell the agent must cross, FACING it, and wait. A* over the model
  finds these in seconds.
- RE-PLAN EVERY TICK: a precomputed multi-step plan desyncs the moment a block crosses E's path.
- KEEP AN ANTI-STUCK GUARD (repeat state -> force a different action) or E oscillates forever.
- Choose the cheapest (box, GRAB-SIDE, target-D) triple — the grab side matters a lot.
- To WAIT, press a direction INTO A WALL (E stays, carriers still tick).

## Discipline (learned the hard way on lvl7)
- A special case that fixes one level and regresses others is an EPICYCLE. Two confident
  block-logic "fixes" regressed lvl1-4 (709->681, ->675) and were reverted; the one real fix
  (path-distance targeting) RAISED the backtest 714->734. **The full backtest is the only
  discriminator — not conviction.**
- A RECURRING mispredict in one subsystem is a real bug, not noise. I dismissed the block
  divergences as "tie-breaks" for turns; they were the Manhattan-vs-path bug.
- run_python writes to world_model_v5.py do NOT reinstall the live model. Only write_file /
  edit_file recompile+install. Re-run run_backtest after any edit to confirm what is LIVE.

## LEVEL 8 (current)
E(8,8). AGENT(15,14) deep in a bottom MAZE — but it CAN escape (reaches all 186 cells) and its
goal2 is (2,8). IT MUST BE KILLED.
Blocks: (4,7) [E's region, will help] and (11,1) [TRAPPED in the sealed top-right region].
9 boxes: (1,5),(1,7),(1,8),(2,3),(2,7),(3,5),(11,5),(12,7),(14,8).
13 D cells: 3x3 at (5-7, 3-5) + (13,2),(14,2),(13,6),(14,6).
  -> (13,2),(14,2) are SEALED behind the row-3 STRIPE (cols 10-15) + the col-9 wall; E cannot
     reach them. But 9 boxes <= 11 reachable D cells (3x3 + (13,6),(14,6)), so they are NOT needed.
Walls: col 9 (rows 0-7); row-3 stripe (cols 10-15); colour-5 MAZE at rows 10-15.
Maze exits to the upper area: (0,10),(1,10),(3,10).
PLAN: pin the bar rate, AMBUSH the agent as it exits the maze, then deliver 9 boxes to the
3x3 D block + (13,6),(14,6), keeping E out of block(4,7)'s delivery lane.
