from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Farmer, User

from .models import Animal, Vaccination


def make_farmer(username="farmer"):
    u = User.objects.create_user(username, password="pass12345", role=User.Role.FARMER)
    return Farmer.objects.create(user=u, farm_name="КХ «Аксу»", district="Байзакский район")


class AnimalModelTests(TestCase):
    def setUp(self):
        self.farmer = make_farmer()

    def test_tag_format_is_validated(self):
        a = Animal(farmer=self.farmer, tag="KZ-123", name="Зорька", species="cattle", sex="F",
                   born=date(2021, 3, 14), weight_kg=480)
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_form_normalizes_tag(self):
        self.client.login(username="farmer", password="pass12345")
        r = self.client.post(reverse("farms:animal_create"), {"tag": "kz0217 4583", "name": "Зорька", "species": "cattle",
                             "breed": "Казахская белоголовая", "sex": "F", "born": "2021-03-14", "weight_kg": "480"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Animal.objects.filter(tag="KZ 0217 4583").exists())

    def test_form_rejects_bad_weight_and_future_date(self):
        from .forms import AnimalForm
        f = AnimalForm(data={"tag": "KZ 0217 4583", "name": "Зорька", "species": "cattle", "sex": "F",
                             "born": date.today() + timedelta(days=5), "weight_kg": "2000"})
        self.assertFalse(f.is_valid())
        self.assertIn("weight_kg", f.errors)
        self.assertIn("born", f.errors)

    def test_vaccination_state(self):
        a = Animal.objects.create(farmer=self.farmer, tag="KZ 0217 4583", name="Зорька", species="cattle",
                                  sex="F", born=date(2021, 3, 14), weight_kg=480)
        v = Vaccination.objects.create(animal=a, vaccine="Ящур", done_on=date.today() - timedelta(days=180),
                                       next_on=date.today() - timedelta(days=2))
        self.assertEqual(v.state, "overdue")


class AnimalAccessTests(TestCase):
    def test_farmer_cannot_open_foreign_animal(self):
        mine, other = make_farmer("farmer"), make_farmer("other")
        a = Animal.objects.create(farmer=other, tag="KZ 0519 2214", name="Ночка", species="cattle",
                                  sex="F", born=date(2020, 12, 1), weight_kg=560)
        self.client.login(username="farmer", password="pass12345")
        r = self.client.get(reverse("farms:animal_detail", args=[a.pk]))
        self.assertEqual(r.status_code, 404)


class AnimalDeleteTests(TestCase):
    """CRUD: удаление животного."""

    def setUp(self):
        self.farmer, self.other = make_farmer("farmer"), make_farmer("other")
        self.cow = Animal.objects.create(farmer=self.farmer, tag="KZ 0217 4583", name="Зорька", species="cattle",
                                         sex="F", born=date(2021, 3, 1), weight_kg=480)
        Vaccination.objects.create(animal=self.cow, vaccine="Ящур", done_on=date.today(),
                                   next_on=date.today() + timedelta(days=180))

    def test_owner_sees_confirmation_and_deletes(self):
        self.client.login(username="farmer", password="pass12345")
        url = reverse("farms:animal_delete", args=[self.cow.pk])
        self.assertContains(self.client.get(url), "Удалить животное?")
        r = self.client.post(url)
        self.assertRedirects(r, reverse("farms:animal_list"))
        self.assertFalse(Animal.objects.filter(pk=self.cow.pk).exists())
        self.assertFalse(Vaccination.objects.filter(animal_id=self.cow.pk).exists())  # каскадное удаление

    def test_other_farmer_cannot_delete(self):
        self.client.login(username="other", password="pass12345")
        r = self.client.post(reverse("farms:animal_delete", args=[self.cow.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Animal.objects.filter(pk=self.cow.pk).exists())

    def test_guest_is_sent_to_login(self):
        r = self.client.post(reverse("farms:animal_delete", args=[self.cow.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
        self.assertTrue(Animal.objects.filter(pk=self.cow.pk).exists())


def make_world():
    """Общие тестовые данные: два фермера, врач и корова первого фермера."""
    from types import SimpleNamespace

    from accounts.models import Vet
    farmer, other = make_farmer("farmer"), make_farmer("other")
    vu = User.objects.create_user("vet", password="pass12345", role=User.Role.VET, first_name="Арман",
                                  last_name="Жумабеков")
    vet = Vet.objects.create(user=vu, specialization="Крупный рогатый скот", license="ВЕТ-0412")
    cow = Animal.objects.create(farmer=farmer, tag="KZ 0217 4583", name="Зорька", species="cattle",
                                sex="F", born=date(2021, 3, 14), weight_kg=480)
    return SimpleNamespace(farmer=farmer, other_farmer=other, vet=vet, cow=cow)
