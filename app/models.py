import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, String, Text,
    UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

UUID_PK = lambda: mapped_column(  # noqa: E731
    UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
)
NOW = lambda: mapped_column(  # noqa: E731
    DateTime(timezone=True), nullable=False, server_default=func.now()
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = UUID_PK()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    fcm_token: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = NOW()
    updated_at: Mapped[datetime] = NOW()


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = UUID_PK()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    created_at: Mapped[datetime] = NOW()


class FamilyMember(Base):
    __tablename__ = "family_members"

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")
    joined_at: Mapped[datetime] = NOW()


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        Index("idx_locations_user_id", "user_id"),
        Index("idx_locations_created_at", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = UUID_PK()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    address: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = NOW()


class WifiStatus(Base):
    __tablename__ = "wifi_status"
    __table_args__ = (UniqueConstraint("user_id", "family_id"),)

    id: Mapped[uuid.UUID] = UUID_PK()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    ssid: Mapped[str] = mapped_column(String(255), nullable=False)
    bssid: Mapped[str] = mapped_column(String(50), nullable=False)
    is_trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    updated_at: Mapped[datetime] = NOW()


class TrustedNetwork(Base):
    __tablename__ = "trusted_networks"
    __table_args__ = (UniqueConstraint("family_id", "bssid"),)

    id: Mapped[uuid.UUID] = UUID_PK()
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    ssid: Mapped[str] = mapped_column(String(255), nullable=False)
    bssid: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")


class Geofence(Base):
    __tablename__ = "geofences"

    id: Mapped[uuid.UUID] = UUID_PK()
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius: Mapped[float] = mapped_column(Float, nullable=False, server_default="200")
    created_at: Mapped[datetime] = NOW()


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_family_id", "family_id"),
        Index("idx_alerts_created_at", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = UUID_PK()
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = NOW()