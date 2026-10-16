from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Пользователь системы с ролью: фермер, ветврач или администратор."""

    class Role(models.TextChoices):
        FARMER = "farmer", "Фермер"
        VET = "vet", "Ветврач"
        ADMIN = "admin", "Администратор"

    role = models.CharField("роль", max_length=10, choices=Role.choices, default=Role.FARMER)
    phone = models.CharField("телефон", max_length=20, blank=True)

    @property
    def is_farmer(self):
        return self.role == self.Role.FARMER

    @property
    def is_vet(self):
        return self.role == self.Role.VET

    @property
    def is_district_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class Farmer(models.Model):
    """Профиль фермера: одно хозяйство на пользователя."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="farmer", verbose_name="пользователь")
    farm_name = models.CharField("хозяйство", max_length=120)
    district = models.CharField("район", max_length=160)

    class Meta:
        verbose_name = "фермер"
        verbose_name_plural = "фермеры"

    def __str__(self):
        return f"{self.farm_name} ({self.user.get_full_name() or self.user.username})"


class Vet(models.Model):
    """Профиль ветеринарного врача."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vet", verbose_name="пользователь")
    specialization = models.CharField("специализация", max_length=120)
    license = models.CharField("номер лицензии", max_length=20, unique=True)

    class Meta:
        verbose_name = "ветврач"
        verbose_name_plural = "ветврачи"

    def __str__(self):
        return self.user.get_full_name() or self.user.username
