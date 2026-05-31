from datetime import datetime
from enum import Enum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base


class CallDirection(str, Enum):
    inbound = "inbound"
    outbound = "outbound"
    internal = "internal"


class CallStatus(str, Enum):
    answered = "answered"
    no_answer = "no_answer"
    busy = "busy"
    failed = "failed"


class SipAccount(Base):
    __tablename__ = "sip_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Keycloak-User-ID (sub-Claim)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Durchwahl z.B. "1001"
    extension: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # Passwort-Hash — Klartext wird nur an Asterisk übergeben, nie gespeichert
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # FCM-Push-Token des Geräts — wird von der App nach Login gesetzt
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    call_records: Mapped[list["CallRecord"]] = relationship(back_populates="sip_account")
    voicemails: Mapped[list["Voicemail"]] = relationship(back_populates="sip_account")


class CallRecord(Base):
    """CDR — Call Detail Record"""
    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sip_account_id: Mapped[int] = mapped_column(ForeignKey("sip_accounts.id"), nullable=False, index=True)
    # Asterisk-interne Unique ID des Channels
    asterisk_unique_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    caller_number: Mapped[str] = mapped_column(String(50), nullable=False)
    callee_number: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[CallDirection] = mapped_column(SAEnum(CallDirection), nullable=False)
    status: Mapped[CallStatus] = mapped_column(SAEnum(CallStatus), nullable=False)
    # Dauer in Sekunden
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sip_account: Mapped["SipAccount"] = relationship(back_populates="call_records")


class Voicemail(Base):
    __tablename__ = "voicemails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sip_account_id: Mapped[int] = mapped_column(ForeignKey("sip_accounts.id"), nullable=False, index=True)
    caller_number: Mapped[str] = mapped_column(String(50), nullable=False)
    # Pfad zur Audiodatei im Asterisk-Dateisystem
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sip_account: Mapped["SipAccount"] = relationship(back_populates="voicemails")
