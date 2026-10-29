# Spec Delta

## Purpose

Define tokens issued by the auth login so their identity, lifetime, signature, and claims remain usable under the JWT contract documented for the API.

## ADDED Requirements

### Requirement: Issued tokens contain required identity and consumer claims
El sistema SHALL emitir un JWT con `sub`, `client`, `role`, `iat`, `exp`, `iss` y `aud`, conservando los valores de emisor y audiencia del contrato documentado.

#### Scenario: Claims match the authenticated login
- **WHEN** se completa un login válido con un `client` no vacío
- **THEN** el JWT contiene `sub` igual al usuario autenticado, `client` igual al valor recibido, `role` igual al rol del usuario, `iss=workshop-auth-backend` y `aud=workshop-requirements-api`

### Requirement: Issued token lifetime matches the login response
El sistema SHALL emitir `iat` y `exp` de forma que el tiempo de vida anunciado en `expiresIn` coincida con `exp - iat` dentro de una tolerancia máxima de un segundo.

#### Scenario: Default lifetime
- **WHEN** se completa un login válido sin configuración de duración alternativa
- **THEN** `expiresIn` es `3600` segundos y `exp - iat` difiere de ese valor como máximo en un segundo

#### Scenario: Expired token
- **WHEN** se presenta al verificador documentado un token emitido cuyo `exp` ya pasó
- **THEN** el token se rechaza por expiración

### Requirement: Issued token signature is verifiable
El sistema SHALL emitir un JWT firmado que pueda validarse con el secreto configurado y SHALL NOT emitir un token cuya firma no sea verificable.

#### Scenario: Token with valid signature
- **WHEN** se valida un token emitido sin alteraciones con el secreto configurado
- **THEN** la firma es válida y los claims requeridos pueden leerse

#### Scenario: Token with altered claims
- **WHEN** se altera un claim del token emitido sin producir una firma válida
- **THEN** la verificación de la firma falla

### Requirement: Signing secret is configured outside source code
El sistema SHALL obtener `AUTH_TOKEN_SECRET` del entorno, SHALL exigir un valor de al menos 32 bytes y SHALL NOT usar un secreto incorporado al código ni un valor por defecto.

#### Scenario: Secret is absent or too short
- **WHEN** se intenta completar un login y `AUTH_TOKEN_SECRET` no está configurado o tiene menos de 32 bytes
- **THEN** el sistema no emite un token y responde con un error de servidor sin exponer el secreto

### Requirement: Signing material is not logged
El sistema SHALL NOT escribir el token emitido ni el secreto de firma en los logs.

#### Scenario: Successful login logging
- **WHEN** se completa un login válido
- **THEN** los logs generados no contienen el token emitido ni el secreto configurado
