## LEVEL 6 (in progress) — palettes + obstacle + multiple deformable objects
- 5 PALETTES (5x5, border 2, 3x3 interior): colours 9,b,8,e,6 at top.  (Detector now handles 5x5 & 6x6.)
- OBSTACLE = the colour-1 anti-diamond blob at (31,31) (obstacle = a BLOB with no boxes & not a
  palette colour; movable objects are recognised primitives).
- 9 BOXES: 8x4 [(9,9),(3,15),(36,15),(9,27)], b x3 [(45,30),(39,48),(51,48)], 9x2 [(57,18),(39,24)].
- 3 MOVABLE OBJECTS: a=PLUS arms9 @(12,48) [SELECTED]; c=SQUARE-RING 13x13 @(21,51);
  7=CROSS arms u9 d9 l18 r18 @(24,54) — asymmetric, so decomposer split it into h-line+plus (both
  colour 7 at (24,54)); render-equivalent statically but MAY mispredict when the 7 moves/deforms.
- Added an ASYMMETRIC-CROSS detector (_asym_cross): the 7 is now ONE plus (arms [9,9,18,18]).
  Refactored parms/pcur to PER-OBJECT dicts (L6 has TWO pluses a & 7) — render/deform/align/mark
  all keyed by object index.  ZORDER[6]=[0,2,3,1] (obstacle<ring<7-plus<a-plus).  Backtest 282/282.
- Objects' colours (a,c,7) don't match box colours -> must RECOLOUR via palettes (to 8,b,9) AND
  reshape/position (likely deforming against the obstacle for big arms).  Rough assignment idea:
  7->9 covers the two 9-boxes (centre (57,24): (57,18) up, (39,24) left18); a or c -> b; the 4th
  object? only 3 objects for 3 colours.  8-boxes span wide (need r=27) => deformation required.
- BUDGET[6]=320 (in (256,384]; n=1,2,3->bar 0,0,1); refit when 2nd bar cell appears (~n=8 vs 9).
- Recolour wired into deform branches (_recolour_cells on current cells).  Backtest 288/288.
- FIXED: a non-selected ring must render from its STATIC layout shape, not a frame-derived bbox
  (occlusion corrupts _ringbox).  bb only refreshes when the ring is the SELECTED object.
- SOLVE (per-object BFS over (centre,arms,colour) using _plus_deform + _recolour_cells):
  * 7-plus -> 8: 38 moves from (24,54) -> (9,15) arms (6,12,6,30), covers 4 eight-boxes.
    path=[1,1,1,1,4,4,4,4,4,2,4,1, 4,4,1,1,4,4,1,1,1,1,1,1,1,1, 3,2,3,3,3,3,3,3,3,3,3,3]
    deforms at steps 5-11, RECOLOUR to 8 at step 26.  Verified end-state in live model.
  * 7->8 DONE (col 8 @(9,15) covers all 4 eight-boxes).  Budget refit to 300 (exact).
  * ACTION5 cycle SKIPS the obstacle (_next_sel); walls aren't selectable.  Backtest 322/322.
  * a-plus -> b: 39-move plan (switch + recolour-to-b + reshape to (45,48) arms [18,0,9,9]) covers
    3 b-boxes.  Split BFS (recolour phase then reshape phase) — combined BFS too deep.  a-plus has
    l+r=18,u+d=18 conserved; (45,48) needs u18/d0/l>=6/r>=6 => arms [18,0,9,9].  Verified in-model.
  * c-ring -> 9: switch + 29 moves, deform 13x13 -> 19x7 bbox [39,57,18,24] col 9 covers 2 nine-boxes
    => LEVEL_UP (verified in-model).  FIXED: ring bb is now threaded PURELY in state (init from entry
    layout), never re-read from the frame (the ring gets occluded by placed objects on lower z).

## LEVEL 7 (LAST) — 2 deformable rings + 2 obstacles + 14 palettes
- Objects: [0]obstacle-1@(60,3), [1]a-RING 13x13@(54,45), [2]c-RING 13x13@(51,48 SELECTED),
  [3]obstacle-1@(36,57).  TWO obstacles (colour-1, 5x5 each).  ZORDER[7]=[0,1,2,3]; entry exact.
