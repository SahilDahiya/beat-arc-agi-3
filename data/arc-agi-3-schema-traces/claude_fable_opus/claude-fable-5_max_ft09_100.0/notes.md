# Notes — ft09 (6 levels)

## Action semantics (confirmed / guessed)
- Level 0: only ACTION6 (click) legal.
- CONFIRMED: click inside a non-center tile toggles its color 8<->9.
- CONFIRMED: row y=63 = energy bar; drains c(12)->b(11) right-to-left. Cumulative cells after n actions = ceil(n*rate); RATE PER-LEVEL: lvl0=2, lvl1=2, lvl2=1/2. Model = predict/state contract with per-level action counter n; _RATE table, default (1,2). Expect ≤1 mispredict per new level to learn rate.
- GUESS: bar empty = dead/game-over.

## GENERAL RULE (verified lvl0-4 backtest 43/43)
- Board = sparse lattice of 6x6 blocks spaced 8px: TILEs (uniform non-bg, clickable),
  GLYPHs (3x3 of 2x2px cells: inks {0,2,3} + center C), CHECKERs (2-color
  alternating cells, e.g. e/6 — decoration, not clickable).
- LEGEND: 4x4 blocks stacked from y=0 at some column (x=60 lvl1-3, x=54 lvl4!)
  = palette CYCLE top->bottom. Click advances tile to NEXT cycle color (wraps).
  lvl0: none -> fallback. lvl1 [9,c], lvl2 [8,c], lvl3 [9,8,c], lvl4 [e,f].
- Glyph constrains its 8 neighbors (+-8px): ink 0 -> block color == C; ink 2 ->
  block color != C (lvl3 proved "!=C" not a specific color); ink 3 -> not a
  plain tile (empty/glyph; structural). "Block color" of a CHECKER = its BASE.
- BUTTON block = base color B (corners+center) + accent-6 dots on a SUBSET of
  ortho cells (N/W/E/S). Click toggles its base AND the neighbor blocks in the
  dotted directions (no cascade — verified lvl5 chains). lvl4 checkers = all-4-dots;
  lvl5 = N-dot only (vertical Lights-Out chains; solve per column bottom-up XOR).
  Buttons count as blocks (base color) for glyph constraints.
- lvl5 (last): 22 N-dot buttons, 4 glyphs C=e, palette [b,e]; 13-click solution.
- Goal: ALL glyph constraints satisfied -> level_up (fires the instant last one fixed).
- Minimal solve = fix violated constraints only: ink0 tile!=C -> click to C;
  ink2 tile==C -> click to other color.

## Game structure (level 0)
- 64x64, bg=5. Row y=63 all color 12 (c) — possible energy/move bar, WATCH if it shrinks per action.
- Four 3x3 panels of 6x6 tiles (colors 8 or 9), tile origins spaced 8px.
- Center tile of each panel = GLYPH: 3x3 of 2x2px cells, colors {0,2}, center cell=8.
- RULE (verified on 3 example panels): glyph 0 -> tile 8, glyph 2 -> tile 9.
- Active puzzle = bottom-right panel, FRAMED with 4s (2s at corners). Its tiles: all 9.
- Frame spans x=32..61,y=32..61; tiles at x=36/44/52, y=36/44/52 (6x6 each).
- Target: [[8,9,9],[8,-,8],[8,9,9]]. Need toggles at (r,c)=(0,0),(1,0),(1,2),(2,0)
  -> clicks (38,38),(38,46),(54,46),(38,54).

## Current plan
1. Probe click (38,38): expect tile (36..41,36..41) flips 9->8. VERIFY toggle mechanic.
2. If confirmed: click remaining 3 tiles; expect level_up on last.

## Hypotheses to test
- Toggle vs cycle vs paint? Click on example panels / empty space = no-op?
- Energy bar (row 63) depletion per click?

## Confirmed facts
- (none yet)
