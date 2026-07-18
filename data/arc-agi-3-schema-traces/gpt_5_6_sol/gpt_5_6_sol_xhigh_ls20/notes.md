# Notes — ARC3 ls20

## Confirmed core
- 1/2/3/4 = U/D/L/R; unique 5x5 colour12/9 token moves by5 on colour3.
- Ordinary/blocked meter cost is level-specific: level0=1, levels1-2=2, level3=1, level4=2, level5=1 columns/action. Do not extrapolate by level number.
- Insufficient meter on non-refill action soft-resets to ENTRY and spends rightmost remaining 2x2 colour8 life marker (flags none). Refill works at zero.
- 11-ring pads are single-use, free full-meter refills; vanish to floor after leaving.
- Persistent 0/1 rotary button rotates 5x5 HUD 90° clockwise. Level0 press free; later presses cost.
- Matching lock: one rim-entry move then center move advances.

## Cleared
- Level0 cleared.
- Level1 cleared after one life-loss probe. Efficient ordering used bottom then unused top refill.

## Cleared level2
- Goal used foreground9 plus two clockwise rotations. The top bumper launched x54,y5 through corridor directly onto the matched lock entrance x54,y45; one down centered and cleared. A launch may terminate on a valid matched-lock entrance.

## Cleared level3
- Cost1. Used pad1, one all-0 shape-selector press, and three palette entries (14→8→12→9); exact final fuel route cleared. Pad2 was unused.

## Cleared level4
- Cost2. Used selector twice (family C), palette thrice (color8), synchronized two reciprocal contacts with the mobile rotary, and used a bottom bumper to the matched lock.
- Mobile rotary patrol/contact rule: short horizontal bounce track; either object entering the other rotates HUD. It can be hidden under the token and resumes after separation.

## Cleared level5
- Two checkpoint locks; completing the first consumes its 9x9 area, and only the second advances. Final successful replay used color8/C180 for lock1, then the all-zero catalogue and three rotary contacts for the second silhouette.
- All-0 catalogue from C180: top-T -> top-U -> Q(010/101/110) -> P180 -> canonical180. Rim tests silhouette; center requires exact color and a wrong-color center is blocked free.
- From the second-shape state, two consecutive palette contacts (follow the hidden southbound palette) produced 8→12→9; the bumper route then cleared lock2.

## Level6 current
- Cost2. Fog is a radius-20 raster disk about token top-left+(1.5,1.5). Terrain and moving sprites are clipped cell-by-cell at the light boundary; the grounded static maze and consumed pads are statefully rendered.
- Consumed pads: x9,y5, x14,y45, x29,y20, x39,y5, x54,y50. Available: x49,y5.
- Collecting x54,y50 powers a vertical rotary patrol at x54: it starts y10, spans six cells y5..30, and rebounds. Target lock x27,y48 needs color8 and occupancy 010/110/011 (rows1-3). Efficient control word: RRSSSSS.
- Current token x14,y45 on the freshly consumed refill, full at 21 actions; two palette contacts and one selector contact are complete. Remaining tail `[U,R,U,D,U,D,L,L,U,U,U,R,R,R,R,D,D,D,D,D]` completes selector/palette cycling, obtains exact target, and centers the lock.
- Model backtest is green on all 511 checkable transitions; the exact remaining 20-action tail simulates level_up with one action of fuel left.
