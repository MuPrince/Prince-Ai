"""agent.config 模块测试。"""
import pytest
from pydantic import ValidationError

from agent.config.config import (
    MODEL,
    SANDBOX_CLEANUP_INTERVAL,
    SANDBOX_EXECUTE_MAX_RETRIES,
    SANDBOX_IDLE_TIMEOUT,
    SANDBOX_IMAGE,
    SANDBOX_PERSIST_CMD_TIMEOUT,
    SANDBOX_PERSIST_MAX_RETRIES,
    SANDBOX_TASK_WAIT_TIMEOUT,
    SANDBOX_USE_SERVER_PROXY,
    get_subagent_model,
)
from agent.config.context_type import ContextType


class TestConfig:
    def test_model_name(self):
        assert MODEL == "deepseek:deepseek-flash"

    def test_sandbox_image(self):
        assert isinstance(SANDBOX_IMAGE, str)
        assert len(SANDBOX_IMAGE) > 0

    def test_sandbox_timeouts(self):
        assert SANDBOX_IDLE_TIMEOUT == 60 * 30
        assert SANDBOX_CLEANUP_INTERVAL == 60
        assert SANDBOX_TASK_WAIT_TIMEOUT == 30
        assert SANDBOX_PERSIST_CMD_TIMEOUT == 120
        assert SANDBOX_PERSIST_MAX_RETRIES == 1
        assert SANDBOX_EXECUTE_MAX_RETRIES == 2

    def test_sandbox_proxy(self):
        assert isinstance(SANDBOX_USE_SERVER_PROXY, bool)


class TestSubagentModel:
    def test_lazy_singleton(self):
        """子 Agent 模型为惰性单例。"""
        m1 = get_subagent_model()
        m2 = get_subagent_model()
        assert m1 is m2


class TestContextType:
    def test_defaults(self):
        ctx = ContextType()
        assert ctx.user_id == "local_user"
        assert ctx.org_id == "default_org"

    def test_custom_values(self):
        ctx = ContextType(user_id="u1", org_id="o1")
        assert ctx.user_id == "u1"
        assert ctx.org_id == "o1"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            ContextType(user_id=123)
