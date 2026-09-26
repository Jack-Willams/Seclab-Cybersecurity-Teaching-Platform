import unittest
from unittest.mock import patch

import profile_repository


class SourceCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = {}

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows


class RecordingCursor:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))


class RecordingConnection:
    def __init__(self):
        self.cursor_instance = RecordingCursor()
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True


class ProfileDataProvenanceTest(unittest.TestCase):
    def test_nonproduction_sources_cannot_be_counted_as_real_learning_data(self):
        for value in (
            "showcase-seed",
            "STATIC-FALLBACK",
            "mock-profile",
            "demo",
            "pytest-seed",
        ):
            with self.subTest(value=value):
                self.assertFalse(profile_repository.is_production_source(value))

    def test_runtime_sources_are_eligible_for_real_learning_data(self):
        for value in (
            "api",
            "hook",
            "ai-agent-service",
            "course_question",
            "personalized_training",
        ):
            with self.subTest(value=value):
                self.assertTrue(profile_repository.is_production_source(value))

    def test_snapshot_requires_clean_production_provenance_and_real_records(self):
        eligible = {
            "profile_summary_json": {
                "data_provenance": {
                    "mode": "production_events",
                    "calculationVersion": "capability-growth-v1",
                    "eligibleRecordCount": 4,
                    "excludedRecordCount": 0,
                    "unverifiableRecordCount": 0,
                }
            }
        }

        self.assertTrue(profile_repository.is_growth_eligible_snapshot(eligible))

        eligible["profile_summary_json"]["data_provenance"]["eligibleRecordCount"] = 0
        self.assertFalse(profile_repository.is_growth_eligible_snapshot(eligible))

        eligible["profile_summary_json"]["data_provenance"]["eligibleRecordCount"] = 4
        eligible["profile_summary_json"]["data_provenance"]["excludedRecordCount"] = 1
        self.assertFalse(profile_repository.is_growth_eligible_snapshot(eligible))

        eligible["profile_summary_json"]["data_provenance"]["excludedRecordCount"] = 0
        eligible["profile_summary_json"]["data_provenance"]["unverifiableRecordCount"] = 1
        self.assertFalse(profile_repository.is_growth_eligible_snapshot(eligible))

        self.assertFalse(
            profile_repository.is_growth_eligible_snapshot(
                {"profile_summary_json": {}}
            )
        )

    def test_provenance_mode_stays_ineligible_when_inputs_are_mixed(self):
        result = profile_repository.build_data_provenance(
            {"api": 3, "showcase-seed": 2},
            eligible_record_count=3,
            excluded_record_count=2,
            unverifiable_record_count=0,
        )

        self.assertEqual(result["mode"], "mixed_or_insufficient_data")
        self.assertEqual(result["eligibleRecordCount"], 3)
        self.assertEqual(result["excludedRecordCount"], 2)
        self.assertEqual(result["excludedReasons"], ["showcase-seed"])

    def test_provenance_mode_is_production_only_for_clean_inputs(self):
        result = profile_repository.build_data_provenance(
            {"api": 3, "hook": 2},
            eligible_record_count=5,
            excluded_record_count=0,
            unverifiable_record_count=0,
        )

        self.assertEqual(result["mode"], "production_events")
        self.assertEqual(result["calculationVersion"], "capability-growth-v1")
        self.assertEqual(result["sourceTypes"], ["api", "hook"])

    def test_source_rows_count_unverifiable_records_instead_of_assuming_they_are_real(self):
        result = profile_repository.summarize_source_rows(
            [
                {"source": "api", "record_count": 3},
                {"source": "showcase-seed", "record_count": 2},
                {"source": None, "record_count": 4},
            ]
        )

        self.assertEqual(result["mode"], "mixed_or_insufficient_data")
        self.assertEqual(result["eligibleRecordCount"], 3)
        self.assertEqual(result["excludedRecordCount"], 2)
        self.assertEqual(result["unverifiableRecordCount"], 4)

    def test_profile_provenance_query_covers_every_scoring_source(self):
        cursor = SourceCursor([{"source": "api", "record_count": 6}])

        result = profile_repository._collect_data_provenance(cursor, user_id=261)

        self.assertEqual(result["mode"], "production_events")
        self.assertEqual(cursor.params, {"user_id": 261})
        for table in (
            "question_submission",
            "generated_question_attempt",
            "flag_submission",
            "lab_session",
            "ai_message",
            "ai_context_injection",
            "learning_event",
            "container_command_event",
            "container_file_event",
            "error_event",
        ):
            with self.subTest(table=table):
                self.assertIn(table, cursor.sql)

    def test_rebuilt_snapshot_carries_the_provenance_used_for_growth_eligibility(self):
        connection = RecordingConnection()
        stats = {
            "event_count": 4,
            "ai_interaction_count": 1,
            "ai_ask_count": 1,
            "question_submit_count": 3,
            "flag_submit_count": 1,
            "lab_session_count": 1,
            "active_day_count": 2,
        }
        scores = {
            "knowledge_mastery_score": 70.0,
            "troubleshooting_score": 68.0,
            "autonomy_score": 66.0,
            "ai_collaboration_score": 64.0,
            "engagement_score": 72.0,
            "overall_score": 68.4,
        }
        provenance = profile_repository.build_data_provenance(
            {"api": 8},
            eligible_record_count=8,
            excluded_record_count=0,
            unverifiable_record_count=0,
        )

        with (
            patch.object(profile_repository, "ensure_profile_schema"),
            patch.object(profile_repository, "get_connection", return_value=connection),
            patch.object(profile_repository, "_collect_source_range", return_value=(None, None)),
            patch.object(profile_repository, "_collect_stats", return_value=stats),
            patch.object(profile_repository, "_score_profile", return_value=(scores, {})),
            patch.object(profile_repository, "_strengths_and_weaknesses", return_value=([], [])),
            patch.object(profile_repository, "_load_catalog_resources", return_value={}),
            patch.object(profile_repository, "_build_recommendations", return_value=[]),
            patch.object(profile_repository, "_latest_context", return_value={"class_id": 101, "course_id": 7}),
            patch.object(profile_repository, "_rebuild_daily_features"),
            patch.object(profile_repository, "_collect_data_provenance", return_value=provenance),
        ):
            result = profile_repository.rebuild_student_profile(261)

        self.assertEqual(result["profile_summary_json"]["data_provenance"], provenance)
        self.assertTrue(profile_repository.is_growth_eligible_snapshot(result))
        self.assertTrue(connection.committed)


if __name__ == "__main__":
    unittest.main()
