"""
Operation environment session repository.
Persists the lifecycle of per-student noVNC desktop containers.

Schema mirrors 数据库文件/operation-session.sql; the table is created
on first access (ensure_schema) so a clean install does not need a
manual SQL import.

If MySQL is unreachable (e.g. the seclab_app account is not provisioned
on this host yet), every operation transparently falls back to an
in-process dict. Sessions then do not survive a service restart and
the cleanup loop only sees what is in memory — acceptable for MVP
smoke testing, not for production.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from database import ensure_database, get_connection

logger = logging.getLogger("operation_session_repo")

# In-memory fallback store. Activated when the first DB call fails
# (e.g. user/password not yet set up on the host MySQL).
_MEMORY_STORE: dict = {}
_USE_MEMORY = False


def _switch_to_memory(reason: Exception) -> None:
    global _USE_MEMORY
    if not _USE_MEMORY:
        logger.warning("operation_session repository falling back to in-memory store: %s", reason)
        _USE_MEMORY = True


OPERATION_SESSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `operation_session` (
  `session_id`        VARCHAR(64)  NOT NULL,
  `user_id`           BIGINT       NOT NULL,
  `module_id`         BIGINT       NULL,
  `course_id`         BIGINT       NULL,
  `container_name`    VARCHAR(128) NOT NULL,
  `network_name`      VARCHAR(128) NOT NULL,
  `target_containers` JSON         NOT NULL,
  `vnc_host`          VARCHAR(64)  NOT NULL DEFAULT '127.0.0.1',
  `vnc_port`          INT          NOT NULL,
  `status`            VARCHAR(16)  NOT NULL DEFAULT 'running',
  `created_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`session_id`),
  KEY `idx_operation_session_user` (`user_id`),
  KEY `idx_operation_session_status_created` (`status`, `created_at`),
  KEY `idx_operation_session_module_user` (`module_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()


_schema_ready = False


def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready or _USE_MEMORY:
        return
    try:
        ensure_database()
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(OPERATION_SESSION_TABLE_SQL)
            conn.commit()
        _schema_ready = True
    except Exception as exc:
        _switch_to_memory(exc)


def _row_to_dict(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None
    targets = row.get("target_containers")
    if isinstance(targets, str):
        try:
            row["target_containers"] = json.loads(targets)
        except json.JSONDecodeError:
            row["target_containers"] = []
    return row


def insert_session(
    *,
    session_id: str,
    user_id: int,
    module_id: Optional[int],
    course_id: Optional[int],
    container_name: str,
    network_name: str,
    target_containers: list,
    vnc_host: str,
    vnc_port: int,
) -> None:
    ensure_schema()
    record = {
        "session_id": session_id,
        "user_id": user_id,
        "module_id": module_id,
        "course_id": course_id,
        "container_name": container_name,
        "network_name": network_name,
        "target_containers": list(target_containers or []),
        "vnc_host": vnc_host,
        "vnc_port": vnc_port,
        "status": "running",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    if _USE_MEMORY:
        _MEMORY_STORE[session_id] = record
        return
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO operation_session
                      (session_id, user_id, module_id, course_id,
                       container_name, network_name, target_containers,
                       vnc_host, vnc_port, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'running')
                    """,
                    (
                        session_id,
                        user_id,
                        module_id,
                        course_id,
                        container_name,
                        network_name,
                        json.dumps(target_containers, ensure_ascii=False),
                        vnc_host,
                        vnc_port,
                    ),
                )
            conn.commit()
    except Exception as exc:
        _switch_to_memory(exc)
        _MEMORY_STORE[session_id] = record


def find_session(session_id: str) -> Optional[dict]:
    ensure_schema()
    if _USE_MEMORY:
        rec = _MEMORY_STORE.get(session_id)
        return dict(rec) if rec else None
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM operation_session WHERE session_id=%s",
                    (session_id,),
                )
                return _row_to_dict(cursor.fetchone())
    except Exception as exc:
        _switch_to_memory(exc)
        rec = _MEMORY_STORE.get(session_id)
        return dict(rec) if rec else None


def find_running_by_user_module(user_id: int, module_id: Optional[int]) -> Optional[dict]:
    """Return a still-running session for the same (user, module) — used to
    short-circuit duplicate start clicks without leaking containers."""
    ensure_schema()
    if _USE_MEMORY:
        candidates = [
            r for r in _MEMORY_STORE.values()
            if r.get("status") == "running"
            and r.get("user_id") == user_id
            and r.get("module_id") == module_id
        ]
        if not candidates:
            return None
        return dict(sorted(candidates, key=lambda r: r["created_at"], reverse=True)[0])
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                if module_id is None:
                    cursor.execute(
                        "SELECT * FROM operation_session "
                        "WHERE user_id=%s AND module_id IS NULL AND status='running' "
                        "ORDER BY created_at DESC LIMIT 1",
                        (user_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM operation_session "
                        "WHERE user_id=%s AND module_id=%s AND status='running' "
                        "ORDER BY created_at DESC LIMIT 1",
                        (user_id, module_id),
                    )
                return _row_to_dict(cursor.fetchone())
    except Exception as exc:
        _switch_to_memory(exc)
        return find_running_by_user_module(user_id, module_id)


def mark_stopped(session_id: str) -> None:
    ensure_schema()
    if _USE_MEMORY:
        rec = _MEMORY_STORE.get(session_id)
        if rec:
            rec["status"] = "stopped"
            rec["updated_at"] = datetime.utcnow()
        return
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE operation_session SET status='stopped' WHERE session_id=%s",
                    (session_id,),
                )
            conn.commit()
    except Exception as exc:
        _switch_to_memory(exc)
        rec = _MEMORY_STORE.get(session_id)
        if rec:
            rec["status"] = "stopped"
            rec["updated_at"] = datetime.utcnow()


def find_expired_running(timeout_seconds: int) -> list:
    ensure_schema()
    cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    if _USE_MEMORY:
        return [
            dict(r) for r in _MEMORY_STORE.values()
            if r.get("status") == "running" and r.get("created_at") and r["created_at"] < cutoff
        ]
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM operation_session "
                    "WHERE status='running' AND created_at < %s",
                    (cutoff,),
                )
                rows = cursor.fetchall() or []
                return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        _switch_to_memory(exc)
        return find_expired_running(timeout_seconds)
