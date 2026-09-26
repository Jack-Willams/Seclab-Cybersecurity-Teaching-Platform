import json
import unittest
from unittest.mock import patch

import question_repository


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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        return None


class QuestionSnapshotPersistenceTest(unittest.TestCase):
    def test_question_submission_persists_the_exact_question_snapshot(self):
        connection = RecordingConnection()
        question = {
            "id": 7,
            "content": "哪个输入最适合初步判断 SQL 注入？",
            "options": ["随机字符", "单引号", "脚本", "请求头"],
            "answer": [1],
        }

        with (
            patch.object(question_repository, "ensure_question_schema"),
            patch.object(question_repository, "get_connection", return_value=connection),
        ):
            question_repository.save_question_submission(
                {
                    "user_id": 295,
                    "module_id": 1,
                    "task_id": 3,
                    "question_id": 7,
                    "question_type": "multiple-choice",
                    "question_snapshot": question,
                    "answer": [1],
                    "question_score": 4,
                }
            )

        submission_sql, params = next(
            (sql, params)
            for sql, params in connection.cursor_instance.executed
            if "INSERT INTO question_submission" in sql
        )
        self.assertIn("question_snapshot_json", submission_sql)
        self.assertEqual(json.loads(params["question_snapshot_json"]), question)

    def test_schema_upgrade_adds_snapshot_column_when_missing(self):
        class SchemaCursor:
            def __init__(self):
                self.added = []

            def execute(self, sql, params=None):
                if "ADD COLUMN" in sql:
                    self.added.append(sql)

            def fetchone(self):
                return None

        cursor = SchemaCursor()

        question_repository._ensure_question_submission_columns(cursor)

        self.assertTrue(any("question_snapshot_json" in sql for sql in cursor.added))


if __name__ == "__main__":
    unittest.main()
