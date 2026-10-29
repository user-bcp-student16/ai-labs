# Spec Delta

## Purpose

Define el contrato observable del login de `auth/` y preservar la respuesta que los consumidores necesitan mientras se incorpora un cliente validado.

## ADDED Requirements

### Requirement: Login requires a client identifier
El sistema SHALL requerir un `client` no vacío en la solicitud de `POST /auth/login`. Al no existir un catálogo de clientes en el Issue ni en el contrato documentado, todo valor no vacío se considera válido para esta propuesta.

#### Scenario: Missing client
- **WHEN** se envían credenciales válidas sin el campo `client`
- **THEN** el login responde `400` y no emite un token

#### Scenario: Blank client
- **WHEN** se envían credenciales válidas con `client` vacío o compuesto solo por espacios
- **THEN** el login responde `400` y no emite un token

#### Scenario: Non-empty client
- **WHEN** se envían credenciales válidas con `client` no vacío
- **THEN** el login puede autenticarlas y el token emitido refleja ese mismo valor en el claim `client`

### Requirement: Successful login preserves its response contract
El sistema SHALL responder `200` al autenticar credenciales válidas y SHALL incluir `token`, `expiresIn` y `user` en el cuerpo JSON.

#### Scenario: Valid login
- **WHEN** se envían credenciales válidas y un `client` no vacío
- **THEN** la respuesta tiene estado `200`, incluye los campos `token`, `expiresIn` y `user`, y `token` no está vacío

### Requirement: Invalid credentials do not issue a token
El sistema SHALL rechazar credenciales inválidas con estado `401` y no SHALL incluir un token en la respuesta.

#### Scenario: Invalid password
- **WHEN** se envía un usuario existente con una contraseña incorrecta y un `client` no vacío
- **THEN** la respuesta tiene estado `401` y no incluye `token`

### Requirement: Login errors do not expose credentials or signing material
El sistema SHALL NOT incluir la contraseña, el token ni el secreto de firma en los cuerpos de error del login.

#### Scenario: Authentication error response
- **WHEN** las credenciales se rechazan o la solicitud no cumple los requisitos
- **THEN** el cuerpo de error no contiene la contraseña, el token ni el secreto de firma
