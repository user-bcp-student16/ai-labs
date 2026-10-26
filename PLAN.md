# Plan de corrección

### Aprobacion Humana

-Alex
-2026/10/26
-H-API-02, H-API-04, H-API-04, H-API-01

## Alcance seleccionado

Se planifican los hallazgos pendientes **H-API-01**, **H-API-02** y
**H-API-04** de [HALLAZGOS.md](./HALLAZGOS.md). H-API-01 se incorpora con la
aprobación registrada arriba y debe resolverse antes de H-API-02, porque la
autorización depende de una identidad autenticada y confiable. H-API-02 se
seleccionó por el riesgo alto de acceso y asignación entre propietarios;
H-API-04, por su riesgo alto y el alcance acotado al flujo de carga. No se
planifican los demás hallazgos.

`docs/ENDPOINTS.md` no existe. Se toma como contrato observado lo registrado
en HALLAZGOS.md: conservar rutas, método, formato de entrada, forma de las
respuestas exitosas y estado 201 en las creaciones. Los cambios que rechacen
solicitudes antes aceptadas son cambios intencionales de seguridad; su
comportamiento de error debe acordarse y documentarse antes de implementar.

## H-API-01 — verificación de token

- **Hallazgo:** H-API-01, “Token Base64 con secreto embebido y sin firma”, en
  estado Pendiente. Evidencia: `api/app/main.py:14,19-22`.
- **Problema:** Base64 no prueba la integridad del token y el secreto estático
  no permite autenticar de forma segura la identidad que luego usan las rutas.
- **Cambio propuesto:** validar un JWT firmado con algoritmo permitido, emisor,
  audiencia y expiración; obtener el secreto o clave de verificación de
  configuración externa y fallar de forma cerrada si falta. Devolver un error
  401 genérico para credenciales inválidas. No aceptar el token Base64 legado
  como fallback. Usar una biblioteca JWT mantenida si se aprueba tras revisar
  su versión y advisories; no implementar criptografía propia.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py` y,
  únicamente si se aprueba una dependencia, `api/requirements.txt`.
- **Pruebas de caracterización antes de tocar código:**
  1. Fijar el comportamiento actual de una solicitud con token legado válido
     y de una solicitud con token inválido o expirado.
  2. Tras el cambio, aceptar un token de prueba con firma, emisor, audiencia y
     expiración válidos; rechazar firma incorrecta, emisor o audiencia
     incorrectos, expiración vencida y tokens Base64 legados, siempre con error
     genérico.
- **Bloqueo de integración:** `docs/ENDPOINTS.md` no existe y el formato
  observado por la API es Base64, no JWT. Antes de implementar hace falta
  coordinar, sin leer ni cambiar otros componentes, el contrato del emisor:
  algoritmo, emisor, audiencia y mecanismo de provisión de claves mediante
  configuración. La dependencia y versión también requieren revisión. No se
  inventan esos valores ni se añade una clave real.

## H-API-02 — autorización ligada a la identidad

- **Hallazgo:** H-API-02, “Acceso a tareas de otro `owner`”, en estado
  Pendiente. Evidencia: `api/app/main.py:68-70,78,83`.
- **Problema:** los parámetros `owner` de lectura y el campo `owner` del body
  pueden prevalecer sobre `identity["username"]`. Además, la identidad actual
  depende de H-API-01, cuyo token no tiene firma verificable. Aplicar una
  restricción de propietario antes de tener una identidad autenticada y
  confiable no resolvería el riesgo de suplantación.
- **Cambio propuesto:** limitar las consultas y creaciones al usuario de la
  identidad verificada; no permitir que el cliente elija otro propietario.
  Conservar rutas, parámetros/campos y forma de respuesta exitosa. Para un
  `owner` distinto, proponer una respuesta genérica de autorización denegada;
  acordar el estado y formato del error antes de implementar. Reutilizar una
  única validación de propietario en las rutas pertinentes, con retornos
  anticipados. Parametrizar el filtro de propietario afectado; esto se solapa
  parcialmente con H-API-03 y no implica dar ese hallazgo por corregido.
- **Archivos a tocar:** `api/app/main.py`,
  `api/tests/test_api.py`. No crear dependencias ni alterar contratos de otros
  componentes.
- **Pruebas de caracterización antes de tocar código:**
  1. Caracterizar `GET /api/tasks` y `GET /api/summary` para la identidad
     propia: rutas, estado, forma de respuesta y datos limitados al usuario.
  2. Caracterizar `POST /api/tasks` con `owner` omitido: estado 201, forma de
     respuesta y propietario predeterminado igual a la identidad.
  3. Añadir pruebas de regresión que intenten consultar otro `owner` en ambas
     rutas de lectura y asignar otro `owner` al crear; deben demostrar el
     comportamiento inseguro actual antes del cambio y exigir rechazo después.
     Aislar la lógica de autorización de la firma de token en estas pruebas;
     la verificación integral queda bloqueada hasta resolver H-API-01.
- **Dependencia y pendiente:** implementar y validar H-API-01 antes de
  considerar eficaz la autorización. Acordar el estado y formato de error para
  un propietario distinto; no se presume esa aprobación.

## H-API-04 — carga segura de archivos

- **Hallazgo:** H-API-04, “Nombre y tamaño de archivo sin controles”, en estado
  Pendiente. Evidencia: `api/app/main.py:107-111`.
- **Problema:** el nombre proporcionado se usa para construir la ruta y el
  archivo se lee completo antes de guardarse. No hay normalización, allowlist
  de extensiones ni límite de tamaño.
- **Cambio propuesto:** normalizar o rechazar nombres con componentes de ruta,
  asegurar que el destino permanezca dentro del directorio de cargas, aceptar
  solo extensiones permitidas y limitar el tamaño mientras se lee en bloques.
  Definir la allowlist y el tamaño máximo como constantes con nombre. En una
  carga válida, conservar `POST /api/requirements`, multipart `file`, estado
  201 y las claves/tipos de la respuesta; `fileName` reflejará el nombre
  normalizado. Rechazar nombres inseguros, extensiones no permitidas y archivos
  demasiado grandes sin escribirlos.
- **Archivos a tocar:** `api/app/main.py`,
  `api/tests/test_api.py`. No se justifica agregar dependencias.
- **Pruebas de caracterización antes de tocar código:**
  1. Ampliar la prueba de carga válida para fijar estado 201, claves de
     respuesta, `fileName`, tamaño reportado y contenido persistido.
  2. Añadir pruebas para un nombre con traversal y para una extensión no
     permitida; comprobar que se rechacen y que no se escriba fuera del
     directorio de cargas.
  3. Añadir una prueba que exceda el límite acordado y compruebe rechazo sin
     persistir el archivo.
- **Decisiones pendientes:** `docs/GOOD_PRACTICES.md` requiere limitar
  extensión y tamaño, pero no define valores. Acordar allowlist, máximo y
  estados/formato de error antes de implementar; no se inventan aquí.

## Validación posterior (no ejecutada)

Después de resolver los bloqueos, obtener las aprobaciones necesarias e
implementar los cambios, ejecutar desde `ai-labs/api/`:

```text
python -m pytest --cov=app --cov-report=term-missing
```

Registrar el resultado real y la cobertura; este plan no afirma que las pruebas
se hayan ejecutado ni que exista aprobación humana.

## Ejecuciones

| componente | IDs | comando | resultado |
|---|---|---|---|
| api | H-API-01, H-API-02, H-API-04 | Sin ejecutar | Bloqueado: falta el contrato JWT del emisor y las decisiones de autorización y carga descritas arriba. |
