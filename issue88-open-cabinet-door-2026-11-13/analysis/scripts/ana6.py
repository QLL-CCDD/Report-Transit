import json
B = "/dev/shm/e10-door88/diag-seeds"
late = ["s1cap-5.7M","s2cap-5.7M","s2unc-10.3M","s3cap-15M","s3unc-5.8M","s3cap-5.7M","s2unc-5.7M"]
F={}
for n in late:
    f={}
    for e in sorted([e for e in json.load(open(f"{B}/{n}/phases.json"))["episodes"] if e["type"]=="pull0"],key=lambda e:e["episode"]): f.setdefault(e["env"],e)
    F[n]=f
envs=sorted(F[late[0]])
rows=[(F[late[0]][i]["series"][0][6]*100, F[late[0]][i]["series"][0][2]*100, sum(not F[n][i]["success"] for n in late)/len(late)) for i in envs]
for lo,hi in [(0,1),(1,1.5),(1.5,2),(2,3),(3,5),(5,99)]:
    s=[r for r in rows if lo<=r[0]<hi]
    if s: print(f"handle dist {lo}-{hi} cm: n={len(s)} fail rate {sum(r[2] for r in s)/len(s):.2f}  grip med {sorted(r[1] for r in s)[len(s)//2]:.1f} cm")
for lo,hi in [(0,1.5),(1.5,2.5),(2.5,99)]:
    s=[r for r in rows if lo<=r[1]<hi]
    if s: print(f"grip width {lo}-{hi} cm: n={len(s)} fail rate {sum(r[2] for r in s)/len(s):.2f}")
for n in late+["s2unc-2.5M","s3unc-2.5M"]:
    print(n, open(f"{B}/{n}/pick.txt").read().split(), [p.split('/')[-1] for p in __import__('glob').glob(f"{B}/{n}/videos/*/*.mp4")][:6])
