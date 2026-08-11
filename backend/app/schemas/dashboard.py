import uuid
from datetime import datetime

from pydantic import BaseModel

from app.db.enums import TicketPriority, TicketStatus


class RecentTicketOut(BaseModel):
    id: uuid.UUID
    ticket_number: str
    title: str
    machine_id: uuid.UUID
    machine_name: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime


class DashboardStatsOut(BaseModel):
    plants_count: int
    machines_count: int
    machines_online: int
    machines_offline: int
    open_tickets_count: int
    recent_tickets: list[RecentTicketOut]
