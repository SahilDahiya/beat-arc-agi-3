# Notes — ARC3 game (8 levels). Model: world_model_v5.py (branches on CURRENT_LEVEL).

## COUNTER (col0 bar) — model is STATEFUL predict() now
fill = round(64*k/BUDGET), k=click count since level entry. BUDGETS: L0=13, L1=60, L2=80.
When BUDGET>64 the fill REPEATS values (non-invertible from grid) -> must track k in state.
BUT the globally-first transition is SKIPPED in state-threading -> desyncs k for level 0.
FIX (predict): derive click-count-before from before-grid col0 fill c (cands = k with round(64k/BUDGET)==c); disambiguate with state k; new fill=round(64*(cur+1)/BUDGET). Robust. backtest 22/22 GREEN.
init_state -> {'k':0}. Each level has own BUDGET (read from data: fit round(64k/BUDGET)).

## LEVEL 7 (LAST) — big complex lattice (IN PROGRESS)
Lattice y=6+3r, x=3+3c (r0..15, c0..13). Diagonal line r-c=-1: (0,1)..(8,9) values 9,1,9,1,b,1,f,a,9. Dense right cols c7,c9,c11,c13 (r7-15).
BUTTONS: right pairs 8/e at y23-26/28-31/33-36, x48-50(8)/x52-54(e) [~(49,24),(53,24),(49,29),(53,29),(49,34),(53,34)]; bottom 8@(31,57) e@(36,57).
BRACKETS b: 5 cells (15,7),(15,8),(15,9),(15,10),(15,11) [bottom row]. b-tiles at (1,5),(4,5),(7,5) (only 3?). GOAL unclear yet.
PROBE top-right e(53,24): SWAP (1,5)<->(2,6) [involution, clicking 2x returns]. Not a rotation. On diagonal r-c=-4.
MECHANIC: e-button = swap EVEN tile-pairs (idx0-1,2-3,4-5..) along ITS diagonal; 8-button = odd pairs. (odd-even transposition). A single b-tile can slide to ANY position on its diagonal via e/8 alternation.
 top-right e(53,24) -> diagonal r-c=-4 (b-tile (1,5)). mid-right e(53,29) -> diagonal r-c=-1 (b-tile (4,5)). bottom-right e(53,34) -> prob r-c=2 (b-tile (7,5)).
 3 b-tiles at (1,5),(4,5),(7,5) [c5, on diags r-c=-4,-1,2]. GOAL cells (15,7),(15,9),(15,11) [diags r-c=8,6,4] filled; (15,8),(15,10) bg.
 => b-tiles must change diagonals to reach goal. HOW? bottom button pair (31,57)/(36,57) near goal row r15 - probe it. Maybe diagonals connect at edges / bottom row transfers.
