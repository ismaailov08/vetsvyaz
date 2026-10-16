from django.test import SimpleTestCase

from .services import assess


class TwinTests(SimpleTestCase):
    def test_normal_cow_is_ok(self):
        a = assess("cattle", {"temperature": 38.6, "heart_rate": 65, "activity": 350, "rumination": 30})
        self.assertEqual(a.level, "ok")
        self.assertEqual(a.flags, [])

    def test_fever_cow_is_alarm(self):
        a = assess("cattle", {"temperature": 40.8, "heart_rate": 96, "activity": 90, "rumination": 8})
        self.assertEqual(a.level, "alarm")
        self.assertEqual(len(a.flags), 4)
