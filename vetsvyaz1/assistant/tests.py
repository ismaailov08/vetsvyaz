from django.test import SimpleTestCase, override_settings

from .services import ask, offline_triage


class AssistantTests(SimpleTestCase):
    def test_urgent_words(self):
        self.assertEqual(offline_triage("Корова не встаёт с утра")["urgency"], "СРОЧНО")

    @override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY="")
    def test_without_key_uses_rules(self):
        self.assertEqual(ask("у овцы понос")["source"], "offline")
