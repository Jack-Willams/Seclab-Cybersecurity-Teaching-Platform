import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import teacher_course_analysis_service as course_service
from teacher_course_analysis_service import (
    TeacherCourseAnalysisRepository,
    build_course_analysis_fallback,
    build_course_question_summary,
)


class TeacherCourseQuestionSummaryTest(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "generatedQuestionId": "q-1",
                "student": {"studentId": 21, "studentName": "张晨", "studentNumber": "20260001"},
                "courseId": 2,
                "courseName": "XSS与CSRF攻击",
                "knowledgePointName": "XSS输出上下文",
                "title": "识别属性上下文",
                "attemptHistory": [
                    {"attemptId": "a-1", "isCorrect": False, "score": 40, "submittedAt": "2026-07-14T09:00:00"},
                    {"attemptId": "a-2", "isCorrect": True, "score": 90, "submittedAt": "2026-07-14T09:08:00"},
                ],
            },
            {
                "generatedQuestionId": "q-2",
                "student": {"studentId": 22, "studentName": "李晴", "studentNumber": "20260002"},
                "courseId": 2,
                "courseName": "XSS与CSRF攻击",
                "knowledgePointName": "XSS输出上下文",
                "title": "选择编码方式",
                "attemptHistory": [
                    {"attemptId": "a-3", "isCorrect": False, "score": 20, "submittedAt": "2026-07-14T10:00:00"},
                ],
            },
        ]

    def test_summary_counts_all_attempts_but_accuracy_uses_latest_result(self):
        summary = build_course_question_summary(self.records)

        self.assertEqual(summary["questionCount"], 2)
        self.assertEqual(summary["attemptCount"], 3)
        self.assertEqual(summary["correctQuestionCount"], 1)
        self.assertEqual(summary["incorrectQuestionCount"], 1)
        self.assertEqual(summary["accuracyRate"], 0.5)
        self.assertEqual(summary["studentCount"], 2)

    def test_summary_keeps_student_and_knowledge_point_drill_down(self):
        summary = build_course_question_summary(self.records)

        zhang = next(item for item in summary["students"] if item["studentId"] == 21)
        self.assertEqual(zhang["attemptCount"], 2)
        self.assertEqual(summary["knowledgePoints"][0]["incorrectQuestionCount"], 1)
        self.assertEqual(summary["knowledgePoints"][0]["affectedStudentCount"], 1)

    def test_fallback_is_course_evidence_not_dimension_categories(self):
        analysis = build_course_analysis_fallback(
            self.records,
            scope="student",
            course={"courseId": 2, "courseName": "XSS与CSRF攻击"},
        )

        self.assertEqual(analysis["scope"], "student_course")
        self.assertTrue(analysis["fallbackUsed"])
        self.assertEqual(analysis["courseId"], 2)
        self.assertIn("XSS输出上下文", analysis["overallComment"])
        self.assertTrue(analysis["knowledgeFindings"])
        self.assertTrue(analysis["representativeMistakes"])

    def test_fallback_builds_different_teaching_plans_from_each_real_wrong_answer(self):
        records = [
            {
                "generatedQuestionId": "sql-1",
                "student": {"studentId": 21, "studentName": "陈宇航", "studentNumber": "20260001"},
                "knowledgePointName": "SQL注入联合查询列数判断",
                "title": "UNION 查询列数判断",
                "referenceAnswer": "从 ORDER BY 1 开始递增，首次报错的序号减一即为原查询列数。",
                "attemptHistory": [
                    {
                        "attemptId": "sql-a-1",
                        "answer": "只写出了部分步骤，缺少验证依据。",
                        "isCorrect": False,
                        "score": 54,
                    }
                ],
            },
            {
                "generatedQuestionId": "xss-1",
                "student": {"studentId": 22, "studentName": "李沐阳", "studentNumber": "20260002"},
                "knowledgePointName": "XSS输入输出上下文判断",
                "title": "HTML 属性上下文编码",
                "referenceAnswer": "按属性上下文编码，并限制危险协议。",
                "attemptHistory": [
                    {
                        "attemptId": "xss-a-1",
                        "answer": "统一做 HTML 转义。",
                        "isCorrect": False,
                        "score": 40,
                    }
                ],
            },
        ]

        analysis = build_course_analysis_fallback(
            records,
            scope="class",
            course={"courseId": 1, "courseName": "Web 安全"},
        )
        findings = {
            item["knowledgePointName"]: item
            for item in analysis["knowledgeFindings"]
        }
        sql = findings["SQL注入联合查询列数判断"]
        xss = findings["XSS输入输出上下文判断"]

        self.assertEqual(sql["affectedStudents"], ["陈宇航"])
        self.assertEqual(sql["representativeQuestionTitle"], "UNION 查询列数判断")
        self.assertEqual(sql["observedAnswer"], "只写出了部分步骤，缺少验证依据。")
        self.assertIn("ORDER BY", sql["standardAnswer"])
        self.assertIn("ORDER BY", sql["diagnosis"])
        self.assertIn("UNION SELECT NULL", sql["instruction"])
        self.assertIn("陈宇航", sql["check"])
        self.assertIn("属性上下文", xss["diagnosis"])
        self.assertIn("HTML 文本、属性值和 JavaScript", xss["instruction"])
        self.assertNotEqual(sql["teacherAction"], xss["teacherAction"])
        self.assertNotIn("打开下方错题", str(analysis))


class TeacherCourseAnalysisProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_real_provider_gets_enough_time_to_finish_reasoning_response(self):
        evidence = {
            "items": [{"generatedQuestionId": "q-1"}],
            "course": {"courseId": 1, "courseName": "SQL注入攻击"},
            "summary": {"questionCount": 1},
        }
        captured_timeout = None

        async def capture_wait_for(awaitable, timeout):
            nonlocal captured_timeout
            captured_timeout = timeout
            return await awaitable

        with (
            patch.object(course_service, "collect_course_question_records", return_value=evidence),
            patch.object(
                course_service,
                "_call_ai_for_student_analysis",
                new=AsyncMock(return_value={"overallComment": "真实分析"}),
            ),
            patch.object(course_service.asyncio, "wait_for", side_effect=capture_wait_for),
            patch.object(course_service.COURSE_ANALYSIS_REPOSITORY, "begin"),
            patch.object(course_service.COURSE_ANALYSIS_REPOSITORY, "save_success"),
            patch.object(
                course_service.COURSE_ANALYSIS_REPOSITORY,
                "get_latest",
                return_value={"analysisStatus": "READY"},
            ),
        ):
            await course_service.run_course_analysis(1, 1, {"user_id": 1, "role": "TEACHER"})

        self.assertGreaterEqual(captured_timeout, 30)


class TeacherCourseAnalysisRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.store = {}
        self.repository = TeacherCourseAnalysisRepository(memory_store=self.store)
        self.cutoff = datetime(2026, 7, 17, 9, 0, 0)

    def test_course_and_scope_have_independent_results(self):
        self.repository.save_success(7, 101, 1, "CLASS", 0, self.cutoff, {"overallComment": "SQL班级"}, {})
        self.repository.save_success(7, 101, 2, "STUDENT", 21, self.cutoff, {"overallComment": "张晨XSS"}, {})

        class_result = self.repository.get_latest(7, 101, 1, "CLASS", 0)
        student_result = self.repository.get_latest(7, 101, 2, "STUDENT", 21)

        self.assertEqual(class_result["analysis"]["overallComment"], "SQL班级")
        self.assertEqual(student_result["analysis"]["overallComment"], "张晨XSS")
        self.assertEqual(student_result["courseId"], 2)

    def test_failed_refresh_preserves_previous_course_result(self):
        self.repository.save_success(7, 101, 2, "STUDENT", 21, self.cutoff, {"overallComment": "旧结果"}, {})
        self.repository.begin(7, 101, 2, "STUDENT", 21, self.cutoff + timedelta(hours=1))
        self.repository.save_failure(7, 101, 2, "STUDENT", 21, "Dify超时")

        result = self.repository.get_latest(7, 101, 2, "STUDENT", 21)

        self.assertEqual(result["analysisStatus"], "READY")
        self.assertEqual(result["analysis"]["overallComment"], "旧结果")
        self.assertEqual(result["lastErrorMessage"], "Dify超时")


if __name__ == "__main__":
    unittest.main()
