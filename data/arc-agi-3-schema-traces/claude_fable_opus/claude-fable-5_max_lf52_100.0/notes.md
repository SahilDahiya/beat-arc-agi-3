# Notes — living scratchpad

## COMPLETION RULE R2 (replaces old consume-gated rule; verified vs ALL 762 transitions)
- After ANY action (arrow or click): if count(non-8 pegs, any colour incl. red) <= 1
  AND no legal jump exists anywhere (any peg/cart-peg over peg/wall/wall-cart/loaded-cart
  into empty cell/empty transport) -> LEVEL_UP.
- Encoded with knowledge gate state['maxpegs']>=2 (model only counts SEEN pegs; L6 starts
  with all pegs off-screen east -> without gate, false level_up at entry).
- L5 keeps legacy branch (keyhole/hero + decoy exclusion) gated by CURRENT_LEVEL==5.
- Proved: consume-gated variant makes L6 unwinnable (every final settling step is an arrow) -> wrong.
- Unresolved (harmless): count-only variant (no settled req) also fits history; L6 plan works
  under both (if count-only, level_up fires at the consume click instead of the final arrow).

## PHANTOM-CART DEDUP (_find_carts)
- Stacked carts (6 apart) render fused with a shared seam -> phantom core candidate 1px off.
- Fix: among candidate pairs within Chebyshev<=2, drop the one whose ring-sample contains rail-5s.
- Fixed the #755-#761 ghost-repaint mispredict class.

