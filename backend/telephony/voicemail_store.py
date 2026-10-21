"""Voicemail-Abgleich mit dem Asterisk-Spool.

Asterisk legt jede Nachricht als msgNNNN.txt (Metadaten) + msgNNNN.wav ab:
  <spool>/<context>/<durchwahl>/<ordner>/msgNNNN.{txt,wav}
Das Spool-Verzeichnis ist als Volume read-only ins Backend eingehängt.
Asterisk bleibt die Quelle der Wahrheit — die DB-Tabelle hält nur, was der
Spool hergibt, plus den Gelesen-Status aus dem Web-Client.
"""
import asyncio
import configparser
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from telephony.models import SipAccount, Voicemail

logger = logging.getLogger(__name__)

# Ordner, deren Nachrichten als ungelesen gelten (Old = am Telefon abgehört)
UNREAD_FOLDERS = {"INBOX", "Urgent"}
_FOLDERS = ("INBOX", "Urgent", "Old", "Work", "Family", "Friends")

# '"Jessica Schemel" <1002>' | '<1002>' | '1002'
_CALLERID_RE = re.compile(r'^\s*"?(?P<name>[^"<]*?)"?\s*<(?P<num>[^>]*)>\s*$')


@dataclass
class SpoolMessage:
    msg_id: str
    folder: str
    caller_number: str
    caller_name: str | None
    duration_seconds: int
    received_at: datetime
    audio_path: Path


def spool_root() -> Path:
    return Path(get_settings().VOICEMAIL_SPOOL_DIR)


def parse_callerid(raw: str) -> tuple[str, str | None]:
    match = _CALLERID_RE.match(raw)
    if not match:
        return raw.strip() or "unbekannt", None
    name = match.group("name").strip() or None
    number = match.group("num").strip() or "unbekannt"
    return number, None if name == number else name


def _read_message(txt: Path, folder: str) -> SpoolMessage | None:
    audio = txt.with_suffix(".wav")
    if not audio.is_file():
        # Nur wav49 (GSM) vorhanden — kann kein Browser abspielen
        return None

    parser = configparser.RawConfigParser(strict=False, comment_prefixes=(";", "#"))
    try:
        parser.read(txt, encoding="utf-8")
        info = parser["message"]
    except (configparser.Error, KeyError, UnicodeDecodeError):
        logger.warning("[Voicemail] Metadaten unlesbar: %s", txt)
        return None

    origtime = int(info.get("origtime", "0") or 0)
    number, name = parse_callerid(info.get("callerid", ""))
    return SpoolMessage(
        # msg_id fehlt nur bei sehr alten Asterisk-Versionen
        msg_id=info.get("msg_id") or f"{origtime}-{txt.stem}",
        folder=folder,
        caller_number=number,
        caller_name=name,
        duration_seconds=int(info.get("duration", "0") or 0),
        received_at=datetime.fromtimestamp(origtime, tz=timezone.utc),
        audio_path=audio,
    )


def scan_mailbox(extension: str) -> list[SpoolMessage] | None:
    """Liest alle Nachrichten einer Mailbox. None = Spool nicht eingehängt."""
    root = spool_root()
    if not root.is_dir():
        return None

    mailbox = root / get_settings().VOICEMAIL_CONTEXT / extension
    messages: list[SpoolMessage] = []
    for folder in _FOLDERS:
        for txt in sorted((mailbox / folder).glob("msg*.txt")):
            msg = _read_message(txt, folder)
            if msg:
                messages.append(msg)
    return messages


async def sync_mailbox(db: AsyncSession, account: SipAccount) -> None:
    """Gleicht die DB-Einträge eines Accounts mit dem Spool ab."""
    messages = await asyncio.to_thread(scan_mailbox, account.extension)
    if messages is None:
        # Ohne Spool nichts löschen — sonst wären alle Einträge weg
        logger.warning("[Voicemail] Spool %s nicht gefunden", spool_root())
        return

    existing = {
        vm.asterisk_msg_id: vm
        for vm in await db.scalars(
            select(Voicemail).where(Voicemail.sip_account_id == account.id)
        )
    }

    for msg in messages:
        vm = existing.pop(msg.msg_id, None)
        if vm is None:
            db.add(Voicemail(
                sip_account_id=account.id,
                asterisk_msg_id=msg.msg_id,
                caller_number=msg.caller_number,
                caller_name=msg.caller_name,
                file_path=str(msg.audio_path),
                duration_seconds=msg.duration_seconds,
                is_read=msg.folder not in UNREAD_FOLDERS,
                received_at=msg.received_at,
            ))
            continue
        # Asterisk nummeriert beim Verschieben/Löschen neu
        vm.file_path = str(msg.audio_path)
        if msg.folder not in UNREAD_FOLDERS:
            vm.is_read = True

    # Nachrichten, die am Telefon (*98) gelöscht wurden
    for vm in existing.values():
        await db.delete(vm)

    await db.flush()


def resolve_audio(vm: Voicemail) -> Path | None:
    """Pfad zur Audiodatei, nur innerhalb des Spools."""
    root = spool_root().resolve()
    path = Path(vm.file_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    return path
