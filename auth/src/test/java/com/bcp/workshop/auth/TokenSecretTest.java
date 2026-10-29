package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class TokenSecretTest {
    private static final String BYTES_31 = "abcdefghijklmnopqrstuvwxyz01234";
    private static final String BYTES_32 = "abcdefghijklmnopqrstuvwxyz012345";

    @Test
    void rejectsSecretShorterThan32Bytes() {
        assertThrows(IllegalStateException.class, () -> TokenSecret.toSigningKey(BYTES_31));
    }

    @Test
    void acceptsSecretOf32Bytes() {
        assertEquals(32, TokenSecret.toSigningKey(BYTES_32).getEncoded().length);
    }

    @Test
    void rejectsMissingSecret() {
        assertThrows(IllegalStateException.class, () -> TokenSecret.toSigningKey(null));
        assertThrows(IllegalStateException.class, () -> TokenSecret.toSigningKey("   "));
    }
}
