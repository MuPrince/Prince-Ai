import app.api.summaries as summaries_api
from app.models.entities import SummaryStatus, Task


def _task(client):
    resp = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "API笔记任务", "description": ""},
    )
    return resp.json()


def test_note_put_and_get(client):
    task = _task(client)
    put = client.put(f"/api/tasks/{task['id']}/note", json={"content": "# 正文"})
    assert put.status_code == 200
    got = client.get(f"/api/tasks/{task['id']}/note").json()
    assert got["content"] == "# 正文"
    assert got["rel_path"].endswith("API笔记任务.md")


def test_manual_record_post_and_list(client):
    task = _task(client)
    payload = {
        "started_at": "2026-09-06T10:00:00Z",
        "content": "今天学了工具调用",
    }
    resp = client.post(f"/api/tasks/{task['id']}/records", json=payload)
    assert resp.status_code == 201
    assert resp.json()["record_type"] == "manual"
    rows = client.get(f"/api/tasks/{task['id']}/records").json()
    assert len(rows) == 1


def test_summary_get_and_regenerate(client, monkeypatch, db_session):
    calls = []

    def fake_run(session_factory, task_id, generator=None, after_success=None):
        calls.append(task_id)

    monkeypatch.setattr(summaries_api, "run_summary_generation", fake_run)
    task = _task(client)
    task_id = task["id"]

    model_task = db_session.get(Task, task_id)
    model_task.summary_status = SummaryStatus.success
    db_session.commit()

    got = client.get(f"/api/tasks/{task_id}/summary")
    assert got.status_code == 200
    resp = client.post(f"/api/tasks/{task_id}/summary/regenerate")
    assert resp.status_code == 200
    assert calls == [task_id]
