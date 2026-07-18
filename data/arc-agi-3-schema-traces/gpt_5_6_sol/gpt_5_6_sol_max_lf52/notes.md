# ARC3 game notes

## Action semantics
- Confirmed click(6) on a movable peg selects it: colour-3 ring; every legal landing cell gets a colour-2 motif.
- Confirmed: clicking a marked landing executes the orthogonal jump, removes the jumped peg, and clears guides.
- Confirmed arrows: 1 up, 2 down, 3 left, 4 right; each moves every rail slider one 6px step when that slider's next rail cell is open. Action7 remains unconfirmed.

## Cleared level 0
- Lattice top 7x3 + lower 3x4; forced four-jump chain reduced 5 pegs to 1.

## Current level (1)
- Top 7x3 board tokens at tile top-lefts (13,15),(19,15),(31,15),(43,15); bottom 2x2 board token (43,51).
- Normal chain performed: top c1->c3, c3->c5; remaining top c5,c6 and singleton bottom peg.
- Central b/c object click was inert; connector lines appear decorative.
- Reducing each lattice separately to one peg is a DEAD END: remaining disks turn filled colour2 and a large colour-f retry icon appears bottom-left. Clicking its hollow centre resets all pegs exactly to ENTRY (meter retained). Model reproduces both.
- Thus goal is still likely one total peg; disconnected boards require an undiscovered transformation/connection.
- Central b/c object and colour5 line network likely encode that mechanic. Clicking central alone is inert.

## Connector/slider mechanic
- Confirmed action3 moves the b/c 6x6-faced slider left by one logical step (6 px); action1/2 were blocked at its initial horizontal track position. Mapping inferred 1 up,2 down,3 left,4 right.
- Slider travels a colour5 two-pixel rail network. Model now erases/draws its outline+shadow and follows rails, including corners.
- Slider cannot enter board tiles. At bottom it docks one logical cell LEFT of the 2x2 board; neither clicking adjacent peg nor slider alone does anything.
- Key insight: docked slider is likely a movable EXTRA EMPTY CELL. Intended solution: dock right of top board; after ordinary chain leaves adjacent c5,c6, jump c5 over c6 INTO slider (load it); transport loaded slider to bottom; jump from slider over bottom singleton into bottom-right empty tile. This reduces all pegs to one.

## Current solution progress (level 1)
- After RESET, slider docked right of top board (R4,U3,L), top performed c1->c3, c3->c5.
- Docked slider is confirmed extra cell: selecting c5 marked its inner c area; c5 jumped over c6 into it. Loaded face renders an e disk on c background and carries it during movement.
- Loaded slider transported to bottom dock via D3,L7,D3,R4 and selected.
- Special-source selection: slider face non-peg pixels turn 3 except four b corners; bottom-right tile is marked.
- Final bottom transfer cleared level 1.

## Current level 2
- 24 regular tiles in 3 components:
  - main irregular 16-cell component, 5 pegs at (12,12),(30,12),(12,18),(24,18),(18,24);
  - bottom 7-cell component, 2 pegs at (12,48),(24,48);
  - far-right singleton tile (60,12) with 1 peg.
- TWO b/c sliders initially at (41,11),(35,47); action3 moves BOTH left simultaneously to docks (35,11),(29,47). Multi-slider model generalized and backtest-green.
- Strong hypothesis: the two synchronized sliders are linked portal ends. Forced main-board chain loads upper dock:
  (12,12)->(12,24)->(24,24)->(24,12)->upper slider (36,12).
  Observe whether the peg appears in upper, lower, or both.
