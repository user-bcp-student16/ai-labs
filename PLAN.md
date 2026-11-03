# Plan de correccion

Propuesta para componente api. Basada en HALLAZGOS.md. Los IDs usan el formato existente H-API-01 a H-API-05; no se renumera nada. El usuario aprobo H-API-01 a H-API-05; H-API-03 esta Resuelto y H-API-01, H-API-02, H-API-04 y H-API-05 estan Aprobados. Las decisiones tecnicas pendientes siguen indicadas por separado.

## api

### Contrato a preservar

- Rutas: GET /api/tasks, POST /api/tasks, GET /api/summary, POST /api/requirements, GET /api/backend-health (api/app/main.py:67-121).
- Formato de tarea y resumen tal como lo devuelve el codigo (api/app/main.py:56-65, api/app/main.py:94).
- Codigos observados: 201 en creacion y carga, 200 en lecturas, 401 con token invalido.
- docs/ENDPOINTS.md no existe. Mientras no exista, el comportamiento observado en el codigo es la referencia. Cualquier cambio de contrato marcado abajo requiere decision humana.

### Orden sugerido y dependencias

1. H-API-01 (identidad verificada): base para H-API-02.
2. H-API-03 (SQL parametrizado): independiente, toca la capa de datos.
3. H-API-02 (autorizacion por identidad): depende de H-API-01.
4. H-API-04 y H-API-05 (carga segura): independientes, tocan solo el flujo de archivos.

Reglas comunes de AGENTS.md (api) y docs/GOOD_PRACTICES.md aplicadas a todos los cambios: una responsabilidad por funcion, sin duplicacion, sin anidamiento profundo, constantes con nombre y modelos Pydantic en request y response. Cobertura objetivo del codigo modificado: 85% o superior.

Estructura objetivo propuesta (se confirma al implementar):

