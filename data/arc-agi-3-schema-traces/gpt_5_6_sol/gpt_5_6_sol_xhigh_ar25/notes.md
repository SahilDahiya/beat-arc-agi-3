# ARC3 Notes

## Confirmed mechanics/model
- 3x3 tiles; color5 physical source, color10 mirror axes, color4 reflection closure, color11 targets.
- Source components are 8-connected (corner contact joins). Click selects a component or axis; arrows translate selected object. Perpendicular axes generate V/H/VH copies.
- Win/level clear when all targets are covered; extra copies allowed. For final level the exact-cover solution is unique.
- Actions1-5 tick right meter; clicks/undo do not. Model backtest-green through 213 checkable transitions.

## Current level 7 (final)
- Entry axes vertical x3 inactive, horizontal y5 selected.
- Exhaustive global search found unique minimum exact cover: axes vertical x12, horizontal y11 (axis cost15).
- Two source components totaling15; four-copy orbit exactly equals all60 targets:
  1. Component7 {(7,7),(8,7),(9,7..11)}: RIGHT9, UP4 -> {(16,3),(17,3),(18,3..7)} (cost13).
  2. Component8 {(13,13..15),(14,13),(14,15),(15..17,15)}: LEFT9, UP7 -> {(4,6..8),(5,6),(5,8),(6..8,8)} (cost16).
- Immediate: selected horizontal DOWN6; click vertical at (9,0), RIGHT9. Then move Component7 and Component8 as above.
- Total movement 44, safely below meter; candidate has zero non-target orbit extras and no orbit overlap.
