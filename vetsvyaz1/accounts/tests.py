from django.test import TestCase
from django.urls import reverse

from .models import Farmer, User


class RegisterTests(TestCase):
    def test_register_creates_farmer_profile(self):
        r = self.client.post(reverse("accounts:register"), {
            "username": "aidar", "first_name": "Айдар", "last_name": "Сейтов", "phone": "+7 701 555 12 34",
            "farm_name": "КХ «Береке»", "district": "Байзакский район",
            "password1": "Sapa-Kz-2026", "password2": "Sapa-Kz-2026"})
        self.assertRedirects(r, reverse("farms:home"))
        user = User.objects.get(username="aidar")
        self.assertEqual(user.role, User.Role.FARMER)
        self.assertTrue(Farmer.objects.filter(user=user, farm_name="КХ «Береке»").exists())

    def test_register_rejects_bad_phone(self):
        r = self.client.post(reverse("accounts:register"), {"username": "x", "first_name": "a", "last_name": "b",
            "phone": "12345", "farm_name": "f", "district": "d", "password1": "Sapa-Kz-2026", "password2": "Sapa-Kz-2026"})
        self.assertContains(r, "Формат: +7 700 000 00 00")
