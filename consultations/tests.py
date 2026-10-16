from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from farms.tests import make_world
from notifications.models import Notification

from .forms import ConsultationForm
from .models import Consultation


def tomorrow_at(hour):
    t = timezone.localtime() + timedelta(days=1)
    return t.replace(hour=hour, minute=0, second=0, microsecond=0)


class ConsultationTests(TestCase):
    def setUp(self):
        self.w = make_world()

    def book(self, hour=10):
        return Consultation.objects.create(farmer=self.w.farmer, vet=self.w.vet, animal=self.w.cow,
                                           scheduled_at=tomorrow_at(hour), complaint="Не ест")

    def test_one_slot_per_vet(self):
        self.book(10)
        with self.assertRaises(IntegrityError):
            self.book(10)

    def test_form_rejects_past_and_night(self):
        f = ConsultationForm(data={"animal": self.w.cow.pk, "vet": self.w.vet.pk, "kind": "video",
                                   "scheduled_at": tomorrow_at(23).strftime("%Y-%m-%dT%H:%M"),
                                   "complaint": "Хромает"}, farmer=self.w.farmer)
        self.assertFalse(f.is_valid())
        self.assertIn("scheduled_at", f.errors)

    def test_signal_notifies_vet(self):
        self.book(11)
        self.assertEqual(Notification.objects.filter(user=self.w.vet.user).count(), 1)

    def test_conclude_sets_done_and_treatment(self):
        c = self.book(12)
        self.client.force_login(self.w.vet.user)
        resp = self.client.post(reverse("consultations:conclude", args=[c.pk]), {
            "diagnosis": "Мастит", "conclusion": "Сдаивать каждые 3 часа",
            "prescriptions-TOTAL_FORMS": "1", "prescriptions-INITIAL_FORMS": "0",
            "prescriptions-MIN_NUM_FORMS": "0", "prescriptions-MAX_NUM_FORMS": "1000",
            "prescriptions-0-drug": "Мастиет форте", "prescriptions-0-dose": "1 шприц в долю",
            "prescriptions-0-days": "4", "prescriptions-0-withdrawal_days": "5"})
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db(); self.w.cow.refresh_from_db()
        self.assertEqual(c.status, "done")
        self.assertEqual(self.w.cow.status, "treatment")
        self.assertTrue(Notification.objects.filter(user=self.w.farmer.user).exists())

    def test_farmer_cannot_conclude(self):
        c = self.book(13)
        self.client.force_login(self.w.farmer.user)
        self.client.post(reverse("consultations:conclude", args=[c.pk]), {"diagnosis": "x"})
        c.refresh_from_db()
        self.assertEqual(c.status, "scheduled")
