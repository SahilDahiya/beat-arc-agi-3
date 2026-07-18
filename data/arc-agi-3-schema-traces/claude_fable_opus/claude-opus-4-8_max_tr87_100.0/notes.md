# Notes — "rotated cipher word" game (levels 0-4 CLEARED; on level 5, the last)

## UNIFIED MECHANIC (one model, world_model_v5.py, explains every level)
- TOP (bg 2): DICTIONARY. Entries in bands; boxes pair left->right ([box]==333==[box]).
  Box border colour = FONT; a box holds 1..3 glyphs (width 7/14/21) => an entry maps a SEQUENCE of
  letters to a SEQUENCE. Font pairs may CHAIN (level 3 and 5: a -> 7 -> b).
- BOTTOM (bg 3): CLUE word (upper box) and ANSWER word (lower box).
- GOAL (ALL LEVELS): translate(clue word, dictionary) == answer word.
- Colour-0 bracket cursor selects ONE editable unit. The editable SET is whichever the cursor
  starts on (init_state detects it):
    levels 0-3: the ANSWER-WORD slots (one glyph each).
    levels 4-5: the DICTIONARY BOXES  -> the WORD is fixed and the DICT must be repaired.
- A dictionary BOX is edited as a unit: all its glyphs CYCLE TOGETHER, each keeping a fixed OFFSET
  from the box's base letter (level 4: offsets 0 => identical glyphs; level 5: offsets 5/2/0) and
  its own fixed display ROTATION.
- Actions: 1 = next letter in that box's FONT wheel, 2 = previous, 3 = cursor prev, 4 = cursor next.
- Every glyph is a ROTATED letter; identity = canonical form (min over 4 rotations). Display
  rotations are arbitrary and are kept as candidate sets ('kc'), narrowed from the live grid;
  a symmetric letter can leave them ambiguous -> costs at most one mispredict (history #51/#105/#109).
- row 63 = budget bar: floor(n_actions/2) cells of colour 4 from the right. RESET refunds it.

## FONT WHEELS (cyclic order) — measured by pressing 1 and recording the DISPLAYED glyph
WHEELS[7]=W7, WHEELS[11]=WB, WHEELS[10]=WA — all three fonts are now known, so no new measuring
is needed unless a new font colour appears (then: wheelscan.py).

## LEVEL 5 (final) — dictionary repair with chain a -> 7 -> b
clue (a) [3,4,2]; answer (b) [4,6,2,2,6,4] (both fixed). 12 editable boxes.
Solution (target base letters per box, reading order):
  [2, 3, 3, 6, 3, 1, 4, 2, 4, 4, 1, 4]
 = entries: a2 -> 7(3,1) ; a3 -> 7(1,3) ; a4 -> 7(4,4) ; and 7->b: 1->4, 3->6, 4->2.
24-action plan committed; model predicts level_up (and its independent goal check agrees).
