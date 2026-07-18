# Notes — ls20 (ARC-AGI-3), 8 levels (0..7)

## CONFIRMED MECHANICS (all encoded in world_model_v5.py; backtest green)
- AVATAR = the BLOCK: a rigid bw x bh sprite (L0: 5x5, 2 rows of colour 12 over 3 rows of colour 9).
  Found as the connected {9,12} component containing a 12.
- ACTIONS 1=UP 2=DOWN 3=LEFT 4=RIGHT. Each moves the block by exactly its OWN SIZE
  (one coarse cell). Move happens iff the whole destination footprint is walkable.
- WALKABLE = every colour EXCEPT VOID(4).  <-- 4 is the ONLY wall.
  (colour 5 = panel/box interior IS passable; the block drives right into the lock box.)
- COLOURS: 3 floor, 4 VOID(wall), 5 panel bg, 9 key-pattern & block body, 11 budget bar,
  12 block head, 0/1 rotator plus.
- ROTATOR = 3x3 plus of colours 0/1 centred in a coarse cell. PERMANENT (reappears when the
  block leaves). ENTERING it: HUD key pattern rotates 90° CW, and that move is FREE (no bar drain).
  Leaving costs 1 as normal.
  L0 plus colouring:  .0. / 100 / .1.   (0 at N,C,E ; 1 at W,S)
  STILL OPEN: is the direction set by the glyph colouring or by the entry direction (I entered
  moving DOWN)? Compare when a level has 2+ rotators / a differently-coloured plus.
- TWO 3x3 PATTERN PANELS = a connected {5,9} component containing 9s; its bbox INSET BY 2
  is the 3x3 pattern grid (cell size = (w-4)/3):
    * LOCK/KEYHOLE: the panel INSIDE the map. Its pattern is STATIC -> cache from ENTRY_GRID
      (the block covers it when inserted!). Its interior is exactly block-size + 1px margin.
    * HUD: the panel BELOW the map. Shows the CURRENT key; the rotator turns it.
- GOAL = drive the block fully INSIDE a keyhole panel bbox whose (pattern,colour) MATCHES the HUD
  key -> level_up.
