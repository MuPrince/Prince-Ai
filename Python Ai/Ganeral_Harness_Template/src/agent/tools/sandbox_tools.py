"""
沙箱任务生命周期工具（Agent 可见）。

5 个工具覆盖沙箱任务完整生命周期：
- sandbox_task_start        申请沙箱并创建标准工作目录（input/work/output）
- sandbox_task_import_file  将用户上传文件导入沙箱工作目录 input/
- sandbox_task_publish      把 output/ 产物持久化到 download/ 并返回下载链接
- sandbox_task_finish       释放沙箱（可选销毁），任务级绑定解除
- sandbox_pool_status       查询沙箱池状态

路径约定（每个工作目录内分 input/、work/、output/ 三个子目录，仅 output/ 会被 publish）：
| 场景       | scenario | 沙箱工作目录                 | 本地持久化          |
| 文件生成   | outputs  | /workspace/outputs/{task_id}/ | download/{task_id}/ |
| Skill 管理 | dist     | /workspace/dist/{task_id}/    | download/{task_id}/ |
| 数据分析   | analysis | /workspace/analysis/{task_id}/| download/{task_id}/ |
| 格式转换   | convert  | /workspace/convert/{task_id}/ | download/{task_id}/ |
| Skill 测试 | debug    | /workspace/debug/{task_id}/   | download/{task_id}/ |
| 批量处理   | batch    | /workspace/batch/{task_id}/   | download/{task_id}/ |
| 临时环境   | env      | /workspace/env/{task_id}/     | download/{task_id}/ |
"""
import logging
import threading
from contextvars import ContextVar
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.tools import tool

from agent.backends.sandbox import SandboxTask, get_sandbox_pool
from agent.backends.sandbox_pool_backend import (
    bind_task_context,
    get_current_org_id,
    get_current_task_id,
    unbind_task_context,
)
from agent.config.config import SANDBOX_TASK_WAIT_TIMEOUT

logger = logging.getLogger(__name__)

# 支持的场景标识集合
SCENARIOS = {"outputs", "dist", "analysis", "convert", "debug", "batch", "env"}

# task_id -> SandboxTask：活跃任务登记表，finish / 兜底清理时移除
_active_tasks: Dict[str, SandboxTask] = {}
_active_tasks_lock = threading.Lock()

# 每次聊天流的任务清单：chat_service 在流开始前重置，finally 中兜底释放
_context_tasks: ContextVar[Optional[List[SandboxTask]]] = ContextVar(
    "sandbox_context_tasks", default=None
)


def _workdir(scenario: str, task_id: str) -> str:
    """按场景约定生成沙箱工作目录。"""
    return f"/workspace/{scenario}/{task_id}"


def _resolve_current_task() -> Optional[SandboxTask]:
    """解析当前上下文绑定的活跃任务。"""
    task_id = get_current_task_id()
    if not task_id:
        return None
    with _active_tasks_lock:
        return _active_tasks.get(task_id)


def _register_task(task: SandboxTask):
    """登记活跃任务，并追加到当前聊天流的任务清单（用于 finally 兜底）。"""
    with _active_tasks_lock:
        _active_tasks[task.task_id] = task
    tracked = _context_tasks.get()
    if tracked is not None:
        tracked.append(task)


def _unregister_task(task: SandboxTask):
    """移除活跃任务登记，并解除 P0-1 任务级绑定。"""
    with _active_tasks_lock:
        _active_tasks.pop(task.task_id, None)
    unbind_task_context(task.org_id, task.task_id)


