import unittest
from datetime import datetime, timedelta

from teacher_analysis_repository import (
    AnalysisAlreadyRunningError,
    TeacherAnalysisRepository,
    TeacherStudentAnalysisRepository,
)


class TeacherAnalysisRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.store = {}
        self.repository = TeacherAnalysisRepository(memory_store=self.store)
        self.cutoff = datetime(2026, 7, 14, 10, 0, 0)

    def test_begin_analysis_rejects_second_running_request(self):
        self.repository.begin(101, requested_by=7, data_cutoff_at=self.cutoff)

        with self.assertRaises(AnalysisAlreadyRunningError):
            self.repository.begin(101, requested_by=7, data_cutoff_at=self.cutoff)

    def test_failed_refresh_keeps_previous_successful_analysis(self):
        self.repository.begin(101, 7, self.cutoff)
        self.repository.save_success(
            101,
            7,
            self.cutoff,
            {"overallComment": "旧结果"},
            {"studentCount": 20},
        )
        self.repository.begin(101, 7, self.cutoff + timedelta(hours=1))
        self.repository.save_failure(101, "AI 服务暂不可用")

        result = self.repository.get_latest(101)

        self.assertEqual("旧结果", result["analysis"]["overallComment"])
        self.assertEqual("READY", result["analysisStatus"])
        self.assertEqual("AI 服务暂不可用", result["lastErrorMessage"])

    def test_never_run_returns_idle_without_fake_analysis(self):
        result = self.repository.get_latest(999)

        self.assertEqual("IDLE", result["analysisStatus"])
        self.assertIsNone(result["analysis"])


class TeacherStudentAnalysisRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.store = {}
        self.repository = TeacherStudentAnalysisRepository(memory_store=self.store)
        self.cutoff = datetime(2026, 7, 15, 10, 0, 0)

    def test_never_run_returns_idle_without_fake_analysis(self):
        result = self.repository.get_latest(7, 101, 21)

        self.assertEqual("IDLE", result["analysisStatus"])
        self.assertIsNone(result["analysis"])

    def test_begin_rejects_second_running_request(self):
        self.repository.begin(7, 101, 21, self.cutoff)

        with self.assertRaises(AnalysisAlreadyRunningError):
            self.repository.begin(7, 101, 21, self.cutoff)

    def test_failed_refresh_preserves_latest_success(self):
        self.repository.begin(7, 101, 21, self.cutoff)
        self.repository.save_success(
            7,
            101,
            21,
            self.cutoff,
            {"overallComment": "previous result"},
            {"attemptCount": 4},
        )
        self.repository.begin(7, 101, 21, self.cutoff + timedelta(hours=1))
        self.repository.save_failure(7, 101, 21, "provider unavailable")

        result = self.repository.get_latest(7, 101, 21)

        self.assertEqual("READY", result["analysisStatus"])
        self.assertEqual("previous result", result["analysis"]["overallComment"])
        self.assertEqual("provider unavailable", result["lastErrorMessage"])


if __name__ == "__main__":
    unittest.main()
