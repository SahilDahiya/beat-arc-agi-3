# vc33 — CONFIRMED MECHANICS (L0-L4 cleared, 273 transitions green)

## Core hydraulics
- Tanks split by rods (color 5). Water green(3) floor-side, black(0) sky-side; sky = valve side.
- Valve (9-block) press: its tank loses `step`=rod-thickness across the adjacent rod. Bounds [box lo, hi+1]; L2-style full-to-edge flooding legal (incl. covering valves).
- Floats (4-body+tail 11/14/15) ride their tank's surface; tail at sky-most 2 cols.
- Doors (blue 1 in rod): OPEN iff both adjacent levels == flush with door's sky edge (hi+1 sky-right / lo sky-left). Render: cyan 12 + black channels rod±2 rows, door-span shrunk 2. Click open door: ALL fitting floats (occ ⊆ door span) cross, centered in dest band, riding dest level.
- GATES (tail-colored cols in rod): WIN = every float tail on its color-matched gate cols FROM ITS DOCK TANK. Dock tank: must DIFFER from float's entry tank when level has doors (journey!); doorless levels: entry tank ok. (L4: bb D→A, ee A→D; L3: S1→S3; L0/L2: same-tank.)
- BLOCKS (door-levels): float-tank DESCENDING landing its tail exactly on gate cols is REFUSED unless it completes the WIN. Rising/empty/outer... final understanding: non-win gate-col landings refused for INNER bands; outer/non-dock bands may park freely (L4 data). Rising always free.
- Timer row0: per-level (a n + b)//c click-indexed; refit by brute force when broken. Never matters much (64 budget).

## LESSONS
- NEVER eyeball grids or ad-hoc scan levels (valve rows lie!) — use wm._parse/_levels via run_python.
- Verify plans by SIMULATING through wm.predict before committing.
- Planner state must come from the model's own scanners.

## L5 (current): MIXED topology!
- Horizontal rod rows 29-31 (full width) + vertical rod cols 21-23 (rows 1-28). Sky-LEFT (valves at cols 0-2 & 24-26).
- Tanks: TL (cols3-20 rows1-28, L=3 FULL), TR (cols27-63 rows1-28, L=39), BOT (rows32-63, L=18). Levels = first green col (sky-left).
- Doors on horiz rod: D1 cols6-17 (TL<->BOT, opens @ L==6 both), D2 cols30-41 (TR<->BOT, opens @30). Gate bb cols48-49 (TR/BOT). Float bb in TL (occ [L,L+5], tail [L,L+1]).
- Valves: TL->BOT (1,27); BOT->TL (1,33); TR->BOT (25,27); BOT->TR (25,33). Step 3.
- PLAN (20 clicks): (25,27)x3 [TR 39->48, BOT->9], (1,27) [TL 6, BOT 6], door1 (11,30) [float->BOT], (1,33)x2 [TL->0 flood, BOT 12], (25,33)x6 [TR 48->30, BOT 30], door2 (35,30) [float->TR], (25,27)x6 [TR 30->48: float tail lands 48-49 = DOCK = WIN].
- Sum L conserved = 60. Dock=TR (≠ entry TL ✓ journey rule).
- Model needs 2D region pathway (bands can't express mixed rods) — writing it.
