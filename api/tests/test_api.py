import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app

TOKEN_LIFETIME_SECONDS = 3600
JWT_ISSUER = "workshop-auth-backend"
JWT_AUDIENCE = "workshop-requirements-api"


@pytest.fixture(autouse=True)
def token_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_TOKEN_SECRET", secrets.token_urlsafe(32))
    monkeypatch.setenv("WORKSHOP_LEGACY_SECRET", secrets.token_urlsafe(16))
    monkeypatch.delenv("WORKSHOP_LEGACY_TOKENS_ENABLED", raising=False)


def token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
) -> str:
    """Token del flujo legacy Base64, firmado con el secreto legacy de entorno."""
    expiration = (
        expires_at
        if expires_at is not None
        else int(time.time()) + TOKEN_LIFETIME_SECONDS
    )
    raw_token = f"{username}|{role}|{expiration}|{os.environ['WORKSHOP_LEGACY_SECRET']}"
    return base64.b64encode(raw_token.encode()).decode()


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def jwt_token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
    issuer: str = JWT_ISSUER,
    audience: str = JWT_AUDIENCE,
    secret: str | None = None,
    claims_override: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": username,
        "role": role,
        "iat": now,
        "exp": expires_at if expires_at is not None else now + TOKEN_LIFETIME_SECONDS,
    }
    claims.update(claims_override or {})
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps(claims).encode())
    key = (secret if secret is not None else os.environ["AUTH_TOKEN_SECRET"]).encode()
    signature = hmac.new(key, f"{header}.{payload}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(signature)}"


def jwt_headers(**kwargs: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_token(**kwargs)}"}


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


def test_accepts_valid_signed_token_on_protected_route(client: TestClient) -> None:
        response = client.get("/api/tasks", headers=jwt_headers(username="student"))

        assert response.status_code == 200
        assert {task["owner"] for task in response.json()} == {"student"}


def test_rejects_signed_token_with_altered_payload(client: TestClient) -> None:
        valid_token = jwt_token(username="student")
        header, _, signature = valid_token.split(".")
        forged_payload = _b64url(
            json.dumps(
                {
                    "iss": JWT_ISSUER,
                    "aud": JWT_AUDIENCE,
                    "sub": "trainer",
                    "role": "ADMIN",
                    "iat": int(time.time()),
                    "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
                }
            ).encode()
        )

        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {header}.{forged_payload}.{signature}"},
        )

        assert response.status_code == 401


def test_rejects_expired_signed_token(client: TestClient) -> None:
        response = client.get(
            "/api/tasks",
            headers=jwt_headers(expires_at=int(time.time()) - 1),
        )

        assert response.status_code == 401


@pytest.mark.parametrize(
        "claims",
        [
            {"issuer": "unknown-issuer"},
            {"audience": "unknown-audience"},
        ],
)
def test_rejects_signed_token_with_wrong_issuer_or_audience(
        client: TestClient,
        claims: dict[str, str],
) -> None:
        response = client.get("/api/tasks", headers=jwt_headers(**claims))

        assert response.status_code == 401


def test_rejects_token_signed_with_another_secret(client: TestClient) -> None:
        other_secret = secrets.token_urlsafe(32)

        response = client.get(
            "/api/tasks",
            headers=jwt_headers(secret=other_secret),
        )

        assert response.status_code == 401


def test_rejects_unsigned_token_with_none_algorithm(client: TestClient) -> None:
        header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        payload = _b64url(
            json.dumps(
                {
                    "iss": JWT_ISSUER,
                    "aud": JWT_AUDIENCE,
                    "sub": "student",
                    "role": "STUDENT",
                    "iat": int(time.time()),
                    "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
                }
            ).encode()
        )

        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {header}.{payload}."},
        )

        assert response.status_code == 401


def test_rejects_signed_token_when_signing_secret_is_missing(
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
        valid_headers = jwt_headers()
        monkeypatch.delenv("AUTH_TOKEN_SECRET")

        response = client.get("/api/tasks", headers=valid_headers)

        assert response.status_code == 401


def test_rejects_signed_token_when_signing_secret_is_too_short(
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
        short_secret = "too-short"
        monkeypatch.setenv("AUTH_TOKEN_SECRET", short_secret)

        response = client.get(
            "/api/tasks",
            headers=jwt_headers(secret=short_secret),
        )

        assert response.status_code == 401


def test_rejects_legacy_token_when_legacy_flow_is_disabled(
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
        monkeypatch.setenv("WORKSHOP_LEGACY_TOKENS_ENABLED", "false")

        response = client.get("/api/tasks", headers=headers())

        assert response.status_code == 401


def test_rejects_legacy_token_when_legacy_secret_is_missing(
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
        legacy_headers = headers()
        monkeypatch.delenv("WORKSHOP_LEGACY_SECRET")

        response = client.get("/api/tasks", headers=legacy_headers)

        assert response.status_code == 401


def test_app_source_does_not_embed_the_legacy_secret() -> None:
        app_directory = Path(__file__).resolve().parents[1] / "app"

        for source_file in app_directory.glob("*.py"):
            assert "WORKSHOP_SECRET" not in source_file.read_text(encoding="utf-8")

