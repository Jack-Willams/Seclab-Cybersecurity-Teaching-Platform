import unittest
from datetime import datetime

import teacher_learning_insight_repository as insights


class TeacherLearningInsightHelpersTest(unittest.TestCase):
    def test_redacts_secrets_from_commands(self):
        command = "curl -H 'Authorization: Bearer top-secret' --password hunter2 --cookie session=abc http://target"

        redacted = insights.redact_command(command)

        self.assertNotIn("top-secret", redacted)
        self.assertNotIn("hunter2", redacted)
        self.assertNotIn("session=abc", redacted)
        self.assertIn("Bearer ***", redacted)
        self.assertIn("--password ***", redacted)

    def test_timeline_is_chronological_and_marks_successful_retry(self):
        command_rows = [
            {
                "command_id": "cmd-fail",
                "lab_session_id": "lab-1",
                "command": "sqlmap --technique=T",
                "cmd_category": "sql_injection",
                "exit_code": 1,
                "output_digest": "missing baseline",
                "executed_at": datetime(2026, 7, 14, 14, 5),
            },
            {
                "command_id": "cmd-ok",
                "lab_session_id": "lab-1",
                "command": "sqlmap --technique=T --time-sec=3",
                "cmd_category": "sql_injection",
                "exit_code": 0,
                "output_digest": "verified",
                "executed_at": datetime(2026, 7, 14, 14, 18),
            },
        ]
        timeline = insights.compose_learning_timeline(
            learning_rows=[
                {
                    "event_id": "hint-1",
                    "lab_session_id": "lab-1",
                    "event_type": "HINT_REQUEST",
                    "event_time": datetime(2026, 7, 14, 14, 10),
                    "payload_json": '{"summary":"requested help"}',
                }
            ],
            command_rows=command_rows,
            error_rows=[],
            attempt_rows=[],
            completion_rows=[],
        )

        self.assertEqual([item["kind"] for item in timeline], ["COMMAND", "HINT", "COMMAND"])
        self.assertEqual(timeline[0]["retryOutcome"], "recovered")
        self.assertEqual(timeline[2]["retryOutcome"], "success")

    def test_dimension_evidence_maps_security_events_to_all_five_dimensions(self):
        timeline = [
            {"kind": "ATTEMPT", "status": "success", "title": "题目作答", "occurredAt": "2026-07-14T10:00:00"},
            {"kind": "ERROR", "status": "failed", "title": "实验错误", "occurredAt": "2026-07-14T10:01:00"},
            {"kind": "COMMAND", "status": "success", "title": "命令执行", "occurredAt": "2026-07-14T10:02:00"},
            {"kind": "AI", "status": "info", "title": "AI 求助", "occurredAt": "2026-07-14T10:03:00"},
            {"kind": "SUCCESS", "status": "success", "title": "实验完成", "occurredAt": "2026-07-14T10:04:00"},
        ]
        profile = {
            "knowledge_mastery_score": 71,
            "troubleshooting_score": 63,
            "autonomy_score": 68,
            "ai_collaboration_score": 74,
            "engagement_score": 80,
            "overall_score": 70,
            "profile_summary_json": {"dimension_explanations": {"troubleshooting_score": "能根据错误调整步骤"}},
        }

        result = insights.build_capability_dimensions(profile, timeline)

        self.assertEqual([item["key"] for item in result], [
            "knowledge_mastery", "troubleshooting", "autonomy", "ai_collaboration", "engagement"
        ])
        self.assertEqual(result[1]["score"], 63.0)
        self.assertEqual(result[1]["summary"], "能根据错误调整步骤")
        self.assertTrue(all(item["evidence"] for item in result))

    def test_dimension_summary_extracts_teacher_facing_explanation_from_detail_object(self):
        profile = {
            "troubleshooting_score": 92,
            "profile_summary_json": {
                "dimension_explanations": {
                    "troubleshooting_score": {
                        "stats": {"error_count": 2},
                        "explanation": "能够根据报错调整方案，并在修复后主动复测。",
                    }
                }
            },
        }

        result = insights.build_capability_dimensions(profile, [])

        self.assertEqual(result[1]["summary"], "能够根据报错调整方案，并在修复后主动复测。")
        self.assertNotIn("error_count", result[1]["summary"])

    def test_display_text_rejects_question_mark_only_legacy_data(self):
        self.assertEqual(
            insights.normalize_display_text("????????????", "暂无有效说明"),
            "暂无有效说明",
        )
        self.assertEqual(
            insights.normalize_display_text("已完成 SQL 盲注验证", "暂无有效说明"),
            "已完成 SQL 盲注验证",
        )

    def test_risk_thresholds_match_the_four_colour_teacher_legend(self):
        self.assertEqual(insights.classify_risk(12, 8, 0.60), "high")
        self.assertEqual(insights.classify_risk(10, 4, 0.40), "medium")
        self.assertEqual(insights.classify_risk(8, 2, 0.20), "attention")
        self.assertEqual(insights.classify_risk(8, 1, 0.125), "good")

    def test_risk_items_are_scoped_by_real_experiment_id_not_category_guessing(self):
        rows = [
            {
                "course_id": 7,
                "course_name": "SQL 注入攻击",
                "teaching_order": 2,
                "knowledge_point_id": 71,
                "knowledge_point_name": "联合查询列数判断",
                "knowledge_category": "SQL 注入",
                "student_count": 10,
                "attempted_student_count": 8,
                "incorrect_student_count": 3,
                "attempted_count": 10,
                "incorrect_count": 3,
                "affected_students": "261::陈宇航|||262::刘子涵",
                "representative_questions": "q-1::列数判断",
            },
            {
                "course_id": 8,
                "course_name": "XSS 与 CSRF 攻击",
                "teaching_order": 3,
                "knowledge_point_id": 81,
                "knowledge_point_name": "输出上下文编码",
                "knowledge_category": "XSS",
                "student_count": 10,
                "attempted_student_count": 5,
                "incorrect_student_count": 4,
                "attempted_count": 5,
                "incorrect_count": 4,
            },
        ]

        result = insights.build_knowledge_risk_items(rows, course_id=7)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["courseId"], 7)
        self.assertEqual(result[0]["knowledgePointId"], 71)
        self.assertEqual(result[0]["riskLevel"], "attention")
        self.assertEqual(result[0]["errorShare"], 1.0)

    def test_risk_detail_groups_common_wrong_answers_without_ai(self):
        result = insights.build_knowledge_risk_detail(
            summary={"knowledgePointId": 71, "knowledgePointName": "联合查询列数判断"},
            attempt_rows=[
                {"student_id": 261, "student_name": "陈宇航", "answer_json": '"直接试 3 列"', "standard_answer": "先 ORDER BY", "title": "列数判断", "generated_question_id": "q-1", "score": 50},
                {"student_id": 262, "student_name": "刘子涵", "answer_json": '"直接试 3 列"', "standard_answer": "先 ORDER BY", "title": "列数判断", "generated_question_id": "q-1", "score": 55},
                {"student_id": 263, "student_name": "唐俊杰", "answer_json": '"没有验证"', "standard_answer": "先 ORDER BY", "title": "列数判断", "generated_question_id": "q-1", "score": 40},
            ],
            page=1,
            size=2,
        )

        self.assertEqual(result["commonMistakes"][0]["answer"], "直接试 3 列")
        self.assertEqual(result["commonMistakes"][0]["studentCount"], 2)
        self.assertEqual(len(result["affectedStudents"]), 2)
        self.assertEqual(result["pagination"], {"page": 1, "size": 2, "total": 3})
        self.assertEqual(result["representativeAttempts"][0]["standardAnswer"], "先 ORDER BY")

    def test_knowledge_category_matches_teaching_schedule_or_marks_extension(self):
        courses = [
            {"courseId": 1, "courseName": "SQL注入攻击", "teachingOrder": 2},
            {"courseId": 2, "courseName": "XSS与CSRF攻击", "teachingOrder": 3},
        ]

        self.assertEqual(insights.match_knowledge_course("SQL注入", courses), courses[0])
        self.assertEqual(insights.match_knowledge_course("CSRF", courses), courses[1])
        self.assertEqual(
            insights.match_knowledge_course("文件上传", courses),
            {"courseId": None, "courseName": "扩展知识点（未排期）", "teachingOrder": None},
        )


if __name__ == "__main__":
    unittest.main()
