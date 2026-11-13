"""issue 90: compare the start distribution of the v1 bank (types fixed first, rows sampled per type) and the v2
continuum bank (whole expert trajectories first, sliced by progress). Read-only; numpy only."""
import json, sys
import numpy as np, torch, yaml
sys.path.insert(0, ".")
from a2r.benchmark.contact_rl.factory.omnireset.stage_distribution import pose, rotate
from a2r.benchmark.contact_rl.spec import RESET_TYPES

SPEC = yaml.safe_load(open("a2r/benchmark/contact_rl/configs/tasks/industrial/wrench_slide_onto_nut.yaml"))
ORDER = ["pregrasp", "pick_descend", "pick_close", "pick_lift", "grasped_far", "near", "aligned", "p25", "p50", "p75"]
BANKS = {"v1": sys.argv[1], "v2": sys.argv[2]}
OUT = sys.argv[3]


def inv(q):
    q = q.copy(); q[:, 1:] *= -1; return q


def features(path):
    d = torch.load(path + "/cache.pt", map_location="cpu", weights_only=False)
    tcp, tq = pose("@tcp", SPEC, d)
    gp, gq = pose("@grasp", SPEC, d)
    jp, jq = pose("jaw", SPEC, d)
    sp, sq = pose("seat", SPEC, d)
    hand = rotate(inv(gq), tcp - gp) * 1000                 # hand in the wrench frame, mm
    jaw = rotate(inv(sq), jp - sp) * 1000                   # wrench mouth in the seat frame, mm
    tz = rotate(tq, np.array([0., 0., 1.]))
    tilt = np.degrees(np.arccos(np.clip(-tz[:, 2], -1, 1)))  # hand approach axis from straight down
    nut = d["obj/nut"].numpy()[:, :3]
    wr = d["obj/wrench"].numpy()[:, :3]
    grip = d["grip"].numpy() * 1000
    t = [RESET_TYPES[i] for i in d["type"].long().tolist()]
    local = d["extra/grasp/local"].numpy() * 1000 if "extra/grasp/local" in d else np.tile(np.asarray(SPEC["grasp"]["local"]) * 1000, (len(t), 1))
    entries = [json.loads(l) for l in open(path + "/entries.jsonl")]
    tau = np.array([e.get("tau", -1) for e in entries], dtype=float)
    return {"type": np.array(t), "hand": hand, "hand_dist": np.linalg.norm(hand, axis=1), "tilt": tilt,
            "jaw": jaw, "jaw_dist": np.linalg.norm(jaw, axis=1), "grip": grip,
            "nut_r": np.linalg.norm(nut[:, :2], axis=1) * 1000, "nut_bearing": np.degrees(np.arctan2(nut[:, 1], nut[:, 0])),
            "carry": np.linalg.norm((wr - nut)[:, :2], axis=1) * 1000, "grasp_x": local[:, 0], "tau": tau}


def q(x):
    return [round(float(v), 1) for v in np.quantile(x, [.1, .5, .9])] if len(x) else None


def fvec(f, m):
    """state feature for nearest-neighbour gaps: hand in wrench frame, mouth in seat frame (mm), grip opening (mm)"""
    return np.concatenate([f["hand"][m], f["jaw"][m], f["grip"][m, None]], 1)


def nearest(a, b):
    out = []
    for s in range(0, len(a), 256):
        out.append(np.sqrt(((a[s:s + 256, None] - b[None]) ** 2).sum(-1)).min(1))
    return np.concatenate(out) if out else np.zeros(0)


