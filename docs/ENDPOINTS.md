# Contratos HTTP de ReqFlow

## api

### Estado del contrato

Este apartado documenta el comportamiento observado en la API actual. No hay un contrato de API previamente acordado registrado en este documento. Los ejemplos muestran valores concretos compatibles con el código; `createdAt`, los IDs, las rutas locales y el cuerpo de backend-health pueden variar según ejecución y configuración.

### GET /api/tasks

#### 1. Que hace
Devuelve las tareas del propietario solicitado; si no se indica propietario, lista las tareas de la identidad del token.

#### 2. Autenticacion
Requiere encabezado Authorization con un JWT firmado HS256 y claims sub, role, iat y exp. La API valida la firma y expiracion con AUTH_TOKEN_SECRET (minimo 32 bytes). El formato heredado solo se acepta si LEGACY_TOKEN_ACCEPT_UNTIL configura un corte UTC vigente; si no, se rechaza.

#### 3. Request

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `owner` (query) | string | No | Propietario a filtrar. Si falta o es cadena vacia se usa el `username` del token. No se restringe a la identidad autenticada. |
| `Authorization` (header) | string | Si | Header Bearer indicado arriba. |

Ejemplo:

```http
GET /api/tasks?owner=student HTTP/1.1
Authorization: Bearer <token>
```

#### 4. Response exitosa
Codigo: `200 OK`.

| Campo | Tipo | Descripcion |
|---|---|---|
| respuesta | array de tareas | Puede estar vacio. |
| `id` | integer | Identificador de la tarea. |
| `title` | string | Titulo. |
| `description` | string | Descripcion. |
| `status` | string | Estado almacenado, por ejemplo `TODO` o `IN_PROGRESS`. |
| `owner` | string | Propietario almacenado. |
| `priority` | string | Prioridad almacenada, por ejemplo `HIGH` o `MEDIUM`. |
| `createdAt` | string | Fecha y hora producidas por SQLite como `YYYY-MM-DD HH:MM:SS`. |

Ejemplo:

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-11-02 09:00:00"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-11-02 09:00:00"
  }
]
```

Los tiempos del ejemplo son ilustrativos; la base de datos fija `createdAt` al crear cada fila.

#### 5. Errores

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token invalido. | `{"detail":"Invalid token: authentication failed"}` |
| `500 Internal Server Error` | Error no manejado al consultar SQLite. La ruta no define un cuerpo para este caso; el manejador ASGI predeterminado responde texto `Internal Server Error`. Un manejador de despliegue puede cambiarlo. | `Internal Server Error` (texto). |

#### 6. Notas de seguridad
El filtro `owner` es controlado por el cliente y no se compara con el usuario del token. Un usuario con token valido puede solicitar las tareas de otro `owner` (IDOR, H-API-02). Los JWT se verifican con HS256, pero no se validan emisor ni audiencia. La compatibilidad con el formato heredado permanece disponible hasta el corte configurado (H-API-01, H-AUTH-02). SQL se ejecuta con parametro SQLite para el valor de `owner` (H-API-03).

Implementacion observable: `api/app/main.py:24-78`, `api/app/main.py:116-123`; consulta parametrizada en `api/app/repositories/tasks.py:7-9`.

### POST /api/tasks

#### 1. Que hace
Crea una tarea y devuelve la fila persistida.

#### 2. Autenticacion
Requiere `Authorization: Bearer <token>` con el formato y validacion descritos en GET `/api/tasks`.

#### 3. Request
El cuerpo debe ser un objeto JSON. Sus campos son opcionales; el endpoint convierte cada valor con `str()` antes de persistirlo.

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `title` (body) | valor JSON convertido a string | No | Titulo. Por defecto, cadena vacia. |
| `description` (body) | valor JSON convertido a string | No | Descripcion. Por defecto, cadena vacia. |
| `status` (body) | valor JSON convertido a string | No | Estado. Por defecto, `TODO`. |
| `priority` (body) | valor JSON convertido a string | No | Prioridad. Por defecto, `MEDIUM`. |
| `owner` (body) | valor JSON convertido a string | No | Propietario. Por defecto, `username` del token; si se envia, el valor del cliente se usa sin comparacion. |
| `Authorization` (header) | string | Si | Header Bearer indicado arriba. |

Ejemplo:

```http
POST /api/tasks HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "priority": "HIGH"
}
```

#### 4. Response exitosa
Codigo: `201 Created`.

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | integer | Identificador generado por SQLite. |
| `title` | string | Titulo persistido. |
| `description` | string | Descripcion persistida. |
| `status` | string | Estado persistido. |
| `owner` | string | Propietario persistido. |
| `priority` | string | Prioridad persistida. |
| `createdAt` | string | Fecha y hora generadas por SQLite como `YYYY-MM-DD HH:MM:SS`. |

Ejemplo:

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-11-02 09:00:00"
}
```

