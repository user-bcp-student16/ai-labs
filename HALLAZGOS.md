# Hallazgos

## API — contrato y flujo observado

`docs/ENDPOINTS.md` no existe. Lo siguiente se deriva del código de `api/`;
el contrato acordado queda pendiente de documentar y validar.

| Método y ruta | Autenticación y contrato observado |
|---|---|
| `GET /api/tasks` | Requiere `Authorization`; acepta `owner` opcional y, si falta, usa el usuario del token. Devuelve tareas con `id`, `title`, `description`, `status`, `owner`, `priority` y `createdAt`. (`api/app/main.py:56-64,67-75`) |
| `POST /api/tasks` | Requiere `Authorization`; recibe un objeto JSON y devuelve la tarea creada con estado 201. `status`, `priority` y `owner` tienen valores predeterminados. (`api/app/main.py:56-64,77-88`) |
| `GET /api/summary` | Requiere `Authorization`; acepta `owner` opcional y devuelve `owner`, `total`, `byStatus` y `highPriorityOpen`. (`api/app/main.py:90-105`) |
| `POST /api/requirements` | Requiere `Authorization`; recibe `file` como multipart y devuelve `owner`, `fileName`, `storedAt` y `size`, con estado 201. (`api/app/main.py:107-112`) |
| `GET /api/backend-health` | Requiere `Authorization`; devuelve `requestedBy`, `status` y `body`. Si falla la consulta al backend, el código devuelve `status: 0` y el texto de la excepción. (`api/app/main.py:114-121`) |

El token se toma de `Authorization`, se decodifica desde Base64 y se interpreta
como `username|role|expiracion|secreto`; se comprueba el secreto fijo y la
expiración. (`api/app/main.py:14,17-25`) `create_app` resuelve la ruta de
SQLite desde el argumento o `WORKSHOP_DB_PATH`, crea una conexión compartida,
la tabla y datos iniciales si está vacía; las rutas consultan esa conexión
directamente. (`api/app/main.py:29-42,46,67-105`) La carga construye la ruta con
el nombre recibido, lee todo el archivo y escribe sus bytes. (`api/app/main.py:107-111`)

## Matriz de seguimiento

Los hallazgos están ordenados por severidad. Las versiones de dependencias
identifican un candidato de SCA, no una CVE confirmada; la verificación de
advisories queda pendiente. El análisis es estático; no se ejecutaron pruebas.

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido y sin firma | Vulnerabilidad | Base64 no autentica el contenido y el secreto fijo está en el código; no se verifican firma, emisor ni audiencia. Si se conoce el secreto, se pueden falsificar identidad, rol o expiración y acceder a rutas protegidas como otra identidad. | api/app/main.py:14, api/app/main.py:19-22 | alta | Pendiente |
| H-API-02 | api | Acceso a tareas de otro `owner` | Vulnerabilidad | La identidad del token no limita el `owner` de lectura ni el de creación: el cliente puede pedir tareas de otro usuario o asignar la tarea creada a otro propietario. | api/app/main.py:68-70, api/app/main.py:78, api/app/main.py:83 | alta | Pendiente |
| H-API-03 | api | Filtros e inserts SQL concatenados | Vulnerabilidad | Valores controlados por el cliente se concatenan en consultas SQL. Esto permite alterar las consultas de lectura o escritura y puede exponer o modificar registros. | api/app/main.py:70, api/app/main.py:84, api/app/main.py:93 | alta | Pendiente |
| H-API-04 | api | Nombre y tamaño de archivo sin controles | Vulnerabilidad | El nombre recibido se usa directamente para formar la ruta, sin normalización ni límite de extensión o tamaño; puede permitir escritura fuera del directorio previsto y consumo excesivo de memoria al leer el archivo completo. | api/app/main.py:109-111 | alta | Pendiente |
| H-API-05 | api | Versiones de dependencias candidatas a revisión SCA | Vulnerabilidad | `urllib3` y `python-multipart` están fijadas a las versiones señaladas por RETO.md. La presencia de las versiones está confirmada, pero su afectación por advisories y la severidad no; no se asigna una CVE sin esa evidencia. | api/requirements.txt:4-5 | media | Pendiente |
| H-API-06 | api | Rutas, persistencia, reglas y serialización concentradas en un módulo | Refactor | `create_app` crea la base y define serialización, rutas, SQL y reglas de resumen en el mismo módulo; el acoplamiento dificulta aislar y probar cambios sin afectar otras responsabilidades. | api/app/main.py:29-42, api/app/main.py:56, api/app/main.py:67-121 | baja | Pendiente |
| H-API-07 | api | Tipado genérico, excepciones amplias y lógica anidada | Refactor | El body y varias respuestas usan `dict`/`Any`, se capturan excepciones genéricas y el resumen anida condiciones; esto dificulta validar contratos y acotar errores o mantener las reglas. | api/app/main.py:25, api/app/main.py:78, api/app/main.py:94-103, api/app/main.py:120 | baja | Pendiente |
| H-API-08 | api | Lectura de tareas de otro `owner` falla en prueba de caracterización | Prueba fallida | `test_owner_query_does_not_expose_other_user_tasks` falla porque `GET /api/tasks` devuelve tareas de otro propietario cuando se envía `owner`. Es la manifestación de H-API-02 en la suite; ya fallaba antes de H-API-01. Verificado con `python tools/lab.py test api` (3 failed, 39 passed, cobertura 94%). | api/tests/test_api.py:158 | alta | Pendiente |
| H-API-09 | api | Creación de tarea con otro `owner` falla en prueba de caracterización | Prueba fallida | `test_create_task_cannot_assign_another_owner` falla porque `POST /api/tasks` acepta un `owner` distinto al del token. Es la manifestación de H-API-02 en la suite; ya fallaba antes de H-API-01. Verificado con `python tools/lab.py test api`. | api/tests/test_api.py:226 | alta | Pendiente |
| H-API-10 | api | Resumen de otro `owner` falla en prueba de caracterización | Prueba fallida | `test_summary_query_does_not_expose_another_owner` falla porque `GET /api/summary` acepta `owner` ajeno al token. Es la manifestación de H-API-02 en la suite; ya fallaba antes de H-API-01. Verificado con `python tools/lab.py test api`. | api/tests/test_api.py:282 | alta | Pendiente |
