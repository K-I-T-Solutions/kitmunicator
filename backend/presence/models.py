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


class UserPresence(Base):
    __tablename__ = "user_presence"

    # Keycloak-User-ID als Primary Key — ein Eintrag pro User
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[PresenceStatus] = mapped_column(
        SAEnum(PresenceStatus), nullable=False, default=PresenceStatus.available
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