#### 5. Errores

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token invalido. | `{"detail":"Invalid token: authentication failed"}` |
| `422 Unprocessable Entity` | Cuerpo ausente o no es un objeto JSON. | `{"detail":[{"type":"dict_type","loc":["body"],"msg":"Input should be a valid dictionary","input":[]}]}` al enviar `[]`. |
| `500 Internal Server Error` | Error no manejado al insertar o leer SQLite. No hay cuerpo definido por esta ruta; el manejador ASGI predeterminado responde texto `Internal Server Error`. | `Internal Server Error` (texto). |

#### 6. Notas de seguridad
El cuerpo permite que el cliente elija `owner`, incluso si difiere del usuario autenticado (IDOR, H-API-02). La ruta convierte valores a texto, pero no valida listas permitidas para estado o prioridad. La escritura y lectura usan parametros SQLite (H-API-03). El error 401 usa un detalle generico.

Implementacion observable: `api/app/main.py:24-78`, `api/app/main.py:128-137`; SQL parametrizado en `api/app/repositories/tasks.py:15-28`.

### GET /api/summary

#### 1. Que hace
Resume el total de tareas, su distribucion por estado y las tareas de prioridad alta que siguen abiertas para un propietario.

#### 2. Autenticacion
Requiere `Authorization: Bearer <token>` con el formato y validacion descritos en GET `/api/tasks`.

#### 3. Request

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `owner` (query) | string | No | Propietario a resumir. Si falta o es cadena vacia se usa el `username` del token. No se restringe a la identidad autenticada. |
| `Authorization` (header) | string | Si | Header Bearer indicado arriba. |

Ejemplo:

```http
GET /api/summary?owner=student HTTP/1.1
Authorization: Bearer <token>
```

#### 4. Response exitosa
Codigo: `200 OK`.

