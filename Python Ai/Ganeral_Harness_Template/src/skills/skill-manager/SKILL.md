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

本技能指导 Agent 完成其他技能的**创建 → 安装 → 校验 → 检索 → 卸载 → 分配**全流程。

## 硬性约束（必须遵守）

1. **脚本运行环境为当前组织沙箱**：一律用 `execute` 工具执行 `python3`，仅依赖 Python 标准库与系统自带 curl/wget，**禁止 pip install**。
2. **交付目录约定**：新创建/安装的技能统一落在沙箱 `/workspace/dist/<skill-name>/`，**校验（validate）通过后才算成品**，未通过前不得分配。
3. **高风险操作必须确认**：卸载技能、覆盖已有技能前，必须先用自然语言列出影响（目标 agent、目录路径、技能名），**等用户明确回复确认后才执行**。
4. **分配默认主 agent**：用户未指定目标时分配到主 agent（`main`）；允许一次分配给多个 agent。
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

沙箱内脚本目录：`/skills/skill-manager/scripts/`（随技能预装）。若脚本不存在，先用 `read_file` 从宿主映射读取本技能脚本，用 `write_file` 写入沙箱 `/workspace/skill-manager/scripts/` 后再执行，下文统一以 `$SM` 指代脚本所在目录。

```bash
SM=/skills/skill-manager/scripts   # 或 /workspace/skill-manager/scripts
```

## 操作流程

### 1. 创建新技能

1. 与用户确认：技能名（kebab-case）、描述、用途。
2. 执行骨架生成：
   ```bash
   python3 $SM/scaffold.py --name <skill-name> --description "<描述>" \
     --author "<作者>" --tags "tag1,tag2" --output-dir /workspace/dist
   ```
3. 按需用 `write_file` 往 `/workspace/dist/<skill-name>/` 补充脚本与资源。
4. 执行校验（见第 3 节），通过后进入分配流程（见第 5 节）。

### 2. 安装技能

- **GitHub（zip 方式，默认）**：
  ```bash
  python3 $SM/install.py --github <owner>/<repo>[@branch] [--subdir <子目录>] --output-dir /workspace/dist
  ```
  示例：`python3 $SM/install.py --github anthropic/skills@main --subdir pptx`
- **本地 zip / 目录**（用户已上传到沙箱的包）：
  ```bash
  python3 $SM/install.py --local /workspace/xxx.zip --output-dir /workspace/dist
  ```
- 安装脚本会自动执行一次校验并输出结果；失败则按输出修复后重试。
- 技能市场安装：预留配置项 `MARKET_REGISTRY_URL`（当前未实现），用户提及时回复"暂未配置技能市场地址"。

### 3. 校验 / 体检

- 单技能校验：
  ```bash
  python3 $SM/validate.py /workspace/dist/<skill-name> --json
  ```
  退出码 0 = 通过（可能有告警），1 = 有报错。
- 批量体检（对已安装技能或交付目录）：
  ```bash
  python3 $SM/check_all.py /workspace/dist --json
  ```
  输出每个技能的状态（ok/warn/error）与问题清单，整理成中文报告回复用户。

### 4. 检索已安装技能

- 用 `read_file` 读取宿主映射 `/skills/` 下各技能的 SKILL.md（路径以 `/skills/` 开头），或读取索引 `/skills/index.json`（若存在）获取名称、版本、来源、所属 agent。
- 按用户关键词在名称/描述/标签中匹配，列出清单。

### 5. 分配技能给 agent（核心流程）

校验通过后：

1. **列出可选 agent**：GET 后端接口 `GET /api/skills/agents`，拿到注册 agent 列表（含主 agent 标识）。
   沙箱内调用方式（依次尝试可达地址）：
   ```bash
   for H in host.docker.internal gateway.docker.internal 172.17.0.1; do
     curl -fsS -m 5 "http://$H:8088/api/skills/agents" && break
   done
   ```
2. **向用户列出 agent 清单**（主 agent 标注"默认"），询问分配给哪个/哪些 agent；用户不指定则用 `main`。
3. **执行分配**：POST 接口（`overwrite` 仅在用户已明确确认覆盖时传 true）：
   ```bash
   curl -fsS -m 60 -X POST "http://<host>:8088/api/skills/distribute" \
     -H "Content-Type: application/json" \
     -d '{"org_id":"<消息末尾【运行环境】中的org_id>","sandbox_path":"/workspace/dist/<skill-name>","target_agents":["main"],"overwrite":false,"source":"<来源，如 github:owner/repo>"}'
   ```
4. 把每个目标 agent 的分配结果（成功/跳过/失败及原因）如实回复用户。
5. 若沙箱内无法连通后端 API，则把上述 curl 命令原样给出，请用户在宿主机终端执行。

### 6. 卸载技能

1. 先列出将删除的内容（技能名、所在 agent、目录路径），**等用户明确确认**。
2. 目前卸载在宿主机执行：告知用户执行 `rm -rf skills/<agent_dir>/<skill-name>`（主 agent 为 `skills/<skill-name>`），或等待后续卸载 API。
3. 卸载后提醒：索引 `skills/index.json` 会在下次分配/体检时自动校正。

## 错误处理

- validate 报错：按字段提示修复 SKILL.md 后重跑，不得跳过校验直接分配。
- GitHub 下载失败：检查仓库名/分支名（默认 main，可尝试 master），必要时让用户提供 zip。
- distribute 返回 409（目标已存在且未确认覆盖）：回到确认话术，用户同意覆盖后带 `"overwrite":true` 重试。
