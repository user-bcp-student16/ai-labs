# Design

## Componente

Único componente afectado: `auth/`. No se modifican `api/` ni `web/`; el consumidor
[api/app/security.py](../../../api/app/security.py) se usa solo como referencia de
compatibilidad, y su contrato ya acepta JWT HS256 con los claims requeridos.

## Contexto técnico

- `POST /auth/login` está en [AuthResource.java](../../../auth/src/main/java/com/bcp/workshop/auth/AuthResource.java).
  Valida `request`, `username` y `password`, consulta credenciales y emite el token.
  Toda la lógica está anidada en un único método.
- El token actual se genera en [LegacyTokenUtil.java](../../../auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java):
  Base64 de `username|role|exp|WORKSHOP_SECRET_2026`. El secreto está en el código y no hay firma.
- `expiresIn` es el literal `3600` y `exp` usa otra constante implícita (`plusSeconds(3600)`).
- `LoginRequest` ya declara `client`, pero el login no lo valida ni lo usa.
- El `catch` general responde `500` con `error.getMessage()` y el nombre de la excepción.
- La respuesta actual incluye `debug: "authenticated-with-legacy-flow"`; no está en la spec.
- [LegacyDatabase.java](../../../auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java)
  concatena usuario y contraseña en SQL y captura las excepciones con `printStackTrace`.
  Esta persistencia queda fuera de alcance según la propuesta.
- La API verifica JWT en [api/app/security.py](../../../api/app/security.py): exige
  `iss`, `aud`, `sub`, `role`, `iat`, `exp` (entero), firma HS256 con `AUTH_TOKEN_SECRET`
  de al menos 32 bytes y rechaza `exp <= ahora`. Acepta también el Base64 legacy si
  `WORKSHOP_LEGACY_SECRET` está configurado y el flag está activo.
- [compose.yaml](../../../compose.yaml) no define `AUTH_TOKEN_SECRET` ni para `auth` ni para `api`.
- `auth/pom.xml` no incluye ninguna librería JWT; la BOM de Quarkus no administra la versión que se agregue.

## Goals

- Emitir un JWT HS256 firmado con `sub`, `client`, `role`, `iat`, `exp`, `iss` y `aud`.
- Validar `client` como no vacío antes de emitir token.
- Hacer que `expiresIn` y `exp - iat` salgan de una única constante de 3600 segundos.
- Leer el secreto desde `AUTH_TOKEN_SECRET` (sin valor por defecto, mínimo 32 bytes).
- No registrar ni devolver token, secreto ni contraseña en errores o logs del login.
- Mantener al menos 85% de cobertura en el código modificado.

## Non-goals

- Cambiar `LegacyDatabase` (SQL, esquema, datos semilla) ni rotación, refresh o revocación.
- Definir catálogo de clientes permitidos.
- Desactivar en `api/` el soporte de Base64 legacy (`WORKSHOP_LEGACY_TOKENS_ENABLED`).
- Modificar `web/` (el login ya envía `client: 'angular-workshop'`).
- Eliminar el campo `debug` de la respuesta ni cambiar `user` (no requerido por la spec; se conserva por compatibilidad).
- Rediseñar el resto de `auth/` o adoptar un framework de seguridad completo.

## Contratos protegidos

| Contrato | Fuente | Tratamiento |
|---|---|---|
| `POST /auth/login` acepta `username`, `password`, `client` en JSON | [LoginRequest.java](../../../auth/src/main/java/com/bcp/workshop/auth/LoginRequest.java) | Se conserva; `client` pasa a obligatorio. |
| `200` con `token`, `expiresIn`, `user{username,displayName,role}` | `AuthResource` | Se conserva la forma; `expiresIn` = 3600. |
| `401` con credenciales inválidas, sin token | `AuthResource` | Se conserva. |
| `400` para `request`, `username`, `password` vacíos | `AuthResource` | Se conserva el mensaje actual. |
| JWT HS256, `iss=workshop-auth-backend`, `aud=workshop-requirements-api` | [docs/ENDPOINTS.md](../../../docs/ENDPOINTS.md), `api/app/security.py` | Se respeta literalmente. |
| `exp` entero en segundos | `api/app/security.py` | Se emite `long`/entero. |
| `AUTH_TOKEN_SECRET` de al menos 32 bytes, sin default | `docs/ENDPOINTS.md`, `api/app/security.py` | Auth lo lee del entorno; el mismo valor debe configurarse en `api`. |
| Ruta `/q/health` y puerto 8080 | `application.properties`, `compose.yaml` | Sin cambios. |

