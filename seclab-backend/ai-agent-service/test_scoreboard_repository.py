import unittest
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch

import scoreboard_repository as repository


class FakeCursor:
    """
    按 SQL 片段路由的假游标：只关心 get_scoreboard 依次问了哪几张表，
    不复刻 MySQL 语义。
    """

    def __init__(self, roster_rows, snapshot_rows, existing_tables):
        self.roster_rows = roster_rows
        self.snapshot_rows = snapshot_rows
        self.existing_tables = existing_tables
        self._result: list = []

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        if "information_schema.tables" in normalized:
            table_name = params[-1] if params else None
            self._result = [{"1": 1}] if table_name in self.existing_tables else []
        elif "teaching_class_student" in normalized:
            self._result = list(self.roster_rows)
        elif "FROM student_profile_snapshot" in normalized:
            self._result = list(self.snapshot_rows)
        else:
            # generated_question_attempt / question_submission / learning_event 统计
            self._result = []

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def roster_row(user_id, number, name, class_name="网安242班", class_id=8):
    return {
        "user_id": user_id,
        "user_student_number": number,
        "user_name": name,
        "user_image": None,
        "class_id": class_id,
        "class_name": class_name,
    }


def snapshot_row(user_id, score, class_id=8):
    return {
        "snapshot_id": f"snap-{user_id}",
        "user_id": user_id,
        "class_id": class_id,
        "course_id": None,
        "computed_at": datetime(2026, 7, 28, 16, 27),
        "knowledge_mastery_score": score,
        "troubleshooting_score": score,
        "autonomy_score": score,
        "ai_collaboration_score": score,
        "engagement_score": score,
        "overall_score": score,
        "profile_summary_json": None,
        "created_at": datetime(2026, 7, 28, 16, 27),
    }


class ScoreboardRosterTest(unittest.TestCase):
    ALL_TABLES = {
        "teaching_class_student",
        "teaching_class",
        "student_profile_snapshot",
        "generated_question_attempt",
        "question_submission",
        "learning_event",
    }

    def run_scoreboard(self, roster_rows, snapshot_rows, existing_tables=None, limit=300):
        cursor = FakeCursor(
            roster_rows,
            snapshot_rows,
            existing_tables if existing_tables is not None else self.ALL_TABLES,
        )

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(repository, "get_connection", fake_connection):
            return repository.get_scoreboard(limit)

    def test_students_without_profile_data_still_appear_on_the_board(self):
        roster = [
            roster_row(122, "2024210214042", "韩力旺"),
            roster_row(123, "2024210214043", "未开始A"),
            roster_row(124, "2024210214044", "未开始B"),
        ]
        result = self.run_scoreboard(roster, [snapshot_row(122, 9.0)])

        items = result["items"]
        # 名单里三个人一个不少，教师端看到几个学生端就看到几个
        self.assertEqual([item["userId"] for item in items], [122, 123, 124])
        self.assertEqual([item["rank"] for item in items], [1, 2, 3])

    def test_zero_data_students_rank_last_and_expose_null_score(self):
        roster = [
            roster_row(200, "20240001", "没数据的人"),
            roster_row(201, "20240002", "有数据的人"),
        ]
        result = self.run_scoreboard(roster, [snapshot_row(201, 42.5)])

        first, second = result["items"]
        self.assertEqual(first["userId"], 201)
        self.assertEqual(first["overallScore"], 42.5)
        self.assertTrue(first["hasActivity"])

        self.assertEqual(second["userId"], 200)
        # 综合分留空，前端 formatScore 渲染成 --，而不是伪造一个 0 分
        self.assertIsNone(second["overallScore"])
        self.assertIsNone(second["averageTrainingScore"])
        self.assertIsNone(second["lastActiveAt"])
        self.assertFalse(second["hasActivity"])

    def test_class_name_comes_from_the_roster_row(self):
        roster = [
            roster_row(300, "20240003", "甲", class_name="网安241班", class_id=7),
            roster_row(301, "20240004", "乙", class_name="网安242班", class_id=8),
        ]
        result = self.run_scoreboard(roster, [])

        self.assertEqual(
            {item["className"] for item in result["items"]},
            {"网安241班", "网安242班"},
        )

    def test_limit_truncates_after_ranking_not_before(self):
        roster = [roster_row(400 + index, f"2024{index:04d}", f"学生{index}") for index in range(5)]
        # 最后一个人分最高，截断前必须先排好序，否则他会被切掉
        result = self.run_scoreboard(roster, [snapshot_row(404, 99.0)], limit=2)

        items = result["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["userId"], 404)

    def test_falls_back_to_snapshot_driven_board_without_teaching_class_tables(self):
        result = self.run_scoreboard(
            [],
            [snapshot_row(500, 12.0)],
            existing_tables={"student_profile_snapshot", "user", "class"},
        )

        self.assertEqual([item["userId"] for item in result["items"]], [500])


if __name__ == "__main__":
    unittest.main()
