# Notes — living scratchpad

## L5 PROGRESS (as of t1005, bar 23/64):
- MECHANICS ALL ENCODED (backtest green minus known phase-noise class):
  portal net: (18,48) slot + nodes 67->(32,52), 9a->(34,58), cb->(4,4),
  d8->NULL; quad-dial cycles 67->d8->cb->9a; 6-press = ride(swap)+flip other
  nodes+ROTOR rotate (90CW around (9.5,33.5), knob invariant, arm cells园
  under cage render 8); e-on-ARM/V-arm = penalty; e-on-ring/knob = OK.
  Conveyor: 3 bands, logical runs +2/press, fuse at east-edge-21, dock
  removed+fresh@6-11 on press; runs/docks are e-floors. Cage: 8-ring on the
  0-track (center-2x2 rule), driven by port-blocks (e at legend ports N/W/E/S
  lights f/c/e/a block; press = 4-step drive); berths: shaft-top/top-channel
  x18/22/26/east-shaft/home/home-W/S. CAGE RENDERS OVER e (x>=16 8s).
  8-block: DEAD in every tested state incl. e-in-cage-mouth + arm-grip.
  Items: 8-item -> 8-block; ba/8877 -> quad. e can enter cage-mouth via
  ring->H-arm walk (rotor V climb from 2col, rotate on ring, walk east).
- UNSOLVED: entry to top complex (32,4)-(49,11) w/ goal bb(46,6). NOTHING
  touches it: cage max reach x18-25 rows 6-13 / x26-33; no 4th node.
  Untested: clicking machine pieces (knob/ring/cage/arm), full-state
  hand-rolled simulator search.
- e now at (18,34) cage-mouth (half under wall). Route back: west along arm,
  ring, V-climb down (needs rotor V), 2col, conveyor east, home region.

## L5 (old survey): NEW BOARD — divider x40-41, right panel x42+. Features seen:
- duals: cb/bc at (4,4); 76/67 at (18,47); 9a/a9 at (34,58)?; 67/76 at (33,52)?
- e starts ~(28,52) in a 2-region rows 47-53 x18-31.
- big 0-pipe x20-33 rows 8-38 w/ 8-ring box (22-29,30-37); c-sea x0-19 rows
  30-37 w/ embedded 8-ring (8-11,32-35) holding cc; item clusters ('ba/8877'
  at (6,18)-(9,19), '88' at (34,47), '2210/220f/109a/0ca90e' rows 56-61 x32-37).
- right panel: b-flask (rows 5-11), bb-in-2box at (46,6); 6-hex rows 23-27;
  marker diagram rows 30-42 (c/e/f/a singles). 1-runs staircase rows 54-59.
- Clock row63 empty. Model has NO L5 tables yet — learn from probes.

## L4 — CLEARED (recipe): pocket exit = tow column D3(claw x2)+R3(bottom run)
to x22-25 rows 22-33; e climbs, dismount 2-box; column home via L3,U3,R3;
e up to dual (24,6), press 6 = ride to shaft; column L3,D3 to x10 rows 22-33;
e climbs into f-box, consume item = flask-f (rows 12-16, slots checker
(26,46,4x8) H/F + pool (14,50,10x4) F/H); press 9 (col F), descend shaft,
deploys to fuse rail w=8, cross east, press f, down checker, b x5 (dock reset
+ run to x22-27), west along run, press f (pool F), pool west, b at (10,50).

## L4 STATE OF KNOWLEDGE (historical)
- e cage: box(30,34,4x4)+door(26,34,4x4 flask-9 H/F)+segment(26,30,4x4). ALL exits 4s. PROVEN no escape via (moves x flask9 x glyph x cart) joint-BFS.
- CLAW (was "glyph"; t409-426, backtest 425/425 green): the 8-sprite is a
  C-CLAMP. OPEN 8x8 (30 cells, mouth on RIGHT rel-rows2-5, zigzag ARM on left);
  CLOSED 8x6 (28 cells, jaws gripping the column-tab T-knob = chain link).
  sq8 (48,34,9x3): CLOSES claw iff knob crossbar (c col at rel-x+6 rows+2..+5)
  is in the mouth (cost5). While closed: sq8=no-op cost5 (NO reopen found yet);
  L/R = TOW whole train (claw+tab+column, 4-step; c-cells only land on {0,4};
  claw rolls over anything w/ gcover); U/D refused (arm rule). Away from knob:
  sq8 = dead button cost0. Column positions: x14-17 / x18-21 / x22-25(home).
  Pipe top run = rows14-17 x3-20 (revealed by tow). Refused presses cost 5.
  D-pad = code blocks (L=43,28; U=48,28; R=53,28; D=58,28); moves 4-step; ARM
  (rows w/ rel-x<3 cells, excl. jaw rel-x7) must stay in pipe (left-col x3-6
  y14-29, top x3-20 y14-17, bottom x3-18 y26-29). Open-anchor reach:
  (2,12..24),(6,12),(10,12),(14,12),(6,24),(10,24),(14,24).
  Flask battery at all 3 tow positions: quiet (no position-gated effects).
