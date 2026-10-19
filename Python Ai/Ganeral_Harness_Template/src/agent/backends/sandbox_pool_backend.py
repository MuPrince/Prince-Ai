"""
沙箱池 Backend：实现 deepagents SandboxBackendProtocol，将操作委托给池内沙箱。

设计要点：
- 实现 SandboxBackendProtocol 全部方法（ls/read/grep/glob/write/edit/delete/upload/download/execute）
- P0-1 任务级绑定：引入任务上下文后，同一 task_id 的所有 backend 调用
  都路由到池内同一个 _SandboxEntry，直到显式 finish（release_task）才释放
- 无任务上下文时的单次操作：临时申请沙箱，操作完成后立即释放（不持久化产物）
- 危险命令正则预检：rm -rf /、dd、mkfs 等直接拒绝
"""
import asyncio
import logging
import re
import threading
from contextvars import ContextVar
from typing import List, Optional

from deepagents.backends.protocol import (
    DeleteResult,
    EditResult,
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
    GlobResult,
    GrepResult,
    LsResult,
    ReadResult,
    SandboxBackendProtocol,
    WriteResult,
)

from agent.backends.sandbox import get_sandbox_pool, SandboxTask

logger = logging.getLogger(__name__)

# 上下文变量：跟踪当前任务的 org_id 和 task_id
_current_org_id: ContextVar[str] = ContextVar("current_org_id", default="default_org")
_current_task_id: ContextVar[Optional[str]] = ContextVar("current_task_id", default=None)

# org_id -> 当前活跃 task_id 的兜底映射。
# 由于 LangGraph 在线程池中执行工具时 ContextVar 不一定会回传，
# 工具内设置的 task_id 通过该映射对同 org 的后续 backend 调用可见。
# 注意：同一 org 并发多个任务时以最近 start 的任务为准（单任务 org 场景无影响）。
_org_active_task: dict = {}
_org_active_task_lock = threading.Lock()

