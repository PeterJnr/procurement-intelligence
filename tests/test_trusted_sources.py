import unittest

from app.services.trusted_sources import append_trusted_sources, trusted_sources_for


class TrustedSourceTests(unittest.TestCase):
    def test_weather_question_returns_curated_weather_sources(self) -> None:
        sources = trusted_sources_for("What is the weather in Nigeria today?")

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].url, "https://nimet.gov.ng/")

    def test_unmatched_topic_does_not_add_arbitrary_sources(self) -> None:
        self.assertEqual(trusted_sources_for("Help me plan a birthday"), ())

    def test_sources_are_appended_as_markdown_links(self) -> None:
        result = append_trusted_sources(
            "I do not have live weather data.",
            "Will it rain in Lagos?",
        )

        self.assertIn("**Trusted places to check:**", result)
        self.assertIn("[Nigerian Meteorological Agency", result)


if __name__ == "__main__":
    unittest.main()
