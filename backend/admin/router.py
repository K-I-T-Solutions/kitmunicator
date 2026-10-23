"""Verwaltung für Admins (Rolle telephony_admin): Nebenstellen und Asterisk-Status.

Nebenstellen sind Zeilen in sip_accounts — Asterisk liest sie per Realtime
(Migration 0006), jede Änderung wirkt sofort.
"""
import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.keycloak_admin import KeycloakAdminError, list_users, get_user
from database import get_db
from keycloak import require_role
from telephony.models import RingGroup, SipAccount
from telephony.routing import GROUP_EXTENSION_RE, USER_EXTENSION_RE, normalize_number
from telephony.service import (
    ARIError,
    encrypt_password,
    generate_sip_password,
    get_active_channels,
    list_pjsip_endpoints,
    reload_pjsip,
    sip_md5_cred,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_role("telephony_admin"))])

_SIP_USERNAME_RE = re.compile(r"[^a-z0-9._-]")
_TRUNK = "sipgate_trunk"


def _validate_extension(value: str | None) -> str | None:
    if value is not None and not USER_EXTENSION_RE.match(value):
        raise ValueError("Durchwahl muss 1000–1099 sein")
    return value


# ── Schemas ───────────────────────────────────────────────────────────────────

class SipInfo(BaseModel):
    id: int
    username: str
    extension: str
    display_name: str | None
    email: str | None
    is_active: bool
    online: bool | None = None

    model_config = {"from_attributes": True}


class AdminUser(BaseModel):
    user_id: str
    username: str
    display_name: str
    email: str | None
    enabled: bool
    # False: Nebenstelle existiert, der Keycloak-User aber nicht (mehr)
    in_keycloak: bool
    sip: SipInfo | None


class AdminUserList(BaseModel):
    users: list[AdminUser]
    keycloak_error: str | None = None
    next_extension: str | None


class AssignSip(BaseModel):
    extension: str | None = None
    display_name: str | None = None

    _check_ext = field_validator("extension")(_validate_extension)


class UpdateSip(BaseModel):
    extension: str | None = None
    display_name: str | None = None
    email: str | None = None
    is_active: bool | None = None

    _check_ext = field_validator("extension")(_validate_extension)


class EndpointStatus(BaseModel):
    username: str
    extension: str | None
    display_name: str | None
    state: str


class CallStatus(BaseModel):
    channel: str
    caller: str
    caller_name: str | None
    connected: str | None
    state: str
    since: datetime | None


class PbxStatus(BaseModel):
    endpoints: list[EndpointStatus]
    calls: list[CallStatus]
    trunk_state: str | None
    asterisk_error: str | None = None


# ── Helfer ────────────────────────────────────────────────────────────────────

async def _next_free_extension(db: AsyncSession) -> str | None:
    used = set((await db.scalars(select(SipAccount.extension))).all())
    return next((f"10{n:02d}" for n in range(1, 100) if f"10{n:02d}" not in used), None)


async def _ensure_extension_free(db: AsyncSession, extension: str, exclude_id: int | None = None) -> None:
    other = await db.scalar(select(SipAccount).where(SipAccount.extension == extension))
    if other and other.id != exclude_id:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Durchwahl {extension} ist schon an {other.username} vergeben")


async def _endpoint_states() -> dict[str, str]:
    try:
        return {e["resource"]: e.get("state", "unknown") for e in await list_pjsip_endpoints()}
    except (ARIError, OSError) as exc:
        logger.warning("[Admin] Endpoint-Status nicht abrufbar: %s", exc)
        return {}


