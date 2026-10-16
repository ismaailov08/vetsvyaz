from django.contrib import admin

from .models import Consultation, Prescription


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("animal", "farmer", "vet", "kind", "scheduled_at", "status")
    list_filter = ("status", "kind", "vet")
    search_fields = ("animal__name", "animal__tag", "complaint", "diagnosis")
    date_hierarchy = "scheduled_at"
    inlines = [PrescriptionInline]
