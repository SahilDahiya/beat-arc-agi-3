# Notes — living scratchpad

## Action semantics (confirmed / guessed)
- Legal at L0 start: only 6 (click x,y) and 7.
- action 7 on entry state: NO-OP (grid unchanged, no budget cost). Maybe context-dependent.
- BUDGET BAR (row 63): progress bar = floor(k*64/N) cells consumed after k clicks; N=click allowance per level {L0:32,L1:32,L2:48}. Model default N=48 for new levels; first clicks of a level reveal true N (cheap mispredict).
- click (4,59) bottom f-block: also inert, -2 budget (bar now 60).
- click (31,5) TOP f-block (in 4-band): TOTAL no-op, zero cost. Top band = non-interactive (HUD).
- click (10,53) the 0-plus: f-block MOVED from center (4,59) to center (10,53) (click point), plus consumed, old spot cleared, -2 budget (58 left). Move was +6,-6 along the x+y=63 diagonal.
- click (16,53) off-diagonal empty: block moved EXACTLY there (center=click). Free placement confirmed. Dot (10,53) revealed (was under plus all along; trail dots are static decor, occluded by objects).
- Movement = teleport block center to click point. Δ(6,6)&Δ(6,0) OK; Δ(4,-10) onto a DOT cell FAILED (-2 budget only). Confound: range (cheb>6? eucl>9? manh>12?) vs target-cell-occupancy (dot=3 cell). Testing dot (14,49) at cheb 4.
- GOAL GUESS: land block exactly on ball's 3x3 core (center 48,15; core cells 47-49x14-16, matches block size; trail leads there).

