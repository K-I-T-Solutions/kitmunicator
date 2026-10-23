"""Keycloak-Admin-API über den Service-Client (client_credentials).

Nur lesend: Nutzerliste für die Verwaltung. Der Client braucht in Keycloak
"Service accounts roles" → realm-management: view-users, query-users.
"""
import time
from dataclasses import dataclass

import httpx

from config import get_settings


class KeycloakAdminError(Exception):
    pass


@dataclass
class KeycloakUser:
    id: str
    username: str
    first_name: str
    last_name: str
    email: str | None
    enabled: bool

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username


_token: str | None = None
_token_expires = 0.0


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token, _token_expires
    if _token and time.monotonic() < _token_expires:
        return _token

    s = get_settings()
    if not s.KEYCLOAK_ADMIN_CLIENT_ID or not s.KEYCLOAK_ADMIN_CLIENT_SECRET:
        raise KeycloakAdminError("Keycloak-Service-Client ist nicht konfiguriert")

    resp = await client.post(
        f"{s.KEYCLOAK_URL}/realms/{s.KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": s.KEYCLOAK_ADMIN_CLIENT_ID,
            "client_secret": s.KEYCLOAK_ADMIN_CLIENT_SECRET,
        },
    )
    if resp.status_code != 200:
        raise KeycloakAdminError(f"Keycloak-Login des Service-Clients fehlgeschlagen ({resp.status_code})")
    body = resp.json()
    _token = body["access_token"]
    # Etwas vor Ablauf erneuern
    _token_expires = time.monotonic() + body.get("expires_in", 60) - 30
    return _token


async def list_users() -> list[KeycloakUser]:
    s = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        token = await _get_token(client)
        resp = await client.get(
            f"{s.KEYCLOAK_URL}/admin/realms/{s.KEYCLOAK_REALM}/users",
            params={"max": 500, "briefRepresentation": "true"},
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        raise KeycloakAdminError(f"Nutzerliste aus Keycloak nicht lesbar ({resp.status_code})")
    return [
        KeycloakUser(
            id=u["id"],
            username=u["username"],
            first_name=u.get("firstName", ""),
            last_name=u.get("lastName", ""),
            email=u.get("email"),
            enabled=u.get("enabled", True),
        )
        # Service-Accounts von Clients sind keine Personen
        for u in resp.json()
        if not u["username"].startswith("service-account-")
    ]


async def get_user(user_id: str) -> KeycloakUser | None:
    return next((u for u in await list_users() if u.id == user_id), None)
