"""Java 服务端 Api 的异步客户端封装。

接口契约来自前端实际调用（project/client/web/src 下），Java 端源码不在本仓库，
因此按前端可见行为实现，并兼容 Spring Boot 常见响应包裹：

| 用途       | 方法                | HTTP 请求                                 |
| ---------- | ------------------- | ----------------------------------------- |
| 知识库列表 | list_rag_files      | GET    /rag/list                          |
| 知识库上传 | upload_rag_file     | PUT    /rag/upload    (multipart/form-data) |
| 知识库入库 | add_rag_knowledge   | POST   /rag/add       {filename, splits}   |
| 知识库删除 | delete_rag_file     | DELETE /rag/delete    ?file_path=          |
| 业务问答   | chat                | POST   /{feature_code}/chat  {message}     |

响应包裹：前端在 axios 拦截器中返回 body，再读取 body.data，说明 Java 端返回
{"code": ..., "message": ..., "data": ...}；_unwrap 统一取出 data，同时兼容裸响应。
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from mcp_server.config import JAVA_API_BASE_URL, JAVA_API_TIMEOUT, JAVA_API_TOKEN

logger = logging.getLogger(__name__)

# 业务成功码。Java 端 code 取值约定未确认，仅在 code 明确存在且不在其中时报错
_SUCCESS_CODES = {0, 200, "0", "200"}


class JavaApiError(RuntimeError):
    """调用 Java 服务端失败：网络异常、HTTP 错误码、业务错误码或响应不可解析。"""


def _unwrap(body: Any) -> Any:
    """取出 Spring Boot 风格响应包裹中的 data 字段。"""
    if isinstance(body, dict) and "data" in body:
        code = body.get("code")
        if code is not None and code not in _SUCCESS_CODES:
            raise JavaApiError(
                f"Java 服务业务错误: code={code}, "
                f"message={body.get('message') or body.get('msg') or ''}"
            )
        return body["data"]
    return body


class JavaApiClient:
    """Java Api 客户端。

    每次请求独立建连：httpx 连接池与事件循环绑定，MCP 服务可能被不同循环驱动，
    逐次建连可避免连接池跨循环复用的隐患（示例服务请求量小，开销可忽略）。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._base_url = (base_url if base_url is not None else JAVA_API_BASE_URL).rstrip("/")
        self._token = JAVA_API_TOKEN if token is None else token
        self._timeout = JAVA_API_TIMEOUT if timeout is None else timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self) -> Dict[str, str]:
        """构造请求头：配置了 token 时注入 Bearer 鉴权，与前端拦截器行为一致。"""
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """发送请求并返回解包后的业务数据，失败统一抛 JavaApiError。"""
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, headers=self._headers(), **kwargs)
        except httpx.HTTPError as exc:
            raise JavaApiError(f"请求 Java 服务失败: {method} {url} -> {exc}") from exc

        if response.status_code >= 400:
            raise JavaApiError(
                f"Java 服务返回 HTTP {response.status_code}: {method} {url} "
                f"-> {response.text[:500]}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise JavaApiError(
                f"Java 服务响应不是合法 JSON: {method} {url} -> {response.text[:500]}"
            ) from exc

        return _unwrap(body)

    async def list_rag_files(self) -> Any:
        """GET /rag/list：返回知识库中已入库的文件列表。"""
        return await self._request("GET", "/rag/list")

    async def upload_rag_file(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Any:
        """PUT /rag/upload：上传文件，返回切分结果 splits。"""
        files = {"file": (filename, content, content_type)}
        return await self._request("PUT", "/rag/upload", files=files)

    async def add_rag_knowledge(self, filename: str, splits: List[str]) -> Any:
        """POST /rag/add：把确认后的切分内容正式写入知识库。"""
        return await self._request(
            "POST", "/rag/add", json={"filename": filename, "splits": splits}
        )

    async def delete_rag_file(self, file_path: str) -> Any:
        """DELETE /rag/delete：按文件名或路径删除知识库文件。"""
        return await self._request("DELETE", "/rag/delete", params={"file_path": file_path})

    async def chat(self, feature_code: str, message: str) -> Any:
        """POST /{feature_code}/chat：调用对应业务功能的问答接口。"""
        return await self._request("POST", f"/{feature_code}/chat", json={"message": message})
