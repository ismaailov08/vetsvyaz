"""Цифровой двойник: сравнение показаний с нормой вида и прогноз «что если»."""
from dataclasses import dataclass, field

# нормы для взрослого животного: (мин, макс)
NORMS = {
    "cattle": {"temperature": (37.5, 39.5), "heart_rate": (50, 80), "activity": (180, 600), "rumination": (20, 40)},
    "sheep":  {"temperature": (38.5, 40.0), "heart_rate": (70, 90), "activity": (150, 500), "rumination": (15, 35)},
    "goat":   {"temperature": (38.5, 40.0), "heart_rate": (70, 90), "activity": (150, 550), "rumination": (15, 35)},
    "horse":  {"temperature": (37.5, 38.5), "heart_rate": (28, 44), "activity": (250, 900), "rumination": (0, 60)},
    "camel":  {"temperature": (36.0, 38.6), "heart_rate": (40, 50), "activity": (150, 600), "rumination": (20, 40)},
}
LABELS = {"temperature": "Температура", "heart_rate": "Пульс", "activity": "Активность", "rumination": "Жвачка"}
WEIGHTS = {"temperature": 40, "heart_rate": 25, "activity": 20, "rumination": 15}


@dataclass
class Assessment:
    risk: int                      # 0–100
    flags: list = field(default_factory=list)

    @property
    def level(self):
        return "alarm" if self.risk >= 60 else "watch" if self.risk >= 25 else "ok"

    @property
    def label(self):
        return {"alarm": "Тревога", "watch": "Наблюдение", "ok": "Норма"}[self.level]


def assess(species, values):
    """values — словарь показаний. Возвращает риск и список отклонений."""
    norms = NORMS.get(species, NORMS["cattle"])
    risk, flags = 0, []
    for key, (lo, hi) in norms.items():
        v = float(values[key])
        if lo <= v <= hi:
            continue
        span = hi - lo or 1
        dev = (lo - v) / span if v < lo else (v - hi) / span
        part = min(WEIGHTS[key], round(WEIGHTS[key] * (0.5 + dev * 2)))
        risk += part
        flags.append(f"{LABELS[key]} {'ниже' if v < lo else 'выше'} нормы: {v:g} (норма {lo:g}–{hi:g})")
    return Assessment(min(risk, 100), flags)


def _values(r):
    return {"temperature": r.temperature, "heart_rate": r.heart_rate,
            "activity": r.activity, "rumination": r.rumination}


def animal_assessment(animal):
    """Оценка по последнему показанию датчика; None, если датчика нет."""
    sensor = getattr(animal, "sensor", None)
    if sensor is None:
        return None
    last = sensor.readings.first()
    return assess(animal.species, _values(last)) if last else None


def simulate(animal, mode="none", hours=24):
    """Прогноз на сутки: mode='none' — без лечения, 'now' — лечение начато сейчас."""
    sensor = getattr(animal, "sensor", None)
    last = sensor.readings.first() if sensor else None
    if last is None:
        return []
    norms = NORMS.get(animal.species, NORMS["cattle"])
    cur = {k: float(v) for k, v in _values(last).items()}
    mid = {k: (lo + hi) / 2 for k, (lo, hi) in norms.items()}
    sick = assess(animal.species, cur).level != "ok"
    points = []
    for h in range(1, hours + 1):
        for k in cur:
            if mode == "now":            # лечение: каждые сутки возврат к норме ~на 60 %
                cur[k] += (mid[k] - cur[k]) * 0.04
            elif sick:                   # без лечения болезнь развивается
                drift = {"temperature": 0.03, "heart_rate": 0.4, "activity": -6, "rumination": -0.4}[k]
                cur[k] = max(0, cur[k] + drift)
        a = assess(animal.species, cur)
        points.append({"h": h, "temperature": round(cur["temperature"], 1), "risk": a.risk})
    return points
