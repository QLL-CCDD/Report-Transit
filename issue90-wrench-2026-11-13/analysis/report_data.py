"""issue 90 report data (C side, read-only): training progress per run on environment steps, and start distributions
of the banks before / after the point fill and of the all-points (continuum) bank, as the hand relative to the nut.
Usage (from a source checkout): python report_data.py OUT.json"""
import glob
import json
import sys

import numpy as np
import torch
import yaml

sys.path.insert(0, ".")
from a2r.benchmark.contact_rl.factory.omnireset.stage_distribution import pose, rotate
from a2r.benchmark.contact_rl.spec import RESET_TYPES

OUT = sys.argv[1]
CROOT = "/home/zhaobo/contact_rl/issue90-scratch-c-20261112"
CR = "/home/zhaobo/contact_rl/issue90-progress-c-20261113"
TASK = "wrench_slide_onto_nut"
STEP = 8192
ORDER = ["p75", "p50", "p25", "aligned", "near", "grasped_far", "pick_lift", "pick_close", "pick_descend", "pregrasp"]
SPEC = yaml.safe_load(open("a2r/benchmark/contact_rl/configs/tasks/industrial/wrench_slide_onto_nut.yaml"))


def hist(path):
    try:
        return [json.loads(l) for l in open(path)]
    except OSError:
        return []


# ------------------------------------------------------------------ training progress on environment steps
def lineage():
    """the hand-over lineage (random init .. R390): per stage the first opening, and where the bank became r5"""
    rows = json.load(open(f"{CROOT}/r390/lineage-progress.json"))["rounds"]
    ev, s, switch = {}, 0, None
    for r in rows:
        bank = r["reset_bank"].split("/")[0]
        if switch is None and bank.startswith("curriculum-r5"):
            switch = s / 1e6
        for e in r.get("unlock_events", []):
            ev.setdefault(e["unlocked"][0], (s + e.get("minutes", 0) / max(r["training_minutes"], 1e-9) * r["environment_steps"]) / 1e6)
        s += r["environment_steps"]
    return ev, s / 1e6, switch


def runs(dirs):
    """first opening of every stage / band, end, and every full-bank evaluation of orchestrated runs"""
    ev, evals, s0, last = {}, [], 0, {}
    for d in dirs:
        prog = json.load(open(f"{d}/progress.json")) if glob.glob(f"{d}/progress.json") else {"rounds": []}
        for rd in sorted(glob.glob(f"{d}/round-*/train")):
            h = hist(f"{rd}/history.jsonl")
            for i, x in enumerate(h):
                e = x["tasks"][TASK].get("unlock_event")
                if e:
                    ev.setdefault(e["unlocked"][0], (s0 + (i + 1) * STEP) / 1e6)
            s0 += len(h) * STEP
            for r in prog["rounds"]:
                if r.get("evaluation") and rd.endswith(f"round-{r['round']:03d}-{r['view']}/train"):
                    pt = r["evaluation"]
                    a, b = sum(v["successes"] for v in pt.values()), sum(v["trials"] for v in pt.values())
                    evals.append([round(s0 / 1e6, 2), round(a / b, 3), round(min(v["success_rate"] for v in pt.values()), 3)])
                    last = {k: [v["successes"], v["trials"]] for k, v in pt.items()}
    return {"events": {k: round(v, 2) for k, v in ev.items()}, "end": round(s0 / 1e6, 2), "evals": evals, "last": last}


old_ev, old_end, switch = lineage()
r388 = json.load(open(f"{CROOT}/r388/eval/eval.json"))["tasks"][TASK]["per_type"]
progress = {
    "old": {"events": {k: round(v, 2) for k, v in old_ev.items()}, "end": round(old_end, 2), "switch_r5": round(switch, 2),
            "evals": [[94.3, round(sum(v["successes"] for v in r388.values()) / sum(v["trials"] for v in r388.values()), 3),
                       round(min(v["success_rate"] for v in r388.values() if v["trials"]), 3)]]},
    "full": runs([f"{CROOT}/R396-scratch-full", f"{CROOT}/R398-scratch-full-cont"]),
    "lean": runs([f"{CROOT}/R397-scratch-lean"]),
    "bands": runs([f"{CR}/R399-progress-b40"]),
    "types_v2": runs([f"{CR}/R400-continuum-types"]),
    "allpoints": runs([f"{CR}/R401-allpoints-b40"]),
}
ap = json.load(open(f"{CR}/R401-allpoints-b40/progress.json"))
progress["allpoints"].update(status=ap["status"], minutes=round(ap["training_minutes"]))
pv = json.load(open(f"{CR}/allpoints-b40/manifest.json"))["progress_view"]["table"]
progress["allpoints_bands"] = {k: {"tau": v["tau"], "rows": v["rows"], "types": v["types"]} for k, v in pv.items()}
ck = json.load(open(f"{CR}/continuum-wrench/check/check.json"))["results"]["expert"]
progress["eval_expert"] = {t: round(v["success_rate"], 2) for t, v in ck.items() if isinstance(v, dict) and "success_rate" in v}
pv = json.load(open(f"{CR}/progress-b40/manifest.json"))["progress_view"]["table"]
progress["band_table"] = {k: {"tau": v["tau"], "rows": v["rows"], "types": v["types"]} for k, v in pv.items()}