- Bottom board initially has no legal move (pegs x12,x24 separated); it needs an additional transported peg somehow.
- Sliders are NOT portals: loading upper affected only upper.
- Oversized world/camera confirmed. At left camera bound, L docked both. First R with loaded upper pans viewport 8px right while sliders move 6px in-world (net screen -2); new offscreen columns reveal many more board tiles/pegs. Model converted to stateful predict with camera offset, slider-free underlay, and learned strip world x64..71; full backtest green.
- Full world mapped: width 88, camera max cam24 (extra R is inert). Dynamic off-screen cells are now preserved in model. During a pan each slider independently tries ±6 world: moving slider nets ∓2 screen, blocked slider shifts the full 8.
- Far 24-cell board initial pegs: (60,12),(72,18),(78,18),(72,30),(78,30),(66,42),(72,48). Upper docks as cell(54,12); lower as cell(60,48). Abstract search found the unique 7-jump transfer after upper delivery: 78,18→66,18; 78,30→66,30; upper54,12→66,12; then 66,12→66,24→66,36→66,48; finally 72,48→lower60,48.
- Current cam24: upper is loaded at right dock; lower is mid-track world bbox(41,47). Route lower to right dock U,U,R,R,D,D,R, perform far chain, then return loaded lower via L,U,U,L,L,D,D,L,L (camera pans back during first 3 Ls). At left dock jump slider30→tile18 over24, then tile18→6 over12; this should leave one total peg and clear.

## Cleared level 2
- Two synchronized sliders connected three peg components across an 88px horizontal world. Main→upper slider→far board→lower slider→bottom board solution cleared; model now preserves dynamic off-screen world through reverse pans.

## Current level 3
- Visible main 7x3 board at tile x6..42,y18..30: pegs (12,24),(42,24); two colour-f/7 block sprites replace cells (18,24),(30,24).
- One empty slider bbox(53,23), with rail continuing off the right edge. A lower board begins at x30..42,y60 and is clipped below; peg (36,60). Rail also re-enters from right at y49+, suggesting a larger 2D world.
- Before loading, slider travels beyond fixed cam0. Confirmed top track bboxes x47..71; Down is blocked. Model tracks clipped/hidden sliders; retry detection distinguishes small f locks.
- Top hidden rail is a dead-end: positions x53,59,65,71; at x71 R/U/D all blocked. Empty exploration does not reach the lower rail.
- Level3 has TWO synchronized sliders: upper initial world bbox(53,23); lower initial hidden bbox(77,47). Top horizontal track x47..71; lower x53..77. Model reconstructs both exactly.
- f/7 sprites are permanent jump supports: a disk can leap over them, but they remain and are not counted as disks. Forced main chain 12→24 over lock18, 24→36 over lock30, 36→upper-slider48 over peg42 succeeded.
- Loading upper triggered automatic camera snap cam0→30, revealing world x64..93 and a new vertical board (peg78,24; locks84,30 and84,42) plus bottom peg36,60.
- In stage 2, each R moves both sliders +6 world AND camera +6. Full world mapped through x117; current cam54, upper loaded cell72/24 and lower empty cell78/48 at far docks.
- Far transfer completed: upper72→84 over disk78; down locks to84,48; disk102 down locks to102,48, left over lock96 to90; then 90→loaded lower78 over disk84.
- Loading lower triggered camera snap (54,0)→(39,30), revealing a THIRD compact slider. Four L + D2 route loaded lower to bbox53/59; R3 aligns third53/71; lower jumps over lock54/66 into third. Camera follows the loaded slider but lower-stage horizontal camera is bounded at x=15 (confirmed: loaded third moved 53→47 while cam stayed15). Final chain: carry third to cell30/72; down over lock30/78, right over peg36/84; empty third R2 to cell42/72; disk up into third over lock42/78, up over lock42/66 to42/60; left over peg36/60 to30/60. With fixed cam15, final screen x coordinates are world-x minus15: x15 for world30 and x27 for world42.

## Cleared level 3
- Three synchronized sliders and permanent f/7 supports connected four stages in a 118x106 world. Camera tracked only the loaded slider, with stage-specific bounds. Final third-slider chain eliminated both remaining pegs; level cleared in 52 post-reset actions.

