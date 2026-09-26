import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SCHEMA = ROOT / "database" / "sql" / "teacher_teaching_class.sql"
USER_SERVICE_INIT = ROOT / "database" / "sql" / "user-service-local-init.sql"
COURSE_SERVICE_INIT = (
    ROOT / "database" / "sql" / "experiment-module-service-local-init.sql"
)
PROFILE_INIT = ROOT / "database" / "sql" / "init_seclab_profile.sql"
LEGACY_BUSINESS_INIT = ROOT / "database" / "sql" / "init_seclab_db.sql"


class TeacherTeachingClassSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            CANONICAL_SCHEMA.exists(),
            f"canonical schema is missing: {CANONICAL_SCHEMA}",
        )
        self.sql = CANONICAL_SCHEMA.read_text(encoding="utf-8")

    def assert_has_table(self, schema: str, table: str) -> None:
        pattern = rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`{schema}`\.`{table}`"
        self.assertRegex(self.sql, re.compile(pattern, re.IGNORECASE))

    def test_defines_explicit_user_role_and_course_creator(self) -> None:
        self.assertRegex(
            self.sql,
            re.compile(
                r"`user_role`\s+VARCHAR\(16\)\s+NOT\s+NULL\s+DEFAULT\s+''?STUDENT''?",
                re.IGNORECASE,
            ),
        )
        self.assertIn("`created_by` BIGINT NULL", self.sql)
        self.assertIn("`idx_course_creator_status`", self.sql)

    def test_defines_teaching_class_tables(self) -> None:
        for table in (
            "teaching_class",
            "teaching_class_student",
            "teaching_class_course",
            "teaching_class_import_batch",
        ):
            self.assert_has_table("userservice", table)

    def test_teaching_class_course_stores_teacher_written_content(self) -> None:
        self.assertIn("`teaching_content` TEXT NULL", self.sql)

        runtime_sql = USER_SERVICE_INIT.read_text(encoding="utf-8")
        self.assertIn("`teaching_content` TEXT NULL", runtime_sql)
        self.assertRegex(
            self.sql,
            re.compile(
                r"ADD\s+COLUMN\s+`teaching_content`\s+TEXT\s+NULL",
                re.IGNORECASE,
            ),
        )
        self.assertRegex(
            runtime_sql,
            re.compile(
                r"ADD\s+COLUMN\s+`teaching_content`\s+TEXT\s+NULL",
                re.IGNORECASE,
            ),
        )

    def test_defines_teacher_profile_tables(self) -> None:
        self.assert_has_table("seclab_profile", "teacher_typical_question")
        self.assert_has_table("seclab_profile", "teacher_class_analysis")
        self.assert_has_table("seclab_profile", "teacher_student_analysis")

    def test_contains_required_unique_indexes_and_status_checks(self) -> None:
        required_fragments = (
            "`uk_teacher_term_class_name`",
            "`uk_teaching_class_course`",
            "`uk_teaching_class_order`",
            "`uk_teacher_typical_question`",
            "CHECK (`semester` IN (1, 2))",
            "CHECK (`status` IN ('ACTIVE', 'ARCHIVED'))",
            "CHECK (`analysis_status` IN ('IDLE', 'RUNNING', 'READY'))",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, self.sql)

    def test_user_service_runtime_init_mirrors_role_and_class_tables(self) -> None:
        sql = USER_SERVICE_INIT.read_text(encoding="utf-8")
        self.assertIn("`user_role` VARCHAR(16) NOT NULL DEFAULT 'STUDENT'", sql)
        self.assertIn("`idx_user_role_deleted`", sql)
        for table in (
            "teaching_class",
            "teaching_class_student",
            "teaching_class_course",
            "teaching_class_import_batch",
        ):
            self.assertRegex(
                sql,
                re.compile(
                    rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`{table}`",
                    re.IGNORECASE,
                ),
            )

    def test_course_runtime_init_mirrors_creator_ownership(self) -> None:
        sql = COURSE_SERVICE_INIT.read_text(encoding="utf-8")
        self.assertIn("`created_by` BIGINT NULL", sql)
        self.assertIn("`idx_course_creator_status`", sql)
        self.assertIn("`fk_course_creator`", sql)

    def test_profile_runtime_init_mirrors_teacher_tables(self) -> None:
        sql = PROFILE_INIT.read_text(encoding="utf-8")
        self.assertRegex(
            sql,
            re.compile(
                r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`teacher_typical_question`",
                re.IGNORECASE,
            ),
        )
        self.assertRegex(
            sql,
            re.compile(
                r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`teacher_class_analysis`",
                re.IGNORECASE,
            ),
        )
        self.assertRegex(
            sql,
            re.compile(
                r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`teacher_student_analysis`",
                re.IGNORECASE,
            ),
        )

    def test_legacy_business_init_keeps_role_and_creator_columns_compatible(self) -> None:
        sql = LEGACY_BUSINESS_INIT.read_text(encoding="utf-8")
        self.assertIn("`user_role` VARCHAR(16) NOT NULL DEFAULT 'STUDENT'", sql)
        self.assertIn("`idx_user_role_deleted`", sql)
        self.assertIn("`created_by` BIGINT NULL", sql)
        self.assertIn("`idx_course_creator_status`", sql)


if __name__ == "__main__":
    unittest.main()
