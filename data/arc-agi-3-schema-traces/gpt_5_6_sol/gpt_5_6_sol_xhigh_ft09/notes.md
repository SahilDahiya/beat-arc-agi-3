# Notes

## Confirmed mechanics
- Doubled 3x3 normal codes constrain surrounding 6x6 cells; click cycles ordered swatch palette.
- Normal alphabet: 0 -> center colour, 2 -> other/shared non-center; 3 absent.
- Patterned cells are masked multi-cell switches: clicking cycles their own palette pixels (preserving mask ink) and each neighbouring cell indicated by mask ink.
- Footer: plain <=16 buttons +2/press; plain 17-24 uses 1,0,1; masked-switch layouts use 0,1,1,0 repeating.
- L0 spacer5 examples are noneditable; editable layout uses background4.

## Cleared
- L0 8/9; L1 9/c; L2 8/c; L3 9/8/c; L4 e/f cross switches.

## Current level (5, final)
- Palette b/e. Four normal clues and 22 editable b/6 switches. Each has one 6 above center, so clicking flips itself and the switch immediately above.
- GF(2) system unique solution was 13 clicks. First (6,8) executed correctly; only footer cadence differed and is now fixed/green.
- Remaining clicks:
  (6,16),(14,24),(14,32),(22,16),(22,24),(22,40),
  (30,32),(38,16),(38,32),(46,32),(46,40),(54,40).
- Model matches all 84 checkable transitions and should win on final click.
