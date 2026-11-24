# 宽范围配对对照：spec:kitchen/open_kettle_lid

改前 `/home/zyl5090/e10-kettle-lid-t12-20261124/wide/bd9300a2/wide`（bd9300a201e2e1dca538cee0d0ac4a940f668c9e），改后 `/home/zyl5090/e10-kettle-lid-t12-20261124/wide/1c8e1a36/wide`（1c8e1a368cca2d9b81193eff75471d22582ca61c）；同种子 ['3201', '3202', '3203']，每种子各轮 env 数 [[128], [128], [128]]，放置最大差 0.000 mm。行记作 `种子/r轮:env`，成功按 `success`（与 validate.md 同口径）。

| 集合 | 分母 | 改前成功 | 改后成功 |
|---|---|---|---|
| 各自有效起点 | 102 / 102 | 99 | 99 |
| 共同有效起点 | 102 | 99 | 99 |

共同有效起点上挽回 0：无
共同有效起点上损失 0：无

**净下降 0（损失 0 − 挽回 0），容差 2（分母 102 的 1%，向上取整，至少 1）：在容差内。**

只在改前有效 0：无；只在改后有效 0：无。

SUMMARY pair --wide spec:kitchen/open_kettle_lid /home/zyl5090/e10-kettle-lid-t12-20261124/wide/bd9300a2/wide -> /home/zyl5090/e10-kettle-lid-t12-20261124/wide/1c8e1a36/wide: common valid 102, success 99 -> 99, rescued 0, lost 0, net decline 0 (tolerance 2, within)

