# Hallazgos de seguimiento

Matriz de Discovery. Componente api. Evidencias citadas como api/ruta:linea desde la raiz de ai-labs. Estado inicial de todos los hallazgos: Pendiente. Sin cambios de codigo en este paso.

## api

### Matriz de seguimiento

id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado
--- | --- | --- | --- | --- | --- | --- | ---
H-API-01 | api | Token Base64 con secreto embebido y sin firma | Vulnerabilidad | Quien conozca el secreto fijo del codigo puede fabricar tokens con username y role arbitrarios. El role se devuelve sin verificar y ninguna ruta lo usa. La expiracion si se valida, pero no hay emisor ni audiencia. | api/app/main.py:14, api/app/main.py:19-24; api/tests/test_api.py:11 (mismo secreto en pruebas) | alta | Aprobado
H-API-02 | api | Autorizacion: el cliente elige el owner | Vulnerabilidad | El parametro owner de las consultas y el campo owner del body se usan sin compararlos con la identidad del token. Cualquier usuario autenticado lee tareas y resumen de otro owner y crea tareas a nombre de otro. | api/app/main.py:68-69, api/app/main.py:83, api/app/main.py:91-92 | alta | Aprobado
H-API-03 | api | SQL concatenado en listados, inserts y resumen | Vulnerabilidad | Los valores del cliente se concatenan en el SQL. Un titulo, descripcion u owner con comillas altera la consulta, lee filas de otros owners o rompe el insert. | api/app/main.py:70, api/app/main.py:84, api/app/main.py:93 (tambien api/app/main.py:87 con lastrowid, riesgo bajo) | alta | Resuelto: consultas parametrizadas en api/app/repositories/tasks.py
H-API-04 | api | Nombre de archivo subido usado tal cual (path traversal) | Vulnerabilidad | file.filename se une a la ruta de carga sin normalizar. Un nombre con componentes de ruta escribe fuera del directorio de uploads y la respuesta expone la ruta real almacenada. | api/app/main.py:109, api/app/main.py:112 | alta | Aprobado
H-API-05 | api | Carga sin limite de extension ni de tamano | Vulnerabilidad | Se acepta cualquier extension y el archivo completo se lee en memoria antes de escribirlo. Un archivo grande agota memoria o disco, y un HTML o ejecutable queda guardado sin filtro. | api/app/main.py:108, api/app/main.py:110-111 | media | Aprobado
H-API-06 | api | Dependencia urllib3 2.5.0 sin revisar advisories | Vulnerabilidad (SCA) | La version fijada puede tener CVEs conocidos. Aun no se confirma cual aplica ni cual es la version corregida. Se usa en backend-health para HTTP saliente. | api/requirements.txt:4 | media | Pendiente
H-API-07 | api | Dependencia python-multipart 0.0.21 sin revisar advisories | Vulnerabilidad (SCA) | Parsea el cuerpo multipart de la carga de requerimientos. Un advisory aplicable afectaria la subida. Pendiente confirmar CVEs y version corregida. | api/requirements.txt:5 | media | Pendiente
H-API-08 | api | CORS con origen comodin y credenciales (no listado en RETO.md) | Vulnerabilidad | allow_origins con comodin junto con allow_credentials permite que cualquier sitio envie peticiones autenticadas desde el navegador. | api/app/main.py:50-51 | media | Pendiente
H-API-09 | api | Errores exponen detalle interno (no listado en RETO.md) | Vulnerabilidad | El 401 concatena str(error) en el detail y backend-health devuelve str(error) como cuerpo. Se filtra informacion interna al cliente. | api/app/main.py:26, api/app/main.py:121 | media | Pendiente
H-API-10 | api | Arquitectura en un solo archivo | Refactor | Rutas, acceso SQLite, reglas del resumen y serializacion conviven dentro de create_app. Un cambio de esquema o de regla toca el mismo bloque que la capa HTTP. | api/app/main.py:29-127 (serializacion en 56-65, reglas del resumen en 90-105) | media | Pendiente
H-API-11 | api | Tipado debil con dict[str, Any] | Refactor | Payload, respuestas e identidad son diccionarios sin esquema. Un campo mal escrito o de tipo incorrecto pasa sin error hasta runtime o llega a la BD. | api/app/main.py:17, api/app/main.py:56, api/app/main.py:78, api/app/main.py:91, api/app/main.py:108 | baja | Pendiente
H-API-12 | api | Excepciones amplias | Refactor | except Exception captura tambien errores de programacion y oculta la causa real. En legacy_identity cualquier fallo se convierte en 401. | api/app/main.py:25, api/app/main.py:120 | baja | Pendiente
H-API-13 | api | Condicionales anidados y duplicacion | Refactor | El conteo de highPriorityOpen tiene tres niveles de if y la lista de columnas del SELECT se repite. Conviene extraer funciones pequenas y una constante de columnas. | api/app/main.py:101-104, api/app/main.py:70, api/app/main.py:87 | baja | Pendiente
H-API-14 | api | Valores magicos sueltos (no listado en RETO.md) | Refactor | Secreto, URL por defecto y timeout estan escritos en linea. AGENTS.md (api, regla 12) pide constantes con nombre. | api/app/main.py:14, api/app/main.py:116, api/app/main.py:118 | baja | Pendiente
H-API-15 | api | Hook on_event obsoleto (no listado en RETO.md) | Sugerencia | FastAPI marca on_event como obsoleto. El manejo de lifespan es la forma vigente de cerrar la conexion. | api/app/main.py:123-125 | baja | Pendiente

