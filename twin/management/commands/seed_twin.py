"""Команда: python manage.py seed_twin — ставит датчики всем животным и загружает показания за 7 дней.

Для каждого животного без датчика создаётся датчик (болюс у КРС, ошейник у остальных) и 168 часовых
показаний: температура, пульс, активность и жвачка. У здоровых животных показания колеблются вокруг
нормы вида с суточным ритмом, у больных — меняются по картине болезни из последнего диагноза.
"""
import math
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from farms.models import Animal
from twin.models import Reading, Sensor
from twin.services import NORMS

HOURS = 168  # 7 суток


def scenario(animal):
    """По последнему диагнозу выбираем, как болезнь меняет показания."""
    if animal.status == Animal.Status.HEALTHY:
        return "ok"
    last = animal.consultations.filter(status="done").order_by("-scheduled_at").first()
    d = (last.diagnosis if last else "").lower()
    if any(w in d for w in ("копыт", "пододерм", "колик")):
        return "lame"
    if any(w in d for w in ("диспепс", "эймер", "кетоз", "тимпан", "фасциол")):
        return "digest"
    if any(w in d for w in ("чесот", "саркопт", "трихоф", "кератит", "кератоконъ")):
        return "mild"
    return "fever"


class Command(BaseCommand):
    help = "Ставит датчики всем животным без датчика и загружает показания за 7 дней"

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        animals = Animal.objects.filter(sensor__isnull=True)
        made, rows_total = 0, 0
        for a in animals:
            rnd = random.Random(a.pk * 7919)
            s = Sensor.objects.create(animal=a, serial=f"VS-{5000 + a.pk}",
                                      installed=date.today() - timedelta(days=30 + a.pk % 200))
            norms = NORMS.get(a.species, NORMS["cattle"])
            mid = {k: (lo + hi) / 2 for k, (lo, hi) in norms.items()}
            sc = scenario(a)
            rows = []
            for h in range(HOURS, 0, -1):
                t = now - timedelta(hours=h)
                day = math.sin((t.hour - 9) / 24 * 2 * math.pi)        # суточный ритм: днём активнее
                k = max(0.0, 1 - h / 60)                                 # болезнь развивается за последние ~60 ч
                temp = mid["temperature"] + 0.25 * day + rnd.uniform(-0.15, 0.15)
                hr = mid["heart_rate"] + 3 * day + rnd.uniform(-3, 3)
                act = mid["activity"] * (1 + 0.45 * day) * rnd.uniform(0.85, 1.15)
                rum = mid["rumination"] * rnd.uniform(0.9, 1.1)
                if sc == "fever":
                    temp += 1.8 * k; hr *= 1 + 0.3 * k; act *= 1 - 0.5 * k; rum *= 1 - 0.5 * k
                elif sc == "lame":
                    act *= 1 - 0.65 * k; hr *= 1 + 0.1 * k
                elif sc == "digest":
                    temp += 0.7 * k; rum *= 1 - 0.65 * k; act *= 1 - 0.3 * k
                elif sc == "mild":
                    temp += 0.4 * k; act *= 1 - 0.2 * k
                rows.append(Reading(sensor=s, taken_at=t, temperature=round(temp, 1), heart_rate=max(1, round(hr)),
                                    activity=max(0, round(act)), rumination=max(0, round(rum))))
            Reading.objects.bulk_create(rows, batch_size=500)
            made += 1
            rows_total += len(rows)
        # у датчиков из seed_demo только 48 ч — дополняем более ранние часы нормальными показаниями до 7 суток
        filled = 0
        for s in Sensor.objects.select_related("animal"):
            n = s.readings.count()
            if n >= HOURS:
                continue
            first = s.readings.order_by("taken_at").first()
            start = first.taken_at if first else now
            norms = NORMS.get(s.animal.species, NORMS["cattle"])
            mid = {k: (lo + hi) / 2 for k, (lo, hi) in norms.items()}
            rnd = random.Random(s.pk * 104729)
            rows = []
            for h in range(1, HOURS - n + 1):
                t = start - timedelta(hours=h)
                day = math.sin((t.hour - 9) / 24 * 2 * math.pi)
                rows.append(Reading(sensor=s, taken_at=t,
                                    temperature=round(mid["temperature"] + 0.25 * day + rnd.uniform(-0.15, 0.15), 1),
                                    heart_rate=round(mid["heart_rate"] + 3 * day + rnd.uniform(-3, 3)),
                                    activity=max(0, round(mid["activity"] * (1 + 0.45 * day) * rnd.uniform(0.85, 1.15))),
                                    rumination=max(0, round(mid["rumination"] * rnd.uniform(0.9, 1.1)))))
            Reading.objects.bulk_create(rows, batch_size=500, ignore_conflicts=True)
            filled += len(rows)
        rows_total += filled
        self.stdout.write(self.style.SUCCESS(
            f"Готово: датчиков поставлено {made}, показаний загружено {rows_total}. "
            f"Всего датчиков: {Sensor.objects.count()}, показаний: {Reading.objects.count()}"))