- Boxes: b x4 [(9,39),(15,39),(9,57),(15,57)] = rect 7x19; 6 x4 [(6,45),(21,45),(6,54),(21,54)] = 16x10.
- SOLVE: c-ring->b deform 13x13->7x19 bbox(9,15,39,57) [50 moves found]; a-ring->6 deform 13x13->16x10
  bbox(6,21,45,54).  Both rings 48 cells (perimeter conserved).  Recolour via b-palette@(5,5), 6-palette@(5,20).
- MODEL CHANGES this level (backtest 391/391): (1) clipped-palette detection (5x5 partly off-grid);
  (2) blob fallback splits into CONNECTED COMPONENTS; (3) MULTIPLE obstacles: _obstacles() list +
  _obs_cells() = union of all obstacle bboxes for deform collision; _next_sel skips all obstacles.
- PER-OBJECT bbs/gss dicts (was single bb -> deformed the wrong ring).  Backtest 391/391.
- BUDGETS[7]=400 provisional (>256 so far); refit on 1st bar cell (n,k): 64n/(k+.5)<B<=64n/(k-.5).
- PALETTE TIE-BREAK: when a ring touches TWO palettes at once, "highest value" is WRONG (L7: ring
  touched b(11)+6(6) -> became 6).  ROBUST FIX (as L4): BFS with a >1-palette guard so recolour is
  always single-touch (unambiguous); DON'T model the tie-break.
- GRID EDGE BLOCKS: a ring can't move so its bbox CENTRE goes off-grid (observed: ring at bbox
  center x0 blocked from moving left).  BFS must stay strictly ON-GRID (0<=x0,x1<64,0<=y0,y1<63).
