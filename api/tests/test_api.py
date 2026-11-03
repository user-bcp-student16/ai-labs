import base64
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main as api_main
from app.main import create_app
from app.repositories import tasks as task_repository


def token(username: str = "student", role: str = "STUDENT") -> str:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json() == {
        "owner": "student",
        "total": 3,
        "byStatus": {"TODO": 2, "IN_PROGRESS": 1},
        "highPriorityOpen": 2,
    }


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert (upload_dir / "requirements.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_owner_filter_with_quote_is_literal(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", params={"owner": "x' OR '1'='1"}, headers=headers())
    assert response.status_code == 200
    assert response.json() == []


def test_title_with_quote_is_stored_literally(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Login's bug", "description": "Comillas", "status": "TODO", "priority": "LOW"},
        )
    assert created.status_code == 201
    assert created.json()["title"] == "Login's bug"


def test_lists_only_authenticated_owner_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", params={"owner": "trainer"}, headers=headers())
    assert response.status_code == 200
    assert all(task["owner"] == "student" for task in response.json())


def test_empty_owner_filter_defaults_to_authenticated_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", params={"owner": ""}, headers=headers())
    assert response.status_code == 200
    assert {task["owner"] for task in response.json()} == {"student"}


def test_empty_task_object_uses_documented_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})
    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_task_body_must_be_json_object(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json=[])
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "dict_type"


def test_summary_for_unknown_owner_is_empty(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary", params={"owner": "unknown"}, headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "unknown",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_upload_without_extension_and_empty_content(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"", "application/octet-stream")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == 0
    assert (upload_dir / "requirements").read_bytes() == b""


def test_backend_health_returns_downstream_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    monkeypatch.setattr(
        api_main.urllib3.PoolManager,
        "request",
        lambda self, *args, **kwargs: SimpleNamespace(status=200, data=b'{"status":"UP"}'),
    )
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": '{"status":"UP"}'}


def test_backend_health_wraps_downstream_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def fail_request(self, *args, **kwargs):
        raise OSError("backend unavailable")

    monkeypatch.setattr(api_main.urllib3.PoolManager, "request", fail_request)
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 0, "body": "backend unavailable"}


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("get", "/api/tasks", {}),
        ("post", "/api/tasks", {"json": {}}),
        ("get", "/api/summary", {}),
        ("post", "/api/requirements", {"files": {"file": ("requirements.txt", b"x", "text/plain")}}),
        ("get", "/api/backend-health", {}),
    ],
)
def test_every_endpoint_rejects_invalid_token(
    tmp_path: Path, method: str, path: str, request_kwargs: dict[str, object]
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = getattr(client, method)(
            path,
            headers={"Authorization": "Bearer invalid"},
            **request_kwargs,
        )
    assert response.status_code == 401
    assert response.json()["detail"].startswith("Invalid token:")


@pytest.mark.parametrize(
    ("method", "path", "repository_method", "request_kwargs"),
    [
        ("get", "/api/tasks", "find_tasks_by_owner", {}),
        ("post", "/api/tasks", "insert_task", {"json": {}}),
        ("get", "/api/summary", "find_status_and_priority_by_owner", {}),
    ],
)
def test_database_errors_return_server_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    repository_method: str,
    request_kwargs: dict[str, object],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def fail_query(*args, **kwargs):
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(task_repository, repository_method, fail_query)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = getattr(client, method)(path, headers=headers(), **request_kwargs)
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_missing_upload_file_returns_422(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_write_error_returns_server_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def fail_write(self, content):
        raise OSError("disk unavailable")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"x", "text/plain")},
        )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
