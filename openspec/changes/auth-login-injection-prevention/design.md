# Design

## Context

Issue #22 (H-AUTH-01) reporta que `POST /auth/login` puede eludirse con entradas de inyeccion. El proposal y el spec `auth-login` (en esta misma carpeta de cambio) fijan el comportamiento esperado: credenciales validas siguen dando `200` con `user.username` y `token`; entradas de inyeccion en usuario o contraseña dan `401` sin token.

Estado actual del componente `auth/` (Quarkus, Java, SQLite):

- `AuthResource.login` valida nulos/vacios (`400`), llama a `LegacyDatabase.findByCredentials` y, si el resultado es `null`, responde `401`; si no, arma la respuesta con `LegacyTokenUtil.create`.
- `LegacyDatabase.findByCredentials` construye el SQL concatenando `username` y `password` dentro de un `Statement`:
  `... WHERE username='" + username + "' AND password='" + password + "'`.
  Esta concatenacion es la causa raiz: una entrada como `' OR '1'='1' --` altera la sentencia y devuelve una fila sin credenciales validas.
- Ante una excepcion SQL el metodo registra el error y devuelve `null`, es decir, falla cerrado con `401`.
- `AuthResourceTest` solo cubre el caso de credenciales validas. No existe prueba que cubra rechazo ni entradas de inyeccion.
- Existen artefactos de `target/` (por ejemplo reportes de `AuthTokenServiceTest`) sin fuente correspondiente en `src/test`; no se consideran base de pruebas.

## Goals / Non-Goals

### Goals

- Garantizar que `username` y `password` se traten siempre como datos y nunca alteren la estructura de la consulta de autenticacion.
- Cumplir los escenarios del spec `auth-login`: `200` con `user.username` y `token` para credenciales validas; `401` sin token para inyeccion en usuario o contraseña.
- Dejar pruebas de caracterizacion y de regresion en `AuthResourceTest` que demuestren el cambio de comportamiento.
- Cobertura de 85% o superior en el codigo modificado, sin silenciar CodeQL, Dependency Review ni JaCoCo.

### Non-Goals

- Cambiar el formato o la firma del token (`LegacyTokenUtil`), su secreto o su expiracion.
- Almacenar contraseñas con hash, cambiar politicas de credenciales o flujos de registro/recuperacion.
- Refactorizar `AuthResource.login` en capas o eliminar el anidamiento (las reglas de clean code aplican al codigo que se modifique, no justifican ampliar el alcance de este cambio).
- Cambiar el mensaje de `401`, el campo `debug`, el manejo del `500` o la semilla de usuarios.
- Tocar `api/`, `web/` o endpoints distintos de `POST /auth/login`.

## Protected Contracts

Contratos que no deben cambiar (observables por `web/` y por el Issue):

| Contrato | Comportamiento protegido |
| --- | --- |
| Ruta y metodo | `POST /auth/login`, JSON de entrada con `username`, `password` y `client` opcional |
| Exito | `200`; cuerpo con `token`, `expiresIn` (3600), `user.username`, `user.displayName` (escapado HTML), `user.role` y `debug` |
| Credenciales incorrectas | `401` con `message` de la forma `Invalid user <username> or password`; sin `token` |
| Validacion de entrada | `400` para request nulo, usuario vacio o contraseña vacia, con sus mensajes actuales |
| Token | Estructura y expiracion generadas por `LegacyTokenUtil.create` |
| Falla interna | Excepcion SQL en la consulta sigue resultando en `401` (falla cerrada), no en `200` |

Nota: `docs/ENDPOINTS.md` no define `POST /auth/login`, por lo que el baseline efectivo es el comportamiento actual del codigo mas el Issue #22. El mensaje `401` refleja el usuario enviado; es un punto a revisar aparte y no se modifica aqui.

## Affected Components

- `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`: unico cambio funcional previsto (`findByCredentials`).
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`: nuevas pruebas.
- Sin cambios en `AuthResource`, `LegacyTokenUtil`, `LoginRequest`, `UserRecord`, `pom.xml` ni dependencias.
- Fuera del componente: ninguno. `api/` y `web/` no se leen ni modifican.

## Decisions

### D1. Consulta parametrizada con `PreparedStatement`

`findByCredentials` usara una sentencia con marcadores (`WHERE username = ? AND password = ?`) y `setString` para ambos valores, manteniendo las mismas columnas, la misma tabla y el mismo mapeo a `UserRecord`.

Razon: elimina la causa raiz, no depende de listar caracteres peligrosos, y es el control que esperan CodeQL y las guias del repositorio. Una entrada de inyeccion pasa a ser un valor que no coincide con ningun usuario, por lo que el resultado es `null` y `AuthResource` ya responde `401` sin token.

Alternativas consideradas:

- **Escapar comillas manualmente o usar una lista negra de patrones (`'`, `--`, `OR`)**: fragil, evadible y puede rechazar contraseñas legitimas. Descartada.
- **Validar con una expresion regular de caracteres permitidos en `AuthResource`**: rechazaria contraseñas validas como `Workshop123!` si la lista es estricta, cambia el contrato (`400` vs `401`) y no corrige la consulta. Descartada como control principal.
- **Migrar a JPA/Panache o un ORM**: amplia el alcance, añade dependencias y no es necesario. Descartada.
- **Consultar solo por `username` y comparar la contraseña en Java**: es un cambio valido pero modifica la semantica de la consulta y roza el diseño de credenciales (hashing), que esta fuera de alcance. Queda como mejora posterior.

