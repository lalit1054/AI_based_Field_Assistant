"""Python mirrors of the PostgreSQL enum types in database-schema.sql.

Each is wired to SQLAlchemy via `sqlalchemy.Enum(..., name=..., create_type=False)`
in the model files — the actual `CREATE TYPE` happens in the Alembic migration,
not via SQLAlchemy's own DDL, so these must stay byte-for-byte in sync with the
schema file's enum labels.
"""

import enum


class MachineType(str, enum.Enum):
    VISUAL_INSPECTION = "VISUAL_INSPECTION"


class OsType(str, enum.Enum):
    linux = "linux"
    windows = "windows"


class MachineStatus(str, enum.Enum):
    active = "active"
    maintenance = "maintenance"
    decommissioned = "decommissioned"


class UserRole(str, enum.Enum):
    operator = "operator"
    field_tech = "field_tech"
    support_l2 = "support_l2"
    support_l3 = "support_l3"
    plant_manager = "plant_manager"
    admin = "admin"
    company_viewer = "company_viewer"


class SessionStatus(str, enum.Enum):
    active = "active"
    resolved_self = "resolved_self"
    ticket_raised = "ticket_raised"
    abandoned = "abandoned"


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"


class TicketStatus(str, enum.Enum):
    new = "new"
    assigned = "assigned"
    in_progress = "in_progress"
    on_hold = "on_hold"
    resolved = "resolved"
    closed = "closed"
    reopened = "reopened"


class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IssueCategory(str, enum.Enum):
    connectivity = "connectivity"
    app_crash = "app_crash"
    api_error = "api_error"
    camera_image = "camera_image"
    data_mismatch = "data_mismatch"
    hardware = "hardware"
    power = "power"
    other = "other"


class AttachmentKind(str, enum.Enum):
    photo = "photo"
    video = "video"
    log_bundle = "log_bundle"
    document = "document"


class KbDocType(str, enum.Enum):
    runbook = "runbook"
    sop = "sop"
    oem_manual = "oem_manual"
    known_error = "known_error"
    resolved_ticket = "resolved_ticket"
    faq = "faq"


class NotifyChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"
    in_app = "in_app"


class NotifyStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
