"""FCM HTTP v1 API — Push-Benachrichtigungen via google-auth Service Account."""
import json
from pathlib import Path
from typing import Any

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest

from config import get_settings

_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# Gecachte Credentials (werden automatisch refresht wenn abgelaufen)
_credentials: service_account.Credentials | None = None


class FCMError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _get_credentials() -> service_account.Credentials:
    global _credentials

    if _credentials is None:
        settings = get_settings()
        path = Path(settings.FIREBASE_SERVICE_ACCOUNT_FILE)
        if not path.is_file():
            raise FileNotFoundError(f"Service-Account-Datei nicht gefunden: {path}")
        sa_info = json.loads(path.read_text())
        _credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=[_FCM_SCOPE],
        )

    if not _credentials.valid:
        _credentials.refresh(GoogleRequest())

    return _credentials


async def send_incoming_call_push(
    *,
    fcm_token: str,
    caller_id: str,
    caller_name: str,
    call_uuid: str,
) -> str:
    """Sendet einen FCM-Push für einen eingehenden Anruf.

    Gibt die FCM-Nachrichten-ID zurück.
    """
    settings = get_settings()
    creds = _get_credentials()

    payload = {
        "message": {
            "token": fcm_token,
            "android": {
                "priority": "high",
            },
            "data": {
                "type": "incoming_call",
                "uuid": call_uuid,
                "caller_id": caller_id,
                "caller_name": caller_name,
            },
        }
    }

    url = _FCM_SEND_URL.format(project_id=settings.FCM_PROJECT_ID)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
        )
        if resp.is_error:
            raise FCMError(resp.status_code, f"FCM-Fehler: {resp.text}")
        return resp.json().get("name", "")
