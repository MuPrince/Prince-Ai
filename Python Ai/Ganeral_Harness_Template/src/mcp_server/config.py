"""MCP 服务配置：对接已有 Java 服务端 Api。

环境变量（项目根目录 .env 或进程环境）：

| 变量名             | 默认值                       | 说明                                       |
| ------------------ | ---------------------------- | ------------------------------------------ |
| JAVA_API_BASE_URL  | http://localhost:8001/api    | Java 服务根地址，与前端 VITE_API_BASE_URL 一致 |
| JAVA_API_TOKEN     | 空                           | 可选，注入 Authorization: Bearer <token>   |
| JAVA_API_TIMEOUT   | 60                           | 单次请求超时秒数，与前端 axios timeout 一致 |
| JAVA_API_MOCK      | 0                            | 置 1 时由 MCP 服务内置拉起 Mock，不访问真实 Java 服务 |
| JAVA_API_MOCK_PORT | 8001                         | 内置 Mock 的监听端口                       |
| MCP_APPROVAL_ENABLED        | 1                   | 置 0 关闭人工审批中间件与审批台            |
| MCP_APPROVAL_TOOLS          | rag_add_knowledge,rag_delete_file | 需人工审批的工具名，逗号分隔   |
| MCP_APPROVAL_TIMEOUT        | 120                 | 等待人类决定的秒数，超时按拒绝处理          |
| MCP_APPROVAL_DASHBOARD_HOST | 127.0.0.1           | 网页审批台监听地址                          |
| MCP_APPROVAL_DASHBOARD_PORT | 9001                | 网页审批台监听端口                          |
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（与 src/ 同级）下的 .env
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

JAVA_API_BASE_URL = os.getenv("JAVA_API_BASE_URL", "http://localhost:8001/api").rstrip("/")
JAVA_API_TOKEN = os.getenv("JAVA_API_TOKEN", "").strip()
JAVA_API_TIMEOUT = float(os.getenv("JAVA_API_TIMEOUT", "60"))

# 开发阶段内置 Mock：置 1 时 MCP 服务自行拉起 mock_java_api，不依赖真实 Java 服务
JAVA_API_MOCK = os.getenv("JAVA_API_MOCK", "0").strip().lower() not in ("0", "", "false")
JAVA_API_MOCK_HOST = "127.0.0.1"
JAVA_API_MOCK_PORT = int(os.getenv("JAVA_API_MOCK_PORT", "8001"))

# 待上传文件的本地落盘根目录：rag_upload_file 的相对路径按此目录解析
UPLOAD_ROOT = PROJECT_ROOT / "uploads"

# 人工审批：拦截不可逆写操作，等人类批准后才放行；超时按拒绝处理
MCP_APPROVAL_ENABLED = os.getenv("MCP_APPROVAL_ENABLED", "1").strip().lower() not in ("0", "", "false")
MCP_APPROVAL_TOOLS = [
    name.strip()
    for name in os.getenv(
        "MCP_APPROVAL_TOOLS", "rag_add_knowledge,rag_delete_file"
    ).split(",")
    if name.strip()
]
MCP_APPROVAL_TIMEOUT = float(os.getenv("MCP_APPROVAL_TIMEOUT", "120"))
MCP_APPROVAL_DASHBOARD_HOST = os.getenv("MCP_APPROVAL_DASHBOARD_HOST", "127.0.0.1").strip()
MCP_APPROVAL_DASHBOARD_PORT = int(os.getenv("MCP_APPROVAL_DASHBOARD_PORT", "9001"))
