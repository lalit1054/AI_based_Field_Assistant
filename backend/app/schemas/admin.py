import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.enums import UserRole


class CompanyIn(BaseModel):
    code: str
    name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    is_active: bool | None = None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PlantIn(BaseModel):
    company_id: uuid.UUID
    code: str
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "Asia/Kolkata"


class PlantUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    is_active: bool | None = None


class PlantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    address: str | None
    latitude: float | None
    longitude: float | None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LineIn(BaseModel):
    plant_id: uuid.UUID
    line_number: int
    name: str | None = None


class LineUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class LineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plant_id: uuid.UUID
    line_number: int
    name: str | None
    is_active: bool


class UserCreateIn(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    password: str = Field(min_length=8)
    language: str = "en"


class UserUpdateIn(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    language: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str
    role: UserRole
    language: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class PlantAccessIn(BaseModel):
    plant_id: uuid.UUID
