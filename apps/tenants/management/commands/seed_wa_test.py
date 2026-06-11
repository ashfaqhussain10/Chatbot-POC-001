"""
Seed a real-WhatsApp test tenant from .env, for end-to-end testing against the
Meta Cloud API. Idempotent: `python manage.py seed_wa_test`.

Reads `phone_number_id` and `wa_access_token` from the environment (.env). The
phone_number_id is how the worker routes Meta's inbound webhook to this tenant
(apps/channels/tasks.py). The token is stored Fernet-encrypted at rest (SEC-02).
"""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.flows.models import FlowOption, FlowStep
from apps.tenants.models import Tenant

TENANT_NAME = "WA Test"


class Command(BaseCommand):
    help = "Create/update a WhatsApp test tenant (from .env) with a small button flow."

    @transaction.atomic
    def handle(self, *args, **options):
        pnid = os.environ.get("phone_number_id")
        token = os.environ.get("wa_access_token")
        if not pnid or not token:
            self.stderr.write(self.style.ERROR(
                "Missing phone_number_id and/or wa_access_token in .env — cannot seed."
            ))
            return

        # Key on wa_phone_number_id (unique) so re-runs never hit MultipleObjectsReturned;
        # name is not unique.
        tenant, _ = Tenant.objects.update_or_create(
            wa_phone_number_id=pnid,
            defaults={
                "name": TENANT_NAME,
                "wa_access_token": token,            # encrypted on save (SEC-02)
                "greeting_message": "Hi 👋 Welcome to the Relay WhatsApp test bot!",
                "closing_message": "Thanks for testing Relay! 🎉",
                "handoff_enabled": False,            # terminal → closing message (no email noise)
                "is_active": True,
            },
        )

        # Rebuild the flow from scratch so re-running is fully idempotent.
        tenant.steps.all().delete()
        start = FlowStep.objects.create(
            tenant=tenant, label="Welcome",
            message_text="What would you like to do?", is_start=True,
        )
        menu = FlowStep.objects.create(
            tenant=tenant, label="Menu",
            message_text="Here's our menu 🍽 — tap an item:",
        )
        FlowOption.objects.create(step=start, button_label="View menu", next_step=menu)
        FlowOption.objects.create(step=start, button_label="Talk to a human", next_step=None)  # terminal
        FlowOption.objects.create(step=menu, button_label="Pizza 🍕", next_step=None)           # terminal
        FlowOption.objects.create(step=menu, button_label="Back", next_step=start)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded '{tenant.name}' (id={tenant.id}, phone_number_id={pnid}). "
            "Send 'hi' from a verified WhatsApp number to test."
        ))
