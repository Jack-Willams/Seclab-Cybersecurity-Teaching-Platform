import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import teacher_intervention_repository as interventions


class TeacherInterventionHelpersTest(unittest.TestCase):
    def test_legacy_course_column_migration_uses_information_schema_not_unsupported_if_not_exists(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"column_exists": 1}

        interventions._ensure_course_id_column(cursor)

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("information_schema.columns" in sql for sql in statements))
        self.assertFalse(any("ADD COLUMN IF NOT EXISTS" in sql for sql in statements))
        self.assertFalse(any("ALTER TABLE teacher_intervention" in sql for sql in statements))

    def test_legacy_course_column_is_added_only_when_missing(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"column_exists": 0}

        interventions._ensure_course_id_column(cursor)

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        migration = next(sql for sql in statements if "ALTER TABLE teacher_intervention" in sql)
        self.assertIn("ADD COLUMN course_id", migration)
        self.assertNotIn("IF NOT EXISTS", migration)

    def test_student_assignment_summary_exposes_experiment_questions_deadline_and_result(self):
        row = {
            "assignment_status": "COMPLETED",
            "due_at": datetime.now() - timedelta(days=1),
            "snapshot_question_count": 3,
            "session_question_count": 3,
            "attempt_count": 3,
            "correct_count": 2,
            "average_score": 78.5,
        }

        summary = interventions.build_assignment_learning_summary(row)

        self.assertEqual(summary["questionCount"], 3)
        self.assertEqual(summary["estimatedMinutes"], 15)
        self.assertFalse(summary["isOverdue"])
        self.assertEqual(summary["resultSummary"], {
            "attemptCount": 3, "correctCount": 2, "averageScore": 78.5,
        })

    def test_assignment_is_complete_only_after_every_snapshot_question_was_answered(self):
        self.assertFalse(interventions.has_completed_assignment(3, 1))
        self.assertTrue(interventions.has_completed_assignment(3, 3))
        self.assertFalse(interventions.has_completed_assignment(0, 0))
        self.assertEqual(interventions.resolve_assignment_status("STARTED", 3, 3), "COMPLETED")

    def test_only_approved_exercises_can_be_snapshotted(self):
        approved = {
            "exercise_id": 31,
            "source_version": 2,
            "exercise_role": "FOUNDATION",
            "question_type": "short_answer",
            "stem": "如何判断列数？",
            "options_json": "[]",
            "standard_answer": "使用 ORDER BY 递增",
            "explanation": "观察报错边界",
            "difficulty": 1,
            "review_status": "APPROVED",
            "knowledge_point_id": 71,
        }

        snapshots = interventions.build_approved_exercise_snapshots([approved])

        self.assertEqual(snapshots[0]["sourceExerciseId"], 31)
        self.assertEqual(snapshots[0]["stem"], "如何判断列数？")
        rejected = {**approved, "review_status": "PENDING_REVIEW"}
        with self.assertRaises(ValueError):
            interventions.build_approved_exercise_snapshots([rejected])

    def test_snapshot_questions_preserve_exact_teacher_approved_content(self):
        snapshots = [{
            "sourceExerciseId": 31,
            "sourceVersion": 2,
            "role": "FOUNDATION",
            "questionType": "short_answer",
            "stem": "如何判断列数？",
            "options": [],
            "standardAnswer": "使用 ORDER BY 递增",
            "explanation": "观察报错边界",
            "difficulty": 1,
            "knowledgePointId": 71,
        }]

        questions = interventions.build_snapshot_training_questions(snapshots, intervention_id=17)

        self.assertEqual(questions[0]["stem"], "如何判断列数？")
        self.assertEqual(questions[0]["answer"], "使用 ORDER BY 递增")
        self.assertEqual(questions[0]["knowledge_point_id"], 71)
        self.assertEqual(questions[0]["sourceExerciseId"], 31)
        self.assertEqual(questions[0]["sourceVersion"], 2)

    def test_student_start_builds_training_from_snapshots_without_ai_generation(self):
        assignment = {
            "interventionId": 17,
            "teachingClassId": 101,
            "courseId": 7,
            "knowledgePointId": 71,
            "trainingSessionId": None,
        }
        snapshots = [{
            "sourceExerciseId": 31,
            "sourceVersion": 2,
            "role": "FOUNDATION",
            "questionType": "short_answer",
            "stem": "教师审核后的题干",
            "options": [],
            "standardAnswer": "教师审核后的答案",
            "explanation": "教师审核后的解析",
            "difficulty": 1,
            "knowledgePointId": 71,
        }]
        with (
            patch.object(interventions, "get_student_assignment", return_value=assignment),
            patch.object(interventions, "load_intervention_exercise_snapshots", return_value=snapshots),
            patch.object(interventions, "create_training_session", return_value={"training_session_id": "train-approved-1"}),
            patch.object(interventions, "save_generated_questions", return_value=[{"generated_question_id": "gq-approved-1"}]) as save,
            patch.object(interventions, "mark_student_assignment_started", return_value={**assignment, "trainingSessionId": "train-approved-1"}),
        ):
            result = interventions.start_student_assignment_from_snapshots(261, 17)

        self.assertEqual(result["generation"]["trainingSessionId"], "train-approved-1")
        saved_questions = save.call_args.kwargs["questions"]
        self.assertEqual(saved_questions[0]["stem"], "教师审核后的题干")
        self.assertEqual(saved_questions[0]["answer"], "教师审核后的答案")

    def test_metric_snapshot_contains_all_profile_dimensions(self):
        snapshot = interventions.build_metric_snapshot(
            {
                "snapshot_id": "profile-1",
                "computed_at": "2026-07-17T10:00:00",
                "overall_score": 70,
                "knowledge_mastery_score": 71,
                "troubleshooting_score": 63,
                "autonomy_score": 68,
                "ai_collaboration_score": 74,
                "engagement_score": 80,
            }
        )

        self.assertEqual(snapshot["snapshotId"], "profile-1")
        self.assertEqual(snapshot["scores"]["aiCollaboration"], 74.0)
        self.assertEqual(set(snapshot["scores"]), {
            "overall", "knowledgeMastery", "troubleshooting", "autonomy", "aiCollaboration", "engagement"
        })

    def test_comparison_reports_delta_and_improvement(self):
        baseline = {"scores": {"overall": 60.0, "troubleshooting": 50.0}}
        latest = {"scores": {"overall": 68.0, "troubleshooting": 62.0}}

        result = interventions.compare_metric_snapshots(baseline, latest)

        self.assertEqual(result["delta"]["overall"], 8.0)
        self.assertEqual(result["delta"]["troubleshooting"], 12.0)
        self.assertEqual(result["improvedDimensions"], ["overall", "troubleshooting"])

    def test_comparison_handles_missing_latest_profile(self):
        result = interventions.compare_metric_snapshots({"scores": {"overall": 60.0}}, None)

        self.assertEqual(result, {"delta": {}, "improvedDimensions": [], "status": "NO_FOLLOW_UP"})


if __name__ == "__main__":
    unittest.main()
