from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from database import get_connection
from teacher_ai_analysis_service import _call_ai_for_student_analysis
from teacher_learning_insight_repository import get_knowledge_risk_detail


# 顺序固定：模型漏掉 role 字段时按数组下标回填，见 _validate_result
EXERCISE_ROLE_SEQUENCE = ("FOUNDATION", "CONSOLIDATION", "TRANSFER")
EXERCISE_ROLES = set(EXERCISE_ROLE_SEQUENCE)

# 一次分析要模型产出结论 + 三道完整例题，实测 DeepSeek 常在 8~30 秒之间波动，
# 原先写死 20 秒会随机把成功的生成判成失败。
KNOWLEDGE_ANALYSIS_TIMEOUT_SECONDS = float(
    os.getenv("KNOWLEDGE_ANALYSIS_TIMEOUT_SECONDS", "90")
)
REVIEW_STATUSES = {"PENDING_REVIEW", "APPROVED", "NEEDS_REVISION", "REJECTED"}
EDITABLE_FIELDS = {
    "questionType": "question_type",
    "stem": "stem",
    "options": "options_json",
    "standardAnswer": "standard_answer",
    "explanation": "explanation",
    "difficulty": "difficulty",
    "generationRationale": "generation_rationale",
}


class AnalysisAlreadyRunningError(RuntimeError):
    pass


class ProviderUnavailableError(RuntimeError):
    pass


