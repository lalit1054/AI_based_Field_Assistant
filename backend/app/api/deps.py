import uuid

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_access_token
from app.db.enums import UserRole
from app.db.models import User
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def require_roles(*roles: UserRole):
    """Dependency factory for endpoints restricted to specific roles, e.g.
    `Depends(require_roles(UserRole.admin, UserRole.support_l2))`.
    """

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return dependency


async def require_agent_heartbeat(
    x_plant_code: str = Header(...),
    x_agent_key: str = Header(...),
) -> str:
    """Auth for the field-agent heartbeat endpoint — machines authenticate with
    a shared per-plant key (settings.agent_heartbeat_key_map), not a JWT/User.
    Returns the plant code on success, for the caller to cross-check against
    the machine's actual plant.
    """
    key_map = get_settings().agent_heartbeat_key_map
    expected = key_map.get(x_plant_code)
    if expected is None or expected != x_agent_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid plant code or agent key")
    return x_plant_code
