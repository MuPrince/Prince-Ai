---
name: sandbox-doc-convert
description: 在沙箱中把 Markdown 等文档转换为 PDF/Word(docx)/HTML，注入 CJK 字体防中文乱码后发布下载
version: 1.0.0
author: Prince-AI
tags:
  - sandbox
  - doc-convert
  - markdown
  - pandoc
  - weasyprint
---

# sandbox-doc-convert（沙箱文档格式转换）

在沙箱中用 pandoc / weasyprint 将 Markdown 文档转换为 PDF、Word(docx)、HTML，并保证中文正常显示。

## 触发条件

- "把这段 Markdown 转成 PDF / Word / HTML"
- "这个 md 文件帮我转 docx / pdf"
- 其他轻量文档格式互转（md ↔ html ↔ docx）

## 执行步骤

1. **启动**：`sandbox_task_start(scenario="convert")` → 拿到 `{task_id, workdir}`（`/workspace/convert/{task_id}`）。
2. **确定输入来源**（三选一）：
   - 用户直接贴的正文 → `write_file` 写到 `/sandbox{workdir}/input/source.md`；
   - 用户上传的文件 → `sandbox_task_import_file(file_id)`，落到 `{workdir}/input/`；
   - 前序沙箱任务的产物 → 沙箱之间不共享文件，需请用户重新上传，或回到对应场景重新生成后再转。
3. **选择转换器**：
   - md → docx / html：优先 `pandoc`（先 `which pandoc` 探测）；缺失时 `pip install pypandoc-binary`，用 `pypandoc` 在 Python 内转换。
   - md → pdf：优先 `pandoc` 直出；不可用时降级为 `weasyprint`（先 md → html，再 html → pdf）。
4. **中文防乱码**：目标为 HTML/PDF 时，在中间 HTML 的 `<style>` 注入 CJK 字体 CSS：

   ```css
   body { font-family: "Noto Sans CJK SC", "WenQuanYi Zen Hei", "Microsoft YaHei", sans-serif; }
   ```

   pandoc 走 `--standalone --css` 或模板注入；weasyprint 直接把 CSS 写进 HTML。
5. **执行**：`execute("cd {workdir} && <转换命令>", timeout=180)`，产物输出到 `{workdir}/output/`。
6. **校验产物**：文件非空；PDF 用 `pypdf` 读页数 ≥1，docx 用 `python-docx` 能打开，HTML 抽查无方块字。
7. **发布**：`sandbox_task_publish()`，回复下载链接。
8. **收尾**：`sandbox_task_finish(destroy=False)`（仅 pip 级安装可回池；装过 apt 系统包则 `destroy=True`）。

## 路径规划

- 输入：`{workdir}/input/`（源 md / 上传文件）
- 工作：`{workdir}/work/`（中间 HTML、CSS、转换脚本）
- 产物：`{workdir}/output/`（**只有该目录会被 publish**）

## 错误处理

- `pandoc: command not found`：`pip install pypandoc-binary` 后改用 `pypandoc` 重试。
- PDF 中文变方块/乱码：回到第 4 步补齐 CJK 字体 CSS；pandoc 可显式指定 `--pdf-engine=weasyprint`。
- 转换报错：阅读 stderr 自动修复（语法/路径/编码），**最多修复 2 次**；仍失败如实告知。
- 产物为空：**不得 publish**。

## 产物返回

- 转换后文件的下载链接（publish 返回什么发什么），并注明源格式 → 目标格式。

  示例：`[下载 报告.pdf](/api/sandbox/download?path={task_id}/报告.pdf&org_id={org_id})`
