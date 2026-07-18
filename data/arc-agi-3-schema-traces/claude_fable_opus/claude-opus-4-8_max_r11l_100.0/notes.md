# Notes — living scratchpad

## THE GAME — "centroid docking".  ALL MECHANICS CONFIRMED (levels 0 & 1); encoded in world_model_v5.py
Only action 6 (click) is ever legal.  Backtest green on every transition so far.

- NODE = filled Manhattan diamond r<=2 (12 cells) of a BODY colour + a CENTRE DOT.
  * BODY colour = SELECTION, not identity:  BLACK(0) = the ONE globally selected node,
    GREEN(3) = all others.  (Proved on L0: clicking the green node swapped the two bodies'
    colours, 12 cells 0->3 and 12 cells 3->0, and nothing moved.)
  * CENTRE-DOT colour = the node's SYSTEM id.  (L0: all 15.  L1: systems 12 and 15.)
- Each SYSTEM s has its own nodes + CENTROID MARKER + TARGET RING, all drawn in colour s:
  * CENTROID MARKER = octagon (Chebyshev<=2 minus 4 corners) + DOT(6) at its centre, drawn at the
    FLOOR-AVERAGE of that system's node centres: ((sum x)//n, (sum y)//n).
  * TARGET RING = static dashed ring: Manhattan==4 minus the 4 axis tips (12 cells in 4 disjoint
    arcs).  A ring whose system has DOCKED renders BLACK(0) — the "locked in" indicator.
  * *** FROM L3: octagons and rings are multi-coloured PIE CHARTS. *** Each system's octagon has a
    fixed colour signature (e.g. {12,14,15}); its target is the ring with the SAME COLOUR SET.
    L3 has 8 rings for 3 systems => 5 DECOYS.  Match by colour set (unambiguous).  Do NOT use the
    old "ring = leftover cells of the system colour" logic — it gives totally wrong targets.
    Detect rings: 12 cells at Manhattan 4 (minus tips), none of them land/sea, the 4 TIPS are
    terrain, not a solid blob.  NB colour 10 doubles as terrain AND a ring-sector colour.
    An octagon centre = a DOT(6) whose 20 sector cells are all signature colours (L3's ring at
    (20,8) has six DOT-coloured cells — surrounded by land, correctly excluded).
  * *** DOCKING HAS A SNAP RADIUS — it is NOT exact-centre. *** L2 sys14 levelled up with centroid
    (55,48) vs ring (55,53), Manhattan 5, and an exact match was arithmetically impossible there.
    Every non-docked state in all history is >=12 away, so the true radius is in [5,11]; model uses
    <=5 (the observed lower bound — safe, since any larger radius also docks).  When planning, keep
    intermediate centroids >11 from their ring so the ambiguity can never bite.
- SPOKES = colour-1 lines drawn FROM THE CENTROID OUTWARD to each of its own nodes.
  *** EXACT RASTERISATION (matters — it decides spoke legality): n=max(|dx|,|dy|); cell i =
  start + round(delta*i/n) where .5 TIES ROUND AWAY FROM THE START (round the OFFSET half away
  from zero).  NOT plain round-half-up: an x-tie 19.5 went UP to 20 on L0 (dx>0) but a y-tie
  13.5 went DOWN to 13 on L1 (dy<0). ***
- TERRAIN: land = the colour the nodes sit on (5).  Everything else (sea 2, and colour 10 on L1)
  is NOT placeable.
- CLICK within Manhattan<=2 of a node's centre => SELECT it (turns black; old one turns green).
  Nothing moves.
- CLICK elsewhere => the SELECTED node teleports there, but ONLY IF THE MOVE IS LEGAL.  Otherwise
  nothing happens (bar still ticks).  *** LEGALITY IS BIGGER THAN THE NODE BODY: ***
    (a) the node's whole 13-cell diamond must be on land   [proved: L0 click (45,6) no-op]
    (b) the resulting CENTROID OCTAGON (21 cells) must be on land
    (c) the resulting SPOKES must be on land                [(b)+(c) proved: L1 click (37,31)
        no-op — body was fully on land but the new octagon/spokes hit colour-10]
    (d) *** TRAVEL PATH: REFUTED. *** (8,21)->(41,31) moved even though the straight path crosses
        colour-10.  Nodes TELEPORT; only the redrawn cells (body/octagon/spokes) must be on land.
