from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import User
from accounts.permissions import RoleRequiredMixin, visible_animals, visible_consultations
from consultations.models import Consultation
from twin.services import animal_assessment

from .forms import AnimalForm, VaccinationForm
from .models import Animal, Vaccination


def landing(request):
    """Страница для гостя: что умеет система, общие цифры, врачи, вход и регистрация."""
    from accounts.models import Farmer, Vet
    stats = {"farms": Farmer.objects.count(), "animals": Animal.objects.count(),
             "vets": Vet.objects.count(),
             "cases": Consultation.objects.filter(status=Consultation.Status.DONE).count()}
    vets = Vet.objects.select_related("user").annotate(n=Count("farms"))
    return render(request, "farms/landing.html", {"stats": stats, "vets": vets})


def home(request):
    if not request.user.is_authenticated:
        return landing(request)
    return _home(request)


@login_required
def _home(request):
    """Главная страница: сводка для текущей роли."""
    animals = visible_animals(request.user)
    upcoming = visible_consultations(request.user).filter(status=Consultation.Status.SCHEDULED,
                                                          scheduled_at__gte=timezone.now())[:5]
    vaccinations = Vaccination.objects.filter(animal__in=animals).select_related("animal")[:6]
    alerts = [(a, animal_assessment(a)) for a in animals.select_related("sensor")]
    alerts = [x for x in alerts if x[1] and x[1].level != "ok"]
    stats = animals.aggregate(total=Count("id"), sick=Count("id", filter=~Q(status=Animal.Status.HEALTHY)))
    return render(request, "farms/home.html", {"stats": stats, "upcoming": upcoming,
                                               "vaccinations": vaccinations, "alerts": alerts})


class AnimalListView(RoleRequiredMixin, ListView):
    template_name = "farms/animal_list.html"
    context_object_name = "animals"
    paginate_by = 12

    def get_queryset(self):
        qs = visible_animals(self.request.user).select_related("farmer")
        q = self.request.GET.get("q", "").strip()
        species = self.request.GET.get("species", "")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(tag__icontains=q) | Q(breed__icontains=q))
        if species:
            qs = qs.filter(species=species)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["species_choices"] = Animal.Species.choices
        return ctx


