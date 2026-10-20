from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class PresenceStatus(str, Enum):
    available = "available"
    busy = "busy"
    away = "away"
    dnd = "dnd"  # Do Not Disturb


class PhoneStatus(str, Enum):
    idle = "idle"        # NOT_INUSE — Telefon frei
    ringing = "ringing"  # RINGING — klingelt
    in_call = "in_call"  # INUSE/BUSY — im Gespräch
    offline = "offline"  # UNAVAILABLE — nicht registriert


class UserPresence(Base):
    __tablename__ = "user_presence"

    # Keycloak-User-ID als Primary Key — ein Eintrag pro User
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    # Manuell gesetzter Status (vom User selbst)
    status: Mapped[PresenceStatus] = mapped_column(
        SAEnum(PresenceStatus), nullable=False, default=PresenceStatus.available
    )
    # Automatisch aus Asterisk Device-State abgeleitet
    phone_status: Mapped[PhoneStatus] = mapped_column(
        SAEnum(PhoneStatus), nullable=False, default=PhoneStatus.offline
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
