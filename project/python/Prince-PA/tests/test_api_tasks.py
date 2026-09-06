import app.api.tasks as tasks_api


def test_create_and_list_task(client):
    resp = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "LangChain", "description": "d"},
    )
    assert resp.status_code == 201
    task = resp.json()
    assert task["language"] == "Python"

    rows = client.get("/api/tasks?language=Python").json()
    assert len(rows) == 1


def test_duplicate_task_returns_400(client):
    payload = {"language": "Python", "title": "重复任务", "description": ""}
    assert client.post("/api/tasks", json=payload).status_code == 201
    assert client.post("/api/tasks", json=payload).status_code == 400


def test_start_creates_auto_record(client):
    task_id = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "开始任务", "description": ""},
    ).json()["id"]

    resp = client.post(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    records = client.get(f"/api/tasks/{task_id}/records").json()
    assert len(records) == 1
    assert records[0]["record_type"] == "auto"


def test_complete_schedules_summary(client, monkeypatch):
    calls = []

    def fake_run(session_factory, task_id, generator=None, after_success=None):
        calls.append(task_id)

    monkeypatch.setattr(tasks_api, "run_summary_generation", fake_run)
    task_id = client.post(
        "/api/tasks",
        json={"language": "Python", "title": "完成任务", "description": ""},
    ).json()["id"]

    resp = client.post(f"/api/tasks/{task_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert calls == [task_id]
