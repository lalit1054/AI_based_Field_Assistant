import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import ChatRole, IssueCategory, SessionStatus


class ChatSessionIn(BaseModel):
    machine_id: uuid.UUID
    category: IssueCategory | None = None


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    user_id: uuid.UUID
    status: SessionStatus
    category: IssueCategory | None
    diagnosis_summary: str | None
    started_at: datetime
    ended_at: datetime | None


class ChatMessageIn(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: ChatRole
    content: str
    created_at: datetime
