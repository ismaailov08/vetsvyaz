from django.contrib import admin

from .models import Reading, Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("serial", "animal", "installed")


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ("sensor", "taken_at", "temperature", "heart_rate", "activity", "rumination")
    list_filter = ("sensor",)
