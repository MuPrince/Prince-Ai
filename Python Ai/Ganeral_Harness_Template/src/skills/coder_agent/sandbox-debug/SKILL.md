---
name: sandbox-debug
description: 在沙箱中快速试运行用户代码片段，原样返回 stdout/stderr/exit_code 并协助排错，最轻量不装依赖
version: 1.0.0
author: Prince-AI
tags:
  - sandbox
  - debug
  - run-code
---

# sandbox-debug（沙箱代码调试）

最轻量的沙箱场景：把用户贴的代码放进沙箱跑一次，原样回传运行结果并协助分析，**不安装任何依赖**。

## 触发条件

- "帮我跑一下这段代码 / 测试一下"
- "这段 Python 有没有问题 / 看看会不会报错"
- "这个报错是什么原因"（需要在沙箱复现）

代码依赖沙箱没有的第三方库时，改用 sandbox-temp-env。

## 执行步骤

1. **启动**：`sandbox_task_start(scenario="debug")` → 拿到 `{task_id, workdir}`（`/workspace/debug/{task_id}`）。
2. **危险预检**：代码中含 `rm -rf /`、`dd of=/dev/`、`mkfs`、fork 炸弹、`shutdown/reboot`、覆写块设备等危险操作时，**直接拒绝执行**并向用户说明原因（后端也有安全预检，命中会以 exit_code=126 拒绝）。
3. **写入代码**：`write_file` 把用户代码原样写到 `/sandbox{workdir}/work/main.py`（其他语言按对应解释器命名与执行）。
4. **执行**：`execute("cd {workdir} && python3 work/main.py", timeout=60)`。
5. **如实回复**：原样给出 **stdout、stderr、exit_code**；有报错时附原因分析与修改建议。
6. **修复重跑**：用户要求修复时，改代码后重跑，**最多修复 2 次**；每次改动说明改了什么。
7. **收尾**：`sandbox_task_finish(destroy=False)`。多数情况**无产物，不调用 publish**；仅当代码明确产出文件且用户需要时，才把文件放到 `output/` 再 publish。

## 路径规划

- 输入：`{workdir}/input/`（用户提供的测试数据文件，经 import 导入）
- 工作：`{workdir}/work/`（用户代码 main.py）
- 产物：`{workdir}/output/`（默认留空；有产物才 publish）

## 错误处理

- **超时（60s）**：判定运行超时，提示用户代码可能有死循环/重 IO，建议优化或拆分后重试；不得无限拉长超时。
- **ImportError / ModuleNotFoundError**：本场景**不装依赖**，如实告知缺哪个包，引导用户改用 sandbox-temp-env。
- **危险命令**：拒绝执行并解释，不尝试绕过安全预检。
- 代码自身报错：属于正常调试结果，不算失败——回传 stderr 并给出分析即可。

## 产物返回

- 默认无产物：回复内容 = 运行结果（stdout/stderr/exit_code）+ 分析建议，随后直接 `sandbox_task_finish`。
- 有产物且用户需要时：`sandbox_task_publish()` 后给下载链接，例如
  `[下载 result.txt](/api/sandbox/download?path={task_id}/result.txt&org_id={org_id})`。