def _ari_time(value: str | None) -> datetime | None:
    """ARI liefert '2026-10-21T20:30:00.123+0000' — ohne Doppelpunkt in der Zone."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        return None


async def _get_account(db: AsyncSession, account_id: int) -> SipAccount:
    account = await db.get(SipAccount, account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nebenstelle nicht gefunden")
    return account


# ── Benutzer & Nebenstellen ───────────────────────────────────────────────────

@router.get("/users", response_model=AdminUserList)
async def admin_list_users(db: AsyncSession = Depends(get_db)) -> AdminUserList:
    accounts = {a.user_id: a for a in (await db.scalars(select(SipAccount))).all()}
    states = await _endpoint_states()

    def sip_info(account: SipAccount | None) -> SipInfo | None:
        if not account:
            return None
        info = SipInfo.model_validate(account)
        if account.is_active and states:
            info.online = states.get(account.username) == "online"
        return info

    keycloak_error = None
    users: list[AdminUser] = []
    try:
        for kc in await list_users():
            account = accounts.pop(kc.id, None)
            users.append(AdminUser(
                user_id=kc.id, username=kc.username, display_name=kc.display_name,
                email=kc.email, enabled=kc.enabled, in_keycloak=True, sip=sip_info(account),
            ))
    except KeycloakAdminError as exc:
        keycloak_error = str(exc)

    # Nebenstellen ohne (erreichbaren) Keycloak-User trotzdem zeigen
    for account in accounts.values():
        users.append(AdminUser(
            user_id=account.user_id, username=account.username,
            display_name=account.display_name or account.username, email=account.email,
            enabled=True, in_keycloak=False, sip=sip_info(account),
        ))

    users.sort(key=lambda u: (u.sip is None, u.sip.extension if u.sip else "", u.display_name.lower()))
    return AdminUserList(users=users, keycloak_error=keycloak_error, next_extension=await _next_free_extension(db))


async def _reload_pjsip() -> None:
    """Nach dem Commit: Asterisk soll neue/geänderte Nebenstellen sofort richtig führen."""
    try:
        await reload_pjsip()
    except Exception as exc:
        logger.warning("[Admin] PJSIP-Reload fehlgeschlagen: %s", exc)


@router.post("/users/{user_id}/sip", response_model=SipInfo, status_code=status.HTTP_201_CREATED)
async def admin_assign_sip(user_id: str, body: AssignSip, db: AsyncSession = Depends(get_db)) -> SipAccount:
    if await db.scalar(select(SipAccount).where(SipAccount.user_id == user_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Der Nutzer hat schon eine Nebenstelle")
    try:
        kc = await get_user(user_id)
    except KeycloakAdminError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    if not kc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nutzer nicht in Keycloak gefunden")

    extension = body.extension or await _next_free_extension(db)
    if not extension:
        raise HTTPException(status.HTTP_409_CONFLICT, "Keine freie Durchwahl mehr (1001–1099)")
    await _ensure_extension_free(db, extension)

    # SIP-Username = Endpoint-Name in Asterisk, muss eindeutig und SIP-tauglich sein
    username = _SIP_USERNAME_RE.sub("", kc.username.lower()) or f"user{extension}"
    if await db.scalar(select(SipAccount).where(SipAccount.username == username)):
        username = f"{username}{extension}"

    password = generate_sip_password()
    account = SipAccount(
        user_id=kc.id,
        username=username,
        extension=extension,
        display_name=body.display_name or kc.display_name,
        email=kc.email,
        password_encrypted=encrypt_password(password),
        sip_md5_cred=sip_md5_cred(username, password),
    )
    db.add(account)
    await db.commit()
    await _reload_pjsip()
    logger.warning("[Admin] Nebenstelle %s → %s (%s)", extension, username, kc.display_name)
    return account


@router.patch("/sip/{account_id}", response_model=SipInfo)
async def admin_update_sip(account_id: int, body: UpdateSip, db: AsyncSession = Depends(get_db)) -> SipAccount:
    account = await _get_account(db, account_id)
    if body.extension and body.extension != account.extension:
        await _ensure_extension_free(db, body.extension, exclude_id=account.id)
        account.extension = body.extension
    if body.display_name is not None:
        account.display_name = body.display_name.strip() or None
    if body.email is not None:
        account.email = body.email.strip() or None
    if body.is_active is not None:
        account.is_active = body.is_active
    await db.commit()
    await _reload_pjsip()
    logger.warning("[Admin] Nebenstelle %s geändert: %s", account.username, body.model_dump(exclude_none=True))
    return account


@router.post("/sip/{account_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reset_password(account_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Neues SIP-Passwort. Der Client holt es beim nächsten Laden selbst (/accounts/me/credentials)."""
    account = await _get_account(db, account_id)
    password = generate_sip_password()
    account.password_encrypted = encrypt_password(password)
    account.sip_md5_cred = sip_md5_cred(account.username, password)
    logger.warning("[Admin] SIP-Passwort für %s neu erzeugt", account.username)


