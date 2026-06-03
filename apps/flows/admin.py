from django.contrib import admin

from .models import FlowOption, FlowStep


class FlowOptionInline(admin.TabularInline):
    model = FlowOption
    fk_name = "step"  # FlowOption has two FKs to FlowStep; this is the owning one
    extra = 1


@admin.register(FlowStep)
class FlowStepAdmin(admin.ModelAdmin):
    list_display = ("label", "tenant", "is_start", "is_terminal")
    list_filter = ("tenant", "is_start", "is_terminal")
    search_fields = ("label",)
    inlines = [FlowOptionInline]
