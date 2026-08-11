"""KB document upload + ingestion trigger, known_errors CRUD. Milestone 6.

No real retrieval/agent wiring here (that's Milestone 7's job) — this is
just persistence: chunk+embed documents on upload (fake embeddings unless
`EMBEDDING_FAKE=false`, see app/services/kb_ingest.py), and CRUD for the
known_errors lookup table, with `engineer_fix_steps` hidden from operators.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.enums import IssueCategory, MachineType, UserRole
from app.db.models import KbChunk, KbDocument, KnownError, User
from app.db.session import get_session
from app.schemas.kb import (
    KbDocumentIn,
    KbDocumentOut,
    KnownErrorIn,
    KnownErrorOut,
    KnownErrorUpdate,
)
from app.services.kb_ingest import chunk_text, embed

router = APIRouter(prefix="/kb", tags=["kb"])

WRITE_ROLES = (UserRole.admin, UserRole.support_l2, UserRole.support_l3, UserRole.plant_manager)


def _mask_known_error(known_error: KnownError, user: User) -> KnownErrorOut:
    out = KnownErrorOut.model_validate(known_error)
    if user.role == UserRole.operator:
        out.engineer_fix_steps = None
    return out


# ---- Documents ----


@router.post(
    "/documents",
    response_model=KbDocumentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_document(
    body: KbDocumentIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KbDocumentOut:
    document = KbDocument(
        title=body.title,
        doc_type=body.doc_type,
        machine_type=body.machine_type,
        created_by=user.id,
    )
    db.add(document)
    await db.flush()

    chunks = chunk_text(body.content)
    for index, content in enumerate(chunks):
        vector = await embed(content)
        db.add(
            KbChunk(document_id=document.id, chunk_index=index, content=content, embedding=vector)
        )

    await db.commit()
    await db.refresh(document)
    out = KbDocumentOut.model_validate(document)
    out.chunk_count = len(chunks)
    return out


@router.get("/documents", response_model=list[KbDocumentOut])
async def list_documents(
    machine_type: MachineType | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[KbDocumentOut]:
    stmt = select(KbDocument)
    if machine_type is not None:
        stmt = stmt.where(KbDocument.machine_type == machine_type)
    stmt = stmt.order_by(KbDocument.created_at.desc()).limit(limit).offset(offset)
    documents = list(await db.scalars(stmt))

    results = []
    for doc in documents:
        count = await db.scalar(
            select(func.count()).select_from(KbChunk).where(KbChunk.document_id == doc.id)
        )
        out = KbDocumentOut.model_validate(doc)
        out.chunk_count = count or 0
        results.append(out)
    return results


@router.get("/documents/{document_id}", response_model=KbDocumentOut)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> KbDocumentOut:
    document = await db.get(KbDocument, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    count = await db.scalar(
        select(func.count()).select_from(KbChunk).where(KbChunk.document_id == document.id)
    )
    out = KbDocumentOut.model_validate(document)
    out.chunk_count = count or 0
    return out


# ---- Known errors ----


@router.post(
    "/known-errors",
    response_model=KnownErrorOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_known_error(
    body: KnownErrorIn,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KnownErrorOut:
    known_error = KnownError(**body.model_dump())
    db.add(known_error)
    await db.commit()
    await db.refresh(known_error)
    return _mask_known_error(known_error, user)


@router.get("/known-errors", response_model=list[KnownErrorOut])
async def list_known_errors(
    machine_type: MachineType | None = None,
    category: IssueCategory | None = None,
    is_active: bool | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[KnownErrorOut]:
    stmt = select(KnownError)
    if machine_type is not None:
        stmt = stmt.where(KnownError.machine_type == machine_type)
    if category is not None:
        stmt = stmt.where(KnownError.category == category)
    if is_active is not None:
        stmt = stmt.where(KnownError.is_active == is_active)
    stmt = stmt.order_by(KnownError.created_at.desc()).limit(limit).offset(offset)
    known_errors = list(await db.scalars(stmt))
    return [_mask_known_error(ke, user) for ke in known_errors]


@router.get("/known-errors/{known_error_id}", response_model=KnownErrorOut)
async def get_known_error(
    known_error_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KnownErrorOut:
    known_error = await db.get(KnownError, known_error_id)
    if known_error is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Known error not found")
    known_error.hit_count += 1
    await db.commit()
    await db.refresh(known_error)
    return _mask_known_error(known_error, user)


@router.patch(
    "/known-errors/{known_error_id}",
    response_model=KnownErrorOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_known_error(
    known_error_id: uuid.UUID,
    body: KnownErrorUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KnownErrorOut:
    known_error = await db.get(KnownError, known_error_id)
    if known_error is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Known error not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(known_error, field, value)
    await db.commit()
    await db.refresh(known_error)
    return _mask_known_error(known_error, user)
