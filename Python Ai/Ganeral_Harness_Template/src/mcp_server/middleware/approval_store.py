"""人工审批票据的内存存储。

票据记录一次写操作的审批请求；每张票据配一个同步 ``threading.Event``，
用于跨线程唤醒等待中的中间件——审批台跑在 uvicorn 线程，中间件跑在
MCP 事件循环线程，``threading.Event`` 天然线程安全，中间件侧用
``asyncio.to_thread(event.wait, timeout)`` 阻塞等待即可，无需再绕
``loop.call_soon_threadsafe``。

存储本身用一把 ``threading.Lock`` 保护，所有读写都在锁内完成。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional

# 票据状态枚举值
PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
TIMEOUT = "timeout"


@dataclass
class ApprovalTicket:
    """一张待审（或已决）票据。"""

    id: int
    tool_name: str
    arguments: Dict[str, Any]
    created_at: float
    status: str = PENDING
    decided_by: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转成可直接 JSON 序列化的结构，供审批台接口返回。"""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "created_at": self.created_at,
            "created_at_text": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at)),
            "status": self.status,
            "decided_by": self.decided_by,
            "note": self.note,
        }


class ApprovalStore:
    """票据内存存储（线程安全）。

    与审批台、中间件共享同一个实例即可跨线程传递审批结果。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tickets: Dict[int, ApprovalTicket] = {}
        # 每票一个同步事件：审批台决定后 set，唤醒阻塞等待的中间件
        self._events: Dict[int, threading.Event] = {}
        self._next_id = 1

    def create(self, tool_name: str, arguments: Dict[str, Any]) -> ApprovalTicket:
        """登记一张新票据，返回其快照。"""
        with self._lock:
            ticket = ApprovalTicket(
                id=self._next_id,
                tool_name=tool_name,
                arguments=dict(arguments or {}),
                created_at=time.time(),
            )
            self._tickets[ticket.id] = ticket
            self._events[ticket.id] = threading.Event()
            self._next_id += 1
            return replace(ticket)

    def get(self, ticket_id: int) -> Optional[ApprovalTicket]:
        """按 id 取票据快照，不存在返回 None。"""
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            return replace(ticket) if ticket is not None else None

    def list_pending(self) -> List[ApprovalTicket]:
        """列出全部待审票据（按 id 升序）快照。"""
        with self._lock:
            return [replace(t) for t in self._tickets.values() if t.status == PENDING]

    def decide(
        self,
        ticket_id: int,
        approved: bool,
        decided_by: str = "dashboard",
        note: str = "",
    ) -> Optional[ApprovalTicket]:
        """对票据作出决定并唤醒等待方。

        - 票据不存在返回 None；
        - 票据已决则原样返回（重复决定幂等，不覆盖已有结论）。
        """
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            if ticket.status != PENDING:
                return replace(ticket)
            ticket.status = APPROVED if approved else DENIED
            ticket.decided_by = decided_by
            ticket.note = note
            self._events[ticket_id].set()
            return replace(ticket)

    def wait(self, ticket_id: int, timeout: float) -> Optional[ApprovalTicket]:
        """阻塞等待票据被决定，超时则按 ``timeout`` 状态返回。

        由中间件通过 ``asyncio.to_thread`` 调用，故这里是同步阻塞实现。
        票据不存在返回 None。
        """
        with self._lock:
            event = self._events.get(ticket_id)
        if event is None:
            return None

        signaled = event.wait(timeout)
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            if not signaled and ticket.status == PENDING:
                # 无人决定，超时按拒绝处理
                ticket.status = TIMEOUT
                ticket.decided_by = "timeout"
            return replace(ticket)

    def reset(self) -> None:
        """清空全部票据（供测试隔离使用）。"""
        with self._lock:
            self._tickets.clear()
            self._events.clear()
            self._next_id = 1


# 进程内共享的默认存储：server.py 注册的中间件与审批台都用它
default_store = ApprovalStore()
