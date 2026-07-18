# Notes — living scratchpad

## CONFIRMED GAME RULES (all encoded in world_model_v5.py, backtest green)
- Balloon puzzle: char (9-body/11-eye, 5x5 box sprite) moves LEFT(3)/RIGHT(4) one 6px tile;
  faces move dir; then AUTO-RISES tile-by-tile while the 5x5 tile above is fully open 'a'(10).
- Click (6) on an 'e'(14) tile POPS it from ANY distance: 5x5 -> 'a'; adjacent 1px gap cells melt
  iff both across-gap neighbors open (t/b/l/r; corners no).
- ORANGE(7) cradle tile (char silhouette): moving/rising INTO it = LEVEL UP (encoded in predict info).
- Camera: vertical scroll pins char box top at VIEW ROW 37 (offset = char_world_row-37). Horizontal: none seen yet.
- HUD row63: +1 'f' per action (any action incl. no-op clicks). Budget/limit unknown; L0 used 19/64.
- World bigger than view; unknown rows revealed on scroll -> ingest + seed per-level TOP constants (keyed CURRENT_LEVEL).
- Tile lattice: origins ≡1 mod 6 (rows/cols 1,7,13,...); movement checks only 5x5 tile interiors (gaps cosmetic;
  unmelted-gap blocking untested — design melts gaps along intended paths).
- DEATH: coming to REST with a PILLAR/SPIKE tile directly above (tile contains any 'f'=15 cell) POPS
  the balloon => GAME_OVER + auto-available RESET. Pillars = white fff columns w/ 'b0b' bottom row.
  (encoded in predict: info.dead) — RESET refunds the HUD counter (row63 back to all-0).
- Action 7: STILL UNTESTED. Click on non-'e' cells: no-op.
- 9 levels total. RESET(0) restarts current level.

## CONFIRMED: cyan 'c'(12) tiles TOGGLE on click: full 5x5 block <-> small X pinwheel (center 3x3, 5 c-cells).
Shrink melts adjacent gaps (both-neighbors-open rule); expand RE-CLOSES its non-corner gap ring.
Pinwheel tiles are ENTERABLE (move or rise through); entering CONSUMES the X (cells->'a').

## NEW MECHANIC (L3): color-8 tile = GRAVITY FLIPPER. Click it (remote ok) → global gravity toggles:
char FALLS instead of rises. Camera anchor: view row 37 floating / 27 sinking. Sink sprite adds knot
'555' in gap row above its tile. Death rule symmetric: f-tile in gravity direction kills. 7=no-op.
World extends BELOW row 62 (revealed when sinking): 'e' row at (67,{31,37,43,49}), rooms to 84+.

## Current level (L3): grav=SINK now, char at (49,37). 8-tile at (-5,31) (can re-click when visible to
re-float). Route down: left to col19, fall thru popped col (55,19) → (79,19). Then explore below.
Popped: (55,13),(55,19). Pillar cols 13/19 at rows 37-41 above; staircase & top room explored (no exit).

## OLD L2 notes: PINWHEELS STAY when char passes (hidden under sprite, reappear). char at (13,37).
DANGER: pillars at (-5,{19,25,31,37}) above the band; pinwheel cols (7,{19,25,31}) = auto-rise death funnels!
PLAN: expand pinwheels to FULL (seal funnels): clicks (33,33),(27,33),(21,33); walk left 4x to (13,13);
auto-rise col13 chain to (-17,13) (overshoots band, safe, big reveal to world -54).
Then: right channel cols 42-53 goes up (world -24..+); c-tiles at (-23,31),(-23,37); watch unknown (-29,*).
Toggle-to-full = seal enterable columns; toggle-to-pin = open them. Gap ring closes on expand.

## OLD L1 notes — SAFE ROUTE (after death at (-29,37) under pillar):
shaft col37 up to (-11,37); remote-pop (-11,31/25/19/13)+(-17,13); walk left to (-11,13) -> auto-rise
to (-35,13); walk right to (-35,31); pop (-41,31), pop (-47,31) -> rise to (-59,31). Then reveal > -66.
Left room (7..23) pillars sit above ALL its entry cols (13,19,25) = trap, never rise into it.
Top room (-59..-49): pillar at cols 50-52 (tile (-59,49)); 'e' row above at (-65,{13,19,25}).

## L1 layout (entry world coords = view coords, offset 0)
- Char starts (37,19) facing R, in big bottom room rows 37-62, cols 13-53.
- TWO stacked 'e' rows spanning cols 13-53 (tiles at 13,19,25,31,37,43,49): rows 25-29 and 31-35.
- Left room rows 13-23, cols 13-29 with THREE white pillars (f=15) cols 14-16,20-22,26-28 rows 7-11,
  each bottom row 'b0b' (11,0,11); thin 1px 'a' slits at cols 18,24 rows 7-12. Purpose UNKNOWN.
- Right shaft 'a' cols 37-53, rows 0-23 -> reaches top edge; world continues above (unknown).
- PLAN: walk right to col 37, pop (31,37) then (25,37), rise up shaft -> reveal above (expect mispredict on reveal).
- Cradle location: not visible yet, probably above.

