from datetime import date

from django import forms

from .models import Animal, Vaccination


class DateInput(forms.DateInput):
    """Поле <input type="date">. Браузер принимает дату только в формате ГГГГ-ММ-ДД,
    иначе при изменении записи поле оказывается пустым."""
    input_type = "date"

    def __init__(self, attrs=None, format="%Y-%m-%d"):
        super().__init__(attrs, format=format)


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

    def clean_photo(self):
        """Фото: не больше 5 МБ и только JPG, PNG или WEBP."""
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size"):
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Фото больше 5 МБ – уменьшите размер")
            if not photo.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                raise forms.ValidationError("Загрузите фото в формате JPG, PNG или WEBP")
        return photo

    def clean_weight_kg(self):
        w = self.cleaned_data["weight_kg"]
        if w is not None and not (1 <= w <= 1500):
            raise forms.ValidationError("Вес должен быть от 1 до 1500 кг")
        return w

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
