"""SandboxPoolBackend 协议实现测试。"""
from unittest.mock import MagicMock, patch

import pytest
from deepagents.backends.protocol import (
    ExecuteResponse,
    LsResult,
    ReadResult,
    WriteResult,
)

from agent.backends.sandbox_pool_backend import (
    SandboxPoolBackend,
    _is_dangerous_command,
    bind_task_context,
    clear_sandbox_context,
    get_current_org_id,
    get_current_task_id,
    set_sandbox_context,
    unbind_task_context,
)


class TestDangerousCommand:
    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf ~",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "fdisk /dev/sda",
            ":(){ :|:& };:",
            "shutdown now",
            "reboot",
            "> /dev/sda",
            "chmod -R 777 /",
        ],
    )
    def test_dangerous_commands(self, cmd):
        assert _is_dangerous_command(cmd)

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls -la",
            "python3 script.py",
            "rm -rf ./build",
            "echo hello",
            "tar -czf out.tar.gz dir/",
        ],
    )
    def test_safe_commands(self, cmd):
        assert not _is_dangerous_command(cmd)


class TestSandboxContext:
    def setup_method(self):
        clear_sandbox_context()

    def teardown_method(self):
        clear_sandbox_context()

    def test_set_and_get_org(self):
        set_sandbox_context("org1")
        assert get_current_org_id() == "org1"

    def test_bind_and_unbind_task(self):
        set_sandbox_context("org1", "task1")
        assert get_current_task_id() == "task1"

        unbind_task_context("org1", "task1")
        assert get_current_task_id() is None

    def test_bind_updates_org_mapping(self):
        bind_task_context("org1", "task1")
        assert get_current_task_id() == "task1"

        # 同 org 新任务覆盖
        bind_task_context("org1", "task2")
        assert get_current_task_id() == "task2"

    def test_unbind_clears_org_mapping(self):
        bind_task_context("org1", "task1")
        unbind_task_context("org1", "task1")
        assert get_current_task_id() is None

    def test_unbind_different_task_noop(self):
        bind_task_context("org1", "task1")
        unbind_task_context("org1", "task2")
        assert get_current_task_id() == "task1"


class TestSandboxPoolBackend:
    @patch("agent.backends.sandbox_pool_backend.get_sandbox_pool")
    def test_execute_dangerous_command(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_get_pool.return_value = mock_pool

        backend = SandboxPoolBackend()
        result = backend.execute("rm -rf /")
        assert result.exit_code == 126
        assert "危险命令被拒绝" in result.output

    @patch("agent.backends.sandbox_pool_backend.get_sandbox_pool")
    def test_execute_safe_command_no_sandbox(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_pool.get_task_entry.return_value = None
        mock_pool.submit_task.return_value = None
        mock_get_pool.return_value = mock_pool

        backend = SandboxPoolBackend()
        result = backend.execute("ls -la")
        assert result.exit_code == 1
        assert "沙箱不可用" in result.output

    @patch("agent.backends.sandbox_pool_backend.get_sandbox_pool")
    def test_ls_no_sandbox(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_pool.submit_task.return_value = None
        mock_get_pool.return_value = mock_pool

        backend = SandboxPoolBackend()
        result = backend.ls("/tmp")
        assert result.error is not None

    @patch("agent.backends.sandbox_pool_backend.get_sandbox_pool")
    def test_read_no_sandbox(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_pool.submit_task.return_value = None
        mock_get_pool.return_value = mock_pool

        backend = SandboxPoolBackend()
        result = backend.read("/tmp/file.txt")
        assert result.error is not None

    @patch("agent.backends.sandbox_pool_backend.get_sandbox_pool")
    def test_write_no_sandbox(self, mock_get_pool):
        mock_pool = MagicMock()
        mock_pool.submit_task.return_value = None
        mock_get_pool.return_value = mock_pool

        backend = SandboxPoolBackend()
        result = backend.write("/tmp/file.txt", "content")
        assert result.error is not None
