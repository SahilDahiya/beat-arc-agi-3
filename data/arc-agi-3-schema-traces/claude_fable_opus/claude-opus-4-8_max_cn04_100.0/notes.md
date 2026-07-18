# Notes — living scratchpad

## RENDERING (confirmed)
- 64x64 cells, background = 10. Everything is drawn on a **3x3 BLOCK lattice**, offset (2,2):
  block (bx,by) = cells x=2+3bx..4+3bx, y=2+3by..4+3by  => 20x20 logical board.
- HUD budget bar: row y=0, x=16..47 (32 cells). colour 4 = remaining, 0 = consumed, fills
  contiguously from the LEFT.
  **BUDGET IS PER-LEVEL AND NOT A FORMULA.** Fitted from the bar: L0=[74,75], L1=100 (exact),
  L2=[123,128], L3=[123,128]. The formula 75+25*level is REFUTED (it wanted 150 for L3, but
  L3's bar forces B<=128). Use LEARNED_BUDGET in the model + the exact [lo,hi] narrowing, and
  just refit whenever a new level's bar disagrees. The budget is never the binding constraint
  (plans need ~30 moves of ~125) — a wrong B only costs a HALTED PLAN, never a loss.
  It is a **PROPORTIONAL GAUGE of a PER-LEVEL move budget B, not a per-move counter**:
      used_cells = round_half_up(m * 32 / B)  ==  (64*m + B) // (2*B)
  (m = total actions this level; every action costs 1, rotations included.)
  **B IS PER LEVEL**: level0 B in {74,75} (2 pieces), level1 B in [86,128] (4 pieces).
      => B = 25 * (n_pieces + 1)   gives 75 and 125. Both consistent. ENCODED.
  Safety net (encoded): the model also NARROWS an exact interval [lo,hi] for B from every
  observed (m,used) pair  [B > 64m/(2u+1); if u>=1, B <= 64m/(2u-1)]  and clamps the guess
  into it -> a wrong formula self-corrects after at most a halt or two.
  !! Two HUD traps already cost me halted plans:
     (1) "floor(m/2)" fit the first 3 points then broke at m=8.
     (2) BUDGET is NOT global — level 1 uses a different B than level 0.
     When a plan halts and the GRID is right, always suspect the HUD first.

## ACTION SEMANTICS (all confirmed by walked transitions)
- 1 = move key UP 1 block, 2 = DOWN, 3 = LEFT, 4 = RIGHT.
- 5 = **ROTATE 90 deg CLOCKWISE**, and the key's bounding-box TOP-LEFT corner is PRESERVED
  (the bbox just transposes h<->w around that anchor). Verified exactly.
- 6 = click, still untried (not needed so far).

## GOAL — THREE HYPOTHESES KILLED (level 4). THE ZCELL IS THE ONLY THING LEFT.
1. "bond every connector"  -> IMPOSSIBLE: connector geometry alone forbids it (verified even
   with NO collision constraints, and with reflections, and with 3+ per cell).
2. "no visible colour-8 cells" -> REFUTED by experiment (bonded the active piece's 2 connectors,
   zero 8s on screen, no advance).
3. "all pieces CONNECTED via pairwise bonds" -> REFUTED by experiment (4 pairwise bonds spanning
   all 4 pieces, no 3-way junctions, no advance).
4. **THE ZCELL IS A PASSABLE HOLE** (CONFIRMED): piece3's CONNECTOR entered (7,8) — my solid-BODY
   rule wrongly blocked it. It rendered 8, NOT 3, so it is NOT a socket and does NOT bond.
   Model fixed: ZCELL is passable (anything may sit on it); backtest 172/172 green.
   Connector sets RE-READ from the live active frames and CONFIRMED: p0=2, p1=3(+1 ZCELL),
   p2=3, p3=2. So the data is right and "all connectors bonded" is genuinely impossible.
5. "fill the hole with a BODY cell" -> REFUTED (piece3's body sat on (7,8), no advance).
6. "bond every connector" is impossible even with COLLISIONS REMOVED ENTIRELY — proven 3 ways.
=> KEY REALISATION: my two refutations never overlapped!
   - the "0 visible 8s" test had p0 fully bonded but the pieces NOT all connected;
   - the "connected" test had all 4 connected but p3 ACTIVE with 1 unbonded connector (1 visible 8).
   ...THE CONJUNCTION IS ALSO REFUTED: achieved all-4-connected AND zero visible 8s (piece1
   active with all 3 of its connectors bonded) — NO ADVANCE.
## LEVEL-4 SCOREBOARD (all REFUTED / IMPOSSIBLE):
   1 all connectors bonded  - IMPOSSIBLE (proven 3 ways incl. with collisions REMOVED entirely)
   2 zero visible 8s        - refuted      3 all pieces connected   - refuted
   4 connected AND 0 visible 8s - refuted  5 connector on the hole  - refuted (renders 8)
   6 body on the hole       - refuted
   Decomposition re-verified from ENTRY_GRID: exactly 4 components; the ZCELL really is part of
   piece1 (touches (6,8)=colour 11). Connector sets re-read from live ACTIVE frames: 2,3,3,2.
   7 bond ON the hole (2 connectors coincide there) - refuted (rendered 3 as predicted, no advance)
## !! SEARCH-TIMEOUT TRAP: my first "connected AND hole covered" search printed 0 configs, but it
   had TIMED OUT (the `break` only exited the inner loop). Redone with bond-chaining: 275 configs
   exist. NEVER trust a 0 from a search that hit its time cap — re-run it a faster way.
   8 TRIPLE conjunction (all connected + hole BONDED + zero visible 8s, all at once) - REFUTED.
## => THE WHOLE BOND/CONNECT/HOLE FAMILY IS EXHAUSTED. The goal is something else.
## PIECE1 MOVES NORMALLY (tested after RESET) — it is NOT an anchor. Hypothesis dead.
## SEARCH VERIFIED CORRECT: the EXACT level-4 search code rediscovers level-3's winning assembly
   from all 4 pins, and returns 0 for level 4. So 'all connectors bonded' really is impossible
   under my rules, and the connector data (2,3,3,2) is confirmed by direct observation.
   => A RULE is wrong, not the data.
## ===== LEVEL 5 (5 pieces, bg=9). Budget B>=193 (set 200). Model 370/370 GREEN. =====
##   *** TWO pieces carry a MASK-HIDDEN ZCELL -> BOTH GROW on action 5 (info['zis']=[2,4]) ***
##   piece0: col14, 14 cells, 3 conn (ACTIVE at entry)
##   piece1: col12, 10 cells, 2 conn (3,15),(4,17)          - no zcell
##   piece2: col11,  7 cells, 2 conn (6,8),(8,6)  + ZCELL (10,7)   <-- GROWS
##   piece3: col10,  7 cells, 2 conn (12,1),(17,2)   - no zcell  [CONFIRMED]
##   FULL MAP COMPLETE. degrees (3,2,2,2,3)=12 EVEN at g=0, but NO perfect matching exists at
##   g2=g4=0 (searched: all-bonded + no-body-overlap, growables pinned to ori0). => MUST GROW.
##   Growable pieces CANNOT ROTATE (action 5 grows them) -> pieces 2 and 4 are LOCKED at ori 0.
##   !! GROWTH GEOMETRY DOES **NOT** TRANSFER ACROSS LEVELS/PIECES -- CONFIRMED.
##   Level 4: tip moved DOWN, arms alternated L1,R4,L1,R3, tip consumed at g=4.
##   Level 5 piece2: tip moves RIGHT and a NEW CONNECTOR drops BELOW the old tip. g=1 observed:
##      O  / ## / O# / # / ##. / O      (10 cells, 3 conn, tip (4,3))
##   _grow_shape is now TABLE-DRIVEN (LEARNED_GROWN[(lvl,piece)] = {g: cells}) from real frames.
##   (5,4) has an EMPTY table on purpose: piece4's growth is UNOBSERVED, so the model must not
##   silently reuse level-4's arm rule. LEARN IT before using it in any search.
## *** LEVEL 5 SOLVED: g2=5 (TERMINAL) + g4=3 (TERMINAL) -> perfect matching, 16 connectors ***
##   BOTH growable pieces must be grown to COMPLETION (tips consumed) -- exactly as on level 4.
##   piece2 conn by stage: g0=2 g1=3 g2=3 g3=4 g4=4 g5=6(TIP CONSUMED). The FINAL growth added
##   TWO connectors at once. Nothing short of the terminal shape admits a matching.
##   => GENERAL RULE: on a level with growable pieces, GROW THEM TO COMPLETION and search there
##      FIRST. Intermediate stages are usually decoys.
## (older) PIECE2 stages: g0=2 g1=3 g2=3 g3=4 g4=4. Tip STILL ALIVE.
##   Searched g2 in {3,4} x g4 in {0..3} (pin=2, all orders, both win clauses): NONE.
##   On LEVEL 4 the winning shape was the TERMINAL one (tip CONSUMED). Piece2 is not there yet,
##   so KEEP GROWING one press at a time, reading + encoding each stage, until the tip is gone.
##   TRAP HIT AGAIN: a str.replace() silently failed to insert stage g=4 -> the search crashed
##   instead of using stale data (lucky). ALWAYS assert the stage count after encoding.
## (older) PIECE2 CONNECTORS BY GROWTH: g0=2, g1=3, g2=3, g3=4  -> ODD growths ADD a connector.
##    At g2=3 the TOTAL is 3+2+4+2+3 = 14 = EVEN, so a perfect matching is possible again.
##    Searched g2=3 x g4=0..3 (all pins, all orders): none. But piece2's TIP IS STILL ALIVE at
##    g=3, so its growth is UNFINISHED -- keep growing and reading each stage.
##    Growth cap is now PER-PIECE (= last observed stage), never the global GROW_MAX.
## (older) NO matching over g2=0, g4=0..3, and
##   the search is TRUSTWORTHY — it rediscovers level-4's known win from all pins/orders.
##   So a MECHANIC IS MISSING, not the level. Connector counts: p2 g0=2, g1=3, g2=3 (only the
##   FIRST growth adds one); p4 stays 3 always. Totals: 12 (g2=0) or 13 (g2>=1, ODD).
##   KEY LEAD: on LEVEL 4 the win used the growable piece FULLY GROWN (tip consumed) and its
##   FINAL growth ADDED a connector. Piece2's tip is still ALIVE at g=2 -> grow it to completion
##   and check whether its last growth adds a connector (total would become 14 = EVEN).
## !! PIECE4 GROWTH **CAPS AT g=3** — the tip is CONSUMED (becomes BODY) and growth terminates.
##    My widening rule was right but I EXTRAPOLATED it to g=5 and built a whole 61-action plan on
##    a shape that can never exist. 43 actions executed before the model caught it. Model now
##    caps at 3 and is 419/419 GREEN.
##    LESSON (again): NEVER feed an unobserved growth stage into a search. Verify, then use.
##    Reachable dials: g4 in {0,1,2,3}. Parity: total = 12 + g2, so g2 must be EVEN.
##    Searches with GUESSED piece2 g>=2 shapes returned "none" — UNRELIABLE, must observe first.

## (STALE — g4=5 is UNREACHABLE) LEVEL 5 SOLUTION: g2=0, g4=5 (all bonded + no body
##     overlap). K={4:0, 0:2, 1:0, 2:0, 3:1}  T={4:(0,0), 0:(3,-4), 1:(-3,7), 2:(4,-4), 3:(-1,2)}
##     PIECE4's GROWTH IS A **SPACING DIAL**: connector count stays 3, but each growth slides its
##     right leg (and that leg's connector) one further right. g4=5 is the setting that makes the
##     matching close. My first search only tried g4=0 -- far too narrow. SWEEP THE DIAL.
##     Validated widening rule vs frames g=0,1,2; model 376/376 GREEN.
##     Piece2 must be at g=0, but it is already g=1 and growth is IRREVERSIBLE -> RESET (which
##     restores g=0 AND refunds the budget AND re-scatters positions; _parse_board handles that).
##   !! EACH GROWABLE PIECE HAS ITS **OWN** GROWTH GEOMETRY -- even within one level:
##      piece2 growth: tip moves RIGHT, +1 body, and **+1 NEW CONNECTOR** below the old tip.
##      piece4 growth: tip moves RIGHT 1, +1 body, and **NO new connector** (conn stays 3 at g=1).
##   So connector totals: piece2 = 2+g2 ; piece4 = 3 + (however many its growth actually adds).
##   Parity: total must be EVEN. At g2=1,g4=1 total = 13 (ODD) -> keep growing/learning.
##   NEVER extrapolate an unobserved growth stage -- read every one from a frame.
##   piece4: col15, 16 cells, 3 conn (14,11),(14,13),(17,9) + ZCELL (18,12)  <-- GROWS
##   Connector total = 12 + g2 + g4  -> EVEN iff (g2+g4) is even. Parity is CONTROLLABLE.
##   DO NOT assume level-4's growth arms (L1,R4,L1,R3) carry over -- derive them empirically.

## (old header) LEVEL 5 =====
##   idx0 (14 cells, col14, ACTIVE at entry, 3 conn) / idx1 (10) / idx2 (7) / idx3 (7) / idx4 (16)
##   !! idx4 HAS A **MASK-HIDDEN ZCELL** at (18,12): connectors (14,11),(14,13),(17,9), colour 15.
##      A masked piece's ZCELL renders as mask-colour and is INVISIBLE in ENTRY_GRID -- it can
##      only be found by ACTIVATING the piece. So idx4 GROWS on action 5 (never rotates).
##      Encoded via LEARNED_CONNECTORS[5][4] / LEARNED_ZCELLS[5][4] / LEARNED_COLORS[5][4].
##   => ALWAYS click every masked piece on entry: it reveals connectors AND any hidden ZCELL.
##   Still to read: connectors of idx1, idx2, idx3 (and check each for a hidden ZCELL too).

## ***** WIN = ALL CONNECTORS BONDED **AND NO BODY-BODY OVERLAP** (both needed!) *****
##   PROVEN on the board: I built an all-bonded config with 7 body overlaps and it did NOT win.
##   The data fit had TWO perfect predicates and I picked the weaker one; the overlap clause is
##   real. With BOTH clauses there is exactly ONE valid assembly on level 4.
## ROUTING RULE: NEVER ROTATE A BONDED PIECE (unmodelled - it drags/derails). Always translate
##   away to break the bond FIRST, then rotate, then translate into place. piece1 never rotates.

## ***** LEVEL 4: GROWTH IS THE MECHANIC. Model 354/354 GREEN. *****
## The ZCELL piece (piece1) GROWS on action 5 (it can NEVER rotate). Arms, verified from frames:
##   growth 1 = LEFT len1, growth 2 = RIGHT len4, growth 3 = LEFT len1, growth 4 = RIGHT len3,
##   and the 4th growth CONSUMES THE ZCELL -> the piece is COMPLETE: 20 cells, 7 CONNECTORS.
## Fully grown, piece1's LEFT connectors sit at (1,0),(3,0),(5,0): COLLINEAR, SPACED 2 --
## exactly the (2,0)/(4,0) offsets that piece2's three collinear connectors require and that NO
## piece could supply while shapes were fixed. Degrees become (2,7,3,2)=14 -> 7 bonds, EVEN.
## => A PERFECT MATCHING EXISTS (piece2 triple-bonds to piece1's left arms). All the earlier
##    "all-bonded is impossible" proofs were computed on the UNGROWN piece: a variable treated
##    as a constant. THE PIECE IS THE PUZZLE.
## WIN = every connector bonded (exactly 2 per cell); burial refuted; bodies may overlap.

## (old) MODEL IS 311/311 GREEN WITH GROWTH ENCODED.
## GROWTH RULE (validated against g=0,1,2,3 exactly): the ZCELL piece grows on action 5.
##   Spine at the ZCELL column. Odd growth -> LEFT arm length 1. Even growth -> RIGHT arm whose
##   length DOUBLES (2,4,8...). The ZCELL tip moves one row down each time. +1 connector each.
##   ENCODED as: for the ZCELL piece the "orientation" index IS the growth count g (it can NEVER
##   rotate, since action 5 grows it) -> oris[g] = grown shape, g in 0..GROW_MAX.
## PIECE1 CAN NEVER ROTATE (action 5 = grow). Only pieces 0/2/3 rotate.
## Growth is BLOCKED at the board edge -> move the piece up before growing.
## Assembly search so far: 0 perfect matchings at g=2,4,6,8 (bodies allowed to overlap, which is
##   legal). Grown piece1 DOES gain left-arm connectors collinear & spaced 2 at (1,0),(3,0),(5,0)
##   -- exactly the (2,0)/(4,0) structure piece2's collinear trio needs -- so keep pushing g and
##   re-search; also re-check with piece1 PINNED at k=g (no rotation) which is the true constraint.

## ======== LEVEL 4 — THE ACTUAL MECHANIC (durable; re-read this first) ========
## ACTION 5 on the piece carrying the ZCELL = **GROW**, not rotate. (On every other piece it
## rotates normally — that is why 295 transitions stayed green.) Each press appends a new ROW
## with an ARM ending in a **NEW CONNECTOR**, and pushes the ZCELL one further down. The arms
## alternate right/left and the piece unrolls like a SPIRAL. Observed piece1 shapes:
##   g=0 (entry):        g=1:               g=2 (now):
##     #O                 #O                 #O
##    O#                 O#                 O#
##     ##O                ##O                ##O
##     .                 O#                 O#
##                        .                  ####O
##                                           .
##   connectors: 3  ->  4  ->  5     (cells 8 -> 10 -> 15)
## => piece1's connector count is NOT fixed. Degree seq = (2, 3+g, 3, 2), total 10+g.
## *** THIS VOIDS EVERY "ALL-BONDED IS IMPOSSIBLE" PROOF *** — all three algorithms assumed
## piece1 had exactly 3 connectors forever. Grow piece1 (g even keeps the total even), then
## re-run the perfect-matching search on the GROWN shape.
## WIN (fitted to all 295 states, TP=4 FP=0 FN=0, only survivor): every connector BONDED,
## none buried. Burial refuted twice.
## Other confirmed level-4 facts:
##   - NO piece-piece collisions at all; only the board edge blocks a move.
##   - A single bond does NOT drag a partner on rotation (tested: piece3 stayed put).
##   - RESET RE-SCATTERS the pieces to new positions AND refunds the whole budget.
##   - Bonds = 2 coincident connectors (render 3). Adjacency does NOT bond. 3-way piles render 8.
##   - The ACTIVE piece draws on top of everything; masked pieces hide their connectors.
## TODO: encode growth (state: per-piece growth count g; rebuild the ZCELL piece's cells and its
## 4 orientations from g), backtest to green, then search for a perfect matching with g growths.

## (old) THE ZCELL IS A GROWTH TIP. ACTION 5 ON THE ZCELL PIECE GROWS IT.
##   Probe: bonded piece1 to piece3 with ONE bond, then pressed 5.
##   - piece3 did NOT move  => a single bond does NOT drag. (The "drag" I saw was this growth.)
##   - piece1 did NOT rotate. Its shape became ori0 + an extra "O#" segment, with the ZCELL
##     pushed one cell further along:   #O / O# / ##O / O#(NEW) / .(ZCELL moved down)
##   So action 5 = ROTATE on a normal piece (why 295 transitions stayed green), but = EXTEND
##   on the piece carrying the ZCELL. Each growth adds a BODY cell **and a NEW CONNECTOR**.
##   *** THIS VOIDS THE "ALL-BONDED IS IMPOSSIBLE" PROOF *** — that proof assumed piece1's
##   connector count was fixed at 3. Piece1 can GROW connectors, so the degree sequence is
##   (2, 3+g, 3, 2) with g growths; total = 10+g, which is EVEN iff g is even. Grow piece1 to
##   fix both the parity and the geometry, then re-run the perfect-matching search.
##   Earlier "growth" observations were 1 and 2 presses of 5 => shapes with 10 and 15 cells. Fits.

## RESET **RE-SCATTERS** THE PIECES — it does NOT restore the entry layout!
##   After RESET the 4 pieces sat at brand-new positions (piece0 (1,15), piece1 (4,7),
##   piece2 (12,1), piece3 (15,15), all ori 0) and the budget was fully refunded.
##   => poses must be PARSED FROM THE LIVE BOARD, never taken from ENTRY_GRID.
##   _parse_board() does this: match each component's normalised shape against the 4 pieces x 4
##   orientations (all four sizes differ: 10/8/6/11, so it is unambiguous). Backtest still green.
##   TRAP HIT AGAIN: my first _parse_board indexed _blocks()[0] (the 64x64) instead of [1] (the
##   20x20 block grid), returned None, and SILENTLY FELL BACK — backtest stayed green while the
##   function did nothing. Always assert the parse actually returned something.
## DRAG rule is CONDITIONAL: "rotation always drags the bonded group" breaks 77 transitions.
##   Reverted to single-piece dynamics (292/294 green; only the 2 known drag-rotations fail).
##   Probing now with a CLEAN 2-piece / 1-bond experiment: bond piece1 to piece3 far from the
##   others, then rotate. If piece3 follows -> a single bond drags. If not -> a chain is needed.

## (old) ROTATING A BONDED PIECE DRAGS ITS PARTNERS.
##   Rotating piece1 while it had 2 bonds produced an active blob of 15 cells / 5 connectors —
##   it did not "grow", it PULLED its bonded neighbours with it. A second rotation dragged more.
##   BUT bonded partners still render MASKED (a naive "weld = all render active" model mismatches
##   level-4 action #13), and 14 earlier moves of bonded pieces in lvl1/lvl2 replayed fine under
##   the no-weld model -- so the drag is NOT unconditional. Pin down exactly when it fires:
##   likely ROTATION drags bonded partners while TRANSLATION breaks the bond (lvl1/2 moves that
##   stayed green were mostly translations; lvl2 had one rotation of a bonded piece -- re-check it).
##   *** This is the 5th rule my own planner never stressed: I always moved pieces BEFORE
##   bonding them, so "move a bonded piece" was never exercised and never falsifiable. ***
## RESET taken: the tangled position was unpredictable; RESET restores the known entry state
##   AND REFUNDS THE WHOLE BUDGET. Re-plan from entry.
## Until the drag rule is modelled: PLAN ROUTES THAT NEVER MOVE/ROTATE A BONDED PIECE — that
##   keeps every step inside the region the model actually reproduces.

## (old) ROTATION OF PIECE1 mispredicted — GRID mismatch, not just a flag.
##   I had NEVER rotated piece1 in 295 transitions, so its rotation was never exercised. Same
##   blind spot as ZCELL / MARK-on-BODY / BODY-on-BODY: a rule my own planner never stressed.
##   After rotating, the ACTIVE piece renders 10 cells with 4 connectors, matching NONE of my 4
##   orientations (my ori0 has 8 cells / 3 connectors). There is an 8 at a cell where my model
##   has NOTHING.
##   => EVERY assembly search used piece1's WRONG SHAPES, so the "all-bonded is impossible"
##   proof is VOID. Re-derive piece1's true orientations from frames, then re-run the search.
##   The win condition refit (below) now says ONLY "all connectors bonded" survives, and burial
##   is rejected — consistent with all-bonded being achievable once the shapes are right.
## Probing: rotate piece1 repeatedly to map its true 4-cycle.

## ******** WIN CONDITION (FITTED TO DATA; only ALL-BONDED survives) ********
##   WIN = (a) NO BARE CONNECTOR: every connector is BONDED (>=2 on its cell) or BURIED under
##             another piece's BODY;  AND
##         (b) NO TWO BODIES OVERLAP.
##   Fitted against ALL 292 recorded states: TP=4 FP=0 FN=0. Exactly ONE non-win state had
##   bare==0 -- it had a body-body overlap -- and that single counterexample is what pins (b).
##   Levels 0-3 won with everything bonded and no overlaps: just the special case.
##   Level 4 reaches 3 bonds + 4 buried + 0 body-overlaps. 30 such configs exist.
## METHOD NOTE: I burned ~40 turns GUESSING win conditions one at a time. The moment I instead
##   computed features for all 292 states and asked which predicate separates the 4 wins from
##   the 188 non-wins, the answer fell out immediately. FIT THE PREDICATE TO THE DATA.
##   (old, REFUTED: bonded-or-buried with no overlap rule -- it fired on a body-overlap state)  Level 4's connector geometry makes a perfect matching impossible
##   (proved 3 independent ways: chained assembly search, brute-force enumeration of all 372
##   matchings x 64 orientations, and a max-bond search whose ceiling is 4 of the 5 needed).
##   Burying the two leftover connectors IS reachable -- but ONLY because pieces don't collide.
##   WHY I MISSED IT FOR ~40 TURNS: "no visible 8s" was tested under the OLD collision model,
##   which BLOCKED connector-on-body. My own routing made the hypothesis unreachable, so the
##   test that "refuted" it never actually ran. Two wrong beliefs propped each other up.
## LESSON (cost me the whole level): a GREEN BACKTEST CANNOT TEST A RULE YOUR OWN PLANNER
##   NEVER VIOLATES. Every rule I inherited and never violated was suspect; 3 of them were
##   flat wrong (ZCELL passable, MARK-on-BODY legal, BODY-on-BODY legal).
## Keep ONE source of truth: predict() and is_goal() both call _won(). They had drifted apart
##   (predict still hard-coded all-bonded), which silently made the first winning plan "fail".

## !!!! THERE ARE **NO PIECE-PIECE COLLISIONS AT ALL** !!!!  (probed; backtest 280/280 green)
   MARK-on-BODY and BODY-on-BODY are BOTH legal — pieces pass straight through each other.
   Only the board edge blocks a move. My "blocked unless connector-on-connector" rule was WRONG
   from level 0 onwards, and it was NEVER EXERCISED because every route I planned obeyed it.
   *** A green backtest cannot test a rule your own planner never violates. ***
## => the last suspect is THE BOND RULE. Independently confirmed (two different algorithms,
   incl. brute-force enumeration of all 372 matchings x 64 orientation combos): with bonds
   requiring COINCIDENT connectors, NO perfect matching of the ten connectors exists.
   So "two connectors must coincide" must be wrong/incomplete.
   TESTING: park a connector ADJACENT to another piece's connector and look for a colour-3.
   If adjacency bonds, the impossibility proof collapses and "all connectors bonded" is back on.

## (old) MARK-on-BODY IS LEGAL (probed, model fixed, backtest 279/279).
   A connector may sit on another piece's BODY. It renders 8 (the active piece draws on top) and
   does NOT bond. My collision rule had blocked this since level 0 and NO ROUTE EVER TESTED IT —
   the same blind spot as the ZCELL. Collision rule is now: only BODY-on-BODY is blocked
   (BODY-on-BODY itself still UNTESTED -> probing action 4 now, blocked solely by it).
   NOTE: re-running the assembly search with the corrected rule (and even with NO collisions)
   STILL gives 0 => 'all connectors bonded' is impossible for pure connector-geometry reasons,
   independent of collisions. The search was verified by rediscovering level-3's assembly.

## (old) LAST UNTESTED COLLISION RULE: can a CONNECTOR sit on another piece's BODY?
   My model blocks MARK-on-BODY and NO MOVE HAS EVER TESTED IT (all routing avoided it) —
   exactly the same blind spot as the ZCELL. If it is ALLOWED, and especially if a connector
   landing on a BODY *bonds* (renders 3), the whole bond model changes and the impossibility
   proof collapses (my 'collisions removed' search still required bonds to be connector-on-
   connector). Probing: action 1 from the current state is blocked SOLELY by MARK-on-BODY.

## RENDER RULE (confirmed, model fixed, backtest 229/229):
   **THE ACTIVE PIECE'S CELL IS DRAWN ON TOP OF EVERYTHING.**
   - piece1 active + another piece's connector on piece1's ZCELL -> cell shows 0 (the ZCELL).
   - piece3 active + its connector on piece1's MASKED ZCELL      -> cell shows 8 (the connector).
   This also SETTLES the ZCELL: seen from its OWNER's side it renders 0, never 3 => it does NOT
   bond. The ZCELL is a passable, inert HOLE. (Masked pieces still render entirely 4, so a bond
   between two masked pieces stays invisible.)

## (superseded) FLAW FOUND IN MY OWN ZCELL TEST: when I drove piece3's connector onto the hole, PIECE3 was
   ACTIVE and PIECE1 was MASKED — so that cell was rendered from PIECE3's point of view (its own
   unbonded connector => 8). I NEVER looked at the hole with PIECE1 ACTIVE. Since MASKING WINS
   OVER BONDING, a bond involving a masked piece is invisible; "it rendered 8" therefore does NOT
   prove the ZCELL cannot bond. RE-TESTING: land a connector on the hole, THEN click piece1.
   Model (ZCELL = not a connector) predicts that cell renders 4. If the game shows 3, the ZCELL
   IS a connector — which fixes the parity (11 connectors) and would explain why a perfect
   matching of only the ten 8s is provably impossible.

