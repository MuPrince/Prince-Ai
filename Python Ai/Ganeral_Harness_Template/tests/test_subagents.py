"""子 Agent 规格与 schemas 测试。"""

from agent.subagent import SUBAGENTS
from agent.subagent.coder_agent import CODER_AGENT
from agent.subagent.file_agent import FILE_AGENT
from agent.subagent.schemas import SubAgentReport
from agent.subagent.statistic_agent import STATISTIC_AGENT


class TestSubAgentRegistry:
    def test_subagents_count(self):
        assert len(SUBAGENTS) == 3

    def test_subagents_names(self):
        names = {a["name"] for a in SUBAGENTS}
        assert names == {"file_agent", "statistic_agent", "coder_agent"}

    def test_subagents_have_required_fields(self):
        for agent in SUBAGENTS:
            assert "name" in agent
            assert "description" in agent
            assert "system_prompt" in agent
            assert "model" in agent
            assert "skills" in agent
            assert "tools" in agent
            assert "response_format" in agent

    def test_subagents_descriptions_not_empty(self):
        for agent in SUBAGENTS:
            assert len(agent["description"]) > 10

    def test_subagents_tools_include_sandbox(self):
        for agent in SUBAGENTS:
            tool_names = {t.name for t in agent["tools"]}
            assert "sandbox_task_start" in tool_names
            assert "sandbox_task_execute" in tool_names
            assert "sandbox_task_finish" in tool_names


class TestSubAgentReport:
    def test_valid_report(self):
        report = SubAgentReport(
            status="success",
            summary="任务完成",
            artifacts=["/api/sandbox/download?path=task1/out.pdf"],
            findings=["行数=100"],
            error=None,
        )
        assert report.status == "success"
        assert report.summary == "任务完成"
        assert len(report.artifacts) == 1
        assert len(report.findings) == 1
        assert report.error is None

    def test_default_values(self):
        report = SubAgentReport(status="failed", summary="失败", error="原因")
        assert report.artifacts == []
        assert report.findings == []

    def test_status_literal(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SubAgentReport(status="unknown", summary="test")
