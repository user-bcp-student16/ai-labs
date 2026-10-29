# Tasks

Componente único: `auth/`. Ejecutar pruebas desde la raíz con `python tools/lab.py test auth`.
Git, MCP y OpenSpec se ejecutan desde la raíz. No se modifican `api/`, `web/`, `compose.yaml` ni `docs/`.
Cada tarea debe quedar verificada antes de iniciar la siguiente.

## 1. Preparación y aprobación

- [x] 1.1 Confirmar que la rama de trabajo es local y que no hay cambios sin relación en `auth/`.
  - Verificación: `git status` desde la raíz muestra solo los archivos del cambio.
- [x] 1.2 Obtener aprobación humana de las preguntas abiertas de `design.md`: orden de validación (400 por `client` antes del 401), dependencia `io.jsonwebtoken` y configuración de `AUTH_TOKEN_SECRET` para `auth` y `api`.
  - Verificación: decisiones registradas en el PR o en `design.md`. Sin aprobación, detener el cambio funcional.
- [x] 1.3 Ejecutar la suite actual de `auth/` y registrar la línea base.
  - Verificación: `python tools/lab.py test auth` pasa (o registra fallos preexistentes) y se anota la cobertura actual.

## 2. Pruebas de caracterización (antes de cualquier cambio funcional)

- [x] 2.1 Caracterizar login válido: `200`, `user.username=student`, `token` no vacío, `user.role=STUDENT`.
  - Verificación: prueba en `AuthResourceTest` pasa sobre el código actual.
- [x] 2.2 Caracterizar la forma de la respuesta: existen `token`, `expiresIn`, `user` y `debug`; `expiresIn=3600`; `displayName` escapado.
  - Verificación: prueba pasa sobre el código actual.
- [x] 2.3 Caracterizar contraseña incorrecta: `401` sin campo `token`.
  - Verificación: prueba pasa sobre el código actual.
- [x] 2.4 Caracterizar validaciones existentes: `username` vacío o ausente (`400`, `Username is required`) y `password` vacía o ausente (`400`, `Password is required`).
  - Verificación: pruebas pasan sobre el código actual.
- [x] 2.5 Caracterizar el comportamiento que cambiará: login sin `client` responde `200`, y el token actual es Base64 con `username|role|exp|secreto`.
  - Verificación: pruebas marcadas en el código como caracterización del comportamiento anterior y documentadas como cambio intencional.
- [x] 2.6 Revisar que la caracterización no fija detalles fuera de la spec, salvo `debug` y los mensajes existentes, que se conservan.
  - Verificación: `python tools/lab.py test auth` pasa completo antes de la tarea 3.

## 3. Pruebas nuevas en rojo

- [x] 3.1 Agregar prueba: `client` ausente, `null` o solo espacios responde `400` y no incluye `token`.
  - Verificación: la prueba falla con el código actual (esperado en rojo).
- [x] 3.2 Agregar prueba: el token emitido tiene `sub`, `client`, `role`, `iss=workshop-auth-backend`, `aud=workshop-requirements-api`, `iat` y `exp` enteros.
  - Verificación: la prueba falla con el código actual.
- [x] 3.3 Agregar prueba: `exp - iat` es igual a `expiresIn` (3600).
  - Verificación: la prueba falla con el código actual.
- [x] 3.4 Agregar prueba: la firma se verifica con el secreto de prueba y falla si se altera un claim.
  - Verificación: la prueba falla con el código actual.
- [x] 3.5 Agregar prueba: sin `AUTH_TOKEN_SECRET` o con menos de 32 bytes, el login responde `500` con mensaje genérico y el cuerpo no contiene el secreto.
  - Verificación: la prueba falla con el código actual.
- [x] 3.6 Agregar prueba: el cuerpo de error no contiene el token, el secreto ni el mensaje interno de la excepción.
  - Verificación: la prueba falla con el código actual.

## 4. Configuración del secreto

- [ ] 4.1 Agregar la configuración de `AUTH_TOKEN_SECRET` en `application.properties` sin valor por defecto.
  - Verificación: arranque de la aplicación sin la variable no falla; el valor no aparece en el repositorio.
- [ ] 4.2 Agregar un secreto de prueba de al menos 32 bytes solo en el perfil `%test`.
  - Verificación: `python tools/lab.py test auth` usa el valor de prueba y no existe secreto real en el código.