## (older) GOAL — TWO HYPOTHESES KILLED, ONE LEFT (level 4)
- "no visible colour-8 cells": **REFUTED**. I bonded BOTH of the active piece's connectors,
  leaving zero 8s on screen, and the game did NOT advance. So it tracks HIDDEN connectors.
- "bond EVERY connector": **IMPOSSIBLE HERE**. All 4 connector sets are OBSERVED (2,3,3,2);
  the bond multigraph is forced & unique (K4 minus p0-p3), and it cannot be realised even
  IGNORING body collisions — pure connector geometry forbids it.
- => LEADING HYPOTHESIS: the goal is **ALL PIECES FORM ONE CONNECTED STRUCTURE** (a spanning
  set of bonds), NOT that every connector bonds. Levels 0-3 never distinguished the two: my
  final move always created the last bond AND completed connectivity at the same instant.
  TESTING NOW: attach p2 and p3 to the already-bonded p0+p1 -> all four connected, with 3
  connectors still unbonded. My model uses the strict goal, so a level_up = mispredict = CONFIRMED.
- **A BOND IS STRICTLY PAIRWISE.** 3+ connectors on one cell is LEGAL (the move is not blocked)
  but does NOT bond — it renders 8, not 3. CONFIRMED: (5,7) with pieces 0,1,2 rendered 8.
  So a 3-way junction WASTES connectors and can even BREAK an existing 2-way bond. My first
  connectivity plan was invalid for exactly this reason. Model now uses `len(owners)==2`.