- Column x=0 is a PROGRESS BAR, not a click counter:
      cells_filled = round(64 * clicks / 60)      <-- CLICK BUDGET IS 60 PER LEVEL (bar has 64 cells)
  M=60 is the UNIQUE budget fitting all history.  L1's "+2" at click 8 was pure rounding
  (8*64/60 = 8.53 -> 9).  *** DOCKING COSTS NOTHING *** — every "docking surcharge / upkeep /
  lagged charge" theory was an artifact of this rounding and is REFUTED.  Model is stateless again
  (invert the bar to get the click count).  Budget 60/level is ample (L2 solved in 22).
- z-order: terrain < spokes < rings < NODES < OCTAGONS.  *** The centroid OCTAGON is drawn ON TOP
  of node bodies *** (proved: octagon at (41,33) overdrew the node at (41,31)).  So a node's
  diamond can be PARTLY HIDDEN by an octagon -> _find_nodes must accept "body colour OR under an
  octagon" for each diamond cell (and require >=6 genuinely visible body cells, else a phantom
  node is 'found' inside every octagon).  A node whose centre is within Chebyshev 2 of its own
  centroid gets heavily occluded — AVOID that in plans (keep nodes >=5 from every centroid).
- GOAL: EVERY system's centroid marker docks on its own ring centre => level_up.

## LEVEL 4 — new mechanic: EMPTY octagons + COLOUR PICKUPS
- L4 octagons have NO DOT centre -> detect octagons BY SHAPE (21 cells, none terrain(2/5/10)).
  A node overlapping an octagon creates a PHANTOM octagon shape next to the real one; on L0-L3 the
  real one has a DOT centre, so prefer dotted candidates and drop shapes that shadow them.
- Node centre-dot colour is NOT a system id on L4 (all 5 nodes are colour 4).  Get the systems by
  solving the PARTITION: each octagon centre == floor-average of its group of nodes.
- A real node always has >=6 body cells OUTSIDE every octagon; that test kills the false "node"
  that an all-black octagon's inner diamond otherwise produces.
- L4 systems: A = (25,35)+(43,34) -> centroid (34,34);  B = (41,47)+(34,55)+(52,55) -> (42,52).
  Both octagons are ALL BLACK = an EMPTY pie chart.
- 4 PICKUPS (octagon-shaped, static, half colour / half black):
     (14,40)=9 LEFT   (33,19)=8 RIGHT   (20,53)=14 LEFT   (56,43)=11 RIGHT
  Combining 9-left+8-right gives exactly ring (13,28); 14-left+11-right gives exactly ring (48,9).
  *** ABSORPTION CONFIRMED: driving a system's CENTROID onto a pickup permanently paints that
  pickup's COLOURED cells into the octagon's pie chart (the black half is overwritten), and the
  PICKUP IS CONSUMED — its 21 cells revert to terrain.  So pickups must be read from the LIVE grid
  (= octagons that are not any system's centroid), never from the static entry layout.
  Once the chart's colour set matches a ring's, dock there (snap radius as usual). ***
  *** CAPTURE = the two octagons OVERLAP (Chebyshev distance of centres <= 4) — NOT exact centre.
  Proved: absorbed at Chebyshev 4 (centroid (52,41), pickup (56,43)); not at Chebyshev 9.
  So an intermediate centroid can EAT A PICKUP IN PASSING — plans must keep centroids Chebyshev>4
  from any pickup they don't want to collect. ***
  ALSO: keep NODE centres >=6 from every pickup — a node overlapping a pickup's octagon corrupts
  the shape-based octagon detection and the node parse.
  Decoy rings: (15,15)={9,12}, (57,18)={7,6}, (53,28)={14}.

## LEVEL 5 (final) — 2 systems, 9 pickups, 3 rings; each ring needs THREE colours
- sysA (3 nodes, centroid (12,16)) collects 14@(34,17), 9@(11,33), 15@(16,45) -> ring (51,12).
- sysB (2 nodes, centroid (49,50)) collects 6@(45,30), 11@(32,44), 10@(25,55) -> ring (11,55).
- Ring (29,31) needs colour 7 and NO pickup has 7 => decoy.  Pickups 8/12/13 unused.
- The pickups' coloured sectors tile each ring's pie chart exactly (overlaps land only on the
  ring's 4 MISSING TIPS, so order of absorption doesn't matter).
- Since capture is by OVERLAP and pickups are CONSUMED, eating a wrong colour is UNRECOVERABLE —
  route every centroid Chebyshev>4 from pickups it must not take.

## RENDER LAYERING (subtle!)
A static cell (ring / pickup) whose colour is one of the engine's MAP colours (2 sea, 5 land,
10 obstacle) is drawn in the MAP layer, i.e. UNDER the spokes; any other colour is an object drawn
OVER them.  Proved on L5: one spoke crossed ring (11,55) at (8,54)=colour 11 (the RING won) and at
(8,56)=colour 10 (the SPOKE won).  This is a FIXED palette fact — colour 10 counts as map even on
L5 where it is only ~10 cells and is NOT the level's derived terrain.
Also: an UNDOCKED ring draws BELOW the nodes (a selected black node overdrew ring cells on L2/L4/L5),
but a DOCKED ring (rendered BLACK) draws ABOVE them (it overdrew a green node body at (50,9)/(49,10)).
FULL ORDER: terrain -> map-coloured statics -> spokes -> undocked rings & pickups -> nodes ->
            docked rings -> octagons.
