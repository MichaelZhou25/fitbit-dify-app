from __future__ import annotations

import io
import os
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.deps import get_db
from app.main import app
from app.models.base import Base
from app.models.raw_segment import RawSegment
from app.schemas.user import UserCreateRequest
from app.services.user_service import create_user


class ApiExtensionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False, class_=Session)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.engine.dispose()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_get_user_by_external_id_endpoint(self) -> None:
        with self.SessionLocal() as db:
            user = create_user(
                db=db,
                payload=UserCreateRequest(
                    external_user_id="fitbit_demo_user",
                    name="Demo User",
                    timezone="Asia/Shanghai",
                ),
            )

        response = self.client.get(f"/api/v1/users/by-external-id/{user.external_user_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], user.id)
        self.assertEqual(payload["external_user_id"], "fitbit_demo_user")

    def test_bootstrap_profile_endpoint(self) -> None:
        with self.SessionLocal() as db:
            user = create_user(
                db=db,
                payload=UserCreateRequest(
                    external_user_id="fitbit_bootstrap_user",
                    name="Bootstrap User",
                    timezone="Asia/Shanghai",
                ),
            )
            base = datetime(2026, 4, 4, 8, 0, 0)
            db.add_all(
                [
                    RawSegment(
                        user_id=user.id,
                        segment_start=base,
                        segment_end=base + timedelta(hours=1),
                        granularity="1h",
                        source_type="fitbit_export",
                        raw_payload_json={
                            "steps": 800,
                            "calories": 90,
                            "sleep_minutes": 0,
                            "active_minutes": 25,
                            "sedentary_minutes": 35,
                            "heart_rate_series": [60, 62, 64],
                        },
                    ),
                    RawSegment(
                        user_id=user.id,
                        segment_start=base + timedelta(days=1),
                        segment_end=base + timedelta(days=1, hours=1),
                        granularity="1h",
                        source_type="fitbit_export",
                        raw_payload_json={
                            "steps": 320,
                            "calories": 55,
                            "sleep_minutes": 420,
                            "active_minutes": 10,
                            "sedentary_minutes": 20,
                            "heart_rate_series": [58, 60],
                        },
                    ),
                ]
            )
            db.commit()
            user_id = user.id

        response = self.client.post(f"/api/v1/users/{user_id}/bootstrap-profile")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile_json"]["source"], "fitbit_export")
        self.assertIn("daily_steps_goal", payload["goals_json"])
        self.assertTrue(payload["system_prompt_prefix"])

    def test_import_fitbit_endpoint_accepts_zip_upload(self) -> None:
        archive_bytes = self._build_fitbit_zip()

        response = self.client.post(
            "/api/v1/imports/fitbit",
            files={"archive": ("fitbit-export.zip", archive_bytes, "application/zip")},
            data={
                "external_user_id": "fitbit_api_import_user",
                "timezone": "Asia/Shanghai",
                "name": "Imported User",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["mode"], "fitbit_export")
        self.assertEqual(payload["generated_segments"], 2)
        self.assertEqual(payload["inserted_segments"], 2)
        self.assertEqual(payload["affected_external_user_ids"], ["fitbit_api_import_user"])

    @staticmethod
    def _build_fitbit_zip() -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "steps.csv",
                "\n".join(
                    [
                        "date,time,steps",
                        "2026-04-04,08:00:00,120",
                        "2026-04-04,08:01:00,30",
                        "2026-04-04,09:00:00,50",
                    ]
                ),
            )
            archive.writestr(
                "heart_rate-2026-04-04.json",
                (
                    '{"activities-heart": [{"dateTime": "2026-04-04"}], '
                    '"activities-heart-intraday": {"dataset": ['
                    '{"time": "08:00:00", "value": 80}, '
                    '{"time": "09:00:00", "value": 78}'
                    "]}}"
                ),
            )
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
