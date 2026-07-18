# Notes — ARC3 game

## Confirmed mechanics
- Paired brackets change all matching segment lengths atomically ±3 (min2); hitbox is the whole 3x3 tile, including blank center.
- Five-cell plus rotates the selected segment and its entire downstream suffix 90° CCW.
- Segment bodies MAY EXTEND OFF-SCREEN (8 confirmed), but every 3-cell proximal cap/joint must remain fully on-screen: e+ was blocked when downstream caps became partly x>63. Off-screen body cells are clipped/non-colliding. Visible-grid reconnection was disproved.
- Dynamic chains block one another (confirmed a extension into horizontal 8 was blocked).
- Parent changes translate suffixes; target centers have four cardinal d arms and all must be filled simultaneously.
- Color-2 panels overlay the world; headless terminals may carry rigid payloads.
- Turn bars L0=50,L1=150,L2=200,L3=100,L4=150,L5=150; L6 guessed200. Levels0-5 cleared.

## Level 6
- Targets (22,7) filled by a and (25,16) hollow. 8 is now rotated up/clipped; a restored.
- Main chain initial b(up,L2)->e(right,L5)->9(down,L5)->c(left,L2), head(55,16).
- Current after RESET + five b CCW rotations: initial lengths; dirs b-left,e-up,9-right,c-down; 8 down, a target filled.
- Every tested colored arm, neutral corner, and top arm rotates the selected segment + full suffix CCW. The whole 3x3 plus tile is one generic CCW hitbox; arm-specific direction/scope is ruled out.
- CONFIRMED compact-rotation skip: if the entire selected suffix is at min length2 and the next CCW quarter-turn collides, the control skips to the first later collision-free orientation (observed 9-up/c-right -> 9-down/c-left, skipping left/up). Longer suffixes simply reject a blocked turn. Model green.
- Current after reset experiment: a/8 entry, b up L2, e right L2, 9 down L2, c left L2. Exact verified route: park 8 up (a-2,8rot2,a+2), restore e+1, b rot2,b+8,e+8,9rot,e+4,9rot2 (second uses compact skip),9+7,c+6. This reaches both targets in 45 clicks.
- Final-geometry enumeration under the green model finds one goal: b26,e41,9=23,c20, dirs b-down,e-left,9-up,c-right. Exhaustive state search still says unreachable, so probe neutral corner hitboxes / revisit collision rule.
- Main clicks: b fwd=(10,51), e fwd=(10,58), 9 fwd=(32,51), c fwd=(32,58); e rot=(17,58), 9 rot=(39,51).

## Level 7
- Four same-colour b spokes form one stationary shared hub. Rotating b permutes/rotates only the four downstream arms around the common center; the b hub stays fixed. Model reproduces observed first turn.
- Bottom progress bar is foreground UI like control panels; long off-screen tracks may continue beneath it.
- Current hub orientation is rot1. Verified remaining route (39 clicks): hub, 8+3, a-6, 8-3, hub, 9+2, 7-6, 9-2, hub2, e+13. This parks both headless blockers compactly and moves the sole e head to target (19,43).
