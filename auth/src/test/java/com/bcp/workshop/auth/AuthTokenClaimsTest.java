package com.bcp.workshop.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.Response;
import org.junit.jupiter.api.Test;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;

import static io.restassured.RestAssured.given;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
class AuthTokenClaimsTest {
    // Valor de prueba; debe coincidir con AUTH_TOKEN_SECRET del perfil %test (tarea 4.2).
    static final String TEST_SECRET = "workshop-test-secret-0123456789abcdef";
    private static final String VALID_STUDENT_LOGIN =
            "{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}";
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Base64.Decoder URL_DECODER = Base64.getUrlDecoder();

    // Requisito auth-token-issuance: el token incluye sub, client, role, iss, aud, iat y exp.
    @Test
    void tokenHasRequiredClaims() throws Exception {
        JsonNode claims = claimsOf(loginResponse().path("token"));

        assertEquals("student", claims.get("sub").asText());
        assertEquals("angular-workshop", claims.get("client").asText());
        assertEquals("STUDENT", claims.get("role").asText());
        assertEquals("workshop-auth-backend", claims.get("iss").asText());
        JsonNode audience = claims.get("aud");
        assertTrue(audience.isTextual(), "aud must be a single string per docs/ENDPOINTS.md");
        assertEquals("workshop-requirements-api", audience.asText());
        assertTrue(claims.get("iat").isIntegralNumber());
        assertTrue(claims.get("exp").isIntegralNumber());
    }

    // Requisito auth-token-issuance: exp - iat es igual a expiresIn (3600).
    @Test
    void expMinusIatEqualsExpiresIn() throws Exception {
        Response response = loginResponse();
        JsonNode claims = claimsOf(response.path("token"));
        int expiresIn = response.path("expiresIn");

        assertEquals(3600, expiresIn);
        assertEquals(expiresIn, claims.get("exp").asLong() - claims.get("iat").asLong());
    }

    // Requisito auth-token-issuance: la firma HS256 verifica con el secreto configurado.
    @Test
    void signatureVerifiesWithConfiguredSecret() throws Exception {
        String token = loginResponse().path("token");

        assertTrue(hasValidSignature(token, TEST_SECRET));
    }

    // Requisito auth-token-issuance: alterar un claim invalida la firma.
    @Test
    void alteredClaimInvalidatesSignature() throws Exception {
        String token = loginResponse().path("token");
        String[] parts = segments(token);
        ObjectNode claims = (ObjectNode) claimsOf(token);
        claims.put("role", "TRAINER");
        String tamperedPayload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(MAPPER.writeValueAsBytes(claims));

        assertFalse(hasValidSignature(parts[0] + "." + tamperedPayload + "." + parts[2], TEST_SECRET));
    }

    // Requisito auth-token-issuance: ni el token ni el secreto se escriben en stderr durante un login correcto.
    @Test
    void successfulLoginDoesNotWriteTokenOrSecretToStderr() throws Exception {
        PrintStream originalErr = System.err;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        String token;
        System.setErr(new PrintStream(captured, true, StandardCharsets.UTF_8));
        try {
            token = loginResponse().path("token");
        } finally {
            System.setErr(originalErr);
        }

        String output = captured.toString(StandardCharsets.UTF_8);
        assertFalse(output.contains(token));
        assertFalse(output.contains(TEST_SECRET));
    }

    private Response loginResponse() {
        return given()
                .contentType("application/json")
                .body(VALID_STUDENT_LOGIN)
                .when().post("/auth/login")
                .then().statusCode(200)
                .extract().response();
    }

    private static String[] segments(String token) {
        String[] parts = token.split("\\.");
        assertEquals(3, parts.length, "El token debe ser un JWT con tres segmentos");
        return parts;
    }

    private static JsonNode claimsOf(String token) throws Exception {
        return MAPPER.readTree(URL_DECODER.decode(segments(token)[1]));
    }

    private static boolean hasValidSignature(String token, String secret) throws Exception {
        String[] parts = segments(token);
        Mac mac = Mac.getInstance(HMAC_ALGORITHM);
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
        byte[] expected = mac.doFinal((parts[0] + "." + parts[1]).getBytes(StandardCharsets.US_ASCII));
        return MessageDigest.isEqual(expected, URL_DECODER.decode(parts[2]));
    }
}
