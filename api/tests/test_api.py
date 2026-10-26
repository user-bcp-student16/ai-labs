import base64
import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app

TOKEN_LIFETIME_SECONDS = 3600
TEST_TOKEN_SECRET = "WORKSHOP_SECRET_2026"


def token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
) -> str:
    expiration = (
        expires_at
        if expires_at is not None
        else int(time.time()) + TOKEN_LIFETIME_SECONDS
    )
    raw_token = f"{username}|{role}|{expiration}|{TEST_TOKEN_SECRET}"
    return base64.b64encode(raw_token.encode()).decode()


def headers(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role, expires_at)}"}


@pytest.fixture
def api_app(tmp_path: Path) -> FastAPI:
    return create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))


@pytest.fixture
def client(api_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(api_app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("GET", "/api/tasks", {}),
        ("POST", "/api/tasks", {"json": {"title": "Task"}}),
        (
            "GET",
            "/api/summary",
            {},
        ),
        (
            "POST",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"content", "text/plain")}},
        ),
        ("GET", "/api/backend-health", {}),
    ],
)
def test_each_endpoint_requires_authentication(
    client: TestClient,
    method: str,
    path: str,
    request_kwargs: dict[str, object],
) -> None:
    response = client.request(method, path, **request_kwargs)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token: invalid token"}