- flask-9: door(26,34)H/F <-> col(10,38)F/H. e-in-slot press = +104 penalty.
- flask-6: portal duals (24,6)<->(10,34) cellswap (e-ride possible but e can't reach).
- flask-b: 1-cart y54-55 slides +2 from x14; docks x24-29 (turns c); press-at-dock = reset x14.
- 8-square (48,34,9x3): INERT in all tested states (pristine, docks, door states, encircled).
- f-item-box (10,18,4x4, flask-f pic): island (0-walls above, 4s around). Glyph ring can encircle its stem (at (6,12)) - no effect w/ any button.
- Right stack x26-29: cage(y30-37) / gap y38-43 / RAIL(5s y44-45 x14-29) / half-f col y46-53 / cart track y54-55. Left corridor x10-13: dual-box(34-37)/9col(38-41)/2s(42-45)/gap 46-49/b-box(50-53 b at 10,50)/f-block x14-23 y50-53.
- DEPLOY (2-block 54,20-59,25; found t427): L3-style pendulum on the 5-rail
  y44-45 x14-29: w 0..8 (+2/side/press, reverse at ends), w=8 FUSES all c;
  reservoir is ABSTRACT (w=0: nothing renders anywhere). Cost 10/press.
- L3 SOLUTION PATTERN (traced t200-270): pendulum = 2-band ferry; each band
  fuses c when full -> successive e-bridges; bands fill AROUND e (e-holes).
  L3 e ALSO started pocketed; its tube band ran THROUGH the pocket rows.
- POCKET EXIT RULED OUT (real-tested): all 15 wall faces pushed; flask-6 and
  flask-9 pressed with e on EVERY pocket 2x2 (no hidden cellswap rides);
  e-in-door x all buttons; vertical tows (D/U refused at home+leftmost);
  deploy overflow (reverses instead); claw mouth can't reach e (arm-locked);
  all left-panel clicks inert; b-bowl = same flask-b button; dock=slide-reset
  (t321-322); joint model-BFS closed at 3600 states.
- **POCKET SOLVED (t645-656)!** Tow has NO solid-rule — ONLY the arm rule
  (arm cells rel-x<=4 in arm rows must land in pipe or x<3); the train rolls
  over EVERYTHING with gcover (t644 pushed column over the f-box). Tow space:
  claw ax 2..14 on top run (column x10..22 rows 10-21), D-tows at ax=2 down
  the pipe-left (column x10-13 sinks rows 14-25/18-29/22-33), then R along
  the BOTTOM run rows 26-29 (claw ay=25, ax 2..14 => column x10..22-25 at
  rows 22-33). Column parked x22-25 rows 22-33 = LADDER flush against the
  pocket west wall: e exits segment (26,30) -> (24,30), climbs. e IS OUT.
- ENDGAME plan: f-box (10-13,18-21) entry consumes f-item -> flask-f; shaft
  dual (10,34) ride (press 6) after 9col=F (door H); rail fused w=8; checker
  H->F via flask-f; run at x22-27; pool F (juggle flask-f with e in run);
  b-box (12,50)->(10,50) = LEVEL UP. Clock: death at cum>2560 (64 bars);
  RESET refunds to 0 but loses all machine state.
- UNVERIFIED: e-on-column tow semantics (ride? refuse? hole?). TEST before
  relying. Claw at (14,25) closed; tab crossbar x20 r26-29, stem x21 r27-28
  (e can stand on tab but cannot cross the claw body).

## GENERAL RULES (confirmed L0+L1, encoded in model)
- e(14) = 2x2 SWIMMER: 1/2/3/4=U/D/L/R by 2. Enter 2x2 iff UNIFORM color not in {0,3,4,5}. Mixed/empty blocks (except item-boxes). Vacated := carried color; carried := entered color (material self-heals behind e).
- GOAL: move e ONTO b (uniform 11 2x2) => level_up (L0 cleared).
- FLASK BUTTONS (click on fill, right panel): swap that color's slot-pairs' FILL-STATES (full / half=odd-(x+y)-checker / empty). Unequal sizes re-render. Reversible toggles. Multiple pairs per flask fire together. Button active only if clicked cell shows flask color.
- ITEM-BOX (L1): 4x4 2-framed box holding mini-flask-c picture; e may push into its mixed {2,c} 2x2s: item consumed, full flask-c button materializes on right panel; e inside box; carried:=2.
- PENALTY: clicking a flask while e inside one of its slots: NO swap, +20 units.
- Clock row63: cum +1/action, +2/effective pour, +20 penalty; bar=ceil(cum/den), den=LEVEL+2 (L0:2, L1:3 confirmed). Level-up resets bar; RESET refunds.
- Other clicks: no-ops. Framework: transition #0 skipped in threading; cum recalibrates from bar when desynced.

## LEVEL 1 (current)
- A' 4x4 (20,12)-(23,15), b=top-right (22,12). B' (4,28)-(7,31). e collected flask-8 from item-box (16,52); e now in that box.
- Upper strip y24-27: 2(x8-11)|8(x12-19)|d(x20-23)|8(x24-31)|2(x32-35). GAP x20-23 y16-23 under A'.
- Flasks: 6@y20-24 (7-runs horiz(y40-43 x8-15,x20-27) <-> vertical x16-19 (y32-39,y44-51)); 9@y38-42 (block(8,28,4x4) <-> column(4,32,4x8)); 8@y29-33 NEW (pairs GUESS: left-8(12,24,8x4)<->gap(20,16,4x8); right-8(24,24,8x4)<->(20,28,4x8)).
- Flask geometry: stem x49-55 (3 rows), body x46-58 (2 rows).
- ROUTE (committing): up x4 (bottom-7), into 6-block, flask-6 (horiz), left x5 to 2-cap, up x5 (column solid), B', flask-9 (block solid), right+up x3, right x6 to d, FLASK-8 (fills gap!), up x4 gap, up x2 A', right onto b. ~36 actions, bar ends ~42/64.

## Current state: 7s vertical, 9-column solid/block half, flask-8 collected.

## L5 ENDGAME MASTER PLAN (locked 2026-07-18, pivot@(29.5,37.5) knob(29,37), arm H, e@S-port, dial=9a, bar~12/64 den80)
GOAL: bb 2x2 at (46,6)-(47,7) inside top complex (x32-49 rows 4-11; x40-41 rows 4-5&8-9 are 0s; bridges rows 6-7 & 10-11).
ROUTE (verified vs ENTRY: all 9 knob-dests in {0,8}; walk cells 2s; ride symmetry precedented seq3252/3500/3552):
 1. e [1][1] S-port->node(34,58)->N-port(34,56); click (50,32) N-tow x4 -> pivot (29.5,21.5)   [knob 29,37->29,21]
 2. e [2][3] ->W-port(32,58); click (46,36) W-tow x2 -> pivot (21.5,21.5)
 3. e [4][1] ->N-port; click (50,32) N-tow x3 -> pivot (21.5,9.5); arm stays H = x12-31 rows 8-11 (BRIDGE), ring (19,7)-(24,12), knob (21,9)
 4. e [2] onto node(34,58); 6-hex (52,25): ride ->slot(18,48); rotor H->V (arm x20-23 rows 0-19, harmless)
 5. quad (49,46) x3: dial 9a->67->d8->cb (quads don't rotate rotor; e sits on slot, recolor-under-e may mispredict = OK)
 6. 6-hex (52,25): ride slot->(4,4) cb node; rotor V->H = BRIDGE RESTORED
 7. walk: [2,2] (4,4)->(4,8); [4]x13 ->(30,8) (over room 2s, arm c x12-18, ring 8s x19-24 incl knob, arm c x25-31);
    [4] ->(32,8) COMPLEX; [4]x3 ->(38,8); [2] ->(38,10); [4]x4 ->(46,10); [1] ->(46,8); [1] ->(46,6)=bb LEVEL_UP
NOTES: tows sweep arm over 4s LEGALLY (proven: E/S-tows swept arm across entry-4s at x33-39 rows 32-39). Only knob-dest 2x2 must be entry-{0,8,12}.
Each tow/press click MISPREDICTS (grip untracked in model) -> commit clicks LAST in each batch, one click per commit.
DO NOT RESET (would undo grip+tows? unknown - avoid). Budget: ~270 adds, cum ~1230 << 5120 OK.
