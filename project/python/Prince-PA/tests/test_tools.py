from agents.tools.note_tools import build_note_tools
from agents.tools.task_tools import build_task_tools


def _factory(db_session):
    return lambda: db_session


def test_create_and_read_task_tool(db_session):
    task_tools = build_task_tools(_factory(db_session))
    created = task_tools[0].invoke(
        {"language": "Python", "title": "工具任务", "description": "通过工具创建"}
    )
    assert "id" in created

    note_tools = build_note_tools(_factory(db_session))
    init_result = note_tools[0].invoke({"task_id": 1})
    assert "已创建笔记文件" in init_result
    read_result = note_tools[1].invoke({"task_id": 1})
    assert "空" in read_result
