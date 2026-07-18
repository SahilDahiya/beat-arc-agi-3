# Notes — living scratchpad

## Game: ARC-AGI-3, 8 levels. Currently level 0.

## Action semantics (confirmed / guessed)
- 1,2,3,4: guess directional (up/down/left/right) — UNCONFIRMED
- 5: guess interact/select/rotate — UNCONFIRMED
- 6: click at x,y — UNCONFIRMED
- 7: guess undo — UNCONFIRMED
- 0: RESET (env control)

## Level 0 layout (from ENTRY_GRID)
- bg=9; wall color10(a) vertical x30-32 full height; border color11(b) at x63 full ht; floor color5 at y63.
- LEFT half (x0-29): "5-shape" = L-pentomino of 3x3 tiles, color5, EACH tile has a 0-hole at center.
    top row 3 tiles x18-26 y15-17; vert arm 2 tiles x24-26 y18-23 -> arm on RIGHT. 5 holes total.
- RIGHT half (x33-62):
    "4-shape" solid L-pentomino color4: top x36-44 y15-17 + vert arm x36-38 y18-23 -> arm on LEFT.
    "b-shape" solid L-pentomino color11: top x51-59 y45-47 + vert arm x51-53 y48-53 -> arm on LEFT.
- 5-shape (holes) is MIRROR-orientation of 4/b shapes (arm opposite side).

## Hypotheses to test
- Is there a movable player/cursor? None obvious yet.
- Maybe move/rotate/reflect a solid piece to overlay the holed template? Goal = fill holes?
- Probe: try action 1 first; observe what (if anything) moves.

