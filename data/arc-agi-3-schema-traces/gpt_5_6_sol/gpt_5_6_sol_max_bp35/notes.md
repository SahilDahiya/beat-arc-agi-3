# Notes — ARC3 bp35

## Confirmed mechanics
- Logical pitch 6 px. Action4 moves/faces right; action3 moves/faces left.
- Action6 drills e (one hit) and toggles c gates dense ↔ sparse. Sparse c is traversable. Gate corners reopen only when both the horizontal neighbour and the exact vertical underlay continuation are open.
- Colour-8 switches reverse gravity. Up anchor y37; down anchor y27; flips add the 10px anchor change to camera motion.
- Colour-f/b0b kills on gravity contact. Framed 7 is the goal. Action7 is inert except advancing the meter.
- Every non-reset action advances the bottom meter; L0–L5 use f, while L6 uses colour 7.

## Progress
- L0–L5 cleared; installed model reproduces all recorded transitions.
- L5 used three gravity switches and c-gate staging to weave around two hazard banks, then returned down c8 to the reopened c2 goal corridor.

## Current level — L6
- Entry player c3/world36, gravity up, scroll0.
- The left sidebar is a stack of separate colour-8 gravity switches at x1..5; a click consumes that segment, while adjacent consumed segments merge into one continuous open band.
- Cell map c2..c8 by world row:
  - w0 .#ccc.#; w6 same
  - w12 ..ccc..; w18 same
  - w24 .FcccF. (f at c3,c7; safe c2,c8)
  - w30 ######. (only c8 shaft)
  - w36 .P..c#.; w42 .......
  - w48 ....c#.; w54 ######. (only c8 shaft)
- Confirmed first sidebar click (3,39): only that six-column segment is consumed; gravity down, player c6/world42, scroll -16. The clicked segment shifts to screen rows21..25 as open; other sidebar segments remain usable.
- Newly revealed: world66 has an f hazard at c8, so descending the apparent c8 shaft would die. Goal is visible at c3/world72.
- Confirmed second sidebar click (3,29) from c7: gravity returns up; the world36 c7 wall blocks physical rise, scroll -16→-6, and the two consumed sidebar segments merge.
- Entering c8 rose 30 px to c8/world12 (scroll24), safely bypassing the c7/world24 hazard.
- Newly exposed upper map c2..c9: w-24 .cc.Cc#.; w-18 .c.C.c#.; w-12 .c.F.F#.; w-6 .######.; c9 is the sole open edge shaft through these rows.
- The c9 ascent is lethal under upward gravity: the long open shaft eventually reaches the f device at c9/world-54 (not world-30). Under downward gravity, c9 below world-42 remains the likely safe bypass.
- Replayed and closed c6/world24. Moving c8→c7 rose to c7/world0 (scroll36), stopped by the world-6 wall.
- Newly exposed: w-36 c2..c9 = #####c..; w-30 = .cF.Fc#. (f at c4,c6). Current c7/world0, up gravity.
- Third sidebar switch confirmed: c6 fell world0→18 onto the closed world24 gate; gravity down, scroll36→8.
- Fourth switch confirmed: after closing c4–c6/world12, gravity up with zero physical rise; scroll8→18, player c6/world18.
- Traversed to c2/world-30 (scroll66), stopped by world-36. Upper map c2..c9: w-54 #####c#F; w-48 #####c#.; w-42/-36 #####c..; w-30 .cF.Fc#. Hazards alternate at c4,c6.
- Fifth switch confirmed: c3/world-30 fell one cell onto closed c3/world-18; gravity down, scroll66→50, now c3/world-24.
- Entering c4 fell 12 px to c4/world-12 (scroll50→38), stopped by the world-6 wall. Newly revealed lower rows match the three dense c4–c6/world12 gates.
- Sixth switch confirmed after closing c4/world-24: c4 rose one cell to world-18 and the up-anchor moved scroll38→54. Consumed switch world coordinates are now tracked so hidden sidebar segments persist on reveal.
- Opened c5/world-18 and entered c5; it rose safely to world-30 (scroll54→66), between the c4/c6 hazards.
- Completed the next weave: closed c5/world-18, opened c6/world-24, flipped down, crossed into c6/world-12, re-closed c6/world-24, and flipped up to c6/world-18 (scroll54).
- Entering c7 under upward gravity rose to c7/world-54 (scroll90), revealing open world -90..-79, a solid wall bank world -78..-60, and the known c9/world-54 hazard. This is a dead end: c6/c8 are solid, upward is capped, and every visible sidebar switch is already consumed/off-screen.
- Safe c7 bracket confirmed, then c8/world-36 entered under down gravity. The c9 bypass falls 114 px to c9/world78 (scroll62→-52), safely passing the c8/world66 hazard and landing on the world84 floor.
- Lower chamber route completed: c7 rose to world60, crossed to c3, and the final down-flip entered the c3/world72 goal. L6 cleared.

