from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Optional

from database import get_connection


USER_SERVICE_SCHEMA = "userservice"


class AnalysisAlreadyRunningError(RuntimeError):
    pass


class InsufficientAnalysisDataError(RuntimeError):
    pass


class TeacherAnalysisProviderError(RuntimeError):
    pass


def _json_loads(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


class TeacherAnalysisRepository:
    def __init__(
        self,
        connection_factory: Callable[..., Any] = get_connection,
        memory_store: Optional[dict[int, dict[str, Any]]] = None,
    ):
        self.connection_factory = connection_factory
        self.memory_store = memory_store

    def begin(self, teaching_class_id: int, requested_by: int, data_cutoff_at: datetime) -> None:
        if self.memory_store is not None:
            row = self.memory_store.setdefault(teaching_class_id, self._empty_row(teaching_class_id))
            if row["analysis_status"] == "RUNNING":
                raise AnalysisAlreadyRunningError("analysis is already running")
            row.update(
                analysis_status="RUNNING",
                requested_by=requested_by,
                data_cutoff_at=data_cutoff_at,
                last_attempt_at=datetime.now(),
                last_error_message=None,
            )
            return

        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT analysis_status FROM teacher_class_analysis "
                        "WHERE teaching_class_id = %(class_id)s FOR UPDATE",
                        {"class_id": teaching_class_id},
                    )
                    existing = cursor.fetchone()
                    if existing and existing.get("analysis_status") == "RUNNING":
                        raise AnalysisAlreadyRunningError("analysis is already running")
                    if existing:
                        cursor.execute(
                            """
                            UPDATE teacher_class_analysis
                            SET requested_by = %(requested_by)s,
                                analysis_status = 'RUNNING',
                                data_cutoff_at = %(data_cutoff_at)s,
                                last_attempt_at = NOW(6),
                                last_error_message = NULL
                            WHERE teaching_class_id = %(class_id)s
                            """,
                            {
                                "class_id": teaching_class_id,
                                "requested_by": requested_by,
                                "data_cutoff_at": data_cutoff_at,
                            },
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO teacher_class_analysis (
                                teaching_class_id, requested_by, analysis_status,
                                data_cutoff_at, last_attempt_at
                            ) VALUES (
                                %(class_id)s, %(requested_by)s, 'RUNNING',
                                %(data_cutoff_at)s, NOW(6)
                            )
                            """,
                            {
                                "class_id": teaching_class_id,
                                "requested_by": requested_by,
                                "data_cutoff_at": data_cutoff_at,
                            },
                        )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def save_success(
        self,
        teaching_class_id: int,
        requested_by: int,
        data_cutoff_at: datetime,
        analysis: dict[str, Any],
        source_stats: dict[str, Any],
    ) -> None:
        generated_at = datetime.now()
        if self.memory_store is not None:
            row = self.memory_store.setdefault(teaching_class_id, self._empty_row(teaching_class_id))
            row.update(
                requested_by=requested_by,
                analysis_status="READY",
                data_cutoff_at=data_cutoff_at,
                analysis_json=analysis,
                source_stats_json=source_stats,
                last_error_message=None,
                generated_at=generated_at,
            )
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_class_analysis
                    SET requested_by = %(requested_by)s,
                        analysis_status = 'READY',
                        data_cutoff_at = %(data_cutoff_at)s,
                        analysis_json = %(analysis_json)s,
                        source_stats_json = %(source_stats_json)s,
                        last_error_message = NULL,
                        generated_at = NOW(6)
                    WHERE teaching_class_id = %(class_id)s
                    """,
                    {
                        "class_id": teaching_class_id,
                        "requested_by": requested_by,
                        "data_cutoff_at": data_cutoff_at,
                        "analysis_json": json.dumps(analysis, ensure_ascii=False),
                        "source_stats_json": json.dumps(source_stats, ensure_ascii=False),
                    },
                )
            conn.commit()

    def save_failure(self, teaching_class_id: int, message: str) -> None:
        error_message = str(message or "AI 服务暂不可用")[:500]
        if self.memory_store is not None:
            row = self.memory_store.setdefault(teaching_class_id, self._empty_row(teaching_class_id))
            row["analysis_status"] = "READY" if row.get("analysis_json") else "IDLE"
            row["last_error_message"] = error_message
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_class_analysis
                    SET analysis_status = CASE WHEN analysis_json IS NULL THEN 'IDLE' ELSE 'READY' END,
                        last_error_message = %(message)s
                    WHERE teaching_class_id = %(class_id)s
                    """,
                    {"class_id": teaching_class_id, "message": error_message},
                )
            conn.commit()

    def get_latest(self, teaching_class_id: int) -> dict[str, Any]:
        if self.memory_store is not None:
            return self._to_result(
                self.memory_store.get(teaching_class_id, self._empty_row(teaching_class_id))
            )
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM teacher_class_analysis WHERE teaching_class_id = %(class_id)s LIMIT 1",
                    {"class_id": teaching_class_id},
                )
                row = cursor.fetchone() or self._empty_row(teaching_class_id)
        return self._to_result(row)

    @staticmethod
    def _empty_row(teaching_class_id: int) -> dict[str, Any]:
        return {
            "teaching_class_id": teaching_class_id,
            "analysis_status": "IDLE",
            "analysis_json": None,
            "source_stats_json": None,
            "generated_at": None,
            "data_cutoff_at": None,
            "last_error_message": None,
        }

    @staticmethod
    def _to_result(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "teachingClassId": int(row.get("teaching_class_id") or 0),
            "analysisStatus": row.get("analysis_status") or "IDLE",
            "analysis": _json_loads(row.get("analysis_json")),
            "sourceStats": _json_loads(row.get("source_stats_json")),
            "generatedAt": _iso(row.get("generated_at")),
            "dataCutoffAt": _iso(row.get("data_cutoff_at")),
            "lastErrorMessage": row.get("last_error_message"),
        }


class TeacherStudentAnalysisRepository:
    def __init__(
        self,
        connection_factory: Callable[..., Any] = get_connection,
        memory_store: Optional[dict[tuple[int, int, int], dict[str, Any]]] = None,
    ):
        self.connection_factory = connection_factory
        self.memory_store = memory_store

    @staticmethod
    def _key(teacher_id: int, teaching_class_id: int, student_id: int) -> tuple[int, int, int]:
        return int(teacher_id), int(teaching_class_id), int(student_id)

    def begin(
        self,
        teacher_id: int,
        teaching_class_id: int,
        student_id: int,
        data_cutoff_at: datetime,
    ) -> None:
        key = self._key(teacher_id, teaching_class_id, student_id)
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, self._empty_row(*key))
            if row["analysis_status"] == "RUNNING":
                raise AnalysisAlreadyRunningError("analysis is already running")
            row.update(
                analysis_status="RUNNING",
                data_cutoff_at=data_cutoff_at,
                last_attempt_at=datetime.now(),
                last_error_message=None,
            )
            return
        params = {
            "teacher_id": teacher_id,
            "class_id": teaching_class_id,
            "student_id": student_id,
            "data_cutoff_at": data_cutoff_at,
        }
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT analysis_status FROM teacher_student_analysis
                        WHERE teacher_id = %(teacher_id)s
                          AND teaching_class_id = %(class_id)s
                          AND student_id = %(student_id)s
                        FOR UPDATE
                        """,
                        params,
                    )
                    existing = cursor.fetchone()
                    if existing and existing.get("analysis_status") == "RUNNING":
                        raise AnalysisAlreadyRunningError("analysis is already running")
                    if existing:
                        cursor.execute(
                            """
                            UPDATE teacher_student_analysis
                            SET analysis_status = 'RUNNING',
                                data_cutoff_at = %(data_cutoff_at)s,
                                last_attempt_at = NOW(6),
                                last_error_message = NULL
                            WHERE teacher_id = %(teacher_id)s
                              AND teaching_class_id = %(class_id)s
                              AND student_id = %(student_id)s
                            """,
                            params,
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO teacher_student_analysis (
                                teacher_id, teaching_class_id, student_id,
                                analysis_status, data_cutoff_at, last_attempt_at
                            ) VALUES (
                                %(teacher_id)s, %(class_id)s, %(student_id)s,
                                'RUNNING', %(data_cutoff_at)s, NOW(6)
                            )
                            """,
                            params,
                        )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def save_success(
        self,
        teacher_id: int,
        teaching_class_id: int,
        student_id: int,
        data_cutoff_at: datetime,
        analysis: dict[str, Any],
        source_stats: dict[str, Any],
    ) -> None:
        key = self._key(teacher_id, teaching_class_id, student_id)
        generated_at = datetime.now()
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, self._empty_row(*key))
            row.update(
                analysis_status="READY",
                data_cutoff_at=data_cutoff_at,
                analysis_json=analysis,
                source_stats_json=source_stats,
                last_error_message=None,
                generated_at=generated_at,
            )
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_student_analysis
                    SET analysis_status = 'READY',
                        data_cutoff_at = %(data_cutoff_at)s,
                        analysis_json = %(analysis_json)s,
                        source_stats_json = %(source_stats_json)s,
                        last_error_message = NULL,
                        generated_at = NOW(6)
                    WHERE teacher_id = %(teacher_id)s
                      AND teaching_class_id = %(class_id)s
                      AND student_id = %(student_id)s
                    """,
                    {
                        "teacher_id": teacher_id,
                        "class_id": teaching_class_id,
                        "student_id": student_id,
                        "data_cutoff_at": data_cutoff_at,
                        "analysis_json": json.dumps(analysis, ensure_ascii=False),
                        "source_stats_json": json.dumps(source_stats, ensure_ascii=False),
                    },
                )
            conn.commit()

    def save_failure(
        self,
        teacher_id: int,
        teaching_class_id: int,
        student_id: int,
        message: str,
    ) -> None:
        key = self._key(teacher_id, teaching_class_id, student_id)
        error_message = str(message or "AI 服务暂不可用")[:500]
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, self._empty_row(*key))
            row["analysis_status"] = "READY" if row.get("analysis_json") else "IDLE"
            row["last_error_message"] = error_message
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_student_analysis
                    SET analysis_status = CASE WHEN analysis_json IS NULL THEN 'IDLE' ELSE 'READY' END,
                        last_error_message = %(message)s
                    WHERE teacher_id = %(teacher_id)s
                      AND teaching_class_id = %(class_id)s
                      AND student_id = %(student_id)s
                    """,
                    {
                        "teacher_id": teacher_id,
                        "class_id": teaching_class_id,
                        "student_id": student_id,
                        "message": error_message,
                    },
                )
            conn.commit()

    def get_latest(self, teacher_id: int, teaching_class_id: int, student_id: int) -> dict[str, Any]:
        key = self._key(teacher_id, teaching_class_id, student_id)
        if self.memory_store is not None:
            return self._to_result(self.memory_store.get(key, self._empty_row(*key)))
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM teacher_student_analysis
                    WHERE teacher_id = %(teacher_id)s
                      AND teaching_class_id = %(class_id)s
                      AND student_id = %(student_id)s
                    LIMIT 1
                    """,
                    {"teacher_id": teacher_id, "class_id": teaching_class_id, "student_id": student_id},
                )
                row = cursor.fetchone() or self._empty_row(*key)
        return self._to_result(row)

    @staticmethod
    def _empty_row(teacher_id: int, teaching_class_id: int, student_id: int) -> dict[str, Any]:
        return {
            "teacher_id": teacher_id,
            "teaching_class_id": teaching_class_id,
            "student_id": student_id,
            "analysis_status": "IDLE",
            "analysis_json": None,
            "source_stats_json": None,
            "generated_at": None,
            "data_cutoff_at": None,
            "last_error_message": None,
        }

    @staticmethod
    def _to_result(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "teacherId": int(row.get("teacher_id") or 0),
            "teachingClassId": int(row.get("teaching_class_id") or 0),
            "studentId": int(row.get("student_id") or 0),
            "analysisStatus": row.get("analysis_status") or "IDLE",
            "analysis": _json_loads(row.get("analysis_json")),
            "sourceStats": _json_loads(row.get("source_stats_json")),
            "generatedAt": _iso(row.get("generated_at")),
            "dataCutoffAt": _iso(row.get("data_cutoff_at")),
            "lastErrorMessage": row.get("last_error_message"),
        }


