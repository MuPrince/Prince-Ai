"""skill_tools 工具函数测试。"""
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.tools.skill_tools import (
    _is_safe_name,
    _load_index,
    _parse_frontmatter,
    _read_skill_meta,
    _scan_zip_members,
    _update_index_entry,
    _write_index,
    skill_distribute,
    skill_list,
    skill_list_agents,
)


class TestIsSafeName:
    @pytest.mark.parametrize(
        "name",
        ["my-skill", "skill_1", "SkillName", "a", "A-1_b"],
    )
    def test_safe_names(self, name):
        assert _is_safe_name(name)

    @pytest.mark.parametrize(
        "name",
        ["", "my skill", "my/skill", "../etc", "skill.name", "skill@name"],
    )
    def test_unsafe_names(self, name):
        assert not _is_safe_name(name)


class TestParseFrontmatter:
    def test_no_frontmatter(self):
        assert _parse_frontmatter("# Hello") == {}

    def test_simple_fields(self):
        text = """---
name: my-skill
version: 1.0.0
description: A test skill
---
# Content
"""
        fields = _parse_frontmatter(text)
        assert fields["name"] == "my-skill"
        assert fields["version"] == "1.0.0"
        assert fields["description"] == "A test skill"

    def test_list_field(self):
        text = """---
name: my-skill
tags:
  - python
  - data
---
"""
        fields = _parse_frontmatter(text)
        assert fields["name"] == "my-skill"
        assert fields["tags"] == ["python", "data"]

    def test_unclosed_frontmatter(self):
        text = "---\nname: test\n# no closing"
        assert _parse_frontmatter(text) == {}


