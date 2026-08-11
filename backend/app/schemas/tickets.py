import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import IssueCategory, TicketPriority, TicketStatus


class TicketIn(BaseModel):
    machine_id: uuid.UUID
    title: str
    description: str | None = None
    priority: TicketPriority = TicketPriority.medium
    category: IssueCategory = IssueCategory.other


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: uuid.UUID | None = None
    resolution_notes: str | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_number: str
    machine_id: uuid.UUID
    session_id: uuid.UUID | None
    reporter_id: uuid.UUID
    assignee_id: uuid.UUID | None
    status: TicketStatus
    priority: TicketPriority
    category: IssueCategory
    title: str
    description: str | None
    diagnosis_summary: str | None
    sla_policy_id: uuid.UUID | None
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    first_responded_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime


class TicketCommentIn(BaseModel):
    body: str
    is_internal: bool = False


class TicketCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    is_internal: bool
    created_at: datetime


class TicketStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    from_status: TicketStatus | None
    to_status: TicketStatus
    changed_by: uuid.UUID | None
    changed_at: datetime
