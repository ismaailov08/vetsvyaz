from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse

from accounts.models import Farmer

TAG_VALIDATOR = RegexValidator(r"^KZ \d{4} \d{4}$", "Номер бирки пишется так: KZ 0000 0000")


class Animal(models.Model):
    """Животное хозяйства с биркой ИНЖ."""

    class Species(models.TextChoices):
        CATTLE = "cattle", "КРС"
        SHEEP = "sheep", "Овца"
        GOAT = "goat", "Коза"
        HORSE = "horse", "Лошадь"
        CAMEL = "camel", "Верблюд"

    class Sex(models.TextChoices):
        FEMALE = "F", "Самка"
        MALE = "M", "Самец"

    class Status(models.TextChoices):
        HEALTHY = "healthy", "Здоров"
        TREATMENT = "treatment", "На лечении"
        QUARANTINE = "quarantine", "Карантин"

    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="animals", verbose_name="владелец")
    tag = models.CharField("бирка (ИНЖ)", max_length=12, unique=True, validators=[TAG_VALIDATOR])
    name = models.CharField("кличка", max_length=60)
    species = models.CharField("вид", max_length=10, choices=Species.choices)
    breed = models.CharField("порода", max_length=80, blank=True)
    sex = models.CharField("пол", max_length=1, choices=Sex.choices)
    born = models.DateField("дата рождения")
    weight_kg = models.DecimalField("живой вес, кг", max_digits=6, decimal_places=1, validators=[MinValueValidator(1)])
    status = models.CharField("статус", max_length=12, choices=Status.choices, default=Status.HEALTHY)
    photo = models.ImageField("фото", upload_to="animals/", blank=True)
    created = models.DateTimeField("добавлено", auto_now_add=True)

    class Meta:
        verbose_name = "животное"
        verbose_name_plural = "животные"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} · {self.tag}"

    def get_absolute_url(self):
        return reverse("farms:animal_detail", args=[self.pk])

    @property
    def age_text(self):
        months = (date.today().year - self.born.year) * 12 + date.today().month - self.born.month
        return f"{months} мес." if months < 12 else f"{months // 12} г."


class Vaccination(models.Model):
    """Прививка животного и дата следующей ревакцинации."""

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="vaccinations", verbose_name="животное")
    vaccine = models.CharField("вакцина", max_length=120)
    done_on = models.DateField("дата прививки")
    next_on = models.DateField("следующая прививка")
    batch = models.CharField("серия", max_length=30, blank=True)

    class Meta:
        verbose_name = "вакцинация"
        verbose_name_plural = "вакцинации"
        ordering = ["next_on"]

    def __str__(self):
        return f"{self.vaccine} — {self.animal.name}"

    def clean(self):
        if self.done_on and self.next_on and self.next_on <= self.done_on:
            raise ValidationError({"next_on": "Следующая прививка должна быть позже текущей"})

    @property
    def state(self):
        """overdue — просрочена, due — в ближайшие 14 дней, ok — в срок."""
        if self.next_on < date.today():
            return "overdue"
        if self.next_on <= date.today() + timedelta(days=14):
            return "due"
        return "ok"
