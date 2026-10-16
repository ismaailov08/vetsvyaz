from django.urls import path

from . import views

app_name = "farms"

urlpatterns = [
    path("", views.home, name="home"),
    path("animals/", views.AnimalListView.as_view(), name="animal_list"),
    path("diseases/", views.disease_log, name="disease_log"),
    path("farms/", views.farm_list, name="farm_list"),
    path("farms/<int:pk>/", views.farm_detail, name="farm_detail"),
    path("animals/new/", views.AnimalCreateView.as_view(), name="animal_create"),
    path("animals/<int:pk>/", views.AnimalDetailView.as_view(), name="animal_detail"),
    path("animals/<int:pk>/edit/", views.AnimalUpdateView.as_view(), name="animal_edit"),
    path("animals/<int:pk>/vaccinations/", views.add_vaccination, name="add_vaccination"),
]
