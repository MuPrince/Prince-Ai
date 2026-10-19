"""sandbox_tools 工具函数测试（mock 沙箱池）。"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.backends.sandbox import SandboxTask
from agent.tools.sandbox_tools import (
    SCENARIOS,
    _active_tasks,
    _build_download_urls,
    _list_sandbox_output_files,
    _register_task,
    _unregister_task,
    _resolve_current_task,
    _workdir,
    begin_context_tracking,
    cleanup_context_tasks,
    sandbox_pool_status,
    sandbox_task_execute,
    sandbox_task_finish,
    sandbox_task_import_file,
    sandbox_task_publish,
    sandbox_task_start,
)


class TestWorkdir:
    def test_workdir_format(self):
        assert _workdir("outputs", "abc123") == "/workspace/outputs/abc123"
        assert _workdir("analysis", "xyz") == "/workspace/analysis/xyz"


class TestTaskRegistry:
    def setup_method(self):
        _active_tasks.clear()

    def teardown_method(self):
        _active_tasks.clear()

    def test_register_and_resolve(self):
        task = SandboxTask(org_id="o1", scenario="outputs")
        _register_task(task)
        assert task.task_id in _active_tasks
        _unregister_task(task)
        assert task.task_id not in _active_tasks

    def test_resolve_no_task(self):
        assert _resolve_current_task() is None


class TestBuildDownloadUrls:
    def test_empty_dir(self, tmp_path):
        task = SandboxTask(org_id="o1", scenario="outputs")
        task.task_id = "abc123"
        urls = _build_download_urls(task, tmp_path / "nonexistent")
        assert urls == []

    def test_with_files(self, tmp_path):
        task = SandboxTask(org_id="o1", scenario="outputs")
        task.task_id = "abc123"
        download_dir = tmp_path / "abc123"
        download_dir.mkdir()
        (download_dir / "report.pdf").write_text("pdf")
        (download_dir / "data.csv").write_text("csv")

        urls = _build_download_urls(task, download_dir)
        assert len(urls) == 2
        assert any("report.pdf" in u for u in urls)
        assert any("data.csv" in u for u in urls)
        assert all("/api/sandbox/download" in u for u in urls)
        assert all("org_id=o1" in u for u in urls)


class TestSandboxTaskStart:
    def setup_method(self):
        _active_tasks.clear()

    def teardown_method(self):
        _active_tasks.clear()

    @patch("agent.tools.sandbox_tools.get_sandbox_pool")
    def test_invalid_scenario(self, mock_get_pool):
        result = sandbox_task_start.invoke({"scenario": "invalid"})
        assert "error" in result
        assert "非法场景" in result["error"]

    @patch("agent.tools.sandbox_tools.get_sandbox_pool")
    def test_pool_unavailable(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_pool.available = False
        mock_get_pool.return_value = mock_pool

        result = sandbox_task_start.invoke({"scenario": "outputs"})
        assert "error" in result
        assert "沙箱服务不可用" in result["error"]

    @patch("agent.tools.sandbox_tools.get_sandbox_pool")
    @patch("agent.tools.sandbox_tools.bind_task_context")
    def test_start_success(self, mock_bind, mock_get_pool):
        mock_backend = MagicMock()
        mock_resp = MagicMock()
        mock_resp.exit_code = 0
        mock_backend.execute.return_value = mock_resp

        mock_pool = MagicMock()
        mock_pool.available = True
        mock_pool.submit_task.return_value = mock_backend
        mock_get_pool.return_value = mock_pool

        begin_context_tracking()
        result = sandbox_task_start.invoke({"scenario": "outputs"})
        assert "task_id" in result
        assert "workdir" in result
        assert result["workdir"].startswith("/workspace/outputs/")
        cleanup_context_tasks()


class TestSandboxTaskExecute:
    def setup_method(self):
        _active_tasks.clear()

    def teardown_method(self):
        _active_tasks.clear()

    def test_execute_no_active_task(self):
        result = sandbox_task_execute.invoke({"command": "ls"})
        assert "error" in result
        assert "没有活跃的沙箱任务" in result["error"]


class TestSandboxTaskFinish:
    def setup_method(self):
        _active_tasks.clear()

    def teardown_method(self):
        _active_tasks.clear()

    def test_finish_no_active_task(self):
        result = sandbox_task_finish.invoke({})
        assert "error" in result
        assert "没有活跃的沙箱任务" in result["error"]


class TestSandboxPoolStatus:
    @patch("agent.tools.sandbox_tools.get_sandbox_pool")
    def test_pool_status(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_pool.get_status.return_value = {
            "busy": 2,
            "idle": 3,
            "queue_len": 1,
            "max_concurrent": 64,
            "available": True,
        }
        mock_get_pool.return_value = mock_pool

        result = sandbox_pool_status.invoke({})
        assert result["busy"] == 2
        assert result["idle"] == 3
        assert result["queue_len"] == 1
        assert result["max_concurrent"] == 64
        assert result["available"] is True
