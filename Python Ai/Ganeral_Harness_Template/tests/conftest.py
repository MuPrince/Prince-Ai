"""pytest 共享 fixtures。"""
import sys
from pathlib import Path

import pytest

# 确保 src/ 在 sys.path 中，使测试可导入项目模块
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def tmp_download_dir(tmp_path, monkeypatch):
    """临时 download 目录，隔离测试产物。"""
    download_dir = tmp_path / "download"
    download_dir.mkdir()
    monkeypatch.setattr("agent.backends.sandbox.DOWNLOAD_ROOT", download_dir)
    return download_dir


@pytest.fixture
def tmp_upload_dir(tmp_path, monkeypatch):
    """临时 upload 目录，隔离测试文件。"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr("agent.config.config.UPLOAD_ROOT", upload_dir)
    return upload_dir


@pytest.fixture
def tmp_skills_dir(tmp_path, monkeypatch):
    """临时 skills 目录，隔离技能测试。"""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "index.json").write_text('{"skills": []}', encoding="utf-8")
    monkeypatch.setattr("agent.config.constants.LOCAL_SKILLS_DIR", skills_dir)
    return skills_dir
