import base64
def v(f): return '<video controls muted loop autoplay playsinline src="data:video/mp4;base64,%s"></video>' % base64.b64encode(open(f, "rb").read()).decode()
rows = [("起点（续训开始时）", "—", "0.02", "0.13", ""),
        ("种子1 · 最多 10%", "2.5M / 5.7M", "0.63 / 0.78", "0.23 / 0.64", "7.0M 过"),
        ("种子2 · 最多 10%", "2.5M / 5.7M", "0.77 / 0.77", "0.60 / 0.70", "6.2M 过"),
        ("种子2 · 不限", "2.5M / 5.7M / 10.3M", "0.70 / 0.75 / 0.80", "0.33 / 0.53 / 0.73", "12.0M 过"),
        ("种子3 · 最多 10%", "2.5M / 5.7M / 15M", "0.76 / 0.80 / 0.81", "0.53 / 0.64 / 0.73", "没过"),
        ("种子3 · 不限", "2.5M / 5.8M", "0.32 / 0.77", "0.16 / 0.54", "8.6M 过")]
tr = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td></tr>" for a, b, c, d, e in rows)
html = f"""<!doctype html><html lang="zh"><meta charset="utf-8"><title>pull0：快的种子和卡住的种子</title>
<style>body{{font:17px/1.65 -apple-system,"PingFang SC",sans-serif;max-width:1340px;margin:32px auto;padding:0 24px;color:#1c1b18;background:#faf9f6}}
h1{{font-size:28px}}h2{{font-size:22px;margin-top:36px}}table{{border-collapse:collapse;margin:12px 0}}th,td{{padding:8px 14px;border-bottom:1px solid #ddd;text-align:left}}
th{{font-size:16px}}video{{width:100%;border-radius:6px;background:#000}}.cap{{display:flex;justify-content:space-around;font-weight:600;margin:4px 0}}.note{{color:#555;font-size:15px}}
li{{margin:6px 0}}</style>
<h1>pull0（门关着、刚握住把手）：快的种子和卡住的种子有什么共性</h1>
<p>六条从高点续训里，取几个时刻的权重，只在同一组 128 个 pull0 起点上各跑一回合，分别用确定性动作和带探索噪声的动作（训练和过线用的是后者）。</p>
<h2>发现</h2>
<ul>
<li><b>动作上没有"快种子特有的做法"。</b>所有种子、所有时刻，成功都是同一个动作：握着把手先把门拉开约 2–3.5° 再松手；失败也基本是同一个：门还没开就松手，手卡在门边外侧绕不过去。快慢只差在这个动作做得稳不稳。</li>
<li><b>约 1/5 的起点谁都过不了。</b>128 个起点里有 23 个在 7 个较晚的检查点上全部或几乎全部失败，换哪个种子都一样。这些起点手其实没握住把手：两指张开（2.7–4.5 cm，正常握住约 1.1 cm）或手离把手几厘米。门关着时没握住就拉不开，策略也没学会重新抓。</li>
<li><b>这些坏起点来自施力扰动。</b>起点库里 pull0 共 468 个，89 个（19%）两指张开超过 2 cm，全部来自施力扰动生成的那部分（300 个里 83 个，宽扰动 13 个里 6 个）；专家直接截取的 150 个一个也没有。扰动把手从把手上推开，样本仍按规则沿用 pull0 标签。pull_a、pull_b、pull1、pull2 也有 15–17%，但那时门已有缝，没握住也能从门边勾开，所以不影响。</li>
<li><b>所以 pull0 的上限只有约 0.8，过不过线像抽签。</b>确定性成功率最后都停在 0.77–0.81；加上探索噪声是 0.64–0.73，正好贴着过线 0.7。谁先碰到 0.7 主要看运气：种子3 限比例到 15M 带噪声 0.73，训练里读数约 0.6，就一直没过。早期带噪声成功率高低也预测不了谁先过（种子3 限比例 2.5M 时 0.53，比后来过线的种子1、种子2 不限都高）。</li>
</ul>
<p><b>建议（待验证）：</b>pull0 里两指张开、没握住把手的扰动起点去掉，或单列成"重新抓把手"一类。按上面的数据，pull0 上限会到约 0.9 以上，过线不再靠运气。这会改动"扰动样本沿用原标签"的做法，需要你决定。</p>
<h2>每个时刻的成功率（同一组 128 个起点，每个起点一回合）</h2>
<table><tr><th>续训</th><th>时刻（续训后步数）</th><th>确定性动作</th><th>带探索噪声</th><th>训练里过 pull0</th></tr>{tr}</table>
<p class="note">评测种子 9911，所有检查点用同一组起点。只算每个起点的第一回合；按回合数算会偏高，因为成功的回合短、同一时间里跑得多。</p>
<h2>视频</h2>
<h3>1 同一个好起点：快的种子和卡住的种子动作一样</h3><div class="cap"><span>种子2 · 最多 10%，5.7M（6.2M 过线）</span><span>种子3 · 最多 10%，15M（一直没过）</span></div>{v("good_fast_vs_stuck.mp4")}
<p>两边都是先拉开门再松手，绕到门后推开。</p>
<h3>2 同一个坏起点（手离把手 7.6 cm、两指张开）：两个种子都失败</h3><div class="cap"><span>种子2 · 最多 10%，5.7M</span><span>种子3 · 最多 10%，15M</span></div>{v("bad_start_both_fail.mp4")}
<p>没握住把手，门拉不开，手在门边外侧来回，直到超时。</p>
<h3>3 训练早期的典型失败：门没开就松手</h3><div class="cap"><span>种子3 · 不限，2.5M，失败</span><span>同一权重，另一个起点，成功</span></div>{v("early_letgo_vs_pull.mp4")}
<p>左边一开始就松手去找门缝，门关着没有缝，卡在门边外；右边先握着把手把门拉开一点再松手。</p>
"""
open("pull0-seeds.html", "w", encoding="utf-8").write(html)
