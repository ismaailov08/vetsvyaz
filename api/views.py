from rest_framework import mixins, permissions, viewsets

from accounts.permissions import visible_animals, visible_consultations
from twin.models import Reading

from .serializers import AnimalSerializer, ConsultationSerializer, ReadingSerializer


class AnimalViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/animals/ — животные, доступные текущему пользователю."""
    serializer_class = AnimalSerializer

    def get_queryset(self):
        return visible_animals(self.request.user).prefetch_related("vaccinations")


class ConsultationViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultationSerializer

    def get_queryset(self):
        return visible_consultations(self.request.user).prefetch_related("prescriptions")

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user.farmer)


class IsSensorGateway(permissions.BasePermission):
    """Писать показания может только служебная учётная запись (администратор)."""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or request.user.is_staff


class ReadingViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """POST /api/readings/ — датчики присылают показания в цифровой двойник."""
    serializer_class = ReadingSerializer
    permission_classes = [permissions.IsAuthenticated, IsSensorGateway]

    def get_queryset(self):
        animals = visible_animals(self.request.user)
        return Reading.objects.filter(sensor__animal__in=animals).select_related("sensor")[:200]
