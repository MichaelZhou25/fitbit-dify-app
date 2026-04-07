from __future__ import annotations

import unittest

from app.core.config import Settings
from app.db.session import build_engine, engine_kwargs_for_database_url


class DatabaseSessionConfigTest(unittest.TestCase):
    def test_sqlite_engine_kwargs_enable_check_same_thread(self) -> None:
        kwargs = engine_kwargs_for_database_url("sqlite:///./app.db")

        self.assertEqual(kwargs, {"connect_args": {"check_same_thread": False}})

    def test_postgresql_engine_kwargs_enable_pool_health_checks(self) -> None:
        kwargs = engine_kwargs_for_database_url(
            "postgresql://postgres.abc123:password@aws-0.pooler.supabase.com:6543/postgres"
        )

        self.assertEqual(
            kwargs,
            {
                "pool_pre_ping": True,
                "pool_recycle": 1800,
            },
        )

    def test_build_engine_uses_psycopg_driver_for_postgresql_urls(self) -> None:
        settings = Settings(
            _env_file=None,
            database_url=(
                "postgresql://postgres.abc123:"
                "password@aws-0.pooler.supabase.com:6543/postgres"
            ),
        )

        engine = build_engine(settings.resolved_database_url)

        self.assertEqual(engine.url.drivername, "postgresql+psycopg")


if __name__ == "__main__":
    unittest.main()