## Current level 4
- Initial regular board: 3x3 cells x12,18,24 at y18,24,30; peg12,24 and permanent lock18,24. Separate cells36,24(empty),42,24(peg).
- Top rail has an empty b/c slider and a b-framed f/7 lock-slider. Confirmed both receive arrows synchronously: initial Left moved normal17→11 and lock41→35. The lock is now parked at logical (30,24) after L,D3; its rail/board dock variants are modelled exactly. It is a dynamic permanent jump support, not a disk/landing.
- Immediate chain completed: disk12,24 jumped over fixed lock18 to24, then over movable lock30 to36. Normal was routed to48,24 while lock parked (D3,R3,L5,D2,R3,D6,R3,U3); disk36 then jumped over42 into the carrier.
- Loading normal snapped cam0→18. Route U,R3,D put it at world cell66,24; jump over peg72 into tile78. This did NOT clear: it snapped cam36→69 and revealed stage 2/world x100..132 plus a new movable lock carrier at world cell126,18. Model reproduces the snap exactly.
- Stage-2 pegs: world (78,24),(120,6),(114,30),(102,54); fixed locks (102,6),(96,24),(102,30),(96,48). New lock rail: top y12 x84..126, verticals x84/108/126 to y36, bottom y36. Weighted search proves this optimal 56-action plan (screen clicks; each arrow/click listed): `U,L7,D2; 9,24→21,24; U2,R4,D2; 21,24→33,24→45,24; U2,R; 45,30→45,18→45,6; L3; 51,6→39,6→27,6→27,18; L2,D4,R2; 27,18→27,30→27,42→27,54; 33,54→21,54`. First segment through jump9→21 is validated. Stage2 alone needs56 actions. Confirmed at action65: after all 64 cells reached colour1, cell0 became colour2; the meter is a layered counter, not a hard budget (model now increments the leftmost minimum-colour cell).

## Cleared level 4
- Normal and movable-lock carriers connected the initial board, a first far board, and a second 4-peg stage in a 133px world. The stage-2 56-action route in the prior note cleared exactly. Action counter is layered, not a budget.

## Cleared level 5
- Entry has a top 4x4 board (one e peg at18,24 and a colour-8 jumper at18,18), a lower 6x3 board with peg12,48, a lower extension peg24,54, and two edge-adjacent ordinary b/c carrier faces bbox47,41 and53,41. Slider detector rejects false overlapping b-windows.
- Colour8 is confirmed selectable exactly like an e disk and preserves its colour. Its jump18,18→18,30 over e18,24 moved the 8 piece but DID NOT consume the intervening e disk: colour8 is a non-capturing jumper/tool. Model encodes this and the full 330-transition backtest is green.
- Confirmed: e18,24 jumped into lower-board tile18,36 over colour8 at18,30, and colour8 SURVIVED. Thus colour8 is an indestructible, non-capturing movable support: neither direction of a jump consumes either participant. Model encodes both directions; full 332-transition backtest green.
- The colour8 carrier reached156,18; e150 crossed it to162,18 and captured e162,24 downward, leaving e at162,30. Remaining e: (162,30),(138,36),(126,48). Confirmed finish route: D2; e162,30→150,30 over loaded8; route carrier D2,L2,U2 to144,30; e150,30→138,30 over8; e138,30→138,42 over e138,36 (capture); carrier D2 to144,42; unload8 left144→132 over e138; e138→126 over8; e126,42→126,54 over e126,48 (capture/level-up). Colour8 is excluded from the level5 goal count; full 399/399 remained green.
- The second reveal camera is a fixed far-board view at cam106 (unlike the first carrier-follow stage). After e162→150, carrier route has completed D2,L1; continue L1,U2 to dock loaded8 at144,30. Model fix restores full 406/406 history.

