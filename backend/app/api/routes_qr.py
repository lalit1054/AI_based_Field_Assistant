"""QR token generation, public token resolution, sticker PDF export. Milestone 3."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.security import generate_qr_token
from app.db.enums import UserRole
from app.db.models import AuditLog, Line, Machine, Plant, QrToken
from app.db.session import get_session
from app.schemas.qr import QrResolveOut, QrTokenOut, StickerExportIn
from app.services.qr import build_sticker_pdf

router = APIRouter(tags=["qr"])

WRITE_ROLES = (UserRole.admin, UserRole.support_l2, UserRole.support_l3, UserRole.plant_manager)


async def _get_machine_or_404(db: AsyncSession, machine_id: uuid.UUID) -> Machine:
    machine = await db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")
    return machine


async def _require_machine(db: AsyncSession, machine_id: uuid.UUID) -> Machine:
    """For a machine_id sourced from a trusted FK (e.g. qr_token.machine_id) —
    should never be None, so this is an invariant check, not a 404 case."""
    machine = await db.get(Machine, machine_id)
    assert machine is not None
    return machine


async def _require_plant(db: AsyncSession, plant_id: uuid.UUID) -> Plant:
    """machine.plant_id is a NOT NULL FK — should never be None."""
    plant = await db.get(Plant, plant_id)
    assert plant is not None
    return plant


async def _latest_active_token(db: AsyncSession, machine_id: uuid.UUID) -> QrToken | None:
    return await db.scalar(
        select(QrToken)
        .where(QrToken.machine_id == machine_id, QrToken.is_active.is_(True))
        .order_by(QrToken.created_at.desc())
    )


@router.post(
    "/qr/machines/{machine_id}/tokens",
    response_model=QrTokenOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def issue_qr_token(
    machine_id: uuid.UUID,
    revoke_existing: bool = True,
    db: AsyncSession = Depends(get_session),
) -> QrToken:
    await _get_machine_or_404(db, machine_id)
    if revoke_existing:
        now = datetime.now(timezone.utc)
        existing = await db.scalars(
            select(QrToken).where(QrToken.machine_id == machine_id, QrToken.is_active.is_(True))
        )
        for token in existing:
            token.is_active = False
            token.revoked_at = now

    qr_token = QrToken(machine_id=machine_id, token=generate_qr_token())
    db.add(qr_token)
    await db.commit()
    await db.refresh(qr_token)
    return qr_token


@router.get("/qr/machines/{machine_id}/tokens", response_model=list[QrTokenOut])
async def list_qr_tokens(
    machine_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> list[QrToken]:
    await _get_machine_or_404(db, machine_id)
    stmt = (
        select(QrToken).where(QrToken.machine_id == machine_id).order_by(QrToken.created_at.desc())
    )
    return list(await db.scalars(stmt))


@router.post(
    "/qr/tokens/{token_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def revoke_qr_token(token_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> None:
    qr_token = await db.get(QrToken, token_id)
    if qr_token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "QR token not found")
    if qr_token.is_active:
        qr_token.is_active = False
        qr_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()


@router.get("/a/{token}", response_model=QrResolveOut)
async def resolve_qr_token(token: str, db: AsyncSession = Depends(get_session)) -> QrResolveOut:
    """Public, no auth — this is what the frontend's /a/<token> route calls
    right after a field user scans the sticker, to find out which machine
    it's for before routing them into the chat/ticket flow.
    """
    qr_token = await db.scalar(select(QrToken).where(QrToken.token == token))
    if qr_token is None or not qr_token.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or revoked QR code")

    machine = await _require_machine(db, qr_token.machine_id)
    plant = await _require_plant(db, machine.plant_id)
    line = await db.get(Line, machine.line_id) if machine.line_id else None

    db.add(AuditLog(action="qr_scanned", entity_type="machine", entity_id=machine.id))
    await db.commit()

    return QrResolveOut(
        machine_id=machine.id,
        machine_name=machine.name,
        machine_status=machine.status.value,
        plant_id=plant.id,
        plant_name=plant.name,
        plant_code=plant.code,
        line_id=line.id if line else None,
        line_name=line.name if line else None,
    )


@router.get("/qr/machines/{machine_id}/sticker.pdf")
async def machine_sticker(
    machine_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> Response:
    machine = await _get_machine_or_404(db, machine_id)
    token = await _latest_active_token(db, machine_id)
    if token is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No active QR token for this machine — issue one first"
        )
    plant = await _require_plant(db, machine.plant_id)
    pdf_bytes = build_sticker_pdf([(token.token, machine.name, plant.name)])
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/qr/stickers/export", dependencies=[Depends(require_roles(*WRITE_ROLES))])
async def export_stickers(
    body: StickerExportIn, db: AsyncSession = Depends(get_session)
) -> Response:
    entries: list[tuple[str, str, str]] = []
    for machine_id in body.machine_ids:
        machine = await db.get(Machine, machine_id)
        if machine is None:
            continue
        token = await _latest_active_token(db, machine_id)
        if token is None:
            continue
        plant = await _require_plant(db, machine.plant_id)
        entries.append((token.token, machine.name, plant.name))

    if not entries:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "No machines with an active QR token found"
        )

    pdf_bytes = build_sticker_pdf(entries)
    return Response(content=pdf_bytes, media_type="application/pdf")
