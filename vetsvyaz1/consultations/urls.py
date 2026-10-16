from django.urls import path

from . import views

app_name = "consultations"

urlpatterns = [
    path("", views.ConsultationListView.as_view(), name="list"),
    path("new/", views.create, name="create"),
    path("<int:pk>/", views.ConsultationDetailView.as_view(), name="detail"),
    path("<int:pk>/cancel/", views.cancel, name="cancel"),
    path("<int:pk>/conclude/", views.conclude, name="conclude"),
    path("<int:pk>/call/", views.call, name="call"),
    path("<int:pk>/report/", views.report, name="report"),
]
