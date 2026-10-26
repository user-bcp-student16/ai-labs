# Pruebas de API

## Alcance y matriz de casos

La suite de caracterización y regresión está en [api/tests/test_api.py](../api/tests/test_api.py). Se usa SQLite y un directorio de carga temporales por test; las llamadas al servicio externo de salud están simuladas. Los tokens son valores aislados de laboratorio.

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | `test_lists_seeded_tasks` | Camino feliz | `200`; lista de tareas del usuario autenticado con los campos documentados. |
| `GET /api/tasks` | `test_empty_owner_query_defaults_to_authenticated_user` | Borde | `200`; `owner` vacío consulta las tareas del usuario autenticado. |
| `GET /api/tasks` | `test_each_endpoint_requires_authentication` | Error | Sin token válido responde `401` con `{"detail":"Invalid token: invalid token"}`. |
| `GET /api/tasks` | `test_list_tasks_returns_internal_error_when_database_is_unavailable` | Error | Un fallo de SQLite responde `500` sin detalle interno en el cuerpo. |
| `GET /api/tasks` | `test_owner_query_does_not_expose_other_user_tasks` | Autorización / H-API-02 | No devuelve tareas de otro `owner`; el test actualmente **falla** porque la respuesta expone esas tareas. |
| `POST /api/tasks` | `test_creates_task_and_returns_created_task` | Camino feliz | `201`; la respuesta contiene los valores guardados, la identidad autenticada y `createdAt`. |
| `POST /api/tasks` | `test_empty_task_body_uses_documented_defaults` | Borde | Un objeto vacío responde `201` con los valores por defecto documentados. |
| `POST /api/tasks` | `test_task_body_must_be_an_object` | Error | Un cuerpo que no sea objeto responde `422`. |
| `POST /api/tasks` | `test_task_body_is_required` | Error | La ausencia de cuerpo responde `422`. |
| `POST /api/tasks` | `test_each_endpoint_requires_authentication` | Error | Sin token válido responde `401`. |
| `POST /api/tasks` | `test_create_task_returns_internal_error_when_database_is_unavailable` | Error | Un fallo de SQLite responde `500` sin detalle interno. |
| `POST /api/tasks` | `test_create_task_cannot_assign_another_owner` | Autorización / H-API-02 | El propietario debe derivarse de la identidad autenticada; el test actualmente **falla** porque acepta el `owner` enviado por el cliente. |
| `GET /api/summary` | `test_summarizes_tasks_for_authenticated_user` | Camino feliz | `200`; resumen con `owner`, `total`, `byStatus` y `highPriorityOpen`. |
| `GET /api/summary` | `test_summary_for_owner_without_tasks_is_empty` | Borde | `200`; un usuario sin tareas obtiene conteos vacíos y cero. |
| `GET /api/summary` | `test_summary_query_does_not_expose_another_owner` | Autorización / H-API-02 | El resumen debe quedar ligado a la identidad autenticada; el test actualmente **falla** porque la respuesta refleja `owner=trainer`. |
| `GET /api/summary` | `test_summary_excludes_done_and_archived_high_priority_tasks` | Borde | `DONE` y `ARCHIVED` se cuentan por estado, pero no como tareas abiertas de prioridad alta. |
| `GET /api/summary` | `test_each_endpoint_requires_authentication` | Error | Sin token válido responde `401`. |
| `GET /api/summary` | `test_summary_returns_internal_error_when_database_is_unavailable` | Error | Un fallo de SQLite responde `500` sin detalle interno. |
| `POST /api/requirements` | `test_uploads_requirement_file` | Camino feliz | `201`; devuelve nombre, tamaño y propietario y persiste el contenido. |
| `POST /api/requirements` | `test_upload_accepts_empty_file_without_extension` | Borde | Un archivo vacío y sin extensión responde `201` y se persiste vacío, conforme al comportamiento documentado actual. |
| `POST /api/requirements` | `test_each_endpoint_requires_authentication` | Error | Sin token válido responde `401`. |
| `POST /api/requirements` | `test_malformed_multipart_request_returns_bad_request` | Error | Multipart mal formado responde `400` con el detalle documentado. |
| `POST /api/requirements` | `test_missing_upload_file_returns_validation_error` | Error | Sin el campo `file` responde `422`. |
| `POST /api/requirements` | `test_upload_returns_internal_error_when_destination_is_not_directory` | Error | Un destino de carga inválido responde `500` sin detalle interno. |
| `GET /api/backend-health` | `test_backend_health_returns_upstream_status_and_body` | Camino feliz | `200`; devuelve solicitante, estado upstream y cuerpo recibido. |
| `GET /api/backend-health` | `test_backend_health_handles_empty_upstream_body` | Borde | Un upstream `204` sin cuerpo se representa con `status: 204` y `body: ""` en la respuesta `200` de esta API. |
| `GET /api/backend-health` | `test_each_endpoint_requires_authentication` | Error | Sin token válido responde `401`. |
| `GET /api/backend-health` | `test_backend_health_returns_caught_upstream_error` | Error upstream | Una excepción upstream se representa actualmente como HTTP `200`, `status: 0` y el texto de la excepción en `body`. |
| Todas las rutas protegidas | `test_rejects_expired_token` | Error de autenticación | Un token expirado responde `401`. |
| Aplicación | `test_create_app_does_not_seed_an_existing_database` | Inicialización / borde | Reiniciar la aplicación con una base existente conserva los registros y no los vuelve a sembrar. |