## L6 ENDGAME PLAN (56 actions committed; dress-rehearsal green, level_up at final press-1)
Pieces: e(114,36), 8(138,36), fe(138,42); C empty@(132,18); walls (102,18),(126,6),(138,24); cam(84,0).
A[1,3,3,2,4,2,2] C->(138,30); J1 fe boards C over 8; B[1,1,3,3,3,3,2,2] ride->(114,30);
J2 fe CONSUMES e ->(114,42) (if count-only rule: LEVEL_UP HERE); J3,J4 fe west row42 ->(90,42);
C-phase[1,1,4,1,4,4,2,4,2,2] stage walls (138,30)+(114,30), C->(138,24); J5 8 boards C;
D[1,3,3,3,3,2] ->(114,24); J6 8 drops ->(114,36); J7,J8 8 west ->(90,36);
J9 fe (90,42) over 8 ->(90,30) FINAL REST; J10,J11 8 east ->(114,36); J12 8 re-boards C;
E[1]: C-8->(114,18) -> zero jumps + n_all==1 -> LEVEL_UP.
Mechanics: pegs move ONLY by 12px jumps (mid at 6 = peg/wall/wall-cart/loaded-cart; land = empty
cell/EMPTY transport); 8-jumps never consume & jumps over 8 never consume; non-8 over non-8 ALWAYS
consumes; interfaces = 1-wide rail spurs above board cells (x=114 spur {18,24,30}->cell(114,36);
x=138 spur->(138,36); spur order fixed - no passing); board-W rows 36/42 connect only via x=90
column with peg mids; arrows move ALL carts jointly 1 step (fixpoint, blocked by non-movers).
On queue stop (seam wobble): replay state (run_python, replay-from-#522 snippet) + phase-BFS
(plan_l6b.py) from current cfg, recommit remainder. If level_up early: count-only rule -> L7.

## Game: unknown, 10 levels. Level 0.

## Action semantics (confirmed / guessed)
- legal: 1,2,3,4,6(click),7. No 5.
- nothing confirmed yet.

## Level 0 layout (from ENTRY_GRID)
- bg=10(a); row y=0 is black(0).
- Grey(5)-bordered panel(s) with maroon(9) shadow, interior black(0), containing 4x4 blue(1) blocks.
- L-shaped board: big panel x=9..52, y=10..29 (7 block-cols x 3 block-rows);
  right extension x=33..52, y=29..53 (block-cols 4..6, block-rows 3..6).
- Block grid: col c at x=11+6c (c=0..6), row r at y=12+6r (r=0..6).
  Rows 0-2: cols 0-6. Rows 3-6: cols 4-6 only.
- Some blocks contain a diamond of e(14): pattern 1ee1/eeee/eeee/1ee1 inside the 4x4.
- Diamond blocks at (c,r): (1,1),(2,1),(4,1),(5,2),(5,4).

## GAME = PEG SOLITAIRE (confirmed level 0)
- Board of 4x4 blocks (6px lattice). Peg = diamond of e(14). Empty = all 1(blue).
- Click peg -> selects it (green 3 corners + 6x6 ring); red(2) hollow outlines appear on all
  legal jump landings (over orthogonally-adjacent peg into empty 2 blocks away).
- Click red outline -> JUMP: source & jumped peg removed, landing gets peg. Selection clears.
- Arrows 1-4 & 7: NO effect (counter only), even with selection.
- Every action appends 1 at leftmost 0 of row 0 = move counter.
- GOAL: reduce to 1 peg total => level_up (confirmed L0).
- Action 7 = UNDO (full grid except move counter; per-action stack; modeled via predict-state).
- Click peg w/o legal jump = no-op. Click outside blocks = deselect.
- CART (L1+): 8x8 box (5 ring, b=11 ring, c=12 core 4x4, 9 shadow) rides 2px '5' pipe rails.
  Arrows 1=up,2=down,3=left,4=right move cart 6px per press along rails (center 2x2 must stay
  on rails); successful move clears selection. L0 had no cart -> arrows were no-ops.
- DOCKING: cart drives flush to a board edge; its 5-border on that side is omitted and the board
  border column is replaced by the cart's b-ring; core then sits 6px from edge block = jumpable
  cell. Encoded exactly (base-grid eraser + conditional border painter). DON'T hand-count rows —
  use code (had off-by-one: L1 row1 y0=15, pipes rows 16/17 & 34/35!).
- L1 CORRECT lattice: main row1 y0=15, x0=7+6c: c3=(25,15),c4=(31,15),c5=(37,15),c6=(43,15).
  2nd board: S0=(43,51),S1=(49,51). Cart stops: entry(31,33),(37,33),(43,33),(49,33),(55,33)corner,
  (55,27),(55,21),(55,15)corner,(49,15)DOCK-main. To 2nd dock: 4(undock),2x3,3x7,2x3,4x4 -> (37,51).
- CONFIRMED renders: target-in-cart = 12/2 hollow; loaded cart = 12-corner diamond; cart
  selection = corners 3 + ring edges 3 (ring corners stay b). Jump out of cart works. L1 cleared.
- VIEWPORT/CAMERA (v9): the 64x64 frame is a WINDOW onto a WIDER WORLD. Row 0 = HUD counter
  (screen-anchored). Camera follows the single LOADED cart: cam=max(0,((cartx+2-32)//8)*8),
  clamped to world width (learned per level via 'wtrue' when observed cam < predicted).
  Model state: world map 64x192 (-1 unknown), base (world minus carts), cam, undo stack, wtrue.
  EXPECTED PERMANENT BACKTEST MISSES: #36 (L1 clamp), #80/#81/#82 (L2 reveals), #97 (L2
  base-unknown undock, fixed by _sync_base going forward).
  CAMERA RULE (fits all data): while ANY cart is loaded, cam=max(0,((carts[0].x+2-32)//8)*8)
  where carts[0] = topmost cart in scan order; frozen when no cart loaded; clamped by wtrue.
  Reveals of unseen area are inherently unpredictable -> ~1 miss per first-reveal; fine.
- ARROWS move ALL carts simultaneously (each iff its target center-2x2 is on rails).
- L2 world (known so far, world coords): mega-board towers (6,6..12,12 / 24,6..30,12) + base
  (cols 6..24, rows 18,24); pegs left: (12,12)~gone? see current; bottom board (cols 6..24 row
  48, cols 6..18 row 54) pegs (12,48),(24,48); BIG RIGHT BOARD x>=58: alcove block (60,12) w/
  peg + col x0=66 blocks y0=6..54, peg (66,42); extends beyond x=71 (unrevealed).
  Top cart pipe rows 13/14 (world x=36..57+), docks: towerB (36,12), alcove-left (54,12).
  Bottom cart pipe rows 49/50 + loop (risers x=43/44 & 55/56, horiz rows 37/38), docks:
  bottom board (30,48), big-board-left (60,48).
- L2 status: mega cleared into cart; TOP CART LOADED at (42,12); bottom cart (60,48) empty;
  pegs remaining: cart-peg, (60,12), (66,42), (12,48), (24,48) = 5 total.
- L2 plan: drive loaded cart right, dock (54,12); cart-peg JUMPS over (60,12) -> lands (66,12)
  (real cell!). Then explore big board (reveal cols 72+), get pegs down to bottom-cart dock
  (66,48 adjacent), ferry into bottom board to unlock (12,48),(24,48). Watch cam rule on moves.
- L2 counter: 26 used of 64 — WATCH THIS; undo/redo do not refund.

## Confirmed facts
- Top row 0 = move counter (all actions tick it; undo does NOT refund).
- Level advances even mid-queue; snapshots of level-clearing code saved under snapshots/.


## L5 endgame knowledge (turn ~82, post model-overhaul)
- RESET was #314 = socket click (68,55). Keyhole (64..74,51..63) spawns WITH hero; socket click = LEVEL RESET — never click it.
- Right board (88..113,10..29) + CORRIDOR arm at cell-row y=18: cells (114,18),(120,18),(126,18),(132,18)... extending east past x=137 (unrevealed). Row-16/23 borders.
- Far-east cluster: board B (rows 40..47; cells (126,42),(132,42),..., extends east ≥138) stacked on decoy board A (cells (126,48) [decoy e-peg], (126,54) empty). Not reachable by carts: pipe rows 43/44 ENDS ~x=114 (carts max park (102,42),(108,42) — #305 blocked). Corridor y=18 is the hero's road east.
- PLAN (committed): ferry done → 8@(108,18), e@(90,18), jump (90,18)o(96,18)->(102,18) = HERO + keyhole. THEN leapfrog east: hero over 8 ->(114,18); 8 over hero ->(120,18); hero ->(126,18); ... camera: carts parked at (102,42),(108,42) put cam≈74 (sees to world 137). Camera does NOT follow cell jumps (maybe follows hero? observe). Pre-reset cam followed even EMPTY carts (#303/304 pans — model 1-missed those).
- _count_pegs: L5 excludes x>=116 (decoy board not counted — conversion fired with decoy present).
- Conversion rule (encoded): consuming jump -> count==1 -> L5: paint hero + KEYHOLE_STAMP; other levels: level_up.

## Model overhaul (this session)
- _paint_cart border-5s guarded by CURRENT w too (fused carts: no stray 5 between).
- Arrow moves: collision fixpoint (a mover into a NON-moving cart's spot is blocked); STRICT rails only (no unknown-optimism: genuine pipe ends exist — L2 #68 dock).
- RESET branch: keeps BASE (geography memory; base=LAST-SEEN via _sync_base), world=base copy + scrub transients (targets, selections, color-2 heroes) + entry-window merge. wtrue/htrue no longer reset.
- Permanent backtest registry (41): reveals #80-82,#97,#117-121,#135-138,#195-197,#201-202,#280-289,#302-304,#308-309,#314,#326,#334,#338-339; hidden-peg-count flags/grid #193,#200,#272 (pre-reveal windows, cannot recur once world revealed); load-snaps #334.
- LESSON: base = last-seen, NOT entry state. Post-reset stale mid-play content must be scrubbed; hidden regions => count underestimates => gate endgame branches on `consumed`.


## BREAKTHROUGH (turn ~86): hero = STUCK-RESCUE, not goal!
- #347-run: jump (90,18)o(96,18)->(102,18) consumed mid, count-excl-8==1, but NO conversion: 8@(108,18) gave a LEGAL jump (e over 8).
- Pre-reset #293: same jump converted BECAUSE position was DEAD (8 was far away on left board, no legal jumps anywhere).
- UNIFIED COMPLETION RULE (hypothesis R1): after a CONSUMING jump, if NO legal jumps exist anywhere (all pieces):
    - no other e-pegs left anywhere -> LEVEL_UP  (fits L1-L4 endings: lone stuck peg)
    - else (e-pegs remain, e.g. decoy) -> HERO conversion + keyhole = rescue marker (fits #293)
  8-pegs = tools: their EXISTENCE doesn't block level_up, but their LEGAL JUMPS block settledness.
- => L5 GOAL: leapfrog e+8 EAST along corridor y=18 (cells 108..132+,18), find link down to B (y=42) at x>=138 (unrevealed), get e to (126,42), consume decoy (126,48) -> land (126,54). End position must be DEAD: e@(126,54) stuck ✓, 8 must end stuck too (e.g. (132,42) with (126,42),(138,42) empty).
- CAMERA RISK: cells >=126 at screen >=64 with cam 62; carts parked east give cam 74 max (sees to 137). If corridor continues past 138, need camera to follow PEGS — TEST during first jumps.
- Current: e@(102,18), 8@(108,18), empty carts docked (90,30),(108,30), cam (62,0).


## L5 CLEARED (turn ~93) — 40-action endgame ran perfectly
Solver-planned: cart bridge (156,18); leapfrog e+8 east; 8→cart; e east-board; consume (162,24);
cart-8 as mobile mid (156,30)/(144,30); e re-entry west; consume (138,36); cart-8 unload (132,42);
e consume decoy (126,48)→(126,54); R1 fired → level_up. NO camera pans during clicks (pan at #359
was a one-off — maybe only when the moved piece exits/nears view edge).
KEY REUSABLE PATTERN: build solver over (pegs, cart pos+load) with jumps (mids=pegs/walls/cart-pegs,
landing=empty cell or docked empty cart) + cart rail-graph arrows; goal = R1 (consuming jump →
no legal jumps anywhere → ne<=1 → level_up).

## L6 START (level 6/10)
Entry: two mini-boards top: e-peg (left) + 8-peg (right), each 1 cell above a WALL (jump down over
wall = no landing cell visible — pegs likely must be CARTed). One empty cart mid-map. Pipe net:
horiz rows 25/26 (x~7..44+), horiz rows 37/38 (x~13..44, 55..63), verticals x~25/26, 13/14, 55/56,
62/63, 44?. Two lower wall-boards (walls at ~(12,47),(42,47)); wide bottom board rows 52..60 with
cells + 2 walls (18,54),(30,54), extends east past view. Plan: explore with arrows (cam follows carts),
map world, re-run solver pattern.
