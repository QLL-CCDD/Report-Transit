"""issue 90 wrench report, three parts only: training progress on environment steps, start distributions before /
after the point fill and of the all-points bank (hand relative to the nut), and the 1:1 RL / expert videos.
Run on the Mac (visualisation host): python3 build_report.py report-data.json videos.json OUT.html [stall.json]"""
import html
import json
import sys

D = json.load(open(sys.argv[1]))
VIDEOS = json.load(open(sys.argv[2]))
OUT = sys.argv[3]
STALL = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else None
ORDER = D["order"]                       # unlock order p75 .. pregrasp
TASK_ORDER = ORDER[::-1]
P = D["progress"]
SHORT = {"pregrasp": "手在扳手上方约 7 cm", "pick_descend": "张开夹爪往下降", "pick_close": "手指到位、正要合上",
         "pick_lift": "夹住、正要抬起", "grasped_far": "拿着扳手、离螺母远", "near": "拿着扳手、在螺母附近",
         "aligned": "开口对准螺母", "p25": "套进约 1/4", "p50": "套进约一半", "p75": "套进约 3/4"}
COLORS = {"pregrasp": "#7a7a7a", "pick_descend": "#e8892a", "pick_close": "#c0392b", "pick_lift": "#8e44ad",
          "grasped_far": "#2a78d6", "near": "#1baf7a", "aligned": "#17a2b8", "p25": "#b58900", "p50": "#d35d9c", "p75": "#5d4037"}


def esc(x):
    return html.escape(str(x))


# ------------------------------------------------------------------ line / step charts (SVG + hover)
def ticks(lo, hi, n=8):
    for st in (0.25, 0.5, 1, 2, 5, 10, 20, 25, 50):
        if (hi - lo) / st <= n:
            break
    k = int(lo / st + (0 if lo <= 0 else 0.999)) * st
    out = []
    while k <= hi + 1e-9:
        out.append(round(k, 6))
        k += st
    return out


def fmt(v):
    return f"{v:g}" if abs(v - round(v)) > 1e-9 else f"{int(round(v))}"


def chart(cid, series, x0, x1, y0, y1, xname, ytick=None, cats=None, hlines=(), vmarks=(), h=260, dec=2):
    W, l, r, T, B = 940, (118 if cats else 52), 16, 14, 40
    fx = lambda x: l + (x - x0) / (x1 - x0) * (W - l - r)
    fy = lambda y: T + (1 - (y - y0) / (y1 - y0)) * (h - T - B)
    g = [f'<svg viewBox="0 0 {W} {h}" width="100%" role="img">']
    for y in (range(len(cats)) if cats else (ytick or ticks(y0, y1, 5))):
        lab = cats[y] if cats else fmt(y)
        g.append(f'<line x1="{l}" x2="{W-r}" y1="{fy(y):.1f}" y2="{fy(y):.1f}" stroke="var(--grid)"/>'
                 f'<text x="{l-6}" y="{fy(y)+4:.1f}" font-size="11" text-anchor="end" class="svgmuted">{esc(lab)}</text>')
    for x in ticks(x0, x1):
        g.append(f'<text x="{fx(x):.1f}" y="{h-B+16}" font-size="11" text-anchor="middle" class="svgmuted">{fmt(x)}</text>')
    g.append(f'<text x="{(l+W-r)/2}" y="{h-6}" font-size="11" text-anchor="middle" class="svgmuted">{esc(xname.split("：")[0])}</text>')
    for y, lab in hlines:
        g.append(f'<line x1="{l}" x2="{W-r}" y1="{fy(y):.1f}" y2="{fy(y):.1f}" stroke="var(--text-muted)" stroke-dasharray="4 4"/>'
                 f'<text x="{W-r-4}" y="{fy(y)+14:.1f}" font-size="11" text-anchor="end" class="svgmuted">{esc(lab)}</text>')
    for x, lab, *side in vmarks:
        if x0 <= x <= x1:
            left = side[0] == "left" if side else fx(x) > W * 0.7
            g.append(f'<line x1="{fx(x):.1f}" x2="{fx(x):.1f}" y1="{T}" y2="{h-B}" stroke="var(--text-muted)" stroke-dasharray="2 3"/>'
                     f'<text x="{fx(x)+(-4 if left else 4):.1f}" y="{T+10}" font-size="11" text-anchor="{"end" if left else "start"}" class="svgmuted">{esc(lab)}</text>')
    data = []
    for s in series:
        pts = [(x, y) for x, y in s["pts"] if x0 - 1e-9 <= x <= x1 + 1e-9]
        if not pts:
            continue
        if s.get("step"):
            d, prev = [], None
            for x, y in pts:
                d.append(f"{'M' if prev is None else 'L'}{fx(x):.1f},{fy(prev if prev is not None else y):.1f} L{fx(x):.1f},{fy(y):.1f}")
                prev = y
            path = " ".join(d)
        else:
            path = " ".join(f"{'M' if i == 0 else 'L'}{fx(x):.1f},{fy(y):.1f}" for i, (x, y) in enumerate(pts))
        dash = ' stroke-dasharray="7 4"' if s.get("dash") else ""
        g.append(f'<path d="{path}" fill="none" stroke="{s["color"]}" stroke-width="2.2"{dash}/>')
        if s.get("dots"):
            g += [f'<circle cx="{fx(x):.1f}" cy="{fy(y):.1f}" r="3.5" fill="{s["color"]}"/>' for x, y in pts]
        data.append({"name": s["name"], "color": s["color"], "step": bool(s.get("step")), "pts": [[x, y] for x, y in pts]})
    g.append(f'<line class="xh" x1="0" x2="0" y1="{T}" y2="{h-B}" stroke="var(--text-muted)" visibility="hidden"/></svg>')
    D_ = {"W": W, "l": l, "r": r, "x0": x0, "x1": x1, "tol": (x1 - x0) / 40, "xname": xname, "dec": dec, "cats": cats, "series": data}
    return (f"<div class='chart' id='{cid}'>{''.join(g)}<div class='tip'></div></div>"
            f"<script>chartTip('{cid}',{json.dumps(D_, ensure_ascii=False)})</script>")


