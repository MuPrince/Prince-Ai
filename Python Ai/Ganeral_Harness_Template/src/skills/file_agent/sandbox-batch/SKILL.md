---
name: sandbox-batch
description: 在沙箱中对多个上传文件做批量压缩打包/格式转换/重命名，产物超 5 个自动打 zip 后发布
version: 1.0.0
author: Prince-AI
tags:
  - sandbox
  - batch
  - zip
  - rename
  - convert
---

# sandbox-batch（沙箱批量处理）

把用户上传的多个文件批量导入沙箱，按子类型执行批量压缩、格式转换或重命名，打包后发布下载。

## 触发条件

- 用户上传多个文件并要求"批量压缩 / 打包成 zip"
- "批量转格式"（如一堆 png 转 jpg、heic 转 png）
- "批量重命名"（按规则统一改名）

单文件处理不走本技能（转格式用 sandbox-doc-convert，生成用 sandbox-file-gen）。

## 执行步骤

1. **识别子类型**：`compress`（批量压缩打包）/ `convert`（批量格式转换）/ `rename`（批量重命名）。
2. **启动**：`sandbox_task_start(scenario="batch")` → 拿到 `{task_id, workdir}`（`/workspace/batch/{task_id}`）。
3. **逐个导入**：对每个 `file_id` 调 `sandbox_task_import_file(file_id)`，全部落到 `{workdir}/input/`；`ls` 核对文件数与用户上传数一致。
4. **按子类型执行**（产物一律放 `{workdir}/output/`）：
   - **compress**：`execute("cd {workdir} && zip -r output/打包结果.zip input/", timeout=300)`（或 `tar -czf output/打包结果.tar.gz -C . input/`）。
   - **convert**：图片批量用 `mogrify -format jpg input/*.png -path output/`（无 ImageMagick 时用 PIL 写 Python 循环逐个转换）；其他格式用对应库，逐个输出到 `output/`。
   - **rename**：**先生成"原文件名 → 新文件名"映射表发给用户确认**，确认后再写脚本按映射 `cp` 到 `output/新文件名`；未确认前不得执行。
5. **自动打包**：产物文件数 **>5 个**时，在 `output/` 内打一个 zip（如 `批量结果.zip`），便于用户一次下载。
6. **总量检查**：`execute("du -sm {workdir}/output/")`，**总产物 >200MB 时拒绝发布**，告知用户分批处理。
7. **发布**：`sandbox_task_publish()`，回复下载链接 + 处理结果清单。
8. **收尾**：`sandbox_task_finish(destroy=False)`。

## 路径规划

- 输入：`{workdir}/input/`（批量上传的原始文件）
- 工作：`{workdir}/work/`（转换/重命名脚本、映射表）
- 产物：`{workdir}/output/`（**只有该目录会被 publish**）

## 错误处理

- **单文件失败**（损坏/格式不支持）：记录到失败清单，跳过并继续处理其余文件；最终如实汇报"成功 N 个 / 失败 M 个（附清单）"，不得因单个失败中止整批。
- **总产物 >200MB**：不 publish，回复用户超出限制，建议分多批处理。
- `execute` 非零退出：阅读 stderr 自动修复，**最多修复 2 次**。
- rename 映射表用户未确认：暂停执行，等待确认；用户修改映射后按新表执行。

## 产物返回

- 下载链接（>5 个产物时以 zip 为主，零散文件可一并列出），附处理结果清单：成功数量、失败清单及原因。
- 链接示例：`[下载 批量结果.zip](/api/sandbox/download?path={task_id}/批量结果.zip&org_id={org_id})`
