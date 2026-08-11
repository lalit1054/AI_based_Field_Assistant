import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import IssueCategory, KbDocType, MachineType, TicketPriority


class KbDocumentIn(BaseModel):
    title: str
    doc_type: KbDocType
    machine_type: MachineType | None = None
    content: str


class KbDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    doc_type: KbDocType
    machine_type: MachineType | None
    version: int
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0


class KnownErrorIn(BaseModel):
    machine_type: MachineType
    category: IssueCategory
    title: str
    error_signature: str
    probable_cause: str
    operator_fix_steps: str
    engineer_fix_steps: str | None = None
    severity: TicketPriority = TicketPriority.medium


class KnownErrorUpdate(BaseModel):
    title: str | None = None
    error_signature: str | None = None
    probable_cause: str | None = None
    operator_fix_steps: str | None = None
    engineer_fix_steps: str | None = None
    severity: TicketPriority | None = None
    is_active: bool | None = None


class KnownErrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_type: MachineType
    category: IssueCategory
    title: str
    error_signature: str
    probable_cause: str
    operator_fix_steps: str
    engineer_fix_steps: str | None
    severity: TicketPriority
    is_active: bool
    hit_count: int
    created_at: datetime
    updated_at: datetime