@router.delete("/sip/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_sip(account_id: int, db: AsyncSession = Depends(get_db)) -> None:
    account = await _get_account(db, account_id)
    await db.delete(account)
    logger.warning("[Admin] Nebenstelle %s (%s) entfernt", account.extension, account.username)


# ── Sammelrufgruppen ──────────────────────────────────────────────────────────

class GroupMember(BaseModel):
    id: int
    username: str
    extension: str
    display_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class GroupOut(BaseModel):
    id: int
    name: str
    extension: str
    ring_timeout: int
    fallback_extension: str | None
    inbound_number: str | None
    inbound_catch_all: bool
    members: list[GroupMember]

    model_config = {"from_attributes": True}


class GroupIn(BaseModel):
    name: str
    extension: str
    ring_timeout: int = 25
    fallback_extension: str | None = None
    inbound_number: str | None = None
    inbound_catch_all: bool = False
    member_ids: list[int] = []

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name fehlt")
        return v[:100]

    @field_validator("extension")
    @classmethod
    def _ext(cls, v: str) -> str:
        if not GROUP_EXTENSION_RE.match(v):
            raise ValueError("Gruppen-Durchwahl muss 2000–2099 sein")
        return v

    @field_validator("ring_timeout")
    @classmethod
    def _timeout(cls, v: int) -> int:
        if not 5 <= v <= 120:
            raise ValueError("Klingeldauer 5–120 Sekunden")
        return v

    @field_validator("fallback_extension")
    @classmethod
    def _fallback(cls, v: str | None) -> str | None:
        v = (v or "").strip() or None
        if v and not (USER_EXTENSION_RE.match(v) or GROUP_EXTENSION_RE.match(v)):
            raise ValueError("Weiterleitung nur an 10xx oder 20xx")
        return v

    @field_validator("inbound_number")
    @classmethod
    def _inbound(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        number = normalize_number(v)
        if len(number) < 5:
            raise ValueError("Rufnummer zu kurz")
        return number


async def _apply_group(db: AsyncSession, group: RingGroup, body: GroupIn) -> None:
    clash = await db.scalar(select(RingGroup).where(RingGroup.extension == body.extension))
    if clash and clash.id != group.id:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Durchwahl {body.extension} gehört schon zu „{clash.name}“")
    if body.fallback_extension == body.extension:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Die Gruppe kann nicht an sich selbst weiterleiten")
    if body.inbound_number:
        taken = await db.scalar(select(RingGroup).where(RingGroup.inbound_number == body.inbound_number))
        if taken and taken.id != group.id:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Die Rufnummer ist schon „{taken.name}“ zugeordnet")
    if body.inbound_catch_all:
        # Nur eine Gruppe kann die Hauptnummer sein
        for other in (await db.scalars(select(RingGroup).where(RingGroup.inbound_catch_all.is_(True)))).all():
            if other.id != group.id:
                other.inbound_catch_all = False

    members = (await db.scalars(select(SipAccount).where(SipAccount.id.in_(body.member_ids)))).all() if body.member_ids else []
    group.name = body.name
    group.extension = body.extension
    group.ring_timeout = body.ring_timeout
    group.fallback_extension = body.fallback_extension
    group.inbound_number = body.inbound_number
    group.inbound_catch_all = body.inbound_catch_all
    group.members = list(members)


@router.get("/groups", response_model=list[GroupOut])
async def admin_list_groups(db: AsyncSession = Depends(get_db)) -> list[RingGroup]:
    return list((await db.scalars(select(RingGroup).order_by(RingGroup.extension))).all())


@router.get("/groups/next-extension")
async def admin_next_group_extension(db: AsyncSession = Depends(get_db)) -> dict[str, str | None]:
    used = set((await db.scalars(select(RingGroup.extension))).all())
    return {"extension": next((f"20{n:02d}" for n in range(0, 100) if f"20{n:02d}" not in used), None)}


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def admin_create_group(body: GroupIn, db: AsyncSession = Depends(get_db)) -> RingGroup:
    group = RingGroup()
    await _apply_group(db, group, body)
    db.add(group)
    await db.flush()
    await db.refresh(group)
    logger.warning("[Admin] Gruppe %s „%s“ angelegt", group.extension, group.name)
    return group


@router.put("/groups/{group_id}", response_model=GroupOut)
async def admin_update_group(group_id: int, body: GroupIn, db: AsyncSession = Depends(get_db)) -> RingGroup:
    group = await db.get(RingGroup, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gruppe nicht gefunden")
    await _apply_group(db, group, body)
    await db.flush()
    await db.refresh(group)
    logger.warning("[Admin] Gruppe %s „%s“ geändert", group.extension, group.name)
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_group(group_id: int, db: AsyncSession = Depends(get_db)) -> None:
    group = await db.get(RingGroup, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gruppe nicht gefunden")
    await db.delete(group)
    logger.warning("[Admin] Gruppe %s „%s“ entfernt", group.extension, group.name)


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status", response_model=PbxStatus)
async def admin_status(db: AsyncSession = Depends(get_db)) -> PbxStatus:
    accounts = {a.username: a for a in (await db.scalars(select(SipAccount))).all()}
    try:
        endpoints = await list_pjsip_endpoints()
        channels = await get_active_channels()
    except (ARIError, OSError) as exc:
        return PbxStatus(endpoints=[], calls=[], trunk_state=None, asterisk_error=f"Asterisk nicht erreichbar: {exc}")

    trunk_state = None
    endpoint_list: list[EndpointStatus] = []
    for e in endpoints:
        name = e["resource"]
        if name == _TRUNK:
            trunk_state = e.get("state")
            continue
        account = accounts.get(name)
        endpoint_list.append(EndpointStatus(
            username=name,
            extension=account.extension if account else None,
            display_name=account.display_name if account else None,
            state=e.get("state", "unknown"),
        ))
    endpoint_list.sort(key=lambda e: e.extension or "")

    calls = [
        CallStatus(
            channel=c["name"],
            caller=c.get("caller", {}).get("number", ""),
            caller_name=c.get("caller", {}).get("name") or None,
            connected=c.get("connected", {}).get("number") or c.get("dialplan", {}).get("exten") or None,
            state=c.get("state", ""),
            since=_ari_time(c.get("creationtime")),
        )
        for c in channels
    ]
    return PbxStatus(endpoints=endpoint_list, calls=calls, trunk_state=trunk_state)

