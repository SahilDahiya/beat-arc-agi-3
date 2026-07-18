# ARC3 Notes

## General mechanics
- Only click (6). Color-5 bridge bands separate coupled green slabs; color-9 pads transfer one unit of green from the pad-side slab to the other. Boundaries move oppositely; every arrow on a slab rides with it.
- Unit = bridge thickness (4 in L0–1, 2 in framed L2). Transfers block at physical bounds. In framed chains, a markerless reservoir has one native unit below its entry fill; farther donation requires prior upstream replenishment (stock is visible in its moving boundary).
- Goal requires exact same-color marker coordinate alignment simultaneously AND each arrow must occupy the chamber directly adjacent to its target bridge on the side implied by its entry position. Apparent transfer blocks are donor stock/capacity limits.
- Framed chain stock: a markerless donor has one native unit below entry fill. A donor feeding a downstream arrow begins one unit short of the transfer needed to align it, forcing an upstream replenishment; moving boundaries visibly track stock.
- Clock: horizontal unframed floor((5t+2)/4); vertical unframed floor((14t+6)/11), matched L3 t1..16 (old 9/7 failed at t16); yellow-framed floor((17t+11)/20). Stateful phase.

## Cleared
- L0: one horizontal bridge, marker 11.
- L1: two horizontal bridges, routed through upstream donor.
- L2: four framed vertical bridges. Correct finish was exact e/f/b=41/39/47 after routing stock; adjacent docks and reservoir settling were disproved.

## Level 3 cleared
- Unframed vertical unit3 layout, bridges x=12–14,27–29,42–44,54–56. Actual bottom pads exist only at x=(10,16),(40,46),(52,58), y62; bridge2 has no pads (x25 probe was black/no-op and model matched).
- Color1 sections interrupt bridge1 (y43–54) and bridge2 (y34–45), likely gates. The b arrow in S0 (bar y48–49) lies beside gate1; target b is in bridge3 y29–30, suggesting the arrow may need to traverse gates horizontally rather than simply align by vertical slab motion.
- Bridge1-left matched ordinary unit3 transfer exactly: arrow bar 48–49→45–46, S0 boundary49→46, S1 boundary61→64; color1 did not change. Bridge1 cannot continue while S1 is full.
- Bridge3-left shifted only S2→S3 (boundaries55→52 and58→61); no nonlocal cascade yet. Hypothesis: drain S2 toward gate2's lower edge y46, using bridge4 to make S3 capacity, then gate2 may open/transfer.
- Second bridge3-left succeeded (S2 52→49, S3 61→64), proving donor-stock floors are specific to yellow-framed L2; model guard fixed, backtest 51/51.
- Alternating bridge4/bridge3 brought S2 boundary to46 at gate2's lower edge; both moves remained local and no automatic gate event fired.
- Clicking gate1 color1 beside the aligned arrow was also inert. Color1 is not directly interactive.
- Alternating bridge4-left/bridge3-left remained purely local while sweeping S2 through gate2. Latest 7 queued geometries matched; stop was meter-only. Current S2/S3/S4=34/64/61, so S2 is now empty across gate2 y34–45 while S1 is full.
- Clicking gate2 color1 at (28,40) remained inert even with S2 empty across the gate; direct gate controls are ruled out. Backtest 63/63.
- Bridge1-left still blocked with S2 boundary34, ruling out a simple overflow whenever S2 is empty across color1. Backtest 64/64.
- Filled downstream to S2/S3/S4=31/64/64, but bridge1-left still blocked. Direct and passive fluid-transfer theories for color1 are ruled out; backtest 67/67.
- Clicking b at y44 was inert. Crucial correction: gate crossing may require the entire arrow component, not just its bar, inside color1. At entry the arrow spans y43–48, fully inside gate1 y43–54; after the first upward transfer it spans40–45 and is no longer fully inside gate1.
- At full gate containment, clicking b bar, color4 arrowhead, and color1 gate all remained inert. Click-triggered arrow crossing is ruled out; backtest 72/72.
- Reset refunded the clock. Color1 center, left edge x27, and right edge x29 were all inert, so it is not an embedded rocker. Backtest 74/74.
- Both bridge2 color5 segments were inert. All direct visible-region controls are ruled out; backtest 76/76.
- CONFIRMED condition gate: after bridge1-right twice, S0=S1=55 (= gate1 lower edge+1). Gate1 automatically changed color1→12 and carved black vents at the adjacent pad-center columns, inset two cells from each gate end. General activation encoded; backtest 78/78.
- CONFIRMED activated-gate traversal: clicking color12 gate1 at (13,48) moved the whole aligned arrow from S0 to the same relative position in S1 (x +15), without moving boundaries. Encoded generally; backtest 79/79.
- Activated color12 is conditional, not permanent: the next x16 made adjacent boundaries unequal, so gate1 reverted 12→1 and vents restored to natural slab fill while the arrow rode S1 upward. Dynamic update encoded; backtest 80/80.
- Revised BFS from current (17): x16×2; x52×6; x40×3 activates gate2; click (28,40) crosses arrow; x40×5 aligned b at y29–30 and cleared L3.

