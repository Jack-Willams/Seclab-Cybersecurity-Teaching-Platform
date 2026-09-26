import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "database" / "sql" / "teacher_knowledge_analysis.sql"
MIRROR = ROOT / "database" / "legacy" / "teacher_knowledge_analysis.sql"
PROFILE_INIT = ROOT / "database" / "sql" / "init_seclab_profile.sql"
INTERVENTION = ROOT / "database" / "sql" / "teacher_intervention.sql"
INTERVENTION_MIRROR = ROOT / "database" / "legacy" / "teacher_intervention.sql"


class TeacherKnowledgeAnalysisSchemaTest(unittest.TestCase):
    def test_declares_analysis_and_reviewable_exercise_tables_everywhere(self):
        for path in (CANONICAL, MIRROR, PROFILE_INIT):
            sql = path.read_text(encoding="utf-8")
            self.assertIn("`teacher_knowledge_analysis`", sql)
            self.assertIn("`teacher_knowledge_exercise`", sql)
            self.assertIn("`uk_teacher_knowledge_scope`", sql)
            self.assertIn("`review_status`", sql)
            self.assertIn("`source_version`", sql)

    def test_analysis_preserves_last_success_and_last_attempt_error_fields(self):
        sql = CANONICAL.read_text(encoding="utf-8")
        for column in (
            "`analysis_json` LONGTEXT NULL",
            "`evidence_json` LONGTEXT NULL",
            "`last_error_message` VARCHAR(500) NULL",
            "`generated_at` DATETIME(6) NULL",
            "`last_attempt_at` DATETIME(6) NULL",
        ):
            self.assertIn(column, sql)
        self.assertIn("FOREIGN KEY (`analysis_id`)", sql)

    def test_intervention_declares_course_and_immutable_exercise_snapshot(self):
        for path in (INTERVENTION, INTERVENTION_MIRROR, PROFILE_INIT):
            sql = path.read_text(encoding="utf-8")
            self.assertIn("`course_id` INT NULL", sql)
            self.assertIn("`teacher_intervention_exercise_snapshot`", sql)
            self.assertIn("`source_exercise_id` BIGINT NOT NULL", sql)
            self.assertIn("`source_version` INT NOT NULL", sql)
            self.assertIn("`snapshot_json` LONGTEXT NOT NULL", sql)


if __name__ == "__main__":
    unittest.main()