## Componentes afectados

- `AuthResource`: validar `client` y delegar; devolver `500` genérico.
- `LegacyTokenUtil`: se reemplaza por un emisor JWT; se elimina si no quedan referencias.
- Nuevo emisor de tokens (p. ej. `TokenIssuer`): construye y firma el JWT.
- Nueva configuración (p. ej. `TokenConfig` con `@ConfigProperty`): lee `AUTH_TOKEN_SECRET` y valida longitud.
- `application.properties`: referencia a la variable de entorno y valor de prueba solo en perfil `%test`.
- `AuthResourceTest` y nuevas pruebas en `auth/src/test/java/com/bcp/workshop/auth/`.
- `auth/pom.xml`: nueva dependencia JWT (ver decisión 2).

No afectados: `LegacyDatabase`, `UserRecord`, `LoginRequest`, `api/`, `web/`, `compose.yaml`.

## Decisiones técnicas y alternativas

1. **Formato del token: JWT HS256 firmado.**
   Es el único formato que el verificador de `api/` acepta sin cambios.
   Se descarta mantener Base64 porque no autentica el contenido (H-API-01 y la guía de buenas prácticas).

2. **Librería de firma: `io.jsonwebtoken` (jjwt).**
   - Se prefiere a implementar HMAC a mano: evita errores de codificación y comparación en código propio.
   - jjwt rechaza claves HMAC menores de 256 bits, lo que refuerza el mínimo de 32 bytes.
   - Alternativa evaluada: `quarkus-smallrye-jwt-build` (Quarkus nativo, administrado por la BOM). Se descarta en esta propuesta porque la configuración de clave HS256 es menos explícita para el contrato del verificador.
   - Requiere justificación en el PR y revisión de Dependency Review y SCA.

3. **Orden de validación.**
   Se valida la forma de la solicitud (`request`, `username`, `password`, `client`) antes de consultar la base.
   Así, una solicitud sin `client` responde `400` sin tocar la persistencia.
   La spec no fija el orden entre `400` por `client` y `401` por credenciales inválidas; esta decisión lo fija y debe confirmarse en revisión.

4. **Tiempo de vida.**
   Una constante `TOKEN_LIFETIME_SECONDS = 3600`. Se usa para `expiresIn` y para `exp = iat + lifetime`, con `iat` y `exp` en segundos enteros.
   Esto cumple la tolerancia de 1 segundo con diferencia exacta de 0.

5. **Secreto.**
   Se lee de `AUTH_TOKEN_SECRET` mediante configuración de Quarkus sin valor por defecto.
   Si falta o es menor de 32 bytes, el login responde `500` con mensaje genérico, sin incluir el valor ni el nombre de la excepción.
   No se valida al arrancar para no romper el arranque del contenedor sin la variable; el fallo queda acotado al login.

6. **Error `500`.**
   Se reemplaza el `catch` que devuelve `getMessage()` y el nombre de la clase por un mensaje fijo.
   Motivo: el mensaje de excepción puede contener fragmentos del SQL concatenado con la contraseña, lo que violaría la spec de errores.

7. **Respuesta.**
   Se conservan `token`, `expiresIn`, `user` y `debug`. Quitar `debug` sería un cambio no pedido por la spec.

8. **Clean code en el alcance del cambio.**
   El flujo se separa en validación de solicitud, autenticación (persistencia) y emisión de token. `AuthResource` queda como capa HTTP.
   No se extrae un repositorio nuevo, porque la persistencia está fuera de alcance.

## Estrategia incremental

1. **Caracterizar** el comportamiento actual (ver siguiente sección) sin cambiar código; las pruebas deben pasar antes del cambio, salvo los casos marcados como cambio intencional.
2. **Agregar pruebas nuevas en rojo**: `client` ausente y vacío (400), JWT verificable, claims, `exp - iat == expiresIn`, secreto ausente (500 sin secreto).
3. **Introducir configuración del secreto y el emisor JWT** sin conectarlos todavía; probar el emisor de forma aislada.
4. **Conectar `AuthResource`** al nuevo flujo: validación de `client`, emisión JWT y `500` genérico.
5. **Eliminar `LegacyTokenUtil`** cuando ya no tenga referencias y sus pruebas de caracterización se hayan reemplazado.
6. **Verificar compatibilidad con `api/`**: validar un token emitido con el verificador de `api/app/security.py` usando el mismo `AUTH_TOKEN_SECRET` (prueba manual o de integración, sin modificar `api/`).
7. **Medir cobertura** del código modificado (JaCoCo) y confirmar al menos 85%.

