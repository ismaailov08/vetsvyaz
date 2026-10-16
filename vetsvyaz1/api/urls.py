from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("animals", views.AnimalViewSet, basename="animal")
router.register("consultations", views.ConsultationViewSet, basename="consultation")
router.register("readings", views.ReadingViewSet, basename="reading")

urlpatterns = router.urls
