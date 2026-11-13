import json, os, statistics as S
B = "/dev/shm/e10-door88/diag-seeds"
def med(v): return round(S.median(v), 2) if v else None
print("name | ok/n | closed ok | pulled>=0.5deg before release (closed ok) | closed fail: release deg med, hold s med, end handle cm med, end door med, timeout")
for name in sorted(os.listdir(B)):
    p = f"{B}/{name}/phases.json"
    if not os.path.exists(p): continue
    eps = [e for e in json.load(open(p))["episodes"] if e["type"] == "pull0"]
    def rel(e): return next((r for r in e["series"] if r[2] >= 0.06), None)
    closed = [e for e in eps if e["series"][0][1] > -0.5]
    okc = [e for e in closed if e["success"]]; fc = [e for e in closed if not e["success"]]
    pulled = sum(1 for e in okc if rel(e) and rel(e)[1] <= -0.5)
    pulled_f = sum(1 for e in fc if rel(e) and rel(e)[1] <= -0.5)
    noRel = sum(1 for e in fc if rel(e) is None)
    rd = [rel(e)[1] for e in fc if rel(e)]; rt = [rel(e)[0] - e["series"][0][0] for e in fc if rel(e)]
    rt_ok = [rel(e)[0] - e["series"][0][0] for e in okc if rel(e)]
    endh = [e["series"][-1][6] * 100 for e in fc]; endd = [e["series"][-1][1] for e in fc]
    to = sum(1 for e in fc if not e["fail"])
    print(f"{name:12s} {sum(e['success'] for e in eps)}/{len(eps)} | {len(okc)}/{len(closed)} | {pulled}/{len(okc)} (fails that pulled: {pulled_f}/{len(fc)}, never released {noRel}) "
          f"| rel deg {med(rd)} rel s {med(rt)} (ok {med(rt_ok)}) endH {med(endh)}cm endDoor {med(endd)} timeout {to}/{len(fc)} | ok secs {med([e['seconds'] for e in okc])}")
