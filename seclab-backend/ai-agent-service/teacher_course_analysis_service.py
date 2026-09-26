from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from database import get_connection
from teacher_ai_analysis_service import _call_ai_for_student_analysis, provider_failure_message
from teacher_analysis_repository import AnalysisAlreadyRunningError
from teacher_repository import (
    list_generated_questions_for_teacher,
    require_owned_teaching_class,
    require_student_in_owned_teaching_class,
)
from training_repository import list_generated_question_attempts_for_sessions


USER_SERVICE_SCHEMA = "userservice"
COURSE_ANALYSIS_PROVIDER_TIMEOUT_SECONDS = 30


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _json_loads(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def _latest(attempts: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return attempts[-1] if attempts else None


def build_course_question_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    student_groups: dict[int, dict[str, Any]] = {}
    knowledge_groups: dict[str, dict[str, Any]] = {}
    latest_attempts = [attempt for item in records if (attempt := _latest(item.get("attemptHistory") or []))]

    for item in records:
        student = item.get("student") or {}
        student_id = int(student.get("studentId") or 0)
        student_group = student_groups.setdefault(
            student_id,
            {
                "studentId": student_id,
                "studentName": student.get("studentName") or "未知学生",
                "studentNumber": student.get("studentNumber"),
                "questionCount": 0,
                "attemptCount": 0,
                "correctQuestionCount": 0,
                "incorrectQuestionCount": 0,
            },
        )
        attempts = item.get("attemptHistory") or []
        latest = _latest(attempts)
        student_group["questionCount"] += 1
        student_group["attemptCount"] += len(attempts)
        if latest and latest.get("isCorrect") is True:
            student_group["correctQuestionCount"] += 1
        elif latest and latest.get("isCorrect") is False:
            student_group["incorrectQuestionCount"] += 1

        knowledge_name = str(item.get("knowledgePointName") or "未标注知识点")
        knowledge_group = knowledge_groups.setdefault(
            knowledge_name,
            {
                "knowledgePointName": knowledge_name,
                "questionCount": 0,
                "attemptCount": 0,
                "correctQuestionCount": 0,
                "incorrectQuestionCount": 0,
                "affectedStudentIds": set(),
            },
        )
        knowledge_group["questionCount"] += 1
        knowledge_group["attemptCount"] += len(attempts)
        if latest and latest.get("isCorrect") is True:
            knowledge_group["correctQuestionCount"] += 1
        elif latest and latest.get("isCorrect") is False:
            knowledge_group["incorrectQuestionCount"] += 1
            knowledge_group["affectedStudentIds"].add(student_id)

    attempted_questions = len(latest_attempts)
    correct_questions = sum(1 for item in latest_attempts if item.get("isCorrect") is True)
    incorrect_questions = sum(1 for item in latest_attempts if item.get("isCorrect") is False)
    scores = [float(item.get("score") or 0) for item in latest_attempts]

    students = []
    for item in student_groups.values():
        attempted = item["correctQuestionCount"] + item["incorrectQuestionCount"]
        item["accuracyRate"] = round(item["correctQuestionCount"] / attempted, 4) if attempted else 0.0
        students.append(item)
    students.sort(key=lambda item: (-item["incorrectQuestionCount"], item["studentNumber"] or ""))

    knowledge_points = []
    for item in knowledge_groups.values():
        affected = item.pop("affectedStudentIds")
        attempted = item["correctQuestionCount"] + item["incorrectQuestionCount"]
        item["affectedStudentCount"] = len(affected)
        item["accuracyRate"] = round(item["correctQuestionCount"] / attempted, 4) if attempted else 0.0
        knowledge_points.append(item)
    knowledge_points.sort(key=lambda item: (-item["incorrectQuestionCount"], item["knowledgePointName"]))

    return {
        "studentCount": len(student_groups),
        "questionCount": len(records),
        "attemptedQuestionCount": attempted_questions,
        "attemptCount": sum(len(item.get("attemptHistory") or []) for item in records),
        "correctQuestionCount": correct_questions,
        "incorrectQuestionCount": incorrect_questions,
        "accuracyRate": round(correct_questions / attempted_questions, 4) if attempted_questions else 0.0,
        "averageScore": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "students": students,
        "knowledgePoints": knowledge_points,
    }


def _display_answer(value: Any, limit: int = 180) -> str:
    if value is None:
        return "未记录"
    if isinstance(value, str):
        text = value.strip()
    else:
        text = json.dumps(value, ensure_ascii=False)
    if not text:
        return "未记录"
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def _answer_key(value: Any) -> str:
    return "".join(
        character.lower()
        for character in _display_answer(value)
        if not character.isspace()
    )


def _meaningfully_different_answer(observed: Any, standard: Any) -> bool:
    observed_key = _answer_key(observed)
    standard_key = _answer_key(standard)
    if observed_key in {"", "未记录"} or standard_key in {"", "未记录"}:
        return False
    return observed_key not in standard_key and standard_key not in observed_key


def _teaching_strategy(
    knowledge_name: str,
    *,
    question_title: str,
    student_label: str,
) -> tuple[str, str, str]:
    normalized = knowledge_name.lower()
    if "sql" in normalized and ("联合" in knowledge_name or "列数" in knowledge_name):
        return (
            "作答缺少 ORDER BY 逐级探测、首次报错位置与最终列数之间的完整判断链。",
            f"用《{question_title}》现场演示 ORDER BY 1、2、3…直到首次报错，再用 UNION SELECT NULL 补齐相同列数验证结果。",
            f"让 {student_label} 独立判断一个不同列数的查询；答案必须写出探测序列、首次报错序号和最终列数。",
        )
    if "xss" in normalized or "上下文" in knowledge_name:
        return (
            "作答没有先识别属性上下文，容易把所有输出统一按 HTML 文本转义处理。",
            f"围绕《{question_title}》并排展示同一输入进入 HTML 文本、属性值和 JavaScript 三种位置时的解析差异，再标出引号闭合与危险协议。",
            f"让 {student_label} 对三个输出点先标注上下文，再分别选择编码方式并说明不能通用替换的原因。",
        )
    if "上传" in knowledge_name or "文件类型" in knowledge_name:
        return (
            "作答把扩展名或 Content-Type 当成可信类型，缺少内容特征、存储位置和执行权限的联合校验。",
            f"用《{question_title}》对比扩展名、Content-Type 与文件头三类证据，演示伪造 MIME 后为什么仍需重命名、隔离存储并关闭执行权限。",
            f"让 {student_label} 审核两个上传请求，逐项写出服务端应检查的内容特征、保存路径和权限设置。",
        )
    if "命令" in knowledge_name and "空格" in knowledge_name:
        return (
            "作答只关注普通空格，没有覆盖 IFS、变量展开、重定向等 shell 等价表达。",
            f"用《{question_title}》逐一替换空格并观察命令仍可执行的路径，再对比无 shell 参数化调用。",
            f"让 {student_label} 标出三种绕过路径，并将易受攻击的命令改写为参数数组调用。",
        )
    return (
        "最后作答与参考答案的关键步骤不一致，需要先定位缺失的判断依据。",
        f"以《{question_title}》为例逐句对照学生作答与参考答案，圈出缺失步骤并要求学生解释每一步的验证目的。",
        f"让 {student_label} 完成一道同知识点题，除最终答案外必须写出关键判断步骤和验证依据。",
    )


def _build_knowledge_finding(
    summary_item: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    knowledge_name = str(summary_item["knowledgePointName"])
    wrong_records = []
    for item in records:
        if str(item.get("knowledgePointName") or "未标注知识点") != knowledge_name:
            continue
        latest = _latest(item.get("attemptHistory") or [])
        if latest and latest.get("isCorrect") is False:
            wrong_records.append((item, latest))

    student_names = list(
        dict.fromkeys(
            str((item.get("student") or {}).get("studentName") or "未知学生")
            for item, _ in wrong_records
        )
    )
    representative_item, representative_attempt = next(
        (
            (item, latest)
            for item, latest in wrong_records
            if _meaningfully_different_answer(
                latest.get("answer"),
                item.get("standardAnswer") or item.get("referenceAnswer"),
            )
        ),
        wrong_records[0] if wrong_records else ({}, {}),
    )
    question_title = str(representative_item.get("title") or "未命名题目")
    observed_answer = _display_answer(representative_attempt.get("answer"))
    standard_answer = _display_answer(
        representative_item.get("standardAnswer")
        or representative_item.get("referenceAnswer")
    )
    if not student_names:
        student_names = ["暂无可定位学生"]
    student_label = "、".join(student_names[:4])
    if len(student_names) > 4:
        student_label = f"{student_label}等 {len(student_names)} 人"
    diagnosis, instruction, check = _teaching_strategy(
        knowledge_name,
        question_title=question_title,
        student_label=student_label,
    )
    teacher_action = f"先处理 {student_label}；{instruction}；{check}"
    return {
        **summary_item,
        "evidence": (
            f"{summary_item['questionCount']} 道题中有 {summary_item['incorrectQuestionCount']} 道最后一次仍答错，"
            f"正确率 {summary_item['accuracyRate'] * 100:.0f}%，涉及 {summary_item['affectedStudentCount']} 名学生。"
        ),
        "affectedStudents": student_names,
        "representativeQuestionId": representative_item.get("generatedQuestionId"),
        "representativeQuestionTitle": question_title,
        "observedAnswer": observed_answer,
        "standardAnswer": standard_answer,
        "diagnosis": diagnosis,
        "instruction": instruction,
        "check": check,
        "teacherAction": teacher_action,
    }


def build_course_analysis_fallback(
    records: list[dict[str, Any]],
    *,
    scope: str,
    course: dict[str, Any],
    provider_message: Optional[str] = None,
) -> dict[str, Any]:
    summary = build_course_question_summary(records)
    course_name = str(course.get("courseName") or "当前课程")
    weak = [item for item in summary["knowledgePoints"] if item["incorrectQuestionCount"] > 0][:3]
    representative = []
    for item in records:
        latest = _latest(item.get("attemptHistory") or [])
        if latest and latest.get("isCorrect") is False:
            representative.append(
                {
                    "generatedQuestionId": item.get("generatedQuestionId"),
                    "title": item.get("title") or "未命名题目",
                    "studentName": (item.get("student") or {}).get("studentName"),
                    "knowledgePointName": item.get("knowledgePointName") or "未标注知识点",
                    "latestAnswer": latest.get("answer"),
                    "standardAnswer": item.get("standardAnswer") or item.get("referenceAnswer"),
                    "score": latest.get("score"),
                }
            )
        if len(representative) >= 5:
            break
    focus_text = "、".join(item["knowledgePointName"] for item in weak) or "暂无集中错误知识点"
    return {
        "scope": "student_course" if scope.upper() == "STUDENT" or scope.lower() == "student" else "class_course",
        "courseId": int(course.get("courseId") or 0),
        "courseName": course_name,
        "generatedBy": "course_evidence_fallback",
        "fallbackUsed": True,
        "providerMessage": provider_message,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "overallComment": (
            f"{course_name}共记录 {summary['questionCount']} 道题、{summary['attemptCount']} 次作答，"
            f"按每道题最后一次作答统计正确率为 {summary['accuracyRate'] * 100:.1f}%。重点关注：{focus_text}。"
        ),
        "summary": summary,
        "knowledgeFindings": [
            _build_knowledge_finding(item, records)
            for item in weak
        ],
        "representativeMistakes": representative,
        "teachingSuggestions": [
            "优先讲解最后一次仍答错的题目，并要求学生说明错误原因。",
            "对同一题重试后答对的学生，抽查其修正过程而不只看最终答案。",
            "五维画像仅作为跨课程统计参考，课程结论以本课程真实作答证据为准。",
        ],
    }


class TeacherCourseAnalysisRepository:
    def __init__(
        self,
        connection_factory: Callable[..., Any] = get_connection,
        memory_store: Optional[dict[tuple[int, int, int, str, int], dict[str, Any]]] = None,
    ):
        self.connection_factory = connection_factory
        self.memory_store = memory_store

    @staticmethod
    def _key(teacher_id: int, class_id: int, course_id: int, scope: str, student_id: int) -> tuple[int, int, int, str, int]:
        return teacher_id, class_id, course_id, scope.upper(), student_id

    def _empty(self, key: tuple[int, int, int, str, int]) -> dict[str, Any]:
        teacher_id, class_id, course_id, scope, student_id = key
        return {"teacher_id": teacher_id, "teaching_class_id": class_id, "course_id": course_id, "scope": scope, "student_id": student_id, "analysis_status": "IDLE", "analysis_json": None, "source_stats_json": None, "last_error_message": None, "generated_at": None}

    def ensure_schema(self) -> None:
        if self.memory_store is not None:
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS teacher_course_analysis (
                        teacher_id BIGINT NOT NULL,
                        teaching_class_id BIGINT NOT NULL,
                        course_id INT NOT NULL,
                        analysis_scope VARCHAR(16) NOT NULL,
                        student_id BIGINT NOT NULL DEFAULT 0,
                        analysis_status VARCHAR(16) NOT NULL DEFAULT 'IDLE',
                        analysis_json LONGTEXT NULL,
                        source_stats_json LONGTEXT NULL,
                        data_cutoff_at DATETIME(6) NULL,
                        last_attempt_at DATETIME(6) NULL,
                        last_error_message VARCHAR(500) NULL,
                        generated_at DATETIME(6) NULL,
                        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                        PRIMARY KEY (teacher_id, teaching_class_id, course_id, analysis_scope, student_id),
                        KEY idx_teacher_course_analysis_lookup (teaching_class_id, course_id, analysis_scope, student_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            conn.commit()

    def begin(self, teacher_id: int, class_id: int, course_id: int, scope: str, student_id: int, cutoff: datetime) -> None:
        key = self._key(teacher_id, class_id, course_id, scope, student_id)
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, self._empty(key))
            if row["analysis_status"] == "RUNNING":
                raise AnalysisAlreadyRunningError("course analysis is already running")
            row.update(analysis_status="RUNNING", data_cutoff_at=cutoff, last_attempt_at=datetime.now(), last_error_message=None)
            return
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teacher_course_analysis (teacher_id, teaching_class_id, course_id, analysis_scope, student_id, analysis_status, data_cutoff_at, last_attempt_at)
                    VALUES (%(teacher_id)s, %(class_id)s, %(course_id)s, %(scope)s, %(student_id)s, 'RUNNING', %(cutoff)s, NOW(6))
                    ON DUPLICATE KEY UPDATE analysis_status='RUNNING', data_cutoff_at=VALUES(data_cutoff_at), last_attempt_at=NOW(6), last_error_message=NULL
                    """,
                    {"teacher_id": teacher_id, "class_id": class_id, "course_id": course_id, "scope": scope.upper(), "student_id": student_id, "cutoff": cutoff},
                )
            conn.commit()

    def save_success(self, teacher_id: int, class_id: int, course_id: int, scope: str, student_id: int, cutoff: datetime, analysis: dict[str, Any], stats: dict[str, Any]) -> None:
        key = self._key(teacher_id, class_id, course_id, scope, student_id)
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, self._empty(key))
            row.update(analysis_status="READY", analysis_json=analysis, source_stats_json=stats, data_cutoff_at=cutoff, generated_at=datetime.now(), last_error_message=None)
            return
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teacher_course_analysis (teacher_id, teaching_class_id, course_id, analysis_scope, student_id, analysis_status, analysis_json, source_stats_json, data_cutoff_at, generated_at)
                    VALUES (%(teacher_id)s, %(class_id)s, %(course_id)s, %(scope)s, %(student_id)s, 'READY', %(analysis)s, %(stats)s, %(cutoff)s, NOW(6))
                    ON DUPLICATE KEY UPDATE analysis_status='READY', analysis_json=VALUES(analysis_json), source_stats_json=VALUES(source_stats_json), data_cutoff_at=VALUES(data_cutoff_at), generated_at=NOW(6), last_error_message=NULL
                    """,
                    {"teacher_id": teacher_id, "class_id": class_id, "course_id": course_id, "scope": scope.upper(), "student_id": student_id, "analysis": json.dumps(analysis, ensure_ascii=False), "stats": json.dumps(stats, ensure_ascii=False), "cutoff": cutoff},
                )
            conn.commit()

    def save_failure(self, teacher_id: int, class_id: int, course_id: int, scope: str, student_id: int, message: str) -> None:
        key = self._key(teacher_id, class_id, course_id, scope, student_id)
        if self.memory_store is not None:
            row = self.memory_store.setdefault(key, self._empty(key))
            row["analysis_status"] = "READY" if row.get("analysis_json") else "FAILED"
            row["last_error_message"] = message
            return
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE teacher_course_analysis SET analysis_status=IF(analysis_json IS NULL,'FAILED','READY'), last_error_message=%(message)s WHERE teacher_id=%(teacher_id)s AND teaching_class_id=%(class_id)s AND course_id=%(course_id)s AND analysis_scope=%(scope)s AND student_id=%(student_id)s", {"teacher_id": teacher_id, "class_id": class_id, "course_id": course_id, "scope": scope.upper(), "student_id": student_id, "message": str(message)[:500]})
            conn.commit()

    def get_latest(self, teacher_id: int, class_id: int, course_id: int, scope: str, student_id: int) -> dict[str, Any]:
        key = self._key(teacher_id, class_id, course_id, scope, student_id)
        if self.memory_store is not None:
            row = self.memory_store.get(key, self._empty(key))
        else:
            self.ensure_schema()
            with self.connection_factory() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM teacher_course_analysis WHERE teacher_id=%(teacher_id)s AND teaching_class_id=%(class_id)s AND course_id=%(course_id)s AND analysis_scope=%(scope)s AND student_id=%(student_id)s", {"teacher_id": teacher_id, "class_id": class_id, "course_id": course_id, "scope": scope.upper(), "student_id": student_id})
                    row = cursor.fetchone() or self._empty(key)
        return {"teacherId": teacher_id, "teachingClassId": class_id, "courseId": course_id, "scope": scope.upper(), "studentId": student_id or None, "analysisStatus": row.get("analysis_status") or "IDLE", "analysis": _json_loads(row.get("analysis_json")), "sourceStats": _json_loads(row.get("source_stats_json")), "lastErrorMessage": row.get("last_error_message"), "generatedAt": _iso(row.get("generated_at"))}


COURSE_ANALYSIS_REPOSITORY = TeacherCourseAnalysisRepository()


def require_course_in_owned_class(teacher_id: int, class_id: int, course_id: int) -> dict[str, Any]:
    require_owned_teaching_class(teacher_id, class_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT c.id AS course_id, c.course_name FROM `{USER_SERVICE_SCHEMA}`.`teaching_class_course` tcc INNER JOIN `{USER_SERVICE_SCHEMA}`.`course` c ON c.id=tcc.course_id WHERE tcc.teaching_class_id=%(class_id)s AND tcc.course_id=%(course_id)s LIMIT 1", {"class_id": class_id, "course_id": course_id})
            row = cursor.fetchone()
    if not row:
        raise PermissionError("course is outside the selected teaching class")
    return {"courseId": int(row["course_id"]), "courseName": row.get("course_name") or f"课程 {course_id}"}


def collect_course_question_records(class_id: int, course_id: int, current_user: dict[str, Any], student_id: Optional[int] = None) -> dict[str, Any]:
    teacher_id = int(current_user.get("user_id") or 0)
    course = require_course_in_owned_class(teacher_id, class_id, course_id)
    if student_id is not None:
        require_student_in_owned_teaching_class(teacher_id, class_id, student_id)
    first = list_generated_questions_for_teacher(current_user=current_user, teaching_class_id=class_id, course_id=course_id, student_id=student_id, page=1, size=100)
    records = list(first.get("items") or [])
    page = 2
    while len(records) < int(first.get("total") or 0):
        batch = list_generated_questions_for_teacher(current_user=current_user, teaching_class_id=class_id, course_id=course_id, student_id=student_id, page=page, size=100)
        records.extend(batch.get("items") or [])
        page += 1
    attempts_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # 一条 IN 查询取回全班的作答，别按会话逐个查：139 个会话逐个查要 1.7 秒，合并后 23 毫秒
    session_ids = {item.get("trainingSessionId") for item in records if item.get("trainingSessionId")}
    for attempts in list_generated_question_attempts_for_sessions(session_ids, user_id=student_id).values():
        for attempt in attempts:
            attempts_by_question[str(attempt.get("generated_question_id"))].append({"attemptId": attempt.get("attempt_id"), "answer": attempt.get("answer"), "isCorrect": attempt.get("is_correct"), "score": attempt.get("score"), "costTime": attempt.get("cost_time"), "submittedAt": attempt.get("submitted_at")})
    for item in records:
        item["attemptHistory"] = attempts_by_question.get(str(item.get("generatedQuestionId")), [])
    return {"success": True, "teachingClassId": class_id, "course": course, "studentId": student_id, "items": records, "summary": build_course_question_summary(records)}


def get_course_analysis(class_id: int, course_id: int, current_user: dict[str, Any], student_id: Optional[int] = None) -> dict[str, Any]:
    teacher_id = int(current_user.get("user_id") or 0)
    require_course_in_owned_class(teacher_id, class_id, course_id)
    if student_id is not None:
        require_student_in_owned_teaching_class(teacher_id, class_id, student_id)
    return COURSE_ANALYSIS_REPOSITORY.get_latest(teacher_id, class_id, course_id, "STUDENT" if student_id else "CLASS", student_id or 0)


async def run_course_analysis(class_id: int, course_id: int, current_user: dict[str, Any], student_id: Optional[int] = None) -> dict[str, Any]:
    teacher_id = int(current_user.get("user_id") or 0)
    scope = "STUDENT" if student_id else "CLASS"
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    evidence = collect_course_question_records(class_id, course_id, current_user, student_id)
    if not evidence["items"]:
        raise ValueError("当前课程暂无可分析的做题记录")
    COURSE_ANALYSIS_REPOSITORY.begin(teacher_id, class_id, course_id, scope, student_id or 0, cutoff)
    provider_message = None
    result = None
    prompt = "你是网络安全课程教师助理。请只根据给定课程作答证据返回JSON，字段包括overallComment、knowledgeFindings、representativeMistakes、teachingSuggestions；不得按五维画像组织结论。证据：" + json.dumps(evidence, ensure_ascii=False)
    try:
        payload = await asyncio.wait_for(
            _call_ai_for_student_analysis(
                prompt,
                f"course-{course_id}-{scope.lower()}-{student_id or class_id}",
            ),
            timeout=COURSE_ANALYSIS_PROVIDER_TIMEOUT_SECONDS,
        )
        if isinstance(payload, dict) and payload.get("overallComment"):
            grounded = build_course_analysis_fallback(
                evidence["items"],
                scope=scope,
                course=evidence["course"],
            )
            provider_findings = {
                str(item.get("knowledgePointName") or ""): item
                for item in payload.get("knowledgeFindings") or []
                if isinstance(item, dict)
            }
            result = {
                **payload,
                "scope": "student_course" if student_id else "class_course",
                "courseId": course_id,
                "courseName": evidence["course"]["courseName"],
                "generatedBy": "dify",
                "fallbackUsed": False,
                "providerMessage": None,
                "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "summary": evidence["summary"],
                "knowledgeFindings": [
                    {
                        **item,
                        **provider_findings.get(str(item.get("knowledgePointName") or ""), {}),
                    }
                    for item in grounded["knowledgeFindings"]
                ],
                "representativeMistakes": payload.get("representativeMistakes")
                or grounded["representativeMistakes"],
                "teachingSuggestions": payload.get("teachingSuggestions")
                or grounded["teachingSuggestions"],
            }
    except Exception as exc:
        provider_message = provider_failure_message(exc)
    if result is None:
        result = build_course_analysis_fallback(evidence["items"], scope=scope, course=evidence["course"], provider_message=provider_message)
    COURSE_ANALYSIS_REPOSITORY.save_success(teacher_id, class_id, course_id, scope, student_id or 0, cutoff, result, evidence["summary"])
    return COURSE_ANALYSIS_REPOSITORY.get_latest(teacher_id, class_id, course_id, scope, student_id or 0)
