import os

os.environ["AUTH_TOKEN_SECRET"] = "test-only-auth-token-secret-32-bytes"
os.environ.pop("LEGACY_TOKEN_ACCEPT_UNTIL", None)
