---
name: sandbox-file-gen
description: 在沙箱中生成 PPT/Excel/PDF/海报/图片等文件产物，校验后发布下载链接交付用户
version: 1.0.0
author: Prince-AI
tags:
  - sandbox
  - file-generation
  - pptx
  - excel
  - pdf
---

# sandbox-file-gen（沙箱文件生成）

在隔离沙箱中编写并运行生成脚本，产出 PPT / Excel / PDF / 海报 / 图表等文件，发布下载链接交付用户。

## 触发条件

用户明确要求"生成/制作一份文件"，例如：

- 帮我生成/做一份 PPT、Excel 表格、PDF 报告、海报、宣传图
- 画一张图（流程图/示意图/数据图）并给我文件
- 把 xxx 整理成 Excel / PPT 发给我

仅问答、不需要文件产物时不要启用本技能。

## 执行步骤

1. **确认需求**：与用户敲定文件类型、内容大纲、风格/配色、文件名；需求不清时先提问，不要直接开沙箱。
2. **启动沙箱**：调用 `sandbox_task_start(scenario="outputs")`，拿到 `task_id` 与 `workdir`（`/workspace/outputs/{task_id}`）。后续所有文件操作经 `/sandbox/` 路由（如 `write_file` 到 `/sandbox{workdir}/work/xxx.py`），`execute` 命令内使用沙箱内部路径（`{workdir}/...`）。
3. **探测依赖**：`execute` 按需探测，例如 `python3 -c "import pptx, openpyxl, reportlab, matplotlib, PIL; print('ok')"`；缺失的库用 `pip install <pkg>` 安装（装过 apt 系统依赖时收尾须 `destroy=True`）。
4. **编写生成脚本**：把脚本写到 `{workdir}/work/gen_xxx.py`，产物一律输出到 `{workdir}/output/`。
   - PPT 用 `python-pptx`；Excel 用 `openpyxl`；PDF 用 `reportlab`；图表/海报用 `matplotlib`（必须 `matplotlib.use("Agg")`）/ `PIL`。
   - 含中文的图：设置字体 fallback——`plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]`，并 `plt.rcParams["axes_unicode_minus"] = False`。
5. **执行**：`execute("cd {workdir} && python3 work/gen_xxx.py", timeout=180)`。
6. **校验产物**：`execute("ls -l {workdir}/output/")` 确认文件存在且大小 > 0；必要时用脚本重新打开校验（如 `Presentation(path)` 能解析、`openpyxl.load_workbook` 能读）。
7. **发布**：`sandbox_task_publish()`，把返回的下载链接原样回复用户。
8. **收尾**：`sandbox_task_finish(destroy=False)`；仅当装过 apt 系统级依赖时用 `destroy=True`。

## 路径规划

- 输入：`{workdir}/input/`（用户参考材料，经 `sandbox_task_import_file(file_id)` 导入）
- 工作：`{workdir}/work/`（生成脚本与中间产物）
- 产物：`{workdir}/output/`（**只有该目录会被 publish 到 download/**）

## 错误处理

- `execute` 非零退出：阅读回传的 stderr，自动修复脚本后重跑，**最多修复 2 次**；仍失败则如实告知失败原因并 `sandbox_task_finish` 收尾。
- 产物为空或大小为 0：**不得 publish**，回到第 4 步修正脚本重新生成。
- pip 安装失败：换镜像源重试 1 次（`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>`）；仍失败则改用已可用库实现或告知用户。
- 沙箱启动失败/并发满：用 `sandbox_pool_status()` 查询池状态，回复用户稍后重试。

## 产物返回

- 只发布 `output/` 下的最终文件；中间脚本、临时素材不得放入 `output/`。
- 回复格式（`sandbox_task_publish` 已返回现成链接，直接引用即可）：

  `[下载 年度报告.pptx](/api/sandbox/download?path={task_id}/年度报告.pptx&org_id={org_id})`

- 链接中的 `org_id` 取消息末尾【运行环境】中的值；不得伪造链接，publish 返回什么就发什么。
