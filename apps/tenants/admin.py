from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "wa_phone_number", "ig_account_id", "handoff_enabled", "is_active")
    list_filter = ("is_active", "handoff_enabled")
    search_fields = ("name", "wa_phone_number", "ig_account_id")
    fieldsets = (
        (None, {"fields": ("name", "is_active")}),
        ("Channels", {"fields": ("wa_phone_number", "ig_account_id")}),
        ("Messages", {"fields": ("greeting_message", "closing_message")}),
        ("Handoff", {"fields": ("handoff_enabled", "handoff_email")}),
    )