## Level 4 cleared
- Horizontal unit3 with three bridges and two arrows. Both must traverse inward: e S0→S1→S2 and b S3→S2→S1, then align to target x14/x20.
- Goal requires both coordinate alignment and target-adjacent chamber placement; the earlier coordinate-only state did not clear.
- Conditional color1 gates are the rotated L3 mechanic. Gate crossing preserves the movement-axis coordinate but CENTERS the whole object in the destination chamber along the orthogonal axis (confirmed by gate3 b landing rows39–44, not translated to38–43).
- Meter is a 64-cell elapsed-budget gauge rendered nearest-cell: standard levels budget50 => (64t+25)//50; framed L2 budget75 => (64t+37)//75; L4 budget200 => (64t+100)//200. This general rule matches all history through L4 t30; prior short rational fits were epicycles.
- Gate3 traversal and middle-gate simultaneous swap both matched exactly. Afterward e was S2 x50 and b S1 x50.
- Refined stop observation: any arrow in its target-adjacent chamber cannot be carried left once its slab boundary is25; b via target bridge0, e via target bridge2, and b via the non-target middle bridge all no-op from this state. The earlier 'matching bridge' rule was too narrow. A hard floor makes the old coordinate/chamber goal unreachable, so some dock interaction or goal abstraction is still missing.
- Current b S1 x23 and e S2 x23, boundaries [61,25,25,52], both at the observed stop. Fixed b target click (20,15) was inert; backtest 152/152.
- Exact-column probes ruled out direct docking and pad subcell control. Both middle directions from symmetric b/e x23 were blocked. Moving e right once to x26 did NOT unlock p1-above: b/S1 still could not cross boundary25, confirming a real inner-slab floor rather than arrow interlock. Current [B0..B3]=[61,25,28,49], b=S1 x23, e=S2 x26.
- CONFIRMED goal generalization: a target accepts its arrow from EITHER immediately adjacent chamber. Exact inner alignment was impossible because B1/B2 stop at25, but routing b through gate0 to outer S0 and e through gate2 to outer S3 allowed exact x20/x14 and cleared. `_all_aligned` now checks either adjacent side.

## Level 5 cleared
- Entry has horizontal bridge y30–32 split above by vertical wall x21–23: top-left and top-right are separate reservoirs, while the bottom is shared. Four pads connect each top reservoir to the bottom. NW (1,28) changed top-left right-filled boundary 3→6, bottom boundary18→15, and carried b x3→6; no y motion. L5-specific branching transfer is encoded/backtest green.
- CONFIRMED side-right gates: left color1 x6–17 activated when top-left=bottom=6; right gate x30–41 analogously activates at top-right=bottom=30. Vents are the same inset pattern. Clicking active left gate carried b into the shared bottom; BFS then activated/crossed the right gate and aligned b x48 in top-right, clearing.

## Level 6 current
- Yellow-framed unit2 FIVE-RESERVOIR STAR, not independent rows: one continuous central reservoir x24–39,y8–55, surrounded by TL/BL x8–21 and TR/BR x42–55 arms split at horizontal wall y30–31. Vertical bridges x22–23 and40–41. Pad pairs at y8–9 and32–33 couple each arm to the shared center.
- Entry boundaries C/TL/BL/TR/BR = 16/28/40/14/42 (bottom-filled). Clicking BL central-side pad (24,32) confirmed ordinary mass transfer C16→18, BL40→38, carrying b y40→38. Layout detector was fixed to exclude meter row; backtest 210/210.
- Gates: TR y16–23; BL and BR y38–45. Targets e(y18) on left-top bridge, b(y26) right-top, f(y50) left-bottom; arrows b BL y38 and e BR y42.
- CONFIRMED TR activation: outer-side pad (42,8) made C18→16 and TR/f14→16, gate y16–23 changed 1→12, and unit2 inset vents opened at x38,43 over y17–22. L6 meter t1=0,t2=1 provisionally fits budget200.
- CONFIRMED gate traversal: click (40,19) carried f TR→C preserving y16 and centered its width3 component at x31–33 (ceil-centering in even-width chamber). Backtest 212/212.
- Key invariant: every arrow begins at its reservoir boundary and remains there through transfers/gates. Finish is f in BL boundary50, b in TR boundary26, e in C boundary18. Constructed 46-click route from current: BR-central×2, TL-central×9, BL-gate (swap f/b); BL-outer×6, TL-outer×5, TR-gate (b out); TL-central×6, BL-central×5, BR-gate (e in); BL-outer×5, TR-outer×5. Pixel-model simulation reaches exact markers and predicts final win.