class AnimalDetailView(RoleRequiredMixin, DetailView):
    template_name = "farms/animal_detail.html"
    context_object_name = "animal"

    def get_queryset(self):
        return visible_animals(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        a = self.object
        ctx["history"] = a.consultations.filter(status=Consultation.Status.DONE).prefetch_related("prescriptions")
        ctx["vaccinations"] = a.vaccinations.all()
        ctx["vaccination_form"] = VaccinationForm()
        ctx["assessment"] = animal_assessment(a)
        if self.request.user.is_farmer:
            from consultations.forms import ConsultationForm
            ctx["book_form"] = ConsultationForm(farmer=self.request.user.farmer, initial={"animal": a})
        return ctx


class AnimalCreateView(RoleRequiredMixin, CreateView):
    roles = (User.Role.FARMER,)
    form_class = AnimalForm
    template_name = "farms/animal_form.html"

    def form_valid(self, form):
        form.instance.farmer = self.request.user.farmer
        messages.success(self.request, f"Животное {form.instance.tag} добавлено")
        return super().form_valid(form)


class AnimalUpdateView(RoleRequiredMixin, UpdateView):
    roles = (User.Role.FARMER,)
    form_class = AnimalForm
    template_name = "farms/animal_form.html"

    def get_queryset(self):
        return visible_animals(self.request.user)


@login_required
@require_POST
def add_vaccination(request, pk):
    """Врач отмечает прививку из всплывающего окна на карточке животного."""
    if not (request.user.is_vet or request.user.is_district_admin):
        messages.error(request, "Отмечать прививки может только ветврач")
        return redirect("farms:animal_detail", pk=pk)
    animal = get_object_or_404(Animal, pk=pk)
    form = VaccinationForm(request.POST)
    if form.is_valid():
        v = form.save(commit=False)
        v.animal = animal
        v.full_clean()
        v.save()
        messages.success(request, f"Прививка «{v.vaccine}» внесена, напоминание — {v.next_on:%d.%m.%Y}")
    else:
        messages.error(request, "Проверьте даты прививки: " + "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect("farms:animal_detail", pk=pk)


@login_required
def disease_log(request):
    """Журнал болезней: кто болеет сейчас и вся история диагнозов."""
    animals = visible_animals(request.user)
    # фермер видит историю только своего хозяйства, врач и администратор — всех хозяйств
    cases = Consultation.objects.filter(animal__in=animals, status=Consultation.Status.DONE)
    history = (cases
               .select_related("animal", "farmer__user", "vet__user").prefetch_related("prescriptions"))
    q = request.GET.get("q", "").strip()
    species = request.GET.get("species", "")
    if q:
        history = history.filter(Q(animal__name__icontains=q) | Q(animal__tag__icontains=q) |
                                 Q(diagnosis__icontains=q) | Q(farmer__farm_name__icontains=q))
    if species:
        history = history.filter(animal__species=species)
    history = history.order_by("-scheduled_at")

    # кто болеет сейчас: животные на лечении или в карантине + их последний диагноз
    sick = []
    for a in animals.exclude(status=Animal.Status.HEALTHY).select_related("farmer__user").order_by("status", "name"):
        last = a.consultations.filter(status=Consultation.Status.DONE).order_by("-scheduled_at").first()
        sick.append((a, last))

    top = (cases.values("diagnosis").annotate(n=Count("id")).order_by("-n", "diagnosis")[:6])
    stats = {
        "animals": animals.count(),
        "treatment": animals.filter(status=Animal.Status.TREATMENT).count(),
        "quarantine": animals.filter(status=Animal.Status.QUARANTINE).count(),
        "cases": cases.count(),
    }
    return render(request, "farms/disease_log.html", {
        "sick": sick, "history": history, "top": top, "stats": stats,
        "species_choices": Animal.Species.choices})


SPECIES_KEYS = [s for s, _ in Animal.Species.choices]


def _herd_counts():
    """Аннотации: сколько животных каждого вида и сколько больных в хозяйстве."""
    counts = {"total": Count("animals"),
              "sick": Count("animals", filter=~Q(animals__status=Animal.Status.HEALTHY))}
    for sp in SPECIES_KEYS:
        counts[sp] = Count("animals", filter=Q(animals__species=sp))
    return counts


def _visible_farms(user):
    from accounts.models import Farmer
    qs = Farmer.objects.select_related("user")
    return qs.filter(user=user) if user.is_farmer else qs


def _split_district(text):
    """«Байзакский район, Жамбылская обл.» -> («Жамбылская обл.», «Байзакский район»)."""
    parts = [x.strip() for x in text.split(",", 1)]
    return (parts[1], parts[0]) if len(parts) == 2 else ("Без области", parts[0])


def _new_group(name):
    return {"name": name, "farms": [], "total": 0, "sick": 0,
            "species": {label: 0 for _, label in Animal.Species.choices}}


def _add_to_group(g, f):
    g["total"] += f.total
    g["sick"] += f.sick
    for sp, label in Animal.Species.choices:
        g["species"][label] += getattr(f, sp)


@login_required
def farm_list(request):
    """Хозяйства: область -> район -> хозяйства, с поголовьем по видам."""
    if request.user.is_farmer:
        return redirect("farms:farm_detail", pk=request.user.farmer.pk)
    farms = _visible_farms(request.user).annotate(**_herd_counts()).order_by("district", "farm_name")
    selected = request.GET.get("oblast", "")
    oblasts = {}
    for f in farms:
        oblast, district = _split_district(f.district)
        f.herd = [(label, getattr(f, sp)) for sp, label in Animal.Species.choices if getattr(f, sp)]
        o = oblasts.setdefault(oblast, dict(_new_group(oblast), districts={}))
        d = o["districts"].setdefault(district, _new_group(district))
        d["farms"].append(f)
        o["farms"].append(f)
        _add_to_group(d, f)
        _add_to_group(o, f)
    for o in oblasts.values():
        o["species"] = [(k, v) for k, v in o["species"].items() if v]
        o["districts"] = sorted(o["districts"].values(), key=lambda d: d["name"])
        for d in o["districts"]:
            d["species"] = [(k, v) for k, v in d["species"].items() if v]
    all_oblasts = sorted(oblasts.values(), key=lambda o: o["name"])
    shown = [o for o in all_oblasts if not selected or o["name"] == selected]
    totals = Animal.objects.aggregate(total=Count("id"),
                                      sick=Count("id", filter=~Q(status=Animal.Status.HEALTHY)))
    return render(request, "farms/farm_list.html", {
        "oblasts": shown, "all_oblasts": all_oblasts, "selected": selected,
        "district_count": sum(len(o["districts"]) for o in all_oblasts),
        "farm_count": farms.count(), "totals": totals})


@login_required
def farm_detail(request, pk):
    """Полная карточка хозяйства: владелец, поголовье, все животные, болезни, прививки."""
    farm = get_object_or_404(_visible_farms(request.user).annotate(**_herd_counts()), pk=pk)
    animals = farm.animals.all().order_by("species", "name")
    species = request.GET.get("species", "")
    if species:
        animals = animals.filter(species=species)
    rows = []
    for a in animals:
        last = a.consultations.filter(status=Consultation.Status.DONE).order_by("-scheduled_at").first()
        rows.append((a, last))
    herd = [(sp, label, getattr(farm, sp)) for sp, label in Animal.Species.choices if getattr(farm, sp)]
    cases = Consultation.objects.filter(farmer=farm, status=Consultation.Status.DONE) \
        .select_related("animal", "vet__user").order_by("-scheduled_at")[:10]
    vaccinations = Vaccination.objects.filter(animal__farmer=farm).select_related("animal").order_by("next_on")[:8]
    return render(request, "farms/farm_detail.html", {
        "farm": farm, "rows": rows, "herd": herd, "cases": cases, "vaccinations": vaccinations,
        "healthy": farm.total - farm.sick, "species": species, "vets": farm.vets.select_related("user")})
