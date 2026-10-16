from django.test import TestCase
from django.urls import reverse

from farms.tests import make_world

from .services import notify


class NotificationTests(TestCase):
    def test_mark_all_read(self):
        w = make_world()
        notify(w.farmer.user, "Тест")
        self.client.force_login(w.farmer.user)
        self.assertContains(self.client.get(reverse("notifications:inbox")), "Тест")
        self.client.post(reverse("notifications:mark_all_read"))
        self.assertFalse(w.farmer.user.notifications.filter(is_read=False).exists())
