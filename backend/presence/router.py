"""
Presence-Modul: Status setzen, abfragen und via WebSocket in Echtzeit empfangen.

WebSocket-Protokoll (JSON):
  Client → Server:  {"type": "auth",       "token": "<bearer>"}
  Client → Server:  {"type": "subscribe",  "user_ids": ["id1", "id2"]}
  Server → Client:  {"type": "presence",   "user_id": "...", "status": "...", "updated_at": "..."}
  Server → Client:  {"type": "error",      "detail": "..."}
"""
import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from database import get_db, AsyncSessionLocal
from keycloak import get_current_user, _get_jwks
from config import get_settings
from presence.models import UserPresence, PresenceStatus
from telephony.models import SipAccount

router = APIRouter()


# ── Connection-Manager ────────────────────────────────────────────────────────

class PresenceManager:
    """
    Hält alle aktiven WebSocket-Verbindungen und verteilt Updates.
    Jede Verbindung kann beliebig viele user_ids abonnieren.
    """

    def __init__(self) -> None:
        # websocket → set of subscribed user_ids
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._subscriptions[ws] = set()

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._subscriptions.pop(ws, None)

    async def subscribe(self, ws: WebSocket, user_ids: list[str]) -> None:
        async with self._lock:
            if ws in self._subscriptions:
                self._subscriptions[ws].update(user_ids)

    async def broadcast(self, user_id: str, status: PresenceStatus, updated_at: datetime) -> None:
        """Sendet ein Presence-Update an alle, die diesen User abonniert haben."""
        payload = json.dumps({
            "type": "presence",
            "user_id": user_id,
            "status": status.value,
            "updated_at": updated_at.isoformat(),
        })
        dead: list[WebSocket] = []

        async with self._lock:
            targets = [ws for ws, subs in self._subscriptions.items() if user_id in subs]

        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)


manager = PresenceManager()


# ── Hilfsfunktion: Token aus WebSocket validieren ────────────────────────────

async def _authenticate_ws(token: str) -> dict[str, Any] | None:
    """Gibt den JWT-Payload zurück oder None bei ungültigem Token."""
    from jose import JWTError, jwt as jose_jwt

    settings = get_settings()
    try:
        jwks = await _get_jwks(settings)
        header = jose_jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if key is None:
            return None
        issuer = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        return jose_jwt.decode(
            token, key,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_CLIENT_ID,
            issuer=issuer,
        )
    except (JWTError, Exception):
        return None


# ── Schemas ───────────────────────────────────────────────────────────────────

class PresenceUpdate(BaseModel):
    status: PresenceStatus


class PresenceOut(BaseModel):
    user_id: str
    status: PresenceStatus
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberPresence(BaseModel):
    user_id: str
    username: str
    extension: str
    status: PresenceStatus
    updated_at: datetime | None


# ── REST-Endpoints ────────────────────────────────────────────────────────────

@router.get("/team", response_model=list[TeamMemberPresence])
async def get_team_presence(
    db: AsyncSession = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
) -> list[TeamMemberPresence]:
    """Alle aktiven SIP-User mit ihrem aktuellen Presence-Status."""
    accounts = list((await db.scalars(
        select(SipAccount).where(SipAccount.is_active == True)  # noqa: E712
    )).all())

    user_ids = [a.user_id for a in accounts]
    presence_map = {
        p.user_id: p
        for p in (await db.scalars(
            select(UserPresence).where(UserPresence.user_id.in_(user_ids))
        )).all()
    }

    return [
        TeamMemberPresence(
            user_id=a.user_id,
            username=a.username,
            extension=a.extension,
            status=presence_map[a.user_id].status if a.user_id in presence_map else PresenceStatus.away,
            updated_at=presence_map[a.user_id].updated_at if a.user_id in presence_map else None,
        )
        for a in accounts
    ]


@router.get("/{user_id}", response_model=PresenceOut)
async def get_presence(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
) -> UserPresence:
    presence = await db.scalar(
        select(UserPresence).where(UserPresence.user_id == user_id)
    )
    if not presence:
        # Kein Eintrag → User gilt als offline/away
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein Presence-Eintrag gefunden")
    return presence


@router.put("/me", response_model=PresenceOut)
async def set_my_presence(
    body: PresenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserPresence:
    user_id: str = current_user["sub"]

    # Upsert: Eintrag anlegen oder Status aktualisieren
    stmt = (
        pg_insert(UserPresence)
        .values(user_id=user_id, status=body.status)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"status": body.status, "updated_at": func.now()},
        )
        .returning(UserPresence)
    )
    result = await db.execute(stmt)
    presence = result.scalar_one()
    await db.flush()

    # Alle Subscriber asynchron benachrichtigen
    asyncio.ensure_future(manager.broadcast(user_id, presence.status, presence.updated_at))

    return presence


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/presence")
async def ws_presence(ws: WebSocket) -> None:
    await manager.connect(ws)
    authenticated_user_id: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "detail": "Ungültiges JSON"}))
                continue

            msg_type = msg.get("type")

            if msg_type == "auth":
                token = msg.get("token", "")
                payload = await _authenticate_ws(token)
                if payload is None:
                    await ws.send_text(json.dumps({"type": "error", "detail": "Token ungültig"}))
                    await ws.close(code=4001)
                    return
                authenticated_user_id = payload["sub"]
                await ws.send_text(json.dumps({"type": "auth_ok", "user_id": authenticated_user_id}))

                # Eigenen aktuellen Status direkt senden
                async with AsyncSessionLocal() as db:
                    presence = await db.scalar(
                        select(UserPresence).where(UserPresence.user_id == authenticated_user_id)
                    )
                if presence:
                    await manager.broadcast(authenticated_user_id, presence.status, presence.updated_at)

            elif msg_type == "subscribe":
                if authenticated_user_id is None:
                    await ws.send_text(json.dumps({"type": "error", "detail": "Nicht authentifiziert"}))
                    continue

                user_ids: list[str] = msg.get("user_ids", [])
                if not isinstance(user_ids, list):
                    await ws.send_text(json.dumps({"type": "error", "detail": "user_ids muss eine Liste sein"}))
                    continue

                await manager.subscribe(ws, user_ids)

                # Aktuellen Status aller abonnierten User sofort liefern
                async with AsyncSessionLocal() as db:
                    rows = await db.scalars(
                        select(UserPresence).where(UserPresence.user_id.in_(user_ids))
                    )
                    for p in rows.all():
                        await ws.send_text(json.dumps({
                            "type": "presence",
                            "user_id": p.user_id,
                            "status": p.status.value,
                            "updated_at": p.updated_at.isoformat(),
                        }))

            else:
                await ws.send_text(json.dumps({"type": "error", "detail": f"Unbekannter Typ: {msg_type}"}))

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(ws)


