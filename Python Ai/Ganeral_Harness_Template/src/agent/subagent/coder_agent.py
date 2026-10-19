"""代码执行子 Agent（coder_agent）规格。

职责：编写 / 运行 / 调试代码片段、精确数值计算、脚本化验证。
边界：不做文件格式转换、数据分析报告、PPT/Excel 生成与批量文件处理。
"""
from deepagents.middleware.subagents import SubAgent
from langchain.agents.structured_output import ToolStrategy

from agent.config.config import get_subagent_model
from agent.subagent.schemas import SubAgentReport
from agent.tools.sandbox_tools import (
    sandbox_task_execute,
    sandbox_task_finish,
    sandbox_task_import_file,
    sandbox_task_publish,
    sandbox_task_start,
)

CODER_AGENT_PROMPT = """你是「代码执行」子 Agent，由主 Agent 通过 task 工具委派，只向它汇报结果，不直接面向用户。

## 职责范围（只做这些）
- 编写、运行、调试代码片段（Python / shell 等）
- 精确数值计算、算法验证、脚本化逻辑验证
- 对沙箱内已有文件做程序化读取与检查

## 职责之外（不要勉强执行）
文档格式转换、数据统计分析报告、PPT/Excel/图片生成、多个用户文件的批量处理、技能管理，
都不属于你。遇到这类任务，在 summary 中说明"不属于我的职责"，不要强行尝试。

## 沙箱工作流程
1. 调用 sandbox_task_start(scenario="debug") 申请沙箱，返回 workdir。
2. 把脚本写到 workdir 下的 work/ 子目录（backend 路径形如 /sandbox<workdir>/work/run.py），
   用 execute 运行；ls / read / write / edit / glob / grep 同样落在该沙箱内。
3. execute 非零退出时，读取输出中的 stderr 定位原因并修复，最多重试 2 次；
   仍失败就如实上报，不要反复尝试同一种写法。
4. 若结论需要以文件交付，把产物放到 workdir 下的 output/ 子目录后调用 sandbox_task_publish；
   纯文本结论不需要 publish。
5. 无论成功或失败，最后都必须调用 sandbox_task_finish() 释放沙箱。

## 纪律
- 你是子 Agent，不能再委派给其他子 Agent（再次调用 task 会被拒绝），必须自己完成。
- 不要编造路径、退出码或数值；artifacts 只填真实存在的文件。
"""

CODER_AGENT: SubAgent = {
    "name": "coder_agent",
    "description": (
        "当任务需要编写/运行/调试代码、做精确数值计算、或脚本化验证时使用，"
        "它在沙箱中执行并返回结论与错误信息。"
        "不处理文档格式转换、数据分析统计报告、PPT/Excel 生成与批量文件处理。"
    ),
    "system_prompt": CODER_AGENT_PROMPT,
    # DeepSeek thinking 模式拒绝强制 tool_choice，须用关闭 thinking 的共享模型实例
    "model": get_subagent_model(),
    "skills": ["/skills/coder_agent/"],
    "tools": [
        sandbox_task_start,
        sandbox_task_import_file,
        sandbox_task_execute,
        sandbox_task_publish,
        sandbox_task_finish,
    ],
    "response_format": ToolStrategy(SubAgentReport),
}
