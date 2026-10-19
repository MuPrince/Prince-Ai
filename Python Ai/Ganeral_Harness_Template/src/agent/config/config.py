import os
from pathlib import Path

MODEL = "deepseek:deepseek-flash"


def _build_subagent_model():
    """构建子 Agent 专用模型实例。

    DeepSeek 的 thinking 模式拒绝强制 tool_choice，而 ToolStrategy 结构化输出
    会强制 tool_choice="any"（见 langchain agents factory），二者冲突导致 400。
    主 Agent 不强制 tool_choice，保持 thinking；子 Agent 必须显式关闭 thinking。
    """
    from langchain_deepseek import ChatDeepSeek

    model_name = MODEL.split(":", 1)[1] if ":" in MODEL else MODEL
    return ChatDeepSeek(
        model=model_name,
        extra_body={"thinking": {"type": "disabled"}},
    )


# 惰性单例：不能在本模块 import 时实例化——此时 load_dotenv() 尚未执行，
# DEEPSEEK_API_KEY 未就绪会导致 ChatDeepSeek 校验失败。
_SUBAGENT_MODEL = None


def get_subagent_model():
    """返回子 Agent 共享的无 thinking 模型实例（ChatDeepSeek 无状态，可安全共享）。"""
    global _SUBAGENT_MODEL
    if _SUBAGENT_MODEL is None:
        _SUBAGENT_MODEL = _build_subagent_model()
    return _SUBAGENT_MODEL

SANDBOX_IDLE_TIMEOUT = 60 * 30
SANDBOX_CLEANUP_INTERVAL = 60

SANDBOX_IMAGE = os.getenv(
    "SANDBOX_IMAGE",
    "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.1",
)

# 是否经沙箱管理服务代理转发 execd 请求。
# 服务端跑在 Docker（WSL2/bridge 网络）时，沙箱容器内网 IP 从宿主不可路由，必须为 True；
# 若 SDK 能直连沙箱容器（同网络环境），可设 OPEN_SANDBOX_USE_PROXY=0 关闭。
SANDBOX_USE_SERVER_PROXY = os.getenv("OPEN_SANDBOX_USE_PROXY", "1") != "0"

# ----------------------------------------------------------------------
# 沙箱任务（SandboxPool）相关配置
# ----------------------------------------------------------------------

# 并发已满时，submit_task(wait=True) 在等待队列中的最长阻塞时间（秒）
SANDBOX_TASK_WAIT_TIMEOUT = int(os.getenv("SANDBOX_TASK_WAIT_TIMEOUT", "30"))

# execute 非零退出时允许 LLM 自动修复的最大次数（由工具提示约束）
SANDBOX_EXECUTE_MAX_RETRIES = 2

# 产物持久化失败时的重试次数（除首次外的额外尝试次数）
SANDBOX_PERSIST_MAX_RETRIES = 1

# 沙箱内执行 tar 打包 / find 收集产物清单的超时时间（秒）
SANDBOX_PERSIST_CMD_TIMEOUT = 120

# 用户上传文件的本地落盘根目录：与 src/ 同级
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads"
