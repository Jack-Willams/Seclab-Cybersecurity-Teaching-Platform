import unittest
from unittest.mock import patch

import teacher_repository


class _SingleRowCursor:
    def __init__(self, row):
        self.rows = row if isinstance(row, list) else [row]
        self.index = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, *_args, **_kwargs):
        return None

    def fetchone(self):
        row = self.rows[min(self.index, len(self.rows) - 1)]
        self.index += 1
        return row


class _SingleRowConnection:
    def __init__(self, row):
        self.cursor_instance = _SingleRowCursor(row)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_instance


class TeacherRepositoryHelperTest(unittest.TestCase):
    def test_generated_question_query_is_scoped_to_current_teacher(self):
        sql = teacher_repository._generated_question_from_sql(7, "")

        self.assertIn("tc.teacher_id = 7", sql)

    def test_owned_teaching_class_rejects_another_teacher(self):
        connection = _SingleRowConnection({"teaching_class_id": 102, "teacher_id": 8})

        with patch.object(teacher_repository, "get_connection", return_value=connection):
            with self.assertRaises(PermissionError):
                teacher_repository.require_owned_teaching_class(7, 102)

    def test_student_must_belong_to_selected_owned_teaching_class(self):
        connection = _SingleRowConnection(
            [{"teaching_class_id": 101, "teacher_id": 7}, None]
        )

        with patch.object(teacher_repository, "get_connection", return_value=connection):
            with self.assertRaises(PermissionError):
                teacher_repository.require_student_in_owned_teaching_class(7, 101, 21)

    def test_generated_question_record_is_live_data_not_review_workflow(self):
        row = {
            "generated_question_id": "gq-1",
            "training_session_id": "session-course-2",
            "user_id": 21,
            "user_student_number": "20260001",
            "user_name": "张晨",
            "teaching_class_id": 101,
            "teaching_class_name": "2026级网络安全1班",
            "course_id": 2,
            "course_name": "Web安全基础",
            "knowledge_point_id": 201,
            "knowledge_point_name": "XSS输出上下文",
            "question_type": "short_answer",
            "difficulty": "medium",
            "title": "判断输出上下文",
            "stem": "请分析该输出点。",
            "standard_answer": "先识别上下文。",
            "explanation": "根据HTML解析位置判断。",
            "raw_ai_json": '{"generationReason":"学生在上下文判断上连续出错","reviewStatus":"APPROVED"}',
            "attempt_count": 2,
            "latest_attempt_id": "a-2",
            "latest_answer_json": '{"answer":"属性上下文"}',
            "latest_is_correct": 0,
            "latest_score": 40,
            "latest_submitted_at": "2026-07-14T10:00:00",
            "is_typical": 1,
            "created_at": "2026-07-14T09:00:00",
        }

        item = teacher_repository.map_generated_question_record(row)

        self.assertEqual(item["teachingClassId"], 101)
        self.assertEqual(item["trainingSessionId"], "session-course-2")
        self.assertEqual(item["generationReason"], "学生在上下文判断上连续出错")
        self.assertTrue(item["isTypical"])
        self.assertFalse(item["latestAttempt"]["isCorrect"])
        self.assertNotIn("reviewStatus", item)

    def test_answer_result_filter_rejects_review_status_words(self):
        self.assertEqual(teacher_repository._normalize_answer_result("incorrect"), "incorrect")
        with self.assertRaises(ValueError):
            teacher_repository._normalize_answer_result("approved")

    def test_current_user_profiles_exclude_orphans_and_use_current_class(self):
        users = {
            3: {"user_id": 3, "class_id": 2},
            5: {"user_id": 5, "class_id": 1},
        }
        profiles = [
            {"user_id": 3, "class_id": 1, "overall_score": 59.8},
            {"user_id": 9001, "class_id": 232, "overall_score": 26.3},
        ]

        current_profiles = teacher_repository._profiles_for_current_users(profiles, users)

        self.assertEqual(current_profiles, [{"user_id": 3, "class_id": 2, "overall_score": 59.8}])

    def test_group_profiles_uses_users_current_class_and_ignores_orphan_profile_classes(self):
        users = {
            3: {"user_id": 3, "class_id": 2},
            5: {"user_id": 5, "class_id": 1},
        }
        profiles = [
            {"user_id": 3, "class_id": 1, "overall_score": 59.8},
            {"user_id": 9001, "class_id": 232, "overall_score": 26.3},
        ]

        grouped = teacher_repository._group_profiles_by_current_class(profiles, users)

        self.assertNotIn(232, grouped)
        self.assertNotIn(1, grouped)
        self.assertEqual([item["user_id"] for item in grouped[2]], [3])

    def test_current_class_profiles_include_each_current_student_once(self):
        users = {
            3: {"user_id": 3, "class_id": 2},
            5: {"user_id": 5, "class_id": 1},
            6: {"user_id": 6, "class_id": 1},
        }
        profiles = [
            {"user_id": 3, "class_id": 1, "overall_score": 59.8},
            {"user_id": 5, "class_id": 9, "overall_score": 34.0},
            {"user_id": 9001, "class_id": 1, "overall_score": 21.7},
        ]

        current_profiles = teacher_repository._profiles_for_current_class(profiles, users, 1)

        self.assertEqual([item["user_id"] for item in current_profiles], [5, 6])
        self.assertEqual(current_profiles[0]["overall_score"], 34.0)
        self.assertEqual(current_profiles[0]["class_id"], 1)
        self.assertEqual(current_profiles[1], {"user_id": 6, "class_id": 1})

    def test_display_class_name_normalizes_seed_and_placeholder_names(self):
        cases = [
            ("Cyber Security 232", 2, "网络安全232班"),
            ("SecLab Demo Class", 9, "SecLab演示班"),
            ("????", 4, "未命名班级 4"),
            ("", 5, "未命名班级 5"),
        ]

        for raw_name, class_id, expected in cases:
            with self.subTest(raw_name=raw_name):
                self.assertEqual(
                    teacher_repository._display_class_name(raw_name, class_id),
                    expected,
                )

    def test_student_recommendations_use_personal_evidence_and_teacher_actions(self):
        profile = {
            "knowledge_mastery_score": 88,
            "troubleshooting_score": 15,
            "autonomy_score": 52,
            "ai_collaboration_score": 83.9,
            "engagement_score": 49.4,
        }
        attempts = [
            {"score": 40, "isCorrect": False},
            {"score": 78, "isCorrect": True},
        ]

        recommendations = teacher_repository.build_rule_based_student_recommendations(profile, attempts, "2026-04-27T10:53:00")

        self.assertEqual(recommendations[0]["scope"], "student")
        self.assertEqual(recommendations[0]["dimension"], "troubleshooting")
        self.assertEqual(recommendations[0]["score"], 15.0)
        self.assertIn("该学生", recommendations[0]["summary"])
        self.assertIn("个人五维得分", recommendations[0]["evidence"])
        self.assertIn("最近 2 次训练作答", recommendations[0]["evidence"])
        self.assertIn("个人复盘", recommendations[0]["teacherAction"])
        self.assertNotIn("班级", recommendations[0]["summary"])


if __name__ == "__main__":
    unittest.main()
