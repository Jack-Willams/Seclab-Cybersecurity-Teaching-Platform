"""
Operation environment (per-student noVNC desktop) orchestration.

Ported from CyberDojo (E:/Project/cyber/cyberdojo-backend-for-frontend/src/modules/experiment/service.ts),
adapted to Docker SDK for Python. Lifecycle:

  start_operation_env -> create network, create+start container with random
                         host VNC port, attach the experiment target
                         container(s) to that network, persist session
  stop_operation_env  -> stop+remove the operation container, detach targets,
                         remove the network, mark session stopped
  cleanup_idle_sessions -> stop sessions whose created_at exceeds the
                          OPERATION_SESSION_TIMEOUT_SECONDS budget
"""
import logging
import socket
import time
from typing import Optional
from uuid import uuid4

from docker.errors import APIError, NotFound

import operation_session_repository as session_repo
from config import (
    OPERATION_CLEANUP_INTERVAL_SECONDS,
    OPERATION_IMAGE,
    OPERATION_SESSION_TIMEOUT_SECONDS,
    OPERATION_TARGET_CONTAINERS,
    OPERATION_VNC_HOST,
)
from docker_tools import get_client

logger = logging.getLogger("operation_env")


def _short_session_id() -> str:
    return uuid4().hex[:12]


def _short_user(user_id: int) -> str:
    return str(user_id)[-8:] or "u0"


def _base_lab_id(module_id: Optional[int]) -> Optional[int]:
    """Mirror SecLab-FrontEnd-2/src/pages/User/Module/index.vue:getBaseLabId().
    Modules >= 100 use the first digit of the id (101..199 -> 1, 201..299 -> 2, etc);
    smaller ids are used as-is."""
    if module_id is None:
        return None
    if module_id >= 100:
        return int(str(module_id)[0])
    return module_id


def _resolve_target_containers(module_id: Optional[int]) -> list:
    base = _base_lab_id(module_id)
    if base is None:
        return []
    return list(OPERATION_TARGET_CONTAINERS.get(base, []))


