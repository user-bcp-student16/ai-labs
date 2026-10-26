# ReqFlow API endpoints

## API — FastAPI

### Estado del contrato

- **Contrato observado:** este apartado se verificó contra `api/app/main.py`
  y ejemplos ejecutados con una base SQLite y un directorio de carga
  temporales.
- **Contrato acordado:** no hay un contrato acordado separado del
  comportamiento observado.
- **Riesgos y preguntas pendientes:** la autenticación sigue usando un token
  Base64 con secreto fijo; las consultas permiten elegir `owner`; el SQL se
  construye por concatenación; la carga usa el nombre de archivo recibido y no
  define extensión ni tamaño máximo. Estos comportamientos se documentan, no
  se consideran controles seguros. Véanse H-API-01 a H-API-05 en
  [HALLAZGOS.md](../HALLAZGOS.md).

### Autenticación común

Las cinco rutas requieren el header:

```http
Authorization: Bearer <token>
```

El token observado es Base64 de la cadena
`username|role|expiracion_unix|WORKSHOP_SECRET_2026`. Para los ejemplos se
utiliza este token local de demostración:

```text
c3R1ZGVudHxTVFVERU5UfDIxNDc0ODM2NDd8V09SS1NIT1BfU0VDUkVUXzIwMjY=
```

Su expiración de ejemplo es `2147483647`. El secreto es un valor de laboratorio
codificado, no una credencial de producción. Base64 no firma ni cifra el token.
El código también acepta el valor codificado sin el prefijo `Bearer ` porque
elimina ese texto si está presente.

Las solicitudes sin token o con token inválido responden `401`:

```json
{"detail":"Invalid token: invalid token"}
```

El texto del detalle puede variar según el error al decodificar o validar el
token.

## `GET /api/tasks`

Implementación observada en `api/app/main.py:67-75`.

### 1. Qué hace

Lista las tareas cuyo propietario coincide con el valor `owner` solicitado o,
si no se proporciona, con el nombre de usuario decodificado del token.

### 2. Autenticación

Requiere `Authorization: Bearer <token>` como se describe en Autenticación
común.

### 3. Request

No tiene cuerpo.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `owner` (query) | string | no | Propietario que se usa para filtrar. Si falta o está vacío, se usa el usuario del token. |

Ejemplo completo:

```http
GET /api/tasks?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer c3R1ZGVudHxTVFVERU5UfDIxNDc0ODM2NDd8V09SS1NIT1BfU0VDUkVUXzIwMjY=
```

### 4. Response exitosa

Estado `200 OK`; cuerpo: array de tareas.

| campo | tipo | descripción |
|---|---|---|
| `id` | integer | Identificador de la tarea. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado guardado. |
| `owner` | string | Propietario guardado. |
| `priority` | string | Prioridad guardada. |
| `createdAt` | string | Fecha de creación serializada desde `created_at` de SQLite. |

Ejemplo observado con las tareas de inicio:

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-10-26 21:14:44"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-10-26 21:14:44"
  }
]
```

### 5. Responses de error

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401` | Falta `Authorization` o el token no se puede validar. | `{"detail":"Invalid token: invalid token"}` |
| `500` | Ocurre un error no controlado al consultar SQLite. El endpoint no define un manejador propio. | Texto plano: `Internal Server Error` |

### 6. Notas de seguridad

El parámetro `owner` se usa directamente y puede seleccionar tareas de otro
propietario; no queda limitado a la identidad del token. Además, el filtro SQL
se concatena con ese valor. La firma del token no se verifica. Estos riesgos
siguen pendientes.

## `POST /api/tasks`

Implementación observada en `api/app/main.py:77-88`.

### 1. Qué hace

Crea una tarea y devuelve el registro almacenado.

### 2. Autenticación

Requiere `Authorization: Bearer <token>` como se describe en Autenticación
común.

### 3. Request

