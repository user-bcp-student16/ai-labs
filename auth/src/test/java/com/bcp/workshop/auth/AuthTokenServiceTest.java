package com.bcp.workshop.auth;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.interfaces.DecodedJWT;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AuthTokenServiceTest {
    private static final String TEST_TOKEN_SECRET = "test-only-auth-token-secret-32-bytes";

    @Test
    void createsSignedTokenWithIdentityAndExpiry() {
        AuthTokenService tokenService = new AuthTokenService(TEST_TOKEN_SECRET);

        String token = tokenService.create("student", "STUDENT");

        DecodedJWT claims = JWT.require(Algorithm.HMAC256(TEST_TOKEN_SECRET)).build().verify(token);
        assertEquals("student", claims.getSubject());
        assertEquals("STUDENT", claims.getClaim("role").asString());
        assertEquals(
                AuthTokenService.TOKEN_LIFETIME_SECONDS,
                (claims.getExpiresAt().getTime() - claims.getIssuedAt().getTime()) / 1000
        );
    }

    @Test
    void rejectsSigningSecretsShorterThan32Bytes() {
        assertThrows(IllegalStateException.class, () -> new AuthTokenService("too-short"));
    }
}