## Current level 6
- Entry has one ordinary e at tile(6,12) above fixed lock(6,18), one colour8 at(42,12) above fixed lock(42,18), one empty carrier bbox(35,35), and a bottom row y54 with fixed locks at x18,30. Carrier graph visibly docks below the top pieces at cells(6,24)/(42,24) and above lower fixed locks at cells(12,42)/(42,42), suggesting delivery of e to bottom x12 and colour8 to bottom x42.
- Visible carrier graph: start cell36,36; branch via cell24,36,U2 to top y24 rail x6..42; lower docks through x12,36→12,42 and x42,36→42,42. A disconnected-looking far-right rail component at x54 may imply a later camera/world stage.
- Bottom sequence e12→24→36→48 and colour8 42→54 triggered a camera snap cam0→44. Full world now mapped through x107; second empty carrier spawned at world cell78,24 while original empty carrier remains world42,42. Model tracks both and full 469/469 is green.
- New carrier component route to the required bottom bridge cell66,54 is L3,D2,L,D2,R2,D from78,24. First L exposed the displaced world82 board rim. The route has reached new-carrier cell54,48; its one-sided shadow must preserve the horizontal rail cut-through, now modelled with full 477/477 green. Remaining route R2,D to cell66,54. Then e world48→60 over8, and 8 world54→carrier66 over e60 loads it; this is now complete with carrier8 at66,54 and e at60,54. The forced e60→72 bridge matched without a reveal. Now carry loaded8 from66,54 to dock78,24 via U,L2,U2,R,U2,R3, then unload it across fixed lock84 into tile90,24. Afterward return the empty carrier to72,42 via L3,D2,R2,D so e72,54 can jump up over fixed lock72,48 into it. Visible new board has fixed locks world84,24;96,36;96,42;72,48 and regular cells world90 at y24/30/36/42, world102 y36/42.
- Delivered e to world90,30 and leapfrogged 8/e down to y36/y42. Colour8 world90,36→world102,36 over fixed lock96 triggered cam44→84; both pieces crossed fixed locks to world114. Carrier choreography ultimately loaded the hidden far e at world138,30; the other e is114,42 and colour8 remains138,36. Finish route: move e114,42 left twice across fixed locks to90,42; arrows `U3,R,L3,D,L,D` put loaded far e at114,24 above movable lock114,30; unload it to114,36, move it left twice to90,36, then e90,42 jumps up over/captures it into90,30. Colour8 is an indestructible tool excluded from the goal only after cam84 reveals the hidden second ordinary disk. Moved locks participate in normal outline geometry and an upper normal owns a shared six-cell seam. Level6 backtest 148/148.

## Cleared level 6
- Final hidden e was transported from world138 to114, unloaded over a movable lock, moved left across fixed locks to world90,36, and captured by the other e from90,42→90,30. Colour8 remained and was excluded only after the cam84 hidden-disk reveal. Final route cleared exactly.

