# ARC3 game notes (v20 model) — L5 in progress (FINAL level, 5/6 cleared=win?)

## CONFIRMED CORE MECHANICS (all in world_model_v5.py, backtest 266/279; residuals = ±2-row bar wobbles that self-heal)
- HEAD: s×s (4 or 2) half-split 9|a block; facing = 9-side. Moves s px onto target
  all-{2,11,15} (pad-walk over ring corners b / f-solid). All-10 target = DOCK (level_up).
  {2,14}-mix target = E-PICKUP (block consumed, refunds m moves). Blocked+facing≠dir → turn
  in place. Bump (blocked same dir) = harmless. Vacate restores ENTRY 11/15, else 2.
- CARDS (left column, 10x10 3-framed): pattern = VERB, color = TARGET FAMILY.
  {N,W,E,S}=SIZE-TOGGLE: shrink 4→2 keep top-left; grow 2→4 = min-slide fit from keep-BR
  (candidates: all s2× squares walkable {2,11,15} containing old footprint; pri: keep-BR,
  then min |shift|, then gy,gx). Confirmed grows: #89,#238 keep-BR; #206 slide to (51,35).
  {NW,N,C}=TELEPORT to enterable card-color pad; facing preserved; f-solid pad first,
  else nearest (L4 #249: chose f-station over closer-scan-order pad; nearest untested vs f).
  {N,C,S}=DISSOLVE: raycast ahead (skip {2,4} ONLY — d/13 BLOCKS the ray! L5 proved; fail {5,9,10}); flood hit structure;
  WHIFF unless card-color ∈ flood colors (L4 #154 c-wall hit with 6-card = nothing!);
  else destroy structure cells + wipe payload colors (flood − cardcolor) GLOBALLY in field
  (cards/panel excluded). NO cross-structure rider; other same-frame-color structures survive
  (#227 wiped one 6-box + all c; the other 6-box stayed).
- PANEL (bottom, 3x3 of 3x3 cells): click toggles 2↔14, 0→14; marks accumulate; when
  marked set == some card's pattern → panel clears + verb fires. Click coords: NW(25,50)
  N(30,50) NE(35,50) W(25,55) C(30,55) E(35,55) SW(25,60) S(30,60) SE(35,60).
- CARD CLICK: re-seeds that card's pattern cells to 0 (free action).
- PADS: 4 corner cells of card color at corners of (s+2)×(s+2) ring; landing = s×s interior.
  4x4 pads also render inner corners (own corners, always visible). RING VISIBILITY by head
  size: b outer 6x6 corners visible iff head 4x4; f-station 6x6 f-ring visible iff head 2x2;
  2x2 b-rings / inner corners / f-solid always. F-STATION = 2x2 f-solid with b-ring = a pad.
- ENERGY BAR x62-63: tank full of 'e'; drains top-down (rows→0) as you spend. od = drained
  rows. DEATH at od=64 (game over → auto reset, full bar).
- COSTS L4/L5 (c-model): c counter, od = 2*floor(c/2) clamp[0,64]. Level entry: c=-2 (grace).
  +1: mark/unmark clicks, moves. +2: completion (any, incl whiffs). ~3: teleport?? (ambiguous
  2-3; using 2). 0: card-clicks, bumps, CCW turns. +1: CW/180 blocked-turns. E-pickup refunds
  moves-since-completion. NO side-freebies (that theory was wrong).
  L0-3 legacy: dark=2*paid2+2*mc; L3 2rows/move + structure-adjacent-arrival free + side
  freebie clicks; L0-2 cheaper moves. (Kept as legacy branch, greenish.)
- Gates (4): block movement, transparent to rays, never dissolve. d(13): transparent to rays.

## L5 LAYOUT (ENTRY) — plan
- Cards: {N,W,E,S}=f toggle; {NW,N,C}=b teleport; {N,C,S}=6 dissolve (same as L4).
- Base (32,8)-(37,12), interior x33-36,y9-12, mouth open at y13; c-PLUG x33-36,y14-16 blocks.
- Left corridor x33-36 y13-32 + widened x29-36 y29-32 + stub x30-31 y33-36 w/ 2x2 pad (30,34).
  ISOLATED — only reachable via 2x2 teleport.
- Head start: 4x4 (42,21) facing U. Band x42-53 y17-20; right corridor x50-53 y21-32,
  widened x50-57 y29-32, col x54-57 y33-36 → 4x4 pad (53,37)-(56,40) [ring (52,36)/(57,41),
  inner corners (53,37) etc].
- Right lane y37-40: pad → x45-52 red → d-wall x42-44 (transparent) → x41 red → 6-BOX
  (37,37)-(40,40) with cc INTERIOR ← dissolve target (payload c kills the c-plug!).
- 6-BOX (17,33)-(20,36) with dd interior, in POCKET: 2x2 pad+f-solid (13,41) [station],
  x15-18 y41-42, col x17-18 y37-42. Pocket disconnected from left corridor.
- 2x2 pads: (13,41) station [f-priority target], (30,34) stub, (54,38) right-pad-nested.

### PLAN v2 (after RESET; d blocks rays so dd-box must die first; ~51 units, death 64)
KEY FACTS: stub pad is DUAL (2x2 (30,34) + 4x4 landing (29,33), outer ring (28,32)/(33,37)
appeared only after first teleport — L5 rings copy-through in model). Self-occupied pad is
EXCLUDED from teleport candidates (L4 #168 whiff) → stand ON a pad to force the other.
1. RESET. 2. NW,N,C → tele4x4 (42,21)→(53,37). 3. N,W,E,S → shrink 2x2 @(53,37).
4. NW,N,C → tele2x2 → station (13,41) [f-priority; if reality=nearest → lands (54,38),
   then chain re-teleports → (30,34) → (13,41); +8 units, replan/RESET if needed].
5. a4,a4 → (17,41) face R. 6. N,C,S → DISSOLVE ray U → dd-box → ALL d dies (d-wall too).
7. a1,a1 → (17,37). 8. N,W,E,S → GROW → unique fit (17,35) 4x4.
9. NW,N,C → tele4x4 → stub (29,33) [nearest+scan agree]. 10. NW,N,C again → right pad
   (53,37) [stub self-excluded → unique]. 11. a3 → (49,37) face L.
12. N,C,S → DISSOLVE ray L (x42-44 now red) → cc-box → ALL c dies (c-plug!).
13. a4 → back on (53,37). 14. NW,N,C → tele4x4 → stub (29,33) [unique].
15. a1 (29,29), a4 (33,29), a1×4 → (33,13), a1 → DOCK rows 9-12 = WIN.

## History tooling (run_python)
- events.jsonl: kind=='action_taken' items; e['grid'] = AFTER grid; level_up steps carry NEW
  level's board (dock action logged with new level!). Level starts: {0:0,1:29,2:34,3:76,4:145,5:283}.
- L4 resets at #169(manual),#242(death); pickups #221,#257 (od drops).
- Emulate model: exec(src, {'np':np,'ENTRY_GRID':entry,'CURRENT_LEVEL':L}); entry for L =
  tr[levelstart]['grid'].
