from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Farmer, User


class RegisterForm(UserCreationForm):
    """Регистрация фермера: создаёт пользователя и профиль хозяйства."""

    first_name = forms.CharField(label="Имя", max_length=150)
    last_name = forms.CharField(label="Фамилия", max_length=150)
    phone = forms.RegexField(label="Телефон", regex=r"^\+7\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$",
                             error_messages={"invalid": "Формат: +7 700 000 00 00"})
    farm_name = forms.CharField(label="Название хозяйства", max_length=120)
    district = forms.CharField(label="Район", max_length=160)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.FARMER
        user.phone = self.cleaned_data["phone"]
        if commit:
            user.save()
            Farmer.objects.create(user=user, farm_name=self.cleaned_data["farm_name"],
                                  district=self.cleaned_data["district"])
        return user
