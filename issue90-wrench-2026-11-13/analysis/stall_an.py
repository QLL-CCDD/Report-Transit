"""issue 90: why the two continuum-bank arms stall at aligned / near (read-only, training histories only)."""
import glob, json, os
CR = "/home/zhaobo/contact_rl/issue90-progress-c-20261113"
CROOT = "/home/zhaobo/contact_rl/issue90-scratch-c-20261112"
T = "wrench_slide_onto_nut"
LIMIT = {"aligned": 144, "near": 208, "p25": 137}
LIMIT_V1 = {"aligned": 150, "near": 180, "p25": 150}


def hist(d):
    out, s = [], 0
    for rd in sorted(glob.glob(f"{d}/round-*/train")):
        if os.path.exists(rd + "/history.jsonl"):
            for l in open(rd + "/history.jsonl"):
                s += 8192
                out.append((s / 1e6, json.loads(l)["tasks"][T]))
    return out


def curve(h, key, sub, window=300, start=0.0):
    pts, win = [], []
    for s, t in h:
        if s < start:
            continue
        if sub == "type":
            n, p = t["episodes_by_type"].get(key, 0), t["success_by_type"].get(key)
        else:     # band/type cells of the progress arm, pooled over the cells of one band
            cells = [v for k, v in (t.get("success_by_band_type") or {}).items() if k.startswith(key + "/")]
            n, p = sum(c[0] for c in cells), (sum(c[0] * c[1] for c in cells) / max(sum(c[0] for c in cells), 1))
        if n and p is not None:
            win.append((n, n * p))
        while sum(a for a, _ in win) > window and len(win) > 1:
            win.pop(0)
        tot = sum(a for a, _ in win)
        if tot >= 100:
            pts.append([round(s, 3), round(sum(b for _, b in win) / tot, 3)])
    return pts[::max(1, len(pts) // 300)]


def tail_stats(h, types, n_last=150):
    agg = {}
    for _, t in h[-n_last:]:
        for k in types:
            n = t["episodes_by_type"].get(k, 0)
            if n:
                a = agg.setdefault(k, [0, 0, 0])
                a[0] += n; a[1] += n * t["success_by_type"][k]; a[2] += t.get("steps_by_type", {}).get(k, 0)
        for k, (n, r) in (t.get("success_by_type_tier") or {}).items():
            if k.split("/")[0] in types:
                a = agg.setdefault(k, [0, 0, 0]); a[0] += n; a[1] += n * r
    return {k: {"episodes": int(a[0]), "success": round(a[1] / a[0], 3), "mean_steps": round(a[2] / a[0]) if a[2] else None}
            for k, a in agg.items() if a[0]}


def evals(d):
    p = json.load(open(f"{d}/progress.json"))
    out, s = [], 0
    for r in p["rounds"]:
        s += r["training"]["environment_steps"]
        if r.get("evaluation"):
            e = r["evaluation"]
            out.append([round(s / 1e6, 2), round(sum(v["successes"] for v in e.values()) / sum(v["trials"] for v in e.values()), 3),
                        {k: round(v["success_rate"], 2) for k, v in e.items()}])
    return out


h399, h400 = hist(f"{CR}/R399-progress-b40"), hist(f"{CR}/R400-continuum-types")
h396 = hist(f"{CROOT}/R396-scratch-full")
h396 = [x for x in h396 if x[0] <= 6.0]
res = {
    "curves": {"bands_b02": curve(h399, "b02", "band", start=0.5), "bands_near": curve(h399, "near", "type", start=0.5),
               "bands_aligned": curve(h399, "aligned", "type", start=0.5),
               "types_aligned": curve(h400, "aligned", "type", start=0.74),
               "v1_aligned": curve(h396, "aligned", "type", start=0.74), "v1_near": curve(h396, "near", "type", start=2.06)},
    "tail": {"bands": tail_stats(h399, ["aligned", "near", "p25"]), "types": tail_stats(h400, ["aligned", "p25"]),
             "v1_at_same_stage": tail_stats([x for x in h396 if 0.74 <= x[0] <= 2.4], ["aligned", "near", "p25"], 10 ** 6)},
    "evals": {"bands": evals(f"{CR}/R399-progress-b40"), "types": evals(f"{CR}/R400-continuum-types")},
    "end": {"bands": round(h399[-1][0], 2), "types": round(h400[-1][0], 2)},
    "grip": {"bands": round(h399[-1][1].get("grip_mu_mean", float("nan")), 2) if h399 else None},
    "limits": {"v2": LIMIT, "v1": LIMIT_V1},
}
json.dump(res, open(f"{CR}/analysis/stall.json", "w"), ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "curves"}, ensure_ascii=False, indent=0)[:3500])
print({k: (len(v), v[-1] if v else None) for k, v in res["curves"].items()})