## (superseded) LEVEL 4: "BOND EVERY CONNECTOR" IS IMPOSSIBLE -> GOAL IS "NO VISIBLE 8s" — REFUTED
All 4 pieces' connectors are OBSERVED (p0=2, p1=3, p2=3, p3=2; sum 10). The bond multigraph is
forced & unique (K4 minus p0-p3) yet NO geometric assembly exists — verified under every variant:
rotations only, +reflections, ZCELL as body / passable / connector, and allowing 3+ connectors
per cell. All give ZERO.
=> The win condition must be what the SCREEN shows: **zero colour-8 cells**. In MASK mode only the
   ACTIVE piece's connectors are visible, so it suffices to bond ALL OF THE ACTIVE PIECE'S
   connectors. Levels 0-3 never distinguished this (I always bonded everything).
   TESTING NOW: make piece0 active (2 connectors) and double-bond it to piece1 -> 0 visible 8s.
   My model still uses all-connectors-bonded, so a level_up here = mispredict = hypothesis CONFIRMED.

## SEARCH BUG (cost several turns): do NOT apply board-bounds while computing the RELATIVE
   assembly — pinning a piece near an edge then forces its neighbours off-board and kills valid
   solutions. Bounds belong only at GLOBAL placement. (Caught by sanity-checking the search on
   level 3, which I had already solved: pinning piece3 found 0 assemblies.)
   ALWAYS sanity-check a search against a level you have already solved.

