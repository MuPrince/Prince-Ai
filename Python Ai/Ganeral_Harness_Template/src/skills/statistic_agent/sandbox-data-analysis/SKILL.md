---
name: sandbox-data-analysis
description: 在沙箱中用 pandas/matplotlib 分析用户上传的 CSV/Excel 数据，输出统计结论、透视表与图表
version: 1.0.0
author: Prince-AI
tags:
  - sandbox
  - data-analysis
  - pandas
  - matplotlib
---

# sandbox-data-analysis（沙箱数据分析）

把用户上传的数据文件导入沙箱，用 pandas 探查与分析，产出图表与汇总表，并给出中文结论要点。

## 触发条件

- 用户上传 CSV / Excel / JSON 等数据文件，要求"分析一下 / 统计 / 画图 / 透视 / 看趋势"
- 对已有数据做汇总、分组对比、相关性、分布、占比等分析

用户没给数据文件时先请其上传；纯文字问答不启用本技能。

## 执行步骤

1. **启动**：`sandbox_task_start(scenario="analysis")` → 拿到 `{task_id, workdir}`（`/workspace/analysis/{task_id}`）。
2. **导入数据**：对用户消息中的每个 `file_id` 调 `sandbox_task_import_file(file_id)`，文件落到 `{workdir}/input/`。
3. **探查数据**：写探查脚本（`{workdir}/work/explore.py`）读取 input/，输出 shape、dtypes、head、缺失值、描述统计，据此与用户确认分析口径。
   - 文件 **>50MB 时先采样**：`pd.read_csv(path, nrows=100000)` 或 `df.sample(n=100000, random_state=42)`，并在结论中注明"基于采样"。
4. **编写分析脚本**：写到 `/sandbox{workdir}/work/analysis.py`：
   - `matplotlib` 必须 `matplotlib.use("Agg")`（无显示环境）。
   - 中文字体 fallback：`plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]`，`plt.rcParams["axes_unicode_minus"] = False`。
   - 图表存 `{workdir}/output/*.png`（`dpi=150`, `bbox_inches="tight"`）；透视/汇总表存 `{workdir}/output/summary.xlsx` 或 `.csv`。
5. **执行**：`execute("cd {workdir} && python3 work/analysis.py", timeout=300)`。
6. **校验产物**：`ls -l {workdir}/output/` 确认图表与汇总表非空。
7. **发布**：`sandbox_task_publish()`，回复 3-5 条中文结论要点 + 下载链接。
8. **收尾**：`sandbox_task_finish(destroy=False)`。

## 路径规划

- 输入：`{workdir}/input/`（上传文件经 import 落在这里）
- 工作：`{workdir}/work/`（探查/分析脚本、中间结果）
- 产物：`{workdir}/output/`（**只有该目录会被 publish**）

## 错误处理

- `execute` 非零退出：stderr 已随结果回传，阅读后自动修复重跑，**最多修复 2 次**。常见问题：
  - 编码错误：`read_csv(..., encoding="utf-8")` 与 `"gbk"` 轮换试；
  - 内存不足：改 `chunksize` 分块聚合，或加大采样比例；
  - 列名不符：回到第 3 步打印 `df.columns` 对齐后再改。
- **总执行超时 300s**：超时后缩小数据规模（采样/分块）重跑，不得无限拉长超时。
- 产物为空：**不得 publish**；分析做不出来要如实说明数据问题（如关键列缺失、全部为 null）。
- 沙箱不可用/并发满：`sandbox_pool_status()` 查询后请用户稍后重试。

## 产物返回

- 图表 PNG + 汇总 CSV/XLSX 的下载链接（publish 返回的现成链接原样转发），配 3-5 条中文结论要点。
- 结论必须基于脚本真实输出，禁止编造数字；采样分析的结论需注明采样规模。

  链接格式示例：`[下载 销售趋势.png](/api/sandbox/download?path={task_id}/销售趋势.png&org_id={org_id})`
