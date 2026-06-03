import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("chatbot_platform")

# Read CELERY_* settings from Django settings.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks.py modules in every installed app.
app.autodiscover_tasks()


@app.task(name="config.ping")
def ping():
    """Trivial task to verify the Celery + Redis wiring (D1-03)."""
    return "pong"
