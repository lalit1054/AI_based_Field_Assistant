import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import MachineStatus, MachineType, OsType
from app.db.pg_types import pg_enum


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    plants: Mapped[list["Plant"]] = relationship(back_populates="company")


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()
    timezone: Mapped[str] = mapped_column(
        Text, default="Asia/Kolkata", server_default=text("'Asia/Kolkata'")
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    company: Mapped["Company"] = relationship(back_populates="plants")
    lines: Mapped[list["Line"]] = relationship(back_populates="plant")
    machines: Mapped[list["Machine"]] = relationship(back_populates="plant")


class Line(Base):
    __tablename__ = "lines"
    __table_args__ = (UniqueConstraint("plant_id", "line_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    plant: Mapped["Plant"] = relationship(back_populates="lines")
    machines: Mapped[list["Machine"]] = relationship(back_populates="line")


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False
    )
    line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lines.id", ondelete="SET NULL")
    )
    machine_type: Mapped[MachineType] = mapped_column(
        pg_enum(MachineType, "machine_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    hostname: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)
    os: Mapped[OsType | None] = mapped_column(pg_enum(OsType, "os_type"))
    app_version: Mapped[str | None] = mapped_column(Text)
    device_model: Mapped[str | None] = mapped_column(Text)
    log_labels: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'"))
    status: Mapped[MachineStatus] = mapped_column(
        pg_enum(MachineStatus, "machine_status"),
        default=MachineStatus.active,
        server_default=text("'active'"),
    )
    installed_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    plant: Mapped["Plant"] = relationship(back_populates="machines")
    line: Mapped["Line | None"] = relationship(back_populates="machines")
    qr_tokens: Mapped[list["QrToken"]] = relationship(back_populates="machine")


class QrToken(Base):
    __tablename__ = "qr_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    revoked_at: Mapped[datetime | None] = mapped_column()

    machine: Mapped["Machine"] = relationship(back_populates="qr_tokens")
