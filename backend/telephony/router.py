import logging
import uuid as uuid_module
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from keycloak import get_current_user, require_role
from telephony.models import SipAccount, CallRecord, Voicemail, CallDirection, CallStatus
from telephony.service import (
    generate_sip_password,
    encrypt_password,
    decrypt_password,
    sip_md5_cred,
)
from telephony.voicemail_store import sync_mailbox, resolve_audio
from telephony.routing import group_dial_info, inbound_target
from telephony.greetings import (
    GreetingError, MAX_BYTES as GREETING_MAX_BYTES,
    delete_greeting, greeting_path, read_greeting, save_greeting,
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
    caller_name: str | None
    callee_number: str
    callee_name: str | None
    direction: CallDirection
    status: CallStatus
    duration_seconds: int
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class VoicemailOut(BaseModel):
    id: int
    caller_number: str
    caller_name: str | None
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

    # Asterisk sieht den Account sofort über die Realtime-Views
    account = SipAccount(
        user_id=target_user_id,
        username=body.username,
        extension=body.extension,
        password_encrypted=encrypt_password(password),
        sip_md5_cred=sip_md5_cred(body.username, password),
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


class SipCredentialsOut(BaseModel):
    username: str
    extension: str
    password: str


@router.get("/accounts/me/credentials", response_model=SipCredentialsOut)
async def get_my_credentials(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SipCredentialsOut:
    account = await db.scalar(
        select(SipAccount).where(SipAccount.user_id == current_user["sub"])
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")
    return SipCredentialsOut(
        username=account.username,
        extension=account.extension,
        password=decrypt_password(account.password_encrypted),
    )


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

    # Verschwindet damit auch aus den Realtime-Views
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

    # Alle Anrufe wo der User Anrufer ODER Angerufener war
    result = await db.scalars(
        select(CallRecord)
        .where(
            (CallRecord.sip_account_id == account.id)
            | (CallRecord.callee_number == account.extension)
        )
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

    await sync_mailbox(db, account)

    query = select(Voicemail).where(Voicemail.sip_account_id == account.id)
    if unread_only:
        query = query.where(Voicemail.is_read == False)  # noqa: E712
    query = query.order_by(Voicemail.received_at.desc())

    result = await db.scalars(query)
    return list(result.all())


async def _get_own_voicemail(db: AsyncSession, user_id: str, voicemail_id: int) -> Voicemail:
    vm = await db.scalar(
        select(Voicemail)
        .join(SipAccount, Voicemail.sip_account_id == SipAccount.id)
        .where(Voicemail.id == voicemail_id, SipAccount.user_id == user_id)
    )
    if not vm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voicemail nicht gefunden")
    return vm


@router.patch("/voicemail/{voicemail_id}/read", response_model=VoicemailOut)
async def mark_voicemail_read(
    voicemail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Voicemail:
    vm = await _get_own_voicemail(db, current_user["sub"], voicemail_id)
    vm.is_read = True
    return vm


@router.get("/voicemail/{voicemail_id}/audio", response_class=FileResponse)
async def get_voicemail_audio(
    voicemail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FileResponse:
    vm = await _get_own_voicemail(db, current_user["sub"], voicemail_id)
    path = resolve_audio(vm)
    if not path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audiodatei nicht gefunden")
    return FileResponse(path, media_type="audio/wav")


# ── Eigene Voicemail-Ansage ───────────────────────────────────────────────────

class GreetingOut(BaseModel):
    exists: bool
    duration_seconds: int | None = None
    updated_at: datetime | None = None


async def _my_account(db: AsyncSession, user_id: str) -> SipAccount:
    account = await db.scalar(select(SipAccount).where(SipAccount.user_id == user_id))
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein SIP-Account gefunden")
    return account


@router.get("/greeting", response_model=GreetingOut)
async def get_greeting(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GreetingOut:
    account = await _my_account(db, current_user["sub"])
    info = read_greeting(account.extension)
    if not info:
        return GreetingOut(exists=False)
    return GreetingOut(exists=True, duration_seconds=info.duration_seconds, updated_at=info.updated_at)


@router.get("/greeting/audio", response_class=FileResponse)
async def get_greeting_audio(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FileResponse:
    account = await _my_account(db, current_user["sub"])
    path = greeting_path(account.extension)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Keine eigene Ansage")
    return FileResponse(path, media_type="audio/wav")


@router.put("/greeting", response_model=GreetingOut)
async def put_greeting(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GreetingOut:
    """Body: rohes WAV (16 kHz, 16 bit, mono), vom Browser erzeugt."""
    account = await _my_account(db, current_user["sub"])
    data = await request.body()
    if len(data) > GREETING_MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Ansage zu groß")
    try:
        info = save_greeting(account.extension, data)
    except GreetingError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    logger.info("[Voicemail] Neue Ansage für %s (%ds)", account.username, info.duration_seconds)
    return GreetingOut(exists=True, duration_seconds=info.duration_seconds, updated_at=info.updated_at)


@router.delete("/greeting", status_code=status.HTTP_204_NO_CONTENT)
async def remove_greeting(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    account = await _my_account(db, current_user["sub"])
    delete_greeting(account.extension)


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


@router.get("/internal/ext-lookup/{extension}", response_class=PlainTextResponse)
async def extension_lookup(
    extension: str,
    db: AsyncSession = Depends(get_db),
) -> str:
    """Interner Asterisk-Dialplan-Lookup: Durchwahl → SIP-Username.
    Kein Auth — nur aus dem internen Docker-Netz erreichbar."""
    account = await db.scalar(
        select(SipAccount).where(
            SipAccount.extension == extension,
            SipAccount.is_active == True,
        )
    )
    return account.username if account else ""


@router.get("/internal/group/{extension}", response_class=PlainTextResponse)
async def group_lookup(extension: str, db: AsyncSession = Depends(get_db)) -> str:
    """Dialplan _20XX: 'timeout|Dial-String|Fallback'. Kein Auth — wie ext-lookup."""
    return await group_dial_info(db, extension)


@router.get("/internal/inbound/{dialed}", response_class=PlainTextResponse)
async def inbound_lookup(dialed: str, db: AsyncSession = Depends(get_db)) -> str:
    """Dialplan from_trunk: angerufene Nummer → Ziel-Durchwahl (leer = keine Zuordnung)."""
    return await inbound_target(db, dialed)
