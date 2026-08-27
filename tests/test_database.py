import unittest

from app.database import normalize_database_url


class DatabaseConfigurationTests(unittest.TestCase):
    def test_render_postgresql_url_uses_psycopg_v3(self) -> None:
        self.assertEqual(
            normalize_database_url("postgresql://user:password@host/database"),
            "postgresql+psycopg://user:password@host/database",
        )

    def test_legacy_postgres_url_uses_psycopg_v3(self) -> None:
        self.assertEqual(
            normalize_database_url("postgres://user:password@host/database"),
            "postgresql+psycopg://user:password@host/database",
        )

    def test_explicit_driver_url_is_unchanged(self) -> None:
        url = "postgresql+psycopg://user:password@host/database"
        self.assertEqual(normalize_database_url(url), url)


if __name__ == "__main__":
    unittest.main()