def _vnc_ready(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            banner = sock.recv(12)
        return banner.startswith(b"RFB ")
    except OSError:
        return False


def _wait_vnc_ready(host: str, port: int, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _vnc_ready(host, port):
            return
        time.sleep(0.4)
    raise RuntimeError(f"operation VNC port {host}:{port} did not become ready")


def _session_runtime_ready(session: dict) -> bool:
    client = get_client()
    try:
        container = client.containers.get(session["container_name"])
        container.reload()
    except NotFound:
        return False
    except Exception as exc:
        logger.warning("check operation container %s failed: %s", session.get("container_name"), exc)
        return False
    return container.status == "running" and _vnc_ready(session["vnc_host"], int(session["vnc_port"]))


def _attach_target_to_network(network, target_name: str) -> bool:
    """Best-effort attach. Returns True if attached or already attached,
    False if the target container does not exist (caller can log + continue)."""
    client = get_client()
    try:
        container = client.containers.get(target_name)
    except NotFound:
        logger.warning("target container '%s' not found, skipping attach", target_name)
        return False
    try:
        network.connect(container)
        return True
    except APIError as exc:
        # 'endpoint with name ... already exists in network' is fine.
        msg = str(exc).lower()
        if "already exists" in msg or "already attached" in msg:
            return True
        logger.warning("attach %s -> %s failed: %s", target_name, network.name, exc)
        return False


def _detach_target_from_network(network, target_name: str) -> None:
    client = get_client()
    try:
        container = client.containers.get(target_name)
    except NotFound:
        return
    try:
        network.disconnect(container, force=True)
    except APIError as exc:
        msg = str(exc).lower()
        if "is not connected" in msg or "not found" in msg:
            return
        logger.warning("detach %s from %s failed: %s", target_name, network.name, exc)


def start_operation_env(user_id: int, module_id: Optional[int], course_id: Optional[int] = None) -> dict:
    """Create network + operation container, attach target containers, persist
    session. Returns a dict suitable to return to the frontend."""
    existing = session_repo.find_running_by_user_module(user_id, module_id)
    if existing:
        if _session_runtime_ready(existing):
            return {
                "session_id": existing["session_id"],
                "container_name": existing["container_name"],
                "network_name": existing["network_name"],
                "vnc_host": existing["vnc_host"],
                "vnc_port": existing["vnc_port"],
                "ws_path": f"/api/docker/vnc/{existing['session_id']}",
                "reused": True,
            }
        logger.warning("discarding stale operation session %s", existing["session_id"])
        _safe_cleanup(
            existing["container_name"],
            existing["network_name"],
            existing.get("target_containers") or [],
        )
        session_repo.mark_stopped(existing["session_id"])

    client = get_client()
    session_id = _short_session_id()
    network_name = f"seclab-op-{session_id}"
    container_name = f"operation_{_short_user(user_id)}_{session_id}"
    base_lab_id = _base_lab_id(module_id)

    network = None
    container = None
    attached_targets: list = []
    try:
        network = client.networks.create(name=network_name, driver="bridge", check_duplicate=True)

        target_names = _resolve_target_containers(module_id)
        for tname in target_names:
            if _attach_target_to_network(network, tname):
                attached_targets.append(tname)

        container = client.containers.create(
            image=OPERATION_IMAGE,
            name=container_name,
            detach=True,
            ports={"5901/tcp": None},  # docker-py equivalent of HostPort=""
            network=network_name,
            environment={"SECLAB_LAB_BASE_ID": str(base_lab_id or "")},
        )
        container.start()
        container.reload()

        port_bindings = (container.attrs.get("NetworkSettings", {}) or {}).get("Ports", {}) or {}
        host_binding = port_bindings.get("5901/tcp") or []
        if not host_binding:
            raise RuntimeError("operation container started but 5901/tcp was not bound")
        vnc_port = int(host_binding[0]["HostPort"])
        _wait_vnc_ready(OPERATION_VNC_HOST, vnc_port)

        session_repo.insert_session(
            session_id=session_id,
            user_id=user_id,
            module_id=module_id,
            course_id=course_id,
            container_name=container_name,
            network_name=network_name,
            target_containers=attached_targets,
            vnc_host=OPERATION_VNC_HOST,
            vnc_port=vnc_port,
        )

        return {
            "session_id": session_id,
            "container_name": container_name,
            "network_name": network_name,
            "vnc_host": OPERATION_VNC_HOST,
            "vnc_port": vnc_port,
            "ws_path": f"/api/docker/vnc/{session_id}",
            "reused": False,
        }
    except Exception:
        # Roll back partial setup so a failed start does not leak resources.
        logger.exception("start_operation_env failed, rolling back %s", session_id)
        _safe_cleanup(container_name, network_name, attached_targets)
        raise


def _safe_cleanup(container_name: str, network_name: str, target_containers: list) -> None:
    client = get_client()
    try:
        c = client.containers.get(container_name)
        try:
            c.stop(timeout=0)
        except APIError:
            pass
        try:
            c.remove(force=True)
        except APIError:
            pass
    except NotFound:
        pass
    except Exception as exc:
        logger.warning("cleanup container %s failed: %s", container_name, exc)

    try:
        network = client.networks.get(network_name)
        for tname in target_containers or []:
            _detach_target_from_network(network, tname)
        try:
            network.remove()
        except APIError as exc:
            logger.warning("remove network %s failed: %s", network_name, exc)
    except NotFound:
        pass
    except Exception as exc:
        logger.warning("cleanup network %s failed: %s", network_name, exc)


def stop_operation_env(session_id: str) -> dict:
    session = session_repo.find_session(session_id)
    if not session:
        return {"success": False, "error": f"session '{session_id}' not found"}
    _safe_cleanup(
        session["container_name"],
        session["network_name"],
        session.get("target_containers") or [],
    )
    session_repo.mark_stopped(session_id)
    return {"success": True, "session_id": session_id}


def get_operation_env_status(session_id: str) -> dict:
    session = session_repo.find_session(session_id)
    if not session:
        return {"success": False, "error": f"session '{session_id}' not found"}
    return {
        "success": True,
        "data": {
            "session_id": session["session_id"],
            "status": session["status"],
            "container_name": session["container_name"],
            "vnc_host": session["vnc_host"],
            "vnc_port": session["vnc_port"],
            "ws_path": f"/api/docker/vnc/{session['session_id']}",
            "created_at": session["created_at"].isoformat() if session.get("created_at") else None,
        },
    }


def cleanup_idle_sessions(timeout_seconds: int = OPERATION_SESSION_TIMEOUT_SECONDS) -> int:
    expired = session_repo.find_expired_running(timeout_seconds)
    for s in expired:
        try:
            _safe_cleanup(s["container_name"], s["network_name"], s.get("target_containers") or [])
            session_repo.mark_stopped(s["session_id"])
        except Exception:
            logger.exception("cleanup_idle_sessions failed for %s", s["session_id"])
    if expired:
        logger.info("cleanup_idle_sessions removed %d sessions", len(expired))
    return len(expired)


async def cleanup_loop() -> None:
    """Run forever; meant to be launched as an asyncio task on app startup."""
    import asyncio

    while True:
        try:
            cleanup_idle_sessions()
        except Exception:
            logger.exception("cleanup_loop tick failed")
        await asyncio.sleep(OPERATION_CLEANUP_INTERVAL_SECONDS)
