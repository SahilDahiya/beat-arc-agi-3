# L7 — MULTI-STAGE (turn ~52). Rotation found; now pointer blocked by '7'/'a' bars in its col19 path.
## POINTER BLOCKED: e-grow no-op at (13,19) - pointer tip row14, can't enter '7' bar (rows15-17). OVERLAP NOT ALLOWED (confirmed 0-cell no-op). Obstacles in col18-20: '7'(rows15-17), 'a'(rows33-35). Must CLEAR them.
## ROTATION cycles the RIGHT arm 90°/click of a 'b'-box '4'-RING cell (46,18). Each coupling's right-partner points a direction; only the one pointing DOWN (into open gap cols48-50) can grow unlimited:
##   e-down => pointer descends (current). 9-down => topleft arm raises unlimited. 8-down => botleft arm moves unlimited. (only ONE down at a time - they're 90° apart)
## PLAN (multi-stage, needs MODEL+BFS - too complex for hand): 
##   1. retract 'e'(53,11) so right bars short enough to rotate (e is long now).
##   2. rotate(46,18) until right-9 DOWN. grow '9'(45,4) to raise topleft arm HIGH so topleft-1 clears its wall(cols12-14 rows21-23, need '1' rows<=20).
##   3. shrink '7'(21,58) to slide topleft-1 RIGHT past col20 (to cols21-23) => col18-20 CLEAR of '7'&'1'.
##   4. similarly clear 'a': rotate 8-down, move botleft arm, shrink 'a'(7,58) to move botleft-1 out of col18-20.
##   5. rotate(46,18) until right-e DOWN. grow 'e'(59,11) to descend pointer thru now-clear col19 to (43,19)=WIN.
## NEXT: BUILD _predict_l7 model (arms+rotation+couplings+walls+off-grid-clip) -> run_bfs. Complex like L6. OR execute manually 1/turn (~20 turns).
## CORRECTED coords (box center=+/-3, any left-half cell shrinks, right-half grows):
##   TOP boxes: '9'box center col42 row4 -> 9-grow(45,4) 9-shrink(39,4). '8'&'e' center col42/56 row11 -> 8-grow(45,11) 8-shrink(39,11) e-grow(59,11) e-shrink(53,11). 'c' center col56 row4 -> c-grow(59,4) c-shrink(53,4).
##   BOTTOM boxes (middle row 57 NOT 58!): 'a'box center col11 -> a-shrink(9,57) a-grow(13,57). '7'box center col25 -> 7-shrink(23,57) 7-grow(27,57).
##   rotate(46,18). 
## KINEMATICS: '1' tips are 15 ROWS long. Growing coupling TRANSLATES '1' up by 3. botleft-1 was rows33-47, needs bottom<=41 to clear wall(rows42-44) => need +6 raise = 2x 8-grow.
## STAGE B progress: 8-grow x1 done (botleft-1 rows30-44, bottom44 STILL in wall). a-shrink x1 done (botleft-1 cols27-29). NEED 1 MORE 8-grow (-> rows27-41, bottom41 clears wall), THEN shrink 'a'(9,57) 4x -> botleft-1 cols27->15-17. Then shrink '8'(39,11) 2x to lower.
## STAGE B DONE (turn ~66): 'a' cleared - botleft-1 cols15-17, 'a' cols10-14, col18-20 CLEAR rows26-41. right-8 len11 (down). 
## NOW: shrink '8'(39,11) 2x -> lower arm, right-8 len11->5 (rotation-safe). Then rotate(46,18) 1x -> 9-DOWN for stage A.
## !!!! PATH CLEAR (turn ~79) !!!! BOTH '7'&'a' obstacles cleared. col18-20 rows9-41 ALL EMPTY. pointer rows4-8, diamond rows42-44. 
## FINAL SEQUENCE: shrink '9'(39,4) 1x (right-9 len8->5, rotation-safe; topleft-1 stays cols21-23 clear). Then rotate(46,18) 2x -> e-DOWN [state2->3->0]. Then grow 'e'(59,11) ~12x: pointer (7,19)->(10)->(13)->...->(43,19) = DOCK = WIN 8/8 GAME COMPLETE!!
## Watch for win/level-up flag. Build e-grow model to batch OR 1/turn.