- api/app/config.py: constantes y lectura de variables de entorno.
- api/app/schemas.py: modelos Pydantic de request y response.
- api/app/security.py: verificacion del token y dependencia de identidad.
- api/app/repositories/tasks.py: SQL parametrizado.
- api/app/services/tasks.py: reglas de negocio (resumen, autorizacion).
- api/app/services/uploads.py: nombre seguro, extension y tamano.
- api/app/routes/*.py: solo HTTP.

Nota de compatibilidad: api/app/main.py sigue exponiendo `app` y `create_app` para que las pruebas actuales sigan importandolas.

---

### H-API-01: Token Base64 con secreto embebido

- Problema: el token es Base64 con un secreto fijo en el codigo (api/app/main.py:14), sin firma verificada (api/app/main.py:19-24). Quien conozca el secreto fabrica tokens. El role no se verifica. El secreto tambien aparece en las pruebas (api/tests/test_api.py:11).
- Cambio propuesto: verificar un JWT firmado con HS256 usando una libreria estandar de JWT. Validar firma, exp, iss y aud. El secreto se lee de una variable de entorno (por ejemplo WORKSHOP_JWT_SECRET) sin valor por defecto; si falta, la aplicacion no arranca. Ajustar la identidad devuelta a username y role verificados.
- Nueva dependencia: una libreria JWT. Se justifica porque implementar verificacion de firma propia no es recomendable. La version se fija tras revisar advisories, no se asume aqui.
- Archivos a tocar: api/app/security.py (nuevo), api/app/main.py (dependencia legacy_identity), api/app/config.py (nuevo), api/requirements.txt (nueva dependencia fijada), api/tests/test_api.py (helper de token).
- Prueba de caracterizacion antes de tocar: con el formato actual, un token valido devuelve 200 en GET /api/tasks; un token con secreto incorrecto, con exp vencido, con menos de cuatro partes o no Base64 devuelve 401. Estos casos deben seguir en verde con el formato actual antes del cambio.
- Pruebas posteriores: token firmado valido 200; firma incorrecta 401; exp vencido 401; iss o aud incorrectos 401; falta de la variable de entorno impide el arranque.
- Decision pendiente: si auth emite el token en el formato actual, cambiar el formato exige coordinacion con auth. No verificado en este paso. Hasta resolverla, no se cambia el emisor.

### H-API-02: Autorizacion: el cliente elige el owner

- Problema: el parametro owner de GET /api/tasks y GET /api/summary (api/app/main.py:68-69, api/app/main.py:91-92) y el campo owner del body de POST /api/tasks (api/app/main.py:83) no se comparan con la identidad del token. Cualquier usuario autenticado lee o crea datos de otro owner.
- Cambio propuesto: el owner sale siempre de identity["username"]. Si llega un owner distinto, se rechaza con 403 o se ignora, segun la decision pendiente. El campo owner del body se ignora. Toda consulta usa la identidad verificada.
- Decision pendiente: el comportamiento para un rol de entrenador o administrador. El codigo no define valores de role mas alla de los que aparecen en las pruebas; hace falta definir la lista de roles y si alguno puede consultar otros owners. Tambien si el 403 es aceptable como cambio de contrato.
- Archivos a tocar: api/app/routes/tasks.py, api/app/services/tasks.py, api/app/schemas.py, api/app/main.py.
- Prueba de caracterizacion antes de tocar: un token de student sin owner en GET /api/tasks devuelve sus dos tareas sembradas (api/app/main.py:40-41). Un POST sin owner crea la tarea con owner student. Estos casos son el contrato a preservar.
- Caracterizacion marcada para cambio: GET /api/tasks?owner=trainer con token de student devuelve las tareas de trainer. Se escribe como prueba que documenta el comportamiento actual y se cambia tras aprobacion.
- Pruebas posteriores: owner ajeno rechazado o ignorado segun decision; POST con owner ajeno crea la tarea con el username del token.

### H-API-03: SQL concatenado en listados, inserts y resumen

- Problema: los valores del cliente se concatenan en el SQL en GET /api/tasks (api/app/main.py:70), POST /api/tasks (api/app/main.py:84) y GET /api/summary (api/app/main.py:93). El SELECT por id con lastrowid (api/app/main.py:87) concatena un entero; el riesgo es bajo, pero se parametriza igual.
- Cambio propuesto: consultas con parametros de sqlite3 (?). Mover el SQL a api/app/repositories/tasks.py. La funcion de ruta solo llama al repositorio.
- Archivos a tocar: api/app/repositories/tasks.py (nuevo), api/app/services/tasks.py, api/app/main.py.
- Prueba de caracterizacion antes de tocar: crear una tarea con titulo normal devuelve 201 y campos esperados; listar devuelve la tarea creada; resumen cuenta total y highPriorityOpen. Escribir tambien una prueba con comillas simples en el titulo que documente el comportamiento actual (error de SQL o fallo de la respuesta) y que se reemplaza tras el cambio por una prueba que espera 201 y el texto guardado tal cual.
- Pruebas posteriores: titulo con comillas se guarda literal; filtro owner con comillas no altera la consulta; resultados iguales a la caracterizacion en los casos normales.

### H-API-04: Nombre de archivo subido usado tal cual (path traversal)

- Problema: Path(selected_uploads) / str(file.filename) (api/app/main.py:109) usa el nombre sin normalizar. Un nombre con componentes de ruta escribe fuera de uploads. La respuesta expone storedAt con la ruta real (api/app/main.py:112).
- Cambio propuesto: no usar el nombre del cliente como ruta. Generar un nombre de archivo en el servidor (por ejemplo un identificador unico) y conservar el nombre original solo como dato de respuesta, reducido a su parte final y con caracteres permitidos. Verificar que la ruta final quede dentro del directorio de carga.
- Decision pendiente: si storedAt debe seguir mostrando la ruta real. Mostrarla es una fuga de informacion; ocultarla cambia el contrato observado.
- Archivos a tocar: api/app/services/uploads.py (nuevo), api/app/routes/requirements.py (nuevo), api/app/main.py.
- Prueba de caracterizacion antes de tocar: cargar requirements.txt devuelve 201 y el archivo existe en uploads/requirements.txt (api/tests/test_api.py, prueba test_uploads_requirement). Escribir una prueba marcada xfail que documenta que un nombre con ../ hoy escribe fuera del directorio.
- Pruebas posteriores: nombre con ../ queda dentro del directorio de uploads; nombre de la respuesta sin componentes de ruta; la prueba xfail pasa a prueba normal.

### H-API-05: Carga sin limite de extension ni de tamano

- Problema: cualquier extension se acepta (api/app/main.py:108) y el contenido se lee completo en memoria antes de escribirlo (api/app/main.py:110-111).
- Cambio propuesto: lista blanca de extensiones y tamano maximo como constantes en api/app/config.py. Leer en fragmentos y cortar al superar el tamano. Respuesta 415 para extension no permitida y 413 para tamano excedido, con mensajes genericos.
- Decision pendiente: lista de extensiones permitidas (la prueba actual usa .txt) y el tamano maximo. Ambos son decisiones de producto.
- Archivos a tocar: api/app/services/uploads.py, api/app/config.py, api/app/routes/requirements.py.
- Prueba de caracterizacion antes de tocar: .txt pequeno devuelve 201 (test_uploads_requirement). Escribir una prueba que documenta que hoy un archivo de otra extension devuelve 201, marcada para cambio tras aprobacion.
- Pruebas posteriores: extension no permitida 415; archivo sobre el limite 413 sin escribir en disco; archivo dentro del limite 201.

---

## Decisiones humanas pendientes

- H-API-01: coordinacion con auth si cambia el formato del token. Pendiente.
- H-API-02: lista de roles y comportamiento para consultar otros owners; 403 frente a ignorar. Pendiente.
- H-API-04: exponer o no storedAt. Pendiente.
- H-API-05: extensiones permitidas y tamano maximo. Pendiente.
- Dependencia nueva para JWT (H-API-01): aprobacion y version fijada tras revisar advisories. Pendiente.

## Pendientes de ejecucion

- H-API-01, H-API-02, H-API-04 y H-API-05 estan aprobados para implementacion. Resolver sus decisiones tecnicas pendientes antes de los cambios que dependen de ellas.
- H-API-03 esta Resuelto; su caracterizacion y suite posterior se ejecutaron con cwd api/ usando python tools/lab.py test api.

## Registro de ejecucion

- Estado inicial de implementacion: bloqueada mientras no habia aprobacion humana registrada; no se edito codigo en esa comprobacion inicial.
- H-API-01, H-API-02, H-API-04 y H-API-05: aprobados por el usuario; las decisiones tecnicas listadas en "Decisiones humanas pendientes" siguen sin resolver.
- Ejecucion api H-API-03: caracterizacion escrita primero (line base 6 pruebas en verde, cobertura 91%). Cambio: consultas parametrizadas en api/app/repositories/tasks.py; main.py solo llama al repositorio. Pruebas de correccion: owner con comillas devuelve lista vacia; titulo con comillas se guarda literal (201). Resultado tras el cambio: 6 pruebas en verde, cobertura 92%.
- Desviacion: no se creo api/app/services/tasks.py; la regla de negocio del resumen sigue en main.py. Pendiente para el paso de capas.
- Nueva comprobacion: HALLAZGOS.md marca H-API-01 a H-API-05 como "Aprobado", pero este documento no registra aprobacion y las cinco decisiones siguen pendientes. Sin cambios en codigo ni pruebas.
- Aprobacion humana registrada: el usuario aprueba H-API-01 a H-API-05 (api). Las decisiones pendientes de la seccion anterior siguen abiertas; cada una se resuelve antes de su cambio.
