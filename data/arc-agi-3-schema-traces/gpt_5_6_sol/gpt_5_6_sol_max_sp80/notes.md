# ARC3 game notes

## Core model
- Actions1/2/3/4 move selected sprite up/down/left/right by derived unit; click selects visible 8 or 15; selected cells render9; action5 tests.
- Yellow4 caps adjacent to6 define global direction; isolated/embedded caps also emit in that direction.
- Flow splits at platform ends; coincident inputs merge (adjacent remain distinct); wholly offscreen branches vanish.
- An immediately-upstream, diagonally-adjacent platform can seal one splitter outlet.
- Movable objects are persistent layers. Composite 8-4-8 sprites and L-shaped colour15 elbows move/select as units.
- Sideways flow collected by an ordinary bar resumes the board's global flow from that bar's horizontal ends.
- Elbows funnel accepted input to the L component's bottom row, then release toward the horizontal arm's direction.
- Four animated action5 previews are allowed per level/reset; a fifth press kills immediately.
- Timers: L0=30,L1=45,L2≈100,L3=120,L4=100.

## Cleared
- L0 splitter alignment; L1 three-way tree; L2 multi-source/offscreen disposal; L3 movable emitter/outlet blocking; L4 movable elbow plus three top and one side cup.

## Level5
- Final level, unit3, downward flow. Interior macro origin(5,2), 18x19. Main source x8; targets {D8,L7,L12,R10}.
- Movables: selected elbow F1 `f./ff` at (8,5); vertical bar V at (13,4), h4; composite H 8-4-8 at (6,10), embedded source x8; elbow F2 `.f/ff` at (8,14).
- Preview 1 terminals were {R3,R8,D5,D11,L14}: main D8 enters F1 -> D7+R5; V splits R5 at y3/y8; H splits D7 to x5/x11; embedded D8 enters F2 and exits L14.
- Preview 2 at H=(9,6),V=(9,8),F2=(10,9),F1=(12,10) confirmed D8 and R10. H's D11 enters F2 -> L9+D12, but V touching F2 at x9 seals L9 instead of splitting it; thus both left cups remained empty.
- Exact correction: shift H,F2,F1 all right once, leaving V. Gap x10 lets L9 propagate into V and split to L7/L12; D13 enters shifted F1 for R10; main remains D8. Model predicts win.
- Two previews used; L5 timer confirmed budget120. Current failed-flow focus is H; next actions: H right, F1 right, F2 right, test.
