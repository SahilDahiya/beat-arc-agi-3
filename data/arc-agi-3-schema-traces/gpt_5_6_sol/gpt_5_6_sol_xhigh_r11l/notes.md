# Notes — ARC3 centroid constellation game

## Confirmed mechanics/model
- Ink constellations have endpoint diamonds, centroid-to-endpoint Bresenham spokes, a floor-centroid disk/stamp, and a matching hollow ring.
- One endpoint is black-selected. Clicking a green endpoint center transfers selection; any other click attempts to relocate the black endpoint.
- The full resulting constellation must fit color5/foreground ring or piece terrain; invalid relocation is a geometry no-op but still spends the clock.
- Uniform/composite targets solve within Chebyshev 2. Target rings overlay spokes; solved rings become black, then dynamic endpoints/stamps overlay them.
- Left-edge clock spends 1 cell/click, with one extra only on click 8. Logical endpoint state is threaded when overlaps hide centers.
- Assembly levels use neutral-center4 endpoints and movable 21-cell black stamps. Overlapping a static half-stamp footprint absorbs its nonzero colors and removes the source; black is transparent between overlapping stamps.
- A complete no-black assembly stamp maps exactly to one ring pattern. It solves when its center enters the ring interior (Chebyshev 2) OR its 21-cell footprint touches a matching ring cell; L5 confirmed off-center contact at centroid(47,15) with target(51,12).
- Backtest exact on all 83 checkable transitions.

## L5 current/final plan
- g0 endpoints are (61,14),(58,12 black),(22,19), centroid(47,15). It has assembled e+9+f and the top ring is already solved by stamp/ring contact; no recentering is needed.
- g1 has absorbed 6,b,a; endpoints are green(3,55) and black(50,57), centroid(26,56). The a/b tab conflict creates a persistent transparent connector seam (confirmed after selection); the stateful seam model makes all 88 checks exact.
- Move the selected endpoint to (19,55), reaching centroid(11,55). The completed a+b+6 stamp then solves the lower ring and wins; decoy pieces 8,d,c stay untouched.
