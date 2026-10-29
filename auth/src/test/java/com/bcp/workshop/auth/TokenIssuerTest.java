package com.bcp.workshop.auth;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TokenIssuerTest {
    private static final String SECRET = "workshop-test-secret-0123456789abcdef";
    private static final TokenIssuer ISSUER = new TokenIssuer(new TokenSecret(Optional.of(SECRET)));

    @Test
    void issuedTokenCarriesRequiredClaims() {
        Claims claims = parse(ISSUER.issue("student", "angular-workshop", "STUDENT"));

        assertEquals("student", claims.getSubject());
        assertEquals("angular-workshop", claims.get("client", String.class));
        assertEquals("STUDENT", claims.get("role", String.class));
        assertEquals("workshop-auth-backend", claims.getIssuer());
        assertTrue(claims.getAudience().contains("workshop-requirements-api"));
    }

    @Test
    void expirationIsExactlyTheLifetimeAfterIssuance() {
        Claims claims = parse(ISSUER.issue("student", "angular-workshop", "STUDENT"));

        long lifetime = claims.getExpiration().toInstant().getEpochSecond()
                - claims.getIssuedAt().toInstant().getEpochSecond();
        assertEquals(TokenIssuer.TOKEN_LIFETIME_SECONDS, lifetime);
    }

    private static Claims parse(String token) {
        return Jwts.parser()
                .verifyWith(Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8)))
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
