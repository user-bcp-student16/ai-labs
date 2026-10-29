package com.bcp.workshop.auth;

import io.jsonwebtoken.Jwts;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Instant;
import java.util.Date;

@ApplicationScoped
public class TokenIssuer {
    static final int TOKEN_LIFETIME_SECONDS = 3600;
    static final String ISSUER = "workshop-auth-backend";
    static final String AUDIENCE = "workshop-requirements-api";

    private final TokenSecret tokenSecret;

    @Inject
    public TokenIssuer(TokenSecret tokenSecret) {
        this.tokenSecret = tokenSecret;
    }

    public String issue(String username, String client, String role) {
        Instant issuedAt = Instant.now();
        return Jwts.builder()
                .subject(username)
                .claim("client", client)
                .claim("role", role)
                .issuer(ISSUER)
                .audience().single(AUDIENCE)
                .issuedAt(Date.from(issuedAt))
                .expiration(Date.from(issuedAt.plusSeconds(TOKEN_LIFETIME_SECONDS)))
                .signWith(tokenSecret.signingKey(), Jwts.SIG.HS256)
                .compact();
    }
}
