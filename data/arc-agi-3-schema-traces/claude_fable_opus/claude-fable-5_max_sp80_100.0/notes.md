# Notes — living scratchpad

## Confirmed mechanics (encoded in world_model_v5.py, predict/state)
- Pieces (8=unselected, 9=selected) are PERSISTENT rectangles; track in state (adjacent same-color pieces merge visually). Click (6) on piece selects it. Arrows move selected 4px; blocked by non-bg AND by orthogonal adjacency to cup(11) cells.
- Budget row (all-14 at entry; opposite floor): drained(n)=round(64n/N), N per level {0:30, 1:45, 2:90}; n tracked in state + grid-calibrated. Every action drains (clicks too). d=64 → dead (guess).
- POUR (5): ALL dispensers stream at once (level 2 has 3!). Water: 4px column flows (away from 4-block); obstacle → 4-row layer on incoming side, spreads ≤1 block beyond run ends (blocked by obstacles in layer band, clipped at board edges — assumed pooling, no stray); each free layer block continues past obstacle row. Interior column + base → cup fills.
- POUR SUCCESS = ALL cups filled AND ZERO floor-touches (stray voids everything; #21 proved: 3/3 cups + 1 stray = fail). Fail → full restore (only drain persists) + stream-first-hit piece becomes selected.

## Level 3 (CELL=3px!, water falls, walls all around, budget row0 right-drain)
- Stream x23-25 from y8. Cups x8-16, x26-34, x38-46, x50-58 (interiors x11-13, x29-31, x41-43, x53-55). Floor row1 + rows59-63 + side walls x0-1/x62-63.
- Pieces: A 15px (17,17) B 15px (17,38) C 21px (28,8) with EMBEDDED EMITTER (4-colored, offset +9..+11, pours own stream on action 5!) D 12px (31,44) E 12px (40,38).
- Piece lattice: moves 3px; px≡2 mod 3; py: A/B ≡2, C/D/E ≡1.
- Physics detail: layer band = CELL rows on incoming side; spread walks band cells from impact col, capped 1 CELL beyond RUN ends (run from HIT cells only); overflow needs run-row cells bg. Wall clipping = pooling (no stray) CONFIRMED level 2.
- SOLUTION (sim 4 cups 0 strays): A,B stay; E→(46,17) [7 left,2 down]; D→(49,17) [6 down,9 left] (blocks x17-19 outer of cup1R-leg layer); C→(28,32) [8 right]: A splits stream → x14-16 (cup1R leg → x11-13 cup1) + x32-34 → C → x29-31 cup2 + x53-55 cup4 + emitter x41-43 cup3.
- ORDER: E first (out of D's path), then D, then C, pour. 36 actions.

## Level 2 layout (water rises; X,Y = x//4,y//4)
- Floor rows0-3; budget row63 (left-drain). Streams X=1,9,14 (rise from Y=13). Cups interiors X=2,7,13 (legs 1/3, 6/8, 12/14).
- Pieces: P1 4w @(2..5,5); P2 5w @(10..14,7); P3 6w @(2..7,8); P4 6w @(9..14,10) sel at entry.
- SOLUTION (sim-verified 3 cups 0 strays): P1→(3..6,4) x12-27 r16-19; P2→(8..12,4) x32-51 r16-19; P3→(0..5,6) x0-23 r24-27; P4→(10..15,6) x40-63 r24-27.
  Tree: stream1→P3→X=6→P1→{X=2 cup1, X=7 cup2}; stream9→P2(via gap)→{X=7, X=13 cup3}; stream14→P4→X=9→P2.
- Progress: P2 done to (8..12,7), needs up×3. Then P4 (click 46,41): right,up×4. P1 (click 14,21): right,up. P3 (click 20,33): left×2,up×2. Pour.

## Watch out
- Piece move into row adjacent to cups = blocked (Y=3 here).
- Edge-pooling assumption UNVERIFIED (P3/P4 layers clipped at x=0/x=63). If pour fails → check that first.