## Confirmed facts
- RIGHT BORDER x=63 = MOVE COUNTER/GAUGE. Starts full of color11(b). Each VALID move fills the next
  cell TOP-DOWN with color5. move1->(0,63); move2->(1,63). Cumulative. (invalid clicks DON'T advance it.)
- ACT1 = UP, ACT2 = DOWN. Move = shift by exactly 3 cells (=one 3x3 tile) per action.
- The MOVABLE GROUP = {color5 holed template (left of wall) + color4 solid piece (right of wall)}.
  BOTH move together as one unit (up 3, down 3). Entry y15 -> act1 up to y12 -> act2 down to y15.
- FIXED: color11 b-shape (x51-59 y45-53), wall color10 (x30-32), border x63, floor y63.
- Clicking a piece body (40,16) = full NO-OP (no counter tick, no change). Click not the mechanic (so far).

## MIRROR MECHANIC (confirmed)
- Two locked pieces mirror across wall center x=31. RIGHT piece=4-piece(color4,arm-LEFT); LEFT piece=
  template(color5 body + color0 holes,arm-RIGHT). template is the exact reflection of 4-piece across x=31.
- Vertical (act1 up/act2 down): BOTH move SAME y (dy shared).
- Horizontal: MIRROR. act3 => 4-piece RIGHT(+3), template LEFT(-3). act4(pred) => 4-piece LEFT, template RIGHT.
- Step size = 3px (one 3x3 tile) per action.
- Control frame = the 4-piece (right side): act1 up, act2 down, act3 right, act4 left. template mirrors x.

## Probe log
- act1(UP)->group y15->y12. act2(DOWN)->y12->y15. act3-> 4piece x36->39, template x18->15. act6 noop.
- NEXT: build model (movement only, NO win cond yet), backtest green. Then confirm act4. Then move 4-piece
  toward b-shape to learn COLLISION + WIN condition.

## MODEL STATUS (world_model_v5.py) — STATELESS step(), backtest 15/15 GREEN
- Reads 4-piece top-left (min y,x of color4) from the passed grid each call -> offset (oy,ox).
  Template shift=(oy,-ox). Renders: fixed layer (ENTRY minus pieces) + counter(x63 top-down) +
  template(hollow 5/0) + 4-piece(solid 4, but SKIP b-shape tile-centers x%3==1&y%3==1 -> stay 11).
- WIN condition NOT yet encoded (no is_goal). Blocking at walls/edges NOT encoded (untested).

## FRAMEWORK GOTCHAS (important, learned the hard way)
- Sandbox builtins are RESTRICTED: NO id(), NO print? etc. Allowed: range/len/min/max/enumerate/
  zip/list/dict/set/tuple/int/float/bool/str/sum/sorted/any/all/map/filter/reversed/round/isinstance...
  numpy is `np`. Using a banned name -> predict raises -> backtest shows kind 'error'.
- run_backtest SKIPS transition #0 and does NOT thread state through it -> a pure-state model is
  off-by-one. FIX: read piece position from the passed `grid` each step (stateless), don't rely on
  threaded offsets alone.

## LEVEL 1 (current) — WON L0 by full overlay
- Layout: wall color10 x36-38 (center x37, has color0 center-holes = decoration/FIXED).
  player solid4 x15-29 y18-29 (S/Z shape, 8 tiles). template hollow5 x45-59 y18-29 (mirror, RIGHT).
  target bshape11 x3-17 y42-53 (SAME shape as solid4, LEFT). counter x63, floor y63.
- solid4 & bshape SAME shape (pure translation, NOT mirrored). Overlay = move solid4 DOWN 8 tiles
  (dy+24) + LEFT 4 tiles (dx-12) -> [act2 x8, act4 x4].
- RISK: moving solid4 left pushes template RIGHT off the grid (x45-59 -> x57-71). Edge/blocking
  behavior UNKNOWN. Model currently assumes CLIP (may mispredict at left#2 when template hits x63).
- CONFIRMED WIN RULE (L0): player fully overlays target -> level_up (or win on last level).
- L1 PROBES: act2(DOWN)=NO-OP (#18), act1(UP)=NO-OP (#19). Vertical BLOCKED from entry. Neither
  piece is physically obstructed vertically (open bg above/below both) — so block rule is NOT simple
  collision. Testing act3(right)/act4(left) next. Whole board = 3x3 tiles; wall=column of hollow
  tiles (a-border,0-center at x37). Mystery: target is DOWN-left but vertical is locked. Maybe
  vertical unlocks after horizontal alignment, or my L1 identification/mechanic is wrong.

## L1 MECHANIC (REVISED — reflection, wall moves!) — act3 result #20
- The WALL (color10, full-height vertical strip) is what act3/act4 MOVE horizontally.
  act3 -> wall LEFT 3 (x36-38 -> x33-35). act4 -> presumably wall RIGHT 3 (untested).
- template (hollow5, RIGHT of wall) = FIXED source (never moved).
- solid4 (LEFT) = live HORIZONTAL REFLECTION of template across wall center:
  per cell (y unchanged, x = 2*wallcenter - templ_x). Wall moved -3 => solid4 moved -6 (2x).
- act1/act2 (up/down) = NO-OP (wall is full-height, can't move vertically off-grid).
- counter += 1 on a wall move (x63 top-down, same as L0).
- *** PROBLEM: solid4_y == template_y == 18-29, but target bshape is at y42-53. A vertical-wall
  reflection preserves y, so I CANNOT bring solid4 to the target's y by moving the wall alone.
  MUST find vertical control (move the template/source down 8 tiles?). Probing act5/act7/clicks. ***
- NOTE: this differs from L0 (there the solid piece moved & template mirrored, wall fixed). Unify
  later: maybe "you move the WALL; the solid piece is the reflection of a fixed source" — but L0
  backtest was green with wall-fixed/piece-moves. Recheck L0 vs L1 once L1 mechanic fully known.

## act5 = TOGGLE SELECTION (#21) — KEY!
- act5 swapped color-0 tile-CENTER markers: wall centers 0->9 (21 cells), template centers 9->0
  (8 cells). Counter +1. Positions unchanged.
- HYPOTHESIS: the color-0 centers MARK the currently-SELECTED/movable object. Initially wall was
  selected (0-centers on wall) -> act3 moved the wall. After act5, TEMPLATE is selected (0-centers
  on template) -> act1-4 should now move the TEMPLATE. This gives VERTICAL control!
- PLAN to solve L1: (template now selected) act2 x8 -> move template DOWN 8 tiles (y18->42), which
  moves reflection solid4 down to y42-53 (target's y). Then act5 (reselect wall), act3 -> wall left
  3 -> solid4 x9-23 -> x3-17 = bshape footprint -> WIN. Current solid4 x9-23,y18-29; target x3-17,y42-53.
- TESTING act2 now to confirm template moves down (and solid4 reflection follows).

## MODEL v5 = STATEFUL predict(), MULTI-WALL (backtest 95/95 green, L0-L4). CURRENT.
- Generalized to MULTIPLE walls (list): vertical (full-height col, moves x via act3/4) + horizontal
  (full-width row, moves y via act1/2). Each hollow wall is selectable. Template reflects across
  EVERY non-empty subset of walls (2 walls -> 3 reflections incl. 180deg image Rhv). All color4.
- movable = [hollow walls...] + [templates]; act5 cycles; sel = movable index. init selection =
  movable with the MOST 0-centers (walls share cross cells). _read_init reads template offsets (by
  size) + wall offsets from the clean first grid (fixes i=0 skip).
- L4 SOLVE (verified in model, win fires): template->target top-left, both walls positioned so the
  template's 180deg reflection covers target bottom-right. Plan from state after #95 (h-wall c=19):
  [act2 x3 (h-wall c=28), act5->tmpl, act1 x7 + act3 x10 (tmpl to y15-27 x12-24), act5->v-wall,
   act4 x5 (v-wall c=25)] -> WIN. 27 moves. v-wall reflection UNVALIDATED (self-check will confirm).

## (older) MODEL v5 = STATEFUL predict() (L0+L1+L2 single-wall) -- superseded by multi-wall above.
## RENDER RULES (all confirmed via L2 crossing): layer order bottom->top =
##   WALL(full bbox bar; gaps in entry were targets drawn over it) < TARGETS(11) <
##   REFLECTIONS(color4, skip target-centers) < TEMPLATES(border5 covers, center hole transparent:
##   shows target 11 below else marker 0/9) < FRAME(border col11, floor5, counter fill=12 for L2).
## Wall footprint = FILLED bounding box of color10 (was buggy: excluded x-gaps where target arms cross).
- Lazy-init: first predict of each level reads offsets/sel/counter from the (clean) grid, then tracks
  deterministically (no re-reading -> robust to render corruption when a template crosses the wall &
  its reflection overlaps it). Fixes both crossing-corruption AND L0 i=0-skip.
- Render rules: template border=color5 covers; template CENTER hole is TRANSPARENT (shows target 11
  below, else selection marker 0/9). Reflection=solid color4, skips target-centers (target shows through).
- WIN (hypothesis): every target cell covered by a reflection OR a template footprint. (L0/L1: refl only.)
- is_goal(state,grid) uses state (BFS-safe).

## L2 SOLVE PLAN (verified in model, win fires): from state after #44 (t0=sel offs(12,21)):
  [act2 x3] t0->bottom-mid(offs21,21); [act5]->t1; [act3 x12, act2 x5] t1->bottom-left(offs15,-36);
  [act5]->wall; [act1 x6] wall to center y=28 -> reflections land on top-mid & top-left -> WIN.
  = 28 moves. NOTE: deep wall-crossing render (t0/t1 straddling wall, reflection overlapping template,
  wall crossing templates) is UNVALIDATED vs reality -> self-check may halt; if so read_history+diff,
  fix render, re-backtest. If win-condition differs, halt reveals it.

## UNIFIED MODEL (v5, stateless step) — superseded by stateful predict above.
- TEMPLATE (color5 hollow, tile-center holes) = SOURCE. WALL (color10) = mirror axis (solid=fixed,
  hollow=movable-horizontally). SOLID piece (color4) = live reflection of template across wall
  center (y same, x=2c-x), drawn solid. TARGET (color11 excl x63) = fixed; reflection overlap
  hollows target tile-centers.
- SELECTION: one movable object selected, marked by color-0 tile-centers (others show color-9).
  act5 toggles selection (only if wall is hollow). Directional moves the SELECTED object 3px:
  act1 up / act2 down / act3 LEFT / act4 RIGHT. Hollow WALL: only act3/act4 (horiz); act1/act2 no-op.
- counter x63 fills per EFFECTIVE action; no-ops don't advance. WIN=reflection footprint==target.
- L0 = template selected from start, wall solid/fixed (I "moved solid4" = equivalently moved template).
  L1 = wall+template both hollow; start wall-selected; toggle to template to move it vertically.

## L1 SOLVE PLAN (verified in sim, model green): from state after #22 (template sel, dty=+3):
  [act2 x7 (template down to y42, solid4 down to target y), act5 (reselect wall), act3 (wall left 3
  -> solid4 x9-23 -> x3-17 = bshape)] -> level_up. Committing this.

## LEVEL 5 (current) — COMPLEX: 2 crossing walls (h at top y0-2 c=1, v at x21-23 c=22), 5 templates
  (color5, sizes 3,3,1,1,5 tiles), 20 target comps (468 cells = 52 tiles = 13 tmpl-tiles x 4 images).
- Model renders L5 ENTRY exactly (0 diffs) - detection consistent. movable=[h-wall,v-wall,t0..t4].
- Target symmetry axes: cv=19 (x), ch=34 (y). So walls likely -> v-wall c=19 (left 1 tile), h-wall
  c=34 (down 11 tiles). BUT: no win found with templates at entry / uniform offset / walls@(19,34).
  Per-template 'image subset target' search @walls(19,34) found ZERO valid positions => either walls
  not at (19,34), reflection off, or templates straddle axes. Templates at x42-62 (right of target x3-35).
- act2 (h-wall down) VALIDATED (model predicted it exactly). Mechanic confirmed for L5.
- SOLUTION FOUND (model win fires): walls -> h-wall c=34 (down 10 from current c=4), v-wall c=19
  (left 1). Templates offsets: t0(12,-21) t1(0,-21) t2(-3,-30) t3(-3,-12) t4(12,-45). Covers target
  exactly. Min total ~70 moves (t4 forced far). Counter would reach ~71 -- MIGHT exceed a ~63 budget!
- BUDGET UNKNOWN: counter fills x63 (63 cells). Never exceeded before. If 70>budget -> may need RESET
  (refunds budget) or a shorter path (none found - t4 forced). Watch for 'dead' near counter=63.
- Template DYNAMICS unvalidated -> committing walls+t0 first (24 moves) to validate before the rest.
- KEY L5 FIXES: (1) templates are 8-CONNECTED (diagonal-touching comps are ONE piece) - L5's
  "upper" piece = 4 diagonally-linked comps (8 tiles). (2) selection cycle order by SIZE: DESC with
  1 wall (L2/L3), ASC with 2+ walls (L5). (3) selected wall's 0-centers render OVER reflections
  (under targets). All in world_model_v5. backtest 156/156 green.
- L5 real templates: t4(5-tile) + upper(8-tile). Solution: walls h-c=34 v-c=19, t4@(12,-45),
  upper@(36,-21). t4 already placed; upper: down12+left7 -> WIN (counter 53, under budget).
## LEVEL 7 (LAST!): 2 walls (h-c16,v-c10), 2 templates (7-tile t0 anchor(21,21), 8-tile t1 anchor(39,39)),
  target = 4 corner-brackets, ~4-fold about (y34,x37) with 16 asymmetric cells (relaxed win).
  Solution: walls h-c=34 v-c=37, t0@(-12,27), t1@(-21,-27) -> WIN (47 moves, counter 47). win flag
  =True (lvl>=7 => game win, not level_up). Plan committed. THIS WINS THE GAME.

## LEVEL 6: 2 walls (h-c16, v-c10), 2 templates (9-tile t0 anchor(39,51), 14-tile t1 anchor(48,15)),
  target 42 tiles, 180deg-symmetric about (y22,x37) [NOT 4-fold]. NO exact solution exists (2 walls
  give 4-fold reflections but target is only 180deg) => WIN must be relaxed (target SUBSET covered,
  extra color4 on bg OK). Solution: walls h-c=22 v-c=37, t0@(-36,-6), t1@(-45,9) -> WIN (46 moves).
  Plan committed. If it DOESN'T win -> win is stricter than subset; reconsider (but exact impossible).

## LEVEL 4 (cleared) — TWO CROSSING WALLS (double reflection)
- Walls (color10): HORIZONTAL y15-17 (SELECTED, 0-centers at y16) + VERTICAL x9-11 (not selected,
  9-centers). They cross at (x9-11,y15-17). My single-wall model is BROKEN for L4 (bbox=full grid).
- 1 template (color5) at x42-56 y36-50 (11 tiles, zigzag). Target (color11): big shape x12-38 y15-41
  (~21 tiles) + 2 tiny 1-tile targets at corners (x36-38 y15-17; x12-14 y39-41). NO color4 reflections
  visible yet (template far from both walls -> reflections off-grid).
- Target has 180deg ROTATIONAL symmetry => template reflects across BOTH walls (h-flip + v-flip =
  4 images: T, Rh, Rv, Rhv). Target likely = template + reflections positioned to cover it.
- Template TOP-LEFT 5x5 quadrant of target EXACTLY == template shape. So template covers part; reflections cover rest.
- PLAN: probe to confirm (act5 cycle = h-wall/v-wall/template?; move h-wall to see reflection).
  Then EXTEND model: two walls, reflect template across each selected-movable wall; win=all target covered.
- act5 cycles among selectable (hollow) objects. Both walls hollow? v-wall has 9-centers (hollow, selectable).

## LEVEL 2 (was current) — HORIZONTAL wall, multiple templates/targets
- HORIZONTAL wall color10 at y48-50 (center y49), spans width except x33-35 (b-arm crosses it).
  Wall has color-0 centers at y49,x%3==1 => WALL is SELECTED. (horizontal wall -> moves VERTICALLY.)
- 2 hollow templates (color5, 595 centers=9=not selected):
    LEFT L-shape 7 tiles: arm x12-14 y21-32 + foot x12-23 y30-32.
    RIGHT 6 tiles: top bar x45-56 y27-29 + foot x48-53 y30-32.
- 4 solid targets (color11): top-left x9-20 y9-14 (6t), top-mid x33-44 y3-14 (7t, Gamma),
    bottom-left x9-20 y42-47 (6t), bottom-mid x33-44 y42-53 (7t, Gamma).
- 7-tile mid targets are the VERTICAL FLIP of the L template => reflection across the HORIZONTAL
  wall (vertical flip) is the mechanic. NO color4 reflection piece is drawn in entry (unlike L0/L1).
- Tile counts: LEFT template(7)~mid targets(7); RIGHT template(6)~left targets(6).
- HYPOTHESIS: like L1 but horizontal axis. Move wall (up/down) and/or templates; template's
  reflection across wall must overlay targets. Unknowns: is reflection drawn? do both template+
  reflection need to hit targets? PROBING act1(up) to move wall & look for reflection appearing.
- Current model is WRONG for L2 (assumes vertical wall). Will rework after probing.
- CONFIRMED (#32 act1=up): wall SELECTED, act1 moved horizontal wall UP 3 (y48-50->y45-47). This
  REVEALED color4 reflections = VERTICAL FLIP of each template across wall center_y: refl cell =
  (2*cy - ty, tx), drawn SOLID color4, clipped to grid AND skips floor(y63)/border(x63)/target-centers.
  Left refl x12-23 y60-62, right refl x48-53 y60-62. Counter fills with color12('c') in L2 (not 5).
- RENDER VALIDATED in run_python: reproduces entry(diff0) AND after-act1(diff0). Reflection =
  flip templates across horizontal wall; wall moves vertically (act1 up/act2 down); act3/4 = wall no-op(full width).
- STILL UNKNOWN: act5 selection cycle (wall<->t0<->t1?), do templates move independently, WIN condition.
  Probing act5 to see selection cycle. Then move a template. Then land a reflection on a target to see win.
## L2 SOLUTION HYPOTHESIS (worked out geometrically)
- Target shapes: top-mid=Gamma (matches t0 REFLECTION), bottom-mid=L (matches t0 TEMPLATE);
  top-left=foot-top+bar-bottom (matches t1 reflection), bottom-left=bar-top+foot-bottom (matches t1 template).
- Reflection axis must be at tile-center y (c%3==1). Integer/aligned solution: move each TEMPLATE
  DOWN onto its matching BOTTOM target (t0->bottom-mid x33-44 y42-53; t1->bottom-left x9-20 y42-47),
  and set WALL center y=28 -> each template's reflection lands EXACTLY on its matching TOP target
  (t0refl->top-mid, t1refl->top-left). => all 4 targets covered (2 by templates, 2 by reflections).
  => Templates MUST CROSS the wall (from y21-32 down to y42-53).
- t0 move: right 7 tiles (x12->33), down 7 tiles (y21->42). t1: left 12 (x45->9), down 5 (y27->42).
  wall: up to c=28 (from c46 => up 6 tiles = act1 x6, when wall selected).
- WIN condition UNKNOWN (maybe all targets covered by refl OR template). Current model win=all-tgt-in-refl
  (wrong, won't fire). Discover empirically.
- MODEL BUG (stateless): when a template crosses the wall, its own reflection overlaps it and the
  render draws reflection(color4) over template(color5) -> _read loses the template (comp size wrong).
  Need reality's crossing behavior first, then fix render (maybe template drawn over reflection, or
  crossing blocked). PROBING: move t0 right7+down7 toward bottom-mid; self-check halts at the wall
  crossing (~move #13) -> observe: does t0 cross? does reflection overlap it? blocked?

## OLD GENERAL MODEL notes (superseded):
- player=color4, target=color11(excl x63), template=color5(excl border/floor)+color0-adjacent-to-5.
- offset from color4 bbox corner. mirror: template shift=(oy,-ox). counter=color5 count at x63.
- overlap hollows target tile-centers (x%3==1&y%3==1 stay 11). is_goal/win = footprints equal.

## GOAL hypothesis
- b-shape (color11 solid, arm-LEFT) fixed at x51-59 y45-53. 4-piece is arm-LEFT solid too.
- Likely goal: overlay 4-piece exactly onto b-shape footprint (template simultaneously hits b-shape's
  mirror location x3-11 y45-53). From 4-piece@x39-47,y15-23: need +12x(4*act3 right)+30y(10*act2 down).
- UNCONFIRMED: is b-shape a socket(win on overlay) or an obstacle(blocks)? Test by moving toward it.

## Open questions
- Blocked-move behavior: does counter still fill? does piece stay? (not seen yet)
- Collision with wall/border/b-shape? (not seen yet)

## Current plan
- Probe actions one at a time (no model yet). Start action 1.
