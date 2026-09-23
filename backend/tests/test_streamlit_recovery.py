"""Exercise upstream URL recovery against the retained compatibility client."""
from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from frontend.utils import api_client

APP = Path(__file__).resolve().parents[2] / "frontend" / "streamlit_app.py"


def test_url_restores_report_and_followup_then_new_research_clears_url(monkeypatch):
    get_session = Mock(return_value={
        "query": "Existing research",
        "result": {"final_answer": "A persisted report."},
    })
    monkeypatch.setattr(api_client, "get_session", get_session)
    monkeypatch.setattr(api_client, "get_history", lambda: [])
    monkeypatch.setattr(api_client, "get_chat_messages", lambda session_id: [
        {"message_id": "q1", "role": "user", "content": "Explain the evidence."},
        {"message_id": "a1", "role": "assistant", "content": "The saved answer."},
    ])
    app = AppTest.from_file(str(APP), default_timeout=15)
    app.query_params["session_id"] = "saved-task"
    app.run()

    assert not app.exception
    get_session.assert_called_once_with("saved-task")
    state = app.session_state["research"]
    assert state["completed"] and state["session_id"] == "saved-task"
    rendered = "\n".join(element.value for element in app.markdown)
    assert "A persisted report." in rendered
    assert "The saved answer." in rendered
    app.run()
    get_session.assert_called_once()

    app.sidebar.button[0].click().run()
    assert not app.exception
    assert "session_id" not in app.query_params
    assert not app.session_state["research"]["completed"]
    assert app.session_state["research"]["messages"] == []


def test_unknown_url_session_does_not_fabricate_completed_research(monkeypatch):
    monkeypatch.setattr(api_client, "get_session", lambda session_id: None)
    monkeypatch.setattr(api_client, "get_history", lambda: [])
    messages = Mock()
    monkeypatch.setattr(api_client, "get_chat_messages", messages)
    app = AppTest.from_file(str(APP), default_timeout=15)
    app.query_params["session_id"] = "missing-task"
    app.run()

    assert not app.exception
    assert not app.session_state["research"]["completed"]
    assert app.session_state["research"]["session_id"] == ""
    messages.assert_not_called()