- *** MULTIPLE KEYHOLES (confirmed L5, backtest green): a level can have SEVERAL on-floor panels,
  each a keyhole with its OWN (pattern,colour). The block can only ENTER (move fully inside) the
  one its current key MATCHES; moving fully into a NON-matching keyhole is REFUSED (shut, free
  no-op, glyphs don't move) — it acts like a wall. Model: M['locks'] = list; _which_lock(x0,y0)
  returns the keyhole the block would be fully inside; refuse/insert keyed on _matched(G,M,lk).
  L5 has TWO: (53,34,59,40) #.#/##./.## col8 [REACHABLE - THE REAL GOAL] and (53,49,59,55)
  #.#/..#/### col9 [DECOY: in a 3-cell pocket reachable ONLY through the col8 lock].
  *** WATCH: a non-matching keyhole BLOCKS the path. ***
- *** KEYHOLES ARE GATES (confirmed L5 #344, backtest green 340): entering a keyhole with a
  MATCHING key CONSUMES its panel -> it becomes plain FLOOR (a gate opens); the block passes
  through. level_up ONLY when the LAST remaining keyhole is opened (ALL consumed). L0-L4 had 1
  keyhole so entering it = all consumed = win. Model tracks state['opened'] (indices); _which_lock
  skips opened ones; bg_eff floors opened panels; is_goal = every keyhole panel consumed. ***
- L5 is a 2-GATE CHAIN: col8 gate (rows34-40, above) then col9 gate (rows49-55, in the pocket
  behind it). Open col8 first (key #.#/##./.## col8=rot2(C)), THEN change key to #.#/..#/### col9
  (=rot(B)) and open col9 (=WIN). Requires a mid-solve trek back to the glyphs (left side) to
  re-key. Glyphs: pinwheel (0,-4) MODE-B, plus (2,-2) MODE-A, setter (-2,-8) MODE-A.
- *** L5 FUEL: B=42 EXACT (1px/move). Full solve is ~80-100 moves (there-and-back re-key), so it
  needs ~2-3 RING refuels (rings at (-3,-9),(3,-9),(-3,-1); refill -> u=0). I RAN OUT last time
  (refueled once, then stranded at (3,-6) 1 move from death, rings unreachable). MUST route through
  rings: refuel to full RIGHT BEFORE each gate trip (each gate trip ~15-18 mv, fits in 42). BFS
  death-pruning routes through a ring if a phase would die, but small phases let u creep up
  unnoticed -> after each phase CHECK the bar px; when u>~25 insert a refuel phase (POS_GOAL a ring
  cell e.g. (9,5)/(39,5)/(9,45), +SUBGOAL to preserve key) before continuing. ***
- L5 CORRECTED GOAL: match the col8 lock #.#/##./.## and insert (block is right above it, coarse
  (6,-4)). From entry C/14: colour 14->8 = 1 pinwheel; pattern C->#.#/##./.##=rot2(C) = 2 plus hits.
  Plan: RESET, set key=(rot2(C)=((1,0,1),(1,1,0),(0,1,1)), 8), navigate to (6,-4), DOWN to insert.
- BUDGET BAR (colour 11, y61-62, 42 px wide): px = floor(42 * (B - used) / B), where B is that
  LEVEL'S MOVE BUDGET. EVERY action costs exactly 1 (including rotator entry and, assumed,
  blocked moves). B is a per-level constant: **L0 B=46, L1 B=21** (each pinned uniquely by
  brute-forcing B against all observed (used,px) pairs — see LEVEL_BUDGET in the model).
  *** There are NO free moves. *** L0 looked like it had one (the bar stalled at used=12 on the
  rotator) but that was pure DISPLAY ROUNDING (42*34/46 = 31.04 -> 31, same as used=11). I wasted
  several turns modelling that artifact as a "free rotator move" mechanic. Beware rounding.
  A ring refill resets used -> 0 (bar back to full).
  NEW LEVEL: B is unknown -> the first move mispredicts once. Then brute-force B from
  events.jsonl in run_python and add it to LEVEL_BUDGET. RESET refunds, so probing is cheap.
  FRAMEWORK QUIRK (tools.py:977): backtest skips the run's FIRST transition without advancing
  state, so a plain counter drifts -> predict() RESYNCS `u` against the observed bar each call.

## *** SETTER COMMUTES WITH ROTATION (confirmed L5 #501, backtest green): setter(rot^k X) =
## rot^k(next(X)). SETTER_CYCLE only lists the canonical A..F; _setter_apply() finds the rotation
## making pat canonical, advances (A->B->C->D->E->F->A), re-applies the rotation. So a setter hit on
## a ROTATED shape (e.g. rot(B)=#.#/..#/###) advances it (-> rot(C)=#.#/.##/##.). BEWARE: navigating
## a KEY past the setter's row cycles it! Avoid the setter (and plus/pinwheel) once the key is set. ***

## TILE GLYPHS (3x3, centred in a coarse cell, walkable, permanent, trigger on ENTRY)
- PLUS of colours 0/1  (.0./100/.1.)  -> rotate the HUD key 90° CW. Entering is FREE (0 bar).
  [CONFIRMED L0]  Only ONE rotation direction seen so far -> need 3x CW to get a CCW turn.
- LAUNCHER = a 1-px COLOUR-1 STRIP lying on a cell's outer EDGE, exactly block-length long
  (1 x bh on a side edge, or bw x 1 on a top/bottom edge). [CONFIRMED L2]
  ENTERING that cell fires the block AWAY from the strip, sliding cell-by-cell until BLOCKED —
  all as ONE action (one bar charge). L2: up into (0,-8) slid it right to (5,-8) (wall at cx=6);
  entering (9,-8) slides it all the way DOWN column 9 straight into the keyhole at (9,1).
  Detect by SHAPE (a line), never by colour alone — the rotator plus is also colours {0,1}.
  *** A SLIDE STOPS SHORT OF THE KEYHOLE *** — you cannot be flung into the lock; the slide halts
  on the cell before it and you must step in with a deliberate move. (L2: the column-9 chute
  stopped at (9,0), one short of the keyhole at (9,1), even with the key already matching.)
- RING of colour 11    (bbb/b3b/bbb)  -> REFILL the budget bar to FULL, then it is CONSUMED
  (one-shot fuel pickup). [CONFIRMED L1]  NOT a rotator — it left the HUD untouched.
  Colour 11 = the bar colour = the hint.
  * *** BAR MASK = SHAPE, NOT COLOUR-OFF-FLOOR (fixed on L6; was a latent bug) ***: the budget bar is
    the colour-11 component that is a LONG, SHORT horizontal strip (w>=10, h<=4). The old rule
    "(E==11) & ~floor" broke under FOG: a partially-revealed RING sitting BEHIND A WALL is off the
    reachable floor, so its pixels were taken for bar pixels and _draw_bar painted them over the map
    every step (L6 (50,6..8)). Identify UI elements by shape; never by "colour X in the wrong place".
  * A ring is ALIVE iff its colour-11 glyph is still drawn -> refill triggers on
    (current_grid[dest]==11).any(); on vacating, ring cells render as FLOOR, not bg.
  * The PLUS is NOT consumed (it reappears) and is re-enterable — 3x CW is how you get a CCW.
- FUEL ROUTING is the real puzzle from L1 on: plan WHICH ring you spend and WHEN. Spending a
  ring early (I burned ring1 on the way out) can strand you — BFS then has to RESET.

## *** THE KEY IS A (PATTERN, COLOUR) PAIR *** — the single biggest correction so far (L2)
- The keyhole opens only if the HUD key matches the lock in BOTH the 3x3 PATTERN **and** the COLOUR.
  L2 fooled me for several turns: the pattern matched exactly (#.#/#../###) but the key was
  colour 12 against a colour-9 lock, so the lock silently refused. I nearly invented a bogus
  "collect a token" mechanic to explain it. The real rule is just: colour must match too.
- A move into the keyhole with a NON-matching key is REFUSED: 0 cells change, bar does NOT drain.
- TILES that change the key (all 3x3, centred in a coarse cell, PERMANENT, cost 1 like any move):
    * PLUS {0,1}, 5 cells  -> rotate the key PATTERN 90° CW (colour unchanged)
    * PINWHEEL, 9 cells    -> advance the key COLOUR one step CW round its own arm wheel
      (arms N,E,S,W = g[0][1], g[1][2], g[2][1], g[1][0]; L2 wheel = [14,8,12,9], so 12 -> 9).
      Pattern unchanged.
- A BLOCKED/REFUSED move is a completely FREE no-op (no bar drain) — only real moves cost.

## PANELS ARE COLOUR-AGNOSTIC (learned on L2)
- The pattern "on" colour VARIES per panel: L0/L1 lock+hud used 9; L2 lock uses 9 but HUD uses 12.
  So a pattern cell is ON iff its colour != PANEL(5). Panel detection = a PANEL-coloured component
  whose bbox is a SQUARE of side 3*cell+4; the 3x3 pattern lives in the bbox inset by 2.
  _write_pat must write the panel's OWN 'on' colour (stored at parse time), not a constant 9.
- Glyphs are classified by COLOUR SET + SHAPE (not colour alone):
    {0,1} & 3x3 & 5 cells  -> CW rotator plus
    {11}  & 3x3 & 8 cells  -> refill ring
  Anything else -> unknown (kept INERT). Beware: L2 has colour-1 STRIPS (1x5 / 5x1) that would be
  misread as rotators if classified by colour alone.

## Level 0 — SOLVED (BFS: 1 step, action 1 = insert into keyhole)

## Level 1
- HUD starts ###/..#/#.# (carried from L0 end); LOCK = ###/#../#.# -> needs 1 CCW (or 3 CW).
- One PLUS at coarse (4,1); two RINGS at (-3,-5) and (2,2). Keyhole at (-3,0). Block starts (0,0).
  (coarse origin: x=29+5c, y=40+5r)
- BFS plan (17 steps) goes through the ring at (-3,-5) then straight down into the keyhole.

## MODEL BUGS FIXED (were latent, bit me on L1)
- HUD vs LOCK panel must be split by WALKABILITY (lock intersects the floor component, HUD does
  not) — NOT by a maxy row split: on L1 the map floor reaches y54 and overlaps the HUD's rows.
- Exclude the block's own footprint when scanning for {5,9} panels, else its 9-body is a "panel".
- Bar drain must be restricted to (ENTRY==11) & ~floor, else the in-map rings hijack the
  leftmost-11-column search and get erased.

## Level 4 (coarse origin x=49+5cx, y=40+5cy)  -- IN PROGRESS
- BLOCK (0,0). KEYHOLE (1,-7). SETTER (-6,-6). PINWHEEL (-4,-3). PLUS (-7,-1).
  RINGS (-1,-7), (-8,-6), (-7,+1).  8 launchers.
- HUD .#./##./.## colour 12 (5 on-cells); LOCK #.#/##./.## colour 8 (6 on-cells).
  Again 5 -> 6 on-cells => the SETTER is REQUIRED (rotation can't change the count).
  Colour 12 -> 8 = THREE pinwheel visits (wheel [14,8,12,9] CW: 12->9->14->8).
- AVOID the PLUS after the setter — it would rotate the pattern away from the lock's.
- L4 is the TEST of the setter hypothesis: it has BOTH a setter and a plus. If the setter really
  "sets pattern := lock pattern", the model predicts it exactly; if it's really a CYCLER, it will
  mispredict the moment the block steps on it.
## *** MOBILE KEY-GLYPHS — GENERAL MECHANIC (confirmed L4+L5, backtest green) ***
- Which glyphs are MOBILE is per-level: L4 = PLUS only; L5 = PLUS + PINWHEEL + SETTER (all three
  key-transformers). Rings/launchers are always STATIC. Model guard: plus mobile @lvl>=4,
  pinwheel/setter mobile @lvl>=5. (L0-L3 all static -> handled by the slide/cells loop.)
- Each mobile glyph moves ONE coarse cell per REAL block MOVE (bump/refuse => no move; a multi-cell
  launcher slide still moves it ONCE). It moves in 2D, NOT a flat horizontal patrol.
- *** 2D PATROL RULE (hard-won; unified L4+L5, backtest green):
    * INITIAL velocity = HORIZONTAL toward the FARTHER wall of the glyph's row free-segment
      (tie -> LEFT). vx0 = +1 if right wall farther else -1; vy0=0.
    * mir_x = 2*bx0 - x0 (reflection of the glyph start across the BLOCK'S START COLUMN cx=0).
      TWO MODES depending on whether the glyph sits ON that column:
      MODE A (mir != start): HORIZONTAL BOUNCE on its row [start, mir]. Each move: reverse vx if
        (at start heading -v0) OR (at mir heading +v0) OR (cell ahead is a WALL); else step vx.
        NEVER leaves its row. (L4 plus [-7,-5] wall-bounce; L5 setter [-2,2] reverses at mir +2
        though +3 free; L5 plus [-2,2] on row -2.)
      MODE B (mir == start, i.e. glyph on cx=0): 2D CW WALL-FOLLOW. Move straight; when the cell
        ahead is a WALL rotate velocity 90 CW ((vx,vy)->(-vy,vx)) until free. (L5 pinwheel: CW loop
        period 8 around [-1,1]x[-6,-4]: (0,-4)W(-1,-4)N(-1,-5)N(-1,-6)E(0,-6)E(1,-6)S(1,-5)S(1,-4)W back.)
      Track (x,y,vx,vy) per glyph. *** Verified vs ALL history 264/264 green. ***
- OCCLUSION: the block draws ON TOP of any glyph it shares a cell with (glyph hidden).
- TRANSFORM FIRES ON CONVERGENCE: iff block-final cell == glyph-new cell (they END together) the
  glyph applies its transform (plus->rot90CW pattern, pinwheel->colour+1 CW, setter->shape cycle).
  Static "step-onto" is just the degenerate 1-cell-patrol case of this.
- _block() must use SPRITE TEMPLATE MATCHING (mobile pinwheel reuses colour 12/9 and would fool a
  colour/component seed; a glyph under the block is occluded so the block reads clean).
- (was: THE PLUS IS MOBILE FROM L4 — now generalized above)
  RULE (confirmed, backtest green): the plus PATROLS one coarse cell per BLOCK MOVE, starting
  RIGHT, and BOUNCES between fixed bounds. It is NOT a chaser.
  *** THE PATROL BOUNDS ARE [its START cell, the farthest free cell to the RIGHT] ***
  The LEFT bound is its STARTING cell, NOT the corridor wall — at L4 it reversed at (-7,-1)
  even though (-8,-1) is perfectly walkable. Observed trajectory (period 4):
    (-7) -> (-6) -> (-5) -> (-6) -> (-7) -> (-6) -> ...   [wall at (-4,-1); (-8,-1) is FREE]
  It moves once per ACTION (a multi-cell launcher slide still moves it only once), and only when
  the block actually moves. Its rotator effect travels WITH it, so `rot` must be dynamic; the
  plus is erased from the static bg and redrawn each step. Track (pc, pd) in predict state.
  *** OCCLUSION (confirmed #247): the BLOCK draws ON TOP of the plus. *** When they share a cell
  the plus is HIDDEN under the block (draw plus first, stamp block over it).
  *** PLUS HIT = CONVERGENCE (confirmed #247, backtest green): the HUD rotates 90 CW iff, after
  BOTH move, block-new cell == plus-new cell (they END on the same cell). NOT "block steps onto
  the plus's OLD cell". Since the plus always moves when the block moves, you HIT it by timing the
  block to land where the plus is bouncing to. Both bounce off the right bound to the same cell,
  so from the wall a hit is easy to set up. Rotation is CW (np.rot90(pat,-1)); colour untouched.
- L4 ENDGAME STATE (after #247): HUD pattern = #.#/.##/##. colour 8; LOCK = #.#/##./.## colour 8.
  Colour already matches. Need EXACTLY ONE more plus hit (one more CW rot: #.#/.##/##. -> #.#/##./.##
  = LOCK), then drive fully into the keyhole (1,-7). Watch the fuel budget (B=21, refill rings).
- TACTIC: visit the SETTER **LAST** (after the pinwheel). The setter overwrites the pattern, so any
  accidental plus contact BEFORE it is harmless; only contact AFTER the setter would break the key.

## Level 3 (coarse origin x=54+5cx, y=5+5cy)  -- CLEARED
- BLOCK (0,0). KEYHOLE (-9,0). PINWHEEL (-4,+5). RINGS (-7,+2) and (-4,+9).
- 8 LAUNCHERS (colour-1 lines), now on INTERNAL edges too:
    (-2,+3) DOWN, (-4,+3) RIGHT, (-2,+4) LEFT, (-3,+4) UP,
    (-7,+6) DOWN, (-9,+6) RIGHT, (-6,+7) LEFT, (-2,+7) LEFT
  *** A SLIDE KEEPS ITS ORIGINAL DIRECTION *** — launchers it passes OVER do NOT redirect it.
  PROVED by necessity: with re-triggering, the pocket holding the pinwheel and the pattern glyph
  is UNREACHABLE and the level is unsolvable. (BFS finding no path => suspect the MODEL.)
  The launchers act like a pinball table: chained slides are how you reach the pockets.
- KEY: HUD = .#./##./.## colour 14 (5 on-cells).  LOCK = ###/..#/#.# colour 9 (6 on-cells).
  * COLOUR: 14 -> 8 -> 12 -> 9 = THREE pinwheel visits (wheel [14,8,12,9], CW).
  * PATTERN: 5 on-cells vs 6 on-cells -> **ROTATION ALONE IS MATHEMATICALLY IMPOSSIBLE**.
    Something must change the pattern's SHAPE.
- PATTERN GLYPH: 3x3, 4 cells, all colour 0, shape #../.##/.#.  (TWO pieces under 4-connectivity
  -> glyph components MUST use 8-CONNECTIVITY.) It changes the key's PATTERN (colour untouched);
  it is the only tile that can change the pattern's CELL COUNT.
  *** IT IS A CYCLER *** (my "set := LOCK pattern" reading was wrong — on L3 the lock happened to
  BE ###/..#/#.#, so a cycling output masqueraded as "copy the lock").
  CYCLE / SHAPE LIBRARY (each ENTRY advances one step; colour untouched; 2 moves to step off+on):
     A .#./##./.##  (5)
     B ###/..#/#.#  (6)
     C ##./.##/#.#  (6)   <-- L4: this is the LOCK rotated 180° => C + 2 plus hits = win
     D .#./.#./###  (5)
     E #.#/#.#/###  (7)
     F .##/#.#/.#.  (5)
     -> next ???  (if it returns to A the period is 6)
  Rotations preserve cell COUNT, so a 5-cell shape can NEVER reach a 6-cell lock — only the
  cycler can change the count. That prunes the search hard.
  LESSON: two observations with the SAME input tell you nothing about a transform. Vary the input.
  To re-enter the glyph, step OFF and back ON = 2 moves per cycle step.

## Level 2 (coarse origin x=9+5cx, y=45+5cy)
- BLOCK (0,0). KEYHOLE insert cell (9,1). PLUS/CW (8,-7). RINGS (5,-6) and (2,-3).
- HUD ###/..#/#.# (colour 12) vs LOCK #.#/#../### (colour 9) -> needs **2 CW** (=180°).
- SOLVED: the pinwheel is the COLOUR CYCLER (see the KEY = (PATTERN, COLOUR) rule above).
- B = 21 (well, in {21,22}; 21 is conservative and backtests green).

## Level 5 (coarse origin x=24+5cx, y=50+5cy)  -- SOLVED (2-gate chain)
- BLOCK (0,0) 5x5. LOCK bbox px(53,49,59,55) ~coarse (6,0): pattern #.#/..#/### colour 9.
  HUD ##./.##/#.# colour 14  == shape C.
- GLYPHS: PINWHEEL (0,-4) wheel[14,8,12,9]; SETTER (-2,-8) shape #../.##/.#. (same cycler as L3);
  PLUS (2,-2) (model treats mobile, patrol cols34-39 = coarse cx 2..3 on row -2 — VERIFY mobility!);
  RINGS (-3,-9),(3,-9),(-3,-1); 2 launchers (5,-10)DOWN, (5,-7)LEFT. bar0=42, B UNKNOWN.
- COLOUR: 14->8->12->9 = 3 pinwheel visits (CW).
- PATTERN: C -> LOCK. LOCK = shape B rotated 90 CW (rot270CW(LOCK)=B is the only canonical rot).
  So: SETTER C->D->E->F->A->B (5 visits, one-directional cycle) THEN 1 PLUS rotation (B->LOCK).
  => AVOID the plus until the pattern is exactly B; hit the plus LAST. Setter must run on canonical
  shapes only (SETTER_CYCLE has no entry for rotated shapes -> no-op).
- Block can go UP 2 (to row40) then wall at rows35-39; DOWN blocked; L/R free. Needs BFS routing.
- ALL THREE key-glyphs are MOBILE (see MOBILE KEY-GLYPHS section). Model green on the 1 probe move.
  B>=42 (only lower-bounded; set LEVEL_BUDGET[5]=42 conservative). bounce behaviour on L5 still
  UNOBSERVED -> validate as plans execute.
- SOLVE = PHASED BFS (full BFS times out): edit SUBGOAL=(pattern_tuple_or_None, colour_or_None),
  run_bfs target='is_goal', commit, repeat; restore SUBGOAL=None between turns.
  PHASES (block/glyphs on different rows: pinwheel r-4, plus r-2, setter r-8):
   1. COLOUR: SUBGOAL=(C, 9) — 3 pinwheel hits 14->8->12->9, keep pattern C=((1,1,0),(0,1,1),(1,0,1)).
   2. SETTER: SUBGOAL=(target_shape, 9) — cycle C->D->E->F->A->B, 5 hits, keep colour 9.
      B=((1,1,1),(0,0,1),(1,0,1)) [###/..#/#.#].
   3. PLUS:   SUBGOAL=(LOCK, 9) — 1 plus hit rotates B->LOCK. LOCK=((1,0,1),(0,0,1),(1,1,1)).
   4. INSERT: SUBGOAL=None (real goal) — navigate into keyhole. Use rings (-3,-9),(3,-9),(-3,-1) for fuel.
- AVOID the plus/setter during the colour phase and the plus during the setter phase (constrain the
  SUBGOAL pattern) — accidental plus convergence rotates the pattern (cost 3 hits to undo).
- SOLVED #522: opened the col8 gate, trekked back to the glyphs, re-keyed to #.#/..#/### col9
  (= rot(B)), drove through the opened gate into the col9 gate in the pocket -> both keyholes
  consumed -> level_up. Cost: one full RESET after running the tank dry (see L5 FUEL).

## Level 6 (coarse origin x=19+5cx, y=15+5cy)  -- IN PROGRESS -- *** FOG OF WAR ***
### THE BIG ONE: L6 ONLY SHOWS A CIRCLE OF THE MAP AROUND THE BLOCK.
    visible(x,y)  iff  (x-(x0+1.5))^2 + (y-(y0+1.5))^2 <= R^2,   (x0,y0)=block TOP-LEFT,  R=20
  Everything else renders as PANEL(5). EXACT: 0 mismatches over every frame. Detected generally by
  _fog_radius2 (max dist of visible px from the block): L0-L5 = 41..70 (no fog), L6 = 19.96 -> R=20.
  So colour 5 on L6 means **UNEXPLORED**, not off-map, and ENTRY_GRID shows only ~37% of the map.
- CONSEQUENCE: the terrain must be ACCUMULATED from the frames actually seen. `mkterrain.py 6`
  rebuilds it from events.jsonl (first-sighting-wins, so consumed rings stay intact) and patches the
  FOG_TERRAIN literal in world_model_v5.py. _get_map SWAPS that terrain in for ENTRY_GRID and parses
  everything (floor/glyphs/panels/bg) from it. predict() re-renders the map region every step as
  TERRAIN ∩ circle(block), minus consumed rings (state['spent']) and opened gates (state['opened']).
- *** WORKFLOW EVERY TURN ON A FOG LEVEL (do this in order!) ***
    1. run_python mkterrain.py 6          (rebuild terrain from the new frame)
    2. edit_file: BUMP the `# terrain-rev: N` line  <-- REQUIRED! mkterrain writes from a SUBPROCESS,
       which does NOT re-install the live model; only write_file/edit_file do.
    3. run_backtest  (must be green)
    4. commit the next move(s)
- COST OF EXPLORING: a move that brings NEVER-SEEN map into view MUST mispredict (the model renders
  unknown as PANEL) -> the harness drops the rest of the plan. So exploring = ~1 move/turn. But
  RE-WALKING known ground predicts exactly -> long multi-move plans work there. Route accordingly.
- RESET IS FREE KNOWLEDGE: reset refunds the budget AND restores the rings, while my accumulated
  FOG_TERRAIN persists. So: explore ~20 moves, RESET, re-walk to the frontier in ONE commit, explore on.
- B = 21 (bar 42px, drains 2px/move; move 1 gave 42->40 => B in [21,41], 21 = min & matches L1/L2/L4).
- NO lock and NO key-glyph seen YET — but the HUD exists (BORDERLESS: its 5-border is invisible
  against the 5 background) at px(3,55)-(8,60) = L5's HUD slot, cell=2: pattern .#./.#./### (=shape D)
  colour 12. A key implies a KEYHOLE somewhere in the fog -> that is what exploration must find.
  (Not modelled yet: nothing on L6 can change the key, so the key is static.)
- KNOWN so far: rings at cells (-2,-2) and (2,1); a THIRD ring at (4,-2) (only 1 px revealed so far);
  a launcher edge-line at row 19 cols 39+ (clipped -> not yet a full 5px line, so `launch` is empty).
  Map extends RIGHT (cx>=4) and DOWN (cy>=4); coarse grid runs about cx -3..8, cy -3..7.
### FOG MODEL v2 (UI-mask, backtest green 527): the map extends WAY past row 52 (down to ~row 60).
  The always-visible UI = non-PANEL pixels of the ENTRY frame OUTSIDE the entry fog circle (= the HUD
  art rows 55-60 cols 3-8, + the bar rows 61-62). MAP region = everything else, fogged by the circle.
  Model stores M['ui_mask'],M['ui_val']; predict renders map∩circle=terrain, map\circle=PANEL, UI=fixed.
  mkterrain.py rebuilt to match (accumulate over ~ui_mask, block found as the 12-over-9 5x5). Verified
  0-diff on every L6 frame. (Old FOGROWS=53 row-cutoff was clipping map rows 53-60.)
### KEY + KEYHOLE FOUND (after the launcher chute revealed the south, ~67% explored):
  - HUD (borderless, cell=2, px topleft (3,55)) reads as a 3x3 pattern = .#./.#./### (shape D) COLOUR 12.
    (_find_panels can't see it — no colour-5 border square vs the 5 background — so M['hud']=None. Read
    it by hand: cells are 2x2 px.)
  - KEYHOLE (lock) DETECTED at bbox(28,49,34,55), 7x7 cell=1: pattern #.#/##./.## COLOUR 8. Block enters
    it at cell (2,7) = px(29,50). (_find_panels DOES catch this one — the pattern colour-8 forms the
    square? Actually it's found via the colour-8 3x3 cluster. locks:1 now.)
  - KEY (D,12) != LOCK (#.#/##./.##,8): pattern 5->6 on-cells (needs a SETTER), colour 12->8 (needs a
    PINWHEEL). So UNLESS matching isn't required on L6, I must find a SETTER + PINWHEEL in the fog.
  - Partial colour-0 glyph seen at px(21,42) ~ cell (0,5) — a SETTER candidate (setter={0} 4px). Not yet
    fully revealed. HUNT for it + a pinwheel.
### LAUNCHERS (verified): (4,1)->DOWN, (4,3)->LEFT, (3,3)->UP. The (4,3) LEFT-launcher: entering it
  (e.g. from (4,4) going UP) flings the block LEFT, sliding (4,3)->(3,3)->(2,3) (passes the (3,3) UP
  launcher WITHOUT redirect), stops at wall (1,3). Lands (2,3). From (2,3): DOWN x3 -> (2,6) = the cell
  just ABOVE the keyhole. Route (4,5)->[1,1,2,2,2]->(2,6).
### *** L6 WIN PATH (turn 49): KEY == LOCK confirmed (#.#/##./.## col8). Fuel-safe win path from (0,5):
  [1,3,3,1,1,1,1,1,1,2,2,2,2,4,4,4,4,2,2,2,2,2] — UP to ring (-2,-2) [refuel], DOWN to (-2,2), RIGHT to
  (2,2), DOWN into keyhole (2,7) => level_up. Avoids cx=7 + glyphs (key stays=lock), no death (sim
  verified lvlup=True at the end). This CLEARS L6 -> L7. ***
### KEY = LOCK after this (turn 47): HUD confirmed (D.rot180, col8). Committing [4,2,1,4,1,2,1,2,1,2,1,2]
  = refuel at ring (-1,6), to setter(0,5) hit1, UP/DOWN oscillate x4 (hits 2-5). SIM VERIFIED: shape
  D.rot180 --setter x5--> #.#/##./.## = [[1,0,1],[1,1,0],[0,1,1]] col8 = EXACT LOCK. Block ends (0,5) on
  setter, u=10, KEY MATCHES LOCK. THEN: step OFF setter, navigate to keyhole (2,7) [bbox(28,49,34,55)]
  avoiding ALL glyphs (setter(0,5)/pinwheel(-2,5)) and cx=7, and step in = L6 WIN. DON'T re-touch setter!
### ENDGAME PROGRESS (turn 46): key=D.rot180 col12, refueled at (2,1) u=0. Committing pinwheel x3:
  route [2,3,3,3,3,2,2] to (-2,4) then [2,1,2,1,2] (DOWN/UP onto pinwheel(-2,5) x3): colour 12->9->14->8
  (verified in sim), shape stays D.rot180. Ends on pinwheel (-2,5) colour 8, u=12. THEN: refuel at ring
  (-1,6), then SETTER(0,5) x5 (D.rot180 --setter x5--> C.rot180 = lock #.#/##./.## shape). Then keyhole
  (2,7). Setter is at (0,5), reach via (-1,5) (DON'T step on pinwheel (-2,5) again = would change colour).
### *** BOTH ROTATIONS DONE (turn 43): key = D.rot180 = ###/.#./.#. colour 12 (confirmed HUD). ***
  Now: (a) NEVER re-touch the plus (cx=7) — it would rotate the key again; (b) NEVER RESET/die — RESET
  puts the key back to D (loses the 2 rotations). So NO RESET; manage fuel to not die (u=10, 11 safe
  moves). Get OFF cx=7 (LEFT) first, then route WEST to the SW pocket, AVOIDING the plus (cx=7) and not
  dying. REMAINING: setter(0,5) x5 (D.rot180 -> C.rot180 = lock shape #.#/##./.##, setter commutes w/
  rotation) + pinwheel(-2,5) x3 (col 12->8); then keyhole (2,7) = WIN. Route through rings (2,1),(-1,6);
  BEWARE launchers (4,1)D,(4,3)L,(3,3)U in the centre — use run_bfs/model (launcher-aware) to route.
### *** CONVERGENCE WORKS! (turn 42, HUGE) *** Block RIGHT (6,2)->(7,2) as plus descended (7,1)->(7,2):
  HUD rotated D=.#./.#./### -> #../###/#.. = rot90CW(D), colour 12. So HYPOTHESIS B is CONFIRMED — the
  L6 plus does NOT avoid the block; convergence (block-final==plus-final) rotates the key 90CW, exactly
  like L4. Earlier "avoid" confusion was the plus hitting its natural bounds, not fleeing. The plus is
  CATCHABLE the normal way: predict its next cell (it bounces cx=7 between (7,-2) and (7,5), 1 cell/
  block-move) and move the block onto it.
  2ND CONVERGENCE: block+plus now both at (7,2), plus velocity DOWN. Move DOWN -> block (7,3), plus
  (7,3) -> converge again -> key = rot90CW twice = D.rot180 = ###/.#./.#. col 12. That's the 2 rotations
  needed. THEN SW: setter x5 (commutes w/ rotation -> C.rot180 = lock #.#/##./.## shape) + pinwheel x3
  (col 12->8). Then keyhole (2,7) = WIN.
### CONVERGENCE EXECUTION (turn 39): plus at (7,-1) moving DOWN (bounced off top wall (7,-2)). Block
  (6,2), u=6. SEQUENCE [UP,DOWN,RIGHT] to converge at (7,2): move1 UP->(6,1)[plus->(7,0)]; move2 DOWN
  ->(6,2)[plus->(7,1)]; move3 RIGHT->(7,2) as plus lands (7,2) -> block-final==plus-final=(7,2). Each
  move mispredicts (plus in view) so 1/turn; re-observe plus after each. If HUD rotates D=.#./.#./###
  -> #../###/#.. -> CONVERGES (hyp B). If plus FLEES on the RIGHT -> hyp A (avoider, needs trap).
### CONVERGENCE ATTEMPT (turn 36): block refueled at ring (7,7) u=0 (FULL tank). PLUS at (7,3). Block
  is BELOW wall (7,6), so go up cx=6 to reach the plus's row. CONVERGENCE IDEA: get block to (6,k) with
  the plus at (7,k±1) moving toward (7,k); move RIGHT onto (7,k) as the plus lands (7,k) -> if no
  avoidance, block-final==plus-final=(7,k) -> rotate. Need the plus's VELOCITY (observe via 1 move).
  1 move/turn near the plus (it's in view -> model mispredicts). Refuel is right here at (7,7).
### SOLVE PLAN (post-RESET, turn 32): SETTER COMMUTES WITH ROTATION, so order is flexible: rotate
  plus x2 (D->D.rot180) then setter x5 (->C.rot180=lock shape), OR setter-first. Since the chute drops
  the block near the EAST (plus), do the PLUS FIRST to verify convergence, then SW for setter+pinwheel.
  IMPORTANT re-think: obs-4 "convergence fail" had the plus at (7,3) which MIGHT be a natural MODE-A
  bound (not block-avoidance) -> convergence is NOT cleanly disproven. Need a CLEAN test: plus at a
  MID-RANGE cell (e.g. (7,1) heading to (7,2)), move block onto (7,2) from the side; if HUD rotates
  D->#../###/#.. -> converges (hypothesis B, easy). If it flees -> A (needs a trap).
  Route: entry --[1,1,4,4,2,4,2,2,4]--> (4,5) u=9; then east, REFUEL at ring (7,7), then to the plus
  column cx=7 and run the clean convergence test. B=21 tight -> refuel every ~2 rings.
### GLYPHS ON L6 ARE STATIC (not mobile). My model assumed plus/pinwheel/setter mobile @lvl>=5 (from
  L5), but that (a) has NO evidence on L6 and (b) drawing a mobile always-on-top BREAKS the fog circle
  (regressed #522-534). FIX: _is_mobile returns False on any fog level -> glyphs are terrain, rendered
  by the fog circle. (If I ever SEE an L6 glyph move, revisit.) Backtest green 529 after the fix.
### SETTER FOUND at cell (0,5) px(20,41): shape #../.##/.#. colour 0 (same setter as L3/L5). STATIC. It
  is in the WEST pocket (reachable from (0,4)/(-1,4); (1,5) is wall). Still NEED a PINWHEEL (colour
  12->8) and a PLUS (180deg rotate) — both still in fog. Transform plan: D --setter x5--> C (canonical),
  --plus x2--> C.rot180 = lock #.#/##./.## ; colour 12 --pinwheel--> 8. Finding a setter strongly
  implies matching IS required (~95%).
### *** HUD DETECTION FIXED (backtest green 533) — the KEY BREAKTHROUGH for L6 ***: the borderless
  HUD (colour-5 border merges with the 5 backdrop) is now detected as the SQUARE, 3-divisible non-bar
  art component in the UI strip (px(3,55) 6x6 cell=2, borderless so px=x0 not x0+2). Before this
  M['hud']=None -> colour=None -> NO glyph effect could fire or be written (the pinwheel did nothing).
  Also fixed the fog render clobbering the HUD: carry final_pat/final_col out of the moved branch and
  _write the current key AFTER the ui_val backdrop. Model now PREDICTS the pinwheel cycling colour
  12->9->14->8 and the setter cycling the shape. BUT NOT YET VERIFIED vs reality — no L6 glyph has
  fired. MUST verify by actually entering the pinwheel/setter (model assumes L2-L5 mechanics).
### *** PINWHEEL VERIFIED vs REALITY (#542): stepping onto it took HUD colour 12->9, pattern D
  unchanged, 0 HUD mispredicts (the step's mispredict was purely the newly-revealed southern fog).
  So the L6 glyph model (colour cycle, static trigger on entry, HUD write) is CONFIRMED. ***
### *** SETTER VERIFIED vs REALITY (#544): shape D->E=#.#/#.#/### exactly as predicted, colour 9
  unchanged, 0 HUD mispredicts. SETTER_CYCLE (A->B->C->D->E->F) confirmed on L6. BOTH transform
  glyphs now verified (pinwheel colour + setter shape). Only the PLUS's location remains unknown. ***
### PLUS IS DEFINITELY REQUIRED (proof): from canonical D the setter only makes canonical shapes; the
  lock #.#/##./.## = C at rot180. setter+plus can reach any (shape,rotation) but setter ALONE can't
  rotate. No plus seen yet (all colour-0 px = setter/pinwheel centers; all colour-1 px = launcher
  lines). The plus MUST be in the ~17% unexplored fog (the EAST cx>=6 is the big blank). HUNT IT.
### *** THE PLUS IS MOBILE ON L6 (turn 25, rigorously confirmed) *** — this is L6's crux. Proof:
  at seq4602 (block (5,4)) cell (56,22) was IN the fog circle and showed FLOOR; one block-move later
  (seq4637, block (6,4)) the PLUS (.0./100/.1., colours {0,1}) is at (55-57,21-23)=cell (7,1). So it
  MOVED into view -> mobile (moves 1 cell per block MOVE, like L4). The pinwheel(-2,5) & setter(0,5)
  are STATIC (backtest green with them static; I stepped onto them and they stayed). So on L6 ONLY THE
  PLUS is mobile (same as L4). CONSEQUENCES:
  - My _is_mobile returns False on fog levels -> model treats the plus as static/absent -> mispredicts
    (#557) whenever the plus is in view. mkterrain's first-sighting-wins ALSO mis-records it (floor at
    transient spots). The plus is NOT in ENTRY_GRID (it's in the fog), so _get_map can't set up its
    patrol from entry like L4/L5 did.
  - PLAN: OBSERVE the plus's motion over several block-moves (keep it in the fog circle), determine its
    patrol (L4/L5 MODE-A horizontal-bounce is the guess), then model it (probably a special L6 branch:
    detect the plus wherever it currently is, track its cell in state, move it per the patrol) and plan
    a CONVERGENCE (block-final cell == plus-final cell) to rotate the key — exactly like L4.
  - OBSERVATIONS (plus cell, after each real block-move): seq4637 block(6,4) -> plus (7,1);
    seq4696 block(6,3) -> plus (7,2). So the plus moved DOWN (cy 1->2), SAME column cx=7, while the
    block moved UP. Motion is INDEPENDENT of block direction (as on L4/L5) — it's the plus's own patrol.
    Current velocity = DOWN (vy=+1). NOT a horizontal bounce. Looks like MODE-B (2D wall-follow) or a
    vertical patrol. 3rd obs seq4729 block(6,4) -> plus (7,3). So plus (7,1)->(7,2)->(7,3): steady DOWN
    col cx=7, 1 cell/move, velocity DOWN. Plus glyph = .0./100/.1. (CW rotator, colours {0,1}).
  - CONVERGENCE TEST (turn 27) FAILED to converge — and revealed the rule! Block RIGHT (6,4)->(7,4);
    plus was at (7,3) heading DOWN, next cell (7,4). But the block took (7,4), and the plus REVERSED to
    (7,2) (HUD unchanged = D/12, NO rotation). So *** L6's PLUS BOUNCES OFF THE BLOCK (treats the
    block's cell as a wall) ***, UNLIKE L4/L5 where the plus ignored the block and convergence =
    plus-new==block-final. So I CANNOT converge by moving the block into the plus's next cell — it flees.
  - CORRECTION (turn 30): the plus REACHES (7,0)! (my "wall at (7,0)" was the plus's own colour-1 px
    mis-read as terrain; the (55,17) "clue" WAS the plus at (7,0).) Trace: (7,1)->(7,2)->(7,3)->(7,2)
    ->(7,1)->(7,0). TWO hypotheses to resolve: (A) plus AVOIDS the block (obs-4 (7,3)->(7,2) reversal
    was caused by block moving to (7,4)); (B) plus bounces NATURALLY on a fixed range like [0,3] and
    does NOT avoid the block (obs-4 reversal was its natural bottom bound at (7,3)). Under (B) I can
    converge normally (L4 way: move block to plus's next cell). RESOLVE by moving block OFF cx=7 and
    watching whether the plus goes BELOW (7,3) [=>A] or bounces at (7,3) [=>B].
  - PLUS COLUMN cx=7 is FLOOR from (7,-2) to (7,5) (walls at (7,-3) and (7,6); (7,7) below the wall is
    a RING). So the plus's vertical bounce range is [-2,5] (8 cells) — BIG, and it goes OUT of the fog
    circle at the top. Since (7,3) is NOT a wall, the obs-4 reversal at (7,3) was the BLOCK => leaning
    hypothesis A (plus AVOIDS the block). It's a CW rotator; goes off-view when far from the block.
  - *** FUEL NEAR-DEATH (turn 31): all the manual plus-observation burned fuel to u=18/B=21 (3 left),
    no ring within 3 moves -> FORCED RESET. LESSON: manual observation of the mobile plus is very
    fuel-expensive. After RESET, be disciplined: model the plus from the recorded obs + column geometry
    and use BFS, rather than endless manual observation. Or observe in SHORT bursts near a ring. ***
  - PLUS MODEL DRAFT: on cx=7, 1 cell/real-block-move, bounce range [-2,5] (reverse at walls (7,-3)/
    (7,6)), AVOIDS the block (reverse if next cell == block's new cell). CW rotator on convergence.
    Convergence with an avoider needs a TRAP (unresolved) — figure out via BFS once modeled, or test
    trap-at-wall carefully. To model in-fog: detect plus cell from live grid when visible; track
    (cy,vy) in state; the entry position is fogged so may need re-detect on reappearance. 4 obs: (7,1)->(7,2)->(7,3)[block hits
    (7,4)]->(7,2). Consistent with: vertical bouncer on cx=7 bounds ~[1,5], PLUS bounces off the block.
  - REVISED (turn 29): obs (7,1)(7,2)(7,3)(7,2)(7,1) ALSO fit a [1,3] VERTICAL BOUNCE with NO block-
    avoidance (via the L4 rule: START cell is a NEAR bound -> if the plus started at (7,3), it bounces
    [(7,1)=wall bound, (7,3)=start bound]). Under [1,3] the (7,3)->(7,2) reversal at seq4765 was NATURAL
    (its bound), not the block. This is SIMPLER and means CONVERGENCE WORKS (plus doesn't avoid block).
  - DISTINGUISHING TEST: get the plus to (7,3) going DOWN with the block OFF cx=7 and NOT at (7,4). If it
    reverses to (7,2) => bounds [1,3] (no avoidance, convergeable normally). If it continues to (7,4)/(7,5)
    => bounds [1,5] + it avoids the block. Currently plus (7,1) going DOWN; keep block at cx<=6 and watch
    it reach (7,3). THEN: if [1,3], converge L4-style (block-final==plus-final on a cell in [1,3]); model
    the plus (detect cell from live grid, bounce cx=7 [1,3], rotate key 90CW on convergence), backtest.
### PLUS CLUE (turn 23): isolated colour-1 pixel at px(55,17) = cell (7,0), surrounded by floor — a
  PARTIAL reveal, could be a plus corner / launcher end. Heading NE to (6,0)/(7,0) to identify it.
  Still 0 plus detected at 87%. FUEL NOTE: fog-tax = only ~1 move executes/turn, so only ~1 fuel spent
  per turn -> lots of runway; don't over-worry fuel, but a ring is at (7,7) [SE, near] if needed.
### PLUS HUNT: frontier analysis (turn 21) -> the only big unexplored region adjacent to reachable
  floor is the EAST cx=7,8 (cells (7,-2..2),(8,3..5),(6,-3),(6,8),(7,7)); plus a tiny pocket (2,6).
  So the PLUS is almost certainly in the EAST. RESET (turn 21) for full fuel + clean key (D,12) +
  central start (0,0) which reaches the east via the launcher chute ((4,1) DOWN). Then explore east.
  NOTE: exploration is ~1 frontier-move/turn even re-walking (terrain has occlusion holes where the
  block always sat), so RESET's value is fuel+clean-key, not fast repositioning.
### PINWHEEL CONFIRMED at cell (-2,5) px(10,41): wheel [14,8,12,9] (same as L2-L5). Colour 12->8 = 3
  hits (12->9->14->8). Its arms REUSE block colours 9/12 -> mkterrain must NOT floor all 9/12 (only the
  block's 5x5 footprint), else it erases the pinwheel (fixed; backtest green 532). SETTER at (0,5),
  PINWHEEL at (-2,5), with (-1,5) between them. STILL NEED A PLUS (rot 180) — not found yet.
### PINWHEEL earlier partial note (superseded): colour-14 pixel at px(12,41) ~ cell (-1,5), next to setter
  (colour 14 = a pinwheel arm; wheel on L2-L5 = [14,8,12,9]). Also a colour-11 pixel at px(17,46) ~
  cell (-1,6) = maybe a RING (fuel in the pocket). Both PARTIAL — reveal them. So the SW pocket (cx
  -2..0, cy 4..6) holds the SETTER (0,5) + PINWHEEL (~-1,5) + maybe a ring. Still need a PLUS for the
  180deg rotate — keep hunting (maybe also in this pocket or elsewhere).
### SW POCKET IS WALLED from the block's region; the connection is via cx=-2 going SOUTH ((-2,3)->
  (-2,4)->(-1,4)->(0,4)->setter(0,5)), but (-2,4)/(-2,5) are still fog. Exploring (-2,3) reveals it.
### DECISIVE TEST (lower priority now): at (2,6) push DOWN into the keyhole. Model predicts REFUSED (shut, free
  no-op) because key!=lock. If reality REFUSES -> matching IS required -> hunt setter+pinwheel. If
  reality ENTERS (mispredict / level_up) -> matching NOT required -> maybe an instant win. Refused move
  is FREE, so the test costs nothing if it fails.
### (old pre-fog analysis below — the "23 walkable cells" map was just the STARTING CIRCLE, not the level)
*** L6 BREAKS TWO OLD ASSUMPTIONS — model fixed, backtest still 516/516 green: ***
1. The OUTER BACKGROUND is PANEL-coloured (5), not VOID(4)! Three knock-on fixes:
   - _find_panels must REJECT huge components (added `w > 25` bound), else the 64x64 background is
     read as a "panel", masks the block, and _get_map dies ("max() arg is empty").
   - WALKABLE = ((not VOID) and (not PANEL)) OR inside a detected keyhole panel. (Was "not VOID",
     which leaked the floor flood-fill into the whole background: bar0=0, off-map cells "free".)
   - The block-component search must also exclude PANEL, else background + off-map HUD art merge
     into one giant "block" (it picked a 64x64 "block").
2. There is NO {5}-bordered HUD/lock panel: the HUD is BORDERLESS (its 5-border is invisible
   against the 5 background). L6's colour-12 art at px(3,55)-(8,60) is EXACTLY L5's HUD pattern
   area (px=3, py=55, cell=2) -> pattern .#./.#./### (= shape D), colour 12. Not yet modelled
   (harmless: nothing on L6 can change the key).
- LAYOUT: block cell (0,0) at px(19,15); 5x5 cells. 23 walkable cells:
       cx=-2 -1  0  1  2  3
  cy=-2:  .   .  .  .  .  #
  cy=-1:  .   .  .  #  .  .
  cy= 0:  .   .  @  #  #  .
  cy= 1:  .   #  #  #  .  .
  cy= 2:  .   .  .  .  .  #
  RINGS at (-2,-2) and (2,1). bar0=42; B UNKNOWN -> guessed 42, VERIFY ON MOVE 1 (bar 42->41 = B>=42;
  42->40 would mean B=21).
- *** NO LOCK, NO KEY-GLYPH (no plus/pinwheel/setter; no colour-0 anywhere). *** The map holds ONLY
  floor / walls / 2 rings / the block, plus ONE colour-1 nub at px(39,19)-(40,19): a launcher-style
  edge line CLIPPED by the map boundary, lying on the RIGHT EDGE of cell (3,0). On L0-L5 colour-1 is
  only ever (a) a 5-px launcher edge-line or (b) part of a PLUS (which needs colour-0 — absent here).
  So the nub is the ONLY marker on the board -> almost certainly the EXIT/DOOR.
- HYPOTHESIS UNDER TEST (probe [1,1,4,4,2,4,2,4]): go (0,0)->(3,0) in 7 mv, then push RIGHT into the
  nub. Model predicts a BUMP + no level_up; if reality level_ups, the nub is an exit-by-move.
  If it IS just a bump -> the exit must need unlocking; re-examine (collect both rings? cover all
  cells? is the nub a launcher whose target cell only opens later?).

## Next level checklist
- Re-derive everything from ENTRY_GRID (model already does).
- Watch for: multiple rotators, CCW rotators, differently-shaped/sized blocks, several locks,
  what happens if the bar runs out, whether entering the lock with a WRONG key is blocked/deadly.
