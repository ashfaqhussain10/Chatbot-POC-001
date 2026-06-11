from .base import *  # noqa: F401,F403

DEBUG = True
# Local hosts + ngrok tunnel domains (dev-only) so Meta's webhook reaches us
# through the tunnel. ".ngrok-free.app" matches any ngrok subdomain.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".ngrok-free.app", ".ngrok-free.dev", ".ngrok.io"]
# DRF/Django needs the tunnel origin trusted for any unsafe (POST) request paths.
CSRF_TRUSTED_ORIGINS = ["https://*.ngrok-free.app", "https://*.ngrok-free.dev", "https://*.ngrok.io"]

# Dev-only encryption key so the app runs locally without a .env entry.
# NEVER use this in production — prod sets FERNET_KEY from a Railway secret (D-106).
FERNET_KEY = env("FERNET_KEY", default="9i-YVeZcmldJUorQFj6G-3VHTH7GWJ-HhbVEeQF19as=")  # noqa: F405