## !!! CONNECTORS ARE A *DESIGNED SUBSET*, MARKED COLOUR 8 — **NOT** simply "every leaf" !!!
CORRECTED at level 3: piece0 there has FOUR degree-1 leaves but only TWO are connectors.
In levels 0-2 every piece happened to have exactly 2 leaves, so "connectors = leaves" fit by
coincidence. The real rule:
  - A masked piece's TRUE COLOUR is unguessable: there is NO small fixed palette (level-3
    piece2 is colour 12, which was the BACKGROUND in levels 1-2) and no stable index order
    (L1 = 15,14,11,9 in index order; L2 = 11,14,15 reversed). Just activate each masked piece
    once and record it in LEARNED_COLORS. Colour affects RENDERING ONLY, never dynamics, so a
    wrong guess costs a halted plan (one turn) and never a move — the geometry stays valid.
  - **THE LEAF-FALLBACK IS DEAD (level 4).** It worked in L2/L3 only because every masked piece
    there had exactly 2 leaves. In L4 the full-leaf assignment admits ZERO assemblies, and
    enumerating all connector subsets gives 27 candidates -> hopelessly ambiguous.
    => For a MASKED piece you CANNOT infer its connectors. CLICK IT to reveal them (this also
    reveals its true colour). Budget one click per masked piece before planning.
  - Level 4 also adds a **ZCELL**: a leaf of the ACTIVE piece rendered colour 0 (not 8, not the
    body colour). It is NOT a connector (parity: 3+2+3+2=10 works, 4+... = 11 is odd).
    Masked pieces may hide ZCELLs too — masking paints every cell 4.
  - MODE DETECTION: MASK iff some piece is rendered ENTIRELY in colour 4. Do NOT use "any
    colour-0 cell exists" — level 4's lone ZCELL would wrongly flip it to PLAIN.
  - ACTIVE piece  -> its connectors are visible as colour 8. READ THEM.
  - MASKED piece  -> connectors are HIDDEN. Fall back to its leaves, but VERIFY: the fallback
    is only safe when the piece has exactly 2 leaves. If an assembly exists under that
    assumption, that is strong confirmation (level 3: 8 valid assemblies existed => correct).
  - Total connectors is always EVEN (they pair up). Use that as a checksum.
