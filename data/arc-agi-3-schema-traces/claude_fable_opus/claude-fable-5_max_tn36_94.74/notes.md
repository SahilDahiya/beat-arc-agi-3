# Notes — living scratchpad

## CONFIRMED mechanics (encoded in world_model_v5.py, backtest 4/4)
- Icon strip below board: icons = CAP (3-wide, y41; color 5/1; click icon box toggles cap, costs 1 time)
  + STEM (1-wide, y43-45; color fixed so far).
- Button (9-circle, x32-41 y50-59): RUN program left->right: cap 5=execute, 1=skip.
  Executed move = stem color: 5 => key DOWN one band (4px); 1 => key LEFT one tile (4px).
- Run FAIL (key final tile != lock target tile): board+key reset to entry, time-1.
- Time bar row1 (x1..x61, 61 units): rightmost 9 -> 3 per icon click / failed run. ~55 left.
- Tiles: origin x14,y9, pitch 4. Key start tile (col4,band1). Lock target (col4,band6).

## SOLVED mechanism: icons have TWO toggle zones
- Click y<=43 (cap zone) -> toggle CAP (execute=5 / skip=1). Click y=45 (stem zone) -> toggle STEM
  (direction: 5=DOWN, 1=LEFT). y44 boundary guessed=stem (unverified). EVERY click costs 1 time.
- Level-0 solve: caps all 5 + stems all 5 = 5 downs -> key (4,1)->(4,6)=lock -> level_up.

## Level 1 layout
- Right board x32-61 (border x32/x61, tiles anchor x33,y4? pitch4): LOCK at top (walls x44/x49 y7-11,
  ceiling y7, bump y8 x46-47), KEY at bottom (x45-48 y24-27, notch top y24 x46-47). Need UP x4 (col3: band5->band1).
- RIGHT strip (black bg, x32-61 y31-49): 3 cap rows y33/39/45, 4 icons each (caps x38-40,43-45,48-50,53-55;
  stems +2..+4 rows below at x39,44,49,54). All caps 1 (skip), all stems 1 (left).
- LEFT top panel x1-31 y3-31 (bg 3): yellow 4x4 shape w/ LEFT notch (x22-25,y16-19). Purpose unknown.
- LEFT strip (red bg 2, x1-31 y32-50): 3 rows x 4 icons (caps x7-9,12-14,17-19,22-24; row33 caps=5, rows39/45=1;
  stems all 1). Purpose unknown.
- Wires: red strip -> two small boxes (9-box x7-15 w/ 'bb'+2 dots glyph; 2-box x17-25 w/ 'bbb'+dots glyph, y53-62).
  Black strip -> 9-circle button x43-51 y53-62 (run?).
- Time bar refreshed to full 61 at level start.

## CORE MECHANIC (v3, backtest 41/41) — NO execute flag; cap is PART of the code!
- Program = COLUMNS of editable strip (bg 0), left->right. Column code = (cap1, s1, s2, s3):
  (5,1,1,1)=LEFT, (5,5,1,1)=DOWN, (5,1,1,5)=UP, (1,5,1,1)=RIGHT, anything else=NOP.
  (cap2/cap3 must be 1; single-row strips pad stems with 1s.)
- Direction boxes (square rings; bar-side of glyph = direction): pressing writes that direction's code
  into the red DEMO strip (all columns) + billboard ghost shows key path demo (start = key shifted
  perpendicular 0,-1,+1,.. so path fits bounds/walls). Ring colors: selected=9, others=2.
- Red strip (bg2) inert to clicks. Billboard (bg3) = preview. Walls color 6 (semantics: assumed blocking).

## Level 3 (current) — SIZE mechanic + PER-LEVEL CODES
- Key is BIG (8x8 = 2x2 tiles) at (3,1)-(4,2), notch bottom. Lock (col2,band5), bump bottom. Wall band4 except col2.
- CODES REMAP PER LEVEL! Demo boxes = codebook: press box -> red strip shows its code.
  L3: LEFT=(1,5,1,5), DOWN=(5,5,1,1), SHRINK(dot glyph)=(5,1,5,1), GROW(square glyph)=unpressed.
- SHRINK: size -1 tile-step, anchored TOP-LEFT. Demo ghosts: canonical 4x4 key; mv-demos start at key
  top-left tile, shift perpendicular if MID-path wall; sz-demos draw at billboard corner.
- Solve: cols = [SHRINK, LEFT, DOWN, DOWN, DOWN, DOWN] -> (3,1)shrunk ->(2,1)->(2,5)=lock.

## Hypotheses to test
- s[1]=5 -> RIGHT (untested guess — this level's plan tests it).
- Multi-5 stem columns / caps on rows 2-3 semantics unknown.
- Wall semantics: assume path blocked -> run fails (untested; plan avoids walls).
- Time bar empty -> game over? (avoid; each click costs 1)

## Confirmed facts
- RESET (action0) restarts level & refunds budgets (per framework docs).
- 7 levels total.
