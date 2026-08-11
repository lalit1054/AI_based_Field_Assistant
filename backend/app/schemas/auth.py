import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.enums import UserRole

PHONE_PATTERN = r"^\+[1-9]\d{7,14}$"  # E.164


class PhoneLoginIn(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+919800000010"])


class StaffLoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str
    role: UserRole
    language: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