# 危险命令正则预检：命中即拒绝执行
_DANGEROUS_PATTERNS = [
    re.compile(r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+(/|/\*|~|\$HOME)(\s|$)"),  # rm -rf /
    re.compile(r"\bdd\b[^|;&]*\bof=/dev/"),          # dd 写块设备
    re.compile(r"\bmkfs(\.\w+)?\b"),                  # 格式化文件系统
    re.compile(r"\b(fdisk|parted|sfdisk)\b"),         # 分区操作
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;:"),      # fork 炸弹
    re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"),  # 关机重启
    re.compile(r">\s*/dev/sd[a-z]"),                  # 覆写块设备
    re.compile(r"\bchmod\s+-R\s+777\s+/(\s|$)"),      # 递归放权根目录
]


def _is_dangerous_command(command: str) -> bool:
    """判断命令是否命中危险模式。"""
    return any(p.search(command) for p in _DANGEROUS_PATTERNS)


class SandboxPoolBackend(SandboxBackendProtocol):
    """
    沙箱池 Backend：将 deepagents 的文件/执行操作路由到池内沙箱。

    P0-1：当任务上下文存在（task_id 已绑定），所有操作复用同一沙箱 entry；
    仅当任务显式 finish（SandboxPool.release_task）时才释放回池。
    """

    def __init__(self):
        self._pool = get_sandbox_pool()

    @property
    def id(self) -> str:
        return "sandbox-pool-backend"

    # ------------------------------------------------------------------
    # 内部工具：获取/释放沙箱
    # ------------------------------------------------------------------
    def _resolve_bound_backend(self):
        """
        P0-1：解析当前任务绑定的沙箱 backend。
        优先读 ContextVar 中的 task_id，其次读 org 级活跃任务映射。
        命中则返回池内同一 entry 的 backend；未绑定返回 None。
        """
        task_id = _current_task_id.get()
        if task_id:
            entry = self._pool.get_task_entry(task_id)
            if entry is not None:
                entry.touch()
                return entry.backend

        org_id = _current_org_id.get()
        with _org_active_task_lock:
            mapped_task_id = _org_active_task.get(org_id)
        if mapped_task_id:
            entry = self._pool.get_task_entry(mapped_task_id)
            if entry is not None:
                entry.touch()
                return entry.backend
        return None

    def _run_with_sandbox(self, op_name: str, func, *args, **kwargs):
        """
        通用执行模板：
        - 已绑定任务（P0-1）：直接在绑定的沙箱 entry 上执行，不申请不释放
        - 未绑定任务：临时申请一个沙箱执行，完成后立即释放（不持久化产物）
        """
        bound = self._resolve_bound_backend()
        if bound is not None:
            try:
                return func(bound, *args, **kwargs)
            except Exception as e:
                logger.error(f"SandboxPoolBackend: {op_name} 执行异常 - {e}")
                return _error_result(op_name, str(e))

        # 无任务上下文：临时申请，单次操作后立即释放
        org_id = _current_org_id.get()
        task = SandboxTask(org_id=org_id)
        backend = self._pool.submit_task(task)
        if backend is None:
            logger.warning(f"SandboxPoolBackend: 无可用沙箱 org={org_id}")
            return _error_result(op_name, "沙箱不可用或并发已满")

        try:
            return func(backend, *args, **kwargs)
        except Exception as e:
            logger.error(f"SandboxPoolBackend: {op_name} 执行异常 - {e}")
            return _error_result(op_name, str(e))
        finally:
            # 单次操作立即释放回池（不持久化产物）
            try:
                self._pool.release_task(task, destroy=False)
            except Exception as e:
                logger.error(f"SandboxPoolBackend: 临时沙箱释放异常 - {e}")

    # ------------------------------------------------------------------
    # SandboxBackendProtocol 实现
    # ------------------------------------------------------------------
    def execute(self, command: str, *, timeout: Optional[int] = None) -> ExecuteResponse:
        """在沙箱中执行 shell 命令（危险命令预检后拒绝）。

        非零退出时 stderr 包含在 output 中回传，由 LLM 读取后自动修复重试
        （重试次数上限见 SANDBOX_EXECUTE_MAX_RETRIES，由工具提示约束）。
        """
        if _is_dangerous_command(command):
            logger.warning(f"SandboxPoolBackend: 危险命令被拒绝: {command}")
            return ExecuteResponse(
                output=f"危险命令被拒绝执行（安全预检命中）: {command}",
                exit_code=126,
            )

        def _do_execute(backend):
            if timeout is not None:
                return backend.execute(command, timeout=timeout)
            return backend.execute(command)

        result = self._run_with_sandbox("execute", _do_execute)
        if isinstance(result, ExecuteResponse):
            return result
        return ExecuteResponse(output=result.get("error", "unknown error"), exit_code=1)

    async def aexecute(self, command: str, *, timeout: Optional[int] = None) -> ExecuteResponse:
        """异步执行 shell 命令。"""
        return await asyncio.to_thread(self.execute, command, timeout=timeout)

    def ls(self, path: str) -> LsResult:
        """列出目录内容。"""
        def _do_ls(backend):
            return backend.ls(path)

        result = self._run_with_sandbox("ls", _do_ls)
        if isinstance(result, LsResult):
            return result
        return LsResult(error=result.get("error", "unknown error"))

    async def als(self, path: str) -> LsResult:
        return await asyncio.to_thread(self.ls, path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        """读取文件内容。"""
        def _do_read(backend):
            return backend.read(file_path, offset, limit)

        result = self._run_with_sandbox("read", _do_read)
        if isinstance(result, ReadResult):
            return result
        return ReadResult(error=result.get("error", "unknown error"))

    async def aread(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        return await asyncio.to_thread(self.read, file_path, offset, limit)

    def write(self, file_path: str, content: str) -> WriteResult:
        """写入文件。"""
        def _do_write(backend):
            return backend.write(file_path, content)

        result = self._run_with_sandbox("write", _do_write)
        if isinstance(result, WriteResult):
            return result
        return WriteResult(error=result.get("error", "unknown error"))

    async def awrite(self, file_path: str, content: str) -> WriteResult:
        return await asyncio.to_thread(self.write, file_path, content)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """编辑文件（精确字符串替换）。"""
        def _do_edit(backend):
            return backend.edit(file_path, old_string, new_string, replace_all)

        result = self._run_with_sandbox("edit", _do_edit)
        if isinstance(result, EditResult):
            return result
        return EditResult(error=result.get("error", "unknown error"))

    async def aedit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        return await asyncio.to_thread(self.edit, file_path, old_string, new_string, replace_all)

    def delete(self, file_path: str) -> DeleteResult:
        """删除文件或目录。"""
        def _do_delete(backend):
            return backend.delete(file_path)

        result = self._run_with_sandbox("delete", _do_delete)
        if isinstance(result, DeleteResult):
            return result
        return DeleteResult(error=result.get("error", "unknown error"))

    async def adelete(self, file_path: str) -> DeleteResult:
        return await asyncio.to_thread(self.delete, file_path)

    def grep(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        *,
        max_count: Optional[int] = None,
    ) -> GrepResult:
        """搜索文件内容。"""
        def _do_grep(backend):
            if max_count is not None:
                return backend.grep(pattern, path, glob, max_count=max_count)
            return backend.grep(pattern, path, glob)

        result = self._run_with_sandbox("grep", _do_grep)
        if isinstance(result, GrepResult):
            return result
        return GrepResult(error=result.get("error", "unknown error"))

    async def agrep(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        *,
        max_count: Optional[int] = None,
    ) -> GrepResult:
        return await asyncio.to_thread(self.grep, pattern, path, glob, max_count=max_count)

    def glob(self, pattern: str, path: Optional[str] = None) -> GlobResult:
        """按 glob 模式查找文件。"""
        def _do_glob(backend):
            return backend.glob(pattern, path)

        result = self._run_with_sandbox("glob", _do_glob)
        if isinstance(result, GlobResult):
            return result
        return GlobResult(error=result.get("error", "unknown error"))

    async def aglob(self, pattern: str, path: Optional[str] = None) -> GlobResult:
        return await asyncio.to_thread(self.glob, pattern, path)

    def upload_files(self, files: List[tuple[str, bytes]]) -> List[FileUploadResponse]:
        """上传文件到沙箱。"""
        def _do_upload(backend):
            return backend.upload_files(files)

        result = self._run_with_sandbox("upload_files", _do_upload)
        if isinstance(result, list) and all(isinstance(r, FileUploadResponse) for r in result):
            return result
        return [FileUploadResponse(path=f[0], error=result.get("error", "unknown error")) for f in files]

    async def aupload_files(self, files: List[tuple[str, bytes]]) -> List[FileUploadResponse]:
        return await asyncio.to_thread(self.upload_files, files)

    def download_files(self, paths: List[str]) -> List[FileDownloadResponse]:
        """从沙箱下载文件。"""
        def _do_download(backend):
            return backend.download_files(paths)

        result = self._run_with_sandbox("download_files", _do_download)
        if isinstance(result, list) and all(isinstance(r, FileDownloadResponse) for r in result):
            return result
        return [FileDownloadResponse(path=p, error=result.get("error", "unknown error")) for p in paths]

    async def adownload_files(self, paths: List[str]) -> List[FileDownloadResponse]:
        return await asyncio.to_thread(self.download_files, paths)


# ----------------------------------------------------------------------
# 沙箱任务上下文管理（供工具 / chat_service 调用）
# ----------------------------------------------------------------------
def _error_result(op_name: str, error_msg: str) -> dict:
    """构造统一错误结果。"""
    return {"operation": op_name, "error": error_msg}


def set_sandbox_context(org_id: str, task_id: Optional[str] = None):
    """设置当前沙箱上下文（由 chat_service 在调用 Agent 前设置 org_id）。"""
    _current_org_id.set(org_id)
    _current_task_id.set(task_id)


def bind_task_context(org_id: str, task_id: str):
    """绑定任务上下文（由 sandbox_task_start 工具调用）。

    同时写入 ContextVar 与 org 级映射，保证后续 backend 调用无论
    是否在同一个 ContextVar 上下文中都能路由到绑定的沙箱 entry。
    """
    _current_task_id.set(task_id)
    with _org_active_task_lock:
        _org_active_task[org_id] = task_id


def unbind_task_context(org_id: str, task_id: str):
    """解绑任务上下文（由 sandbox_task_finish / 兜底清理调用）。"""
    _current_task_id.set(None)
    with _org_active_task_lock:
        if _org_active_task.get(org_id) == task_id:
            _org_active_task.pop(org_id, None)


def get_current_org_id() -> str:
    """读取当前上下文的 org_id。"""
    return _current_org_id.get()


def get_current_task_id() -> Optional[str]:
    """读取当前上下文绑定的 task_id（ContextVar 优先，其次 org 级映射）。"""
    task_id = _current_task_id.get()
    if task_id:
        return task_id
    org_id = _current_org_id.get()
    with _org_active_task_lock:
        return _org_active_task.get(org_id)


def clear_sandbox_context():
    """清除沙箱上下文。"""
    _current_task_id.set(None)
