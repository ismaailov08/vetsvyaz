from datetime import date

from django import forms

from .models import Animal, Vaccination


class DateInput(forms.DateInput):
    input_type = "date"


class AnimalForm(forms.ModelForm):
    """Форма добавления и изменения животного."""

    class Meta:
        model = Animal
        fields = ["tag", "name", "species", "breed", "sex", "born", "weight_kg", "photo"]
        widgets = {"born": DateInput(), "tag": forms.TextInput(attrs={"placeholder": "KZ 0217 4610"})}
        help_texts = {"tag": "Номер с ушной бирки, формат KZ 0000 0000"}

    def clean_tag(self):
        tag = " ".join(self.cleaned_data["tag"].upper().split())
        if tag.startswith("KZ") and not tag.startswith("KZ "):
            tag = "KZ " + tag[2:].strip()
        return tag

    def clean_born(self):
        born = self.cleaned_data["born"]
        if born > date.today():
            raise forms.ValidationError("Дата рождения не может быть в будущем")
        return born


class VaccinationForm(forms.ModelForm):
    """Форма врача «Отметить вакцинацию» (открывается во всплывающем окне)."""

    class Meta:
        model = Vaccination
        fields = ["vaccine", "done_on", "next_on", "batch"]
        widgets = {"done_on": DateInput(), "next_on": DateInput()}
