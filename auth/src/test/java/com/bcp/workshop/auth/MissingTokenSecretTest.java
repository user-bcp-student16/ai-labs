package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.QuarkusTestProfile;
import io.quarkus.test.junit.TestProfile;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.nullValue;

// Requisito auth-token-issuance: sin AUTH_TOKEN_SECRET el login responde 500 generico sin token.
@QuarkusTest
@TestProfile(MissingTokenSecretTest.NoSecretProfile.class)
class MissingTokenSecretTest {
    private static final String VALID_STUDENT_LOGIN =
            "{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}";

    @Test
    void loginFailsWithGeneric500WithoutSecret() {
        given()
                .contentType("application/json")
                .body(VALID_STUDENT_LOGIN)
                .when().post("/auth/login")
                .then()
                .statusCode(500)
                .body("token", nullValue());
    }

    public static class NoSecretProfile implements QuarkusTestProfile {
        @Override
        public Map<String, String> getConfigOverrides() {
            return Map.of("AUTH_TOKEN_SECRET", "");
        }
    }
}
