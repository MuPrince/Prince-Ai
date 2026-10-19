"""
沙箱池管理：按 org_id 隔离，支持并发任务、等待队列、产物持久化到 download/。

设计要点：
- 最大并发 64 任务，超出进入 FIFO 等待队列
- 沙箱状态：空闲中 / 忙碌中
- 任务完成后产物持久化到本地 download/{task_id}/
- download/ 内容 1 小时后自动清理
- 空闲沙箱 10 分钟无操作后销毁

P0 修复：
- P0-2 _persist_outputs 真实拷贝：先在沙箱内 tar 打包，再 download_files 拿字节流，
  本地解压到 download/{task_id}/；tar 失败降级为逐文件 download_files；失败重试 1 次
- P0-3 等待队列 Future 唤醒：SandboxTask 携带 threading.Event，submit_task(wait=True)
  并发满时入队阻塞，worker 分配成功后 event.set() 唤醒，超时返回 None
- release_task(destroy=)：支持销毁沙箱不回池（用于临时环境场景）
- _task_index：task_id -> _SandboxEntry 映射，支撑 P0-1 任务级绑定路由
"""
import io
import logging
import shutil
import tarfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from queue import Queue, Empty
from typing import Dict, List, Optional, Tuple

from opensandbox import SandboxSync
from deepagents_opensandbox import OpensandboxBackend
from opensandbox.config.connection_sync import ConnectionConfigSync

from agent.config.config import (
    SANDBOX_IDLE_TIMEOUT,
    SANDBOX_CLEANUP_INTERVAL,
    SANDBOX_IMAGE,
    SANDBOX_PERSIST_MAX_RETRIES,
    SANDBOX_PERSIST_CMD_TIMEOUT,
    SANDBOX_USE_SERVER_PROXY,
)

logger = logging.getLogger(__name__)

# 本地下载根目录：与 src/ 同级
DOWNLOAD_ROOT = Path(__file__).resolve().parents[3] / "download"
DOWNLOAD_EXPIRE_SECONDS = 60 * 60  # 1 小时

# 并发限制
MAX_CONCURRENT_TASKS = 64
CLEANUP_DOWNLOAD_INTERVAL = 60  # download 清理扫描间隔（秒）


@dataclass
class SandboxTask:
    """沙箱任务：代表一次沙箱使用申请。

    P0-3：event/backend 用于等待队列唤醒——并发满时任务入队，
    worker 分配沙箱成功后填充 backend 并 set event 唤醒提交方。
    """
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    org_id: str = "default_org"
    priority: int = 5  # 1最高 5普通 9最低
    created_at: float = field(default_factory=time.time)
    # 任务完成后产物从沙箱哪个路径拷贝到 download/
    sandbox_output_path: str = "/workspace/outputs"
    # 场景标识（outputs/dist/analysis/convert/debug/batch/env），仅作记录
    scenario: str = "outputs"
    # P0-3：等待队列唤醒事件与分配结果
    event: threading.Event = field(default_factory=threading.Event)
    backend: Optional[OpensandboxBackend] = None
    # 等待截止时间（epoch 秒），超过后 worker 不再为其分配
    wait_deadline: float = 0.0


class _SandboxEntry:
    """单个沙箱实例：记录状态、最后使用时间、产物路径。"""
    def __init__(self, sandbox: SandboxSync, backend: OpensandboxBackend):
        self.lock = threading.Lock()
        self.sandbox = sandbox
        self.backend = backend
        self.last_use_at = time.time()
        self.is_busy = False
        self.current_task_id: Optional[str] = None
        self.org_id: str = "default_org"

    def touch(self):
        self.last_use_at = time.time()

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_use_at

    def mark_busy(self, task_id: str, org_id: str):
        with self.lock:
            self.is_busy = True
            self.current_task_id = task_id
            self.org_id = org_id
            self.touch()

    def mark_idle(self):
        with self.lock:
            self.is_busy = False
            self.current_task_id = None
            self.touch()

    def close(self):
        try:
            self.sandbox.kill()
        except Exception:
            pass
        try:
            self.sandbox.close()
        except Exception:
            pass


