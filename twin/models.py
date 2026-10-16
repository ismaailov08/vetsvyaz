from django.db import models

from farms.models import Animal


class Sensor(models.Model):
    """Ошейник/болюс с датчиками, закреплённый за животным."""

    animal = models.OneToOneField(Animal, on_delete=models.CASCADE, related_name="sensor", verbose_name="животное")
    serial = models.CharField("серийный номер", max_length=30, unique=True)
    installed = models.DateField("установлен")

    class Meta:
        verbose_name = "датчик"
        verbose_name_plural = "датчики"

    def __str__(self):
        return f"{self.serial} → {self.animal.name}"


class Reading(models.Model):
    """Одно показание датчика (раз в час)."""

    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="readings", verbose_name="датчик")
    taken_at = models.DateTimeField("время замера", db_index=True)
    temperature = models.DecimalField("температура, °C", max_digits=4, decimal_places=1)
    heart_rate = models.PositiveSmallIntegerField("пульс, уд/мин")
    activity = models.PositiveIntegerField("активность, шагов/ч")
    rumination = models.PositiveSmallIntegerField("жвачка, мин/ч", default=0)

    class Meta:
        verbose_name = "показание"
        verbose_name_plural = "показания"
        ordering = ["-taken_at"]
        constraints = [models.UniqueConstraint(fields=["sensor", "taken_at"], name="one_reading_per_moment")]

    def __str__(self):
        return f"{self.sensor.serial} {self.taken_at:%d.%m %H:%M}"
