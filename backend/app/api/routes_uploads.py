"""Presigned upload/download for MinIO-backed attachments. Milestone 4."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.db.enums import AttachmentKind
from app.db.models import Attachment, ChatSession, Ticket, User
from app.db.session import get_session
from app.schemas.uploads import (
    AttachmentConfirmIn,
    AttachmentOut,
    PresignOut,
    PresignRequestIn,
)
from app.services.storage import build_object_key, presign_get, presign_put

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _bucket_for(kind: AttachmentKind) -> str:
    settings = get_settings()
    return (
        settings.minio_bucket_log_bundles
        if kind == AttachmentKind.log_bundle
        else settings.minio_bucket_attachments
    )


async def _validate_parent(
    db: AsyncSession, ticket_id: uuid.UUID | None, session_id: uuid.UUID | None
) -> None:
    if ticket_id is None and session_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Either ticket_id or session_id is required"
        )
    if ticket_id is not None and await db.get(Ticket, ticket_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    if session_id is not None and await db.get(ChatSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")


@router.post("/presign", response_model=PresignOut)
async def presign_upload(
    body: PresignRequestIn,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PresignOut:
    await _validate_parent(db, body.ticket_id, body.session_id)

    settings = get_settings()
    bucket = _bucket_for(body.kind)
    object_key = build_object_key(body.kind.value, body.filename)
    upload_url = presign_put(bucket, object_key, body.content_type)

    return PresignOut(
        upload_url=upload_url,
        object_key=object_key,
        bucket=bucket,
        expires_in_seconds=settings.minio_presigned_url_expire_seconds,
    )


@router.post("/attachments", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def confirm_attachment(
    body: AttachmentConfirmIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AttachmentOut:
    """Called after the client has successfully PUT the file to the presigned
    URL — persists the attachment row so the rest of the app can find it."""
    await _validate_parent(db, body.ticket_id, body.session_id)

    attachment = Attachment(
        kind=body.kind,
        ticket_id=body.ticket_id,
        session_id=body.session_id,
        object_key=body.object_key,
        file_name=body.file_name,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
        uploaded_by=user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    out = AttachmentOut.model_validate(attachment)
    out.download_url = presign_get(_bucket_for(attachment.kind), attachment.object_key)
    return out


@router.get("/attachments/{attachment_id}", response_model=AttachmentOut)
async def get_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> AttachmentOut:
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")

    out = AttachmentOut.model_validate(attachment)
    out.download_url = presign_get(_bucket_for(attachment.kind), attachment.object_key)
    return out
