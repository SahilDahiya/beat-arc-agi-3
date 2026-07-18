# ARC3 Notes

## Confirmed general mechanics
- Logical cells are 3x3, phase pixel(2,2). Arrows move selected piece one logical cell; action5 rotates 90° CW in a top-left-anchored tight bbox, then shifts the rotated box just inside the board if needed.
- Exact terminal-to-terminal/socket overlap renders3; separation restores endpoints. Completion when no visible free8 remains.
- Pieces may occlude; correct rendering is object-layer composition, not collision blocking.
- L0-L1 click swaps colored cores with black0. L2 uses grey inactive silhouettes: click reveals clicked piece's intrinsic core color and turns its degree-1 silhouette blocks into8 terminals; old selected piece becomes all grey4.
- Tiny row0 black meter fragments are not selected cores.

## Completed
- L0 two-piece docking.
- L1 packing: A15 fixed (3,3), B11 ori0 (4,5), Y14 ori0 (8,6), M9 ori3 (12,8).

## Level 2
- Three pieces. Initial active E14 has vertical ports separated6. Inactive upper grey size7 (identity0) and lower grey size22 (identity15); grey graph degree-1 blocks are latent ports.
- Model now stores all three piece layers/poses explicitly and re-renders selected/inactive overlap; all history backtests.
- The first bridge made E's two visible ports purple but did NOT finish: all six latent ports must pair, including the unused upper/lower endpoints.
- Upper is fixed with ports (10,4),(15,3); lower is now in its final pose with ports (10,4),(15,9).
- L2 meter confirmed exact 4-actions/pixel: 128 uses.
- Lower finished its target pose, but level did not clear because E orientation0 causes five core overlaps despite all ports pairing. Final assemblies forbid nonterminal overlap.
- Exact packing search found the unique collision-free fix with upper/lower fixed: E orientation2 at top-left(15,3), ports (15,3),(15,9). Completed.

## Level 3
- Background9. Initial active identity10 has 23 core blocks and ports (2,10),(7,8).
- Three inactive grey connector silhouettes: size3 ports (5,15),(7,15); size11 ports (11,6),(15,6); size16 ports (14,13),(14,18).
- Hidden small connector identity is11 (not0); click rendering now backtests.
- Exact collision-free loop packing while keeping initial identity10 fixed has two variants. Use the cheaper: small11 vertical bbox(2,10), ports (2,10),(2,12); medium grey orientation1 bbox(4,8), ports (7,8),(7,12); large grey orientation1 bbox(2,12), ports (2,12),(7,12).
- Small11 is parked vertical bbox(2,10), pairing the initial piece's port at (2,10).
- Medium14 is parked orientation1 bbox(4,8), pairing at (7,8).
- Large hidden identity12 completed the loop; L3 cleared.
- L3 meter confirmed same 128 uses as L2: second pixel appears at charged turn5.

## Level 4
- Background15. Entry selected piece identity11 has core blocks (8,4),(8,5),(8,6),(9,6), three blue ports (9,4),(7,5),(10,6), plus an adjacent marked black core block (8,7).
- Model generalized rigid pieces to preserve differently-colored marked core blocks during movement/rotation.
- Inactive grey shapes: size6 ports (15,15),(17,16); size10 ports (15,2),(17,1); size11 with three ports (3,12),(3,14),(3,16). Total visible+latent blue ports =10, so the black block is core, not an endpoint.
- RIGHT confirmed the black mark moves rigidly with identity11; backtest exact.
- A pose search found no way to pair all 10 assumed degree-1 ports, even before collision constraints. Therefore some L4 grey leaves/active marks have different terminal semantics; do not reuse the L2/L3 port inference blindly.
- Size6 reveal: identity12; both leaves are blue (15,15),(17,16). Size10 reveal: identity10; both leaves are blue (15,2),(17,1). Thus those terminal templates are sound.
- L4 clicks are not free: rather, the level has two free initial actions. RIGHT and first click filled nothing; second click produced pixel1. Model start phase corrected; 153/153 backtest.
- Three-ended size11 reveal: identity14, and all three leaves (3,12),(3,14),(3,16) are blue. All latent terminal extraction is confirmed.
- L4 action5 is confirmed ordinary CW; transformation is not the missing mechanic.
- Treating the marked black leaf as an additional dockable site yields 11 total sites and 66 collision-free packings with exactly one free site. Cheapest structured candidate keeps identity11 fixed: size6 ori0 bbox(9,7), size10 ori2 bbox(8,1), three-port ori2 bbox(11,6); black (9,7) pairs size6 and only three-port bottom (11,10) remains free.
- L4 meter fully resolved: it is a 150-action scale rendered by nearest-pixel rounding, desired=floor((actions*32+75)/150). This exactly yields action-count thresholds 3,8,12,17,...; the earlier apparent docking delays were just the rounding pattern.
- Size6's terminal covering black stayed blue, and UP adjacency produced no joint. Black is noninteractive marked core; L4 still requires exact terminal overlap.
- Identity10 reached ori2 bbox(8,1), but the black-capped candidate did NOT clear despite the expected visible joints.
- The connected/two-free-end candidate failed because it doubled A-B. A nearest simple identity-cycle candidate was then built exactly: B ori0 bbox(8,6), C ori1 bbox(7,5), A ori2 bbox(9,1), E ori2 bbox(11,4), edges B-C-A-E-B and free B/E ends. It ALSO did not clear. Thus neither generic connectivity nor simple-cycle topology is the L4 goal.
- Clicking black selected B normally, but action5 on marked B is SPECIAL: it does not rotate. The old black tip becomes ordinary B core, the tip advances straight outward one cell, and a new blue terminal sprouts clockwise from the old tip. First growth changed black (9,9)->(9,10) and added blue (8,9); model backtests 220/220.
- One-growth exhaustive search proposed a packing using two triple intersections. Moving A into it proved joints are strictly one-to-one: a selected port landing on an already paired inactive joint stays blue, not purple. Renderer/completion require exactly two ports per joint.
- Marked B's four morph rows are deterministic: add left length1; right length4; left length1; then a FINAL right length3 row that consumes the black tip (no new marker). Completed B has seven ports and bbox(8,6). Model backtests 236/236.
- Exact one-to-one, collision-free search on the completed 7-port B found one relative solution: B bbox(8,6), C ori3 bbox(12,10), A ori3 bbox(10,6), E ori0 bbox(6,7). All seven B ports paired; L4 cleared.

