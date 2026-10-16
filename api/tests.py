from rest_framework.test import APITestCase

from farms.tests import make_world


class ApiTests(APITestCase):
    def test_farmer_sees_only_own_animals(self):
        w = make_world()
        self.client.force_authenticate(w.other_farmer.user)
        data = self.client.get("/api/animals/").json()
        self.assertEqual(data["count"], 0)
        self.client.force_authenticate(w.vet.user)
        self.assertEqual(self.client.get("/api/animals/").json()["count"], 1)

    def test_anonymous_gets_403(self):
        self.assertEqual(self.client.get("/api/animals/").status_code, 403)
