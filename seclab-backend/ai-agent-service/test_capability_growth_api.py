import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main


class CapabilityGrowthApiTest(unittest.TestCase):
    def test_student_and_teacher_growth_routes_are_registered(self):
        paths = {route.path for route in main.app.routes}

        self.assertIn(
            "/api/students/{student_id}/capability-growth",
            paths,
        )
        self.assertIn(
            "/api/teacher/teaching-classes/{class_id}/students/{student_id}/capability-growth",
            paths,
        )

    def test_student_growth_endpoint_accepts_self_and_uses_authenticated_identity(self):
        expected = {"studentId": 261, "calculationVersion": "capability-growth-v1"}
        with patch.object(
            main,
            "get_student_capability_growth",
            return_value=expected,
        ) as load_growth:
            result = asyncio.run(
                main.student_capability_growth(
                    student_id=261,
                    teachingClassId=101,
                    current_user={"role": "student", "user_id": 261},
                )
            )

        self.assertEqual(result, expected)
        load_growth.assert_called_once_with(261, 101)

    def test_student_growth_endpoint_rejects_another_student(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                main.student_capability_growth(
                    student_id=262,
                    teachingClassId=101,
                    current_user={"role": "student", "user_id": 261},
                )
            )

        self.assertEqual(raised.exception.status_code, 403)

    def test_teacher_growth_endpoint_uses_authenticated_teacher_id(self):
        expected = {"studentId": 261, "teachingClassId": 101}
        with patch.object(
            main,
            "get_teacher_student_capability_growth",
            return_value=expected,
        ) as load_growth:
            result = asyncio.run(
                main.teacher_student_capability_growth(
                    class_id=101,
                    student_id=261,
                    current_user={"role": "teacher", "user_id": 7},
                )
            )

        self.assertEqual(result, expected)
        load_growth.assert_called_once_with(7, 101, 261)


if __name__ == "__main__":
    unittest.main()
