from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from accounts.models import User
from accounts.permissions import RoleRequiredMixin, visible_consultations
from farms.models import Animal

from .forms import ConclusionForm, ConsultationForm, PrescriptionFormSet
from .models import Consultation


class ConsultationListView(RoleRequiredMixin, ListView):
    template_name = "consultations/list.html"
    context_object_name = "consultations"
    paginate_by = 15

    def get_queryset(self):
        qs = visible_consultations(self.request.user).select_related("animal", "vet__user", "farmer__user")
        status = self.request.GET.get("status")
        return qs.filter(status=status) if status else qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Consultation.Status.choices
        if self.request.user.is_farmer:
            ctx["form"] = ConsultationForm(farmer=self.request.user.farmer)
        return ctx


class ConsultationDetailView(RoleRequiredMixin, DetailView):
    template_name = "consultations/detail.html"
    context_object_name = "c"

    def get_queryset(self):
        return visible_consultations(self.request.user).prefetch_related("prescriptions")


@login_required
@require_POST
def create(request):
    """Фермер отправляет форму из всплывающего окна «Записаться к врачу»."""
    if not request.user.is_farmer:
        messages.error(request, "Записываться может только фермер")
        return redirect("consultations:list")
    form = ConsultationForm(request.POST, farmer=request.user.farmer)
    if form.is_valid():
        c = form.save(commit=False)
        c.farmer = request.user.farmer
        c.save()
        messages.success(request, f"Вы записаны: {c.vet} — {timezone.localtime(c.scheduled_at):%d.%m.%Y %H:%M}")
        return redirect(c)
    messages.error(request, "Запись не создана: " + "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect(request.POST.get("next") or "consultations:list")


@login_required
@require_POST
def cancel(request, pk):
    c = get_object_or_404(visible_consultations(request.user), pk=pk, status=Consultation.Status.SCHEDULED)
    c.status = Consultation.Status.CANCELLED
    c.save(update_fields=["status"])
    messages.info(request, "Консультация отменена")
    return redirect("consultations:list")


@login_required
def conclude(request, pk):
    """Врач пишет заключение и назначения (формы + набор форм)."""
    if not (request.user.is_vet or request.user.is_superuser):
        messages.error(request, "Заключение пишет только ветврач")
        return redirect("consultations:detail", pk=pk)
    c = get_object_or_404(visible_consultations(request.user), pk=pk)
    form = ConclusionForm(request.POST or None, instance=c)
    formset = PrescriptionFormSet(request.POST or None, instance=c)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            c = form.save(commit=False)
            c.status = Consultation.Status.DONE
            c.save()
            formset.save()
            if c.prescriptions.exists():
                Animal.objects.filter(pk=c.animal_id).update(status=Animal.Status.TREATMENT)
        messages.success(request, "Заключение сохранено, фермер получил уведомление")
        return redirect(c)
    return render(request, "consultations/conclude.html", {"c": c, "form": form, "formset": formset})


@login_required
def call(request, pk):
    """Комната видеоконсультации."""
    c = get_object_or_404(visible_consultations(request.user), pk=pk)
    return render(request, "consultations/call.html", {"c": c})


@login_required
def report(request, pk):
    """Печатная форма заключения."""
    c = get_object_or_404(visible_consultations(request.user).filter(status=Consultation.Status.DONE), pk=pk)
    return render(request, "consultations/report.html", {"c": c})
