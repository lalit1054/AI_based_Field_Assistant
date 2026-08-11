"""JWT auth, staff login. Milestone 2.

Two login paths into the same token pair:
- `/login-phone` — phone only, no verification step; self-registers an
  `operator` user on first login (field ops have no separate signup flow).
- `/login` — email + password for staff roles (password_hash set by an
  admin, e.g. via seed data or the admin CRUD routes in Milestone 3).

Both issue a short-lived JWT access token plus an opaque refresh token
(rotated on every `/refresh`, revocable via `/logout`).
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.db.enums import UserRole
from app.db.models import RefreshToken, User
from app.db.session import get_session
from app.schemas.auth import (
    LogoutIn,
    PhoneLoginIn,
    RefreshIn,
    StaffLoginIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


async def _issue_tokens(db: AsyncSession, user: User) -> TokenOut:
    access_token = create_access_token(str(user.id), user.role.value)
    raw_refresh, refresh_hash = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return TokenOut(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/login-phone", response_model=TokenOut)
async def login_phone(body: PhoneLoginIn, db: AsyncSession = Depends(get_session)) -> TokenOut:
    user = await db.scalar(select(User).where(User.phone == body.phone))
    if user is None:
        # First login for this phone self-registers an operator.
        # full_name is a placeholder until the user (or an admin) sets a real one.
        user = User(phone=body.phone, full_name=body.phone, role=UserRole.operator)
        db.add(user)
        await db.flush()
    elif not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is deactivated")

    return await _issue_tokens(db, user)


@router.post("/login", response_model=TokenOut)
async def staff_login(body: StaffLoginIn, db: AsyncSession = Depends(get_session)) -> TokenOut:
    user = await db.scalar(select(User).where(User.email == body.email))
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is deactivated")

    return await _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_session)) -> TokenOut:
    token_hash = hash_refresh_token(body.refresh_token)
    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    stored.revoked_at = now
    return await _issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutIn, db: AsyncSession = Depends(get_session)) -> None:
    token_hash = hash_refresh_token(body.refresh_token)
    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
