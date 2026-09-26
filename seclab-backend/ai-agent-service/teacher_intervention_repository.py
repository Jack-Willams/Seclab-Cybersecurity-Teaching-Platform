from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from copy import deepcopy
from typing import Any, Optional
from uuid import uuid4

from database import get_connection
from profile_repository import get_latest_student_profile
from teacher_repository import USER_SERVICE_SCHEMA, require_owned_teaching_class
from training_repository import create_training_session, save_generated_questions


ACTION_TYPES = {"FOCUS_GROUP", "TARGETED_PRACTICE", "LESSON_EXAMPLE"}
INTERVENTION_STATUSES = {"ACTIVE", "COMPLETED", "CANCELLED"}


def build_approved_exercise_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("至少选择一道已审核通过的例题")
    snapshots = []
    for row in rows:
        if str(row.get("review_status") or "").upper() != "APPROVED":
            raise ValueError("只有审核通过的例题可以下发")
        snapshots.append(
            {
                "sourceExerciseId": int(row["exercise_id"]),
                "sourceVersion": int(row.get("source_version") or 1),
                "role": row.get("exercise_role"),
                "questionType": row.get("question_type") or "short_answer",
                "stem": row.get("stem") or "",
                "options": deepcopy(_json_loads(row.get("options_json"), [])),
                "standardAnswer": row.get("standard_answer") or "",
                "explanation": row.get("explanation") or "",
                "difficulty": int(row.get("difficulty") or 1),
                "knowledgePointId": row.get("knowledge_point_id"),
            }
        )
    return snapshots


