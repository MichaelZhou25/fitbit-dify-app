from __future__ import annotations

import unittest

from app.core.config import BACKEND_DIR, REPO_ROOT, Settings


class ConfigResolutionTest(unittest.TestCase):
    def test_resolved_database_url_converts_relative_sqlite_path(self) -> None:
        settings = Settings(_env_file=None, database_url="sqlite:///./app.db")
        expected = f"sqlite:///{(BACKEND_DIR / 'app.db').resolve().as_posix()}"
        self.assertEqual(settings.resolved_database_url, expected)
        self.assertEqual(settings.database_backend, "sqlite")

    def test_resolved_database_url_normalizes_postgresql_url_for_psycopg(self) -> None:
        database_url = (
            "postgresql://postgres.abc123:"
            "password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        )
        settings = Settings(_env_file=None, database_url=database_url)

        self.assertEqual(
            settings.resolved_database_url,
            database_url.replace("postgresql://", "postgresql+psycopg://", 1),
        )
        self.assertEqual(settings.database_backend, "postgresql")

    def test_resolved_model_artifact_path_uses_repo_root_for_relative_path(self) -> None:
        settings = Settings(_env_file=None, model_artifact_path="./data/artifacts/fatigue_v1.json")
        expected = (REPO_ROOT / "data" / "artifacts" / "fatigue_v1.json").resolve()
        self.assertEqual(settings.resolved_model_artifact_path, expected)


if __name__ == "__main__":
    unittest.main()