| Campo | Tipo | Descripcion |
|---|---|---|
| `owner` | string | Propietario consultado. |
| `total` | integer | Numero total de tareas. |
| `byStatus` | object de string a integer | Conteo por cada valor de `status`. |
| `highPriorityOpen` | integer | Conteo de tareas `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo con las tareas sembradas para `student`:

```json
{
  "owner": "student",
  "total": 2,
  "byStatus": {
    "TODO": 1,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 1
}
```

#### 5. Errores

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token invalido. | `{"detail":"Invalid token: authentication failed"}` |
| `500 Internal Server Error` | Error no manejado al consultar SQLite. No hay cuerpo definido por esta ruta; el manejador ASGI predeterminado responde texto `Internal Server Error`. | `Internal Server Error` (texto). |

#### 6. Notas de seguridad
El cliente elige `owner`; la API no comprueba que pertenezca a la identidad autenticada (IDOR, H-API-02). El valor se pasa parametrizado a SQLite (H-API-03). El conteo considera abiertas las prioridades altas salvo los estados exactos `DONE` y `ARCHIVED`.

Implementacion observable: `api/app/main.py:90-106`; consulta parametrizada en `api/app/repositories/tasks.py:32-34`.

### POST /api/requirements

#### 1. Que hace
Guarda en el directorio de uploads el archivo de requerimientos recibido y devuelve sus metadatos de almacenamiento.

#### 2. Autenticacion
Requiere `Authorization: Bearer <token>` con el formato y validacion descritos en GET `/api/tasks`.

#### 3. Request
El cuerpo usa `multipart/form-data`.

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `file` (form-data) | archivo binario | Si | Archivo que se guarda. El nombre multipart se usa directamente como nombre de destino. |
| `Authorization` (header) | string | Si | Header Bearer indicado arriba. |

Ejemplo:

```http
POST /api/requirements HTTP/1.1
Authorization: Bearer <token>
Content-Type: multipart/form-data; boundary=example

--example
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login must be accessible
--example--
```

#### 4. Response exitosa
Codigo: `201 Created`.

| Campo | Tipo | Descripcion |
|---|---|---|
| `owner` | string | `username` del token. |
| `fileName` | string o null | Nombre recibido en el multipart. |
| `storedAt` | string | Ruta del archivo guardado. Depende de `WORKSHOP_UPLOAD_DIR` y del directorio de trabajo. |
| `size` | integer | Numero de bytes leidos y escritos. |

Ejemplo con el directorio por defecto y 24 bytes:

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "uploads/requirements.txt",
  "size": 24
}
```

#### 5. Errores

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token invalido. | `{"detail":"Invalid token: authentication failed"}` |
| `422 Unprocessable Entity` | Falta el campo `file` o el multipart no valida. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` al omitir el archivo. |
| `500 Internal Server Error` | Error no manejado al leer o escribir el archivo. La ruta no define cuerpo propio; el manejador ASGI predeterminado responde texto `Internal Server Error`. | `Internal Server Error` (texto). |

#### 6. Notas de seguridad
El nombre recibido se une directamente al directorio, sin normalizacion ni comprobacion de confinamiento; un nombre con componentes de ruta puede escapar de uploads (H-API-04). El contenido completo se lee en memoria y no hay limite de extension ni tamano (H-API-05). La respuesta revela la ruta del servidor en `storedAt`. No hay una respuesta de error propia para fallos de disco; el texto exacto de 500 puede cambiar con el manejador del despliegue.

Implementacion observable: `api/app/main.py:107-111`.

### GET /api/backend-health

#### 1. Que hace
Consulta el endpoint de salud configurado para el backend de autenticacion y devuelve el resultado junto con la identidad que hizo la peticion.

#### 2. Autenticacion
Requiere `Authorization: Bearer <token>` con el formato y validacion descritos en GET `/api/tasks`.

#### 3. Request

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `Authorization` (header) | string | Si | Header Bearer indicado arriba. |
| `AUTH_HEALTH_URL` (configuracion del servidor) | URL string | No | Variable de entorno. Por defecto `http://localhost:8080/q/health`; no es un parametro enviado por el cliente. |

Ejemplo:

```http
GET /api/backend-health HTTP/1.1
Authorization: Bearer <token>
```

#### 4. Response exitosa
Codigo HTTP de la API: `200 OK` cuando la autenticacion es valida, incluso si falla la llamada al backend consultado.

| Campo | Tipo | Descripcion |
|---|---|---|
| `requestedBy` | string | `username` del token. |
| `status` | integer | Codigo HTTP recibido del backend; `0` si la llamada lanza una excepcion. |
| `body` | string | Cuerpo del backend decodificado como UTF-8 o texto de la excepcion si falla la llamada. |

Ejemplo de forma de respuesta (el cuerpo depende del backend configurado):

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "<cuerpo UTF-8 del backend>"
}
```

#### 5. Errores

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token invalido. | `{"detail":"Invalid token: authentication failed"}` |

Una excepcion de conexion al backend no se devuelve como error HTTP: la ruta responde `200 OK` con `status: 0` y el texto de la excepcion en `body`.

#### 6. Notas de seguridad
La respuesta puede exponer el texto crudo de errores del cliente HTTP en `body` (H-API-09). La URL de destino se controla con una variable de entorno del servidor. Los JWT verifican firma y expiracion, pero no emisor ni audiencia; los tokens heredados solo se aceptan antes del corte configurado (H-API-01, H-AUTH-02).

Implementacion observable: `api/app/main.py:114-120`.

### Preguntas abiertas y riesgos pendientes

- La transicion de tokens heredados requiere configurar `LEGACY_TOKEN_ACCEPT_UNTIL` y desactivar la compatibilidad al llegar el corte (H-API-01, H-AUTH-02).
- La autorizacion por `owner` no esta vinculada a la identidad del token en tasks ni en summary (H-API-02).
- La politica de extensiones, tamano maximo y nombre seguro de cargas sigue sin definirse ni aplicarse (H-API-04 y H-API-05).
- Las rutas no especifican respuestas JSON propias para errores internos de SQLite o del sistema de archivos. El cuerpo 500 depende del manejador ASGI del despliegue.
- El contrato exacto del cuerpo de backend-health depende del servicio configurado; no se inspecciono otro componente.