## STAGE A plan (MEASURED turn~68): topleft-1 = 12 rows (rows15-26 cols3-5). '7' bar rows15-17 cols6-28. wall cols12-14 rows21-23.
##   need topleft-1 bottom<=20 to clear wall: raise +6 (2x 9-grow, translate up3 each -> rows9-20). Then shrink '7'(23,57) until '7' left-end>20 & topleft-1 at cols21-23: 6x shrinks (left-end col6->24, topleft-1 cols3-5->21-23). Then col18-20 CLEAR. Then shrink '9'(39,4) 2x lower.
##   right-8 now len5 (rotation-safe). Rotating to 9-down next.
## KEY: right bar must be len<=6 to rotate (right/left hits walls cols39-41/57-59). Lower coupling (shrink) before rotating.
## COUNTER (row63): N '4's at right end (cols 64-N..63), rest '3's. N increments +1 every 3 ACTIONS (pure action counter, incl no-ops). For batch model: thread action-count in state, +1 to N every 3rd. Calibrate phase via backtest.
## MODEL PLAN for batching: L7 predict branch handles specific action by grid-manipulation: e-grow(59,11)=pointer 'd' col19 down3 + right-e cols48-50 down3; 9-grow(45,4)=translate '7'+topleft-1 up3 + right-9 down3; 7-shrink(23,57)=topleft-1 right3 + '7' shorter3. Plus counter. Then commit batches.
## right-e down at cols48-50; diamond (43,19); pointer col19.
## VERIFIED WALLS + rotation cycle (turn ~53):
##  - topleft-1 wall: cols12-14 rows21-23. topleft-1 at rows15-26 (cols3-5 currently). To clear '7' from col18-20: raise arm +6 (2x 9-grow, needs right-9 DOWN) -> topleft-1 rows9-20 (above wall) -> shrink '7' -> topleft-1 slides RIGHT to cols21-23, '7' to cols24-29 => col18-20 CLEAR at rows9-11.
##  - botleft-1 wall: cols24-26 rows42-44. botleft-1 at rows33-44 (cols30-32). To clear 'a': raise arm +3 (1x 8-grow, needs right-8 DOWN) -> botleft-1 rows30-41 (above wall) -> shrink 'a' many -> botleft-1 slides LEFT to cols15-17, 'a' to cols12-14 => col18-20 CLEAR at rows30-32.
##  - ROTATION = 90° CCW per (46,18) click: e:left->down->right->up->left. 9:right->up->left->down. 8:up->left->down->right. Currently (after 1 rot): e-DOWN,8-left,9-up,c-right.
##  - rotating bars len<=8 OK (fit in enclosure cols42-56). Retract 'e' to len<=5 before rotating.
##  - ONLY the DOWN-pointing coupling grows unlimited (gap cols48-50 -> open rows44+). So: rotate 9-down->grow9->clear7; rotate 8-down->grow8->clear a; rotate e-down->grow e to (43,19)=WIN.
##  - pointer must be retracted to <=(7,19) before raising topleft arm (else '7' rising to rows9-11 overlaps pointer bar).

# L7 — !!!! ROTATION FOUND !!!! (turn ~48)
## THE MISSING MECHANIC: clicking a 'b'-box '4'-RING cell (46,18) ROTATES the right hub 90°! (the 'b'-CROSS cells were no-ops, but the '4' RING rotates.)
## After rotation: right-'e' now points DOWN at cols48-50 rows36-40 (was left). Path down cols48-50 rows41-62 is CLEAR (gap+open). So e-grow now extends right-e DOWN freely = UNBLOCKED.
## CONFIRMED WORKING: after rotation, e-grow descends pointer! (7,19)->(10,19), right-e grew down thru gap (rows36-44). KEEP GROWING 'e'(59,11) to (43,19)=WIN. ~11 more grows.
## PLAN: grow 'e' (59,11) repeatedly -> pointer descends col19 toward diamond (43,19) [from (7,19), ~12 grows]. Right-e grows down thru gap into open region (no wall). WATCH: does pointer pass '7' bar(rows15-17) & 'a' bar(rows33-35) in its path? = overlap test. If blocked, clear/rotate. e-grow=(59,11) shrink=(53,11). rotation cell=(46,18) [try again to rotate more if needed].
## rotation: e:left->down, 8:up->left, c:down->right, 9:right->up (90deg). To point e a different way, click (46,18) again (cycles).

