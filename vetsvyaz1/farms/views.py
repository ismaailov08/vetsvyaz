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


@login_required
def home(request):
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
