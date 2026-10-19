import os
from pathlib import Path

MODEL = "deepseek:deepseek-flash"

SANDBOX_IDLE_TIMEOUT = 60 * 10
SANDBOX_CLEANUP_INTERVAL = 60

SANDBOX_IMAGE = os.getenv(
    "SANDBOX_IMAGE",
    "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.1",
)

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