- [ ] 4.3 Crear la clase de configuración que valida la longitud mínima de 32 bytes.
  - Verificación: prueba unitaria con 31 bytes falla con error controlado y con 32 bytes es aceptado.

## 5. Emisor JWT (aislado)

- [ ] 5.1 Aprobar y agregar la dependencia `io.jsonwebtoken` en `auth/pom.xml` con versión explícita.
  - Verificación: `python tools/lab.py test auth` compila; revisión de Dependency Review y SCA sin alertas no justificadas.
- [ ] 5.2 Crear el emisor de tokens que firma HS256 con `sub`, `client`, `role`, `iss`, `aud`, `iat` y `exp` (entero).
  - Verificación: prueba unitaria del emisor verifica claims y firma con el mismo secreto.
- [ ] 5.3 Usar la constante `TOKEN_LIFETIME_SECONDS = 3600` para `exp` y para `expiresIn`.
  - Verificación: prueba unitaria confirma `exp - iat == 3600`.

## 6. Conexión en el login

- [ ] 6.1 Validar `client` no vacío en `AuthResource` antes de consultar la base de datos.
  - Verificación: pruebas 3.1 pasan; las pruebas de caracterización 2.1 a 2.4 siguen pasando.
- [ ] 6.2 Reemplazar la emisión Base64 por el emisor JWT en el login.
  - Verificación: pruebas 3.2 y 3.3 pasan; la respuesta conserva `token`, `expiresIn`, `user` y `debug`.
- [ ] 6.3 Reemplazar el `catch` general por un `500` con mensaje fijo, sin `getMessage()` ni nombre de excepción.
  - Verificación: pruebas 3.5 y 3.6 pasan.
- [ ] 6.4 Separar la validación de solicitud, la autenticación y la emisión en métodos con una sola responsabilidad, sin anidamiento profundo.
  - Verificación: revisión de código; `python tools/lab.py test auth` pasa sin cambios de comportamiento.

## 7. Limpieza

- [ ] 7.1 Eliminar `LegacyTokenUtil` cuando no tenga referencias.
  - Verificación: búsqueda en `auth/` no devuelve referencias; compilación y pruebas pasan.
- [ ] 7.2 Reemplazar las pruebas de caracterización de Base64 marcadas como cambio intencional por pruebas del JWT.
  - Verificación: no quedan pruebas que exijan el formato Base64.
- [ ] 7.3 Confirmar que `LegacyDatabase`, `UserRecord` y `LoginRequest` no cambiaron.
  - Verificación: `git diff` desde la raíz no muestra cambios en esos archivos.

## 8. Verificación de compatibilidad y cobertura

- [ ] 8.1 Validar un token emitido por `auth` con el verificador de `api/app/security.py`, usando el mismo `AUTH_TOKEN_SECRET`, sin modificar `api/`.
  - Verificación: el verificador acepta el token; con otro secreto lo rechaza. Registrar el resultado como evidencia manual o de integración.
- [ ] 8.2 Medir la cobertura del código modificado con JaCoCo.
  - Verificación: cobertura igual o superior a 85% en las clases modificadas.
- [ ] 8.3 Ejecutar la suite completa de `auth/`.
  - Verificación: `python tools/lab.py test auth` pasa sin fallos.
- [ ] 8.4 Revisar que no hay secretos reales, token de ejemplo válido ni datos de producción en el diff.
  - Verificación: revisión de `git diff` desde la raíz.

## 9. Entrega

- [ ] 9.1 Registrar evidencias en la raíz con el identificador `H-AUTH-NN` que corresponda, conservando las secciones existentes.
  - Verificación: `HALLAZGOS.md` o documento de evidencias actualizado solo en la sección de `auth`.
- [ ] 9.2 Preparar el PR con referencia al Issue y lista de cambios incrementales.
  - Verificación: PR revisado por una persona; no hacer push ni crear PR durante el Día 1 sin aprobación.

## Fuera de alcance

- Consultas parametrizadas en `LegacyDatabase` y revisión de logs de `printStackTrace` (cambio posterior).
- Eliminar el campo `debug` de la respuesta.
- Desactivar el soporte Base64 legacy en `api/`.
- Agregar `AUTH_TOKEN_SECRET` a `compose.yaml` sin aprobación explícita.
- Cambios en `web/` o `docs/`.
