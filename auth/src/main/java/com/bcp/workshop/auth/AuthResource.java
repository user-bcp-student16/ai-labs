package com.bcp.workshop.auth;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.apache.commons.text.StringEscapeUtils;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@Path("/auth")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class AuthResource {
    private static final String LEGACY_DEBUG_FLAG = "authenticated-with-legacy-flow";
    private static final String INTERNAL_ERROR_MESSAGE = "Internal authentication error";

    @Inject
    LegacyDatabase database;

    @Inject
    TokenIssuer tokenIssuer;

    @POST
    @Path("/login")
    public Response login(LoginRequest request) {
        Optional<Response> invalidRequest = validateRequest(request);
        if (invalidRequest.isPresent()) {
            return invalidRequest.get();
        }
        try {
            return authenticate(request);
        } catch (Exception error) {
            return internalError();
        }
    }

    private Optional<Response> validateRequest(LoginRequest request) {
        if (request == null) {
            return Optional.of(badRequest("Request is null"));
        }
        if (isBlank(request.username)) {
            return Optional.of(badRequest("Username is required"));
        }
        if (isBlank(request.password)) {
            return Optional.of(badRequest("Password is required"));
        }
        if (isBlank(request.client)) {
            return Optional.of(badRequest("Client is required"));
        }
        return Optional.empty();
    }

    private Response authenticate(LoginRequest request) {
        UserRecord user = database.findByCredentials(request.username, request.password);
        if (user == null) {
            return Response.status(401)
                    .entity(Map.of("message", "Invalid user " + request.username + " or password"))
                    .build();
        }
        return Response.ok(loginBody(user, request.client)).build();
    }

    private Map<String, Object> loginBody(UserRecord user, String client) {
        Map<String, Object> body = new HashMap<>();
        body.put("token", tokenIssuer.issue(user.username(), client, user.role()));
        body.put("expiresIn", TokenIssuer.TOKEN_LIFETIME_SECONDS);
        body.put("user", Map.of(
                "username", user.username(),
                "displayName", StringEscapeUtils.escapeHtml4(user.displayName()),
                "role", user.role()
        ));
        body.put("debug", LEGACY_DEBUG_FLAG);
        return body;
    }

    private static Response badRequest(String message) {
        return Response.status(400).entity(Map.of("message", message)).build();
    }

    private static Response internalError() {
        return Response.status(500).entity(Map.of("message", INTERNAL_ERROR_MESSAGE)).build();
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
