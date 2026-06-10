"""Seed a demo tenant with a small working flow (D3-09). Idempotent: `python manage.py seed_demo`."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.flows.models import FlowOption, FlowStep
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Create a demo tenant 'Verde Kitchen' with a sample button flow."

    @transaction.atomic
    def handle(self, *args, **options):
        if Tenant.objects.filter(name="Verde Kitchen").exists():
            self.stdout.write(self.style.WARNING("Demo tenant already exists — skipping."))
            return

        tenant = Tenant.objects.create(
            name="Verde Kitchen",
            wa_phone_number="+14155550142",
            wa_phone_number_id="demo_pnid_verde",
            ig_account_id="@verdekitchen",
            greeting_message="Hi 👋 Thanks for messaging Verde Kitchen!",
            closing_message="Thanks for stopping by — see you soon! 🌿",
            handoff_enabled=True,
            handoff_email="frontdesk@verdekitchen.com",
        )

        start = FlowStep.objects.create(
            tenant=tenant, label="Welcome", message_text="What can I help you with today?", is_start=True
        )
        menu = FlowStep.objects.create(
            tenant=tenant, label="Menu", message_text="Here's what we serve 🍽 Pick a category:"
        )
        hours = FlowStep.objects.create(
            tenant=tenant, label="Hours", message_text="We're open 11am–10pm, daily.", is_terminal=True
        )

        FlowOption.objects.create(step=start, button_label="View menu", next_step=menu)
        FlowOption.objects.create(step=start, button_label="Opening hours", next_step=hours)
        FlowOption.objects.create(step=start, button_label="Book a table", next_step=None)  # terminal
        FlowOption.objects.create(step=menu, button_label="Back to start", next_step=start)
        FlowOption.objects.create(step=menu, button_label="That's all", next_step=None)  # terminal

        self.stdout.write(self.style.SUCCESS(f"Seeded demo tenant '{tenant.name}' (id={tenant.id})."))
