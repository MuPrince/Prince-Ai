import app.api.chat as chat_api
from app.models.entities import PreferenceStatus, UserPreference


async def fake_stream(session_factory, session_id, user_text):
    yield {"type": "token", "content": "你好，"}
    yield {"type": "token", "content": "已创建任务。"}
    yield {"type": "done"}


def test_chat_send_message_stream(client, monkeypatch):
    monkeypatch.setattr(chat_api, "stream_agent_response", fake_stream)
    session_id = client.post("/api/chat/sessions").json()["id"]
    with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/messages",
        json={"content": "帮我添加 Python 任务"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert "你好，" in body
    assert "data:" in body
    messages = client.get(f"/api/chat/sessions/{session_id}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_profile_confirm_and_snapshot(client, db_session):
    pref = UserPreference(
        user_id="local",
        dimension="response_style",
        value="简洁",
        source="auto",
        status=PreferenceStatus.pending,
        confidence=0.9,
    )
    db_session.add(pref)
    db_session.commit()

    pending = client.get("/api/profile").json()["pending"]
    assert len(pending) == 1
    resp = client.post(f"/api/profile/preferences/{pref.id}/confirm")
    assert resp.status_code == 200
    profile = client.get("/api/profile").json()["profile"]
    assert profile["response_style"]["value"] == "简洁"
