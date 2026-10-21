from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Farmer, User


class RegisterForm(UserCreationForm):
    """Регистрация фермера: создаёт пользователя и профиль хозяйства."""

    first_name = forms.CharField(label="Имя", max_length=150)
    last_name = forms.CharField(label="Фамилия", max_length=150)
    phone = forms.RegexField(label="Телефон", regex=r"^\+7\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$",
                             error_messages={"invalid": "Формат: +7 700 000 00 00"})
    email = forms.EmailField(label="Email", help_text="Например: farmer@mail.kz",
                             error_messages={"invalid": "Введите правильный адрес email"})
    farm_name = forms.CharField(label="Название хозяйства", max_length=120)
    district = forms.CharField(label="Район", max_length=160)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def clean_email(self):
        """Email обязателен, приводится к нижнему регистру и не должен повторяться."""
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.FARMER
        user.phone = self.cleaned_data["phone"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            Farmer.objects.create(user=user, farm_name=self.cleaned_data["farm_name"],
                                  district=self.cleaned_data["district"])
        return user
