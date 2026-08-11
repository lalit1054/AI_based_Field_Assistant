import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import MachineStatus, MachineType, OsType


class MachineIn(BaseModel):
    plant_id: uuid.UUID
    line_id: uuid.UUID | None = None
    machine_type: MachineType = MachineType.VISUAL_INSPECTION
    name: str
    hostname: str | None = None
    ip_address: str | None = None
    os: OsType | None = None
    app_version: str | None = None
    device_model: str | None = None
    log_labels: dict = Field(default_factory=dict)
    installed_at: date | None = None
    notes: str | None = None


class MachineUpdate(BaseModel):
    line_id: uuid.UUID | None = None
    name: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    os: OsType | None = None
    app_version: str | None = None
    device_model: str | None = None
    log_labels: dict | None = None
    status: MachineStatus | None = None
    installed_at: date | None = None
    notes: str | None = None


class MachineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plant_id: uuid.UUID
    line_id: uuid.UUID | None
    machine_type: MachineType
    name: str
    hostname: str | None
    ip_address: str | None
    os: OsType | None
    app_version: str | None
    device_model: str | None
    log_labels: dict
    status: MachineStatus
    installed_at: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BulkImportError(BaseModel):
    row: int
    error: str


class BulkImportResult(BaseModel):
    created: int
    errors: list[BulkImportError]
