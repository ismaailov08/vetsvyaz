from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Farmer, User, Vet


@admin.register(User)
class VetUserAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "role", "phone", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (("ВетСвязь", {"fields": ("role", "phone")}),)


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ("farm_name", "user", "district")
    search_fields = ("farm_name", "user__last_name", "district")


@admin.register(Vet)
class VetAdmin(admin.ModelAdmin):
    list_display = ("__str__", "specialization", "license")