Topology follows from the connector count: 2 pieces = 2 bonds; 3 pieces x2 = 3-cycle;
4 pieces x2 = 4-cycle; a chain uses 2 bonds per adjacent pair (level 1).

## TWO RENDERING MODES (detect from ENTRY_GRID: does any piece render colour 0?)
- PLAIN (levels 0,1): active piece's body -> colour 0; other pieces -> their true colour;
  ALL connectors visible as 8 (or 3 when bonded).
- MASK (level 2): active piece -> its TRUE colour with connectors visible as 8;
  INACTIVE pieces -> rendered ENTIRELY in MASK_COLOR 4, connectors HIDDEN.
  => a masked piece's true colour CANNOT be read from ENTRY_GRID; only activating it reveals it.
     Learned so far: level2 piece2 = 15. piece0 is a palette GUESS (11) — unverified.
- ACTIVE == MOVABLE in both modes (confirmed level 2: the active piece moved).
- **MASKING WINS OVER BONDING**: in MASK mode, a bonded connector renders 3 ONLY if one of its
  two owner pieces is the ACTIVE one. If BOTH owners are masked it renders 4 (fully hidden).
  (Confirmed at block (13,9).)  So you cannot see progress between two inactive pieces —
  track bonds from the POSES, never from the rendered colours.
