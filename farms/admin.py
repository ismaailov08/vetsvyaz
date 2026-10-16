from django.contrib import admin

from .models import Animal, Vaccination


class VaccinationInline(admin.TabularInline):
    model = Vaccination
    extra = 0


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ("tag", "name", "species", "breed", "farmer", "status")
    list_filter = ("species", "status", "farmer")
    search_fields = ("tag", "name", "breed")
    inlines = [VaccinationInline]


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = ("animal", "vaccine", "done_on", "next_on")
    list_filter = ("vaccine",)
    date_hierarchy = "next_on"