El cuerpo debe ser un objeto JSON. No se usa un modelo Pydantic; las claves
indicadas se convierten a string con `str(...)`.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `title` (body) | valor JSON convertido a string | no | Título. Predeterminado: `""`. |
| `description` (body) | valor JSON convertido a string | no | Descripción. Predeterminado: `""`. |
| `status` (body) | valor JSON convertido a string | no | Estado. Predeterminado: `"TODO"`. |
| `priority` (body) | valor JSON convertido a string | no | Prioridad. Predeterminado: `"MEDIUM"`. |
| `owner` (body) | valor JSON convertido a string | no | Propietario. Si falta, se usa el nombre de usuario del token. |

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer c3R1ZGVudHxTVFVERU5UfDIxNDc0ODM2NDd8V09SS1NIT1BfU0VDUkVUXzIwMjY=
Content-Type: application/json

{
  "title": "Test",
  "description": "Sample",
  "status": "TODO",
  "priority": "HIGH"
}
```

### 4. Response exitosa

Estado `201 Created`; cuerpo: una tarea con los mismos campos descritos para
`GET /api/tasks`.

| campo | tipo | descripción |
|---|---|---|
| `id` | integer | Identificador asignado por SQLite. |
| `title` | string | Título almacenado. |
| `description` | string | Descripción almacenada. |
| `status` | string | Estado almacenado. |
| `owner` | string | Propietario almacenado. |
| `priority` | string | Prioridad almacenada. |
| `createdAt` | string | Fecha de creación serializada desde SQLite. |

Ejemplo observado al crear la tarea del request:

```json
{
  "id": 4,
  "title": "Test",
  "description": "Sample",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-10-26 21:14:44"
}
```

### 5. Responses de error

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401` | Falta `Authorization` o el token no se puede validar. | `{"detail":"Invalid token: invalid token"}` |
| `422` | Falta el body o FastAPI no puede validarlo como objeto JSON. | `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}` |
| `422` | El JSON no es un objeto. | `{"detail":[{"type":"dict_type","loc":["body"],"msg":"Input should be a valid dictionary","input":[]}]}` |
| `500` | Ocurre un error no controlado al insertar o leer SQLite. | Texto plano: `Internal Server Error` |

### 6. Notas de seguridad

El campo `owner` del body puede prevalecer sobre el usuario autenticado. Los
valores de entrada se interpolan en una sentencia SQL y no se validan mediante
un modelo Pydantic. No hay comprobación de rol.

## `GET /api/summary`

Implementación observada en `api/app/main.py:90-105`.

### 1. Qué hace

Devuelve el total de tareas y los conteos de estado y prioridad para un
propietario.

### 2. Autenticación

Requiere `Authorization: Bearer <token>` como se describe en Autenticación
común.

### 3. Request

No tiene cuerpo.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `owner` (query) | string | no | Propietario del resumen. Si falta o está vacío, se usa el usuario del token. |

Ejemplo completo:

```http
GET /api/summary?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer c3R1ZGVudHxTVFVERU5UfDIxNDc0ODM2NDd8V09SS1NIT1BfU0VDUkVUXzIwMjY=
```

### 4. Response exitosa

Estado `200 OK`.

