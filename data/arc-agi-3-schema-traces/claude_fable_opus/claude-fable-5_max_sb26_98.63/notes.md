# Notes — living scratchpad

## Action semantics (confirmed / guessed)
- Legal at L0: [5,6,7]. 6=click(x,y). Guess: 5=submit/confirm?, 7=undo/clear?
- CONFIRMED t0: click inside a bottom palette block => SELECTS it (0-ring drawn around its bbox, 1px). Middle slots unchanged.

## Current level (L7 of 8)
- Code = ALL panel rows CONCATENATED (line-wrap!): 12 = 8,b,c,9,e,f,8,b,c,9,e,f (periodic).
- REFUTED: per-row roots + cycle-skip (submit failed with A=(8,b,c,P9),B=(P8,9,e,f)).
- NEW RULE (backtest 123/123): single root = topmost box; reading = lazy STREAM expansion
  (cycles => infinite periodic stream); accept iff stream prefix(len code) == code (finite: exact).
- Failed submit costs a counter tick (row 52; ~55 left).
- FIX: rearrange B from (P8,9,e,f) to (9,e,f,P8) -> stream (8,b,c,9,e,f)* ✓. Committing.

## Previous levels (L0-L5 cleared)
- L4 taught: panel rows excluded from box scan; path-based cycle guard (same box via 2 portals OK).
- L5 taught: 3 portals to 3 boxes, each pre-holding own-color solid.
Layout (from ENTRY_GRID):
- TOP display (rows 0-7, bg 5): four HOLLOW squares, colors L->R: 9, e, b, f (the CODE)
  - 9 @x18-23, e @x25-30, b @x32-37, f @x39-44 (rows 1-6)
- MIDDLE box (rows 24-35, border 8): four 2x2 slots of color 2 at rows 29-30,
  x=22-23, 28-29, 34-35, 40-41 -> guess: input slots, red=empty
- ROW 52: full-width line of color 2 (divider? timer/lives?)
- BOTTOM palette (rows 56-59): 4x4 blocks: e @x18-21, f @x26-29, 9 @x34-37, b @x42-45
- bg color 4 everywhere else.

## Confirmed mechanics (in model, backtest green thru L0)
- Block-mover: click block=select (0-ring around 4x4 zone); click empty pos (2x2 red marker)
  = move selected block there; source->bg+marker; counter row (all-2s at entry): rightmost 2->3 per MOVE.
- Action 5 = SUBMIT: level_up iff all marker zones match target colors (L0 confirmed).
- Top panel row1 = code sequence (hollow square border colors L->R).

## Hypotheses to test
1. DFS portal reading (L1: A=c,f,[B],6; B=8,9,e,b) — submit will confirm.
2. Action 7 = ? (undo?) — untested.
3. Counter row: what if it empties? (not urgent)

## Confirmed facts
- 8 levels total. Colors as hex 0-15.
