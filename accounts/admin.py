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
    list_display = ("farm_name", "user", "district", "vets_list")
    search_fields = ("farm_name", "user__last_name", "district")
    list_filter = ("vets",)
    filter_horizontal = ("vets",)  # удобный выбор врачей для связи Many-to-Many

    @admin.display(description="ветврачи")
    def vets_list(self, obj):
        return ", ".join(str(v) for v in obj.vets.all()) or "—"


@admin.register(Vet)
class VetAdmin(admin.ModelAdmin):
    list_display = ("__str__", "specialization", "license", "farms_count")
    search_fields = ("user__last_name", "specialization", "license")

    @admin.display(description="хозяйств")
    def farms_count(self, obj):
        return obj.farms.count()
