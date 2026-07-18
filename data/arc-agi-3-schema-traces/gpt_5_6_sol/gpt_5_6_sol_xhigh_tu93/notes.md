# Notes

## Core
- Directions 1/2/3/4=U/D/L/R. 3x3 graph nodes, centers 6 px apart; connector2=edge, 5=wall, 0=free. Player 9/4; goal e.
- Bar: spent=round(64*n/budget). Budgets L0=50,L1=50,L2=35,L3=20,L4=50,L5=60,L6=30.

## Hazards
- 8/f stationary sentry: f marks front; it lunges/kills player ending on adjacent front node. It remains active even while visually covered by a walker. Direct body entry disables it; state tracks this persistently.
- c/f walkers advance after successful player moves, reverse only at terrain dead ends, and pass through walkers/goals/sentries. With 8/f: collinear (same or opposite facing) renders sentry above walker; perpendicular renders walker above sentry. Both persist and separate later. Covered terrain restores unless player disabled sentry.
- IMPORTANT hidden multiplicity: walkers can overlap in one rendered 3x3 block but remain separate and split later. World model is stateful and tracks each initial walker separately.
- Walkers pass through overlaps retaining direction; only terrain dead ends reverse them. Overlap sprite uses stable actor priority seeded by initial facing: up > right > down > left (then layout order). State retains all actors.

## Progress/current
- Levels0-3 cleared. L4: first move made two vertical walkers overlap at goal; second move split that pair while another perpendicular pair overlapped. This exposed hidden multiplicity. Stateful rewrite backtests all 70 transitions exactly.
- Levels0-7 cleared. d/f ambusher: inactive f arms to b from forward LOS to the player's new node; each later successful move advances it, then chooses the non-reverse exit nearest the player's PRE-MOVE node (reverse only at a dead end). This simultaneous-tick ordering explains the apparent diagonal tie turns. c/f renders above overlapping d/b and both persist. Budgets L6=30,L7=50,L8=50. Final L8 combines all hazards. Goal entry is not immediate: hazards resolve first, so the right-facing 8/f left of the goal lunges into and kills a player entering from the right. Must disable it via body before finishing. After death/reset, all 221 checkable transitions green.
