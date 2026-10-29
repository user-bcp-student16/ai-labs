# Proposal

## Why

GitHub Issue [#23](https://github.com/user-bcp-student16/ai-labs/issues/23) contiene HU-01, que pide claims mínimos, expiración verificable y protección del secreto y los logs; se toma su cuerpo como fuente, aunque el título del Issue no coincide. El flujo actual de `auth/` emite un token Base64 con un secreto fijo, y la API documenta JWT firmado como contrato preferido, por lo que un token de login interoperable es necesario para una autenticación coherente entre componentes.

## What Changes

- El login de `auth/` emitirá un token firmado con los claims `sub`, `client`, `iat` y `exp`.
- El token también conservará `iss`, `aud` y `role`, requeridos por el contrato JWT consumidor documentado en `docs/ENDPOINTS.md`. No se reemplazará `aud` por `client`.
- `client` se tomará de la solicitud y se rechazará si falta o está vacío. Como el Issue no define un catálogo de clientes válidos, se asume que cualquier valor no vacío es admisible.
- La respuesta exitosa conservará los campos `token`, `expiresIn` y `user`; el valor predeterminado observado de `expiresIn` es 3600 segundos. La diferencia entre `expiresIn` y `exp - iat` tendrá una tolerancia máxima de un segundo para timestamps Unix enteros.
- El token firmado expirará según `exp`, y los errores de autenticación no expondrán token, secreto ni contraseña. Los logs no incluirán token ni secreto.
- **BREAKING**: el token deja de ser el formato Base64 legacy observado en `auth/` y pasa a ser un JWT firmado. `docs/ENDPOINTS.md` documenta ya la aceptación de JWT HS256 con `iss=workshop-auth-backend`, `aud=workshop-requirements-api`, los claims requeridos y secreto `AUTH_TOKEN_SECRET` de al menos 32 bytes, sin valor por defecto.

## Capabilities

### New Capabilities

- `auth-login`: contrato observable del endpoint de login, incluyendo el requisito de `client` y la conservación de la forma de respuesta.
- `auth-token-issuance`: emisión de tokens firmados interoperables con el contrato JWT documentado para la API, expiración y tratamiento del secreto.

### Modified Capabilities

Ninguna. `openspec/specs/` no contiene capacidades existentes.

## Alcance y fuera de alcance

**Dentro del alcance**

- `POST /auth/login` y la emisión de tokens en el componente `auth/`.
- Claims, expiración, secreto y redacción de información sensible definidos arriba.
- Escenarios verificables para login válido, credenciales inválidas, cliente ausente o vacío y token expirado.

**Fuera del alcance**

- Cambios de código o pruebas en `api/` o `web/`.
- Cambios en persistencia de usuarios, refresh tokens, revocación o rotación de secretos.
- Elección de librería o diseño interno de la implementación.
- Definir una lista de clientes permitidos, ya que el Issue no la proporciona.
- Crear `design.md` o `tasks.md` en esta etapa.

## Comportamiento que debe preservarse

`docs/ENDPOINTS.md` no documenta `POST /auth/login`; por tanto, no se atribuyen al documento códigos de error ni detalles de entrada del login. El Issue describe una respuesta con `token`, `expiresIn` y `user`, y la implementación actual responde `200` al login válido y `401` ante credenciales inválidas; esos comportamientos observados se conservan. Se conserva también la compatibilidad con el contrato consumidor documentado: JWT firmado HS256, `iss=workshop-auth-backend`, `aud=workshop-requirements-api`, claims `sub`, `role`, `iat`, `exp`, y rechazo de tokens vencidos. `client` se añade como claim sin alterar esos valores.

La respuesta actual incluye otros detalles no definidos por `docs/ENDPOINTS.md` ni por los criterios del Issue; esta propuesta no los eleva a requisitos nuevos.

## Impact

- Código y pruebas del componente `auth/`.
- Contrato de token compartido con el consumidor descrito en `docs/ENDPOINTS.md`; no se propone cambiar el código del consumidor.
- Configuración de `AUTH_TOKEN_SECRET` según el contrato documentado. La implementación actual de `auth/` usa un secreto fijo, por lo que el contexto del Issue sobre la configuración existente no coincide con lo observado en el componente.
