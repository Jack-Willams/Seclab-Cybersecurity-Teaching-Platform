import unittest
from datetime import datetime

import profile_dashboard_repository


class ScriptedCursor:
    def __init__(self, result_sets):
        self.result_sets = list(result_sets)
        self.executed = []

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.result_sets.pop(0)


class ProfileDashboardSolveRecordsTest(unittest.TestCase):
    def test_course_submission_uses_the_persisted_question_snapshot(self):
        cursor = ScriptedCursor(
            [
                [
                    {
                        "submission_id": "sub-1",
                        "question_id": 1,
                        "question_uid": "1",
                        "module_id": 1,
                        "task_id": 3,
                        "question_type": "multiple-choice",
                        "question_source": "course_question",
                        "question_snapshot_json": {
                            "content": "以下哪种方法最适合初步判断 SQL 注入？",
                            "options": ["随机字符", "输入单引号", "JavaScript", "修改请求头"],
                        },
                        "answer_json": [1],
                        "standard_answer_json": [1],
                        "is_correct": 1,
                        "score": 4,
                        "cost_time": 18,
                        "created_at": "2026-07-24 20:58:31",
                    }
                ]
            ]
        )

        records = profile_dashboard_repository._question_records(cursor, 295)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "以下哪种方法最适合初步判断 SQL 注入？")
        self.assertEqual(records[0]["stem"], "以下哪种方法最适合初步判断 SQL 注入？")
        self.assertEqual(records[0]["options"], ["随机字符", "输入单引号", "JavaScript", "修改请求头"])
        self.assertEqual(records[0]["studentAnswer"], ["输入单引号"])
        self.assertEqual(records[0]["standardAnswer"], ["输入单引号"])
        self.assertEqual(records[0]["costTime"], 18)
        self.assertTrue(records[0]["contentAvailable"])
        self.assertIn("question_snapshot_json", cursor.executed[0][0])

    def test_generated_training_wrong_answer_is_included_with_review_details(self):
        cursor = ScriptedCursor(
            [
                [
                    {
                        "attempt_id": "attempt-1",
                        "generated_question_id": "gq-1",
                        "training_session_id": "train-1",
                        "module_id": 1,
                        "question_type": "SHORT_ANSWER",
                        "title": "联合查询列数判断",
                        "stem": "如何判断 UNION SELECT 的列数？",
                        "options_json": None,
                        "answer_json": {"answerText": "直接猜三列"},
                        "standard_answer": "使用 ORDER BY 递增或 UNION SELECT NULL 逐步验证。",
                        "explanation": "应通过数据库响应差异逐步确认列数。",
                        "is_correct": 0,
                        "score": 35,
                        "cost_time": 42,
                        "submitted_at": "2026-07-25 10:00:00",
                    }
                ]
            ]
        )

        records = profile_dashboard_repository._generated_question_records(cursor, 295)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["sourceType"], "generated_training")
        self.assertEqual(records[0]["result"], "错误")
        self.assertFalse(records[0]["isCorrect"])
        self.assertEqual(records[0]["studentAnswer"], "直接猜三列")
        self.assertEqual(records[0]["standardAnswer"], "使用 ORDER BY 递增或 UNION SELECT NULL 逐步验证。")
        self.assertEqual(records[0]["explanation"], "应通过数据库响应差异逐步确认列数。")
        self.assertTrue(records[0]["contentAvailable"])

    def test_legacy_submission_without_snapshot_is_marked_unavailable(self):
        cursor = ScriptedCursor(
            [
                [
                    {
                        "submission_id": "sub-old",
                        "question_id": 99,
                        "question_uid": "legacy-99",
                        "module_id": None,
                        "task_id": None,
                        "question_type": "single-choice",
                        "question_source": "course_question",
                        "question_snapshot_json": None,
                        "answer_json": [0],
                        "standard_answer_json": [1],
                        "is_correct": 0,
                        "score": 0,
                        "cost_time": None,
                        "created_at": "2025-01-01 00:00:00",
                    }
                ]
            ]
        )

        record = profile_dashboard_repository._question_records(cursor, 295)[0]

        self.assertEqual(record["title"], "历史题目 legacy-99")
        self.assertEqual(record["stem"], "")
        self.assertFalse(record["contentAvailable"])

    def test_solve_records_merge_course_generated_and_flag_sources(self):
        cursor = ScriptedCursor(
            [
                [
                    {
                        "submission_id": "sub-1",
                        "question_id": 1,
                        "question_uid": "1",
                        "module_id": 1,
                        "task_id": 3,
                        "question_type": "multiple-choice",
                        "question_source": "course_question",
                        "question_snapshot_json": {"content": "课程题", "options": ["A", "B"]},
                        "answer_json": [0],
                        "standard_answer_json": [1],
                        "is_correct": 0,
                        "score": 0,
                        "cost_time": 11,
                        "created_at": datetime(2026, 7, 25, 9, 0, 0),
                    }
                ],
                [
                    {
                        "attempt_id": "attempt-1",
                        "generated_question_id": "gq-1",
                        "training_session_id": "train-1",
                        "module_id": 1,
                        "question_type": "SHORT_ANSWER",
                        "title": "训练题",
                        "stem": "训练题干",
                        "options_json": None,
                        "answer_json": {"answerText": "我的答案"},
                        "standard_answer": "参考答案",
                        "explanation": "解析",
                        "is_correct": 1,
                        "score": 88,
                        "cost_time": 20,
                        "submitted_at": datetime(2026, 7, 25, 10, 0, 0),
                    }
                ],
                [
                    {
                        "submission_id": "flag-1",
                        "module_id": 1,
                        "task_id": 9,
                        "is_correct": 1,
                        "score": 10,
                        "created_at": datetime(2026, 7, 25, 8, 0, 0),
                    }
                ],
            ]
        )

        records = profile_dashboard_repository._solve_records(cursor, 295)

        self.assertEqual([record["sourceType"] for record in records], ["generated_training", "course_question", "flag"])
        self.assertEqual(len(cursor.executed), 3)


if __name__ == "__main__":
    unittest.main()
