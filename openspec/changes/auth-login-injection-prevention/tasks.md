# Tasks

Alcance: Issue #22 (H-AUTH-01), componente `auth/`, `POST /auth/login`. Comandos Git y OpenSpec desde la raiz de `ai-labs`; pruebas con `python tools/lab.py test auth`. Rama de trabajo: `feature/h-auth-01`.

## 1. Linea base

- [x] 1.1 Confirmar con `git branch --show-current` que la rama es `feature/h-auth-01` y que el arbol de trabajo no tiene cambios ajenos al cambio.
- [x] 1.2 Ejecutar `python tools/lab.py test auth` sin modificaciones y registrar el resultado como linea base (solo existe `logsInWithWorkshopUser`).

## 2. Pruebas de caracterizacion (sin tocar codigo de produccion)

Todas en `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`, con usuario de prueba `student` / `Workshop123!`.

- [x] 2.1 Comportamiento protegido: login valido conserva `200`, `user.username`, `token`, `expiresIn`, `user.role` y `user.displayName`.
- [x] 2.2 Comportamiento protegido: contraseña incorrecta para un usuario existente responde `401` sin `token`.
- [x] 2.3 Comportamiento protegido: usuario inexistente responde `401` sin `token`.
- [x] 2.4 Comportamiento protegido: usuario vacio, contraseña vacia y cuerpo nulo responden `400` con los mensajes actuales.
- [x] 2.5 Defecto: inyeccion en usuario (`' OR '1'='1' --` con contraseña cualquiera) espera `401` sin `token`.
- [x] 2.6 Defecto: inyeccion con comentario tras usuario real (`student'--`) espera `401` sin `token`.
- [x] 2.7 Defecto: inyeccion en contraseña (`' OR '1'='1` con usuario `student`) espera `401` sin `token`.
- [x] 2.8 Ejecutar `python tools/lab.py test auth` y confirmar que 2.1-2.4 pasan y 2.5-2.7 fallan; guardar la salida como evidencia del defecto en la raiz (ID `H-AUTH-01`), conservando las secciones existentes.
- [x] 2.9 Commit de las pruebas de caracterizacion, separado de la correccion si es posible.

## 3. Correccion incremental

- [x] 3.1 En `LegacyDatabase.findByCredentials`, reemplazar la concatenacion SQL por una consulta parametrizada (`WHERE username = ? AND password = ?` con `PreparedStatement` y `setString`), manteniendo columnas, mapeo a `UserRecord` y retorno `null` ante ausencia de fila o excepcion.
- [x] 3.2 Confirmar que `AuthResource`, `LegacyTokenUtil`, `LoginRequest`, `UserRecord`, `pom.xml` y otros componentes no tienen cambios (`git diff --stat`).
- [x] 3.3 Ejecutar `python tools/lab.py test auth` y confirmar que todas las pruebas de la seccion 2 pasan.
- [x] 3.4 Commit de la correccion.

## 4. Validacion

- [x] 4.1 Verificar el reporte JaCoCo del componente: cobertura >= 85% del codigo modificado (`LegacyDatabase.findByCredentials`).
- [x] 4.2 Si hace falta cobertura, agregar una prueba de `LegacyDatabase` inyectado: credenciales validas devuelven el `UserRecord` correcto y una entrada de inyeccion devuelve `null`.
- [x] 4.3 Verificar que no se silencio ni excluyo CodeQL, Dependency Review ni JaCoCo, y que no se agregaron secretos ni dependencias.
- [x] 4.4 Validar los escenarios del spec `auth-login` contra las pruebas: credenciales validas, inyeccion en usuario e inyeccion en contraseña.
- [x] 4.5 Ejecutar `openspec validate auth-login-injection-prevention` desde la raiz, si la CLI esta disponible.

## 5. Evidencia y cierre

- [x] 5.1 Registrar en el documento general de evidencias (ID `H-AUTH-01`) los resultados de 2.8, 3.3 y 4.1, sin alterar las secciones de `api` y `web`.
- [x] 5.2 Dejar el cambio listo para revision humana; la integracion y el checkpoint locales del Dia 1 ocurren solo tras aprobacion y pruebas reales, sin push ni PR.

## Fuera de alcance (no tratar en este cambio)

- Refactor de `AuthResource.login` en capas o eliminacion de anidamiento.
- Mensaje `401` que refleja el usuario, campo `debug`, manejo de `500` y `printStackTrace`.
- Hash de contraseñas, secreto o formato del token, y politicas de credenciales.
- Cambios en `api/`, `web/` o endpoints distintos de `POST /auth/login`.
