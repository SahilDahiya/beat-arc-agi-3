# Notes — ARC3 game

## Confirmed mechanics
- Actions 1/2/3/4 move the active shape up/down/left/right by 3. Action5 cycles active shapes.
- Active center is 0 unless hidden by a higher layer. Hollow X/diamond centers become background after moving; an unmoved inactive same-hue center can retain entry fill.
- Framed same-hue markers encode placements. Level clears when every movable shape reaches its marker-derived placement.
- Layer order: X below diamond below solid plus/line.
- L0 and L1 cleared; model exactly replays all transitions.

## L2 current analysis
All shapes/markers are hue8:
- Line aligned at (27,6); X aligned at (42,24).
- Active diamond now (21,48), goal (18,30).
- Global marker exact-cover is essential: independent nearest fits are ambiguous. The unique disjoint cover is line (27,6), X (42,24), diamond (18,30).
- Action5 cycle line -> X -> diamond. Leaving aligned line charged; leaving aligned X was free.
- Movement cost is a per-shape 0/1/2 meter: ordinary moves at meter2 charge and reset; other moves increment. Initial meters line=1, X=0, diamond=2. This generated the apparent coordinate residues.
- A due line/diamond move that touches one of that shape's exact-cover markers is constructively free and leaves meter2, deferring the charge. X marker crossings do not waive charges.
- Same-hue overlaps affect layering/visibility only, not movement cost.

## Current plan
- L2 cleared by diamond left once/up six exactly as predicted.

