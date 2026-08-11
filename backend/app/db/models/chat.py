import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ChatRole, IssueCategory, SessionStatus
from app.db.pg_types import pg_enum


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (CheckConstraint("user_rating BETWEEN 1 AND 5", name="user_rating_check"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SessionStatus] = mapped_column(
        pg_enum(SessionStatus, "session_status"),
        default=SessionStatus.active,
        server_default=text("'active'"),
    )
    category: Mapped[IssueCategory | None] = mapped_column(pg_enum(IssueCategory, "issue_category"))
    langgraph_thread_id: Mapped[str | None] = mapped_column(Text)
    diagnosis_summary: Mapped[str | None] = mapped_column(Text)
    token_cost_usd: Mapped[float | None] = mapped_column(
        Numeric(10, 4), default=0, server_default=text("0")
    )
    user_rating: Mapped[int | None] = mapped_column(SmallInteger)
    started_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    ended_at: Mapped[datetime | None] = mapped_column()

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(pg_enum(ChatRole, "chat_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    tool_name: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
