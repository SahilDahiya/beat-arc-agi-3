# L6 — WIN needs BOTH diamonds: c-ptr@(16,25) AND a-ptr@(7,22)
## OFF-GRID RULE (confirmed): a +90 rotation MAY push a bar off the grid edge (allowed); +180 rotation and LENGTH changes require ON-grid (strict). Code: _l6_valid(...,allow_off=False default); rotation passes allow_off=(turns==1). => While a bar is off-grid, length changes no-op. So 8 (rotated up=off-grid) must be rotated back on-grid (up->left, +90) BEFORE a-grow works.
## FINISH from here (8=up off-grid, c docked, La=8): 8-rot(60,59) [up->left on-grid], a-grow(60,51) x2 [La->14] -> aptr(7,22) -> WIN. (live model 117/117 clean, verified.)
## WIN CONDITION (confirmed): cptr==(16,25) AND aptr==(7,22). (Docking only c did NOT win at #570.)
## Top arm: 8-bar (root (7,13), ROTATE-only, no length click) + a-bar (root (7,34), grow/shrink, points left, aptr=(7,34-(La-2))).
## At ENTRY a is docked (La=14 -> aptr=(7,22)). 8-bar must be positioned to NOT block row16 (for c-bar) AND NOT cover (7,22) (for a). 8 pointing LEFT (cols0-13, rows6-8) satisfies both. I wrongly rot-8 to RIGHT (covers diamond) + shrank a.
## FINISH from c-docked state: 8-rot(60,59) [right->left +180], a-grow(60,51) x2 [La 8->14] -> aptr(7,22) -> WIN. (a-grow=(60,51),a-shrink=(54,51),8-rot=(60,59).)

# L6 c-arm (SOLVED earlier)

## State model (all in world_model_v5.py, backtest-clean)
- Arm b->e->9->c rooted at Pb=(13,49) down. Child pivot = parent_tip + 2*dir.
- 9 & c rigidly coupled: c is 90deg CW from 9 (9=up->c=right, 9=left->c=up, 9=down->c=left, 9=right->c=down). c NOT independently rotatable (no c-rot click; rot-9 rotates 9+c together).
- ROTATION RULE (CORRECTED, confirmed from 28 rot transitions): try +90; if invalid try +180; else NO-OP. NEVER +270. Code: `for turns in (1,2)`. (Old skip-blocked (1,2,3) was WRONG - it let 9 reach 'up' from 'left' via +270 which the game forbids; caused the step13 no-op mispredict.) To rotate 9 from left->up you must first SHRINK 9 to L2, then it can go left->down(+90)->up(+180).
- Validity STRICT: no bar-bar overlap, no walls(15), no off-grid, len 2..47. Grow/shrink = +/-3.
- Goal: c-pointer docks hollow diamond (16,25) [row,col]. win=level_up when cptr==(16,25).

## Walls (exact)
- cols39-41 vertical: rows 0-26 (top wall)
- rows27-29 horizontal band: cols 0-5, 9-29, 33-41  (GAPS: cols 6-8, 30-32, 42-63)
- cols15-17 vertical: rows 30-38 AND 42-44  (GAP: rows 39-41 only)
- rows45-47 full bottom wall

## KEY MAZE INSIGHT (why length-only fails)
Lower arena (rows30-44) split by cols15-17 wall; only crossing = rows39-41 gap.
Wrist (9-up short + c) is ~5 rows tall -> can't fit 3-row gap vertically.
=> Rotate 9 to LEFT (horizontal): whole wrist lies in rows39-41, THEN it fits & crosses.
A tall 9 can only sit in a rows27-29 col-gap (6-8, 30-32, 42-47) and can't translate between gaps.
So: cross cols15-17 with 9 HORIZONTAL/short at row40, then rotate up in the col6-8 gap.

## Counter (row63 trailing-4 count) — CRACKED (general loop, backtest 108/108 clean)
Post-reset: +1 per 3 raw clicks, but a STALL (gap 4 not 3) each time t4 reaches k with k%8==5 (k=5,13,21...).
Render (na=state na = na_seg+1): n6=na-1; cc=0; p=1; k=1; while p<=n6: cc=k; k+=1; p+= 4 if k%8==5 else 3.
Confirmed thru na_seg=38 (2 stalls at t4=5,13). Next stall t4=21 (~na_seg 63).
## (old notes below)
Per segment (na = clicks since reset/entry):
- post-RESET seg: t4 = (na+2)//3 for na<=12, then ONE stall -> (na+1)//3 for na>=13.
- level-ENTRY seg (seg0 only): t4=(na+1)//3. (init_state can't tell entry vs reset -> use post-reset; seg0 backtest mismatch is harmless/historical.)
- In render (na param = internal na): cc=(na+1)//3 if na<=13 else na//3.  [DONE in code, backtest 46/46 clean on seg4+seg5]
- Only 1 stall confirmed thru na=36. na 37-41 extrapolated (low risk).

## WINNING PATH (from post-reset state after 14 setup clicks: b=down26, e=left5, 9=up2, c=right2, cptr(37,43), na=14)
27 clicks, verified thru full predict() -> cptr(16,25), win+level_up on last:
  (39,52) 9-rot->left
  (32,51)x2 9-grow (extend flat wrist left)
  (10,58)x10 e-grow (translate wrist left across cols15-17 gap @row40)
  (39,52) 9-rot->up (@col13)
  (10,58)x2 e-grow (9 to col7, in cols6-8 gap)
  (32,51)x5 9-grow up (through cols6-8 gap to row16)
  (32,58)x6 c-grow right (dock cptr at col25)
=> cptr(16,25) WIN.

## IF it does NOT win at (16,25): check 8/a top arm.
Setup clicks earlier included shrink-a x2 + rot-8 — maybe a-arm pointer must ALSO dock diamond (7,22).
_L6_RINGS also has a diamond at (7,22). If win needs BOTH: model win cond must be cptr==(16,25) AND aptr==(7,22).
a-arm: pivot PA=(7,34) up; a-grow(60,51)/a-shrink(54,51); 8-rot(60,59). Re-derive if needed.
