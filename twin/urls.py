from django.urls import path

from . import views

app_name = "twin"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("<int:pk>/", views.detail, name="detail"),
]
