"""
Asterisk ARI WebSocket Consumer.

Verfolgt Anruf-State via Channel-Events und setzt:
  - phone_status in UserPresence (ringing / in_call / idle)
  - CallRecord (CDR) beim Beenden jedes Channels
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosed
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func

from config import get_settings
from database import AsyncSessionLocal
from presence.models import UserPresence, PhoneStatus
from telephony.models import SipAccount, CallRecord, CallDirection, CallStatus
from telephony.service import sync_sip_accounts_to_asterisk

log = logging.getLogger(__name__)

# Aktive Channels pro SIP-Username { "jessica": {"PJSIP/jessica-00000001", ...} }
_active_channels: dict[str, set[str]] = {}

# Offene CDR-Einträge pro Channel-ID
_pending_calls: dict[str, dict] = {}

_INTERNAL_EXT = re.compile(r"^10\d{2}$")
_TRUNK_PREFIX = "PJSIP/sipgate_trunk-"


def _username_from_channel(channel_name: str) -> str | None:
    """Extrahiert SIP-Username aus Channel-Name 'PJSIP/jessica-00000001'.
    Gibt None für Trunk-Channels zurück — die werden separat behandelt."""
    if not channel_name.startswith("PJSIP/"):
        return None
    if channel_name.startswith(_TRUNK_PREFIX):
        return None
    rest = channel_name.removeprefix("PJSIP/")
    return rest.split("-")[0] if "-" in rest else rest


def _is_trunk_channel(channel_name: str) -> bool:
    return channel_name.startswith(_TRUNK_PREFIX)


def _call_direction(caller: str, callee: str) -> CallDirection:
    if _INTERNAL_EXT.match(caller) and _INTERNAL_EXT.match(callee):
        return CallDirection.internal
    elif _INTERNAL_EXT.match(caller):
        return CallDirection.outbound
    else:
        return CallDirection.inbound


async def _set_phone_status(sip_username: str, phone_status: PhoneStatus) -> None:
    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(SipAccount).where(SipAccount.username == sip_username)
        )
        if account is None:
            return

        stmt = (
            pg_insert(UserPresence)
            .values(user_id=account.user_id, phone_status=phone_status)
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={"phone_status": phone_status, "updated_at": func.now()},
            )
            .returning(UserPresence)
        )
        result = await db.execute(stmt)
        presence = result.scalar_one()
        await db.commit()

    from presence.router import manager
    asyncio.ensure_future(
        manager.broadcast(account.user_id, presence.status, presence.phone_status, presence.updated_at)
    )
    log.warning("PhoneStatus %s → %s", sip_username, phone_status.value)


async def _write_cdr(channel_id: str, cause: int) -> None:
    """Schreibt einen CDR-Eintrag für den beendeten Channel."""
    info = _pending_calls.pop(channel_id, None)
    if info is None or not info.get("write_cdr", True):
        return

    now = datetime.now(timezone.utc)
    answered: bool = info["answered"]
    answered_at: datetime | None = info.get("answered_at")

    if answered:
        cdr_status = CallStatus.answered
        duration = int((now - answered_at).total_seconds()) if answered_at else 0
    elif cause == 17:
        cdr_status = CallStatus.busy
        duration = 0
    else:
        cdr_status = CallStatus.no_answer
        duration = 0

    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(SipAccount).where(SipAccount.username == info["username"])
        )
        if account is None:
            return

        # Callee-Namen per Extension-Lookup ermitteln
        callee_account = await db.scalar(
            select(SipAccount).where(SipAccount.extension == info["callee_number"])
        )
        callee_name = callee_account.username if callee_account else None

        try:
            record = CallRecord(
                sip_account_id=account.id,
                asterisk_unique_id=channel_id,
                caller_number=info["caller_number"],
                caller_name=info.get("caller_name"),
                callee_number=info["callee_number"],
                callee_name=callee_name,
                direction=info["direction"],
                status=cdr_status,
                duration_seconds=duration,
                started_at=info["started_at"],
                ended_at=now,
            )
            db.add(record)
            await db.commit()
            log.warning(
                "CDR %s → %s (%s, %ds, cause=%d)",
                info["caller_number"], info["callee_number"],
                cdr_status.value, duration, cause,
            )
        except Exception as exc:
            await db.rollback()
            log.warning("CDR-Schreiben fehlgeschlagen: %s", exc)


async def _handle_trunk_channel_created(channel: dict, channel_id: str) -> None:
    """Trackt eingehende Sipgate-Trunk-Channels für CDR.

    Bei Trunk-Anrufen kommt der ChannelCreated-Event für den Trunk-Channel
    bevor Dial() den internen User-Channel erzeugt. Wir merken uns die
    Caller-Daten und schreiben den CDR-Eintrag dem Callee-Account zu.
    """
    caller_number = channel.get("caller", {}).get("number", "") or "unknown"
    caller_name = channel.get("caller", {}).get("name", "") or None
    callee_number = (
        channel.get("dialplan", {}).get("exten", "")
        or channel.get("connected", {}).get("number", "")
        or ""
    )
    created_str = channel.get("creationtime", "")
    try:
        started_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        started_at = datetime.now(timezone.utc)

    if not _INTERNAL_EXT.match(callee_number):
        return

    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(SipAccount).where(SipAccount.extension == callee_number)
        )
        if account is None:
            return
        callee_username = account.username

    _pending_calls[channel_id] = {
        "username": callee_username,
        "caller_number": caller_number,
        "caller_name": caller_name,
        "callee_number": callee_number,
        "direction": CallDirection.inbound,
        "started_at": started_at,
        "answered": False,
        "answered_at": None,
        "write_cdr": True,
    }
    log.info("Trunk-Anruf: %s → %s (%s)", caller_number, callee_number, callee_username)


async def _handle_event(event: dict) -> None:
    event_type = event.get("type", "")
    channel = event.get("channel", {})
    channel_name: str = channel.get("name", "")
    channel_id: str = channel.get("id", "")

    # Eingehende Trunk-Channels separat verarbeiten
    if _is_trunk_channel(channel_name):
        if event_type == "ChannelCreated":
            await _handle_trunk_channel_created(channel, channel_id)
        elif event_type == "ChannelStateChange":
            if channel.get("state") == "Up" and channel_id in _pending_calls:
                _pending_calls[channel_id]["answered"] = True
                _pending_calls[channel_id]["answered_at"] = datetime.now(timezone.utc)
        elif event_type == "ChannelDestroyed":
            cause = event.get("cause", 0)
            asyncio.ensure_future(_write_cdr(channel_id, cause))
        return

    username = _username_from_channel(channel_name)
    if not username:
        return

    if event_type == "ChannelCreated":
        _active_channels.setdefault(username, set()).add(channel_id)
        await _set_phone_status(username, PhoneStatus.ringing)

        caller_number = channel.get("caller", {}).get("number", "") or username
        caller_name = channel.get("caller", {}).get("name", "") or None
        callee_number = (
            channel.get("dialplan", {}).get("exten", "")
            or channel.get("connected", {}).get("number", "")
            or ""
        )
        created_str = channel.get("creationtime", "")
        try:
            started_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            started_at = datetime.now(timezone.utc)

        # "s" ist der Default-Eintrag für Dial()-Outbound-Legs — diese werden
        # nicht als eigener CDR-Eintrag gespeichert, da der Anrufer-Channel
        # bereits den vollständigen Eintrag liefert.
        write_cdr = callee_number not in ("s", "")

        _pending_calls[channel_id] = {
            "username": username,
            "caller_number": caller_number,
            "caller_name": caller_name,
            "callee_number": callee_number,
            "direction": _call_direction(caller_number, callee_number),
            "started_at": started_at,
            "answered": False,
            "answered_at": None,
            "write_cdr": write_cdr,
        }

    elif event_type == "ChannelStateChange":
        state = channel.get("state", "")
        if state == "Up":
            _active_channels.setdefault(username, set()).add(channel_id)
            await _set_phone_status(username, PhoneStatus.in_call)
            if channel_id in _pending_calls:
                _pending_calls[channel_id]["answered"] = True
                _pending_calls[channel_id]["answered_at"] = datetime.now(timezone.utc)

    elif event_type == "ChannelDestroyed":
        channels = _active_channels.get(username, set())
        channels.discard(channel_id)
        if not channels:
            await _set_phone_status(username, PhoneStatus.idle)

        cause = event.get("cause", 0)
        asyncio.ensure_future(_write_cdr(channel_id, cause))


async def ari_consumer() -> None:
    """Dauerhafte ARI WebSocket-Verbindung mit exponentiellem Backoff."""
    settings = get_settings()

    base = settings.ASTERISK_ARI_URL.replace("http://", "ws://").replace("https://", "wss://")
    params = urlencode({
        "api_key": f"{settings.ASTERISK_ARI_USER}:{settings.ASTERISK_ARI_SECRET}",
        "app": "kitmunicator",
        "subscribeAll": "true",
    })
    uri = f"{base}/ari/events?{params}"
    backoff = 1

    while True:
        try:
            async with websockets.connect(uri) as ws:
                log.warning("ARI WebSocket verbunden — warte auf Channel-Events")
                backoff = 1
                _active_channels.clear()
                _pending_calls.clear()

                # Nach (Re-)Connect alle SIP-Accounts in Asterisk registrieren,
                # damit dynamische Endpoints einen Asterisk-Neustart überleben.
                asyncio.ensure_future(sync_sip_accounts_to_asterisk())

                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") in ("ChannelCreated", "ChannelStateChange", "ChannelDestroyed"):
                        await _handle_event(event)

        except (ConnectionClosed, OSError) as exc:
            log.warning("ARI Verbindung verloren (%s) — Reconnect in %ds", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except asyncio.CancelledError:
            log.info("ARI Consumer gestoppt")
            return