class InvalidAnalysisResultError(ValueError):
    pass


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS teacher_knowledge_analysis (
      analysis_id BIGINT NOT NULL AUTO_INCREMENT,
      teacher_id BIGINT NOT NULL,
      teaching_class_id BIGINT NOT NULL,
      course_id INT NOT NULL,
      knowledge_point_id BIGINT NOT NULL,
      analysis_status VARCHAR(16) NOT NULL DEFAULT 'IDLE',
      analysis_json LONGTEXT NULL,
      evidence_json LONGTEXT NULL,
      last_attempt_at DATETIME(6) NULL,
      last_error_message VARCHAR(500) NULL,
      generated_at DATETIME(6) NULL,
      updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (analysis_id),
      UNIQUE KEY uk_teacher_knowledge_scope (teacher_id, teaching_class_id, course_id, knowledge_point_id),
      KEY idx_teacher_knowledge_lookup (teaching_class_id, course_id, knowledge_point_id, analysis_status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS teacher_knowledge_exercise (
      exercise_id BIGINT NOT NULL AUTO_INCREMENT,
      analysis_id BIGINT NOT NULL,
      exercise_role VARCHAR(24) NOT NULL,
      question_type VARCHAR(32) NOT NULL,
      stem TEXT NOT NULL,
      options_json LONGTEXT NULL,
      standard_answer LONGTEXT NOT NULL,
      explanation LONGTEXT NULL,
      difficulty INT NOT NULL DEFAULT 1,
      generation_rationale TEXT NULL,
      review_status VARCHAR(24) NOT NULL DEFAULT 'PENDING_REVIEW',
      review_comment TEXT NULL,
      source_version INT NOT NULL DEFAULT 1,
      reviewed_by BIGINT NULL,
      reviewed_at DATETIME(6) NULL,
      created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
      PRIMARY KEY (exercise_id),
      UNIQUE KEY uk_teacher_knowledge_exercise_role (analysis_id, exercise_role),
      KEY idx_teacher_knowledge_exercise_review (review_status, updated_at),
      CONSTRAINT fk_teacher_knowledge_exercise_analysis FOREIGN KEY (analysis_id)
        REFERENCES teacher_knowledge_analysis (analysis_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)


def _loads(value: Any, default: Any) -> Any:
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


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_exercise(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "exerciseId": int(row["exercise_id"]),
        "analysisId": int(row["analysis_id"]),
        "role": row.get("exercise_role"),
        "questionType": row.get("question_type"),
        "stem": row.get("stem"),
        "options": _loads(row.get("options_json"), []),
        "standardAnswer": row.get("standard_answer"),
        "explanation": row.get("explanation") or "",
        "difficulty": int(row.get("difficulty") or 1),
        "generationRationale": row.get("generation_rationale") or "",
        "reviewStatus": row.get("review_status") or "PENDING_REVIEW",
        "reviewComment": row.get("review_comment") or "",
        "sourceVersion": int(row.get("source_version") or 1),
        "reviewedBy": row.get("reviewed_by"),
        "reviewedAt": _iso(row.get("reviewed_at")),
        "updatedAt": _iso(row.get("updated_at")),
    }


class KnowledgeAnalysisRepository:
    def __init__(
        self,
        connection_factory: Callable[..., Any] = get_connection,
        memory_store: Optional[dict[Any, Any]] = None,
    ):
        self.connection_factory = connection_factory
        self.memory_store = memory_store

    @staticmethod
    def _key(teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int):
        return teacher_id, class_id, course_id, knowledge_point_id

    def ensure_schema(self) -> None:
        if self.memory_store is not None:
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)
            conn.commit()

    def begin(self, teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int) -> None:
        key = self._key(teacher_id, class_id, course_id, knowledge_point_id)
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, {
                "analysis_id": len([item for item in self.memory_store if isinstance(item, tuple) and len(item) == 4]) + 1,
                "teacher_id": teacher_id,
                "teaching_class_id": class_id,
                "course_id": course_id,
                "knowledge_point_id": knowledge_point_id,
                "analysis_status": "IDLE",
                "analysis_json": None,
                "evidence_json": None,
                "last_error_message": None,
                "generated_at": None,
                "exercises": [],
            })
            if row["analysis_status"] == "RUNNING":
                raise AnalysisAlreadyRunningError("knowledge analysis is already running")
            row.update(analysis_status="RUNNING", last_attempt_at=_utcnow(), last_error_message=None)
            return
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT analysis_status FROM teacher_knowledge_analysis
                    WHERE teacher_id=%s AND teaching_class_id=%s AND course_id=%s AND knowledge_point_id=%s
                    FOR UPDATE
                    """,
                    key,
                )
                current = cursor.fetchone()
                if current and current.get("analysis_status") == "RUNNING":
                    raise AnalysisAlreadyRunningError("knowledge analysis is already running")
                cursor.execute(
                    """
                    INSERT INTO teacher_knowledge_analysis (
                      teacher_id, teaching_class_id, course_id, knowledge_point_id,
                      analysis_status, last_attempt_at, last_error_message
                    ) VALUES (%s,%s,%s,%s,'RUNNING',NOW(6),NULL)
                    ON DUPLICATE KEY UPDATE analysis_status='RUNNING', last_attempt_at=NOW(6), last_error_message=NULL
                    """,
                    key,
                )
            conn.commit()

    def save_success(
        self,
        teacher_id: int,
        class_id: int,
        course_id: int,
        knowledge_point_id: int,
        analysis: dict[str, Any],
        evidence: dict[str, Any],
        exercises: list[dict[str, Any]],
    ) -> None:
        key = self._key(teacher_id, class_id, course_id, knowledge_point_id)
        if self.memory_store is not None:
            row = self.memory_store[key]
            row.update(
                analysis_status="READY",
                analysis_json=analysis,
                evidence_json=evidence,
                last_error_message=None,
                generated_at=_utcnow(),
            )
            stored = []
            for item in exercises:
                exercise_id = max(
                    [value.get("exercise_id", 0) for value in self.memory_store.values() if isinstance(value, dict)] + [0]
                ) + len(stored) + 1
                stored.append({
                    "exercise_id": exercise_id,
                    "analysis_id": row["analysis_id"],
                    "exercise_role": item["role"],
                    "question_type": item["questionType"],
                    "stem": item["stem"],
                    "options_json": item.get("options") or [],
                    "standard_answer": item["standardAnswer"],
                    "explanation": item.get("explanation") or "",
                    "difficulty": item.get("difficulty") or 1,
                    "generation_rationale": item.get("generationRationale") or "",
                    "review_status": "PENDING_REVIEW",
                    "review_comment": "",
                    "source_version": 1,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "updated_at": _utcnow(),
                })
            row["exercises"] = stored
            return
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_knowledge_analysis
                    SET analysis_status='READY', analysis_json=%s, evidence_json=%s,
                        generated_at=NOW(6), last_error_message=NULL
                    WHERE teacher_id=%s AND teaching_class_id=%s AND course_id=%s AND knowledge_point_id=%s
                    """,
                    (_dumps(analysis), _dumps(evidence), *key),
                )
                cursor.execute(
                    """SELECT analysis_id FROM teacher_knowledge_analysis
                    WHERE teacher_id=%s AND teaching_class_id=%s AND course_id=%s AND knowledge_point_id=%s""",
                    key,
                )
                analysis_id = int(cursor.fetchone()["analysis_id"])
                for item in exercises:
                    cursor.execute(
                        """
                        INSERT INTO teacher_knowledge_exercise (
                          analysis_id, exercise_role, question_type, stem, options_json,
                          standard_answer, explanation, difficulty, generation_rationale,
                          review_status, review_comment, source_version, reviewed_by, reviewed_at
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING_REVIEW',NULL,1,NULL,NULL)
                        ON DUPLICATE KEY UPDATE question_type=VALUES(question_type), stem=VALUES(stem),
                          options_json=VALUES(options_json), standard_answer=VALUES(standard_answer),
                          explanation=VALUES(explanation), difficulty=VALUES(difficulty),
                          generation_rationale=VALUES(generation_rationale), review_status='PENDING_REVIEW',
                          review_comment=NULL, source_version=source_version+1, reviewed_by=NULL, reviewed_at=NULL
                        """,
                        (
                            analysis_id, item["role"], item["questionType"], item["stem"],
                            _dumps(item.get("options") or []), item["standardAnswer"],
                            item.get("explanation") or "", item.get("difficulty") or 1,
                            item.get("generationRationale") or "",
                        ),
                    )
            conn.commit()

    def save_failure(self, teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int, message: str) -> None:
        key = self._key(teacher_id, class_id, course_id, knowledge_point_id)
        if self.memory_store is not None:
            row = self.memory_store[key]
            row["analysis_status"] = "READY" if row.get("analysis_json") else "FAILED"
            row["last_error_message"] = str(message)[:500]
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_knowledge_analysis
                    SET analysis_status=IF(analysis_json IS NULL,'FAILED','READY'), last_error_message=%s
                    WHERE teacher_id=%s AND teaching_class_id=%s AND course_id=%s AND knowledge_point_id=%s
                    """,
                    (str(message)[:500], *key),
                )
            conn.commit()

    def _get_memory_exercise(self, teacher_id: int, class_id: int, exercise_id: int):
        for key, row in self.memory_store.items():
            if not isinstance(key, tuple) or len(key) != 4:
                continue
            if key[0] != teacher_id or key[1] != class_id:
                continue
            for exercise in row.get("exercises") or []:
                if int(exercise["exercise_id"]) == int(exercise_id):
                    return exercise
        raise KeyError("knowledge exercise does not exist")

    def update_exercise(self, teacher_id: int, class_id: int, exercise_id: int, changes: dict[str, Any]) -> dict[str, Any]:
        allowed = {key: value for key, value in changes.items() if key in EDITABLE_FIELDS}
        if not allowed:
            raise ValueError("no editable exercise fields supplied")
        if self.memory_store is not None:
            row = self._get_memory_exercise(teacher_id, class_id, exercise_id)
            for key, value in allowed.items():
                row[EDITABLE_FIELDS[key]] = value
            row.update(
                review_status="PENDING_REVIEW",
                review_comment="",
                reviewed_by=None,
                reviewed_at=None,
                source_version=int(row.get("source_version") or 1) + 1,
                updated_at=_utcnow(),
            )
            return _serialize_exercise(row)
        assignments = []
        values = []
        for key, value in allowed.items():
            column = EDITABLE_FIELDS[key]
            assignments.append(f"{column}=%s")
            values.append(_dumps(value) if key == "options" else value)
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE teacher_knowledge_exercise e
                    INNER JOIN teacher_knowledge_analysis a ON a.analysis_id=e.analysis_id
                    SET {', '.join(assignments)}, e.review_status='PENDING_REVIEW',
                        e.review_comment=NULL, e.reviewed_by=NULL, e.reviewed_at=NULL,
                        e.source_version=e.source_version+1
                    WHERE e.exercise_id=%s AND a.teacher_id=%s AND a.teaching_class_id=%s
                    """,
                    (*values, exercise_id, teacher_id, class_id),
                )
                if cursor.rowcount != 1:
                    raise KeyError("knowledge exercise does not exist")
            conn.commit()
        return self.get_exercise(teacher_id, class_id, exercise_id)

    def review_exercise(self, teacher_id: int, class_id: int, exercise_id: int, status: str, comment: str) -> dict[str, Any]:
        status = str(status or "").upper()
        if status not in REVIEW_STATUSES - {"PENDING_REVIEW"}:
            raise ValueError("unsupported exercise review status")
        if self.memory_store is not None:
            row = self._get_memory_exercise(teacher_id, class_id, exercise_id)
            row.update(
                review_status=status,
                review_comment=str(comment or "").strip(),
                reviewed_by=teacher_id,
                reviewed_at=_utcnow(),
                updated_at=_utcnow(),
            )
            return _serialize_exercise(row)
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teacher_knowledge_exercise e
                    INNER JOIN teacher_knowledge_analysis a ON a.analysis_id=e.analysis_id
                    SET e.review_status=%s, e.review_comment=%s, e.reviewed_by=%s, e.reviewed_at=NOW(6)
                    WHERE e.exercise_id=%s AND a.teacher_id=%s AND a.teaching_class_id=%s
                    """,
                    (status, str(comment or "").strip(), teacher_id, exercise_id, teacher_id, class_id),
                )
                if cursor.rowcount != 1:
                    raise KeyError("knowledge exercise does not exist")
            conn.commit()
        return self.get_exercise(teacher_id, class_id, exercise_id)

    def get_exercise(self, teacher_id: int, class_id: int, exercise_id: int) -> dict[str, Any]:
        if self.memory_store is not None:
            return _serialize_exercise(self._get_memory_exercise(teacher_id, class_id, exercise_id))
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT e.* FROM teacher_knowledge_exercise e
                    INNER JOIN teacher_knowledge_analysis a ON a.analysis_id=e.analysis_id
                    WHERE e.exercise_id=%s AND a.teacher_id=%s AND a.teaching_class_id=%s
                    """,
                    (exercise_id, teacher_id, class_id),
                )
                row = cursor.fetchone()
        if not row:
            raise KeyError("knowledge exercise does not exist")
        return _serialize_exercise(row)

    def get(self, teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int) -> dict[str, Any]:
        key = self._key(teacher_id, class_id, course_id, knowledge_point_id)
        if self.memory_store is not None:
            row = self.memory_store.get(key)
            if not row:
                return {
                    "teacherId": teacher_id, "teachingClassId": class_id, "courseId": course_id,
                    "knowledgePointId": knowledge_point_id, "analysisStatus": "IDLE", "analysis": None,
                    "evidence": None, "lastErrorMessage": None, "generatedAt": None, "exercises": [],
                }
            exercises = [_serialize_exercise(item) for item in row.get("exercises") or []]
        else:
            self.ensure_schema()
            with self.connection_factory() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT * FROM teacher_knowledge_analysis
                        WHERE teacher_id=%s AND teaching_class_id=%s AND course_id=%s AND knowledge_point_id=%s""",
                        key,
                    )
                    row = cursor.fetchone()
                    if row:
                        cursor.execute(
                            "SELECT * FROM teacher_knowledge_exercise WHERE analysis_id=%s ORDER BY exercise_id",
                            (row["analysis_id"],),
                        )
                        exercises = [_serialize_exercise(item) for item in cursor.fetchall() or []]
                    else:
                        exercises = []
            if not row:
                return {
                    "teacherId": teacher_id, "teachingClassId": class_id, "courseId": course_id,
                    "knowledgePointId": knowledge_point_id, "analysisStatus": "IDLE", "analysis": None,
                    "evidence": None, "lastErrorMessage": None, "generatedAt": None, "exercises": [],
                }
        return {
            "teacherId": teacher_id,
            "teachingClassId": class_id,
            "courseId": course_id,
            "knowledgePointId": knowledge_point_id,
            "analysisStatus": row.get("analysis_status") or "IDLE",
            "analysis": _loads(row.get("analysis_json"), None),
            "evidence": _loads(row.get("evidence_json"), None),
            "lastErrorMessage": row.get("last_error_message"),
            "generatedAt": _iso(row.get("generated_at")),
            "exercises": exercises,
        }


_DIFFICULTY_WORDS = {
    "easy": 2, "simple": 2, "basic": 2, "beginner": 2,
    "简单": 2, "基础": 2, "低": 2, "入门": 2,
    "medium": 3, "moderate": 3, "normal": 3, "intermediate": 3,
    "中": 3, "中等": 3, "一般": 3,
    "hard": 4, "difficult": 4, "advanced": 4, "challenging": 4,
    "困难": 4, "较难": 4, "高": 4, "进阶": 4,
}


def _coerce_difficulty(value: Any) -> int:
    """把模型给的难度归一到 1-5。

    模型经常返回 "easy"/"medium"/"hard" 而不是数字，直接 int() 会抛 ValueError
    并让整份分析失败，所以这里对文字等级和异常值都给出兜底。
    """
    if isinstance(value, bool):
        return 3
    if isinstance(value, (int, float)):
        return max(1, min(int(value), 5))
    text = str(value or "").strip().lower()
    if not text:
        return 3
    if text.isdigit():
        return max(1, min(int(text), 5))
    for word, level in _DIFFICULTY_WORDS.items():
        if word in text:
            return level
    return 3


def _validate_result(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidAnalysisResultError("AI analysis must be a JSON object")
    for field in ("overallConclusion", "commonMistakes", "teachingAdvice", "exercises"):
        if not payload.get(field):
            raise InvalidAnalysisResultError(f"AI analysis is missing {field}")
    exercises = payload.get("exercises")
    if not isinstance(exercises, list) or len(exercises) != 3:
        raise InvalidAnalysisResultError("AI analysis must contain exactly three exercises")
    # 模型常按顺序输出三道题却不带 role 字段，这里按数组下标回填，
    # 不因为一个可由位置推断的字段把整份分析判失败。
    resolved_roles: list[str] = []
    for index, item in enumerate(exercises):
        if not isinstance(item, dict):
            raise InvalidAnalysisResultError("AI exercise must be a JSON object")
        role = str(item.get("role") or "").strip().upper()
        resolved_roles.append(role or EXERCISE_ROLE_SEQUENCE[index])
    if set(resolved_roles) != EXERCISE_ROLES:
        raise InvalidAnalysisResultError("AI exercises must cover foundation, consolidation and transfer")
    normalized = []
    for index, item in enumerate(exercises):
        if not item.get("stem") or not item.get("standardAnswer"):
            raise InvalidAnalysisResultError("AI exercise is missing stem or standard answer")
        normalized.append({
            **item,
            "role": resolved_roles[index],
            "questionType": item.get("questionType") or "short_answer",
            "options": item.get("options") if isinstance(item.get("options"), list) else [],
            "difficulty": _coerce_difficulty(item.get("difficulty")),
        })
    return {**payload, "exercises": normalized}


class KnowledgeAnalysisService:
    def __init__(
        self,
        repository: KnowledgeAnalysisRepository,
        evidence_loader: Callable[[int, int, int, int], dict[str, Any]],
        provider: Callable[[str, str], Awaitable[dict[str, Any]]],
    ):
        self.repository = repository
        self.evidence_loader = evidence_loader
        self.provider = provider

    def get_analysis(self, teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int):
        return self.repository.get(teacher_id, class_id, course_id, knowledge_point_id)

    async def run_analysis(self, teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int):
        evidence = self.evidence_loader(teacher_id, class_id, course_id, knowledge_point_id)
        if int(evidence.get("attemptedCount") or 0) <= 0:
            raise ValueError("当前知识点暂无可分析的有效作答")
        self.repository.begin(teacher_id, class_id, course_id, knowledge_point_id)
        prompt = (
            "你是网络安全实验课教师助理。只能根据给定知识点证据返回JSON。"
            "字段必须是overallConclusion、commonMistakes、teachingAdvice、exercises。"
            "exercises必须正好三道，每道必须包含role、questionType、stem、options、"
            "standardAnswer、explanation、difficulty、generationRationale这些字段，"
            "三道题的role依次取FOUNDATION、CONSOLIDATION、TRANSFER，不得省略role字段。"
            "不得编造学生姓名、人数或证据。证据：" + _dumps(evidence)
        )
        try:
            raw = await asyncio.wait_for(
                self.provider(prompt, f"knowledge-{class_id}-{course_id}-{knowledge_point_id}"),
                timeout=KNOWLEDGE_ANALYSIS_TIMEOUT_SECONDS,
            )
            result = _validate_result(raw)
        except AnalysisAlreadyRunningError:
            raise
        except Exception as exc:
            self.repository.save_failure(teacher_id, class_id, course_id, knowledge_point_id, str(exc))
            raise ProviderUnavailableError(str(exc)) from exc
        analysis = {key: result[key] for key in ("overallConclusion", "commonMistakes", "teachingAdvice")}
        self.repository.save_success(
            teacher_id, class_id, course_id, knowledge_point_id,
            analysis, evidence, result["exercises"],
        )
        return self.get_analysis(teacher_id, class_id, course_id, knowledge_point_id)

    def update_exercise(self, teacher_id: int, class_id: int, exercise_id: int, changes: dict[str, Any]):
        return self.repository.update_exercise(teacher_id, class_id, exercise_id, changes)

    def review_exercise(self, teacher_id: int, class_id: int, exercise_id: int, status: str, comment: str = ""):
        return self.repository.review_exercise(teacher_id, class_id, exercise_id, status, comment)

    async def regenerate_exercise(self, teacher_id: int, class_id: int, exercise_id: int):
        current = self.repository.get_exercise(teacher_id, class_id, exercise_id)
        prompt = (
            "你是网络安全实验课教师助理。请重新生成一道与原题相同角色的例题，只返回JSON对象，"
            "字段为role、questionType、stem、options、standardAnswer、explanation、difficulty、generationRationale。"
            "不得改变role。原题：" + _dumps(current)
        )
        try:
            raw = await asyncio.wait_for(
                self.provider(prompt, f"knowledge-exercise-{exercise_id}"),
                timeout=KNOWLEDGE_ANALYSIS_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        item = raw.get("exercise") if isinstance(raw, dict) and isinstance(raw.get("exercise"), dict) else raw
        if not isinstance(item, dict) or not item.get("stem") or not item.get("standardAnswer"):
            raise ProviderUnavailableError("AI 未返回完整例题")
        if str(item.get("role") or "").upper() != str(current.get("role") or "").upper():
            raise ProviderUnavailableError("AI 返回的例题角色与原题不一致")
        return self.repository.update_exercise(
            teacher_id,
            class_id,
            exercise_id,
            {
                "questionType": item.get("questionType") or "short_answer",
                "stem": item["stem"],
                "options": item.get("options") if isinstance(item.get("options"), list) else [],
                "standardAnswer": item["standardAnswer"],
                "explanation": item.get("explanation") or "",
                "difficulty": _coerce_difficulty(item.get("difficulty")),
                "generationRationale": item.get("generationRationale") or "",
            },
        )


def _load_evidence(teacher_id: int, class_id: int, course_id: int, knowledge_point_id: int):
    return get_knowledge_risk_detail(teacher_id, class_id, course_id, knowledge_point_id, 1, 100)


async def _provider(prompt: str, user_key: str):
    return await _call_ai_for_student_analysis(prompt, user_key)


KNOWLEDGE_ANALYSIS_REPOSITORY = KnowledgeAnalysisRepository()
KNOWLEDGE_ANALYSIS_SERVICE = KnowledgeAnalysisService(
    KNOWLEDGE_ANALYSIS_REPOSITORY,
    _load_evidence,
    _provider,
)
