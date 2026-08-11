"""Aggregate dashboard stats. Milestone 9."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.enums import TicketStatus, UserRole
from app.db.models import Machine, MachineHealth, Plant, Ticket, User, UserPlantAccess
from app.db.session import get_session
from app.schemas.dashboard import DashboardStatsOut, RecentTicketOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

CLOSED_STATUSES = (TicketStatus.resolved, TicketStatus.closed)


async def _accessible_plant_ids(db: AsyncSession, user: User) -> list[uuid.UUID] | None:
    if user.role == UserRole.admin:
        return None
    stmt = select(UserPlantAccess.plant_id).where(UserPlantAccess.user_id == user.id)
    return list(await db.scalars(stmt))


@router.get("/stats", response_model=DashboardStatsOut)
async def get_dashboard_stats(
    plant_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DashboardStatsOut:
    accessible = await _accessible_plant_ids(db, user)

    if plant_id is not None:
        if accessible is not None and plant_id not in accessible:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this plant")
        plant_ids: list[uuid.UUID] | None = [plant_id]
    else:
        plant_ids = accessible

    if plant_ids is not None and not plant_ids:
        return DashboardStatsOut(
            plants_count=0,
            machines_count=0,
            machines_online=0,
            machines_offline=0,
            open_tickets_count=0,
            recent_tickets=[],
        )

    plants_stmt = select(func.count()).select_from(Plant)
    machines_stmt = select(func.count()).select_from(Machine)
    if plant_ids is not None:
        plants_stmt = plants_stmt.where(Plant.id.in_(plant_ids))
        machines_stmt = machines_stmt.where(Machine.plant_id.in_(plant_ids))

    plants_count = await db.scalar(plants_stmt) or 0
    machines_count = await db.scalar(machines_stmt) or 0

    online_stmt = (
        select(func.count())
        .select_from(MachineHealth)
        .join(Machine, Machine.id == MachineHealth.machine_id)
        .where(MachineHealth.is_online.is_(True))
    )
    if plant_ids is not None:
        online_stmt = online_stmt.where(Machine.plant_id.in_(plant_ids))
    machines_online = await db.scalar(online_stmt) or 0
    machines_offline = machines_count - machines_online

    open_stmt = (
        select(func.count()).select_from(Ticket).where(Ticket.status.notin_(CLOSED_STATUSES))
    )
    if plant_ids is not None:
        open_stmt = open_stmt.join(Machine, Machine.id == Ticket.machine_id).where(
            Machine.plant_id.in_(plant_ids)
        )
    elif user.role == UserRole.operator:
        open_stmt = open_stmt.where(Ticket.reporter_id == user.id)
    open_tickets_count = await db.scalar(open_stmt) or 0

    recent_stmt = (
        select(Ticket, Machine.name.label("machine_name"))
        .join(Machine, Machine.id == Ticket.machine_id)
        .order_by(Ticket.created_at.desc())
        .limit(5)
    )
    if plant_ids is not None:
        recent_stmt = recent_stmt.where(Machine.plant_id.in_(plant_ids))
    elif user.role == UserRole.operator:
        recent_stmt = recent_stmt.where(Ticket.reporter_id == user.id)

    rows = (await db.execute(recent_stmt)).all()
    recent_tickets = [
        RecentTicketOut(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            title=ticket.title,
            machine_id=ticket.machine_id,
            machine_name=machine_name,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at,
        )
        for ticket, machine_name in rows
    ]

    return DashboardStatsOut(
        plants_count=plants_count,
        machines_count=machines_count,
        machines_online=machines_online,
        machines_offline=machines_offline,
        open_tickets_count=open_tickets_count,
        recent_tickets=recent_tickets,
    )
