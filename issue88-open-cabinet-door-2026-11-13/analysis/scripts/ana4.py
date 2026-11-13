import json, os
B = "/dev/shm/e10-door88/diag-seeds"
names = ["start","s1cap-2.5M","s1cap-5.7M","s2cap-2.5M","s2cap-5.7M","s2unc-2.5M","s2unc-5.7M","s2unc-10.3M","s3cap-2.5M","s3cap-5.7M","s3cap-15M","s3unc-2.5M","s3unc-5.8M"]
print("name  det(first ep per env)  sto(first ep)  | sto: closed-door starts ok, fails that released without pulling, ok that pulled first")
for n in names:
    row=[n]
    for suf in ("","-sto"):
        eps=[e for e in json.load(open(f"{B}/{n}{suf}/phases.json"))["episodes"] if e["type"]=="pull0"]
        first={}
        for e in sorted(eps,key=lambda e:e["episode"]):
            first.setdefault(e["env"],e)
        f=list(first.values()); ok=sum(e["success"] for e in f)
        row.append(f"{ok}/{len(f)}={ok/len(f):.2f}")
        if suf:
            rel=lambda e: next((r for r in e["series"] if r[2]>=0.06),None)
            bad=[e for e in f if not e["success"]]; good=[e for e in f if e["success"]]
            nop=sum(1 for e in bad if rel(e) and rel(e)[1]>-0.5)
            pulled=sum(1 for e in good if rel(e) and rel(e)[1]<=-0.5)
            # release time & door angle when released, fails vs oks
            rt=lambda L:[round(rel(e)[0],1) for e in L if rel(e)]
            import statistics as S
            md=lambda v: round(S.median(v),2) if v else None
            row.append(f"fails released w/o pulling {nop}/{len(bad)}; ok pulled first {pulled}/{len(good)}; release t med ok {md(rt(good))}s fail {md(rt(bad))}s; door at release ok {md([rel(e)[1] for e in good if rel(e)])} fail {md([rel(e)[1] for e in bad if rel(e)])}")
    print(" | ".join(row))
