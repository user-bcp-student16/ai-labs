# Proposal

## Why

El Issue #22 (H-AUTH-01) reporta que entradas de credenciales especialmente construidas pueden alterar la validacion del login y permitir acceso sin credenciales validas. Corregir ese comportamiento evita accesos no autorizados y debe preservar el contrato existente de `POST /auth/login`.

## What Changes

- Se especifica el rechazo de intentos de autenticacion que usan entradas diseñadas para eludir la validacion de credenciales.
- Se explicita que el inicio de sesion exitoso conserva la respuesta observable que requiere el Issue.

## Scope

### In Scope

- El comportamiento de autenticacion de `POST /auth/login` en `auth/`.
- El rechazo con `401 Unauthorized` y sin token ante entradas de prueba de inyeccion en usuario o contraseña.
- La preservacion de la respuesta exitosa con `user.username` y `token`.

### Out of Scope

- Cambios en `api/`, `web/` o endpoints distintos de `POST /auth/login`.
- Cambios al formato del token, las politicas de credenciales o los flujos de registro y recuperacion.
- El diseño de implementacion y los cambios de codigo o pruebas, que no forman parte de esta etapa.

## Preserved Behavior

- `docs/ENDPOINTS.md` sirve como baseline del Dia 1, pero actualmente documenta solo `api/` y no define `POST /auth/login`. Por tanto, esta propuesta no atribuye a esa baseline un contrato de autenticacion que no contiene.
- El Issue #22 exige expresamente preservar `POST /auth/login`: credenciales validas siguen produciendo `200 OK` con `user.username` y `token`; los intentos de inyeccion especificados por el Issue producen `401 Unauthorized` y no devuelven token. No se propone cambiar el contrato del endpoint.

## Capabilities

### New Capabilities

- `auth-login`: comportamiento observable del inicio de sesion, incluidos el acceso valido y el rechazo de intentos de eludir la validacion de credenciales.

### Modified Capabilities

- Ninguna. No existen specs previas en el repositorio.

## Impact

- Componente `auth/`: comportamiento de `POST /auth/login` y su prueba de caracterizacion `AuthResourceTest`, segun los criterios del Issue #22.
- Sin impacto en APIs, dependencias o contratos de otros componentes.