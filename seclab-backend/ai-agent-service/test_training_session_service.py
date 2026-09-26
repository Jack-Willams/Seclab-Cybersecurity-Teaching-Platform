import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import training_session_service


def valid_question(index):
    return {
        "questionType": "SHORT_ANSWER",
        "difficulty": 3,
        "dimension": "知识掌握",
        "knowledgeTags": ["SQL注入"],
        "standardAnswer": f"参考答案 {index}",
        "explanation": f"解析 {index}",
        "sourceKnowledgeUnitIds": ["ku-1"],
        "sourceExampleQuestionIds": [],
        "validationHints": {"keywords": ["SQL"], "minLength": 10},
        "teachingObjective": "检验基础概念",
        "expectedSkill": "解释风险",
        "difficultyReason": "中等难度",
        "commonMistakes": ["缺少依据"],
        "gradingRubric": [{"point": "说明依据", "score": 100}],
        "qualityScore": 90,
        "qualitySummary": "可用",
        "qualityFlags": [],
        "title": f"题目 {index}",
        "stem": f"真实题干 {index}",
    }


def request(count=4):
    return {
        "user_id": 295,
        "dimension": "知识掌握",
        "recommendation_id": "rec-1",
        "module_id": 1,
        "course_id": 1,
        "knowledge_tags": ["SQL注入"],
        "difficulty": 3,
        "question_type": "SHORT_ANSWER",
        "count": count,
        "source": "student_profile_snapshot",
    }


class TrainingQuestionConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_question_slots_start_without_waiting_for_previous_slot(self):
        started = 0
        all_started = asyncio.Event()

        async def generate(item_req, *_args):
            nonlocal started
            started += 1
            if started == 4:
                all_started.set()
            await all_started.wait()
            return {
                "generator": "real-provider",
                "payload": valid_question(item_req["question_index"]),
                "difyMetadata": {},
            }

        with (
            patch.object(training_session_service, "generate_question_with_llm", side_effect=generate),
            patch.object(
                training_session_service,
                "validate_generated_question",
                side_effect=lambda payload, *_args: payload,
            ),
            patch.object(training_session_service, "_pick_knowledge_point_id", return_value=101),
            patch.object(training_session_service, "_pick_module_id", return_value=1),
        ):
            rows, generator = await asyncio.wait_for(
                training_session_service._generate_question_rows(
                    request(4),
                    knowledge_units=[{"knowledgeUnitId": "ku-1"}],
                    recommendation={},
                    example_questions=[],
                    rag_context={
                        "ragMode": "local",
                        "retrievalQuery": "SQL",
                        "retrievalMetadata": {},
                    },
                    training_session_id="train-1",
                ),
                timeout=0.2,
            )

        self.assertEqual(started, 4)
        self.assertEqual(len(rows), 4)
        self.assertEqual([row["title"] for row in rows], ["题目 1", "题目 2", "题目 3", "题目 4"])
        self.assertEqual(generator, "real-provider")

    async def test_failed_slots_can_return_a_real_partial_set_when_four_questions_succeed(self):
        async def generate(item_req, *_args):
            if item_req["question_index"] > 4:
                raise RuntimeError("provider rejected slot")
            return {
                "generator": "real-provider",
                "payload": valid_question(item_req["question_index"]),
                "difyMetadata": {},
            }

        with (
            patch.object(training_session_service, "generate_question_with_llm", side_effect=generate),
            patch.object(
                training_session_service,
                "validate_generated_question",
                side_effect=lambda payload, *_args: payload,
            ),
            patch.object(training_session_service, "_pick_knowledge_point_id", return_value=101),
            patch.object(training_session_service, "_pick_module_id", return_value=1),
        ):
            rows, _generator = await training_session_service._generate_question_rows(
                request(7),
                knowledge_units=[{"knowledgeUnitId": "ku-1"}],
                recommendation={},
                example_questions=[],
                rag_context={
                    "ragMode": "local",
                    "retrievalQuery": "SQL",
                    "retrievalMetadata": {},
                },
                training_session_id="train-1",
            )

        self.assertEqual(len(rows), 4)

    def test_persisted_knowledge_fallback_reuses_real_stems_answers_and_sources(self):
        rows, generator = training_session_service._build_grounded_fallback_rows(
            request(4),
            knowledge_units=[
                {
                    "knowledgeUnitId": "question-live-1",
                    "moduleId": 1,
                    "moduleTitle": "SQL注入基础实验",
                    "question": "数据库层注入与浏览器层脚本执行的核心区别是什么？",
                    "answer": "前者影响数据库查询，后者在浏览器执行脚本。",
                    "explanation": "该题来自已持久化训练题。",
                    "knowledgeTags": ["SQL注入", "XSS"],
                    "difficulty": 3,
                },
                {
                    "knowledgeUnitId": "question-live-2",
                    "moduleId": 1,
                    "moduleTitle": "SQL注入基础实验",
                    "question": "参数化查询为什么能降低 SQL 注入风险？",
                    "answer": "它将 SQL 结构和输入数据分离。",
                    "explanation": "该题来自已持久化训练题。",
                    "knowledgeTags": ["SQL注入"],
                    "difficulty": 3,
                },
            ],
            example_questions=[
                {
                    "exampleQuestionId": "approved-1",
                    "title": "联合查询识别",
                    "stem": "UNION 在联合查询注入中的作用是什么？",
                    "standardAnswer": "合并两个查询结果集。",
                    "explanation": "该题来自平台标准题库。",
                    "knowledgeTags": ["SQL注入", "联合查询"],
                    "difficulty": 3,
                    "gradingRubric": [{"point": "说明结果集合并", "score": 100}],
                },
                {
                    "exampleQuestionId": "approved-2",
                    "title": "输出编码",
                    "stem": "上下文输出编码为什么能降低 XSS 风险？",
                    "standardAnswer": "避免不可信输入进入脚本执行上下文。",
                    "explanation": "该题来自平台标准题库。",
                    "knowledgeTags": ["XSS", "输出编码"],
                    "difficulty": 2,
                    "gradingRubric": [{"point": "说明执行上下文", "score": 100}],
                },
            ],
            training_session_id="train-real-fallback",
        )

        self.assertEqual(generator, "persisted_knowledge")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["stem"], "数据库层注入与浏览器层脚本执行的核心区别是什么？")
        self.assertEqual(rows[0]["answer"], "前者影响数据库查询，后者在浏览器执行脚本。")
        self.assertEqual(rows[0]["sourceKnowledgeUnitIds"], ["question-live-1"])
        self.assertEqual(rows[2]["stem"], "UNION 在联合查询注入中的作用是什么？")
        self.assertEqual(rows[2]["sourceExampleQuestionIds"], ["approved-1"])


class TrainingQuestionTimeoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_question_set_timeout_returns_a_stable_504_error(self):
        async def never_finishes(*_args, **_kwargs):
            await asyncio.Event().wait()

        with (
            patch.object(training_session_service, "_normalize_question_set_request", return_value=request(4)),
            patch.object(training_session_service, "get_latest_student_profile", return_value={}),
            patch.object(training_session_service, "_extract_recommendation_context", return_value={}),
            patch.object(
                training_session_service,
                "retrieve_knowledge_units",
                return_value=[{"knowledgeUnitId": "ku-1"}],
            ),
            patch.object(training_session_service, "_retrieve_standard_examples", return_value=[]),
            patch.object(
                training_session_service,
                "_build_rag_context",
                return_value={"ragMode": "local", "retrievalQuery": "SQL", "retrievalMetadata": {}},
            ),
            patch.object(training_session_service, "_generate_question_rows", side_effect=never_finishes),
            patch.object(training_session_service, "QUESTION_SET_TIMEOUT_SECONDS", 0.01, create=True),
        ):
            with self.assertRaises(training_session_service.TrainingSessionServiceError) as raised:
                await training_session_service.generate_training_question_set_batch({})

        self.assertEqual(raised.exception.code, "QUESTION_SET_GENERATION_TIMEOUT")
        self.assertEqual(raised.exception.status_code, 504)


if __name__ == "__main__":
    unittest.main()
