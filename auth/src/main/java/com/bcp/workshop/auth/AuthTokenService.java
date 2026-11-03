package com.bcp.workshop.auth;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Instant;
import java.util.Date;

@ApplicationScoped
public class AuthTokenService {
    public static final int TOKEN_LIFETIME_SECONDS = 3600;

    private final Algorithm signingAlgorithm;

    @Inject
    public AuthTokenService(@ConfigProperty(name = "auth.token.secret") String secret) {
        if (secret.getBytes(java.nio.charset.StandardCharsets.UTF_8).length < 32) {
            throw new IllegalStateException("AUTH_TOKEN_SECRET must contain at least 32 bytes");
        }
        signingAlgorithm = Algorithm.HMAC256(secret);
    }

    public String create(String username, String role) {
        Instant issuedAt = Instant.now();
        return JWT.create()
                .withSubject(username)
                .withClaim("role", role)
                .withIssuedAt(Date.from(issuedAt))
                .withExpiresAt(Date.from(issuedAt.plusSeconds(TOKEN_LIFETIME_SECONDS)))
                .sign(signingAlgorithm);
    }
}
