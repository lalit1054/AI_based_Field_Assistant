"""Ticket CRUD, comments, status workflow, SLA. Milestone 8.

Creation requires an authenticated user (any role) — the QR-landing "report an
issue" flow logs the operator in via `/auth/login-phone` first (which
self-registers on first use), so every ticket has a real reporter rather than
being anonymous. Reads/writes are scoped: `admin` sees everything; `operator`
sees only tickets they reported; every other role sees tickets for machines
in a plant they've been granted access to (`user_plant_access`).
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.enums import TicketPriority, TicketStatus, UserRole
from app.db.models import (
    AuditLog,
    Machine,
    SlaPolicy,
    Ticket,
    TicketComment,
    TicketStatusHistory,
    User,
    UserPlantAccess,
)
from app.db.session import get_session
from app.schemas.tickets import (
    TicketCommentIn,
    TicketCommentOut,
    TicketIn,
    TicketOut,
    TicketUpdate,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

WRITE_ROLES = (UserRole.admin, UserRole.support_l2, UserRole.support_l3, UserRole.plant_manager)


async def _accessible_plant_ids(db: AsyncSession, user: User) -> list[uuid.UUID] | None:
    """None means "no plant restriction" (admin). Otherwise the list of plant
    ids the user may see tickets for (empty list = none)."""
    if user.role == UserRole.admin:
        return None
    stmt = select(UserPlantAccess.plant_id).where(UserPlantAccess.user_id == user.id)
    return list(await db.scalars(stmt))


async def _get_ticket_or_404(db: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


async def _assert_can_view(db: AsyncSession, user: User, ticket: Ticket) -> None:
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.operator:
        if ticket.reporter_id == user.id:
            return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your ticket")
    machine = await db.get(Machine, ticket.machine_id)
    assert machine is not None
    access = await db.get(UserPlantAccess, (user.id, machine.plant_id))
    if access is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this ticket's plant")


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    body: TicketIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Ticket:
    machine = await db.get(Machine, body.machine_id)
    if machine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")

    sla_policy = await db.scalar(select(SlaPolicy).where(SlaPolicy.priority == body.priority))

    now = datetime.now(timezone.utc)
    ticket = Ticket(
        machine_id=body.machine_id,
        reporter_id=user.id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        category=body.category,
        sla_policy_id=sla_policy.id if sla_policy else None,
        first_response_due_at=(
            now + timedelta(minutes=sla_policy.response_minutes) if sla_policy else None
        ),
        resolution_due_at=(
            now + timedelta(minutes=sla_policy.resolution_minutes) if sla_policy else None
        ),
    )
    db.add(ticket)
    await db.flush()

    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id, from_status=None, to_status=ticket.status, changed_by=user.id
        )
    )
    db.add(
        AuditLog(
            user_id=user.id, action="ticket_created", entity_type="ticket", entity_id=ticket.id
        )
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    status_: TicketStatus | None = Query(None, alias="status"),
    priority: TicketPriority | None = None,
    plant_id: uuid.UUID | None = None,
    machine_id: uuid.UUID | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[Ticket]:
    stmt = select(Ticket)
    needs_machine_join = False

    accessible = await _accessible_plant_ids(db, user)
    if user.role == UserRole.operator:
        stmt = stmt.where(Ticket.reporter_id == user.id)
    elif accessible is not None:
        if not accessible:
            return []
        stmt = stmt.where(Machine.plant_id.in_(accessible))
        needs_machine_join = True

    if plant_id is not None:
        stmt = stmt.where(Machine.plant_id == plant_id)
        needs_machine_join = True

    if needs_machine_join:
        stmt = stmt.join(Machine, Machine.id == Ticket.machine_id)

    if status_ is not None:
        stmt = stmt.where(Ticket.status == status_)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    if machine_id is not None:
        stmt = stmt.where(Ticket.machine_id == machine_id)

    stmt = stmt.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    return list(await db.scalars(stmt))


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Ticket:
    ticket = await _get_ticket_or_404(db, ticket_id)
    await _assert_can_view(db, user, ticket)
    return ticket


@router.patch(
    "/{ticket_id}",
    response_model=TicketOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_ticket(
    ticket_id: uuid.UUID,
    body: TicketUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Ticket:
    ticket = await _get_ticket_or_404(db, ticket_id)
    await _assert_can_view(db, user, ticket)

    updates = body.model_dump(exclude_unset=True)
    new_status = updates.get("status")
    if new_status is not None and new_status != ticket.status:
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=ticket.status,
                to_status=new_status,
                changed_by=user.id,
            )
        )
        now = datetime.now(timezone.utc)
        if new_status == TicketStatus.resolved:
            ticket.resolved_at = now
        elif new_status == TicketStatus.closed:
            ticket.closed_at = now

    for field, value in updates.items():
        setattr(ticket, field, value)

    db.add(
        AuditLog(
            user_id=user.id, action="ticket_updated", entity_type="ticket", entity_id=ticket.id
        )
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post(
    "/{ticket_id}/comments", response_model=TicketCommentOut, status_code=status.HTTP_201_CREATED
)
async def add_comment(
    ticket_id: uuid.UUID,
    body: TicketCommentIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TicketComment:
    ticket = await _get_ticket_or_404(db, ticket_id)
    await _assert_can_view(db, user, ticket)

    is_internal = body.is_internal and user.role != UserRole.operator
    comment = TicketComment(
        ticket_id=ticket_id, author_id=user.id, body=body.body, is_internal=is_internal
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentOut])
async def list_comments(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[TicketComment]:
    ticket = await _get_ticket_or_404(db, ticket_id)
    await _assert_can_view(db, user, ticket)

    stmt = select(TicketComment).where(TicketComment.ticket_id == ticket_id)
    if user.role == UserRole.operator:
        stmt = stmt.where(TicketComment.is_internal.is_(False))
    stmt = stmt.order_by(TicketComment.created_at)
    return list(await db.scalars(stmt))