def legend(items):
    out = []
    for name, color, dash in items:
        da = ' stroke-dasharray="6 3"' if dash else ""
        out.append(f"<span><svg width='26' height='10'><line x1='0' x2='26' y1='5' y2='5' stroke='{color}' stroke-width='2.5'{da}/></svg> {esc(name)}</span>")
    return f"<div class='legend'>{''.join(out)}</div>"


CATS = ["（还没有）"] + ORDER


def ladder(run, target=False):
    """the furthest start type that passed its gate (the next one opened), on the run's own order; ``target``: the
    last one passed by the full-bank evaluation at the end"""
    ev = sorted((s, k) for k, s in run["events"].items() if k in ORDER)
    opened = ["p75"] + [k for _, k in ev]
    pts = [(0, 0)] + [(s, ORDER.index(opened[i]) + 1) for i, (s, _) in enumerate(ev)]
    if target:
        pts.append((run["end"], ORDER.index(opened[-1]) + 1))
    return pts + [(run["end"], pts[-1][1])]


old, full, lean, bands, tv2 = P["old"], P["full"], P["lean"], P["bands"], P["types_v2"]
sec = []

# ================================================================== 1 training progress
band_now = max([int(k[1:]) for k in bands["events"]] + [0])
band_tau = P["band_table"] and P["band_table"].get(f"b{band_now:02d}", {}).get("tau")
fe = full["evals"][-1] if full["evals"] else None
sec.append(f"""<h2>1 训练进度：补点前后，按环境步数</h2>
<p class='lead'>“补点”指往起点库里追加中间状态：旧库 r4 → r5 追加了 1000 个真实的“张开夹爪往下降”起点。这里只放已经训出结论的两次从零训练，还在训练、或中途停下没有结论的实验先不放。
横轴是环境步数（M = 百万步）。上图纵轴是已经学会（训练成功率过 0.7）的最前一级起点：课程从最下面的 p75 开始往上逐级解锁，最上面的 pregrasp 学会、并且完整库评测十类都 ≥90% 才算达标；下图是完整库上的确定性评测，十类起点合计的成功率。鼠标移到图上可以看数值。</p>
{legend([("补点前开始的旧做法（第 {:.0f}M 步起换成补点后的库）".format(old["switch_r5"]), "var(--orig)", True),
         ("补点后的库 + 夹爪修正，从零训练", "var(--s1)", False)])}
{chart("c_ladder", [{"name": "补点前开始的旧做法", "color": "var(--orig)", "step": True, "dash": True, "pts": ladder(old)},
                    {"name": "补点后 + 修正", "color": "var(--s1)", "step": True, "pts": ladder(full, True)}],
       0, round(old["end"] + 1), -0.5, 10.5, "从零训练的环境步数（百万步）：第 {x} 百万步", cats=CATS, h=340,
       vmarks=[(old["switch_r5"], "旧做法换成补点后的库", "left"), (full["end"], "补点后 + 修正：评测达标")])}
{legend([("补点后 + 修正", "var(--s1)", False), ("旧做法交接时的一次评测（第 94M 步）", "var(--orig)", True)])}
{chart("c_eval", [{"name": "补点后 + 修正", "color": "var(--s1)", "dots": True, "pts": [(s, a) for s, a, _ in full["evals"]]},
                  {"name": "旧做法交接时", "color": "var(--orig)", "dots": True, "pts": [(s, a) for s, a, _ in old["evals"]]}],
       0, round(old["end"] + 1), 0.5, 1, "从零训练的环境步数（百万步）：第 {x} 百万步", ytick=[0.5, 0.6, 0.7, 0.8, 0.9, 1],
       hlines=[(0.9, "达标线 0.9")], h=220)}
<ul>
<li><b>只补点不够：</b>旧做法在补点前用了 {old["events"]["pick_descend"]:.1f}M 步才开放 pick_descend；第 {old["switch_r5"]:.1f}M 步换成补点后的库，又训了 {old["end"] - old["switch_r5"]:.1f}M 步，pregrasp 仍然一次都没成功（交接时评测 pregrasp 0/54）。原因是夹爪动作被截断，总在第 7–8 步就合上。</li>
<li><b>补点加夹爪修正：</b>同一份补点后的库从零训练，{full["end"]:.1f}M 步达标{f"（{fe[1]:.1%}，最差一类 {fe[2]:.0%}）" if fe else ""}，约为旧做法所用步数的一半。抓取段几级在 {full["events"]["pick_lift"]:.1f}–{full["events"]["pregrasp"]:.1f}M 步依次学会。</li>
</ul>""")

# ================================================================== 2 distributions
AP = D["dist"].get("allpoints")
CN = D["dist"]["continuum"]["total"]
BANKS = [("before", "补点前（旧库 r4）"), ("after", "补点后（旧库 r5，+1000 个下降起点）"),
         ("continuum", f"连续体库第一版（11 月 12 日建，{CN / 1e4:.1f} 万行，R399/R400 用过）")]
