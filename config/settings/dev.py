from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Dev-only encryption key so the app runs locally without a .env entry.
# NEVER use this in production — prod sets FERNET_KEY from a Railway secret (D-106).
FERNET_KEY = env("FERNET_KEY", default="9i-YVeZcmldJUorQFj6G-3VHTH7GWJ-HhbVEeQF19as=")  # noqa: F405
