import unittest
from unittest.mock import call, patch

import teacher_profile_service


class _Cursor:
    def __init__(self, student_ids):
        self.student_ids = student_ids

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _sql, params):
        self.class_id = params["class_id"]

    def fetchall(self):
        return [{"student_id": student_id} for student_id in self.student_ids]


class _Connection:
    def __init__(self, student_ids):
        self.cursor_instance = _Cursor(student_ids)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_instance


class TeacherProfileServiceTest(unittest.TestCase):
    def test_rebuilds_only_members_after_owner_check(self):
        with (
            patch.object(teacher_profile_service, "require_owned_teaching_class") as owner_check,
            patch.object(teacher_profile_service, "get_connection", return_value=_Connection([21, 22])),
            patch.object(
                teacher_profile_service,
                "rebuild_student_profile",
                side_effect=[{"snapshot_id": "p-21"}, {"snapshot_id": "p-22"}],
            ) as rebuild,
        ):
            result = teacher_profile_service.rebuild_teaching_class_profiles(101, 7)

        owner_check.assert_called_once_with(7, 101)
        self.assertEqual(rebuild.call_args_list, [call(21), call(22)])
        self.assertEqual(result["studentCount"], 2)
        self.assertEqual(result["rebuiltCount"], 2)
        self.assertEqual(result["failedCount"], 0)
        self.assertEqual(result["failures"], [])

    def test_one_student_failure_does_not_abort_remaining_rebuilds(self):
        with (
            patch.object(teacher_profile_service, "require_owned_teaching_class"),
            patch.object(teacher_profile_service, "get_connection", return_value=_Connection([21, 22, 23])),
            patch.object(
                teacher_profile_service,
                "rebuild_student_profile",
                side_effect=[{"snapshot_id": "p-21"}, RuntimeError("bad evidence"), {"snapshot_id": "p-23"}],
            ),
        ):
            result = teacher_profile_service.rebuild_teaching_class_profiles(101, 7)

        self.assertEqual(result["rebuiltCount"], 2)
        self.assertEqual(result["failedCount"], 1)
        self.assertEqual(result["failures"], [{"studentId": 22, "message": "画像生成失败"}])
        self.assertNotIn("bad evidence", str(result))


if __name__ == "__main__":
    unittest.main()
