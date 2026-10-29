package com.bcp.workshop.auth;

import io.jsonwebtoken.security.Keys;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Optional;

@ApplicationScoped
public class TokenSecret {
    static final int MIN_SECRET_BYTES = 32;

    private final Optional<String> secret;

    @Inject
    public TokenSecret(@ConfigProperty(name = "AUTH_TOKEN_SECRET") Optional<String> secret) {
        this.secret = secret;
    }

    SecretKey signingKey() {
        return toSigningKey(secret.orElse(null));
    }

    static SecretKey toSigningKey(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("AUTH_TOKEN_SECRET no configurado");
        }
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        if (bytes.length < MIN_SECRET_BYTES) {
            throw new IllegalStateException("AUTH_TOKEN_SECRET debe tener al menos 32 bytes");
        }
        return Keys.hmacShaKeyFor(bytes);
    }
}
