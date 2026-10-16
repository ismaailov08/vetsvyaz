"""Команда: python manage.py seed_demo — заполняет базу демонстрационными данными."""
import math
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Farmer, User, Vet
from consultations.models import Consultation, Prescription
from farms.models import Animal, Vaccination
from twin.models import Reading, Sensor

PASSWORD = "vet12345"
ANIMALS = [  # кличка, бирка, вид, порода, пол, год, вес, сценарий датчика
    ("Зорька", "KZ 0217 4583", "cattle", "Казахская белоголовая", "F", 2021, 480, "mastitis"),
    ("Маржан", "KZ 0217 4591", "cattle", "Алатауская", "F", 2020, 510, "ok"),
    ("Батыр", "KZ 0308 1172", "cattle", "Казахская белоголовая", "M", 2019, 720, "lame"),
    ("Акбас", "KZ 0412 0081", "sheep", "Эдильбаевская", "M", 2022, 85, "ok"),
    ("Шустрик", "KZ 0412 0093", "sheep", "Казахская курдючная", "M", 2023, 52, "fever"),
    ("Тулпар", "KZ 0605 3307", "horse", "Кушумская", "M", 2018, 470, "ok"),
    ("Белка", "KZ 0519 2201", "goat", "Зааненская", "F", 2022, 58, "ok"),
    ("Ночка", "KZ 0519 2214", "cattle", "Голштинская", "F", 2020, 560, "ok"),
]
BASE = {"cattle": (38.6, 65, 360, 30), "sheep": (39.2, 80, 300, 25), "goat": (39.2, 80, 320, 25),
        "horse": (38.0, 36, 500, 30), "camel": (37.5, 45, 300, 30)}


class Command(BaseCommand):
    help = "Создаёт демо-пользователей, животных, датчики и консультации"

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(7)
        admin = User.objects.create_superuser("admin", "admin@vetsvyaz.kz", PASSWORD, role=User.Role.ADMIN,
                                              first_name="Гульнара", last_name="Ахметова")
        fu = User.objects.create_user("farmer", password=PASSWORD, role=User.Role.FARMER, first_name="Ерлан",
                                      last_name="Тулегенов", phone="+7 701 555 12 34")
        farmer = Farmer.objects.create(user=fu, farm_name="КХ «Аксу»", district="Байзакский район, Жамбылская обл.")
        vets = []
        for login, fn, ln, spec, lic in [("vet", "Арман", "Жумабеков", "Крупный рогатый скот", "ВЕТ-0412"),
                                         ("vet2", "Динара", "Касымова", "Мелкий рогатый скот", "ВЕТ-0577")]:
            u = User.objects.create_user(login, password=PASSWORD, role=User.Role.VET, first_name=fn, last_name=ln)
            vets.append(Vet.objects.create(user=u, specialization=spec, license=lic))

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        animals = {}
        for i, (name, tag, sp, breed, sex, year, kg, scenario) in enumerate(ANIMALS):
            a = Animal.objects.create(farmer=farmer, tag=tag, name=name, species=sp, breed=breed, sex=sex,
                                      born=date(year, 3 + i % 6, 10), weight_kg=kg)
            animals[name] = a
            Vaccination.objects.create(animal=a, vaccine="Ящур (ФМД)", done_on=date.today() - timedelta(days=170 - i * 9),
                                       next_on=date.today() + timedelta(days=12 - i * 3))
            s = Sensor.objects.create(animal=a, serial=f"VS-{2400 + i}", installed=date.today() - timedelta(days=60))
            t0, hr0, act0, rum0 = BASE[sp]
            rows = []
            for h in range(48, 0, -1):
                k = (48 - h) / 47  # 0 → 1 за двое суток
                day = math.sin((now.hour - h) / 24 * 2 * math.pi)
                t, hr, act, rum = t0 + 0.2 * day, hr0 + 3 * day, act0 * (1 + 0.4 * day), rum0
                if scenario == "mastitis":
                    t += 1.9 * k; hr += 24 * k; act *= 1 - 0.55 * k; rum -= 16 * k
                elif scenario == "fever":
                    t += 1.6 * k; hr += 14 * k; act *= 1 - 0.4 * k
                elif scenario == "lame":
                    act *= 1 - 0.7 * k
                rows.append(Reading(sensor=s, taken_at=now - timedelta(hours=h), temperature=round(t + random.uniform(-.1, .1), 1),
                                    heart_rate=round(hr), activity=max(0, round(act)), rumination=max(0, round(rum))))
            Reading.objects.bulk_create(rows)

        Consultation.objects.create(farmer=farmer, vet=vets[0], animal=animals["Зорька"], kind="video",
                                    scheduled_at=now + timedelta(days=1, hours=2),
                                    complaint="Уплотнение задней правой доли вымени, молоко с хлопьями, корова вялая")
        Consultation.objects.create(farmer=farmer, vet=vets[1], animal=animals["Шустрик"], kind="visit",
                                    scheduled_at=now + timedelta(days=2), complaint="Кашель, температура, плохо ест")
        done = Consultation.objects.create(farmer=farmer, vet=vets[0], animal=animals["Батыр"], kind="video",
                                           scheduled_at=now - timedelta(days=5), complaint="Хромает на левую переднюю",
                                           )
        done.status, done.diagnosis = "done", "Пододерматит, лёгкая форма"
        done.conclusion = "Расчистка копыта, ванночки с медным купоросом через день, сухая подстилка."
        done.save()
        Prescription.objects.create(consultation=done, drug="Тетрациклиновый спрей", dose="на копыто 2 раза в день",
                                    days=7, withdrawal_days=0)
        animals["Батыр"].status = Animal.Status.TREATMENT
        animals["Батыр"].save()
        self.stdout.write(self.style.SUCCESS(
            f"Готово: пользователи admin / farmer / vet / vet2 (пароль {PASSWORD}), "
            f"{Animal.objects.count()} животных, {Reading.objects.count()} показаний датчиков"))