class SandboxPool:
    """
    沙箱池：按 org_id 分组管理沙箱实例，支持并发任务与等待队列。
    """
    def __init__(
        self,
        image: str = SANDBOX_IMAGE,
        idle_timeout: int = SANDBOX_IDLE_TIMEOUT,
        cleanup_interval: int = SANDBOX_CLEANUP_INTERVAL,
        max_concurrent: int = MAX_CONCURRENT_TASKS,
    ):
        self._image = image
        self._idle_timeout = idle_timeout
        self._cleanup_interval = cleanup_interval
        self._max_concurrent = max_concurrent
        # Docker/bridge 网络下沙箱容器内网 IP 不可路由，必须走服务端代理（默认开）
        self._connection_config = ConnectionConfigSync(
            use_server_proxy=SANDBOX_USE_SERVER_PROXY
        )

        # org_id -> list of _SandboxEntry（每个 org 可有多沙箱支持并发）
        self._pools: Dict[str, List[_SandboxEntry]] = {}
        # P0-1：task_id -> _SandboxEntry 映射，任务级绑定路由的核心索引
        self._task_index: Dict[str, _SandboxEntry] = {}
        # 全局并发计数（跨 org）
        self._global_busy_count = 0
        self._global_lock = threading.Lock()
        self._stop_event = threading.Event()

        # 等待队列：FIFO，优先级通过多次取队列实现简化（实际用 list 模拟）
        self._wait_queue: Queue[SandboxTask] = Queue()

        self._cleanup_thread: Optional[threading.Thread] = None
        self._download_cleanup_thread: Optional[threading.Thread] = None
        self._queue_worker_thread: Optional[threading.Thread] = None
        self._available = False

        # 确保 download 目录存在
        DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self):
        """启动沙箱池：探测可用性 + 启动后台线程。"""
        try:
            logger.info("SandboxPool: 探测沙箱可用性...")
            probe = SandboxSync.create(
                self._image, connection_config=self._connection_config
            )
            probe.kill()
            probe.close()
            self._available = True
            logger.info("SandboxPool: 沙箱可用，后台线程启动中...")
        except Exception as e:
            logger.error(f"SandboxPool: 沙箱不可用 - {e}")
            self._available = False
            return

        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, name="sandbox-pool-cleanup", daemon=True
        )
        self._cleanup_thread.start()

        self._download_cleanup_thread = threading.Thread(
            target=self._download_cleanup_loop, name="sandbox-download-cleanup", daemon=True
        )
        self._download_cleanup_thread.start()

        self._queue_worker_thread = threading.Thread(
            target=self._queue_worker_loop, name="sandbox-queue-worker", daemon=True
        )
        self._queue_worker_thread.start()

    def stop(self):
        """停止沙箱池：回收所有沙箱，停止后台线程。"""
        self._stop_event.set()

        for t in [self._cleanup_thread, self._download_cleanup_thread, self._queue_worker_thread]:
            if t and t.is_alive():
                t.join(timeout=5)

        with self._global_lock:
            for entries in self._pools.values():
                for entry in entries:
                    with entry.lock:
                        entry.close()
            self._pools.clear()
            self._task_index.clear()

        logger.info("SandboxPool: 已停止，所有沙箱已回收。")

    @property
    def available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    # 任务提交与沙箱分配
    # ------------------------------------------------------------------
    def submit_task(
        self,
        task: SandboxTask,
        wait: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[OpensandboxBackend]:
        """
        提交沙箱任务：尝试分配沙箱。

        - 有空闲容量：立即分配并返回 backend
        - 并发已满：
          * wait=False：直接返回 None（调用方拒绝/自行处理）
          * wait=True ：P0-3 入队并阻塞在 task.event 上，worker 分配成功后唤醒；
                        超过 timeout 仍未分配则返回 None
        """
        if not self._available:
            return None

        backend = self._try_assign(task)
        if backend is not None:
            return backend

        # 并发已满或分配失败
        if not wait:
            logger.info(
                f"SandboxPool: 并发已满({self._max_concurrent})，任务被拒绝 "
                f"task_id={task.task_id}"
            )
            return None

        # P0-3：进入等待队列，阻塞等待 worker 唤醒
        task.event.clear()
        task.wait_deadline = time.time() + (timeout if timeout is not None else 30.0)
        logger.info(
            f"SandboxPool: 并发已满({self._max_concurrent})，任务进入等待队列 "
            f"task_id={task.task_id} timeout={timeout}"
        )
        self._wait_queue.put(task)

        got = task.event.wait(timeout=timeout)
        if not got or task.backend is None:
            logger.warning(
                f"SandboxPool: 等待队列超时，任务未分配到沙箱 task_id={task.task_id}"
            )
            return None
        return task.backend

    def _try_assign(self, task: SandboxTask) -> Optional[OpensandboxBackend]:
        """在全局锁内尝试为任务分配沙箱；成功则登记 _task_index 并返回 backend。"""
        with self._global_lock:
            if self._global_busy_count >= self._max_concurrent:
                return None

            entry = self._acquire_sandbox_locked(task.org_id)
            if entry is None:
                return None

            self._global_busy_count += 1
            entry.mark_busy(task.task_id, task.org_id)
            # P0-1：登记任务级绑定索引，供 SandboxPoolBackend 路由复用
            self._task_index[task.task_id] = entry
            task.backend = entry.backend
            logger.info(
                f"SandboxPool: 任务分配成功 task_id={task.task_id} org={task.org_id} "
                f"busy={self._global_busy_count}/{self._max_concurrent}"
            )
            return entry.backend

    def release_task(
        self,
        task: SandboxTask,
        sandbox_output_path: Optional[str] = None,
        destroy: bool = False,
    ) -> bool:
        """
        释放沙箱：将产物从沙箱持久化到 download/，标记沙箱为空闲（或销毁）。

        - destroy=False：正常释放，沙箱回池复用
        - destroy=True ：销毁沙箱不回池（临时环境场景），且不做产物持久化
        返回 True 表示成功释放。
        """
        if not destroy:
            output_path = sandbox_output_path or task.sandbox_output_path
            download_dir = DOWNLOAD_ROOT / task.task_id
            try:
                # 从沙箱拷贝产物到 download/
                self._persist_outputs(task.org_id, task.task_id, output_path, download_dir)
            except Exception as e:
                logger.error(f"SandboxPool: 产物持久化失败 task_id={task.task_id} - {e}")

        with self._global_lock:
            entry = self._task_index.pop(task.task_id, None)
            if entry is None:
                entry = self._find_busy_entry_locked(task.org_id, task.task_id)
            if entry is None:
                logger.warning(
                    f"SandboxPool: 未找到对应忙碌沙箱 task_id={task.task_id} org={task.org_id}"
                )
                return False

            if destroy:
                # 销毁沙箱不回池
                entries = self._pools.get(entry.org_id, [])
                if entry in entries:
                    entries.remove(entry)
                with entry.lock:
                    entry.close()
                logger.info(
                    f"SandboxPool: 任务释放并销毁沙箱 task_id={task.task_id} org={task.org_id}"
                )
            else:
                entry.mark_idle()

            self._global_busy_count = max(0, self._global_busy_count - 1)
            logger.info(
                f"SandboxPool: 任务释放 task_id={task.task_id} org={task.org_id} "
                f"busy={self._global_busy_count}/{self._max_concurrent} destroy={destroy}"
            )
            return True

    def get_task_entry(self, task_id: str) -> Optional[_SandboxEntry]:
        """P0-1：按 task_id 查询绑定的沙箱 entry（供 SandboxPoolBackend 路由）。"""
        with self._global_lock:
            return self._task_index.get(task_id)

    def persist_task(self, task: SandboxTask, sandbox_output_path: Optional[str] = None) -> Path:
        """
        显式触发一次产物持久化（不释放沙箱）。
        供 sandbox_task_publish 工具在任务进行中发布产物使用。
        返回本地产物目录 download/{task_id}/。
        """
        output_path = sandbox_output_path or task.sandbox_output_path
        download_dir = DOWNLOAD_ROOT / task.task_id
        self._persist_outputs(task.org_id, task.task_id, output_path, download_dir)
        return download_dir

    def _acquire_sandbox_locked(self, org_id: str) -> Optional[_SandboxEntry]:
        """在持有全局锁的情况下，为 org 分配一个空闲沙箱，无则创建。"""
        entries = self._pools.setdefault(org_id, [])

        # 优先复用空闲沙箱
        for entry in entries:
            with entry.lock:
                if not entry.is_busy:
                    return entry

        # 创建新沙箱
        try:
            logger.info(f"SandboxPool: 为 org={org_id} 创建新沙箱")
            sandbox = SandboxSync.create(
                self._image, connection_config=self._connection_config
            )
            backend = OpensandboxBackend(sandbox=sandbox)
            entry = _SandboxEntry(sandbox=sandbox, backend=backend)
            entries.append(entry)
            return entry
        except Exception as e:
            logger.error(f"SandboxPool: 创建沙箱失败 org={org_id} - {e}")
            return None

    def _find_busy_entry_locked(self, org_id: str, task_id: str) -> Optional[_SandboxEntry]:
        """在持有全局锁的情况下，找到对应 task 的忙碌沙箱。"""
        for entry in self._pools.get(org_id, []):
            with entry.lock:
                if entry.is_busy and entry.current_task_id == task_id:
                    return entry
        return None

    # ------------------------------------------------------------------
    # 产物持久化（P0-2 真实拷贝）
    # ------------------------------------------------------------------
    def _persist_outputs(self, org_id: str, task_id: str, sandbox_path: str, local_dir: Path):
        """
        将沙箱内产物真实拷贝到本地 download/{task_id}/。

        策略：
        1. 优先在沙箱内执行 tar 打包，再 download_files 拿字节流，本地解压
        2. tar 失败时降级：用 find 递归收集产物清单，逐文件 download_files 落盘
        3. 整体失败按 SANDBOX_PERSIST_MAX_RETRIES 重试
        """
        last_err: Optional[Exception] = None
        for attempt in range(1 + SANDBOX_PERSIST_MAX_RETRIES):
            try:
                self._persist_once(org_id, task_id, sandbox_path, local_dir)
                logger.info(f"SandboxPool: 产物已持久化到 {local_dir}")
                return
            except Exception as e:
                last_err = e
                logger.warning(
                    f"SandboxPool: 产物持久化第 {attempt + 1} 次失败 task_id={task_id} - {e}"
                )
        logger.error(
            f"SandboxPool: 产物持久化最终失败（重试 {SANDBOX_PERSIST_MAX_RETRIES} 次）"
            f" task_id={task_id} - {last_err}"
        )
        if last_err is not None:
            raise last_err

    def _persist_once(self, org_id: str, task_id: str, sandbox_path: str, local_dir: Path):
        """单次持久化尝试：tar 优先，逐文件降级。"""
        entry = self._locate_entry(org_id, task_id)
        if entry is None:
            raise RuntimeError(f"无可用沙箱读取产物 org={org_id} task_id={task_id}")

        backend = entry.backend
        local_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._persist_via_tar(backend, task_id, sandbox_path, local_dir)
        except Exception as e:
            logger.warning(
                f"SandboxPool: tar 方式持久化失败，降级为逐文件拷贝 task_id={task_id} - {e}"
            )
            self._persist_via_listing(backend, sandbox_path, local_dir)

    def _locate_entry(self, org_id: str, task_id: str) -> Optional[_SandboxEntry]:
        """定位用于读取产物的沙箱 entry：优先任务绑定，其次同 org 任意沙箱。"""
        with self._global_lock:
            entry = self._task_index.get(task_id)
            if entry is None:
                entry = self._find_busy_entry_locked(org_id, task_id)
            if entry is None:
                entries = self._pools.get(org_id, [])
                if entries:
                    entry = entries[0]
            return entry

    def _persist_via_tar(
        self,
        backend: OpensandboxBackend,
        task_id: str,
        sandbox_path: str,
        local_dir: Path,
    ):
        """tar 打包 → download_files 取字节流 → 本地解压。"""
        tar_path = f"/tmp/{task_id}.tar.gz"
        # 确保产物目录存在，避免 tar 因目录不存在而失败
        cmd = (
            f"mkdir -p {sandbox_path} && "
            f"tar -czf {tar_path} -C {sandbox_path} ."
        )
        resp = backend.execute(cmd, timeout=SANDBOX_PERSIST_CMD_TIMEOUT)
        exit_code = getattr(resp, "exit_code", 1)
        if exit_code != 0:
            output = getattr(resp, "output", "")
            raise RuntimeError(f"沙箱内 tar 打包失败 exit={exit_code} output={output}")

        try:
            downloads = backend.download_files([tar_path])
        finally:
            # 无论成败都清理沙箱内临时 tar 包
            try:
                backend.execute(f"rm -f {tar_path}", timeout=30)
            except Exception:
                pass

        if not downloads:
            raise RuntimeError("download_files 返回空结果")
        item = downloads[0]
        err = getattr(item, "error", None)
        if err:
            raise RuntimeError(f"下载 tar 包失败: {err}")
        data = getattr(item, "content", None)
        if not data:
            raise RuntimeError("下载 tar 包内容为空")

        # 本地解压（带 tar slip 防护）
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for member in tf.getmembers():
                member_name = member.name
                # 拒绝绝对路径与目录穿越，防止 tar slip
                if member_name.startswith("/") or ".." in PurePosixPath(member_name).parts:
                    logger.warning(f"SandboxPool: 跳过可疑 tar 成员 {member_name}")
                    continue
                tf.extract(member, path=local_dir)

    def _persist_via_listing(
        self,
        backend: OpensandboxBackend,
        sandbox_path: str,
        local_dir: Path,
    ):
        """降级方案：find 递归收集产物清单，逐文件 download_files 落盘。"""
        resp = backend.execute(
            f"find {sandbox_path} -type f", timeout=SANDBOX_PERSIST_CMD_TIMEOUT
        )
        exit_code = getattr(resp, "exit_code", 1)
        if exit_code != 0:
            output = getattr(resp, "output", "")
            raise RuntimeError(f"沙箱内收集产物清单失败 exit={exit_code} output={output}")

        output = getattr(resp, "output", "") or ""
        remote_files = [line.strip() for line in output.splitlines() if line.strip()]
        if not remote_files:
            logger.info(f"SandboxPool: 产物目录为空，无需拷贝 {sandbox_path}")
            return

        # 批量下载并逐文件写盘，保持相对目录结构
        downloads = backend.download_files(remote_files)
        base = sandbox_path.rstrip("/")
        for remote_path, item in zip(remote_files, downloads):
            err = getattr(item, "error", None)
            if err:
                logger.warning(f"SandboxPool: 下载产物失败 {remote_path} - {err}")
                continue
            content = getattr(item, "content", None)
            if content is None:
                continue
            # 计算相对路径，防止目录穿越
            rel = remote_path[len(base):].lstrip("/") if remote_path.startswith(base) else PurePosixPath(remote_path).name
            if ".." in PurePosixPath(rel).parts:
                continue
            target = local_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    # ------------------------------------------------------------------
    # 等待队列处理（P0-3 唤醒）
    # ------------------------------------------------------------------
    def _queue_worker_loop(self):
        """后台线程：从等待队列取任务，尝试分配沙箱并唤醒阻塞的提交方。"""
        while not self._stop_event.is_set():
            try:
                task = self._wait_queue.get(timeout=1)
            except Empty:
                continue

            # 已被唤醒或超过等待截止时间：丢弃
            if task.event.is_set():
                continue
            if task.wait_deadline and time.time() > task.wait_deadline:
                logger.info(
                    f"SandboxPool: 等待任务已超时，丢弃 task_id={task.task_id}"
                )
                continue

            backend = self._try_assign(task)
            if backend is None:
                # 仍无法分配，重新入队等待下一轮
                self._wait_queue.put(task)
                time.sleep(2)
            else:
                # 分配成功：唤醒 submit_task(wait=True) 中阻塞的提交方
                task.event.set()
                logger.info(
                    f"SandboxPool: 等待队列任务分配成功 task_id={task.task_id}"
                )

    # ------------------------------------------------------------------
    # 沙箱清理（空闲超时销毁）
    # ------------------------------------------------------------------
    def _cleanup_loop(self):
        """后台线程：扫描并销毁空闲超时的沙箱。"""
        logger.info(
            f"SandboxPool: 清理线程启动 "
            f"(idle_timeout={self._idle_timeout}s, interval={self._cleanup_interval}s)"
        )
        while not self._stop_event.is_set():
            try:
                self._reap_expired()
            except Exception as e:
                logger.error(f"SandboxPool: 清理异常 - {e}", exc_info=True)

            self._stop_event.wait(self._cleanup_interval)

        logger.info("SandboxPool: 清理线程已停止。")

    def _reap_expired(self):
        """回收空闲超时的沙箱。"""
        to_remove: List[Tuple[str, _SandboxEntry]] = []

        with self._global_lock:
            for org_id, entries in self._pools.items():
                for entry in entries:
                    with entry.lock:
                        if not entry.is_busy and entry.idle_seconds >= self._idle_timeout:
                            to_remove.append((org_id, entry))

            for org_id, entry in to_remove:
                if entry in self._pools.get(org_id, []):
                    self._pools[org_id].remove(entry)
                    with entry.lock:
                        entry.close()
                    logger.info(f"SandboxPool: 回收空闲沙箱 org={org_id} idle={entry.idle_seconds:.0f}s")

        if to_remove:
            logger.info(f"SandboxPool: 本轮回收 {len(to_remove)} 个空闲沙箱")

    # ------------------------------------------------------------------
    # download 目录清理（1小时过期）
    # ------------------------------------------------------------------
    def _download_cleanup_loop(self):
        """后台线程：定期清理 download/ 中过期内容。"""
        logger.info(f"SandboxPool: download 清理线程启动 (expire={DOWNLOAD_EXPIRE_SECONDS}s)")
        while not self._stop_event.is_set():
            try:
                self._cleanup_download_expired()
            except Exception as e:
                logger.error(f"SandboxPool: download 清理异常 - {e}", exc_info=True)

            self._stop_event.wait(CLEANUP_DOWNLOAD_INTERVAL)

        logger.info("SandboxPool: download 清理线程已停止。")

    def _cleanup_download_expired(self):
        """删除 download/ 中超过 1 小时的目录。"""
        if not DOWNLOAD_ROOT.exists():
            return

        now = time.time()
        removed = 0

        for item in DOWNLOAD_ROOT.iterdir():
            if not item.is_dir():
                continue
            try:
                # 用目录修改时间判断
                mtime = item.stat().st_mtime
                if now - mtime > DOWNLOAD_EXPIRE_SECONDS:
                    shutil.rmtree(item)
                    removed += 1
                    logger.info(f"SandboxPool: 清理过期 download 目录 {item.name}")
            except Exception as e:
                logger.error(f"SandboxPool: 清理 {item} 失败 - {e}")

        if removed:
            logger.info(f"SandboxPool: download 清理完成，移除 {removed} 个过期目录")

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    def get_status(self) -> dict:
        """返回沙箱池当前状态（用于监控/调试）。"""
        with self._global_lock:
            total = sum(len(entries) for entries in self._pools.values())
            busy = sum(
                1 for entries in self._pools.values()
                for e in entries if e.is_busy
            )
            return {
                "available": self._available,
                "total_sandboxes": total,
                "busy": busy,
                "idle": total - busy,
                "global_busy_count": self._global_busy_count,
                "max_concurrent": self._max_concurrent,
                "queue_len": self._wait_queue.qsize(),
                "orgs": {org: len(entries) for org, entries in self._pools.items()},
            }


# 模块级单例
_pool: Optional[SandboxPool] = None


def get_sandbox_pool() -> SandboxPool:
    """获取沙箱池单例（未启动时自动启动）。"""
    global _pool
    if _pool is None:
        _pool = SandboxPool()
        _pool.start()
    return _pool


def close_sandbox_pool():
    """关闭沙箱池（应用 shutdown 时调用）。"""
    global _pool
    if _pool is not None:
        _pool.stop()
        _pool = None