class TestReadSkillMeta:
    def test_valid_skill(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: my-skill
version: 1.0.0
description: Test skill
---
# My Skill
""",
            encoding="utf-8",
        )
        meta = _read_skill_meta(skill_dir / "SKILL.md")
        assert meta["name"] == "my-skill"
        assert meta["version"] == "1.0.0"
        assert meta["description"] == "Test skill"

    def test_missing_file(self, tmp_path):
        meta = _read_skill_meta(tmp_path / "nonexistent" / "SKILL.md")
        assert meta["name"] == ""
        assert meta["version"] == ""
        assert meta["description"] == ""


class TestSkillIndex:
    def test_load_missing_index(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools._INDEX_PATH", tmp_path / "index.json")
        index = _load_index()
        assert index == {"skills": []}

    def test_load_valid_index(self, tmp_path, monkeypatch):
        index_file = tmp_path / "index.json"
        index_file.write_text(
            json.dumps({"skills": [{"name": "s1", "agent": "main"}]}),
            encoding="utf-8",
        )
        monkeypatch.setattr("agent.tools.skill_tools._INDEX_PATH", index_file)
        index = _load_index()
        assert len(index["skills"]) == 1

    def test_load_corrupted_index(self, tmp_path, monkeypatch):
        index_file = tmp_path / "index.json"
        index_file.write_text("not json", encoding="utf-8")
        monkeypatch.setattr("agent.tools.skill_tools._INDEX_PATH", index_file)
        index = _load_index()
        assert index == {"skills": []}

    def test_write_and_update(self, tmp_path, monkeypatch):
        index_file = tmp_path / "index.json"
        monkeypatch.setattr("agent.tools.skill_tools._INDEX_PATH", index_file)

        index = _update_index_entry("main", "s1", "1.0.0", "desc1")
        assert len(index["skills"]) == 1

        # 同 agent+name 覆盖
        index = _update_index_entry("main", "s1", "2.0.0", "desc2")
        assert len(index["skills"]) == 1
        assert index["skills"][0]["version"] == "2.0.0"

        # 不同 agent 追加
        index = _update_index_entry("file_agent", "s1", "1.0.0", "desc1")
        assert len(index["skills"]) == 2


class TestScanZipMembers:
    def test_safe_zip(self, tmp_path):
        zip_path = tmp_path / "skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("my-skill/SKILL.md", "---\nname: my-skill\n---\n")
            zf.writestr("my-skill/scripts/run.py", "print(1)")

        members, err = _scan_zip_members(zip_path, "my-skill", tmp_path / "dest")
        assert err is None
        assert len(members) == 2

    def test_zip_slip_absolute(self, tmp_path):
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/passwd", "root:x:0:0:")

        members, err = _scan_zip_members(zip_path, "my-skill", tmp_path / "dest")
        assert err is not None
        assert "非法路径" in err

    def test_zip_slip_dotdot(self, tmp_path):
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("my-skill/../../etc/passwd", "root:x:0:0:")

        members, err = _scan_zip_members(zip_path, "my-skill", tmp_path / "dest")
        assert err is not None
        assert "非法路径" in err

    def test_invalid_zip(self, tmp_path):
        zip_path = tmp_path / "not-a.zip"
        zip_path.write_text("not a zip")

        members, err = _scan_zip_members(zip_path, "my-skill", tmp_path / "dest")
        assert err is not None
        assert "无法读取 zip" in err


class TestSkillListAgents:
    def test_list_agents(self, tmp_path, monkeypatch):
        (tmp_path / "main").mkdir()
        (tmp_path / "file_agent").mkdir()
        (tmp_path / "index.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)

        result = skill_list_agents.invoke({})
        assert set(result["agents"]) == {"main", "file_agent"}

    def test_list_agents_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path / "empty")
        result = skill_list_agents.invoke({})
        assert result["agents"] == []


class TestSkillList:
    def test_list_all(self, tmp_path, monkeypatch):
        (tmp_path / "main" / "skill-a").mkdir(parents=True)
        (tmp_path / "main" / "skill-a" / "SKILL.md").write_text(
            "---\nname: skill-a\nversion: 1.0.0\ndescription: A\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "file_agent" / "skill-b").mkdir(parents=True)
        (tmp_path / "file_agent" / "skill-b" / "SKILL.md").write_text(
            "---\nname: skill-b\nversion: 2.0.0\ndescription: B\n---\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)

        result = skill_list.invoke({})
        assert len(result["skills"]) == 2

    def test_list_by_agent(self, tmp_path, monkeypatch):
        (tmp_path / "main" / "skill-a").mkdir(parents=True)
        (tmp_path / "main" / "skill-a" / "SKILL.md").write_text(
            "---\nname: skill-a\nversion: 1.0.0\ndescription: A\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "file_agent" / "skill-b").mkdir(parents=True)
        (tmp_path / "file_agent" / "skill-b" / "SKILL.md").write_text(
            "---\nname: skill-b\nversion: 2.0.0\ndescription: B\n---\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)

        result = skill_list.invoke({"agent": "main"})
        assert len(result["skills"]) == 1
        assert result["skills"][0]["agent"] == "main"

    def test_list_invalid_agent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)
        result = skill_list.invoke({"agent": "bad/name"})
        assert "error" in result


class TestSkillDistribute:
    def test_invalid_skill_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)
        result = skill_distribute.invoke({"skill_name": "bad/name", "task_id": "task1", "target_agents": ["main"]})
        assert "error" in result

    def test_invalid_task_id(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)
        result = skill_distribute.invoke({"skill_name": "skill", "task_id": "bad/task", "target_agents": ["main"]})
        assert "error" in result

    def test_invalid_agent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)
        result = skill_distribute.invoke({"skill_name": "skill", "task_id": "task1", "target_agents": ["bad/agent"]})
        assert "error" in result

    def test_missing_zip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", tmp_path)
        monkeypatch.setattr("agent.tools.skill_tools.DOWNLOAD_ROOT", tmp_path / "download")
        result = skill_distribute.invoke({"skill_name": "skill", "task_id": "task1", "target_agents": ["main"]})
        assert "error" in result
        assert "找不到技能包" in result["error"]

    def test_distribute_success(self, tmp_path, monkeypatch):
        # 准备 zip
        download_dir = tmp_path / "download" / "task1"
        download_dir.mkdir(parents=True)
        zip_path = download_dir / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "my-skill/SKILL.md",
                "---\nname: my-skill\nversion: 1.0.0\ndescription: Test\n---\n",
            )
            zf.writestr("my-skill/scripts/run.py", "print(1)")

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", skills_dir)
        monkeypatch.setattr("agent.tools.skill_tools.DOWNLOAD_ROOT", tmp_path / "download")

        result = skill_distribute.invoke({"skill_name": "my-skill", "task_id": "task1", "target_agents": ["main"]})
        assert "installed" in result
        assert len(result["installed"]) == 1
        assert result["installed"][0]["agent"] == "main"
        assert (skills_dir / "main" / "my-skill" / "SKILL.md").is_file()
        assert (skills_dir / "main" / "my-skill" / "scripts" / "run.py").is_file()

    def test_distribute_conflict_no_overwrite(self, tmp_path, monkeypatch):
        download_dir = tmp_path / "download" / "task1"
        download_dir.mkdir(parents=True)
        zip_path = download_dir / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "my-skill/SKILL.md",
                "---\nname: my-skill\nversion: 1.0.0\ndescription: Test\n---\n",
            )

        skills_dir = tmp_path / "skills"
        (skills_dir / "main" / "my-skill").mkdir(parents=True)
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", skills_dir)
        monkeypatch.setattr("agent.tools.skill_tools.DOWNLOAD_ROOT", tmp_path / "download")

        result = skill_distribute.invoke({"skill_name": "my-skill", "task_id": "task1", "target_agents": ["main"], "overwrite": False})
        assert len(result["conflicts"]) == 1
        assert "已存在" in result["conflicts"][0]["reason"]

    def test_distribute_overwrite(self, tmp_path, monkeypatch):
        download_dir = tmp_path / "download" / "task1"
        download_dir.mkdir(parents=True)
        zip_path = download_dir / "my-skill.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "my-skill/SKILL.md",
                "---\nname: my-skill\nversion: 2.0.0\ndescription: New\n---\n",
            )

        skills_dir = tmp_path / "skills"
        (skills_dir / "main" / "my-skill").mkdir(parents=True)
        (skills_dir / "main" / "my-skill" / "SKILL.md").write_text(
            "---\nname: my-skill\nversion: 1.0.0\ndescription: Old\n---\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("agent.tools.skill_tools.LOCAL_SKILLS_DIR", skills_dir)
        monkeypatch.setattr("agent.tools.skill_tools.DOWNLOAD_ROOT", tmp_path / "download")

        result = skill_distribute.invoke({"skill_name": "my-skill", "task_id": "task1", "target_agents": ["main"], "overwrite": True})
        assert len(result["installed"]) == 1
        meta = (skills_dir / "main" / "my-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "2.0.0" in meta
