# Notes — ARC3 puzzle

## Confirmed mechanics
- Paired mirrored tokens; independent blocking. 1/2 vertical. Normal boards:3 outward/4 inward. The pressure-only bg6/7 L4 swaps them; final bg6/7+checker8 L5 uses normal mapping.
- Completion is an inward collision: exact overlap or, for even size, face adjacency then a command that attempts identity exchange. On bg6/7 use action3 when identity0 is left, action4 when identity0 is right.
- Checker8 collision resets all dynamics to entry.
- Compact smaller specials are clickable/movable by token stride. Clicking the selected marker is idempotent (does NOT toggle off); a different interior click cancels.
- Token-size colored keys pressure-open larger same-color doors. Door passability uses keys occupied at START of action; newly pressed opens after movement, released stays open for releasing move then closes.
- L4 cleared via final adjacent inward collision. Model backtest 228/228.

## L5 final
- Combines all mechanics. Size4 tokens start (18,22),(42,22); backgrounds6/7 (3 inward).
- Checker8 reset maze; compact 2x2 9 near (32,43); pressure families c/e (token-size keys and 12x4 doors).
- Marker parked at (23,27). L5 horizontal mapping was experimentally corrected to normal. Current tokens (14,26),(46,42). Corrected BFS continuation: action4 x7, then 2,3,2, action1 x4, final action4 reaches face-adjacent (18,34)/(22,34) and contact wins. Model backtest 255/255 and exact current replay matches.
