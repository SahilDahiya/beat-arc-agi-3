# Notes

## LEVEL 6 (current) — full 122-action plan SIMULATED TO LEVEL_UP, saved in plan6.json
TWO SELECTABLE (outline-14) TOKENS: V = vertical 1x2 (starts selected, (18,14)) and
T = horizontal 2x1 (digit 5, (11,17)). Either can be clicked; the OTHER can then be LAUNCHED.
That is the level's key: a token is only "the pusher" while it is the selected one.
REGIONS (walking; row12 is wall c6-20, rows15-16 wall c0-7, row6 wall c0-10 except c11):
  Y = rows13-20 (both tokens start here; V's frame (9,15),(9,16) is here)
  X = rows7-11 + middle chamber rows2-5/c8-12 + top-right room rows2-5/c14-20
      (T's frame (8,8),(9,8) + the plus-frame centre (4,13) are here)
  Z = row0 + rows1-5/c0-6  — SEALED. The PLUS lives here. Nothing can walk in or out.
X and Y are DISCONNECTED for walking. Everything crosses by LAUNCH (launches pierce walls).
Shape matters: V (1 wide) can pass the 1-cell gap (11,6); T (1 tall) can cross row 10 at c6,7.
V cannot cross column 16 (rows 7-12 wall) -> V can never reach the top-right room.
ROUTE: V bumps T UP -> T lands (11,11) in X. V rides G2's UP-muzzle fire -> X.
  T (only T can reach the top-right room) bumps G1 LEFT -> (10,2). T then goes and WAITS at
  (4,7) in the left column BEFORE the plus arrives (once the plus sits at (4,9) it plugs
  (4,10) = the only row-10 crossing, locking T out).
  V (only V is 1 wide enough to stand at (12,2)) bumps G1 LEFT again -> G1 lands in Z at
  (5,2); its DOWN-muzzle beam (5,4),(6,4) hits the plus -> fires the plus down to (4,9).
  T bumps the plus DOWN: it OVERSHOOTS the frame (k=9 passable) and lands at (4,18) in Y.
  T bumps V down into Y; V walks under the plus and bumps it UP 5 -> exactly onto the frame.
  V walks to its frame; T walks to its frame -> LEVEL_UP.
BUDGETS[6]=200 (pinned by fitting zeros=round(64n/B) to 14 observed (n,zeros) pairs).
*** LAUNCH DISTANCE = v, MINUS 1 IF THE LAUNCHED TOKEN IS THE *CURRENTLY SELECTED* ONE. ***
Proven by two frames that finally pinned it (model 340/340 green on ALL levels):
  - L0 #21: a WORN token (displaying 4, i.e. v=5 and ever-selected) that was NOT selected got
    bumped and flew 5 = its full v.  So wear/being-ever-selected does NOT shrink the launch.
  - L4/L5/L6: the gauge fired the token that WAS SELECTED, and it flew v-1 every time
    (L6: V has v=5, displays 4 after deselection, and was fired exactly 4).
So DISPLAY and LAUNCH follow DIFFERENT flags:
    display = 0 if currently selected, else v - (1 if EVER selected)
    launch  = v - (1 if CURRENTLY selected)
START_VALUE_BY_LEVEL = intrinsic v of the entry-selected token = {4:4, 5:6, 6:5}.
=> CONSEQUENCE FOR PLANNING: the same token flies a DIFFERENT distance depending on whether it
   is selected. Bumping an unselected token = full v; a gauge firing the selected token = v-1.
   Never reuse a launch distance measured in one selection state for the other.
Current plan: replan from live state each time (plan6b.json is stale after this fix).

## *** GAUGE FIRING — SOLVED. Model is 281/281 GREEN on ALL levels. ***
Every earlier prose theory here was wrong ("shoves ~5 away", "has range >1", "always down").
The real rule, and it is SIMPLE — firing is just A BUMP DELIVERED BY THE GAUGE:
- The colour-13 region is a FUSE and it marks the MUZZLE (the side it sits on).
  row/end (13 at bottom) -> fires DOWN;  row/start (13 at top) -> fires UP;  ditto L/R.
- On WRAP (k=1 -> kmax) the gauge LAUNCHES any token IMMEDIATELY ADJACENT (RANGE EXACTLY 1)
  on its MUZZLE side, away from itself, through the SAME launch rule as a bump: fly >= v,
  overshoot through walls, k<v fallback, shove occupants.
  => non-muzzle sides are SAFE, and so is distance >= 2. Standing "above" is only dangerous
  if the muzzle points up AND you are touching it.
- DISTANCE = THE LAUNCHED TOKEN'S v, not the gauge's. L5 token v=5 (thrown 5); L4 token v=3
  (thrown 3). That single fact explains the L4-vs-L5 discrepancy that blocked me for ages.
  A selected token renders 0, so its v is invisible -> pin it per level (START_VALUE_BY_LEVEL).
- Fire resolves AFTER the move (L5 s19: the token only entered the beam post-move).
- MOVES burn the fuse; CLICKS DO NOT. BLOCKED moves DO -> the phase-alignment tool.
- A FULL gauge is uniform, so pixels pin neither axis nor side: fall back to GEOMETRY
  (the muzzle faces the only PASSABLE side), then re-read from the live grid once it burns.
- Clicking a gauge does NOT select it: only OUTLINE (14) tokens are selectable.
- BUDGETS: L0=100 L1=128 L2=100 L3=128 L4=100 L5=150.  (150 sat outside the old
  BUDGET_RANGE(96..145), which silently corrupted EVERY level-5 bar prediction — the real
  cause of the endless "harmless" mispredicts. Never let a budget fall off the range.)

## LEVEL 5 layout (origin (0,0))
- TOP r1..r9 (SPLIT by a BG column at c10) | wall r10,r11 | MIDDLE r12..r16 (full width,
  c1..c19; wall r17 except c0/c20) | BOTTOM r18..r20.
- Gauges: (8,5) & (11,5) in the TOP, muzzle DOWN (top->middle one-way chutes);
  (14,15) in the MIDDLE, muzzle UP  == THE ONLY ELEVATOR back into the top.
- The e-token is the ONLY selectable token => always the pusher => it can never be launched
  by a bump. The gauges' FIRE is therefore the sole way across the r10/r11 wall.
- Ferry the middle gauge sideways with bumps (5 cells each), then stand on its muzzle cell
  at the fire tick to ride it up into whichever half of the top you need.
## Tokens DO overwrite frame-outline pixels (a frame cell is passable).

## *** TWO-TONE (12/13) TOKENS ARE COUNTDOWN GAUGES ***
- The colour-13 region shrinks by ONE UNIT per action and WRAPS to full when it hits 0.
    k(n) = ((k0 - 1 - n) % kmax) + 1
  Axis/side detected from the entry pattern (corridor blob: rows, d at the BOTTOM, k0=4,
  kmax=6; frame-side blob: cols, d at the LEFT, k0=1, kmax=3).
- Observed: corridor d = 4,3,2...  frame d = 1,3,2 (i.e. 1 -> 0 -> wraps to 3 -> 2).
- They are still real TOKENS (obstacles, launchable) — only their FILL animates.
- Do not mistake an animated HUD/gauge for geometry (same trap as the level-0 bar).

## LEVEL 4 — two-tone tokens (colours 12/13)
- Tokens can be NON-outline with a multi-colour pixel fill and NO digit. Generalised:
  a token is OUTLINE only if colour 14 is present; otherwise store its raw PIXEL PATTERN
  and redraw it verbatim. render(entry)==ENTRY confirms it.
- A token can be drawn OVER part of a frame's border -> the frame's outline is not a closed
  ring, so the flood-fill leaks. Fix: treat TOKEN pixels as barrier AND exclude them from
  the interior.
- is_goal must use the TRACKED STATE, not a re-parse: two TOUCHING tokens merge into one
  component under parse_tokens, so a token that just landed beside another vanishes.
  (is_goal(state, grid) form.)
- Layout: e-token trapped at the bottom of a walled channel (c=8,9), a 2x2 plug above it,
  ONE 1x1 frame at (16,9). Bump the plug UP (it overshoots out of the channel), walk up and
  right onto the frame. 17 actions.

## *** LAUNCH — FINAL RULE (174/174) ***
- A bumped token flies AT LEAST v (=5): scan k=v, v+1, ... for the first PASSABLE landing
  (overshoot; passes THROUGH walls, intermediate cells never checked).
- *** IF NO k>=v LANDING EXISTS, it goes AS FAR AS IT CAN: scan k=v-1 down to 1. ***
  This fallback branch had NEVER fired in 177 transitions, so nothing could contradict
  "it just doesn't move" — and that wrong default made L3 provably unsolvable.
  It is exactly what lands the plus on its frame: from (12,5) an up-launch has no k>=5
  landing, so it takes k=2 -> (12,3) = the plus frame.
- LANDING IGNORES OCCUPANCY; occupants are SHOVED along the launch direction to the first
  free passable cell (can cross a wall). Blockers do NOT extend a launch.
- A BLOCKED move still COSTS an action (the bar ticks). This bug hid for ages because the
  bar often rounds to the same value.
- SOLID tokens are NOT selectable (tested twice, incl. same-region).
- Walls DO block walking (tested).
- LESSON: when a green model says a human-designed level is IMPOSSIBLE, hunt for the rule
  branch that has never once fired — that is where the wrong default is hiding.

## (resolved) L3 IMPASSE
- Model (170/170 green) says L3 is UNSOLVABLE even from entry: BFS over the full state
  space (450k states) never reaches the plus frame. The plus can only sit at rows
  5/10/15/17 — never row 3. So a rule is WRONG, not the level.
- SHOVE (confirmed): a launch's landing IGNORES occupancy; the launched token lands by
  passability alone and any token in the landing is SHOVED along the launch direction to
  the first free passable cell (it can cross a wall). Proof: plus (12,15)->(12,10) landed
  on E1 at (12,10), which was shoved to (12,8).
- UNTESTED ASSUMPTION being probed now: *** CAN A TOKEN WALK ONTO A WALL CELL? ***
  I have NEVER walked into a wall in any level, so the backtest could never contradict
  "walls block". Launches already pass THROUGH walls. If walls are walkable, L3 is easy.

## *** LAUNCH = OVERSHOOT (final rule; 140/140) ***
- A bumped token flies EXACTLY v cells. If that landing is INVALID (wall/bg/off-field/
  OCCUPIED) it KEEPS GOING in the same direction to the FIRST VALID landing.
  It NEVER travels less than v. Intermediate cells are never checked (it passes through
  walls) -- only the LANDING matters.
- Both earlier rules were wrong: "exactly v" (L0-L2 all had a valid landing at k=v) and
  "furthest valid <= v" (the clip). Do NOT revive either.
- ALL tokens (outline AND solid) have intrinsic 5. The L3 plus's "7-cell" jump was v=5
  OVERSHOOTING past the 2-row wall. There is no per-token value variation so far.
- *** BLOCKERS ARE A MECHANIC ***: a landing must be UNOCCUPIED, so parking a token on the
  k=v landing forces the launched token to OVERSHOOT further. This is the only way to get
  displacements that are not the "natural" landing — it is how L3 is solved.
- Consequence: if a target looks unreachable, check whether a BLOCKER can extend a launch.

## *** LAUNCH VALUE — pusher vs launched (L3) ***
- The launch distance is the **LAUNCHED** token's own value, NOT the pusher's.
  Proof: a value-5 token pushed the L3 plus and it flew 7.
- OUTLINE (14) tokens display their value. SOLID (11) tokens display NOTHING, so their
  value must be MEASURED by bumping once. L2 plus = 5 but L3 plus = 7 — THEY DIFFER.
  Never assume 5 for a solid token; measure it, then set SOLID_VALUE_BY_LEVEL.
- Combined with the CLIP rule this explains everything: the L3 plus's "5-cell" left push
  was really v=7 clipped to 5 by the field edge.

## GAME RULES (confirmed; level 0 cleared with these)
- LATTICE: 3x3 px cells, origin (0,0). cell(c,r) -> px x=3c..3c+2, y=3r..3r+2.
- TOKENS: rectangular 'e'(14) outlines, w x h CELLS. Rendered 3w x 3h px; the DIGIT is a
  w x h px block at pixel offset (+w,+h) inside the box.
- Each token has TWO quantities (the crux):
    * INTRINSIC value (IMMUTABLE) = distance in CELLS it flies when LAUNCHED.
    * DISPLAYED digit = intrinsic - (1 if it has EVER been selected else 0).
      The SELECTED token displays 0 instead.  *** MOVES DECAY NOTHING. ***
      (Dead ends, do NOT revive: "digit decays per move"; "vertical costs / horizontal
       free"; "(2n+1)//3"; "launch slides until it hits a frame". All fit for a while, all
       false.)
    * read an intrinsic off the grid: displayed + (1 if ever selected else 0).
- ACTIONS: 1=U 2=D 3=L 4=R move the SELECTED token 1 cell.
    Bumping another token does NOT move the selected one -> the bumped token LAUNCHES.
    *** LAUNCH = the bumped token flies UP TO its intrinsic v cells and lands on the
    FURTHEST VALID landing (try k=v down to 1). It passes THROUGH walls (intermediate
    cells are never checked) but the LANDING must be fully passable and unoccupied. ***
    "Exactly v" fitted levels 0-2 only because every landing there was valid at k=v.
    Level 3 needs the CLIP: two k=2 pushes are what produce dr=-14, which no multiple of 5
    could. If a level looks unsolvable under "exactly v", suspect the clip.
    6 = click a token to SELECT it (old one reveals its digit). Every action costs 1 tick.
    => CROSS A WALL: launch a token over it, then CLICK it to take control on the far side.
- FRAMES: colour-4 rectangular outlines. Interior = a w x h cell region matching a token's
  SHAPE.  GOAL (is_goal): every frame's interior exactly covered by a token.
- BAR (row 63): zeros = round(64*n/BUDGET); n = actions since level start/RESET.
  *** THE BUDGET IS PER-LEVEL *** — PINNED: L0=100, L1=128, L2=100. Unknown levels carry a
  feasible SET, pruned against the observed bar each step (a bar mispredict is harmless:
  actions still execute, and the observation prunes the set).
- ANALYSIS GOTCHA: in events.jsonl the LEVEL-CLEARING action is recorded under the NEW
  level, so grouping actions by a['level'] puts one bogus leading entry in each level's
  series. That off-by-one made the budgets look infeasible. Drop the first entry.
- All tokens seen so far have intrinsic 5 (START_VALUE_BY_LEVEL: selected token's value is
  hidden at entry; assume 5, verify on the first click).

## CONTACT HIGHLIGHT (corrected)
- If ANY token touches a SIDE of the SELECTED token, that ENTIRE side renders as 0
  (not just the touching cells). Level 0 could not distinguish this (all tokens were 1x1);
  level 1 proved it: a 1x1 token above the LEFT half of a 2x2 token lit the 2x2's WHOLE
  6px top edge.

## MODEL
- world_model_v5.py is fully general (multi-cell tokens). Backtest 27/27 GREEN.
- Sanity check that caught bugs: _render(ENTRY state) must equal ENTRY_GRID exactly.
- CAUTION: parse_tokens merges two TOUCHING tokens into one component -> never use it to
  resync mid-level; resync by comparing OCCUPIED CELLS (cells containing a 14).

## LEVEL 3 (current) — wall band splits board; plus must cross it
- origin (2,2). TOP region r2..11 (r2..5 only c11..18); WALL rows r12,r13; BOT region
  r14..18, c1..13.
- Tokens: E1 1x1 @(6,9) SELECTED, E2 1x1 @(9,10) [both TOP]; solid PLUS center (7,17) [BOT].
- Frames: PLUS-frame center (12,3) [TOP], 1x1 @(16,9) [TOP], 1x1 @(12,17) [BOT].
- *** SOLID TOKENS ARE NOT SELECTABLE *** (proven: clicked the plus centre, nothing
  happened, the previously selected token still showed 0). A click ALWAYS costs an action.
  => the plus can ONLY be moved by being LAUNCHED (bumped).
- PUZZLE: the plus needs d=(+5,-14). No single launch distance v divides BOTH 5 and 14
  (gcd=1), and v must be >=5 to clear the 2-row wall. So the level is only solvable if
  DIFFERENT PUSHES GIVE DIFFERENT DISTANCES.
- *** UNRESOLVED AMBIGUITY (never testable until now) ***: is the launch distance the
  LAUNCHED token's intrinsic, or the PUSHER's? Every launch so far had BOTH = 5.
  E1 (selected at entry, value HIDDEN) pushed E2 exactly 5; E2 displays 5.
    - if E1's revealed digit is 4 (intrinsic 5): still ambiguous.
    - if E1's revealed digit is 6 (intrinsic 7): the PUSHER theory is refuted.
  If the distance is the PUSHER's and E1=7, the level solves as: E2 pushes the plus RIGHT 5,
  then E1 pushes it UP 7 twice -> centre (12,3) = the plus frame. That fits perfectly.
- EXPERIMENT COMMITTED: click E2 (reveals E1's digit), walk E2 to (9,17), bump the plus
  LEFT (safe for any v in 1..5) to measure the actual launch distance.

## (cleared) LEVEL 2 — plus/cross shapes, open room (no walls)
- NEW: tokens can be ANY CELL-SET (not just rectangles) and come in 2 render styles:
    * OUTLINE (14): rectangle, w x h box + digit block.
    * SOLID (11): every cell filled, NO digit (the plus/cross shapes). Intrinsic still 5.
- NEW: the LATTICE ORIGIN differs per level! L0/L1 = (0,0); L2 = (2,2). Detect it from the
  entry grid (token pixels sit at x,y = origin + 3k).
- Frames can be plus-shaped too -> parse a frame's interior by FLOOD-FILLING inside its
  colour-4 outline (works for any shape).
- Level design confirms intrinsic 5: plus P2 center (7,12) -> its frame (12,12) is exactly
  +5; plus P1 (17,7) -> its frame (7,7) is exactly -10 = two 5-launches.
- GOTCHA: the playfield is only c=1..18, r=1..18. I planned to push P1 left from (19,7),
  which does NOT exist -> E got blocked and bumped P1 DOWNWARD instead. Push from the
  arm-adjacent cell (18,6) instead. ALWAYS simulate the plan before committing.

## (cleared) LEVEL 1 — shape-matching, 3 sealed regions
- Regions (walking cannot cross; only LAUNCH can):
    R1 top-left  c0..6,  r0..7    <- frame F_B (1x2 @ c3,r3-4)
    R2 bot-left  c0..6,  r10..20  <- frame F_C (2x2 @ c2-3,r14-15)
    R3 bot-right c10..20,r10..20  <- all 4 tokens + F_A (2x1 @c18-19,r13), F_D (1x1 @c17,r17)
- Tokens: A 2x1 @(13,11) | B 1x2 @(11,14) | C 2x2 @(14,15) | D 1x1 @(12,18) SELECTED.
- Key geometry:
    * C can only land inside R2 if launched LEFT from cols (10,11)  -> exactly c=10.
    * B can only land inside R1 if launched UP from rows (10,11) while in R2.
    * So C must be the PUSHER for B's up-launch (only other token that can reach R2).
- 51-action plan simulated: all 4 tokens land on their frames, level_up fires. COMMITTED.
