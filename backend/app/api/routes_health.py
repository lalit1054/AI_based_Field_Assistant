"""Heartbeat ingest (agent-key auth) + machine health card. Milestone 5."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_agent_heartbeat
from app.db.models import Heartbeat, Machine, MachineHealth, Plant
from app.db.session import get_session
from app.schemas.health import HeartbeatIn, MachineHealthOut

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/heartbeat", response_model=MachineHealthOut, status_code=status.HTTP_200_OK)
async def ingest_heartbeat(
    body: HeartbeatIn,
    db: AsyncSession = Depends(get_session),
    plant_code: str = Depends(require_agent_heartbeat),
) -> MachineHealth:
    machine = await db.get(Machine, body.machine_id)
    if machine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")

    plant = await db.get(Plant, machine.plant_id)
    assert plant is not None
    if plant.code != plant_code:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Agent key not valid for this machine's plant"
        )

    now = datetime.now(timezone.utc)
    health = await db.get(MachineHealth, body.machine_id)
    if health is None:
        health = MachineHealth(machine_id=body.machine_id)
        db.add(health)

    health.last_heartbeat = now
    health.is_online = body.is_online
    health.cpu_percent = body.cpu_percent
    health.memory_percent = body.memory_percent
    health.disk_percent = body.disk_percent
    health.services = body.services
    health.extra = body.extra
    health.updated_at = now

    db.add(Heartbeat(machine_id=body.machine_id, metrics=body.model_dump(mode="json")))

    await db.commit()
    await db.refresh(health)
    return health


@router.get("/machines/{machine_id}", response_model=MachineHealthOut)
async def get_machine_health(
    machine_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> MachineHealth:
    health = await db.get(MachineHealth, machine_id)
    if health is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No health data reported for this machine yet"
        )
    return health


@router.get("/machines", response_model=list[MachineHealthOut])
async def list_machine_health(
    plant_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> list[MachineHealth]:
    stmt = select(MachineHealth)
    if plant_id is not None:
        stmt = stmt.join(Machine, Machine.id == MachineHealth.machine_id).where(
            Machine.plant_id == plant_id
        )
    return list(await db.scalars(stmt))