BANKS += [("allpoints", f"全量点库（11 月 13 日建，{AP['total'] / 1e4:.1f} 万行）")] if AP else []
PANELS = BANKS
counts_rows = "".join(
    f"<tr><td><span class='dot' style='background:{COLORS[t]}'></span>{t}<div class='sub'>{esc(SHORT[t])}</div></td>"
    + "".join(f"<td class='num'>{D['dist'][k]['counts'].get(t, 0)}</td>" for k, _ in BANKS) + "</tr>" for t in TASK_ORDER)
cols = "".join(f"<th>{esc(n)}</th>" for _, n in BANKS)
dist_js = {k: D["dist"][k]["points"] for k, _ in PANELS}
sec.append(f"""<h2>2 起点分布：补点前、补点后、连续体库第一版、全量点库</h2>
<p class='lead'>每个点是库里的一个起点，画的是<b>手（两指之间的中心点）相对螺母</b>的位置：手的坐标减去螺母中心的坐标，单位 mm，坐标轴沿机器人底座（x 朝前、y 朝左、z 向上），原点（黑点）就是螺母。
颜色表示起点类型，点击图例可以隐藏或显示某一类。点太多时按 1 cm 的小格抽样，每格每类最多留 2 个点，这样稀疏的地方不会被密集的地方盖住。
抓取段的手在扳手旁边，所以离螺母 15–25 cm；越往后，手越靠近螺母。</p>
<div class='legend' id='stage_legend'></div>
<div class='grid3'>{''.join(f"<div><h3>{esc(n)}</h3><div class='cap'>左：离螺母的水平距离 × 高度（侧视）　右：Δx × Δy（俯视）</div><div class='pair2'><canvas id='hd_{k}' height='300'></canvas><canvas id='xy_{k}' height='300'></canvas></div>" + "</div>" for k, n in PANELS)}</div>
<h3>三维：拖动旋转，滚轮缩放</h3>
<div class='bankbtn' id='bankbtn'>{''.join(f"<button data-k='{k}'>{esc(n)}</button>" for k, n in PANELS)}</div>
<canvas id='c3d' height='520'></canvas>
<details><summary>各类起点的行数</summary><table class='tt'><tr><th>起点类型</th>{cols}</tr>{counts_rows}</table></details>
<ul>
<li><b>补点前：</b>“张开夹爪往下降”只有一小段，下降途中大部分高度没有起点，从 pregrasp 到合上夹爪之间断开。</li>
<li><b>补点后：</b>下降段补成了从抓点到 6 cm 高的一整列，但仍然只在抓点正上方一条竖线上，手没有水平偏差，也不倾斜。</li>
<li><b>连续体库第一版：</b>先采全部点、再按进度分阶段的第一版（螺母离底座 0.15–0.60 m，16 轮专家轨迹，每格 400 行）。点沿着专家的整条路径连续分布，下降、合爪、搬运都带水平偏差和倾斜；搬运段一直铺到螺母附近，扳手摆放和抓法也更多样。代价是同一类起点里的难度跨度变大，而且点更稀（第 3 节）。</li>
<li><b>全量点库：</b>同一做法放大：螺母离底座放宽到 0.15–0.70 m（旧 v1 库最远到 0.665 m），专家轨迹从 16 轮加到 64 轮（前 16 轮就是第一版那 16 轮），每格 1000 行，偏离路径的宽扰动从 15%×2.0 加到 40%×2.5，共 {AP["total"] if AP else 0} 行。按决定不做逐行专家筛选，所以库里会留下一部分专家也做不完的起点。第 4 节用它从零训练。</li>
</ul>""")