## Hypotheses to test
- Pillars: dangers? pushables? balloons to free? (they have eye-colored 'b' cells)
- Action 7 semantics.
- What happens when HUD row63 fills (64 actions)?

## History landmarks
- L0 cleared at t18 by docking into cradle (-59,19) after 4 pops. Snapshot: snapshots/ has L0-clearing model.


## L6 WINNING PLAN (committed; map complete in world_map_L6.txt, rows -84..84)
Breakthrough: death frame aligns at offset -84 -> ATTIC region rows -53..-25 (pinwheel stack col 43,
pillar (-53,55) b0b-bot, open cols 43-59 rows -41..-31, (-35/-41,49) rest shelf, col-55 open TOP-TO-BOTTOM
from -47 down to chamber floor (79,55)). Col 1 = GRAV TOWER: '8' tile every 6 rows from -47..79, each 1-use,
click any visible one to flip. Trick: expand pin->full to create rest ceilings/floors that prevent pillar deaths.
Route: (49,37)sink: expand(37,37), flip -> (43,37); R,R -> (13,49); L,L,L,L -> (1,25); flip -> (25,25);
restore(37,37); expand(7,25); flip -> (13,25); L,L -> (-29,13); R -> (-29,19); flip -> (-11,19); R -> (-11,25);
expand(-23,25); flip -> (-17,25); shrink(7,25); shrink(-17,31); R -> (-29,31); restore(-17,31); flip -> (-23,31);
shrink(-23,37); R -> (-11,37); restore(-23,37); flip -> (-17,37); R -> rise pin stack -> (-53,43); expand(-35,43);
flip -> (-41,43); R -> (-35,49); R -> PLUNGE col55 -> (79,55); L,L -> (79,43); flip -> (61,43); L,L,L,L -> (61,19);
flip -> falls (67,19) -> CRADLE (73,19) WIN.
Grav tiles used in order: (25,1),(1,1),(7,1),(-29,1),(-11,1),(-41,1),(-17,1),(-35,1),(55,1),(31,1).
If queue halts early: re-derive offset (=char_row - 37 float / 27 sink), recompute click view coords (y=world_row-offset).
Backtest 236/236 green after seeding full map (LEVEL6_EXTRA rows -84..-1 & 63..84, '?' skipped by loader).


## L6 CLEARED (t~282). L7 (7/9) layout & status
Entry: char float (37,19). Spike ceiling: b0b-BOT pillars (7,c) c=7..43 (kills risers at (13,c)).
Full-'f' BLOCK (19,13) — NEW object, no b0b row (safety unknown, maybe safe solid).
Band rows 30-36 solid except cols 31-47 open -> tiles (31,31/37/43). Rows 13-29 + 37-54 open cols 7-59.
Right shaft cols 49-59 rows 0-12 open to unseen world above (row 0 open at cols 49-59); sealed below band (31,49/55 solid).
NO 8-grav, NO c, NO e tiles visible. All float rises from start band: blocked (cols 49/55) or lethal ((13,c) under pillars).
=> new mechanic needed. Probing: click f-block, click pillar, action 7, click empty. HUD L7 tick color unknown (first tick reveals; model guesses 15).

## L7 upper world (revealed): CRADLE at (-41,55)!
Pocket: (-41,49) open + cradle (-41,55); walled left (-41,43) solid, floor (-35,49/55) solid, above unseen.
Floaters can't descend => need GRAV TILE (unseen, above row -42) then sink col 49/55 into pocket.
C-WALL: 9 full-c blocks at (-23,7..55) — toggleable ceiling. Rows -17,-29 open wide (7-59). -35..-31 open only cols 7-41.
Row -41: open 7-37, solid 43, pocket 49+. Gap row -42: open 7-17,25-41 (=> no pillar bottoms at (-47,7..13),(-47,25..37)).
Route: c-door (-5,43)->pin, L,L rise col37 -> rest (-17,37) under c-wall; peek rows -54..-43; then toggle (-23,37) pin, rise -35/-41/beyond hunting grav tiles.


## L7 MASTER PLAN (after funnel death at t~300; funnel frame saved l7_funnel_frame.txt)
Funnel above expanse (D = death/trap row, D<=-101, exact TBD during climb):
 S1 row D+18: pillars cols 7,55; open 13-49. S2 D+12: pillars 13,49; open 19-43. S3 D+6: pillars 19,43; open 25-42.
 TRAP row D: open 25-41, pillars (D-6,25/31/37) b0b-bot. GRAV TILE embedded in solid at (D-30..D-26, col 31-35) — remote-click only.
