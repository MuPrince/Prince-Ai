---
name: sandbox-temp-env
description: 在沙箱中临时安装系统/pip 依赖（ffmpeg、latex、指定 pip 包）后执行任务，完成后销毁沙箱不回池
version: 1.0.0
author: Prince-AI
tags:
  - sandbox
  - temp-env
  - pip
  - apt
  - ffmpeg
---

# sandbox-temp-env（沙箱临时环境）

在沙箱中临时安装依赖（pip 包 / apt 系统包，如 ffmpeg、latex），验证可用后执行用户任务，**完成后销毁沙箱**。

## 触发条件

- "装一下 xxx 然后帮我……"
- "需要 ffmpeg / latex / 某个 pip 包才能跑"
- 其他场景（file-gen / debug 等）执行中发现缺系统级依赖，明确需要安装才能继续

只是跑代码、不装依赖时用 sandbox-debug；纯 pip 包即可满足的文件生成优先留在 sandbox-file-gen。

## 执行步骤

1. **启动**：`sandbox_task_start(scenario="env")` → 拿到 `{task_id, workdir}`（`/workspace/env/{task_id}`）。
2. **安装依赖**：
   - pip 包：`execute("pip install <pkg>", timeout=180)`；
   - 系统包：`execute("apt-get update && apt-get install -y <pkg>", timeout=180)`；
   - **单次安装超过 180s 立即中止**该安装项，转入错误处理。
3. **验证安装**：`execute("which ffmpeg && ffmpeg -version | head -1")` 或 `python3 -c "import <pkg>"` 确认可用。
4. **执行任务**：按用户需求写脚本/跑命令，产物输出到 `{workdir}/output/`。
5. **发布**：有产物时 `sandbox_task_publish()`；纯文字结果可跳过。
6. **收尾（关键）**：**必须 `sandbox_task_finish(destroy=True)`**——装过系统依赖的沙箱已"污染"，**销毁后不回池复用**，即使任务失败也要销毁。

## 路径规划

- 输入：`{workdir}/input/`（用户材料经 `sandbox_task_import_file(file_id)` 导入）
- 工作：`{workdir}/work/`（脚本、中间产物、安装日志）
- 产物：`{workdir}/output/`（**只有该目录会被 publish**）

## 错误处理

- **安装超时（>180s）**：中止安装，告知用户该依赖安装超时，可建议更轻量的替代包。
- **apt 无权限/源不可用**：降级为 pip 等价物（如 `apt: ffmpeg` → 静态构建/pip 包装器；`apt: texlive` 过重时建议用户改用 reportlab/weasyprint 方案）；无替代则如实告知无法安装。
- pip 安装失败：换镜像源重试 1 次（`-i https://pypi.tuna.tsinghua.edu.cn/simple`）。
- 任务执行报错：阅读 stderr 自动修复，**最多修复 2 次**。
- **无论成功失败，最后都要 `sandbox_task_finish(destroy=True)`**；漏掉会导致被污染的沙箱回池。

## 产物返回

- 有产物：下载链接（publish 返回的现成链接原样转发）+ 简短说明装了什么、做了什么。
- 无产物：直接回复执行结果文字（stdout 摘要），并说明沙箱已销毁。
