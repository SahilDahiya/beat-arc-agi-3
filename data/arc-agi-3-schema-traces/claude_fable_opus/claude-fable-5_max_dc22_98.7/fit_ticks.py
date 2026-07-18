import json
from itertools import product

acts = []
with open("events.jsonl") as f:
    for line in f:
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("kind") == "action_taken":
            acts.append(ev)

def ticks(g): return sum(1 for v in g[63] if v == 3)
def find_e(g):
    for yy in range(64):
        for xx in range(64):
            if g[yy][xx] == 14:
                return xx, yy

seq = []  # (cat, ticks, is_reset_boundary)
for i in range(271, len(acts)):
    ev = acts[i]
    if ev["action"] == 0:
        seq.append(("RESET", ticks(ev["grid"])))
        continue
    prev = acts[i-1]["grid"]; cur = ev["grid"]
    T = ticks(cur)
    a = ev["action"]
    non63 = sum(1 for y in range(63) for x in range(64) if prev[y][x] != cur[y][x])
    if a != 6:
        cat = "move" if find_e(prev) != find_e(cur) else "blocked"
    else:
        xx, yy = ev["x"], ev["y"]
        if (43 <= xx <= 46 or 48 <= xx <= 51 or 53 <= xx <= 56 or 58 <= xx <= 61) and 28 <= yy <= 31:
            cat = "snake_ok" if non63 else "snake_blk"
        elif 46 <= xx <= 58 and 39 <= yy <= 43:
            cat = "flask9" if non63 else "pen"
        elif 47 <= xx <= 59 and 46 <= yy <= 50:
            cat = "flask6"
        elif 44 <= xx <= 50 and 19 <= yy <= 25:
            # cart dock/reset presses still count as flaskb
            cat = "flaskb"
        elif 48 <= xx <= 56 and 34 <= yy <= 36:
            cat = "sq8"
        else:
            cat = "blank"
    seq.append((cat, T))

sols = []
for D in range(30, 61):
    for move, blocked, pour, snok, snblk, sq, blank, pen in product(
            (5,),(5,6),(6,8,10,12),(3,4,5,6),(0,1,2,5),(0,1,2,5),(1,5),range(90,150,1)):
        cost = {"move":move,"blocked":blocked,"flaskb":pour,"flask9":pour,
                "flask6":pour,"snake_ok":snok,"snake_blk":snblk,"sq8":sq,
                "blank":blank,"pen":pen}
        S = 0; ok = True
        for item in seq:
            if item[0] == "RESET":
                S = 0
                continue
            cat, T = item
            S += cost[cat]
            if -(-S // D) != T:
                ok = False; break
        if ok:
            sols.append((D, move, blocked, pour, snok, snblk, sq, blank, pen))
print(len(sols), "solutions")
for s in sols[:10]:
    print("D=%d move=%d blocked=%d pour=%d sn_ok=%d sn_blk=%d sq8=%d blank=%d pen=%d" % s)