- GOAL (both modes): every connector coincides with another  => all terminals paired.
  Do NOT test this by counting colour-8 cells — in MASK mode inactive connectors are invisible.
  Compute it from the POSES.

## SANDBOX: `globals()` AND `next()` are both unavailable. Use try/except NameError + explicit loops.

## !!! TOOLING TRAP (cost me a whole commit) !!!
Writing world_model_v5.py from **run_python** does NOT reinstall the live model — only
write_file / edit_file recompile+install it. I patched the connector rule via run_python,
ran run_backtest (87/87 GREEN — because levels 0-2 pass under BOTH the old and new rule),
and then committed a plan against a STALE live model. It mispredicted immediately.
=> After ANY run_python edit of the model, force a reinstall with edit_file, THEN backtest.
=> A green backtest only proves the model matches transitions you have ALREADY WALKED.
   It cannot vouch for a rule that no recorded transition exercises.

## THE GAME — core model
A level = N rigid PIECES on the 20x20 block lattice. Each piece has a body colour + CONNECTORS (8).
- **Exactly one piece is SELECTED. The selected piece's body renders as colour 0** — colour 0 is
  the SELECTION HIGHLIGHT, not a piece identity!  (Proven: clicking obj11 turned it 0 and turned
  the old "key" back to its true colour 15. The initially-selected piece's true colour is HIDDEN
  in ENTRY_GRID; it is 15.)
