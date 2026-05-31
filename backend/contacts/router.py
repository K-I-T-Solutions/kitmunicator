"""
Contacts-Router: Proxy zur WorkmateOS CRM API mit In-Memory-Cache.

Caching-Strategie:
  - Pro User wird die Kontaktliste für CACHE_TTL_SECONDS gecacht.
  - Einzelne Kontakte werden separat gecacht (nützlich für Dialer-Lookup).
  - Cache wird bei PUT /contacts/cache/invalidate manuell geleert (Admin).
"""
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from config import get_settings, Settings
from keycloak import get_current_user, require_role

router = APIRouter()

CACHE_TTL_SECONDS = 300  # 5 Minuten


# ── In-Memory-Cache ───────────────────────────────────────────────────────────

class _CacheEntry:
    __slots__ = ("data", "expires_at")

    def __init__(self, data: Any, ttl: int) -> None:
        self.data = data
        self.expires_at = time.monotonic() + ttl


_cache: dict[str, _CacheEntry] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None or time.monotonic() > entry.expires_at:
        _cache.pop(key, None)
        return None
    return entry.data


def _cache_set(key: str, data: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
    _cache[key] = _CacheEntry(data, ttl)


# ── WorkmateOS HTTP-Client ────────────────────────────────────────────────────

def _workmate_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.WORKMATE_API_URL,
        headers={"Authorization": f"Bearer {settings.WORKMATE_API_KEY}"},
        timeout=10.0,
    )


async def _workmate_get(path: str, params: dict | None = None) -> Any:
    settings = get_settings()
    async with _workmate_client(settings) as client:
        resp = await client.get(path, params=params)
        if resp.status_code == 404:
            return None
        if resp.is_error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"WorkmateOS-Fehler {resp.status_code}: {resp.text[:200]}",
            )
        return resp.json()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContactOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    display_name: str
    phone_numbers: list[str]
    email: str | None = None
    department: str | None = None
    avatar_url: str | None = None


class ContactListOut(BaseModel):
    items: list[ContactOut]
    total: int
    page: int
    page_size: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ContactListOut)
async def list_contacts(
    search: str | None = Query(None, description="Name oder Nummer"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ContactListOut:
    cache_key = f"contacts:list:{current_user['sub']}:{search}:{page}:{page_size}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    data = await _workmate_get(
        "/api/v1/contacts",
        params={"search": search, "page": page, "page_size": page_size},
    )
    if data is None:
        data = {"items": [], "total": 0, "page": page, "page_size": page_size}

    result = ContactListOut(**data)
    _cache_set(cache_key, result)
    return result


@router.get("/lookup", response_model=ContactOut | None)
async def lookup_by_number(
    number: str = Query(..., description="Rufnummer für Dialer-Lookup"),
    _: dict[str, Any] = Depends(get_current_user),
) -> ContactOut | None:
    """Schnellsuche nach Rufnummer — wird vom Dialer bei eingehenden Anrufen genutzt."""
    cache_key = f"contacts:lookup:{number}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    data = await _workmate_get("/api/v1/contacts/lookup", params={"phone": number})
    result = ContactOut(**data) if data else None

    # Nicht-gefundene Nummern kurz cachen (verhindert Spam bei verpassten Anrufen)
    _cache_set(cache_key, result, ttl=60)
    return result


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(
    contact_id: str,
    _: dict[str, Any] = Depends(get_current_user),
) -> ContactOut:
    cache_key = f"contacts:single:{contact_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    data = await _workmate_get(f"/api/v1/contacts/{contact_id}")
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kontakt nicht gefunden")

    result = ContactOut(**data)
    _cache_set(cache_key, result)
    return result


@router.delete("/cache/invalidate", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_cache(
    _: dict[str, Any] = Depends(require_role("telephony_admin")),
) -> None:
    """Leert den gesamten Kontakt-Cache (z.B. nach CRM-Import)."""
    _cache.clear()
