from django.contrib import admin

from .models import Message, Session


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    readonly_fields = ("direction", "content", "channel", "provider_message_id", "sent_at")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("customer_identifier", "tenant", "channel", "status", "updated_at")
    list_filter = ("tenant", "channel", "status")
    search_fields = ("customer_identifier",)
    inlines = [MessageInline]
