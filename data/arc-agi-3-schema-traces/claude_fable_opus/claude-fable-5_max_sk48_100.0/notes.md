# Notes — sk48 (ARC3), 8 levels. Game: "crane & train" skewer puzzle. Level 4/8 now.

## Confirmed cross-level mechanics (backtest-green 148/148; geometry from layout(ENTRY_GRID))
- Actions: 1/2 engine up/down 6 (track lattice, clamps top_min=tr0-2 / top_max=tr1-3;
  clamp can REALIGN lattice, e.g. L2 41->35->...->11->6). 3/4 rope -6/+6 (L 1..l_max).
  6 click = TOTAL no-op (no bar tick). 7 untested. RESET refunds bar & restores level.
- Riding: r0==top+1 && c0<=tip. Riders follow all rope/engine motion.
- Extend: riders +6; tip-PLOW pushes free ahead-blocks to new_tip+2; 6-gap push chains;
  jam at blk_cmax/immovables -> jammed blocks slide UNDER rope (=hook). Retract: mirror
  (floor blk_cmin=ec1+2), jammed -> rope slides out (park/unhook).
- Vertical: riders follow; non-riders straddling rope DEST rows (r0==newtop+1, c0<=tip)
  pushed by dy, chain pushes via 4-overlap. Blocks pushed past margins = dead-guard (avoid).
- CHAINS (vertical ropes from 2x2 anchors above panel; cols cc0/cc0+1, rows rtop..rbot,
  tex (3,2),(2,3),(2,2) from rtop; fixed length): blocks overlapping at chain rows are
  threaded: pinned horizontally (and act as jam obstacles), slide vertically, fall off
  past rbot (become free). Horizontal move INTO chain col JAMS (thread from below only!).
  Chained riders SNAP vertical moves to slot lattice (next slot in direction; jam above
  top slot rtop+2). My rope renders OVER chains, blocks over both.
- WALLS (5-rects in panel, L4+): cap rope tip at wall_c0-1 when rope rows intersect;
  jam horizontal block moves; vertical move canceled if a moved block would overlap (guess).
- GOAL: picture groups below divider (hub 2x2: color 6=engine rope, else anchor color's
  chain). Holder CONTENTS (cars by c0 / chain occupants top-down) must == pictured
  sequence — PURE ORDER, no slot positions, skewering irrelevant (t#137). Tracker
  hollows picture block k iff k-th content matches, LIVE (un-hollows too). Level up
  the instant ALL groups match exactly. DUPLICATE colors exist (L4): blocks = list.
- Budget bar: divider row, rightmost k 2->3, k=(T-1)//3, T=actions since entry (~193 cap).
- Harness: run's 1st transition skipped in rolls (sync via ENTRY_GRID compare in predict).
- Workflow per level: planner.py (abstract BFS over (top,L,blocks) via wm.abstract_step,
  reads events.jsonl) -> verify plan via wm.predict -> commit. Full-grid run_bfs too slow.

## L5/L6 mechanics (all in model, 293/293 green)
- SECOND CRANE (f-box on horizontal track rows4-5): hub-CLICK toggles active holder
  (interior 0=active/4=inactive; rope values +1 when inactive). Actions are GLOBAL dirs:
  1=up 2=down 3=left 4=right — engine: 1/2 track, 3/4 rope; crane: 3/4 track, 1/2 chain.
- Crane physics mirror engine's (riders/plow/jam/park/hooks, floor=chain_r0+2, rmax=pr1-4).
- CROSS-HOLD: blocks riding my rope are PINNED vertically (crane can't drag them off;
  block moving vertically onto/through my rope band JAMS — release-by-jam parking!).
  Blocks on a chain pinned horizontally. Crane transit SWEEPS parked blocks at rows<=tip
  (chain skewers/pushes them) — park deep or route around!
- a7 = TOTAL no-op (no tick). Clicks free. BUDGET: bar = floor(T*16/49) = T/196 of 64
  cells; T = ticking actions since level entry. Budget 196/level.
- Planner: planner.py (flat BFS) -> planner2.py (staged, per-level hand subgoals, action
  modes engine/crane, auto-skip satisfied stages).

## Current level: 6 (of 8)
- No wall. Engine top=26 L=7; crane cc0=29 KL=7. Blocks: 8@(21,24), 9@(21,30),
  9@(27,24), 8@(27,30), e@(33,36) — ONE e only!
- Goal: engine cars [9,e,9] AND crane occupants [8,e,8] — ropes must CROSS at the
  shared e (rides both). Assembly: pack cars against cmax; place e before rope arrives
  (band-jam ordering); chain picks 8s around e.

## Older level notes: 4
- Engine mid-track (top=24 entry); WALL 6x6 at rows24-29 cols29-34 splits the row.
- Three 9-blocks riding (cars [9,9,9]), three 8-blocks right of wall at rows25-28.
- Goal: cars [8,9,8] (extra blocks parked off-rope). Plan (verified, 17 steps):
  [1,3,4,4,4,1,4,2,4,2,3,3,3,2,4,4,4] -> level_up at step 17.

## Watch / open
- Wall vertical-cancel rule is a GUESS (plan uses vertical moves near wall rows).
- a7 semantics unknown. Bar-full consequence unknown (stay well under).
