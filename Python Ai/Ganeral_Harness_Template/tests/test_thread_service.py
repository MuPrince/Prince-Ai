"""thread_service 测试。"""

from api_view.services.thread_service import delete_thread, get_history, list_threads


class TestThreadService:
    def test_list_threads(self):
        result = list_threads(org_id="org1", only_mine=False, user_id=None)
        assert result == []

    def test_get_history(self):
        result = get_history("thread-1")
        assert result["thread_id"] == "thread-1"
        assert result["messages"] == []

    def test_delete_thread(self):
        # 不抛异常即可
        delete_thread("thread-1")
