"""
Skill 全生命周期工具（Agent 可见）。

覆盖 Skill 从创建到分配的关键环节：
- skill_list_agents：列出全部可用 agent（用于询问用户分配目标）
- skill_list：扫描技能根目录，列出已安装技能（读 SKILL.md frontmatter）
- skill_package：在当前 dist 沙箱任务内把 output/<skill-name>/ 打包为 <skill-name>.zip
- skill_distribute：从 download/{task_id}/<skill-name>.zip 解压安装到 skills/{agent}/{skill_name}/

路径约定：技能根目录 src/skills/（LOCAL_SKILLS_DIR），结构为 skills/{agent_name}/{skill_name}/；
索引 skills/index.json 仅在分配成功后增量维护，检索以目录扫描为准，不依赖索引。
"""
import json
import logging
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

from langchain_core.tools import tool

from agent.backends.sandbox import DOWNLOAD_ROOT, SandboxTask, get_sandbox_pool
from agent.backends.sandbox_pool_backend import get_current_task_id
from agent.config.constants import LOCAL_SKILLS_DIR
from agent.tools.sandbox_tools import (
    _active_tasks,
    _active_tasks_lock,
    _workdir,
)

logger = logging.getLogger(__name__)

# 名称安全校验：仅允许字母数字、中划线、下划线，防目录穿越
_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

# 技能索引文件：src/skills/index.json（附加索引，非检索唯一来源）
_INDEX_PATH = LOCAL_SKILLS_DIR / "index.json"


# ----------------------------------------------------------------------
# 通用辅助
# ----------------------------------------------------------------------
def _is_safe_name(name: str) -> bool:
    """名称是否安全（匹配 ^[A-Za-z0-9_\\-]+$，防目录穿越）。"""
    return bool(name) and bool(_NAME_RE.match(name))


