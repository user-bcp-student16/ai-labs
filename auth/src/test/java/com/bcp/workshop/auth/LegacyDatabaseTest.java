package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

@QuarkusTest
class LegacyDatabaseTest {
    @Inject
    LegacyDatabase database;

    // Tarea 4.2: credenciales validas devuelven el usuario sembrado.
    @Test
    void findsSeededUserWithValidCredentials() {
        UserRecord user = database.findByCredentials("student", "Workshop123!");

        assertNotNull(user);
        assertEquals("student", user.username());
        assertEquals("Workshop Student", user.displayName());
        assertEquals("STUDENT", user.role());
    }

    // Tarea 4.2: una entrada de inyeccion se trata como dato y no coincide con ningun usuario.
    @Test
    void returnsNullForInjectionInput() {
        assertNull(database.findByCredentials("' OR '1'='1' --", "anything"));
        assertNull(database.findByCredentials("student", "' OR '1'='1"));
    }
}
