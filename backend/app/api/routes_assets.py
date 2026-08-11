"""Machine registry CRUD (companies/plants/lines/machines), bulk import.
Milestone 3 (registry). Health card lands in Milestone 5.
"""

import uuid
from io import BytesIO

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.enums import MachineStatus, MachineType, UserRole
from app.db.models import Line, Machine, Plant
from app.db.session import get_session
from app.schemas.assets import (
    BulkImportError,
    BulkImportResult,
    MachineIn,
    MachineOut,
    MachineUpdate,
)

router = APIRouter(prefix="/assets", tags=["assets"])

WRITE_ROLES = (UserRole.admin, UserRole.support_l2, UserRole.support_l3, UserRole.plant_manager)


async def _get_machine_or_404(db: AsyncSession, machine_id: uuid.UUID) -> Machine:
    machine = await db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")
    return machine


def _row_cell(row: tuple, col_index: dict[str, int], name: str) -> str | None:
    idx = col_index.get(name)
    if idx is None or idx >= len(row):
        return None
    value = row[idx]
    return str(value).strip() if value is not None else None


@router.post(
    "/machines",
    response_model=MachineOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_machine(body: MachineIn, db: AsyncSession = Depends(get_session)) -> Machine:
    if await db.get(Plant, body.plant_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    if body.line_id is not None:
        line = await db.get(Line, body.line_id)
        if line is None or line.plant_id != body.plant_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Line does not belong to this plant")

    machine = Machine(**body.model_dump())
    db.add(machine)
    await db.commit()
    await db.refresh(machine)
    return machine


@router.get("/machines", response_model=list[MachineOut])
async def list_machines(
    plant_id: uuid.UUID | None = None,
    line_id: uuid.UUID | None = None,
    machine_type: MachineType | None = None,
    status_: MachineStatus | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> list[Machine]:
    stmt = select(Machine)
    if plant_id is not None:
        stmt = stmt.where(Machine.plant_id == plant_id)
    if line_id is not None:
        stmt = stmt.where(Machine.line_id == line_id)
    if machine_type is not None:
        stmt = stmt.where(Machine.machine_type == machine_type)
    if status_ is not None:
        stmt = stmt.where(Machine.status == status_)
    stmt = stmt.order_by(Machine.name).limit(limit).offset(offset)
    return list(await db.scalars(stmt))


@router.get("/machines/{machine_id}", response_model=MachineOut)
async def get_machine(
    machine_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> Machine:
    return await _get_machine_or_404(db, machine_id)


@router.patch(
    "/machines/{machine_id}",
    response_model=MachineOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_machine(
    machine_id: uuid.UUID, body: MachineUpdate, db: AsyncSession = Depends(get_session)
) -> Machine:
    machine = await _get_machine_or_404(db, machine_id)
    updates = body.model_dump(exclude_unset=True)
    if updates.get("line_id") is not None:
        line = await db.get(Line, updates["line_id"])
        if line is None or line.plant_id != machine.plant_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Line does not belong to this plant")
    for field, value in updates.items():
        setattr(machine, field, value)
    await db.commit()
    await db.refresh(machine)
    return machine


@router.post(
    "/machines/bulk-import",
    response_model=BulkImportResult,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def bulk_import_machines(
    file: UploadFile, db: AsyncSession = Depends(get_session)
) -> BulkImportResult:
    """Expects an .xlsx with a header row: plant_code, line_number (optional),
    name, hostname (optional), device_model (optional), notes (optional).
    Every machine is created as machine_type=VISUAL_INSPECTION, status=active.
    Plants/lines must already exist (create them via /admin first) — this
    endpoint doesn't create them.
    """
    raw = await file.read()
    try:
        workbook = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Could not read spreadsheet: {exc}"
        ) from exc

    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Spreadsheet is empty")

    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    missing = [c for c in ("plant_code", "name") if c not in header]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Missing required column(s): {', '.join(missing)}"
        )
    col_index = {name: i for i, name in enumerate(header)}

    plant_cache: dict[str, Plant] = {}
    created = 0
    errors: list[BulkImportError] = []

    for row_num, row in enumerate(rows[1:], start=2):
        if row is None or all(cell is None for cell in row):
            continue

        plant_code = _row_cell(row, col_index, "plant_code")
        name = _row_cell(row, col_index, "name")
        if not plant_code or not name:
            errors.append(BulkImportError(row=row_num, error="plant_code and name are required"))
            continue

        plant = plant_cache.get(plant_code)
        if plant is None:
            plant = await db.scalar(select(Plant).where(Plant.code == plant_code))
            if plant is None:
                errors.append(
                    BulkImportError(row=row_num, error=f"Unknown plant_code '{plant_code}'")
                )
                continue
            plant_cache[plant_code] = plant

        line_id = None
        line_number_raw = _row_cell(row, col_index, "line_number")
        if line_number_raw:
            try:
                line_number = int(float(line_number_raw))
            except ValueError:
                errors.append(BulkImportError(row=row_num, error="line_number must be a number"))
                continue
            line = await db.scalar(
                select(Line).where(Line.plant_id == plant.id, Line.line_number == line_number)
            )
            if line is None:
                errors.append(
                    BulkImportError(
                        row=row_num, error=f"No line {line_number} for plant '{plant_code}'"
                    )
                )
                continue
            line_id = line.id

        db.add(
            Machine(
                plant_id=plant.id,
                line_id=line_id,
                machine_type=MachineType.VISUAL_INSPECTION,
                name=name,
                hostname=_row_cell(row, col_index, "hostname"),
                device_model=_row_cell(row, col_index, "device_model"),
                notes=_row_cell(row, col_index, "notes"),
            )
        )
        created += 1

    await db.commit()
    return BulkImportResult(created=created, errors=errors)
