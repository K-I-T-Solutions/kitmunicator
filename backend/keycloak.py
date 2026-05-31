from typing import Any
import httpx
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import get_settings, Settings

bearer_scheme = HTTPBearer()

# JWKS-Cache — wird beim ersten Request befüllt
_jwks_cache: dict[str, Any] | None = None


async def _get_jwks(settings: Settings) -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token ungültig oder abgelaufen",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        jwks = await _get_jwks(settings)
        # Unverified header auslesen um den passenden Key zu wählen
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        signing_key = next(
            (k for k in jwks["keys"] if k.get("kid") == kid),
            None,
        )
        if signing_key is None:
            raise credentials_exception

        base = settings.KEYCLOAK_ISSUER or settings.KEYCLOAK_URL
        issuer = f"{base}/realms/{settings.KEYCLOAK_REALM}"
        # Audience aus dem unverifizierten Token lesen und zurückgeben,
        # damit python-jose nicht auf None==aud prüft.
        # Stattdessen prüfen wir azp (authorized party) manuell.
        unverified_claims = jwt.get_unverified_claims(token)
        aud = unverified_claims.get("aud")
        # jose 3.3 erwartet String oder None – Liste auf erstes Element kürzen
        if isinstance(aud, list):
            aud = aud[0] if aud else None

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=aud,
        )
        azp = payload.get("azp", "")
        if azp != settings.KEYCLOAK_CLIENT_ID:
            raise credentials_exception
        return payload

    except JWTError as e:
        import logging
        logging.getLogger(__name__).warning("JWT-Fehler: %s", e)
        raise credentials_exception
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak nicht erreichbar",
        )


def require_role(role: str):
    """Dependency-Factory: prüft ob der User eine bestimmte Keycloak-Rolle hat."""
    async def _check(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        realm_roles: list[str] = (
            user.get("realm_access", {}).get("roles", [])
        )
        if role not in realm_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rolle '{role}' erforderlich",
            )
        return user
    return _check