La matriz refleja el comportamiento comprobado en el código y la documentación actual. Los tres casos de H-API-02 son pruebas de regresión deliberadamente estrictas: aceptan una respuesta exitosa limitada a la identidad autenticada o una respuesta 4xx, sin fijar un estado de autorización aún no acordado. No se relajaron para hacerlas pasar frente al comportamiento vulnerable observado.

## Código de los tests

El siguiente es el código ejecutable mantenido en `api/tests/test_api.py`:

```python
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
```

## Ejecuciones y cobertura

Todas las ejecuciones se hicieron con directorio de trabajo `api/`, usando el intérprete del entorno del proyecto y el comando:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

| momento | componente e IDs | código de salida | resultado | cobertura |
|---|---|---:|---|---|
| Baseline antes de ampliar tests | `api`; H-API-02, H-API-04 | 0 | `4 passed` | `app/main.py`: 96 sentencias, 7 no cubiertas, 16 ramas, 3 parciales; 91% reportado por Coverage.py. |
| Suite ampliada actual | `api`; H-API-02 | 1 | `27 passed, 3 failed`; fallan `test_owner_query_does_not_expose_other_user_tasks`, `test_create_task_cannot_assign_another_owner` y `test_summary_query_does_not_expose_another_owner`. | `app/main.py`: 95/96 sentencias cubiertas (98.96% de cobertura de sentencias); 16 ramas, 1 parcial; 98% reportado por Coverage.py. La línea no cubierta es la 98. |

**Método:** `pytest-cov` instrumenta `app` con cobertura de ramas activada según la configuración del proyecto y genera el reporte de terminal `term-missing`. El porcentaje combinado mostrado por Coverage.py considera sentencias y ramas; se informa además el numerador/denominador de sentencias.

**Cobertura del código modificado:** no se modificó código de implementación; el único archivo de código cambiado es `api/tests/test_api.py`. La configuración `source = ["app"]` no mide los propios tests, así que no se atribuye a ese archivo un porcentaje de cobertura.

**Cobertura global de la API:** `app/main.py` es el único módulo dentro de `app` medido por esta configuración. La suite ejecutada cubrió 95/96 sentencias (98.96%); el reporte combinado de sentencias y ramas fue 98%. Esto supera el umbral del 85% para la implementación ejercitada, pero no sustituye una medición de cobertura de un cambio futuro en código de producción.

La corrida baseline de cuatro tests se ejecutó antes de agregar los nuevos tests. La corrida actual cubre 30 casos parametrizados/individuales: tres regresiones de autorización fallan contra el comportamiento existente, no por errores de ejecución accidental. Se observaron 65 warnings deprecados relacionados con `on_event` de FastAPI/Starlette y `BlockingPortal` de AnyIO; no se suprimieron.

## Fallos

- **H-API-02 — acceso de tareas entre owners:** `test_owner_query_does_not_expose_other_user_tasks` recibe HTTP `200` y tareas con `owner == "trainer"` al autenticarse como `student`. El cliente puede elegir el `owner` consultado; el aislamiento por identidad no está aplicado.
- **H-API-02 — asignación de tareas a otro owner:** `test_create_task_cannot_assign_another_owner` recibe HTTP `201` y `owner == "trainer"` al enviar ese campo como usuario `student`. El propietario de la tarea puede ser controlado por el cuerpo de la petición.
- **H-API-02 — lectura de resumen de otro owner:** `test_summary_query_does_not_expose_another_owner` recibe `owner == "trainer"` al autenticarse como `student`; el parámetro del resumen no está ligado a la identidad.

Los tres fallos reproducen el mismo hallazgo de autorización H-API-02 y quedan pendientes de la corrección de producción. No se cambió ni se debilitó ningún test para hacer pasar la suite.

## Pendientes

- Corregir H-API-02 en el código de API y volver a ejecutar los tres tests de regresión y la suite completa.
- La cobertura reportada mide `app/`, no los propios archivos de prueba. El test actual alcanza 95/96 sentencias de la implementación, pero esto no sustituye la verificación de cobertura del código productivo después de un cambio futuro.

## Pruebas propuestas

- Tras implementar H-API-02: ejecutar los tres tests fallidos y luego la suite completa con el comando indicado; exigir que no se devuelvan ni asignen tareas de otro owner y que el resumen no revele datos ajenos.
- Mantener el umbral mínimo de 85% y adjuntar el reporte Coverage.py de la implementación corregida.
