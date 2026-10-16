from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from accounts.models import Vet
from farms.models import Animal

from .models import Consultation, Prescription


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%dT%H:%M", **kwargs)


class ConsultationForm(forms.ModelForm):
    """Форма записи к врачу (открывается во всплывающем окне)."""

    class Meta:
        model = Consultation
        fields = ["animal", "vet", "kind", "scheduled_at", "complaint"]
        widgets = {"scheduled_at": DateTimeInput(),
                   "complaint": forms.Textarea(attrs={"rows": 3, "placeholder": "Что беспокоит, с какого дня"})}

    def __init__(self, *args, farmer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.farmer = farmer
        if farmer is not None:
            self.fields["animal"].queryset = Animal.objects.filter(farmer=farmer)
        self.fields["vet"].queryset = Vet.objects.select_related("user")

    def clean_scheduled_at(self):
        value = self.cleaned_data["scheduled_at"]
        if value <= timezone.now():
            raise forms.ValidationError("Выберите время в будущем")
        if not 8 <= timezone.localtime(value).hour < 20:
            raise forms.ValidationError("Врачи принимают с 08:00 до 20:00")
        return value

    def clean(self):
        data = super().clean()
        vet, at = data.get("vet"), data.get("scheduled_at")
        if vet and at and Consultation.objects.filter(vet=vet, scheduled_at=at,
                                                      status=Consultation.Status.SCHEDULED).exists():
            raise forms.ValidationError("У врача уже есть запись на это время")
        return data


class ConclusionForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ["diagnosis", "conclusion"]
        widgets = {"conclusion": forms.Textarea(attrs={"rows": 5})}

    def clean_diagnosis(self):
        d = self.cleaned_data["diagnosis"].strip()
        if not d:
            raise forms.ValidationError("Укажите диагноз")
        return d


PrescriptionFormSet = inlineformset_factory(
    Consultation, Prescription,
    fields=["drug", "dose", "days", "withdrawal_days"],
    extra=1, can_delete=True,
)
