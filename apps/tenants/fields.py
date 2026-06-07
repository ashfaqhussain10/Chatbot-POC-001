"""
Transparent field-level encryption for tenant Meta tokens (SEC-02 / D-100 = Fernet).

Values are encrypted on the way to the database and decrypted on the way out, so the
plaintext token never sits at rest and never appears in the DB. The key comes from
settings.FERNET_KEY (env / Railway secret — never the DB, D-106).
"""
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _fernet():
    key = getattr(settings, "FERNET_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "FERNET_KEY is not set — required to read/write encrypted tenant tokens."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedTextField(models.TextField):
    """TextField that stores its value Fernet-encrypted at rest."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        # Decrypt; let an invalid token raise loudly rather than leak/guess.
        return _fernet().decrypt(value.encode()).decode()