F = {k: features(v) for k, v in BANKS.items()}
res = {"per_type": {}, "gaps": {}, "cross": {}, "workspace": {}}
for k, f in F.items():
    res["per_type"][k] = {}
    for t in ORDER:
        m = f["type"] == t
        res["per_type"][k][t] = {"rows": int(m.sum()), "hand_dist_mm": q(f["hand_dist"][m]), "hand_height_mm": q(f["hand"][m, 2]),
                                 "hand_lateral_mm": q(np.linalg.norm(f["hand"][m, :2], axis=1)), "tilt_deg": q(f["tilt"][m]),
                                 "mouth_to_seat_mm": q(f["jaw_dist"][m]), "grip_mm": q(f["grip"][m]),
                                 "carry_mm": q(f["carry"][m]), "nut_r_mm": q(f["nut_r"][m]), "nut_bearing_deg": q(f["nut_bearing"][m]),
                                 "grasp_x_mm": q(f["grasp_x"][m]), "tau": q(f["tau"][m]) if (f["tau"][m] >= 0).any() else None}
    # gap between neighbouring types: each row of the upstream type to the nearest row of the next type downstream
    res["gaps"][k] = {}
    for a, b in zip(ORDER, ORDER[1:]):
        ma, mb = f["type"] == a, f["type"] == b
        if ma.any() and mb.any():
            res["gaps"][k][f"{a}->{b}"] = q(nearest(fvec(f, ma), fvec(f, mb)))
# coverage: rows of one bank far from every row of the other bank (same type, and any type)
for k, o in (("v1", "v2"), ("v2", "v1")):
    a, b = F[k], F[o]
    res["cross"][f"{k}_not_in_{o}"] = {}
    for t in ORDER:
        ma, mb = a["type"] == t, b["type"] == t
        if ma.any() and mb.any():
            dist = nearest(fvec(a, ma)[::2], fvec(b, mb))
            res["cross"][f"{k}_not_in_{o}"][t] = {"nearest_p50_p90": [round(float(x), 1) for x in np.quantile(dist, [.5, .9])],
                                                   "share_over_20mm": round(float((dist > 20).mean()), 3)}
for k, f in F.items():
    res["workspace"][k] = {"nut_r_mm": q(f["nut_r"]), "nut_r_minmax": [round(float(f["nut_r"].min())), round(float(f["nut_r"].max()))],
                           "nut_bearing_deg": q(f["nut_bearing"]), "bearing_minmax": [round(float(f["nut_bearing"].min())), round(float(f["nut_bearing"].max()))],
                           "grasp_x_mm": q(f["grasp_x"]), "grasp_x_minmax": [round(float(f["grasp_x"].min()), 1), round(float(f["grasp_x"].max()), 1)]}
json.dump(res, open(OUT, "w"), indent=1)
for k in F:
    print("==", k)
    for t, v in res["per_type"][k].items():
        print(f"{t:13s} n={v['rows']:5d} hand={v['hand_dist_mm']} h={v['hand_height_mm']} lat={v['hand_lateral_mm']} tilt={v['tilt_deg']} mouth={v['mouth_to_seat_mm']} grip={v['grip_mm']} carry={v['carry_mm']} tau={v['tau']}")
    print("gaps", res["gaps"][k])
    print("workspace", res["workspace"][k])
print("cross", json.dumps(res["cross"]))

# v2 progress bands (40 expert steps each): every row of band k to the nearest row of band k - 1 (closer to the goal)
f = F["v2"]
band = np.minimum(f["tau"] // 40, 13).astype(int)
bands = {}
for b in range(1, 14):
    ma, mb = band == b, band == b - 1
    if ma.any() and mb.any():
        bands[f"b{b:02d}->b{b-1:02d}"] = q(nearest(fvec(f, ma), fvec(f, mb)))
res["band_gaps_v2"] = bands
json.dump(res, open(OUT, "w"), indent=1)
print("band gaps", bands)

# density: every row to the nearest other row of the same type, in the same feature (mm), per bank
dens = {}
for k, f in F.items():
    dens[k] = {}
    for t in ORDER:
        m = np.flatnonzero(f["type"] == t)
        if len(m) < 2:
            continue
        x = fvec(f, f["type"] == t)
        out = []
        for s in range(0, len(x), 256):
            d2 = ((x[s:s + 256, None] - x[None]) ** 2).sum(-1)
            d2[np.arange(len(d2)), np.arange(s, s + len(d2))] = np.inf
            out.append(np.sqrt(d2.min(1)))
        nn = np.concatenate(out)
        dens[k][t] = {"rows": int(len(m)), "nn_p50": round(float(np.median(nn)), 1), "nn_p90": round(float(np.quantile(nn, .9)), 1)}
res["density"] = dens
json.dump(res, open(OUT, "w"), indent=1)
for t in ORDER:
    print(f"{t:13s}", "v1", dens["v1"].get(t), "| v2", dens["v2"].get(t))
