from datetime import datetime, timedelta
from uuid import uuid4

_ACTIVE_CAPTURE: dict | None = None


def start_uid_capture(timeout_seconds: int = 15) -> dict:
    global _ACTIVE_CAPTURE

    now = datetime.utcnow()
    _ACTIVE_CAPTURE = {
        "capture_id": str(uuid4()),
        "uid": None,
        "device_code": None,
        "started_at": now,
        "expires_at": now + timedelta(seconds=timeout_seconds),
        "status": "waiting",
    }
    return _ACTIVE_CAPTURE.copy()


def get_uid_capture_status(capture_id: str) -> dict:
    global _ACTIVE_CAPTURE

    if not _ACTIVE_CAPTURE or _ACTIVE_CAPTURE["capture_id"] != capture_id:
        return {"status": "not_found"}

    now = datetime.utcnow()

    if _ACTIVE_CAPTURE["status"] == "success":
        return {
            "status": "success",
            "uid": _ACTIVE_CAPTURE["uid"],
            "device_code": _ACTIVE_CAPTURE["device_code"],
        }

    if now > _ACTIVE_CAPTURE["expires_at"]:
        _ACTIVE_CAPTURE["status"] = "expired"
        return {"status": "expired"}

    return {"status": "waiting"}


def submit_uid_capture(uid: str, device_code: str | None = None) -> bool:
    global _ACTIVE_CAPTURE

    if not _ACTIVE_CAPTURE:
        return False

    now = datetime.utcnow()

    if _ACTIVE_CAPTURE["status"] != "waiting":
        return False

    if now > _ACTIVE_CAPTURE["expires_at"]:
        _ACTIVE_CAPTURE["status"] = "expired"
        return False

    _ACTIVE_CAPTURE["uid"] = uid.strip()
    _ACTIVE_CAPTURE["device_code"] = device_code
    _ACTIVE_CAPTURE["status"] = "success"
    return True


def reset_uid_capture() -> None:
    global _ACTIVE_CAPTURE
    _ACTIVE_CAPTURE = None