def build_snapshot_training_questions(
    snapshots: list[dict[str, Any]],
    intervention_id: int,
) -> list[dict[str, Any]]:
    role_labels = {
        "FOUNDATION": "基础例题",
        "CONSOLIDATION": "巩固例题",
        "TRANSFER": "迁移例题",
    }
    questions = []
    for snapshot in snapshots:
        questions.append(
            {
                "question_id": f"assigned-{intervention_id}-{snapshot['sourceExerciseId']}-{uuid4()}",
                "question_type": snapshot.get("questionType") or "short_answer",
                "knowledge_point_id": snapshot.get("knowledgePointId"),
                "difficulty": snapshot.get("difficulty") or 1,
                "title": role_labels.get(str(snapshot.get("role") or "").upper(), "教师个性化练习"),
                "stem": snapshot.get("stem") or "",
                "options": deepcopy(snapshot.get("options") or []),
                "answer": snapshot.get("standardAnswer") or "",
                "reference_answer": snapshot.get("standardAnswer") or "",
                "explanation": snapshot.get("explanation") or "",
                "sourceExerciseId": snapshot.get("sourceExerciseId"),
                "sourceVersion": snapshot.get("sourceVersion"),
                "source": "teacher_approved_exercise",
            }
        )
    return questions


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS teacher_intervention (
      intervention_id BIGINT NOT NULL AUTO_INCREMENT,
      teacher_id BIGINT NOT NULL,
      teaching_class_id BIGINT NOT NULL,
      course_id INT NULL,
      title VARCHAR(255) NOT NULL,
      action_type VARCHAR(32) NOT NULL,
      knowledge_point_id BIGINT NULL,
      description TEXT NULL,
      status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
      baseline_at DATETIME(6) NOT NULL,
      due_at DATETIME(6) NOT NULL,
      created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (intervention_id),
      KEY idx_intervention_class_status_due (teaching_class_id, status, due_at),
      KEY idx_intervention_teacher_time (teacher_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS teacher_intervention_student (
      intervention_id BIGINT NOT NULL,
      student_id BIGINT NOT NULL,
      baseline_snapshot_json JSON NULL,
      latest_snapshot_json JSON NULL,
      assignment_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
      training_session_id VARCHAR(64) NULL,
      started_at DATETIME(6) NULL,
      completed_at DATETIME(6) NULL,
      updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (intervention_id, student_id),
      KEY idx_intervention_student_status (student_id, assignment_status, updated_at),
      KEY idx_intervention_training_session (training_session_id),
      CONSTRAINT fk_intervention_student_parent FOREIGN KEY (intervention_id)
        REFERENCES teacher_intervention (intervention_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS teacher_intervention_question (
      intervention_id BIGINT NOT NULL,
      generated_question_id VARCHAR(64) NOT NULL,
      usage_type VARCHAR(32) NOT NULL,
      created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      PRIMARY KEY (intervention_id, generated_question_id, usage_type),
      KEY idx_intervention_question (generated_question_id, created_at),
      CONSTRAINT fk_intervention_question_parent FOREIGN KEY (intervention_id)
        REFERENCES teacher_intervention (intervention_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS teacher_intervention_exercise_snapshot (
      snapshot_id BIGINT NOT NULL AUTO_INCREMENT,
      intervention_id BIGINT NOT NULL,
      source_exercise_id BIGINT NOT NULL,
      source_version INT NOT NULL,
      snapshot_json LONGTEXT NOT NULL,
      created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      PRIMARY KEY (snapshot_id),
      UNIQUE KEY uk_intervention_exercise_snapshot (intervention_id, source_exercise_id),
      CONSTRAINT fk_intervention_exercise_snapshot_parent FOREIGN KEY (intervention_id)
        REFERENCES teacher_intervention (intervention_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        value = float(value)
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_assignment_learning_summary(row: dict[str, Any]) -> dict[str, Any]:
    question_count = max(
        int(row.get("snapshot_question_count") or 0),
        int(row.get("session_question_count") or 0),
    )
    attempt_count = int(row.get("attempt_count") or 0)
    due_at = row.get("due_at")
    is_overdue = bool(
        due_at
        and row.get("assignment_status") != "COMPLETED"
        and due_at < datetime.utcnow()
    )
    result_summary = None
    if attempt_count:
        result_summary = {
            "attemptCount": attempt_count,
            "correctCount": int(row.get("correct_count") or 0),
            "averageScore": _number(row.get("average_score")) or 0.0,
        }
    return {
        "questionCount": question_count,
        "estimatedMinutes": question_count * 5,
        "isOverdue": is_overdue,
        "resultSummary": result_summary,
    }


def has_completed_assignment(question_count: int, attempted_question_count: int) -> bool:
    return int(question_count or 0) > 0 and int(attempted_question_count or 0) >= int(question_count or 0)


def resolve_assignment_status(current_status: str, question_count: int, attempted_question_count: int) -> str:
    if str(current_status or "").upper() == "COMPLETED":
        return "COMPLETED"
    if has_completed_assignment(question_count, attempted_question_count):
        return "COMPLETED"
    return str(current_status or "PENDING").upper()


def build_metric_snapshot(profile: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not profile:
        return None
    return {
        "snapshotId": profile.get("snapshot_id"),
        "computedAt": _iso(profile.get("computed_at")),
        "scores": {
            "overall": _number(profile.get("overall_score")),
            "knowledgeMastery": _number(profile.get("knowledge_mastery_score")),
            "troubleshooting": _number(profile.get("troubleshooting_score")),
            "autonomy": _number(profile.get("autonomy_score")),
            "aiCollaboration": _number(profile.get("ai_collaboration_score")),
            "engagement": _number(profile.get("engagement_score")),
        },
    }


def compare_metric_snapshots(
    baseline: Optional[dict[str, Any]],
    latest: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if not latest:
        return {"delta": {}, "improvedDimensions": [], "status": "NO_FOLLOW_UP"}
    baseline_scores = (baseline or {}).get("scores") or {}
    latest_scores = latest.get("scores") or {}
    delta = {}
    for key, latest_value in latest_scores.items():
        baseline_value = baseline_scores.get(key)
        if latest_value is None or baseline_value is None:
            continue
        delta[key] = round(float(latest_value) - float(baseline_value), 2)
    return {
        "delta": delta,
        "improvedDimensions": [key for key, value in delta.items() if value > 0],
        "status": "READY",
    }


def _ensure_course_id_column(cursor) -> None:
    cursor.execute(
        """
        SELECT COUNT(*) AS column_exists
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'teacher_intervention'
          AND column_name = 'course_id'
        """
    )
    row = cursor.fetchone() or {}
    if int(row.get("column_exists") or 0) == 0:
        cursor.execute(
            "ALTER TABLE teacher_intervention "
            "ADD COLUMN course_id INT NULL AFTER teaching_class_id"
        )


def ensure_intervention_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
            _ensure_course_id_column(cursor)
        conn.commit()


def _validate_members(cursor, class_id: int, student_ids: list[int]) -> None:
    if not student_ids:
        raise ValueError("至少选择一名学生")
    placeholders = ", ".join(["%s"] * len(student_ids))
    cursor.execute(
        f"""
        SELECT student_id
        FROM `{USER_SERVICE_SCHEMA}`.`teaching_class_student`
        WHERE teaching_class_id = %s AND student_id IN ({placeholders})
        """,
        [class_id, *student_ids],
    )
    found = {int(row["student_id"]) for row in cursor.fetchall() or []}
    if found != set(student_ids):
        raise PermissionError("intervention includes student outside selected teaching class")


def _validate_questions(cursor, class_id: int, question_ids: list[str]) -> None:
    if not question_ids:
        return
    placeholders = ", ".join(["%s"] * len(question_ids))
    cursor.execute(
        f"""
        SELECT DISTINCT gq.generated_question_id
        FROM generated_question gq
        INNER JOIN training_session ts ON ts.training_session_id = gq.training_session_id
        INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class_student` tcs
          ON tcs.student_id = ts.user_id
        WHERE tcs.teaching_class_id = %s
          AND gq.generated_question_id IN ({placeholders})
        """,
        [class_id, *question_ids],
    )
    found = {str(row["generated_question_id"]) for row in cursor.fetchall() or []}
    if found != set(question_ids):
        raise PermissionError("intervention includes question outside selected teaching class")


def _load_approved_exercises(
    cursor,
    *,
    teacher_id: int,
    class_id: int,
    course_id: int,
    knowledge_point_id: Optional[int],
    exercise_ids: list[int],
) -> list[dict[str, Any]]:
    if not exercise_ids:
        return []
    placeholders = ", ".join(["%s"] * len(exercise_ids))
    params: list[Any] = [teacher_id, class_id, course_id, *exercise_ids]
    point_filter = ""
    if knowledge_point_id is not None:
        point_filter = "AND a.knowledge_point_id = %s"
        params.append(knowledge_point_id)
    cursor.execute(
        f"""
        SELECT e.*, a.knowledge_point_id
        FROM teacher_knowledge_exercise e
        INNER JOIN teacher_knowledge_analysis a ON a.analysis_id = e.analysis_id
        WHERE a.teacher_id = %s
          AND a.teaching_class_id = %s
          AND a.course_id = %s
          AND e.exercise_id IN ({placeholders})
          {point_filter}
        ORDER BY e.exercise_id
        """,
        params,
    )
    rows = list(cursor.fetchall() or [])
    if {int(row["exercise_id"]) for row in rows} != set(exercise_ids):
        raise PermissionError("exercise is outside selected teacher, class, experiment or knowledge point")
    return rows


def create_intervention(
    *,
    teacher_id: int,
    class_id: int,
    course_id: Optional[int] = None,
    title: str,
    action_type: str,
    student_ids: list[int],
    knowledge_point_id: Optional[int] = None,
    description: str = "",
    question_ids: Optional[list[str]] = None,
    approved_exercise_ids: Optional[list[int]] = None,
    due_at: Optional[datetime] = None,
) -> dict[str, Any]:
    action_type = str(action_type or "").upper()
    if action_type not in ACTION_TYPES:
        raise ValueError("unsupported intervention action type")
    if not str(title or "").strip():
        raise ValueError("intervention title is required")
    student_ids = sorted({int(value) for value in student_ids})
    question_ids = list(dict.fromkeys(str(value) for value in (question_ids or []) if str(value)))
    approved_exercise_ids = sorted({int(value) for value in (approved_exercise_ids or [])})
    if approved_exercise_ids and course_id is None:
        raise ValueError("下发审核例题时必须指定实验")
    require_owned_teaching_class(teacher_id, class_id)
    ensure_intervention_schema()
    baseline_at = datetime.utcnow()
    due_at = due_at or (baseline_at + timedelta(days=7))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            _validate_members(cursor, class_id, student_ids)
            _validate_questions(cursor, class_id, question_ids)
            exercise_rows = _load_approved_exercises(
                cursor,
                teacher_id=teacher_id,
                class_id=class_id,
                course_id=int(course_id or 0),
                knowledge_point_id=knowledge_point_id,
                exercise_ids=approved_exercise_ids,
            )
            snapshots = build_approved_exercise_snapshots(exercise_rows) if exercise_rows else []
            cursor.execute(
                """
                INSERT INTO teacher_intervention (
                    teacher_id, teaching_class_id, course_id, title, action_type,
                    knowledge_point_id, description, status, baseline_at, due_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s)
                """,
                (
                    teacher_id, class_id, course_id, str(title).strip(), action_type,
                    knowledge_point_id, str(description or "").strip(), baseline_at, due_at,
                ),
            )
            intervention_id = int(cursor.lastrowid)
            for student_id in student_ids:
                baseline = build_metric_snapshot(get_latest_student_profile(student_id))
                cursor.execute(
                    """
                    INSERT INTO teacher_intervention_student (
                        intervention_id, student_id, baseline_snapshot_json, assignment_status
                    ) VALUES (%s, %s, %s, 'PENDING')
                    """,
                    (intervention_id, student_id, _json_dumps(baseline) if baseline else None),
                )
            usage_type = "LESSON_EXAMPLE" if action_type == "LESSON_EXAMPLE" else "ASSIGNED_PRACTICE"
            for question_id in question_ids:
                cursor.execute(
                    """
                    INSERT IGNORE INTO teacher_intervention_question (
                        intervention_id, generated_question_id, usage_type
                    ) VALUES (%s, %s, %s)
                    """,
                    (intervention_id, question_id, usage_type),
                )
            for snapshot in snapshots:
                cursor.execute(
                    """
                    INSERT INTO teacher_intervention_exercise_snapshot (
                      intervention_id, source_exercise_id, source_version, snapshot_json
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        intervention_id,
                        snapshot["sourceExerciseId"],
                        snapshot["sourceVersion"],
                        _json_dumps(snapshot),
                    ),
                )
        conn.commit()
    return get_intervention(teacher_id, class_id, intervention_id)


def _serialize_intervention(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "interventionId": int(row["intervention_id"]),
        "teacherId": int(row["teacher_id"]),
        "teachingClassId": int(row["teaching_class_id"]),
        "courseId": row.get("course_id"),
        "title": row.get("title"),
        "actionType": row.get("action_type"),
        "knowledgePointId": row.get("knowledge_point_id"),
        "description": row.get("description") or "",
        "status": row.get("status"),
        "baselineAt": _iso(row.get("baseline_at")),
        "dueAt": _iso(row.get("due_at")),
        "createdAt": _iso(row.get("created_at")),
        "updatedAt": _iso(row.get("updated_at")),
    }


def get_intervention(teacher_id: int, class_id: int, intervention_id: int) -> dict[str, Any]:
    require_owned_teaching_class(teacher_id, class_id)
    ensure_intervention_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM teacher_intervention
                WHERE intervention_id = %s AND teacher_id = %s AND teaching_class_id = %s
                LIMIT 1
                """,
                (intervention_id, teacher_id, class_id),
            )
            row = cursor.fetchone()
            if not row:
                raise KeyError("intervention does not exist")
            cursor.execute(
                f"""
                SELECT tis.*, u.user_student_number, u.user_name,
                       (SELECT COUNT(*) FROM teacher_intervention_exercise_snapshot ties
                         WHERE ties.intervention_id=tis.intervention_id) AS snapshot_question_count,
                       (SELECT COUNT(*) FROM generated_question gq
                         WHERE gq.training_session_id=tis.training_session_id) AS session_question_count,
                       (SELECT COUNT(*) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id) AS attempt_count,
                       (SELECT COUNT(DISTINCT gqa.generated_question_id) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id) AS attempted_question_count,
                       (SELECT COUNT(*) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id AND gqa.is_correct=1) AS correct_count,
                       (SELECT AVG(gqa.score) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id) AS average_score
                FROM teacher_intervention_student tis
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`user` u ON u.user_id = tis.student_id
                WHERE tis.intervention_id = %s
                ORDER BY u.user_student_number, tis.student_id
                """,
                (intervention_id,),
            )
            student_rows = list(cursor.fetchall() or [])
            cursor.execute(
                """
                SELECT tiq.generated_question_id, tiq.usage_type, gq.title
                FROM teacher_intervention_question tiq
                LEFT JOIN generated_question gq
                  ON gq.generated_question_id = tiq.generated_question_id
                WHERE tiq.intervention_id = %s
                ORDER BY tiq.created_at
                """,
                (intervention_id,),
            )
            question_rows = list(cursor.fetchall() or [])

    result = _serialize_intervention(row)
    completed_count = 0
    students = []
    for item in student_rows:
        baseline = _json_loads(item.get("baseline_snapshot_json"), None)
        latest = _json_loads(item.get("latest_snapshot_json"), None)
        effective_status = resolve_assignment_status(
            item.get("assignment_status"),
            item.get("session_question_count"),
            item.get("attempted_question_count"),
        )
        if effective_status == "COMPLETED":
            completed_count += 1
        students.append(
            {
                "studentId": int(item["student_id"]),
                "studentNumber": item.get("user_student_number"),
                "studentName": item.get("user_name"),
                "assignmentStatus": effective_status,
                "trainingSessionId": item.get("training_session_id"),
                "startedAt": _iso(item.get("started_at")),
                "completedAt": _iso(item.get("completed_at")),
                "baseline": baseline,
                "latest": latest,
                "comparison": compare_metric_snapshots(baseline, latest),
                "resultSummary": build_assignment_learning_summary(item)["resultSummary"],
            }
        )
    result["students"] = students
    result["questions"] = [
        {
            "generatedQuestionId": item.get("generated_question_id"),
            "title": item.get("title") or "训练题",
            "usageType": item.get("usage_type"),
        }
        for item in question_rows
    ]
    result["progress"] = {
        "studentCount": len(students),
        "completedCount": completed_count,
        "completionRate": round(completed_count / len(students), 4) if students else 0.0,
        "evaluationDue": bool(row.get("due_at") and row.get("due_at") <= datetime.utcnow()),
    }
    return result


def list_interventions(teacher_id: int, class_id: int) -> dict[str, Any]:
    require_owned_teaching_class(teacher_id, class_id)
    ensure_intervention_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT intervention_id
                FROM teacher_intervention
                WHERE teacher_id = %s AND teaching_class_id = %s
                ORDER BY created_at DESC, intervention_id DESC
                """,
                (teacher_id, class_id),
            )
            ids = [int(row["intervention_id"]) for row in cursor.fetchall() or []]
    return {"teachingClassId": class_id, "items": [get_intervention(teacher_id, class_id, value) for value in ids]}


def update_intervention_status(
    teacher_id: int,
    class_id: int,
    intervention_id: int,
    status: str,
) -> dict[str, Any]:
    status = str(status or "").upper()
    if status not in INTERVENTION_STATUSES:
        raise ValueError("unsupported intervention status")
    get_intervention(teacher_id, class_id, intervention_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE teacher_intervention SET status = %s WHERE intervention_id = %s",
                (status, intervention_id),
            )
        conn.commit()
    return get_intervention(teacher_id, class_id, intervention_id)


def refresh_intervention_metrics(
    teacher_id: int,
    class_id: int,
    intervention_id: int,
) -> dict[str, Any]:
    intervention = get_intervention(teacher_id, class_id, intervention_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for student in intervention["students"]:
                student_id = int(student["studentId"])
                latest = build_metric_snapshot(get_latest_student_profile(student_id))
                status = student["assignmentStatus"]
                completed_at = None
                if student.get("trainingSessionId"):
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT gq.generated_question_id) AS question_count,
                               COUNT(DISTINCT gqa.generated_question_id) AS attempted_question_count
                        FROM generated_question gq
                        LEFT JOIN generated_question_attempt gqa
                          ON gqa.generated_question_id=gq.generated_question_id
                         AND gqa.training_session_id=gq.training_session_id
                        WHERE gq.training_session_id = %s
                        """,
                        (student["trainingSessionId"],),
                    )
                    completion = cursor.fetchone() or {}
                    if has_completed_assignment(
                        completion.get("question_count"),
                        completion.get("attempted_question_count"),
                    ):
                        status = "COMPLETED"
                        completed_at = datetime.utcnow()
                cursor.execute(
                    """
                    UPDATE teacher_intervention_student
                    SET latest_snapshot_json = %s,
                        assignment_status = %s,
                        completed_at = COALESCE(completed_at, %s)
                    WHERE intervention_id = %s AND student_id = %s
                    """,
                    (
                        _json_dumps(latest) if latest else None,
                        status,
                        completed_at,
                        intervention_id,
                        student_id,
                    ),
                )
        conn.commit()
    return get_intervention(teacher_id, class_id, intervention_id)


def list_student_assignments(student_id: int) -> dict[str, Any]:
    ensure_intervention_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT ti.*, tis.assignment_status, tis.training_session_id,
                       tis.started_at, tis.completed_at,
                       tc.class_name, u.user_name AS teacher_name,
                       c.course_name, kp.name AS knowledge_point_name,
                       (SELECT COUNT(*) FROM teacher_intervention_exercise_snapshot ties
                         WHERE ties.intervention_id=ti.intervention_id) AS snapshot_question_count,
                       (SELECT COUNT(*) FROM generated_question gq
                         WHERE gq.training_session_id=tis.training_session_id) AS session_question_count,
                       (SELECT COUNT(*) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id) AS attempt_count,
                       (SELECT COUNT(DISTINCT gqa.generated_question_id) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id) AS attempted_question_count,
                       (SELECT COUNT(*) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id AND gqa.is_correct=1) AS correct_count,
                       (SELECT AVG(gqa.score) FROM generated_question_attempt gqa
                         WHERE gqa.training_session_id=tis.training_session_id) AS average_score
                FROM teacher_intervention_student tis
                INNER JOIN teacher_intervention ti
                  ON ti.intervention_id = tis.intervention_id
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class` tc
                  ON tc.teaching_class_id = ti.teaching_class_id
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`user` u
                  ON u.user_id = ti.teacher_id
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`course` c
                  ON c.id = ti.course_id
                LEFT JOIN knowledge_point kp
                  ON kp.knowledge_point_id = ti.knowledge_point_id
                WHERE tis.student_id = %s
                  AND ti.status <> 'CANCELLED'
                ORDER BY CASE tis.assignment_status
                           WHEN 'PENDING' THEN 0 WHEN 'STARTED' THEN 1 ELSE 2 END,
                         ti.due_at, ti.created_at DESC
                """,
                (student_id,),
            )
            rows = list(cursor.fetchall() or [])
    items = []
    for row in rows:
        effective_status = resolve_assignment_status(
            row.get("assignment_status"),
            row.get("session_question_count"),
            row.get("attempted_question_count"),
        )
        summary_row = {**row, "assignment_status": effective_status}
        item = _serialize_intervention(row)
        item.update(
            {
                "className": row.get("class_name"),
                "teacherName": row.get("teacher_name"),
                "courseName": row.get("course_name"),
                "knowledgePointName": row.get("knowledge_point_name"),
                "assignmentStatus": effective_status,
                "trainingSessionId": row.get("training_session_id"),
                "startedAt": _iso(row.get("started_at")),
                "completedAt": _iso(row.get("completed_at")),
                **build_assignment_learning_summary(summary_row),
            }
        )
        items.append(item)
    return {"studentId": student_id, "items": items}


def get_student_assignment(student_id: int, intervention_id: int) -> dict[str, Any]:
    items = list_student_assignments(student_id)["items"]
    assignment = next(
        (item for item in items if int(item["interventionId"]) == int(intervention_id)),
        None,
    )
    if not assignment:
        raise KeyError("teacher assignment does not exist")
    return assignment


def mark_student_assignment_started(
    student_id: int,
    intervention_id: int,
    training_session_id: str,
) -> dict[str, Any]:
    assignment = get_student_assignment(student_id, intervention_id)
    existing_session_id = assignment.get("trainingSessionId")
    if existing_session_id:
        return {**assignment, "startedNow": False}
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE teacher_intervention_student
                SET training_session_id = %s,
                    assignment_status = 'STARTED',
                    started_at = COALESCE(started_at, NOW(6))
                WHERE intervention_id = %s AND student_id = %s
                  AND training_session_id IS NULL
                """,
                (training_session_id, intervention_id, student_id),
            )
        conn.commit()
    return {**get_student_assignment(student_id, intervention_id), "startedNow": True}


def load_intervention_exercise_snapshots(intervention_id: int) -> list[dict[str, Any]]:
    ensure_intervention_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT snapshot_json
                FROM teacher_intervention_exercise_snapshot
                WHERE intervention_id = %s
                ORDER BY snapshot_id
                """,
                (intervention_id,),
            )
            rows = list(cursor.fetchall() or [])
    return [_json_loads(row.get("snapshot_json"), {}) for row in rows]


def start_student_assignment_from_snapshots(
    student_id: int,
    intervention_id: int,
) -> Optional[dict[str, Any]]:
    assignment = get_student_assignment(student_id, intervention_id)
    if assignment.get("trainingSessionId"):
        return {**assignment, "startedNow": False, "generation": None}
    snapshots = load_intervention_exercise_snapshots(intervention_id)
    if not snapshots:
        return None
    profile = get_latest_student_profile(student_id)
    training_context = {
        "source": "teacher_approved_exercise",
        "interventionId": intervention_id,
        "knowledgePointId": assignment.get("knowledgePointId"),
        "approvedExerciseIds": [item.get("sourceExerciseId") for item in snapshots],
    }
    session = create_training_session(
        user_id=student_id,
        class_id=assignment.get("teachingClassId"),
        course_id=assignment.get("courseId"),
        profile_snapshot_id=(profile or {}).get("snapshot_id"),
        diagnose_result={
            "user_id": student_id,
            "weak_knowledge_points": [assignment.get("knowledgePointId")],
            "source": "teacher_approved_exercise",
        },
        training_context=training_context,
    )
    questions = build_snapshot_training_questions(snapshots, intervention_id)
    saved = save_generated_questions(
        training_session_id=str(session["training_session_id"]),
        questions=questions,
        source_model="teacher_approved",
    )
    started = mark_student_assignment_started(
        student_id,
        intervention_id,
        str(session["training_session_id"]),
    )
    return {
        **started,
        "generation": {
            "success": True,
            "trainingSessionId": session["training_session_id"],
            "count": len(saved),
            "questions": [
                {
                    "generatedQuestionId": item.get("generated_question_id"),
                    "title": item.get("title"),
                    "stem": item.get("stem"),
                }
                for item in saved
            ],
            "metadata": {"generator": "teacher_approved", "mode": "reviewed_exercise_snapshot"},
        },
    }