- **ACTION 6 (click) selects the piece under the clicked block.** Costs a move like any other.
- ACTIONS 1-4 translate the SELECTED piece 1 block; ACTION 5 rotates it 90 CW, bbox-TOP-LEFT anchored.
- A move is blocked unless every overlap with another piece is CONNECTOR-on-CONNECTOR.
- Two coincident connectors render colour 3 ("bonded"), but **bonds are NOT persistent** — move
  apart and they revert to 8. Pieces never merge.
- **GOAL: every connector coincident SIMULTANEOUSLY  <=>  ZERO colour-8 cells left.**
  So you must build the whole assembly and hold it; you cannot bank docks one at a time.
- Planning: BFS over all pieces x poses x selection is far too big. Instead SOLVE THE ASSEMBLY
  ANALYTICALLY (match connector pairs by canonical rotation-invariant offset), then route each
  piece with a per-piece BFS and pick a piece ORDER that avoids collisions. Simulate the whole
  plan through the installed model before committing.

## LEVEL 2 — NEW PUZZLE, GOAL NOT YET UNDERSTOOD  (bg=12)
3 components:
  piece0: colour 4, 7 blocks, 0 connectors   (bbox r3..4,  c10..15)  "upper 4-blob"
  piece1: colour 14, 13 body + 2 CONNECTORS at (4,6),(10,6)  offset (6,0)   "e snake"
  piece2: colour 4, 22 blocks, 0 connectors  (bbox r9..15, c9..15)  "lower 4-blob" (a loop + 2 stubs)
- **NOTHING IS SELECTED at entry** (no colour-0 anywhere) -> sel starts None; first click must select.
- **Two pieces SHARE colour 4** -> pieces are now located per colour-COMPONENT (fixed in model).
- ONLY 2 connectors in the whole level, BOTH on piece1 => "bond all 8s" cannot work the old way:
  an 8 has nothing to bond to. So either 8s bond to something else, or the goal differs here.
- Checked and RULED OUT: 4-cell pairs with piece1's connector offset (6,0) exist —
  {(4,10),(10,10)}, {(4,11),(10,11)}, {(9,10),(15,10)} — but placing piece1's 8s on ANY of them
  drives piece1's BODY into a colour-4 cell (collision). Rotating gives offset (0,6)/(0,-6) and
  NO 4-cell pair has those. So "8s land on colour-4 cells" does NOT work.
### CLICK RESULT — completely new mechanic (nothing moved, only COLOURS changed!)
  e-snake  : colour 14 + 8s on its 2 terminals  ->  ALL colour 4, no 8s
  lower-4  : ALL colour 4                        ->  colour 15 + 8s on its 2 terminals
  upper-4  : colour 4 (unchanged)
=> **Exactly ONE piece is ACTIVE. The ACTIVE piece shows its TRUE colour and reveals its
   CONNECTORS (8s) on its terminals. All INACTIVE pieces are masked to colour 4, connectors
   hidden.  Clicking a piece makes it the active one.**