# ================================================================== 3 the two curricula on the all-points bank (stopped)
if STALL:
    C_, E_, TL = STALL["curves"], STALL["evals"], STALL["tail"]
    tb, tt, v1 = TL["bands"], TL["types"], TL["v1_at_same_stage"]
    last_b, last_t = E_["bands"][-1], E_["types"][-1]
    xmax = max(STALL["end"].values()) + 0.3
    rows = [("起点库", "同一份：连续体库第一版，先沿专家整条轨迹采点（d7 物理，13199 行）"),
            ("阶段怎么分", "按“离专家完成还剩多少步”，每 40 步一档，共 14 档", "按起点的语义类型，共 10 级"),
            ("开放顺序", "从离完成最近的一档开始，逐档往远处开；一档里可以同时有好几类起点", "p75 → p50 → p25 → aligned → near → … → pregrasp，一次开一类"),
            ("过线条件", "档内每类起点（该档里行数 ≥20 的）各自 ≥0.7；整档合计 ≥256 个回合、每类 ≥32 个回合，开档后至少 30 次迭代",
             "当前这一类 ≥0.7，最近 256 个回合，开放后至少 30 次迭代"),
            ("新开放阶段的保底抽样", "20% 的回合给最新一档，按类型分（行数的平方根加权）", "20% 的回合给最新一类"),
            ("其余设置", "完全相同：随机初始化、同一训练配方和随机种子、按类型的回合时长上限、每 30 分钟一轮、同一张显卡")]
    trs = "".join(f"<tr><th>{esc(r[0])}</th><td colspan='2'>{esc(r[1])}</td></tr>" if len(r) == 2 else
                  f"<tr><th>{esc(r[0])}</th><td>{esc(r[1])}</td><td>{esc(r[2])}</td></tr>" for r in rows)
    sec.append(f"""<h2>3 新库上的两种课程：按进度分档 vs 按类型解锁（已停止，未出结论）</h2>
<p class='lead'>在连续体库第一版上，同时从零训练两条，只有“课程怎么分阶段”不同。两条在“对准螺母、推进”这一步卡了约 5M 步，为了把显卡让给正在建的全量点库，已经停止。这里记录现象和初步判断，还不能比较两种课程的好坏。后来全量点库上同配方的一条在同一阶段卡了更久，最终突破（第 4 节）。</p>
<table class='tt'><tr><th></th><th>按进度分档</th><th>按类型解锁</th></tr>{trs}</table>
<h3>卡住那一步的训练成功率</h3>
<p class='lead'>横轴是从零训练的环境步数。两条在 0.5–0.7M 步内都过了推进段（p75–p25），之后停在 aligned（开口对准螺母）和 near（拿着扳手在螺母附近）。灰线是补点后的旧库在同一阶段的曲线作参照：旧库 aligned 在开放后 1.3M 步过线。成功率按最近约 300 个训练回合计算（带探索噪声）。</p>
{legend([("按类型解锁：aligned", "var(--s3)", False), ("按进度分档：aligned", "var(--s5)", False), ("按进度分档：near", "var(--s5)", True),
         ("旧库（参照）：aligned", "var(--orig)", False), ("旧库（参照）：near", "var(--orig)", True)])}
{chart("c_stall", [{"name": "按类型：aligned", "color": "var(--s3)", "pts": C_["types_aligned"]},
                   {"name": "按进度：aligned", "color": "var(--s5)", "pts": C_["bands_aligned"]},
                   {"name": "按进度：near", "color": "var(--s5)", "dash": True, "pts": C_["bands_near"]},
                   {"name": "旧库：aligned", "color": "var(--orig)", "pts": C_["v1_aligned"]},
                   {"name": "旧库：near", "color": "var(--orig)", "dash": True, "pts": C_["v1_near"]}],
       0, round(xmax, 1), 0, 1, "从零训练的环境步数（百万步）：第 {x} 百万步", ytick=[0, 0.25, 0.5, 0.7, 1], hlines=[(0.7, "过线 0.7")], h=250)}
<h3>新库上的完整库评测（十类合计）</h3>
{legend([("按类型解锁", "var(--s3)", False), ("按进度分档", "var(--s5)", False)])}
{chart("c_stall_eval", [{"name": "按类型解锁", "color": "var(--s3)", "dots": True, "pts": [(s, a) for s, a, _ in E_["types"]]},
                        {"name": "按进度分档", "color": "var(--s5)", "dots": True, "pts": [(s, a) for s, a, _ in E_["bands"]]}],
       0, round(xmax, 1), 0, 0.5, "从零训练的环境步数（百万步）：第 {x} 百万步", ytick=[0, 0.1, 0.2, 0.3, 0.4, 0.5], h=190)}
<h3>现象</h3>
<ul>
<li><b>推进段很快：</b>p75–p25 两条都在 0.5M 步内学会，训练成功率 0.9 以上，平均 21–25 步就完成。</li>
<li><b>aligned 在涨，但很慢：</b>停止前最后约 1.2M 步，按类型解锁的一条 aligned 训练成功率 {tt["aligned"]["success"]:.2f}，按进度分档的一条 {tb["aligned"]["success"]:.2f}；完整库评测里 aligned 分别是 {last_t[2]["aligned"]:.2f}、{last_b[2]["aligned"]:.2f}。旧库在同一阶段起步也只有 {v1["aligned"]["success"]:.2f}，但开放后 1.3M 步就过了 0.7。</li>
<li><b>near 几乎学不动：</b>按进度分档的一条里 near 训练成功率 {tb["near"]["success"]:.2f}，平均回合 {tb["near"]["mean_steps"]} 步，训练时限是 {STALL["limits"]["v2"]["near"]} 步，几乎每个失败回合都跑满时限。旧库同一阶段 near 成功率 {v1["near"]["success"]:.2f}、平均 {v1["near"]["mean_steps"]} 步。按进度分档要求一档里每类都过线，所以 near 把整档卡住；按类型解锁的一条还没开放到 near。</li>
<li><b>抓姿影响不大：</b>aligned 里首选抓姿 / 可接受抓姿的成功率是 {tb["aligned/preferred"]["success"]:.2f} / {tb["aligned/acceptable"]["success"]:.2f}（按进度）、{tt["aligned/preferred"]["success"]:.2f} / {tt["aligned/acceptable"]["success"]:.2f}（按类型）；near 两者都在 0.06 左右。</li>
</ul>
<h3>初步判断（未验证）</h3>
<ul>
<li><b>新库的这两类起点更难，也更稀：</b>新库 aligned 只有 400 行（旧库 3605 行），同类起点之间最近相距约 3 mm（旧库 0.1 mm，几乎是重复的点）；near 有 1200 行，最近相距约 4 mm（旧库 0.8 mm）。新库里手还带 3–24° 的倾斜，扳手开口离螺母 2–7 cm，比旧库更分散。</li>
<li><b>near 的回合时长偏紧：</b>新库 near 起点的专家要 101–145 步，训练时限 208 步只有专家的约 1.4–2 倍；刚学的时候策略比专家慢，失败回合几乎都是超时。</li>
<li>要确认，需要录一批 aligned / near 失败回合，看是对不准、放不平还是时间不够；这一步还没做。</li>
</ul>""")

