package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.ValidatableResponse;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

@QuarkusTest
class AuthResourceTest {
    private static final String VALID_USERNAME = "student";
    private static final String VALID_PASSWORD = "Workshop123!";
    private static final String BOOLEAN_BYPASS = "' OR '1'='1";
    private static final String BOOLEAN_BYPASS_WITH_COMMENT = "' OR '1'='1' --";

    private ValidatableResponse postLogin(Map<String, String> credentials) {
        return given()
                .contentType("application/json")
                .body(credentials)
                .when().post("/auth/login")
                .then();
    }

    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("token", notNullValue());
    }

    // Spec "Credenciales validas": la respuesta 200 conserva el contrato observable (tarea 2.1).
    @Test
    void validLoginKeepsResponseContract() {
        postLogin(Map.of("username", VALID_USERNAME, "password", VALID_PASSWORD))
                .statusCode(200)
                .body("token", notNullValue())
                .body("expiresIn", is(3600))
                .body("user.username", is("student"))
                .body("user.displayName", is("Workshop Student"))
                .body("user.role", is("STUDENT"));
    }

    // Contrato 401 de credenciales incorrectas, sin token (tarea 2.2).
    @Test
    void wrongPasswordForExistingUserIsRejected() {
        postLogin(Map.of("username", VALID_USERNAME, "password", "WrongPassword1!"))
                .statusCode(401)
                .body("token", nullValue())
                .body("message", is("Invalid user student or password"));
    }

    // Contrato 401 de usuario inexistente, sin token (tarea 2.3).
    @Test
    void unknownUserIsRejected() {
        postLogin(Map.of("username", "nobody", "password", VALID_PASSWORD))
                .statusCode(401)
                .body("token", nullValue())
                .body("message", is("Invalid user nobody or password"));
    }

    // Contrato 400 de validacion de entrada (tarea 2.4).
    @Test
    void emptyUsernameIsBadRequest() {
        postLogin(Map.of("username", "", "password", VALID_PASSWORD))
                .statusCode(400)
                .body("message", is("Username is required"));
    }

    @Test
    void emptyPasswordIsBadRequest() {
        postLogin(Map.of("username", VALID_USERNAME, "password", ""))
                .statusCode(400)
                .body("message", is("Password is required"));
    }

    @Test
    void missingBodyIsBadRequest() {
        given()
                .contentType("application/json")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Request is null"));
    }

    // Spec "Entrada de inyeccion en el usuario": 401 sin token (tarea 2.5, defecto del Issue #22).
    @Test
    void injectionInUsernameIsRejected() {
        postLogin(Map.of("username", BOOLEAN_BYPASS_WITH_COMMENT, "password", "anything"))
                .statusCode(401)
                .body("token", nullValue());
    }

    // Spec "Entrada de inyeccion en el usuario": comentario tras un usuario real (tarea 2.6).
    @Test
    void commentInjectionAfterRealUsernameIsRejected() {
        postLogin(Map.of("username", VALID_USERNAME + "'--", "password", "anything"))
                .statusCode(401)
                .body("token", nullValue());
    }

    // Spec "Entrada de inyeccion en la contraseña": 401 sin token (tarea 2.7).
    @Test
    void injectionInPasswordIsRejected() {
        postLogin(Map.of("username", VALID_USERNAME, "password", BOOLEAN_BYPASS))
                .statusCode(401)
                .body("token", nullValue());
    }
}
