import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import AttachmentKind


class PresignRequestIn(BaseModel):
    kind: AttachmentKind
    filename: str
    content_type: str
    ticket_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None


class PresignOut(BaseModel):
    upload_url: str
    object_key: str
    bucket: str
    expires_in_seconds: int


class AttachmentConfirmIn(BaseModel):
    kind: AttachmentKind
    object_key: str
    file_name: str
    content_type: str
    size_bytes: int
    ticket_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: AttachmentKind
    ticket_id: uuid.UUID | None
    session_id: uuid.UUID | None
    message_id: uuid.UUID | None
    object_key: str
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: uuid.UUID | None
    created_at: datetime
    download_url: str | None = None
