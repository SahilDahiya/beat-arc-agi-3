# ARC3 notes

## Confirmed mechanics (levels 0-3)
- Actions 3/4 move a black selector among editable 5x5 glyph slots.
- Actions 1/2 cycle selected glyph forward/reverse through a level-specific 7-state alphabet, preserving fixed D4 orientation.
- Red meter advances every two actions.
- Framed examples act as left-to-right sequence rewrite rules; glyph matching is up to D4. Rules may have variable-length sides and intermediate frame colors.

## Cleared
- L0 direct single→single.
- L1 direct single→variable.
- L2 variable→variable; cycle F→G→E→C→B→D→A.
- L3 transitive orange→purple→maroon; cycle B4→B5→X→B2→B3→B1→B0.

## Current level 4
- Layout reverses the editable region: black selector brackets the first TOP orange source frame (x8..14,y10..16), not the bottom purple frame.
- Top visible pairs: A0→P0; A0→P1P1; A1A1→P2; A2→P3.
- Bottom fixed-looking pair: [A2,A3,A4,A4,A0] → [P2,P4,P4,P0,P3].
- Selector traverses ALL ten upper rule glyphs in reading order (first action4 moved from first orange source to first purple output).
- Goal is to edit top rules so they rewrite the fixed bottom query to fixed bottom answer. Ordered target rule slots are exactly: [A2,P2, A3,P4,P4, A4,A4,P0, A0,P3], partitioned by frame lengths.
- Generic model now detects reversed layouts, arbitrary ordered frame slots, and reads current editable rules for goal checking; 110 scored transitions green.
- Purple-frame cycle is a capped linear list: P0→X→Y→P1/P2→Z→P0b→P4→P3; action1 at P3 is a no-op.
- Current selected slot1 is P3 after exploration; restore four reverse steps to target P1/P2, move left to orange slot0, then probe its separate color-specific cycle toward A2.
- CYCLE4A is seeded with A0; purple/orange frame colors select separate cycles.
