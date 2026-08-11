import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QrTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    token: str
    is_active: bool
    created_at: datetime
    revoked_at: datetime | None


class QrResolveOut(BaseModel):
    machine_id: uuid.UUID
    machine_name: str
    machine_status: str
    plant_id: uuid.UUID
    plant_name: str
    plant_code: str
    line_id: uuid.UUID | None
    line_name: str | None


class StickerExportIn(BaseModel):
    machine_ids: list[uuid.UUID]