# ------------------------------------------------------------------ distributions: hand relative to the nut
def inv(q):
    q = q.copy()
    q[:, 1:] *= -1
    return q


def bank_points(path, seed=0, voxel=10.0, per_voxel=2, cap=5000):
    d = torch.load(f"{path}/cache.pt", map_location="cpu", weights_only=False)
    tcp, _ = pose("@tcp", SPEC, d)
    nut, nq = pose("nut", SPEC, d)
    local = (tcp - nut) * 1000                         # hand minus nut on the robot base axes (x forward, y left, z up), mm
    types = d["type"].long().numpy()
    counts = {RESET_TYPES[t]: int((types == t).sum()) for t in np.unique(types)}
    rng = np.random.default_rng(seed)
    keep = []
    for t in np.unique(types):
        idx = np.flatnonzero(types == t)
        idx = idx[rng.permutation(len(idx))]
        cell = np.floor(local[idx] / voxel).astype(np.int64)
        _, first = np.unique(cell, axis=0, return_inverse=True)
        seen = {}
        for j, c in zip(idx, first.ravel()):
            if seen.get(c, 0) < per_voxel:
                seen[c] = seen.get(c, 0) + 1
                keep.append(j)
    keep = np.asarray(keep)
    if len(keep) > cap:
        keep = rng.choice(keep, cap, replace=False)
    pts = [[round(float(x), 1), round(float(y), 1), round(float(z), 1), ORDER.index(RESET_TYPES[types[i]])]
           for i, (x, y, z) in zip(keep, local[keep])]
    horiz = np.linalg.norm(local[:, :2], axis=1)
    stats = {RESET_TYPES[t]: {"horiz_mm": [round(float(v)) for v in np.quantile(horiz[types == t], [.1, .5, .9])],
                              "height_mm": [round(float(v)) for v in np.quantile(local[types == t, 2], [.1, .5, .9])]}
             for t in np.unique(types)}
    return {"points": pts, "counts": counts, "total": int(len(types)), "stats": stats}


def source_points(src, seed=0, voxel=10.0, per_voxel=2, cap=6000, band=40):
    """the all-points bank under construction: every recorded frame of the successful expert trajectories so far,
    hand minus nut, labelled by expert steps to go (100 + band index)"""
    parts, taus = [], []
    for f in sorted(glob.glob(f"{src}/sources/round_*.pt")):
        meta = json.load(open(f[:-3] + ".json"))
        n = len(meta["valid"])
        rnd = int(f.split("_")[-1][:4])
        d = torch.load(f, map_location="cpu", weights_only=False)
        if d is None:
            continue
        end = {rnd * n + e: meta["end_step"][e] for e in range(n) if meta["success"][e]}
        tcp, _ = pose("@tcp", SPEC, d["rows"])
        nut, _ = pose("nut", SPEC, d["rows"])
        parts.append((tcp - nut) * 1000)
        taus.append(np.array([end[int(t)] - int(k) for t, k in zip(d["traj"], d["step"])]))
    local, tau = np.concatenate(parts), np.concatenate(taus)
    bucket = np.minimum(tau // band, 14).astype(int)
    rng = np.random.default_rng(seed)
    keep = []
    for b in np.unique(bucket):
        idx = np.flatnonzero(bucket == b)
        idx = idx[rng.permutation(len(idx))]
        _, cell = np.unique(np.floor(local[idx] / voxel).astype(np.int64), axis=0, return_inverse=True)
        seen = {}
        for j, c in zip(idx, cell.ravel()):
            if seen.get(c, 0) < per_voxel:
                seen[c] = seen.get(c, 0) + 1
                keep.append(j)
    keep = np.asarray(keep)
    if len(keep) > cap:
        keep = rng.choice(keep, cap, replace=False)
    rounds = len(glob.glob(f"{src}/sources/round_*.json"))
    return {"points": [[round(float(x), 1), round(float(y), 1), round(float(z), 1), 100 + int(bucket[i])] for i, (x, y, z) in zip(keep, local[keep])],
            "total": int(len(tau)), "rounds": rounds, "tau_max": int(tau.max())}


banks = {"before": "/media/zhaobo/Element1/issue90-wrench-20261109/curriculum-r4",
         "after": f"{CROOT}/curriculum-r5",
         "continuum": f"{CR}/continuum-wrench/filter-0"}
dist = {k: bank_points(v) for k, v in banks.items()}
dist["allpoints"] = bank_points("/home/zhaobo/contact_rl/issue90-allpoints-c-20261113/wrench_slide_onto_nut/bank")
json.dump({"progress": progress, "dist": dist, "order": ORDER}, open(OUT, "w"), ensure_ascii=False)
print(json.dumps({k: {"sampled": len(v["points"]), "total": v["total"]} for k, v in dist.items()}))
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "evals"} if isinstance(v, dict) and "events" in v else None for k, v in progress.items()})[:1800])
