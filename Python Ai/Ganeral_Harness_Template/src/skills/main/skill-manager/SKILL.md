---
name: skill-manager
description: 技能全生命周期管理——创建新技能、从 GitHub/本地安装、校验体检、检索卸载，以及把校验完成的技能分配给指定 agent
version: 1.0.0
author: Prince-AI
tags:
  - skill
  - management
  - meta
---

# skill-manager（技能管理技能）

本技能指导 Agent 完成其他技能的**创建 → 安装 → 校验 → 打包发布 → 检索 → 卸载 → 分配**全流程。

## 硬性约束（必须遵守）

1. **脚本运行环境为当前组织沙箱**：一律用 `execute` 工具执行 `python3`，仅依赖 Python 标准库与系统自带 curl/wget，**禁止 pip install**。
2. **交付目录约定**：新创建/安装的技能统一落在当前沙箱 dist 任务的 `{workdir}/output/<skill-name>/`（`workdir` 由 `sandbox_task_start(scenario="dist")` 返回），**四步校验通过并打包发布后才算成品**，未通过前不得分配。
3. **高风险操作必须确认**：卸载技能、覆盖已有技能前，必须先用自然语言列出影响（目标 agent、目录路径、技能名），**等用户明确回复确认后才执行**。
4. **分配默认主 agent**：用户未指定目标时分配到主 agent（`main`）；允许一次分配给多个 agent。技能最终路径为 `src/skills/{agent_name}/{skill_name}/`。
5. **不主动提及本技能**：只有当用户明确表达"创建技能/安装技能/管理技能/校验技能/分配技能"等意图时才启用。

## 前置：技能目录结构规范

一个标准技能目录结构如下：

```
<skill-name>/
├── SKILL.md          # 必需：指令文档，含 YAML frontmatter
├── scripts/          # 可选：脚本工具
└── templates/ 等      # 可选：其他资源目录
```

SKILL.md 的 frontmatter 字段规范：

| 字段 | 级别 | 说明 |
|---|---|---|
| `name` | **必填** | 技能名，须与目录名一致（小写字母/数字/中划线） |
| `description` | **必填** | 一句话描述技能用途与触发场景 |
| `version` | 推荐 | 语义化版本，如 1.0.0 |
| `author` | 推荐 | 作者/维护方 |
| `tags` | 推荐 | 标签列表，便于检索 |

缺必填项 = 校验报错；缺推荐项 = 告警。

## 本技能脚本位置

沙箱内脚本目录：`/skills/main/skill-manager/scripts/`（随技能预装）。若脚本不存在，先用 `read_file` 从宿主映射读取本技能脚本，用 `write_file` 写入沙箱 `/workspace/skill-manager/scripts/` 后再执行，下文统一以 `$SM` 指代脚本所在目录。

```bash
SM=/skills/main/skill-manager/scripts   # 或 /workspace/skill-manager/scripts
```

## 操作流程

### 1. 创建新技能

1. 与用户确认：技能名（kebab-case）、描述、用途。
2. 启动 dist 场景沙箱任务：
   ```
   sandbox_task_start(scenario="dist")   # 返回 task_id 与 workdir（如 /workspace/dist/<task_id>）
   ```
3. 执行骨架生成（输出到工作目录的 `output/` 下）：
   ```bash
   python3 $SM/scaffold.py --name <skill-name> --description "<描述>" \
     --author "<作者>" --tags "tag1,tag2" --output-dir {workdir}/output
   ```
4. 按需用 `write_file` 往 `{workdir}/output/<skill-name>/` 补充脚本与资源。
5. 执行四步校验（见第 3 节）。
6. **打包并发布**：`skill_package("<skill-name>")` 在沙箱内把 `{workdir}/output/<skill-name>/` 打包为 `<skill-name>.zip` → 调用 `sandbox_task_publish()` 落盘到 `download/{task_id}/` 并取得下载链接 → 调用 `sandbox_task_finish()` 释放沙箱。
7. 进入分配流程（见第 5 节）。

### 2. 安装技能

- **GitHub（zip 方式，默认）**：
   ```bash
   python3 $SM/install.py --github <owner>/<repo>[@branch] [--subdir <子目录>] --output-dir {workdir}/output
   ```
   示例：`python3 $SM/install.py --github anthropic/skills@main --subdir pptx`
