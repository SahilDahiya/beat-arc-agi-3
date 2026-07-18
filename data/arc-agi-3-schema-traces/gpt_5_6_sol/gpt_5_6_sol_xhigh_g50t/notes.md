# Notes — ARC3 game

## Confirmed mechanics
- HUD slots record time-loop actors. ACTION5 finalizes/rewinds; after last slot starts fresh cycle. Replays advance only on successful live moves; blocked inputs discarded. Ghosts color2.
- Color8 = PRESSURE: remote retracts toward terminal while any actor occupies it; restores when last leaves. ACTION5 resets. Both color8 and solid color11 remotes physically block actor movement at their current lattice tile.
- Color11 = two-position TOGGLE: any actor entering a terminal toggles its solid remote. Open sweeps old/new 7x7 floor; close restores original wall/tether. On ACTION5 only the most recently LIVE-activated color11 device retains its state; replay toggles do not change this rewind focus. All other solid devices reset; focus persists across cycles.
- Color15 = powered PORTAL pair: while any actor (including runner) holds that connected controller, entering either outlined pad exits its paired pad. Multiple disconnected portal systems act independently.
- Color14 = automatic track runner. Each successful live tick takes the unique continuation other than its previous tile; at an endpoint/closed gate it bounces back. It resets on ACTION5 and triggers/powers devices.
- Bottom tape paints 1 in color9 cells lying in the rightmost floor(total inputs/2) columns; fixed frame cells remain.
- Live entering ENTRY_GRID center color9 completes level.

## Completed
- Levels0/1 pressure; level2 toggle + pressures/meta-cycle; level3 pressure + portal; level4 toggles + pressure + portal; level5 runner + gates.

## Level6 final
- 3 slots, start (26,26), runner (20,56), goal (32,50). Solid terminal/remote (20,38)/(2,38); pressure terminal/remote (14,2)/(32,2). Left portal: controller (2,26), pads (14,14)/(14,26). Right portal: controller (50,2), pads (50,38)/(50,50).
- Precycle opens/focuses solid then clears records: DOWN,DOWN,LEFT,A5; DOWN,A5; DOWN,A5.
- Fresh slot0 avoids retoggling solid and reaches pressure via runner-powered left portal: DOWN,UP,DOWN,UP,DOWN,UP,LEFT,LEFT,UP,UP; A5.
- Slot1 reaches/holds right portal controller after replay0 opens pressure gate: DOWNx2 RIGHTx2 UPx4 LEFT UPx2 RIGHTx3; A5.
- Slot2 reaches right upper pad at t14 and warps to lower: DOWNx2 RIGHTx2 UPx4 RIGHTx2 DOWNx4; then LEFTx3 into goal.
- Precycle and slot0 are now confirmed; runner-powered left portal warped correctly and slot0 holds pressure. Remaining exact plan: slot1 controller route above+A5, then slot2 route above. 32 actions predict level_up+win; all 424 transitions green.
