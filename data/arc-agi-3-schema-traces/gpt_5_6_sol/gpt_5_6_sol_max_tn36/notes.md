# ARC3 game notes

## Confirmed mechanics/opcodes
- action6 normally consumes a rightmost color9 meter cell→3. Late maze levels L5–L6 advance it every second click (odd free, even paid; stateful parity).
- T strokes toggle 1↔5; 69-pixel wired color9 circle RUNs six columns.
- 0/4 stay, 1 L,2 R,3 D,33 U; 10/11 R2,12/13 L2,34 L.
- 5 CW,6/16 CCW,7 half-turn,8 enlarge,9 shrink; 14 recolor9,15 recolor8,63 recolor15.
- Goal matches plug/socket position, scale, orientation,color. Color6 walls.
- L5: motion resets unless FINAL cell is goal or a persistent checker save pad. Parking hides pad; leaving restores it from ENTRY_GRID. Model exact.
- Cleared L0–L5; full-history backtest green.

## Final L6
- Normal color11 UP plug at logical (2,6); matching UP socket target (2,1).
- Direct U×5 failed: on entering row3,c2, mirrored color12/13/14 emitters at (1,3),(6,3) activate a c/d beam across interior c2..c5; plug is destroyed and run resets.
- Three checker save pads: (5,5),(0,2),(5,1). Likely L5 save mechanic recurs.
- Endpoint probe [L,U×4,L] also destroyed plug when it entered left emitter c1,r3; no geometric crossing is safe.
- All recolors (15/9/8) are destroyed in the beam; opcode9 cannot shrink scale1; opcode32 is a true no-op.
- Timed-beam route succeeded: bottom checkpoint (5,5), then U×4 crossed (enter row3 cmd2, exit cmd3) and saved at top pad (5,1). Hidden checker under start modeled exactly; full backtest green. Final socket at (2,1) is flanked by walls, so route below it with [D,L2,L,U,0,0]; scratch simulation predicts level_up+win.
- Program centers x=[34,39,44,49,54,59], bits y=[33,36,39,42,45,48], RUN=(57,58).
- Model detects emitter beam as interior-row obstacles; right-program parsing restricted below y32.
