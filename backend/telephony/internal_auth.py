"""Absicherung der Aufrufe Asterisk → Backend (Dialplan-CURL).

Die internen Endpoints liefern Benutzernamen, Status und Gruppenmitglieder und
lösen Push-Benachrichtigungen aus. Sie sind über den Reverse Proxy erreichbar,
deshalb muss Asterisk ein gemeinsames Secret mitschicken (sub_backend im Dialplan).
"""
import hmac
import logging

from fastapi import HTTPException, Request, status

from config import get_settings

logger = logging.getLogger(__name__)

HEADER = "X-Internal-Secret"


async def require_internal_secret(request: Request) -> None:
    expected = get_settings().ASTERISK_INTERNAL_SECRET
    # Ohne konfiguriertes Secret lieber ablehnen als offen lassen
    if not expected:
        logger.error("ASTERISK_INTERNAL_SECRET ist nicht gesetzt — interner Aufruf abgelehnt")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Internes Secret nicht konfiguriert")
    if not hmac.compare_digest(request.headers.get(HEADER, ""), expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ungültiges internes Secret")
