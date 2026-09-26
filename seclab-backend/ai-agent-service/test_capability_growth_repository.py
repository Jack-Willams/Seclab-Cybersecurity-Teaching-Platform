import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import capability_growth_repository as repository


def eligible_snapshot(snapshot_id, score, day):
    return {
        "snapshot_id": snapshot_id,
        "user_id": 261,
        "class_id": 101,
        "computed_at": datetime(2026, 7, day, 9, 0),
        "knowledge_mastery_score": score,
        "troubleshooting_score": score,
        "autonomy_score": score,
        "ai_collaboration_score": score,
        "engagement_score": score,
        "overall_score": score,
        "profile_summary_json": {
            "data_provenance": {
                "mode": "production_events",
                "calculationVersion": "capability-growth-v1",
                "eligibleRecordCount": 6,
                "excludedRecordCount": 0,
                "unverifiableRecordCount": 0,
            }
        },
    }


class CapabilityGrowthRepositoryTest(unittest.TestCase):
    def test_partition_excludes_seed_and_unverifiable_rows_from_samples(self):
        clean, provenance = repository.partition_production_rows(
            {
                "questionRows": [
                    {"sourceId": "real-1", "originSource": "course_question"},
                    {"sourceId": "seed-1", "originSource": "showcase-seed"},
                    {"sourceId": "unknown-1", "originSource": None},
                ],
                "commandRows": [
                    {"sourceId": "cmd-1", "originSource": "hook"},
                ],
            }
        )

        self.assertEqual(
            [item["sourceId"] for item in clean["questionRows"]],
            ["real-1"],
        )
        self.assertEqual(provenance["eligibleRecordCount"], 2)
        self.assertEqual(provenance["excludedRecordCount"], 1)
        self.assertEqual(provenance["unverifiableRecordCount"], 1)
        self.assertEqual(provenance["excludedReasons"], ["showcase-seed"])

    def test_question_metrics_compare_same_knowledge_type_and_difficulty(self):
        start = datetime(2026, 7, 1, 9, 0)
        rows = []
        for index, (correct, cost_time) in enumerate(
            [
                (False, 130),
                (False, 120),
                (True, 110),
                (True, 70),
                (True, 60),
                (True, 50),
            ]
        ):
            rows.append(
                {
                    "sourceId": f"attempt-{index}",
                    "sourceType": "generated_question_attempt",
                    "originSource": "personalized_training",
                    "knowledgePointId": 101,
                    "questionType": "single_choice",
                    "difficulty": "medium",
                    "isCorrect": correct,
                    "costTime": cost_time,
                    "occurredAt": start + timedelta(days=index),
                    "title": "联合查询列数判断",
                }
            )

        metrics, evidence = repository.build_question_growth(rows)

        self.assertEqual(
            [item["key"] for item in metrics],
            ["accuracy", "answer_time"],
        )
        self.assertEqual(metrics[0]["baselineValue"], 33.33)
        self.assertEqual(metrics[0]["currentValue"], 100.0)
        self.assertEqual(metrics[1]["baselineValue"], 120.0)
        self.assertEqual(metrics[1]["currentValue"], 60.0)
        self.assertEqual(metrics[1]["direction"], "improved")
        self.assertEqual(evidence[0]["sourceId"], "attempt-5")

    def test_troubleshooting_metrics_use_real_failed_to_successful_command_pairs(self):
        start = datetime(2026, 7, 1, 9, 0)
        command_rows = []
        for index, recovery_seconds in enumerate([600, 660, 720, 300, 360, 420]):
            session_id = f"lab-{index}"
            failed_at = start + timedelta(days=index)
            command_rows.extend(
                [
                    {
                        "sourceId": f"fail-{index}",
                        "sourceType": "container_command_event",
                        "originSource": "hook",
                        "labSessionId": session_id,
                        "commandCategory": "sql_injection",
                        "exitCode": 1,
                        "occurredAt": failed_at,
                    },
                    {
                        "sourceId": f"success-{index}",
                        "sourceType": "container_command_event",
                        "originSource": "hook",
                        "labSessionId": session_id,
                        "commandCategory": "sql_injection",
                        "exitCode": 0,
                        "occurredAt": failed_at + timedelta(seconds=recovery_seconds),
                    },
                ]
            )

        metrics, evidence = repository.build_troubleshooting_growth(command_rows)

        recovery = next(item for item in metrics if item["key"] == "recovery_time")
        self.assertEqual(recovery["baselineValue"], 660.0)
        self.assertEqual(recovery["currentValue"], 360.0)
        self.assertEqual(recovery["direction"], "improved")
        self.assertIn("fail-0", recovery["sourceRecordIds"])
        self.assertTrue(evidence)

    def test_lab_evidence_exposes_the_actual_accessed_experiment_and_session(self):
        evidence = repository.build_lab_evidence(
            [
                {
                    "sourceId": "lab-real-1",
                    "sourceType": "lab_session",
                    "originSource": "docker-runtime",
                    "courseId": 1,
                    "moduleId": 1,
                    "taskId": None,
                    "moduleName": "SQL注入基础实验",
                    "containerName": "sqli-lab-web-1",
                    "targetUrl": "http://localhost:8091/index.php",
                    "status": "stopped",
                    "startedAt": datetime(2026, 7, 25, 0, 48, 42),
                    "endedAt": datetime(2026, 7, 25, 0, 50, 52),
                    "durationSeconds": 130,
                    "eventCount": 2,
                    "eventTypes": "LAB_START,LAB_STOP",
                    "isCompleted": False,
                    "occurredAt": datetime(2026, 7, 25, 0, 48, 42),
                }
            ]
        )

        self.assertEqual(evidence[0]["title"], "SQL注入基础实验")
        self.assertEqual(evidence[0]["detail"], "访问 http://localhost:8091/index.php")
        self.assertEqual(evidence[0]["labSessionId"], "lab-real-1")
        self.assertEqual(evidence[0]["containerName"], "sqli-lab-web-1")
        self.assertEqual(evidence[0]["durationSeconds"], 130)
        self.assertEqual(evidence[0]["eventCount"], 2)
        self.assertEqual(evidence[0]["eventTypes"], ["LAB_START", "LAB_STOP"])

    def test_ai_evidence_exposes_the_actual_student_message(self):
        evidence = repository.build_ai_evidence(
            [
                {
                    "sourceId": "message-real-1",
                    "sourceType": "ai_message",
                    "originSource": "frontend",
                    "conversationId": "conversation-real-1",
                    "moduleId": 1,
                    "taskId": 2,
                    "moduleName": "SQL注入基础实验",
                    "messageContent": "为什么 UNION 查询的列数必须一致？",
                    "isContextRich": True,
                    "occurredAt": datetime(2026, 7, 25, 8, 49, 21),
                }
            ]
        )

        self.assertEqual(
            evidence[0]["title"],
            "提问：为什么 UNION 查询的列数必须一致？",
        )
        self.assertEqual(
            evidence[0]["messageContent"],
            "为什么 UNION 查询的列数必须一致？",
        )
        self.assertEqual(
            evidence[0]["conversationId"],
            "conversation-real-1",
        )
        self.assertEqual(evidence[0]["moduleName"], "SQL注入基础实验")

    def test_ai_growth_query_does_not_turn_a_missing_task_id_into_task_zero(self):
        executed_sql = []

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def execute(self, sql, _params):
                executed_sql.append(sql)

            def fetchall(self):
                return []

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def cursor(self):
                return Cursor()

        with patch.object(repository, "get_connection", return_value=Connection()):
            repository._load_growth_rows(295, None)

        ai_query = next(sql for sql in executed_sql if "FROM ai_message m" in sql)
        self.assertIn("c.task_id AS taskId", ai_query)
        self.assertNotIn("COALESCE(c.task_id, 0)", ai_query)

    def test_growth_response_uses_loaded_real_rows_without_fallback_values(self):
        loaded = {
            "snapshots": [
                eligible_snapshot("start", 60, 1),
                eligible_snapshot("current", 74, 20),
            ],
            "questionRows": [],
            "commandRows": [],
            "completionRows": [],
            "aiMessageRows": [],
            "labRows": [],
        }

        with patch.object(repository, "_load_growth_rows", return_value=loaded):
            result = repository.get_student_capability_growth(261, 101)

        self.assertEqual(result["studentId"], 261)
        self.assertEqual(result["teachingClassId"], 101)
        self.assertEqual(result["overall"]["delta"], 14.0)
        self.assertEqual(result["message"], None)
        self.assertNotIn("mock", str(result).lower())

    def test_teacher_growth_checks_owned_class_membership_before_loading_data(self):
        with (
            patch.object(
                repository,
                "require_student_in_owned_teaching_class",
            ) as require_member,
            patch.object(
                repository,
                "get_student_capability_growth",
                return_value={"studentId": 261},
            ),
        ):
            result = repository.get_teacher_student_capability_growth(7, 101, 261)

        require_member.assert_called_once_with(7, 101, 261)
        self.assertEqual(result, {"studentId": 261})


if __name__ == "__main__":
    unittest.main()
