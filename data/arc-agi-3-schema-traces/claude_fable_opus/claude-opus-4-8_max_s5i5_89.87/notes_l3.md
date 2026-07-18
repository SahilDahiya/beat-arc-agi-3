# LEVEL 3 — SOLVED (2026)! Key: boxes CLIP obstacle growth (not block). O_c pushed DOWN to rows45-47 (long body),
# grows right until CLIPPED at box-9 edge x47 (g9) while pointer+others keep growing -> pointer docks at g11 = WIN.
# Solution: RESET; grow(33,54)x3; upO9(57,48)x4; upOe(12,48)x4; upO8(57,57)x4; dnOc(6,57)x7; grow(33,54)x8.
# box-b is NOT strictly all-or-nothing: an obstacle whose growth is CLIPPED (box edge / grid edge row0) just stops;
# pointer+others still grow. (Obstacle-obstacle bar collision DOES no-op the whole grow.) Model _L3_BOXES_BLOCK should
# be a CLIP not a wall for future accuracy, but win-step grid isn't scored so we win regardless.
# ===== (below = pre-solve reverse-engineering notes, kept for reference) =====
# LEVEL 3 (3/8). Levels 0,1,2 CLEARED. ===== FULLY RE-DERIVED 2026 (old notes were WRONG on counter/merge) =====

## CONFIRMED MECHANICS (validated vs history, robust measurement):
- GOAL: dock pointer d-marker at diamond center (31,10). d-marker row = 43 - 3*g (g=net grows). Dock => g=11.
- POINTER: vertical color-11 bar x30-32, BOTTOM FIXED row43, handle 333 row44 x29-31. Grows UP.
  Occupies rows[42-3g .. 43]. d-marker(13) at (43-3g, 31), i.e. pointer_top+1. Entry g=0: rows42-43,d row43.
- box-b RIGHT (33,54)=GROW (+1 g): pointer +3 up AND all 4 obstacles +3 wider. box-b LEFT (27,54)=SHRINK. center(30,54)=inert.
- box-b is **ALL-OR-NOTHING** (100% confirmed, 40+ grows): pointer + ALL 4 obstacles grow together, OR nothing moves.
  BLOCK RULE: no-op iff ANY element's 3 new cells land on a non-background(!=5) cell (bar/body/pointer/diamond/BOX).
  (Diamond exception: pointer's FINAL grow into diamond at g=11 = DOCK/win, not block.)
- 4 OBSTACLES (horiz color-11 bars, each grows toward center x30-32 from a FIXED anchor; width=2+3g):
    O_9: anchor x52 grow LEFT;  body 999 cols51-53; handle row17; home bar rows12-14.
    O_e: anchor x10 grow RIGHT; body eee cols9-11;  handle row20; home rows15-17.
    O_8: anchor x46 grow LEFT;  body 888 cols45-47; handle row23; home rows18-20.
    O_c: anchor x19(~x18) grow RIGHT; body ccc cols18-20; handle row53(!); home rows24-26.
  BODY hangs DOWN from bar_bottom+1 to handle_row (fixed handle => body stretches when bar pushed UP).
  Bodies are WALLS: block other bars' growth (non-5 cells). Bodies at anchor cols (never x30-32, so never block pointer).
- PUSH (obstacle boxes, ±3 rows, x unchanged, works even wide): 
    UP=box RIGHT: O_c(12,57) O_e(12,48) O_8(57,57) O_9(57,48).  DOWN=box LEFT: O_c(6,57) O_e(6,48) O_8(51,57) O_9(51,48).
  Bar clamps: top>=0 (bar CLIPS at row0, NOT removed); bottom must stay above handle (bar_top+2 < handle_row).
  => Only O_c can down-park deep (handle 53 => bar down to rows~48-50). Others handle 17/20/23 => ~1 down-push only.
- COUNTER row63: simple MOVE COUNTER = +1 per click (EVEN no-ops), reset 0 on RESET. N rightmost cells color-4. (NOT adversarial! old note wrong.)
- DEAD LEVERS (retested clean): removal=FALSE (bar clips row0, body grows); direct-click(diamond/cells)=INERT; box center=inert; shrink=inverse grow.

## THE SOLUTION (BFS over confirmed mechanics, WITHOUT modeling boxes as walls => DOCKS at g11):
  grow x3;  up O_9 x4 (rows12->0);  up O_e x4 (rows15->3);  up O_8 x4 (rows18->6);  down O_c x7 (rows24->45);  grow x8 => DOCK
  = 3 bands above (O_9 r0-2, O_e r3-5, O_8 r6-8) + O_c parked BELOW pointer at rows45-47 (its long body lets it go down there).
  KEY INSIGHT I long missed: the 4th obstacle goes DOWN below row43, not a 4th band above.
  Explicit clicks: [ (33,54)x3, (57,48)x4, (12,48)x4, (57,57)x4, (6,57)x7, (33,54)x8 ]  (30 clicks)

## THE ONE UNTESTED QUESTION (decides solvability):
  Do obstacles grow OVER the control boxes, or do boxes BLOCK growth (like other non-5 cells)?
  O_c at rows45-47 grows RIGHT; reaches box-9 (x48-60, rows45-51) at width~31 => g~10. 
  - If boxes DON'T block => O_c grows through, pointer docks at g11 => WIN.
  - If boxes DO block (BFS-with-boxes gave max g=9) => this path caps at g9; level needs yet another mechanic.
  Boxes/diamond static; obstacles never interacted with boxes in history => genuinely untested.
  TEST = execute the solution; watch O_c's right edge at grow ~9-10 (6th of final grow x8). If O_c passes x48 => boxes non-walls => keep going to dock.

## MODEL BUILT & INSTALLED (world_model_v5.py has L3 predict branch, boxes NON-walls). Backtest: L3 dynamics PERFECT
  (only 2 cosmetic 1-cell counter mismatches in ~140 L3 steps). Counter modeled as _l3_counter(n)=lut[0,1,1,2,3,3,4] then floor(2n/3).
  Python-verified the plan DOCKS (g=11, zero no-ops), final bt {O_9:0,O_e:3,O_8:6,O_c:45}.

## COMMITTED PLAN (RESET first, then 30 clicks) — auto-executes on installed model:
  RESET(0); (33,54)x3; (57,48)x4; (12,48)x4; (57,57)x4; (6,57)x7; (33,54)x8
  = grow x3, upO9 x4, upOe x4, upO8 x4, dnOc x7, grow x8.
## WATCH DURING EXEC:
  - If it DOCKS (d-marker reaches (31,10)) => WIN L3 => go to level 4.
  - DIVERGENCE at the 6th final grow (g9->g10, ~action 29): O_c right edge hits box-9 (x48). If model (boxes non-walls)
    mispredicts there (reality: O_c blocked, box-b no-op) => BOXES ARE WALLS => level needs another idea (re-open; O_c-down dead).
  - If stalls on COUNTER (cosmetic row63, 1 cell): just RE-COMMIT the remaining clicks from where it stopped (state re-threads fine).
  - Track d-marker row (target 10) & g via pointer top (g=(42-top)/3).
