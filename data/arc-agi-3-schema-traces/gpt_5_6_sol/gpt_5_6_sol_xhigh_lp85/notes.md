# Notes — ARC3 game lp85

## Confirmed prior levels
- Only action6 clicks; arrows permute tile tracks. Matching marker colors must fill corner-bracket targets.
- L0 one 20-ring; L1 outer ring+rows; L2 two overlapping16-cycles; L3 global H/V 20-cycles; L4 coupled top5 + snake17 cycles. All solved.
- Target detection on dynamic grids requires all nearby bracket corners same color. world_model_v5.py statefully models L0-L4; all-history backtest 67/67 green at L5 entry.

## Level5
- 75 colored 2x2 tile slots on x lattice [5,8,11,14,17,20,23,26,29,32,35,38,41,44,47,50,53], irregular y lattice [6,9,12,15,18,21,24,27,33,36,39,42,45,48,51,54].
- Three b targets: (26,27),(32,27),(29,33), bracketed by single b corner pixels. Three b marker tiles: (47,12),(11,18),(26,45).
- Seven e arrow components/control candidates: boxes approx (26,14),(56,14),(14,27),(44,27),(41,44),(52,54),(29,57). Likely overlapping row/column/cycle network extending L3/L4.
- Top y15 has two six-tile groups: left x5,8,11,17,20,23 with right/e arrow at (27,16); right x35,38,41,47,50,53 with arrow at (57,16). Other sparse arms connect markers to center targets.
- Confirmed top-left e arrow (27,16): on star centered (14,15), independently cycles each of 8 three-slot rays outer<-middle<-inner<-outer; b (11,18)->(8,21). x0 meter gained 1. Model detects analogous stars at (44,15),(29,45); backtest 68/68 green.
- Confirmed top-right e arrow (57,16) performs same ray operation around (44,15), moving b (47,12)->(50,9); meter +1. Backtest 69/69 green.
- Confirmed bottom-star right/e arrow (42,46) performs same operation around (29,45), moving b (26,45)->(23,45). L5 meter uses round(4n/5), so third press adds no pixel. Backtest 70/70 green.
- Confirmed each star has a second/below e control: (15,28) rotates each of its 3 concentric 8-position rings one angular slot (new[i]=old[i+1], angular order NW,N,NE,E,SE,S,SW,W). Backtest 71/71 green.
- Analogous below-star controls (45,28),(30,58) both match exactly. All six local star operations confirmed; backtest 73/73 green.
- Isolated control (54,55) swaps each central target with the adjacent outer slot of its star: (26,27)<->(23,24), (32,27)<->(35,24), (29,33)<->(29,36). Backtest 74/74 green.
- L5 solved with verified 13-step plan.

## Level6
- 2x2 tokens. Two b targets: (41,23), already occupied b, and (32,35), with b marker at (32,38).
- Top L-track: row y23 x20,23,...,41 plus left tail (20,26),(20,29); opposite up/down controls at (20,20) e and (20,33) 8.
- Bottom square slots clockwise TL,TR(target),BR(marker),BL; paired controls (29,43) 8 and (33,43) e.
- Confirmed e click (33,43) is a coupled generator: advances top horizontal 8-cycle right by 1 and bottom square clockwise by 1. Thus top b target moved idx7->idx0; bottom b BR->BL. Meter +1; backtest 88/88 green.
- Confirmed lower 8 click (29,43) is exact inverse of lower e: top H8 and square both step backward, restoring entry. Lower paired controls are one generator; meter +1 per click. Backtest 89/89 green.
- Upper pair is independent V3 generator: e (20,20) cycles [top,mid,bottom] upward (old top->bottom), 8 (20,33) modeled inverse/down. L6 meter round(4n/5). Backtest 90/90 green.
- L6 solved by BFS plan lower e, upper e, lower 8, upper 8, lower 8.

## Level7 (final)
- 2x2 lattice tokens; three b markers at (18,9),(18,18),(18,27). Bottom rack has five b-bracketed capacity slots (24,51),(27,51),(30,51),(33,51),(36,51), likely goal is all three b markers inside rack.
- Four inverse control pairs: 8/e at right around y24,29,34 and bottom around (31,58)/(36,58). Need learn four generators.
- First side pair is confirmed involutive gate swapping source (18,9) with SE neighbor (21,12); repeated e returned it. General hypothesis: side pairs y24/29/34 independently gate the 3 sources to SE neighbors. L7 meter modeled round(4n/5); backtest 97/97.
- Side generators are NW-SE diagonal cycles ending one slot SE of their source. y24 length2; y29 confirmed length6 from (6,6)..(21,21), e rotates SE. General track = consecutive NW slots through source plus one SE; 8 inverse. Backtest 98/98.
- y34 e exactly matched length7 diagonal track (3,12)..(21,30). All three side cycles confirmed; current b positions: (18,9),(21,21),(21,30). Backtest 99/99.
- Bottom e (36,58) rotates 3 disjoint L-shaped transport cycles forward: each starts at NW end of a source diagonal, turns at reverse-paired rack column x36/x30/x24, then descends to rack endpoint y51. Bottom 8 (31,58) modeled inverse. Backtest 100/100 green.
- From current state, exact simulated 19-step win: bottom8; S1e; S2e×3; S3e; bottomE×13. Final b positions (24,51),(30,51),(36,51), and model returns win=True.
