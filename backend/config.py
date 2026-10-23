from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Datenbank
    DATABASE_URL: str

    # Keycloak
    KEYCLOAK_URL: str          # intern (JWKS-Fetch): http://keycloak:8080
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    # Öffentliche Issuer-URL aus dem JWT – leer = KEYCLOAK_URL verwenden
    KEYCLOAK_ISSUER: str = ""

    # Keycloak-Service-Client (Admin-API: Nutzer lesen für die Verwaltung)
    # Confidential Client mit Service-Account, Rollen realm-management: view-users, query-users
    KEYCLOAK_ADMIN_CLIENT_ID: str = ""
    KEYCLOAK_ADMIN_CLIENT_SECRET: str = ""

    # Asterisk ARI
    ASTERISK_ARI_URL: str
    ASTERISK_ARI_USER: str
    ASTERISK_ARI_SECRET: str

    # WorkmateOS CRM
    WORKMATE_API_URL: str
    WORKMATE_API_KEY: str

    # Firebase / FCM
    FIREBASE_SERVICE_ACCOUNT_FILE: str = "/app/firebase-adminsdk.json"
    FCM_PROJECT_ID: str = "kitmunicator"

    # Gemeinsames Secret für Asterisk → Backend (/telephony/internal/*, Push-Webhook).
    # Leer = alle internen Aufrufe werden abgelehnt.
    ASTERISK_INTERNAL_SECRET: str = ""

    # Asterisk-Voicemail-Spool (Volume, read-only eingehängt)
    VOICEMAIL_SPOOL_DIR: str = "/var/spool/asterisk/voicemail"
    VOICEMAIL_CONTEXT: str = "internal_vm"
    # Eigene Ansagen (Volume, Backend schreibt, Asterisk liest)
    GREETINGS_DIR: str = "/var/lib/kitmunicator/greetings"

    # Fernet-Schlüssel für reversible SIP-Passwortverschlüsselung
    SIP_ENCRYPTION_KEY: str

    # App
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    DEBUG: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
