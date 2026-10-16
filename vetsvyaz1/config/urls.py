"""Главная карта адресов проекта «ВетСвязь»."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "ВетСвязь — администрирование"
admin.site.site_title = "ВетСвязь"
admin.site.index_title = "Управление данными"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("consultations/", include("consultations.urls")),
    path("notifications/", include("notifications.urls")),
    path("twin/", include("twin.urls")),
    path("assistant/", include("assistant.urls")),
    path("api/", include("api.urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("", include("farms.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
