package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.ValidatableResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;
import static org.junit.jupiter.api.Assertions.assertEquals;

@QuarkusTest
class AuthResourceTest {
    private static final String VALID_STUDENT_LOGIN =
            "{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}";
    private static final String ESCAPE_USERNAME = "escape-test-user";
    private static final String ESCAPE_PASSWORD = "escape-test-pass";
    private static final String DB_URL = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");

    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body(VALID_STUDENT_LOGIN)
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("token", notNullValue());
    }

    // Requisito auth-login: login valido devuelve el rol del usuario.
    @Test
    void loginReturnsStudentRole() {
        postLogin(VALID_STUDENT_LOGIN)
                .statusCode(200)
                .body("user.role", is("STUDENT"));
    }

    // Requisito auth-login: la respuesta conserva expiresIn, debug y displayName.
    @Test
    void loginResponseKeepsExistingShape() {
        postLogin(VALID_STUDENT_LOGIN)
                .statusCode(200)
                .body("expiresIn", is(3600))
                .body("debug", is("authenticated-with-legacy-flow"))
                .body("user.displayName", is("Workshop Student"));
    }

    // Requisito auth-login: credenciales invalidas responden 401 sin token.
    @Test
    void wrongPasswordReturns401WithoutToken() {
        postLogin("{\"username\":\"student\",\"password\":\"incorrecta\",\"client\":\"angular-workshop\"}")
                .statusCode(401)
                .body("token", nullValue());
    }

    // Requisito auth-login: username vacio o ausente responde 400 con mensaje existente.
    @Test
    void blankUsernameReturns400() {
        postLogin("{\"username\":\"   \",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .statusCode(400)
                .body("message", is("Username is required"));
    }

    @Test
    void missingUsernameReturns400() {
        postLogin("{\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .statusCode(400)
                .body("message", is("Username is required"));
    }

    // Requisito auth-login: password vacia o ausente responde 400 con mensaje existente.
    @Test
    void blankPasswordReturns400() {
        postLogin("{\"username\":\"student\",\"password\":\"\",\"client\":\"angular-workshop\"}")
                .statusCode(400)
                .body("message", is("Password is required"));
    }

    @Test
    void missingPasswordReturns400() {
        postLogin("{\"username\":\"student\",\"client\":\"angular-workshop\"}")
                .statusCode(400)
                .body("message", is("Password is required"));
    }

    // Requisito auth-login: client ausente, null o vacio responde 400 sin token. Cambio intencional frente a la caracterizacion anterior.
    @Test
    void missingClientReturns400WithoutToken() {
        postLogin("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .statusCode(400)
                .body("token", nullValue());
    }

    @Test
    void nullClientReturns400WithoutToken() {
        postLogin("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":null}")
                .statusCode(400)
                .body("token", nullValue());
    }

    @Test
    void blankClientReturns400WithoutToken() {
        postLogin("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"   \"}")
                .statusCode(400)
                .body("token", nullValue());
    }

    // Requisito auth-token-issuance: el token es un JWT firmado de tres segmentos, no el Base64 legacy.
    @Test
    void loginReturnsSignedJwt() {
        String token = postLogin(VALID_STUDENT_LOGIN).statusCode(200).extract().path("token");

        assertEquals(3, token.split("\\.").length);
    }

    // Requisito auth-login: displayName se devuelve escapado en HTML. Usa un usuario de prueba propio.
    @Test
    void displayNameIsHtmlEscaped() throws SQLException {
        insertEscapeUser("<b>Ana</b>");

        postLogin("{\"username\":\"" + ESCAPE_USERNAME + "\",\"password\":\"" + ESCAPE_PASSWORD + "\",\"client\":\"angular-workshop\"}")
                .statusCode(200)
                .body("user.displayName", is("&lt;b&gt;Ana&lt;/b&gt;"));
    }

    @AfterEach
    void removeEscapeUser() throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement("DELETE FROM legacy_users WHERE username = ?")) {
            statement.setString(1, ESCAPE_USERNAME);
            statement.executeUpdate();
        }
    }

    private void insertEscapeUser(String displayName) throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "INSERT INTO legacy_users(username, password, display_name, role) VALUES (?, ?, ?, 'STUDENT')")) {
            statement.setString(1, ESCAPE_USERNAME);
            statement.setString(2, ESCAPE_PASSWORD);
            statement.setString(3, displayName);
            statement.executeUpdate();
        }
    }

    private ValidatableResponse postLogin(String body) {
        return given()
                .contentType("application/json")
                .body(body)
                .when().post("/auth/login")
                .then();
    }
}
