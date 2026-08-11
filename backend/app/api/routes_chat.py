"""Chat session lifecycle + messages. Milestone 7 (bounded scope).

No SSE streaming, no LangGraph diagnostic agent yet — sessions/messages are
persisted and a synchronous keyword-matched canned reply
(app/services/canned_reply.py) stands in for the real assistant, mirroring
the frontend's previous mockAssistant.ts behavior so the UI doesn't regress
while the real agent is built in a later pass.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.enums import ChatRole, UserRole
from app.db.models import ChatMessage, ChatSession, Machine, User
from app.db.session import get_session
from app.schemas.chat import ChatMessageIn, ChatMessageOut, ChatSessionIn, ChatSessionOut
from app.services.canned_reply import get_reply

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_session_or_404(db: AsyncSession, session_id: uuid.UUID) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    return session


def _assert_can_access(user: User, session: ChatSession) -> None:
    if user.role == UserRole.admin or session.user_id == user.id:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your chat session")


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatSession:
    machine = await db.get(Machine, body.machine_id)
    if machine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")

    session = ChatSession(machine_id=body.machine_id, user_id=user.id, category=body.category)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    session = await _get_session_or_404(db, session_id)
    _assert_can_access(user, session)

    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(await db.scalars(stmt))


@router.post(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageOut],
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    session_id: uuid.UUID,
    body: ChatMessageIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    session = await _get_session_or_404(db, session_id)
    _assert_can_access(user, session)

    user_message = ChatMessage(session_id=session_id, role=ChatRole.user, content=body.content)
    db.add(user_message)

    assistant_message = ChatMessage(
        session_id=session_id, role=ChatRole.assistant, content=get_reply(body.content)
    )
    db.add(assistant_message)

    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)
    return [user_message, assistant_message]
