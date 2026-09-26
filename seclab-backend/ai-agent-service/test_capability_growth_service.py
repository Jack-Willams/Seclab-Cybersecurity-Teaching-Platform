import unittest
from datetime import datetime, timedelta

import capability_growth_service as growth


def snapshot(snapshot_id, score, day, eligible=True):
    provenance = {
        "mode": "production_events" if eligible else "mixed_or_insufficient_data",
        "calculationVersion": "capability-growth-v1",
        "eligibleRecordCount": 4 if eligible else 0,
        "excludedRecordCount": 0,
        "unverifiableRecordCount": 0,
    }
    return {
        "snapshot_id": snapshot_id,
        "computed_at": datetime(2026, 7, day, 9, 0),
        "overall_score": score,
        "knowledge_mastery_score": score + 1,
        "troubleshooting_score": score + 2,
        "autonomy_score": score + 3,
        "ai_collaboration_score": score + 4,
        "engagement_score": score + 5,
        "profile_summary_json": {"data_provenance": provenance},
    }


class CapabilityGrowthServiceTest(unittest.TestCase):
    def test_selects_first_and_latest_eligible_snapshots_only(self):
        baseline, current, history = growth.select_growth_snapshots(
            [
                snapshot("legacy", 55, day=1, eligible=False),
                snapshot("first-real", 61, day=2),
                snapshot("latest-real", 74, day=5),
            ]
        )

        self.assertEqual(baseline["snapshot_id"], "first-real")
        self.assertEqual(current["snapshot_id"], "latest-real")
        self.assertEqual(
            [item["snapshot_id"] for item in history],
            ["first-real", "latest-real"],
        )

    def test_single_eligible_snapshot_has_current_value_but_no_baseline(self):
        baseline, current, history = growth.select_growth_snapshots(
            [snapshot("only-real", 65, day=3)]
        )

        self.assertIsNone(baseline)
        self.assertEqual(current["snapshot_id"], "only-real")
        self.assertEqual(len(history), 1)

    def test_windows_never_share_the_same_task_instance(self):
        start = datetime(2026, 7, 1, 9, 0)
        rows = [
            {
                "sourceId": f"attempt-{index}",
                "bucket": "kp-101:single_choice:medium",
                "occurredAt": start + timedelta(days=index),
            }
            for index in range(5)
        ]

        comparisons = growth.split_comparable_windows(
            rows,
            bucket_key=lambda row: row["bucket"],
        )

        self.assertEqual(len(comparisons), 1)
        self.assertEqual(comparisons[0]["baselineIds"], ["attempt-0", "attempt-1"])
        self.assertEqual(comparisons[0]["currentIds"], ["attempt-3", "attempt-4"])
        self.assertTrue(
            set(comparisons[0]["baselineIds"]).isdisjoint(
                comparisons[0]["currentIds"]
            )
        )

    def test_window_is_omitted_when_each_side_has_fewer_than_two_samples(self):
        rows = [
            {"sourceId": "a-1", "bucket": "same", "occurredAt": "2026-07-01"},
            {"sourceId": "a-2", "bucket": "same", "occurredAt": "2026-07-02"},
            {"sourceId": "a-3", "bucket": "same", "occurredAt": "2026-07-03"},
        ]

        self.assertEqual(
            growth.split_comparable_windows(
                rows,
                bucket_key=lambda row: row["bucket"],
            ),
            [],
        )

    def test_confidence_depends_on_real_samples_and_consistency(self):
        self.assertEqual(growth.confidence_for_samples(1, 3), "insufficient")
        self.assertEqual(growth.confidence_for_samples(2, 2), "emerging")
        self.assertEqual(growth.confidence_for_samples(3, 3), "moderate")
        self.assertEqual(growth.confidence_for_samples(5, 5, consistent=True), "high")
        self.assertEqual(
            growth.confidence_for_samples(5, 5, consistent=False),
            "moderate",
        )

    def test_faster_time_is_not_improvement_when_success_rate_falls(self):
        metric = growth.compare_duration_metric(
            key="answer_time",
            label="有效作答时间",
            baseline_values=[90, 100, 110],
            current_values=[50, 60, 70],
            baseline_quality=0.90,
            current_quality=0.60,
            source_rows=[
                {"sourceType": "generated_question_attempt", "sourceId": "a-1"},
                {"sourceType": "generated_question_attempt", "sourceId": "a-2"},
            ],
        )

        self.assertEqual(metric["direction"], "declined")
        self.assertIn("正确率或完成率下降", metric["explanation"])
        self.assertEqual(metric["baselineValue"], 100)
        self.assertEqual(metric["currentValue"], 60)

    def test_duration_uses_median_and_reports_traceable_sources(self):
        metric = growth.compare_duration_metric(
            key="recovery_time",
            label="遇错后恢复时间",
            baseline_values=[600, 660, 3600],
            current_values=[360, 420, 480],
            baseline_quality=0.70,
            current_quality=0.80,
            source_rows=[
                {"sourceType": "error_event", "sourceId": "error-17"},
                {"sourceType": "container_command_event", "sourceId": "command-44"},
                {"sourceType": "challenge_completion_event", "sourceId": "completion-9"},
            ],
        )

        self.assertEqual(metric["baselineValue"], 660)
        self.assertEqual(metric["currentValue"], 420)
        self.assertEqual(metric["direction"], "improved")
        self.assertEqual(
            metric["sourceRecordIds"],
            ["error-17", "command-44", "completion-9"],
        )

    def test_rate_metric_returns_honest_sample_counts_and_percentage_points(self):
        metric = growth.compare_rate_metric(
            key="accuracy",
            label="可比题目正确率",
            baseline_success_count=2,
            baseline_sample_count=4,
            current_success_count=4,
            current_sample_count=5,
            source_rows=[
                {"sourceType": "question_submission", "sourceId": "q-1"},
                {"sourceType": "question_submission", "sourceId": "q-2"},
            ],
        )

        self.assertEqual(metric["baselineValue"], 50.0)
        self.assertEqual(metric["currentValue"], 80.0)
        self.assertEqual(metric["changeRate"], 30.0)
        self.assertEqual(metric["direction"], "improved")
        self.assertEqual(metric["confidence"], "moderate")

    def test_builds_five_dimension_deltas_without_inventing_metrics(self):
        result = growth.build_capability_growth(
            student_id=261,
            teaching_class_id=101,
            snapshots=[
                snapshot("start", 60, day=1),
                snapshot("current", 74, day=20),
            ],
            metrics_by_dimension={
                "knowledge_mastery": [
                    growth.compare_rate_metric(
                        key="accuracy",
                        label="可比题目正确率",
                        baseline_success_count=2,
                        baseline_sample_count=4,
                        current_success_count=4,
                        current_sample_count=5,
                        source_rows=[
                            {
                                "sourceType": "generated_question_attempt",
                                "sourceId": "attempt-real-1",
                            }
                        ],
                    )
                ]
            },
            evidence_by_dimension={
                "knowledge_mastery": [
                    {
                        "kind": "ATTEMPT",
                        "title": "完成真实题目作答",
                        "detail": "同知识点近期作答正确",
                        "occurredAt": "2026-07-20T09:00:00",
                        "sourceId": "attempt-real-1",
                        "sourceType": "generated_question_attempt",
                    }
                ]
            },
            data_provenance={
                "mode": "production_events",
                "eligibleRecordCount": 12,
                "excludedRecordCount": 0,
                "unverifiableRecordCount": 0,
                "sourceTypes": ["generated_question_attempt"],
            },
        )

        self.assertEqual(result["overall"]["delta"], 14.0)
        self.assertEqual(len(result["dimensions"]), 5)
        knowledge = result["dimensions"][0]
        self.assertEqual(knowledge["key"], "knowledge_mastery")
        self.assertEqual(knowledge["delta"], 14.0)
        self.assertEqual(knowledge["metrics"][0]["key"], "accuracy")
        self.assertEqual(knowledge["evidence"][0]["sourceId"], "attempt-real-1")
        self.assertEqual(result["calculationVersion"], "capability-growth-v1")

    def test_one_snapshot_returns_current_scores_and_no_fake_delta(self):
        result = growth.build_capability_growth(
            student_id=261,
            teaching_class_id=101,
            snapshots=[snapshot("current", 74, day=20)],
            metrics_by_dimension={},
            evidence_by_dimension={},
            data_provenance={
                "mode": "production_events",
                "eligibleRecordCount": 4,
                "excludedRecordCount": 0,
                "unverifiableRecordCount": 0,
                "sourceTypes": ["api"],
            },
        )

        self.assertIsNone(result["overall"]["baselineScore"])
        self.assertEqual(result["overall"]["currentScore"], 74.0)
        self.assertIsNone(result["overall"]["delta"])
        self.assertEqual(result["message"], "尚未形成成长对比")


if __name__ == "__main__":
    unittest.main()
