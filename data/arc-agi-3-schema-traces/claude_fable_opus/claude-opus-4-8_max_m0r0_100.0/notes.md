# Notes — living scratchpad

## LEVEL 5 (LAST) — S=4, phase (2,2), 15x15; bg 6/7; avatars (4,5) & (10,5), msum=14, axis bx=7
- COMBINES EVERYTHING: checkerboard hazards (walls), keys/gates (c=12, e=14), and a pilotable
  DOOR (9) at (7,10). Column bx=7 is solid hazard EXCEPT (7,10) — so the door occupies the ONLY
  link between the rooms, which is also the only square a mirrored pair (msum=14) can merge on.
- KEYS ARE CROSS-COUPLED: the c key (4,3) is in the LEFT room but opens the c gate on the RIGHT;
  the e key (10,3) is on the RIGHT but opens the e gate on the LEFT.
- !! CHECKERBOARD HAZARDS ARE **DEADLY**, NOT WALLS !! (finally settled, level 5)
  An avatar walked from (6,6) into the hazard at (7,6) and the level SOFT-RESET: the board snapped
  back to its entry layout while the ACTION COUNTER KEPT RUNNING (the bar did not reset). The game
  reports NO dead flag — it just resets. I had dodged hazards for five levels so wall-vs-deadly
  never fired, and my level-3 "they must block" reasoning was WRONG (the DOOR was the blocker).
  => in search, entering a hazard is FORBIDDEN, not a free "wait". That mistake killed a 35-move plan.
  => also CONFIRMED chir0=+1 on level 5 (A moved RIGHT from (6,6) into (7,6)).
- Gates do NOT crush: an avatar can sit inside a gate that closes and is unharmed (verified — the
  model matched reality through exactly that).
- !! THE PIVOTAL RULE: A PILOTED DOOR CAN DRIVE THROUGH A GATE THAT IS HELD OPEN !!
  Avatars FREEZE while you pilot, so park an avatar on a key to hold its gate open, then drive the
  door through it. Forbidding this made the level look UNSOLVABLE for BOTH chirality signs —
  a green backtest plus an impossible level always means MY MODEL, not the level.
- Solution (35 actions): pilot the door up to (4,4), directly BENEATH the c key (4,3). Now avatar
  A standing on that key is WALL-BLOCKED from below and cannot be dragged off the plate, so it
  HOLDS THE C GATE OPEN while its twin crosses. Merge at (5,8).
- The first 17 actions are IDENTICAL for both chirality signs (vertical moves + raw-direction door
  pilots), so the sign resolves itself mid-plan for free.

## LEVEL 4 (S=4, phase (2,2), 15x15; bg 6/7; avatars 10 at (1,12) & (13,12), msum=14, axis bx=7)
- THREE new colours, each appearing as BOTH a single filled 4x4 block AND a 3-block-wide BAND:
    f/15: singles (3,1), (3,12)      bands (10-12, 5) and (10-12, 9)
    e/14: single  (8,6)              band  (3-5, 5)
    c/12: single  (14,6)             band  (2-4, 9)
  (They are FULLY FILLED blocks, unlike L2/L3 doors which were floor + a centred core.)
- Rows by=5 and by=9 are COMPLETE BARRIERS; the coloured BANDS are their only gaps. The avatars
  start in the bottom strip (by=10..13); the axis (bx=7) is only open at by=1..4, so the merge
  must happen up top => the pair MUST get through both barrier rows.
