package com.bcp.workshop.auth;

import io.quarkus.test.InjectMock;
import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;

@QuarkusTest
class AuthResourceErrorTest {
    @InjectMock
    LegacyDatabase database;

    // Requisito auth-login: un error interno responde 500 generico, sin mensaje ni clase de excepcion.
    // Cambio intencional: reemplaza la caracterizacion anterior que exponia getMessage() y el nombre de la excepcion.
    @Test
    void internalErrorReturnsGeneric500() {
        doThrow(new IllegalStateException("db unavailable"))
                .when(database).findByCredentials(anyString(), anyString());

        String body = given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(500)
                .extract().asString();

        assertFalse(body.contains("db unavailable"));
        assertFalse(body.contains("IllegalStateException"));
    }
}
