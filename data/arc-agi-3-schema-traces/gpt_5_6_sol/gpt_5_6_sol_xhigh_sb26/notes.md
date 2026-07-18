# ARC3 game notes

## Confirmed unified model
- Solid/hollow lower pieces select/transfer preserving shape; meter y53 spends rightmost 2→3. Action7 undo no refund; action5 submit.
- Trays are recursive lists: hollow token expands child tray; movable tokens occupy sockets; fixed solids are leaves/labels; repeated same-color tokens alias a child; matching labels handle same-tier children, nearest lower otherwise.
- Backtest green through 109 checkable transitions, levels 0-6.

## Final level 7: cyclic hierarchy
- Top shows TWO identical target rows: 8,b,c,9,e,f twice (12-leaf unrolling).
- Root/frame8 sockets: (22,26),(28,26),(34,26),(40,26).
- Child/frame9 sockets: (22,40),(28,40),(34,40),(40,40).
- Bottom solids f,b,c,8,9,e plus hollow tokens 8 and9.
- Intended cycle:
  - tray8 = [8,b,c, token9]
  - tray9 = [9,e,f, token8]
  - recursive unrolling from tray8 repeats 8,b,c,9,e,f.
- Model now parses multiple target rows, maps token8 back to root, and caps cyclic emission at displayed target length. Prior backtest remains green.
- Final submit predicts both level_up and win (CURRENT_LEVEL 7).
