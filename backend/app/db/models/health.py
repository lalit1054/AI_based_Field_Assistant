import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MachineHealth(Base):
    __tablename__ = "machine_health"

    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), primary_key=True
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column()
    is_online: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    cpu_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    memory_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    disk_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    services: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'"))
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False
    )
    reported_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'"))
