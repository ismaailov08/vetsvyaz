from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from accounts.permissions import visible_animals
from farms.models import Animal

from .services import NORMS, assess, simulate

LEVELS = [("alarm", "Тревога"), ("watch", "Наблюдение"), ("ok", "Норма")]
METRICS = [("temperature", "Температура", "°C", "#c0473b"), ("heart_rate", "Пульс", "уд/мин", "#3a5f8f"),
           ("activity", "Активность", "шагов/ч", "#3f7d5c"), ("rumination", "Жвачка", "мин/ч", "#c98a1b")]


def _values(r):
    return {"temperature": r.temperature, "heart_rate": r.heart_rate, "activity": r.activity,
            "rumination": r.rumination}


@login_required
def overview(request):
    """Двойник стада: все животные с датчиками, последние показания и риск, с фильтрами."""
    animals = (visible_animals(request.user).filter(sensor__isnull=False)
               .select_related("sensor", "farmer"))
    q, species, level = request.GET.get("q", "").strip(), request.GET.get("species", ""), request.GET.get("level", "")
    if q:
        animals = animals.filter(Q(name__icontains=q) | Q(tag__icontains=q) | Q(farmer__farm_name__icontains=q))
    if species:
        animals = animals.filter(species=species)
    rows, counts = [], {"alarm": 0, "watch": 0, "ok": 0}
    for a in animals:
        last = a.sensor.readings.first()
        if last is None:
            continue
        s = assess(a.species, _values(last))
        counts[s.level] += 1
        if not level or s.level == level:
            rows.append((a, s, last))
    rows.sort(key=lambda x: (-x[1].risk, x[0].name))
    page = Paginator(rows, 48).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "twin/overview.html", {
        "page": page, "counts": counts, "total": sum(counts.values()), "levels": LEVELS,
        "species_choices": Animal.Species.choices, "params": params.urlencode()})


@login_required
def detail(request, pk):
    """Двойник одного животного: 4 графика за выбранный период, таблица показаний, прогноз."""
    animal = get_object_or_404(visible_animals(request.user).select_related("sensor", "farmer"), pk=pk)
    sensor = getattr(animal, "sensor", None)
    hours = request.GET.get("hours", "48")
    hours = int(hours) if hours in ("24", "48", "168") else 48
    readings = list(sensor.readings.all()[:hours])[::-1] if sensor else []
    norms = NORMS.get(animal.species, NORMS["cattle"])
    last = readings[-1] if readings else None
    assessment = assess(animal.species, _values(last)) if last else None
    charts = []
    for key, label, unit, color in METRICS:
        vals = [float(getattr(r, key)) for r in readings]
        lo, hi = norms[key]
        charts.append({"key": key, "label": label, "unit": unit, "color": color, "lo": lo, "hi": hi,
                       "values": vals, "min": min(vals) if vals else 0, "max": max(vals) if vals else 0,
                       "avg": round(sum(vals) / len(vals), 1) if vals else 0,
                       "now": vals[-1] if vals else None, "bad": bool(vals) and not lo <= vals[-1] <= hi})
    table = []
    for r in readings[::-1][:24]:
        cells = []
        for key, *_ in METRICS:
            v = float(getattr(r, key))
            lo, hi = norms[key]
            cells.append((v if key == "temperature" else int(v), not lo <= v <= hi))
        table.append((r.taken_at, cells))
    mode = request.GET.get("mode", "none")
    return render(request, "twin/detail.html", {
        "animal": animal, "sensor": sensor, "assessment": assessment, "charts": charts, "table": table,
        "hours": hours, "mode": mode, "forecast": simulate(animal, mode), "last": last,
        "total_readings": sensor.readings.count() if sensor else 0,
        "labels": [r.taken_at.strftime("%d.%m %H:%M") for r in readings]})