def require_teaching_class_owner(teaching_class_id: int, teacher_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT teaching_class_id, class_name, teacher_id, status
                FROM `{USER_SERVICE_SCHEMA}`.`teaching_class`
                WHERE teaching_class_id = %(class_id)s
                LIMIT 1
                """,
                {"class_id": teaching_class_id},
            )
            row = cursor.fetchone()
    if not row:
        raise KeyError(f"teaching class does not exist: {teaching_class_id}")
    if int(row.get("teacher_id") or 0) != int(teacher_id):
        raise PermissionError("only the teaching class owner can start analysis")
    return row


def collect_teaching_class_analysis_evidence(teaching_class_id: int) -> dict[str, Any]:
    from teacher_repository import summarize_generated_questions_for_class

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT tc.teaching_class_id, tc.class_name,
                       COUNT(DISTINCT tcs.student_id) AS student_count
                FROM `{USER_SERVICE_SCHEMA}`.`teaching_class` tc
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class_student` tcs
                  ON tcs.teaching_class_id = tc.teaching_class_id
                WHERE tc.teaching_class_id = %(class_id)s
                GROUP BY tc.teaching_class_id, tc.class_name
                """,
                {"class_id": teaching_class_id},
            )
            class_row = cursor.fetchone()
            if not class_row:
                raise KeyError(f"teaching class does not exist: {teaching_class_id}")
            student_count = int(class_row.get("student_count") or 0)
            if student_count == 0:
                raise InsufficientAnalysisDataError("教学班暂无学生，不能进行分析")

            cursor.execute(
                f"""
                SELECT c.id AS course_id, c.course_name, tcc.teaching_order
                FROM `{USER_SERVICE_SCHEMA}`.`teaching_class_course` tcc
                INNER JOIN `{USER_SERVICE_SCHEMA}`.`course` c ON c.id = tcc.course_id
                WHERE tcc.teaching_class_id = %(class_id)s
                ORDER BY tcc.teaching_order
                """,
                {"class_id": teaching_class_id},
            )
            courses = list(cursor.fetchall() or [])

            cursor.execute(
                f"""
                SELECT COUNT(*) AS event_count,
                       SUM(CASE WHEN le.event_type IN ('LAB_START', 'START_LAB') THEN 1 ELSE 0 END) AS lab_start_count,
                       SUM(CASE WHEN le.event_type IN ('LAB_COMPLETE', 'CHALLENGE_COMPLETE') THEN 1 ELSE 0 END) AS lab_complete_count,
                       SUM(CASE WHEN le.event_type IN ('HINT_REQUEST', 'AI_INTERACTION') THEN 1 ELSE 0 END) AS hint_count,
                       SUM(CASE WHEN le.event_type IN ('ERROR_EVENT', 'FLAG_SUBMIT_FAILED') THEN 1 ELSE 0 END) AS failure_count
                FROM learning_event le
                INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class_student` tcs
                  ON tcs.student_id = le.user_id
                WHERE tcs.teaching_class_id = %(class_id)s
                """,
                {"class_id": teaching_class_id},
            )
            event_stats = cursor.fetchone() or {}

    question_summary = summarize_generated_questions_for_class(teaching_class_id)
    summary_items = question_summary.get("items") or []
    generated_count = sum(int(item.get("generatedQuestionCount") or 0) for item in summary_items)
    event_count = int(event_stats.get("event_count") or 0)
    if generated_count == 0 and event_count == 0:
        raise InsufficientAnalysisDataError("教学班暂无学习或训练记录，不能进行分析")
    question_ids = sorted(
        {
            question_id
            for item in summary_items
            for question_id in item.get("representativeQuestionIds") or []
            if question_id
        }
    )
    return {
        "teachingClassId": teaching_class_id,
        "className": class_row.get("class_name"),
        "studentCount": student_count,
        "courses": courses,
        "eventStats": {
            "eventCount": event_count,
            "labStartCount": int(event_stats.get("lab_start_count") or 0),
            "labCompleteCount": int(event_stats.get("lab_complete_count") or 0),
            "hintCount": int(event_stats.get("hint_count") or 0),
            "failureCount": int(event_stats.get("failure_count") or 0),
        },
        "generatedQuestionSummary": summary_items,
        "evidenceQuestionIds": question_ids,
    }
