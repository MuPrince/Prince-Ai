"""sandbox_service 测试。"""
from pathlib import Path
from unittest.mock import patch

import pytest

from api_view.services.sandbox_service import download


@pytest.fixture(autouse=True)
def patch_download_root(tmp_path):
    """把 DOWNLOAD_ROOT patch 到临时目录，隔离测试产物。"""
    download_dir = tmp_path / "download"
    download_dir.mkdir()
    with patch("api_view.services.sandbox_service.DOWNLOAD_ROOT", download_dir):
        yield download_dir


class TestSandboxDownload:
    def test_download_direct_path(self, patch_download_root):
        task_dir = patch_download_root / "task1"
        task_dir.mkdir()
        (task_dir / "report.pdf").write_bytes(b"pdf content")

        content, filename = download("task1/report.pdf", "org1")
        assert content == b"pdf content"
        assert filename == "report.pdf"

    def test_download_sandbox_path(self, patch_download_root):
        task_dir = patch_download_root / "task1"
        task_dir.mkdir()
        (task_dir / "report.pdf").write_bytes(b"pdf content")

        content, filename = download("/workspace/outputs/task1/report.pdf", "org1")
        assert content == b"pdf content"
        assert filename == "report.pdf"

    def test_download_nested_path(self, patch_download_root):
        task_dir = patch_download_root / "task1" / "subdir"
        task_dir.mkdir(parents=True)
        (task_dir / "data.csv").write_bytes(b"csv")

        content, filename = download("task1/subdir/data.csv", "org1")
        assert content == b"csv"
        assert filename == "data.csv"

    def test_download_directory_traversal(self, patch_download_root):
        with pytest.raises(ValueError, match="目录遍历"):
            download("../etc/passwd", "org1")

    def test_download_not_found(self, patch_download_root):
        with pytest.raises(FileNotFoundError, match="文件不存在或已过期"):
            download("task1/nonexistent.pdf", "org1")