## Current level 7
- Entry shows an 8x6 board (tile x12..54, y18..48), ordinary e at(12,24) and(54,48), fixed locks at(18,24),(42,24),(48,30),(18,36),(42,36), and colour9 disks at(30,42),(30,48). Two lower carriers exist: left bbox17,59 visible and right bbox47,65 hidden. Up brought only right to47,59; Right moved both to23,59 and53,59; Up then took only the right carrier around its turn to the upper endpoint bbox53,53. Their clean substrate is two disconnected row61/62 rail segments (left x7..30, right x49..56); the large board owns the upper dock's zero separator corner. Model exactly replays all three transitions. Colour9 is selectable, preserves its colour, and is confirmed indestructible/non-capturing in both roles: a 9 mover left its 9 support, and ordinary e24→36 left the intervening 9 at30,24. It is a reusable bridge tool like colour8 and should be excluded from the ordinary-e goal. Abstract search finds the forced first-stage load: route left carrier from current cell24,60 via L3,U4,R to cell12,36; then e12,24→24,24; 9(30,42)→30,30; 9(30,36)→30,24; e24→36 over9; 9(30,24)→30,36; e36,24→48,24→48,36→36,36→24,36→loaded carrier12,36. Loading did not immediately reveal another stage: ordinary e is now carried while the other e remains world54,48 and both 9 tools remain at30,30/36. The loaded carrier moved L then D to world bbox5,41 and triggered vertical camera follow cam_y0→6. The empty right carrier simultaneously reached bbox53,59, its short spur endpoint. Newly exposed substrate proves the true downward shafts are x25:26 below left bbox23,59 and x49:50 below right bbox47,59 (not x55). Further loaded Downs now reached world bbox5,53 with cam_y18. They revealed a second 8-column board beginning world y70: top-row colour9 tools at (48,72),(54,72), plus a horizontal three-carrier train at world y77—movable locks bbox17/29 flanking an empty normal bbox23. Loaded carrier reached world bbox5,59/cam_y24. The new train did not move on Down and is completed by bottom rims/shadow at world y82..84, so it has no downward branch. Its three adjacent faces remain at y77 (lock17, normal23, lock29) on a long horizontal rail. The loaded carrier reached world bbox23,65/cell24,66 at the shaft's true endpoint dock above the second board; shafts end at y70 (not infinite). The lower train is synchronized and now at lock cells36/48 with normal42 on row78. Transfer plan: L3 puts its normal at24 and the old right carrier at bbox47,59; D docks that carrier empty at cell48,66. The first Left confirmed that x55:56 below world row63 was only the departing carrier's rim, not a short vertical rail; the clean exposed spur is background and is now modelled. The two 9s were leapfrogged from48/54 to24/30 and e loaded downward from old carrier24,66 over9 into train normal24,78 exactly. The first loaded-train Right exposed that dock renderers must restore live moved-9 tiles rather than entry pieces; fixed with 57/57 green. Three more Rights carry it30→48 while the empty right carrier stays docked; 9s were leapfrogged24/30→42/48 and e unloaded upward into right carrier48,66 exactly. Before returning it, shift the lower train Left once so its right lock is not blocking the synchronized Right endpoint. Route loaded right carrier L,U,R,U to cell54,54 (camera30→24→18), then jump it upward over/capture the remaining e at54,48 into tile54,42.

## Cleared level 7
- Two reusable colour9 tools bridged two boards. The last ordinary e was returned by the right carrier and jumped upward over/captured the other e; level cleared exactly.

## Cleared level 8
- A loaded carrier exposed a far board through a long horizontal camera-follow rail. Two reusable colour9 tools were leapfrogged across its locks; the far ordinary e was brought to the terminal carrier dock and captured the carried e. The level cleared exactly.

## Current level 9
- Two ordinary e disks exist: top board e(30,4), lower board e now at(18,46). Colour9 is again a reusable, indestructible bridge tool and is excluded from the goal.
- Three empty upper carriers and a five-face colour9 carrier train share a 6px rail graph. The support shunt is complete: empty bboxes (5,15),(17,15),(29,15); colour9 bboxes (29,9),(53,21),(53,27),(53,33),(53,39). Carrier sprites render spatially top-to-bottom; the lower face owns the upper sprite's bottom outline/shadow, while the upper face retains the compact shared seam.
- The lower-board preparation is complete: ordinary e(18,46), empty landing(18,52), colour9 at (30,34),(24,46),(30,58),(36,52),(42,52).
- Top transfer succeeded: e(30,4) jumped over reusable colour9 carrier(30,10) and is now loaded in carrier bbox(29,15), logical(30,16).
- Loaded transport has completed U,R,U. Current top row includes empty bbox(11,9),(23,9), loaded-e bbox(29,9), colour9 bbox(35,9), with the right train at x53. Compact horizontal trains use the same ownership rule: the left face owns the shared six-pixel b column.
- Descent D5 and first Right matched geometrically except for a side-dock cap renderer, now fixed: one-sided carrier outline remains, but the substrate owns its zero top cap and fixed-5 side cap. Loaded-e carrier is bbox(11,39). One Right remains to bbox(17,39)/logical(18,40), then click 18,40→18,52 over/capturing lower e18,46 to win.
- The clipped initial bottom carrier hid the last three cells of the fixed right rail. The L9 underlay now derives the outer rail from ENTRY_GRID's longest frame and continues its final two columns to the bottom; all 33 L9 transitions backtest exactly.

## Confirmed facts
- Peg solitaire, movable rail sliders, layered action counter, and camera-panned oversized worlds recur across levels.