def test_rejects_expired_token(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        headers=headers(expires_at=int(time.time()) - 1),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token: invalid token"


def test_lists_seeded_tasks(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 200
    tasks = response.json()
    assert [task["title"] for task in tasks] == ["Refactor login", "Review API"]
    assert all(task["owner"] == "student" for task in tasks)
    assert all(isinstance(task["createdAt"], str) for task in tasks)


def test_empty_owner_query_defaults_to_authenticated_user(client: TestClient) -> None:
    response = client.get("/api/tasks?owner=", headers=headers())

    assert response.status_code == 200
    assert {task["owner"] for task in response.json()} == {"student"}
    assert len(response.json()) == 2


def test_owner_query_does_not_expose_other_user_tasks(client: TestClient) -> None:
    response = client.get("/api/tasks?owner=trainer", headers=headers())

    if response.status_code == 200:
        assert all(task["owner"] == "student" for task in response.json())
    else:
        assert 400 <= response.status_code < 500


def test_list_tasks_returns_internal_error_when_database_is_unavailable(
    client: TestClient,
) -> None:
    client.app.state.connection.close()

    response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_creates_task_and_returns_created_task(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=headers(),
        json={
            "title": "Add tests",
            "description": "Improve coverage",
            "status": "TODO",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 201
    created_task = response.json()
    assert created_task["id"] == 4
    assert created_task["title"] == "Add tests"
    assert created_task["description"] == "Improve coverage"
    assert created_task["status"] == "TODO"
    assert created_task["owner"] == "student"
    assert created_task["priority"] == "HIGH"
    assert isinstance(created_task["createdAt"], str)


def test_empty_task_body_uses_documented_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=headers(), json={})

    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_task_body_must_be_an_object(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=headers(), json=[])

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "dict_type"


def test_task_body_is_required(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=headers())

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_create_task_cannot_assign_another_owner(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=headers(),
        json={
            "title": "Unassigned task",
            "description": "Owner must come from identity",
            "owner": "trainer",
        },
    )

    if response.status_code == 201:
        assert response.json()["owner"] == "student"
    else:
        assert 400 <= response.status_code < 500


def test_create_task_returns_internal_error_when_database_is_unavailable(
    client: TestClient,
) -> None:
    client.app.state.connection.close()

    response = client.post(
        "/api/tasks",
        headers=headers(),
        json={"title": "Task"},
    )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_summarizes_tasks_for_authenticated_user(client: TestClient) -> None:
    response = client.get("/api/summary", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_summary_for_owner_without_tasks_is_empty(client: TestClient) -> None:
    response = client.get("/api/summary?owner=unknown", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "owner": "unknown",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_summary_query_does_not_expose_another_owner(client: TestClient) -> None:
    response = client.get("/api/summary?owner=trainer", headers=headers())

    if response.status_code == 200:
        assert response.json()["owner"] == "student"
        assert response.json()["total"] == 2
    else:
        assert 400 <= response.status_code < 500


def test_summary_excludes_done_and_archived_high_priority_tasks(
    client: TestClient,
) -> None:
    for status in ("DONE", "ARCHIVED"):
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": status, "status": status, "priority": "HIGH"},
        )
        assert response.status_code == 201

    summary = client.get("/api/summary", headers=headers())

    assert summary.status_code == 200
    assert summary.json()["highPriorityOpen"] == 1
    assert summary.json()["byStatus"] == {
        "TODO": 1,
        "IN_PROGRESS": 1,
        "DONE": 1,
        "ARCHIVED": 1,
    }


def test_summary_returns_internal_error_when_database_is_unavailable(
    client: TestClient,
) -> None:
    client.app.state.connection.close()

    response = client.get("/api/summary", headers=headers())

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_uploads_requirement_file(client: TestClient) -> None:
    response = client.post(
        "/api/requirements",
        headers=headers(),
        files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["owner"] == "student"
    assert response.json()["fileName"] == "requirements.txt"
    assert response.json()["size"] == len(b"Login must be accessible")
    assert (Path(client.app.state.upload_dir) / "requirements.txt").read_bytes() == (
        b"Login must be accessible"
    )


def test_upload_accepts_empty_file_without_extension(client: TestClient) -> None:
    response = client.post(
        "/api/requirements",
        headers=headers(),
        files={"file": ("requirements", b"", "application/octet-stream")},
    )

    assert response.status_code == 201
    assert response.json()["fileName"] == "requirements"
    assert response.json()["size"] == 0
    assert (Path(client.app.state.upload_dir) / "requirements").read_bytes() == b""


def test_malformed_multipart_request_returns_bad_request(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/requirements",
        headers={
            **headers(),
            "Content-Type": "multipart/form-data; boundary=missing",
        },
        content=b"not-a-multipart-body",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "There was an error parsing the body"}


def test_missing_upload_file_returns_validation_error(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=headers())

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_returns_internal_error_when_destination_is_not_directory(
    client: TestClient,
) -> None:
    upload_directory = Path(client.app.state.upload_dir)
    upload_directory.rmdir()
    upload_directory.write_text("not a directory", encoding="utf-8")

    response = client.post(
        "/api/requirements",
        headers=headers(),
        files={"file": ("requirements.txt", b"content", "text/plain")},
    )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_backend_health_returns_upstream_status_and_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream_response = SimpleNamespace(status=200, data=b'{"health":"UP"}')
    pool_manager = Mock()
    pool_manager.request.return_value = upstream_response
    monkeypatch.setattr("app.main.urllib3.PoolManager", lambda: pool_manager)
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.test/q/health")

    response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"health":"UP"}',
    }
    pool_manager.request.assert_called_once_with(
        "GET",
        "http://auth.test/q/health",
        timeout=3.0,
    )


def test_backend_health_handles_empty_upstream_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool_manager = Mock()
    pool_manager.request.return_value = SimpleNamespace(status=204, data=b"")
    monkeypatch.setattr("app.main.urllib3.PoolManager", lambda: pool_manager)

    response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 204,
        "body": "",
    }


def test_backend_health_returns_caught_upstream_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool_manager = Mock()
    pool_manager.request.side_effect = RuntimeError("upstream unavailable")
    monkeypatch.setattr("app.main.urllib3.PoolManager", lambda: pool_manager)

    response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "upstream unavailable",
    }


def test_create_app_does_not_seed_an_existing_database(tmp_path: Path) -> None:
    database_path = str(tmp_path / "workshop.db")
    upload_path = str(tmp_path / "uploads")
    first_app = create_app(database_path, upload_path)
    with TestClient(first_app) as first_client:
        assert first_client.get("/api/tasks", headers=headers()).status_code == 200

    second_app = create_app(database_path, upload_path)
    with TestClient(second_app) as second_client:
        response = second_client.get("/api/tasks", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2