## L3 entry / current hypothesis
- Two central shapes: active solid plus hue6 at (54,36), apparent radius13 (right edge initially clipped); inactive hollow X hue a at (24,21), radius10.
- Framed markers: hue c at (15,18),(27,30),(15,43); hue e at (48,21),(36,24),(30,39).
- Six bordered swatches form a legend: top a,c,d and bottom b,6,e. Column c/6 strongly suggests hue6 plus belongs to c markers; those markers define a clean plus goal near (15,30).
- Specialized L3 parser/renderer ignores legend swatches. First plus up move (54,36)->(54,33) and a free footer matched exactly, supporting by3 translation and initial meter0.
- ACTION5 transferred control to X at (24,21) with no recoloring and charged one footer. L3 handoffs always provisionally charge.
- Second ACTION5 returned X->plus, confirming exactly two selectable shapes. It was footer-free: leaving plus charges, leaving X is free.
- Plus left 54->51 matched exactly and revealed a true symmetric radius13; footer remained free. Its meter is now2 after the earlier up and this left.
- Plus x51->48 was its due third move and charged exactly; crossing foreign e marker (48,21) did not waive. Meter reset0, footer length2.
- Queued left route reached x33 after five moves. x39 charged as expected; x33's only mismatch was layering: X hue-a remains above the plus at intersection (33,30). Fixed; all 118 transitions green.
- Remaining route reached x24 after three moves: x30 charged, x27/x24 free. At x24, the only mismatch was the inactive never-moved X's entry-filled center: hue-a remains a top-layer pixel over the plus. Fixed; all 121 transitions green.
- Hollow-center interaction is a deferred one-use grace, not a reset: x24 armed it; due x21 was waived while meter stayed2; x18 then charged/reset. This exactly fits all 123 transitions.
- Plus reached full c-marker placement (15,30), meter2/footer5. Its active center lies on the higher X arm at (15,30), so 0 is hidden and hue-a remains; this was the sole mismatch and is now modelled (125/125 green).
- Plus->X handoff charged footer6. X first right to (27,21) was free and rendered exactly, meter1.
- X right x30 was free; due x33 charged even though its arm hit e marker (36,24). Thus ordinary framed-marker contact does not waive the X meter. X now (33,21), meter0/footer7.
- Route to X (39,27) matched fully: x36/x39 free, y24 due charge, y27 free; footer8, X meter1.
- X reached (39,30) (meter2/footer8), covering the two far e centers, but this did NOT level up (#134); grid prediction was exact. Therefore e-marker fit alone is insufficient and the six swatches likely encode a palette/recolor condition.
- ACTION5 at that X placement returned control to plus but charged footer9 and filled the inactive moved X center hue-a. This matches the completed-outline handoff cost rather than a level lock.
- Handoff from a marker-fit placement charges and resets that shape's meter.
- Palette mechanic confirmed at #143: plus endpoint entering the top-middle c well recolored the whole plus 6->c. Goal now requires fitted centers plus target marker hues (plus c, X e).
- L3 cleared after painting plus c and X e, returning them to (15,30)/(39,30); model exact through 168 transitions.

## L4 entry
- Movable shapes: active X b center(24,42), radius11; diamond e center(30,18), radius9; plus c center(54,33), radius14.
- Palette wells: b,a,e,9,8. Visible framed markers: 9 at (21,6),(39,6),(33,45),(24,51),(45,51),(33,60); 8 at (51,27),(42,36).
- Unique reachable exact cover: diamond -> (30,6) painted9 (top pair); X -> (45,33) painted8 (two 8 markers); plus -> (33,51) painted9 (four lower 9 markers).
- New grounded L4 parser/renderer/palette/exact-cover branch installed; all prior 168 transitions green. Probe active X right toward its 8 well/goal.

## L5 deformation
- Shapes are a hue-b 72-cell flexible rectangle and a hue9 plus made from two length25 strokes; translations are by3 with per-object 3-step footer meters. ACTION5 switches without advancing/resetting the meter.
- Color1 ring x28..35,y28..35 reshapes on collision. Rectangle left-pushes keep its left side, retract right by3, and alternately extend top/bottom, conserving perimeter. It is now parked at exact b bbox x45..54,y30..57.
- Plus is two independently sliding strokes. At V x30,y3..27 / H y15,x18..42, a down push into the device pinned V and selection anchor, while H slid to y18. The due collision charged. Model represents explicit H/V lines and exactly replays through #340.
- Four hue9 markers require final V x12,y3..27 and H y9,x6..30: each stroke remains length25, with H offset (-6 y) from V midpoint and V offset (-6 x) from H midpoint.
- Planned manufacture: move current cross far left and below device; approach upward at x30 to pin V and slide H upward 3 times; move right of device, approach to H y33, push left twice to pin H and slide V left6; then move up8 and left10 to exact marker cross.

## L7 final level
- Two conserved-perimeter rectangles deform against color1 devices in 3-cell increments. id1 is solved: color b, bbox x9..15,y39..57. id0 goal is color6, bbox x6..21,y45..54.
- After passing its exact target aspect, a foreign-repainted endpoint in the same orientation receives direct deformation credit (#739). Crossing the solved anchor's projected centre axis credits only the first new coordinate, without banking or crediting endpoint-identity exchange (#740-741); at an anchor edge, the full enter/exchange/depart sequence is constructive (#743-745).
- Route to repaint6: finish rising to y15..18, left9 to x0..21, down2 across standalone q6 panel to y21..24, up2, right13 to x39..60,y15..18. Then upper-device rotation, vertical gap descent, lower-device rotation to 16x10, and left8 to goal.
- Palette repaint ranking ignores the carried hue. On first upward strip entry it ranks newly covered cells, tie left (#746); on continued overlap it advances to the rightmost different touched panel (#747, e->8). Continued upward horizontal-transport overlap is ordinary, and simultaneous overlap suppresses projected approach credit from a different standalone panel, so #747 charges.
- Fully clearing a standalone palette upward banks one due-move release waiver. The c-panel release at #751 made the first left translation #752 free. While carrying the other rectangle's entry hue c, id0 receives no projected credit from an own-target edge (#753), but its own target centre remains constructive (#759). A four-cell transport's centre-to-edge projection exchange with the solved anchor remains constructive even during along-axis overlap (#757). The first upward withdrawal from a matching standalone palette is constructive even when the hue stays6 (#763). A rightward 22x4 transport receives a projected standalone-panel exit phase even when vertically disjoint (#775); leftward exits do not (#603). When painted, expanding away from the four-cell endpoint into the other outline's aspect is a completed detour and charges even if rotated (#622,#785); reaching that aspect while compressing back toward four cells remains constructive (#625,#790). Painted near-device withdrawal is constructive at the square midpoint (#788) and at an exact own aspect while reducing contact (#646), but ordinary at a foreign 7x19 aspect (#791). A painted four-cell transport receives a final device-release phase when it crosses outward beyond the four-cell guidance horizon (#794); the analogous foreign-painted exit charges (#741). A painted transport's projected device-side phase is constructive only while it retains a projected overlap with some device (#776); converting its sole projected overlap into a disjoint side alignment charges (#797). Model 803/803 green. A vertical four-cell transport gets a constructive downward selector-release when its selector leaves a standalone palette's y-span (#800); horizontal/right selector exits remain ordinary (#697,#772). Once both rectangles are correctly painted/solved, first projected target-edge guidance is ranked only on the target's long axis; id0's x-edge is constructive (#684,#771), but its short y-edge45 charges (#803). At painted projected-device side alignment, approaching the device is constructive (#806), while withdrawing from the only projection charges (#797). Device-withdrawal credit for a painted exact aspect is suppressed when the move first enters its own marker points: that exact-placement milestone charges (#816), overriding the reduced device contact that was constructive at #646. Model 816/816 green. A direct outline-overlap topology change is constructive when a long collinear shared edge contracts to two transverse crossings (#819). Model 819/819 green. Active id0 hue6 exact 16x10 is x12..27,y45..54; two lefts remain (x9..24, then goal x6..21).
