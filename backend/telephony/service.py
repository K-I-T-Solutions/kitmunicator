"""Asterisk ARI REST Client — alle Operationen async via httpx."""
import hashlib
import secrets
from typing import Any

import httpx
from cryptography.fernet import Fernet

from config import get_settings, Settings


def _get_ari_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.ASTERISK_ARI_URL,
        auth=(settings.ASTERISK_ARI_USER, settings.ASTERISK_ARI_SECRET),
        timeout=10.0,
    )


def _get_fernet() -> Fernet:
    return Fernet(get_settings().SIP_ENCRYPTION_KEY.encode())


def encrypt_password(password: str) -> str:
    return _get_fernet().encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def generate_sip_password() -> str:
    return secrets.token_urlsafe(24)


class ARIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def _raise_for_ari(response: httpx.Response) -> None:
    if response.is_error:
        try:
            detail = response.json().get("message", response.text)
        except Exception:
            detail = response.text
        raise ARIError(response.status_code, detail)


# ── Endpoints ────────────────────────────────────────────────────────────────
# Endpoints, Auths und AORs liest Asterisk per Realtime aus Views auf
# sip_accounts (Migration 0006) — anlegen/sperren ist ein reines DB-Update.

# Muss zur Realm in der View ps_auths passen
SIP_REALM = "asterisk"


def sip_md5_cred(username: str, password: str) -> str:
    """Digest-Hash für ps_auths (auth_type=md5) — Asterisk braucht kein Klartext-Passwort."""
    return hashlib.md5(f"{username}:{SIP_REALM}:{password}".encode()).hexdigest()


async def list_pjsip_endpoints() -> list[dict[str, Any]]:
    """Alle PJSIP-Endpoints inkl. Realtime, mit state online/offline."""
    settings = get_settings()
    async with _get_ari_client(settings) as client:
        resp = await client.get("/ari/endpoints/PJSIP")
        await _raise_for_ari(resp)
        return resp.json()


async def get_active_channels() -> list[dict[str, Any]]:
    """Gibt alle aktiven Channels zurück (für Presence-Sync)."""
    settings = get_settings()
    async with _get_ari_client(settings) as client:
        resp = await client.get("/ari/channels")
        await _raise_for_ari(resp)
        return resp.json()


async def hangup_channel(channel_id: str) -> None:
    settings = get_settings()
    async with _get_ari_client(settings) as client:
        resp = await client.delete(f"/ari/channels/{channel_id}")
        if resp.status_code not in (200, 204, 404):
            await _raise_for_ari(resp)
