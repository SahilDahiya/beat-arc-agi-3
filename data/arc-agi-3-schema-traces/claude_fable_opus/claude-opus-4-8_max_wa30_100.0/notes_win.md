# LEVEL 1 — BLOCK AUTO-DROPS (model fix) + fresh efficient plan (turn ~101)
## FIX: the BLOCK auto-delivers — once its carried box is on an empty D cell, it DROPS it
## (bgrab->normal) on the NEXT step, NO action-5 needed. (Old model matched only because I always
## followed block deliveries with action-5.) Encoded in _block_step. Also encoded bar-64 => dead.
## => block deliveries no longer need action-5; action-5 is only for E-carry (grab/release) & steal.
## CURRENT (bar=10): E(9,7)R, block(4,8), box on (4,7), off-D (10,5)(12,6)(12,8)(11,10).
## 39-move remaining WIN: E-carries (12,6)->(3,9) & (11,10)->(4,9), block auto-finishes the rest.
## PLAN(39): [4,4,4,1,5,3,3,2,2,2,3,3,3,3,3,3,3,5,2,4,4,4,4,4,4,4,4,1,5,3,3,3,3,3,3,3,1,5,1]
## bar 10+39=49<64 SAFE. Bar-skips STOP -> re-run e_deliver+block_finish (AUTO-DROP version) sweep
## from actual state, verify cov==6 & moves<=(64-bar-2), re-commit. WATCH level_up=>LEVEL 2.

# LEVEL 1 — EFFICIENT 59-MOVE WIN (fits the 64 bar limit!) (turn ~99)
## From ENTRY E(3,2)'U', block(6,9), boxes (9,7)(10,5)(12,6)(12,8)(11,10):
## E-carries (12,6)->(4,9) and (11,10)->(3,9) (in PARALLEL with block auto-delivery), then block
## finishes. VERIFIED reaches cov==6 at move 59 (boxes (3,7)(3,9)(4,7)(4,8)(4,9)+block on (3,8)).
## PLAN(59): [2,2,2,2,4,4,4,4,2,4,4,4,4,4,1,5,3,2,2,3,2,3,3,3,3,3,3,5,2,4,4,4,4,4,4,4,1,5,3,3,3,3,
##            3,3,3,3,1,5,1,1,1,1,1,1,1,1,1,5,5]
## 59<64 so SAFE even w/ zero bar-skips. Bar-skips still STOP the plan (~every 12 mv) -> re-commit
## the remaining tail (state stays correct). If state diverges, re-run the E-deliver+block-finish
## sweep in run_python from actual state. WATCH for level_up=>LEVEL 2.

# LEVEL 1 — CRITICAL: BAR IS A DEATH LIMIT @ 64 (turn ~98)

## I DIED: the move-counter bar (row 63, fills leftward w/ color 4) increments ~+1 EVERY move
## (with ~7 rare skips per 84), and at fill==64 => GAME OVER (auto-RESET refunds bar to 0).
## So EACH ATTEMPT HAS ~64 MOVES. My hold-E/block-auto win plans take 80-95 moves => TOO LONG.
## Block delivering all 5 boxes serially = ~95 moves & TRAPS. Must be much more EFFICIENT.

## KEY: E and the BLOCK both move EVERY action -> deliver boxes in PARALLEL (E-carry some boxes
## while the block auto-delivers others) to fit <=63 moves. Directing E to just "hold" wastes E.

## ENTRY (reset) STATE: E(3,2)'U', BLOCK(6,9), 5 boxes: (9,7)(10,5)(12,6)(12,8)(11,10), D empty
## (6 cells (3,7)(4,7)(3,8)(4,8)(3,9)(4,9)). Boxes are FAR (cols 36-51); D at cols 12-19.

## WIN = all 6 D cells covered by 5 boxes + block (block covers 6th = its final rest cell).
## is_goal in model fires level_up at cov==6. Model backtest-green except bar-skip cells.

## MECHANICS (all validated & in world_model_v5.py):
## - BLOCK = BFS pathfinder, neighbor order L,R,U,D. Fetch nearest non-D box (grab on contact,
##   offset = -approach dir). Carry: rigid-pair BFS to nearest cell where box lands on empty D cell.
## - action-5: drops block's carried box if on D (or E-faces it). Block steps iff still-carrying OR
##   (not-carrying-before AND E grab/release changed). Delivered block STAYS put.
## - E-carry: E grabs box it faces (offset=facing dir at grab, LOCKED while carrying); places box on
##   any D cell C by standing at C-offset (e.g. box-above -> stand below C) + action5. E CAN grab
##   on-D boxes (no constraint). E facing a box during an action-5 GRABS it (watch this).
## - Bar +1/move; NOT block-only. RESET (action0) refunds bar+level.

## NEED: a <=63-move plan. Approach: E-carry 2-3 boxes (esp. the ones far from the block / the
## MIDDLE cells (3,8)(4,8) the block traps on) in parallel with block auto-delivering 2-3 corners;
## block's last delivery leaves it on the 6th cell. Blind BFS/DFS/best-first find NO win (too big).
## Construct via simulation (apply()/block_step LRUD-BFS/action-5 rule/e_deliver in run_python
## history) and MINIMIZE moves. RESET is free (refunds) so exploration is safe.
