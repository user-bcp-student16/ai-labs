# Pruebas de API ReqFlow

## api

Cada ejecucion esta relacionada con el componente `api` y los IDs aplicables. La suite reside en `api/tests/test_api.py`; no se modifico codigo de produccion.

### Matriz de casos

| Endpoint | Caso | Tipo | Resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Listar tareas sembradas del usuario | Camino feliz (H-API-01) | 200 y solo las filas del usuario cuando no se envia `owner`. |
| `GET /api/tasks` | `owner` vacio | Borde (H-API-02) | Usa el username del token. |
| `GET /api/tasks` | Filtro con comillas SQL | Borde (H-API-03) | 200 y lista vacia, sin alterar la consulta. |
| `GET /api/tasks` | Solicitar `owner=trainer` con token `student` | Seguridad (H-API-02) | No devuelve filas de `trainer`. La prueba falla actualmente: la API entrega esa tarea. |
| `GET /api/tasks` | Token invalido | Error 401 (H-API-01) | 401 con detalle de token invalido. |
| `GET /api/tasks` | Fallo SQLite simulado | Error 500 | 500 `Internal Server Error`. |
| `POST /api/tasks` | Crear tarea completa | Camino feliz (H-API-03) | 201 y tarea persistida; summary refleja sus conteos. |
| `POST /api/tasks` | Titulo con comilla SQL | Borde (H-API-03) | 201 y titulo almacenado literalmente. |
| `POST /api/tasks` | Objeto JSON vacio | Borde | 201 con defaults: titulo/descripcion vacios, estado `TODO`, prioridad `MEDIUM`, owner del token. |
| `POST /api/tasks` | Cuerpo que no es objeto JSON | Error 422 | 422 por tipo de cuerpo invalido. |
| `POST /api/tasks` | Token invalido | Error 401 (H-API-01) | 401 con detalle de token invalido. |
| `POST /api/tasks` | Fallo SQLite simulado | Error 500 | 500 `Internal Server Error`. |
| `GET /api/summary` | Conteos del usuario tras crear una tarea | Camino feliz (H-API-03) | 200 con `total`, `byStatus` y `highPriorityOpen` correctos. |
| `GET /api/summary` | Owner desconocido | Borde (H-API-02) | 200 con total cero, mapa vacio y prioridad abierta cero. |
| `GET /api/summary` | Token invalido | Error 401 (H-API-01) | 401 con detalle de token invalido. |
| `GET /api/summary` | Fallo SQLite simulado | Error 500 | 500 `Internal Server Error`. |
| `POST /api/requirements` | Cargar archivo `.txt` | Camino feliz (H-API-04, H-API-05) | 201 y archivo guardado con el tamano informado. |
| `POST /api/requirements` | Archivo vacio y sin extension | Borde (H-API-05) | 201, tamano cero y archivo creado; el codigo no valida extension. |
| `POST /api/requirements` | Falta el campo `file` | Error 422 | 422 con ubicacion `body/file`. |
| `POST /api/requirements` | Token invalido | Error 401 (H-API-01) | 401 con detalle de token invalido. |
| `POST /api/requirements` | Fallo de escritura simulado | Error 500 (H-API-04, H-API-05) | 500 `Internal Server Error`. |
| `GET /api/backend-health` | Backend responde 200 | Camino feliz (H-API-09) | 200 con identidad, status remoto y cuerpo UTF-8. La llamada externa se simula. |
| `GET /api/backend-health` | Error de conexion simulado | Borde (H-API-09) | 200 con `status: 0` y texto del error en `body`. |
| `GET /api/backend-health` | Token invalido | Error 401 (H-API-01) | 401 con detalle de token invalido. |

### Codigo de pruebas

Codigo completo de `api/tests/test_api.py` para esta ejecucion:

```python
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
```

### Ejecuciones y cobertura

#### Línea base (antes de ampliar la suite)

- Componente: `api`.
- IDs relacionados: H-API-01 y H-API-03.
- Directorio de ejecución: `api/`.
- Comando: `.venv\\Scripts\\python.exe -m pytest --cov=app --cov-report=term-missing`.
- Código de salida: `0`.
- Resultado: 6 pruebas aprobadas; cobertura total informada por pytest-cov: 92.13%.

#### Suite ampliada

- Componente: `api`.
- IDs relacionados: H-API-01, H-API-02, H-API-03, H-API-04, H-API-05 y H-API-09.
- Directorio de ejecución: `api/`.
- Comando: `.venv\\Scripts\\python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=json:coverage.json`.
- Código de salida: `1`.
- Resultado: 23 aprobadas y 1 fallida. La falla es `test_lists_only_authenticated_owner_tasks`: con token `student` y `owner=trainer`, la API devuelve la tarea de `trainer`. La prueba se conserva como falla visible; no se marca `xfail` ni se modifica el test para reflejar el defecto.
- Cobertura global de `app`: `110/111` sentencias cubiertas (99.10% de sentencias), 13/16 ramas (81.25%) y 96.85% combinado de sentencias y ramas (pytest-cov lo muestra redondeado como 97%).
- Metodo: pytest-cov/Coverage.py con `branch = true`, `source = ["app"]`; numeradores y denominadores leidos de `coverage.json` producido por esa ejecucion. La cifra global abarca los modulos bajo `app`, no es una medicion aislada de las lineas nuevas de pruebas. No se modifico codigo de produccion.
- Advertencias: 51 avisos de deprecacion de `FastAPI.on_event`/Starlette durante la suite ampliada.

### Fallos

- H-API-02 sigue presente: la ruta confia en el parametro `owner` del cliente (`api/app/main.py:71`). La prueba falla de forma deliberada porque el comportamiento actual permite leer tareas de otro propietario. La correccion de autorizacion no forma parte de este cambio de pruebas.

### Pendientes

- La suite no queda verde hasta que se implemente y apruebe la autorizacion por identidad para `GET /api/tasks` y `GET /api/summary`.
- No se ejecutaron pruebas integradas contra el servicio real de backend-health; sus respuestas se simularon para mantener la suite aislada de otros componentes.
- `coverage.json` es un reporte generado localmente por la ejecucion, no una evidencia versionada requerida.

### Pruebas propuestas

- Tras corregir H-API-02, repetir `GET /api/tasks?owner=trainer` con token `student` y mantener la expectativa de no exponer filas de `trainer`.
- Al cambiar el manejo de errores del servidor o del backend-health, actualizar los ejemplos solo despues de comprobar el nuevo cuerpo observable.