- Every shape here is a path/graph with exactly 2 degree-1 TERMINALS, and the 8s sit exactly
  on the terminals of the active piece. True colours so far: e-snake=14, lower-4=15, upper-4=?
- This is NOT level-1's rendering (there ALL pieces showed true colours + 8s, and the SELECTED
  one was colour 0; here NO piece is ever colour 0). Level 2 masks non-active pieces.
- !! So the "only 2 connectors" puzzle was an artefact of masking: each piece HAS connectors,
   they are just hidden while inactive. The chain/assembly idea is probably alive after all.
- OPEN + TESTING NOW: does the ACTIVE piece MOVE (actions 1-4)? If yes, active == movable and
  the level is playable. If nothing moves, I must find how to actually select (maybe a 2nd click).

## OLD (level-0-only) framing — superseded, kept for context
- One movable **KEY** (body colour 0, with colour-8 PRONG TIPS) + one static **LOCK**
  (ring colour 14, with colour-8 SOCKETS sticking out of one wall).
- Key = a 2-pronged fork; the 8s are the tips of its prongs.
- **GOAL: land the key's two colour-8 tips exactly on the lock's two colour-8 sockets.**
  Collisions are blocked EXCEPT 8-on-8 (tip seats into socket) -> that move = level_up.
- Orientation cycle under CW rotation: mouth DOWN -> LEFT -> UP -> RIGHT -> DOWN.

## MODEL IMPLEMENTATION NOTES (world_model_v5.py)
- Key is located by MATCHING ITS COLOUR-0 PATTERN against the 4 rotations of the entry key,
  NOT by connected components — because when the key touches/docks the lock the two blobs
  merge and component-based detection silently grabs the lock too.
- `static` (everything in ENTRY_GRID that isn't the entry key) is re-painted every frame,
  so the render is exact even when the key overlaps a socket.
- Level 0 dock pose: orient3 (mouth RIGHT), full-bbox top-left = block (10,7).

## FRAMEWORK QUIRKS (bit me; keep in mind)
- `_backtest_rollout` (tools.py) and `_rollout` (agent.py) replay the GLOBAL FIRST transition
  WITHOUT advancing predict()'s state (`before is None -> continue`). A state move-counter
  therefore runs 1 behind forever on level 0.  FIX = `_recover_moves`: if state m==0 but
  grid != ENTRY_GRID, set m=1.  Never fires in live play or after a RESET.
- `globals()` is NOT available in the sandbox -> reference ENTRY_GRID via try/except NameError.

## LEVEL 0 — CLEARED (dock key's 2 eights onto lock's 2 eights).

## LEVEL 1 — ASSEMBLY CHAIN (background is 12, NOT 10 -> BG is now derived per level!)
Four pieces, each with 8-connectors. Canonical 8-pair offsets (up to rotation) chain them:
    obj0 (col 0, 2 eights, canon(-2,1))
      -> obj11 (4 eights: pair{(12,5),(14,4)} canon(-2,1); pair{(12,10),(17,8)} canon(-5,2))
      -> obj14 (4 eights: pair{(4,14),(9,12)} canon(-5,2); pair{(6,16),(8,16)} canon(-2,0))
      -> obj9  (2 eights: {(16,16),(16,18)} canon(-2,0))
  12 eights = 3 docks x 4.  => GOAL is to ASSEMBLE ALL FOUR into one chain, not one dock.
- Dock #1: obj0 moves DOWN 6 (collision-free; the 6th step overlaps ONLY 8-on-8). Confirmed by hand.
- Dock #2 (if pieces MERGE): the merged 0+11 translates (-8,+4) so {(12,10),(17,8)}->{(4,14),(9,12)}.
- Dock #3: needs a 90deg ROTATION (obj14's free pair is vertical (2,0); obj9's is horizontal (0,2)).

### BONDING — CONFIRMED
Seating a key 8 onto a socket 8 turns that cell **colour 3 = a BONDED JOINT**.
Dock #1 done: obj0's 8s at (12,5),(14,4) are now 3. 8 unbonded 8s remain (obj11 x2, obj14 x4, obj9 x2).
**GOAL = bond every connector => ZERO colour-8 cells left.**  (Also explains level 0.) ENCODED.

### NO MERGE — SETTLED (tested: obj0 moved up alone, obj11 stayed, the 3s reverted to 8s)
- Pieces do NOT fuse. **Colour 3 is NOT persistent state** — it just renders "these two
  connectors currently COINCIDE". Move away and they go back to 8.
- => level_up needs ALL 12 connectors coincident SIMULTANEOUSLY.
- obj14 and obj9 are not coincident with each other and DON'T respond to actions 1-5
  (only obj0 does). So they must be movable some other way.
- **=> ACTION 6 (click) MUST be the piece selector.** It is the only untried mechanic.
  Testing now: click obj11's body at cell (x=27,y=36) [block (11,8)], then action 1 (up).
  My model treats click as a no-op and always moves obj0, so:
    * if obj11 moves up instead -> CLICK SELECTS THE ACTIVE PIECE. Rewrite: track the
      selected piece in predict() state; each piece has its own pose; 1-4 move / 5 rotates
      the SELECTED one; collisions vs all other pieces; 8-on-8 allowed (bond).
    * watch the HUD too: does a click cost a move? (m=7 now, used=2; if a click costs a
      move, used(8)=3 with B=100.)

## NEXT LEVELS — what to check first
- BG is derived (most common colour) — do NOT hardcode.
- Is the key still colour 0? More pieces? Longer chains? Extra obstacles?
- If a level has no colour-0 component, _entry_info() returns None -> model no-ops. Fix then.
- BUDGET may differ per level; refit if the HUD mispredicts.