## Current level — L7
- Entry player c3/world36, gravity up. The world30 wall has an open c5–c7 gap, but entering it would rise through the broad upper chamber into a full ceiling bank of f/b0b devices.
- Clicking a framed-f cell **splits/grows**, not XOR: the clicked block vanishes; each valid empty orthogonal neighbour appears; already-occupied neighbours remain. Static walls/devices suppress children. Initial c2/world18 produced its four-neighbour cross. Meter is colour7 on L7 too.
- Static walls and f/b0b devices are immutable: a propagated neighbour toggles only a base-open 5×5 cell, so the attempted child at c2/world6 was suppressed. Current framed blocks after two clicks are w12:c1,c3; w18:c1,c2,c3; w24:c2.
- Framed blocks are confirmed **safe solid canopies**, unlike f/b0b devices. The grown world24 canopy stopped c5 safely at world30 (scroll0→6); new reveal shows a dense c gate at c7/world-6.
- Canopy surfing confirmed: the player suppresses a would-be child in its occupied cell, so clicking the overhead block lifts exactly one cell. Surfed through c8 to world-6, opened c7, and crossed left; c6 rose to world-18 beneath the full dense gate bank at world-24 (scroll54).
- Goal is c9/world-42; its only open neighbor c8/world-42 is reached from above through dense c8/world-48, so a downward switchback is required. Upper seed was propagated to cap c6; surfed to c6/world-84 (scroll120). Hazard funnel: w-96 c1/c9, w-102 c2/c8, w-108 c3/c7, w-114 only c4-c6 open, w-120 c4-c6 hazards/full ceiling.
- Action7 is true undo (restores the prior spatial frame/state but does not refund HUD ticks); its earlier apparent inertia only undid a no-op. It remains exact full-state undo during the active-f HUD phase, so it is not gravity reversal. Direct clicks on the world-120 b0b ceiling devices are inert.
- The upper funnel is the intended route, not a dead end: it narrows c1/c9→c2/c8→c3/c7, w-114 leaves c4-c6 open, and w-120 fills those with hazards. Continuing the safe c6 canopy surf through w-108 reveals a colour-8 switch embedded at c5/world-144, above three ordinary full wall rows w-138..-126. Clicking it remotely reverses gravity down and drops c6/w-108 safely to c6/w-6 on the world0 floor (scroll144→32); never remove the final w-114 cap or contact w-120.
- A naive post-flip descent is a dead end: c8 falls to w18/w24, and c7 can downward-surf to w48, but world54..78 is a four-row full solid bank. The first exposed chamber rows w79..84 are open and contain no switch, so no lower reversal exists at the reachable bank.
- Correct plan: before ascending, open c8/w-48 and grow a flower at c6/w-48. Open c6/w-24 to land below it, surf twice to c6/w-54, then click the c5/w-48 side flower to regenerate the c6/w-48 floor behind/below the player. Continue surfing to w-108 and flip down; the staged floor catches c6 at w-54. A c7/w-54 side flower remains: split it, enter c7 (player suppresses its left regrowth), split the new c8/w-54 flower, then enter c8 through sparse c8/w-48 to fall into c8/w-42 and step right into the goal.
- Tried routing the w-48 seed above the c7 barrier: growth reached c8/w-54, but both sparse **and dense** c8/w-48 suppress its downward child (only shared seams redraw). Movable growth neither occupies nor consumes either gate state, so it cannot reach c8/w-42.
- Direct clicking the visible c9/w-42 goal is inert even from c8/w-54 directly above its open entrance (as well as remotely, with all gates open, and at a full-7 HUD). Action7 after an actual horizontal move fully restores the player as well as the grid, ruling out a partial-rewind exploit. Exact clicks on an f/b0b device's f, b, and central-0 pixels, the avatar, and empty-stack action7 are all inert—there is no direct object-click gravity control.
- Both horizontal board edges are closed (left-edge and right-edge movement tests block; no wrap or exterior route). Direct clicks on the ordinary c7/w-42 and c8/w-36 pocket walls are inert. Flower children aimed directly into both decisive barriers—sideways into c7/w-42 and upward into c8/w-36—are suppressed without damage, so no physical breach route exists. Opening c8/w-48 with a touching block is also ordinary; exact/off-center sparse-gate clicks toggle the whole gate.
- A player occupying a sparse gate intercepts every interior click; seam clicks are inert, so the underlying gate cannot be closed around the avatar. A remote block split while the gate is fully hidden also preserves its sparse state and does not displace the player, ruling out layer-redraw ejection. Opening c8/world-48 while the player is directly above it at c8/world-54 is also ordinary and does not act as a trapdoor or flip gravity.
- L7 block positions and sparse-gate toggles must be tracked in world coordinates: growth can create off-screen children whose shared seam is ambiguous in a viewport, and camera rises later reveal them.
- HUD is a 128-action budget: first 64 ticks fill 7, next 64 overwrite with f; the action filling the last f kills and auto-shows the entry board. Filling it never changes gravity, and clicking a filled-7 HUD pixel is inert.
- Horizontal movement into a movable framed-f block is simply blocked; it does not push the block. Clicking all three block pixel classes—outer 5, inner 3 accents, and central f—triggers the same split. A seam shared by two adjacent blocks selects only the lattice cell on its right/below (floor-coordinate ownership), not both objects.
- Clicking a movable block directly below the player is ordinary: the upward child is suppressed, but fixed upward gravity does not pull/push the player down into the vacancy. Block surfing is not symmetric. Completing a four-sided enclosure (static ceiling plus flower blocks left/right/below) and clicking the enclosed avatar are also inert.
- Opening every L7 c gate (the full nine-gate world-24 bank plus the already-open world-6/world-48 gates) has no collective reversal or mode effect. Clicking an arbitrary empty cell in the isolated c8/world-42 goal pocket is inert; blocks cannot be placed from empty space.
- Clicking the framed goal remains inert even with every c gate open and the HUD filled completely with goal-colour 7; full charge is only a budget phase, not a goal/reversal unlock. Clicking an unfilled colour-0 HUD cell after RESET is also inert, so the meter is not an interactive control.
- A genuine remote flower split performed after the HUD was already in its f phase still used normal growth and fixed upward gravity; both HUD phases are budget-only, not global physics modes. Clicking the adjacent framed goal while already in active f is also inert. Filled-7, empty-0, and filled-f HUD pixels are all inert, so phase-conditioned target/UI interaction is fully ruled out.
- L7 cleared with the staged c6/w-48 catch-floor route: down-flip landed w-54, clear c7/c8 side flowers, fall through sparse c8/w-48, enter goal.