BOTTOM-e (36,57): moves tiles DOWN-RIGHT (r+1,c+1) along diagonals [b-tiles: (1,5)->(2,6),(5,6)->(6,7),(7,5)->(8,6)]. BUT has a COLUMN-c7 cycle [(10,7),(11,7),(12,7),(13,7)] = crosses diagonals! Hypothesis: conveyor flows down diagonals, TURNS down column c7 (and c9,c11?) to goal row r15. Goal cells (15,7),(15,9),(15,11) at bottom of cols c7,c9,c11.
 b-tiles now at (3,7),(7,8),(9,7) [2 at col c7!]. r-c invariant under diag moves -> need col-turn to reach goal.
 Full bottom-perm 214/224 AMBIGUOUS (can't model exactly). Tracking b-tiles empirically instead.
CONFIRMED conveyor: b-tile (9,7)->(10,7) = DOWN col c7 (crosses diag)! But (3,7)->(4,8) went down-right. So col-c7 turn only at rows ~9-13. bottom-e = big CONVEYOR: diag down-right, turns down cols c7/c9/c11 to goal row r15.
b-tile orbit (bottom-e clicks): 105(2,6),(6,7),(8,6) -> 106(3,7),(7,8),(9,7) -> 107(4,8),(8,9),(10,7).
STRATEGY: keep clicking bottom-e, track 3 b-tiles; each flows to a goal cell (15,7/9/11) via its stream; use right buttons(topR r-c=-4, midR r-c=-1, botR r-c=2) to adjust individual b phase. Map conveyor empirically (can't get full perm - ambiguous). Cleared 7/8; last level.
ROUTING MAPPED: each b-tile -> different goal column via a TURN POINT:
 b3 (r-c=2 diag) turned down c7 at (9,7)->(10,7) -> goal (15,7).
 b2 (r-c=-1) turned down c9 at (8,9)->(9,9) -> goal (15,9).
 b1 (r-c=-4) will turn down c11 at (7,11) -> goal (15,11). [pattern: col c7 turn@row9, c9@row8, c11@row7]
 After turn, flows DOWN column to r15. Then wraps (period unknown).
 Orbit: 108 b=(5,9),(9,9),(11,7). b3 leads (nearest goal), b1 lags.
STRATEGY: bottom-e advances all b's one conveyor step. To align all 3 at goals simultaneously, use right e/8 buttons to shift a b-tile's PHASE on its diagonal (advance/retard entry into its column). Track empirically. is_goal: b at (15,7),(15,9),(15,11) = grid[51][24]&[51][30]&[51][36]==11.
CONVEYOR DISTANCES (from clean entry b=(1,5)r-c=-4,(4,5)r-c=-1,(7,5)r-c=2):
 b3 (7,5): downright 2 to turn (9,7), then down c7 6 -> (15,7). total 8.
 b2 (4,5): downright 4 to turn (8,9), then down c9 7 -> (15,9). total 11.
 b1 (1,5): downright 6 to turn (7,11), then down c11 8 -> (15,11). total 14.
 => staggered. Can only phase-adjust a b while it's on its DIAGONAL (r-c=-4/-1/2) via right e/8 (even/odd swaps). Once in a column, uncontrollable.
ALIGN-AT-11 PLAN: RESET; move b1 (1,5)->(4,8) [+3 on r-c=-4: topR e,8,e]; move b3 (7,5)->(4,2) [-3 on r-c=2: botR e,8,e]; b2 stays. Then bottom-e x11 -> all at goals (15,7),(15,9),(15,11).
 idx on diagonal (first tile=idx0): e swaps even pairs(0-1,2-3,4-5), 8 swaps odd(1-2,3-4,5-6). Move b step: alternate e/8 by parity.
 Right buttons: topR e(53,24)/8(49,24)=r-c=-4; midR e(53,29)/8(49,29)=r-c=-1; botR e(53,34)/8(49,34)=r-c=2. bottom e(36,57)/8(31,57).
 NEED to confirm: topR-8, botR-e, botR-8 (unprobed). And verify conveyor distances.
is_goal: b at (15,7),(15,9),(15,11) = grid[51][24]==11 & grid[51][30]==11 & grid[51][36]==11.
NEXT: RESET(action0), then position b1,b3 (track), then bottom-e x11. If distances off, re-measure & retry (budget refunds on reset).

## LEVEL 6 — two small loops (SOLVED! 5-move b-BFS, coupled loops)
Lattice y=23+3r, x=20+3c. Entry:
 r-1 c0=e(btn)
 r0  f a 1 f 2 1 9 b   (horiz strip c0-c7)
 r1  c0=2
 r2  c0=f
 r3  c0=8(btn)
 r4  c3=1 c4=f
 r5  c3=9 c4=b
 r6  c3=8(btn) c4=e(btn)
BUTTONS: TOP e@(19-21,19-22)~(20,20), 8@(32-34,19-22)~(20,33) [loop A: horiz r0 + left col c0]. LOW 8@(41-44,28-30)~(29,42), e@(41-44,32-34)~(33,42) [loop B: r4-5 c3-c4].
BRACKETS b: around r0c7 (rows22-25 cols40-43) [b tile ALREADY there!]; around r4c4 (rows34-37 cols31-34).
b TILES: r0c7 (in bracket already?), r5c3. GOAL likely: b tiles in both brackets -> only need r5c3 -> r4c4 (loop B)?
PROBE top-e(20,20): swapped only (0,0)<->(1,0) [col c0 3-cell rot, r2 coincided]. Doesn't move horiz strip or top-b(r0c7). Top-b already in its bracket! col0=1 after 1 click.
b at r5c4, bracket at r4c4 (need b up 1 in col c4). GOAL: b's in brackets r0c7(done) & r4c4. is_goal grid[23][41]==11 & grid[35][32]==11.
CONFIRMED perms:
 top-e(20,20): rotate col c0 [(0,0),(1,0),(2,0)] UP: new(0,0)=old(1,0),new(1,0)=old(2,0),new(2,0)=old(0,0).
 loopB-e(33,42): rotate STRIP Q=r0[(0,0)..(0,7)] RIGHT (new(0,c)=old(0,c-1),wrap) AND 2x2 R rotate: new(4,3)=old(5,3),new(4,4)=old(4,3),new(5,4)=old(4,4),new(5,3)=old(5,4). BOTH together (coupled!).
(0,0) shared by col-c0 loop & strip Q -> interlocking.
GOAL: b at r0c7(bracket) & r4c4(bracket). is_goal grid[23][41]==11 & grid[35][32]==11.
ALL 4 btns encoded (_level6_step source-maps). top-e/loopB-e/loopB-8 CONFIRMED (backtest 3/3); top-8 GUESSED (col c0 down). loopB-8 = inverse of loopB-e.
b-position BFS -> 5-move PLAN: lbE(33,42),topE(20,20),lb8(29,42),top8(20,33),lb8(29,42). goal b@(0,7)&(4,4). Committing.
budget 80 assumed. If top8 mispredicts, it's not col-c0-down; re-derive + re-BFS.

## LEVEL 5 — big 4-fold mandala (SOLVED! 12-move b-position BFS)
Lattice: 2x2 tiles at y=6+3r, x=5+3c (r0..18, c0..16). Entry ('.'=bg,'#'=button):
    c:0123456789abcdef0
 r0 1..f..f...a..f..1
 r1 .a.2.2.....2.f.9.
 r2 ..191.......a2b..
 r3 fa9.9afe..a22.922
 r4 ..b19.......af1..
 r5 .a.a.a.....f.f.a.
 r6 f..9..f...f..2..9
 r7 ...e...2.a...e...
 r8 ...#.........#...
 r9 ........f........
 r10 .....1..a..1.....
 r11 ......2.9.a......
 r12 .......2a1.......
 r13 .....19b.21ae....
 r14 .......aa2.......
 r15 ......a.2.1......
 r16 .....9..f..1....e
 r17 ........e........
 r18 ........#........
BUTTONS (all 'e'): (27,15)r3c7-top-ctr ; (57,15)?; (15,28)r7c3-left ; (45,28)r7c13-right ; (42,45)r13c12 ; (53,55)r16c16 ; (30,58)r17c8-bot-ctr. [7 found]
BRACKETS b: cluster rows26-35 cols25-34 (center) = ~r7-10,c7-10. Looks like central 2x2+ target.
Likely 4 radial/diagonal loops meeting at center. b marker tiles -> center brackets (pattern).
CONFIRMED button1: top-center e (27,15) box(14,17,26,28) = rotates TOP-LEFT pinwheel @center(3,3): 8 radial arms (len3, dirs N,S,E,W,NE,NW,SE,SW) cycle OUTWARD (d1->d2->d3->wrap). Encoded _l5_arms(3,3). backtest OK. budget tentative 80.
Structure: 4 corner pinwheels @ (3,3),(3,13),(15,3),(15,13) + central region (r7-11,c7-9) w/ b-brackets.
7 buttons: (27,15)TL-done, (57,15)r3c17, (15,28)r7c3, (45,28)r7c13, (42,45)r13c12, (53,55)r16c16, (30,58)r17c8.
Corner pinwheels cycle radially WITHIN a corner -> don't reach global center. CENTRAL buttons must route to center.
CONFIRMED btn2: (45,28) box(27,30,44,46) = TR pinwheel ANGULAR = _l5_rings(3,13) [3 rings d1,2,3 each 8-cell CCW [N,NW,W,SW,S,SE,E,NE], new[i]=old[i-1]]. backtest 4/4 OK.
So corners have RADIAL (_l5_arms) &/or ANGULAR (_l5_rings) buttons.
b TILES (3): (2,13)[TR], (6,0)[TL], (13,7)[center]. b-BRACKETS outline central cells ~(7,7),(7,9),(8,8),(9,8) (rows26-35). is_goal TBD.
PINWHEELS (each 24 cells, buttons RADIAL=_l5_arms & ANGULAR=_l5_rings; radial btn offset(0,+4), angular offset(+4,0) from center):
 TL@(3,3): radial(27,15) box(14,17,26,28); angular(15,28) box(27,30,14,16). CONFIRMED.
 TR@(3,13): angular(45,28) box(27,30,44,46) CONFIRMED. radial = (57,15)? test _l5_arms(3,13).
 @(13,8): radial(42,45) box(44,47,41,43); angular(30,58) box(57,60,29,31). CONFIRMED.
GOAL: 3 b-tiles -> cells (7,7),(7,9),(9,8) = NW/NE/S d1 of CENTRAL pinwheel@(8,8). is_goal = grid[27][26]==11 & grid[27][32]==11 & grid[33][29]==11.
 Need central@(8,8) button (rotates those cells) -> among (57,15),(53,55). OR reachable via pinwheel OVERLAPS (e.g. (5,5) shared by @(3,3)SE-d2 & @(8,8)NW-d3).
SOLVE PLAN: once all 7 btns mapped, BFS over just the 3 b-tile POSITIONS (moves=each button's permutation applied to b-cells) -> tractable! goal=b at {(7,7),(7,9),(9,8)}.
ALL 7 BUTTONS MAPPED: TL@(3,3) rad(27,15)/ang(15,28); TR@(3,13) rad(57,15)/ang(45,28); @(13,8) rad(42,45)/ang(30,58); central@(8,8) SWAP-d1d2(53,55). backtest 8/8 GREEN.
SOLVE: b-position BFS (track only 3 b-cells, apply button perms) FOUND 12-move plan. is_goal grid[27][26]&[27][32]&[33][29]==11.
PLAN: TLang(15,28),TRrad(57,15),TRang(45,28)x3,BRrad(42,45),BRang(30,58)x5,Cswap(53,55). Committing.
Method WIN: don't-care all non-b tiles -> BFS over 3 b-positions is tiny. budget 80 (refit if counter mispredicts).
NEXT: probe (15,28) r7c3 (maybe TL angular). Keep mapping; look for CENTRAL loop that connects corners to center brackets (needed to route b-tiles). budget 80.

## CONFIRMED cross-level facts
- Only ACTION6 (click x,y) is legal. 8-shape = LEFT/CCW button, e(14)-shape = RIGHT/CW button.
- Move-budget bar: col0 left border fills color5 top-down = round(64*clicks/BUDGET). Direction-agnostic. LEVEL0 BUDGET=13. (level1 budget unknown; read from 1st click's fill.)
- TOP BAR row1 = 8 segments = LEVEL PROGRESS. Solving a level turns its segment from 5 -> e. (After L0: segment0 = eeee.)
- GOAL PATTERN (L0): rotate the UNIQUE marker tile into a same-colored bracket slot. Bracket color == target tile color.

## LEVEL 0 — SOLVED (13x? conveyor)
Single 20-cell CW loop (ROW A top / right col / ROW B bottom / left col). RIGHT=CW new[i]=old[i-1], LEFT=CCW new[i]=old[i+1]. Goal: unique b tile -> bracket idx0 (top-left px (19,12)). Coded in world_model_v5 _level0_step / _level0_is_goal. backtest GREEN.

## LEVEL 1 (interlocking conveyors) — IN PROGRESS
Lattice: 2x2 cells at y=17+3*r (r0..9), x=17+3*c (c0..9). Sample px (y,x)=(17+3r,17+3c).
Entry logical 10x10 ('.'=bg4; 8/e in r0 are BUTTONS not tiles):
 r0 .8a9fbfe..   H-strip r0 content c2..c6 = a,9,f,b,f ; btns 8@rows16-19 cols19-21, e@cols38-40
 r1 ..f...9...
 r2 ..2...a...
 r3 1991af2a22   H-strip r3 c0..c9 ; btns 8@rows25-28 cols13-15, e@cols47-49
 r4 ..1...1...
 r5 ..1...2...
 r6 1a919af92a   H-strip r6 c0..c9 ; btns 8@rows34-37 cols13-15, e@cols47-49
 r7 ..b...1...
 r8 ..2...9...
 r9 ..aaff2...
V-strips: c2 (r0..r9), c6 (r0..r9) — full columns. Interlock: H r0/r3/r6 cross V c2/c6.
BRACKETS (color b): around cells (r3,c6) & (r6,c6). b TILES: (r0,c5) & (r7,c2).
HYP: move b tiles into the 2 brackets (like L0). UNCONFIRMED.
UNKNOWNS: button dir/scope; intersection behaviour; how V-strips c2/c6 rotate (no vert buttons seen!); goal; budget.

## LEVEL 1 MECHANIC (partly confirmed)
3 interlocking LOOPS (rotate = cyclic color shift of loop cells):
- RING (26 cells): border of c2..c6 x r0..r9 rect. Order CW from (0,2). CONFIRMED: r0 top-right e-btn(rows16-19 cols38-40)=+1 (new[i]=old[i-1]). top-left 8-btn(cols19-21)=-1 (assumed).
- CROSS3 (10 cells) = (3,c) c0..c9. btns e@rows25-28 cols47-49, 8@cols13-15. dir GUESSED +1/-1. TESTING.
- CROSS6 (10 cells) = (6,c) c0..c9. btns e@rows34-37 cols47-49, 8@cols13-15.
Shared cells: RING∩CROSS3={(3,2),(3,6)}, RING∩CROSS6={(6,2),(6,6)}.
Counter: BUDGET=60 CONFIRMED (col0 fill=round(64*clicks/60)). (each level has own budget: L0=13, L1=60.)
GOAL HYP: is_goal = cells (r3,c6)&(r6,c6) both == b(11). brackets there, 2 b-tiles exist.
Model _level1_step coded, backtest 10/10 GREEN. CONFIRMED: RING-e=+1, CROSS3-e=+1. Budget=64 (+1/click, confirmed 2px@2clicks).
BFS INFEASIBLE here (interlocking-loop state space explodes: 300k nodes, no goal). => SOLVE CONSTRUCTIVELY by routing tiles:
Ring idx (CW from (0,2)): (0,c2..6)=0-4,(r1..9,c6)=5-13,(r9,c5..2)=14-17,(r8..1,c2)=18-25. Junctions: J1(3,2)=ring23=c3idx2, J2(3,6)=ring7=c3idx6[bracketA], J3(6,2)=ring20=c6idx2, J4(6,6)=ring10=c6idx6[bracketB].
Rotation: e/+1 => new[i]=old[i-1] (tile idx j -> j+1). 8/-1 opposite.
Routing trick: a ring-only tile (not on a crossbar) must move via ring; park the OTHER tile on a crossbar-interior (off-ring) cell first so ring rotation doesn't disturb it; place ring-tile at its bracket; then bring parked tile to its bracket via that crossbar (crossbar rotation doesn't touch the other bracket).
SOLUTION (from state@11 transitions, b@(0,6)&(6,2)): C6-1 x1, RING+1 x3, C6+1 x5 = 9 moves -> both brackets=b (simulated goal=True). Committing.
Clicks: RING+ =(39,17); RING- =(20,17); C3+ =(48,26); C3- =(14,26); C6+ =(48,35); C6- =(14,35).
LEVEL 1 SOLVED (budget 60). top-bar segs 0,1 now e.

## LEVEL 2 — two-loop puzzle (IN PROGRESS)
Lattice 7x11: cell (r,c) 2x2 @ px (19+3r, 15+3c). r0..6, c0..10.
Entry lattice ('.'=bg4):
 c:  0 1 2 3 4 5 6 7 8 9 10
 r0  . . 9 f 2 . a f 9 . .
 r1  . 9 . . . 9 . . . b .
 r2  1 . . . f . 1 . . . 2
 r3  9 . . . 1 . f . . . 9
 r4  a . . . 2 . 9 . . . f
 r5  . c . . . 2 . . . 1 .
 r6  . . 1 9 a . 1 2 a . .
TWO octagon-ish rings (left & right), mirror symmetric.
BUTTON pairs (rows40-43): LEFT 8@cols22-24 e@cols25-27 ; RIGHT 8@cols34-36 e@cols37-39.
  centers: Left8=(23,41) Lefte=(26,41) ; Right8=(35,41) Righte=(38,41).
BRACKETS: b(11) around cell (r3,c0)=px(28,15); c(12) around (r3,c10)=px(28,45).
UNIQUE TILES: b @ (r1,c9); c @ (r5,c1). GOAL HYP: b->b-bracket(r3,c0), c->c-bracket(r3,c10).
Budget: tentative 60 (col0=1 @1click). refit if mispredict.
LEFT OCTAGON (15 cells) CONFIRMED order & rotation. order (start (2,0), CW-ish):
 [(2,0),(3,0),(4,0),(5,1),(6,2),(6,3),(6,4),(5,5),(4,6),(3,6),(2,6),(1,5),(0,4),(0,3),(1,1)]
 LEFT e-btn(25-27,40-43): new[i]=old[(i+1)%15] (s=+1). LEFT 8-btn(22-24): s=-1 (guess).
RIGHT OCTAGON = mirror across c5: [(r,10-c) for cell in LEFT]. shares JUNCTIONS (1,5)&(5,5) with LEFT (=interlocking rings!).
 RIGHT e-btn(37-39,40-43) s=+1 guess ; RIGHT 8-btn(34-36) s=-1. TESTING.
Model _level2_step coded, backtest 20/20 GREEN (LEFT validated).
b tile @(1,9)[RIGHT ring], b-bracket @(3,0)[LEFT ring]. c tile @(5,1)[LEFT ring], c-bracket @(3,10)[RIGHT ring].
=> tiles must route across junctions (1,5)/(5,5). Solve CONSTRUCTIVELY.
BOTH octagons CONFIRMED (16 cells). LEFT-e s=+1, LEFT-8 s=-1; RIGHT-e s=-1, RIGHT-8 s=+1. backtest 21/21 GREEN.
Tile-move rule: Le: p->p-1; L8: p->p+1; Re: p->p+1; R8: p->p-1 (idx in loop order).
SOLVE method: relaxed subgoal BFS (real python, ~/agent-lp85/system/run_python) = "c at (3,10) & b anywhere on LEFT ring" (shallow), then finish with pure LEFT rotations to seat b at (3,0) [RIGHT rotations don't touch LEFT-only bracket, & vice versa]. Full-goal BFS too deep (3M nodes fail).
SOLUTION (from state@22 transitions): 21 moves L8x5,R8x5,Le,R8,Lex9. verified final goal=True. Committing.
Buttons: Le=(26,41) L8=(23,41) Re=(38,41) R8=(35,41).
LEVEL 2 SOLVED (budget 80). LEVEL 3 SOLVED (budget ~150, two 20-cell loops V=cols c2+c12, H=rows r2+r12).

## LEVEL 4 — (IN PROGRESS) irregular conveyor(s)
Lattice: tiles 4x4 at y=6+6r, x=17+6c (r0..8, c0..4). Entry lattice ('.'=bg, e@r5c3 is a BUTTON):
 r0 a 9 2 f 1
 r1 f . . . .
 r2 b 2 9 . .
 r3 . . 1 . .
 r4 1 1 9 . .
 r5 a . . . .
 r6 f 1 a . .
 r7 . . 9 . .
 r8 1 1 b . .
BUTTONS (8=CCW,e=CW): T8 rows4-11 cols7-12 (9,7); Te rows4-11 cols49-54 (51,7); B8 rows34-41 cols9-14 (11,37); Be rows34-41 cols35-40 (37,37).
BRACKETS (bb): around top-row c0 (cols15-16,21-22 @rows4-5,10-11) and c4 (cols39-40,45-46). => 2 bracket slots at r0c0 & r0c4.
b TILES: r2c0, r8c2. GOAL HYP: 2 b tiles -> 2 top brackets (r0c0,r0c4)? like level 2.
Budget: unknown (read col0 after clicks). 
PROBE Te(51,7): rotated ONLY top row r0 (5 cells c0-c4) RIGHT by 1 (new[i]=old[i-1], wrap c4->c0). So TOP loop = 5-cell row. col0=1 after 1 click (big budget like L3).
=> top row is small 5-loop; b tiles are in LOWER structure. Need connectivity top<->lower OR reconsider goal.
Lower structure looks like a serpentine: r1c0,r2(c0-2),r3c2,r4(c0-2),r5c0,r6(c0-2),r7c2,r8(c0-2). Buttons B8(11,37),Be(37,37).
SOLVED MECHANIC: TWO loops sharing the 5 top-row cells.
 TOP loop = [(0,0),(0,1),(0,2),(0,3),(0,4)]. Te(51,7) s=-1 (confirmed). T8(9,7) s=+1 guess.
 BIG loop (21) = [(0,4),(0,3),(0,2),(0,1),(0,0),(1,0),(2,0),(2,1),(2,2),(3,2),(4,2),(4,1),(4,0),(5,0),(6,0),(6,1),(6,2),(7,2),(8,2),(8,1),(8,0)]. Be(37,37) s=+1 (confirmed). B8(11,37) s=-1 guess.
 cell (r,c) -> 4x4 px (6+6r,17+6c). rotate newcols[i]=cols[(i+s)%n].
 GOAL: 2 b tiles -> r0c0 & r0c4 brackets. is_goal grid[6][17]==11 & grid[6][41]==11.
 Budget tentative 64 (col0 1,2 @clicks 1,2 -> B in [51,85]). refit on mispredict.
 backtest 58/58 GREEN. SOLUTION (15 moves confirmed btns): Bex5,Te,Bex4,Te,Bex4 = clicks (37,37)x5,(51,7),(37,37)x4,(51,7),(37,37)x4. verified goal. Committing.

## LEVEL 3 — four "plus" gadgets, 2x2 macro (IN PROGRESS)
Lattice y=9+3r, x=9+3c. Tiles only in corners: r,c in {0..4} and {10..14} (gap 5-9=center w/ buttons). Each quadrant = a PLUS: vertical arm (5 cells) + horizontal arm (5 cells) sharing center.
16 BUTTONS (8=CCW,e=CW). per plus 4 btns (both ends of each arm). lattice-pos:
 TL: Vtop e(5-7,14-17) Vbot 8(24-26,14-17) Hleft 8(14-17,5-7) Hright e(14-17,24-26)
 TR: Vtop e(5-7,44-47) Vbot 8(24-26,44-47) Hleft 8(14-17,35-37) Hright e(14-17,54-56)
 BL: Vtop e(35-37,14-17) Vbot 8(54-56,14-17) Hleft 8(44-47,5-7) Hright e(44-47,24-26)
 BR: Vtop e(35-37,44-47) Vbot 8(54-56,44-47) Hleft 8(44-47,35-37) Hright e(44-47,54-56)
TILES: ONE b @ (r2,c10)[TR horiz], ONE c @ (r13,c2)[BL vert].
BRACKETS: b @ cell(r12,c12)[BR center], c @ cell(r12,c14)[BR horiz right end].
PUZZLE: b(TR)->BR, c(BL)->BR. tiles in DIFFERENT quadrants from brackets => opposite arms must connect into longer loops OR unknown connectivity. UNRESOLVED->PROBE.
PROBE1 (8@45,25 "TR-vert-bottom"): rotated BOTH vertical columns c2 AND c12 together by +1!
 Each column = ONE 10-cell cyclic loop, order O=[r0,r1,r2,r3,r4,r10,r11,r12,r13,r14], new[i]=old[i-1] (tiles move down, wrap r14->r0). So TL-vert+BL-vert = V-left loop(c2); TR-vert+BR-vert = V-right loop(c12).
 => a VERTICAL button rotates BOTH vertical loops at once. Likely HORIZONTAL buttons rotate both horizontal loops (r2 & r12) together. 4 effective controls: V+/V-/H+/H-.
 c tile moved (r13,c2)->(r14,c2). b tile still (r2,c10).
LOOPS: V-left c2[r0-4,r10-14], V-right c12, H-top r2[c0-4,c10-14], H-bot r12. Intersections (junctions): (r2,c2),(r2,c12),(r12,c2),(r12,c12) = # shape / 4 interlocking loops.
GOAL: b->(r12,c12)[Vright∩Hbot], c->(r12,c14)[H-bot]. Budget: col0 still 0?! (probe didn't fill col0 -> maybe budget huge or counter differs). CHECK.
SOLVED MECHANIC: TWO 20-cell interlocking loops.
 VERTICAL loop = col c2(r0-4,r10-14)+col c12, order [(r,2) r in VC]+[(r,12) r in VC], VC=[0,1,2,3,4,10,11,12,13,14].
 HORIZONTAL loop = row r2(c0-4,c10-14)+row r12, order [(2,c) c in VC]+[(12,c) c in VC].
 Share 4 junctions (r2,c2),(r2,c12),(r12,c2),(r12,c12).
 Rotation newcols[i]=cols[(i+s)%20]. CONFIRMED: V-btn 8@(24-26,44-47)->(45,25) s=-1; H-btn e@(14-17,54-56)->(55,15) s=-1.
 All 16 btns: V (8=bottom s=-1, e=top s=+1); H (e=right s=-1, 8=left s=+1) [only s=-1 confirmed].
 GOAL: b->(r12,c12)[junction], c->(r12,c14)[H-only]. is_goal grid[45][45]==11 & grid[45][51]==12.
 Budget tentative 128 (col0: 0@1click,1@2click). refit if counter mispredicts.
 backtest 44/44 GREEN. SOLUTION (12 moves, confirmed btns only): V-x4,H-,V-x4,H-,H-,V- = clicks (45,25)x4,(55,15),(45,25)x4,(55,15)x2,(45,25). verified goal. Committing.
 SOLVE method: relaxed subgoal BFS (real python) "c@(12,14) & b@(11,12)" using ONLY confirmed V-/H- moves, then finish 1 V-.
CAUTION: L2 budget assumed 60 (only 2 data pts). If counter mispredicts (~k=8), refit round(64k/BUDGET), resume remaining moves (loop moves are correct).
