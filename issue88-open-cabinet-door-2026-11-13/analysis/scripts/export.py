import json, os, csv, sys
B = "/dev/shm/e10-door88/diag-seeds"
out = sys.argv[1]
w = csv.writer(open(out, "w", newline=""))
w.writerow(["checkpoint", "mode", "env", "success", "seconds", "stuck", "start_door_deg", "start_grip_width_cm", "start_handle_dist_cm",
            "release_t_s", "door_deg_at_release", "end_handle_dist_cm"])
for n in sorted(os.listdir(B)):
    p = f"{B}/{n}/phases.json"
    if not os.path.exists(p): continue
    eps = [e for e in json.load(open(p))["episodes"] if e["type"] == "pull0"]
    first = {}
    for e in sorted(eps, key=lambda e: e["episode"]): first.setdefault(e["env"], e)
    for env, e in sorted(first.items()):
        s = e["series"]; rel = next((r for r in s if r[2] >= 0.06), None)
        w.writerow([n.removesuffix("-sto"), "noisy" if n.endswith("-sto") else "deterministic", env, int(e["success"]), e["seconds"],
                    e.get("stuck") or "", round(s[0][1], 2), round(s[0][2] * 100, 2), round(s[0][6] * 100, 2),
                    round(rel[0] - s[0][0], 2) if rel else "", round(rel[1], 2) if rel else "", round(s[-1][6] * 100, 2)])