Cada paso debe quedar en un cambio revisable separado si el PR lo permite.

## Pruebas de caracterización

Antes de modificar comportamiento crítico, en `AuthResourceTest` o pruebas nuevas:

| Caso | Comportamiento actual a fijar | Estado tras el cambio |
|---|---|---|
| Login válido `student` con `client` | `200`, `user.username=student`, `token` no vacío | Se conserva |
| Campos de respuesta | Existen `token`, `expiresIn`, `user`, `debug`; `expiresIn=3600`; `user.role=STUDENT`; `displayName` escapado | Se conserva |
| Contraseña incorrecta | `401`, sin `token` | Se conserva |
| `username` vacío o ausente | `400` con `Username is required` | Se conserva |
| `password` vacía o ausente | `400` con `Password is required` | Se conserva |
| Login sin `client` (credenciales válidas) | `200` | **Cambio intencional**: pasa a `400` según la spec |
| Token actual Base64 | Decodifica a `username|role|exp|secreto` | **Cambio intencional**: se reemplaza por JWT |
| Error interno (`500`) | Cuerpo con `message` y `exception` | **Cambio intencional**: mensaje genérico |

Pruebas nuevas (rojo primero):

- `client` ausente, `null` y solo espacios → `400` sin `token`.
- Token JWT: `sub`, `client`, `role`, `iss`, `aud`, `iat`, `exp` correctos; `exp - iat == expiresIn`.
- Firma verificable con el secreto de prueba; alterar un claim invalida la firma.
- `AUTH_TOKEN_SECRET` ausente o de 31 bytes → `500` sin el secreto en el cuerpo.
- Logs o cuerpo de error sin token ni secreto (verificar que el `500` no contiene el mensaje de la excepción).

Datos de prueba: secreto de prueba de al menos 32 bytes definido solo en perfil `%test`, sin credenciales reales.

## Riesgos y trade-offs

- **Ruptura de compatibilidad (BREAKING).** Los clientes que dependan del Base64 o de un login sin `client` dejan de funcionar. El consumidor documentado (`api/`) ya acepta JWT, pero el token legacy sigue aceptado por `api/` mientras `WORKSHOP_LEGACY_SECRET` esté configurado.
- **Configuración compartida.** `auth` y `api` deben recibir el mismo `AUTH_TOKEN_SECRET`. `compose.yaml` no lo define hoy; agregarlo está fuera del componente y requiere aprobación explícita. Sin esta variable el login responde `500`.
- **Nueva dependencia.** Aumenta superficie de SCA y requiere revisión. El trade-off es menor riesgo que una implementación propia de HMAC.
- **Persistencia fuera de alcance.** La concatenación SQL en `LegacyDatabase` y el `printStackTrace` pueden exponer fragmentos de contraseña en logs. No se corrige aquí; se recomienda un cambio separado (consultas parametrizadas en `auth/`).
- **Campo `debug` conservado.** Mantiene un detalle de implementación en la respuesta; se documenta como deuda.
- **Validación de orden.** El `400` por `client` se evalúa antes que el `401`; un cliente que envía credenciales inválidas sin `client` recibe `400`.

## Rollback

- Revertir el commit del cambio restaura `LegacyTokenUtil` y el login sin `client`.
- Los JWT ya emitidos siguen siendo válidos hasta `exp` (1 hora) para `api/` si `AUTH_TOKEN_SECRET` no cambia; tras el rollback, `api/` los seguirá validando mientras el secreto esté configurado en `api/`.
- Como `api/` no cambia, el rollback no requiere tocar el consumidor.
- Si se agregó `AUTH_TOKEN_SECRET` a `compose.yaml`, puede retirarse sin efecto sobre el flujo anterior.

## Decisiones aprobadas

- Orden de validación: `400` por `client` antes del `401` por credenciales (decisión 3). Aprobado.
- Dependencia `io.jsonwebtoken` (jjwt) 0.12.6 en `auth/pom.xml` (decisión 2). Aprobado.
- `AUTH_TOKEN_SECRET` se lee solo en `auth/` (sin default en `application.properties`; valor de prueba solo en `%test`). Aprobado.
- No aprobado: agregar `AUTH_TOKEN_SECRET` a `compose.yaml` y cambiar `api/`. Requiere aprobación explícita separada.
- Pendiente: si el campo `debug` se retira en un cambio posterior (fuera de este cambio).