| campo | tipo | descripción |
|---|---|---|
| `owner` | string | Propietario usado para el resumen. |
| `total` | integer | Número de tareas del propietario. |
| `byStatus` | object de string a integer | Conteo de tareas por cada estado presente. |
| `highPriorityOpen` | integer | Tareas `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo observado después de crear la tarea del ejemplo anterior:

```json
{
  "owner": "student",
  "total": 3,
  "byStatus": {
    "TODO": 2,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 2
}
```

### 5. Responses de error

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401` | Falta `Authorization` o el token no se puede validar. | `{"detail":"Invalid token: invalid token"}` |
| `500` | Ocurre un error no controlado al consultar SQLite. | Texto plano: `Internal Server Error` |

### 6. Notas de seguridad

El parámetro `owner` puede seleccionar datos de otro propietario y se concatena
directamente en SQL. La consulta no está ligada a la identidad del token.

## `POST /api/requirements`

Implementación observada en `api/app/main.py:107-112`.

### 1. Qué hace

Guarda un archivo recibido como requisito y devuelve sus metadatos.

### 2. Autenticación

Requiere `Authorization: Bearer <token>` como se describe en Autenticación
común.

### 3. Request

El cuerpo es `multipart/form-data`.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `file` (form-data) | archivo (`UploadFile`) | sí | Contenido del archivo; se usa también el nombre enviado por el cliente. |

Ejemplo completo; el archivo local `requirements.txt` contiene el texto
`Requirement example`:

```bash
curl -i -X POST http://localhost:8000/api/requirements \
  -H "Authorization: Bearer c3R1ZGVudHxTVFVERU5UfDIxNDc0ODM2NDd8V09SS1NIT1BfU0VDUkVUXzIwMjY=" \
  -F "file=@requirements.txt;type=text/plain"
```

### 4. Response exitosa

Estado `201 Created`.

| campo | tipo | descripción |
|---|---|---|
| `owner` | string | Nombre de usuario del token. |
| `fileName` | string o null | Nombre reportado por el cliente en la parte multipart. |
| `storedAt` | string | Ruta formada con el directorio configurado y el nombre recibido. |
| `size` | integer | Cantidad de bytes leídos. |

Ejemplo observado; `storedAt` depende del directorio configurado:

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "C:\\Users\\Usuario\\AppData\\Local\\Temp\\tmpuhgewgec\\uploads\\requirements.txt",
  "size": 19
}
```

### 5. Responses de error

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401` | Falta `Authorization` o el token no se puede validar. | `{"detail":"Invalid token: invalid token"}` |
| `400` | El cuerpo multipart está mal formado. | `{"detail":"There was an error parsing the body"}` |
| `422` | No se incluye la parte requerida `file`. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |
| `500` | Ocurre un error no controlado al leer o escribir el archivo. | Texto plano: `Internal Server Error` |

### 6. Notas de seguridad

El nombre recibido se combina directamente con el directorio de carga. El
código no define allowlist de extensiones ni tamaño máximo y lee el archivo
completo antes de escribirlo. `storedAt` expone la ruta resultante.

## `GET /api/backend-health`

Implementación observada en `api/app/main.py:114-121`.

### 1. Qué hace

Consulta el endpoint de salud del servicio de autenticación configurado para
mostrar su estado a quien llama.

### 2. Autenticación

Requiere `Authorization: Bearer <token>` como se describe en Autenticación
común.

### 3. Request

No tiene query parameters ni cuerpo.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `Authorization` (header) | string | sí | Header de autenticación común. |

La URL upstream se configura con `AUTH_HEALTH_URL`; si no está definida, el
código usa `http://localhost:8080/q/health`.

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer c3R1ZGVudHxTVFVERU5UfDIxNDc0ODM2NDd8V09SS1NIT1BfU0VDUkVUXzIwMjY=
```

### 4. Response exitosa

La respuesta HTTP de esta ruta es `200 OK`; `status` contiene el estado HTTP
del upstream y `body` su contenido decodificado como UTF-8.

| campo | tipo | descripción |
|---|---|---|
| `requestedBy` | string | Nombre de usuario del token. |
| `status` | integer | Estado HTTP del upstream; cero si la consulta lanza una excepción. |
| `body` | string | Cuerpo UTF-8 del upstream o texto de la excepción capturada. |

Ejemplo observado con un upstream local que respondió `200` y el cuerpo
`{"health":"UP"}`:

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "{\"health\":\"UP\"}"
}
```

### 5. Responses de error

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401` | Falta `Authorization` o el token no se puede validar. | `{"detail":"Invalid token: invalid token"}` |

Si falla la consulta al upstream, la ruta no devuelve un error HTTP: responde
`200 OK` con `status: 0` y el texto de la excepción en `body`. El texto depende
del error y del entorno. No hay un manejador para errores de autenticación
distinto del `401` común.

### 6. Notas de seguridad

`AUTH_HEALTH_URL` controla el destino de una solicitud HTTP saliente. El código
devuelve directamente al cliente el cuerpo del upstream o el texto de la
excepción, que puede revelar detalles operativos.
