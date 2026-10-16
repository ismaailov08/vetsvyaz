from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from accounts.permissions import visible_animals

from .services import animal_assessment, simulate


@login_required
def overview(request):
    animals = visible_animals(request.user).filter(sensor__isnull=False).select_related("sensor")
    rows = [(a, animal_assessment(a)) for a in animals]
    rows.sort(key=lambda x: -(x[1].risk if x[1] else 0))
    return render(request, "twin/overview.html", {"rows": rows})


@login_required
def detail(request, pk):
    animal = get_object_or_404(visible_animals(request.user).select_related("sensor"), pk=pk)
    readings = list(animal.sensor.readings.all()[:48])[::-1] if hasattr(animal, "sensor") else []
    chart = [{"t": r.taken_at.strftime("%d.%m %H:%M"), "temperature": float(r.temperature),
              "heart_rate": r.heart_rate, "activity": r.activity} for r in readings]
    mode = request.GET.get("mode", "none")
    return render(request, "twin/detail.html", {
        "animal": animal, "assessment": animal_assessment(animal), "chart": chart,
        "mode": mode, "forecast": simulate(animal, mode), "last": readings[-1] if readings else None})
