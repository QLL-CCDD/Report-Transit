import json, collections as C, statistics as S
B = "/dev/shm/e10-door88/diag-seeds"
late = ["s1cap-5.7M","s2cap-5.7M","s2unc-10.3M","s3cap-15M","s3unc-5.8M","s3cap-5.7M","s2unc-5.7M"]
first = {}
for n in late:
    eps=[e for e in json.load(open(f"{B}/{n}/phases.json"))["episodes"] if e["type"]=="pull0"]
    f={}
    for e in sorted(eps,key=lambda e:e["episode"]): f.setdefault(e["env"],e)
    first[n]=f
envs=sorted(first[late[0]])
# same start? compare difficulty + initial door/grip
same=all(abs(first[n][i]["difficulty"]-first[late[0]][i]["difficulty"])<1e-6 for n in late for i in envs)
print("same starts across checkpoints:", same)
nfail=C.Counter({i:sum(not first[n][i]["success"] for n in late) for i in envs})
print("starts failed by k of", len(late), "checkpoints:", sorted(C.Counter(nfail.values()).items()))
hard=[i for i in envs if nfail[i]>=len(late)-1]; easy=[i for i in envs if nfail[i]==0]
f0=first[late[0]]
def desc(ids):
    s=[f0[i]["series"][0] for i in ids]
    return dict(n=len(ids), difficulty=round(S.median(f0[i]["difficulty"] for i in ids),2),
      grip_cm=round(S.median(r[2] for r in s)*100,2), door=round(S.median(r[1] for r in s),2),
      handle_cm=round(S.median(r[6] for r in s)*100,2), edge_x=round(S.median(r[3] for r in s)*100,1), edge_y=round(S.median(r[4] for r in s)*100,1))
print("hard (fail in >=6/7):", desc(hard)); print("easy (never fail):", desc(easy))
print("hard ids", hard[:40])
