import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import IssueCategory, KbDocType, MachineType, TicketPriority
from app.db.pg_types import pg_enum

EMBEDDING_DIM = 1024  # must match database-schema.sql: vector(1024)


class KbDocument(Base):
    __tablename__ = "kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[KbDocType] = mapped_column(pg_enum(KbDocType, "kb_doc_type"), nullable=False)
    machine_type: Mapped[MachineType | None] = mapped_column(pg_enum(MachineType, "machine_type"))
    source_object_key: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    chunks: Mapped[list["KbChunk"]] = relationship(back_populates="document")


class KbChunk(Base):
    __tablename__ = "kb_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'")
    )

    document: Mapped["KbDocument"] = relationship(back_populates="chunks")


class KnownError(Base):
    __tablename__ = "known_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    machine_type: Mapped[MachineType] = mapped_column(
        pg_enum(MachineType, "machine_type"), nullable=False
    )
    category: Mapped[IssueCategory] = mapped_column(
        pg_enum(IssueCategory, "issue_category"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    error_signature: Mapped[str] = mapped_column(Text, nullable=False)
    probable_cause: Mapped[str] = mapped_column(Text, nullable=False)
    operator_fix_steps: Mapped[str] = mapped_column(Text, nullable=False)
    engineer_fix_steps: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[TicketPriority] = mapped_column(
        pg_enum(TicketPriority, "ticket_priority"),
        default=TicketPriority.medium,
        server_default=text("'medium'"),
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    hit_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
