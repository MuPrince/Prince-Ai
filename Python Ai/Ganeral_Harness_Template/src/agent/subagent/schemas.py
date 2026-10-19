"""子 Agent 回传给主 Agent 的结构化结果格式。

四个子 Agent 统一使用 SubAgentReport 作为 response_format，
deepagents 会把 structured_response 序列化后作为 ToolMessage 内容回传主 Agent，
主 Agent 据此稳定读取产物路径与失败原因，无需解析自由文本。
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SubAgentReport(BaseModel):
    """子 Agent 的任务结果（结构化回传主 Agent）。"""

    status: Literal["success", "partial", "failed"] = Field(
        description="任务状态：success 完全达成 / partial 部分达成 / failed 失败"
    )
    summary: str = Field(
        description="做了什么、得到什么结论的简短摘要（写给主 Agent，不是面向用户的话术）"
    )
    artifacts: List[str] = Field(
        default_factory=list,
        description="产物清单：沙箱内文件路径或 /api/sandbox/download 下载链接；无产物则为空",
    )
    findings: List[str] = Field(
        default_factory=list,
        description="关键发现、指标数值、审查问题清单等要点；无则为空",
    )
    error: Optional[str] = Field(
        default=None,
        description="失败或部分失败时的原因；成功时为 null",
    )
