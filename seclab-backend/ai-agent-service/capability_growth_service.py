from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import median
from typing import Any, Callable, Hashable, Iterable, Optional

from profile_repository import CALCULATION_VERSION, is_growth_eligible_snapshot


DIMENSIONS = (
    ("knowledge_mastery", "知识掌握", "knowledge_mastery_score"),
    ("troubleshooting", "故障排查", "troubleshooting_score"),
    ("autonomy", "自主学习", "autonomy_score"),
    ("ai_collaboration", "AI 协同", "ai_collaboration_score"),
    ("engagement", "学习投入", "engagement_score"),
)

CONFIDENCE_ORDER = {
    "insufficient": 0,
    "emerging": 1,
    "moderate": 2,
    "high": 3,
}


def _timestamp(value: Any) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).timestamp()
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 2)


def _delta(baseline: Any, current: Any) -> Optional[float]:
    if baseline is None or current is None:
        return None
    return round(float(current) - float(baseline), 2)


def select_growth_snapshots(
    snapshots: Iterable[dict[str, Any]],
) -> tuple[
    Optional[dict[str, Any]],
    Optional[dict[str, Any]],
    list[dict[str, Any]],
]:
    eligible = sorted(
        (dict(item) for item in snapshots if is_growth_eligible_snapshot(item)),
        key=lambda item: (
            _timestamp(item.get("computed_at")),
            str(item.get("snapshot_id") or ""),
        ),
    )
    if not eligible:
        return None, None, []
    if len(eligible) == 1:
        return None, eligible[0], eligible
    return eligible[0], eligible[-1], eligible