### Mapa observado de rutas

Metodo | Ruta | Identidad por token | Linea | Acceso a datos
--- | --- | --- | --- | ---
GET | /api/tasks | Si (legacy_identity) | api/app/main.py:67-75 | SQLite, SELECT concatenado (70)
POST | /api/tasks | Si | api/app/main.py:77-88 | SQLite, INSERT concatenado (84) y SELECT por id (87)
GET | /api/summary | Si | api/app/main.py:90-105 | SQLite, SELECT concatenado (93)
POST | /api/requirements | Si | api/app/main.py:107-112 | Escritura en disco en WORKSHOP_UPLOAD_DIR (109-111)
GET | /api/backend-health | Si | api/app/main.py:114-121 | HTTP saliente a AUTH_HEALTH_URL (116-118)

### Flujo del token

1. El cliente envia `Authorization: Bearer <base64>` (api/app/main.py:19).
2. Se decodifica el Base64 y se separa en cuatro partes con el separador pipe (api/app/main.py:20-21).
3. Se valida el secreto fijo y que la expiracion no haya pasado (api/app/main.py:22).
4. Se devuelven username y role (api/app/main.py:24). Solo username se usa; el owner por defecto sale de aqui.

### Acceso a SQLite

- Conexion unica creada en create_app con check_same_thread=False y sin lock (api/app/main.py:35-36).
- La tabla tasks se crea si falta y se siembran tres filas si esta vacia (api/app/main.py:37-43).
- La conexion se cierra en el evento shutdown (api/app/main.py:123-125).

### Carga de archivos

- El nombre sale de file.filename sin validar (api/app/main.py:109).
- El contenido se lee completo y se escribe sin limite (api/app/main.py:110-111).
- La respuesta devuelve fileName y storedAt con la ruta real (api/app/main.py:112).

### Contrato observado (sin docs/ENDPOINTS.md)

- Tarea: id, title, description, status, owner, priority, createdAt (api/app/main.py:56-65).
- Resumen: owner, total, byStatus, highPriorityOpen (api/app/main.py:94).
- Codigos: 201 en creacion y carga; 401 con token invalido (api/app/main.py:26); 200 en el resto.
- Contrato acordado: pendiente. docs/ENDPOINTS.md no existe y no se creo en este paso.

## Pendientes

- docs/ENDPOINTS.md no existe; el contrato anterior se derivo solo del codigo.
- No se ejecutaron pruebas ni se midio cobertura en este paso de Discovery.
- Advisories de urllib3 2.5.0 y python-multipart 0.0.21 pendientes de verificar; no se confirmaron CVEs.
- H-API-01 cambia el formato del token. Si auth emite el token, requiere coordinacion con auth; no verificado en este paso.
- backend-health depende de auth en localhost:8080/q/health. Sin cambios en auth.
