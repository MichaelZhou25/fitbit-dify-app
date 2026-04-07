from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
import unittest

from app.services.analysis_service import build_saved_analysis_response


class SavedAnalysisResponseTest(unittest.TestCase):
    def test_build_saved_analysis_response_extracts_outputs_and_model_output(self) -> None:
        run = SimpleNamespace(
            id="run_001",
            workflow_run_id="workflow_001",
            created_at=datetime(2026, 4, 4, 18, 0, 0),
            segment_id="segment_001",
            user_id="user_001",
            status="sent",
            dify_inputs_json={
                "inputs": {
                    "top_label": "fatigue_high",
                    "probability_json": '{"fatigue_low": 0.1, "fatigue_high": 0.9}',
                }
            },
            dify_outputs_json={
                "data": {
                    "outputs": {
                        "summary": "high fatigue",
                        "explanation": "explanation text",
                    }
                }
            },
        )

        response = build_saved_analysis_response(run)

        self.assertEqual(response.dify_run_id, "run_001")
        self.assertEqual(response.workflow_run_id, "workflow_001")
        self.assertEqual(response.model_output["top_label"], "fatigue_high")
        self.assertEqual(response.model_output["probabilities"]["fatigue_high"], 0.9)
        self.assertEqual(response.llm_output["summary"], "high fatigue")
        self.assertEqual(response.status, "sent")

    def test_build_saved_analysis_response_prefers_fallback_output_for_skipped_runs(self) -> None:
        run = SimpleNamespace(
            id="run_002",
            workflow_run_id=None,
            created_at=datetime(2026, 4, 4, 19, 0, 0),
            segment_id="segment_002",
            user_id="user_002",
            status="skipped",
            dify_inputs_json={
                "inputs": {
                    "top_label": "fatigue_low",
                    "probability_json": '{"fatigue_low": 0.7, "fatigue_high": 0.3}',
                }
            },
            dify_outputs_json={
                "message": "Dify API key is empty.",
                "fallback_output": {
                    "summary": "local fallback summary",
                    "explanation": "local fallback explanation",
                    "personalized_advice": ["sleep earlier"],
                },
            },
        )

        response = build_saved_analysis_response(run)

        self.assertEqual(response.status, "skipped")
        self.assertEqual(response.llm_output["summary"], "local fallback summary")
        self.assertEqual(response.llm_output["explanation"], "local fallback explanation")


if __name__ == "__main__":
    unittest.main()
