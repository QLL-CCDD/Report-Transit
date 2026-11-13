"""#88 section 6: resumes from seed 1's pre-collapse checkpoint, three seeds, with and without the new-start share cap.
Seeds 1/2/3 here = 8871/8872/8873 (uncapped: E10-R337/R341/R343, capped: E10-R340/R342/R344)."""
import json, html, sys, os
sys.argv = sys.argv[:1]
import contact_rl_trace_phases as T
A = "ablation"
STAGES = ["p75", "p50", "handoff3", "handoff2", "handoff1", "p25", "pull2", "pull1", "pull_b", "pull_a", "pull0", "pick_close", "pick_descend", "pregrasp"]
COL = {"1": "var(--s1)", "2": "var(--s2)", "3": "var(--s3)"}
ARMS = [("1", False, ["hf-R337/train/history.jsonl"]), ("1", True, [f"{A}/cap-8871b.jsonl", f"{A}/cap-8871c.jsonl"]),
        ("2", False, [f"{A}/peak-8872b.jsonl", f"{A}/peak-8872c.jsonl"]), ("2", True, [f"{A}/cap-8872b.jsonl", f"{A}/cap-8872c.jsonl"]),
        ("3", False, [f"{A}/peak-8873b.jsonl", f"{A}/peak-8873c.jsonl"]), ("3", True, [f"{A}/cap-8873b.jsonl", f"{A}/cap-8873c.jsonl"])]
key = lambda seed, cap: f"s{seed}{'c' if cap else 'u'}"

def files(paths):
    out, off = [], 0.0
    for p in paths:
        if os.path.exists(p) and os.path.getsize(p):
            out.append((p, off))
            off += max(json.loads(l)["env_steps"] for l in open(p) if '"env_steps"' in l) / 1e6
    return out

def stats(paths):
    opened = passed = full = None; prev = None; ce = 0; gmin = None; m = 0
    for p, off in files(paths):
        for line in open(p):
            r = json.loads(line)
            if "env_steps" not in r: continue
            m = off + r["env_steps"] / 1e6; t = next(iter(r["tasks"].values())); s = t.get("unlock_stage")
            if prev is not None and s != prev:
                if s == STAGES.index("pull0"): opened = m
                if s == STAGES.index("pull0") + 1: passed = m
                if s == len(STAGES) - 1: full = m
            prev = s; ce += bool(r.get("collapse_event"))
            g = (t.get("collapse_guard") or {}).get("rate")
            if g is not None and opened is not None: gmin = g if gmin is None else min(gmin, g)
    return dict(opened=opened, passed=passed, full=full, end=m, collapses=ce, guard_min=gmin, stage=prev)

cur = {}
for ty in ("pull0", "pull_b,pull_a"):
    argv = ["--type", ty, "--out", f"{A}/curves-{ty.replace(',', '+')}.json"]
    for seed, cap, paths in ARMS:
        for p, off in files(paths): argv += ["--run", f"{key(seed, cap)}:{p}:{off}"]
    T.curves(argv)
    cur[ty] = json.load(open(f"{A}/curves-{ty.replace(',', '+')}.json"))
cur["pull_a"] = cur["pull_b,pull_a"]

def last(series):
    v = [p for p in series if p[2] is not None]
    return v[-1][2] if v else None
def low(series, frm):
    v = [p[2] for p in series if p[0] >= frm + 0.5 and p[2] is not None]
    return min(v) if v else None

