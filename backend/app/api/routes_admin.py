"""Admin CRUD: users, plants, lines, companies. Milestone 3.

Every endpoint requires the `admin` role — this is back-office management,
not something plant managers or field roles reach directly (Milestone 5+
health/ticket views will expose plant-scoped read access separately).
"""

import uuid
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.security import hash_password
from app.db.base import Base
from app.db.enums import UserRole
from app.db.models import Company, Line, Plant, User, UserPlantAccess
from app.db.session import get_session
from app.schemas.admin import (
    CompanyIn,
    CompanyOut,
    CompanyUpdate,
    LineIn,
    LineOut,
    LineUpdate,
    PlantAccessIn,
    PlantIn,
    PlantOut,
    PlantUpdate,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles(UserRole.admin))]
)

ModelT = TypeVar("ModelT", bound=Base)


async def _get_or_404(
    db: AsyncSession, model: type[ModelT], obj_id: uuid.UUID, label: str
) -> ModelT:
    obj = await db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} not found")
    return obj


# ---- Companies ----


@router.post("/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def create_company(body: CompanyIn, db: AsyncSession = Depends(get_session)) -> Company:
    if await db.scalar(select(Company).where(Company.code == body.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Company code already exists")
    company = Company(**body.model_dump())
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(
    is_active: bool | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
) -> list[Company]:
    stmt = select(Company)
    if is_active is not None:
        stmt = stmt.where(Company.is_active == is_active)
    stmt = stmt.order_by(Company.name).limit(limit).offset(offset)
    return list(await db.scalars(stmt))


@router.get("/companies/{company_id}", response_model=CompanyOut)
async def get_company(company_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> Company:
    return await _get_or_404(db, Company, company_id, "Company")


@router.patch("/companies/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: uuid.UUID, body: CompanyUpdate, db: AsyncSession = Depends(get_session)
) -> Company:
    company = await _get_or_404(db, Company, company_id, "Company")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await db.commit()
    await db.refresh(company)
    return company


# ---- Plants ----


@router.post("/plants", response_model=PlantOut, status_code=status.HTTP_201_CREATED)
async def create_plant(body: PlantIn, db: AsyncSession = Depends(get_session)) -> Plant:
    await _get_or_404(db, Company, body.company_id, "Company")
    if await db.scalar(select(Plant).where(Plant.code == body.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Plant code already exists")
    plant = Plant(**body.model_dump())
    db.add(plant)
    await db.commit()
    await db.refresh(plant)
    return plant


@router.get("/plants", response_model=list[PlantOut])
async def list_plants(
    company_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
) -> list[Plant]:
    stmt = select(Plant)
    if company_id is not None:
        stmt = stmt.where(Plant.company_id == company_id)
    if is_active is not None:
        stmt = stmt.where(Plant.is_active == is_active)
    stmt = stmt.order_by(Plant.name).limit(limit).offset(offset)
    return list(await db.scalars(stmt))


@router.get("/plants/{plant_id}", response_model=PlantOut)
async def get_plant(plant_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> Plant:
    return await _get_or_404(db, Plant, plant_id, "Plant")


@router.patch("/plants/{plant_id}", response_model=PlantOut)
async def update_plant(
    plant_id: uuid.UUID, body: PlantUpdate, db: AsyncSession = Depends(get_session)
) -> Plant:
    plant = await _get_or_404(db, Plant, plant_id, "Plant")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(plant, field, value)
    await db.commit()
    await db.refresh(plant)
    return plant


# ---- Lines ----


@router.post("/lines", response_model=LineOut, status_code=status.HTTP_201_CREATED)
async def create_line(body: LineIn, db: AsyncSession = Depends(get_session)) -> Line:
    await _get_or_404(db, Plant, body.plant_id, "Plant")
    existing = await db.scalar(
        select(Line).where(Line.plant_id == body.plant_id, Line.line_number == body.line_number)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Line number already exists for this plant")
    line = Line(**body.model_dump())
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


@router.get("/lines", response_model=list[LineOut])
async def list_lines(
    plant_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_session)
) -> list[Line]:
    stmt = select(Line)
    if plant_id is not None:
        stmt = stmt.where(Line.plant_id == plant_id)
    stmt = stmt.order_by(Line.line_number)
    return list(await db.scalars(stmt))


@router.patch("/lines/{line_id}", response_model=LineOut)
async def update_line(
    line_id: uuid.UUID, body: LineUpdate, db: AsyncSession = Depends(get_session)
) -> Line:
    line = await _get_or_404(db, Line, line_id, "Line")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(line, field, value)
    await db.commit()
    await db.refresh(line)
    return line


# ---- Users ----


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateIn, db: AsyncSession = Depends(get_session)) -> User:
    if await db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        language=body.language,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
) -> list[User]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(User.full_name).limit(limit).offset(offset)
    return list(await db.scalars(stmt))


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> User:
    return await _get_or_404(db, User, user_id, "User")


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID, body: UserUpdateIn, db: AsyncSession = Depends(get_session)
) -> User:
    user = await _get_or_404(db, User, user_id, "User")
    updates = body.model_dump(exclude_unset=True, exclude={"password"})
    for field, value in updates.items():
        setattr(user, field, value)
    if body.password:
        user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}/plant-access", response_model=list[PlantOut])
async def list_user_plant_access(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_session)
) -> list[Plant]:
    await _get_or_404(db, User, user_id, "User")
    stmt = (
        select(Plant)
        .join(UserPlantAccess, UserPlantAccess.plant_id == Plant.id)
        .where(UserPlantAccess.user_id == user_id)
    )
    return list(await db.scalars(stmt))


@router.post("/users/{user_id}/plant-access", status_code=status.HTTP_204_NO_CONTENT)
async def grant_plant_access(
    user_id: uuid.UUID, body: PlantAccessIn, db: AsyncSession = Depends(get_session)
) -> None:
    await _get_or_404(db, User, user_id, "User")
    await _get_or_404(db, Plant, body.plant_id, "Plant")
    existing = await db.get(UserPlantAccess, (user_id, body.plant_id))
    if existing is None:
        db.add(UserPlantAccess(user_id=user_id, plant_id=body.plant_id))
        await db.commit()


@router.delete("/users/{user_id}/plant-access/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_plant_access(
    user_id: uuid.UUID, plant_id: uuid.UUID, db: AsyncSession = Depends(get_session)
) -> None:
    access = await db.get(UserPlantAccess, (user_id, plant_id))
    if access is not None:
        await db.delete(access)
        await db.commit()
