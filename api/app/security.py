from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from typing import Any

JWT_ISSUER = "workshop-auth-backend"
JWT_AUDIENCE = "workshop-requirements-api"
REQUIRED_CLAIMS = ("iss", "aud", "sub", "role", "iat", "exp")
SIGNING_SECRET_ENV = "AUTH_TOKEN_SECRET"
LEGACY_SECRET_ENV = "WORKSHOP_LEGACY_SECRET"
LEGACY_ENABLED_ENV = "WORKSHOP_LEGACY_TOKENS_ENABLED"
MIN_SIGNING_SECRET_BYTES = 32
INVALID_TOKEN = "invalid token"


class InvalidTokenError(Exception):
    pass


def authenticate(authorization: str, now: int | None = None) -> dict[str, str]:
    token = authorization.replace("Bearer ", "")
    current_time = int(time.time()) if now is None else now
    if token.count(".") == 2:
        claims = _verify_jwt(token, _signing_secret(), current_time)
    else:
        claims = _verify_legacy(token, current_time)
    return {"username": str(claims["sub"]), "role": str(claims["role"])}


def _signing_secret() -> str:
    secret = os.getenv(SIGNING_SECRET_ENV, "")
    if len(secret.encode("utf-8")) < MIN_SIGNING_SECRET_BYTES:
        raise InvalidTokenError(INVALID_TOKEN)
    return secret


def _verify_jwt(token: str, secret: str, current_time: int) -> dict[str, Any]:
    header_segment, payload_segment, signature_segment = token.split(".")
    header = _decode_json(header_segment)
    if header.get("alg") != "HS256":
        raise InvalidTokenError(INVALID_TOKEN)
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{header_segment}.{payload_segment}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected, _decode_segment(signature_segment)):
        raise InvalidTokenError(INVALID_TOKEN)
    claims = _decode_json(payload_segment)
    if any(name not in claims for name in REQUIRED_CLAIMS):
        raise InvalidTokenError(INVALID_TOKEN)
    if claims["iss"] != JWT_ISSUER or claims["aud"] != JWT_AUDIENCE:
        raise InvalidTokenError(INVALID_TOKEN)
    if not isinstance(claims["exp"], int) or claims["exp"] <= current_time:
        raise InvalidTokenError(INVALID_TOKEN)
    return claims


def _verify_legacy(token: str, current_time: int) -> dict[str, Any]:
    secret = os.getenv(LEGACY_SECRET_ENV, "")
    if os.getenv(LEGACY_ENABLED_ENV, "true").lower() != "true" or not secret:
        raise InvalidTokenError(INVALID_TOKEN)
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise InvalidTokenError(INVALID_TOKEN) from error
    parts = decoded.split("|")
    if len(parts) != 4 or not hmac.compare_digest(parts[3], secret):
        raise InvalidTokenError(INVALID_TOKEN)
    if not parts[2].isdigit() or int(parts[2]) < current_time:
        raise InvalidTokenError(INVALID_TOKEN)
    return {"sub": parts[0], "role": parts[1]}


def _decode_segment(segment: str) -> bytes:
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (binascii.Error, UnicodeEncodeError) as error:
        raise InvalidTokenError(INVALID_TOKEN) from error


def _decode_json(segment: str) -> dict[str, Any]:
    try:
        value = json.loads(_decode_segment(segment))
    except (ValueError, UnicodeDecodeError) as error:
        raise InvalidTokenError(INVALID_TOKEN) from error
    if not isinstance(value, dict):
        raise InvalidTokenError(INVALID_TOKEN)
    return value