# L7 (LAST level, 7/8) — COUPLED articulated-arm puzzle. HARD.

## GOAL: dock 'e' pointer at hollow diamond (43,19). Pointer currently (7,19) [entry (4,19)]. Only 13-pointer on board.

## MECHANIC (probes 1-6, consolidated)
- Click a COLOR's box -> grow/shrink/rotate ALL bars of that color TOGETHER (COUPLING).
- Coupling map: '7'=unique(topleft). 'a'=unique(botleft). '8'=COUPLED(botleft '8' cols9-11 + right '8' cols47-49). 'e'=COUPLED(pointer (4,19) + right-arm 'e' cols45-46). '9'=?coupled(topleft '9' + right '9'). 'c','b'=right arm.
- 'e'-grow: pointer moves DOWN col19 (+3), right 'e' extends LEFT (+3). To reach diamond need 12 grows.
- BLOCKED: 'e'-grow no-ops when right 'e' hits col39-41 WALL (happens after ~1 grow from entry). '8'-grow blocked when right '8' hits rows23-25 wall. Every coupled grow limited by partner+wall.
- 'b'-rotate(17,48) = NO-OP (blocked; right arm too boxed OR wrong button).
- Counter row63 = (na+2)//3, na=click# (L6-style). t4=2 after 6 clicks. no-op clicks still tick it sometimes.