- With everything treated as wall the level is UNSOLVABLE (backtest green, so it is a MISSING
  MECHANIC, not a bad model — same signal as level 2's doors).
- !! CONFIRMED: PRESSURE PLATES (not consumables) !!
    * an ISOLATED filled block = a KEY  -> a walkable PRESSURE PLATE.
    * a 3-block BAND = a GATE -> open ONLY WHILE an avatar STANDS on a key of the same colour.
      Step off and it SLAMS SHUT and the key reappears. Keys are NOT consumed.
  I first read it as "key consumed, gates permanently open" — WRONG. When A stepped off the f key
  the key came back and BOTH f gates re-closed.
  => ONE TWIN HOLDS THE BUTTON WHILE THE OTHER PASSES. That is the whole level. It works because
  the button-holder is WALL-BLOCKED so it cannot be dragged off the plate: A is blocked at (3,11)
  above the f key (3,12); B is blocked at (14,5) above the c key (14,6).
  Keys/gates come from ENTRY_GRID (they never move); "pressed" is derived from the live avatars,
  so NO state is needed. Classify STRUCTURALLY: group same-colour filled blocks by adjacency,
  size 1 = key, size > 1 = gate. (Doors = floor + centred core; hazards = checkerboards.)
- !! THE CHIRALITY SIGN IS PER-LEVEL AND NOT DEDUCIBLE FROM THE ENTRY GRID !!
  Levels 0-3: the LEFTMOST entry avatar moves WITH the key (+1). LEVEL 4 INVERTS IT — action 4
  sent the left avatar LEFT and the right avatar RIGHT (they moved APART). Both avatars are the
  same colour, so nothing in the grid says which is which: PROBE ONE HORIZONTAL MOVE on every new
  level before planning. (Encoded as chir0 in _analyse, keyed on CURRENT_LEVEL.)
  => on level 4, ACTION 3 moves the LEFT avatar RIGHT.

## LEVEL 3 (S=5, phase (4,4), 12x12; bg 11/15; hazards 8; door 9 at the centre (5,5))
- THE CLONE IS STILL A VERTICAL MIRROR. I guessed 180-deg point reflection because the avatars
  start on DIFFERENT rows and the maze is 121/121 perfectly 180-symmetric — BOTH RED HERRINGS.
  A vertical probe settled it in one action: A went UP and the clone went UP too.
- THE REAL NOVELTY: the pair starts VERTICALLY DESYNCED (by 2). No earlier level did that.
- Inside the rooms (by=2..8) there are NO vertical walls, so vertical moves shift both avatars
  equally and the desync is INVARIANT. The ONLY way to fix it is to make one avatar bump.
- !! THE DOOR IS THE TOOL, NOT JUST AN OBSTACLE !! Park it at (3,6), directly below avatar A;
  then DOWN twice blocks A while the clone keeps descending -> desync 2 -> 1 -> 0. Then both
  slide right and merge on the centre (5,5) — the one square a mirrored pair with msum=10 can meet.
- Colour 11 is BOTH the left-room BACKGROUND *and* the HELD-DOOR colour here (and AV_FROZEN is 1,
  same as L2). So do NOT exclude bg colours when detecting doors — the structural test (block =
  FLOOR + a centred (S-2)^2 core of one other colour) is already sufficient, and excluding bg
  blinded the model to the held door entirely.

## !! (superseded) THE SYMMETRY IS PER-LEVEL: MIRROR *or* 180-DEG POINT REFLECTION !!
- The clone's HORIZONTAL sense is ALWAYS opposite. Its VERTICAL sense depends on the level:
    * MIRROR (levels 0-2): avatars start on the SAME ROW -> clone moves (-dx, +dy)
    * 180-deg ROTATION (level 3): avatars start on DIFFERENT ROWS, as point images about the
      board centre -> clone moves (-dx, -dy)
- Detect from the entry rows (same row => mirror). Level 3's maze is 121/121 perfectly
  180-symmetric about (5,5); a vertical mirror only matches 128/144.
- The two differ ONLY vertically, so a HORIZONTAL probe can never tell them apart — the same trap
  that made me wrongly "rule out" mirroring back on level 0. Probe VERTICALLY.
- Level 3: the DOOR sits exactly ON the symmetry centre (5,5) = the only square two point-
  reflected avatars can ever meet. Move it aside, then walk in from both sides.
- Door core is (S-2)x(S-2) at offset 1 inside the block (2x2 when S=4, 3x3 when S=5).

## THE GAME: "you and your MIRROR CLONE" maze.  Backtest 8/8 green on level 0.
Board = lattice of SxS blocks (level 0: S=5, origin px (9,9), 10x10 maze).
Colour 5 = floor, the two bg colours (11 left room / 12 right room) = wall, 10 = avatar.

### 1. MIRROR (the core mechanic)
- TWO avatars, ONE key. Avatar B is the MIRROR IMAGE of A about a vertical axis:
  bx_A + bx_B = MSUM  (invariant while both move freely; level 0: MSUM=8, axis bx=4).
- VERTICAL moves are the SAME for both; HORIZONTAL moves are OPPOSITE.
- I wrongly ruled this out early: my first probe was ACTION1=UP, and a HORIZONTAL mirror leaves
  vertical motion untouched. VERTICAL EVIDENCE CAN NEVER DISTINGUISH mirrored from un-mirrored.
- => the merge can ONLY happen ON the axis. Merge square = the unique floor block of column
  bx=axis. Level 0: (4,0), dead centre of the top corridor — the one place the two rooms connect.

### 2. WALLS DESYNC
- An avatar that would enter a wall / leave the board DOES NOT MOVE while the other still does.
  That is the ONLY way to break the mirror relation, and it is REQUIRED: the "both-walkable"
  intersection maze is disconnected (A must squeeze through bx=1 where its mirror bx=7 is wall).

### 3. THE BAR = (32n+37)//75 ~= round(64*n/150). A 64-px bar over a ~150-ACTION level budget.
- Fitted to EVERY transition of levels 0-2 (backtest 83/83). n resets each level. EVERY action
  counts, including ACTION5 and no-op clicks.
- LESSON: 3/7 was very slightly too fast and only broke at n=41 (said 18, truth 17). Then
  (5n+6)//12 fitted the 21 turn-BOUNDARY samples perfectly and still failed 11 transitions —
  FIT AGAINST EVERY ACTION, not just the frames lying around in events.jsonl. The backtest is
  the only honest judge.

### 3-OLD (superseded) THE BAR = floor(3*(n+1)/7)
- Depends ONLY on n (actions taken). BUMPS DO NOT AFFECT IT — every linear fit over
  (both-moved steps, bump steps) collapsed to a function of n alone.
- 3 px per 7 actions; tick gaps run 2,2,3 repeating. The rate is just UNDER 1/2, which is
  exactly why floor(n/2) fitted n<=7 and then drifted.
- Colour 0; row 0 fills right->left, row 63 left->right; both rows always show the SAME value.
- Must reproduce (n=0..11): bar = 0,0,1,1,2,2,3,3,3,4,4,5
- OPEN: the rate is only bounded to 0.4 < r < 0.5. 3/7 and 4/9 both fit all data so far and
  first DIVERGE at n=15 (3/7 -> bar 6, 4/9 -> bar 7). If a plan dies exactly at n=15, switch to
  (4n+3)//9 and re-plan. Everything else is unaffected.
- RULED OUT — verified counterexamples, DO NOT REVISIT:
  * bump counter alone: n=4 bumped NOBODY yet ticked; n=3 DID bump yet did not tick.
  * |dy| / any mirror-desync function: n=3 and n=4 share desync (-1,+1) but bar 1 vs 2.
  * floor(n/2): fits n<=7 then FAILS at n=8. (n+bumps+2)//4: fits n<=10 then FAILS at n=11.
  * ANY per-step event rule ("both moved" ticked at n=4 but not n=1/n=7).
  * ANY state function g(A,B) (n=5,n=6 share dA=8 but bar 2 vs 3).
- Pure HUD: never affects the avatars, does not gate the goal.

## Action semantics (all CONFIRMED by executed moves)
- ACTION1 = UP. ACTION3 = LEFT (for A) / right for B. ACTION4 = RIGHT (for A) / left for B.
- ACTION2 = assumed DOWN (never needed yet). ACTION5 / ACTION6 = never probed.

## !! CHIRALITY IS A FIXED IDENTITY — CARRY IT IN STATE, NEVER DERIVE IT FROM POSITION !!
- The avatars CAN CROSS each other. Both are the same colour, so a swap is INVISIBLE in the grid.
- A "leftmost avatar = un-mirrored" rule silently INVERTS after a crossing. Worse, it stays
  hidden: vertical moves are unaffected by chirality, so the model keeps matching until the
  next HORIZONTAL move, which then goes the WRONG WAY. (Level 1: crossed at step 21 while the
  pair was stacked in the same column bx=6; the error only surfaced at step 23, and the plan
  pushed them APART instead of merging.)
- FIX (in world_model_v5.py): state carries A and B positions; each predict() re-anchors the
  labels onto the real grid blobs by NEAREST NEIGHBOUR to their last known positions. This keeps
  A=+1 / B=-1 straight across crossings AND self-heals the level-0 one-step state lag.
- The leftmost avatar AT LEVEL ENTRY is the un-mirrored one (+1). Confirmed on levels 0 and 1.

## FRAMEWORK GOTCHA — the run's FIRST-EVER transition never advances state
- tools.py:954 AND agent.py:468 both `continue` before `state = next_state` when before is None
  (i==0). So a predict() state starts ONE action behind on the level containing that step.
- Handled: init_state seeds n=1, bumps=0 on level 0 (that skipped step was action 1 with BOTH
  avatars moving, so bumps=0 is exact). CAVEAT: if level 0 is ever RESET, change the seed to n=0.
- POSITIONS are read from the GRID every call (ground truth), never carried in state.
- Chirality = left/right order about the axis (leftmost avatar = un-mirrored). Only breaks if the
  avatars CROSS the axis; they converge to the axis and merge, so a normal solution never does.
  VERIFY any plan is crossing-free (I did, in run_python).

## Model design (world_model_v5.py) — everything derived from ENTRY_GRID, nothing hard-coded
- token colour = rarest non-floor colour; block size S + lattice phase from a token blob's bbox;
  block = FLOOR iff uniformly floor(5) or uniformly token, else WALL (so the decorative all-5
  border rows land in MIXED blocks = wall and can't be walked on); axis = midpoint of the two
  entry avatars; has_bar = top+bottom rows uniformly floor at entry.

## LEVEL 1 (S=4, phase (2,2), 15x15 blocks; bg 6/15, avatars 10, NEW colour 8)
- NEW BLOCK TYPE "X": a CHECKERBOARD of floor+8 inside a 4x4 block. Detected generically as
  "block contains a colour that is not floor / avatar / a room-background colour".
  Modelled as DEADLY (conservative — its true nature is UNPROBED: could be wall, death or floor).
- Map (A=(5,2),B=(9,2), MSUM=14):
```
   012345678901234
 0 ###############
 1 #......#......#
 2 #....A.#.A....#
 3 #......#......#
 4 #..#########..#
 5 #..#.#######..#
 6 #.....X#......#
 7 #.....X#......#
 8 #.....X#......#
 9 #XXX.XX#.XXXXX#   <- crux: left gap bx=4, right gap bx=8; their mirrors (10 and 6) are X
10 #......#......#
11 #.............#   <- the two rooms join here
12 #.............#
13 #XXXXXXXXXXXXX#
14 ###############
```
- The pair CANNOT cross by=9 while mirror-synced; they must first desync to bx_A=4, bx_B=8.
- The 23-move plan NEVER TOUCHES AN X, so it is valid whether X is wall, death, or floor.

## KEY CORRECTION — the merge square is NOT always the axis
- Merging needs bx_A == bx_B, i.e. sum = 2*bx_A. It needs sum == MSUM only when the pair is
  PERFECTLY SYNCED. Level 1 merges at (6,11) with sum=12 (they stay desynced from the by=9 crossing).

## LEVEL 2 (S=4, phase (2,2), 15x15; bg 15/8, avatars 10, NEW colour 9 = 2x2 "dot")
- COLOUR ROLES ARE PER-LEVEL. Colour 8 was the level-1 HAZARD but is a room BACKGROUND here.
  => backgrounds are read from the FRAME ROWS (row 1 / row H-2), never hard-coded.
- "rarest non-floor colour = avatar" WAS WRONG and would have hijacked detection: the dots (9)
  have only 12 px vs the avatars' 32. Avatar is now = the non-floor/non-bg colour forming the
  LARGEST SOLID SQUARES (avatars fill a whole SxS block; dots are a 2x2 centred in a floor block).
- 3 dots at (7,3), (2,4), (9,7). Column bx=7 is wall EVERYWHERE except by=3 — and that one
  passage IS a dot — so every solution must walk over (7,3); dots are therefore WALKABLE.
- The 31-move merge path steps on ALL THREE dots, so it works whether the goal is "merge" or
  "collect all dots then merge". Merge lands at (5,6).
- !! DOTS ARE DOORS: THEY BLOCK !! Confirmed: B at (10,7) tried to enter the dot (9,7) and did
  NOT move. So dots are NOT walkable markers.
- CONSEQUENCE: with dots shut, column bx=7 is wall at EVERY row (the sole passage (7,3) IS a
  dot), so the two rooms are DISCONNECTED and the merge is IMPOSSIBLE with actions 1-4 alone.
  => there MUST be an open/toggle mechanic.
- ACTION5 PROBED (level 2, with B standing adjacent to the door at (9,7)): it is INERT — avatars
  unchanged, doors unchanged — but it DOES count as an action (the HUD bar ticked 3->4). So
  ACTION5 is not the door mechanic. Modelled as "n increments, nothing else".
- !! ACTION6 = CLICK A DOOR. Confirmed: clicking door (7,3) flipped THAT door 9 -> 11 AND flipped
  BOTH AVATARS 10 -> 1. Positions unchanged. Other doors untouched. This is a POLARITY system and
  is why ACTION5/6 exist at all.
- => THE AVATAR COLOUR IS NOT CONSTANT. Never look avatars up by the entry colour. Find them
  structurally: the only colour whose lattice blocks are completely FILLED SxS (a door is just a
  2x2 core inside a floor block). Model does this now.
- Door pixel geometry: block (bx,by) spans px x=2+4bx..5+4bx, y=2+4by..5+4by; the 2x2 core is the
  centre. Doors: (7,3)->px(31,15); (2,4)->px(11,19); (9,7)->px(39,31).
- !! CLICK = "SELECT WHAT YOU CONTROL", *NOT* A TOGGLE:
    * click an IDLE door (9) -> you pilot it (->11); all other doors go idle; avatars FREEZE (->1)
    * click the HELD door (11) -> it is ALREADY selected => NO-OP (it still burns an action)
    * click an AVATAR -> the avatars WAKE (->10) and every door goes idle (->9)
  Confirmed: clicking the held door at (3,2) changed nothing at all.
- !! THE DOORS ARE PUSHABLE BLOCKS YOU PILOT. Clicking one does NOT open it — it TAKES CONTROL:
  that door goes 9 -> 11 (held) and BOTH AVATARS FREEZE (10 -> 1). While it is held the direction
  keys move THAT DOOR one block in the RAW direction (no mirroring) and the avatars do not move.
  Click again to put it down. Confirmed: action 4 moved the held door (7,3) -> (8,3), avatars
  stayed at (5,10)/(10,7).
- => DOORS MOVE, so locate them in the CURRENT grid every step. Looking them up at their ENTRY
  blocks silently loses them the instant one is pushed.
- => and scope door colours per level: colour 11 is a room BACKGROUND on level 0, so scanning for
  it there invented doors everywhere (caught as a 36/53 regression).
- LEVEL 2 IS SOKOBAN. Both other doors sit on FORCED chokepoints: A can only climb the 1-wide
  column bx=2 through (2,4); B can only reach the upper corridor through (9,7). All three doors
  must be relocated to dead-ends — (3,2), (1,8), (10,4) — and only then can the pair merge.

## BFS PERFORMANCE TRAP (world.py:136)
- BFS keys nodes on grid-bytes + repr(state). ANY state field that changes every step (action
  counter, bump tally) makes every key unique => nothing dedupes => exhaustive PATH search =>
  timeout. Dropped `bumps`. `n` is unavoidable (the HUD bar needs it) and still forks nodes
  across depths, so for LONG searches use a scratchpad BFS over block coords (fast: level 2's
  whole joint space is only 1618 states) and commit that plan; the model still validates it
  step-by-step via the auto-check.
- Also: _tokens() must scan only the avatar's pixels, not every block (225 numpy slices/call).

## NEXT LEVEL checklist
- Re-derive the block map (run_python over events.jsonl), run_backtest over ALL levels
  (a regression on level 0 = an edit broke a confirmed mechanic), then run_bfs.
- Watch for NEW motifs: >2 avatars, a different symmetry (rotation / point reflection rather than
  mirror), extra colours, ACTION5/6 becoming relevant.