### D2. `AuthResource` sin cambios

El flujo `null -> 401` ya satisface el spec una vez corregida la consulta. No se separa en capas en este cambio para mantener la revision pequeña y el riesgo bajo.

### D3. Manejo de errores sin cambios de contrato

La captura de `Exception` en `findByCredentials` seguira devolviendo `null`. Se conserva la falla cerrada. No se cambia el registro con `printStackTrace` en este cambio.

### D4. Pruebas primero

Las pruebas se escriben y ejecutan antes de modificar `LegacyDatabase`, para documentar el estado actual y mostrar que las pruebas de inyeccion fallan antes y pasan despues.

## Incremental Strategy

1. **Caracterizacion (sin tocar codigo de produccion)**: ampliar `AuthResourceTest` con los casos de la siguiente seccion y ejecutar `python tools/lab.py test auth`. Registrar que las pruebas de comportamiento protegido pasan y que las de inyeccion fallan (evidencia del defecto).
2. **Correccion**: cambiar solo `LegacyDatabase.findByCredentials` a consulta parametrizada.
3. **Verificacion**: ejecutar de nuevo las pruebas del componente y comprobar cobertura JaCoCo >= 85% del codigo modificado.
4. **Evidencia**: registrar resultados con el ID `H-AUTH-01` en los documentos generales, conservando las secciones de otros componentes.
5. **Revision**: cambio revisable por separado (pruebas y correccion en commits distintos si es posible); la integracion sigue el cierre local del Dia 1 y la aprobacion humana.

## Characterization Tests

Todas se ubican en `AuthResourceTest` (`@QuarkusTest`, RestAssured), antes de modificar `LegacyDatabase`. Datos de prueba: usuarios sembrados `student` / `Workshop123!`.

Comportamiento a proteger (deben pasar antes y despues):

- Login valido: `200`, `user.username == "student"`, `token` no nulo (ya existe).
- Respuesta valida conserva `expiresIn`, `user.role` y `user.displayName`.
- Contraseña incorrecta para usuario existente: `401` y sin `token`.
- Usuario inexistente: `401` y sin `token`.
- Usuario vacio, contraseña vacia y cuerpo nulo: `400` con el mensaje actual.

Defecto a demostrar (fallan antes, pasan despues):

- Inyeccion en usuario, por ejemplo `' OR '1'='1' --` con una contraseña cualquiera: `401` y sin `token`.
- Inyeccion en usuario con comentario tras un usuario real, por ejemplo `student'--`: `401` y sin `token`.
- Inyeccion en contraseña, por ejemplo `' OR '1'='1` con usuario `student`: `401` y sin `token`.

Complementarias para cobertura (opcional, a nivel `LegacyDatabase` inyectado): `findByCredentials` devuelve el `UserRecord` correcto para credenciales validas y `null` para una entrada de inyeccion. Una prueba de falla de conexion solo se añade si es sencilla de aislar sin cambiar la configuracion; en caso contrario se omite y se justifica en la evidencia.

Las pruebas deben usar solo valores de prueba aislados y no agregar secretos reales.

## Risks / Trade-offs

- **Dependencia de la base SQLite local y su semilla**: las pruebas usan `./data/workshop.db`. Mitigacion: la semilla es `INSERT OR IGNORE` e idempotente; no se asumen otros datos.
- **Mensaje `401` que refleja la entrada del usuario**: se conserva por contrato, aunque refleja datos no confiables. Riesgo aceptado y documentado como seguimiento; no forma parte de este Issue.
- **Contraseñas en texto plano y secreto de token en codigo**: persisten y quedan fuera de alcance; la parametrizacion no los mitiga.
- **Falsa sensacion de cierre**: otras entradas de `auth/` no estan evaluadas en este cambio. Se limita la afirmacion a `POST /auth/login`.
- **Pruebas que fallan antes del cambio**: es intencional en el paso 1; evitar integrarlas sin la correccion.
- **Diferencias de comparacion**: `PreparedStatement` conserva la semantica de igualdad actual (sensible a mayusculas/minusculas segun SQLite); no se espera cambio de comportamiento para entradas legitimas.

## Rollback

- El cambio es local a `LegacyDatabase.findByCredentials` y a pruebas; no modifica esquema, datos, configuracion ni dependencias.
- Rollback: revertir el commit de la correccion (`git revert`), manteniendo las pruebas de caracterizacion de comportamiento protegido.
- Advertencia: revertir restaura la vulnerabilidad. Solo debe hacerse si el login valido falla en un entorno, y debe acompañarse de una mitigacion alternativa o un arreglo inmediato.

## Open Questions

- Ninguna que bloquee el diseño. Se confirmara en la revision humana que el mensaje `401` reflejado queda como seguimiento separado.
