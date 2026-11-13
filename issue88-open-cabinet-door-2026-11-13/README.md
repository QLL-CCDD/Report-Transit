# 开柜门 open_cabinet_door（a2r #88）

单任务 RL 补齐拉门与换手中间起点后的训练与诊断。代码：Shiki42/a2r PR #120；科研记录：E-10 的 E10-R334–R339、O-277–O-280。

## 报告（单文件 HTML，直接用浏览器打开）

| 文件 | 内容 |
| --- | --- |
| [index.html](index.html) | 主报告：课程阶梯、起点俯视卡片、成功率曲线（横轴环境步数）、续训重复与新阶段采样比例对照、RL / 专家视频 |
| [pull0-diagnosis.html](pull0-diagnosis.html) | pull0（刚合爪、门还关着）为什么卡住：失败阶段分类与代表回合 |
| [pull0-seeds.html](pull0-seeds.html) | 快 / 慢种子在动作上有没有共性：逐起点成功率、坏起点来源、三段并排视频 |

## 结论（pull0-seeds）

- 各种子成功都是同一个动作：握着把手把门拉开约 2–3.5° 后松手；失败是门没开就松手，卡在门边外侧。
- 128 个固定起点里 23 个在 7 个较晚的检查点上都失败。这些起点两指张开 2.7–4.5 cm 或手离把手几厘米，全部来自施力扰动。起点库 pull0 中这类起点占 19%（89/468）。
- 确定性成功率上限约 0.8；带噪声 0.64–0.73，贴着 0.7 的解锁线，谁先过线接近运气。

## analysis/

- `data/pull0_first_episode.csv`：26 次评测（13 个检查点 × 确定性 / 带噪声）× 128 个起点，每个起点只取第一回合。列有成功、用时、卡住阶段、起点门角 / 两指间距 / 手到把手距离、松手时刻与此时门角、结束时手到把手距离。
- `scripts/`
  - 评测作业：`diag_pull0.sh`、`diag2.sh`、`diag3.sh`，任务列表 `jobs*.txt`；在节点 e 上运行。
  - 统计：`ana2–6.py`；导出 CSV：`export.py`。
  - 报告生成：`mk_pull0_seeds.py`、`mk_ablation.py`；在 Mac 上运行。
- `videos/`：pull0-seeds 里的三段并排视频。

完整逐步轨迹（phases.json，共 93 MB）和评测原始输出在节点 e 的 `/dev/shm/e10-door88/diag-seeds/`，未上传。