NB a docked ring therefore OCCLUDES node body cells — the node parser must tolerate that.

## Parser rules that matter (hard-won)
- TERRAIN colours are derived PER LEVEL = colours whose largest 4-connected component >= 50.
  (L3 sea's largest comp is 93 => terrain; L5's black octagon cells are 33 and its colour-10 ring
  sectors are 7 => NOT terrain.  A fixed terrain list breaks: colour 10 is obstacle on L1-L3 but a
  sector colour on L5.)
- System partition: enumerate NODE PARTITIONS (Bell(5)=52) and keep the one whose group
  floor-averages are all octagon centres AND whose SPOKES explain every colour-1 cell.
- Keep node centres CHEBYSHEV >=5 from every octagon (own centroid, other centroid, pickups) —
  a node overlapping an octagon makes a PHANTOM octagon and the parse loses the node.  L4/L5
  octagons have no DOT centre, so the dotted-candidate filter can't save you there.

## Ruled out (do not re-litigate)
"nearest node to the click moves" (REFUTED), farthest-node, round-robin, angular/same-side,
"black is a fixed identity".

## Framework gotchas
- run_backtest's rollout SKIPS transition 0 without advancing state (tools.py:954) => keep the
  model STATELESS (step()); everything is readable from the grid.
- is_goal() is called with state=None at install time -> must tolerate None.

## Level 2+ : the terrain is a MAZE — plan with a land-distance beam search
The obstacle (colour 10) regions split the map into regions joined by narrow corridors.  Because a
SPOKE must lie on land, the centroid cannot "see" two nodes that sit in regions whose corridors run
opposite ways => you CANNOT just move each node once to its final spot.  The cluster has to MIGRATE
region by region (nodes teleport, but the octagon+spokes must stay legal at EVERY step).
Working method (solved L2 in 22 clicks):
  1. BFS the land to get D[cell] = land-distance from the ring (respects the maze topology).
  2. Beam search over configs (state = tuple of that system's node positions).  Successors: move
     one node to a candidate legal cell; keep only configs where octagon+spokes are on land, node
     centres are >=5 apart and >=5 from the centroid.  Heuristic h = sum(D[node]) + D[centroid].
  3. At each state test a 1-move EXACT-SUM completion (q = S - (sum - p_i) for each valid S).
  4. Cross-system: node centres of DIFFERENT systems must also be >=5 apart, and every MOVE target
     must be >=3 from EVERY node (else the click SELECTS).  Easiest: finish one system first, then
     plan the other with those nodes fixed.
  5. Multi-hop on the SAME node in a row is cheap (it stays selected => 1 click per extra hop).

## Planning recipe (works; use it every level)
1. run_python: load the entry grid from events.jsonl; build the land mask (terrain==land colour)
   and enumerate LEGAL placements = cells whose whole 13-cell diamond is land.
2. For each system with n nodes and ring R: need floor(sum/n) == R, i.e.
   sum_x in {n*Rx .. n*Rx+n-1}, sum_y in {n*Ry .. n*Ry+n-1}.  Search legal tuples with that sum.
3. Keep all node centres pairwise Manhattan >= 5 (no overlap; unambiguous selects) and make every
   MOVE target >= 3 from every current node centre (else the click SELECTS instead of moving).
4. Cost: 2 clicks per node moved (select + move); 1 for the already-selected node.
5. Simulate the whole click list by importing world_model_v5.py in run_python before committing.

## Level 1 (current): 2 systems
sys12: 3 nodes (17,6)[sel],(49,9),(8,21) -> ring (40,51).  sys15: 2 nodes (45,35),(54,48) -> ring (57,18).
Committed 9-click plan (simulated: both dock, level_up=True):
(37,31) | (49,9)->(39,61) | (8,21)->(44,61) | (45,35)->(53,8) | (54,48)->(61,28)
