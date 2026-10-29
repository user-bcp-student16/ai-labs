package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.QuarkusTestProfile;
import io.quarkus.test.junit.TestProfile;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.junit.jupiter.api.Assertions.assertFalse;

// Requisito auth-token-issuance: un secreto menor de 32 bytes responde 500 sin revelar el secreto.
@QuarkusTest
@TestProfile(ShortTokenSecretTest.ShortSecretProfile.class)
class ShortTokenSecretTest {
    static final String SHORT_SECRET = "abcdefghijklmnopqrstuvwxyz01234";
    private static final String VALID_STUDENT_LOGIN =
            "{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}";

    @Test
    void loginFailsWithGeneric500AndDoesNotLeakSecret() {
        String body = given()
                .contentType("application/json")
                .body(VALID_STUDENT_LOGIN)
                .when().post("/auth/login")
                .then()
                .statusCode(500)
                .extract().asString();

        assertFalse(body.contains(SHORT_SECRET));
    }

    public static class ShortSecretProfile implements QuarkusTestProfile {
        @Override
        public Map<String, String> getConfigOverrides() {
            return Map.of("AUTH_TOKEN_SECRET", SHORT_SECRET);
        }
    }
}