# ================================================================== 4 from scratch on the all-points bank (R401)
AR = P.get("allpoints")
if AR and AR["evals"]:
    BT = P["allpoints_bands"]
    NB = len(BT)
    BCATS = ["b00 开始"] + [f"b{k:02d} 开放" for k in range(1, NB)]
    def band_ladder(run):
        ev = sorted((st, int(k[1:])) for k, st in run["events"].items() if k.startswith("b"))
        pts = [(0, 0)] + [(st, b) for st, b in ev]
        return pts + [(run["end"], pts[-1][1])]
    band_rows = "".join(
        f"<tr><td>{k}</td><td class='num'>{v['tau'][0]}–{v['tau'][1] if int(k[1:]) < NB - 1 else '…'}</td><td class='num'>{v['rows']}</td>"
        f"<td>{esc('、'.join(f'{t} {n}' for t, n in sorted(v['types'].items(), key=lambda x: -x[1])))}</td>"
        f"<td>{AR['events'].get(k, '—') if k != 'b00' else 0}</td></tr>" for k, v in BT.items())
    last, EX = AR["last"], P["eval_expert"]
    per_rows = "".join(
        f"<tr><td><span class='dot' style='background:{COLORS[t]}'></span>{t}<div class='sub'>{esc(SHORT[t])}</div></td>"
        f"<td class='num'>{last[t][0]}/{last[t][1]}</td><td class='num' style='color:{'var(--s3)' if last[t][0] / last[t][1] >= 0.9 else 'var(--critical)'}'>{last[t][0] / last[t][1]:.0%}</td>"
        f"<td class='num'>{EX.get(t, 0):.0%}</td></tr>" for t in TASK_ORDER if t in last)
    ev_by = {round(st): a for st, a, _ in AR["evals"]}
    stall_end = AR["events"].get("b03", AR["end"])
    pre = [a for st, a, _ in AR["evals"] if st < stall_end]
    fin = AR["evals"][-1]
    xmax4 = round(AR["end"] + 8)
    sec.append(f"""<h2>4 全量点库从零训练：按进度分档（R401）</h2>
<p class='lead'>用第 3 节按进度分档那一条（R399）的同一套配方，只把起点库换成全量点库（3.7 万行，不做逐行专家筛选），按“离专家完成还剩多少步”每 40 步一档、共 {NB} 档。
训练时长上限 {AR["minutes"]} 分钟用完后停止，共 {AR["end"]:.1f}M 环境步，<b>没有达标</b>（最后一次评测 {fin[1]:.1%}，最差一类 {fin[2]:.0%}），曲线还在上升。
评测和第 3 节相同：连续体库第一版，确定性策略，十类起点各约 50 回合。</p>
<h3>课程开放到第几档</h3>
<p class='lead'>纵轴是已经开放的最远一档（b00 离完成最近，b{NB-1:02d} 是完整任务开头）。一档里每类起点都过 0.7 才开下一档。</p>
{legend([("全量点库（R401）", "var(--s2)", False), (f"连续体库第一版（R399，同配方，{bands['end']:.1f}M 步时停止）", "var(--s5)", True)])}
{chart("c_ap_ladder", [{"name": "全量点库 R401", "color": "var(--s2)", "step": True, "pts": band_ladder(AR)},
                       {"name": "连续体库第一版 R399", "color": "var(--s5)", "step": True, "dash": True, "pts": band_ladder(bands)}],
       0, xmax4, -0.5, NB - 0.5, "从零训练的环境步数（百万步）：第 {x} 百万步", cats=BCATS, h=330,
       vmarks=[(stall_end, "突破对准 / 推进档", "left")])}
<h3>完整库评测（十类合计，同一评测库）</h3>
{legend([("全量点库（R401）", "var(--s2)", False), ("连续体库第一版 · 按进度分档（R399）", "var(--s5)", False), ("连续体库第一版 · 按类型解锁（R400）", "var(--s3)", False)])}
{chart("c_ap_eval", [{"name": "全量点库 R401", "color": "var(--s2)", "dots": True, "pts": [(st, a) for st, a, _ in AR["evals"]]},
                     {"name": "R399 按进度", "color": "var(--s5)", "dots": True, "pts": [(st, a) for st, a, _ in bands["evals"]]},
                     {"name": "R400 按类型", "color": "var(--s3)", "dots": True, "pts": [(st, a) for st, a, _ in tv2["evals"]]}],
       0, xmax4, 0, 1, "从零训练的环境步数（百万步）：第 {x} 百万步", ytick=[0, 0.2, 0.4, 0.6, 0.8, 0.9, 1], hlines=[(0.9, "达标线 0.9")], h=260)}
<h3>最后一次评测（第 {fin[0]:.1f}M 步）各类成功率</h3>
<p class='lead'>右列是专家脚本在同一评测库上抽检的成功率，作为参照：评测库里有一部分起点专家也做不完。</p>
<table class='tt'><tr><th>起点类型</th><th>成功 / 回合</th><th>成功率</th><th>专家（同一评测库）</th></tr>{per_rows}</table>
<details><summary>各档的范围、行数和开放时刻</summary><table class='tt'><tr><th>档</th><th>离完成还剩（步）</th><th>行数</th><th>包含的起点类型（行数）</th><th>开放时刻（M 步）</th></tr>{band_rows}</table></details>
<h3>现象</h3>
<ul>
<li><b>同样在对准 / 推进档卡住，但卡了更久之后突破了：</b>前三档在 {AR["events"].get("b02", 0):.1f}M 步内开放，之后在 b02（aligned、near、p25）停了约 {stall_end - AR["events"].get("b02", 0):.0f}M 步，期间评测一直在 {min(pre):.0%}–{max(pre):.0%}；第 {stall_end:.0f}M 步突破，随后 b03–b05 在 0.6M 步内连开，评测从约 30% 跳到 60%，之后一路涨到 {max(a for _, a, _ in AR["evals"]):.0%}。</li>
<li><b>R399 停得太早，不能说明按进度分档学不会：</b>R401 在 7M 步时评测 {ev_by.get(7, pre[-1]):.0%}，和 R399 停止时（{bands["evals"][-1][0]:.1f}M 步，{bands["evals"][-1][1]:.1%}）几乎一样；但两者用的库不同，R399 继续训会不会同样突破，没有验证。</li>
<li><b>专家做不完的起点，策略不一定做不完：</b>aligned、grasped_far 上策略分别做到 {last["aligned"][0] / last["aligned"][1]:.0%}、{last["grasped_far"][0] / last["grasped_far"][1]:.0%}，专家只有 {EX["aligned"]:.0%}、{EX["grasped_far"]:.0%}。不做逐行专家筛选留下的起点，有不少其实能完成。</li>
<li><b>还没到 90% 的是抓取段：</b>pregrasp、pick_lift、pick_descend、pick_close；它们大部分落在 b07 以后的档里，b07、b08 在 {AR["events"].get("b07", 0):.0f}M 步才开放，b09–b{NB-1:02d}（多数 pregrasp）到停止时还没开放。</li>
</ul>
<p class='cap'>与第 1 节的 v1 库（补点后 + 修正，{full["end"]:.1f}M 步达标）评测库不同，步数不能直接比较。</p>""")

