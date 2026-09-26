from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Iterable, Optional

from capability_growth_service import (
    build_capability_growth,
    compare_duration_metric,
    compare_rate_metric,
    split_comparable_windows,
)
from database import get_connection
from profile_repository import (
    build_data_provenance,
    is_growth_eligible_snapshot,
    is_production_source,
)
from teacher_repository import require_student_in_owned_teaching_class


ROWSET_KEYS = (
    "questionRows",
    "commandRows",
    "completionRows",
    "aiMessageRows",
    "labRows",
)


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def partition_production_rows(
    rowsets: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    clean: dict[str, list[dict[str, Any]]] = {}
    source_counts: dict[str, int] = defaultdict(int)
    eligible_count = 0
    excluded_count = 0
    unverifiable_count = 0
    for key, rows in rowsets.items():
        clean_rows: list[dict[str, Any]] = []
        for raw_row in rows:
            row = dict(raw_row)
            source = str(row.get("originSource") or "").strip()
            if not source:
                unverifiable_count += 1
                continue
            source_counts[source] += 1
            if is_production_source(source):
                eligible_count += 1
                clean_rows.append(row)
            else:
                excluded_count += 1
        clean[key] = clean_rows
    provenance = build_data_provenance(
        dict(source_counts),
        eligible_count,
        excluded_count,
        unverifiable_count,
    )
    if eligible_count > 0:
        provenance["mode"] = "production_events"
    return clean, provenance


def _combined_windows(
    rows: Iterable[dict[str, Any]],
    bucket_fields: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    comparisons = split_comparable_windows(
        rows,
        bucket_key=lambda row: tuple(row.get(field) for field in bucket_fields)
        if all(row.get(field) not in (None, "") for field in bucket_fields)
        else None,
    )
    baseline_rows: list[dict[str, Any]] = []
    current_rows: list[dict[str, Any]] = []
    for item in comparisons:
        baseline_rows.extend(item["baselineRows"])
        current_rows.extend(item["currentRows"])
    return baseline_rows, current_rows


def _rate(
    rows: Iterable[dict[str, Any]],
    field: str,
) -> tuple[int, int, float]:
    values = [bool(row.get(field)) for row in rows]
    successes = sum(1 for value in values if value)
    return successes, len(values), successes / len(values) if values else 0.0


def build_question_growth(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows = list(rows)
    baseline, current = _combined_windows(
        source_rows,
        ("knowledgePointId", "questionType", "difficulty"),
    )
    if not baseline or not current:
        return [], _question_evidence(source_rows)

    baseline_success, baseline_count, baseline_quality = _rate(baseline, "isCorrect")
    current_success, current_count, current_quality = _rate(current, "isCorrect")
    comparison_sources = baseline + current
    metrics = [
        compare_rate_metric(
            key="accuracy",
            label="可比题目正确率",
            baseline_success_count=baseline_success,
            baseline_sample_count=baseline_count,
            current_success_count=current_success,
            current_sample_count=current_count,
            source_rows=comparison_sources,
        )
    ]
    baseline_times = [
        row.get("costTime") for row in baseline if row.get("costTime") is not None
    ]
    current_times = [
        row.get("costTime") for row in current if row.get("costTime") is not None
    ]
    if len(baseline_times) >= 2 and len(current_times) >= 2:
        metrics.append(
            compare_duration_metric(
                key="answer_time",
                label="有效作答时间",
                baseline_values=baseline_times,
                current_values=current_times,
                baseline_quality=baseline_quality,
                current_quality=current_quality,
                source_rows=comparison_sources,
            )
        )
    return metrics, _question_evidence(source_rows)


def _question_evidence(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: _as_datetime(row.get("occurredAt")), reverse=True)
    return [
        {
            "kind": "ATTEMPT",
            "title": str(row.get("title") or "真实题目作答"),
            "detail": "作答正确" if row.get("isCorrect") else "作答未正确",
            "occurredAt": _iso(row.get("occurredAt")),
            "sourceId": str(row.get("sourceId") or ""),
            "sourceType": str(row.get("sourceType") or ""),
            # 下面这些是作答本身的业务明细。原先只回标题和 ID，前端的证据详情就只能显示
            # 「该历史记录没有保存更多业务明细」——可追溯的证据链等于断在最后一步。
            "knowledgePointId": row.get("knowledgePointId"),
            "knowledgePointName": row.get("knowledgePointName"),
            "questionType": row.get("questionType"),
            "difficulty": row.get("difficulty"),
            "costTime": row.get("costTime"),
            "isCorrect": bool(row.get("isCorrect")),
        }
        for row in ordered[:5]
    ]


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _recovery_rows(
    command_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_session_category: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in command_rows:
        session_id = row.get("labSessionId")
        category = row.get("commandCategory")
        if session_id and category:
            by_session_category[(session_id, category)].append(dict(row))

    recovered: list[dict[str, Any]] = []
    for (session_id, category), rows in by_session_category.items():
        ordered = sorted(rows, key=lambda row: _as_datetime(row.get("occurredAt")))
        for index, failed in enumerate(ordered):
            if failed.get("exitCode") in (0, "0"):
                continue
            failed_at = _as_datetime(failed.get("occurredAt"))
            success = next(
                (
                    candidate
                    for candidate in ordered[index + 1 :]
                    if candidate.get("exitCode") in (0, "0")
                ),
                None,
            )
            if not success:
                continue
            recovered.append(
                {
                    "sourceId": str(failed.get("sourceId") or ""),
                    "sourceType": "container_command_event",
                    "occurredAt": failed.get("occurredAt"),
                    "bucket": category,
                    "labSessionId": session_id,
                    "moduleId": failed.get("moduleId"),
                    "taskId": failed.get("taskId"),
                    # 带上两条命令原文，证据详情才能给出「哪条失败、改成什么才通过」
                    "failedCommand": failed.get("commandText"),
                    "recoveredCommand": success.get("commandText"),
                    "recoverySeconds": max(
                        0,
                        (
                            _as_datetime(success.get("occurredAt")) - failed_at
                        ).total_seconds(),
                    ),
                    "sourceRows": [failed, success],
                }
            )
            break
    return recovered


def build_troubleshooting_growth(
    command_rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    commands = list(command_rows)
    recovery_rows = _recovery_rows(commands)
    baseline, current = _combined_windows(recovery_rows, ("bucket",))
    metrics: list[dict[str, Any]] = []
    if baseline and current:
        comparison_rows = baseline + current
        source_rows = [
            source
            for item in comparison_rows
            for source in item.get("sourceRows") or []
        ]
        metrics.append(
            compare_duration_metric(
                key="recovery_time",
                label="遇错后恢复时间",
                baseline_values=[row["recoverySeconds"] for row in baseline],
                current_values=[row["recoverySeconds"] for row in current],
                baseline_quality=1.0,
                current_quality=1.0,
                source_rows=source_rows,
            )
        )

    evidence = [
        {
            "kind": "ERROR_RECOVERY",
            "title": "失败命令后完成同类命令恢复",
            "detail": f"恢复用时 {int(row['recoverySeconds'])} 秒",
            "occurredAt": _iso(row.get("occurredAt")),
            "sourceId": str(row.get("sourceId") or ""),
            "sourceType": "container_command_event",
            "labSessionId": row.get("labSessionId"),
            "moduleId": row.get("moduleId"),
            "taskId": row.get("taskId"),
            "commandCategory": row.get("bucket"),
            "recoverySeconds": int(row["recoverySeconds"]),
            "failedCommand": row.get("failedCommand"),
            "recoveredCommand": row.get("recoveredCommand"),
        }
        for row in sorted(
            recovery_rows,
            key=lambda item: _as_datetime(item.get("occurredAt")),
            reverse=True,
        )[:5]
    ]
    return metrics, evidence


def _build_rate_dimension(
    rows: Iterable[dict[str, Any]],
    *,
    bucket_fields: tuple[str, ...],
    success_field: str,
    key: str,
    label: str,
    evidence_kind: str,
    evidence_title: str,
    evidence_fields: tuple[str, ...] = (),
    detail_builder: Optional[Callable[[dict[str, Any]], str]] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows = list(rows)
    baseline, current = _combined_windows(source_rows, bucket_fields)
    metrics: list[dict[str, Any]] = []
    if baseline and current:
        baseline_success, baseline_count, _ = _rate(baseline, success_field)
        current_success, current_count, _ = _rate(current, success_field)
        metrics.append(
            compare_rate_metric(
                key=key,
                label=label,
                baseline_success_count=baseline_success,
                baseline_sample_count=baseline_count,
                current_success_count=current_success,
                current_sample_count=current_count,
                source_rows=baseline + current,
            )
        )
    evidence = [
        {
            "kind": evidence_kind,
            "title": evidence_title,
            "detail": detail_builder(row) if detail_builder else str(row.get("detail") or ""),
            "occurredAt": _iso(row.get("occurredAt")),
            "sourceId": str(row.get("sourceId") or ""),
            "sourceType": str(row.get("sourceType") or ""),
            # evidence_fields 让各维度把自己的业务明细带到证据详情里，
            # 否则前端只能显示「该历史记录没有保存更多业务明细」
            **{field: row.get(field) for field in evidence_fields},
        }
        for row in sorted(
            source_rows,
            key=lambda item: _as_datetime(item.get("occurredAt")),
            reverse=True,
        )[:5]
    ]
    return metrics, evidence


def _event_type_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]


def build_lab_evidence(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: _as_datetime(row.get("occurredAt")),
        reverse=True,
    )
    evidence: list[dict[str, Any]] = []
    for row in ordered[:5]:
        source_id = str(row.get("sourceId") or "")
        module_id = row.get("moduleId")
        module_name = str(row.get("moduleName") or "").strip()
        target_url = str(row.get("targetUrl") or "").strip()
        title = module_name or (
            f"实验模块 {module_id}" if module_id is not None else f"实验会话 {source_id}"
        )
        evidence.append(
            {
                "kind": "LAB",
                "title": title,
                "detail": f"访问 {target_url}" if target_url else "未记录访问地址",
                "occurredAt": _iso(row.get("occurredAt")),
                "sourceId": source_id,
                "sourceType": str(row.get("sourceType") or ""),
                "labSessionId": source_id,
                "courseId": row.get("courseId"),
                "moduleId": module_id,
                "taskId": row.get("taskId"),
                "moduleName": module_name or None,
                "status": row.get("status"),
                "startedAt": _iso(row.get("startedAt")),
                "endedAt": _iso(row.get("endedAt")),
                "durationSeconds": row.get("durationSeconds"),
                "targetUrl": target_url or None,
                "containerName": row.get("containerName"),
                "eventCount": int(row.get("eventCount") or 0),
                "eventTypes": _event_type_list(row.get("eventTypes")),
            }
        )
    return evidence


def build_ai_evidence(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: _as_datetime(row.get("occurredAt")),
        reverse=True,
    )
    evidence: list[dict[str, Any]] = []
    for row in ordered[:5]:
        content = str(row.get("messageContent") or "").strip()
        module_name = str(row.get("moduleName") or "").strip()
        evidence.append(
            {
                "kind": "AI",
                "title": f"提问：{content}" if content else "AI 提问内容未记录",
                "detail": (
                    f"{module_name} · {'包含实验上下文' if row.get('isContextRich') else '未包含实验上下文'}"
                    if module_name
                    else ("包含实验上下文" if row.get("isContextRich") else "未包含实验上下文")
                ),
                "occurredAt": _iso(row.get("occurredAt")),
                "sourceId": str(row.get("sourceId") or ""),
                "sourceType": str(row.get("sourceType") or ""),
                "conversationId": row.get("conversationId"),
                "moduleId": row.get("moduleId"),
                "taskId": row.get("taskId"),
                "moduleName": module_name or None,
                "messageContent": content or None,
            }
        )
    return evidence


def _fetch_rows(cursor, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    cursor.execute(sql, params)
    return list(cursor.fetchall() or [])


def _load_growth_rows(
    student_id: int,
    teaching_class_id: Optional[int],
) -> dict[str, list[dict[str, Any]]]:
    params = {"student_id": student_id, "class_id": teaching_class_id}
    class_filter = (
        "AND class_id = %(class_id)s"
        if teaching_class_id is not None
        else ""
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            snapshots = _fetch_rows(
                cursor,
                f"""
                SELECT *
                FROM student_profile_snapshot
                WHERE user_id = %(student_id)s
                  {class_filter}
                ORDER BY computed_at ASC, created_at ASC
                """,
                params,
            )
            question_rows = _fetch_rows(
                cursor,
                """
                SELECT
                    'generated_question_attempt' AS sourceType,
                    gqa.attempt_id AS sourceId,
                    ts.source_type AS originSource,
                    gq.knowledge_point_id AS knowledgePointId,
                    gq.question_type AS questionType,
                    gq.difficulty AS difficulty,
                    gqa.is_correct AS isCorrect,
                    gqa.cost_time AS costTime,
                    gqa.submitted_at AS occurredAt,
                    gq.title AS title,
                    gq_kp.name AS knowledgePointName
                FROM generated_question_attempt gqa
                INNER JOIN generated_question gq
                  ON gq.generated_question_id = gqa.generated_question_id
                INNER JOIN training_session ts
                  ON ts.training_session_id = gqa.training_session_id
                LEFT JOIN knowledge_point gq_kp
                  ON gq_kp.knowledge_point_id = gq.knowledge_point_id
                WHERE gqa.user_id = %(student_id)s
                  AND (%(class_id)s IS NULL OR ts.class_id = %(class_id)s)
                  AND gq.knowledge_point_id IS NOT NULL
                  AND gq.question_type IS NOT NULL
                  AND gq.difficulty IS NOT NULL

                UNION ALL

                SELECT
                    'question_submission' AS sourceType,
                    qs.submission_id AS sourceId,
                    qs.question_source AS originSource,
                    qs.knowledge_point_id AS knowledgePointId,
                    qs.question_type AS questionType,
                    kp.difficulty_level AS difficulty,
                    qs.is_correct AS isCorrect,
                    qs.cost_time AS costTime,
                    qs.created_at AS occurredAt,
                    COALESCE(kp.name, '课程题目') AS title,
                    kp.name AS knowledgePointName
                FROM question_submission qs
                LEFT JOIN knowledge_point kp
                  ON kp.knowledge_point_id = qs.knowledge_point_id
                WHERE qs.user_id = %(student_id)s
                  AND (%(class_id)s IS NULL OR qs.class_id = %(class_id)s)
                  AND qs.knowledge_point_id IS NOT NULL
                  AND qs.question_type IS NOT NULL
                  AND kp.difficulty_level IS NOT NULL
                ORDER BY occurredAt ASC
                """,
                params,
            )
            command_rows = _fetch_rows(
                cursor,
                """
                SELECT
                    'container_command_event' AS sourceType,
                    command_id AS sourceId,
                    source AS originSource,
                    lab_session_id AS labSessionId,
                    module_id AS moduleId,
                    task_id AS taskId,
                    cmd_category AS commandCategory,
                    command AS commandText,
                    exit_code AS exitCode,
                    duration_ms AS durationMs,
                    executed_at AS occurredAt
                FROM container_command_event
                WHERE user_id = %(student_id)s
                  AND (%(class_id)s IS NULL OR class_id = %(class_id)s)
                ORDER BY executed_at ASC
                """,
                params,
            )
            completion_rows = _fetch_rows(
                cursor,
                """
                SELECT
                    'challenge_completion_event' AS sourceType,
                    CAST(cce.id AS CHAR) AS sourceId,
                    COALESCE(
                        (
                            SELECT le.source FROM learning_event le
                            WHERE le.lab_session_id = cce.lab_session_id
                            ORDER BY le.event_time ASC LIMIT 1
                        ),
                        (
                            SELECT cmd.source FROM container_command_event cmd
                            WHERE cmd.lab_session_id = cce.lab_session_id
                            ORDER BY cmd.executed_at ASC LIMIT 1
                        )
                    ) AS originSource,
                    cce.lab_session_id AS labSessionId,
                    COALESCE(kp.difficulty_level, 'unknown') AS difficulty,
                    cce.completion_status = 'completed' AS isCompleted,
                    cce.total_ai_ask_count = 0 AS isIndependent,
                    cce.total_ai_ask_count AS aiAskCount,
                    cce.total_time_seconds AS activeSeconds,
                    cce.created_at AS occurredAt
                FROM challenge_completion_event cce
                LEFT JOIN task_knowledge_point tkp
                  ON tkp.module_id = cce.module_id AND tkp.task_id = cce.task_id
                LEFT JOIN knowledge_point kp
                  ON kp.knowledge_point_id = tkp.knowledge_point_id
                WHERE cce.user_id = %(student_id)s
                  AND (%(class_id)s IS NULL OR cce.class_id = %(class_id)s)
                GROUP BY cce.id, kp.difficulty_level
                ORDER BY cce.created_at ASC
                """,
                params,
            )
            ai_message_rows = _fetch_rows(
                cursor,
                """
                SELECT
                    'ai_message' AS sourceType,
                    m.message_id AS sourceId,
                    c.source AS originSource,
                    c.conversation_id AS conversationId,
                    c.module_id AS moduleId,
                    c.task_id AS taskId,
                    module_catalog.module_name AS moduleName,
                    m.content AS messageContent,
                    (m.contains_context = 1 OR m.contains_error_excerpt = 1) AS isContextRich,
                    m.created_at AS occurredAt
                FROM ai_message m
                INNER JOIN ai_conversation c
                  ON c.conversation_id = m.conversation_id
                LEFT JOIN userservice.module module_catalog
                  ON module_catalog.module_id = c.module_id
                WHERE c.user_id = %(student_id)s
                  AND m.role = 'user'
                  AND (%(class_id)s IS NULL OR c.class_id = %(class_id)s)
                ORDER BY m.created_at ASC
                """,
                params,
            )
            lab_rows = _fetch_rows(
                cursor,
                """
                SELECT
                    'lab_session' AS sourceType,
                    ls.session_id AS sourceId,
                    COALESCE(
                        (
                            SELECT le.source FROM learning_event le
                            WHERE le.lab_session_id = ls.session_id
                            ORDER BY le.event_time ASC LIMIT 1
                        ),
                        (
                            SELECT cmd.source FROM container_command_event cmd
                            WHERE cmd.lab_session_id = ls.session_id
                            ORDER BY cmd.executed_at ASC LIMIT 1
                        )
                    ) AS originSource,
                    ls.course_id AS courseId,
                    ls.module_id AS moduleId,
                    ls.task_id AS taskId,
                    module_catalog.module_name AS moduleName,
                    COALESCE(kp.difficulty_level, 'unknown') AS difficulty,
                    ls.status = 'completed' AS isCompleted,
                    ls.status AS status,
                    ls.container_name AS containerName,
                    ls.target_url AS targetUrl,
                    ls.start_time AS startedAt,
                    ls.end_time AS endedAt,
                    CASE
                        WHEN ls.end_time IS NULL THEN NULL
                        ELSE TIMESTAMPDIFF(SECOND, ls.start_time, ls.end_time)
                    END AS durationSeconds,
                    (
                        SELECT COUNT(*)
                        FROM learning_event event_count
                        WHERE event_count.lab_session_id = ls.session_id
                    ) AS eventCount,
                    (
                        SELECT GROUP_CONCAT(
                            DISTINCT event_type.event_type
                            ORDER BY event_type.event_time
                            SEPARATOR ','
                        )
                        FROM learning_event event_type
                        WHERE event_type.lab_session_id = ls.session_id
                    ) AS eventTypes,
                    ls.start_time AS occurredAt
                FROM lab_session ls
                LEFT JOIN userservice.module module_catalog
                  ON module_catalog.module_id = ls.module_id
                LEFT JOIN task_knowledge_point tkp
                  ON tkp.module_id = ls.module_id AND tkp.task_id = ls.task_id
                LEFT JOIN knowledge_point kp
                  ON kp.knowledge_point_id = tkp.knowledge_point_id
                WHERE ls.user_id = %(student_id)s
                  AND (%(class_id)s IS NULL OR ls.class_id = %(class_id)s)
                GROUP BY
                    ls.session_id,
                    ls.course_id,
                    ls.module_id,
                    ls.task_id,
                    module_catalog.module_name,
                    kp.difficulty_level,
                    ls.status,
                    ls.container_name,
                    ls.target_url,
                    ls.start_time,
                    ls.end_time
                ORDER BY ls.start_time ASC
                """,
                params,
            )
    return {
        "snapshots": snapshots,
        "questionRows": question_rows,
        "commandRows": command_rows,
        "completionRows": completion_rows,
        "aiMessageRows": ai_message_rows,
        "labRows": lab_rows,
    }


def _snapshot_provenance(snapshots: Iterable[dict[str, Any]]) -> dict[str, Any]:
    eligible = [item for item in snapshots if is_growth_eligible_snapshot(item)]
    if not eligible:
        return {}
    latest = max(eligible, key=lambda item: _as_datetime(item.get("computed_at")))
    summary = _json_object(latest.get("profile_summary_json"))
    provenance = summary.get("data_provenance")
    return dict(provenance) if isinstance(provenance, dict) else {}


def get_student_capability_growth(
    student_id: int,
    teaching_class_id: Optional[int] = None,
) -> dict[str, Any]:
    loaded = _load_growth_rows(student_id, teaching_class_id)
    behavior_rows = {
        key: list(loaded.get(key) or [])
        for key in ROWSET_KEYS
    }
    clean, behavior_provenance = partition_production_rows(behavior_rows)
    metrics_by_dimension: dict[str, list[dict[str, Any]]] = {}
    evidence_by_dimension: dict[str, list[dict[str, Any]]] = {}

    metrics_by_dimension["knowledge_mastery"], evidence_by_dimension["knowledge_mastery"] = (
        build_question_growth(clean["questionRows"])
    )
    metrics_by_dimension["troubleshooting"], evidence_by_dimension["troubleshooting"] = (
        build_troubleshooting_growth(clean["commandRows"])
    )
    metrics_by_dimension["autonomy"], evidence_by_dimension["autonomy"] = (
        _build_rate_dimension(
            clean["completionRows"],
            bucket_fields=("difficulty",),
            success_field="isIndependent",
            key="independent_completion_rate",
            label="无直接求助完成率",
            evidence_kind="SUCCESS",
            evidence_title="真实实验完成记录",
            evidence_fields=("labSessionId", "difficulty", "aiAskCount", "activeSeconds"),
            detail_builder=lambda row: (
                "独立完成，未向 AI 求助"
                if not int(row.get("aiAskCount") or 0)
                else f"完成前向 AI 求助 {int(row.get('aiAskCount') or 0)} 次"
            ),
        )
    )
    metrics_by_dimension["ai_collaboration"], _ = _build_rate_dimension(
        clean["aiMessageRows"],
        bucket_fields=("moduleId", "taskId"),
        success_field="isContextRich",
        key="context_rich_question_rate",
        label="包含上下文的 AI 提问比例",
        evidence_kind="AI",
        evidence_title="真实 AI 提问记录",
    )
    evidence_by_dimension["ai_collaboration"] = build_ai_evidence(clean["aiMessageRows"])
    metrics_by_dimension["engagement"], _ = _build_rate_dimension(
        clean["labRows"],
        bucket_fields=("difficulty",),
        success_field="isCompleted",
        key="lab_completion_rate",
        label="同难度实验完成率",
        evidence_kind="LAB",
        evidence_title="真实实验会话",
    )
    evidence_by_dimension["engagement"] = build_lab_evidence(clean["labRows"])

    provenance = _snapshot_provenance(loaded.get("snapshots") or [])
    if behavior_provenance.get("eligibleRecordCount", 0) > 0:
        source_types = sorted(
            set(provenance.get("sourceTypes") or [])
            | set(behavior_provenance.get("sourceTypes") or [])
        )
        provenance.update(behavior_provenance)
        provenance["mode"] = "production_events"
        provenance["sourceTypes"] = source_types
    elif not provenance:
        provenance = behavior_provenance

    return build_capability_growth(
        student_id=student_id,
        teaching_class_id=teaching_class_id,
        snapshots=loaded.get("snapshots") or [],
        metrics_by_dimension=metrics_by_dimension,
        evidence_by_dimension=evidence_by_dimension,
        data_provenance=provenance,
    )


def get_teacher_student_capability_growth(
    teacher_id: int,
    class_id: int,
    student_id: int,
) -> dict[str, Any]:
    require_student_in_owned_teaching_class(teacher_id, class_id, student_id)
    return get_student_capability_growth(student_id, class_id)
