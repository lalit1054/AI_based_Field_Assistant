"""Round-trips every model through a real Postgres instance running the
Alembic-migrated schema, exercising FKs, enums, defaults, and the
ticket-number trigger. Not exhaustive business-logic testing (that comes
with each later milestone) — just proof the models match the schema.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.enums import (
    AttachmentKind,
    ChatRole,
    IssueCategory,
    KbDocType,
    MachineType,
    NotifyChannel,
    SessionStatus,
    TicketPriority,
    UserRole,
)
from app.db.models import (
    Attachment,
    AuditLog,
    ChatMessage,
    ChatSession,
    Company,
    Heartbeat,
    KbChunk,
    KbDocument,
    KnownError,
    Line,
    Machine,
    MachineHealth,
    Notification,
    Plant,
    QrToken,
    RefreshToken,
    SlaPolicy,
    Ticket,
    TicketComment,
    TicketStatusHistory,
    User,
    UserPlantAccess,
)


async def test_full_model_round_trip(db_session):
    company = Company(code=f"TEST-{uuid.uuid4().hex[:8]}", name="Test Company")
    db_session.add(company)
    await db_session.flush()

    plant = Plant(company_id=company.id, code=f"PLANT-{uuid.uuid4().hex[:8]}", name="Test Plant")
    db_session.add(plant)
    await db_session.flush()

    line = Line(plant_id=plant.id, line_number=1, name="Line 1")
    db_session.add(line)
    await db_session.flush()

    machine = Machine(
        plant_id=plant.id,
        line_id=line.id,
        machine_type=MachineType.VISUAL_INSPECTION,
        name="Test VI Cam",
        log_labels={"plant": plant.code, "line": "1", "machine": "vi"},
    )
    db_session.add(machine)
    await db_session.flush()
    assert machine.status.value == "active"

    qr_token = QrToken(machine_id=machine.id, token=uuid.uuid4().hex[:26])
    db_session.add(qr_token)

    user = User(
        phone=f"+91900000{uuid.uuid4().hex[:4]}",
        full_name="Test Operator",
        role=UserRole.operator,
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(UserPlantAccess(user_id=user.id, plant_id=plant.id))
    db_session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc),
        )
    )
    await db_session.flush()

    chat_session = ChatSession(
        machine_id=machine.id,
        user_id=user.id,
        status=SessionStatus.active,
        category=IssueCategory.camera_image,
    )
    db_session.add(chat_session)
    await db_session.flush()

    chat_message = ChatMessage(
        session_id=chat_session.id, role=ChatRole.user, content="camera is dark"
    )
    db_session.add(chat_message)
    await db_session.flush()

    sla_policy = await db_session.scalar(
        select(SlaPolicy).where(SlaPolicy.priority == TicketPriority.high)
    )
    assert sla_policy is not None  # seeded by the 0001_initial migration

    ticket = Ticket(
        machine_id=machine.id,
        session_id=chat_session.id,
        reporter_id=user.id,
        priority=TicketPriority.high,
        category=IssueCategory.camera_image,
        title="Camera feed is blank",
        sla_policy_id=sla_policy.id,
    )
    db_session.add(ticket)
    await db_session.flush()
    assert ticket.ticket_number.startswith("TKT-")  # set by the assign_ticket_number trigger

    db_session.add(TicketComment(ticket_id=ticket.id, author_id=user.id, body="Looking into it"))
    db_session.add(
        TicketStatusHistory(
            ticket_id=ticket.id, from_status=None, to_status=ticket.status, changed_by=user.id
        )
    )

    db_session.add(
        Attachment(
            kind=AttachmentKind.photo,
            session_id=chat_session.id,
            object_key="attachments/test.jpg",
            file_name="test.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
            uploaded_by=user.id,
        )
    )

    kb_document = KbDocument(
        title="VI Runbook", doc_type=KbDocType.runbook, machine_type=MachineType.VISUAL_INSPECTION
    )
    db_session.add(kb_document)
    await db_session.flush()

    db_session.add(
        KbChunk(document_id=kb_document.id, chunk_index=0, content="Check the camera cable.")
    )

    db_session.add(
        KnownError(
            machine_type=MachineType.VISUAL_INSPECTION,
            category=IssueCategory.camera_image,
            title="Blank camera feed",
            error_signature=r"no video signal",
            probable_cause="Cable loose",
            operator_fix_steps="Check the cable.",
        )
    )

    db_session.add(MachineHealth(machine_id=machine.id, is_online=True))
    db_session.add(Heartbeat(machine_id=machine.id, metrics={"cpu": 12.3}))

    db_session.add(
        Notification(
            user_id=user.id, ticket_id=ticket.id, channel=NotifyChannel.in_app, subject="New ticket"
        )
    )
    db_session.add(
        AuditLog(user_id=user.id, action="qr_scanned", entity_type="machine", entity_id=machine.id)
    )

    await db_session.flush()

    # Round-trip: refetch the machine via its plant/line FK chain.
    fetched = await db_session.scalar(select(Machine).where(Machine.id == machine.id))
    assert fetched is not None
    assert fetched.machine_type == MachineType.VISUAL_INSPECTION
    assert fetched.log_labels["machine"] == "vi"
