from fastapi import APIRouter, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.esp32_access import (
    Esp32AccessCheckRequest,
    Esp32AccessCheckResponse,
)
from app.services.esp32_access_service import (
    Esp32AccessServiceError,
    check_esp32_access_service,
)

router = APIRouter(prefix="/api/esp32/access", tags=["ESP32 Access"])


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header manquant.",
        )

    parts = authorization.strip().split(" ", 1)

    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header invalide.",
        )

    return parts[1].strip()


@router.post("/check", response_model=Esp32AccessCheckResponse)
def check_access(
    payload: Esp32AccessCheckRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    bearer_token = extract_bearer_token(authorization)

    try:
        result = check_esp32_access_service(
            db,
            payload=payload,
            bearer_token=bearer_token,
        )
        return result

    except Esp32AccessServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    
"""
jacob@jacob-IdeaPad-3-15IAU7:/var/www/html/ENI/rfid-door-platform$ curl -X POST "http://127.0.0.1:8000/api/esp32/access/check" -H "Content-Type: application/json" -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY" -d '{"device_code": "ssqa","uid": "id_puce_rfid"}'

{"decision":"denied","door_opened":false,"direction":"unknown","reason":"card_not_found","user_id":null,"assignment_id":null,"card_id":null,"scanned_at":"2026-04-11T21:38:51.010528"}jacob@jacob-IdeaPad-3-15IAU7:/var/www/html/ENI/rfid-door-platform$ curl -X POST "http://127.0.0.1:8000/api/esp32/access/check"   -H "Content-Type: application/json"   -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY"   -d '{
    "device_code": "ssqa",
    "uid": "qdsqdqsdqsdqsdsqdss"
  }'
{"decision":"granted","door_opened":true,"direction":"entry","reason":"access_granted","user_id":2,"assignment_id":1,"card_id":1,"scanned_at":"2026-04-11T21:40:31.642180"}jacob@jacob-IdeaPad-3-15IAU7:/var/www/html/ENI/rfid-door-platform$ curl -X POST "http://127.0.0.1:8000/api/esp32/access/check"   -H "Content-Type: application/json"   -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY"   -d '{
    "device_code": "ssqa",
    "uid": "qdsqdqsdqsdqsdsqdss"
  }'
{"decision":"granted","door_opened":true,"direction":"exit","reason":"access_granted","user_id":2,"assignment_id":1,"card_id":1,"scanned_at":"2026-04-11T21:41:14.965324"}
"""