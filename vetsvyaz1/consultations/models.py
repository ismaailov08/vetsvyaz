from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse

from accounts.models import Farmer, Vet
from farms.models import Animal


class Consultation(models.Model):
    """Запись фермера к ветврачу: видео, чат или выезд."""

    class Kind(models.TextChoices):
        VIDEO = "video", "Видеозвонок"
        CHAT = "chat", "Чат"
        VISIT = "visit", "Выезд на ферму"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Запланирована"
        DONE = "done", "Завершена"
        CANCELLED = "cancelled", "Отменена"

    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="consultations", verbose_name="фермер")
    vet = models.ForeignKey(Vet, on_delete=models.PROTECT, related_name="consultations", verbose_name="ветврач")
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="consultations", verbose_name="животное")
    kind = models.CharField("формат", max_length=6, choices=Kind.choices, default=Kind.VIDEO)
    scheduled_at = models.DateTimeField("дата и время")
    complaint = models.TextField("жалоба / симптомы")
    status = models.CharField("статус", max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    diagnosis = models.CharField("диагноз", max_length=200, blank=True)
    conclusion = models.TextField("заключение врача", blank=True)
    created = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "консультация"
        verbose_name_plural = "консультации"
        ordering = ["-scheduled_at"]
        constraints = [
            # один врач не может принять двух фермеров в одно и то же время
            models.UniqueConstraint(fields=["vet", "scheduled_at"], condition=Q(status="scheduled"),
                                    name="one_slot_per_vet"),
        ]

    def __str__(self):
        return f"{self.animal.name}: {self.scheduled_at:%d.%m %H:%M}"

    def get_absolute_url(self):
        return reverse("consultations:detail", args=[self.pk])

    def clean(self):
        if self.animal_id and self.farmer_id and self.animal.farmer_id != self.farmer_id:
            raise ValidationError({"animal": "Можно записать только своё животное"})


class Prescription(models.Model):
    """Назначение препарата по итогам консультации."""

    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="prescriptions",
                                     verbose_name="консультация")
    drug = models.CharField("препарат", max_length=120)
    dose = models.CharField("доза и способ", max_length=120)
    days = models.PositiveSmallIntegerField("курс, дней", validators=[MinValueValidator(1), MaxValueValidator(60)])
    withdrawal_days = models.PositiveSmallIntegerField("срок ожидания (молоко/мясо), дней", default=0)

    class Meta:
        verbose_name = "назначение"
        verbose_name_plural = "назначения"

    def __str__(self):
        return f"{self.drug} {self.dose}"