def _build_download_urls(task: SandboxTask, download_dir: Path) -> List[str]:
    """按约定格式生成本地产物的下载链接（仅列实际落盘的文件）。"""
    if not download_dir.exists():
        return []
    urls = []
    for file in sorted(download_dir.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(download_dir).as_posix()
        name = file.name
        urls.append(
            f"[下载 {name}](/api/sandbox/download?"
            f"path={task.task_id}/{rel}&org_id={task.org_id})"
        )
    return urls


def _list_sandbox_output_files(task: SandboxTask) -> List[str]:
    """列出沙箱 output/ 目录下的产物文件（相对路径）。"""
    pool = get_sandbox_pool()
    entry = pool.get_task_entry(task.task_id)
    if entry is None:
        return []
    output_dir = f"{_workdir(task.scenario, task.task_id)}/output"
    resp = entry.backend.execute(f"find {output_dir} -type f", timeout=60)
    if getattr(resp, "exit_code", 1) != 0:
        return []
    base = output_dir.rstrip("/")
    files = []
    for line in (getattr(resp, "output", "") or "").splitlines():
        line = line.strip()
        if not line:
            continue
        rel = line[len(base):].lstrip("/") if line.startswith(base) else line
        files.append(rel)
    return files


@tool
def sandbox_task_start(scenario: str, need_network: bool = False) -> dict:
    """启动一个沙箱任务：申请沙箱并创建标准工作目录（input/、work/、output/）。

    Args:
        scenario: 场景标识，必须是 outputs(文件生成)/dist(Skill管理)/analysis(数据分析)/
                  convert(格式转换)/debug(Skill测试)/batch(批量处理)/env(临时环境) 之一。
                  env 场景在 finish 时应使用 destroy=True 销毁沙箱不回池。
        need_network: 是否需要网络访问（保留参数，当前镜像默认联网能力由沙箱配置决定）。

    Returns:
        {"task_id": ..., "workdir": ...}；失败返回 {"error": ...}。
        启动后，对 /sandbox/ 路径的所有文件/执行操作都会绑定到同一沙箱，
        直到调用 sandbox_task_finish。execute 命令非零退出时请阅读 stderr 自动修复，
        最多重试 2 次；产物完成后务必调用 sandbox_task_publish 与 sandbox_task_finish。
    """
    if scenario not in SCENARIOS:
        return {"error": f"非法场景 scenario={scenario}，可选值: {sorted(SCENARIOS)}"}

    pool = get_sandbox_pool()
    if not pool.available:
        return {"error": "沙箱服务不可用，请稍后重试"}

    org_id = get_current_org_id()
    task = SandboxTask(org_id=org_id, scenario=scenario)
    workdir = _workdir(scenario, task.task_id)
    # 只有 output/ 子目录会被 publish / 持久化
    task.sandbox_output_path = f"{workdir}/output"

    # P0-3：并发满时入队等待，超时返回 None
    backend = pool.submit_task(task, wait=True, timeout=SANDBOX_TASK_WAIT_TIMEOUT)
    if backend is None:
        return {
            "error": f"沙箱并发已满且等待 {SANDBOX_TASK_WAIT_TIMEOUT}s 超时，请稍后重试"
        }

    # 创建标准工作目录 input/、work/、output/
    resp = backend.execute(f"mkdir -p {workdir}/input {workdir}/work {workdir}/output", timeout=60)
    if getattr(resp, "exit_code", 1) != 0:
        # 目录创建失败：立即释放，避免泄漏
        pool.release_task(task, destroy=True)
        return {
            "error": f"沙箱工作目录创建失败: {getattr(resp, 'output', '')}"
        }

    # P0-1：绑定任务上下文，后续 backend 调用路由到同一沙箱 entry
    bind_task_context(org_id, task.task_id)
    _register_task(task)
    logger.info(f"sandbox_task_start: task_id={task.task_id} scenario={scenario} org={org_id}")
    return {"task_id": task.task_id, "workdir": workdir}


@tool
def sandbox_task_import_file(file_id: str) -> dict:
    """将用户上传的文件导入当前沙箱任务的工作目录 input/ 子目录。

    Args:
        file_id: 用户上传文件时返回的文件 ID。

    Returns:
        {"sandbox_path": ...}；失败返回 {"error": ...}。
    """
    task = _resolve_current_task()
    if task is None:
        return {"error": "当前没有活跃的沙箱任务，请先调用 sandbox_task_start"}

    # 延迟导入避免循环依赖（api_view -> agent）
    from api_view.services import file_service

    try:
        data, filename = file_service.read_upload(file_id)
    except FileNotFoundError:
        return {"error": f"上传文件不存在: {file_id}"}
    except Exception as e:
        return {"error": f"读取上传文件失败: {e}"}

    pool = get_sandbox_pool()
    entry = pool.get_task_entry(task.task_id)
    if entry is None:
        return {"error": "任务绑定的沙箱已释放，请重新启动任务"}

    workdir = _workdir(task.scenario, task.task_id)
    sandbox_path = f"{workdir}/input/{filename}"
    results = entry.backend.upload_files([(sandbox_path, data)])
    if results and getattr(results[0], "error", None):
        return {"error": f"导入沙箱失败: {results[0].error}"}

    logger.info(f"sandbox_task_import_file: file_id={file_id} -> {sandbox_path}")
    return {"sandbox_path": sandbox_path}


@tool
def sandbox_task_publish(files: Optional[List[str]] = None) -> dict:
    """把当前沙箱任务 output/ 目录的产物持久化到本地，并返回下载链接。

    Args:
        files: 可选，仅发布指定文件（相对 output/ 的路径列表）；
               为空时发布 output/ 下全部产物。产物为空时不发布。

    Returns:
        {"download_urls": [...], "files": [...]}；产物为空或失败返回 {"error"/"message"}。
    """
    task = _resolve_current_task()
    if task is None:
        return {"error": "当前没有活跃的沙箱任务，请先调用 sandbox_task_start"}

    # 产物为空不 publish
    remote_files = _list_sandbox_output_files(task)
    if files:
        wanted = set(files)
        remote_files = [f for f in remote_files if f in wanted]
    if not remote_files:
        return {"message": "产物为空，未发布任何文件", "download_urls": [], "files": []}

    pool = get_sandbox_pool()
    try:
        download_dir = pool.persist_task(task)
    except Exception as e:
        return {"error": f"产物持久化失败: {e}"}

    urls = _build_download_urls(task, download_dir)
    logger.info(f"sandbox_task_publish: task_id={task.task_id} files={len(urls)}")
    return {"download_urls": urls, "files": remote_files}


@tool
def sandbox_task_finish(destroy: bool = False) -> dict:
    """结束当前沙箱任务：持久化产物并释放沙箱（解除任务级绑定）。

    Args:
        destroy: True 时销毁沙箱不回池（用于 env 临时环境场景）；
                 False 时正常释放回池复用，并自动持久化 output/ 产物。

    Returns:
        {"ok": True}；失败返回 {"error": ...}。
    """
    task = _resolve_current_task()
    if task is None:
        return {"error": "当前没有活跃的沙箱任务"}

    pool = get_sandbox_pool()
    ok = pool.release_task(task, destroy=destroy)
    _unregister_task(task)
    logger.info(f"sandbox_task_finish: task_id={task.task_id} destroy={destroy} ok={ok}")
    if not ok:
        return {"error": "沙箱释放失败（任务绑定关系已清理）"}
    return {"ok": True}


@tool
def sandbox_pool_status() -> dict:
    """查询沙箱池当前状态：忙碌 / 空闲沙箱数与等待队列长度。

    Returns:
        {"busy": ..., "idle": ..., "queue_len": ..., "max_concurrent": ...}
    """
    status = get_sandbox_pool().get_status()
    return {
        "busy": status["busy"],
        "idle": status["idle"],
        "queue_len": status["queue_len"],
        "max_concurrent": status["max_concurrent"],
        "available": status["available"],
    }


# ----------------------------------------------------------------------
# chat_service 兜底：流结束 / 异常时释放本次会话遗留的沙箱任务
# ----------------------------------------------------------------------
def begin_context_tracking():
    """开始跟踪本次聊天流创建的沙箱任务（在调用 Agent 前调用）。"""
    _context_tasks.set([])


def cleanup_context_tasks():
    """兜底释放本次聊天流中未显式 finish 的沙箱任务，并清理跟踪状态。"""
    tracked = _context_tasks.get() or []
    pool = get_sandbox_pool()
    for task in list(tracked):
        with _active_tasks_lock:
            still_active = task.task_id in _active_tasks
        if not still_active:
            continue
        logger.warning(
            f"sandbox_tools: 聊天流结束但任务未 finish，兜底释放 task_id={task.task_id}"
        )
        try:
            pool.release_task(task, destroy=False)
        except Exception as e:
            logger.error(f"sandbox_tools: 兜底释放异常 task_id={task.task_id} - {e}")
        _unregister_task(task)
    _context_tasks.set(None)


# 对外暴露的工具列表（main_agnet 注册用）
SANDBOX_TOOLS = [
    sandbox_task_start,
    sandbox_task_import_file,
    sandbox_task_publish,
    sandbox_task_finish,
    sandbox_pool_status,
]