- **本地 zip / 目录**（用户已上传到沙箱的包）：
   ```bash
   python3 $SM/install.py --local /workspace/xxx.zip --output-dir {workdir}/output
   ```
- 安装脚本会自动执行一次校验并输出结果；失败则按输出修复后重试。
- 安装完成后同样需通过第 3 节四步校验，再按第 1 节第 6 步打包发布。
- 技能市场安装：预留配置项 `MARKET_REGISTRY_URL`（当前未实现），用户提及时回复"暂未配置技能市场地址"。

### 3. 校验 / 体检（四步校验）

技能发布前必须依次通过以下四步校验，任一步失败都要修复后重跑：

1. **格式校验**：`python3 $SM/validate.py {workdir}/output/<skill-name> --json`，退出码 0 = 通过（可能有告警），1 = 有报错。
2. **功能验证**：执行技能自带示例脚本（如 `python3 {workdir}/output/<skill-name>/scripts/example.py`），确认可正常运行、无异常退出。
3. **产物校验**：检查脚本产物是否生成且格式正确、可正常打开（如 PDF/图片能预览、zip 能解包）。
4. **安全检查**：扫描技能脚本是否含危险命令（`rm -rf`、`dd`、`mkfs`、网络外联等），并核对 SKILL.md 声明的 `allowed_tools` 白名单，仅保留最小权限。

批量体检（对已安装技能或交付目录）：

```bash
python3 $SM/check_all.py {workdir}/output --json
```

输出每个技能的状态（ok/warn/error）与问题清单，整理成中文报告回复用户。

### 4. 检索已安装技能

- 用工具 `skill_list(agent)` 列出指定 agent（或全部 agent）下已安装技能的名称/版本/描述；也可用 `read_file` 读取宿主映射 `/skills/{agent_name}/{skill_name}/SKILL.md`，或读取索引 `/skills/index.json`（若存在）。
- 按用户关键词在名称/描述/标签中匹配，列出清单。

### 5. 分配技能（核心流程）

四步校验通过并打包发布（见第 1 节第 6 步）后，用内部工具 `skill_distribute` 完成分配给指定 agent：

1. **列出目标 agent 并询问用户**：调用工具 `skill_list_agents()` 得到全部 agent（如 `["main"]`），用自然语言列出可用 agent，**等用户明确回复要分配到哪个（可多个）agent**。
2. **执行分配**：用户确认后调用
   ```
   skill_distribute(skill_name="<skill-name>", task_id="<task_id>", target_agents=["main"], overwrite=False)
   ```
   工具从 `download/{task_id}/<skill-name>.zip` 解压安装到 `src/skills/{agent_name}/{skill_name}/`（防目录穿越），并更新 `src/skills/index.json`。
3. **回复结果**：
   - `installed`：列出已安装的 agent 与最终路径，如实告知用户。
   - `conflicts`：目标目录已存在且 `overwrite=False` 时被跳过的 agent（含原因与路径）；询问用户是否覆盖，同意后带 `overwrite=True` 重试。
4. **失败处理**：返回 `error` 时如实告知原因（找不到 zip 包 / 名称非法 / zip 条目越界 / 安装失败），不得伪造结果；按提示修复后可重试。

### 6. 卸载技能

1. 先列出将删除的内容（技能名、所在 agent、目录路径），**等用户明确确认**。
2. 目前卸载在宿主机执行：告知用户执行 `rm -rf src/skills/{agent_name}/<skill-name>`（如 `src/skills/main/pptx`），或等待后续卸载能力。
3. 卸载后提醒：索引 `src/skills/index.json` 会在下次分配时自动校正。

## 错误处理

- validate 报错：按字段提示修复 SKILL.md 后重跑，不得跳过校验直接打包或分配。
- GitHub 下载失败：检查仓库名/分支名（默认 main，可尝试 master），必要时让用户提供 zip。
- 安全检查未过：技能脚本含危险命令或超出 `allowed_tools` 白名单，先删改到最小权限后重跑。
- distribute 返回 `conflicts`（目标目录已存在且 `overwrite=False`）：回到确认话术，用户同意覆盖后带 `overwrite=True` 重试；返回 `error`（找不到 zip 包 / zip 条目越界等）时按提示修复后重试。