# ================================================================== 5 videos
by = {v["stage"].split()[0]: v for v in VIDEOS}
vv = []
for n in TASK_ORDER:
    if n in by:
        v = by[n]
        vv.append(f"""<h3>从 {n} 出发（{esc(SHORT[n])}）</h3><div class='pair'>
<div><div class='cap'>RL 策略（补点后的库上训练的最终权重）</div><video controls muted loop playsinline preload='metadata' src='{esc(v['rl'])}'></video></div>
<div><div class='cap'>专家脚本（同一个起点）</div><video controls muted loop playsinline preload='metadata' src='{esc(v['expert'])}'></video></div></div>""")
sec.append(f"""<h2>5 同一个起点：RL 策略和专家</h2>
<p class='lead'>每类起点各一组，左边是 RL 策略，右边是专家脚本，从同一个保存的起点出发。按任务顺序从 pregrasp 开始。视频存在 HF 上，打开时需要联网。</p>
{''.join(vv)}""")

style = """.viz-root{color-scheme:light;--surface-1:#fcfcfb;--surface-2:#f1f0ec;--text-primary:#0b0b0b;--text-secondary:#52514e;
 --text-muted:#8a8984;--grid:#e3e2dd;--orig:#9a9993;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#8a63d2;--critical:#d03b3b}
body{margin:0;background:var(--surface-1)}
.viz-root{background:var(--surface-1);color:var(--text-primary);font:14px/1.6 -apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:1400px;margin:0 auto;padding:20px 24px}
h1{font-size:22px;margin:4px 0 8px}h2{font-size:18px;margin:30px 0 6px}h3{font-size:15px;margin:14px 0 4px}
.lead{color:var(--text-secondary);max-width:1050px}ul{max-width:1050px}.cap,.sub{font-size:12px;color:var(--text-secondary)}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--text-secondary);font-size:13px;margin:6px 0;align-items:center}
#stage_legend span{cursor:pointer;user-select:none}#stage_legend span.off{opacity:.3}
.dot{display:inline-block;width:10px;height:10px;border-radius:5px;margin-right:6px;vertical-align:-1px}
.grid3{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;max-width:1300px}
.grad{display:inline-block;width:120px;height:10px;vertical-align:-1px;border-radius:3px;background:linear-gradient(90deg,#3b0f70,#8c2981,#de4968,#fe9f6d,#fcfdbf)}.pair2{display:grid;grid-template-columns:1fr 1fr;gap:6px}
canvas{width:100%;background:#fffdf8;border:1px solid var(--grid);border-radius:6px;display:block}#c3d{cursor:grab;max-width:1100px}
.bankbtn button{margin:4px 6px 8px 0;padding:5px 10px;border:1px solid var(--grid);background:var(--surface-2);border-radius:6px;cursor:pointer;font:inherit}
.bankbtn button.on{background:var(--s1);color:#fff;border-color:var(--s1)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:6px 0 16px;max-width:1100px}.pair video{width:100%;border-radius:6px;background:#000}
table{border-collapse:collapse;margin:6px 0}td,th{border:1px solid var(--grid);padding:4px 10px}.tt th{background:var(--surface-2);text-align:left}
.tt td.num{text-align:right;font-variant-numeric:tabular-nums}
.chart{position:relative;max-width:1000px}.chart .tip{position:absolute;pointer-events:none;background:var(--surface-1);border:1px solid var(--grid);border-radius:6px;padding:4px 8px;font-size:12px;display:none;white-space:nowrap;box-shadow:0 1px 4px #0002}
.svgtext{fill:var(--text-primary)}.svgmuted{fill:var(--text-secondary)}
@media(max-width:1100px){.grid3{grid-template-columns:1fr}}"""
tipjs = """function chartTip(id,D){const box=document.getElementById(id),svg=box.querySelector('svg'),xh=svg.querySelector('.xh'),tip=box.querySelector('.tip');
svg.addEventListener('pointermove',e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*D.W/b.width,m=D.x0+(px-D.l)/(D.W-D.l-D.r)*(D.x1-D.x0);
if(m<D.x0||m>D.x1){xh.setAttribute('visibility','hidden');tip.style.display='none';return}
xh.setAttribute('x1',px);xh.setAttribute('x2',px);xh.setAttribute('visibility','visible');tip.replaceChildren();
const h=document.createElement('div');h.textContent=D.xname.split('：').pop().replace('{x}',m.toFixed(1));tip.appendChild(h);
for(const s of D.series){let best=null;if(s.step){for(const p of s.pts){if(p[0]<=m)best=p}if(m>s.pts[s.pts.length-1][0])best=null}
else{for(const p of s.pts){if(Math.abs(p[0]-m)<=D.tol&&(best===null||Math.abs(p[0]-m)<Math.abs(best[0]-m)))best=p}}
const row=document.createElement('div'),dot=document.createElement('span'),v=document.createElement('b'),n=document.createElement('span');
dot.textContent='● ';dot.style.color=s.color;v.textContent=best?(D.cats?D.cats[best[1]]:best[1].toFixed(D.dec)):'—';n.textContent=' '+s.name;
row.append(dot,v,n);tip.appendChild(row)}
tip.style.display='block';const bx=e.clientX-b.left;tip.style.left=(bx>b.width*0.6?bx-tip.offsetWidth-12:bx+12)+'px';tip.style.top='8px'});
svg.addEventListener('pointerleave',()=>{xh.setAttribute('visibility','hidden');tip.style.display='none'})}"""
distjs = """const P=__PTS__,ORDER=__ORDER__,COL0=__COL__,SHORT=__SHORT__,TASK=ORDER.slice().reverse(),off=new Set();
const GR=['#3b0f70','#57157e','#721f81','#8c2981','#a8327d','#c43c75','#de4968','#f1605d','#fa7f5e','#fe9f6d','#febf84','#fddea0','#fcf4b6','#fcfdbf','#fcfdbf'];
const COL=new Proxy(COL0,{get:(o,k)=>k in o?o[k]:'#999'});const pc=p=>p[3]>=100?GR[p[3]-100]:COL0[ORDER[p[3]]];
const all=Object.values(P).flat(),H=p=>Math.hypot(p[0],p[1]);
const Q=(f,a,b)=>{const v=all.map(f).sort((x,y)=>x-y);const lo=v[Math.floor(v.length*a)],hi=v[Math.floor(v.length*b)],pad=(hi-lo)*0.06;return[lo-pad,hi+pad]};
const R={h:[0,Q(H,0,0.99)[1]],z:[Math.min(-10,Q(p=>p[2],0.01,0.99)[0]),Q(p=>p[2],0.01,0.99)[1]],x:Q(p=>p[0],0.01,0.99),y:Q(p=>p[1],0.01,0.99)};
const nice=(a,b)=>{const st=[10,20,25,50,100,200,250,500].find(s=>(b-a)/s<=5)||1000,o=[];for(let v=Math.ceil(a/st)*st;v<=b;v+=st)o.push(v);return o};
function plot2(cv,pts,fx,fy,rx,ry,lx,ly,equal){const W=cv.clientWidth,Hh=cv.height,r=window.devicePixelRatio||1;cv.width=W*r;cv.height=Hh*r;cv.style.height=Hh+'px';
 const c=cv.getContext('2d');c.scale(r,r);const L=40,Rr=8,T=8,B=30,pw=W-L-Rr,ph=Hh-T-B;let [x0,x1]=rx,[y0,y1]=ry;
 if(equal){const s=Math.max((x1-x0)/pw,(y1-y0)/ph),cx=(x0+x1)/2,cy=(y0+y1)/2;x0=cx-s*pw/2;x1=cx+s*pw/2;y0=cy-s*ph/2;y1=cy+s*ph/2}
 const X=v=>L+(v-x0)/(x1-x0)*pw,Y=v=>T+(1-(v-y0)/(y1-y0))*ph;c.font='10px sans-serif';c.fillStyle='#65695f';c.strokeStyle='#ecebe4';
 for(const vx of nice(x0,x1)){c.beginPath();c.moveTo(X(vx),T);c.lineTo(X(vx),T+ph);c.stroke();c.textAlign='center';c.fillText(vx,X(vx),Hh-B+12)}
 for(const vy of nice(y0,y1)){c.beginPath();c.moveTo(L,Y(vy));c.lineTo(L+pw,Y(vy));c.stroke();c.textAlign='right';c.fillText(vy,L-4,Y(vy)+3)}
 c.save();c.beginPath();c.rect(L,T,pw,ph);c.clip();
 c.textAlign='center';c.fillText(lx,L+pw/2,Hh-4);c.save();c.translate(10,T+ph/2);c.rotate(-Math.PI/2);c.fillText(ly,0,0);c.restore();
 c.fillStyle='#000';c.beginPath();c.arc(X(0),Y(0),3.5,0,7);c.fill();
 for(const p of pts){if(off.has(p[3]))continue;c.globalAlpha=.55;c.fillStyle=pc(p);c.beginPath();c.arc(X(fx(p)),Y(fy(p)),1.8,0,7);c.fill()}c.globalAlpha=1;c.restore()}
let bank3='continuum',yaw=-0.6,pitch=0.35,zoom=1;
function plot3(){const cv=document.getElementById('c3d'),W=cv.clientWidth,Hh=520,r=window.devicePixelRatio||1;cv.width=W*r;cv.height=Hh*r;cv.style.height=Hh+'px';
 const c=cv.getContext('2d');c.scale(r,r);const s=Math.min(W,Hh)/(2*Math.max(-R.x[0],R.x[1],-R.y[0],R.y[1]))*0.95*zoom;
 const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
 const pr=(x,y,z)=>{const a=x*cy-y*sy,b=x*sy+y*cy;return[W/2+a*s,Hh*0.62-(z*cp-b*sp)*s,b*cp+z*sp]};
 c.lineWidth=1;c.font='12px sans-serif';const ax=[[200,0,0,'x 朝前 20 cm'],[0,200,0,'y 朝左 20 cm'],[0,0,100,'z 向上 10 cm']];
 for(const [x,y,z,n] of ax){const o=pr(0,0,0),e=pr(x,y,z);c.strokeStyle='#999';c.beginPath();c.moveTo(o[0],o[1]);c.lineTo(e[0],e[1]);c.stroke();c.fillStyle='#555';c.fillText(n,e[0]+4,e[1])}
 c.strokeStyle='#ddd';for(let g=-300;g<=300;g+=100){let a=pr(g,-300,0),b=pr(g,300,0);c.beginPath();c.moveTo(a[0],a[1]);c.lineTo(b[0],b[1]);c.stroke();a=pr(-300,g,0);b=pr(300,g,0);c.beginPath();c.moveTo(a[0],a[1]);c.lineTo(b[0],b[1]);c.stroke()}
 const q=P[bank3].filter(p=>!off.has(p[3])).map(p=>[...pr(p[0],p[1],p[2]),p[3]]).sort((a,b)=>a[2]-b[2]);
 for(const p of q){c.globalAlpha=.5;c.fillStyle=p[3]>=100?GR[p[3]-100]:COL0[ORDER[p[3]]];c.beginPath();c.arc(p[0],p[1],1.7,0,7);c.fill()}c.globalAlpha=1;
 const o=pr(0,0,0);c.fillStyle='#000';c.beginPath();c.arc(o[0],o[1],5,0,7);c.fill();c.fillText('螺母',o[0]+7,o[1]+14)}
function drawAll(){for(const k in P){plot2(document.getElementById('hd_'+k),P[k],p=>Math.hypot(p[0],p[1]),p=>p[2],R.h,R.z,'离螺母的水平距离 mm','高度 mm',false);
 plot2(document.getElementById('xy_'+k),P[k],p=>p[0],p=>p[1],R.x,R.y,'Δx mm','Δy mm',true)}plot3()}
const lg=document.getElementById('stage_legend');for(const t of TASK){const i=ORDER.indexOf(t),s=document.createElement('span');
 s.innerHTML=`<span class='dot' style='background:${COL0[t]}'></span>${t}（${SHORT[t]}）`;s.onclick=()=>{off.has(i)?off.delete(i):off.add(i);s.classList.toggle('off');drawAll()};lg.append(s)}
for(const b of document.querySelectorAll('#bankbtn button')){if(b.dataset.k==bank3)b.classList.add('on');b.onclick=()=>{bank3=b.dataset.k;
 document.querySelectorAll('#bankbtn button').forEach(x=>x.classList.toggle('on',x===b));plot3()}}
const cv3=document.getElementById('c3d');let drag=null;cv3.onpointerdown=e=>{drag=[e.clientX,e.clientY,yaw,pitch];cv3.setPointerCapture(e.pointerId)};
cv3.onpointermove=e=>{if(!drag)return;yaw=drag[2]+(e.clientX-drag[0])*0.01;pitch=Math.max(-1.5,Math.min(1.5,drag[3]+(e.clientY-drag[1])*0.01));plot3()};
cv3.onpointerup=()=>drag=null;cv3.onwheel=e=>{e.preventDefault();zoom*=e.deltaY<0?1.1:0.9;plot3()};
window.addEventListener('resize',drawAll);drawAll();"""
distjs = (distjs.replace("__PTS__", json.dumps(dist_js)).replace("__ORDER__", json.dumps(ORDER))
          .replace("__COL__", json.dumps(COLORS)).replace("__SHORT__", json.dumps(SHORT, ensure_ascii=False)))
title = "扳手卡螺母：补点前后的训练与起点分布（issue #90）"
doc = f"""<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title>
<style>{style}</style><script>{tipjs}</script><body><div class="viz-root"><h1>{title}</h1>
<p class='lead'>任务：抓起平放的开口扳手，搬到螺母旁，把开口水平推进去卡住螺母再松手。课程从后往前逐级开放起点，从完整任务起点 pregrasp 出发、在完整起点库上评测十类都 ≥90% 算达标。
这一页回答：补点前后训练快慢差多少，补点前后起点分布差在哪，新库上的两种课程卡在哪，全量点库上从零训练走到哪一步，最终策略做出来是什么样。</p>
{''.join(sec)}
<p class='cap'>科研记录（供追溯）：E-10 下，旧做法 = R353–R390，补点后 + 修正 = R396、R398（接续 R391、R395 另见 PR #114），去掉两档 = R397，先采全部点 = R399（按进度）、R400（按类型），全量点库 = R401；观察记录 O-308–O-313。</p>
</div><script>{distjs}</script></body></html>"""
open(OUT, "w").write(doc)
print(OUT, len(doc))