KEY MECHANIC ASSUMPTIONS: splits spawn copies into OPEN neighbor tiles only (solid/pillar/block = no spawn); char tile = no spawn (UNTESTED — first elevator rung tests it).
ELEVATOR (up): char under block; split block above -> char auto-rises into vacated tile, new block 6 higher; char blocks down-spawn. Repeat.
SEQUENCE:
 A. Rebuild (proven): split (19,13)@(15,21); (19,19)@(21,21); (19,25)@(27,21); (19,31)@(33,21); (19,37)@(39,21); R x5 -> (-5,49); toggle (-5,43)@(45,39); L,L -> (-17,37); L,L,L -> (-17,19); toggle (-23,19)@(21,33) -> rise (-41,19). [17 acts]
 B. Prep: toggle c-door (-47,49) to pin @(51,33) [offset -78].
 C. Elevator col 19: split (-47,19)@(21,33)... then each rung: click block 6 above char (view y = blockcenter - offset; offset = charrow-37). STOP when block reaches (D+12,19) (pillar above visible). Char ends (D+18,19).
 D. split (D+18,25) [rung debris]; R (char under (D+12,25)); split (D+12,25); split (D+6,25) -> char rises to perch (D+6,25) under (D,25). Each split: down=char(no-spawn), sides fine.
 E. GRAV CLICK from perch: grav center (D-28,33): view y=3, x=33 (offset D-31). FLIP -> sink.
 F. Fall col 25 -> rest (D+18,25) atop (D+24,25) rung-debris. Sink camera anchor 27 (offset=charrow-27)!
 G. Walk right with JIT clearing (each split's side into char tile = suppressed): split (D+18,31) [down-spawns floor (D+24,31)]; R; split (D+18,37); R; split (D+18,43); R; split (D+18,49); R -> char (D+18,49).
 H. Down-elevator col 49: split floor under char repeatedly: (D+24,49),(D+30,49)... down-spawn = next floor; sides harmless. LAST: split (-53,49): down-target (-47,49)=PIN no-spawn -> char falls THROUGH pin door -> rest (-41,49) in pocket.
 I. R -> CRADLE (-41,55) -> LEVEL UP.
Budget ~47 of 64 HUD ticks. Cradle pocket: (-41,49) open, (-41,55) cradle, walls: (-41,43) solid, (-35,49) solid, (-47,49)=c-door.


## L7 CLEARED (t~349). All mechanics inc. splits/elevator/melt-rules encoded & green.
Key L7 lessons now in model: split spawns skip char tile; melt strips: open next to open/pin/pillar-fff-side,
closed next to b0b-spike-edge/blocks/badge/c-full/grav; f-block elevator up & down (split block above/below char).

## L8 (8/9) entry: char (37,19) float. GRAV TILES (25,1),(37,1) embedded in left wall (remote-click).
F-block (13,37). Band rows 30-36 solid cols 6-30/48-59, open 31-47 (+left shaft 0-5).
Band rows 55-61 solid 6-63, open 0-5. Left shaft cols 0-5 fully open vertically but SEALED from interior.
Interior: rows 0-29 open cols 13-59; rows 37-54 open 13-59 (minus wall 6-12). World unseen above row 0 and below 63.
No cradle visible yet. Plan: sink-probe via grav (37,1) click (3,39) -> rest (49,19), reveal rows 64-85.
Then decide up-route (R,R rise col 31 through band -> rows <0, blind-rise risk) vs down.


## L8 MASTER PLAN (after softlock discovery; RESET + full route)
Map: interior cols 13-29 + chamber 37-47 (rows -47..-25) merge at rows -47..-43; chamber+chimney(col55) connect at rows -29..-25.
Pillars: b0b-bot (-59,13..43) cap the merged region (NEVER rest at -53 bare); b0b-bot (-11,31..55); b0b-top (-23,37..55) (never sink-rest above).
(-47,49): badge above (-53,49) AND below (-41,49) => flip-safe cell. Chimney col 55 open -59..-25 and continues above -60 (unseen).
SHAFT col 1: sealed horizontally everywhere; plugs = grav tiles (25,1),(37,1),(-23,1),(-47,1),(-59,1); pocket+cradle (67,13) at bottom; enter ONLY by falling in from above the top (rows <=-65, unseen).
PLAN: reset; yo-yo consume (25,1)@(3,27) [sink->(49,19)] then (37,1)@(3,17) [float->back (37,19)];
prep splits (13,37)@(39,15),(13,31)@(33,15); R,R (->25,31 under 19,31); L (->19,25 under 13,25);
elevator 11 rungs @(27,33) -> char (-47,25) under (-53,25) [NEVER split (-53,25)!];
crossing: split (-47,31) [makes (-53,31) ceiling], R, split (-47,37), R, split (-47,43), R, split (-47,49), R -> (-47,49)
 [down-spawns (-41,37),(-41,43) = sinker floor; side-spawn (-47,55) handled later];
flips at (-47,49): click (-23,1) [sink, stays], click (-47,1) [float, stays];
chimney: split (-47,55)-block, R, then chimney-elevator up col 55 (split block above) into unseen top;
at top: find col-1 crossing, click (-59,1) [flip->SINK] while above shaft -> fall to (67,1); R,R -> CRADLE -> WIN.
Flip parity: 5 grav clicks total, start float -> end sink. All seeds clean (entry-state).