def split_comparable_windows(
    rows: Iterable[dict[str, Any]],
    bucket_key: Callable[[dict[str, Any]], Hashable],
    window_size: int = 3,
) -> list[dict[str, Any]]:
    groups: dict[Hashable, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        bucket = bucket_key(row)
        if bucket is None:
            continue
        groups[bucket].append(dict(row))

    comparisons: list[dict[str, Any]] = []
    for bucket, bucket_rows in groups.items():
        ordered = sorted(
            bucket_rows,
            key=lambda item: (
                _timestamp(item.get("occurredAt") or item.get("occurred_at")),
                str(item.get("sourceId") or item.get("source_id") or ""),
            ),
        )
        side_count = min(max(0, int(window_size)), len(ordered) // 2)
        if side_count < 2:
            continue
        baseline_rows = ordered[:side_count]
        current_rows = ordered[-side_count:]
        baseline_ids = [
            str(item.get("sourceId") or item.get("source_id") or "")
            for item in baseline_rows
        ]
        current_ids = [
            str(item.get("sourceId") or item.get("source_id") or "")
            for item in current_rows
        ]
        if set(baseline_ids) & set(current_ids):
            continue
        comparisons.append(
            {
                "bucket": bucket,
                "baselineRows": baseline_rows,
                "currentRows": current_rows,
                "baselineIds": baseline_ids,
                "currentIds": current_ids,
            }
        )
    return comparisons


def confidence_for_samples(
    baseline_count: int,
    current_count: int,
    consistent: bool = False,
) -> str:
    smallest = min(max(0, int(baseline_count)), max(0, int(current_count)))
    if smallest < 2:
        return "insufficient"
    if smallest == 2:
        return "emerging"
    if smallest >= 5 and consistent:
        return "high"
    return "moderate"


def _source_metadata(
    source_rows: Iterable[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    source_types: list[str] = []
    record_ids: list[str] = []
    for row in source_rows:
        source_type = str(
            row.get("sourceType") or row.get("source_type") or ""
        ).strip()
        source_id = str(row.get("sourceId") or row.get("source_id") or "").strip()
        if source_type and source_type not in source_types:
            source_types.append(source_type)
        if source_id and source_id not in record_ids:
            record_ids.append(source_id)
    return source_types, record_ids


def compare_rate_metric(
    *,
    key: str,
    label: str,
    baseline_success_count: int,
    baseline_sample_count: int,
    current_success_count: int,
    current_sample_count: int,
    source_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline_count = max(0, int(baseline_sample_count))
    current_count = max(0, int(current_sample_count))
    confidence = confidence_for_samples(baseline_count, current_count)
    baseline_value = (
        round(int(baseline_success_count) / baseline_count * 100, 2)
        if baseline_count
        else None
    )
    current_value = (
        round(int(current_success_count) / current_count * 100, 2)
        if current_count
        else None
    )
    change = _delta(baseline_value, current_value)
    direction = "insufficient"
    if confidence != "insufficient" and change is not None:
        direction = "improved" if change > 0 else "declined" if change < 0 else "stable"
    source_types, record_ids = _source_metadata(source_rows)
    if direction == "insufficient":
        explanation = (
            f"{label}的早期样本为 {baseline_count} 个、近期样本为 {current_count} 个，"
            "暂不判断变化。"
        )
    else:
        explanation = (
            f"{label}由 {baseline_value:.1f}% 变为 {current_value:.1f}%，"
            f"变化 {abs(change or 0):.1f} 个百分点。"
        )
    return {
        "key": key,
        "label": label,
        "baselineValue": baseline_value,
        "currentValue": current_value,
        "unit": "percent",
        "changeRate": change,
        "direction": direction,
        "baselineSampleCount": baseline_count,
        "currentSampleCount": current_count,
        "confidence": confidence,
        "explanation": explanation,
        "sourceTypes": source_types,
        "sourceRecordIds": record_ids,
    }


def compare_duration_metric(
    *,
    key: str,
    label: str,
    baseline_values: Iterable[int | float],
    current_values: Iterable[int | float],
    baseline_quality: float,
    current_quality: float,
    source_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline_data = [float(item) for item in baseline_values if item is not None]
    current_data = [float(item) for item in current_values if item is not None]
    baseline_count = len(baseline_data)
    current_count = len(current_data)
    confidence = confidence_for_samples(baseline_count, current_count)
    baseline_value = round(float(median(baseline_data)), 2) if baseline_data else None
    current_value = round(float(median(current_data)), 2) if current_data else None
    change = None
    if baseline_value not in (None, 0) and current_value is not None:
        change = round((current_value - baseline_value) / baseline_value * 100, 2)

    direction = "insufficient"
    quality_declined = float(current_quality) < float(baseline_quality)
    if confidence != "insufficient" and baseline_value is not None and current_value is not None:
        if quality_declined:
            direction = "declined"
        elif current_value < baseline_value:
            direction = "improved"
        elif current_value > baseline_value:
            direction = "declined"
        else:
            direction = "stable"

    source_types, record_ids = _source_metadata(source_rows)
    if direction == "insufficient":
        explanation = (
            f"{label}的早期样本为 {baseline_count} 个、近期样本为 {current_count} 个，"
            "暂不判断变化。"
        )
    elif quality_declined:
        explanation = (
            f"{label}虽由 {baseline_value:.0f} 秒变为 {current_value:.0f} 秒，"
            "但正确率或完成率下降，因此不认定为效率提升。"
        )
    else:
        explanation = (
            f"{label}中位数由 {baseline_value:.0f} 秒变为 {current_value:.0f} 秒，"
            "同时正确率或完成率没有下降。"
        )
    return {
        "key": key,
        "label": label,
        "baselineValue": baseline_value,
        "currentValue": current_value,
        "unit": "seconds",
        "changeRate": change,
        "direction": direction,
        "baselineSampleCount": baseline_count,
        "currentSampleCount": current_count,
        "confidence": confidence,
        "explanation": explanation,
        "sourceTypes": source_types,
        "sourceRecordIds": record_ids,
    }


def _dimension_confidence(metrics: list[dict[str, Any]]) -> str:
    if not metrics:
        return "insufficient"
    return max(
        (str(item.get("confidence") or "insufficient") for item in metrics),
        key=lambda item: CONFIDENCE_ORDER.get(item, 0),
    )


def _history_item(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = {
        "snapshotId": snapshot.get("snapshot_id"),
        "computedAt": _iso(snapshot.get("computed_at")),
        "overallScore": _number(snapshot.get("overall_score")),
    }
    for key, _, field in DIMENSIONS:
        result[f"{key}Score"] = _number(snapshot.get(field))
    return result


def build_capability_growth(
    *,
    student_id: int,
    teaching_class_id: Optional[int],
    snapshots: Iterable[dict[str, Any]],
    metrics_by_dimension: dict[str, list[dict[str, Any]]],
    evidence_by_dimension: dict[str, list[dict[str, Any]]],
    data_provenance: dict[str, Any],
) -> dict[str, Any]:
    baseline, current, eligible_history = select_growth_snapshots(snapshots)
    history = eligible_history[-8:]
    baseline_overall = _number(baseline.get("overall_score")) if baseline else None
    current_overall = _number(current.get("overall_score")) if current else None

    dimensions: list[dict[str, Any]] = []
    for key, label, score_field in DIMENSIONS:
        metrics = list(metrics_by_dimension.get(key) or [])
        evidence = list(evidence_by_dimension.get(key) or [])
        baseline_score = _number(baseline.get(score_field)) if baseline else None
        current_score = _number(current.get(score_field)) if current else None
        summary = (
            str(metrics[0].get("explanation") or "")
            if metrics
            else "当前没有足够的可比行为指标。"
        )
        dimensions.append(
            {
                "key": key,
                "label": label,
                "baselineScore": baseline_score,
                "currentScore": current_score,
                "delta": _delta(baseline_score, current_score),
                "confidence": _dimension_confidence(metrics),
                "summary": summary,
                "metrics": metrics,
                "evidence": evidence[:5],
            }
        )

    provenance = dict(data_provenance or {})
    provenance.update(
        {
            "mode": provenance.get("mode") or "mixed_or_insufficient_data",
            "snapshotIds": [
                str(item.get("snapshot_id"))
                for item in (baseline, current)
                if item and item.get("snapshot_id")
            ],
        }
    )
    message = None
    if current is None:
        message = "暂无真实成长数据"
    elif baseline is None:
        message = "尚未形成成长对比"
    return {
        "studentId": int(student_id),
        "teachingClassId": teaching_class_id,
        "baselineComputedAt": _iso(baseline.get("computed_at")) if baseline else None,
        "currentComputedAt": _iso(current.get("computed_at")) if current else None,
        "calculationVersion": CALCULATION_VERSION,
        "dataProvenance": provenance,
        "overall": {
            "baselineScore": baseline_overall,
            "currentScore": current_overall,
            "delta": _delta(baseline_overall, current_overall),
        },
        "dimensions": dimensions,
        "history": [_history_item(item) for item in history],
        "message": message,
    }