## Level 5
- Background9, five pieces. Active identity14 has 3 ports (5,3),(3,5),(1,6). Four grey components: size7 two-ended ports (1,12),(2,17); size7 three-ended ports (6,8),(7,10),(8,6); size10 two-ended ports (15,3),(17,4); size16 three-ended ports (9,17),(11,14),(13,14). Total 13 ports is odd, so likely another hidden morph/special identity must be discovered.
- Three-leaf size7 reveal: identity11 with blue ports only (8,6),(6,8); lower leaf (7,10) is black morph tip. Morph1: old black becomes core, add blue forward at(7,11), and turn black right through core(8,10) to(9,10). Morph2 continues right through core(10,10) to black(11,10), adding no port. Morph3 makes a T at core(12,10), adds blue(12,11), and turns black up to(12,9). Morph4 exactly matched a straight two-cell extension upward: core(12,8), black(12,7), no port. Morph5 is the final cap: old black(12,7) becomes core, add forward core(12,6), blue clockwise at(13,7), and blue counterclockwise at(11,6); black is consumed. Completed B has six ports. The large size16 reveal is identity15: all three graph leaves (9,17),(11,14),(13,14) are blue, plus an interior black stretch marker initially at(12,18). F action5 inserts one core at the marker, shifts the entire right connected half one cell right, and advances black right: first stretch moved marker to(13,18). This is encoded. The vertical two-leaf size7 is ordinary identity10 with two blue leaves. The last size10 is ordinary identity12 with blue leaves (15,3),(17,4) and no marker. Thus only B11 and F15 are special. L5 meter is nearest rounding on exactly 200 actions: pixel thresholds begin at actions4 and10; full model backtests 269/269. F action5 is reversible: three forward stretches reach width9 and consume black; the next action contracts the right half back to width8 and restores black at(14,18), rather than rotating. This inverse is encoded; model backtests 273/273. Exhaustive exact search over every observed B stage and all four F widths finds no solution, even port-only for completed forms. Completed B11 action5 reverses its final cap, restoring stage4; F similarly toggles width8/9. Ordinary C12 action5 is confirmed ordinary CW rotation. The earlier exact search had an invalid open-port pruning bug: removing it finds the unique completed-form assembly with marked orientations fixed. Choose global anchor F bbox(5,11): B11 bbox(6,6) ori0, C12 bbox(11,4) ori0, E14 bbox(4,4) ori0, A10 bbox(4,9) ori0. Ports pair at (5,14),(12,11),(7,11),(13,7),(6,8),(11,6),(8,6),(4,9), with no core collisions. Current route has C at target bbox(11,4) ori0, E target(4,4), A target(4,9), B stage4 target(6,6), and selected F at(9,14). F is a stateful ping-pong telescope: expansion F0→F1→F2→F3 flips its hidden direction, then later actions contract F3→F2→F1→F0 even though intermediate grids do not encode direction. Actions confirmed F2→F1→F0 and then the minimum bounce F0→F1; model stores stretch_dir and backtests 305/305. Finish by cycling F back to completed F3, then LEFT4 UP3 to target(5,11), click B core screen(23,23), action5 completes B and should win. Final flags modeled as win on L5.
