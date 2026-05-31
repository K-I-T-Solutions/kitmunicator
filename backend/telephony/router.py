import logging
import uuid as uuid_module
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from keycloak import get_current_user, require_role
from telephony.models import SipAccount, CallRecord, Voicemail, CallDirection, CallStatus
from telephony.service import (
    create_sip_endpoint,
    delete_sip_endpoint,
    generate_sip_password,
    _hash_password,
    ARIError,
)
from push.fcm_service import send_incoming_call_push, FCMError

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class SipAccountCreate(BaseModel):
    username: str
    extension: str
    user_id: str | None = None  # optional: Admin kann für anderen User anlegen


class SipAccountOut(BaseModel):
    id: int
    user_id: str
    username: str
    extension: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SipAccountCreatedOut(SipAccountOut):
    # Passwort wird nur einmalig beim Anlegen zurückgegeben
    password: str


class CallRecordOut(BaseModel):
    id: int
    asterisk_unique_id: str
    caller_number: str
    callee_number: str
    direction: CallDirection
    status: CallStatus
    duration_seconds: int
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class VoicemailOut(BaseModel):
    id: int
    caller_number: str
    duration_seconds: int
    is_read: bool
    received_at: datetime

    model_config = {"from_attributes": True}


# ── SIP-Account CRUD ─────────────────────────────────────────────────────────

@router.post("/accounts", response_model=SipAccountCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: SipAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_role("telephony_admin")),
) -> SipAccountCreatedOut:
    target_user_id = body.user_id or current_user["sub"]

    # Doppelte Anlage verhindern
    existing = await db.scalar(select(SipAccount).where(SipAccount.user_id == target_user_id))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "SIP-Account existiert bereits")

    password = generate_sip_password()

    try:
        await create_sip_endpoint(body.username, password, body.extension)
    except ARIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Asterisk-Fehler: {e.detail}")

    account = SipAccount(
        user_id=target_user_id,
        username=body.username,
        extension=body.extension,
        password_hash=_hash_password(password),
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    return SipAccountCreatedOut(**SipAccountOut.model_validate(account).model_dump(), password=password)


@router.get("/accounts/me", response_model=SipAccountOut)
async def get_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SipAccount:
    account = await db.scalar(
        select(SipAccount).where(SipAccount.user_id == current_user["sub"])
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")
    return account


@router.get("/accounts/{user_id}", response_model=SipAccountOut)
async def get_account(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict[str, Any] = Depends(require_role("telephony_admin")),
) -> SipAccount:
    account = await db.scalar(select(SipAccount).where(SipAccount.user_id == user_id))
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SIP-Account nicht gefunden")
    return account


@router.delete("/accounts/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict[str, Any] = Depends(require_role("telephony_admin")),
) -> None:
    account = await db.scalar(select(SipAccount).where(SipAccount.user_id == user_id))
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SIP-Account nicht gefunden")

    try:
        await delete_sip_endpoint(account.username)
    except ARIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Asterisk-Fehler: {e.detail}")

    await db.delete(account)


# ── CDR ───────────────────────────────────────────────────────────────────────

@router.get("/cdr", response_model=list[CallRecordOut])
async def list_cdr(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[CallRecord]:
    account = await db.scalar(
        select(SipAccount).where(SipAccount.user_id == current_user["sub"])
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")

    result = await db.scalars(
        select(CallRecord)
        .where(CallRecord.sip_account_id == account.id)
        .order_by(CallRecord.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.all())


# ── Voicemail ─────────────────────────────────────────────────────────────────

@router.get("/voicemail", response_model=list[VoicemailOut])
async def list_voicemail(
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Voicemail]:
    account = await db.scalar(
        select(SipAccount).where(SipAccount.user_id == current_user["sub"])
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")

    query = select(Voicemail).where(Voicemail.sip_account_id == account.id)
    if unread_only:
        query = query.where(Voicemail.is_read == False)  # noqa: E712
    query = query.order_by(Voicemail.received_at.desc())

    result = await db.scalars(query)
    return list(result.all())


@router.patch("/voicemail/{voicemail_id}/read", response_model=VoicemailOut)
async def mark_voicemail_read(
    voicemail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Voicemail:
    account = await db.scalar(
        select(SipAccount).where(SipAccount.user_id == current_user["sub"])
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")

    vm = await db.scalar(
        select(Voicemail).where(
            Voicemail.id == voicemail_id,
            Voicemail.sip_account_id == account.id,
        )
    )
    if not vm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voicemail nicht gefunden")

    vm.is_read = True
    return vm


# ── FCM Push-Token ────────────────────────────────────────────────────────────

class PushTokenUpdate(BaseModel):
    token: str


@router.put("/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def update_push_token(
    body: PushTokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """App registriert ihren aktuellen FCM-Token nach Login."""
    account = await db.scalar(
        select(SipAccount).where(SipAccount.user_id == current_user["sub"])
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")
    account.fcm_token = body.token
    logger.info("[FCM] Token für %s gespeichert", account.username)


# ── Asterisk-Webhook (intern, kein Auth) ─────────────────────────────────────

class IncomingCallWebhook(BaseModel):
    caller_id: str
    caller_name: str = ""
    callee_extension: str
    # Asterisk UNIQUEID des Channels — wird als CallKit-UUID verwendet
    uuid: str = ""
    # Optionaler Webhook-Secret-Header zur Absicherung
    secret: str = ""


@router.post("/webhook/incoming-call", status_code=status.HTTP_204_NO_CONTENT)
async def incoming_call_webhook(
    body: IncomingCallWebhook,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Asterisk ruft diesen Endpoint auf, wenn ein Anruf eingeht und der
    SIP-Endpoint nicht erreichbar ist (CHANUNAVAIL). Das Backend schickt
    dann einen FCM-Push an das Gerät des Nutzers."""
    settings = get_settings()

    # Webhook-Secret prüfen (wenn konfiguriert)
    if settings.ASTERISK_WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Webhook-Secret", "")
        if header_secret != settings.ASTERISK_WEBHOOK_SECRET:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Ungültiges Webhook-Secret")

    account = await db.scalar(
        select(SipAccount).where(SipAccount.extension == body.callee_extension)
    )
    if not account:
        logger.warning("[Webhook] Kein Account für Durchwahl %s", body.callee_extension)
        return

    if not account.fcm_token:
        logger.warning("[Webhook] Kein FCM-Token für %s", account.username)
        return

    call_uuid = body.uuid or str(uuid_module.uuid4())
    caller_name = body.caller_name or body.caller_id

    try:
        msg_id = await send_incoming_call_push(
            fcm_token=account.fcm_token,
            caller_id=body.caller_id,
            caller_name=caller_name,
            call_uuid=call_uuid,
        )
        logger.info(
            "[FCM] Push gesendet für %s ← %s, msg_id=%s",
            account.username,
            body.caller_id,
            msg_id,
        )
    except FCMError as e:
        logger.error("[FCM] Fehler beim Push: %s (HTTP %s)", e.detail, e.status_code)
