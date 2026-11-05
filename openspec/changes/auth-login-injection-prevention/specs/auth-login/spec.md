# Spec Delta

## Purpose

Esta capacidad define el comportamiento observable del inicio de sesion, incluyendo la preservacion del acceso valido y el rechazo de intentos de eludir la validacion de credenciales.

## ADDED Requirements

### Requirement: El inicio de sesion valido conserva su respuesta

El sistema MUST responder a credenciales validas con HTTP 200 y un cuerpo que contenga `user.username` y `token`.

#### Scenario: Credenciales validas

- **WHEN** se envia `POST /auth/login` con las credenciales de prueba validas `student` y `Workshop123!`
- **THEN** la respuesta es HTTP 200 y contiene `user.username` igual a `student` y el campo `token`

### Requirement: El inicio de sesion rechaza entradas de inyeccion

El sistema MUST rechazar las credenciales que intenten alterar la validacion de autenticacion y MUST responder con HTTP 401 sin incluir un token.

#### Scenario: Entrada de inyeccion en el usuario

- **WHEN** se envia `POST /auth/login` con una entrada de prueba de inyeccion en el campo de usuario
- **THEN** la respuesta es HTTP 401 y no contiene un token

#### Scenario: Entrada de inyeccion en la contraseña

- **WHEN** se envia `POST /auth/login` con una entrada de prueba de inyeccion en el campo de contraseña
- **THEN** la respuesta es HTTP 401 y no contiene un token