- ** RECOLOUR RULE SOLVED (backtest-green on ALL levels): _recolour_enter = the cells that NEWLY
  ENTER a palette this move (new_cells - old_cells); among palettes those newly-entered cells
  touch, MOST-count wins (tie -> highest value).  If nothing newly enters, colour persists. **
  Fits L4/L6 (#138-144,#338) + L7 (m13 e/8/a tie->e; m14 a; move-26 6>b).  BFS must use the same
  rule (track old cells).  On-grid c-ring->b DONE (7x19 [9,15,39,57] col b on 4 b-boxes).  a-ring->6 = switch + 77 moves ->
  16x10 [6,21,45,54] col 6 on 4 six-boxes => LEVEL_UP (verified in-model).  GOTCHA: run_python file
  writes DON'T reinstall the live model - always finish with an edit_file to reinstall!
  BUDGETS[7]=400 confirmed
  (n=81->13 bar cells; 384<B<=414).
- (old off-grid guarded solve was WRONG - grid edge blocks center off-grid):
  Full plan RESET + cpath + 5 + apath = 111 actions => LEVEL_UP (all boxes aligned, verified in-model).
  cpath=[2,3,3,3,3,1,1,1,3,3,3,3,3,3,3,1,1,1,1,1,1,1,1,1,1,1,3,3,3,3,3,3,3,2,2,2,3,3,3,2,2,2,2,2,2,2,2,2,2,4,4,4,4,4,4,4]
  apath=[2,3,3,3,3,2,1,1,1,1,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,1,1,1,1,1,4,3,3,3,3,2,2,2,2,2,2,2,2,2,4,4,4,4,4,4,4,4,4]

## LEVEL 5 — SOLVED (new mechanic: deformation vs obstacle)
- NO palettes.  Objects: 9-PLUS (53 cells) @(48,15); b-SQUARE-RING 72 cells bbox (6..24, 39..57);
  1-ANTI-DIAMOND 40 cells in an 8x8 bbox (EVEN size => centre is NOT a lattice point!).  Mark on
  the b-ring at (15,48).
- Boxes: 9 @ (12,6),(9,9),(30,9),(12,27);  b @ (45,30),(54,30),(45,57),(54,57).
- ** RIGID TRANSLATION CANNOT SOLVE IT **: the 9-plus (arms 12-13) would have to sit at (12,9) and
  reach 18 cells; the b-ring (r=9, spans 18) must cover boxes spanning 27 rows.  Both impossible.
  => the objects must CHANGE SIZE.  Movement is CONFIRMED to be an ordinary rigid +3 translate
  (the ring translated exactly), and the model now represents all L5 shapes (added a SQUARE
  (Chebyshev) RING primitive + a BLOB fallback for anything no primitive explains) — 210/210 green.
- ** MECHANIC FOUND: objects DEFORM against the 1-shape (an obstacle/wall), CONSERVING CELL COUNT. **
  Ring was 19x19 (72 cells).  Moving UP with its top edge blocked by the 1-shape gave 22x16 —
  still 72 cells: height -3, width +3.  I.e. the blocked edge stays put, the opposite edge keeps
  moving (shrinking that axis by 3), and the other axis GROWS by 3 to conserve the perimeter.
  frames: 214 (18..36, 39..57) -> 215 up ok (18..36, 36..54) -> 216 up BLOCKED (15..36, 36..51).
- ** THIS IS THE KEY TO L5 **: the four b-boxes span x 45..54, y 30..57 = a 10x28 rectangle whose
  ring perimeter is 2*(10+28)-4 = 72 = EXACTLY the ring's cell count.  So the goal is to RESHAPE
  the ring into 10x28 and place it on those corners.  Likewise the 9-plus (53 cells, arms 13) must
  become arms u>=3,d>=18,l>=3,r>=18 about (12,9) (sum of arms = 52 = 53-1 -> feasible).
- QUANTIFIED: each BLOCKED move = the blocked axis SHRINKS 3, the other axis GROWS 3, cells conserved:
    19x19 (f214) -> 22x16 (f216) -> 25x13 (f217), always 72 cells.
    The blocked edge stays fixed; the growth appears on alternating sides (f216 grew left, f217 grew
    right) — check whether it alternates or follows some rule.
- ** PLAN FOR L5 **: target ring = 10 wide x 28 tall (the b-boxes' rectangle; perimeter 72 = cells).
  Currently 25x13 => I am deforming the WRONG WAY (UP shrinks height).  Need height +3 / width -3
  => must block a LEFT/RIGHT edge and push SIDEWAYS: exactly 5 blocked sideways pushes (25->10 wide,
  13->28 tall).  The 1-shape (x 28..35, y 28..35) must overlap the ring's rows for a side-block, so
  position the ring's y-range across y 28..35 first.
- ** RULE SETTLED **: UNBLOCKED move = pure rigid translate (f217->f218 DOWN kept 25x13).
  BLOCKED move (leading edge meets the obstacle) = blocked axis -3, other axis +3, 72 cells kept.
- MODEL: added _obstacle/_ringbox/_rect_ring/_deform + ring-aware render.  Ring objects now read
  their LIVE bbox from the frame (so the model never drifts after a deform).  Backtest 214/218 —
  the only misses are the 4 historical DEFORM frames (the grow-side alternation is not yet exact:
  f216 grew LEFT, f217 grew RIGHT; also check where the 0 mark sits on an even-sized ring).
  Unblocked translates ARE predicted correctly, which is what the plan below needs.
- ** EXECUTION PLAN (L5, b-ring) **: ring is 25x13 at x 18..42, y 39..51 (after 1 right).
    1. 7x RIGHT  -> x 36..60 (columns clear of the obstacle x 28..35), still 25x13.
    2. 4x UP     -> y 27..39 (rows now overlap the obstacle band y 28..35), still 25x13 (unblocked,
       because its columns do not overlap the obstacle).
    3. 5x LEFT   -> each BLOCKED by the obstacle's right face (x=35) => width -3, height +3 each:
       25x13 -> 22x16 -> 19x19 -> 16x22 -> 13x25 -> 10x28.  Ring is now at x 36..60, y 27..39
       (rows straddle obstacle band y 28..35, cols clear at x>=36).  GROW-SIDE (does height grow
       up or down?) UNTESTED for a LEFT-block -> commit ONE left and measure before chaining.
    4. translate to put its corners on the b-boxes: DOWN x4 then RIGHT x3 -> bbox x45..54, y30..57
       (all 4 b-boxes covered).  CONFIRMED grow-side: LEFT-block grows height UP; model 229/229 green.
       Mark on an even bbox = round the midpoint UP: ((x0+x1+1)//2, (y0+y1+1)//2).
       ZORDER[5]=[0,1,2] (ring draws on top of the 9-plus).
  ** RING DONE **: b-ring is a 10x28 rectangle exactly on the 4 b-boxes.  Confirmed at f241.
- 9-PLUS still to do.  It is a symmetric 12-arm plus at (48,15), 53 cells.  A rigid 12-plus CANNOT
  cover the 4 9-boxes (12,6),(9,9),(30,9),(12,27) (they span 21 in BOTH x and y but aren't on one
  row/col pair) => the plus MUST deform.  Target: centre (12,9), arms u3 d18 l3 r18 (covers all 4).
  ** PLUS DEFORM (TWO-BAR model, measured on 2 modes) **: a plus = a vertical bar V + a horizontal
  bar H.  A move translates EACH bar by 3, UNLESS that bar's translated cells would enter the
  obstacle (solid bbox), in which case that bar STAYS.  Crossing = (V.x, H.y); arms follow; cells
  conserved.  Mark cursor advances iff the bar PARALLEL to the move is free.
    * f248 LEFT: H blocked (left tip hits wall) -> H stays, V slides left => crossing -3x, l-3 r+3.
    * later LEFT: V blocked (V's upper cells hit the wall SIDEWAYS) -> V stays, H slides =>
      crossing same, l+3 r-3.
  My earlier "leading-arm-only" collision was wrong (missed the perpendicular-arm block).  The
  obstacle is a hollow outline but blocks as a SOLID bbox.
  ** TWO-BAR model backtest 256/256 green. **  Cursor advances iff the parallel bar is free.
  ** PLUS MARK (subtle): the mark is a CURSOR separate from the shape's crossing. **  On a blocked
  (deform) move the cursor STAYS PUT while the crossing slides; on a free move both translate.  So
  crossing and cursor can drift apart (up to many cells).  Model tracks 'pcur' for the mark, and
  the sel-resync matches the visible mark to each object's TRUE mark cell (pcur for plus, bbox
  centre for ring) — else it mis-picked the ring when the plus's crossing drifted from its mark.
  ** SOLUTION (BFS over (crossing,arms), 27 moves, verified LEVEL_UP): reshape the plus
  (45,33)/[12,12,9,15] -> crossing (12,9) arms (3,21,6,18), covering all four 9-boxes. **
  Framework gotcha: run_python edits do NOT reinstall the live model — use edit_file to reinstall.
  Then do the 9-plus: 53 cells, arms 13; needs arms u>=3,d>=18,l>=3,r>=18 about (12,9) — probe how
  a PLUS deforms (its arms presumably redistribute the same way; total arm length stays 52).

# Notes — living scratchpad (game re86).  Model = world_model_v5.py (== v6), backtest 55/55 on L0-L2.

## CONFIRMED mechanics (one generic model, all levels)
- Board = N rigid OBJECTS. Each is a symmetric primitive:
    PLUS (4 orthogonal arms) | X (4 diagonal arms) | DIAMOND (hollow rhombus ring) | HLINE/VLINE.
  ** SEVERAL OBJECTS CAN SHARE ONE COLOUR ** (L2: line+X+diamond, all colour 8).  The model
  DECOMPOSES the entry grid into maximal primitives (greedy exact cover of each colour's cells).
- Objects only TRANSLATE: 3 cells per action, clipped at grid edges, never block each other.
## L4 GOTCHAS (both cost a mispredict — check for them on EVERY new level)
- OBJECTS CAN HIDE BOXES: the L4 plus's 14-long arms covered part of the ring AND the centre of
  two boxes ((57,33),(54,42)) => my strict 8/8-border detector missed them entirely and I solved
  the assignment against 8 boxes when there are 10.  Detector now needs only >=4 border cells with
  no background in the ring.  A box whose CENTRE is covered has an UNKNOWN colour -> must physically
  move the occluding object to reveal it (BOXCOL per-level dict).
- The ENTRY-SELECTED object's CENTRE is hidden under the 0 mark, so whether its centre is a real
  cell is UNKNOWABLE from the entry frame: L1's X had a hole, L4's X is FILLED.  Per-level dict
  CENTREFILL; observe it the first time that object is deselected.

- CENTRE CELL (subtle, solved):
  * the centre belongs to the object's own SEGMENTS only when the shape runs ORTHOGONALLY through
    it (plus / hline / vline).  X and diamond shapes: NOT part of the segments.
  * such a shape MAY still carry a CENTRE DOT — and the game DESTROYS that dot the first time the
    object is SELECTED (the 0 mark overwrites it and it is never redrawn).  So: dot exists iff the
    entry frame shows the colour at the centre AND the object is not entry-selected; it vanishes
    forever once selected.  (L2's X: dot visible until selected, background ever after.  L1's X was
    entry-selected => no dot from the start.  Plus/line centres always show.)
- The 0 MARK is drawn in the SELECTED object's LAYER, so a higher-z object can hide it (mark
  absent from a frame is NORMAL).
- 3x3 boxes (border 4, centre = a colour) = static scenery.
- ACTION 1/2/3/4 = up/down/left/right (3 cells).  ACTION5 = cycle the selected object.
- SWITCH ORDER (ACTION5) = objects sorted by ENTRY centre (y,x) ascending.
- Z-ORDER (draw order, later = on top) is the game's INTERNAL object order — NOT a function of
  position/colour/shape/size.  L0-L2 happen to match ascending entry-x; L3 REVERSES it (the X
  overdraws the plus despite a smaller entry x).  => default to entry-x, and keep a per-level
  override dict ZORDER (learned from the first observed overlap).  ZORDER={3:[1,0]}.
  It only matters where two objects overlap, so a wrong guess costs one mispredict.
- The black pixel 0 marks the SELECTED object's centre.
- BAR = round(64*n/100) right-aligned cells of colour 1 => 100-ACTION BUDGET per level.

## L3 NEW MECHANIC: PALETTES (recolouring)
- 6x6 swatches (uniform border ring + uniform 4x4 interior) = static scenery.
- ** CONFIRMED: an object takes a palette's colour as soon as ANY OF ITS CELLS touches ANY cell of
  that palette's whole 6x6 BLOCK — border ring included, not just the 4x4 interior. **
    * L3 plus -> c when its up-arm tip hit (30,8)   [interior]
    * L3 X    -> 6 (WRONG colour, by accident!) when its DR arm tip hit (33,54) [BORDER ring]
  Colour persists after leaving.  MULTI-PALETTE TIE-BREAK: when an object touches several blocks
  at once the HIGHEST COLOUR VALUE wins (L3: e=14 beat 6; L4: e=14 beat 9 — this kills the earlier
  "last in row-major order" guess).  Only a 2-point fit, so BFS should AVOID standing on two
  palettes at once (add a npals(c)>1 guard) — then the tie-break never matters.
  Long arms make accidental repaints easy => ALWAYS route with a BFS over (position, colour).
- Objects/boxes need not share colours at entry => you must repaint objects to match the boxes.
- Each 4x4 interior contains exactly ONE cell reachable on the 3-step grid — nice design.
- Primitive fitting is now CLIPPING-AWARE (off-grid cells of a primitive count as available), so
  an edge-clipped plus is still recognised with its true arm length.

## GOAL (one rule)
Every box must be COVERED by some object whose CURRENT colour == the box's colour.
level_up fires when all boxes are covered.  (L0/L1: one object per colour; L2: 3 objects, colour 8,
each must cover a share of the 8 boxes — a forced 2/3/3 partition.)

## Level 2 plan (47 of 100 actions)
objects: [0] hline centre (30,45) SELECTED | [1] X centre (18,48) | [2] diamond centre (45,48)
targets: line->(27,6) [1 left,13 up]; X->(42,24) [8 right,8 up]; diamond->(18,30) [9 left,6 up]
switch order assumed: line -> X -> diamond (entry (y,x) order).

## Framework gotchas
- Sandbox has NO `next()` builtin.  Plain loops only.
- backtest/live rollout skip advancing state through transition #0 of the RUN => the model resyncs
  n from the bar and re-locates objects from the frame when the tracked state disagrees.
- events.jsonl "action_taken" = the true per-action frame chain (an.py reads it).
