import os
import threading
import time
from typing import Dict


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default

    try:
        return max(1, int(raw))
    except ValueError:
        return default


LOCAL_APP_ENABLED = os.getenv("LOCAL_APP_SESSION_MODE", "").strip() == "1"
STARTUP_GRACE_SECONDS = _read_int("LOCAL_APP_STARTUP_GRACE_SECONDS", 90)
CLIENT_TIMEOUT_SECONDS = _read_int("LOCAL_APP_CLIENT_TIMEOUT_SECONDS", 45)
EMPTY_SHUTDOWN_SECONDS = _read_int("LOCAL_APP_EMPTY_SHUTDOWN_SECONDS", 8)
BACKEND_PID_FILE = os.getenv("LOCAL_APP_BACKEND_PID_FILE", "").strip()

_lock = threading.Lock()
_clients: Dict[str, float] = {}
_started_at = time.monotonic()
_first_heartbeat_at = 0.0
_empty_since = 0.0
_monitor_started = False
_shutdown_started = False


def _prune_expired_clients(now: float) -> None:
    global _empty_since

    expired_client_ids = [
        client_id
        for client_id, last_seen in _clients.items()
        if now - last_seen > CLIENT_TIMEOUT_SECONDS
    ]
    for client_id in expired_client_ids:
        _clients.pop(client_id, None)

    if _clients:
        _empty_since = 0.0
    elif _first_heartbeat_at and not _empty_since:
        _empty_since = now


def _snapshot(now: float) -> dict:
    return {
        "enabled": LOCAL_APP_ENABLED,
        "active_clients": len(_clients),
        "client_timeout_seconds": CLIENT_TIMEOUT_SECONDS,
        "empty_shutdown_seconds": EMPTY_SHUTDOWN_SECONDS,
        "started_seconds_ago": round(now - _started_at, 2),
    }


def heartbeat(client_id: str) -> dict:
    if not LOCAL_APP_ENABLED:
        return {"enabled": False}

    now = time.monotonic()
    with _lock:
        global _first_heartbeat_at, _empty_since

        _clients[client_id] = now
        if not _first_heartbeat_at:
            _first_heartbeat_at = now
        _empty_since = 0.0
        _prune_expired_clients(now)
        return _snapshot(now)


def _shutdown_process(reason: str) -> None:
    global _shutdown_started

    with _lock:
        if _shutdown_started:
            return
        _shutdown_started = True

    if BACKEND_PID_FILE:
        try:
            os.remove(BACKEND_PID_FILE)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    print(f"[local-runtime] {reason}. Shutting down local backend.", flush=True)
    time.sleep(1)
    os._exit(0)


def _monitor_loop() -> None:
    while True:
        time.sleep(2)
        now = time.monotonic()

        with _lock:
            _prune_expired_clients(now)

            if _clients:
                continue

            if not _first_heartbeat_at:
                should_shutdown = now - _started_at >= STARTUP_GRACE_SECONDS
                reason = "No local app page heartbeat was received after startup"
            else:
                should_shutdown = bool(_empty_since) and now - _empty_since >= EMPTY_SHUTDOWN_SECONDS
                reason = "All local app pages have been closed"

        if should_shutdown:
            _shutdown_process(reason)
            return


def start_monitor() -> None:
    global _monitor_started

    if not LOCAL_APP_ENABLED or _monitor_started:
        return

    _monitor_started = True
    thread = threading.Thread(target=_monitor_loop, name="local-runtime-monitor", daemon=True)
    thread.start()
