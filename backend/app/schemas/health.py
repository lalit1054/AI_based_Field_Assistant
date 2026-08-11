import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HeartbeatIn(BaseModel):
    machine_id: uuid.UUID
    is_online: bool = True
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    memory_percent: float | None = Field(default=None, ge=0, le=100)
    disk_percent: float | None = Field(default=None, ge=0, le=100)
    services: dict = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)


class MachineHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    machine_id: uuid.UUID
    last_heartbeat: datetime | None
    is_online: bool
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float | None
    services: dict
    extra: dict
    updated_at: datetime
