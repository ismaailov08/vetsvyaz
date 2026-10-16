from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    """Пускает в представление только пользователей с нужной ролью."""

    roles = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and self.roles and request.user.role not in self.roles and not request.user.is_superuser:
            raise PermissionDenied("Нет доступа для вашей роли")
        return super().dispatch(request, *args, **kwargs)


def visible_animals(user, queryset=None):
    """Фермер видит только своё стадо, врач и администратор — всех животных."""
    from farms.models import Animal
    qs = queryset if queryset is not None else Animal.objects.all()
    if user.is_farmer:
        return qs.filter(farmer__user=user)
    return qs


def visible_consultations(user, queryset=None):
    from consultations.models import Consultation
    qs = queryset if queryset is not None else Consultation.objects.all()
    if user.is_farmer:
        return qs.filter(farmer__user=user)
    if user.is_vet:
        return qs.filter(vet__user=user)
    return qs