f = lambda v, d=2: "—" if v is None else f"{v:.{d}f}"
meta, rows, DONE = [], [], set()
for seed, cap, paths in ARMS:
    k = key(seed, cap)
    if not files(paths): continue
    meta.append({"key": k, "name": f"种子{seed} {'最多 10%' if cap else '不限'}", "short": f"种子{seed} {'限' if cap else '不限'}",
                 "color": COL[seed], "dash": not cap})
    s = stats(paths)
    iters = sum(1 for p, _ in files(paths) for l in open(p) if '"env_steps"' in l)
    if not (s["full"] or iters >= 1830):
        rows.append(f"<tr><td>种子{seed}</td><td>{'最多 10%' if cap else '不限'}</td><td colspan='5' class='muted'>训练中，跑完后补上</td></tr>")
        continue
    DONE.add(k)
    if s["full"]: res = f"{s['passed']:.1f}M 步过 pull0，{s['full']:.1f}M 步全部解锁"
    elif s["passed"]:
        nxt = STAGES[s["stage"]] if s["stage"] is not None else ""
        res = f"{s['passed']:.1f}M 步过了 pull0，卡在下一级 {nxt}"
    else: res = f"步数预算用完（{s['end']:.1f}M 步），没过 pull0"
    rows.append(f"<tr><td>种子{seed}</td><td>{'最多 10%' if cap else '不限'}</td><td class='num'>{s['end']:.1f}</td><td>{res}</td>"
                f"<td class='num'>{f(last(cur['pull0']['series'].get(k, [])))}</td>"
                f"<td class='num'>{f(low(cur['pull_a']['series'].get(k, []), s['opened'] or 0))}</td>"
                f"<td>{'报警 ' + str(s['collapses']) + ' 次' if s['collapses'] else '没报警' if s['guard_min'] is not None else '没报警（事后回放）'}</td></tr>")

leg = ("<div class='legend'><span><i style='background:var(--s2)'></i>pull0（门关着、刚握住把手）</span>"
       "<span><i style='background:var(--s1)'></i>pull_b、pull_a 合计（握着把手、门开约 4° 和 2°，已学会）</span>"
       "<span><svg width='28' height='8'><line x1='0' x2='28' y1='4' y2='4' stroke='currentColor' stroke-width='2'/></svg> 新开放的起点最多占 10%</span>"
       "<span><svg width='28' height='8'><line x1='0' x2='28' y1='4' y2='4' stroke='currentColor' stroke-width='2' stroke-dasharray='6 4'/></svg> 不限</span></div>")
XL = "续训后的环境步数（百万步）"
charts = []
for seed in "123":
    both = {}
    for ty, tag, colr in (("pull0", "pull0", "var(--s2)"), ("pull_b,pull_a", "pull_b+a", "var(--s1)")):
        for cap in (True, False):
            k = key(seed, cap)
            both[f"{k}:{tag}"] = cur[ty]["series"].get(k, [])
    arms = [cap for cap in (True, False) if key(seed, cap) in DONE]
    if not arms:
        charts.append(f"<h3>种子{seed}</h3><p class='lead'>训练中，跑完后补图。</p>")
        continue
    meta = [{"key": f"{key(seed, cap)}:{tag}", "name": f"{tag} {'最多10%' if cap else '不限'}", "short": f"{tag} {'最多10%' if cap else '不限'}",
             "color": colr, "dash": not cap} for tag, colr in (("pull0", "var(--s2)"), ("pull_b+a", "var(--s1)")) for cap in arms]
    c = {"type": "pull0", "window": 0.3, "series": both}
    charts.append(T._curve_chart(f"ab_s{seed}", c, meta, 2, f"种子{seed}", threshold=0.7, xlabel=XL))
lead = open(f"{A}/lead.html", encoding="utf-8").read()
out = ["<h2>6 从高点续训，再重复两次；限制新起点的抽样比例</h2>", lead,
       "<table class='tt'><tr><th>种子</th><th>新开放的起点</th><th>已续训（百万步）</th><th>结果</th>"
       "<th>pull0 最后的成功率</th><th>pull_b、pull_a 合计最低跌到</th><th>自动崩塌检查</th></tr>", *rows, "</table>",
       "<h3>成功率随续训步数的变化（每个种子一张图）</h3>",
       "<p class='lead'>横轴从续训开始算。橙色是 pull0，蓝色是旁边已学会的 pull_b、pull_a 合在一起；实线是限制比例，虚线是不限。"
       "成功率按最近 0.3M 步内结束的回合计算，每条线开头和刚开放的 0.5M 步不画（开头的成功率会虚高）。课程全部解锁（开放到最前面的 pregrasp）后训练再跑 10 分钟就自动停止，所以有的线较短。</p>",
       leg, *charts]
open(f"{A}/ablation.html", "w", encoding="utf-8").write("\n".join(out))
print("wrote", f"{A}/ablation.html"); print("\n".join(rows))
