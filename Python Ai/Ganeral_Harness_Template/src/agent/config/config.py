import os

MODEL = "deepseek:deepseek-flash"

SANDBOX_IDLE_TIMEOUT = 60 * 10
SANDBOX_CLEANUP_INTERVAL = 60

SANDBOX_IMAGE = os.getenv(
    "SANDBOX_IMAGE",
    "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.1",
)