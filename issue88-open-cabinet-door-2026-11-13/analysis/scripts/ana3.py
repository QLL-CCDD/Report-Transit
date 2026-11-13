import json, os, statistics as S, collections as C
B = "/dev/shm/e10-door88/diag-seeds"
def med(v): return round(S.median(v), 1) if v else None
def q(v,p): v=sorted(v); return round(v[min(len(v)-1,int(p*len(v)))],1) if v else None
names = ["start","s1cap-2.5M","s1cap-5.7M","s2cap-2.5M","s2cap-5.7M","s2unc-2.5M","s2unc-5.7M","s2unc-10.3M","s3cap-2.5M","s3cap-5.7M","s3cap-15M","s3unc-2.5M","s3unc-5.8M"]
for n in names:
    for suf in ("", "-sto"):
        p = f"{B}/{n}{suf}/phases.json"
        if not os.path.exists(p): print(n+suf, "missing"); continue
        eps = [e for e in json.load(open(p))["episodes"] if e["type"] == "pull0"]
        ok = [e for e in eps if e["success"]]; bad = [e for e in eps if not e["success"]]
        def rel(e): return next((r for r in e["series"] if r[2] >= 0.06), None)
        closed_ok = [e for e in ok if e["series"][0][1] > -0.5]
        nopull = sum(1 for e in bad if rel(e) and rel(e)[1] > -0.5)
        regrasp = sum(1 for e in eps if sum(1 for a,b in zip(e["series"],e["series"][1:]) if a[2]>=0.06 and b[2]<0.03)>0)
        stuck = C.Counter(e.get("stuck") for e in bad)
        secs = [e["seconds"] for e in ok]
        print(f"{n+suf:16s} ok {len(ok)}/{len(eps)} = {len(ok)/len(eps):.2f} | ok secs med {med(secs)} p90 {q(secs,.9)} >10s {sum(s>10 for s in secs)} "
              f"| fails: released w/o pulling {nopull}/{len(bad)}, stuck {dict(stuck.most_common(3))}")