## Current level (L8)
- Goals: c + f + D-GLYPH; disks (7-15,37-45),(7-15,51-59),(51-59,51-59). 4× 7-glyphs (→2 e's→d), 8-block (35-41,48-54)→c, two 6s→f.
- L7 SOLVED: e-glyphs: pull-to-click (≤72), chase like 7s otherwise, merge like pieces at clicks; deliver wandering glyphs LAST; piece delivery = ANCHOR in bbox; glyph = CENTER in bbox.
- Leap: 12-dominant, ±8-minor if |minorΔ|>4.5, range cell-d²≤72, clamps at walls (body may overhang row 63).
- UNKNOWN: do e/d glyphs EAT? (block-eat must come from e or d here — all 7s get merged!). d-shape from icon: bigger.

## Previous level (L6)
- HUD: TWO b's. Disks (24,17) & (45,22). Four 6s (=b1), 7x7 8-block (glyph-feed → c → b2), TWO glyphs (14,52) & (55,57).
- Plan: exile west glyph SW (2 leaps), build b1 (4 clicks), east glyph auto-eats block+c during those, deliver b2→east disk (1 pull), b1→west disk (2 pulls).
- NEW RULES from L5 win: leap CLAMPS at walls; glyph delivery = CENTER inside disk box (body-overlap insufficient). Piece delivery = any overlap (L4).

## Previous level (L5) — SOLVED
- Palette now a,6,f,b,c(12),8 = tiers 1-6 (sizes 5x5, 6x6?). HUD goals: b 4x4 + GLYPH ICON (8-cell diamond)!
- Two disks: (6,16) top-left, (57,57) bottom-right. One glyph c(18,36). One 7x7 SOLID 8-block c(36,35) — only material. 49 cells=7x7 doesn't fit tier-size=6...
- HYPOTHESIS: glyph EATS the 8-block repeatedly: 8->c->b (downgrade chain); deliver b to one disk + park GLYPH on other disk = goal. Glyph may be lured by pieces.
- PROBES: block NOT pullable (click on it: inert); glyph TARGETS block (chases it). Budget N=32.
- GLYPH-CLICK RESPONSE (new mechanic!): click within ~8 of glyph cells -> glyph LEAPS ~11-12 toward the click, apparently ALONG THE DOMINANT AXIS of the offset: obs A: center (22,35), click (+1,+9) -> move (0,+11); obs B: center (22,46), click (0,+8) -> move (0,+12). Exact length rule unknown. Far clicks -> normal chase-step (confirmed).
- Herding: leap ~11-12/click beats walk 4-5.66. Plan: herd glyph to block (feed: 8->c->b), then herd glyph to one disk, kite b to other. Parking precision TBD.

## Previous level (L4) — SOLVED
- Disk (32,15) top-center; HUD=b; 4 sixes (7,26),(15,29),(43,27),(54,27) + 4 SPARE a-dots (bait; 12 units for 8 goal). TWO glyphs (6,39)/(48,39). Model multi-glyph (components, indep. steps, 71/71).
- Certified plan (search_l4.py): (47,21),(38,20),(15,25),(23,22),(32,21)=b,(32,15)=WIN. Right glyph eats 2 spare dots (fine).
- Budget N unknown (default 48; c1 may mispredict budget only -> fix N, recommit).

## Previous level (L3) — SOLVED (3 resets, full glyph rules learned)
- HUD goal: [b]. Disk center (5,57). 8 a-dots: (5,26),(11,26),(31,27),(36,29),(8,41),(12,47),(33,47),(30,51) = exactly 8 units.
- GLYPH = NEAREST-PIECE CHASER (48/48): center=round(centroid); target=min-euclid piece anchor; step=(clamp(dx,±4),clamp(dy,±4)) per PAID click, AFTER click effects; EATS piece if step lands ON its anchor (GUESS — testing now via sacrificial no-op click). DASH RULE: if the click consumed its pre-click target, glyph teleports to MIRROR point 2*T−C (no clamp; confirmed (42,29)->(30,29) through (36,29)). Dash = weaponizable (fling glyph by merging its distant target). Freeze-at-wall guess untested.
- Kiting math: piece hop ≤ ~8.6 vs glyph 5.66/click; arrival range = |dx|≤4&|dy|≤4 → piece in that range MUST move/be-consumed on the very next click. Lone b outruns glyph (+3/click).
- L3 budget N=48 ✓. 8 units = b exactly; eaten piece => RESET (refunds budget).
- ENDGAME TRICK: merge so the final piece spawns AT/NEAR dest; b@dest fires level_up instantly.
- EAT RULES v3 (62/62): ALL proximity via piece's NEAREST CELL (like pulls): pre cellΔ<=(4,4) -> half-step floor(Δcellcentroid/2+0.5)+eat; else clamp4 step toward ANCHOR, eat iff post cellΔ<=(2,2). Eaten: downgrade+eject (far cell from INT center, scan-order tie-break, +9 dominant axis, spawned top-right cell there; tier1 destroyed). units<needed -> RED recolor.
- CONSUMED/MOVED TARGET: successor >=6 away on an axis -> normal retarget+step (CONFIRMED); successor <=(3,3) -> mirror dash 2T-C (1 obs); 4-5 zone UNKNOWN (avoid).
- PULL RULE FINAL (57/57): piece pulled iff min CELL distance^2 <= 64 (R=8 to nearest cell of piece; bigger pieces reach farther). Confirmed: a-fail@68, f-pull@81-anchor(cell 64), f-fail@100-anchor(cell 81). Design margin: bystander cells >=100.
- L3 SOLVED by search (search_l3.py: validated sim + beam search + unit-conservation pruning; forbid 3+ merges): 9 clicks.
- UNTESTED: moving (not consuming) the glyph's target — model says dash-through-old-pos; plan robust either way.
- CASCADE STRATEGY (beats the chaser): every time glyph closes in, CONSUME its target with the next merge -> only short mirror-dashes, never an eat. Fs flee along bottom; final f+f merge AT dest so b spawns on goal; final dash lands glyph harmlessly.
- Post-reset plan (12): (28,48)P2,(9,45)P3,(7,31)P1,(6,38)f1,(30,34)N1[dash->34,29],(31,41)f2[dash->26,39],(26,48)f2,(5,45)f1,(19,53)f2,(12,56)f2,(3,51)f1,(5,57)FINAL b@dest.
- CAUTION: interrupted turn-attempts leave file artifacts (dup _move_glyph cleaned; notes merged). Check files after restarts.

## Previous level (L2)
- HUD goals: [b(4), f(3)] left-to-right; disks: (9,50) & (23,50). 6 a-dots + 3 sixes = 12 units = b+f exactly.
- Model generalized: dests = all 9-disk component centers; goal = every dest holds a goal-tier piece, multiset == HUD pieces. 26/26 green. (L0 "core"/plus were just decor; dest = disk center always.)
- Plan (18 clicks): merges (31,18),(58,23),(10,25),(25,18),(52,23); moves (44,22),(37,20); f-merge (31,19)->b; b hops (25,24),(19,30),(13,36),(9,43),(9,50)=left disk; then (23,31),(17,28)->f,(20,35),(23,42),(23,50)=right disk -> level_up.
- Assignment guess: b->left disk, f->right (HUD order). Model fires on any matching; if reality needs the swap, final click mispredicts -> swap.

## Previous level (L1)
- Palette box rows0-3 x0-15 (bg5): 2x2 swatches a(x1-2),6(x5-6),f(x9-10),b(x13-14) at y1-2. Legend/progress?
- HUD piece slot (x30ish): 4x4 b-block at x30-33,y3-6 (L0 had 3x3 f there = the mover!). So mover this level = 4x4 b? Not on board yet.
- Solid 9-disk 9x9 rounded, center (33,27), NO core.
- 8 a-dots: (18,37),(41,37),(37,40),(16,41),(49,54),(14,55),(47,56),(16,57).
- Budget bar full 64. L0 model passed; L0 cleared by landing block on core (level_up confirmed).
- click (25,35): a-dot (18,37) TELEPORTED to click (Δ cheb7! > L0's 6). Selection rule ambiguous: nearest-dot vs scan-order-first (both = (18,37)). Range metric: eucl<=~9 or manh<=12 now favored over cheb6.
- MERGE-CHAIN HYPOTHESIS: palette a->6->f->b = merge sequence, sizes 1 -> 2x2 -> 3x3 -> 4x4. L1 goal: 8 a's -> 4 6s -> 2 fs -> 1 b (4x4, HUD shows it). Merge trigger: two same-color objects adjacent/overlapping?
- CONFIRMED ENGINE (model v2, 15/15): click=magnet with radius^2<=81 (81 vs 100 untested gap): ALL pieces with anchor in range get pulled to click; 1 piece->move, >=2 same tier->merge to next tier at click. Tiers: a=1x1(10), 6=2x2, f=3x3(15), b=4x4(11); anchor span -(s//2)..+(s-1-s//2) (2x2 anchor=bottom-right, 3x3 center).
- b 4x4 created at anchor (38,45) (cells x36-39,y43-46; 4x4 anchor span -2..+1 CONFIRMED). Creation did NOT level_up.
- UNIFIED GOAL RULE (model, 23/23): HUD slot piece (band, x>=17) = goal tier; destination = core center if marked else 9-disk bbox center. level_up when goal-tier piece anchored at dest. L1 dest=(33,27).
- Delivering b: hops (36,38),(34,34),(33,27). Watch: does disk block overlap?

## Previous level (L0)
Layout (from ENTRY_GRID):
- bg bands: rows 0-9 color 4 (top band, maybe HUD), rows 10-62 color 5 (play area), row 63 all 0.
- Ball: 9-colored disk bbox x44-52,y11-19, center (48,15), 3x3 core of 3s at (47-49,14-16).
- Dotted 3-trail on anti-diagonal x+y=63, dots at odd y from 17..57 (step 2), except y=53 (0-plus there). (Earlier "anomaly at y=25" was my transcription error — trail is perfect.)
- 0-plus (5 cells) centered (10,53) — lies exactly on trail.
- f 3x3 block bottom-left, center (4,59) — trail endpoint.
- f 3x3 block top, center (31,5) in the 4-band.
Goal hypothesis: ball travels along dotted path to f-block "hole". Trail = trajectory preview.

## Hypotheses to test
- Exact range metric: cheb6 vs manh12 vs eucl~8.5 (all fit history; model uses cheb6). Refine if a future move surprises.
- Landing on core (48,15) = level_up? (committed plan tests it)
- What happens at budget exhaustion?

## Confirmed facts
- Block teleports center->click if within range (cheb<=6 consistent); cost 2 budget cells (row 63, right-to-left); dots landable; plus consumed on landing (reveals dot at its center); top-band clicks free no-ops; action7 no-op; failed (out-of-range) clicks still cost 2.
- Model in world_model_v5.py passes 7/7. BFS plan: (20,43),(26,37),(32,31),(38,25),(42,21),(48,15).