## Current level — L8
- Entry: player c3/world36, gravity up; flower seed c6/world12. Sidebar c0 has colour-8 switches at world24 and world36 behind an immutable c1 wall. Static board: w0/6/18/24 = c2-c9 open; w12 same with flower c6; w30 has only c5-c7 open; w36/42/48 open c2-c9; w54 is a full board wall. Goal is hidden.
- L8 combines sidebar gravity switches with L7 flower growth. Clicking c0/world36 reverses down, consumes its full 7×6 segment, and drops c3/w36→w48 (scroll0→-22). It reveals goal c2/world66 below a c1-c9 wall bank at w54; the only passage through that bank is the inaccessible c0 sidebar shaft. Therefore flipping down from the entry column is a dead end. The intended route must first climb above the c1 vertical divider, cross into c0, then use a preserved switch to descend the sidebar and cross right to the goal below w60.
- Direct entry ascent via c5 is lethal: c3→c4 is safely capped at w36, but c4→c5 under upward gravity reaches a hidden f/b0b bank and dies. A flower canopy must cap/stage this shaft before using it.
- L8 flower growth is confirmed identical to L7: splitting the entry c6/w12 seed produced the valid cross at c6/w6, c5/c7-w12, and c6/w18. The c5/w12 child safely capped the formerly lethal c5 ascent at player c5/w18 (scroll18).
- Newly exposed upper rows: w-18 has dense e gates at c2-c4; w-12 has lethal f/b0b devices at c5-c9 but c2-c4 are open; w-6 is open c2-c9. Thus c4 is a safe route from c5/w18 up to c4/w-12, capped by the c4/w-18 e gate.
- From c4/w-12 (scroll48), newly revealed w-48..-19: c0 has switches at w-48 and w-24; c1 remains a wall. c5 is a wall through w-42..-24; w-24 also has hazards c6-c9. The c4 column is open from the e gate through w-48.
- Safe staging worked: undo to capped c5/w18, remotely drill c4/w-18, propagate flowers along c4, then surf the regenerated stack upward. Current player c4/w-24 (scroll60), capped by c4/w-30.
- Newly exposed: w-54 has c2-c7 open, c8 wall, c9 open; w-60 has a sidebar switch, lethal c2-c7, c8 wall, c9 open; w-66 is solid c1-c8; w-72 lethal c2-c8; w-78 is open c2-c9; w-84 is a dense-c bank c2-c9 with another sidebar switch. Player is safely c4/w-48 under flower c4/w-54 (scroll84).
- Planned weave reached c4/w-120 under the staged c4/w-126 canopy (scroll156). Upper ceiling is now mapped: w-132 has c0 and c2-c9 open with c1 still solid; w-138 has lethal devices c2-c9 and solid c0/c1; w-144/-150/-156 are full walls. The c1/w-126 e gate is the only sidebar crossing, but no upper colour-8 switch is visible, so preserve undo before committing to the crossing.
- Undid to c4/w-90 (scroll126), opened c1/w-126, and propagated the staged flower left into c0. Splitting a c0 edge flower grows a clipped child at logical x=-6: only its right frame seam (five colour-5 pixels at x0) is visible; the model tracks these offscreen children. Propagating the c0 branch down to w-90 and aiming its child directly into the adjacent c0/w-84 colour-8 switch was completely ordinary: the switch suppresses growth and does not activate.
- The actual player crossing through c1/w-126 was also ordinary: c0/w-126 has no trigger/control, and action3 at the left boundary is blocked even with clipped flowers outside. Thus neither flower-pressure, sidebar entry, nor exterior travel supplies the missing post-crossing down-flip.
- Consumed switch cells are ordinary flower/open terrain; flower pressure into an unconsumed switch is suppressed. Empty-cell probes are inert. Action7 exactly restores switches, gravity, flowers, player, and camera (only HUD cost persists). The c5 divider is immutable, x=6 beside a sidebar switch is inert, while x=0 on that switch's own frame activates it; switch ownership is the whole logical tile.
- Breakthrough from the terminal ascent frame: world-168 is a hidden bank of colour-8 switches at c1-c9, above the full w-162..-144 ceiling. It becomes safely visible only from c0/world-132, because c0/world-138 is an ordinary wall while c2-c9/world-138 are lethal. This is the missing fifth reversal.
- Final route: first consume the +36/+24 switch pair and return to the entry pose, clearing the eventual c0 descent. Execute the verified -60/-48 weave to c4/w-90. Stage only c2-c4/w-126 flowers (leave c1 gate closed), consume -84, route through c9, create a c9/w-42 cap from the w-30 floor, consume -24, surf back to c4/w-90, rise to c2/w-126, then open c1 and cross directly to c0/w-132 without spawning a c0 flower. Click the hidden c1/w-168 switch: with all six sidebar switches consumed, c0 free-falls to w66; move right through c1 into the c2 goal. Model plan length 116 (<128 HUD budget).
- Current run successfully executed actions 1-89 of that route and is at c9/w-42, gravity up. The sole mismatch was a clipped newly exposed seam: consumed c0/w-84 opens x0:6 of the world-78 top row and sparse c9/w-84 opens x55:60. L8 upward flower settling is now world-coordinate rendered; all 1199 checkable transitions are green. Remaining route is six c9 canopy splits, five clear/move-left pairs, two c4 gate clicks, align/cross c1, click the high bank, and enter the goal (27 actions).
