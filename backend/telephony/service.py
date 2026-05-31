"""Asterisk ARI REST Client — alle Operationen async via httpx."""
import secrets
import hashlib
from typing import Any

import httpx

from config import get_settings, Settings


def _get_ari_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.ASTERISK_ARI_URL,
        auth=(settings.ASTERISK_ARI_USER, settings.ASTERISK_ARI_SECRET),
        timeout=10.0,
    )


def _hash_password(password: str) -> str:
    """SHA-256-Hash für lokale Speicherung (Klartext geht nur an Asterisk)."""
    return hashlib.sha256(password.encode()).hexdigest()


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

async def create_sip_endpoint(username: str, password: str, extension: str) -> dict[str, Any]:
    """Legt einen PJSIP-Endpoint in Asterisk an."""
    settings = get_settings()
    async with _get_ari_client(settings) as client:
        # Endpoint anlegen
        resp = await client.put(
            f"/ari/asterisk/config/dynamic/res_pjsip/endpoint/{username}",
            json={
                "fields": [
                    {"attribute": "transport", "value": "transport-wss"},
                    {"attribute": "context", "value": "internal"},
                    {"attribute": "disallow", "value": "all"},
                    {"attribute": "allow", "value": "opus,g722,ulaw,alaw"},
                    {"attribute": "auth", "value": username},
                    {"attribute": "aors", "value": username},
                    {"attribute": "dtmf_mode", "value": "rfc4733"},
                    {"attribute": "ice_support", "value": "yes"},
                    {"attribute": "media_use_received_transport", "value": "yes"},
                    {"attribute": "force_rport", "value": "yes"},
                    {"attribute": "webrtc", "value": "yes"},
                ]
            },
        )
        await _raise_for_ari(resp)

        # Auth-Objekt anlegen
        resp = await client.put(
            f"/ari/asterisk/config/dynamic/res_pjsip/auth/{username}",
            json={
                "fields": [
                    {"attribute": "auth_type", "value": "userpass"},
                    {"attribute": "username", "value": username},
                    {"attribute": "password", "value": password},
                ]
            },
        )
        await _raise_for_ari(resp)

        # AOR anlegen (Address of Record)
        resp = await client.put(
            f"/ari/asterisk/config/dynamic/res_pjsip/aor/{username}",
            json={
                "fields": [
                    {"attribute": "max_contacts", "value": "3"},
                    {"attribute": "remove_existing", "value": "yes"},
                ]
            },
        )
        await _raise_for_ari(resp)

        return {"endpoint": username, "extension": extension}


async def delete_sip_endpoint(username: str) -> None:
    """Löscht PJSIP-Endpoint, Auth und AOR aus Asterisk."""
    settings = get_settings()
    async with _get_ari_client(settings) as client:
        for object_type in ("endpoint", "auth", "aor"):
            resp = await client.delete(
                f"/ari/asterisk/config/dynamic/res_pjsip/{object_type}/{username}"
            )
            # 404 ist kein Fehler — Objekt war schon weg
            if resp.status_code not in (200, 204, 404):
                await _raise_for_ari(resp)


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
