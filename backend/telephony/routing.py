"""Routing-Auskünfte für den Dialplan (Personen, Sammelrufe, eingehende Sipgate-Nummern)."""
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from presence.models import PresenceStatus, UserPresence
from telephony.models import RingGroup, SipAccount

# Durchwahl-Bereiche, müssen zu den Dialplan-Patterns passen
USER_EXTENSION_RE = re.compile(r"^10\d{2}$")
GROUP_EXTENSION_RE = re.compile(r"^20\d{2}$")


def normalize_number(raw: str) -> str:
    """Deutsche Rufnummer auf die nationale Nummer ohne 0 bringen.
    '+49 261 1234', '+49 (0)261 1234', '0049 261 1234', '0261 1234' → '2611234'.
    So passt, was der Admin einträgt, zu dem, was Sipgate schickt."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0049"):
        digits = digits[4:]
    elif digits.startswith("49") and len(digits) > 10:
        digits = digits[2:]
    # Auch "+49 (0)261 …" – die Verkehrsausscheidungsziffer fällt weg
    return digits.lstrip("0")


async def _dnd_user_ids(db: AsyncSession, user_ids: list[str]) -> set[str]:
    rows = await db.scalars(
        select(UserPresence.user_id).where(
            UserPresence.user_id.in_(user_ids), UserPresence.status == PresenceStatus.dnd,
        )
    )
    return set(rows.all())


async def callee_info(db: AsyncSession, extension: str) -> str:
    """'username|status|push' für den Dialplan — leer, wenn es die Durchwahl nicht gibt.
    Ob das Telefon registriert ist, prüft Asterisk selbst (PJSIP_DIAL_CONTACTS)."""
    account = await db.scalar(
        select(SipAccount).where(SipAccount.extension == extension, SipAccount.is_active.is_(True))
    )
    if not account:
        return ""
    status = "dnd" if await _dnd_user_ids(db, [account.user_id]) else ""
    return f"{account.username}|{status}|{'1' if account.fcm_token else '0'}"


async def group_dial_info(db: AsyncSession, extension: str) -> str:
    """'timeout|PJSIP/a&PJSIP/b|fallback' — leer, wenn es die Gruppe nicht gibt.
    Gesperrte Mitglieder und „Nicht stören“ fallen raus; Nicht-Registrierte überspringt Dial().
    Ohne erreichbare Mitglieder bleibt der Dial-Teil leer → direkt Weiterleitung."""
    group = await db.scalar(select(RingGroup).where(RingGroup.extension == extension))
    if not group:
        return ""
    members = [m for m in group.members if m.is_active]
    dnd = await _dnd_user_ids(db, [m.user_id for m in members])
    dial = "&".join(f"PJSIP/{m.username}" for m in members if m.user_id not in dnd)
    return f"{group.ring_timeout}|{dial}|{group.fallback_extension or ''}"


async def inbound_target(db: AsyncSession, dialed: str) -> str:
    """Ziel-Durchwahl für einen eingehenden Trunk-Anruf, leer = nicht zugeordnet."""
    if dialed and dialed != "s":
        number = normalize_number(dialed)
        group = await db.scalar(select(RingGroup).where(RingGroup.inbound_number == number))
        if group:
            return group.extension
    catch_all = await db.scalar(select(RingGroup).where(RingGroup.inbound_catch_all.is_(True)))
    return catch_all.extension if catch_all else ""
