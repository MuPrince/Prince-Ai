"""子 Agent 注册表。

主 Agent 通过 create_deep_agent(subagents=SUBAGENTS) 注册这些子 Agent，
再由内置的 task 工具按各自的 description 决定委派目标。
列表顺序即 task 工具描述中的列举顺序；
deepagents 还会自动追加一个内置的 general-purpose 子 Agent（除非同名覆盖）。

reviewer_agent 已实现（subagent/reviewer_agent.py）但暂未启用，
需要时在下面的列表与 __all__ 中加回即可。
"""
from typing import List

from deepagents.middleware.subagents import SubAgent

from agent.subagent.coder_agent import CODER_AGENT
from agent.subagent.file_agent import FILE_AGENT
from agent.subagent.schemas import SubAgentReport
from agent.subagent.statistic_agent import STATISTIC_AGENT

# 启用中的专职子 Agent：文件产物 / 数据分析 / 代码执行
SUBAGENTS: List[SubAgent] = [
    FILE_AGENT,
    STATISTIC_AGENT,
    CODER_AGENT,
]

__all__ = [
    "SUBAGENTS",
    "SubAgentReport",
    "CODER_AGENT",
    "FILE_AGENT",
    "STATISTIC_AGENT",
]
