from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.device import get_device_by_code
from app.core.security import verify_device_token
from app.services.rfid_uid_capture_service import submit_uid_capture

router = APIRouter(prefix="/api/esp32", tags=["ESP32 Enrollment"])


class EnrollmentScanPayload(BaseModel):
    device_code: str
    uid: str


@router.post("/enrollment/scan")
def esp32_enrollment_scan(
    payload: EnrollmentScanPayload,
    x_api_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = get_device_by_code(db, payload.device_code)

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    if not device.is_active:
        raise HTTPException(status_code=403, detail="Appareil inactif.")

    if not x_api_token or not verify_device_token(x_api_token, device.api_token_hash):
        raise HTTPException(status_code=401, detail="Token appareil invalide.")

    captured = submit_uid_capture(
        uid=payload.uid,
        device_code=device.device_code,
    )

    if not captured:
        return {
            "success": False,
            "message": "Aucune session de capture UID active.",
        }

    return {
        "success": True,
        "message": "UID capturé pour inscription.",
        "uid": payload.uid,
    }



"""

curl -X POST "http://127.0.0.1:8000/api/esp32/enrollment/scan" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: 3r77aMY7GwY6daskvyT8atuU-Ilh7nd6NB1w3fivlrI" \
  -d '{
    "device_code": "ESP32_DEVICE_020",
    "uid": "sdsdxxqzeqzxdqzxdqxdxqx"
  }'

  que l'esp32 doit envoyer pour faire inscription d'une carte uid





"""