## SOLUTION STRUCTURE (hypothesis)
'e' pointer descent needs the coupled right 'e' to have LEFTward room each grow. Right 'e' is boxed by col39-41 wall. => Must shift the right 'e's ROOT rightward (reposition the right-arm chain via 9/c/b) between pointer-descents. CYCLE: grow-e (ptr down) -> reposition right-e root right -> repeat x12.
Right arm layout (cols42-53 rows26-40): '8'(cols47-49 up), 'e'(cols42-46 left), 'b'(cols48-50 hub), '9'(cols52-53 right), 'c'(cols47-49 down rows36-37). 'b' likely the HUB/root. Boxed by fff walls (cols39-41 left, rows23-25 top, cols57-59 right, gap cols48-50 rows41-44 bottom).
Overlap: left '7'/'a' bars sit in pointer path col18-20 but likely OVERLAP-ALLOWED (their '1' tips wall-trapped, can't clear).

## ALT win hypothesis: a BAR covers diamond center (43,19). botleft arm: 8-grow lifts '1' above wall rows42-44, a-shrink '1' to col19, 8-shrink down onto diamond. (But 8-grow coupling-blocked by right-8 wall.)

## Probes done (indices 574-579): 7grow(27,58)[topleft +3left], ashrink(7,58)[botleft '1' left3], 8grow(45,11)[BOTH 8s up, coupled], egrow(59,11)[ptr down3+right-e left3], egrow2[NOOP wall], brot(17,48)[NOOP].
## Box click coords (big box: grow=center+3col, shrink=center-3, middle row):
7:grow(27,58)/shrink(21,58). a:grow(13,58)/shrink(7,58). 9:grow(45,4)/shrink(39,4). c:grow(59,4)/shrink(53,4). 8:grow(45,11)/shrink(39,11). e:grow(59,11)/shrink(53,11). b:7x7 cross center(18,48) rot top(17,48)/left(18,47)/right(18,49)/bot(19,48).

## ENTRY GEOMETRY (acts[573].grid, clean) — bar = 3-thick, len given:
TOP-LEFT arm: '9' root cols27-29 rows18-19(down,len2) -> '7' cols9-28 rows15-17(LEFT,len20) -> '1' cols6-8 rows15-26(down,len12,tip).
BOT-LEFT arm: '8' root cols9-11 rows39-40(?up,len2) -> 'a' cols10-29 rows36-38(RIGHT,len20) -> '1' cols30-32 rows36-50(down,len15,tip).
POINTER 'e': root (4,19) points DOWN len2, pointer 'd' at tip-1 (=(4,19) at entry). Grows down col18-20.
RIGHT: 'b' HUB cols48-50 rows32-34 (3x3). 4 radiating len-2 bars: 'e'(left cols45-46) '9'(right cols52-53) '8'(up cols48-50 rows29-30) 'c'(down cols48-50 rows36-37). All separated from hub by '3' cap.
DIAMOND target hollow (43,19). Walls: fff cols12-14 rows21-23; cols24-26 rows42-44; big right enclosure cols39-59 rows23-44 with gap cols48-50 rows41-44.

## COUPLING pairs (grow/shrink together): 'e'=[ptr(down)+right-e(left)]. '8'=[botleft-8(up)+right-8(up)]. '9'=[topleft-9(down)+right-9(right)]. Unique: '7'(left),'a'(right),'c'(right-down),'b'(hub rot). '1'=passive.

## SOLUTION HYPOTHESIS (test after RESET):
b-rotate was NO-OP because probes had LENGTHENED right bars (didn't fit rotated). At COMPACT entry (all len2), b-rotate should work. Rotate 'b' so right-'e' points DOWN through gap cols48-50 -> open runway (rows45+). Then e-grow works freely (ptr descends col19, right-e grows down). ~13 e-grows -> ptr to (43,19). Manage overlap w/ '7'(rows15-17)/'a'(rows36-38) bars in ptr path — likely overlap-allowed.
=> RESETTING now to clean/compact entry. NEXT: probe b-rotate (try (17,48) top, (19,48) bot, (18,47) left, (18,49) right) at entry to find the rotation that points 'e' DOWN. Then grow 'e' toward diamond.

## !!! CRISIS (probe #8): b-rotate(17,48) NO-OP even at COMPACT entry. Right hub may not rotate at all.
## RIGHT enclosure map (walls f): box interior cols42-56 rows26-40. Walls: cols39-41 & cols57-59 (rows23-43), rows23-25 top, rows41-43 bottom EXCEPT gap cols48-50 (-> open region rows44-52 all cols). All vert bars (8,b,c) at cols48-50 (aligned w/ gap!). e at cols45-46(left), 9 at cols52-53(right).
## Each right bar has only ~1 grow room: e-left(->col42,wall41), 9-right(->col56,wall57), 8-up(->row26,wall25), c-down(->row40; c at cols48-50 CAN grow thru gap into rows44+! but 'c' is UNIQUE/useless).
## => coupled right-e max 1 grow -> 'e' pointer can descend ONLY to (7,19). CANNOT reach diamond (43,19). GOAL AS UNDERSTOOD = IMPOSSIBLE. Either (a) rotation frees right-e (but b-rot no-ops), or (b) I misread the GOAL.
## RECONSIDER GOAL: pointer reachable only (4,19)/(7,19). Diamond (43,19) fixed & unreachable by ptr. Nothing else has a 'd' pointer. Nothing reaches (43,19) (botleft-1 wall-blocked cols24-26; right arm boxed; couplings all wall-limited to 1 grow).
## Next ideas: (1) try other b-buttons (18,49)/(19,48)/(18,47) or the '4' ring cells - maybe rotation works w/ right button. (2) Build full model+BFS to see if ANY seq wins (explores what manual can't). (3) Reconsider if win = non-docking config. (4) 'c' grows down thru gap into open lower region - does that connect to anything useful?

## FULLY CONFIRMED IMPOSSIBLE (dock e-ptr@diamond): each right partner (e,8,9) has EXACTLY 3 cells to its wall = 1 grow each. Couplings mathematically 1-grow-limited. e-ptr maxes (7,19). Walls block bars (a-shrink#2 into wall = 0-cell noop). b-hub won't rotate. Direct-click noop. NOTHING reaches (43,19). '9'-grow just translates topleft arm up3 (no hidden mechanic).
## So WIN CONDITION IS NOT dock-ptr-at-diamond. Unknown. Everything is JUST out of reach (uniform 3-cell margins - suspicious/designed). 
## Diffs done: all 12 probes analyzed. read_history: wins=0, no hints. Reachable notable configs: ptr(7,19); topleft up1/left(7grow); botleft up1/'1' to cols27-29(min,wall)/right(agrow); right bars +1; c down(multi).
## EXPLORING empirically for the real win condition: try configs, watch state for WIN. Candidates: (a) connect ptr to diamond via bar-chain? (b) align two '1' bars? (c) all couplings maxed? (d) something w/ counter.
## probe 11 (diamond direct-click (19,43)) = NO-OP. Direct clicks don't work.
## KEY UNTESTED ASSUMPTION: do WALLS block bars? Assumed yes (from e-grow#2 noop) but NOT directly verified. TESTING: a-shrink botleft-1 (cols30-32) LEFT toward wall cols24-26 rows42-44. Sequence: ashrink->27-29, ->24-26(WALL TEST: blocks or passes?), ->21-23, ->18-20(col19 covers diamond!). If '1' passes the wall & covering (43,19) wins -> SOLVED. If '1' blocks at 24-26 -> walls confirmed, still stuck.
## '9'-grow(probe10): topleft arm MOBILE - '9' grew, raised '7' bar to rows12-14, right-9 grew right(coupled, 1 grow).

## CONFIRMED (probe 8,9 + checks): diamond (43,19) FIXED (doesn't move w/ arm). e-ptr max descent=1 grow ->(7,19). b-rotate NO-OP both buttons (17,48),(18,49) -> right hub CANNOT rotate. right-e stuck pointing left into col41 wall.
## => docking e-ptr at (43,19) is IMPOSSIBLE under my model. I'm MISSING something fundamental. Options: mis-read coupling / arm roots / walls / OR goal is not e-ptr@diamond.
## Nothing reaches (43,19): botleft-1 wall-blocked(cols24-26 rows42-44, can't pass even lifted), botleft-8 fixed col9-11, right arm boxed. 
## TO RECONSIDER: (a) build run_python sim of all arms+coupling matching 9 probes -> BFS/verify. (b) re-read ENTRY for a goal indicator I missed (box contents? a 2nd marker?). (c) test if clicking a NON-box cell (diamond/pointer) does anything. (d) reconsider if win = arms in home config or some alignment, not docking.
## Probing '9'-grow(45,4) = last untested coupled color (topleft-9 down + right-9 right).

## OLD NEXT: probe c-grow(59,4) ... (done)
## ==== FINAL STATUS (turn ~40, ~19 probes) ====
## ALL RULED OUT: rotation(all 5 b-cross cells noop); pointer HARD-capped (7,19) [cell-verified: e-grow no-ops once right-e at cols42-46/wall col41]; walls block bars (a-shrink#2 into wall=0-cell noop); direct-click(19,43)=noop; '3'-handle click(18,3)=noop; box cells=grow(right)/shrink(left) only; 1 diamond+1 pointer (full scan); nothing reaches (43,19); hub 'b' FIXED (can't move, enclosure ~14 wide anyway - even moving hub gives only ~3 more e-grows, need 12); '9'/'8'-grow raise left arms but DON'T move pointer; L1-formula (multi-bar pointer) doesn't apply (only 'e' moves L7 ptr); diamond FIXED; counter cosmetic.
## MATH: pointer row=4+3*le, le<=1 (right-e 3-cell margin) -> ptr max row 7. Diamond row 43. UNREACHABLE. All couplings uniform 1-grow (3-cell margins, DESIGNED). Everything exactly 1-grow short of connecting.
## => Standard goal PROVEN unreachable. Win must be non-standard/unknown OR a mechanic ~19 diverse probes didn't trigger.
## STILL-UNTRIED: build full run_python sim to render ALL reachable states (though math says no win config); click box LETTER cells (e.g. (38,3) '9'-cell); very long sequences; brute-force cells.
## Being thorough but stuck ~28 turns. Per instructions: never conclude impossible - keep trying fresh angles / re-diffing.
