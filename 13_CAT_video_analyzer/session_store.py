import json
import os
import time
import uuid


def _get_static_dir() -> str:
    root_dir = os.environ.get("CCAT_ROOT", os.getcwd())
    static_dir = os.path.join(root_dir, "cat", "static")
    os.makedirs(static_dir, exist_ok=True)
    return static_dir


def _get_sessions_path() -> str:
    return os.path.join(_get_static_dir(), "video_analyzer_sessions.json")


def _read_store() -> dict:
    sessions_path = _get_sessions_path()
    if not os.path.exists(sessions_path):
        return {"sessions": {}}

    try:
        with open(sessions_path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return {"sessions": {}}

    if "sessions" not in data or not isinstance(data["sessions"], dict):
        data["sessions"] = {}
    return data


def _write_store(data: dict):
    with open(_get_sessions_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def create_session(user_id: str) -> dict:
    data = _read_store()
    session_id = uuid.uuid4().hex
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "status": "waiting_upload",
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    data["sessions"][session_id] = session
    _write_store(data)
    return session


def get_session(session_id: str) -> dict | None:
    return _read_store()["sessions"].get(session_id)


def update_session(session_id: str, **updates) -> dict | None:
    data = _read_store()
    session = data["sessions"].get(session_id)
    if session is None:
        return None

    session.update(updates)
    session["updated_at"] = time.time()
    data["sessions"][session_id] = session
    _write_store(data)
    return session


def delete_session(session_id: str) -> bool:
    data = _read_store()
    if session_id not in data["sessions"]:
        return False

    del data["sessions"][session_id]
    _write_store(data)
    return True


def get_latest_waiting_session_for_user(user_id: str) -> dict | None:
    sessions = _read_store()["sessions"].values()
    waiting_sessions = [
        session
        for session in sessions
        if str(session.get("user_id", "")) == str(user_id)
        and session.get("status") == "waiting_upload"
    ]
    if not waiting_sessions:
        return None

    waiting_sessions.sort(key=lambda session: session.get("updated_at", 0), reverse=True)
    return waiting_sessions[0]