def _parse_frontmatter(text: str) -> Dict[str, object]:
    """解析 SKILL.md 顶部 YAML frontmatter（仅标准库，不依赖 PyYAML）。

    仅支持 `key: value` 与 `- item` 列表两种形式，足够覆盖技能元数据。
    返回字段字典，无有效 frontmatter 时返回空字典。
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}

    fields: Dict[str, object] = {}
    current_key: Optional[str] = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        if m:
            current_key = m.group(1)
            value = m.group(2).strip()
            fields[current_key] = value if value else []
        elif line.strip().startswith("- ") and current_key:
            if not isinstance(fields.get(current_key), list):
                fields[current_key] = []
            fields[current_key].append(line.strip()[2:].strip())
    return fields


def _read_skill_meta(skill_md: Path) -> Dict[str, str]:
    """读取技能 SKILL.md，返回 {name, version, description}（缺失字段为空串）。"""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"skill_tools: 读取 SKILL.md 失败 {skill_md} - {e}")
        return {"name": "", "version": "", "description": ""}

    fields = _parse_frontmatter(text)

    def _as_str(key: str) -> str:
        value = fields.get(key, "")
        return value if isinstance(value, str) else ""

    return {
        "name": _as_str("name"),
        "version": _as_str("version"),
        "description": _as_str("description"),
    }


def _resolve_active_task() -> Optional[SandboxTask]:
    """解析当前上下文绑定的活跃沙箱任务（供 skill_package 定位 dist 任务）。

    与 sandbox_tools._resolve_current_task 同思路：读 ContextVar 中的 task_id
    再查活跃任务登记表，命中则返回任务对象。
    """
    task_id = get_current_task_id()
    if not task_id:
        return None
    with _active_tasks_lock:
        return _active_tasks.get(task_id)


# ----------------------------------------------------------------------
# 索引维护（index.json 附加索引）
# ----------------------------------------------------------------------
def _load_index() -> Dict[str, List[dict]]:
    """读取技能索引 index.json；文件不存在或损坏时返回空索引（容错重建）。"""
    if not _INDEX_PATH.is_file():
        return {"skills": []}
    try:
        data = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("skills"), list):
            return {"skills": data["skills"]}
        logger.warning(f"skill_tools: 索引结构异常，将重建 {_INDEX_PATH}")
    except (OSError, ValueError) as e:
        logger.warning(f"skill_tools: 索引文件损坏，将重建 {_INDEX_PATH} - {e}")
    return {"skills": []}


def _write_index(index: Dict[str, List[dict]]) -> None:
    """写回技能索引（ensure_ascii=False, indent=2）。"""
    _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _update_index_entry(
    agent: str, name: str, version: str, description: str
) -> Dict[str, List[dict]]:
    """写入/更新一条索引条目（同 agent+name 去重覆盖），返回最新索引。"""
    index = _load_index()
    skills = [
        s
        for s in index["skills"]
        if not (
            isinstance(s, dict) and s.get("agent") == agent and s.get("name") == name
        )
    ]
    skills.append(
        {
            "name": name,
            "agent": agent,
            "version": version,
            "description": description,
            "installed_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    index = {"skills": skills}
    _write_index(index)
    return index


# ----------------------------------------------------------------------
# zip 解包安全校验
# ----------------------------------------------------------------------
def _scan_zip_members(
    zip_path: Path, skill_name: str, dest_root: Path
) -> Tuple[List[Tuple[str, str, bool]], Optional[str]]:
    """校验 zip 全部条目并计算安装相对路径。

    返回 (成员列表[(条目名, 相对路径, 是否目录)], 错误信息或 None)。
    发现绝对路径 / 目录穿越 / 逃逸目标目录的条目即整体中止。
    归档结构与 make_archive 产物一致：顶层目录为 <skill-name>/，安装时剥离该前缀。
    """
    try:
        zf = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as e:
        return [], f"无法读取 zip 包: {e}"

    dest_root = dest_root.resolve()
    members: List[Tuple[str, str, bool]] = []
    with zf:
        for info in zf.infolist():
            raw = info.filename
            is_dir = raw.endswith("/")
            cleaned = raw.rstrip("/")
            if not cleaned:
                continue

            posix = PurePosixPath(cleaned)
            # 拒绝绝对路径与显式目录穿越
            if posix.is_absolute() or ".." in posix.parts:
                return [], f"zip 内存在非法路径条目: {raw}"

            parts = posix.parts
            # 剥离顶层 <skill-name>/ 前缀
            if parts and parts[0] == skill_name:
                parts = parts[1:]
            if not parts:
                continue

            rel = PurePosixPath(*parts)
            # 归一化后必须仍在目标目录内（防 zip-slip）
            final = (dest_root / rel).resolve()
            try:
                final.relative_to(dest_root)
            except ValueError:
                return [], f"zip 内条目逃逸目标目录: {raw}"

            members.append((raw, rel.as_posix(), is_dir))
    return members, None


# ----------------------------------------------------------------------
# Agent 可见工具
# ----------------------------------------------------------------------
@tool
def skill_list_agents() -> dict:
    """列出技能根目录下全部可用 agent（用于询问用户把技能分配到哪个 agent）。

    Returns:
        {"agents": ["main", ...]}；根目录不存在时返回空列表。
    """
    if not LOCAL_SKILLS_DIR.is_dir():
        return {"agents": []}
    agents = [entry.name for entry in sorted(LOCAL_SKILLS_DIR.iterdir()) if entry.is_dir()]
    return {"agents": agents}


@tool
def skill_list(agent: str = "") -> dict:
    """扫描技能根目录，列出已安装技能（名称/所属 agent/版本/描述）。

    Args:
        agent: 可选，指定 agent 名（如 "main"）；为空时扫描全部 agent。

    Returns:
        {"skills": [{"name","agent","version","description"}, ...]}；失败返回 {"error": ...}。
    """
    if agent and not _is_safe_name(agent):
        return {"error": f"非法 agent 名称: {agent}"}

    if agent:
        agent_dirs = [LOCAL_SKILLS_DIR / agent]
    elif LOCAL_SKILLS_DIR.is_dir():
        agent_dirs = [d for d in LOCAL_SKILLS_DIR.iterdir() if d.is_dir()]
    else:
        agent_dirs = []

    skills: List[Dict[str, str]] = []
    for agent_dir in sorted(agent_dirs):
        if not agent_dir.is_dir():
            continue
        for skill_dir in sorted(agent_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            meta = _read_skill_meta(skill_md)
            skills.append(
                {
                    "name": meta.get("name") or skill_dir.name,
                    "agent": agent_dir.name,
                    "version": meta.get("version") or "",
                    "description": meta.get("description") or "",
                }
            )
    return {"skills": skills}


@tool
def skill_package(skill_name: str) -> dict:
    """在当前活跃的 dist 沙箱任务内，把 output/<skill-name>/ 打包为 <skill-name>.zip。

    Args:
        skill_name: 技能名（与沙箱 output/ 下子目录同名，如 "my-skill"）。

    Returns:
        {"package": "<skill-name>.zip", "path": ..., "message": ...}；失败返回 {"error": ...}。
        打包成功后请调用 sandbox_task_publish 发布产物，再调用 sandbox_task_finish 释放沙箱。
    """
    if not _is_safe_name(skill_name):
        return {"error": f"非法 skill 名称: {skill_name}"}

    task = _resolve_active_task()
    if task is None:
        return {"error": '当前没有活跃的沙箱任务，请先调用 sandbox_task_start(scenario="dist")'}

    pool = get_sandbox_pool()
    entry = pool.get_task_entry(task.task_id)
    if entry is None:
        return {"error": "任务绑定的沙箱已释放，请重新启动 dist 场景任务"}

    workdir = _workdir(task.scenario, task.task_id)
    skill_dir = f"{workdir}/output/{skill_name}"

    # 1) 校验技能目录存在
    resp = entry.backend.execute(f"test -d {skill_dir}", timeout=30)
    if getattr(resp, "exit_code", 1) != 0:
        return {"error": f"技能目录不存在: {skill_dir}（请确认已在沙箱内创建/下载技能）"}

    # 2) 优先用 Python 标准库打包（沙箱可能没有 zip 命令）
    package_name = f"{skill_name}.zip"
    cmd = (
        f"cd {workdir}/output && "
        f"python3 -c \"import shutil; shutil.make_archive('{skill_name}', 'zip', '{skill_name}')\""
    )
    resp = entry.backend.execute(cmd, timeout=120)
    if getattr(resp, "exit_code", 1) != 0:
        return {"error": f"沙箱内打包失败: {getattr(resp, 'output', '')}"}

    # 3) 校验 zip 非空
    verify = (
        f"ls -l {workdir}/output/{package_name} && "
        f"test -s {workdir}/output/{package_name}"
    )
    resp = entry.backend.execute(verify, timeout=30)
    if getattr(resp, "exit_code", 1) != 0:
        return {"error": f"打包产物为空或不存在: {package_name}"}

    logger.info(f"skill_package: {skill_name} -> {package_name}")
    return {
        "package": package_name,
        "path": f"{workdir}/output/{package_name}",
        "message": f"已打包为 {package_name}，请调用 sandbox_task_publish 发布后再 finish。",
    }


@tool
def skill_distribute(
    skill_name: str,
    task_id: str,
    target_agents: List[str],
    overwrite: bool = False,
) -> dict:
    """把 download/{task_id}/<skill-name>.zip 解压安装到 skills/{agent}/{skill_name}/ 并更新索引。

    Args:
        skill_name: 技能名（与 zip 包名一致，如 "my-skill"）。
        task_id: 沙箱任务 ID（zip 包已由 sandbox_task_publish 落盘到 download/{task_id}/）。
        target_agents: 目标 agent 名列表（可多个，如 ["main"]）。
        overwrite: 目标目录已存在时是否覆盖；False 时冲突项跳过并记入 conflicts。

    Returns:
        {"installed": [...], "conflicts": [...], "index": {...}}；失败返回 {"error": ...}。
    """
    if not _is_safe_name(skill_name):
        return {"error": f"非法 skill 名称: {skill_name}"}
    if not _is_safe_name(task_id):
        return {"error": f"非法 task_id: {task_id}"}
    if not target_agents:
        return {"error": "target_agents 不能为空，请先用 skill_list_agents 确认目标 agent"}
    for agent in target_agents:
        if not _is_safe_name(agent):
            return {"error": f"非法 agent 名称: {agent}"}

    zip_path = DOWNLOAD_ROOT / task_id / f"{skill_name}.zip"
    if not zip_path.is_file():
        return {"error": f"找不到技能包: {zip_path}（请先 sandbox_task_publish 落盘）"}

    # 一次性校验 zip 全部条目（越界即整体中止，不安装任何 agent）
    anchor_dest = (LOCAL_SKILLS_DIR / target_agents[0] / skill_name).resolve()
    members, err = _scan_zip_members(zip_path, skill_name, anchor_dest)
    if err:
        return {"error": err}

    installed: List[Dict[str, str]] = []
    conflicts: List[Dict[str, str]] = []
    index: Dict[str, List[dict]] = _load_index()

    for agent in target_agents:
        dest = LOCAL_SKILLS_DIR / agent / skill_name

        # 冲突处理：目录已存在且未允许覆盖则跳过该 agent
        if dest.exists() and not overwrite:
            conflicts.append(
                {
                    "agent": agent,
                    "path": str(dest),
                    "reason": "目标目录已存在且 overwrite=False",
                }
            )
            continue

        try:
            with zipfile.ZipFile(zip_path) as zf:
                if overwrite and dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                for entry_name, rel, is_dir in members:
                    target = dest / rel
                    if is_dir:
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(entry_name) as src:
                        target.write_bytes(src.read())
        except Exception as e:
            # 安装失败：清理残留的半成品目录
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return {"error": f"安装到 agent={agent} 失败: {e}"}

        # 安装成功后更新索引
        meta = _read_skill_meta(dest / "SKILL.md")
        index = _update_index_entry(
            agent=agent,
            name=meta.get("name") or skill_name,
            version=meta.get("version") or "",
            description=meta.get("description") or "",
        )
        installed.append({"agent": agent, "path": str(dest)})

    logger.info(
        f"skill_distribute: {skill_name} installed={len(installed)} conflicts={len(conflicts)}"
    )
    return {"installed": installed, "conflicts": conflicts, "index": index}


# 对外暴露的工具列表（main_agnet 注册用）
SKILL_TOOLS = [skill_list_agents, skill_list, skill_package, skill_distribute]
