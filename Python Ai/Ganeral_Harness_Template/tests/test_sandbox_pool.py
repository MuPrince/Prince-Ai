"""SandboxPool 核心逻辑测试（不创建真实沙箱，纯单元测试）。"""
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from agent.backends.sandbox import (
    MAX_CONCURRENT_TASKS,
    SandboxPool,
    SandboxTask,
    _SandboxEntry,
)


class TestSandboxTask:
    def test_default_fields(self):
        task = SandboxTask()
        assert len(task.task_id) == 12
        assert task.org_id == "default_org"
        assert task.priority == 5
        assert task.sandbox_output_path == "/workspace/outputs"
        assert task.scenario == "outputs"
        assert task.event is not None
        assert task.backend is None

    def test_custom_fields(self):
        task = SandboxTask(org_id="org1", scenario="analysis")
        assert task.org_id == "org1"
        assert task.scenario == "analysis"


class TestSandboxEntry:
    def test_state_transitions(self):
        sandbox = MagicMock()
        backend = MagicMock()
        entry = _SandboxEntry(sandbox=sandbox, backend=backend)

        assert not entry.is_busy
        assert entry.current_task_id is None

        entry.mark_busy("t1", "org1")
        assert entry.is_busy
        assert entry.current_task_id == "t1"
        assert entry.org_id == "org1"

        entry.mark_idle()
        assert not entry.is_busy
        assert entry.current_task_id is None

    def test_touch_updates_last_use(self):
        sandbox = MagicMock()
        backend = MagicMock()
        entry = _SandboxEntry(sandbox=sandbox, backend=backend)
        before = entry.last_use_at
        time.sleep(0.01)
        entry.touch()
        assert entry.last_use_at > before

    def test_idle_seconds(self):
        sandbox = MagicMock()
        backend = MagicMock()
        entry = _SandboxEntry(sandbox=sandbox, backend=backend)
        entry.last_use_at = time.time() - 10
        assert entry.idle_seconds >= 10


class TestSandboxPool:
    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_init(self, mock_backend_cls, mock_sandbox_cls):
        pool = SandboxPool(max_concurrent=4)
        assert pool._max_concurrent == 4
        assert not pool.available
        assert pool._global_busy_count == 0

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_start_unavailable(self, mock_backend_cls, mock_sandbox_cls):
        mock_sandbox_cls.create.side_effect = RuntimeError("no docker")
        pool = SandboxPool()
        pool.start()
        assert not pool.available

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_start_available(self, mock_backend_cls, mock_sandbox_cls):
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool()
        pool.start()
        assert pool.available
        mock_probe.kill.assert_called_once()
        mock_probe.close.assert_called_once()
        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_submit_task_no_wait_full(self, mock_backend_cls, mock_sandbox_cls):
        """并发满时 wait=False 直接返回 None。"""
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool(max_concurrent=1)
        pool.start()

        # 占满唯一槽位
        t1 = SandboxTask(org_id="o1")
        b1 = pool.submit_task(t1, wait=False)
        assert b1 is not None

        # 再次提交，拒绝
        t2 = SandboxTask(org_id="o1")
        b2 = pool.submit_task(t2, wait=False)
        assert b2 is None

        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_submit_task_wait_timeout(self, mock_backend_cls, mock_sandbox_cls):
        """并发满时 wait=True 超时返回 None。"""
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool(max_concurrent=1)
        pool.start()

        # 占满槽位
        t1 = SandboxTask(org_id="o1")
        pool.submit_task(t1, wait=False)

        # wait=True 但超时
        t2 = SandboxTask(org_id="o1")
        start = time.time()
        b2 = pool.submit_task(t2, wait=True, timeout=1)
        elapsed = time.time() - start
        assert b2 is None
        assert elapsed >= 0.9

        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_release_task(self, mock_backend_cls, mock_sandbox_cls):
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool()
        pool.start()

        task = SandboxTask(org_id="o1")
        backend = pool.submit_task(task, wait=False)
        assert backend is not None
        assert pool.get_status()["busy"] == 1

        # mock persist 避免真实文件操作
        with patch.object(pool, "_persist_outputs"):
            ok = pool.release_task(task)
        assert ok
        assert pool.get_status()["busy"] == 0

        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_release_task_destroy(self, mock_backend_cls, mock_sandbox_cls):
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool()
        pool.start()

        task = SandboxTask(org_id="o1")
        pool.submit_task(task, wait=False)
        assert pool.get_status()["total_sandboxes"] == 1

        with patch.object(pool, "_persist_outputs"):
            ok = pool.release_task(task, destroy=True)
        assert ok
        assert pool.get_status()["total_sandboxes"] == 0

        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_get_task_entry(self, mock_backend_cls, mock_sandbox_cls):
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool()
        pool.start()

        task = SandboxTask(org_id="o1")
        pool.submit_task(task, wait=False)

        entry = pool.get_task_entry(task.task_id)
        assert entry is not None
        assert entry.current_task_id == task.task_id

        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_get_status(self, mock_backend_cls, mock_sandbox_cls):
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool(max_concurrent=4)
        pool.start()

        status = pool.get_status()
        assert status["available"]
        assert status["max_concurrent"] == 4
        assert status["busy"] == 0
        assert status["idle"] == 0
        assert status["queue_len"] == 0

        pool.stop()

    @patch("agent.backends.sandbox.SandboxSync")
    @patch("agent.backends.sandbox.OpensandboxBackend")
    def test_org_isolation(self, mock_backend_cls, mock_sandbox_cls):
        """不同 org_id 使用独立沙箱实例。"""
        mock_probe = MagicMock()
        mock_sandbox_cls.create.return_value = mock_probe
        pool = SandboxPool(max_concurrent=4)
        pool.start()

        t1 = SandboxTask(org_id="org-a")
        t2 = SandboxTask(org_id="org-b")
        pool.submit_task(t1, wait=False)
        pool.submit_task(t2, wait=False)

        assert pool.get_status()["orgs"]["org-a"] == 1
        assert pool.get_status()["orgs"]["org-b"] == 1

        pool.stop()
